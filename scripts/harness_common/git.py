import fnmatch
import hashlib
import json
import os
import subprocess
import tempfile
from collections import namedtuple
from pathlib import Path

from .constants import (
    BACKUP_SUFFIX,
    COMMIT_COMMITTED,
    COMMIT_FAILED,
    COMMIT_NOTHING,
    SCRATCH_GLOBS,
)

_PREFIX = "[harness]"

# Sentinel distinguishing "PR data not provided → fetch it" from "provided as
# None" (an explicit no-open-PR result that must NOT trigger a re-fetch).
_UNSET = object()


TreeState = namedtuple("TreeState", "digest dirty base entries")


def git_test_output_paths(cwd, paths):
    """Keep output exclusions only for untracked regular files (or absent files)."""
    root = Path(cwd).resolve()
    candidates = []
    for name in paths:
        path = root / name
        try:
            path.resolve().relative_to(root)
        except ValueError:
            continue
        if Path(name).is_absolute() or path.is_symlink() or path.is_dir():
            continue
        if not path.exists() or path.is_file():
            candidates.append(name)
    if not candidates:
        return []
    tracked = subprocess.run(
        [
            "git",
            "ls-files",
            "--cached",
            "--with-tree=HEAD",
            "-z",
            "--",
            *(f":(literal){name}" for name in candidates),
        ],
        cwd=str(root),
        capture_output=True,
    )
    if tracked.returncode:
        raise RuntimeError("Cannot check tracked test outputs")
    tracked_names = {os.fsdecode(name) for name in tracked.stdout.split(b"\0")}
    return [name for name in candidates if name not in tracked_names]


def git_test_tree_state(cwd, progress_file, *, exclude_paths=()):
    """Fingerprint the source bytes a checkpoint would include, without writes.

    Ignore harness state and caller-verified test outputs, matching checkpoint
    exclusions. Include other non-ignored untracked files and HEAD; a green
    result cannot authorize later edits or a different base. Binary Git output
    avoids locale/decoding loss.

    Returns a ``TreeState``: ``digest`` covers everything, ``base`` covers HEAD
    plus the tracked diff, and ``entries`` maps each tracked or untracked path
    to its own content digest — so a caller can tell a file that changed during
    a test run from a file the run merely created (coverage reports, caches).
    """
    root = Path(cwd).resolve()
    excludes = list(_HARNESS_STATE_EXCLUDES)
    try:
        relative = Path(progress_file).resolve().relative_to(root).as_posix()
        excludes.extend([relative, relative + BACKUP_SUFFIX])
    except ValueError:
        pass  # A progress file outside the repo is not part of its tree.
    pathspec = [
        ".",
        *(f":(exclude){pattern}" for pattern in excludes),
        *(f":(exclude,literal){path}" for path in exclude_paths),
    ]

    def git_bytes(*args):
        result = subprocess.run(["git", *args], cwd=str(root), capture_output=True)
        if result.returncode:
            raise RuntimeError(f"Cannot inspect test tree: git {args[0]} failed")
        return result.stdout

    head = git_bytes("rev-parse", "HEAD")
    diff = git_bytes(
        "diff", "--binary", "--no-ext-diff", "--no-textconv", "HEAD", "--", *pathspec
    )
    base = hashlib.sha256(head + b"\0" + diff).hexdigest()
    untracked = git_bytes(
        "ls-files", "--others", "--exclude-standard", "-z", "--", *pathspec
    )
    # --stage exposes the mode: 160000 marks a submodule (gitlink), which is an
    # empty directory in a clone made without --recurse-submodules.
    staged = git_bytes("ls-files", "--cached", "--stage", "-z", "--", *pathspec)
    names = set(filter(None, untracked.split(b"\0")))
    gitlinks = {}
    for record in filter(None, staged.split(b"\0")):
        meta, _, name = record.partition(b"\t")
        mode, sha = meta.split(b" ", 2)[:2]
        names.add(name)
        if mode == b"160000":
            gitlinks[name] = sha
    # Hash actual tracked bytes too: clean/smudge filters and autocrlf can make
    # different test inputs appear identical in a Git diff. Stream large files.
    entries = {
        os.fsdecode(name): _tree_entry_digest(
            root / os.fsdecode(name), gitlinks.get(name), progress_file
        )
        for name in names
    }
    digest = hashlib.sha256(base.encode("ascii"))
    for name in sorted(entries):
        encoded = os.fsencode(name)
        digest.update(len(encoded).to_bytes(8, "big") + encoded)
        digest.update(entries[name].encode("ascii"))
    return TreeState(digest.hexdigest(), bool(diff or untracked), base, entries)


