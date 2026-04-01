import re
from pathlib import Path

from .constants import PREFIX
from .git import git_current_branch


def print_report(progress):
    """Print the consolidated cumulative report."""
    findings = progress["findings"]
    total_fixed = sum(1 for f in findings if f["status"] in ("fixed", "retained — revert failed"))
    total_reverted = sum(
        1
        for f in findings
        if f["status"] in ("reverted — test failure", "reverted — attempt 2", "skipped — apply failed")
    )
    total_persistent = sum(
        1 for f in findings if f["status"] == "persistent — fix failed"
    )
    iterations = progress["iteration"]["completed"]

    last_test = progress["test_results"]["last_full_run"] or "not available"

    print(f"\n{PREFIX}")
    print(f"{PREFIX} {'=' * 50}")
    print(f"{PREFIX}   Cumulative Report")
    print(f"{PREFIX} {'=' * 50}")
    print(f"{PREFIX}   Skill:         {progress['skill']}")
    print(f"{PREFIX}   Iterations:    {iterations}")
    print(f"{PREFIX}   Fixed:         {total_fixed}")
    print(f"{PREFIX}   Reverted:      {total_reverted}")
    print(f"{PREFIX}   Persistent:    {total_persistent}")
    print(f"{PREFIX}   Final tests:   {last_test}")

    term = progress["termination"]
    if term["reason"]:
        print(f"{PREFIX}   Stopped:       {term['reason']} — {term.get('message', '')}")

    print(f"{PREFIX} {'=' * 50}")

    if findings:
        print(f"{PREFIX}")
        print(
            f"{PREFIX}   {'#':<4} {'Iter':<5} {'File':<40} {'Category':<15} {'Summary':<40} {'Status'}"
        )
        print(f"{PREFIX}   {'-'*4} {'-'*5} {'-'*40} {'-'*15} {'-'*40} {'-'*20}")
        for row_num, finding in enumerate(findings, 1):
            file_loc = f"{finding['file']}:{finding.get('line', '?')}"
            if len(file_loc) > 40:
                file_loc = "..." + file_loc[-37:]
            summary = finding["summary"][:40]
            iter_num = finding.get("iteration_discovered", "?")
            print(
                f"{PREFIX}   {row_num:<4} {iter_num:<5} {file_loc:<40} "
                f"{finding['category']:<15} {summary:<40} {finding['status']}"
            )

    print(f"{PREFIX}")
    base = progress["config"].get("base_commit") or "?"

    if total_fixed > 0:
        print(
            f"{PREFIX} To squash checkpoint commits: git rebase -i {base[:8]}"
        )
        print(
            f"{PREFIX} To rollback everything:       git reset --hard {base[:8]}"
        )
        # Suggest push if on a feature branch (not main/master)
        branch = git_current_branch(progress["config"]["project_root"])
        if branch and branch not in ("main", "master"):
            print(
                f"{PREFIX} To push checkpoint branch:    git push -u origin {branch}"
            )
        print(f"{PREFIX}")
        print(f"{PREFIX} Next: run /optimus:commit to commit the fixes.")
    elif term["reason"] in ("parse-failure", "crash"):
        print(f"{PREFIX} No fixes were retained. Check the test output above for details.")
        print(f"{PREFIX} To rollback everything: git reset --hard {base[:8]}")
    else:
        print(f"{PREFIX} No issues found — the codebase looks clean for this skill.")

    print(
        f"{PREFIX} Tip: start a fresh conversation for the next skill "
        f"— each skill gathers its own context from scratch."
    )


def detect_test_command(project_root):
    """
    Try to extract the test command from .claude/CLAUDE.md.
    Looks for common patterns like 'test command: ...' or code blocks with test commands.
    """
    claude_md = Path(project_root) / ".claude" / "CLAUDE.md"
    if not claude_md.exists():
        return None

    content = claude_md.read_text(encoding="utf-8")

    # Look for explicit test command patterns
    patterns = [
        r"(?:test|tests)\s*(?:command|cmd)\s*[:=]\s*`([^`]+)`",
        r"```\s*(?:bash|sh)?\s*\n\s*(.+?(?:test|spec|jest|pytest|cargo test|go test|dotnet test).*)\s*\n\s*```",
        r"(?:run\s+tests?|testing)\s*[:]\s*`([^`]+)`",
    ]
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
        if match:
            cmd = match.group(1).strip()
            # Remove trailing shell comments (e.g. "npm test  # Run tests")
            cmd = re.sub(r"\s+#\s.*$", "", cmd)
            return cmd

    return None


