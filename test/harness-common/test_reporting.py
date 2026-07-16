from harness_common.reporting import (
    build_coverage_commit_body,
    build_deep_commit_body,
    format_finding_line,
    format_section,
)


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

    def test_missing_file_renders_question_mark(self):
        # Regression for e60aa78: the defensive `finding.get('file', '?')`
        # branch had no test, so reverting to `finding['file']` would have
        # passed every other case.
        line = format_finding_line({"line": 1, "category": "Bug", "summary": "x"})
        assert "?:1" in line

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
