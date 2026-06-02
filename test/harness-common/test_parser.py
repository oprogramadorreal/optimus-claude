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

    def test_invalid_json_in_block(self):
        raw = "```json:harness-output\n{invalid json}\n```"
        assert parse_harness_output(raw) is None

    def test_returns_last_parseable_block_when_template_echoed(self):
        # The subagent echoed the harness-mode.md template (placeholder
        # values => invalid JSON) before emitting its real block. The last
        # block that parses as valid JSON must win.
        raw = (
            "```json:harness-output\n"
            '{"iteration": <number>, "no_new_findings": <bool>}\n'
            "```\n"
            "...real output below...\n"
            "```json:harness-output\n"
            '{"iteration": 3, "no_new_findings": true}\n'
            "```"
        )
        assert parse_harness_output(raw) == {
            "iteration": 3,
            "no_new_findings": True,
        }

    def test_last_block_wins_when_multiple_valid(self):
        raw = (
            '```json:harness-output\n{"iteration": 1}\n```\n'
            '```json:harness-output\n{"iteration": 2}\n```'
        )
        assert parse_harness_output(raw) == {"iteration": 2}
