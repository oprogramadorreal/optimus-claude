import re
from pathlib import Path


def detect_test_command(project_root, content=None):
    """
    Try to extract the test command from .claude/CLAUDE.md.
    Looks for common patterns like 'test command: ...' or code blocks with test commands.
    Pass content directly to skip filesystem access (useful for testing).
    """
    if content is None:
        claude_md = Path(project_root) / ".claude" / "CLAUDE.md"
        if not claude_md.exists():
            return None
        content = claude_md.read_text(encoding="utf-8")

    # Look for explicit test command patterns (inline backtick style)
    inline_patterns = [
        r"(?:test|tests)\s*(?:command|cmd)\s*[:=]\s*`([^`]+)`",
        r"(?:run\s+tests?|testing)\s*[:]\s*`([^`]+)`",
    ]
    for pattern in inline_patterns:
        match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
        if match:
            cmd = match.group(1).strip()
            cmd = re.sub(r"\s+#\s.*$", "", cmd)
            return cmd

    # Search within bash/sh code blocks for lines containing test commands
    block_pattern = r"```\s*(?:bash|sh)\s*\n([\s\S]*?)\n\s*```"
    test_command_pattern = r"(?:test|spec|jest|pytest|cargo test|go test|dotnet test)"
    for block_match in re.finditer(block_pattern, content):
        for line in block_match.group(1).strip().splitlines():
            line = line.strip()
            if (
                line
                and not line.startswith("#")
                and re.search(test_command_pattern, line, re.IGNORECASE)
            ):
                return re.sub(r"\s+#\s.*$", "", line)

    return None


def print_phase(prefix, unit, current, total, phase):
    """Emit a single-line phase banner for in-flight debugging.

    Example: ``[harness] [iter 3/10 · run]``. *unit* is "iter" or "cycle".
    """
    print(f"{prefix} [{unit} {current}/{total} \u00b7 {phase}]")
