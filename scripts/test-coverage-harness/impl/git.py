from harness_common.git import commit_checkpoint as _commit_checkpoint

from .constants import PHASE_COMMIT_TYPE, PROGRESS_FILE_NAME
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

    pf = progress_file or PROGRESS_FILE_NAME
    return _commit_checkpoint(commit_message, cwd, pf, _run=_run)
