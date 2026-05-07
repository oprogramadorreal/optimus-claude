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

    def test_powershell_code_block(self):
        content = (
            "```powershell\n"
            "pip install -r requirements.txt          # Install dependencies\n"
            "pytest                                    # Run tests\n"
            "```\n"
        )
        assert detect_test_command("/unused", content=content) == "pytest"

    def test_pwsh_code_block(self):
        content = "```pwsh\npytest\n```\n"
        assert detect_test_command("/unused", content=content) == "pytest"

    def test_cmd_code_block(self):
        content = "```cmd\npytest\n```\n"
        assert detect_test_command("/unused", content=content) == "pytest"

    def test_console_code_block(self):
        content = "```console\npytest -v\n```\n"
        assert detect_test_command("/unused", content=content) == "pytest -v"

    def test_shell_code_block(self):
        content = "```shell\nnpm test\n```\n"
        assert detect_test_command("/unused", content=content) == "npm test"

    def test_untagged_code_block(self):
        content = "```\npytest\n```\n"
        assert detect_test_command("/unused", content=content) == "pytest"

    def test_python_code_block_is_ignored(self):
        content = '```python\nsubprocess.run(["pytest"])\n```\n'
        assert detect_test_command("/unused", content=content) is None

    def test_powershell_block_skips_comment_lines(self):
        content = "```powershell\n# install\npytest\n```\n"
        assert detect_test_command("/unused", content=content) == "pytest"
