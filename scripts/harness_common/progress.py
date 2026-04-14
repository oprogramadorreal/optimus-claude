import json
import os
import shutil
import time
from pathlib import Path

from .constants import BACKUP_SUFFIX


def classify_finding_status(status):
    """Return the canonical bucket for a finding's status string.

    Buckets: ``"fixed"``, ``"reverted"``, ``"persistent"``, ``"pending"``.
    ``"retained"`` (a kept fix after a passing retry) maps to ``"fixed"``.
    """
    status = status or ""
    if "fixed" in status or "retained" in status:
        return "fixed"
    if "persistent" in status:
        return "persistent"
    if "reverted" in status or "skipped" in status:
        return "reverted"
    return "pending"


def is_terminal_status(status):
    """True when a finding status is terminal (no further retries expected)."""
    return classify_finding_status(status) != "pending"


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
# Timing utilities
# ---------------------------------------------------------------------------


def record_timing(progress, label, elapsed_s):
    """Append a timing entry to the progress structure.

    Each entry records the label (e.g. "iteration-3"), wall-clock seconds,
    and an ISO timestamp.  Also updates total_elapsed_seconds.
    """
    if "timing" not in progress:
        progress["timing"] = []
    progress["timing"].append(
        {
            "label": label,
            "elapsed_seconds": round(elapsed_s, 2),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    )
    progress["total_elapsed_seconds"] = round(
        progress.get("total_elapsed_seconds", 0) + elapsed_s, 2
    )


def format_elapsed(total_seconds):
    """Format seconds as a human-readable 'Xm Ys' string."""
    total_seconds = max(0, total_seconds)
    minutes = int(total_seconds) // 60
    seconds = int(total_seconds) % 60
    if minutes > 0:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


# ---------------------------------------------------------------------------
# Progress pruning
# ---------------------------------------------------------------------------


def prune_resolved_findings(progress, current_iteration, archive_after=3):
    """Move old resolved findings to an archived_findings list.

    A finding is archived when it has a terminal status (fixed, retained,
    or persistent) and was last attempted more than *archive_after*
    iterations ago.
    """
    findings = progress.get("findings", [])
    if not findings:
        return

    archived = progress.setdefault("archived_findings", [])
    kept = []
    for f in findings:
        last_attempted = f.get(
            "iteration_last_attempted",
            f.get("iteration_discovered", current_iteration),
        )
        status = f.get("status", "")
        if (
            is_terminal_status(status)
            and (current_iteration - last_attempted) > archive_after
        ):
            archived.append(f)
        else:
            kept.append(f)
    progress["findings"] = kept


def trim_scope_files(progress, max_files=30):
    """Cap scope_files.current to at most *max_files* entries.

    Prioritises files that have active (non-terminal) findings, then fills
    the remaining slots from the existing scope order.
    """
    scope = progress.get("scope_files", {})
    current = scope.get("current", [])
    if len(current) <= max_files:
        return

    # Collect files with active (non-terminal) findings
    active_files = set()
    for f in progress.get("findings", []):
        if not is_terminal_status(f.get("status", "")):
            fpath = f.get("file", "")
            if fpath:
                active_files.add(fpath)

    prioritised = [p for p in current if p in active_files]
    rest = [p for p in current if p not in active_files]
    scope["current"] = (prioritised + rest)[:max_files]


def check_progress_size(path, warn_threshold_kb=100):
    """Return (size_kb, is_over_threshold) for a progress file.

    Used as a pre-flight check before launching a session — oversized
    progress files waste the agent's context window.
    """
    try:
        size_bytes = os.path.getsize(str(path))
    except OSError:
        return 0.0, False
    size_kb = round(size_bytes / 1024, 1)
    return size_kb, size_kb > warn_threshold_kb
