import subprocess

from .constants import BACKUP_SUFFIX, PREFIX, PROGRESS_FILE_NAME, SKILL_COMMIT_TYPE


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
    checkout = subprocess.run(
        ["git", "checkout", "."], cwd=str(cwd), capture_output=True, text=True
    )
    if checkout.returncode != 0:
        print(f"{PREFIX} WARNING: git checkout . failed: {checkout.stderr[:200]}")
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


def _detect_base_branch(cwd):
    """Detect the base branch for the current feature branch.

    Tries (in order):
    1. Open PR target branch via gh CLI
    2. git symbolic-ref refs/remotes/origin/HEAD
    3. origin/main
    4. origin/master

    Returns a branch ref like 'origin/main', or None if detection fails.
    """
    cwd_str = str(cwd)

    # 1. Try gh pr view for open PR target branch
    try:
        result = subprocess.run(
            ["gh", "pr", "view", "--json", "baseRefName,state"],
            capture_output=True,
            text=True,
            cwd=cwd_str,
            timeout=10,
        )
        if result.returncode == 0:
            import json

            pr_info = json.loads(result.stdout)
            if pr_info.get("state") == "OPEN" and pr_info.get("baseRefName"):
                return f"origin/{pr_info['baseRefName']}"
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        pass

    # 2. git symbolic-ref refs/remotes/origin/HEAD
    result = subprocess.run(
        ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
        capture_output=True,
        text=True,
        cwd=cwd_str,
    )
    if result.returncode == 0:
        # Output is like "refs/remotes/origin/main" — strip to "origin/main"
        ref = result.stdout.strip()
        if ref.startswith("refs/remotes/"):
            return ref[len("refs/remotes/") :]
        return ref

    # 3. Try origin/main
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "origin/main"],
        capture_output=True,
        text=True,
        cwd=cwd_str,
    )
    if result.returncode == 0:
        return "origin/main"

    # 4. Try origin/master
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "origin/master"],
        capture_output=True,
        text=True,
        cwd=cwd_str,
    )
    if result.returncode == 0:
        return "origin/master"

    return None


def discover_branch_files(cwd):
    """Discover all files changed in the current feature branch vs. the base branch.

    Returns a list of file paths (relative to repo root), or an empty list
    if detection fails. Also returns the base ref used for scope tracking.
    """
    cwd_str = str(cwd)
    base = _detect_base_branch(cwd_str)
    if not base:
        print(f"{PREFIX} WARNING: Could not detect base branch for scope discovery")
        return [], None

    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...HEAD"],
        capture_output=True,
        text=True,
        cwd=cwd_str,
    )
    if result.returncode != 0:
        print(f"{PREFIX} WARNING: git diff --name-only failed: {result.stderr[:200]}")
        return [], base

    files = [f for f in result.stdout.strip().splitlines() if f]
    return files, base


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
    history = progress["iteration_history"]
    latest = history[-1] if history else {}
    fixed = latest.get("fixed", 0)

    commit_type = SKILL_COMMIT_TYPE.get(skill, "chore")
    title = f"{commit_type}(deep-harness): iteration {iteration} — {fixed} fixed"
    # Lazy import to avoid circular dependency (reporting imports git_current_branch)
    from .reporting import build_commit_body

    body = build_commit_body(progress, iteration)
    commit_message = f"{title}\n\n{body}" if body else title

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
        ["git", "commit", "-m", commit_message],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        if "nothing to commit" in (result.stdout + result.stderr):
            return True  # Not a failure — just nothing to commit after unstaging
        print(f"{PREFIX} WARNING: checkpoint commit failed: {result.stderr[:200]}")
        return False
    return True
