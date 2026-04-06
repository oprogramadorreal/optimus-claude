# Re-export shared fix functions for backward compatibility
from harness_common.fixes import (  # noqa: F401
    _is_path_within,
    _swap_content,
    apply_single_fix,
    revert_single_fix,
)

from .constants import PREFIX
from .findings import mark_finding_status
from .runner import run_tests


def _try_apply_fix(fix, test_command, cwd, progress, pass_detail=None):
    """Apply a single fix, test, revert on failure. Returns 'fixed'|'reverted'|'skipped'."""
    if not apply_single_fix(fix, cwd):
        return "skipped", None
    test_passed, test_summary = run_tests(test_command, cwd)
    if test_passed:
        mark_finding_status(progress, fix, "fixed", pass_detail)
        return "fixed", None
    if not revert_single_fix(fix, cwd):
        print(
            f"{PREFIX} WARNING: Could not revert failing fix for {fix.get('file')} — retaining fix"
        )
        mark_finding_status(
            progress, fix, "fixed", "Revert failed after test failure — fix retained"
        )
        return "fixed", None
    return "reverted", test_summary


def bisect_fixes(fixes, test_command, cwd, progress):
    """
    Incremental bisection: revert all fixes, then re-apply one by one,
    keeping passing fixes applied so subsequent fixes can depend on them.
    After the first pass, retry reverted fixes (they may depend on fixes
    that were applied later in the first pass).
    Returns (fixed_count, reverted_count, skipped_count).
    """
    print(f"{PREFIX} Bisecting {len(fixes)} fixes...")
    # Revert all this iteration's fixes mechanically (preserves prior uncommitted work)
    failed_revert_indices = set()
    for fix_index, fix in reversed(list(enumerate(fixes))):
        if not revert_single_fix(fix, cwd):
            failed_revert_indices.add(fix_index)
            print(
                f"{PREFIX} WARNING: Could not mechanically revert fix for {fix.get('file')}"
            )

    fixed_count = 0
    reverted_count = 0
    skipped_count = 0
    reverted_indices = []
    reverted_summaries = {}  # index -> test failure summary for reverted fixes

    # First pass: apply incrementally, keeping passing fixes
    for i, fix in enumerate(fixes):
        if i in failed_revert_indices:
            mark_finding_status(
                progress,
                fix,
                "retained — revert failed",
                "Could not mechanically revert during bisection — fix retained untested",
            )
            fixed_count += 1  # counts toward applied (fix is in codebase)
            continue
        outcome, fail_summary = _try_apply_fix(fix, test_command, cwd, progress)
        if outcome == "fixed":
            fixed_count += 1
        elif outcome == "skipped":
            # Fix could not be applied (file changed, content not found) — no retry needed
            mark_finding_status(
                progress,
                fix,
                "skipped — apply failed",
                "Could not mechanically apply fix during bisection",
            )
            skipped_count += 1
        else:
            reverted_indices.append(i)
            reverted_summaries[i] = fail_summary

    # Second pass: retry reverted fixes — they may depend on fixes that
    # were applied later in the first pass (e.g., fix A uses an import
    # that fix B added, but B had a higher index)
    if reverted_indices and fixed_count > 0:
        print(f"{PREFIX} Retrying {len(reverted_indices)} reverted fixes...")
        for i in reverted_indices:
            fix = fixes[i]
            outcome, fail_summary = _try_apply_fix(
                fix,
                test_command,
                cwd,
                progress,
                pass_detail="Passed on retry (dependency resolved)",
            )
            if outcome == "fixed":
                fixed_count += 1
            elif outcome == "skipped":
                mark_finding_status(
                    progress,
                    fix,
                    "skipped — apply failed",
                    "Could not mechanically re-apply fix on retry",
                )
                skipped_count += 1
            else:
                # Use the latest failure summary (retry may differ from first attempt)
                summary = fail_summary or reverted_summaries.get(i)
                mark_finding_status(progress, fix, "reverted — test failure", summary)
                reverted_count += 1
    else:
        # No retry needed — mark remaining reverted fixes
        for i in reverted_indices:
            mark_finding_status(
                progress,
                fixes[i],
                "reverted — test failure",
                reverted_summaries.get(i),
            )
            reverted_count += 1

    return fixed_count, reverted_count, skipped_count
