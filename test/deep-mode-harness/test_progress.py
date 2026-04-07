import json
from unittest.mock import patch

from impl.findings import generate_finding_id
from impl.progress import (
    make_initial_progress,
    migrate_progress,
    read_progress,
    record_test_result,
    write_progress,
)


class TestMigrateProgress:
    def test_fills_missing_scope_files(self):
        progress = {"config": {"scope": {}}}
        migrate_progress(progress)
        assert progress["scope_files"] == {"current": []}

    def test_fills_missing_config_scope(self):
        progress = {"config": {}}
        migrate_progress(progress)
        assert progress["config"]["scope"]["mode"] == "local-changes"
        assert progress["config"]["scope"]["base_ref"] is None

    def test_fills_missing_config(self):
        progress = {}
        migrate_progress(progress)
        assert "config" in progress
        assert "scope" in progress["config"]
        assert progress["scope_files"] == {"current": []}

    def test_preserves_existing_values(self):
        progress = {
            "config": {"scope": {"mode": "branch-diff", "base_ref": "origin/dev"}},
            "scope_files": {"current": ["a.py", "b.py"]},
        }
        migrate_progress(progress)
        assert progress["config"]["scope"]["mode"] == "branch-diff"
        assert progress["scope_files"]["current"] == ["a.py", "b.py"]

    def test_partial_scope_files_dict(self):
        progress = {"scope_files": {}}
        migrate_progress(progress)
        assert progress["scope_files"]["current"] == []

    def test_partial_config_scope_dict(self):
        progress = {"config": {"scope": {"mode": "branch-diff"}}}
        migrate_progress(progress)
        # Existing key preserved
        assert progress["config"]["scope"]["mode"] == "branch-diff"
        # Missing subkeys filled in
        assert progress["config"]["scope"]["paths"] == []
        assert progress["config"]["scope"]["base_ref"] is None

    def test_fills_missing_pr_description(self):
        progress = {"config": {"scope": {}}}
        migrate_progress(progress)
        assert progress["config"]["pr_description"] is None

    def test_preserves_existing_pr_description(self):
        progress = {
            "config": {
                "scope": {},
                "pr_description": {
                    "title": "T",
                    "body": "B",
                    "base_ref": "origin/main",
                },
            }
        }
        migrate_progress(progress)
        assert progress["config"]["pr_description"]["title"] == "T"

    def test_resets_old_shape_scope_files_matching_paths(self):
        """FU5: pre-fix progress files stored ['src/auth'] in scope_files.current
        when --scope src/auth was passed — that's the raw directory string,
        not a file list. Migration clears it so _populate_branch_scope can
        rediscover real files."""
        progress = {
            "config": {
                "scope": {"mode": "directory", "paths": ["src/auth"]},
            },
            "scope_files": {"current": ["src/auth"]},
        }
        migrate_progress(progress)
        assert progress["scope_files"]["current"] == []

    def test_preserves_real_file_list_unchanged(self):
        """A real file list (not matching scope.paths) must not be reset."""
        progress = {
            "config": {
                "scope": {"mode": "directory", "paths": ["src/auth"]},
            },
            "scope_files": {"current": ["src/auth/login.py", "src/auth/session.py"]},
        }
        migrate_progress(progress)
        assert progress["scope_files"]["current"] == [
            "src/auth/login.py",
            "src/auth/session.py",
        ]

    def test_preserves_single_file_scope_matching_paths(self):
        """Regression guard: --scope README.md whose branch diff returns
        exactly ['README.md'] must not be cleared as old-shape. The reset
        only fires when the entry looks like a directory (no file suffix)."""
        progress = {
            "config": {"scope": {"mode": "directory", "paths": ["README.md"]}},
            "scope_files": {"current": ["README.md"]},
        }
        migrate_progress(progress)
        assert progress["scope_files"]["current"] == ["README.md"]

    def test_does_not_reset_when_both_empty(self):
        """Empty scope.paths and empty scope_files.current must stay empty —
        the reset requires a non-empty list."""
        progress = {
            "config": {"scope": {"paths": []}},
            "scope_files": {"current": []},
        }
        migrate_progress(progress)
        assert progress["scope_files"]["current"] == []

    def test_resets_old_shape_even_when_paths_key_missing(self):
        """Regression: progress files older than the `scope.paths` key default
        paths=[] via setdefault. The reset must still fire for the stale
        directory entry, which means it cannot couple strictly to
        `current == paths`."""
        progress = {
            # No scope.paths key at all — will default to [] after setdefault
            "config": {"scope": {"mode": "directory"}},
            "scope_files": {"current": ["src/auth"]},
        }
        migrate_progress(progress)
        assert progress["scope_files"]["current"] == []

    def test_preserves_extensionless_real_file_when_paths_mismatches(self):
        """Regression guard for iter-3: common extension-less files
        (Makefile, Dockerfile, LICENSE, .env, Jenkinsfile) must not be
        incorrectly cleared by the suffix-only heuristic when scope.paths
        holds a different value — that case is a legitimate single-file
        branch diff, not an old-shape directory sentinel."""
        for fname in ("Makefile", "Dockerfile", "LICENSE", ".env", "Jenkinsfile"):
            progress = {
                "config": {"scope": {"mode": "directory", "paths": ["src/auth"]}},
                "scope_files": {"current": [fname]},
            }
            migrate_progress(progress)
            assert progress["scope_files"]["current"] == [
                fname
            ], f"{fname} was incorrectly cleared"

    def test_resets_extensionless_entry_when_paths_match(self):
        """The suffix-only heuristic SHOULD still fire for an extension-less
        entry when it matches scope.paths — that is the pre-FU5 shape where
        the raw --scope dir arg was stored as a file list."""
        progress = {
            "config": {"scope": {"mode": "directory", "paths": ["Makefile"]}},
            "scope_files": {"current": ["Makefile"]},
        }
        migrate_progress(progress)
        assert progress["scope_files"]["current"] == []


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
        # FU5: scope_files.current is always left empty by make_initial_progress.
        # _populate_branch_scope fills it with the real branch-diff file list
        # (path-filtered by config.scope.paths when --scope was given), so the
        # list never contains a raw directory string that agents would treat
        # as a file.
        assert progress["scope_files"]["current"] == []

    @patch("impl.progress.git_rev_parse_head", return_value="abc123def456")
    def test_focus_stored_in_config(self, mock_git, tmp_path):
        progress = make_initial_progress(
            "refactor", "", 8, "pytest", tmp_path, focus="testability"
        )
        assert progress["config"]["focus"] == "testability"

    @patch("impl.progress.git_rev_parse_head", return_value="abc123def456")
    def test_focus_default_empty(self, mock_git, tmp_path):
        progress = make_initial_progress("refactor", "", 8, "pytest", tmp_path)
        assert progress["config"]["focus"] == ""

    @patch("impl.progress.git_rev_parse_head", return_value="abc123def456")
    def test_focus_persists_in_json(self, mock_git, tmp_path):
        progress = make_initial_progress(
            "refactor", "", 8, "pytest", tmp_path, focus="guidelines"
        )
        path = tmp_path / "progress.json"
        write_progress(path, progress)
        loaded = read_progress(path)
        assert loaded["config"]["focus"] == "guidelines"
