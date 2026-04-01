import datetime
import json
import re
import shutil
from pathlib import Path

from .constants import BACKUP_SUFFIX
from .git import git_rev_parse_head


def make_initial_progress(skill, scope, max_iterations, test_command, project_root):
    """Create the initial progress file structure."""
    base_commit = git_rev_parse_head(project_root)
    return {
        "schema_version": 1,
        "skill": skill,
        "started_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "config": {
            "max_iterations": max_iterations,
            "test_command": test_command,
            "scope": {
                "mode": "local-changes" if not scope else "directory",
                "paths": [scope] if scope else [],
                "base_ref": None,
            },
            "project_root": str(project_root).replace("\\", "/"),
            "base_commit": base_commit,
        },
        "iteration": {"current": 1, "completed": 0},
        "findings": [],
        "scope_files": {"current": [scope] if scope else []},
        "test_results": {"last_full_run": None, "last_run_output_summary": None},
        "iteration_history": [],
        "termination": {"reason": None, "message": None},
    }


def generate_finding_id(progress):
    """Generate the next finding ID (f-001, f-002, ...)."""
    existing_ids = [f["id"] for f in progress["findings"] if "id" in f]
    max_num = 0
    for fid in existing_ids:
        match = re.match(r"f-(\d+)", fid)
        if match:
            max_num = max(max_num, int(match.group(1)))
    return f"f-{max_num + 1:03d}"


def record_test_result(progress, passed, summary):
    """Store test outcome in the progress structure."""
    progress["test_results"]["last_full_run"] = "pass" if passed else "fail"
    progress["test_results"]["last_run_output_summary"] = summary


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
