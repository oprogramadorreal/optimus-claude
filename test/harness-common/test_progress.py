import json

from harness_common.constants import BACKUP_SUFFIX
from harness_common.progress import (
    format_elapsed,
    read_progress,
    record_timing,
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
        progress = {"timing": [], "total_elapsed_seconds": 0}
        record_timing(progress, "iteration-1", 42)
        assert progress["timing"] == [{"label": "iteration-1", "elapsed_s": 42}]
        assert progress["total_elapsed_seconds"] == 42

    def test_accumulates_total(self):
        progress = {"timing": [], "total_elapsed_seconds": 0}
        record_timing(progress, "iteration-1", 100)
        record_timing(progress, "iteration-2", 50)
        assert len(progress["timing"]) == 2
        assert progress["total_elapsed_seconds"] == 150

    def test_initializes_missing_keys(self):
        progress = {}
        record_timing(progress, "iteration-1", 30)
        assert progress["timing"] == [{"label": "iteration-1", "elapsed_s": 30}]
        assert progress["total_elapsed_seconds"] == 30

    def test_handles_existing_total(self):
        progress = {
            "timing": [{"label": "old", "elapsed_s": 10}],
            "total_elapsed_seconds": 10,
        }
        record_timing(progress, "new", 20)
        assert progress["total_elapsed_seconds"] == 30
        assert len(progress["timing"]) == 2


class TestFormatElapsed:
    def test_seconds_only(self):
        assert format_elapsed(45) == "45s"

    def test_minutes_and_seconds(self):
        assert format_elapsed(125) == "2m 5s"

    def test_zero(self):
        assert format_elapsed(0) == "0s"

    def test_exact_minute(self):
        assert format_elapsed(60) == "1m 0s"

    def test_large_value(self):
        assert format_elapsed(3661) == "61m 1s"

    def test_float_truncated(self):
        assert format_elapsed(45.7) == "45s"
