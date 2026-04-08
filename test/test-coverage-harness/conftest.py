import pytest


@pytest.fixture
def sample_coverage_progress():
    """Minimal valid progress dict for the test-coverage harness."""
    return {
        "schema_version": 1,
        "harness": "test-coverage",
        "started_at": "2025-01-01T00:00:00Z",
        "config": {
            "max_cycles": 5,
            "test_command": "pytest --cov",
            "scope": "",
            "project_root": "/tmp/project",
            "base_commit": "abc1234567890",
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


@pytest.fixture
def sample_unit_test_output():
    """Sample JSON output from a unit-test skill session."""
    return {
        "iteration": 1,
        "phase": "unit-test",
        "coverage": {
            "tool": "pytest-cov",
            "before": 42.3,
            "after": 58.7,
            "delta": 16.4,
        },
        "tests_written": [
            {
                "file": "tests/test_auth.py",
                "target_file": "src/auth.py",
                "target_description": "authenticate()",
                "test_count": 5,
                "status": "pass",
                "failure_reason": None,
            }
        ],
        "untestable_code": [
            {
                "file": "src/db.py",
                "line": 15,
                "end_line": 42,
                "function": "DbClient.query",
                "barrier": "hardcoded-dependency",
                "barrier_description": "Direct connection call",
                "suggested_refactoring": "Extract to constructor",
            }
        ],
        "bugs_discovered": [],
        "no_new_tests": False,
        "no_untestable_code": False,
        "no_coverage_gained": False,
    }


@pytest.fixture
def sample_refactor_output():
    """Sample JSON output from a refactor-testability session."""
    return {
        "iteration": 1,
        "new_findings": [
            {
                "file": "src/db.py",
                "line": 15,
                "category": "Testability Barrier",
                "summary": "Hardcoded connection prevents testing",
                "pre_edit_content": "conn = connect()",
                "post_edit_content": "conn = self._connection",
            }
        ],
        "fixes_applied": [
            {
                "file": "src/db.py",
                "line": 15,
                "category": "Testability Barrier",
                "summary": "Hardcoded connection prevents testing",
                "pre_edit_content": "conn = connect()",
                "post_edit_content": "conn = self._connection",
            }
        ],
        "no_new_findings": False,
        "no_actionable_fixes": False,
    }


@pytest.fixture
def claude_md_dir(tmp_path):
    """tmp_path with .claude/CLAUDE.md containing a test command."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    claude_md = claude_dir / "CLAUDE.md"
    claude_md.write_text(
        "# Project\n\n## Commands\n\n```bash\nnpm test  # Run tests\n```\n",
        encoding="utf-8",
    )
    return tmp_path
