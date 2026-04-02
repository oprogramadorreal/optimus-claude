#!/usr/bin/env python3
"""
Deep-mode harness — external orchestrator for iterative code review / refactor.

Launches fresh `claude -p` sessions per iteration, passing state through a JSON
progress file. Each session gets a clean context window, eliminating the context
bloat that limits in-conversation deep mode to ~3 effective iterations.

Requirements:
  - claude CLI installed and authenticated (Max subscription or API key)
  - Python 3.8+ (stdlib only — no pip dependencies)

Usage:
  /optimus:code-review deep harness            # invoke from within a conversation
  /optimus:refactor deep harness 8 "backend"   # with iteration cap and scope
  /optimus:refactor deep harness testability   # with focus mode

  python scripts/deep-mode-harness/main.py --skill code-review
  python scripts/deep-mode-harness/main.py --skill code-review --scope "src/auth"
  python scripts/deep-mode-harness/main.py --skill refactor --max-iterations 8 --scope "src/api"
  python scripts/deep-mode-harness/main.py --skill refactor --focus testability
  python scripts/deep-mode-harness/main.py --skill refactor --focus guidelines --scope "src/api"
  python scripts/deep-mode-harness/main.py --skill code-review --resume

Security: By default, each claude -p session runs with --dangerously-skip-permissions
because the harness is headless — there is no terminal to approve tool prompts. This
bypasses allow/deny lists and PreToolUse hooks. For a safer alternative, use
--allowed-tools to restrict sessions to a specific tool whitelist via --allowedTools.
For OS-level isolation, use Claude Code's built-in sandboxing (macOS/Linux) or
devcontainers.

The test command is extracted from .claude/CLAUDE.md or --test-command and executed
via shell=True. Treat cloned repos as untrusted — review .claude/CLAUDE.md before
running the harness on unfamiliar codebases.
"""

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Allow direct execution: python scripts/deep-mode-harness/main.py
sys.path.insert(0, str(Path(__file__).resolve().parent))

from impl.constants import (
    BACKUP_SUFFIX,
    DEFAULT_MAX_ITERATIONS,
    DEFAULT_MAX_TURNS,
    DEFAULT_SESSION_TIMEOUT,
    MAX_ITERATIONS_HARD_CAP,
    PERSISTENT_STATUS,
    PREFIX,
    PROGRESS_FILE_NAME,
    VALID_FOCUS_MODES,
)
from impl.findings import (
    finding_key,
    finding_matches,
    mark_all_fixed,
    mark_finding_status,
    update_scope,
)
from impl.fixes import bisect_fixes
from impl.git import (
    git_commit_checkpoint,
    git_diff_has_changes,
    git_rev_parse_head,
    git_stash_snapshot,
    restore_working_tree,
)
from impl.parser import parse_harness_output
from impl.progress import (
    make_initial_progress,
    read_progress,
    record_test_result,
    write_progress,
)
from impl.reporting import detect_test_command, print_report
from impl.runner import run_skill_session, run_tests

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def _build_argument_parser():
    """Build and return the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Deep-mode harness — iterative code review/refactor with fresh context per iteration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/deep-mode-harness/main.py --skill code-review
  python scripts/deep-mode-harness/main.py --skill refactor --max-iterations 8 --scope "src/api"
  python scripts/deep-mode-harness/main.py --skill code-review --resume
        """,
    )
    parser.add_argument(
        "--skill",
        required=True,
        choices=["code-review", "refactor"],
        help="Which skill to run in deep mode",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=DEFAULT_MAX_ITERATIONS,
        help=f"Iteration cap (default: {DEFAULT_MAX_ITERATIONS}, max: {MAX_ITERATIONS_HARD_CAP})",
    )
    parser.add_argument(
        "--scope",
        default="",
        help="Path filter or scope hint (e.g., 'src/auth')",
    )
    parser.add_argument(
        "--focus",
        choices=sorted(VALID_FOCUS_MODES),
        default="",
        help="Finding-cap priority: testability or guidelines (refactor only; default: balanced)",
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
        help="Skip checkpoint commits after each iteration",
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
        help=f"Per-iteration timeout in seconds (default: {DEFAULT_SESSION_TIMEOUT})",
    )
    return parser


# ---------------------------------------------------------------------------
# Environment and progress validation
# ---------------------------------------------------------------------------