def _tree_entry_digest(path, gitlink_sha, progress_file):
    if path.is_symlink():
        return "link:" + hashlib.sha256(os.fsencode(os.readlink(path))).hexdigest()
    if path.is_file():
        file_digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                file_digest.update(block)
        return "file:" + file_digest.hexdigest()
    if path.is_dir() and (path / ".git").exists():
        # A checked-out submodule or nested repository: fingerprint it the same
        # way, so edits inside it during a test run are detected as well.
        _require_clean_nested_repository(path, subprocess.run)
        return "repo:" + git_test_tree_state(path, progress_file).digest
    if gitlink_sha:
        return "gitlink:" + gitlink_sha.decode("ascii")  # registered, not checked out
    if not path.exists():
        return "deleted"
    return "dir"  # a tracked path replaced by a directory; its files list separately


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


def _require_clean_nested_repository(path, _run):
    status = _run_git_text(
        _run,
        [
            "git",
            "status",
            "--porcelain",
            "--untracked-files=normal",
            "--ignore-submodules=none",
        ],
        path,
    )
    if status.returncode != 0:
        raise RuntimeError(f"Cannot inspect nested repository: {path}")
    if status.stdout:
        raise RuntimeError(
            f"Validate and commit dirty nested repository separately: {path}"
        )
    flags = _run(
        ["git", "ls-files", "-v", "-z"],
        capture_output=True,
        cwd=str(path),
    )
    if flags.returncode != 0:
        raise RuntimeError(f"Cannot inspect nested repository tracking flags: {path}")
    # These index flags can hide changed bytes from an otherwise clean status.
    if any(
        entry[:1].islower() or entry.startswith("S ")
        for entry in os.fsdecode(flags.stdout).split("\0")
    ):
        raise RuntimeError(
            f"Nested repository has assume-unchanged or skip-worktree tracking flags: "
            f"{path}. Clear those flags or manage this repository separately before "
            "retrying."
        )


def git_check_nested_repositories(cwd, _run=None, *, restore_commit=None):
    """Refuse unsafe child state; return whether checked-out children exist."""
    _run = _run or subprocess.run
    root = Path(cwd)
    listed = _run(
        ["git", "ls-files", "--stage", "--others", "--exclude-standard", "-z"],
        capture_output=True,
        cwd=str(root),
    )
    if listed.returncode != 0:
        raise RuntimeError(f"Cannot inspect nested repositories: {listed.stderr[:200]}")
    repositories = set()
    for record in filter(None, os.fsdecode(listed.stdout).split("\0")):
        meta, separator, name = record.partition("\t")
        fields = meta.split(" ")
        if not (
            separator
            and len(fields) == 3
            and fields[0] in {"100644", "100755", "120000", "160000"}
        ):
            name = record
        path = root / name
        if not path.is_symlink() and path.is_dir() and (path / ".git").exists():
            repositories.add(name.rstrip("/"))
    if not repositories:
        return False

    expected = {}
    if restore_commit:
        tree = _run(
            ["git", "ls-tree", "-r", "-z", restore_commit],
            capture_output=True,
            cwd=str(root),
        )
        if tree.returncode != 0:
            raise RuntimeError(
                f"Cannot inspect restore tree {restore_commit}: {tree.stderr[:200]}"
            )
        for record in filter(None, os.fsdecode(tree.stdout).split("\0")):
            meta, _, name = record.partition("\t")
            mode, _kind, sha = meta.split(" ")
            if mode == "160000":
                expected[name] = sha

    for name in sorted(repositories):
        path = root / name
        _require_clean_nested_repository(path, _run)
        if restore_commit and _rev_parse("HEAD", path, _run) != expected.get(name):
            raise RuntimeError(
                f"Cannot restore nested repository checkout from the parent: {path}. "
                "Restore its recorded commit separately before retrying."
            )
        git_check_nested_repositories(
            path,
            _run=_run,
            restore_commit=expected.get(name) if restore_commit else None,
        )
    return True


