import json

from harness_common.constants import BACKUP_SUFFIX
from harness_common.progress import (
    prune_resolved_findings,
    read_progress,
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


class TestPruneResolvedFindings:
    def test_archives_old_fixed_findings(self):
        progress = {
            "findings": [
                {"status": "fixed", "iteration_last_attempted": 1, "file": "a.py"},
                {"status": "fixed", "iteration_last_attempted": 3, "file": "b.py"},
                {
                    "status": "reverted — test failure",
                    "iteration_last_attempted": 1,
                    "file": "c.py",
                },
            ]
        }
        prune_resolved_findings(progress, current_iteration=5, archive_after=3)
        # a.py was fixed at iter 1, now iter 5, gap=4 >= 3 → archived
        # b.py was fixed at iter 3, now iter 5, gap=2 < 3 → stays
        # c.py is reverted (not fixed) → stays
        assert len(progress["findings"]) == 2
        assert progress["findings"][0]["file"] == "b.py"
        assert progress["findings"][1]["file"] == "c.py"
        assert len(progress["archived_findings"]) == 1
        assert progress["archived_findings"][0]["file"] == "a.py"

    def test_no_findings_key(self):
        progress = {}
        prune_resolved_findings(progress, current_iteration=5)
        assert "findings" not in progress

    def test_nothing_to_archive(self):
        progress = {
            "findings": [
                {"status": "fixed", "iteration_last_attempted": 4, "file": "a.py"},
            ]
        }
        prune_resolved_findings(progress, current_iteration=5, archive_after=3)
        assert len(progress["findings"]) == 1
        assert "archived_findings" in progress
        assert len(progress["archived_findings"]) == 0

    def test_retained_status_also_archives(self):
        progress = {
            "findings": [
                {
                    "status": "retained — revert failed",
                    "iteration_last_attempted": 1,
                    "file": "a.py",
                },
            ]
        }
        prune_resolved_findings(progress, current_iteration=5, archive_after=3)
        assert len(progress["findings"]) == 0
        assert len(progress["archived_findings"]) == 1


class TestTrimScopeFiles:
    def test_no_trim_under_limit(self):
        progress = {
            "findings": [],
            "scope_files": {"current": ["a.py", "b.py"]},
        }
        trim_scope_files(progress, max_files=10)
        assert progress["scope_files"]["current"] == ["a.py", "b.py"]

    def test_trims_to_max(self):
        files = [f"file{i}.py" for i in range(50)]
        progress = {
            "findings": [],
            "scope_files": {"current": files},
        }
        trim_scope_files(progress, max_files=10)
        assert len(progress["scope_files"]["current"]) == 10

    def test_finding_files_kept_first(self):
        files = [f"file{i}.py" for i in range(20)]
        progress = {
            "findings": [
                {"file": "file15.py"},
                {"file": "file18.py"},
            ],
            "scope_files": {"current": files},
        }
        trim_scope_files(progress, max_files=5)
        result = progress["scope_files"]["current"]
        assert len(result) == 5
        assert "file15.py" in result
        assert "file18.py" in result

    def test_empty_scope(self):
        progress = {
            "findings": [],
            "scope_files": {"current": []},
        }
        trim_scope_files(progress, max_files=10)
        assert progress["scope_files"]["current"] == []
