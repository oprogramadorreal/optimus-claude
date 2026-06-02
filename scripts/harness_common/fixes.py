from pathlib import Path

from .constants import normalize_path


def _is_path_within(filepath, root):
    """Check if filepath is within root (Python 3.8 compatible)."""
    try:
        filepath.relative_to(root)
        return True
    except ValueError:
        return False


def _swap_content(fix, cwd, source_field, target_field):
    """Swap one content string for another in a file."""
    # Normalize path separators for cross-platform compatibility
    fix_file = normalize_path(fix["file"])
    filepath = (Path(cwd) / fix_file).resolve()
    cwd_resolved = Path(cwd).resolve()
    if not _is_path_within(filepath, cwd_resolved):
        return False
    # Block writes to sensitive paths
    rel = filepath.relative_to(cwd_resolved)
    if any(part == ".git" for part in rel.parts):
        return False
    if not filepath.exists():
        return False
    try:
        content = filepath.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return False
    find = fix.get(source_field, "")
    replace = fix.get(target_field, "")
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


def _is_deletion_fix(fix):
    """A deletion fix (empty post_edit_content) can be applied but not reverted
    by content-swap — reverting would need to re-insert pre_edit_content but has
    no anchor to locate the insertion point.
    """
    return not fix.get("post_edit_content")


def _bisect_via_clean_reset(
    fixes, test_command, cwd, run_tests_fn, on_outcome, reset_to_clean
):
    """Bisect a set containing deletion fixes that content-swap can't revert.

    The default revert-all/re-apply strategy can't un-apply a deletion, so the
    deletion stays applied and contaminates every other fix's isolation test.
    Instead, rebuild from the pre-iteration clean state via *reset_to_clean*:
    re-establish the running set of kept (passing) fixes from clean before each
    candidate, so every fix — deletions included — is tested in true isolation.

    Same ``(fixed_count, reverted_count, skipped_count)`` contract as
    :func:`bisect_fixes`. Never emits ``"retained"`` (no un-revertible state
    survives a clean rebuild).
    """

    def _rebuild(indices):
        reset_to_clean()
        for i in indices:
            apply_single_fix(fixes[i], cwd)

    outcome = {}  # idx -> (status, detail)
    kept = []
    rejected = []
    for idx, fix in enumerate(fixes):
        _rebuild(kept)
        if not apply_single_fix(fix, cwd):
            outcome[idx] = ("skipped", None)
            continue
        passed, summary = run_tests_fn(test_command, cwd)
        if passed:
            kept.append(idx)
            outcome[idx] = ("fixed", None)
        else:
            rejected.append(idx)
            outcome[idx] = ("reverted", summary)

    # Retry rejected fixes with all first-pass keepers applied — a fix may have
    # depended on a keeper that was applied later in the first pass.
    for idx in rejected:
        _rebuild(kept)
        if not apply_single_fix(fixes[idx], cwd):
            outcome[idx] = ("skipped", None)
            continue
        passed, _summary = run_tests_fn(test_command, cwd)
        if passed:
            kept.append(idx)
            outcome[idx] = ("fixed", "Passed on retry (dependency resolved)")

    # Re-establish the final kept set on disk, then emit one outcome per fix.
    _rebuild(kept)
    fixed_count = reverted_count = skipped_count = 0
    for idx in range(len(fixes)):
        status, detail = outcome[idx]
        if on_outcome is not None:
            on_outcome(idx, fixes[idx], status, detail)
        if status == "fixed":
            fixed_count += 1
        elif status == "reverted":
            reverted_count += 1
        else:
            skipped_count += 1
    return fixed_count, reverted_count, skipped_count


