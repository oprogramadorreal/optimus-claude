import pytest
from harness_common.reporting import (
    _SHELL_FENCE_LANGS,
    build_coverage_commit_body,
    build_deep_commit_body,
    detect_test_command,
    format_finding_line,
    format_section,
)


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
        content = "```python\nfoo()\n```\n" "```yaml\ntest: pytest tests/\n```\n"
        assert detect_test_command("/unused", content=content) is None

    def test_finds_command_after_non_shell_block_with_blank_line(self):
        # Regression: when the closing fence of a non-shell block is followed
        # by a blank line and a real shell block, the real block must still
        # be detected (the close fence must not be matched as a spurious
        # untagged opener that empty-spans into the shell block's opener).
        content = "```text\nintro\n```\n" "\n" "```bash\npytest\n```\n"
        assert detect_test_command("/unused", content=content) == "pytest"

    def test_skips_first_block_without_token_to_second(self):
        content = (
            "```bash\necho 'install steps'\n```\n" "\n" "```bash\npytest -v\n```\n"
        )
        assert detect_test_command("/unused", content=content) == "pytest -v"

    def test_two_adjacent_untagged_blocks_finds_token_in_second(self):
        # The +? quantifier + (?!```) lookahead must let the loop find the
        # token in block 2 even with no blank line between blocks.
        content = "```\nfoo\n```\n```\npytest\n```\n"
        assert detect_test_command("/unused", content=content) == "pytest"

    def test_inline_form_wins_over_fenced_block(self):
        content = "test command: `inline-cmd`\n" "\n" "```bash\npytest\n```\n"
        assert detect_test_command("/unused", content=content) == "inline-cmd"

    def test_stray_backticks_in_body_do_not_abort_match(self):
        # Single backticks in the body (e.g. shell command substitution)
        # must not trip the embedded-fence guard, which targets ``` only.
        content = "```bash\necho `pwd`\npytest\n```\n"
        assert detect_test_command("/unused", content=content) == "pytest"


class TestFormatFindingLine:
    def test_basic_shape(self):
        line = format_finding_line(
            {
                "file": "src/auth.py",
                "line": 42,
                "category": "Bug",
                "summary": "Null check missing",
            }
        )
        assert line == "- src/auth.py:42 [Bug] Null check missing"

    def test_summary_longer_than_72_is_truncated_with_ellipsis(self):
        summary = "x" * 100
        line = format_finding_line(
            {"file": "f.py", "line": 1, "category": "C", "summary": summary}
        )
        # 69 chars then "..." — 72 chars total after the truncation slice.
        assert "x" * 69 + "..." in line
        # The full 100-char body must not survive verbatim.
        assert "x" * 100 not in line

    def test_summary_at_exactly_72_chars_is_not_truncated(self):
        summary = "x" * 72
        line = format_finding_line(
            {"file": "f.py", "line": 1, "category": "C", "summary": summary}
        )
        assert summary in line
        assert "..." not in line

    def test_missing_line_renders_question_mark(self):
        line = format_finding_line({"file": "f.py", "category": "Bug", "summary": "x"})
        assert "f.py:?" in line

    def test_newlines_in_summary_are_stripped(self):
        # Multi-line summaries must collapse to one line so the commit body
        # stays parseable by tools that split on newlines.
        line = format_finding_line(
            {
                "file": "f.py",
                "line": 1,
                "category": "Bug",
                "summary": "first line\nsecond line\r\nthird",
            }
        )
        assert "\n" not in line
        assert "\r" not in line
        assert "first line second line third" in line


class TestFormatSection:
    def test_empty_items_returns_empty_list(self):
        assert format_section("Fixed:", []) == []

    def test_single_item_includes_header_and_trailing_blank(self):
        result = format_section(
            "Fixed:",
            [{"file": "a.py", "line": 1, "category": "Bug", "summary": "x"}],
        )
        assert result[0] == "Fixed:"
        # Body line + trailing blank line for readability in the commit message.
        assert result[-1] == ""

    def test_overflow_appends_and_n_more(self):
        items = [
            {"file": f"a{i}.py", "line": i, "category": "Bug", "summary": "x"}
            for i in range(15)
        ]
        result = format_section("Fixed:", items, max_entries=10)
        # 10 displayed items + "... and 5 more" overflow line.
        overflow_lines = [line for line in result if "and 5 more" in line]
        assert overflow_lines == ["- ... and 5 more"]

    def test_no_overflow_line_when_below_max_entries(self):
        items = [{"file": "a.py", "line": 1, "category": "Bug", "summary": "x"}]
        result = format_section("Fixed:", items, max_entries=10)
        assert not any("and " in line and " more" in line for line in result)


