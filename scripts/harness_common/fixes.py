import re
from bisect import bisect_left
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
    fix_file = normalize_path(fix.get("file"))
    if not fix_file:
        return False
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
        # newline="" exposes the file's own line endings so the write below can
        # keep them; matching still runs on "\n", the form recorded edits use.
        with filepath.open(encoding="utf-8", newline="") as stream:
            raw = stream.read()
    except (UnicodeDecodeError, OSError):
        return False
    content = raw.replace("\r\n", "\n")
    find = fix.get(source_field, "")
    replace = fix.get(target_field, "")
    # Both content fields must be strings. A non-string value (e.g. a JSON number
    # or null that slipped past the dispatch contract) would crash the membership
    # test and str.replace below — refuse the swap instead of raising.
    if not isinstance(find, str) or not isinstance(replace, str):
        return False
    find = find.replace("\r\n", "\n")
    replace = replace.replace("\r\n", "\n")
    if not find:
        # Empty find string — cannot locate target in file content.
        # This happens when reverting a deletion fix (empty post_edit_content):
        # the revert needs to re-insert pre_edit_content but has no position info.
        return False
    if find not in content:
        return False
    if content.count(find) != 1:
        return False  # Ambiguous match — refuse to apply/revert
    # Splice the match back into the raw text so every byte outside it keeps
    # its own line ending, even in a mixed-ending file. Each CRLF before a
    # position is one character longer in raw than in content.
    crlf_starts = [
        match.start() - count for count, match in enumerate(re.finditer("\r\n", raw))
    ]
    start = content.index(find)
    end = start + len(find)
    raw_start = start + bisect_left(crlf_starts, start)
    raw_end = end + bisect_left(crlf_starts, end)
    # The replacement takes the ending of the line the match starts on.
    line_end = raw.find("\n", raw_start)
    if line_end == -1:
        newline = "\r\n" if crlf_starts else "\n"
    else:
        newline = "\r\n" if raw[line_end - 1 : line_end] == "\r" else "\n"
    with filepath.open("w", encoding="utf-8", newline="") as stream:
        stream.write(raw[:raw_start] + replace.replace("\n", newline) + raw[raw_end:])
    return True


def apply_single_fix(fix, cwd):
    """Apply a single fix by replacing pre_edit_content with post_edit_content."""
    return _swap_content(fix, cwd, "pre_edit_content", "post_edit_content")


def revert_single_fix(fix, cwd):
    """Revert a single fix by replacing post_edit_content with pre_edit_content."""
    return _swap_content(fix, cwd, "post_edit_content", "pre_edit_content")


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
        (``cli._clean_reset_hook``) raises ``RuntimeError`` when its ``git
        restore`` or snapshot apply errors (a locked index, a missing commit).
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

    *reset_to_clean*, when provided, is a zero-arg callable (must be safely
    repeatable) that restores the working tree to the pre-iteration clean
    state. When available, bisection always rebuilds from clean via
    :func:`_bisect_via_clean_reset` — git is the source of truth for reverts,
    so a corrupt recorded content pair can never tear the tree, and deletion
    fixes (empty post_edit_content, no anchor to re-insert at) are isolated
    correctly. When ``None`` (no git snapshot was recorded), the legacy
    incremental revert/re-apply strategy runs instead, which trusts recorded
    content for reverts (an un-revertible fix is left applied and reported
    "retained").

    Returns ``(fixed_count, reverted_count, skipped_count)``.
    """
    if run_tests_fn is None:
        from .runner import run_tests as _default_run_tests

        run_tests_fn = _default_run_tests

    if reset_to_clean is not None:
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
            _emit(idx, fix, "skipped", _warn_skipped_apply(fix))
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
                _emit(idx, fix, "skipped", _warn_skipped_apply(fix))
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
