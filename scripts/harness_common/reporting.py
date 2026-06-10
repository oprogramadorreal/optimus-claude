import re
import sys
from pathlib import Path

from .constants import FIXED_STATUSES, PERSISTENT_STATUS, REVERTED_STATUSES
from .git import git_current_branch


def _force_utf8_stdout():
    """Best-effort: make stdout encode as UTF-8 with replacement so report
    content carrying non-ASCII (accented identifiers, em-dashes quoted from
    user code) can't raise UnicodeEncodeError mid-report on a legacy Windows
    console. No-op when stdout lacks reconfigure (e.g. under test capture)."""
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass


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
    for block_match in re.finditer(block_pattern, content, re.IGNORECASE):
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
# Commit-body builders
# ---------------------------------------------------------------------------


def format_finding_line(finding):
    location = f"{finding.get('file', '?')}:{finding.get('line', '?')}"
    category = finding.get("category", "unknown")
    summary = finding.get("summary", "").replace("\n", " ").replace("\r", "")
    if len(summary) > 72:
        summary = summary[:69] + "..."
    return f"- {location} [{category}] {summary}"


def format_section(header, items, max_entries=10):
    if not items:
        return []
    lines = [header]
    for item in items[:max_entries]:
        lines.append(format_finding_line(item))
    overflow = len(items) - max_entries
    if overflow > 0:
        lines.append(f"- ... and {overflow} more")
    lines.append("")
    return lines


def build_deep_commit_body(progress, iteration, max_entries=10):
    findings = progress.get("findings", [])
    iter_findings = [
        f for f in findings if f.get("iteration_last_attempted") == iteration
    ]
    if not iter_findings:
        return ""
    fixed = [f for f in iter_findings if f.get("status") in FIXED_STATUSES]
    reverted = [f for f in iter_findings if f.get("status") in REVERTED_STATUSES]
    persistent = [f for f in iter_findings if f.get("status") == PERSISTENT_STATUS]
    lines = ["Orchestrator checkpoint — automated fixes applied and tested.", ""]
    lines.extend(format_section("Fixed:", fixed, max_entries))
    lines.extend(format_section("Reverted (test failure):", reverted, max_entries))
    lines.extend(
        format_section("Persistent (all attempts failed):", persistent, max_entries)
    )
    return "\n".join(lines)


def build_coverage_commit_body(progress, cycle, phase, max_entries=10):
    lines = [
        "Coverage orchestrator checkpoint — automated changes applied and tested.",
        "",
    ]
    if phase == "unit-test":
        tests = [
            t for t in progress.get("tests_created", []) if t.get("cycle") == cycle
        ]
        if tests:
            lines.append("Tests written:")
            for t in tests[:max_entries]:
                target = t.get("target_file", "?")
                count = t.get("test_count", "?")
                lines.append(f"- {t.get('file', '?')} → {target} ({count} tests)")
            overflow = len(tests) - max_entries
            if overflow > 0:
                lines.append(f"- ... and {overflow} more")
            lines.append("")
    else:
        findings = [
            f for f in progress.get("refactor_findings", []) if f.get("cycle") == cycle
        ]
        fixed = [f for f in findings if f.get("status") in FIXED_STATUSES]
        reverted = [f for f in findings if "reverted" in (f.get("status") or "")]
        lines.extend(format_section("Testability fixes applied:", fixed, max_entries))
        lines.extend(format_section("Reverted (test failure):", reverted, max_entries))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Final-report printers
# ---------------------------------------------------------------------------


def _print_rollback_footer(progress, has_changes_to_undo):
    if not has_changes_to_undo:
        return
    base = (progress["config"].get("base_commit") or "?")[:8]
    print()
    print(f"To squash checkpoint commits: git rebase -i {base}")
    print(f"To rollback everything:       git reset --hard {base}")
    branch = git_current_branch(progress["config"]["project_root"])
    if branch and branch not in ("main", "master"):
        print(f"To push checkpoint branch:    git push -u origin {branch}")


