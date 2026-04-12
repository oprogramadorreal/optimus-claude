from harness_common.schema import (
    validate_coverage_unit_test_output,
    validate_deep_mode_output,
    validate_harness_output,
)

# ---------------------------------------------------------------------------
# validate_deep_mode_output
# ---------------------------------------------------------------------------


class TestValidateDeepModeOutput:
    def test_valid_output(self):
        data = {
            "new_findings": [
                {
                    "file": "src/app.py",
                    "line": 10,
                    "category": "bug",
                    "pre_edit_content": "old",
                    "post_edit_content": "new",
                }
            ],
            "fixes_applied": [],
            "no_new_findings": False,
            "no_actionable_fixes": False,
        }
        normalized, warnings = validate_deep_mode_output(data)
        assert warnings == []
        assert normalized["no_new_findings"] is False

    def test_missing_fields_get_defaults(self):
        data = {}
        normalized, warnings = validate_deep_mode_output(data)
        assert normalized["new_findings"] == []
        assert normalized["fixes_applied"] == []
        assert normalized["no_new_findings"] is False
        assert normalized["no_actionable_fixes"] is False
        assert len(warnings) == 4

    def test_wrong_type_gets_default(self):
        data = {
            "new_findings": "not a list",
            "fixes_applied": [],
            "no_new_findings": False,
            "no_actionable_fixes": False,
        }
        normalized, warnings = validate_deep_mode_output(data)
        assert normalized["new_findings"] == []
        assert any("expected list" in w for w in warnings)

    def test_finding_missing_file(self):
        data = {
            "new_findings": [
                {
                    "line": 10,
                    "category": "bug",
                    "pre_edit_content": "old",
                    "post_edit_content": "new",
                }
            ],
            "fixes_applied": [],
            "no_new_findings": False,
            "no_actionable_fixes": False,
        }
        _normalized, warnings = validate_deep_mode_output(data)
        assert any("missing or empty 'file'" in w for w in warnings)

    def test_finding_missing_pre_edit(self):
        data = {
            "new_findings": [
                {
                    "file": "src/app.py",
                    "line": 10,
                    "category": "bug",
                    "post_edit_content": "new",
                }
            ],
            "fixes_applied": [],
            "no_new_findings": False,
            "no_actionable_fixes": False,
        }
        _normalized, warnings = validate_deep_mode_output(data)
        assert any("missing 'pre_edit_content'" in w for w in warnings)

    def test_finding_missing_post_edit(self):
        data = {
            "new_findings": [
                {
                    "file": "src/app.py",
                    "line": 10,
                    "category": "bug",
                    "pre_edit_content": "old",
                }
            ],
            "fixes_applied": [],
            "no_new_findings": False,
            "no_actionable_fixes": False,
        }
        _normalized, warnings = validate_deep_mode_output(data)
        assert any("missing 'post_edit_content'" in w for w in warnings)

    def test_non_dict_input(self):
        data, warnings = validate_deep_mode_output("not a dict")
        assert any("not a JSON object" in w for w in warnings)

    def test_finding_non_int_line(self):
        data = {
            "new_findings": [
                {
                    "file": "src/app.py",
                    "line": "ten",
                    "category": "bug",
                    "pre_edit_content": "old",
                    "post_edit_content": "new",
                }
            ],
            "fixes_applied": [],
            "no_new_findings": False,
            "no_actionable_fixes": False,
        }
        _normalized, warnings = validate_deep_mode_output(data)
        assert any("'line' should be int" in w for w in warnings)

    def test_fixes_applied_also_validated(self):
        data = {
            "new_findings": [],
            "fixes_applied": [
                {
                    "line": 5,
                    "category": "style",
                    "pre_edit_content": "a",
                    "post_edit_content": "b",
                }
            ],
            "no_new_findings": True,
            "no_actionable_fixes": False,
        }
        _normalized, warnings = validate_deep_mode_output(data)
        assert any("missing or empty 'file'" in w for w in warnings)


# ---------------------------------------------------------------------------
# validate_coverage_unit_test_output
# ---------------------------------------------------------------------------


class TestValidateCoverageUnitTestOutput:
    def test_valid_output(self):
        data = {
            "tests_written": [{"file": "test_a.py"}],
            "coverage": {"before": 40, "after": 55, "delta": 15},
            "no_new_tests": False,
            "no_untestable_code": True,
            "no_coverage_gained": False,
        }
        normalized, warnings = validate_coverage_unit_test_output(data)
        assert warnings == []
        assert normalized["no_new_tests"] is False

    def test_missing_fields_get_defaults(self):
        data = {}
        normalized, warnings = validate_coverage_unit_test_output(data)
        assert normalized["tests_written"] == []
        assert normalized["coverage"] == {}
        assert normalized["no_new_tests"] is False
        assert len(warnings) >= 4

    def test_coverage_missing_subfields(self):
        data = {
            "tests_written": [],
            "coverage": {},
            "no_new_tests": True,
            "no_untestable_code": True,
            "no_coverage_gained": True,
        }
        _normalized, warnings = validate_coverage_unit_test_output(data)
        assert any("coverage.before missing" in w for w in warnings)
        assert any("coverage.after missing" in w for w in warnings)
        assert any("coverage.delta missing" in w for w in warnings)

    def test_non_dict_input(self):
        _data, warnings = validate_coverage_unit_test_output([1, 2, 3])
        assert any("not a JSON object" in w for w in warnings)


# ---------------------------------------------------------------------------
# validate_harness_output (dispatch)
# ---------------------------------------------------------------------------


class TestValidateHarnessOutput:
    def test_dispatch_deep_mode(self):
        data = {
            "new_findings": [],
            "fixes_applied": [],
            "no_new_findings": True,
            "no_actionable_fixes": True,
        }
        _normalized, warnings = validate_harness_output(data, "deep-mode")
        assert warnings == []

    def test_dispatch_coverage_unit_test(self):
        data = {
            "tests_written": [],
            "coverage": {"before": 0, "after": 0, "delta": 0},
            "no_new_tests": True,
            "no_untestable_code": True,
            "no_coverage_gained": True,
        }
        _normalized, warnings = validate_harness_output(
            data, "coverage", phase="unit-test"
        )
        assert warnings == []

    def test_dispatch_coverage_refactor(self):
        data = {
            "new_findings": [],
            "fixes_applied": [],
            "no_new_findings": True,
            "no_actionable_fixes": True,
        }
        _normalized, warnings = validate_harness_output(
            data, "coverage", phase="refactor"
        )
        assert warnings == []

    def test_unknown_harness_type(self):
        _data, warnings = validate_harness_output({}, "unknown-harness")
        assert any("Unknown harness type" in w for w in warnings)
