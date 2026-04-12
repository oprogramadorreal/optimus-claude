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

    def test_schema_validation_fills_defaults(self):
        raw = '```json:harness-output\n{"iteration": 1}\n```'
        result = parse_harness_output(raw, harness_type="deep-mode")
        # Schema validation should have filled defaults
        assert result["new_findings"] == []
        assert result["fixes_applied"] == []
        assert result["no_new_findings"] is False
        assert result["no_actionable_fixes"] is False

    def test_schema_validation_skipped_when_no_type(self):
        raw = '```json:harness-output\n{"iteration": 1}\n```'
        result = parse_harness_output(raw)
        # Without harness_type, no defaults are filled
        assert "new_findings" not in result

    def test_schema_validation_logs_warnings(self, capsys):
        raw = '```json:harness-output\n{"no_new_findings": true}\n```'
        parse_harness_output(raw, harness_type="deep-mode")
        output = capsys.readouterr().out
        assert "Contract warning" in output
