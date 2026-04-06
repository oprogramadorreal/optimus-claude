from harness_common.reporting import detect_test_command


class TestDetectTestCommand:
    def test_bash_code_block(self, claude_md_dir):
        result = detect_test_command(claude_md_dir)
        assert result == "npm test"

    def test_no_claude_md(self, tmp_path):
        assert detect_test_command(tmp_path) is None

    def test_inline_backtick_pattern(self):
        content = "test command: `pytest --tb=short`\n"
        assert detect_test_command("/unused", content=content) == "pytest --tb=short"

    def test_run_tests_pattern(self):
        content = "run tests: `cargo test`\n"
        assert detect_test_command("/unused", content=content) == "cargo test"

    def test_strips_trailing_comment(self):
        content = "test command: `npm test # Run unit tests`\n"
        assert detect_test_command("/unused", content=content) == "npm test"

    def test_code_block_with_comment_line(self):
        content = "```bash\n# setup\nnpm test\n```\n"
        assert detect_test_command("/unused", content=content) == "npm test"

    def test_code_block_skips_comment_only_lines(self):
        content = "```bash\n# This is a comment\npytest\n```\n"
        assert detect_test_command("/unused", content=content) == "pytest"

    def test_no_test_command_found(self):
        content = "# Project\n\nJust some docs.\n"
        assert detect_test_command("/unused", content=content) is None

    def test_content_parameter_skips_filesystem(self):
        content = "test command: `go test ./...`\n"
        result = detect_test_command("/nonexistent/path", content=content)
        assert result == "go test ./..."