def commit_checkpoint(
    commit_message, cwd, progress_file, _run=None, *, exclude_paths=()
):
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
    try:
        git_check_nested_repositories(cwd, _run=_run)
    except RuntimeError as exc:
        print(f"{_PREFIX} WARNING: checkpoint refused: {exc}")
        return COMMIT_FAILED
    add_args = ["git", "add", "-A"]
    if exclude_paths:
        add_args.extend(
            ["--", ".", *(f":(exclude,literal){path}" for path in exclude_paths)]
        )
    add_result = _run_git_text(_run, add_args, cwd)
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
# step and _clean_working_tree. The scratch prefixes come from
# constants.SCRATCH_GLOBS (shared with cli.py's final-report cleanup); this
# repo's own .gitignore mirrors the full set as a convenience for harness
# development, and references/orchestrator-loop-single.md names them for the
# orchestrator — renaming a prefix requires synchronized updates there.
_HARNESS_STATE_EXCLUDES = (
    ".claude/*-deep-progress.json",
    ".claude/*-deep-progress.json.bak",
    ".claude/*-deep-progress.done.json",
    *(f".claude/{pattern}" for pattern in SCRATCH_GLOBS),
)


def _clean_working_tree(cwd, _run=None, *, reset_tracked=True):
    """Reset tracked files and remove untracked files/dirs.

    Preserves orchestrator state files (progress JSON, backups, per-iteration
    temp files) so the user can `--resume` after a clean-triggered restore.
    """
    _run = _run or subprocess.run
    prefix_result = _run_git_text(_run, ["git", "rev-parse", "--show-prefix"], cwd)
    if prefix_result.returncode != 0:
        raise RuntimeError(f"Cannot scope working-tree cleanup: {prefix_result.stderr}")
    # git clean's exclusions are relative to the repository, even from a
    # package directory. Escape the literal prefix before appending our globs.
    prefix = prefix_result.stdout.rstrip("\n")
    for char in ("\\", "*", "?", "[", "]"):
        prefix = prefix.replace(char, "\\" + char)
    if reset_tracked:
        checkout = _run_git_text(_run, ["git", "checkout", "."], cwd)
        if checkout.returncode != 0:
            raise RuntimeError(f"git checkout . failed: {checkout.stderr[:200]}")
    clean_cmd = ["git", "clean", "-fd"]
    for pattern in _HARNESS_STATE_EXCLUDES:
        clean_cmd.extend(["-e", f"/{prefix}{pattern}" if prefix else pattern])
    clean = _run_git_text(_run, clean_cmd, cwd)
    if clean.returncode != 0:
        raise RuntimeError(f"git clean -fd failed: {clean.stderr[:200]}")


def git_restore_to(commit, cwd, _run=None):
    """Restore working tree to match a commit (resets tracked, removes untracked)."""
    _run = _run or subprocess.run
    git_restore_tracked_to(commit, cwd, _run=_run)
    _clean_working_tree(cwd, _run=_run, reset_tracked=False)


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
    git_check_nested_repositories(cwd, _run=_run, restore_commit=commit)
    _restore_tree(commit, cwd, _run)


def _restore_tree(commit, cwd, _run, *, staged=True, worktree=True, overlay=False):
    # Restore removes iteration-only index additions, like read-tree, but its
    # pathspec confines changes to cwd instead of resetting sibling projects.
    source = _run_git_text(
        _run, ["git", "ls-tree", "-r", "--name-only", "-z", commit, "--", "."], cwd
    )
    if source.returncode != 0:
        raise RuntimeError(f"Cannot inspect restore tree {commit}: {source.stderr}")
    if not source.stdout:
        if overlay:
            return
        indexed = _run_git_text(
            _run, ["git", "ls-files", "--cached", "-z", "--", "."], cwd
        )
        if indexed.returncode != 0:
            raise RuntimeError(f"Cannot inspect restore index: {indexed.stderr}")
        if not indexed.stdout:
            return  # git restore errors on an empty scope, even for a valid tree.
    args = ["git", "restore", "--source", commit]
    if staged:
        args.append("--staged")
    if worktree:
        args.append("--worktree")
    if overlay:
        args.append("--overlay")
    result = _run_git_text(_run, [*args, "--", "."], cwd)
    if result.returncode != 0:
        raise RuntimeError(f"git restore {commit} failed: {result.stderr}")


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
        raise RuntimeError(
            "Could not list untracked files for snapshot: " f"{listed.stderr[:200]}"
        )
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
            raise RuntimeError(
                "Could not index untracked files for " f"snapshot: {added.stderr[:200]}"
            )
        tree = _run_git_text(_run, ["git", "write-tree"], cwd, env=env)
        if tree.returncode != 0:
            raise RuntimeError(
                "Could not write untracked-files tree for "
                f"snapshot: {tree.stderr[:200]}"
            )
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
            raise RuntimeError(
                "Could not commit untracked-files tree for "
                f"snapshot: {commit.stderr[:200]}"
            )
        return commit.stdout.strip()


