import subprocess

from .constants import BACKUP_SUFFIX, PREFIX, PROGRESS_FILE_NAME


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


def _clean_working_tree(cwd):
    """Reset tracked files and remove untracked files/dirs."""
    subprocess.run(
        ["git", "checkout", "."], cwd=str(cwd), capture_output=True, text=True
    )
    clean = subprocess.run(
        ["git", "clean", "-fd"], cwd=str(cwd), capture_output=True, text=True
    )
    if clean.returncode != 0:
        print(f"{PREFIX} WARNING: git clean -fd failed: {clean.stderr[:200]}")


def git_restore_to(commit, cwd):
    """Restore working tree to match a commit (tracked + untracked files)."""
    result = subprocess.run(
        ["git", "checkout", commit, "--", "."],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git checkout {commit} failed: {result.stderr}")
    _clean_working_tree(cwd)


def git_stash_snapshot(cwd):
    """Create a stash snapshot of current working tree without modifying it.

    Returns a stash commit SHA that can be restored later, or None if no changes.
    Uses 'git stash create' which creates a commit object without modifying the
    working tree, index, or stash reflog. The commit is then registered in the
    stash reflog so that 'git stash apply' processes the untracked-files tree.
    """
    result = subprocess.run(
        ["git", "stash", "create", "--include-untracked"],
        capture_output=True,
        text=True,
        cwd=str(cwd),
    )
    sha = result.stdout.strip()
    if not sha:
        return None
    # Register in stash reflog so 'git stash apply' handles untracked files
    store = subprocess.run(
        ["git", "stash", "store", "-m", "deep-mode snapshot", sha],
        capture_output=True,
        text=True,
        cwd=str(cwd),
    )
    if store.returncode != 0:
        print(f"{PREFIX} WARNING: git stash store failed: {store.stderr[:200]}")
        return None
    return sha


def git_restore_snapshot(snapshot_sha, cwd):
    """Restore working tree from a stash snapshot created by git_stash_snapshot."""
    # Clean working tree so stash apply can recreate files cleanly
    _clean_working_tree(cwd)
    # Then apply the snapshot (includes untracked files if --include-untracked was used)
    result = subprocess.run(
        ["git", "stash", "apply", snapshot_sha],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"{PREFIX} WARNING: Could not restore snapshot: {result.stderr[:200]}")
        return False
    # Drop the stash entry to avoid accumulating orphaned snapshots.
    # git stash drop requires a stash ref (stash@{N}), not a raw SHA.
    list_result = subprocess.run(
        ["git", "stash", "list", "--format=%gd %H"],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    for entry in list_result.stdout.strip().splitlines():
        parts = entry.split(" ", 1)
        if len(parts) == 2 and parts[1] == snapshot_sha:
            subprocess.run(
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


def restore_working_tree(stash_sha, head_commit, cwd):
    """Restore working tree to its pre-iteration state.

    Tries the stash snapshot first (preserves uncommitted work from prior
    --no-commit iterations), falls back to git checkout of the HEAD commit.
    """
    if stash_sha:
        if git_restore_snapshot(stash_sha, cwd):
            return
    git_restore_to(head_commit, cwd)


def git_commit_checkpoint(progress, iteration, cwd):
    """Create a checkpoint commit for this iteration. Returns True on success."""
    skill = progress["skill"]
    hist = progress["iteration_history"]
    latest = hist[-1] if hist else {}
    fixed = latest.get("fixed", 0)
    reverted = latest.get("reverted", 0)

    title = (
        f"deep-harness({skill}): iteration {iteration} — "
        f"{fixed} fixed, {reverted} reverted"
    )
    # Lazy import to avoid circular dependency (reporting imports git_current_branch)
    from .reporting import build_commit_body

    body = build_commit_body(progress, iteration)
    msg = f"{title}\n\n{body}" if body else title

    add_result = subprocess.run(
        ["git", "add", "-A"], cwd=str(cwd), capture_output=True, text=True
    )
    if add_result.returncode != 0:
        print(f"{PREFIX} WARNING: git add -A failed: {add_result.stderr[:200]}")
        return False
    # Un-stage harness state files from checkpoint commits
    for pattern in [PROGRESS_FILE_NAME, PROGRESS_FILE_NAME + BACKUP_SUFFIX]:
        subprocess.run(
            ["git", "reset", "HEAD", "--", pattern],
            cwd=str(cwd),
            capture_output=True,
            text=True,
        )
    result = subprocess.run(
        ["git", "commit", "-m", msg],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"{PREFIX} WARNING: checkpoint commit failed: {result.stderr[:200]}")
        return False
    return True
