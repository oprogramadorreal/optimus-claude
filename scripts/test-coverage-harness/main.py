#!/usr/bin/env python3
"""
Test-coverage harness — external orchestrator for iterative unit-test + refactor.

Alternates between /optimus:unit-test and /optimus:refactor testability in paired
cycles. Each cycle writes tests for already-testable code, then refactors
untestable code for better coverage. Fresh claude -p sessions per phase keep
context windows clean.

Requirements:
  - claude CLI installed and authenticated (Max subscription or API key)
  - Python 3.8+ (stdlib only — no pip dependencies)

Usage:
  /optimus:unit-test deep harness              # invoke from within a conversation
  /optimus:unit-test deep harness 5 "src/api"  # with cycle cap and scope

  python scripts/test-coverage-harness/main.py
  python scripts/test-coverage-harness/main.py --scope "src/api" --max-cycles 5
  python scripts/test-coverage-harness/main.py --resume

Security: By default, each claude -p session runs with --dangerously-skip-permissions
because the harness is headless — there is no terminal to approve tool prompts. For
a safer alternative, use --allowed-tools to restrict sessions to a specific tool
whitelist via --allowedTools.
"""

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Allow direct execution: python scripts/test-coverage-harness/main.py
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness_common.constants import BACKUP_SUFFIX, normalize_path
from harness_common.fixes import bisect_fixes
from harness_common.git import (
    git_diff_has_changes,
    git_rev_parse_head,
    git_stash_snapshot,
    restore_working_tree,
)
from harness_common.parser import parse_harness_output
from harness_common.reporting import detect_test_command
from impl.constants import (
    DEFAULT_MAX_CYCLES,
    DEFAULT_MAX_TURNS,
    DEFAULT_SESSION_TIMEOUT,
    MAX_CYCLES_HARD_CAP,
    PREFIX,
    PROGRESS_FILE_NAME,
)
from impl.convergence import (
    check_coverage_plateau,
    check_refactor_convergence,
    check_unit_test_convergence,
)
from impl.git import git_commit_checkpoint
from impl.progress import (
    make_initial_progress,
    read_progress,
    record_cycle_history,
    record_test_result,
    write_progress,
)
from impl.reporting import print_report
from impl.runner import run_coverage_session, run_tests

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def _build_argument_parser():
    """Build and return the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Test-coverage harness — iterative unit-test + refactor testability with fresh context per phase",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/test-coverage-harness/main.py
  python scripts/test-coverage-harness/main.py --scope "src/api" --max-cycles 5
  python scripts/test-coverage-harness/main.py --resume
        """,
    )
    parser.add_argument(
        "--max-cycles",
        type=int,
        default=DEFAULT_MAX_CYCLES,
        help=f"Cycle cap (default: {DEFAULT_MAX_CYCLES}, max: {MAX_CYCLES_HARD_CAP}). Each cycle = unit-test + refactor.",
    )
    parser.add_argument(
        "--scope",
        default="",
        help="Path filter or scope hint (e.g., 'src/auth')",
    )
    parser.add_argument(
        "--progress-file",
        default=PROGRESS_FILE_NAME,
        help=f"Path to progress file (default: {PROGRESS_FILE_NAME})",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=DEFAULT_MAX_TURNS,
        help=f"Per-session turn limit for claude -p (default: {DEFAULT_MAX_TURNS})",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from existing progress file",
    )
    parser.add_argument(
        "--no-commit",
        action="store_true",
        help="Skip checkpoint commits after each phase",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed skill session output",
    )
    parser.add_argument(
        "--test-command",
        default="",
        help="Override the test command (default: auto-detect from .claude/CLAUDE.md)",
    )
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Target project directory (default: current directory)",
    )
    parser.add_argument(
        "--allowed-tools",
        default="",
        help=(
            "Use --allowedTools instead of --dangerously-skip-permissions. "
            "Comma-separated list of tools to allow "
            "(default when flag is given without value: "
            "Read,Edit,Write,MultiEdit,Glob,Grep,Bash,Agent)"
        ),
        nargs="?",
        const="Read,Edit,Write,MultiEdit,Glob,Grep,Bash,Agent",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_SESSION_TIMEOUT,
        help=f"Per-session timeout in seconds (default: {DEFAULT_SESSION_TIMEOUT})",
    )
    return parser


# ---------------------------------------------------------------------------
# Environment and progress validation
# ---------------------------------------------------------------------------


