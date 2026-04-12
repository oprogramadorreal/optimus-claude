import json
import shutil
from pathlib import Path

from .constants import BACKUP_SUFFIX


def write_progress(path, progress):
    """Write the progress file with a backup."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        shutil.copy2(str(path), str(path) + BACKUP_SUFFIX)
    path.write_text(json.dumps(progress, indent=2) + "\n", encoding="utf-8")


def read_progress(path):
    """Read the progress file."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def record_test_result(progress, passed, summary):
    """Store test outcome in the progress structure.

    Used by both harnesses; the test_results shape is shared.
    """
    progress["test_results"]["last_full_run"] = "pass" if passed else "fail"
    progress["test_results"]["last_run_output_summary"] = summary


# ---------------------------------------------------------------------------
# Progress pruning — prevent file bloat in late iterations
# ---------------------------------------------------------------------------

_FIXED_KEYWORDS = ("fixed", "retained")


def prune_resolved_findings(progress, current_iteration, archive_after=3):
    """Move old resolved findings to an ``archived_findings`` section.

    Findings with a "fixed" or "retained" status that were last attempted
    more than *archive_after* iterations ago are moved out of the active
    ``findings`` list.  They remain in the file under ``archived_findings``
    for auditability but are not injected into agent context.

    Mutates *progress* in place.
    """
    if "findings" not in progress:
        return

    active = []
    archived = progress.setdefault("archived_findings", [])

    for finding in progress["findings"]:
        status = finding.get("status", "")
        last_attempted = finding.get("iteration_last_attempted", current_iteration)
        is_resolved = any(kw in status for kw in _FIXED_KEYWORDS)
        is_old = (current_iteration - last_attempted) >= archive_after

        if is_resolved and is_old:
            archived.append(finding)
        else:
            active.append(finding)

    progress["findings"] = active


def trim_scope_files(progress, max_files=30):
    """Limit ``scope_files.current`` to the most relevant files.

    Keeps files that have active (non-archived) findings, then fills the
    remaining budget from the existing scope list in order.  This prevents
    the scope from growing unboundedly across iterations.

    Mutates *progress* in place.
    """
    scope = progress.get("scope_files", {})
    current = scope.get("current", [])
    if len(current) <= max_files:
        return

    # Files with active findings always stay in scope
    finding_files = set()
    for finding in progress.get("findings", []):
        f = finding.get("file")
        if f:
            finding_files.add(f)

    # Build trimmed list: finding files first, then fill from existing order
    trimmed = [f for f in current if f in finding_files]
    for f in current:
        if len(trimmed) >= max_files:
            break
        if f not in finding_files:
            trimmed.append(f)

    scope["current"] = trimmed[:max_files]
