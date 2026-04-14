"""Feed-forward digest and iteration coaching for harness system prompts.

Provides compact, human-readable summaries of progress state so the agent
doesn't waste context tokens parsing raw JSON.  Coaching adapts guidance to
the iteration/cycle phase (early vs. late).
"""

from .progress import classify_finding_status

# ---------------------------------------------------------------------------
# Deep-mode digest + coaching
# ---------------------------------------------------------------------------


def build_progress_digest(progress, iteration):
    """Build a compact multi-line digest of deep-mode progress state."""
    findings = progress.get("findings", [])
    if not findings and iteration <= 1:
        return "First iteration — no prior findings."

    counts = {"fixed": 0, "reverted": 0, "persistent": 0, "pending": 0}
    for f in findings:
        counts[classify_finding_status(f.get("status", ""))] += 1

    parts = [
        f"Iteration {iteration} of {progress.get('config', {}).get('max_iterations', '?')}.",
        f"Findings: {counts['fixed']} fixed, {counts['reverted']} reverted, "
        f"{counts['persistent']} persistent, {counts['pending']} pending.",
    ]

    # Scope summary
    scope_files = progress.get("scope_files", {}).get("current", [])
    if scope_files:
        shown = scope_files[:5]
        suffix = f" (+{len(scope_files) - 5} more)" if len(scope_files) > 5 else ""
        parts.append(f"Scope: {', '.join(shown)}{suffix}")

    # Last test status
    test_results = progress.get("test_results", {})
    last_run = test_results.get("last_full_run")
    if last_run:
        parts.append(f"Last test run: {last_run.upper()}.")

    # Failed fix attempts (iteration 2+)
    if iteration >= 2:
        failed = [
            f
            for f in findings
            if "reverted" in f.get("status", "") or "persistent" in f.get("status", "")
        ]
        if failed:
            hints = []
            for f in failed[:3]:
                hint = f.get("last_failure_hint", "")
                label = f"{f.get('file', '?')}:{f.get('line', '?')}"
                if hint:
                    hints.append(f"  - {label}: {hint[:100]}")
                else:
                    hints.append(f"  - {label}: {f.get('status', 'failed')}")
            parts.append("Prior failed fixes:")
            parts.extend(hints)

    return "\n".join(parts)


def build_iteration_coaching(progress, iteration):
    """Build iteration-adaptive guidance for the deep-mode agent."""
    if iteration <= 1:
        return (
            "Focus on high-severity, high-confidence findings only. "
            "Skip marginal or stylistic issues."
        )

    findings = progress.get("findings", [])
    has_reverts = any("reverted" in f.get("status", "") for f in findings)

    if iteration <= 3:
        coaching = "Focus on NEW patterns not yet covered by prior iterations."
        if has_reverts:
            coaching += (
                " Some prior fixes were reverted — try fundamentally different "
                "approaches rather than variations of the same fix."
            )
        return coaching

    # Iteration 4+: diminishing returns
    return (
        "Late iteration — yield is diminishing. Only report CRITICAL findings "
        "that are clearly bugs or security issues. Skip optimizations, style, "
        "and minor improvements."
    )


# ---------------------------------------------------------------------------
# Coverage digest + coaching
# ---------------------------------------------------------------------------


def build_coverage_digest(progress, cycle, phase):
    """Build a compact digest for the test-coverage harness."""
    parts = [
        f"Cycle {cycle} of {progress.get('config', {}).get('max_cycles', '?')}, phase: {phase}."
    ]

    coverage = progress.get("coverage", {})
    baseline = coverage.get("baseline")
    current = coverage.get("current")
    if baseline is not None:
        parts.append(f"Coverage: baseline {baseline}%")
        if current is not None:
            delta = round(current - baseline, 1)
            parts.append(
                f"  current {current}% (delta: {'+' if delta >= 0 else ''}{delta}%)"
            )

    tests_created = progress.get("tests_created", [])
    if tests_created:
        parts.append(f"Tests written so far: {len(tests_created)}")

    untestable = progress.get("untestable_code", [])
    pending = [u for u in untestable if u.get("status") == "pending"]
    if pending:
        parts.append(f"Untestable code items pending: {len(pending)}")
        for item in pending[:3]:
            parts.append(
                f"  - {item.get('file', '?')}:{item.get('line', '?')} "
                f"({item.get('function', '?')})"
            )

    return "\n".join(parts)


def build_coverage_coaching(progress, cycle, phase):
    """Build cycle-adaptive guidance for the coverage harness agent."""
    if phase == "unit-test":
        if cycle <= 1:
            return (
                "Write tests for the most impactful, already-testable code first. "
                "Report any untestable code you encounter."
            )
        return (
            "Focus on code not yet covered by prior cycles. "
            "Check the progress file for already-written tests to avoid duplicates."
        )

    # phase == "refactor"
    if cycle <= 1:
        return (
            "Focus on the simplest testability barriers — dependency injection, "
            "extracting pure functions, breaking up god classes."
        )
    return (
        "Address remaining untestable items. Prioritise items that block the "
        "most test coverage. Avoid large-scale refactors in late cycles."
    )