class TestBuildDeepCommitBody:
    def _finding(self, **overrides):
        base = {
            "file": "a.py",
            "line": 1,
            "category": "Bug",
            "summary": "x",
            "status": "fixed",
            "iteration_last_attempted": 1,
        }
        base.update(overrides)
        return base

    def test_filters_to_current_iteration(self):
        # Only findings whose iteration_last_attempted matches the iteration
        # arg should appear in the commit body — older iterations were
        # already accounted for in earlier checkpoints.
        progress = {
            "findings": [
                self._finding(file="curr.py", iteration_last_attempted=2),
                self._finding(file="prev.py", iteration_last_attempted=1),
            ]
        }
        body = build_deep_commit_body(progress, iteration=2)
        assert "curr.py" in body
        assert "prev.py" not in body

    def test_partitions_into_fixed_reverted_persistent_sections(self):
        progress = {
            "findings": [
                self._finding(file="f.py", status="fixed"),
                self._finding(file="r.py", status="reverted — test failure"),
                self._finding(file="p.py", status="persistent — fix failed"),
            ]
        }
        body = build_deep_commit_body(progress, iteration=1)
        assert "Fixed:" in body
        assert "Reverted (test failure):" in body
        assert "Persistent (all attempts failed):" in body
        # Each finding appears under its own section, not duplicated across.
        assert body.count("f.py:") == 1
        assert body.count("r.py:") == 1
        assert body.count("p.py:") == 1

    def test_no_iteration_findings_returns_empty(self):
        progress = {"findings": [self._finding(iteration_last_attempted=5)]}
        # No matching iteration_last_attempted → empty body so the caller
        # falls back to title-only commit (cli.py:902).
        assert build_deep_commit_body(progress, iteration=1) == ""


class TestBuildCoverageCommitBody:
    def test_unit_test_phase_lists_tests_with_target_and_count(self):
        progress = {
            "tests_created": [
                {
                    "file": "test_a.py",
                    "target_file": "a.py",
                    "test_count": 5,
                    "cycle": 1,
                }
            ]
        }
        body = build_coverage_commit_body(progress, cycle=1, phase="unit-test")
        assert "Tests written:" in body
        assert "test_a.py → a.py (5 tests)" in body

    def test_unit_test_phase_filters_by_cycle(self):
        progress = {
            "tests_created": [
                {
                    "file": "current.py",
                    "target_file": "x.py",
                    "test_count": 1,
                    "cycle": 2,
                },
                {
                    "file": "older.py",
                    "target_file": "y.py",
                    "test_count": 1,
                    "cycle": 1,
                },
            ]
        }
        body = build_coverage_commit_body(progress, cycle=2, phase="unit-test")
        assert "current.py" in body
        assert "older.py" not in body

    def test_refactor_phase_partitions_fixed_and_reverted(self):
        progress = {
            "refactor_findings": [
                {
                    "file": "f.py",
                    "line": 10,
                    "category": "Testability",
                    "summary": "extract helper",
                    "status": "fixed",
                    "cycle": 1,
                },
                {
                    "file": "r.py",
                    "line": 20,
                    "category": "Testability",
                    "summary": "split function",
                    "status": "reverted — test failure",
                    "cycle": 1,
                },
            ]
        }
        body = build_coverage_commit_body(progress, cycle=1, phase="refactor")
        assert "Testability fixes applied:" in body
        assert "f.py:10" in body
        assert "Reverted (test failure):" in body
        assert "r.py:20" in body

    def test_refactor_phase_with_no_findings_returns_minimal_body(self):
        progress = {"refactor_findings": []}
        body = build_coverage_commit_body(progress, cycle=1, phase="refactor")
        # Header line is still emitted so commits remain consistent in shape.
        assert "Coverage orchestrator checkpoint" in body
