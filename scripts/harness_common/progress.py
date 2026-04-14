import json
import shutil
import time
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
