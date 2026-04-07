import datetime
import json
import shutil
from pathlib import Path

from .constants import BACKUP_SUFFIX, normalize_path
from .git import git_rev_parse_head


def make_initial_progress(
    skill,
    scope,
    max_iterations,
    test_command,
    project_root,
    base_commit=None,
    started_at=None,
    focus="",
):
    """Create the initial progress file structure."""
    if base_commit is None:
        base_commit = git_rev_parse_head(project_root)
    if started_at is None:
        started_at = datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    return {
        "schema_version": 1,
        "skill": skill,
        "started_at": started_at,
        "config": {
            "max_iterations": max_iterations,
            "test_command": test_command,
            "scope": {
                "mode": "local-changes" if not scope else "directory",
                "paths": [scope] if scope else [],
                "base_ref": None,
            },
            "project_root": normalize_path(str(project_root)),
            "base_commit": base_commit,
            "focus": focus,
        },
        "iteration": {"current": 1, "completed": 0},
        "findings": [],
        "scope_files": {"current": [scope] if scope else []},
        "test_results": {"last_full_run": None, "last_run_output_summary": None},
        "iteration_history": [],
        "termination": {"reason": None, "message": None},
    }


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


def migrate_progress(progress):
    """Fill in missing top-level/nested keys for progress files written by older
    schemas. Mutates the progress dict in place. Use on the resume path so
    downstream code can rely on the canonical shape from make_initial_progress.

    Handles both fully-missing keys and partial shapes (e.g., a `scope_files`
    dict that exists but lacks the `current` subkey).
    """
    config = progress.setdefault("config", {})
    scope = config.setdefault("scope", {})
    scope.setdefault("mode", "local-changes")
    scope.setdefault("paths", [])
    scope.setdefault("base_ref", None)
    progress.setdefault("scope_files", {}).setdefault("current", [])
