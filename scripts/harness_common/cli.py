"""Orchestrator CLI for the *-deep skills.

Subcommands compose the per-iteration steps the `/optimus:code-review-deep`,
`/optimus:refactor-deep`, and `/optimus:unit-test-deep` skills run via Bash.
The skills hold no state; the CLI reads/writes a JSON progress file on disk.

Subcommand summary:
  init                    — create initial progress file
  resume                  — validate existing progress file for continuation
  snapshot                — capture pre-iteration git state into progress
  parse                   — extract json:harness-output from subagent text
  deep-step               — apply/test/bisect for code-review-deep / refactor-deep
  unit-test-step          — record tests + coverage for unit-test-deep
  refactor-step           — apply/test/bisect for unit-test-deep's refactor phase
  record-cycle            — append cycle_history entry (paired variant)
  commit-checkpoint       — create git checkpoint commit
  check-termination       — print one of continue|convergence|no-actionable|
                            all-reverted|diminishing-returns|cap
  advance                 — increment iteration counter (deep variant)
  pending-refactor-count  — count untestable_code items still pending refactor
  mark-termination        — record an externally-driven termination reason
                            (e.g. parse-failure after two consecutive failures)
  final-report            — print the cumulative report
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

from .constants import (
    APPLIED_PENDING_TEST,
    BACKUP_SUFFIX,
    COVERAGE_VARIANT_SKILLS,
    DEEP_VARIANT_SKILLS,
    DEFAULT_MAX_CYCLES,
    DEFAULT_MAX_ITERATIONS,
    DEFAULT_PROGRESS_FILES,
    FIXED_STATUSES,
    MAX_CYCLES_HARD_CAP,
    MAX_ITERATIONS_HARD_CAP,
    PERSISTENT_STATUS,
    PHASE_COMMIT_TYPE,
    SKILL_COMMIT_TYPE,
    SOFT_EXIT_LOW_YIELD_THRESHOLD,
    SOFT_EXIT_MIN_ITERATION,
    SOFT_EXIT_WINDOW,
    VALID_FOCUS_MODES,
    normalize_path,
)
from .convergence import (
    check_coverage_plateau,
    check_refactor_convergence,
    check_unit_test_convergence,
)
from .findings import (
    finding_key,
    finding_matches,
    mark_all_fixed,
    mark_finding_status,
    update_scope,
)
from .fixes import bisect_fixes
from .git import commit_checkpoint as git_commit_checkpoint
from .git import (
    get_open_pr_data,
    git_diff_has_changes,
    git_discover_branch_files,
    git_fetch_open_pr_description,
    git_rev_parse_head,
    git_stash_snapshot,
    restore_working_tree,
)
from .parser import parse_harness_output
from .progress import read_progress, record_test_result, write_progress
from .reporting import (
    build_coverage_commit_body,
    build_deep_commit_body,
    detect_test_command,
    print_coverage_report,
    print_deep_report,
)
from .runner import run_tests

# ---------------------------------------------------------------------------
# Progress shape helpers
# ---------------------------------------------------------------------------


def _is_coverage(progress):
    return progress.get("harness") == "test-coverage"


def _make_deep_progress(
    skill,
    scope,
    max_iterations,
    test_command,
    project_root,
    focus,
    base_commit,
    scope_is_path,
    no_commit=False,
):
    return {
        "schema_version": 1,
        "skill": skill,
        "config": {
            "max_iterations": max_iterations,
            "test_command": test_command,
            "scope": {
                "mode": "directory" if scope_is_path else "branch-diff",
                "paths": [scope] if scope_is_path else [],
                "scope_text": scope if (scope and not scope_is_path) else None,
                "base_ref": None,
            },
            "project_root": normalize_path(str(project_root)),
            "base_commit": base_commit,
            "focus": focus,
            "no_commit": no_commit,
            "pr_description": None,
        },
        "iteration": {"current": 1, "completed": 0},
        "findings": [],
        "scope_files": {"current": []},
        "test_results": {"last_full_run": None, "last_run_output_summary": None},
        "iteration_history": [],
        "parse_failure_count": 0,
        "commit_disabled": False,
        "termination": {"reason": None, "message": None},
    }


def _make_coverage_progress(
    scope, max_cycles, test_command, project_root, base_commit, no_commit=False
):
    return {
        "schema_version": 1,
        "harness": "test-coverage",
        "skill": "unit-test",
        "config": {
            "max_cycles": max_cycles,
            "test_command": test_command,
            "scope": scope,
            "project_root": normalize_path(str(project_root)),
            "base_commit": base_commit,
            # The refactor phase dispatches /optimus:refactor in harness mode,
            # which resolves its finding-cap focus from config.focus
            # (references/harness-mode.md step 1). The coverage variant always
            # runs its refactor phase for testability, so pin it here — without
            # it the dispatch prompt's "Focus: testability" line is decorative
            # and the phase silently falls back to balanced allocation.
            "focus": "testability",
            "no_commit": no_commit,
        },
        "cycle": {"current": 1, "completed": 0},
        "phase": "unit-test",
        "coverage": {
            "baseline": None,
            "current": None,
            "tool": None,
            "history": [],
        },
        "tests_created": [],
        "untestable_code": [],
        "refactor_findings": [],
        "bugs_discovered": [],
        "cycle_history": [],
        "scope_files": {"current": []},
        "test_results": {"last_full_run": None, "last_run_output_summary": None},
        "parse_failure_count": 0,
        "commit_disabled": False,
        "termination": {"reason": None, "message": None},
    }


# ---------------------------------------------------------------------------
# Iteration helpers (deep variant)
# ---------------------------------------------------------------------------


def _promote_actionable_fixes(result):
    """Promote findings with valid edit pairs into fixes_applied.

    Defensive guard for the false-no-actionable case — see
    `references/harness-mode.md`.
    """
    if not result.get("no_actionable_fixes", False):
        return
    new_findings = result.get("new_findings", [])
    if not new_findings:
        return
    existing_fixes = result.get("fixes_applied", []) or []
    existing_keys = {finding_key(f) for f in existing_fixes}
    promoted = []
    for finding in new_findings:
        pre = finding.get("pre_edit_content")
        post = finding.get("post_edit_content")
        if not pre or not isinstance(post, str) or pre == post:
            continue
        if finding_key(finding) in existing_keys:
            continue
        promoted.append(finding)
    if not promoted:
        return
    result["fixes_applied"] = existing_fixes + promoted
    result["no_actionable_fixes"] = False


def _register_iteration_findings(progress, result, fixes):
    applied_keys = {finding_key(f) for f in fixes}
    for fix in fixes:
        mark_finding_status(progress, fix, APPLIED_PENDING_TEST, None)
    for new_finding in result.get("new_findings", []):
        if finding_key(new_finding) not in applied_keys:
            mark_finding_status(progress, new_finding, "discovered", None)


def _mark_combined_regression(fixes, progress):
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


_BISECT_OUTCOMES_TO_STATUS = {
    "fixed": "fixed",
    "reverted": "reverted — test failure",
    "retained": "retained — revert failed",
    "skipped": "skipped — apply failed",
}


def _make_bisect_callback(progress):
    def _on_outcome(_idx, fix, outcome, detail):
        mark_finding_status(progress, fix, _BISECT_OUTCOMES_TO_STATUS[outcome], detail)

    return _on_outcome


def _format_test_passed(test_passed):
    """Render test_passed for stdout. None → "-" (no fixes applied, no test run)."""
    if test_passed is None:
        return "-"
    return "1" if test_passed else "0"


def _clean_reset_hook(pre_stash, pre_head, project_root):
    """Return a repeatable clean-reset callback for bisect, or None.

    git_restore_to (commit mode, pre_stash is None) is repeatable; a no-commit
    stash restore drops the stash after one use, so it can't back a clean-reset
    bisect — return None there and let bisect use its legacy deletion handling.
    """
    if pre_stash is None and pre_head:
        return lambda: restore_working_tree(pre_stash, pre_head, project_root)
    return None


def _test_and_reconcile_fixes(
    fixes, test_command, project_root, progress, pre_stash, pre_head
):
    if not fixes:
        return 0, 0, None, False
    passed, summary = run_tests(test_command, project_root)
    record_test_result(progress, passed, summary)
    if passed:
        mark_all_fixed(progress, fixes)
        return len(fixes), 0, True, False

    reset_to_clean = _clean_reset_hook(pre_stash, pre_head, project_root)
    fixed, reverted, _ = bisect_fixes(
        fixes,
        test_command,
        project_root,
        on_outcome=_make_bisect_callback(progress),
        reset_to_clean=reset_to_clean,
    )
    if fixed > 0:
        passed, summary = run_tests(test_command, project_root)
        record_test_result(progress, passed, summary)
        if not passed:
            restore_working_tree(pre_stash, pre_head, project_root)
            _mark_combined_regression(fixes, progress)
            # The full restore reverted every fix this iteration applied, so the
            # honest fix-level tally is zero fixed / all reverted. Set it from
            # `fixed` directly rather than decrementing per demoted finding,
            # which could drive the count negative when several findings share
            # one fix key.
            reverted += fixed
            fixed = 0

    all_reverted = fixed == 0 and reverted > 0
    return fixed, reverted, passed, all_reverted


def _make_refactor_bisect_callback(progress, cycle):
    """Parallel of _make_bisect_callback for the unit-test-deep refactor phase.

    Writes to progress["refactor_findings"] scoped by cycle rather than to
    progress["findings"], and skips the escalation chain (refactor findings
    are cycle-local and don't carry status_history).
    """

    def _on_outcome(_idx, fix, outcome, _detail):
        status = _BISECT_OUTCOMES_TO_STATUS[outcome]
        for finding in progress["refactor_findings"]:
            if finding.get("cycle") == cycle and finding_matches(finding, fix):
                finding["status"] = status
                break

    return _on_outcome


def _test_and_reconcile_refactor_fixes(
    fixes, test_command, project_root, progress, cycle, pre_stash, pre_head
):
    """Parallel of _test_and_reconcile_fixes for the refactor phase."""
    if not fixes:
        return 0, 0, None
    passed, summary = run_tests(test_command, project_root)
    record_test_result(progress, passed, summary)
    if passed:
        return len(fixes), 0, True

    reset_to_clean = _clean_reset_hook(pre_stash, pre_head, project_root)
    fixed, reverted, _ = bisect_fixes(
        fixes,
        test_command,
        project_root,
        on_outcome=_make_refactor_bisect_callback(progress, cycle),
        reset_to_clean=reset_to_clean,
    )
    if fixed > 0:
        passed, summary = run_tests(test_command, project_root)
        record_test_result(progress, passed, summary)
        if not passed:
            restore_working_tree(pre_stash, pre_head, project_root)
            for finding in progress["refactor_findings"]:
                if (
                    finding.get("cycle") == cycle
                    and finding.get("status") in FIXED_STATUSES
                ):
                    finding["status"] = "reverted — test failure"
            # The full restore reverted every fix this phase applied, so report
            # zero fixed / all reverted. Recompute from `fixed` rather than
            # decrementing per finding, which could go negative when several
            # findings share one fix key.
            reverted += fixed
            fixed = 0
    return fixed, reverted, passed


def _record_iteration_history(
    progress, iteration, new_count, fixed, reverted, test_passed
):
    persistent = sum(
        1
        for f in progress["findings"]
        if f["status"] == PERSISTENT_STATUS
        and f.get("iteration_last_attempted") == iteration
    )
    progress["iteration_history"].append(
        {
            "iteration": iteration,
            "new_findings": new_count,
            "fixed": fixed,
            "reverted": reverted,
            "persistent": persistent,
            "test_passed": test_passed,
        }
    )
    progress["iteration"]["completed"] = iteration


def _should_soft_exit(progress, iteration):
    if iteration < SOFT_EXIT_MIN_ITERATION:
        return False
    history = progress.get("iteration_history", [])
    if len(history) < SOFT_EXIT_WINDOW:
        return False
    for entry in history[-SOFT_EXIT_WINDOW:]:
        if entry.get("new_findings", 0) > SOFT_EXIT_LOW_YIELD_THRESHOLD:
            return False
        if entry.get("reverted", 0) > 0:
            return False
    return True


# ---------------------------------------------------------------------------
# Subcommand implementations
# ---------------------------------------------------------------------------


def _progress_path_for_skill(args):
    if args.progress_file:
        return Path(args.progress_file)
    default = DEFAULT_PROGRESS_FILES.get(args.skill)
    if not default:
        raise SystemExit(f"Unknown skill '{args.skill}' (no default progress path)")
    return Path(default)


def _init_coverage(args, project_root, test_command, base_commit):
    """Build the initial progress dict for unit-test-deep (paired variant)."""
    requested_cycles = (
        args.max_cycles if args.max_cycles is not None else DEFAULT_MAX_CYCLES
    )
    max_cycles = max(min(requested_cycles, MAX_CYCLES_HARD_CAP), 1)
    return (
        _make_coverage_progress(
            args.scope,
            max_cycles,
            test_command,
            project_root,
            base_commit,
            args.no_commit,
        ),
        0,
    )


def _init_deep(args, project_root, test_command, base_commit):
    """Build the initial progress dict for code-review-deep / refactor-deep."""
    skill = args.skill
    if args.focus and args.focus not in VALID_FOCUS_MODES:
        print(
            f"ERROR: --focus must be one of {sorted(VALID_FOCUS_MODES)}",
            file=sys.stderr,
        )
        return None, 1
    if args.focus and skill != "refactor":
        print(
            "ERROR: --focus is only supported with --skill refactor",
            file=sys.stderr,
        )
        return None, 1
    requested_iter = (
        args.max_iterations
        if args.max_iterations is not None
        else DEFAULT_MAX_ITERATIONS
    )
    max_iter = max(min(requested_iter, MAX_ITERATIONS_HARD_CAP), 1)
    # Treat scope as a git pathspec only when it resolves to an existing path
    # under project_root. Natural-language scope ("focus on src/auth") cannot be
    # turned into a reliable pathspec, so it is recorded in config.scope.scope_text
    # for provenance only: the harness-mode dispatch does not consume it and the
    # subagent reviews the full branch diff (see the scope note in each -deep
    # SKILL.md / README). The containment check also rejects absolute paths (Path
    # semantics: `project_root / "/etc"` yields `/etc`), which would otherwise be
    # silently handed to git as a pathspec that matches nothing.
    if args.scope:
        candidate = (project_root / args.scope).resolve()
        scope_is_path = candidate.exists() and (
            candidate == project_root or project_root in candidate.parents
        )
    else:
        scope_is_path = False
    progress = _make_deep_progress(
        skill,
        args.scope,
        max_iter,
        test_command,
        project_root,
        args.focus,
        base_commit,
        scope_is_path,
        args.no_commit,
    )
    path_filter = args.scope if scope_is_path else None
    # Fetch the open-PR metadata once and thread it into both base-branch
    # detection and the description builder, instead of each re-shelling out
    # to `gh pr view`.
    pr_data = get_open_pr_data(project_root)
    branch_files, base_ref = git_discover_branch_files(
        project_root, path_filter=path_filter, pr_info=pr_data
    )
    if branch_files:
        progress["scope_files"]["current"] = branch_files
        progress["config"]["scope"]["base_ref"] = base_ref
    pr_info = git_fetch_open_pr_description(project_root, pr_info=pr_data)
    if pr_info:
        progress["config"]["pr_description"] = pr_info
    return progress, 0


def cmd_init(args):
    skill = args.skill
    project_root = Path(args.project_dir).resolve()
    progress_path = _progress_path_for_skill(args)

    if progress_path.exists() and not args.force:
        print(
            f"ERROR: progress file already exists at {progress_path}. "
            "Pass --resume to continue the prior run, or --force to overwrite "
            "(this discards the prior findings).",
            file=sys.stderr,
        )
        return 1

    test_command = args.test_command or detect_test_command(project_root)
    if not test_command:
        print(
            f"ERROR: No test command found in {project_root}/.claude/CLAUDE.md "
            "and --test-command not supplied",
            file=sys.stderr,
        )
        return 1

    base_commit = git_rev_parse_head(project_root)
    if not base_commit:
        print(f"ERROR: Cannot determine HEAD commit in {project_root}", file=sys.stderr)
        return 1

    # A fresh run's checkpoint commits must stay isolated from the user's own
    # work, so refuse to start on a dirty tree. --no-commit runs take a
    # non-destructive stash instead, so they are allowed. The orchestrator
    # SKILL.md enforces the same check, but pinning it here also protects a
    # direct CLI caller or a garbled skill step.
    if not args.no_commit and git_diff_has_changes(project_root):
        print(
            "ERROR: Working tree has uncommitted changes. Commit or stash them "
            "before a fresh deep run, or pass --no-commit to run without "
            "checkpoint commits.",
            file=sys.stderr,
        )
        return 1

    if skill in COVERAGE_VARIANT_SKILLS:
        progress, exit_code = _init_coverage(
            args, project_root, test_command, base_commit
        )
    elif skill in DEEP_VARIANT_SKILLS:
        progress, exit_code = _init_deep(args, project_root, test_command, base_commit)
    else:
        print(f"ERROR: Unknown skill '{skill}'", file=sys.stderr)
        return 1
    if exit_code != 0:
        return exit_code

    write_progress(progress_path, progress)
    print(str(progress_path))
    return 0


def cmd_resume(args):
    progress_path = Path(args.progress_file)
    if not progress_path.exists():
        backup = Path(str(progress_path) + BACKUP_SUFFIX)
        if backup.exists():
            shutil.copy2(str(backup), str(progress_path))
        else:
            print(f"ERROR: No progress file at {progress_path}", file=sys.stderr)
            return 1
    try:
        progress = read_progress(progress_path)
    except (ValueError, OSError) as exc:
        print(f"ERROR: Cannot read progress file: {exc}", file=sys.stderr)
        return 1
    for key in ("skill", "config"):
        if key not in progress:
            print(
                f"ERROR: Progress file missing required field '{key}'", file=sys.stderr
            )
            return 1
    if args.project_dir:
        expected = Path(args.project_dir).resolve()
        saved = progress["config"].get("project_root")
        if saved and Path(saved).resolve() != expected:
            print(
                f"ERROR: project_root mismatch (saved: {saved}, requested: {expected})",
                file=sys.stderr,
            )
            return 1

    # Resuming means "continue the loop". Clear any stored terminal reason so
    # `check-termination` re-evaluates from scratch instead of immediately
    # re-emitting the soft-exit (diminishing-returns) that left this file
    # resumable — without this, every --resume quits after a single iteration.
    config = progress.get("config", {})
    mutated = False
    if (progress.get("termination") or {}).get("reason"):
        progress["termination"] = {"reason": None, "message": None}
        mutated = True
    # Let --resume raise the persisted cap (the documented
    # "--resume --max-iterations <new-cap>" continuation path).
    if args.max_iterations is not None and "max_iterations" in config:
        new_cap = max(min(args.max_iterations, MAX_ITERATIONS_HARD_CAP), 1)
        if new_cap != config["max_iterations"]:
            config["max_iterations"] = new_cap
            mutated = True
    if args.max_cycles is not None and "max_cycles" in config:
        new_cap = max(min(args.max_cycles, MAX_CYCLES_HARD_CAP), 1)
        if new_cap != config["max_cycles"]:
            config["max_cycles"] = new_cap
            mutated = True
    if mutated:
        write_progress(progress_path, progress)

    print(progress["skill"])
    return 0


def cmd_snapshot(args):
    progress_path = Path(args.progress_file)
    progress = read_progress(progress_path)
    project_root = Path(progress["config"]["project_root"])
    head = git_rev_parse_head(project_root)
    if not head:
        print("ERROR: Cannot determine HEAD commit", file=sys.stderr)
        return 1
    progress.setdefault("_snapshot", {})
    progress["_snapshot"]["pre_head"] = head
    progress["_snapshot"]["iteration_token"] = _current_unit(progress)
    if args.include_stash or _is_no_commit(progress):
        progress["_snapshot"]["pre_stash"] = git_stash_snapshot(project_root)
    write_progress(progress_path, progress)
    print(head)
    return 0


def cmd_parse(args):
    parsed = None
    error_message = None
    try:
        raw = Path(args.input_file).read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        error_message = f"ERROR: Cannot read {args.input_file}: {exc}"
    else:
        parsed = parse_harness_output(raw)
        if parsed is None:
            error_message = (
                "ERROR: No json:harness-output block found in subagent output"
            )

    if args.progress_file:
        # When the orchestrator passes --progress-file, parse failures are
        # counted in the progress file so the cross-iteration "two consecutive
        # failures → terminate" check survives Ctrl-C + --resume. On success,
        # the counter resets so an isolated earlier failure doesn't poison
        # later runs.
        progress_path = Path(args.progress_file)
        if progress_path.exists():
            try:
                progress = read_progress(progress_path)
            except (ValueError, OSError):
                progress = None
            if progress is not None:
                if parsed is None:
                    progress["parse_failure_count"] = (
                        progress.get("parse_failure_count", 0) + 1
                    )
                    # The subagent emitted no parseable output, so any partial
                    # edits it left are untrusted. Roll the working tree back to
                    # this iteration's snapshot so the failed dispatch is a true
                    # no-op and a later checkpoint can't sweep half-done work into
                    # a commit. Gated on snapshot freshness so a missing/stale
                    # snapshot never restores to the wrong state.
                    snap = progress.get("_snapshot") or {}
                    token = snap.get("iteration_token")
                    if token is not None and token == _current_unit(progress):
                        try:
                            restore_working_tree(
                                snap.get("pre_stash"),
                                snap.get("pre_head"),
                                Path(progress["config"]["project_root"]),
                            )
                        except (RuntimeError, OSError):
                            # Best-effort rollback — the failure count is still
                            # recorded so the loop can terminate on repeat.
                            pass
                else:
                    progress["parse_failure_count"] = 0
                write_progress(progress_path, progress)

    if parsed is None:
        print(error_message, file=sys.stderr)
        return 1
    if args.output_file:
        try:
            Path(args.output_file).write_text(
                json.dumps(parsed, indent=2), encoding="utf-8"
            )
        except OSError as exc:
            print(f"ERROR: Cannot write {args.output_file}: {exc}", file=sys.stderr)
            return 1
    print(json.dumps(parsed))
    return 0


def _load_result(result_file):
    return json.loads(Path(result_file).read_text(encoding="utf-8"))


def _snapshot_from_progress(progress):
    snap = progress.get("_snapshot") or {}
    return snap.get("pre_stash"), snap.get("pre_head")


def _is_no_commit(progress):
    """True when checkpoint commits are disabled for this run.

    Either the user chose --no-commit at init (``config.no_commit``) or a commit
    failed mid-run and commits were durably disabled (``commit_disabled``). In
    both cases ``snapshot`` captures a stash and ``commit-checkpoint`` self-skips,
    so the safety net does not depend on the orchestrator re-passing a flag.
    """
    return bool(progress["config"].get("no_commit") or progress.get("commit_disabled"))


def _current_unit(progress):
    """The current iteration (deep) or cycle (coverage) — the snapshot token."""
    if _is_coverage(progress):
        return progress["cycle"]["current"]
    return progress["iteration"]["current"]


def _verify_snapshot_fresh(progress, current):
    """Guard against a skipped ``snapshot`` step.

    ``snapshot`` stamps the current iteration/cycle into
    ``_snapshot.iteration_token``. A step running against a token from a prior
    unit means ``snapshot`` was skipped this iteration, so ``pre_head`` /
    ``pre_stash`` are stale — restoring on a test failure would revert to the
    wrong commit. Fail loudly instead.
    """
    token = (progress.get("_snapshot") or {}).get("iteration_token")
    if token is not None and token != current:
        print(
            f"ERROR: snapshot is stale (taken at unit {token}, current is "
            f"{current}). Run `snapshot` before this step.",
            file=sys.stderr,
        )
        return False
    return True


def cmd_deep_step(args):
    """Process a code-review-deep / refactor-deep subagent iteration result.

    Inputs: progress file path, result file path (subagent JSON).
    Output (stdout): one of
        converged | no-actionable | all-reverted | applied
    Side effects: working tree may have fixes reverted via bisection; progress
    file is updated with statuses, iteration history, and (potentially) a
    termination reason.
    """
    progress_path = Path(args.progress_file)
    progress = read_progress(progress_path)
    result = _load_result(args.result_file)

    test_command = progress["config"]["test_command"]
    project_root = Path(progress["config"]["project_root"])
    iteration = progress["iteration"]["current"]
    if not _verify_snapshot_fresh(progress, iteration):
        return 1
    pre_stash, pre_head = _snapshot_from_progress(progress)

    _promote_actionable_fixes(result)
    new_count = len(result.get("new_findings", []))

    if result.get("no_new_findings", False):
        _register_iteration_findings(progress, result, fixes=[])
        _record_iteration_history(progress, iteration, 0, 0, 0, None)
        progress["termination"] = {
            "reason": "convergence",
            "message": f"Zero new findings on iteration {iteration}",
        }
        write_progress(progress_path, progress)
        print("converged")
        return 0
    if result.get("no_actionable_fixes", False):
        _register_iteration_findings(progress, result, fixes=[])
        _record_iteration_history(progress, iteration, new_count, 0, 0, None)
        progress["termination"] = {
            "reason": "no-actionable",
            "message": "Findings exist but none had actionable code edits",
        }
        write_progress(progress_path, progress)
        print("no-actionable")
        return 0

    fixes = result.get("fixes_applied", [])
    _register_iteration_findings(progress, result, fixes)
    fixed, reverted, test_passed, all_reverted = _test_and_reconcile_fixes(
        fixes,
        test_command,
        project_root,
        progress,
        pre_stash,
        pre_head,
    )
    _record_iteration_history(
        progress, iteration, new_count, fixed, reverted, test_passed
    )
    update_scope(progress, result)
    if all_reverted:
        progress["termination"] = {
            "reason": "all-reverted",
            "message": f"All {reverted} fixes in iteration {iteration} caused test failures",
        }
        write_progress(progress_path, progress)
        print("all-reverted")
        return 0
    write_progress(progress_path, progress)
    print(
        f"applied fixed={fixed} reverted={reverted} "
        f"test_passed={_format_test_passed(test_passed)}"
    )
    return 0


def cmd_unit_test_step(args):
    """Process the unit-test phase of a unit-test-deep cycle.

    Inputs: progress file path, result file path (unit-test phase JSON).
    Output: one of converged | continue
    """
    progress_path = Path(args.progress_file)
    progress = read_progress(progress_path)
    result = _load_result(args.result_file)
    project_root = Path(progress["config"]["project_root"])
    test_command = progress["config"]["test_command"]
    cycle = progress["cycle"]["current"]
    if not _verify_snapshot_fresh(progress, cycle):
        return 1

    # Update coverage history
    cov = result.get("coverage") or {}
    if cov.get("tool"):
        progress["coverage"]["tool"] = cov["tool"]
    before = cov.get("before")
    after = cov.get("after")
    delta = cov.get("delta")
    if progress["coverage"]["baseline"] is None and before is not None:
        progress["coverage"]["baseline"] = before
    if after is not None:
        progress["coverage"]["current"] = after
    progress["coverage"]["history"].append(
        {
            "cycle": cycle,
            "before": before,
            "after": after,
            "delta": delta,
        }
    )

    # Merge tests
    for t in result.get("tests_written", []):
        progress["tests_created"].append({**t, "cycle": cycle})
    # Merge untestable items (dedup by file+line+function). Normalize the file
    # path on storage so the dedup key here and the refactor phase's touched-file
    # match are separator-agnostic — the unit-test and refactor subagents can
    # cite the same file with different separators on Windows.
    existing_keys = {
        (u.get("file"), u.get("line"), u.get("function"))
        for u in progress["untestable_code"]
    }
    for item in result.get("untestable_code", []):
        item_file = (
            normalize_path(item["file"]) if item.get("file") else item.get("file")
        )
        key = (item_file, item.get("line"), item.get("function"))
        if key in existing_keys:
            continue
        existing_keys.add(key)
        progress["untestable_code"].append(
            {
                **item,
                "file": item_file,
                "status": "pending",
                "cycle_reported": cycle,
                "refactor_attempt_cycle": None,
            }
        )
    # Bugs
    for b in result.get("bugs_discovered", []):
        progress["bugs_discovered"].append({**b, "cycle_discovered": cycle})

    # Run the full test suite to record pass/fail
    passed, summary = run_tests(test_command, project_root)
    record_test_result(progress, passed, summary)

    # Refresh refactor-phase scope from pending untestable items so the refactor
    # subagent's harness-mode protocol sees the items via scope_files.current
    # (per references/coverage-harness-mode.md "Refactor Phase Execution").
    pending_files = sorted(
        {
            normalize_path(item["file"])
            for item in progress["untestable_code"]
            if item.get("status") == "pending" and item.get("file")
        }
    )
    progress.setdefault("scope_files", {"current": []})
    progress["scope_files"]["current"] = pending_files

    progress["phase"] = "unit-test"

    converged, reason = check_unit_test_convergence(result)
    if converged:
        # Record the cycle that just ran before terminating — the orchestrator
        # loop skips step 10 (record-cycle) on the converged path, so the
        # final report would otherwise miss this cycle in cycle_history.
        progress["cycle_history"].append(
            {"cycle": cycle, "unit_test": {"converged": True}}
        )
        progress["cycle"]["completed"] = cycle
        progress["termination"] = {"reason": "convergence", "message": reason}
        write_progress(progress_path, progress)
        print("converged")
        return 0
    write_progress(progress_path, progress)
    print("continue")
    return 0


def cmd_refactor_step(args):
    """Process the refactor (testability) phase of a unit-test-deep cycle.

    Inputs: progress file path, result file path (refactor phase JSON).
    Output: one of converged | applied
    """
    progress_path = Path(args.progress_file)
    progress = read_progress(progress_path)
    result = _load_result(args.result_file)
    test_command = progress["config"]["test_command"]
    project_root = Path(progress["config"]["project_root"])
    cycle = progress["cycle"]["current"]
    if not _verify_snapshot_fresh(progress, cycle):
        return 1
    pre_stash, pre_head = _snapshot_from_progress(progress)

    _promote_actionable_fixes(result)

    # Merge new findings (refactor_findings is the coverage-variant store)
    fixes = result.get("fixes_applied", [])
    applied_keys = {finding_key(f) for f in fixes}
    new_findings = result.get("new_findings", [])
    represented = set()
    for finding in new_findings:
        status = (
            "fixed" if finding_key(finding) in applied_keys else "skipped — not applied"
        )
        progress["refactor_findings"].append(
            {
                **finding,
                "cycle": cycle,
                "status": status,
            }
        )
        represented.add(finding_key(finding))
    # Register any applied fix the subagent didn't echo in new_findings so every
    # fix has a key-matched refactor_finding — mirrors deep-step's
    # _register_iteration_findings. Without it, such a fix is invisible to the
    # bisect callback and the touched-file match below, stranding its
    # untestable item as permanently "pending".
    for fix in fixes:
        if finding_key(fix) not in represented:
            progress["refactor_findings"].append(
                {**fix, "cycle": cycle, "status": "fixed"}
            )
            represented.add(finding_key(fix))

    fixed_count, reverted_count, test_passed = _test_and_reconcile_refactor_fixes(
        fixes, test_command, project_root, progress, cycle, pre_stash, pre_head
    )

    # Mark only the untestable items whose file was actually touched by a
    # surviving fix as "attempted" — unrelated pending items stay pending so
    # the next cycle can retry them.
    if fixed_count > 0:
        touched_files = {
            normalize_path(f["file"])
            for f in fixes
            if f.get("file")
            and any(
                finding.get("cycle") == cycle
                and finding_matches(finding, f)
                and finding.get("status") in FIXED_STATUSES
                for finding in progress["refactor_findings"]
            )
        }
        for item in progress["untestable_code"]:
            item_file = item.get("file")
            if (
                item.get("status") == "pending"
                and item_file
                and normalize_path(item_file) in touched_files
            ):
                item["status"] = "attempted"
                item["refactor_attempt_cycle"] = cycle

    progress["phase"] = "refactor"

    converged, reason = check_refactor_convergence(result)
    # Coverage plateau check happens at cycle boundary via check-termination.
    output_line = (
        f"applied fixed={fixed_count} reverted={reverted_count} "
        f"test_passed={_format_test_passed(test_passed)}"
    )

    if converged:
        # Record the cycle that just ran before terminating — the orchestrator
        # loop skips step 10 (record-cycle) on the converged path.
        progress["cycle_history"].append(
            {
                "cycle": cycle,
                "refactor": {
                    "converged": True,
                    "fixed": fixed_count,
                    "reverted": reverted_count,
                },
            }
        )
        progress["cycle"]["completed"] = cycle
        progress["termination"] = {"reason": "convergence", "message": reason}
        write_progress(progress_path, progress)
        print("converged")
        return 0
    write_progress(progress_path, progress)
    print(output_line)
    return 0


def cmd_record_cycle(args):
    """Append a cycle history entry and increment the cycle counter."""
    progress_path = Path(args.progress_file)
    progress = read_progress(progress_path)
    cycle = progress["cycle"]["current"]
    try:
        ut_summary = (
            json.loads(args.unit_test_summary) if args.unit_test_summary else {}
        )
        rf_summary = (
            json.loads(args.refactor_summary) if args.refactor_summary else None
        )
    except ValueError as exc:
        print(f"ERROR: Invalid cycle summary JSON: {exc}", file=sys.stderr)
        return 1
    entry = {"cycle": cycle, "unit_test": ut_summary}
    if rf_summary is not None:
        entry["refactor"] = rf_summary
    progress["cycle_history"].append(entry)
    progress["cycle"]["completed"] = cycle
    progress["cycle"]["current"] = cycle + 1
    write_progress(progress_path, progress)
    return 0


def cmd_commit_checkpoint(args):
    progress_path = Path(args.progress_file)
    progress = read_progress(progress_path)
    project_root = Path(progress["config"]["project_root"])

    if _is_no_commit(progress):
        print("commit-skipped")
        return 0

    if _is_coverage(progress):
        cycle = progress["cycle"]["current"]
        phase = args.phase or progress.get("phase", "unit-test")
        if phase == "unit-test":
            count = sum(
                1 for t in progress.get("tests_created", []) if t.get("cycle") == cycle
            )
            detail = f"{count} tests written"
        else:
            count = sum(
                1
                for f in progress.get("refactor_findings", [])
                if f.get("cycle") == cycle and f.get("status") in FIXED_STATUSES
            )
            detail = f"{count} fixed"
        commit_type = PHASE_COMMIT_TYPE.get(phase, "chore")
        title = f"{commit_type}(coverage-orchestrator): cycle {cycle} — {detail}"
        body = build_coverage_commit_body(progress, cycle, phase)
    else:
        skill = progress["skill"]
        iteration = progress["iteration"]["current"]
        history = progress["iteration_history"]
        latest = history[-1] if history else {}
        fixed = latest.get("fixed", 0)
        commit_type = SKILL_COMMIT_TYPE.get(skill, "chore")
        title = (
            f"{commit_type}(deep-orchestrator): iteration {iteration} — {fixed} fixed"
        )
        body = build_deep_commit_body(progress, iteration)

    commit_message = f"{title}\n\n{body}" if body else title

    if not git_diff_has_changes(project_root):
        print("nothing-to-commit")
        return 0
    ok = git_commit_checkpoint(
        commit_message,
        project_root,
        str(progress_path),
    )
    if ok:
        print("committed")
        return 0
    # Durably disable commits so the rest of the run (and any --resume) auto-
    # stashes in snapshot and self-skips commit-checkpoint — preserving the
    # accumulated uncommitted work rather than relying on the orchestrator to
    # switch modes by hand.
    progress["commit_disabled"] = True
    write_progress(progress_path, progress)
    print("commit-failed")
    return 1


PARSE_FAILURE_THRESHOLD = 2


def cmd_check_termination(args):
    progress_path = Path(args.progress_file)
    progress = read_progress(progress_path)
    termination = progress.get("termination") or {}
    reason = termination.get("reason")
    if reason:
        print(reason)
        return 0

    # Two consecutive subagent dispatches that emitted no parseable
    # json:harness-output block — terminate. The counter is incremented by
    # `cmd_parse --progress-file` and reset on every successful parse.
    if progress.get("parse_failure_count", 0) >= PARSE_FAILURE_THRESHOLD:
        progress["termination"] = {
            "reason": "parse-failure",
            "message": (
                f"{PARSE_FAILURE_THRESHOLD} consecutive iterations produced no "
                "json:harness-output block"
            ),
        }
        write_progress(progress_path, progress)
        print("parse-failure")
        return 0

    if _is_coverage(progress):
        # cmd_record_cycle pre-increments cycle.current to N+1 before this runs
        # (per references/orchestrator-loop-paired.md steps 10 → 11), so we cap
        # on `current > max_cycles` to allow exactly max_cycles complete cycles.
        cycle = progress["cycle"]["current"]
        max_cycles = progress["config"]["max_cycles"]
        if cycle > max_cycles:
            progress["termination"] = {
                "reason": "cap",
                "message": f"Reached cycle cap ({max_cycles})",
            }
            write_progress(progress_path, progress)
            print("cap")
            return 0
        plateaued, plateau_reason = check_coverage_plateau(
            progress["coverage"]["history"],
        )
        if plateaued:
            progress["termination"] = {
                "reason": "diminishing-returns",
                "message": plateau_reason,
            }
            write_progress(progress_path, progress)
            print("diminishing-returns")
            return 0
        print("continue")
        return 0

    iteration = progress["iteration"]["current"]
    max_iter = progress["config"]["max_iterations"]
    if iteration >= max_iter:
        progress["termination"] = {
            "reason": "cap",
            "message": f"Reached iteration cap ({max_iter})",
        }
        write_progress(progress_path, progress)
        print("cap")
        return 0
    if _should_soft_exit(progress, iteration):
        progress["termination"] = {
            "reason": "diminishing-returns",
            "message": (
                f"Yield plateaued at ≤{SOFT_EXIT_LOW_YIELD_THRESHOLD}/iter for "
                f"{SOFT_EXIT_WINDOW} iterations ending at iter {iteration}. "
                "Re-run with --resume to continue."
            ),
        }
        write_progress(progress_path, progress)
        print("diminishing-returns")
        return 0
    print("continue")
    return 0


def cmd_advance(args):
    """Increment iteration.current after a successful iteration (deep variant).

    The paired-cycle loop uses ``record-cycle`` to increment ``cycle.current``;
    only deep-variant skills call ``advance``.
    """
    progress_path = Path(args.progress_file)
    progress = read_progress(progress_path)
    progress["iteration"]["current"] += 1
    write_progress(progress_path, progress)
    return 0


def cmd_pending_refactor_count(args):
    """Print the count of pending untestable items (drives refactor-phase dispatch)."""
    progress_path = Path(args.progress_file)
    progress = read_progress(progress_path)
    pending = sum(
        1
        for item in progress.get("untestable_code", [])
        if item.get("status") == "pending"
    )
    print(pending)
    return 0


def cmd_mark_termination(args):
    """Write a terminal reason to progress["termination"] without other side effects.

    The orchestrator skill calls this when it must end the loop for a reason
    the per-iteration steps don't naturally surface — currently the
    parse-failure recovery path (per references/orchestrator-loop-single.md).
    Keeps the orchestrator out of the progress file's internals so the
    "slice-only progress reads" invariant holds.
    """
    progress_path = Path(args.progress_file)
    progress = read_progress(progress_path)
    progress["termination"] = {
        "reason": args.reason,
        "message": args.message,
    }
    write_progress(progress_path, progress)
    return 0


def cmd_final_report(args):
    progress_path = Path(args.progress_file)
    progress = read_progress(progress_path)
    if _is_coverage(progress):
        print_coverage_report(progress)
    else:
        print_deep_report(progress)
    if args.archive:
        # diminishing-returns is a soft, resumable exit — the termination message
        # tells the user to --resume. Archiving renames the progress file to
        # .done.json, which cmd_resume then refuses, breaking the advertised
        # --resume. Leave the active progress file in place so the run continues.
        reason = (progress.get("termination") or {}).get("reason")
        if reason == "diminishing-returns":
            print(
                "not-archived: run left resumable (diminishing-returns). Re-run "
                "with --resume to continue, or delete the progress file to discard."
            )
            return 0
        done_path = progress_path.with_suffix(".done.json")
        # os.replace is atomic on the same filesystem (progress and archive
        # both live in .claude/), so a crash mid-archive leaves either the
        # original progress file or the renamed .done.json — never both gone.
        try:
            os.replace(str(progress_path), str(done_path))
        except OSError as exc:
            print(f"ERROR: archive failed: {exc}", file=sys.stderr)
            return 1
        backup = Path(str(progress_path) + BACKUP_SUFFIX)
        try:
            backup.unlink()
        except FileNotFoundError:
            pass
    return 0


# ---------------------------------------------------------------------------
# Argparse + dispatch
# ---------------------------------------------------------------------------


def _build_parser():
    parser = argparse.ArgumentParser(
        prog="harness_common.cli",
        description="Orchestrator CLI invoked by *-deep skills",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init")
    p.add_argument("--skill", required=True)
    p.add_argument("--max-iterations", type=int, default=None)
    p.add_argument("--max-cycles", type=int, default=None)
    p.add_argument("--scope", default="")
    p.add_argument("--focus", default="")
    p.add_argument("--progress-file", default=None)
    p.add_argument("--test-command", default=None)
    p.add_argument("--project-dir", default=".")
    p.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing progress file (discards prior findings)",
    )
    p.add_argument(
        "--no-commit",
        action="store_true",
        help="Run without per-iteration checkpoint commits; snapshot auto-stashes "
        "so a failed iteration is still restorable. Persisted, so --resume keeps "
        "the mode without re-passing the flag.",
    )
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("resume")
    p.add_argument("--progress-file", required=True)
    p.add_argument("--project-dir", default=None)
    p.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Raise the persisted iteration cap when continuing a deep run",
    )
    p.add_argument(
        "--max-cycles",
        type=int,
        default=None,
        help="Raise the persisted cycle cap when continuing a coverage run",
    )
    p.set_defaults(func=cmd_resume)

    p = sub.add_parser("snapshot")
    p.add_argument("--progress-file", required=True)
    p.add_argument(
        "--include-stash",
        action="store_true",
        help="Also create a git stash snapshot (use with --no-commit mode)",
    )
    p.set_defaults(func=cmd_snapshot)

    p = sub.add_parser("parse")
    p.add_argument(
        "--input-file",
        required=True,
        help="Path to a file holding the subagent's raw text output",
    )
    p.add_argument(
        "--output-file",
        default=None,
        help="If supplied, also write canonical JSON to this path",
    )
    p.add_argument(
        "--progress-file",
        default=None,
        help=(
            "If supplied, increment parse_failure_count on failure / reset on "
            "success. Lets `check-termination` surface `parse-failure` after "
            "two consecutive failed parses, surviving --resume."
        ),
    )
    p.set_defaults(func=cmd_parse)

    p = sub.add_parser("deep-step")
    p.add_argument("--progress-file", required=True)
    p.add_argument("--result-file", required=True)
    p.set_defaults(func=cmd_deep_step)

    p = sub.add_parser("unit-test-step")
    p.add_argument("--progress-file", required=True)
    p.add_argument("--result-file", required=True)
    p.set_defaults(func=cmd_unit_test_step)

    p = sub.add_parser("refactor-step")
    p.add_argument("--progress-file", required=True)
    p.add_argument("--result-file", required=True)
    p.set_defaults(func=cmd_refactor_step)

    p = sub.add_parser("record-cycle")
    p.add_argument("--progress-file", required=True)
    p.add_argument(
        "--unit-test-summary",
        default="",
        help="JSON-encoded unit-test summary for cycle_history",
    )
    p.add_argument(
        "--refactor-summary",
        default="",
        help="JSON-encoded refactor summary for cycle_history (optional)",
    )
    p.set_defaults(func=cmd_record_cycle)

    p = sub.add_parser("commit-checkpoint")
    p.add_argument("--progress-file", required=True)
    p.add_argument(
        "--phase",
        default=None,
        choices=["unit-test", "refactor"],
        help="Coverage variant only — which phase to record",
    )
    p.set_defaults(func=cmd_commit_checkpoint)

    p = sub.add_parser("check-termination")
    p.add_argument("--progress-file", required=True)
    p.set_defaults(func=cmd_check_termination)

    p = sub.add_parser("advance")
    p.add_argument("--progress-file", required=True)
    p.set_defaults(func=cmd_advance)

    p = sub.add_parser("pending-refactor-count")
    p.add_argument("--progress-file", required=True)
    p.set_defaults(func=cmd_pending_refactor_count)

    p = sub.add_parser("mark-termination")
    p.add_argument("--progress-file", required=True)
    p.add_argument(
        "--reason",
        required=True,
        choices=[
            "convergence",
            "no-actionable",
            "all-reverted",
            "diminishing-returns",
            "cap",
            "parse-failure",
        ],
        help="Termination reason to record in progress[termination]",
    )
    p.add_argument(
        "--message",
        default="",
        help="Human-readable detail recorded alongside the reason",
    )
    p.set_defaults(func=cmd_mark_termination)

    p = sub.add_parser("final-report")
    p.add_argument("--progress-file", required=True)
    p.add_argument(
        "--archive",
        action="store_true",
        help="Move progress file to .done.json after printing",
    )
    p.set_defaults(func=cmd_final_report)

    return parser


def main(argv=None):
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
