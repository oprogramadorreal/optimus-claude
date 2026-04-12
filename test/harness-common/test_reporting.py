import json

from harness_common.reporting import (
    build_json_summary,
    detect_test_command,
    write_json_summary,
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


class TestBuildJsonSummary:
    def _deep_mode_progress(self):
        return {
            "skill": "code-review",
            "iteration": {"current": 3, "completed": 3},
            "findings": [
                {"status": "fixed"},
                {"status": "fixed"},
                {"status": "reverted — test failure"},
                {"status": "persistent — fix failed"},
            ],
            "test_results": {"last_full_run": "pass"},
            "termination": {"reason": "convergence", "message": "zero findings"},
            "total_elapsed_seconds": 300,
        }

    def _coverage_progress(self):
        return {
            "cycle": {"current": 2, "completed": 2},
            "coverage": {"baseline": 40, "current": 65},
            "tests_created": [
                {"test_count": 3, "cycle": 1},
                {"test_count": 5, "cycle": 2},
            ],
            "refactor_findings": [
                {"status": "fixed"},
                {"status": "reverted — test failure"},
            ],
            "test_results": {"last_full_run": "pass"},
            "termination": {"reason": "cap", "message": "cycle cap"},
            "total_elapsed_seconds": 600,
        }

    def test_deep_mode_summary(self):
        summary = build_json_summary(self._deep_mode_progress(), "deep-mode")
        assert summary["harness"] == "deep-mode"
        assert summary["skill"] == "code-review"
        assert summary["iterations_completed"] == 3
        assert summary["findings"]["fixed"] == 2
        assert summary["findings"]["reverted"] == 1
        assert summary["findings"]["persistent"] == 1
        assert summary["test_status"] == "pass"
        assert summary["total_elapsed_seconds"] == 300

    def test_coverage_summary(self):
        summary = build_json_summary(self._coverage_progress(), "test-coverage")
        assert summary["harness"] == "test-coverage"
        assert summary["cycles_completed"] == 2
        assert summary["coverage"] == {"baseline": 40, "current": 65}
        assert summary["tests_created"] == 8
        assert summary["testability_fixes"] == 1
        assert summary["total_elapsed_seconds"] == 600

    def test_empty_progress(self):
        summary = build_json_summary({}, "deep-mode")
        assert summary["harness"] == "deep-mode"
        assert summary["skill"] == "unknown"
        assert summary["iterations_completed"] == 0
        assert summary["findings"]["fixed"] == 0


class TestWriteJsonSummary:
    def test_writes_valid_json(self, tmp_path):
        progress = {
            "skill": "refactor",
            "iteration": {"completed": 1},
            "findings": [],
            "test_results": {"last_full_run": "pass"},
            "termination": {"reason": None, "message": None},
            "total_elapsed_seconds": 0,
        }
        path = tmp_path / "summary.json"
        write_json_summary(progress, "deep-mode", path)
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["harness"] == "deep-mode"

    def test_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "nested" / "dir" / "summary.json"
        write_json_summary({}, "test-coverage", path)
        assert path.exists()
