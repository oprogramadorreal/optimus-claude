import pytest


@pytest.fixture
def sample_progress():
    """Minimal valid deep-variant progress dict."""
    return {
        "schema_version": 1,
        "skill": "code-review",
        "started_at": "2025-01-01T00:00:00Z",
        "config": {
            "max_iterations": 8,
            "test_command": "npm test",
            "scope": {"mode": "local-changes", "paths": [], "base_ref": None},
            "project_root": "/tmp/project",
            "base_commit": "abc1234567890",
            "focus": "",
            "pr_description": None,
        },
        "iteration": {"current": 1, "completed": 0},
        "findings": [],
        "scope_files": {"current": []},
        "test_results": {"last_full_run": None, "last_run_output_summary": None},
        "iteration_history": [],
        "termination": {"reason": None, "message": None},
    }


@pytest.fixture
def sample_fix():
    """Fix dict matching the harness-output schema."""
    return {
        "file": "src/app.js",
        "line": 42,
        "end_line": 42,
        "category": "bug",
        "guideline": "General: avoid null dereference",
        "summary": "Add null check before accessing property",
        "fix_description": "Added null guard",
        "severity": "Critical",
        "confidence": "High",
        "agent": "bug-detector",
        "pre_edit_content": "obj.value",
        "post_edit_content": "obj?.value",
    }
