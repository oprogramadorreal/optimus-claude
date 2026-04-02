import shutil
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parent.parent.parent / "scripts" / "deep-mode-harness"
    ),
)

from main import (
    _archive_progress,
    _load_resumed_progress,
    _mark_combined_regression,
    _record_iteration_history,
    _register_iteration_findings,
    _validate_environment,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_progress():
    """Minimal valid progress dict matching make_initial_progress shape."""
    return {
        "schema_version": 1,
        "skill": "code-review",
        "started_at": "2025-01-01T00:00:00Z",
        "config": {
            "max_iterations": 8,
            "test_command": "npm test",
            "scope": {"mode": "local-changes", "paths": [], "base_ref": None},
            "project_root": "/tmp/project",
            "base_commit": "abc1234567890",
        },
        "iteration": {"current": 1, "completed": 0},
        "findings": [],
        "scope_files": {"current": []},
        "test_results": {"last_full_run": None, "last_run_output_summary": None},
        "iteration_history": [],
        "termination": {"reason": None, "message": None},
    }


@pytest.fixture
def sample_fix():
    return {
        "file": "src/app.js",
        "line": 42,
        "category": "bug",
        "summary": "Fix null check",
        "pre_edit_content": "obj.value",
        "post_edit_content": "obj?.value",
    }


# ---------------------------------------------------------------------------
# _record_iteration_history
# ---------------------------------------------------------------------------


class TestRecordIterationHistory:
    def test_appends_entry(self, sample_progress):
        _record_iteration_history(sample_progress, 1, 3, 2, 1, True)
        assert len(sample_progress["iteration_history"]) == 1
        entry = sample_progress["iteration_history"][0]
        assert entry["iteration"] == 1
        assert entry["new_findings"] == 3
        assert entry["fixed"] == 2
        assert entry["reverted"] == 1
        assert entry["test_passed"] is True
        assert sample_progress["iteration"]["completed"] == 1

    def test_counts_persistent_findings(self, sample_progress):
        sample_progress["findings"] = [
            {
                "file": "a.js",
                "line": 1,
                "category": "bug",
                "status": "persistent — fix failed",
                "iteration_last_attempted": 2,
            },
            {
                "file": "b.js",
                "line": 2,
                "category": "bug",
                "status": "persistent — fix failed",
                "iteration_last_attempted": 2,
            },
            {
                "file": "c.js",
                "line": 3,
                "category": "bug",
                "status": "fixed",
                "iteration_last_attempted": 2,
            },
        ]
        _record_iteration_history(sample_progress, 2, 0, 0, 0, True)
        assert sample_progress["iteration_history"][0]["persistent"] == 2

    def test_multiple_iterations(self, sample_progress):
        _record_iteration_history(sample_progress, 1, 5, 3, 1, True)
        _record_iteration_history(sample_progress, 2, 2, 1, 0, True)
        assert len(sample_progress["iteration_history"]) == 2
        assert sample_progress["iteration"]["completed"] == 2


# ---------------------------------------------------------------------------
# _register_iteration_findings
# ---------------------------------------------------------------------------


class TestRegisterIterationFindings:
    def test_registers_fixes_as_applied_pending(self, sample_progress, sample_fix):
        fixes = [sample_fix]
        result = {"new_findings": [], "fixes_applied": fixes}
        _register_iteration_findings(sample_progress, result, fixes)
        assert len(sample_progress["findings"]) == 1
        assert sample_progress["findings"][0]["status"] == "applied-pending-test"

    def test_registers_new_findings_as_discovered(self, sample_progress):
        new_finding = {
            "file": "src/utils.js",
            "line": 10,
            "category": "style",
            "summary": "Formatting issue",
        }
        result = {"new_findings": [new_finding], "fixes_applied": []}
        _register_iteration_findings(sample_progress, result, fixes=[])
        assert len(sample_progress["findings"]) == 1
        assert sample_progress["findings"][0]["status"] == "discovered"

    def test_deduplicates_fixes_from_new_findings(self, sample_progress, sample_fix):
        """If a fix is in both fixes and new_findings, it's only registered once."""
        result = {"new_findings": [sample_fix], "fixes_applied": [sample_fix]}
        _register_iteration_findings(sample_progress, result, fixes=[sample_fix])
        # Should have exactly 1 finding (the fix), not 2
        assert len(sample_progress["findings"]) == 1
        assert sample_progress["findings"][0]["status"] == "applied-pending-test"


# ---------------------------------------------------------------------------
# _mark_combined_regression
# ---------------------------------------------------------------------------


class TestMarkCombinedRegression:
    def test_marks_fixed_as_reverted(self, sample_progress):
        fix = {
            "file": "src/app.js",
            "line": 42,
            "category": "bug",
            "summary": "Fix null check",
        }
        sample_progress["findings"] = [
            {
                "file": "src/app.js",
                "line": 42,
                "category": "bug",
                "summary": "Fix null check",
                "status": "fixed",
            }
        ]
        reverted = _mark_combined_regression([fix], sample_progress)
        assert reverted == 1
        assert sample_progress["findings"][0]["status"] == "reverted — test failure"

    def test_marks_retained_as_reverted(self, sample_progress):
        fix = {
            "file": "src/app.js",
            "line": 42,
            "category": "bug",
            "summary": "Fix null check",
        }
        sample_progress["findings"] = [
            {
                "file": "src/app.js",
                "line": 42,
                "category": "bug",
                "summary": "Fix null check",
                "status": "retained — revert failed",
            }
        ]
        reverted = _mark_combined_regression([fix], sample_progress)
        assert reverted == 1

    def test_ignores_non_matching_status(self, sample_progress):
        fix = {
            "file": "src/app.js",
            "line": 42,
            "category": "bug",
            "summary": "Fix null check",
        }
        sample_progress["findings"] = [
            {
                "file": "src/app.js",
                "line": 42,
                "category": "bug",
                "summary": "Fix null check",
                "status": "discovered",
            }
        ]
        reverted = _mark_combined_regression([fix], sample_progress)
        assert reverted == 0

    def test_no_matching_finding(self, sample_progress):
        fix = {"file": "nonexistent.js", "line": 1, "category": "bug", "summary": "x"}
        sample_progress["findings"] = []
        reverted = _mark_combined_regression([fix], sample_progress)
        assert reverted == 0


# ---------------------------------------------------------------------------
# _validate_environment
# ---------------------------------------------------------------------------


class TestValidateEnvironment:
    @patch("main.subprocess.run")
    @patch("main.detect_test_command", return_value="npm test")
    def test_success(self, mock_detect, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0)
        args = MagicMock(test_command="")
        cmd, err = _validate_environment(tmp_path, args)
        assert cmd == "npm test"
        assert err is None

    @patch("main.subprocess.run", side_effect=FileNotFoundError)
    def test_claude_not_found(self, mock_run, tmp_path):
        args = MagicMock(test_command="")
        cmd, err = _validate_environment(tmp_path, args)
        assert cmd is None
        assert "claude CLI not found" in err

    @patch("main.subprocess.run")
    def test_claude_nonzero_exit(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=1)
        args = MagicMock(test_command="")
        cmd, err = _validate_environment(tmp_path, args)
        assert cmd is None
        assert "claude CLI not found" in err

    @patch("main.subprocess.run")
    @patch("main.detect_test_command", return_value=None)
    def test_no_test_command(self, mock_detect, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0)
        args = MagicMock(test_command="")
        cmd, err = _validate_environment(tmp_path, args)
        assert cmd is None
        assert "No test command found" in err

    @patch("main.subprocess.run")
    def test_explicit_test_command(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0)
        args = MagicMock(test_command="pytest")
        cmd, err = _validate_environment(tmp_path, args)
        assert cmd == "pytest"
        assert err is None


# ---------------------------------------------------------------------------
# _load_resumed_progress
# ---------------------------------------------------------------------------


class TestLoadResumedProgress:
    def _write_progress(self, path, progress):
        import json

        path.write_text(json.dumps(progress), encoding="utf-8")

    def test_success(self, tmp_path, sample_progress):
        progress_path = tmp_path / "progress.json"
        sample_progress["config"]["project_root"] = str(tmp_path)
        self._write_progress(progress_path, sample_progress)
        args = MagicMock(skill="code-review", max_iterations=5)
        result, err = _load_resumed_progress(progress_path, args, tmp_path)
        assert err is None
        assert result["skill"] == "code-review"

    def test_missing_file_no_backup(self, tmp_path):
        progress_path = tmp_path / "progress.json"
        args = MagicMock(skill="code-review")
        result, err = _load_resumed_progress(progress_path, args, tmp_path)
        assert result is None
        assert "No progress file" in err

    def test_restores_from_backup(self, tmp_path, sample_progress):
        progress_path = tmp_path / "progress.json"
        backup_path = Path(str(progress_path) + ".bak")
        sample_progress["config"]["project_root"] = str(tmp_path)
        self._write_progress(backup_path, sample_progress)
        args = MagicMock(skill="code-review", max_iterations=5)
        result, err = _load_resumed_progress(progress_path, args, tmp_path)
        assert err is None
        assert result is not None

    def test_skill_mismatch(self, tmp_path, sample_progress):
        progress_path = tmp_path / "progress.json"
        sample_progress["config"]["project_root"] = str(tmp_path)
        self._write_progress(progress_path, sample_progress)
        args = MagicMock(skill="refactor", max_iterations=5)
        result, err = _load_resumed_progress(progress_path, args, tmp_path)
        assert result is None
        assert "does not match" in err

    def test_missing_required_field(self, tmp_path):
        progress_path = tmp_path / "progress.json"
        self._write_progress(progress_path, {"skill": "code-review"})
        args = MagicMock(skill="code-review")
        result, err = _load_resumed_progress(progress_path, args, tmp_path)
        assert result is None
        assert "missing required field" in err

    def test_project_root_mismatch(self, tmp_path, sample_progress):
        progress_path = tmp_path / "progress.json"
        sample_progress["config"]["project_root"] = "/some/other/path"
        self._write_progress(progress_path, sample_progress)
        args = MagicMock(skill="code-review", max_iterations=5)
        result, err = _load_resumed_progress(progress_path, args, tmp_path)
        assert result is None
        assert "does not match" in err

    def test_extends_iteration_cap(self, tmp_path, sample_progress):
        progress_path = tmp_path / "progress.json"
        sample_progress["config"]["project_root"] = str(tmp_path)
        self._write_progress(progress_path, sample_progress)
        args = MagicMock(skill="code-review", max_iterations=20)
        result, err = _load_resumed_progress(progress_path, args, tmp_path)
        assert err is None
        assert result["config"]["max_iterations"] == 20


# ---------------------------------------------------------------------------
# _archive_progress
# ---------------------------------------------------------------------------


class TestArchiveProgress:
    def test_moves_to_done(self, tmp_path):
        progress_path = tmp_path / "progress.json"
        progress_path.write_text('{"done": true}', encoding="utf-8")
        backup_path = Path(str(progress_path) + ".bak")
        backup_path.write_text('{"backup": true}', encoding="utf-8")

        _archive_progress(progress_path)

        done_path = progress_path.with_suffix(".done.json")
        assert done_path.exists()
        assert not progress_path.exists()
        assert not backup_path.exists()

    def test_overwrites_existing_done(self, tmp_path):
        progress_path = tmp_path / "progress.json"
        progress_path.write_text('{"new": true}', encoding="utf-8")
        done_path = progress_path.with_suffix(".done.json")
        done_path.write_text('{"old": true}', encoding="utf-8")

        _archive_progress(progress_path)

        assert done_path.read_text(encoding="utf-8") == '{"new": true}'

    def test_no_backup_to_clean(self, tmp_path):
        """Works even when no backup file exists."""
        progress_path = tmp_path / "progress.json"
        progress_path.write_text('{"data": 1}', encoding="utf-8")
        _archive_progress(progress_path)
        assert progress_path.with_suffix(".done.json").exists()