def _stash_commit_with_untracked(base, untracked_commit, cwd, _run):
    """Synthesize a 3-parent stash commit (worktree, index, untracked files).

    Mirrors the commit shape ``git stash push --include-untracked`` produces —
    the shape ``git stash apply`` requires to restore untracked files — without
    modifying the working tree. *base* is the 2-parent commit from ``git stash
    create``, or empty when only untracked files changed. Returns the commit
    SHA on success. Raise if any part cannot be captured: a partial snapshot
    is unsafe because restoring it removes untracked files first.
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
        raise RuntimeError("Could not build untracked-files snapshot commit")
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
        raise RuntimeError(
            "Could not build untracked-files snapshot " f"commit: {made.stderr[:200]}"
        )
    return made.stdout.strip()


def git_stash_snapshot(cwd, _run=None):
    """Create a stash snapshot of current working tree without modifying it.

    Returns a complete stash commit SHA, or None only if there are no changes.
    Raises RuntimeError on capture/registration failure. ``git stash create``
    captures tracked changes as a commit object
    without touching the working tree, index, or stash reflog — but it cannot
    capture untracked files (it has no ``--include-untracked``; passing the
    flag is silently consumed as the stash message). Untracked files are
    therefore captured separately and grafted on as the stash's third parent,
    the shape ``git stash apply`` restores untracked files from. The result is
    registered in the stash reflog so apply can process it.
    """
    _run = _run or subprocess.run
    has_nested_repositories = git_check_nested_repositories(cwd, _run=_run)
    created = _run_git_text(_run, ["git", "stash", "create"], cwd)
    if created.returncode != 0:
        raise RuntimeError(f"git stash create failed: {created.stderr[:200]}")
    base = created.stdout.strip()
    untracked_commit = _untracked_snapshot_commit(cwd, _run)
    sha = base
    if untracked_commit:
        sha = _stash_commit_with_untracked(base, untracked_commit, cwd, _run)
    if has_nested_repositories:
        # Git stash omits an unstaged child HEAD advance. Check the actual
        # recovery tree before registering it or claiming a clean HEAD snapshot.
        git_check_nested_repositories(cwd, _run=_run, restore_commit=sha or "HEAD")
    if not sha:
        return None
    store = _run_git_text(
        _run, ["git", "stash", "store", "-m", "harness snapshot", sha], cwd
    )
    if store.returncode != 0:
        raise RuntimeError(f"git stash store failed: {store.stderr[:200]}")
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

    Restores only cwd from the snapshot's working, index and untracked trees,
    leaving its stash reflog entry in place so the restore is repeatable. This
    backs the bisect's clean-reset rebuilds in no-commit mode. Returns True on
    success.
    """
    _run = _run or subprocess.run
    git_check_nested_repositories(cwd, _run=_run, restore_commit=snapshot_sha)
    index_tree = _rev_parse(f"{snapshot_sha}^2", cwd, _run)
    if not index_tree:
        raise RuntimeError(f"Cannot resolve snapshot index tree: {snapshot_sha}")
    untracked_tree = _rev_parse(f"{snapshot_sha}^3", cwd, _run)
    # git stash apply has no pathspec: replay each tree directly so sibling
    # work is untouched, including edits made after the snapshot was captured.
    try:
        _restore_tree(snapshot_sha, cwd, _run)
        _clean_working_tree(cwd, _run=_run, reset_tracked=False)
        _restore_tree(index_tree, cwd, _run, worktree=False)
        if untracked_tree:
            _restore_tree(untracked_tree, cwd, _run, staged=False, overlay=True)
    except RuntimeError as exc:
        print(f"{_PREFIX} WARNING: Could not restore snapshot: {str(exc)[:200]}")
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
    --no-commit iterations), restore from it. If snapshot restoration fails, the
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
