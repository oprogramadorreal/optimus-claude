import subprocess

from harness_common.constants import BACKUP_SUFFIX

from .constants import PHASE_COMMIT_TYPE, PREFIX, PROGRESS_FILE_NAME
from .reporting import build_commit_body


def git_commit_checkpoint(
    progress,
    cycle,
    phase,
    cwd,
    phase_summary=None,
    progress_file=None,
    _run=None,
):
    """Create a checkpoint commit for a coverage harness phase. Returns True on success."""
    _run = _run or subprocess.run
    if phase_summary is None:
        phase_summary = {}

    if phase == "unit-test":
        count = phase_summary.get("tests_written", 0)
        detail = f"{count} tests written"
    else:
        count = phase_summary.get("fixed", 0)
        detail = f"{count} fixed"

    commit_type = PHASE_COMMIT_TYPE.get(phase, "chore")
    title = f"{commit_type}(coverage-harness): cycle {cycle} — {detail}"

    body = build_commit_body(progress, cycle, phase)
    commit_message = f"{title}\n\n{body}" if body else title

    add_result = _run(
        ["git", "add", "-A"], cwd=str(cwd), capture_output=True, text=True
    )
    if add_result.returncode != 0:
        print(f"{PREFIX} WARNING: git add -A failed: {add_result.stderr[:200]}")
        return False
    # Un-stage harness state files from checkpoint commits
    pf = progress_file or PROGRESS_FILE_NAME
    for pattern in [pf, pf + BACKUP_SUFFIX]:
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
        print(f"{PREFIX} WARNING: checkpoint commit failed: {result.stderr[:200]}")
        return False
    return True