def _validate_environment(project_root, args):
    """Validate that claude CLI is available and a test command exists.

    Returns (test_command, None) on success, or (None, error_message) on failure.
    """
    try:
        claude_check = subprocess.run(
            ["claude", "--version"], capture_output=True, text=True
        )
    except FileNotFoundError:
        claude_check = None
    if claude_check is None or claude_check.returncode != 0:
        return None, "claude CLI not found. Install and authenticate first."

    test_command = args.test_command or detect_test_command(project_root)
    if not test_command:
        return None, (
            "No test command found in .claude/CLAUDE.md.\n"
            f"{PREFIX} Deep mode requires a test command for safe auto-apply.\n"
            f"{PREFIX} Run /optimus:init to set up test infrastructure, or pass --test-command."
        )

    return test_command, None


def _load_resumed_progress(progress_path, args, project_root):
    """Load and validate a progress file for --resume.

    Returns (progress_dict, None) on success, or (None, error_message) on failure.
    """
    if not progress_path.exists():
        backup = Path(str(progress_path) + BACKUP_SUFFIX)
        if backup.exists():
            print(f"{PREFIX} Progress file not found, restoring from backup...")
            shutil.copy2(str(backup), str(progress_path))
        else:
            return None, f"No progress file to resume from: {progress_path}"

    progress = read_progress(progress_path)

    for key in ("skill", "iteration", "config", "findings"):
        if key not in progress:
            return None, f"Progress file missing required field '{key}'"

    if progress["skill"] != args.skill:
        return None, (
            f"Progress file skill '{progress['skill']}' "
            f"does not match --skill '{args.skill}'"
        )

    saved_root_str = progress["config"].get("project_root")
    if not saved_root_str:
        return None, "Progress file missing project_root"
    if Path(saved_root_str).resolve() != project_root:
        return None, (
            f"Progress file project_root '{saved_root_str}' "
            f"does not match --project-dir '{project_root}'"
        )

    # Allow extending the iteration cap on resume
    if args.max_iterations != DEFAULT_MAX_ITERATIONS:
        progress["config"]["max_iterations"] = args.max_iterations

    print(f"{PREFIX} Resuming from iteration {progress['iteration']['current']}")
    return progress, None


# ---------------------------------------------------------------------------
# Startup and shutdown helpers
# ---------------------------------------------------------------------------


def _print_startup_info(args, progress):
    """Print harness startup information."""
    max_iter = progress["config"]["max_iterations"]
    test_command = progress["config"]["test_command"]
    remaining = max_iter - progress["iteration"]["current"] + 1
    agents_per_iteration = 7 if args.skill == "code-review" else 4
    estimated_messages = remaining * agents_per_iteration + remaining
    print(f"{PREFIX} Starting {args.skill} harness (max {max_iter} iterations)")
    print(f"{PREFIX} Test command: {test_command}")
    print(f"{PREFIX} Base commit: {progress['config']['base_commit'][:8]}")
    print(f"{PREFIX} Estimated messages: ~{estimated_messages} (check rate limits)")
    focus = progress["config"].get("focus", "")
    if focus and args.skill == "refactor":
        print(f"{PREFIX} Focus: {focus}")
    print(f"{PREFIX} Press Ctrl+C to stop — progress is saved. Resume with --resume.")
    print(f"{PREFIX}")


def _handle_interrupt(args, progress, progress_path, project_root):
    """Handle Ctrl+C gracefully: commit work, save progress, print report."""
    print(f"\n{PREFIX} Interrupted.")
    iteration = progress["iteration"]["current"]
    if not args.no_commit and git_diff_has_changes(project_root):
        print(f"{PREFIX} Committing completed work from current iteration...")
        # Interrupt may occur before _record_iteration_history runs
        if (
            not progress["iteration_history"]
            or progress["iteration_history"][-1].get("iteration") != iteration
        ):
            _record_iteration_history(progress, iteration, 0, 0, 0, False)
        git_commit_checkpoint(progress, iteration, project_root)
    progress["termination"] = {
        "reason": "interrupted",
        "message": "User pressed Ctrl+C",
    }
    write_progress(progress_path, progress)
    print(f"{PREFIX} Progress saved. Resume with --resume flag.")
    print_report(progress)


def _archive_progress(progress_path):
    """Move progress file to .done.json and clean up backup."""
    done_path = progress_path.with_suffix(".done.json")
    if done_path.exists():
        done_path.unlink()
    shutil.move(str(progress_path), str(done_path))
    Path(str(progress_path) + BACKUP_SUFFIX).unlink(missing_ok=True)
    print(f"{PREFIX} Progress archived to {done_path.name}")


# ---------------------------------------------------------------------------
# Iteration loop helpers
# ---------------------------------------------------------------------------


