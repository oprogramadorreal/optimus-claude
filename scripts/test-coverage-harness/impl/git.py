import subprocess

from harness_common.constants import BACKUP_SUFFIX

from .constants import PHASE_COMMIT_TYPE, PREFIX, PROGRESS_FILE_NAME


def git_commit_checkpoint(progress, cycle, phase, cwd):
    """Create a checkpoint commit for a coverage harness phase. Returns True on success."""
    cycle_history = progress["cycle_history"]
    latest = cycle_history[-1] if cycle_history else {}

    if phase == "unit-test":
        phase_data = latest.get("unit_test", {})
        count = phase_data.get("tests_written", 0)
        detail = f"{count} tests written"
    else:
        phase_data = latest.get("refactor", {})
        count = phase_data.get("fixed", 0)
        detail = f"{count} fixed"

    commit_type = PHASE_COMMIT_TYPE.get(phase, "chore")
    title = f"{commit_type}(coverage-harness): cycle {cycle} — {detail}"

    from .reporting import build_commit_body

    body = build_commit_body(progress, cycle, phase)
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
            return True
        print(f"{PREFIX} WARNING: checkpoint commit failed: {result.stderr[:200]}")
        return False
    return True