def print_deep_report(progress):
    _force_utf8_stdout()
    findings = progress["findings"]
    total_fixed = sum(1 for f in findings if f["status"] in FIXED_STATUSES)
    total_reverted = sum(1 for f in findings if f["status"] in REVERTED_STATUSES)
    total_persistent = sum(1 for f in findings if f["status"] == PERSISTENT_STATUS)
    iterations = progress["iteration"]["completed"]
    last_test = progress["test_results"]["last_full_run"] or "not available"

    print()
    print("=" * 60)
    print("  Deep-orchestrator cumulative report")
    print("=" * 60)
    print(f"  Skill:         {progress['skill']}")
    print(f"  Iterations:    {iterations}")
    print(f"  Fixed:         {total_fixed}")
    print(f"  Reverted:      {total_reverted}")
    print(f"  Persistent:    {total_persistent}")
    print(f"  Final tests:   {last_test}")
    termination = progress.get("termination") or {}
    if termination.get("reason"):
        print(
            f"  Stopped:       {termination['reason']} - {termination.get('message', '')}"
        )
    print("=" * 60)
    if findings:
        print()
        print(
            f"  {'#':<4} {'Iter':<5} {'File':<40} {'Category':<15} {'Summary':<40} Status"
        )
        print(f"  {'-'*4} {'-'*5} {'-'*40} {'-'*15} {'-'*40} {'-'*20}")
        for row_num, finding in enumerate(findings, 1):
            file_location = f"{finding['file']}:{finding.get('line', '?')}"
            if len(file_location) > 40:
                file_location = "..." + file_location[-37:]
            summary = finding["summary"][:40]
            iter_num = finding.get("iteration_discovered", "?")
            print(
                f"  {row_num:<4} {iter_num:<5} {file_location:<40} "
                f"{finding['category']:<15} {summary:<40} {finding['status']}"
            )
    _print_rollback_footer(progress, total_fixed > 0)


def print_coverage_report(progress):
    _force_utf8_stdout()
    cycles = progress["cycle"]["completed"]
    coverage = progress["coverage"]
    baseline = coverage.get("baseline")
    current = coverage.get("current")
    tests = progress.get("tests_created", [])
    total_tests = sum(t.get("test_count", 0) for t in tests)
    total_files = len(tests)
    untestable = progress.get("untestable_code", [])
    refactor_findings = progress.get("refactor_findings", [])
    fixed = sum(1 for f in refactor_findings if f.get("status") in FIXED_STATUSES)
    bugs = progress.get("bugs_discovered", [])
    last_test = progress["test_results"]["last_full_run"] or "not available"

    print()
    print("=" * 60)
    print("  Coverage orchestrator report")
    print("=" * 60)
    print(f"  Cycles:           {cycles}")
    if baseline is not None and current is not None:
        print(f"  Coverage:         {baseline}% -> {current}%")
    elif baseline is not None:
        print(f"  Coverage:         {baseline}% (baseline; no later measurement)")
    else:
        print("  Coverage:         not measured")
    print(f"  Tests created:    {total_tests} tests in {total_files} files")
    print(f"  Testability fixes: {fixed}")
    if untestable:
        print(f"  Still untestable: {len(untestable)}")
    if bugs:
        print(f"  Bugs discovered:  {len(bugs)}")
    print(f"  Final tests:      {last_test}")
    termination = progress.get("termination") or {}
    if termination.get("reason"):
        print(
            f"  Stopped:          {termination['reason']} - {termination.get('message', '')}"
        )
    print("=" * 60)
    history = coverage.get("history") or []
    if history:
        print()
        print(f"  {'Cycle':<8} {'Before':<10} {'After':<10} {'Delta':<10}")
        print(f"  {'-'*8} {'-'*10} {'-'*10} {'-'*10}")
        for entry in history:
            before = entry.get("before", "?")
            after = entry.get("after", "?")
            delta = entry.get("delta", "?")
            print(
                f"  {entry.get('cycle', '?'):<8} {before!s:<10} {after!s:<10} {delta!s:<10}"
            )
    _print_rollback_footer(progress, total_tests > 0 or fixed > 0)
