import json

from harness_common.parser import parse_harness_output


class TestParseHarnessOutput:
    def test_none_input(self):
        assert parse_harness_output(None) is None

    def test_empty_string(self):
        assert parse_harness_output("") is None

    def test_no_json_block(self):
        assert parse_harness_output("some random text") is None

    def test_valid_json_block(self):
        raw = '```json:harness-output\n{"iteration": 1, "no_new_findings": false}\n```'
        result = parse_harness_output(raw)
        assert result == {"iteration": 1, "no_new_findings": False}

    def test_json_block_with_surrounding_text(self):
        raw = (
            "Some analysis...\n"
            '```json:harness-output\n{"iteration": 2}\n```\n'
            "Done."
        )
        result = parse_harness_output(raw)
        assert result == {"iteration": 2}

    def test_envelope_format(self):
        inner = '```json:harness-output\n{"iteration": 1}\n```'
        envelope = json.dumps({"result": inner})
        result = parse_harness_output(envelope)
        assert result == {"iteration": 1}

    def test_invalid_json_in_block(self):
        raw = "```json:harness-output\n{invalid json}\n```"
        assert parse_harness_output(raw) is None

    def test_envelope_with_non_string_result(self):
        envelope = json.dumps({"result": 42})
        assert parse_harness_output(envelope) is None

    def test_envelope_without_result_key(self):
        envelope = json.dumps({"data": "something"})
        assert parse_harness_output(envelope) is None


class TestParseWithSchemaValidation:
    def test_fills_defaults_when_harness_type_provided(self):
        raw = '```json:harness-output\n{"new_findings": []}\n```'
        result = parse_harness_output(raw, harness_type="deep-mode")
        assert result["no_new_findings"] is False
        assert result["fixes_applied"] == []

    def test_no_validation_without_harness_type(self):
        raw = '```json:harness-output\n{"custom": true}\n```'
        result = parse_harness_output(raw)
        assert result == {"custom": True}

    def test_warnings_printed_to_stderr(self, capsys):
        raw = '```json:harness-output\n{"new_findings": "bad"}\n```'
        result = parse_harness_output(raw, harness_type="deep-mode")
        assert result["new_findings"] == []
        captured = capsys.readouterr()
        assert "Contract warning" in captured.err

    def test_coverage_unit_test_validation(self):
        raw = '```json:harness-output\n{"tests_written": []}\n```'
        result = parse_harness_output(
            raw, harness_type="test-coverage", phase="unit-test"
        )
        assert result["no_new_tests"] is False
        assert "coverage" in result
