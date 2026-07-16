import fnmatch
import json
import os
import subprocess
import tempfile
from pathlib import Path

from .constants import (
    BACKUP_SUFFIX,
    COMMIT_COMMITTED,
    COMMIT_FAILED,
    COMMIT_NOTHING,
)

_PREFIX = "[harness]"

# Sentinel distinguishing "PR data not provided → fetch it" from "provided as
# None" (an explicit no-open-PR result that must NOT trigger a re-fetch).
_UNSET = object()


def _run_git_text(_run, args, cwd, **extra):
    """Run a git command through the ``_run`` seam with the module's text defaults.

    Centralizes the UTF-8 codec pin (``encoding="utf-8", errors="replace"``)
    that every text-mode git call in this module must carry — never the machine
    locale, which silently drops output on the first non-decodable byte on
    cp1252 Windows. Pass ``subprocess.run`` as ``_run`` at call sites that don't
    thread the test seam.
    """
    return _run(
        args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(cwd),
        **extra,
    )


def _rev_parse(ref, cwd, _run):
    """Return the SHA ``ref`` resolves to (stripped), or None on failure."""
    result = _run_git_text(_run, ["git", "rev-parse", ref], cwd)
    return result.stdout.strip() if result.returncode == 0 else None


def commit_checkpoint(commit_message, cwd, progress_file, _run=None):
    """Stage all changes, un-stage harness state files, and commit.

    Returns one of ``COMMIT_COMMITTED`` (a checkpoint was created),
    ``COMMIT_NOTHING`` (nothing remained staged after un-staging harness
    state — a no-op success), or ``COMMIT_FAILED`` (``git add``/``git commit``
    errored for a real reason). The "nothing staged" case is detected
    deterministically with ``git diff --cached --quiet`` so it never depends
    on git's prose: when the user project's .gitignore lacks the harness
    patterns (``/optimus:init`` does not provision them), the still-untracked
    progress file makes git print "nothing added to commit but untracked files
    present" rather than "nothing to commit", which must NOT be misread as a
    commit failure (that would durably disable checkpoint commits).
    """
    _run = _run or subprocess.run
    add_result = _run_git_text(_run, ["git", "add", "-A"], cwd)
    if add_result.returncode != 0:
        print(f"{_PREFIX} WARNING: git add -A failed: {add_result.stderr[:200]}")
        return COMMIT_FAILED
    # Un-stage the progress file, its backup, and the per-iteration harness
    # scratch files so a checkpoint commit never captures orchestrator state.
    # Authoritative — does not rely on the user project's .gitignore carrying
    # these patterns (which /optimus:init does not provision).
    for pattern in [
        progress_file,
        progress_file + BACKUP_SUFFIX,
        *_HARNESS_STATE_EXCLUDES,
    ]:
        _run_git_text(_run, ["git", "reset", "HEAD", "--", pattern], cwd)
    # Deterministic "is anything actually staged?" check. returncode 0 means no
    # staged diff, so the un-stage step removed every path — a clean no-op.
    staged = _run_git_text(_run, ["git", "diff", "--cached", "--quiet"], cwd)
    # `git diff --cached --quiet` exits 0 (nothing staged), 1 (changes staged),
    # or 128 (a real error: locked/corrupt index, etc.). Only a clean "1" means
    # there is something to commit; treat 0 as a no-op and any other code as a
    # failure rather than misreading an error as "staged" and running a doomed
    # commit (which would surface as COMMIT_FAILED and durably disable commits).
    if staged.returncode == 0:
        return COMMIT_NOTHING
    if staged.returncode != 1:
        print(
            f"{_PREFIX} WARNING: 'git diff --cached --quiet' errored "
            f"(rc={staged.returncode}): {staged.stderr[:200]}"
        )
        return COMMIT_FAILED
    result = _run_git_text(_run, ["git", "commit", "-m", commit_message], cwd)
    if result.returncode != 0:
        combined = result.stdout + result.stderr
        # Defense-in-depth: a hook or race could still leave nothing to commit.
        if "nothing to commit" in combined or "nothing added to commit" in combined:
            return COMMIT_NOTHING
        print(f"{_PREFIX} WARNING: checkpoint commit failed: {result.stderr[:200]}")
        return COMMIT_FAILED
    return COMMIT_COMMITTED


def git_rev_parse_head(cwd):
    """Get the current HEAD commit SHA, or None."""
    return _rev_parse("HEAD", cwd, subprocess.run)


