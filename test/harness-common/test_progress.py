import datetime
import json

from harness_common.constants import BACKUP_SUFFIX
from harness_common.progress import (
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
        # Parsing enforces the exact ISO-8601 UTC shape contractually
        # documented for this field; weaker checks let non-UTC or
        # malformed values slip through.
        datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
