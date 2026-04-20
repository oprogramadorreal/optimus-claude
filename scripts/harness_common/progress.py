import datetime
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


def record_timing(progress, label, elapsed_seconds):
    """Append a timing entry and accumulate into total_elapsed_seconds."""
    if "timing" not in progress:
        progress["timing"] = []
    progress["timing"].append(
        {
            "label": label,
            "elapsed_seconds": round(elapsed_seconds, 2),
            "timestamp": datetime.datetime.now(datetime.timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
        }
    )
    progress["total_elapsed_seconds"] = round(
        progress.get("total_elapsed_seconds", 0) + elapsed_seconds, 2
    )
