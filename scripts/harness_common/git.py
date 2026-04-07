import subprocess

from .constants import BACKUP_SUFFIX

_PREFIX = "[harness]"


def commit_checkpoint(commit_message, cwd, progress_file, _run=None):
    """Stage all changes, un-stage harness state files, and commit.

    Returns True on success or when there is nothing to commit (the
    "nothing to commit" exit is treated as a no-op success because it
    means the un-stage step removed every staged path).
    """
    _run = _run or subprocess.run
    add_result = _run(
        ["git", "add", "-A"], cwd=str(cwd), capture_output=True, text=True
    )
    if add_result.returncode != 0:
        print(f"{_PREFIX} WARNING: git add -A failed: {add_result.stderr[:200]}")
        return False
    for pattern in [progress_file, progress_file + BACKUP_SUFFIX]:
        _run(
            ["git", "reset", "HEAD", "--", pattern],
            cwd=str(cwd),
            capture_output=True,
            text=True,
        )
    result = _run(
        ["git", "commit", "-m", commit_message],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        if "nothing to commit" in (result.stdout + result.stderr):
            return True
        print(f"{_PREFIX} WARNING: checkpoint commit failed: {result.stderr[:200]}")
        return False
    return True


def git_rev_parse_head(cwd):
    """Get the current HEAD commit SHA."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        cwd=str(cwd),
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _clean_working_tree(cwd, _run=None):
    """Reset tracked files and remove untracked files/dirs."""
    _run = _run or subprocess.run
    checkout = _run(
        ["git", "checkout", "."], cwd=str(cwd), capture_output=True, text=True
    )
    if checkout.returncode != 0:
        print(f"{_PREFIX} WARNING: git checkout . failed: {checkout.stderr[:200]}")
    clean = _run(["git", "clean", "-fd"], cwd=str(cwd), capture_output=True, text=True)
    if clean.returncode != 0:
        print(f"{_PREFIX} WARNING: git clean -fd failed: {clean.stderr[:200]}")


def git_restore_to(commit, cwd, _run=None):
    """Restore working tree to match a commit (tracked + untracked files)."""
    _run = _run or subprocess.run
    result = _run(
        ["git", "checkout", commit, "--", "."],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git checkout {commit} failed: {result.stderr}")
    _clean_working_tree(cwd, _run=_run)


def git_stash_snapshot(cwd, _run=None):
    """Create a stash snapshot of current working tree without modifying it.

    Returns a stash commit SHA that can be restored later, or None if no changes.
    Uses 'git stash create' which creates a commit object without modifying the
    working tree, index, or stash reflog. The commit is then registered in the
    stash reflog so that 'git stash apply' processes the untracked-files tree.
    """
    _run = _run or subprocess.run
    result = _run(
        ["git", "stash", "create", "--include-untracked"],
        capture_output=True,
        text=True,
        cwd=str(cwd),
    )
    sha = result.stdout.strip()
    if not sha:
        return None
    # Register in stash reflog so 'git stash apply' handles untracked files
    store = _run(
        ["git", "stash", "store", "-m", "harness snapshot", sha],
        capture_output=True,
        text=True,
        cwd=str(cwd),
    )
    if store.returncode != 0:
        print(f"{_PREFIX} WARNING: git stash store failed: {store.stderr[:200]}")
        return None
    return sha


def git_restore_snapshot(snapshot_sha, cwd, _run=None):
    """Restore working tree from a stash snapshot created by git_stash_snapshot."""
    _run = _run or subprocess.run
    # Clean working tree so stash apply can recreate files cleanly
    _clean_working_tree(cwd, _run=_run)
    # Then apply the snapshot (includes untracked files if --include-untracked was used)
    result = _run(
        ["git", "stash", "apply", snapshot_sha],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"{_PREFIX} WARNING: Could not restore snapshot: {result.stderr[:200]}")
        return False
    # Drop the stash entry to avoid accumulating orphaned snapshots.
    # git stash drop requires a stash ref (stash@{N}), not a raw SHA.
    list_result = _run(
        ["git", "stash", "list", "--format=%gd %H"],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    for entry in list_result.stdout.strip().splitlines():
        parts = entry.split(" ", 1)
        if len(parts) == 2 and parts[1] == snapshot_sha:
            _run(
                ["git", "stash", "drop", parts[0]],
                cwd=str(cwd),
                capture_output=True,
                text=True,
            )
            break
    return True


def git_current_branch(cwd):
    """Get the current branch name, or empty string on failure."""
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def git_diff_has_changes(cwd):
    """Check if there are any uncommitted changes (staged, unstaged, or untracked)."""
    cwd_str = str(cwd)
    if (
        subprocess.run(
            ["git", "diff", "--quiet"], cwd=cwd_str, capture_output=True
        ).returncode
        != 0
    ):
        return True
    if (
        subprocess.run(
            ["git", "diff", "--cached", "--quiet"], cwd=cwd_str, capture_output=True
        ).returncode
        != 0
    ):
        return True
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=cwd_str,
        capture_output=True,
        text=True,
    )
    return bool(untracked.stdout.strip())


def restore_working_tree(stash_sha, head_commit, cwd, _run=None):
    """Restore working tree to its pre-iteration state.

    Tries the stash snapshot first (preserves uncommitted work from prior
    --no-commit iterations), falls back to git checkout of the HEAD commit.
    """
    if stash_sha:
        if git_restore_snapshot(stash_sha, cwd, _run=_run):
            return
    git_restore_to(head_commit, cwd, _run=_run)
