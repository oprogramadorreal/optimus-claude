"""Convergence detection for the test-coverage harness."""


def check_unit_test_convergence(unit_test_output):
    """Check if the unit-test phase signals convergence.

    Returns (converged: bool, reason: str or None).
    """
    no_new_tests = unit_test_output.get("no_new_tests", False)
    no_untestable = unit_test_output.get("no_untestable_code", False)
    no_coverage = unit_test_output.get("no_coverage_gained", False)

    if no_new_tests and no_untestable:
        return True, "No new tests and no untestable code — coverage plateau"
    if no_new_tests and no_coverage:
        return True, "No new tests and no coverage gained"
    return False, None


def check_refactor_convergence(refactor_output):
    """Check if the refactor phase signals convergence.

    Returns (converged: bool, reason: str or None).
    """
    no_findings = refactor_output.get("no_new_findings", False)
    no_actionable = refactor_output.get("no_actionable_fixes", False)

    if no_findings:
        return True, "Refactor found no testability issues"
    if no_actionable:
        return True, "Refactor found issues but none had actionable fixes"
    return False, None


def check_coverage_plateau(coverage_history, min_consecutive=2):
    """Check if coverage has plateaued (zero delta for consecutive cycles).

    Returns (plateaued: bool, reason: str or None).
    """
    if len(coverage_history) < min_consecutive:
        return False, None

    recent = coverage_history[-min_consecutive:]
    if all(entry.get("delta", 1) == 0 for entry in recent):
        return True, (f"Zero coverage gain for {min_consecutive} consecutive cycles")
    return False, None
