"""Convergence detection for the coverage-paired orchestrator (unit-test + refactor)."""


def read_flag(output, key):
    """Read one convergence flag out of untrusted subagent JSON.

    These flags decide whether the run STOPS, so a FALSE reading is strict: only
    a value that positively spells true can converge. The parse boundary
    requires these keys to be present but coerces nothing, and a subagent emits
    the string ``"false"`` as readily as the literal. Read raw, ``"false"`` is truthy in Python, so the run
    terminated on cycle 1 reporting a coverage plateau that never happened.

    Anything unrecognized means "keep going", which the cycle cap already
    bounds. This is the same untrusted-scalar class ``_finite_number`` guards
    for the coverage numbers, applied to the flags that end the run.

    Public because ``cmd_deep_step`` reads the SAME schema fields for the review
    and refactor targets. Kept private here, that consumer read them raw and
    ``"false"`` ended the run on iteration 1 — reporting a clean codebase while
    the subagent's applied edits sat untested and un-bisected.

    Strict about what is FALSE, generous about what is TRUE. The asymmetry is
    the point: a spelling this function fails to recognize as true costs the
    whole remaining cycle cap, and costs it invisibly — ``termination.reason``
    comes back ``max_cycles`` with nothing to say a convergence signal arrived
    and was dropped. ``1`` and ``"1"`` converged before this guard existed, so
    rejecting them was a silent regression; the JSON-ish true spellings are
    accepted for the same reason. Anything else still means "keep going", which
    the cycle cap bounds.
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