def _validate_environment(project_root, args, _run=None):
    """Validate that claude CLI is available and a test command exists.

    Returns (test_command, None) on success, or (None, error_message) on failure.
    """
    _run = _run or subprocess.run
    try:
        claude_check = _run(["claude", "--version"], capture_output=True, text=True)
    except FileNotFoundError:
        claude_check = None
    if claude_check is None or claude_check.returncode != 0:
        return None, "claude CLI not found. Install and authenticate first."

    test_command = args.test_command or detect_test_command(project_root)
    if not test_command:
        return None, (
            "No test command found. Add one to .claude/CLAUDE.md or use --test-command."
        )
    return test_command, None


def _load_resumed_progress(progress_path, args, project_root):
    """Load and validate an existing progress file for resume.

    Returns (progress, None) on success, or (None, error_message) on failure.
    """
    path = progress_path
    if not path.exists():
        backup = Path(str(path) + BACKUP_SUFFIX)
        if backup.exists():
            print(f"{PREFIX} Progress file missing, restoring from backup.")
            shutil.copy2(str(backup), str(path))
        else:
            return None, f"No progress file found at {path}"

    try:
        progress = read_progress(path)
    except (ValueError, OSError) as exc:
        return None, f"Cannot read progress file: {exc}"

    if progress.get("harness") != "test-coverage":
        return None, (
            f"Progress file is for harness '{progress.get('harness')}', "
            f"not 'test-coverage'. Delete it or use a different --progress-file."
        )

    stored_root = progress.get("config", {}).get("project_root", "")
    if stored_root and normalize_path(str(project_root)) != stored_root:
        return None, (
            f"Progress file project_root '{stored_root}' does not match "
            f"current project '{normalize_path(str(project_root))}'"
        )

    # Allow extending cycle cap on resume
    if "config" not in progress or "max_cycles" not in progress.get("config", {}):
        return None, "Progress file is missing required 'config.max_cycles' field"
    if args.max_cycles > progress["config"]["max_cycles"]:
        progress["config"]["max_cycles"] = args.max_cycles

    return progress, None


# ---------------------------------------------------------------------------
# Unit-test phase helpers
# ---------------------------------------------------------------------------


def _process_unit_test_output(progress, result, cycle):
    """Process unit-test phase output, updating progress. Returns unit_test summary dict."""
    tests_written = result.get("tests_written", [])
    coverage = result.get("coverage", {})
    untestable = result.get("untestable_code", [])
    bugs = result.get("bugs_discovered", [])

    # Record tests created
    for test in tests_written:
        test["cycle"] = cycle
        progress["tests_created"].append(test)

    # Update coverage
    if coverage:
        if (
            progress["coverage"]["baseline"] is None
            and coverage.get("before") is not None
        ):
            progress["coverage"]["baseline"] = coverage["before"]
        if coverage.get("tool"):
            progress["coverage"]["tool"] = coverage["tool"]
        if coverage.get("after") is not None:
            progress["coverage"]["current"] = coverage["after"]
        progress["coverage"]["history"].append(
            {
                "cycle": cycle,
                "before": coverage.get("before"),
                "after": coverage.get("after"),
                "delta": coverage.get("delta"),
            }
        )

    # Merge untestable code — append new items, preserve prior cycles' entries.
    # Dedup key is (file, line, function) so multiple untestable functions in
    # the same file are all recorded; items missing a file are skipped.
    def _untestable_key(item):
        return (item.get("file"), item.get("line"), item.get("function"))

    existing_keys = {
        _untestable_key(item)
        for item in progress["untestable_code"]
        if item.get("file")
    }
    for item in untestable:
        if not item.get("file"):
            continue
        if _untestable_key(item) in existing_keys:
            continue
        existing_keys.add(_untestable_key(item))
        progress["untestable_code"].append(
            {
                **item,
                "cycle_reported": cycle,
                "status": "pending",
                "refactor_attempt_cycle": None,
            }
        )

    # Record bugs
    for bug in bugs:
        bug["cycle_discovered"] = cycle
        progress["bugs_discovered"].append(bug)

    tests_passed_count = sum(1 for t in tests_written if t.get("status") == "pass")
    return {
        "tests_written": len(tests_written),
        "tests_passed": tests_passed_count,
        "coverage_delta": coverage.get("delta", 0),
        "untestable_items_reported": len(untestable),
    }


