from harness_common.git import git_current_branch
from harness_common.progress import format_elapsed

from .constants import FIXED_STATUSES, PREFIX


def print_report(progress, current_branch=None):
    """Print the consolidated coverage harness report."""
    cycles = progress["cycle"]["completed"]
    coverage = progress["coverage"]
    baseline = coverage.get("baseline")
    current = coverage.get("current")
    tests_created = progress.get("tests_created", [])
    total_tests = sum(t.get("test_count", 0) for t in tests_created)
    total_files = len(tests_created)
    untestable = progress.get("untestable_code", [])
    refactor_findings = progress.get("refactor_findings", [])
    fixed = sum(1 for f in refactor_findings if f.get("status") in FIXED_STATUSES)
    bugs = progress.get("bugs_discovered", [])

    last_test = progress["test_results"]["last_full_run"] or "not available"

    print(f"\n{PREFIX}")
    print(f"{PREFIX} {'=' * 50}")
    print(f"{PREFIX}   Coverage Harness Report")
    print(f"{PREFIX} {'=' * 50}")
    print(f"{PREFIX}   Cycles:           {cycles}")
    if baseline is not None:
        print(f"{PREFIX}   Coverage:         {baseline}% → {current}%")
    else:
        print(f"{PREFIX}   Coverage:         not measured")
    print(f"{PREFIX}   Tests created:    {total_tests} tests in {total_files} files")
    print(f"{PREFIX}   Testability fixes: {fixed}")
    if untestable:
        print(f"{PREFIX}   Still untestable: {len(untestable)}")
    if bugs:
        print(f"{PREFIX}   Bugs discovered:  {len(bugs)}")
    total_elapsed = progress.get("total_elapsed_seconds", 0)
    if total_elapsed:
        print(f"{PREFIX}   Elapsed:          {format_elapsed(total_elapsed)}")
    print(f"{PREFIX}   Final tests:      {last_test}")

    termination = progress["termination"]
    if termination["reason"]:
        print(
            f"{PREFIX}   Stopped:          "
            f"{termination['reason']} — {termination.get('message', '')}"
        )

    print(f"{PREFIX} {'=' * 50}")

    # Coverage history
    history = coverage.get("history", [])
    if history:
        print(f"{PREFIX}")
        print(f"{PREFIX}   {'Cycle':<8} {'Before':<10} {'After':<10} {'Delta':<10}")
        print(f"{PREFIX}   {'-'*8} {'-'*10} {'-'*10} {'-'*10}")
        for entry in history:
            before = entry.get("before", "?")
            after = entry.get("after", "?")
            delta = entry.get("delta", "?")
            print(
                f"{PREFIX}   {entry.get('cycle', '?'):<8} "
                f"{before!s:<10} {after!s:<10} {delta!s:<10}"
            )

    print(f"{PREFIX}")
    base = progress["config"].get("base_commit") or "?"

    if total_tests > 0 or fixed > 0:
        print(f"{PREFIX} To squash checkpoint commits: git rebase -i {base[:8]}")
        print(f"{PREFIX} To rollback everything:       git reset --hard {base[:8]}")
        branch = (
            current_branch
            if current_branch is not None
            else git_current_branch(progress["config"]["project_root"])
        )
        if branch and branch not in ("main", "master"):
            print(f"{PREFIX} To push checkpoint branch:    git push -u origin {branch}")
    else:
        print(
            f"{PREFIX} No changes made — the codebase may already have full coverage."
        )


def build_commit_body(progress, cycle, phase, max_entries=10):
    """Build commit body for a coverage harness checkpoint."""
    lines = ["Coverage harness checkpoint — automated changes applied and tested.", ""]

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
        reverted = [f for f in findings if "reverted" in f.get("status", "")]
        if fixed:
            lines.append("Testability fixes applied:")
            for f in fixed[:max_entries]:
                lines.append(
                    f"- {f.get('file', '?')}:{f.get('line', '?')} "
                    f"[{f.get('category', '?')}] {f.get('summary', '')[:72]}"
                )
            lines.append("")
        if reverted:
            lines.append("Reverted (test failure):")
            for f in reverted[:max_entries]:
                lines.append(
                    f"- {f.get('file', '?')}:{f.get('line', '?')} "
                    f"[{f.get('category', '?')}] {f.get('summary', '')[:72]}"
                )
            lines.append("")

    return "\n".join(lines)