def _handle_safe_exit(
    progress,
    progress_path,
    args,
    test_command,
    project_root,
    pre_snapshot,
    pre_hash,
    *,
    reason,
    message,
    log_message,
    new_count,
):
    """Handle convergence or no-actionable-fixes exit with test verification."""
    iteration = progress["iteration"]["current"]
    test_passed = True
    if git_diff_has_changes(project_root):
        print(f"{PREFIX} {log_message} but working tree has changes — verifying tests")
        test_passed, summary = run_tests(test_command, project_root)
        record_test_result(progress, test_passed, summary)
        if not test_passed:
            print(f"{PREFIX} Tests failed — reverting unexpected changes")
            restore_working_tree(pre_snapshot, pre_hash, project_root)
    progress["termination"] = {"reason": reason, "message": message}
    _record_iteration_history(progress, iteration, new_count, 0, 0, test_passed)
    write_progress(progress_path, progress)
    if not args.no_commit and test_passed and git_diff_has_changes(project_root):
        git_commit_checkpoint(progress, iteration, project_root)


def _run_session_with_retry(
    args, progress, progress_path, pre_stash, pre_head, project_root, iteration
):
    """Launch a claude session with one retry on failure.

    Returns raw output on success, or None if both attempts failed.
    On failure, sets progress termination reason before returning.
    """
    for attempt in range(2):
        try:
            return run_skill_session(progress, args, progress_path)
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            if isinstance(exc, subprocess.TimeoutExpired):
                print(f"{PREFIX} Session timed out after {args.timeout}s")
            else:
                print(f"{PREFIX} Session error: {exc}")
            restore_working_tree(pre_stash, pre_head, project_root)
            if attempt == 0:
                write_progress(progress_path, progress)
                print(f"{PREFIX} Retrying iteration {iteration}...")
            else:
                print(f"{PREFIX} Iteration {iteration} failed after retry. Stopping.")
                progress["termination"] = {
                    "reason": "crash",
                    "message": f"Session failed twice on iteration {iteration}: {exc}",
                }
                write_progress(progress_path, progress)
                return None


def _recover_from_missing_output(
    output, test_command, project_root, pre_stash, pre_head, progress, progress_path
):
    """Handle iterations where the skill produced no parseable JSON output.

    Returns a synthetic result dict if recovery succeeds, or None on failure.
    On failure, sets progress termination reason before returning.
    """
    if not git_diff_has_changes(project_root):
        print(f"{PREFIX} No output and no changes — treating as convergence")
        return {
            "no_new_findings": True,
            "no_actionable_fixes": False,
            "fixes_applied": [],
            "new_findings": [],
        }

    print(f"{PREFIX} No JSON output but git shows changes — proceeding to test")
    if output and len(output) < 50:
        print(
            f"{PREFIX}   Hint: session output was very short — may have hit max-turns limit"
        )
    elif not output:
        print(f"{PREFIX}   Hint: session produced no output (likely timed out)")

    test_passed, test_summary = run_tests(test_command, project_root)
    record_test_result(progress, test_passed, test_summary)
    if test_passed:
        # Changes passed tests but are untracked — stop to avoid silent drift
        return {
            "no_new_findings": False,
            "no_actionable_fixes": True,
            "fixes_applied": [],
            "new_findings": [],
        }

    print(f"{PREFIX} Tests failed with unparseable output — reverting iteration")
    if test_summary:
        for line in test_summary.split("\n"):
            print(f"{PREFIX}   {line}")
    restore_working_tree(pre_stash, pre_head, project_root)
    progress["termination"] = {
        "reason": "parse-failure",
        "message": "Could not parse skill output and tests failed",
    }
    write_progress(progress_path, progress)
    return None


def _register_iteration_findings(progress, result, fixes):
    """Register applied fixes and discovered-but-not-applied findings."""
    applied_keys = {finding_key(f) for f in fixes}
    for fix in fixes:
        mark_finding_status(progress, fix, "applied-pending-test", None)
    for new_finding in result.get("new_findings", []):
        if finding_key(new_finding) not in applied_keys:
            mark_finding_status(progress, new_finding, "discovered", None)


def _mark_combined_regression(fixes, progress):
    """Mark individually-passing fixes as reverted due to combined test failure.

    After restore_working_tree, all changes are gone — both "fixed" and
    "retained — revert failed" findings need their status updated.
    """
    reverted = 0
    for fix in fixes:
        for finding in progress["findings"]:
            if not finding_matches(finding, fix):
                continue
            status = finding.get("status")
            if status == "fixed":
                mark_finding_status(
                    progress,
                    fix,
                    "reverted — test failure",
                    "Interaction bug — combined fixes failed",
                )
                reverted += 1
            elif status == "retained — revert failed":
                mark_finding_status(
                    progress,
                    fix,
                    "reverted — test failure",
                    "Interaction bug — full working tree restore removed retained fix",
                )
                reverted += 1
            break
    return reverted


