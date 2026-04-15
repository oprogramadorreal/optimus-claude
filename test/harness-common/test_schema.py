from harness_common.schema import (
    validate_coverage_unit_test_output,
    validate_deep_mode_output,
    validate_harness_output,
)


class TestValidateDeepModeOutput:
    def test_valid_output(self):
        data = {
            "new_findings": [
                {"file": "a.py", "line": 10, "category": "bug"},
            ],
            "fixes_applied": [],
            "no_new_findings": False,
            "no_actionable_fixes": False,
        }
        result, warnings = validate_deep_mode_output(data)
        assert warnings == []
        assert result is data

    def test_fills_missing_lists(self):
        data = {"no_new_findings": True, "no_actionable_fixes": True}
        result, warnings = validate_deep_mode_output(data)
        assert result["new_findings"] == []
        assert result["fixes_applied"] == []

    def test_fills_missing_bools(self):
        data = {}
        result, warnings = validate_deep_mode_output(data)
        assert result["no_new_findings"] is False
        assert result["no_actionable_fixes"] is False

    def test_wrong_type_list(self):
        data = {"new_findings": "not a list"}
        result, warnings = validate_deep_mode_output(data)
        assert any("should be a list" in w for w in warnings)
        assert result["new_findings"] == []

    def test_wrong_type_bool(self):
        data = {"no_new_findings": "yes"}
        result, warnings = validate_deep_mode_output(data)
        assert any("should be bool" in w for w in warnings)
        assert result["no_new_findings"] is False

    def test_finding_missing_file(self):
        data = {"new_findings": [{"line": 10, "category": "bug"}]}
        _, warnings = validate_deep_mode_output(data)
        assert any("missing required field 'file'" in w for w in warnings)

    def test_finding_line_coercion(self):
        data = {"new_findings": [{"file": "a.py", "line": "42", "category": "bug"}]}
        result, warnings = validate_deep_mode_output(data)
        assert result["new_findings"][0]["line"] == 42
        assert warnings == []

    def test_finding_bad_line(self):
        data = {"new_findings": [{"file": "a.py", "line": "abc", "category": "bug"}]}
        _, warnings = validate_deep_mode_output(data)
        assert any("not an integer" in w for w in warnings)

    def test_finding_non_integer_float_warns_and_nulls(self):
        data = {"new_findings": [{"file": "a.py", "line": 2.5, "category": "bug"}]}
        result, warnings = validate_deep_mode_output(data)
        assert result["new_findings"][0]["line"] is None
        assert any("not an integer" in w for w in warnings)

    def test_finding_integer_valued_float_coerces(self):
        data = {"new_findings": [{"file": "a.py", "line": 10.0, "category": "bug"}]}
        result, warnings = validate_deep_mode_output(data)
        assert result["new_findings"][0]["line"] == 10
        assert warnings == []

    def test_non_dict_input(self):
        result, warnings = validate_deep_mode_output([1, 2, 3])
        assert any("Expected dict" in w for w in warnings)

    def test_non_dict_finding(self):
        data = {"new_findings": ["not a dict"]}
        _, warnings = validate_deep_mode_output(data)
        assert any("not a dict" in w for w in warnings)


class TestValidateCoverageUnitTestOutput:
    def test_valid_output(self):
        data = {
            "tests_written": [{"file": "test_a.py"}],
            "coverage": {"before": 40, "after": 50, "delta": 10},
            "no_new_tests": False,
            "no_untestable_code": True,
            "no_coverage_gained": False,
        }
        result, warnings = validate_coverage_unit_test_output(data)
        assert warnings == []

    def test_fills_defaults(self):
        data = {}
        result, warnings = validate_coverage_unit_test_output(data)
        assert result["tests_written"] == []
        assert result["no_new_tests"] is False
        assert result["coverage"] == {"before": None, "after": None, "delta": None}

    def test_wrong_coverage_type(self):
        data = {"coverage": "50%"}
        result, warnings = validate_coverage_unit_test_output(data)
        assert any("should be dict" in w for w in warnings)
        assert result["coverage"] == {"before": None, "after": None, "delta": None}

    def test_coverage_fills_missing_subfields(self):
        data = {"coverage": {"before": 40}}
        result, _ = validate_coverage_unit_test_output(data)
        assert result["coverage"]["after"] is None
        assert result["coverage"]["delta"] is None


class TestValidateHarnessOutput:
    def test_dispatches_deep_mode(self):
        data = {"new_findings": [], "fixes_applied": []}
        result, warnings = validate_harness_output(data, "deep-mode")
        assert "no_new_findings" in result

    def test_dispatches_coverage_unit_test(self):
        data = {"tests_written": []}
        result, warnings = validate_harness_output(
            data, "test-coverage", phase="unit-test"
        )
        assert "no_new_tests" in result

    def test_dispatches_coverage_refactor(self):
        data = {"new_findings": []}
        result, warnings = validate_harness_output(
            data, "test-coverage", phase="refactor"
        )
        assert "no_new_findings" in result

    def test_unknown_harness_type(self):
        data = {"anything": True}
        result, warnings = validate_harness_output(data, "unknown")
        assert warnings == []
        assert result is data
