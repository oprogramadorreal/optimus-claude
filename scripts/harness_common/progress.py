import json
import os
import shutil
from pathlib import Path

from .constants import BACKUP_SUFFIX


def write_progress(path, progress):
    """Write the progress file atomically, keeping a backup of the prior state.

    The serialized content is written to a sibling temp file and then
    ``os.replace``d into place (atomic on the same filesystem), so an interrupted
    write — Ctrl-C, crash, power loss — can never leave a torn/truncated progress
    file that ``--resume`` would then refuse. The prior good state is also copied
    to ``<path>.bak`` as a second recovery anchor.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        shutil.copy2(str(path), str(path) + BACKUP_SUFFIX)
    data = json.dumps(progress, indent=2) + "\n"
    tmp_path = path.with_name(path.name + ".tmp")
    tmp_path.write_text(data, encoding="utf-8")
    os.replace(str(tmp_path), str(path))


def read_progress(path):
    """Read the progress file."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def record_test_result(progress, passed, summary):
    """Store test outcome in the progress structure.

    Used by both harnesses; the test_results shape is shared.
    """
    progress["test_results"]["last_full_run"] = "pass" if passed else "fail"
    progress["test_results"]["last_run_output_summary"] = summary