def _test_and_reconcile_fixes(
    fixes, test_command, project_root, progress, pre_stash, pre_head
):
    """Run tests on applied fixes, bisecting on failure.

    Returns (fixed_count, reverted_count, test_passed, all_reverted).
    """
    if not fixes:
        return 0, 0, True, False

    test_passed, test_summary = run_tests(test_command, project_root)
    record_test_result(progress, test_passed, test_summary)

    if test_passed:
        mark_all_fixed(progress, fixes)
        print(f"{PREFIX} Results: {len(fixes)} fixed, 0 reverted")
        return len(fixes), 0, True, False

    # Bisect: revert all, re-apply one-by-one
    fixed_count, reverted_count, skipped_count = bisect_fixes(
        fixes, test_command, project_root, progress
    )
    print(
        f"{PREFIX} Results: {fixed_count} fixed, "
        f"{reverted_count} reverted, {skipped_count} skipped (bisection)"
    )

    # Verify combined fixes don't interact badly
    if fixed_count > 0:
        test_passed, test_summary = run_tests(test_command, project_root)
        record_test_result(progress, test_passed, test_summary)
        if not test_passed:
            print(
                f"{PREFIX} WARNING: Combined fixes fail tests — interaction bug, reverting all"
            )
            restore_working_tree(pre_stash, pre_head, project_root)
            interaction_reverted = _mark_combined_regression(fixes, progress)
            reverted_count += interaction_reverted
            fixed_count -= interaction_reverted

    all_reverted = fixed_count == 0 and reverted_count > 0
    return fixed_count, reverted_count, test_passed, all_reverted


def _record_iteration_history(
    progress, iteration, new_count, fixed_count, reverted_count, test_passed
):
    """Append an entry to the iteration history."""
    persistent_count = sum(
        1
        for f in progress["findings"]
        if f["status"] == PERSISTENT_STATUS
        and f.get("iteration_last_attempted") == iteration
    )
    progress["iteration_history"].append(
        {
            "iteration": iteration,
            "new_findings": new_count,
            "fixed": fixed_count,
            "reverted": reverted_count,
            "persistent": persistent_count,
            "test_passed": test_passed,
        }
    )
    progress["iteration"]["completed"] = iteration


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def _run_iteration_loop(
    args, progress, progress_path, project_root, test_command, max_iter
):
    """Run the iterative analysis-apply loop until convergence or cap."""
    skip_commits = args.no_commit
    while True:
        iteration = progress["iteration"]["current"]
        print(f"{PREFIX} === Iteration {iteration}/{max_iter} ===")
        iteration_start = time.time()

        pre_head = git_rev_parse_head(project_root)
        if not pre_head:
            print(
                f"{PREFIX} ERROR: Cannot determine HEAD commit before iteration {iteration}."
            )
            progress["termination"] = {
                "reason": "error",
                "message": f"Cannot determine HEAD commit before iteration {iteration}",
            }
            write_progress(progress_path, progress)
            break

        # When --no-commit, prior iterations leave uncommitted changes.
        # Snapshot them so we can restore on failure without losing that work.
        # Use args.no_commit (not skip_commits) so a commit failure doesn't
        # change the stash strategy.
        pre_stash = git_stash_snapshot(project_root) if args.no_commit else None

        write_progress(progress_path, progress)

        output = _run_session_with_retry(
            args,
            progress,
            progress_path,
            pre_stash,
            pre_head,
            project_root,
            iteration,
        )
        if output is None:
            break

        result = parse_harness_output(output)
        elapsed = int(time.time() - iteration_start)

        if result is None:
            result = _recover_from_missing_output(
                output,
                test_command,
                project_root,
                pre_stash,
                pre_head,
                progress,
                progress_path,
            )
            if result is None:
                break

        new_count = len(result.get("new_findings", []))
        applied_count = len(result.get("fixes_applied", []))
        print(
            f"{PREFIX} Skill session complete — "
            f"{new_count} new findings, {applied_count} fixes applied ({elapsed}s)"
        )

        # Check early-exit conditions (convergence or no actionable fixes)
        if result.get("no_new_findings", False):
            _register_iteration_findings(progress, result, fixes=[])
            _handle_safe_exit(
                progress,
                progress_path,
                args,
                test_command,
                project_root,
                pre_stash,
                pre_head,
                reason="convergence",
                message=f"Zero new findings on iteration {iteration}",
                log_message="Convergence",
                new_count=0,
            )
            print(f"{PREFIX} Converged: no new findings.")
            break
        elif result.get("no_actionable_fixes", False):
            _register_iteration_findings(progress, result, fixes=[])
            _handle_safe_exit(
                progress,
                progress_path,
                args,
                test_command,
                project_root,
                pre_stash,
                pre_head,
                reason="no-actionable",
                message="Findings exist but none had actionable code edits",
                log_message="No actionable fixes",
                new_count=new_count,
            )
            print(
                f"{PREFIX} No actionable fixes — remaining findings need manual review."
            )
            break

        # Merge new findings into progress
        fixes = result.get("fixes_applied", [])
        _register_iteration_findings(progress, result, fixes)

        # Test and reconcile fixes
        fixed_count, reverted_count, test_passed, all_reverted = (
            _test_and_reconcile_fixes(
                fixes, test_command, project_root, progress, pre_stash, pre_head
            )
        )

        _record_iteration_history(
            progress, iteration, new_count, fixed_count, reverted_count, test_passed
        )

        if all_reverted:
            progress["termination"] = {
                "reason": "all-reverted",
                "message": f"All {reverted_count} fixes in iteration {iteration} caused test failures",
            }
            write_progress(progress_path, progress)
            print(f"{PREFIX} All fixes reverted — stopping.")
            break

        update_scope(progress, result)

        # Checkpoint commit (skip if post-bisection tests failed — interaction bug)
        if (
            not skip_commits
            and test_passed
            and (fixed_count > 0 or git_diff_has_changes(project_root))
        ):
            if git_commit_checkpoint(progress, iteration, project_root):
                print(
                    f"{PREFIX} Checkpoint: deep-harness({args.skill}): iteration {iteration}"
                )
            else:
                print(
                    f"{PREFIX} WARNING: Checkpoint failed — skipping commits for remaining iterations"
                )
                skip_commits = True

        # Check iteration cap
        if iteration >= max_iter:
            progress["termination"] = {
                "reason": "cap",
                "message": f"Reached iteration cap ({max_iter})",
            }
            write_progress(progress_path, progress)
            print(f"{PREFIX} Iteration cap reached ({max_iter}).")
            break

        progress["iteration"]["current"] += 1
        write_progress(progress_path, progress)


