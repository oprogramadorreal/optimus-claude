import re
from pathlib import Path


_SHELL_FENCE_LANGS = (
    "bash",
    "sh",
    "shell",
    "console",
    "powershell",
    "pwsh",
    "cmd",
    "bat",
    "zsh",
    "fish",
)


def detect_test_command(project_root, content=None):
    """Extract the test command from ``.claude/CLAUDE.md``.

    Test-command discovery contract (shared between the deep-mode harness, the
    test-coverage harness, and any future skill that needs to read this):

    1. **Inline form** — ``test command: `<cmd>` `` / ``tests: `<cmd>` `` /
       ``run tests: `<cmd>` `` / ``testing: `<cmd>` ``. First inline match
       wins.
    2. **Fenced-block form** — a fenced code block whose language tag is one
       of ``bash``, ``sh``, ``shell``, ``console``, ``powershell``, ``pwsh``,
       ``cmd``, ``bat``, ``zsh``, ``fish``, or empty (untagged). Inside the
       block, the first non-comment line that mentions a test-runner token
       (``test``, ``spec``, ``jest``, ``pytest``, ``cargo test``, ``go test``,
       ``dotnet test``) wins.

    A trailing ``# comment`` is stripped from whichever form matched. The
    language-tag allow-list is intentionally restricted to shell-style fences
    so that ``python``/``yaml``/``dockerfile`` blocks containing a substring
    like ``pytest`` inside string literals are not mistaken for commands.

    Pass ``content`` directly to skip filesystem access (useful for testing).
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

    # Search within shell-style code blocks for lines containing test commands.
    # Allow-list of language tags (plus untagged) keeps the door closed against
    # python/yaml/dockerfile blocks where a substring like "pytest" can appear
    # inside string literals.
    block_pattern = (
        r"```\s*(?:" + "|".join(_SHELL_FENCE_LANGS) + r")?\s*\n([\s\S]*?)\n\s*```"
    )
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
