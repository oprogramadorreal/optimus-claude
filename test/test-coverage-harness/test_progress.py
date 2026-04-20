from unittest.mock import patch

from impl.progress import (
    make_initial_progress,
    record_cycle_history,
    record_test_result,
)


class TestMakeInitialProgress:
    @patch("impl.progress.git_rev_parse_head", return_value="abc123")
    def test_basic_structure(self, mock_git):
        progress = make_initial_progress(
            scope="src/api",
            max_cycles=5,
            test_command="pytest",
            project_root="/tmp/project",
            started_at="2025-01-01T00:00:00Z",
        )
        assert progress["schema_version"] == 1
        assert progress["harness"] == "test-coverage"
        assert progress["config"]["max_cycles"] == 5
        assert progress["config"]["test_command"] == "pytest"
        assert progress["config"]["scope"] == "src/api"
        assert progress["cycle"]["current"] == 1
        assert progress["phase"] == "unit-test"
        assert progress["coverage"]["baseline"] is None
        assert progress["tests_created"] == []
        assert progress["untestable_code"] == []
        assert progress["timing"] == []
        assert progress["total_elapsed_seconds"] == 0

    @patch("impl.progress.git_rev_parse_head", return_value="def456")
    def test_auto_detects_base_commit(self, mock_git):
        progress = make_initial_progress(
            scope="",
            max_cycles=3,
            test_command="npm test",
            project_root="/project",
            started_at="2025-01-01T00:00:00Z",
        )
        assert progress["config"]["base_commit"] == "def456"
        mock_git.assert_called_once_with("/project")

    def test_explicit_base_commit(self):
        progress = make_initial_progress(
            scope="",
            max_cycles=3,
            test_command="npm test",
            project_root="/project",
            base_commit="explicit123",
            started_at="2025-01-01T00:00:00Z",
        )
        assert progress["config"]["base_commit"] == "explicit123"

    @patch("impl.progress.git_rev_parse_head", return_value="abc")
    def test_auto_timestamp(self, mock_git):
        progress = make_initial_progress(
            scope="",
            max_cycles=3,
            test_command="npm test",
            project_root="/project",
        )
        assert progress["started_at"] is not None
        assert "T" in progress["started_at"]

    @patch("impl.progress.git_rev_parse_head", return_value="abc")
    def test_empty_scope(self, mock_git):
        progress = make_initial_progress(
            scope="",
            max_cycles=3,
            test_command="npm test",
            project_root="/project",
            started_at="2025-01-01T00:00:00Z",
        )
        assert progress["config"]["scope"] == ""


class TestRecordTestResult:
    def test_pass(self, sample_coverage_progress):
        record_test_result(sample_coverage_progress, True, "5 passed")
        assert sample_coverage_progress["test_results"]["last_full_run"] == "pass"
        assert (
            sample_coverage_progress["test_results"]["last_run_output_summary"]
            == "5 passed"
        )

    def test_fail(self, sample_coverage_progress):
        record_test_result(sample_coverage_progress, False, "2 failed")
        assert sample_coverage_progress["test_results"]["last_full_run"] == "fail"


class TestRecordCycleHistory:
    def test_appends_entry(self, sample_coverage_progress):
        ut = {"tests_written": 3, "coverage_delta": 10.0}
        record_cycle_history(sample_coverage_progress, 1, ut)
        assert len(sample_coverage_progress["cycle_history"]) == 1
        entry = sample_coverage_progress["cycle_history"][0]
        assert entry["cycle"] == 1
        assert entry["unit_test"] == ut
        assert "refactor" not in entry
        assert sample_coverage_progress["cycle"]["completed"] == 1

    def test_with_refactor(self, sample_coverage_progress):
        ut = {"tests_written": 2}
        rf = {"findings_count": 1, "fixed": 1}
        record_cycle_history(sample_coverage_progress, 1, ut, rf)
        entry = sample_coverage_progress["cycle_history"][0]
        assert entry["refactor"] == rf
