import json
from unittest.mock import patch

from impl.findings import generate_finding_id
from impl.progress import (
    make_initial_progress,
    read_progress,
    record_test_result,
    write_progress,
)


class TestGenerateFindingId:
    def test_empty_findings(self, sample_progress):
        assert generate_finding_id(sample_progress) == "f-001"

    def test_sequential(self, sample_progress):
        sample_progress["findings"] = [{"id": "f-001"}, {"id": "f-002"}]
        assert generate_finding_id(sample_progress) == "f-003"

    def test_counts_by_list_length(self, sample_progress):
        """ID is based on list length, not on max existing ID."""
        sample_progress["findings"] = [{"id": "f-001"}, {"id": "f-005"}]
        assert generate_finding_id(sample_progress) == "f-003"

    def test_findings_without_id_field(self, sample_progress):
        sample_progress["findings"] = [{"file": "a.js"}]
        assert generate_finding_id(sample_progress) == "f-002"


class TestRecordTestResult:
    def test_pass(self, sample_progress):
        record_test_result(sample_progress, True, "all passed")
        assert sample_progress["test_results"]["last_full_run"] == "pass"
        assert (
            sample_progress["test_results"]["last_run_output_summary"] == "all passed"
        )

    def test_fail(self, sample_progress):
        record_test_result(sample_progress, False, "2 failed")
        assert sample_progress["test_results"]["last_full_run"] == "fail"


class TestWriteReadProgress:
    def test_round_trip(self, tmp_path, sample_progress):
        path = tmp_path / ".claude" / "progress.json"
        write_progress(path, sample_progress)
        loaded = read_progress(path)
        assert loaded == sample_progress

    def test_creates_parent_dirs(self, tmp_path, sample_progress):
        path = tmp_path / "deep" / "nested" / "progress.json"
        write_progress(path, sample_progress)
        assert path.exists()

    def test_backup_created(self, tmp_path, sample_progress):
        path = tmp_path / "progress.json"
        write_progress(path, sample_progress)
        # Write again — should create backup
        sample_progress["iteration"]["current"] = 2
        write_progress(path, sample_progress)
        backup = tmp_path / "progress.json.bak"
        assert backup.exists()
        backup_data = json.loads(backup.read_text(encoding="utf-8"))
        assert backup_data["iteration"]["current"] == 1


class TestMakeInitialProgress:
    @patch("impl.progress.git_rev_parse_head", return_value="abc123def456")
    def test_basic(self, mock_git, tmp_path):
        progress = make_initial_progress("code-review", "", 8, "npm test", tmp_path)
        assert progress["skill"] == "code-review"
        assert progress["config"]["max_iterations"] == 8
        assert progress["config"]["test_command"] == "npm test"
        assert progress["config"]["base_commit"] == "abc123def456"
        assert progress["iteration"]["current"] == 1
        assert progress["findings"] == []

    @patch("impl.progress.git_rev_parse_head", return_value="abc123def456")
    def test_with_scope(self, mock_git, tmp_path):
        progress = make_initial_progress("refactor", "src/api", 5, "pytest", tmp_path)
        assert progress["config"]["scope"]["mode"] == "directory"
        assert progress["config"]["scope"]["paths"] == ["src/api"]
        assert progress["scope_files"]["current"] == ["src/api"]
