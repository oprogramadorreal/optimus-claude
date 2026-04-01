import sys
from pathlib import Path

import pytest

# Add the package to sys.path so tests can import impl modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts" / "deep-mode-harness"))


@pytest.fixture
def sample_progress():
    """Minimal valid progress dict matching make_initial_progress shape."""
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
    """Fix dict with file, line, category, pre_edit_content, post_edit_content."""
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