# Authoritative harness-state patterns matched by commit_checkpoint's un-stage
# step and _clean_working_tree. This repo's own .gitignore mirrors them as a
# convenience for harness development; renaming a prefix requires synchronized
# updates here (authoritative) and in this repo's .gitignore (the dev mirror).
_HARNESS_STATE_EXCLUDES = (
    ".claude/*-deep-progress.json",
    ".claude/*-deep-progress.json.bak",
    ".claude/*-deep-progress.done.json",
    ".claude/.deep-iteration-*",
    ".claude/.unit-test-deep-*",
)


def _clean_working_tree(cwd, _run=None):
    """Reset tracked files and remove untracked files/dirs.

    Preserves orchestrator state files (progress JSON, backups, per-iteration
    temp files) so the user can `--resume` after a clean-triggered restore.
    """
    _run = _run or subprocess.run
    checkout = _run_git_text(_run, ["git", "checkout", "."], cwd)
    if checkout.returncode != 0:
        print(f"{_PREFIX} WARNING: git checkout . failed: {checkout.stderr[:200]}")
    clean_cmd = ["git", "clean", "-fd"]
    for pattern in _HARNESS_STATE_EXCLUDES:
        clean_cmd.extend(["-e", pattern])
    clean = _run_git_text(_run, clean_cmd, cwd)
    if clean.returncode != 0:
        print(f"{_PREFIX} WARNING: git clean -fd failed: {clean.stderr[:200]}")


def git_restore_to(commit, cwd, _run=None):
    """Restore working tree to match a commit (resets tracked, removes untracked)."""
    _run = _run or subprocess.run
    result = _run_git_text(_run, ["git", "checkout", commit, "--", "."], cwd)
    if result.returncode != 0:
        raise RuntimeError(f"git checkout {commit} failed: {result.stderr}")
    _clean_working_tree(cwd, _run=_run)


def git_restore_tracked_to(commit, cwd, _run=None):
    """Reset TRACKED files to a commit, leaving untracked files untouched.

    Unlike :func:`git_restore_to`, this runs no ``git clean``, so untracked
    files created during the iteration (e.g. a new module a fix imports) survive.
    It backs the commit-mode bisect clean-reset: a rebuild must undo the
    subagent's tracked edits back to the pre-iteration commit while preserving
    the non-fix working state that kept fixes may depend on — matching the
    legacy in-place bisect, which never removed untracked files. Raises on a
    failed checkout so the bisect aborts rather than test a candidate on a dirty
    base.
    """
    _run = _run or subprocess.run
    result = _run_git_text(_run, ["git", "checkout", commit, "--", "."], cwd)
    if result.returncode != 0:
        raise RuntimeError(f"git checkout {commit} failed: {result.stderr}")


def _is_harness_state_path(path):
    return any(fnmatch.fnmatch(path, pattern) for pattern in _HARNESS_STATE_EXCLUDES)


