from pathlib import Path

from .constants import PREFIX
from .findings import mark_finding_status
from .runner import run_tests


def _is_path_within(filepath, root):
    """Check if filepath is within root (Python 3.8 compatible)."""
    try:
        filepath.relative_to(root)
        return True
    except ValueError:
        return False


def _swap_content(fix, cwd, find_key, replace_key):
    """Swap one content string for another in a file."""
    # Normalize path separators for cross-platform compatibility
    fix_file = fix["file"].replace("\\", "/")
    filepath = (Path(cwd) / fix_file).resolve()
    if not _is_path_within(filepath, Path(cwd).resolve()):
        return False
    # Block writes to sensitive paths
    try:
        rel = filepath.relative_to(Path(cwd).resolve())
        if any(part == ".git" for part in rel.parts):
            return False
    except ValueError:
        return False
    if not filepath.exists():
        return False
    content = filepath.read_text(encoding="utf-8")
    find = fix.get(find_key, "")
    replace = fix.get(replace_key, "")
    if not find:
        # Empty find string — cannot locate target in file content.
        # This happens when reverting a deletion fix (empty post_edit_content):
        # the revert needs to re-insert pre_edit_content but has no position info.
        return False
    if find not in content:
        return False
    if content.count(find) != 1:
        return False  # Ambiguous match — refuse to apply/revert
    filepath.write_text(content.replace(find, replace, 1), encoding="utf-8")
    return True


def apply_single_fix(fix, cwd):
    """Apply a single fix by replacing pre_edit_content with post_edit_content."""
    return _swap_content(fix, cwd, "pre_edit_content", "post_edit_content")


def revert_single_fix(fix, cwd):
    """Revert a single fix by replacing post_edit_content with pre_edit_content."""
    return _swap_content(fix, cwd, "post_edit_content", "pre_edit_content")


def _try_apply_fix(fix, test_command, cwd, progress, pass_detail=None):
    """Apply a single fix, test, revert on failure. Returns 'fixed'|'reverted'|'skipped'."""
    if not apply_single_fix(fix, cwd):
        return "skipped"
    test_passed, _ = run_tests(test_command, cwd)
    if test_passed:
        mark_finding_status(progress, fix, "fixed", pass_detail)
        return "fixed"
    if not revert_single_fix(fix, cwd):
        print(f"{PREFIX} WARNING: Could not revert failing fix for {fix.get('file')} — retaining fix")
        mark_finding_status(progress, fix, "fixed",
                            "Revert failed after test failure — fix retained")
        return "fixed"
    return "reverted"


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
    revert_failures = set()
    for i in range(len(fixes) - 1, -1, -1):
        if not revert_single_fix(fixes[i], cwd):
            revert_failures.add(i)
            print(f"{PREFIX} WARNING: Could not mechanically revert fix for {fixes[i].get('file')}")

    fixed_count = 0
    reverted_count = 0
    skipped_count = 0
    reverted_indices = []

    # First pass: apply incrementally, keeping passing fixes
    for i, fix in enumerate(fixes):
        if i in revert_failures:
            mark_finding_status(progress, fix, "retained — revert failed",
                                "Could not mechanically revert during bisection — fix retained untested")
            fixed_count += 1  # counts toward applied (fix is in codebase)
            continue
        outcome = _try_apply_fix(fix, test_command, cwd, progress)
        if outcome == "fixed":
            fixed_count += 1
        elif outcome == "skipped":
            # Fix could not be applied (file changed, content not found) — no retry needed
            mark_finding_status(progress, fix, "skipped — apply failed",
                                "Could not mechanically apply fix during bisection")
            skipped_count += 1
        else:
            reverted_indices.append(i)

    # Second pass: retry reverted fixes — they may depend on fixes that
    # were applied later in the first pass (e.g., fix A uses an import
    # that fix B added, but B had a higher index)
    if reverted_indices and fixed_count > 0:
        print(f"{PREFIX} Retrying {len(reverted_indices)} reverted fixes...")
        for i in reverted_indices:
            fix = fixes[i]
            outcome = _try_apply_fix(fix, test_command, cwd, progress,
                                     pass_detail="Passed on retry (dependency resolved)")
            if outcome == "fixed":
                fixed_count += 1
            elif outcome == "skipped":
                mark_finding_status(progress, fix, "skipped — apply failed",
                                    "Could not mechanically re-apply fix on retry")
                skipped_count += 1
            else:
                mark_finding_status(progress, fix, "reverted — test failure",
                                    "Test failure during bisection")
                reverted_count += 1
    else:
        # No retry needed — mark remaining reverted fixes
        for i in reverted_indices:
            mark_finding_status(progress, fixes[i], "reverted — test failure",
                                "Test failure during bisection")
            reverted_count += 1

    return fixed_count, reverted_count, skipped_count
