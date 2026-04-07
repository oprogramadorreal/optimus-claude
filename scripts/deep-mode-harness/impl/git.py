import json
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


def _verify_ref(cwd_str, ref):
    """Return True if ``ref`` resolves locally via ``git rev-parse --verify``.

    Returns False on subprocess failure (timeout, missing ``git`` binary) so
    the base-branch fallback chain in ``_detect_base_branch`` degrades cleanly
    instead of crashing mid-chain.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", ref],
            capture_output=True,
            text=True,
            cwd=cwd_str,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
    return result.returncode == 0


def _fetch_open_pr_data(cwd_str):
    """Return the parsed open-PR metadata dict, or ``None``.

    Returns ``None`` for every failure mode (no PR, closed PR, ``gh`` missing,
    timeout, malformed JSON, non-UTF-8 output) so callers can treat a ``None``
    result as "no PR context available" without branching on the failure reason.
    """
    try:
        result = subprocess.run(
            ["gh", "pr", "view", "--json", "title,body,baseRefName,state"],
            capture_output=True,
            text=True,
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


def _base_from_open_pr(cwd_str):
    """Return the open PR's base ref (e.g. ``origin/main``) if it exists locally."""
    pr_info = _fetch_open_pr_data(cwd_str)
    if not (pr_info and pr_info.get("baseRefName")):
        return None

    pr_base = f"origin/{pr_info['baseRefName']}"
    # Verify the PR base ref exists locally — gh returns the remote name from
    # GitHub, but the corresponding origin/<ref> may not be fetched. Kept
    # outside the gh try/except so a missing `git` binary surfaces loudly
    # instead of masquerading as "no PR".
    return pr_base if _verify_ref(cwd_str, pr_base) else None


def _base_from_symbolic_ref(cwd_str):
    """Return the base ref from ``git symbolic-ref refs/remotes/origin/HEAD``."""
    try:
        result = subprocess.run(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
            capture_output=True,
            text=True,
            cwd=cwd_str,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    if result.returncode != 0:
        return None
    # Output is like "refs/remotes/origin/main" — strip to "origin/main"
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
    return (
        _base_from_open_pr(cwd_str)
        or _base_from_symbolic_ref(cwd_str)
        or _base_from_default_branches(cwd_str)
    )


def git_discover_branch_files(cwd, path_filter=None):
    """Discover all files changed in the current feature branch vs. the base branch.

    When ``path_filter`` is provided, the underlying ``git diff --name-only``
    is scoped to that path via a pathspec — this turns ``--scope src/auth``
    into "only the files under src/auth that the feature branch touched"
    instead of the raw directory string the user typed.

    Returns a tuple ``(files, base_ref)``:

    - ``(files, base_ref)`` on success — ``files`` is a list of repo-relative
      paths, ``base_ref`` is the detected base (e.g. ``"origin/main"``).
    - ``([], base_ref)`` if the base was detected but ``git diff`` failed.
    - ``([], None)`` if no base branch could be detected.
    """
    cwd_str = str(cwd)
    base = _detect_base_branch(cwd)
    if not base:
        print(f"{PREFIX} WARNING: Could not detect base branch for scope discovery")
        return [], None

    cmd = ["git", "diff", "--name-only", f"{base}...HEAD"]
    if path_filter:
        cmd.extend(["--", path_filter])
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd_str,
        timeout=30,
    )
    if result.returncode != 0:
        print(f"{PREFIX} WARNING: git diff --name-only failed: {result.stderr[:200]}")
        return [], base

    files = [f for f in result.stdout.strip().splitlines() if f]
    return files, base


# Caps for PR metadata stored in the progress file. The body mirrors the
# Step 5 PR/MR context-injection truncation ceiling; the title cap is a
# defence against an adversarially-large API response (GitHub's own limit
# is 256, but the field is not validated on our side).
_PR_BODY_TRUNCATE_LIMIT = 4000
_PR_TITLE_TRUNCATE_LIMIT = 500


def git_fetch_open_pr_description(cwd):
    """Return metadata for the current branch's open PR, or ``None``.

    Returns ``{"title": str, "body": str, "base_ref": str | None}`` when an
    open PR exists. Returns ``None`` for any failure mode (closed PR, no PR,
    ``gh`` missing, timeout, malformed or non-UTF-8 output) — the skill
    treats this as "no PR context available" and falls back to the same
    behavior as interactive mode without an open PR.
    """
    cwd_str = str(cwd)
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