def _untracked_snapshot_commit(cwd, _run):
    """Return a commit object capturing the untracked files, or None.

    Built with a temporary index so the real index and working tree are never
    touched. Harness state files (progress JSON, iteration temp files) are
    excluded: ``_clean_working_tree`` preserves them in place during restores,
    and re-applying a stale copy would corrupt the run's bookkeeping.
    """
    listed = _run_git_text(
        _run, ["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd
    )
    if listed.returncode != 0:
        print(
            f"{_PREFIX} WARNING: could not list untracked files for snapshot: "
            f"{listed.stderr[:200]}"
        )
        return None
    files = [
        path
        for path in listed.stdout.split("\0")
        if path and not _is_harness_state_path(path)
    ]
    if not files:
        return None
    with tempfile.TemporaryDirectory() as tmp_dir:
        env = {**os.environ, "GIT_INDEX_FILE": str(Path(tmp_dir) / "index")}
        added = _run_git_text(
            _run,
            ["git", "update-index", "--add", "-z", "--stdin"],
            cwd,
            input="\0".join(files) + "\0",
            env=env,
        )
        if added.returncode != 0:
            print(
                f"{_PREFIX} WARNING: could not index untracked files for "
                f"snapshot: {added.stderr[:200]}"
            )
            return None
        tree = _run_git_text(_run, ["git", "write-tree"], cwd, env=env)
        if tree.returncode != 0:
            print(
                f"{_PREFIX} WARNING: could not write untracked-files tree for "
                f"snapshot: {tree.stderr[:200]}"
            )
            return None
        commit = _run_git_text(
            _run,
            [
                "git",
                "commit-tree",
                tree.stdout.strip(),
                "-m",
                "untracked files on harness snapshot",
            ],
            cwd,
        )
        if commit.returncode != 0:
            print(
                f"{_PREFIX} WARNING: could not commit untracked-files tree for "
                f"snapshot: {commit.stderr[:200]}"
            )
            return None
        return commit.stdout.strip()


def _stash_commit_with_untracked(base, untracked_commit, cwd, _run):
    """Synthesize a 3-parent stash commit (worktree, index, untracked files).

    Mirrors the commit shape ``git stash push --include-untracked`` produces —
    the shape ``git stash apply`` requires to restore untracked files — without
    modifying the working tree. *base* is the 2-parent commit from ``git stash
    create``, or empty when only untracked files changed. Returns the commit
    SHA on success, or *base* unchanged (possibly empty) if synthesis fails,
    degrading to a tracked-only snapshot rather than losing it entirely.
    """
    head = _rev_parse("HEAD", cwd, _run)
    tree = index_commit = None
    if base:
        tree = _rev_parse(f"{base}^{{tree}}", cwd, _run)
        index_commit = _rev_parse(f"{base}^2", cwd, _run)
    elif head:
        # No tracked changes: the worktree and index trees are HEAD's tree.
        tree = _rev_parse("HEAD^{tree}", cwd, _run)
        if tree:
            made = _run_git_text(
                _run,
                [
                    "git",
                    "commit-tree",
                    tree,
                    "-p",
                    head,
                    "-m",
                    "index on harness snapshot",
                ],
                cwd,
            )
            index_commit = made.stdout.strip() if made.returncode == 0 else None
    if not (head and tree and index_commit):
        print(f"{_PREFIX} WARNING: could not build untracked-files snapshot commit")
        return base
    made = _run_git_text(
        _run,
        [
            "git",
            "commit-tree",
            tree,
            "-p",
            head,
            "-p",
            index_commit,
            "-p",
            untracked_commit,
            "-m",
            "harness snapshot",
        ],
        cwd,
    )
    if made.returncode != 0:
        print(
            f"{_PREFIX} WARNING: could not build untracked-files snapshot "
            f"commit: {made.stderr[:200]}"
        )
        return base
    return made.stdout.strip()


def git_stash_snapshot(cwd, _run=None):
    """Create a stash snapshot of current working tree without modifying it.

    Returns a stash commit SHA that can be restored later, or None if no
    changes. ``git stash create`` captures tracked changes as a commit object
    without touching the working tree, index, or stash reflog — but it cannot
    capture untracked files (it has no ``--include-untracked``; passing the
    flag is silently consumed as the stash message). Untracked files are
    therefore captured separately and grafted on as the stash's third parent,
    the shape ``git stash apply`` restores untracked files from. The result is
    registered in the stash reflog so apply can process it.
    """
    _run = _run or subprocess.run
    base = _run_git_text(_run, ["git", "stash", "create"], cwd).stdout.strip()
    untracked_commit = _untracked_snapshot_commit(cwd, _run)
    sha = base
    if untracked_commit:
        sha = _stash_commit_with_untracked(base, untracked_commit, cwd, _run)
    if not sha:
        # With untracked_commit set but no usable stash SHA, synthesis failed on
        # the untracked-only path (empty tracked base) — the untracked files
        # could not be captured at all. Say so loudly: a later restore's
        # ``git clean`` will delete them, so this is not a silent no-op.
        if untracked_commit:
            print(
                f"{_PREFIX} WARNING: untracked files could not be captured in "
                f"the snapshot and will not be restorable"
            )
        return None
    store = _run_git_text(
        _run, ["git", "stash", "store", "-m", "harness snapshot", sha], cwd
    )
    if store.returncode != 0:
        print(f"{_PREFIX} WARNING: git stash store failed: {store.stderr[:200]}")
        return None
    return sha


def git_drop_stash(snapshot_sha, cwd, _run=None):
    """Drop the stash reflog entry matching a snapshot SHA, if present.

    Best-effort: ``git stash drop`` needs a stash ref (``stash@{N}``), not a raw
    SHA, so resolve the ref from ``git stash list``. A no-op when the SHA is
    falsy or no longer listed (already dropped). Lets callers reclaim a prior
    snapshot stash so successful (never-restored) iterations don't leak orphaned
    entries into the reflog.
    """
    if not snapshot_sha:
        return
    _run = _run or subprocess.run
    list_result = _run_git_text(_run, ["git", "stash", "list", "--format=%gd %H"], cwd)
    for entry in list_result.stdout.strip().splitlines():
        parts = entry.split(" ", 1)
        if len(parts) == 2 and parts[1] == snapshot_sha:
            _run_git_text(_run, ["git", "stash", "drop", parts[0]], cwd)
            break


def git_apply_snapshot(snapshot_sha, cwd, _run=None):
    """Restore the working tree from a stash snapshot without consuming it.

    Cleans the tree, then applies the snapshot, leaving its stash reflog entry
    in place so the restore is repeatable — this backs the bisect's clean-reset
    rebuilds in no-commit mode. Returns True on success.
    """
    _run = _run or subprocess.run
    # Clean working tree so stash apply can recreate files cleanly
    _clean_working_tree(cwd, _run=_run)
    # Then apply the snapshot (includes the untracked-files tree if present)
    result = _run_git_text(_run, ["git", "stash", "apply", snapshot_sha], cwd)
    if result.returncode != 0:
        print(f"{_PREFIX} WARNING: Could not restore snapshot: {result.stderr[:200]}")
        print(
            f"{_PREFIX} WARNING: untracked files may be missing from the working "
            f"tree — recover them with: git stash apply {snapshot_sha}"
        )
        return False
    return True


def git_restore_snapshot(snapshot_sha, cwd, _run=None):
    """One-shot restore from a stash snapshot: apply it, then drop it.

    Dropping keeps successful restores from leaking orphaned entries into the
    stash reflog; on a failed apply the snapshot is left intact (a recovery
    hint was printed). Use :func:`git_apply_snapshot` directly when the
    snapshot must stay restorable.
    """
    if not git_apply_snapshot(snapshot_sha, cwd, _run=_run):
        return False
    # Drop the applied entry to avoid accumulating orphaned snapshots.
    git_drop_stash(snapshot_sha, cwd, _run=_run)
    return True


def git_current_branch(cwd):
    """Get the current branch name, or empty string on failure."""
    result = _run_git_text(
        subprocess.run, ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def git_diff_has_changes(cwd):
    """Check if there are any uncommitted changes (staged, unstaged, or untracked)."""
    cwd_str = str(cwd)
    for args in (
        ["git", "diff", "--quiet"],
        ["git", "diff", "--cached", "--quiet"],
    ):
        if subprocess.run(args, cwd=cwd_str, capture_output=True).returncode != 0:
            return True
    untracked = _run_git_text(
        subprocess.run, ["git", "ls-files", "--others", "--exclude-standard"], cwd_str
    )
    return bool(untracked.stdout.strip())


def restore_working_tree(stash_sha, head_commit, cwd, _run=None):
    """Restore working tree to its pre-iteration state.

    With a stash snapshot (preferred — preserves uncommitted work from prior
    --no-commit iterations), restore from it. If the stash apply fails, the
    snapshot is left intact in the reflog (git_restore_snapshot printed a
    recovery hint) and this returns False WITHOUT falling back to a HEAD
    checkout — that fallback would report a successful restore while silently
    discarding the snapshot's uncommitted work. Without a stash, fall back to
    checking out head_commit. Returns True on success, False when no usable
    restore path remains.
    """
    if stash_sha:
        return git_restore_snapshot(stash_sha, cwd, _run=_run)
    if not head_commit:
        print(f"{_PREFIX} WARNING: no snapshot to restore from")
        return False
    git_restore_to(head_commit, cwd, _run=_run)
    return True


def _verify_ref(cwd_str, ref):
    """Return True if ``ref`` resolves locally via ``git rev-parse --verify``."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", ref],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=cwd_str,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
    return result.returncode == 0


def _fetch_open_pr_data(cwd_str):
    """Return the parsed open-PR metadata dict, or ``None``."""
    try:
        result = subprocess.run(
            ["gh", "pr", "view", "--json", "title,body,baseRefName,state"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=cwd_str,
            timeout=10,
        )
        if result.returncode != 0:
            return None
        pr_info = json.loads(result.stdout)
    except (
        subprocess.TimeoutExpired,
        FileNotFoundError,
        ValueError,
        UnicodeDecodeError,
    ):
        return None
    if not (isinstance(pr_info, dict) and pr_info.get("state") == "OPEN"):
        return None
    return pr_info


def get_open_pr_data(cwd):
    """Fetch the current branch's open-PR metadata once, or ``None``.

    Public accessor so a caller (``init``) can fetch the open-PR JSON a single
    time and thread it into both base-branch detection and the PR-description
    builder, instead of each re-shelling out to ``gh pr view``.
    """
    return _fetch_open_pr_data(str(cwd))


def _base_from_open_pr(cwd_str, pr_info=_UNSET):
    """Return the open PR's base ref (e.g. ``origin/main``) if it exists locally."""
    if pr_info is _UNSET:
        pr_info = _fetch_open_pr_data(cwd_str)
    if not (pr_info and pr_info.get("baseRefName")):
        return None
    pr_base = f"origin/{pr_info['baseRefName']}"
    return pr_base if _verify_ref(cwd_str, pr_base) else None


def _base_from_symbolic_ref(cwd_str):
    """Return the base ref from ``git symbolic-ref refs/remotes/origin/HEAD``."""
    try:
        result = subprocess.run(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=cwd_str,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    if result.returncode != 0:
        return None
    ref = result.stdout.strip()
    if ref.startswith("refs/remotes/"):
        return ref[len("refs/remotes/") :]
    return None


def _base_from_default_branches(cwd_str):
    """Return the first of ``origin/main`` / ``origin/master`` that exists."""
    for fallback in ("origin/main", "origin/master"):
        if _verify_ref(cwd_str, fallback):
            return fallback
    return None


def _detect_base_branch(cwd, pr_info=_UNSET):
    """Detect the base branch for the current feature branch."""
    cwd_str = str(cwd)
    return (
        _base_from_open_pr(cwd_str, pr_info)
        or _base_from_symbolic_ref(cwd_str)
        or _base_from_default_branches(cwd_str)
    )


def git_discover_branch_files(cwd, path_filter=None, pr_info=_UNSET):
    """Discover all files changed in the current feature branch vs. the base branch.

    Returns ``(files, base_ref)`` — ``files`` is a list of repo-relative paths;
    ``base_ref`` is the detected base (e.g. ``"origin/main"``) or ``None`` when
    detection fails.
    """
    cwd_str = str(cwd)
    base = _detect_base_branch(cwd, pr_info)
    if not base:
        return [], None
    # core.quotePath=false keeps non-ASCII paths literal (UTF-8) instead of
    # octal-escaped and double-quoted, so discovered filenames match the
    # downstream normalize_path comparisons rather than being silently dropped.
    cmd = ["git", "-c", "core.quotePath=false", "diff", "--name-only", f"{base}...HEAD"]
    if path_filter:
        cmd.extend(["--", path_filter])
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=cwd_str,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return [], base
    if result.returncode != 0:
        return [], base
    files = [f for f in result.stdout.strip().splitlines() if f]
    return files, base


_PR_BODY_TRUNCATE_LIMIT = 4000
_PR_TITLE_TRUNCATE_LIMIT = 500


def git_fetch_open_pr_description(cwd, pr_info=_UNSET):
    """Return metadata for the current branch's open PR, or ``None``.

    Returns ``{"title": str, "body": str, "base_ref": str | None}`` when an
    open PR exists. Returns ``None`` for any failure mode (closed PR, no PR,
    ``gh`` missing, timeout, malformed or non-UTF-8 output). Pass ``pr_info``
    (from :func:`get_open_pr_data`) to reuse an already-fetched payload instead
    of re-shelling out to ``gh``.
    """
    cwd_str = str(cwd)
    if pr_info is _UNSET:
        pr_info = _fetch_open_pr_data(cwd_str)
    if not pr_info:
        return None
    title = (pr_info.get("title") or "")[:_PR_TITLE_TRUNCATE_LIMIT]
    body = pr_info.get("body") or ""
    if len(body) > _PR_BODY_TRUNCATE_LIMIT:
        body = body[:_PR_BODY_TRUNCATE_LIMIT] + "\n\n[...truncated...]"
    base_ref_name = pr_info.get("baseRefName")
    return {
        "title": title,
        "body": body,
        "base_ref": f"origin/{base_ref_name}" if base_ref_name else None,
    }
