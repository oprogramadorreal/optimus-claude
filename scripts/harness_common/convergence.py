"""Convergence detection for the coverage-paired orchestrator (unit-test + refactor)."""


def read_flag(output, key):
    """Read one convergence flag out of untrusted subagent JSON.

    These flags decide whether the run STOPS, and a subagent emits the string
    ``"false"`` (truthy in Python) as readily as the literal, so FALSE is
    strict: only a value that positively spells true converges. TRUE is
    generous (bools, non-zero ints, common true spellings), because a missed
    true spelling silently burns the remaining cap: ``termination.reason`` comes
    back ``cap`` with no sign a convergence signal was dropped. Anything else
    means "keep going", which the cycle cap bounds.

    Public because ``cmd_deep_step`` reads the same flags for the review and
    refactor targets.
    """
    value = output.get(key, False)
    if isinstance(value, bool):
        return value
    # bool is a subclass of int, so this arm only ever sees real integers.
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in ("true", "yes", "y", "t", "on", "1")
    return False


def check_unit_test_convergence(unit_test_output):
    """Check if the unit-test phase signals convergence.

    Returns (converged: bool, reason: str or None).
    """
    no_new_tests = read_flag(unit_test_output, "no_new_tests")
    no_untestable = read_flag(unit_test_output, "no_untestable_code")
    no_coverage = read_flag(unit_test_output, "no_coverage_gained")

    if no_new_tests and no_untestable:
        return True, "No new tests and no untestable code — coverage plateau"
    if no_new_tests and no_coverage:
        return True, "No new tests and no coverage gained"
    return False, None


def check_refactor_convergence(refactor_output):
    """Check if the refactor phase signals convergence.

    Returns (converged: bool, reason: str or None).
    """
    no_findings = read_flag(refactor_output, "no_new_findings")
    no_actionable = read_flag(refactor_output, "no_actionable_fixes")

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
    if all(entry.get("delta") == 0 for entry in recent):
        return True, (f"Zero coverage gain for {min_consecutive} consecutive cycles")
    return False, None
