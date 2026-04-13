import datetime
from pathlib import Path

from harness_common.constants import normalize_path
from harness_common.git import git_rev_parse_head

# Re-export shared functions for backward compatibility
from harness_common.progress import (  # noqa: F401
    read_progress,
    record_test_result,
    write_progress,
)


def make_initial_progress(
    skill,
    scope,
    max_iterations,
    test_command,
    project_root,
    base_commit=None,
    started_at=None,
    focus="",
    _rev_parse=None,
):
    """Create the initial progress file structure."""
    if base_commit is None:
        base_commit = (_rev_parse or git_rev_parse_head)(project_root)
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
            "pr_description": None,
        },
        "iteration": {"current": 1, "completed": 0},
        "timing": [],
        "total_elapsed_seconds": 0,
        "findings": [],
        # scope_files.current is intentionally empty here — _populate_branch_scope
        # fills it by running `git diff --name-only <base>...HEAD` (with an
        # optional path filter from config.scope.paths when --scope was given),
        # so the list always contains real repo-relative file paths rather than
        # the raw directory string the user typed.
        "scope_files": {"current": []},
        "test_results": {"last_full_run": None, "last_run_output_summary": None},
        "iteration_history": [],
        "termination": {"reason": None, "message": None},
    }


def migrate_progress(progress):
    """Fill in missing top-level/nested keys for progress files written by older
    schemas. Mutates the progress dict in place. Use on the resume path so
    downstream code can rely on the canonical shape from make_initial_progress.

    Handles both fully-missing keys and partial shapes (e.g., a `scope_files`
    dict that exists but lacks the `current` subkey). If ``progress`` itself
    is not a dict (e.g., a corrupted JSON file with a top-level list), returns
    early so the downstream "missing required field" check in
    ``_load_resumed_progress`` can produce a friendly error.
    """
    if not isinstance(progress, dict):
        return
    if not isinstance(progress.get("config"), dict):
        progress["config"] = {}
    config = progress["config"]
    if not isinstance(config.get("scope"), dict):
        config["scope"] = {}
    scope = config["scope"]
    scope.setdefault("mode", "local-changes")
    scope.setdefault("paths", [])
    scope.setdefault("base_ref", None)
    config.setdefault("pr_description", None)
    if not isinstance(progress.get("scope_files"), dict):
        progress["scope_files"] = {}
    progress["scope_files"].setdefault("current", [])

    # Old shape: raw --scope directory string stored as a file list. Clear
    # so _populate_branch_scope can rediscover real files via branch-diff.
    # Both signals must agree to avoid false positives on extension-less
    # real files (Makefile, Dockerfile, LICENSE, .env, etc.):
    #   - single entry with no filename suffix (pre-FU5 always stored one
    #     raw directory string); AND
    #   - either the entry mirrors config.scope.paths (current schema) or
    #     the paths key was missing and got defaulted (older schema).
    current = progress["scope_files"]["current"]
    scope_paths = scope["paths"]  # guaranteed by setdefault above
    if (
        len(current) == 1
        and not Path(current[0]).suffix
        and (current == scope_paths or not scope_paths)
    ):
        progress["scope_files"]["current"] = []