def main(argv=None):
    args = _build_argument_parser().parse_args(argv)

    # Clamp iterations
    if args.max_iterations > MAX_ITERATIONS_HARD_CAP:
        print(f"{PREFIX} Iteration cap clamped to {MAX_ITERATIONS_HARD_CAP} (maximum).")
        args.max_iterations = MAX_ITERATIONS_HARD_CAP
    if args.max_iterations < 1:
        print(f"{PREFIX} Iteration cap clamped to 1 (minimum).")
        args.max_iterations = 1

    # Focus modes only apply to refactor
    if args.focus and args.skill != "refactor":
        print(f"{PREFIX} ERROR: --focus is only supported with --skill refactor.")
        return 1

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
        # Sync focus if explicitly provided on resume
        if args.focus:
            progress["config"]["focus"] = args.focus
    else:
        if progress_path.exists():
            print(
                f"{PREFIX} WARNING: Overwriting existing progress file: {progress_path}"
            )
        progress = make_initial_progress(
            args.skill,
            args.scope,
            args.max_iterations,
            test_command,
            project_root,
            focus=args.focus,
        )

    # Validate focus mode (progress file may contain hand-edited values on --resume)
    focus = progress["config"].get("focus", "")
    if focus and focus not in VALID_FOCUS_MODES:
        print(f"{PREFIX} ERROR: Invalid focus mode '{focus}' in progress file.")
        return 1

    # Validate base commit
    if not progress["config"]["base_commit"]:
        print(
            f"{PREFIX} ERROR: Cannot determine HEAD commit. Is this a git repository?"
        )
        return 1

    # Refuse to start with uncommitted changes (fresh runs only)
    if not args.resume and not args.no_commit and git_diff_has_changes(project_root):
        print(f"{PREFIX} ERROR: Uncommitted changes detected.")
        print(f"{PREFIX} The harness creates checkpoint commits per iteration,")
        print(
            f"{PREFIX} which would include your existing changes in the first commit."
        )
        print(f"{PREFIX}")
        print(f'{PREFIX} Commit your changes first:  git add -A && git commit -m "wip"')
        print(f'{PREFIX} Or stash them:              git stash push -m "pre-harness"')
        return 1

    _print_startup_info(args, progress)

    # Main iteration loop
    try:
        _run_iteration_loop(
            args,
            progress,
            progress_path,
            project_root,
            test_command,
            progress["config"]["max_iterations"],
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
