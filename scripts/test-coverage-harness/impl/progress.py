import datetime

from harness_common.constants import normalize_path
from harness_common.git import git_rev_parse_head
from harness_common.progress import read_progress, write_progress  # noqa: F401


def make_initial_progress(
    scope,
    max_cycles,
    test_command,
    project_root,
    base_commit=None,
    started_at=None,
):
    """Create the initial progress file structure for the test-coverage harness."""
    if base_commit is None:
        base_commit = git_rev_parse_head(project_root)
    if started_at is None:
        started_at = datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    return {
        "schema_version": 1,
        "harness": "test-coverage",
        "started_at": started_at,
        "config": {
            "max_cycles": max_cycles,
            "test_command": test_command,
            "scope": scope,
            "project_root": normalize_path(str(project_root)),
            "base_commit": base_commit,
        },
        "cycle": {"current": 1, "completed": 0},
        "phase": "unit-test",
        "coverage": {
            "baseline": None,
            "current": None,
            "tool": None,
            "history": [],
        },
        "tests_created": [],
        "untestable_code": [],
        "refactor_findings": [],
        "bugs_discovered": [],
        "cycle_history": [],
        "test_results": {"last_full_run": None, "last_run_output_summary": None},
        "termination": {"reason": None, "message": None},
    }


def record_test_result(progress, passed, summary):
    """Store test outcome in the progress structure."""
    progress["test_results"]["last_full_run"] = "pass" if passed else "fail"
    progress["test_results"]["last_run_output_summary"] = summary


def record_cycle_history(progress, cycle, unit_test_result, refactor_result=None):
    """Append a cycle summary to the history."""
    entry = {"cycle": cycle, "unit_test": unit_test_result}
    if refactor_result is not None:
        entry["refactor"] = refactor_result
    progress["cycle_history"].append(entry)
    progress["cycle"]["completed"] = cycle
