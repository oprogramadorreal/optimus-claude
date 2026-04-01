import json

from impl.parser import parse_harness_output


class TestParseHarnessOutput:
    def test_valid_json_block(self):
        raw = '```json:harness-output\n{"iteration": 1, "new_findings": []}\n```'
        result = parse_harness_output(raw)
        assert result == {"iteration": 1, "new_findings": []}

    def test_json_envelope_with_result(self):
        inner = '```json:harness-output\n{"iteration": 2}\n```'
        envelope = json.dumps({"result": inner})
        result = parse_harness_output(envelope)
        assert result == {"iteration": 2}

    def test_missing_block(self):
        assert parse_harness_output("No JSON here") is None

    def test_malformed_json(self):
        raw = '```json:harness-output\n{not valid json}\n```'
        assert parse_harness_output(raw) is None

    def test_empty_input(self):
        assert parse_harness_output("") is None
        assert parse_harness_output(None) is None

    def test_block_with_surrounding_text(self):
        raw = (
            "Some analysis text here.\n\n"
            '```json:harness-output\n{"no_new_findings": true}\n```\n\n'
            "More text after."
        )
        result = parse_harness_output(raw)
        assert result == {"no_new_findings": True}

    def test_non_string_result_in_envelope(self):
        envelope = json.dumps({"result": 42})
        assert parse_harness_output(envelope) is None

    def test_non_dict_envelope(self):
        raw = json.dumps([1, 2, 3])
        assert parse_harness_output(raw) is None
