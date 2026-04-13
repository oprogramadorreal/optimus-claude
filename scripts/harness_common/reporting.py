import json
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


# ---------------------------------------------------------------------------
# JSON summary export
# ---------------------------------------------------------------------------


def build_json_summary(progress, harness_type):
    """Build a stable-schema summary dict from a progress structure.

    Intended for CI/CD consumption — the schema is independent of internal
    progress file evolution.
    """
    summary = {
        "harness": harness_type,
        "status": "completed",
    }

    if harness_type == "deep-mode":
        summary["skill"] = progress.get("skill", "unknown")
        iteration = progress.get("iteration", {})
        summary["iterations_completed"] = iteration.get("completed", 0)

        findings = progress.get("findings", [])
        summary["findings"] = {
            "total": len(findings),
            "fixed": sum(1 for f in findings if "fixed" in f.get("status", "")),
            "reverted": sum(1 for f in findings if "reverted" in f.get("status", "")),
            "persistent": sum(
                1 for f in findings if "persistent" in f.get("status", "")
            ),
        }
    elif harness_type == "test-coverage":
        cycle = progress.get("cycle", {})
        summary["cycles_completed"] = cycle.get("completed", 0)

        coverage = progress.get("coverage", {})
        summary["coverage"] = {
            "baseline": coverage.get("baseline"),
            "current": coverage.get("current"),
        }
        summary["tests_created"] = len(progress.get("tests_created", []))

    test_results = progress.get("test_results", {})
    summary["test_status"] = test_results.get("last_full_run", "unknown")
    summary["total_elapsed_seconds"] = progress.get("total_elapsed_seconds", 0)

    termination = progress.get("termination")
    if termination:
        summary["status"] = termination.get("reason", "terminated")
        summary["termination_message"] = termination.get("message", "")

    return summary


def write_json_summary(progress, harness_type, path):
    """Write a JSON summary file for CI/CD integration."""
    summary = build_json_summary(progress, harness_type)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
