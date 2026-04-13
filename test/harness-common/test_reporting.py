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
    def test_deep_mode_summary(self):
        progress = {
            "skill": "code-review",
            "iteration": {"current": 4, "completed": 3},
            "findings": [
                {"status": "fixed"},
                {"status": "reverted — test failure"},
                {"status": "persistent — fix failed"},
            ],
            "test_results": {"last_full_run": "pass"},
            "total_elapsed_seconds": 120.5,
        }
        result = build_json_summary(progress, "deep-mode")
        assert result["harness"] == "deep-mode"
        assert result["skill"] == "code-review"
        assert result["iterations_completed"] == 3
        assert result["findings"]["fixed"] == 1
        assert result["findings"]["reverted"] == 1
        assert result["findings"]["persistent"] == 1
        assert result["test_status"] == "pass"
        assert result["total_elapsed_seconds"] == 120.5

    def test_coverage_summary(self):
        progress = {
            "cycle": {"current": 3, "completed": 2},
            "coverage": {"baseline": 40, "current": 55},
            "tests_created": [{"file": "t1.py"}, {"file": "t2.py"}],
            "test_results": {"last_full_run": "pass"},
            "total_elapsed_seconds": 60,
        }
        result = build_json_summary(progress, "test-coverage")
        assert result["harness"] == "test-coverage"
        assert result["cycles_completed"] == 2
        assert result["coverage"]["baseline"] == 40
        assert result["tests_created"] == 2

    def test_terminated_status(self):
        progress = {
            "skill": "refactor",
            "iteration": {"completed": 1},
            "findings": [],
            "test_results": {},
            "termination": {"reason": "crash", "message": "Session failed"},
        }
        result = build_json_summary(progress, "deep-mode")
        assert result["status"] == "crash"
        assert result["termination_message"] == "Session failed"


class TestWriteJsonSummary:
    def test_writes_file(self, tmp_path):
        progress = {
            "skill": "code-review",
            "iteration": {"completed": 2},
            "findings": [],
            "test_results": {"last_full_run": "pass"},
        }
        path = tmp_path / "summary.json"
        write_json_summary(progress, "deep-mode", path)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["harness"] == "deep-mode"

    def test_creates_parent_dirs(self, tmp_path):
        progress = {
            "skill": "refactor",
            "iteration": {"completed": 1},
            "findings": [],
            "test_results": {},
        }
        path = tmp_path / "nested" / "dir" / "summary.json"
        write_json_summary(progress, "deep-mode", path)
        assert path.exists()