def _revert_test_files(tests_written, cwd):
    """Delete test files created by the unit-test phase on test failure."""
    cwd_resolved = Path(cwd).resolve()
    for test in tests_written:
        filepath = (Path(cwd) / test.get("file", "")).resolve()
        try:
            rel = filepath.relative_to(cwd_resolved)
        except ValueError:
            continue
        # Refuse to delete anything inside .git/ — model-supplied paths must
        # never be able to unlink repo internals (mirrors fixes.py guard).
        if any(part == ".git" for part in rel.parts):
            continue
        if filepath.exists():
            try:
                filepath.unlink()
                print(f"{PREFIX} Reverted: {test.get('file')}")
            except OSError as exc:
                print(f"{PREFIX} WARNING: Could not delete {test.get('file')}: {exc}")


# ---------------------------------------------------------------------------
# Refactor phase helpers
# ---------------------------------------------------------------------------


def _finding_matches_fix(finding, fix):
    """Match a finding to a fix by file + pre_edit_content (the unique apply key)."""
    return finding.get("file") == fix.get("file") and finding.get(
        "pre_edit_content"
    ) == fix.get("pre_edit_content")


def _process_refactor_output(progress, result, cycle):
    """Process refactor phase output, updating progress. Returns refactor summary dict.

    Each new finding is stamped with an initial status: ``"fixed"`` if the
    finding appears in ``fixes_applied`` (Claude actually edited the code),
    otherwise ``"skipped — not applied"``. Bisection may later downgrade
    ``"fixed"`` entries to ``"reverted — test failure"`` via the
    ``bisect_fixes`` ``on_outcome`` callback.
    """
    fixes_applied = result.get("fixes_applied", [])
    new_findings = result.get("new_findings", [])

    for finding in new_findings:
        finding["cycle"] = cycle
        if any(_finding_matches_fix(finding, fix) for fix in fixes_applied):
            finding["status"] = "fixed"
        else:
            finding["status"] = "skipped — not applied"
        progress["refactor_findings"].append(finding)

    return {
        "findings_count": len(new_findings),
        "fixed": len(fixes_applied),
        "reverted": 0,
        "test_passed": True,
    }


_OUTCOME_TO_STATUS = {
    "fixed": "fixed",
    "reverted": "reverted — test failure",
    "retained": "fixed — revert failed",
    "skipped": "skipped — apply failed",
}


def _make_bisect_outcome_callback(progress, cycle):
    """Build an ``on_outcome`` callback that updates refactor_findings statuses
    based on per-fix bisection results. Matches by file + pre_edit_content."""
    findings = [
        f for f in progress.get("refactor_findings", []) if f.get("cycle") == cycle
    ]

    def _callback(idx, fix, outcome):
        new_status = _OUTCOME_TO_STATUS.get(outcome)
        if new_status is None:
            return
        for finding in findings:
            if _finding_matches_fix(finding, fix):
                finding["status"] = new_status
                break

    return _callback


# ---------------------------------------------------------------------------
# Startup info
# ---------------------------------------------------------------------------


def _print_startup_info(args, progress):
    """Print startup banner with configuration summary."""
    max_cycles = progress["config"]["max_cycles"]
    test_command = progress["config"]["test_command"]
    scope = progress["config"]["scope"]
    cycle = progress["cycle"]["current"]
    phase = progress.get("phase", "unit-test")
    remaining_this_cycle = 1 if phase == "refactor" else 2
    estimated_sessions = remaining_this_cycle + (max_cycles - cycle) * 2

    print(f"{PREFIX} Test-Coverage Harness")
    print(f"{PREFIX} {'=' * 40}")
    print(f"{PREFIX}   Max cycles:    {max_cycles}")
    print(f"{PREFIX}   Starting at:   cycle {cycle}")
    print(f"{PREFIX}   Test command:  {test_command}")
    if scope:
        print(f"{PREFIX}   Scope:         {scope}")
    print(f"{PREFIX}   Est. sessions: ~{estimated_sessions}")
    print(f"{PREFIX} {'=' * 40}")


# ---------------------------------------------------------------------------
# Interrupt handling
# ---------------------------------------------------------------------------


