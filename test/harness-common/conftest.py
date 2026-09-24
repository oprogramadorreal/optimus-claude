import pytest


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


@pytest.fixture
def sample_progress():
    """Minimal valid deep-variant progress dict."""
    from harness_common import cli

    return cli._make_deep_progress(
        "code-review", "", 8, "npm test", "/tmp/project", "", "abc1234567890", False
    )


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