def bisect_fixes(
    fixes, test_command, cwd, run_tests_fn=None, on_outcome=None, reset_to_clean=None
):
    """Bisect fixes to find which ones break tests.

    Reverts all fixes, then re-applies one at a time, running the test suite
    after each. Fixes that cause test failures are left reverted.

    *run_tests_fn*, when provided, must be a callable with signature
    ``(test_command, cwd) -> (passed: bool, summary: str)``.  When ``None``
    the function falls back to :func:`harness_common.runner.run_tests`.

    *on_outcome*, when provided, is invoked once per fix with
    ``(idx, fix, outcome, detail)`` where outcome is one of ``"fixed"``,
    ``"reverted"``, ``"skipped"``, or ``"retained"`` (revert failed → fix
    remains applied untested). ``detail`` is a contextual hint string —
    the test-failure summary on ``"reverted"``, the retry-pass note on
    ``"fixed"`` after a successful retry, and ``None`` otherwise. Lets
    callers update per-finding status with provenance.

    *reset_to_clean*, when provided, is a zero-arg callable that restores the
    working tree to the pre-iteration clean state. It is required to correctly
    bisect deletion fixes (empty post_edit_content), which can't be reverted by
    content-swap; when the set contains one, this function rebuilds from clean
    instead. When ``None`` (or no deletion present), the legacy incremental
    strategy runs unchanged.

    Returns ``(fixed_count, reverted_count, skipped_count)``.
    """
    if run_tests_fn is None:
        from .runner import run_tests as _default_run_tests

        run_tests_fn = _default_run_tests

    # Deletion fixes can't be reverted by content-swap. When the caller supplies
    # a clean-reset hook, rebuild from clean so deletions can be isolated;
    # otherwise fall through to the legacy strategy (an un-revertible deletion is
    # left applied and reported "retained").
    if reset_to_clean is not None and any(_is_deletion_fix(f) for f in fixes):
        return _bisect_via_clean_reset(
            fixes, test_command, cwd, run_tests_fn, on_outcome, reset_to_clean
        )

    def _emit(idx, fix, outcome, detail=None):
        if on_outcome is not None:
            on_outcome(idx, fix, outcome, detail)

    # Revert all fixes first
    failed_revert_indices = set()
    for idx, fix in reversed(list(enumerate(fixes))):
        if not revert_single_fix(fix, cwd):
            failed_revert_indices.add(idx)

    fixed_count = 0
    reverted_count = 0
    skipped_count = 0
    reverted_indices = []
    failure_summaries = {}  # idx → first-pass test failure summary

    # First pass: apply fixes one at a time
    for idx, fix in enumerate(fixes):
        if idx in failed_revert_indices:
            fixed_count += 1  # could not revert, so fix remains applied
            _emit(idx, fix, "retained")
            continue
        if not apply_single_fix(fix, cwd):
            skipped_count += 1
            _emit(idx, fix, "skipped")
            continue
        passed, summary = run_tests_fn(test_command, cwd)
        if passed:
            fixed_count += 1
            _emit(idx, fix, "fixed")
        else:
            revert_single_fix(fix, cwd)
            reverted_indices.append(idx)
            failure_summaries[idx] = summary

    # Second pass: retry reverted fixes — they may depend on fixes that
    # were applied later in the first pass (e.g., fix A uses an import
    # that fix B added, but B had a higher index)
    if reverted_indices and fixed_count > 0:
        for idx in reverted_indices:
            fix = fixes[idx]
            if not apply_single_fix(fix, cwd):
                # File content drifted between first revert and retry — fix
                # could not be re-applied. This is the same condition as a
                # first-pass apply failure, so count it as skipped.
                skipped_count += 1
                _emit(idx, fix, "skipped")
                continue
            passed, summary = run_tests_fn(test_command, cwd)
            if passed:
                fixed_count += 1
                _emit(idx, fix, "fixed", "Passed on retry (dependency resolved)")
            else:
                revert_single_fix(fix, cwd)
                reverted_count += 1
                # Prefer the retry's failure summary; fall back to first-pass.
                _emit(idx, fix, "reverted", summary or failure_summaries.get(idx))
    else:
        reverted_count += len(reverted_indices)
        for idx in reverted_indices:
            _emit(idx, fixes[idx], "reverted", failure_summaries.get(idx))

    return fixed_count, reverted_count, skipped_count
