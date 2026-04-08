from harness_common.git import git_current_branch

# Re-export shared function for backward compatibility
from harness_common.reporting import detect_test_command  # noqa: F401

from .constants import FIXED_STATUSES, PERSISTENT_STATUS, PREFIX, REVERTED_STATUSES


def print_report(progress, current_branch=None, _get_branch=None):
    """Print the consolidated cumulative report."""
    findings = progress["findings"]
    total_fixed = sum(1 for f in findings if f["status"] in FIXED_STATUSES)
    total_reverted = sum(1 for f in findings if f["status"] in REVERTED_STATUSES)
    total_persistent = sum(1 for f in findings if f["status"] == PERSISTENT_STATUS)
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

    termination = progress["termination"]
    if termination["reason"]:
        print(
            f"{PREFIX}   Stopped:       {termination['reason']} — {termination.get('message', '')}"
        )

    print(f"{PREFIX} {'=' * 50}")

    if findings:
        print(f"{PREFIX}")
        print(
            f"{PREFIX}   {'#':<4} {'Iter':<5} {'File':<40} {'Category':<15} {'Summary':<40} {'Status'}"
        )
        print(f"{PREFIX}   {'-'*4} {'-'*5} {'-'*40} {'-'*15} {'-'*40} {'-'*20}")
        for row_num, finding in enumerate(findings, 1):
            file_location = f"{finding['file']}:{finding.get('line', '?')}"
            if len(file_location) > 40:
                file_location = "..." + file_location[-37:]
            summary = finding["summary"][:40]
            iteration_num = finding.get("iteration_discovered", "?")
            print(
                f"{PREFIX}   {row_num:<4} {iteration_num:<5} {file_location:<40} "
                f"{finding['category']:<15} {summary:<40} {finding['status']}"
            )

    print(f"{PREFIX}")
    base = progress["config"].get("base_commit") or "?"

    if total_fixed > 0:
        print(f"{PREFIX} To squash checkpoint commits: git rebase -i {base[:8]}")
        print(f"{PREFIX} To rollback everything:       git reset --hard {base[:8]}")
        # Suggest push if on a feature branch (not main/master)
        get_branch = _get_branch or git_current_branch
        branch = (
            current_branch
            if current_branch is not None
            else get_branch(progress["config"]["project_root"])
        )
        if branch and branch not in ("main", "master"):
            print(f"{PREFIX} To push checkpoint branch:    git push -u origin {branch}")
        print(f"{PREFIX}")
        print(f"{PREFIX} Next: run /optimus:commit to commit the fixes.")
    elif termination["reason"] in ("parse-failure", "crash"):
        print(
            f"{PREFIX} No fixes were retained. Check the test output above for details."
        )
        print(f"{PREFIX} To rollback everything: git reset --hard {base[:8]}")
    else:
        print(f"{PREFIX} No issues found — the codebase looks clean for this skill.")

    print(
        f"{PREFIX} Tip: start a fresh conversation for the next skill "
        f"— each skill gathers its own context from scratch."
    )


def _format_finding_line(finding):
    """Format a single finding as a commit-body bullet."""
    location = f"{finding['file']}:{finding.get('line', '?')}"
    category = finding.get("category", "unknown")
    summary = finding.get("summary", "").replace("\n", " ").replace("\r", "")
    if len(summary) > 72:
        summary = summary[:69] + "..."
    return f"- {location} [{category}] {summary}"


def _format_section(header, items, max_entries=10):
    """Format a section of findings as commit-body lines."""
    if not items:
        return []
    lines = [header]
    for item in items[:max_entries]:
        lines.append(_format_finding_line(item))
    overflow = len(items) - max_entries
    if overflow > 0:
        lines.append(f"- ... and {overflow} more")
    lines.append("")
    return lines


def build_commit_body(progress, iteration, max_entries=10):
    """Build commit body listing per-fix details for this iteration."""
    findings = progress.get("findings", [])
    iter_findings = [
        f for f in findings if f.get("iteration_last_attempted") == iteration
    ]
    if not iter_findings:
        return ""

    fixed = [f for f in iter_findings if f.get("status") in FIXED_STATUSES]
    reverted = [f for f in iter_findings if f.get("status") in REVERTED_STATUSES]
    persistent = [f for f in iter_findings if f.get("status") == PERSISTENT_STATUS]

    lines = ["Harness checkpoint — automated fixes applied and tested.", ""]
    lines.extend(_format_section("Fixed:", fixed, max_entries))
    lines.extend(_format_section("Reverted (test failure):", reverted, max_entries))
    lines.extend(
        _format_section("Persistent (all attempts failed):", persistent, max_entries)
    )

    return "\n".join(lines)