def _count_phase_summary(progress, cycle, phase):
    """Derive a phase_summary for the interrupt checkpoint from stored progress.

    Without this, git_commit_checkpoint defaults phase_summary to {} and the
    commit title always reports "0 tests written" / "0 fixed" even when the
    interrupted phase had completed real work.
    """
    if phase == "unit-test":
        tests_written = sum(
            1 for t in progress.get("tests_created", []) if t.get("cycle") == cycle
        )
        return {"tests_written": tests_written}
    fixed = sum(
        1
        for f in progress.get("refactor_findings", [])
        if f.get("cycle") == cycle and f.get("status") == "fixed"
    )
    return {"fixed": fixed}


def _handle_interrupt(args, progress, progress_path, project_root):
    """Handle Ctrl+C gracefully — commit completed work and save progress."""
    print(f"\n{PREFIX} Interrupted — saving progress...")
    progress["termination"] = {
        "reason": "interrupted",
        "message": "User interrupted with Ctrl+C",
    }
    write_progress(progress_path, progress)

    if not args.no_commit and git_diff_has_changes(project_root):
        cycle = progress["cycle"]["current"]
        phase = progress.get("phase", "unit-test")
        phase_summary = _count_phase_summary(progress, cycle, phase)
        if git_commit_checkpoint(
            progress,
            cycle,
            phase,
            project_root,
            phase_summary,
            progress_file=str(progress_path),
        ):
            print(f"{PREFIX} Checkpoint: committed completed work before exit")

    print_report(progress)


# ---------------------------------------------------------------------------
# Archive progress
# ---------------------------------------------------------------------------


def _archive_progress(progress_path):
    """Rename the progress file to indicate completion."""
    p = Path(progress_path)
    done_path = p.with_name(p.stem + "-done" + p.suffix)
    try:
        p.rename(done_path)
    except OSError:
        pass  # Not critical — the file stays as-is
    # Clean up backup file to prevent stale resume
    Path(str(progress_path) + BACKUP_SUFFIX).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Phase runners (extracted from _run_cycle_loop for testability and SRP)
# ---------------------------------------------------------------------------


def _run_unit_test_phase(
    args,
    progress,
    progress_path,
    project_root,
    test_command,
    cycle,
    pre_stash,
    pre_head,
    *,
    skip_commits,
):
    """Run the unit-test phase of a cycle.

    Returns (action, ut_summary, pre_head, skip_commits) where action is:
    - "break": fatal error or parse failure (termination already recorded)
    - "continue": tests failed, caller should skip to next cycle
    - "converged": convergence reached (termination already recorded)
    - "proceed": success, continue to refactor phase
    """
    progress["phase"] = "unit-test"
    write_progress(progress_path, progress)
    print(f"{PREFIX} --- Phase: unit-test ---")

    ut_start = time.time()
    try:
        ut_output = run_coverage_session(progress, args, progress_path, "unit-test")
    except (RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"{PREFIX} ERROR: Unit-test session failed: {exc}")
        restore_working_tree(pre_stash, pre_head, project_root)
        progress["termination"] = {
            "reason": "crash",
            "message": f"Unit-test session failed on cycle {cycle}: {exc}",
        }
        write_progress(progress_path, progress)
        return "break", None, pre_head, skip_commits

    ut_result = parse_harness_output(ut_output)
    ut_elapsed = int(time.time() - ut_start)

    if ut_result is None:
        print(
            f"{PREFIX} WARNING: No parseable output from unit-test session ({ut_elapsed}s)"
        )
        test_passed, test_summary = run_tests(test_command, project_root)
        record_test_result(progress, test_passed, test_summary)
        if not test_passed:
            restore_working_tree(pre_stash, pre_head, project_root)
        progress["termination"] = {
            "reason": "parse-failure",
            "message": f"Unit-test session produced no parseable JSON output on cycle {cycle}",
        }
        write_progress(progress_path, progress)
        return "break", None, pre_head, skip_commits

    ut_tests = ut_result.get("tests_written", [])
    print(
        f"{PREFIX} Unit-test session complete — "
        f"{len(ut_tests)} tests written ({ut_elapsed}s)"
    )

    # Verify new test files pass
    test_passed, test_summary = run_tests(test_command, project_root)
    record_test_result(progress, test_passed, test_summary)
    ut_summary = _process_unit_test_output(progress, ut_result, cycle)

    if not test_passed:
        print(
            f"{PREFIX} Tests failed after unit-test phase — restoring pre-cycle state"
        )
        # Use restore_working_tree (not just _revert_test_files) so that any
        # production-source edits the unit-test session may have left behind
        # are also rolled back, not only the declared test files. The
        # unit-test phase is supposed to write tests only, but we cannot
        # trust the session to honour that — defensively restore everything.
        restore_working_tree(pre_stash, pre_head, project_root)
        reverted_files = {t.get("file") for t in ut_tests}
        # Scope the revert to current-cycle entries: a later cycle may legitimately
        # rewrite a test file that a prior cycle created, and we must not drop the
        # prior cycle's record just because its file path matches.
        progress["tests_created"] = [
            t
            for t in progress["tests_created"]
            if not (t.get("cycle") == cycle and t.get("file") in reverted_files)
        ]
        ut_summary["test_passed"] = False
        record_cycle_history(progress, cycle, ut_summary)
        write_progress(progress_path, progress)
        return "continue", ut_summary, pre_head, skip_commits

    ut_summary["test_passed"] = True

    # Checkpoint commit
    if not skip_commits and git_diff_has_changes(project_root):
        if git_commit_checkpoint(
            progress,
            cycle,
            "unit-test",
            project_root,
            ut_summary,
            progress_file=str(progress_path),
        ):
            print(f"{PREFIX} Checkpoint: test(coverage-harness): cycle {cycle}")
            pre_head = git_rev_parse_head(project_root) or pre_head
        else:
            print(
                f"{PREFIX} WARNING: Checkpoint failed — skipping commits for remaining cycles"
            )
            skip_commits = True

    # Check convergence
    converged, reason = check_unit_test_convergence(ut_result)
    if converged:
        record_cycle_history(progress, cycle, ut_summary)
        progress["termination"] = {"reason": "convergence", "message": reason}
        write_progress(progress_path, progress)
        print(f"{PREFIX} Converged: {reason}")
        return "converged", ut_summary, pre_head, skip_commits

    return "proceed", ut_summary, pre_head, skip_commits


