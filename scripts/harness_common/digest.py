"""Progress digest and iteration coaching for harness system prompts.

Pre-digests key progress state into compact text that is appended to the
``--append-system-prompt``, saving the agent from spending turns reading and
parsing the full progress JSON file.
"""


def _count_finding_statuses(findings):
    """Count findings by status category.

    Returns (fixed, reverted, persistent, pending) counts.
    """
    fixed = 0
    reverted = 0
    persistent = 0
    pending = 0
    for f in findings:
        status = f.get("status", "")
        if status in ("fixed", "retained — revert failed"):
            fixed += 1
        elif "reverted" in status or "skipped" in status:
            reverted += 1
        elif "persistent" in status:
            persistent += 1
        else:
            pending += 1
    return fixed, reverted, persistent, pending


def _format_scope_summary(scope_files, max_shown=8):
    """Build a compact scope summary line."""
    files = scope_files.get("current", [])
    if not files:
        return "Scope: (empty — will discover via git)"
    shown = files[:max_shown]
    summary = ", ".join(shown)
    if len(files) > max_shown:
        summary += f" (+{len(files) - max_shown} more)"
    return f"Scope: {len(files)} files — {summary}"


def _format_failed_fixes(findings, max_entries=5):
    """Build a compact Failed Fix Attempts block from reverted/persistent findings."""
    failed = [
        f
        for f in findings
        if any(
            kw in f.get("status", "") for kw in ("reverted", "persistent", "skipped")
        )
        and f.get("fix_description")
    ]
    if not failed:
        return ""

    lines = ["Failed fix attempts:"]
    for f in failed[:max_entries]:
        file_line = f"{f.get('file', '?')}:{f.get('line', '?')}"
        category = f.get("category", "?")
        fix_desc = f.get("fix_description", "?")
        hint = f.get("last_failure_hint", "")
        entry = f"  - {file_line} ({category}): Tried: {fix_desc}"
        if hint:
            entry += f" | Failed: {hint}"
        lines.append(entry)

    if len(failed) > max_entries:
        lines.append(f"  ... and {len(failed) - max_entries} more")
    return "\n".join(lines)


def build_progress_digest(progress, iteration):
    """Build a compact progress digest for injection into the system prompt.

    Returns a multi-line string summarizing findings, scope, and test state.
    For iteration 1, returns only the scope summary.
    """
    parts = []

    findings = progress.get("findings", [])
    fixed, reverted, persistent, pending = _count_finding_statuses(findings)

    if iteration > 1:
        parts.append(
            f"Progress: {fixed} fixed, {reverted} reverted, "
            f"{persistent} persistent, {pending} pending"
        )

    scope_files = progress.get("scope_files", {})
    parts.append(_format_scope_summary(scope_files))

    test_results = progress.get("test_results", {})
    last_run = test_results.get("last_full_run")
    if last_run:
        summary = test_results.get("last_run_output_summary", "")
        test_line = f"Last test run: {last_run}"
        if summary:
            # Keep summary compact for the system prompt
            compact = summary.strip().replace("\n", " | ")[:150]
            test_line += f" — {compact}"
        parts.append(test_line)

    if iteration > 1:
        failed_block = _format_failed_fixes(findings)
        if failed_block:
            parts.append(failed_block)

    return "\n".join(parts)


def build_iteration_coaching(progress, iteration):
    """Build iteration-adaptive coaching guidance for the system prompt.

    Returns a short guidance string tailored to the current iteration phase.
    """
    findings = progress.get("findings", [])
    fixed, reverted, persistent, _pending = _count_finding_statuses(findings)

    if iteration == 1:
        return (
            "This is the first pass. Prioritize high-severity, "
            "high-confidence findings."
        )

    if reverted > 0:
        return (
            f"{reverted} fix(es) were reverted in prior iterations due to "
            f"test failures. When re-addressing these, try a fundamentally "
            f"different approach — do not repeat the same fix."
        )

    if iteration <= 3:
        return (
            f"{fixed} issue(s) fixed so far. Focus on NEW patterns "
            f"not yet covered by prior iterations."
        )

    # Iterations 4+
    return (
        f"Yield is diminishing (iteration {iteration}). Focus only on "
        f"Critical/High-confidence findings. Skip marginal improvements."
    )


def build_coverage_digest(progress, cycle, phase):
    """Build a compact progress digest for the test-coverage harness.

    Returns a multi-line string summarizing coverage, tests, and untestable items.
    """
    parts = []

    coverage = progress.get("coverage", {})
    baseline = coverage.get("baseline")
    current = coverage.get("current")
    if baseline is not None:
        parts.append(f"Coverage: baseline {baseline}%")
    if current is not None:
        parts.append(f"Coverage: current {current}%")

    tests_created = progress.get("tests_created", [])
    if tests_created:
        parts.append(f"Tests created so far: {len(tests_created)}")

    untestable = progress.get("untestable_code", [])
    pending_untestable = [u for u in untestable if u.get("status") == "pending"]
    if pending_untestable:
        parts.append(f"Untestable code items pending: {len(pending_untestable)}")

    test_results = progress.get("test_results", {})
    last_run = test_results.get("last_full_run")
    if last_run:
        parts.append(f"Last test run: {last_run}")

    if phase == "refactor" and pending_untestable:
        files = sorted(
            set(u.get("file", "") for u in pending_untestable if u.get("file"))
        )
        if files:
            shown = files[:8]
            file_list = ", ".join(shown)
            if len(files) > 8:
                file_list += f" (+{len(files) - 8} more)"
            parts.append(f"Untestable files to address: {file_list}")

    return "\n".join(parts)


def build_coverage_coaching(progress, cycle, phase):
    """Build cycle-adaptive coaching for the test-coverage harness."""
    if cycle == 1 and phase == "unit-test":
        return (
            "First cycle. Discover coverage gaps and write tests for "
            "already-testable code. Flag untestable code for refactoring."
        )

    if phase == "refactor":
        pending = [
            u
            for u in progress.get("untestable_code", [])
            if u.get("status") == "pending"
        ]
        return (
            f"Refactor phase: {len(pending)} untestable item(s) to address. "
            f"Focus on making code testable without changing behavior."
        )

    # unit-test phase, cycle 2+
    coverage = progress.get("coverage", {})
    history = coverage.get("history", [])
    if len(history) >= 2:
        last_delta = history[-1].get("delta", 0)
        if last_delta == 0:
            return (
                "Coverage stalled in the previous cycle. Try different "
                "test strategies or target different modules."
            )

    return (
        f"Cycle {cycle}. Continue writing tests for remaining coverage gaps. "
        f"Avoid duplicating tests from prior cycles."
    )
