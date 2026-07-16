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
    # Both content fields must be strings. A non-string value (e.g. a JSON number
    # or null that slipped past the dispatch contract) would crash the membership
    # test and str.replace below — refuse the swap instead of raising.
    if not isinstance(find, str) or not isinstance(replace, str):
        return False
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


# Emitted as the "skipped" outcome detail when a fix cannot be applied from its
# recorded content. Lands in the finding's status_history/last_failure_hint, so
# the next iteration's subagent sees why the fix was lost.
SKIP_APPLY_DETAIL = (
    "Fix could not be applied from its recorded content — pre_edit_content/"
    "post_edit_content must match the file verbatim (possibly truncated or "
    "re-typed when the subagent output was saved)"
)


def _warn_skipped_apply(fix):
    """Log the skip warning and return the detail hint to persist.

    Returning ``SKIP_APPLY_DETAIL`` lets each call site record exactly the
    reason it just logged in one statement, so the operator-facing warning and
    the finding's persisted ``last_failure_hint`` can never drift apart.
    """
    print(
        f"[harness] WARNING: could not apply fix for {fix.get('file', '?')} "
        f"from its recorded content — skipped"
    )
    return SKIP_APPLY_DETAIL


def _bisect_via_clean_reset(
    fixes, test_command, cwd, run_tests_fn, on_outcome, reset_to_clean
):
    """Bisect by rebuilding from the pre-iteration git snapshot.

    Never trusts recorded ``pre_edit_content``/``post_edit_content`` as revert
    data: *reset_to_clean* re-establishes the running set of kept (passing)
    fixes from the clean state before each candidate, so every fix is tested in
    true isolation. This also covers the two cases content-swap reverts can't:
    deletion fixes (empty ``post_edit_content`` has no anchor to re-insert at)
    and corrupt records (a truncated ``post_edit_content`` would silently
    revert only the part it describes, tearing the file — here a corrupt record
    can only fail to apply, loudly, as ``"skipped"``).

    Same ``(fixed_count, reverted_count, skipped_count)`` contract as
    :func:`bisect_fixes`. Never emits ``"retained"`` (no un-revertible state
    survives a clean rebuild).
    """

    def _rebuild(indices):
        """Restore to the clean base, then re-apply the kept fixes.

        Returns False if the clean reset itself failed: ``reset_to_clean``
        (``restore_working_tree`` → ``git_restore_to``) raises ``RuntimeError``
        when its ``git checkout`` errors (a locked index, a missing commit).
        Testing a candidate on a dirty base gives a meaningless pass/fail, so
        the caller aborts and reports the still-undecided fixes as skipped
        rather than letting the exception crash the whole bisect (and, through
        it, the deep-step / refactor-step that called it).
        """
        try:
            reset_to_clean()
        except (RuntimeError, OSError) as exc:
            print(f"[harness] WARNING: clean reset failed mid-bisect: {exc}")
            return False
        for i in indices:
            apply_single_fix(fixes[i], cwd)
        return True

    outcome = {}  # idx -> (status, detail)
    kept = []
    rejected = []
    aborted = False
    for idx, fix in enumerate(fixes):
        if not _rebuild(kept):
            aborted = True
            break
        if not apply_single_fix(fix, cwd):
            outcome[idx] = ("skipped", _warn_skipped_apply(fix))
            continue
        passed, summary = run_tests_fn(test_command, cwd)
        if passed:
            kept.append(idx)
            outcome[idx] = ("fixed", None)
        else:
            rejected.append(idx)
            outcome[idx] = ("reverted", summary)

    # Retry rejected fixes with all first-pass keepers applied — a fix may have
    # depended on a keeper that was applied later in the first pass. With no
    # keepers the retry would replay the first pass verbatim (same clean base,
    # same fix, same test), so skip it.
    if not aborted and kept:
        for idx in rejected:
            if not _rebuild(kept):
                break
            if not apply_single_fix(fixes[idx], cwd):
                outcome[idx] = ("skipped", _warn_skipped_apply(fixes[idx]))
                continue
            passed, _summary = run_tests_fn(test_command, cwd)
            if passed:
                kept.append(idx)
                outcome[idx] = ("fixed", "Passed on retry (dependency resolved)")

    # Re-establish the final kept set on disk (best-effort), then emit one
    # outcome per fix. A fix left undecided by an aborted reset falls back to
    # "skipped" via the ``.get`` default, so the emit loop never KeyErrors and a
    # fix is never reported fixed/reverted off a result computed on a dirty base.
    _rebuild(kept)
    fixed_count = reverted_count = skipped_count = 0
    for idx in range(len(fixes)):
        status, detail = outcome.get(idx, ("skipped", None))
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

    Rebuilds from the pre-iteration git snapshot for every candidate via
    :func:`_bisect_via_clean_reset` — git is the source of truth for reverts,
    so a corrupt recorded content pair can never tear the tree, and deletion
    fixes (empty post_edit_content, no anchor to re-insert at) are isolated
    correctly.

    *run_tests_fn*, when provided, must be a callable with signature
    ``(test_command, cwd) -> (passed: bool, summary: str)``.  When ``None``
    the function falls back to :func:`harness_common.runner.run_tests`.

    *on_outcome*, when provided, is invoked once per fix with
    ``(idx, fix, outcome, detail)`` where outcome is one of ``"fixed"``,
    ``"reverted"``, or ``"skipped"``. ``detail`` is a contextual hint string —
    the test-failure summary on ``"reverted"``, the retry-pass note on
    ``"fixed"`` after a successful retry, and ``None`` otherwise. Lets
    callers update per-finding status with provenance.

    *reset_to_clean* is a required zero-arg callable (must be safely
    repeatable) that restores the working tree to the pre-iteration clean
    state. The orchestrator loop always snapshots before dispatch, so a
    missing snapshot is a protocol violation — fail loudly rather than
    bisect against an unknown base.

    Returns ``(fixed_count, reverted_count, skipped_count)``.
    """
    if run_tests_fn is None:
        from .runner import run_tests as _default_run_tests

        run_tests_fn = _default_run_tests

    if reset_to_clean is None:
        raise ValueError(
            "bisect_fixes requires reset_to_clean — no git snapshot was "
            "recorded for this iteration (run `snapshot` before the step)"
        )

    return _bisect_via_clean_reset(
        fixes, test_command, cwd, run_tests_fn, on_outcome, reset_to_clean
    )
