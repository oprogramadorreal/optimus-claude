from impl.convergence import (
    check_coverage_plateau,
    check_refactor_convergence,
    check_unit_test_convergence,
)


class TestCheckUnitTestConvergence:
    def test_no_convergence(self):
        output = {
            "no_new_tests": False,
            "no_untestable_code": False,
            "no_coverage_gained": False,
        }
        converged, reason = check_unit_test_convergence(output)
        assert converged is False
        assert reason is None

    def test_no_new_tests_and_no_untestable(self):
        output = {"no_new_tests": True, "no_untestable_code": True}
        converged, reason = check_unit_test_convergence(output)
        assert converged is True
        assert "plateau" in reason.lower()

    def test_no_new_tests_and_no_coverage(self):
        output = {
            "no_new_tests": True,
            "no_untestable_code": False,
            "no_coverage_gained": True,
        }
        converged, reason = check_unit_test_convergence(output)
        assert converged is True
        assert "coverage" in reason.lower()

    def test_has_untestable_but_no_tests(self):
        output = {
            "no_new_tests": True,
            "no_untestable_code": False,
            "no_coverage_gained": False,
        }
        converged, reason = check_unit_test_convergence(output)
        assert converged is False

    def test_missing_keys_default_false(self):
        output = {}
        converged, reason = check_unit_test_convergence(output)
        assert converged is False


class TestCheckRefactorConvergence:
    def test_no_convergence(self):
        output = {"no_new_findings": False, "no_actionable_fixes": False}
        converged, reason = check_refactor_convergence(output)
        assert converged is False
        assert reason is None

    def test_no_findings(self):
        output = {"no_new_findings": True}
        converged, reason = check_refactor_convergence(output)
        assert converged is True
        assert "no testability issues" in reason.lower()

    def test_no_actionable_fixes(self):
        output = {"no_new_findings": False, "no_actionable_fixes": True}
        converged, reason = check_refactor_convergence(output)
        assert converged is True
        assert "actionable" in reason.lower()

    def test_missing_keys_default_false(self):
        output = {}
        converged, reason = check_refactor_convergence(output)
        assert converged is False


class TestCheckCoveragePlateau:
    def test_not_enough_history(self):
        history = [{"delta": 0}]
        plateaued, reason = check_coverage_plateau(history)
        assert plateaued is False

    def test_no_plateau(self):
        history = [{"delta": 5}, {"delta": 3}]
        plateaued, reason = check_coverage_plateau(history)
        assert plateaued is False

    def test_plateau_detected(self):
        history = [{"delta": 5}, {"delta": 0}, {"delta": 0}]
        plateaued, reason = check_coverage_plateau(history)
        assert plateaued is True
        assert "2 consecutive" in reason

    def test_custom_min_consecutive(self):
        history = [{"delta": 0}, {"delta": 0}, {"delta": 0}]
        plateaued, reason = check_coverage_plateau(history, min_consecutive=3)
        assert plateaued is True

    def test_empty_history(self):
        plateaued, reason = check_coverage_plateau([])
        assert plateaued is False

    def test_missing_delta_key(self):
        history = [{"cycle": 1}, {"cycle": 2}]
        plateaued, reason = check_coverage_plateau(history)
        assert plateaued is False
