import pytest

from harness_common.reporting import _SHELL_FENCE_LANGS, detect_test_command


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

    def test_testing_keyword_pattern(self):
        content = "testing: `make test`\n"
        assert detect_test_command("/unused", content=content) == "make test"

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

    @pytest.mark.parametrize("lang", [*_SHELL_FENCE_LANGS, ""])
    def test_shell_fence_languages(self, lang):
        content = f"```{lang}\npytest\n```\n"
        assert detect_test_command("/unused", content=content) == "pytest"

    def test_powershell_code_block_with_inline_comments(self):
        content = (
            "```powershell\n"
            "pip install -r requirements.txt          # Install dependencies\n"
            "pytest                                    # Run tests\n"
            "```\n"
        )
        assert detect_test_command("/unused", content=content) == "pytest"

    def test_powershell_block_skips_comment_lines(self):
        content = "```powershell\n# install\npytest\n```\n"
        assert detect_test_command("/unused", content=content) == "pytest"

    @pytest.mark.parametrize("lang", ["python", "yaml", "dockerfile"])
    def test_non_shell_fence_languages_are_ignored(self, lang):
        content = f"```{lang}\nfoo: pytest tests/\n```\n"
        assert detect_test_command("/unused", content=content) is None

    def test_does_not_span_two_adjacent_non_shell_blocks(self):
        # The closing fence of block 1 must not be mis-read as an untagged
        # opening fence whose body spans into block 2.
        content = (
            "```python\nfoo()\n```\n"
            "```yaml\ntest: pytest tests/\n```\n"
        )
        assert detect_test_command("/unused", content=content) is None

    def test_finds_command_after_non_shell_block_with_blank_line(self):
        # Regression: when the closing fence of a non-shell block is followed
        # by a blank line and a real shell block, the real block must still
        # be detected (the close fence must not be matched as a spurious
        # untagged opener that empty-spans into the shell block's opener).
        content = (
            "```text\nintro\n```\n"
            "\n"
            "```bash\npytest\n```\n"
        )
        assert detect_test_command("/unused", content=content) == "pytest"

    def test_skips_first_block_without_token_to_second(self):
        content = (
            "```bash\necho 'install steps'\n```\n"
            "\n"
            "```bash\npytest -v\n```\n"
        )
        assert detect_test_command("/unused", content=content) == "pytest -v"

    def test_two_adjacent_untagged_blocks_finds_token_in_second(self):
        # The +? quantifier + (?!```) lookahead must let the loop find the
        # token in block 2 even with no blank line between blocks.
        content = "```\nfoo\n```\n```\npytest\n```\n"
        assert detect_test_command("/unused", content=content) == "pytest"

    def test_inline_form_wins_over_fenced_block(self):
        content = (
            "test command: `inline-cmd`\n"
            "\n"
            "```bash\npytest\n```\n"
        )
        assert detect_test_command("/unused", content=content) == "inline-cmd"

    def test_stray_backticks_in_body_do_not_abort_match(self):
        # Single backticks in the body (e.g. shell command substitution)
        # must not trip the embedded-fence guard, which targets ``` only.
        content = "```bash\necho `pwd`\npytest\n```\n"
        assert detect_test_command("/unused", content=content) == "pytest"