def _run_refactor_phase(
    args,
    progress,
    progress_path,
    project_root,
    test_command,
    cycle,
    pre_stash,
    pre_head,
    ut_summary,
    *,
    skip_commits,
):
    """Run the refactor phase of a cycle (conditional on pending untestable items).

    Returns (action, refactor_summary, skip_commits) where action is:
    - "break": fatal error or parse failure (termination already recorded)
    - "skip": no pending untestable items — phase skipped
    - "converged": convergence reached (termination already recorded)
    - "proceed": success
    """
    pending_untestable = [
        i for i in progress.get("untestable_code", []) if i.get("status") == "pending"
    ]
    if not pending_untestable:
        return "skip", None, skip_commits

    progress["phase"] = "refactor"
    write_progress(progress_path, progress)
    print(
        f"{PREFIX} --- Phase: refactor (testability) — {len(pending_untestable)} items ---"
    )

    rf_start = time.time()
    try:
        rf_output = run_coverage_session(progress, args, progress_path, "refactor")
    except (RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"{PREFIX} ERROR: Refactor session failed: {exc}")
        restore_working_tree(pre_stash, pre_head, project_root)
        record_cycle_history(progress, cycle, ut_summary)
        progress["termination"] = {
            "reason": "crash",
            "message": f"Refactor session failed on cycle {cycle}: {exc}",
        }
        write_progress(progress_path, progress)
        return "break", None, skip_commits

    rf_result = parse_harness_output(rf_output)
    rf_elapsed = int(time.time() - rf_start)

    if rf_result is None:
        print(
            f"{PREFIX} WARNING: No parseable output from refactor session ({rf_elapsed}s)"
        )
        record_cycle_history(progress, cycle, ut_summary)
        progress["termination"] = {
            "reason": "parse-failure",
            "message": f"Refactor session produced no parseable JSON output on cycle {cycle}",
        }
        write_progress(progress_path, progress)
        return "break", None, skip_commits

    fixes = rf_result.get("fixes_applied", [])
    print(
        f"{PREFIX} Refactor session complete — "
        f"{len(fixes)} fixes applied ({rf_elapsed}s)"
    )

    refactor_summary = _process_refactor_output(progress, rf_result, cycle)

    # Test and bisect fixes
    if fixes:
        test_passed, test_summary = run_tests(test_command, project_root)
        record_test_result(progress, test_passed, test_summary)

        if not test_passed:
            print(f"{PREFIX} Tests failed after refactor — bisecting fixes")
            on_outcome = _make_bisect_outcome_callback(progress, cycle)
            fixed_count, reverted_count, skipped_count = bisect_fixes(
                fixes, test_command, str(project_root), on_outcome=on_outcome
            )
            refactor_summary["fixed"] = fixed_count
            refactor_summary["reverted"] = reverted_count
            refactor_summary["skipped"] = skipped_count
            # "test_passed" only when at least one fix survived bisection.
            # When fixed_count == 0 the working tree is in the all-reverted
            # state — pre-fix code that was already passing — so reporting
            # test_passed=True would mislead callers into treating a no-op
            # cycle as a successful refactor.
            refactor_summary["test_passed"] = fixed_count > 0

            if fixed_count == 0:
                print(
                    f"{PREFIX} No refactor fixes survived bisection "
                    f"(reverted={reverted_count}, skipped={skipped_count})."
                )
            else:
                combo_passed, combo_summary = run_tests(test_command, project_root)
                record_test_result(progress, combo_passed, combo_summary)
                if not combo_passed:
                    print(f"{PREFIX} Combined test failed — restoring working tree")
                    restore_working_tree(pre_stash, pre_head, project_root)
                    refactor_summary["test_passed"] = False
                    refactor_summary["fixed"] = 0
                    # Subtract already-classified skipped count so the totals
                    # (fixed + reverted + skipped) still equal len(fixes).
                    refactor_summary["reverted"] = len(fixes) - skipped_count
                    # Roll back per-finding statuses to match the restored tree.
                    # restore_working_tree resets to pre_head, so even retained
                    # fixes (status "fixed — revert failed") are gone now.
                    rollback_statuses = {"fixed", "fixed — revert failed"}
                    for finding in progress.get("refactor_findings", []):
                        if (
                            finding.get("cycle") == cycle
                            and finding.get("status") in rollback_statuses
                        ):
                            finding["status"] = "reverted — combined regression"

    # Mark untestable code items as attempted only when fixes actually survived
    if refactor_summary["fixed"] > 0:
        for item in progress.get("untestable_code", []):
            if item.get("status") == "pending":
                item["refactor_attempt_cycle"] = cycle
                item["status"] = "attempted"

    # Checkpoint commit
    if not skip_commits and git_diff_has_changes(project_root):
        if git_commit_checkpoint(
            progress,
            cycle,
            "refactor",
            project_root,
            refactor_summary,
            progress_file=str(progress_path),
        ):
            print(f"{PREFIX} Checkpoint: refactor(coverage-harness): cycle {cycle}")
        else:
            print(
                f"{PREFIX} WARNING: Checkpoint failed — skipping commits for remaining cycles"
            )
            skip_commits = True

    # Check convergence
    converged, reason = check_refactor_convergence(rf_result)
    if converged:
        record_cycle_history(progress, cycle, ut_summary, refactor_summary)
        coverage_plateau, plateau_reason = check_coverage_plateau(
            progress["coverage"]["history"]
        )
        if coverage_plateau:
            reason = plateau_reason
        progress["termination"] = {"reason": "convergence", "message": reason}
        write_progress(progress_path, progress)
        print(f"{PREFIX} Converged: {reason}")
        return "converged", refactor_summary, skip_commits

    return "proceed", refactor_summary, skip_commits


