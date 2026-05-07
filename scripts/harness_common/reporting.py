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
    """Extract the test command from ``.claude/CLAUDE.md``. Returns None if absent.

    Discovery order:
      1. Inline form — see ``inline_patterns`` below for accepted keywords;
         first match wins.
      2. Fenced shell-style block — language tag in ``_SHELL_FENCE_LANGS``
         (or untagged). First non-comment line matching a test-runner token
         (see ``test_command_pattern`` below) wins.

    The allow-list is restricted to shell-style fences so that python / yaml
    / dockerfile blocks containing ``pytest`` inside string literals are not
    mistaken for commands. A trailing ``# comment`` is stripped from the
    matched line. Pass ``content`` directly to skip filesystem access.
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

    # Body forbids embedded ``` and must be non-empty: with the language
    # tag optional, an empty body would let a closing fence match as an
    # opener and swallow the next block. See
    # test_does_not_span_two_adjacent_non_shell_blocks.
    block_pattern = (
        r"```\s*(?:" + "|".join(_SHELL_FENCE_LANGS) + r")?\s*\n"
        r"((?:(?!```)[\s\S])+?)\n\s*```"
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
