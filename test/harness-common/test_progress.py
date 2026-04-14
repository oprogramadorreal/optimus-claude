import json

from harness_common.constants import BACKUP_SUFFIX
from harness_common.progress import (
    check_progress_size,
    format_elapsed,
    prune_resolved_findings,
    read_progress,
    record_timing,
    trim_scope_files,
    write_progress,
)


class TestWriteProgress:
    def test_creates_file(self, tmp_path):
        path = tmp_path / "progress.json"
        write_progress(path, {"key": "value"})
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data == {"key": "value"}

    def test_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "nested" / "dir" / "progress.json"
        write_progress(path, {"nested": True})
        assert path.exists()

    def test_creates_backup(self, tmp_path):
        path = tmp_path / "progress.json"
        write_progress(path, {"v": 1})
        write_progress(path, {"v": 2})
        backup = tmp_path / ("progress.json" + BACKUP_SUFFIX)
        assert backup.exists()
        backup_data = json.loads(backup.read_text(encoding="utf-8"))
        assert backup_data == {"v": 1}

    def test_no_backup_on_first_write(self, tmp_path):
        path = tmp_path / "progress.json"
        write_progress(path, {"first": True})
        backup = tmp_path / ("progress.json" + BACKUP_SUFFIX)
        assert not backup.exists()

    def test_trailing_newline(self, tmp_path):
        path = tmp_path / "progress.json"
        write_progress(path, {})
        content = path.read_text(encoding="utf-8")
        assert content.endswith("\n")


class TestReadProgress:
    def test_round_trip(self, tmp_path):
        path = tmp_path / "progress.json"
        original = {"schema_version": 1, "data": [1, 2, 3]}
        write_progress(path, original)
        loaded = read_progress(path)
        assert loaded == original

    def test_reads_valid_json(self, tmp_path):
        path = tmp_path / "progress.json"
        path.write_text('{"key": "value"}', encoding="utf-8")
        assert read_progress(path) == {"key": "value"}


class TestRecordTiming:
    def test_appends_entry(self):
        progress = {}
        record_timing(progress, "iteration-1", 12.345)
        assert len(progress["timing"]) == 1
        assert progress["timing"][0]["label"] == "iteration-1"
        assert progress["timing"][0]["elapsed_seconds"] == 12.35
        assert progress["total_elapsed_seconds"] == 12.35

    def test_accumulates_total(self):
        progress = {"timing": [], "total_elapsed_seconds": 10.0}
        record_timing(progress, "iteration-2", 5.5)
        assert progress["total_elapsed_seconds"] == 15.5
        assert len(progress["timing"]) == 1

    def test_creates_timing_list(self):
        progress = {}
        record_timing(progress, "x", 1.0)
        assert "timing" in progress

    def test_timestamp_format(self):
        progress = {}
        record_timing(progress, "x", 1.0)
        ts = progress["timing"][0]["timestamp"]
        # Should be ISO-ish: YYYY-MM-DDTHH:MM:SSZ
        assert "T" in ts and ts.endswith("Z")


class TestFormatElapsed:
    def test_seconds_only(self):
        assert format_elapsed(45) == "45s"

    def test_minutes_and_seconds(self):
        assert format_elapsed(125) == "2m 5s"

    def test_zero(self):
        assert format_elapsed(0) == "0s"

    def test_negative_clamped(self):
        assert format_elapsed(-5) == "0s"

    def test_fractional(self):
        assert format_elapsed(90.7) == "1m 30s"


class TestPruneResolvedFindings:
    def test_archives_old_fixed(self):
        progress = {
            "findings": [
                {"status": "fixed", "iteration_last_attempted": 1},
                {"status": "discovered", "iteration_last_attempted": 4},
            ]
        }
        prune_resolved_findings(progress, 6, archive_after=3)
        assert len(progress["findings"]) == 1
        assert progress["findings"][0]["status"] == "discovered"
        assert len(progress["archived_findings"]) == 1

    def test_keeps_recent_fixed(self):
        progress = {
            "findings": [
                {"status": "fixed", "iteration_last_attempted": 4},
            ]
        }
        prune_resolved_findings(progress, 6, archive_after=3)
        assert len(progress["findings"]) == 1
        assert (
            "archived_findings" not in progress
            or len(progress["archived_findings"]) == 0
        )

    def test_archives_retained(self):
        progress = {
            "findings": [
                {"status": "retained — revert failed", "iteration_last_attempted": 1},
            ]
        }
        prune_resolved_findings(progress, 6, archive_after=3)
        assert len(progress["findings"]) == 0
        assert len(progress["archived_findings"]) == 1

    def test_empty_findings(self):
        progress = {"findings": []}
        prune_resolved_findings(progress, 5)
        assert progress["findings"] == []


class TestTrimScopeFiles:
    def test_no_trim_under_limit(self):
        progress = {"scope_files": {"current": ["a.py", "b.py"]}}
        trim_scope_files(progress, max_files=5)
        assert len(progress["scope_files"]["current"]) == 2

    def test_trims_to_limit(self):
        progress = {"scope_files": {"current": [f"f{i}.py" for i in range(10)]}}
        trim_scope_files(progress, max_files=5)
        assert len(progress["scope_files"]["current"]) == 5

    def test_prioritises_active_findings(self):
        progress = {
            "scope_files": {"current": ["a.py", "b.py", "c.py", "d.py"]},
            "findings": [
                {"file": "c.py", "status": "discovered"},
                {"file": "d.py", "status": "fixed"},  # terminal — not prioritised
            ],
        }
        trim_scope_files(progress, max_files=2)
        result = progress["scope_files"]["current"]
        assert "c.py" in result
        assert len(result) == 2

    def test_missing_scope_files(self):
        progress = {}
        trim_scope_files(progress, max_files=5)  # Should not crash


class TestCheckProgressSize:
    def test_existing_file(self, tmp_path):
        path = tmp_path / "progress.json"
        path.write_text("x" * 200_000, encoding="utf-8")
        size_kb, over = check_progress_size(path, warn_threshold_kb=100)
        assert size_kb > 100
        assert over is True

    def test_small_file(self, tmp_path):
        path = tmp_path / "progress.json"
        path.write_text("{}", encoding="utf-8")
        size_kb, over = check_progress_size(path)
        assert over is False

    def test_missing_file(self, tmp_path):
        size_kb, over = check_progress_size(tmp_path / "nope.json")
        assert size_kb == 0.0
        assert over is False