# ---------------------------------------------------------------------------
# Main cycle loop
# ---------------------------------------------------------------------------


def _run_cycle_loop(
    args, progress, progress_path, project_root, test_command, max_cycles
):
    """Run the paired unit-test + refactor cycle loop until convergence or cap."""
    skip_commits = args.no_commit

    while True:
        cycle = progress["cycle"]["current"]
        print(f"\n{PREFIX} === Cycle {cycle}/{max_cycles} ===")

        pre_head = git_rev_parse_head(project_root)
        if not pre_head:
            print(f"{PREFIX} ERROR: Cannot determine HEAD commit before cycle {cycle}.")
            progress["termination"] = {
                "reason": "error",
                "message": f"Cannot determine HEAD commit before cycle {cycle}",
            }
            write_progress(progress_path, progress)
            break

        pre_stash = git_stash_snapshot(project_root) if args.no_commit else None

        # ---- Unit-test phase ----
        action, ut_summary, pre_head, skip_commits = _run_unit_test_phase(
            args,
            progress,
            progress_path,
            project_root,
            test_command,
            cycle,
            pre_stash,
            pre_head,
            skip_commits=skip_commits,
        )
        if action in ("break", "converged"):
            break
        if action == "continue":
            if cycle >= max_cycles:
                progress["termination"] = {
                    "reason": "cap",
                    "message": f"Reached cycle cap ({max_cycles})",
                }
                write_progress(progress_path, progress)
                break
            progress["cycle"]["current"] += 1
            continue

        # Refresh snapshot after a successful unit-test phase so that a
        # refactor-phase rollback only undoes refactor changes. Without this,
        # --no-commit mode would restore to the pre-unit-test state on combo
        # failure and silently discard the tests the unit-test phase just
        # wrote and verified.
        if args.no_commit:
            pre_stash = git_stash_snapshot(project_root)
            pre_head = git_rev_parse_head(project_root) or pre_head

        # ---- Refactor phase ----
        action, refactor_summary, skip_commits = _run_refactor_phase(
            args,
            progress,
            progress_path,
            project_root,
            test_command,
            cycle,
            pre_stash,
            pre_head,
            ut_summary,
            skip_commits=skip_commits,
        )
        if action in ("break", "converged"):
            break

        # Record cycle history
        record_cycle_history(progress, cycle, ut_summary, refactor_summary)

        # Check coverage plateau
        coverage_plateau, plateau_reason = check_coverage_plateau(
            progress["coverage"]["history"]
        )
        if coverage_plateau:
            progress["termination"] = {
                "reason": "convergence",
                "message": plateau_reason,
            }
            write_progress(progress_path, progress)
            print(f"{PREFIX} {plateau_reason}")
            break

        # Check cycle cap
        if cycle >= max_cycles:
            progress["termination"] = {
                "reason": "cap",
                "message": f"Reached cycle cap ({max_cycles})",
            }
            write_progress(progress_path, progress)
            print(f"{PREFIX} Cycle cap reached ({max_cycles}).")
            break

        progress["cycle"]["current"] += 1
        write_progress(progress_path, progress)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv=None):
    args = _build_argument_parser().parse_args(argv)

    # Clamp cycles
    if args.max_cycles > MAX_CYCLES_HARD_CAP:
        print(f"{PREFIX} Cycle cap clamped to {MAX_CYCLES_HARD_CAP} (maximum).")
        args.max_cycles = MAX_CYCLES_HARD_CAP
    if args.max_cycles < 1:
        print(f"{PREFIX} Cycle cap clamped to 1 (minimum).")
        args.max_cycles = 1

    project_root = Path(args.project_dir).resolve()
    test_command, env_error = _validate_environment(project_root, args)
    if env_error:
        print(f"{PREFIX} ERROR: {env_error}")
        return 1

    # Initialize or resume
    progress_path = Path(args.progress_file)
    if not progress_path.is_absolute():
        progress_path = project_root / progress_path

    if args.resume:
        progress, resume_error = _load_resumed_progress(
            progress_path, args, project_root
        )
        if resume_error:
            print(f"{PREFIX} ERROR: {resume_error}")
            return 1
        # Sync freshly detected test command into resumed progress
        progress["config"]["test_command"] = test_command
    else:
        if progress_path.exists():
            print(
                f"{PREFIX} WARNING: Overwriting existing progress file: {progress_path}"
            )
        progress = make_initial_progress(
            args.scope,
            args.max_cycles,
            test_command,
            project_root,
        )

    # Validate base commit
    if not progress["config"]["base_commit"]:
        print(
            f"{PREFIX} ERROR: Cannot determine HEAD commit. Is this a git repository?"
        )
        return 1

    # Refuse to start with uncommitted changes (fresh runs only)
    if not args.resume and not args.no_commit and git_diff_has_changes(project_root):
        print(f"{PREFIX} ERROR: Uncommitted changes detected.")
        print(f"{PREFIX} The harness creates checkpoint commits per phase,")
        print(
            f"{PREFIX} which would include your existing changes in the first commit."
        )
        print(f"{PREFIX}")
        print(f'{PREFIX} Commit your changes first:  git add -A && git commit -m "wip"')
        print(f'{PREFIX} Or stash them:              git stash push -m "pre-harness"')
        return 1

    _print_startup_info(args, progress)

    # Main cycle loop
    try:
        _run_cycle_loop(
            args,
            progress,
            progress_path,
            project_root,
            test_command,
            progress["config"]["max_cycles"],
        )
    except KeyboardInterrupt:
        _handle_interrupt(args, progress, progress_path, project_root)
        return 0

    # Final report and cleanup
    print_report(progress)
    _archive_progress(progress_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
