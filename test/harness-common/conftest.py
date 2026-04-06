import sys
from pathlib import Path

import pytest

# Add scripts/ to sys.path so tests can import harness_common
sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent.parent / "scripts"),
)


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
