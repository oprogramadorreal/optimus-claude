import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parent.parent.parent
        / "scripts"
        / "test-coverage-harness"
    ),
)

from main import (
    _archive_progress,
    _build_argument_parser,
    _handle_interrupt,
    _load_resumed_progress,
    _print_startup_info,
    _process_refactor_output,
    _process_unit_test_output,
    _revert_test_files,
    _run_cycle_loop,
    _validate_environment,
    main,
)

# Fixtures are provided by conftest.py (sample_coverage_progress, etc.)


# ---------------------------------------------------------------------------
# _build_argument_parser
# ---------------------------------------------------------------------------


class TestBuildArgumentParser:
    def test_default_values(self):
        parser = _build_argument_parser()
        args = parser.parse_args([])
        assert args.max_cycles == 5
        assert args.scope == ""
        assert args.resume is False
        assert args.no_commit is False
        assert args.verbose is False
        assert args.test_command == ""
        assert args.project_dir == "."
        assert args.max_turns == 30
        assert args.timeout == 900
        assert args.allowed_tools == ""

    def test_all_flags(self):
        parser = _build_argument_parser()
        args = parser.parse_args(
            [
                "--max-cycles",
                "8",
                "--scope",
                "src/api",
                "--resume",
                "--no-commit",
                "--verbose",
                "--test-command",
                "pytest --cov",
                "--project-dir",
                "/tmp/proj",
                "--max-turns",
                "50",
                "--timeout",
                "1200",
            ]
        )
        assert args.max_cycles == 8
        assert args.scope == "src/api"
        assert args.resume is True
        assert args.no_commit is True
        assert args.verbose is True
        assert args.test_command == "pytest --cov"
        assert args.project_dir == "/tmp/proj"
        assert args.max_turns == 50
        assert args.timeout == 1200

    def test_allowed_tools_default_const(self):
        parser = _build_argument_parser()
        args = parser.parse_args(["--allowed-tools"])
        assert "Read" in args.allowed_tools
        assert "Bash" in args.allowed_tools

    def test_allowed_tools_explicit(self):
        parser = _build_argument_parser()
        args = parser.parse_args(["--allowed-tools", "Read,Grep"])
        assert args.allowed_tools == "Read,Grep"

    def test_max_cycles_clamp_high(self):
        """Parser accepts values above hard cap (clamping is done in main)."""
        parser = _build_argument_parser()
        args = parser.parse_args(["--max-cycles", "99"])
        assert args.max_cycles == 99

    def test_progress_file_default(self):
        parser = _build_argument_parser()
        args = parser.parse_args([])
        assert args.progress_file == ".claude/test-coverage-progress.json"


# ---------------------------------------------------------------------------
# _validate_environment
# ---------------------------------------------------------------------------


class TestValidateEnvironment:
    @patch("main.subprocess.run")
    @patch("main.detect_test_command", return_value="pytest --cov")
    def test_success(self, mock_detect, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0)
        args = MagicMock(test_command="")
        cmd, err = _validate_environment(tmp_path, args)
        assert cmd == "pytest --cov"
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
    @staticmethod
    def _normalized(path):
        """Return a forward-slash normalized path string (matches normalize_path)."""
        return str(path).replace("\\", "/")

    def _write_progress(self, path, progress):
        path.write_text(json.dumps(progress), encoding="utf-8")

    def test_success(self, tmp_path, sample_coverage_progress):
        progress_path = tmp_path / "progress.json"
        sample_coverage_progress["config"]["project_root"] = self._normalized(tmp_path)
        self._write_progress(progress_path, sample_coverage_progress)
        args = MagicMock(max_cycles=5)
        result, err = _load_resumed_progress(progress_path, args, tmp_path)
        assert err is None
        assert result["harness"] == "test-coverage"

    def test_missing_file_no_backup(self, tmp_path):
        progress_path = tmp_path / "progress.json"
        args = MagicMock(max_cycles=5)
        result, err = _load_resumed_progress(progress_path, args, tmp_path)
        assert result is None
        assert "No progress file" in err

    def test_restores_from_backup(self, tmp_path, sample_coverage_progress):
        progress_path = tmp_path / "progress.json"
        backup_path = Path(str(progress_path) + ".bak")
        sample_coverage_progress["config"]["project_root"] = self._normalized(tmp_path)
        self._write_progress(backup_path, sample_coverage_progress)
        args = MagicMock(max_cycles=5)
        result, err = _load_resumed_progress(progress_path, args, tmp_path)
        assert err is None
        assert result is not None
        assert progress_path.exists()

    def test_harness_mismatch(self, tmp_path, sample_coverage_progress):
        progress_path = tmp_path / "progress.json"
        sample_coverage_progress["harness"] = "deep-mode"
        sample_coverage_progress["config"]["project_root"] = self._normalized(tmp_path)
        self._write_progress(progress_path, sample_coverage_progress)
        args = MagicMock(max_cycles=5)
        result, err = _load_resumed_progress(progress_path, args, tmp_path)
        assert result is None
        assert "not 'test-coverage'" in err

    def test_project_root_mismatch(self, tmp_path, sample_coverage_progress):
        progress_path = tmp_path / "progress.json"
        sample_coverage_progress["config"]["project_root"] = "/some/other/path"
        self._write_progress(progress_path, sample_coverage_progress)
        args = MagicMock(max_cycles=5)
        result, err = _load_resumed_progress(progress_path, args, tmp_path)
        assert result is None
        assert "does not match" in err

    def test_extends_cycle_cap(self, tmp_path, sample_coverage_progress):
        progress_path = tmp_path / "progress.json"
        sample_coverage_progress["config"]["project_root"] = self._normalized(tmp_path)
        sample_coverage_progress["config"]["max_cycles"] = 3
        self._write_progress(progress_path, sample_coverage_progress)
        args = MagicMock(max_cycles=8)
        result, err = _load_resumed_progress(progress_path, args, tmp_path)
        assert err is None
        assert result["config"]["max_cycles"] == 8

    def test_does_not_shrink_cycle_cap(self, tmp_path, sample_coverage_progress):
        progress_path = tmp_path / "progress.json"
        sample_coverage_progress["config"]["project_root"] = self._normalized(tmp_path)
        sample_coverage_progress["config"]["max_cycles"] = 5
        self._write_progress(progress_path, sample_coverage_progress)
        args = MagicMock(max_cycles=3)
        result, err = _load_resumed_progress(progress_path, args, tmp_path)
        assert err is None
        assert result["config"]["max_cycles"] == 5

    def test_corrupt_file(self, tmp_path):
        progress_path = tmp_path / "progress.json"
        progress_path.write_text("NOT JSON", encoding="utf-8")
        args = MagicMock(max_cycles=5)
        result, err = _load_resumed_progress(progress_path, args, tmp_path)
        assert result is None
        assert "Cannot read progress file" in err


# ---------------------------------------------------------------------------
# _process_unit_test_output
# ---------------------------------------------------------------------------


class TestProcessUnitTestOutput:
    def test_records_tests_and_coverage(
        self, sample_coverage_progress, sample_unit_test_output
    ):
        progress = sample_coverage_progress
        summary = _process_unit_test_output(progress, sample_unit_test_output, 1)

        assert summary["tests_written"] == 1
        assert summary["tests_passed"] == 1
        assert summary["coverage_delta"] == 16.4
        assert summary["untestable_items_reported"] == 1
        assert len(progress["tests_created"]) == 1
        assert progress["tests_created"][0]["cycle"] == 1

    def test_sets_baseline_on_first_cycle(
        self, sample_coverage_progress, sample_unit_test_output
    ):
        progress = sample_coverage_progress
        _process_unit_test_output(progress, sample_unit_test_output, 1)
        assert progress["coverage"]["baseline"] == 42.3
        assert progress["coverage"]["current"] == 58.7
        assert progress["coverage"]["tool"] == "pytest-cov"

    def test_does_not_overwrite_baseline(
        self, sample_coverage_progress, sample_unit_test_output
    ):
        progress = sample_coverage_progress
        progress["coverage"]["baseline"] = 30.0
        _process_unit_test_output(progress, sample_unit_test_output, 2)
        assert progress["coverage"]["baseline"] == 30.0

    def test_coverage_history_appended(
        self, sample_coverage_progress, sample_unit_test_output
    ):
        progress = sample_coverage_progress
        _process_unit_test_output(progress, sample_unit_test_output, 1)
        assert len(progress["coverage"]["history"]) == 1
        entry = progress["coverage"]["history"][0]
        assert entry["cycle"] == 1
        assert entry["before"] == 42.3
        assert entry["after"] == 58.7
        assert entry["delta"] == 16.4

    def test_untestable_code_updated(
        self, sample_coverage_progress, sample_unit_test_output
    ):
        progress = sample_coverage_progress
        _process_unit_test_output(progress, sample_unit_test_output, 1)
        assert len(progress["untestable_code"]) == 1
        item = progress["untestable_code"][0]
        assert item["cycle_reported"] == 1
        assert item["status"] == "pending"
        assert item["refactor_attempt_cycle"] is None

    def test_bugs_recorded(self, sample_coverage_progress):
        progress = sample_coverage_progress
        result = {
            "tests_written": [],
            "coverage": {},
            "untestable_code": [],
            "bugs_discovered": [{"file": "src/auth.py", "description": "null ref"}],
        }
        _process_unit_test_output(progress, result, 2)
        assert len(progress["bugs_discovered"]) == 1
        assert progress["bugs_discovered"][0]["cycle_discovered"] == 2

    def test_empty_result(self, sample_coverage_progress):
        progress = sample_coverage_progress
        result = {
            "tests_written": [],
            "coverage": {},
            "untestable_code": [],
            "bugs_discovered": [],
        }
        summary = _process_unit_test_output(progress, result, 1)
        assert summary["tests_written"] == 0
        assert summary["tests_passed"] == 0
        assert summary["coverage_delta"] == 0

    def test_failed_tests_not_counted_as_passed(self, sample_coverage_progress):
        progress = sample_coverage_progress
        result = {
            "tests_written": [
                {"file": "tests/test_a.py", "status": "fail"},
                {"file": "tests/test_b.py", "status": "pass"},
            ],
            "coverage": {},
            "untestable_code": [],
            "bugs_discovered": [],
        }
        summary = _process_unit_test_output(progress, result, 1)
        assert summary["tests_written"] == 2
        assert summary["tests_passed"] == 1


# ---------------------------------------------------------------------------
# _revert_test_files
# ---------------------------------------------------------------------------


class TestRevertTestFiles:
    def test_deletes_existing_file(self, tmp_path):
        test_file = tmp_path / "tests" / "test_foo.py"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("# test", encoding="utf-8")
        tests = [{"file": "tests/test_foo.py"}]
        _revert_test_files(tests, str(tmp_path))
        assert not test_file.exists()

    def test_missing_file_no_error(self, tmp_path, capsys):
        tests = [{"file": "tests/nonexistent.py"}]
        _revert_test_files(tests, str(tmp_path))
        # Should not raise; file just doesn't exist

    def test_oserror_prints_warning(self, tmp_path, capsys):
        test_file = tmp_path / "tests" / "test_locked.py"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("# test", encoding="utf-8")
        tests = [{"file": "tests/test_locked.py"}]

        with patch.object(Path, "unlink", side_effect=OSError("Permission denied")):
            _revert_test_files(tests, str(tmp_path))
        output = capsys.readouterr().out
        assert "WARNING" in output
        assert "Permission denied" in output

    def test_empty_tests_list(self, tmp_path):
        _revert_test_files([], str(tmp_path))
        # No error, nothing to do

    def test_multiple_files(self, tmp_path):
        files = []
        for name in ["test_a.py", "test_b.py", "test_c.py"]:
            f = tmp_path / name
            f.write_text("# test", encoding="utf-8")
            files.append({"file": name})
        _revert_test_files(files, str(tmp_path))
        for name in ["test_a.py", "test_b.py", "test_c.py"]:
            assert not (tmp_path / name).exists()

    def test_path_traversal_skipped(self, tmp_path):
        """File path escaping cwd is silently skipped via ValueError guard."""
        outside = tmp_path / ".." / "outside_project" / "test_evil.py"
        outside.parent.mkdir(parents=True, exist_ok=True)
        outside.write_text("# evil", encoding="utf-8")
        tests = [{"file": "../outside_project/test_evil.py"}]
        _revert_test_files(tests, str(tmp_path))
        # File outside cwd must NOT be deleted
        assert outside.exists()


# ---------------------------------------------------------------------------
# _process_refactor_output
# ---------------------------------------------------------------------------


class TestProcessRefactorOutput:
    def test_records_findings(self, sample_coverage_progress, sample_refactor_output):
        progress = sample_coverage_progress
        summary = _process_refactor_output(progress, sample_refactor_output, 1)
        assert summary["findings_count"] == 1
        assert summary["fixed"] == 1
        assert summary["reverted"] == 0
        assert summary["test_passed"] is True
        assert len(progress["refactor_findings"]) == 1
        assert progress["refactor_findings"][0]["cycle"] == 1

    def test_does_not_mark_untestable_items(
        self, sample_coverage_progress, sample_refactor_output
    ):
        """_process_refactor_output no longer marks items — marking is deferred
        to _run_refactor_phase after bisection confirms which fixes survived."""
        progress = sample_coverage_progress
        progress["untestable_code"] = [
            {"file": "src/db.py", "status": "pending", "refactor_attempt_cycle": None}
        ]
        _process_refactor_output(progress, sample_refactor_output, 2)
        # Items should remain pending — marking happens later
        assert progress["untestable_code"][0]["status"] == "pending"
        assert progress["untestable_code"][0]["refactor_attempt_cycle"] is None

    def test_empty_result(self, sample_coverage_progress):
        progress = sample_coverage_progress
        result = {"fixes_applied": [], "new_findings": []}
        summary = _process_refactor_output(progress, result, 1)
        assert summary["findings_count"] == 0
        assert summary["fixed"] == 0


# ---------------------------------------------------------------------------
# _print_startup_info
# ---------------------------------------------------------------------------


class TestPrintStartupInfo:
    def test_prints_key_info(self, capsys, sample_coverage_progress):
        args = SimpleNamespace()
        _print_startup_info(args, sample_coverage_progress)
        output = capsys.readouterr().out
        assert "Test-Coverage Harness" in output
        assert "Max cycles:" in output
        assert "5" in output
        assert "pytest --cov" in output
        assert "cycle 1" in output

    def test_prints_scope_when_set(self, capsys, sample_coverage_progress):
        sample_coverage_progress["config"]["scope"] = "src/api"
        args = SimpleNamespace()
        _print_startup_info(args, sample_coverage_progress)
        output = capsys.readouterr().out
        assert "Scope:" in output
        assert "src/api" in output

    def test_omits_scope_when_empty(self, capsys, sample_coverage_progress):
        args = SimpleNamespace()
        _print_startup_info(args, sample_coverage_progress)
        output = capsys.readouterr().out
        assert "Scope:" not in output

    def test_estimated_sessions(self, capsys, sample_coverage_progress):
        sample_coverage_progress["config"]["max_cycles"] = 3
        sample_coverage_progress["cycle"]["current"] = 1
        args = SimpleNamespace()
        _print_startup_info(args, sample_coverage_progress)
        output = capsys.readouterr().out
        # (3 - 1 + 1) * 2 = 6
        assert "~6" in output


# ---------------------------------------------------------------------------
# _handle_interrupt
# ---------------------------------------------------------------------------


class TestHandleInterrupt:
    @patch("main.print_report")
    @patch("main.git_commit_checkpoint", return_value=True)
    @patch("main.git_diff_has_changes", return_value=True)
    @patch("main.write_progress")
    def test_with_commit(
        self,
        mock_write,
        mock_diff,
        mock_commit,
        mock_report,
        sample_coverage_progress,
        tmp_path,
    ):
        args = SimpleNamespace(no_commit=False)
        progress_path = tmp_path / "progress.json"
        _handle_interrupt(args, sample_coverage_progress, progress_path, tmp_path)

        assert sample_coverage_progress["termination"]["reason"] == "interrupted"
        mock_write.assert_called_once()
        mock_commit.assert_called_once()
        mock_report.assert_called_once()

    @patch("main.print_report")
    @patch("main.git_diff_has_changes", return_value=False)
    @patch("main.write_progress")
    def test_no_changes_no_commit(
        self, mock_write, mock_diff, mock_report, sample_coverage_progress, tmp_path
    ):
        args = SimpleNamespace(no_commit=False)
        progress_path = tmp_path / "progress.json"
        _handle_interrupt(args, sample_coverage_progress, progress_path, tmp_path)

        assert sample_coverage_progress["termination"]["reason"] == "interrupted"
        mock_report.assert_called_once()

    @patch("main.print_report")
    @patch("main.write_progress")
    def test_no_commit_flag(
        self, mock_write, mock_report, sample_coverage_progress, tmp_path
    ):
        args = SimpleNamespace(no_commit=True)
        progress_path = tmp_path / "progress.json"
        _handle_interrupt(args, sample_coverage_progress, progress_path, tmp_path)

        assert sample_coverage_progress["termination"]["reason"] == "interrupted"
        mock_report.assert_called_once()


# ---------------------------------------------------------------------------
# _archive_progress
# ---------------------------------------------------------------------------


class TestArchiveProgress:
    def test_renames_to_done(self, tmp_path):
        progress_path = tmp_path / "test-coverage-progress.json"
        progress_path.write_text('{"done": true}', encoding="utf-8")
        _archive_progress(progress_path)
        done_path = tmp_path / "test-coverage-progress-done.json"
        assert done_path.exists()
        assert not progress_path.exists()

    def test_oserror_ignored(self, tmp_path):
        progress_path = tmp_path / "nonexistent.json"
        # Should not raise even if file doesn't exist
        _archive_progress(progress_path)

    def test_path_object(self, tmp_path):
        progress_path = tmp_path / "progress.json"
        progress_path.write_text("{}", encoding="utf-8")
        _archive_progress(Path(progress_path))
        done_path = tmp_path / "progress-done.json"
        assert done_path.exists()


# ---------------------------------------------------------------------------
# _run_cycle_loop
# ---------------------------------------------------------------------------


class TestRunCycleLoop:
    def _make_args(self, **overrides):
        defaults = dict(
            no_commit=True,
            verbose=False,
            max_turns=30,
            scope="",
            timeout=900,
            allowed_tools=None,
            project_dir=".",
        )
        defaults.update(overrides)
        return SimpleNamespace(**defaults)

    @patch("main.check_coverage_plateau", return_value=(False, ""))
    @patch(
        "main.check_unit_test_convergence", return_value=(True, "No new tests possible")
    )
    @patch("main.run_tests", return_value=(True, "ok"))
    @patch("main.record_test_result")
    @patch("main.parse_harness_output")
    @patch("main.run_coverage_session", return_value="raw output")
    @patch("main.git_rev_parse_head", return_value="abc123")
    @patch("main.write_progress")
    def test_unit_test_convergence(
        self,
        mock_wp,
        mock_head,
        mock_session,
        mock_parse,
        mock_record,
        mock_run_tests,
        mock_conv,
        mock_plateau,
        sample_coverage_progress,
        tmp_path,
    ):
        mock_parse.return_value = {
            "tests_written": [{"file": "tests/test_a.py", "status": "pass"}],
            "coverage": {"before": 40, "after": 60, "delta": 20, "tool": "pytest-cov"},
            "untestable_code": [],
            "bugs_discovered": [],
            "no_new_tests": True,
        }
        args = self._make_args()
        progress = sample_coverage_progress
        progress_path = tmp_path / "progress.json"

        _run_cycle_loop(args, progress, progress_path, tmp_path, "pytest", 5)

        assert progress["termination"]["reason"] == "convergence"
        assert "No new tests" in progress["termination"]["message"]

    @patch("main.check_coverage_plateau", return_value=(False, ""))
    @patch("main.check_refactor_convergence", return_value=(False, ""))
    @patch("main.check_unit_test_convergence", return_value=(False, ""))
    @patch("main.run_tests", return_value=(True, "ok"))
    @patch("main.record_test_result")
    @patch("main.record_cycle_history")
    @patch("main.parse_harness_output")
    @patch("main.run_coverage_session", return_value="raw output")
    @patch("main.git_rev_parse_head", return_value="abc123")
    @patch("main.write_progress")
    def test_cycle_cap(
        self,
        mock_wp,
        mock_head,
        mock_session,
        mock_parse,
        mock_record_cycle,
        mock_record_test,
        mock_run_tests,
        mock_ut_conv,
        mock_rf_conv,
        mock_plateau,
        sample_coverage_progress,
        tmp_path,
    ):
        mock_parse.return_value = {
            "tests_written": [],
            "coverage": {"before": 40, "after": 42, "delta": 2},
            "untestable_code": [],
            "bugs_discovered": [],
            "no_new_tests": False,
        }
        args = self._make_args()
        progress = sample_coverage_progress
        progress["config"]["max_cycles"] = 1
        progress_path = tmp_path / "progress.json"

        _run_cycle_loop(args, progress, progress_path, tmp_path, "pytest", 1)

        assert progress["termination"]["reason"] == "cap"

    @patch("main.git_rev_parse_head", return_value=None)
    @patch("main.write_progress")
    def test_head_not_found(
        self, mock_wp, mock_head, sample_coverage_progress, tmp_path
    ):
        args = self._make_args()
        progress = sample_coverage_progress
        progress_path = tmp_path / "progress.json"

        _run_cycle_loop(args, progress, progress_path, tmp_path, "pytest", 5)

        assert progress["termination"]["reason"] == "error"
        assert "HEAD commit" in progress["termination"]["message"]

    @patch("main.restore_working_tree")
    @patch("main.run_coverage_session", side_effect=RuntimeError("session crash"))
    @patch("main.git_stash_snapshot", return_value=None)
    @patch("main.git_rev_parse_head", return_value="abc123")
    @patch("main.write_progress")
    def test_unit_test_session_crash(
        self,
        mock_wp,
        mock_head,
        mock_stash,
        mock_session,
        mock_restore,
        sample_coverage_progress,
        tmp_path,
    ):
        args = self._make_args()
        progress = sample_coverage_progress
        progress_path = tmp_path / "progress.json"

        _run_cycle_loop(args, progress, progress_path, tmp_path, "pytest", 5)

        assert progress["termination"]["reason"] == "crash"
        assert "Unit-test session failed" in progress["termination"]["message"]
        mock_restore.assert_called_once()

    @patch("main.restore_working_tree")
    @patch("main.run_tests", return_value=(False, "fail"))
    @patch("main.record_test_result")
    @patch("main.parse_harness_output", return_value=None)
    @patch("main.run_coverage_session", return_value="raw output")
    @patch("main.git_stash_snapshot", return_value=None)
    @patch("main.git_rev_parse_head", return_value="abc123")
    @patch("main.write_progress")
    def test_unit_test_parse_failure_tests_fail(
        self,
        mock_wp,
        mock_head,
        mock_stash,
        mock_session,
        mock_parse,
        mock_record,
        mock_run_tests,
        mock_restore,
        sample_coverage_progress,
        tmp_path,
    ):
        args = self._make_args()
        progress = sample_coverage_progress
        progress_path = tmp_path / "progress.json"

        _run_cycle_loop(args, progress, progress_path, tmp_path, "pytest", 5)

        assert progress["termination"]["reason"] == "parse-failure"
        mock_restore.assert_called_once()

    @patch("main.restore_working_tree")
    @patch("main.run_tests", return_value=(True, "ok"))
    @patch("main.record_test_result")
    @patch("main.parse_harness_output", return_value=None)
    @patch("main.run_coverage_session", return_value="raw output")
    @patch("main.git_stash_snapshot", return_value=None)
    @patch("main.git_rev_parse_head", return_value="abc123")
    @patch("main.write_progress")
    def test_unit_test_parse_failure_tests_pass(
        self,
        mock_wp,
        mock_head,
        mock_stash,
        mock_session,
        mock_parse,
        mock_record,
        mock_run_tests,
        mock_restore,
        sample_coverage_progress,
        tmp_path,
    ):
        args = self._make_args()
        progress = sample_coverage_progress
        progress_path = tmp_path / "progress.json"

        _run_cycle_loop(args, progress, progress_path, tmp_path, "pytest", 5)

        assert progress["termination"]["reason"] == "parse-failure"
        mock_restore.assert_not_called()

    @patch("main.check_coverage_plateau", return_value=(False, ""))
    @patch("main.check_unit_test_convergence", return_value=(False, ""))
    @patch("main.restore_working_tree")
    @patch("main.run_tests", return_value=(False, "FAIL"))
    @patch("main.record_test_result")
    @patch("main.record_cycle_history")
    @patch("main.parse_harness_output")
    @patch("main.run_coverage_session", return_value="raw output")
    @patch("main.git_stash_snapshot", return_value=None)
    @patch("main.git_rev_parse_head", return_value="abc123")
    @patch("main.write_progress")
    def test_unit_test_failure_reverts_and_caps(
        self,
        mock_wp,
        mock_head,
        mock_stash,
        mock_session,
        mock_parse,
        mock_record_cycle,
        mock_record_test,
        mock_run_tests,
        mock_restore,
        mock_ut_conv,
        mock_plateau,
        sample_coverage_progress,
        tmp_path,
    ):
        mock_parse.return_value = {
            "tests_written": [{"file": "tests/test_a.py", "status": "fail"}],
            "coverage": {},
            "untestable_code": [],
            "bugs_discovered": [],
        }
        args = self._make_args()
        progress = sample_coverage_progress
        progress["config"]["max_cycles"] = 1
        progress_path = tmp_path / "progress.json"

        _run_cycle_loop(args, progress, progress_path, tmp_path, "pytest", 1)

        mock_restore.assert_called()
        assert progress["termination"]["reason"] == "cap"

    @patch("main.check_coverage_plateau", return_value=(False, ""))
    @patch("main.check_unit_test_convergence", return_value=(False, ""))
    @patch("main.restore_working_tree")
    @patch("main.run_tests", return_value=(False, "FAIL"))
    @patch("main.record_test_result")
    @patch("main.record_cycle_history")
    @patch("main.parse_harness_output")
    @patch("main.run_coverage_session", return_value="raw output")
    @patch("main.git_stash_snapshot", return_value=None)
    @patch("main.git_rev_parse_head", return_value="abc123")
    @patch("main.write_progress")
    def test_unit_test_failure_continues_if_not_at_cap(
        self,
        mock_wp,
        mock_head,
        mock_stash,
        mock_session,
        mock_parse,
        mock_record_cycle,
        mock_record_test,
        mock_run_tests,
        mock_restore,
        mock_ut_conv,
        mock_plateau,
        sample_coverage_progress,
        tmp_path,
    ):
        """When tests fail but cycle < max_cycles, loop should continue (then cap out)."""
        mock_parse.return_value = {
            "tests_written": [{"file": "tests/test_a.py", "status": "fail"}],
            "coverage": {},
            "untestable_code": [],
            "bugs_discovered": [],
        }
        args = self._make_args()
        progress = sample_coverage_progress
        progress["config"]["max_cycles"] = 2
        progress["cycle"]["current"] = 1
        progress_path = tmp_path / "progress.json"

        _run_cycle_loop(args, progress, progress_path, tmp_path, "pytest", 2)

        # Should have incremented and then capped
        assert progress["termination"]["reason"] == "cap"
        assert mock_restore.call_count == 2

    @patch("main.check_coverage_plateau", return_value=(False, ""))
    @patch("main.check_refactor_convergence", return_value=(False, ""))
    @patch("main.check_unit_test_convergence", return_value=(False, ""))
    @patch("main.bisect_fixes")
    @patch("main.run_tests")
    @patch("main.record_test_result")
    @patch("main.record_cycle_history")
    @patch("main.parse_harness_output")
    @patch("main.run_coverage_session", return_value="raw output")
    @patch("main.git_rev_parse_head", return_value="abc123")
    @patch("main.write_progress")
    def test_refactor_phase_with_bisect_on_failure(
        self,
        mock_wp,
        mock_head,
        mock_session,
        mock_parse,
        mock_record_cycle,
        mock_record_test,
        mock_run_tests,
        mock_bisect,
        mock_ut_conv,
        mock_rf_conv,
        mock_plateau,
        sample_coverage_progress,
        tmp_path,
    ):
        ut_result = {
            "tests_written": [],
            "coverage": {"before": 40, "after": 50, "delta": 10},
            "untestable_code": [{"file": "src/db.py", "barrier": "hardcoded-dep"}],
            "bugs_discovered": [],
        }
        rf_result = {
            "fixes_applied": [{"file": "src/db.py", "line": 10}],
            "new_findings": [],
        }
        mock_parse.side_effect = [ut_result, rf_result]
        # First run_tests (after unit-test) passes, second (after refactor) fails
        mock_run_tests.side_effect = [(True, "ok"), (False, "FAIL")]
        mock_bisect.return_value = (0, 1, 0)  # fixed, reverted, skipped

        args = self._make_args()
        progress = sample_coverage_progress
        progress["config"]["max_cycles"] = 1
        progress_path = tmp_path / "progress.json"

        _run_cycle_loop(args, progress, progress_path, tmp_path, "pytest", 1)

        mock_bisect.assert_called_once()
        assert progress["termination"]["reason"] == "cap"

    @patch("main.check_coverage_plateau", return_value=(False, ""))
    @patch("main.check_refactor_convergence", return_value=(False, ""))
    @patch("main.check_unit_test_convergence", return_value=(False, ""))
    @patch("main.restore_working_tree")
    @patch("main.bisect_fixes")
    @patch("main.run_tests")
    @patch("main.record_test_result")
    @patch("main.record_cycle_history")
    @patch("main.parse_harness_output")
    @patch("main.run_coverage_session", return_value="raw output")
    @patch("main.git_rev_parse_head", return_value="abc123")
    @patch("main.write_progress")
    def test_combo_test_failure_after_bisect_restores_tree(
        self,
        mock_wp,
        mock_head,
        mock_session,
        mock_parse,
        mock_record_cycle,
        mock_record_test,
        mock_run_tests,
        mock_bisect,
        mock_restore,
        mock_ut_conv,
        mock_rf_conv,
        mock_plateau,
        sample_coverage_progress,
        tmp_path,
    ):
        """When bisect keeps some fixes but the combo re-test fails,
        restore_working_tree is called and the summary reflects full revert."""
        ut_result = {
            "tests_written": [],
            "coverage": {"before": 40, "after": 50, "delta": 10},
            "untestable_code": [{"file": "src/a.py", "barrier": "hardcoded-dep"}],
            "bugs_discovered": [],
        }
        rf_result = {
            "fixes_applied": [
                {"file": "src/a.py", "line": 1},
                {"file": "src/b.py", "line": 2},
            ],
            "new_findings": [],
        }
        mock_parse.side_effect = [ut_result, rf_result]
        # 1st run_tests (unit-test verify) passes,
        # 2nd (refactor verify) fails → triggers bisect,
        # 3rd (combo verify after bisect) fails → triggers restore
        mock_run_tests.side_effect = [
            (True, "ok"),
            (False, "FAIL"),
            (False, "COMBO FAIL"),
        ]
        mock_bisect.return_value = (1, 1, 0)  # 1 fixed, 1 reverted → combo check runs

        args = self._make_args()
        progress = sample_coverage_progress
        progress["config"]["max_cycles"] = 1
        progress_path = tmp_path / "progress.json"

        _run_cycle_loop(args, progress, progress_path, tmp_path, "pytest", 1)

        mock_restore.assert_called_once()
        # record_cycle_history is called with (progress, cycle, ut_summary, refactor_summary)
        # The last call's 4th positional arg is the refactor summary
        record_call_args = mock_record_cycle.call_args
        refactor_summary = record_call_args[0][3]
        assert refactor_summary["test_passed"] is False
        assert refactor_summary["fixed"] == 0
        assert refactor_summary["reverted"] == 2

    @patch("main.check_coverage_plateau", return_value=(False, ""))
    @patch("main.check_refactor_convergence", return_value=(False, ""))
    @patch("main.check_unit_test_convergence", return_value=(False, ""))
    @patch("main.run_tests", return_value=(True, "ok"))
    @patch("main.record_test_result")
    @patch("main.record_cycle_history")
    @patch("main.parse_harness_output")
    @patch("main.run_coverage_session", return_value="raw output")
    @patch("main.git_rev_parse_head", return_value="abc123")
    @patch("main.write_progress")
    def test_refactor_phase_success(
        self,
        mock_wp,
        mock_head,
        mock_session,
        mock_parse,
        mock_record_cycle,
        mock_record_test,
        mock_run_tests,
        mock_ut_conv,
        mock_rf_conv,
        mock_plateau,
        sample_coverage_progress,
        tmp_path,
    ):
        ut_result = {
            "tests_written": [],
            "coverage": {"before": 40, "after": 50, "delta": 10},
            "untestable_code": [{"file": "src/db.py", "barrier": "hardcoded-dep"}],
            "bugs_discovered": [],
        }
        rf_result = {
            "fixes_applied": [{"file": "src/db.py", "line": 10}],
            "new_findings": [{"file": "src/db.py", "summary": "extracted dep"}],
        }
        mock_parse.side_effect = [ut_result, rf_result]

        args = self._make_args()
        progress = sample_coverage_progress
        progress["config"]["max_cycles"] = 1
        progress_path = tmp_path / "progress.json"

        _run_cycle_loop(args, progress, progress_path, tmp_path, "pytest", 1)

        assert len(progress["refactor_findings"]) == 1
        assert progress["termination"]["reason"] == "cap"

    @patch("main.check_coverage_plateau", return_value=(False, ""))
    @patch("main.check_unit_test_convergence", return_value=(False, ""))
    @patch("main.restore_working_tree")
    @patch("main.run_tests", return_value=(True, "ok"))
    @patch("main.record_test_result")
    @patch("main.record_cycle_history")
    @patch("main.parse_harness_output")
    @patch("main.run_coverage_session")
    @patch("main.git_rev_parse_head", return_value="abc123")
    @patch("main.write_progress")
    def test_refactor_session_crash(
        self,
        mock_wp,
        mock_head,
        mock_session,
        mock_parse,
        mock_record_cycle,
        mock_record_test,
        mock_run_tests,
        mock_restore,
        mock_ut_conv,
        mock_plateau,
        sample_coverage_progress,
        tmp_path,
    ):
        ut_result = {
            "tests_written": [],
            "coverage": {},
            "untestable_code": [{"file": "src/db.py", "barrier": "x"}],
            "bugs_discovered": [],
        }
        mock_parse.return_value = ut_result
        mock_session.side_effect = [
            "ut output",
            RuntimeError("refactor crash"),
        ]

        args = self._make_args()
        progress = sample_coverage_progress
        progress_path = tmp_path / "progress.json"

        _run_cycle_loop(args, progress, progress_path, tmp_path, "pytest", 5)

        assert progress["termination"]["reason"] == "crash"
        assert "Refactor session failed" in progress["termination"]["message"]

    @patch("main.check_unit_test_convergence", return_value=(False, ""))
    @patch("main.run_tests", return_value=(True, "ok"))
    @patch("main.record_test_result")
    @patch("main.record_cycle_history")
    @patch("main.parse_harness_output")
    @patch("main.run_coverage_session")
    @patch("main.git_rev_parse_head", return_value="abc123")
    @patch("main.write_progress")
    def test_refactor_parse_failure(
        self,
        mock_wp,
        mock_head,
        mock_session,
        mock_parse,
        mock_record_cycle,
        mock_record_test,
        mock_run_tests,
        mock_ut_conv,
        sample_coverage_progress,
        tmp_path,
    ):
        ut_result = {
            "tests_written": [],
            "coverage": {},
            "untestable_code": [{"file": "src/db.py", "barrier": "x"}],
            "bugs_discovered": [],
        }
        mock_parse.side_effect = [ut_result, None]
        mock_session.side_effect = ["ut output", "rf output"]

        args = self._make_args()
        progress = sample_coverage_progress
        progress_path = tmp_path / "progress.json"

        _run_cycle_loop(args, progress, progress_path, tmp_path, "pytest", 5)

        assert progress["termination"]["reason"] == "parse-failure"
        assert "Refactor session" in progress["termination"]["message"]

    @patch("main.check_coverage_plateau", return_value=(True, "Coverage plateau"))
    @patch("main.check_refactor_convergence", return_value=(True, "Refactor converged"))
    @patch("main.check_unit_test_convergence", return_value=(False, ""))
    @patch("main.run_tests", return_value=(True, "ok"))
    @patch("main.record_test_result")
    @patch("main.record_cycle_history")
    @patch("main.parse_harness_output")
    @patch("main.run_coverage_session", return_value="raw output")
    @patch("main.git_rev_parse_head", return_value="abc123")
    @patch("main.write_progress")
    def test_refactor_convergence_with_plateau(
        self,
        mock_wp,
        mock_head,
        mock_session,
        mock_parse,
        mock_record_cycle,
        mock_record_test,
        mock_run_tests,
        mock_ut_conv,
        mock_rf_conv,
        mock_plateau,
        sample_coverage_progress,
        tmp_path,
    ):
        ut_result = {
            "tests_written": [],
            "coverage": {"before": 60, "after": 60, "delta": 0},
            "untestable_code": [{"file": "src/db.py", "barrier": "x"}],
            "bugs_discovered": [],
        }
        rf_result = {
            "fixes_applied": [],
            "new_findings": [],
            "no_new_findings": True,
            "no_actionable_fixes": True,
        }
        mock_parse.side_effect = [ut_result, rf_result]

        args = self._make_args()
        progress = sample_coverage_progress
        progress_path = tmp_path / "progress.json"

        _run_cycle_loop(args, progress, progress_path, tmp_path, "pytest", 5)

        assert progress["termination"]["reason"] == "convergence"
        # Plateau reason takes precedence when both converge
        assert (
            "plateau" in progress["termination"]["message"].lower()
            or "Coverage" in progress["termination"]["message"]
        )

    @patch(
        "main.check_coverage_plateau", return_value=(True, "Coverage plateau reached")
    )
    @patch("main.check_unit_test_convergence", return_value=(False, ""))
    @patch("main.run_tests", return_value=(True, "ok"))
    @patch("main.record_test_result")
    @patch("main.record_cycle_history")
    @patch("main.parse_harness_output")
    @patch("main.run_coverage_session", return_value="raw output")
    @patch("main.git_rev_parse_head", return_value="abc123")
    @patch("main.write_progress")
    def test_coverage_plateau_no_untestable(
        self,
        mock_wp,
        mock_head,
        mock_session,
        mock_parse,
        mock_record_cycle,
        mock_record_test,
        mock_run_tests,
        mock_ut_conv,
        mock_plateau,
        sample_coverage_progress,
        tmp_path,
    ):
        """Coverage plateau detected when no untestable code (no refactor phase)."""
        mock_parse.return_value = {
            "tests_written": [],
            "coverage": {"before": 90, "after": 90, "delta": 0},
            "untestable_code": [],
            "bugs_discovered": [],
        }
        args = self._make_args()
        progress = sample_coverage_progress
        progress_path = tmp_path / "progress.json"

        _run_cycle_loop(args, progress, progress_path, tmp_path, "pytest", 5)

        assert progress["termination"]["reason"] == "convergence"
        assert "plateau" in progress["termination"]["message"].lower()

    @patch("main.check_coverage_plateau", return_value=(False, ""))
    @patch("main.check_refactor_convergence", return_value=(False, ""))
    @patch("main.check_unit_test_convergence", return_value=(False, ""))
    @patch("main.bisect_fixes")
    @patch("main.run_tests")
    @patch("main.record_test_result")
    @patch("main.record_cycle_history")
    @patch("main.parse_harness_output")
    @patch("main.run_coverage_session", return_value="raw output")
    @patch("main.git_rev_parse_head", return_value="abc123")
    @patch("main.write_progress")
    def test_refactor_all_fixes_reverted(
        self,
        mock_wp,
        mock_head,
        mock_session,
        mock_parse,
        mock_record_cycle,
        mock_record_test,
        mock_run_tests,
        mock_bisect,
        mock_ut_conv,
        mock_rf_conv,
        mock_plateau,
        sample_coverage_progress,
        tmp_path,
    ):
        ut_result = {
            "tests_written": [],
            "coverage": {},
            "untestable_code": [{"file": "src/db.py", "barrier": "x"}],
            "bugs_discovered": [],
        }
        rf_result = {
            "fixes_applied": [{"file": "a.py"}, {"file": "b.py"}],
            "new_findings": [],
        }
        mock_parse.side_effect = [ut_result, rf_result]
        mock_run_tests.side_effect = [(True, "ok"), (False, "FAIL")]
        mock_bisect.return_value = (0, 2, 0)

        args = self._make_args()
        progress = sample_coverage_progress
        progress["config"]["max_cycles"] = 1
        progress_path = tmp_path / "progress.json"

        _run_cycle_loop(args, progress, progress_path, tmp_path, "pytest", 1)

        mock_bisect.assert_called_once()

    @patch("main.check_coverage_plateau", return_value=(False, ""))
    @patch("main.check_unit_test_convergence", return_value=(False, ""))
    @patch("main.git_commit_checkpoint")
    @patch("main.git_diff_has_changes")
    @patch("main.run_tests", return_value=(True, "ok"))
    @patch("main.record_test_result")
    @patch("main.record_cycle_history")
    @patch("main.parse_harness_output")
    @patch("main.run_coverage_session", return_value="raw output")
    @patch("main.git_rev_parse_head", return_value="abc123")
    @patch("main.write_progress")
    def test_checkpoint_commit_unit_test(
        self,
        mock_wp,
        mock_head,
        mock_session,
        mock_parse,
        mock_record_cycle,
        mock_record_test,
        mock_run_tests,
        mock_diff,
        mock_commit,
        mock_ut_conv,
        mock_plateau,
        sample_coverage_progress,
        tmp_path,
    ):
        mock_parse.return_value = {
            "tests_written": [],
            "coverage": {},
            "untestable_code": [],
            "bugs_discovered": [],
        }
        mock_diff.return_value = True
        mock_commit.return_value = True

        args = self._make_args(no_commit=False)
        progress = sample_coverage_progress
        progress["config"]["max_cycles"] = 1
        progress_path = tmp_path / "progress.json"

        _run_cycle_loop(args, progress, progress_path, tmp_path, "pytest", 1)

        mock_commit.assert_called()

    @patch("main.check_coverage_plateau", return_value=(False, ""))
    @patch("main.check_unit_test_convergence", return_value=(False, ""))
    @patch("main.git_commit_checkpoint", return_value=False)
    @patch("main.git_diff_has_changes", return_value=True)
    @patch("main.run_tests", return_value=(True, "ok"))
    @patch("main.record_test_result")
    @patch("main.record_cycle_history")
    @patch("main.parse_harness_output")
    @patch("main.run_coverage_session", return_value="raw output")
    @patch("main.git_rev_parse_head", return_value="abc123")
    @patch("main.write_progress")
    def test_checkpoint_failure_disables_commits(
        self,
        mock_wp,
        mock_head,
        mock_session,
        mock_parse,
        mock_record_cycle,
        mock_record_test,
        mock_run_tests,
        mock_diff,
        mock_commit,
        mock_ut_conv,
        mock_plateau,
        sample_coverage_progress,
        tmp_path,
        capsys,
    ):
        mock_parse.return_value = {
            "tests_written": [],
            "coverage": {},
            "untestable_code": [],
            "bugs_discovered": [],
        }
        args = self._make_args(no_commit=False)
        progress = sample_coverage_progress
        progress["config"]["max_cycles"] = 1
        progress_path = tmp_path / "progress.json"

        _run_cycle_loop(args, progress, progress_path, tmp_path, "pytest", 1)

        output = capsys.readouterr().out
        assert "skipping commits" in output.lower() or "Checkpoint failed" in output

    @patch("main.check_coverage_plateau", return_value=(False, ""))
    @patch("main.check_refactor_convergence", return_value=(False, ""))
    @patch("main.check_unit_test_convergence", return_value=(False, ""))
    @patch("main.git_commit_checkpoint", return_value=True)
    @patch("main.git_diff_has_changes", return_value=True)
    @patch("main.run_tests", return_value=(True, "ok"))
    @patch("main.record_test_result")
    @patch("main.record_cycle_history")
    @patch("main.parse_harness_output")
    @patch("main.run_coverage_session", return_value="raw output")
    @patch("main.git_rev_parse_head", return_value="abc123")
    @patch("main.write_progress")
    def test_refactor_checkpoint_commit(
        self,
        mock_wp,
        mock_head,
        mock_session,
        mock_parse,
        mock_record_cycle,
        mock_record_test,
        mock_run_tests,
        mock_diff,
        mock_commit,
        mock_ut_conv,
        mock_rf_conv,
        mock_plateau,
        sample_coverage_progress,
        tmp_path,
        capsys,
    ):
        """Cover the refactor checkpoint commit path (lines 576-585)."""
        ut_result = {
            "tests_written": [],
            "coverage": {},
            "untestable_code": [{"file": "src/db.py", "barrier": "x"}],
            "bugs_discovered": [],
        }
        rf_result = {
            "fixes_applied": [{"file": "src/db.py", "line": 10}],
            "new_findings": [],
        }
        mock_parse.side_effect = [ut_result, rf_result]

        args = self._make_args(no_commit=False)
        progress = sample_coverage_progress
        progress["config"]["max_cycles"] = 1
        progress_path = tmp_path / "progress.json"

        _run_cycle_loop(args, progress, progress_path, tmp_path, "pytest", 1)

        output = capsys.readouterr().out
        assert "refactor(coverage-harness)" in output
        # Commit called at least twice (unit-test + refactor phases)
        assert mock_commit.call_count >= 2

    @patch("main.check_coverage_plateau", return_value=(False, ""))
    @patch("main.check_refactor_convergence", return_value=(False, ""))
    @patch("main.check_unit_test_convergence", return_value=(False, ""))
    @patch("main.git_commit_checkpoint")
    @patch("main.git_diff_has_changes", return_value=True)
    @patch("main.run_tests", return_value=(True, "ok"))
    @patch("main.record_test_result")
    @patch("main.record_cycle_history")
    @patch("main.parse_harness_output")
    @patch("main.run_coverage_session", return_value="raw output")
    @patch("main.git_rev_parse_head", return_value="abc123")
    @patch("main.write_progress")
    def test_refactor_checkpoint_failure_disables_commits(
        self,
        mock_wp,
        mock_head,
        mock_session,
        mock_parse,
        mock_record_cycle,
        mock_record_test,
        mock_run_tests,
        mock_diff,
        mock_commit,
        mock_ut_conv,
        mock_rf_conv,
        mock_plateau,
        sample_coverage_progress,
        tmp_path,
        capsys,
    ):
        """Cover the refactor checkpoint failure path (lines 581-585).

        Unit-test checkpoint succeeds, but refactor checkpoint fails.
        """
        # First call (unit-test checkpoint) succeeds, second (refactor) fails
        mock_commit.side_effect = [True, False]
        ut_result = {
            "tests_written": [],
            "coverage": {},
            "untestable_code": [{"file": "src/db.py", "barrier": "x"}],
            "bugs_discovered": [],
        }
        rf_result = {
            "fixes_applied": [],
            "new_findings": [],
        }
        mock_parse.side_effect = [ut_result, rf_result]

        args = self._make_args(no_commit=False)
        progress = sample_coverage_progress
        progress["config"]["max_cycles"] = 1
        progress_path = tmp_path / "progress.json"

        _run_cycle_loop(args, progress, progress_path, tmp_path, "pytest", 1)

        output = capsys.readouterr().out
        assert "Checkpoint failed" in output
        assert "skipping commits" in output.lower()

    @patch("main.check_coverage_plateau", return_value=(False, ""))
    @patch("main.check_refactor_convergence", return_value=(False, ""))
    @patch("main.check_unit_test_convergence", return_value=(False, ""))
    @patch("main.run_tests", return_value=(True, "ok"))
    @patch("main.record_test_result")
    @patch("main.record_cycle_history")
    @patch("main.parse_harness_output")
    @patch("main.run_coverage_session", return_value="raw output")
    @patch("main.git_rev_parse_head", return_value="abc123")
    @patch("main.write_progress")
    def test_multi_cycle_increments_and_continues(
        self,
        mock_wp,
        mock_head,
        mock_session,
        mock_parse,
        mock_record_cycle,
        mock_record_test,
        mock_run_tests,
        mock_ut_conv,
        mock_rf_conv,
        mock_plateau,
        sample_coverage_progress,
        tmp_path,
    ):
        """Cover the cycle increment path (lines 628-629) by running 2 cycles."""
        ut_result = {
            "tests_written": [],
            "coverage": {"before": 40, "after": 50, "delta": 10},
            "untestable_code": [{"file": "src/db.py", "barrier": "x"}],
            "bugs_discovered": [],
        }
        rf_result = {
            "fixes_applied": [],
            "new_findings": [],
        }
        mock_parse.side_effect = [ut_result, rf_result, ut_result, rf_result]

        args = self._make_args()
        progress = sample_coverage_progress
        progress["config"]["max_cycles"] = 2
        progress["cycle"]["current"] = 1
        progress_path = tmp_path / "progress.json"

        _run_cycle_loop(args, progress, progress_path, tmp_path, "pytest", 2)

        # Should have gone through 2 cycles before cap
        assert progress["termination"]["reason"] == "cap"
        # Cycle should have been incremented to 2 before the cap check
        assert progress["cycle"]["current"] == 2


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------


class TestMain:
    @patch("main._validate_environment", return_value=(None, "claude CLI not found"))
    def test_env_error(self, mock_validate, capsys):
        result = main(["--project-dir", "/tmp"])
        assert result == 1
        output = capsys.readouterr().out
        assert "claude CLI not found" in output

    @patch("main._archive_progress")
    @patch("main.print_report")
    @patch("main._run_cycle_loop")
    @patch("main._print_startup_info")
    @patch("main.git_diff_has_changes", return_value=False)
    @patch("main.make_initial_progress")
    @patch("main._validate_environment", return_value=("pytest", None))
    def test_successful_run(
        self,
        mock_validate,
        mock_init,
        mock_diff,
        mock_startup,
        mock_loop,
        mock_report,
        mock_archive,
        tmp_path,
    ):
        mock_init.return_value = {
            "config": {
                "max_cycles": 5,
                "base_commit": "abc123",
                "test_command": "pytest",
                "scope": "",
            },
            "cycle": {"current": 1},
            "coverage": {
                "baseline": None,
                "current": None,
                "tool": None,
                "history": [],
            },
            "tests_created": [],
            "untestable_code": [],
            "refactor_findings": [],
            "bugs_discovered": [],
            "cycle_history": [],
            "test_results": {"last_full_run": None, "last_run_output_summary": None},
            "termination": {"reason": None, "message": None},
        }
        result = main(["--project-dir", str(tmp_path), "--no-commit"])
        assert result == 0
        mock_loop.assert_called_once()
        mock_report.assert_called_once()
        mock_archive.assert_called_once()

    @patch("main.git_diff_has_changes", return_value=True)
    @patch("main.make_initial_progress")
    @patch("main._validate_environment", return_value=("pytest", None))
    def test_uncommitted_changes_blocked(
        self,
        mock_validate,
        mock_init,
        mock_diff,
        tmp_path,
        capsys,
    ):
        mock_init.return_value = {
            "config": {
                "max_cycles": 5,
                "base_commit": "abc123",
                "test_command": "pytest",
                "scope": "",
            },
            "cycle": {"current": 1},
        }
        result = main(["--project-dir", str(tmp_path)])
        assert result == 1
        output = capsys.readouterr().out
        assert "Uncommitted changes" in output

    @patch("main.git_diff_has_changes", return_value=True)
    @patch("main.make_initial_progress")
    @patch("main._validate_environment", return_value=("pytest", None))
    def test_uncommitted_changes_allowed_with_no_commit(
        self,
        mock_validate,
        mock_init,
        mock_diff,
        tmp_path,
    ):
        """--no-commit flag should bypass uncommitted changes check."""
        mock_init.return_value = {
            "config": {
                "max_cycles": 5,
                "base_commit": "abc123",
                "test_command": "pytest",
                "scope": "",
            },
            "cycle": {"current": 1},
            "coverage": {
                "baseline": None,
                "current": None,
                "tool": None,
                "history": [],
            },
            "tests_created": [],
            "untestable_code": [],
            "refactor_findings": [],
            "bugs_discovered": [],
            "cycle_history": [],
            "test_results": {"last_full_run": None, "last_run_output_summary": None},
            "termination": {"reason": None, "message": None},
        }
        with patch("main._print_startup_info"), patch("main._run_cycle_loop"), patch(
            "main.print_report"
        ), patch("main._archive_progress"):
            result = main(["--project-dir", str(tmp_path), "--no-commit"])
        assert result == 0

    @patch("main.make_initial_progress")
    @patch("main._validate_environment", return_value=("pytest", None))
    def test_no_base_commit(self, mock_validate, mock_init, tmp_path, capsys):
        mock_init.return_value = {
            "config": {
                "max_cycles": 5,
                "base_commit": "",
                "test_command": "pytest",
                "scope": "",
            },
            "cycle": {"current": 1},
        }
        result = main(["--project-dir", str(tmp_path)])
        assert result == 1
        output = capsys.readouterr().out
        assert "HEAD commit" in output

    def test_clamp_cycles_high(self, capsys):
        with patch("main._validate_environment", return_value=(None, "stop")):
            main(["--max-cycles", "99"])
        output = capsys.readouterr().out
        assert "clamped" in output.lower()

    def test_clamp_cycles_low(self, capsys):
        with patch("main._validate_environment", return_value=(None, "stop")):
            main(["--max-cycles", "0"])
        output = capsys.readouterr().out
        assert "clamped" in output.lower()

    @patch("main._handle_interrupt")
    @patch("main._run_cycle_loop", side_effect=KeyboardInterrupt)
    @patch("main._print_startup_info")
    @patch("main.git_diff_has_changes", return_value=False)
    @patch("main.make_initial_progress")
    @patch("main._validate_environment", return_value=("pytest", None))
    def test_keyboard_interrupt(
        self,
        mock_validate,
        mock_init,
        mock_diff,
        mock_startup,
        mock_loop,
        mock_interrupt,
        tmp_path,
    ):
        mock_init.return_value = {
            "config": {
                "max_cycles": 5,
                "base_commit": "abc123",
                "test_command": "pytest",
                "scope": "",
            },
            "cycle": {"current": 1},
            "coverage": {
                "baseline": None,
                "current": None,
                "tool": None,
                "history": [],
            },
            "tests_created": [],
            "untestable_code": [],
            "refactor_findings": [],
            "bugs_discovered": [],
            "cycle_history": [],
            "test_results": {"last_full_run": None, "last_run_output_summary": None},
            "termination": {"reason": None, "message": None},
        }
        result = main(["--project-dir", str(tmp_path), "--no-commit"])
        assert result == 0
        mock_interrupt.assert_called_once()

    @patch("main._load_resumed_progress")
    @patch("main._validate_environment", return_value=("pytest", None))
    def test_resume_error(self, mock_validate, mock_resume, tmp_path, capsys):
        mock_resume.return_value = (None, "No progress file found")
        result = main(["--project-dir", str(tmp_path), "--resume"])
        assert result == 1
        output = capsys.readouterr().out
        assert "No progress file" in output

    @patch("main._archive_progress")
    @patch("main.print_report")
    @patch("main._run_cycle_loop")
    @patch("main._print_startup_info")
    @patch("main.git_diff_has_changes", return_value=False)
    @patch("main._load_resumed_progress")
    @patch("main._validate_environment", return_value=("pytest --cov", None))
    def test_resume_success(
        self,
        mock_validate,
        mock_resume,
        mock_diff,
        mock_startup,
        mock_loop,
        mock_report,
        mock_archive,
        tmp_path,
    ):
        mock_resume.return_value = (
            {
                "harness": "test-coverage",
                "config": {
                    "max_cycles": 5,
                    "base_commit": "abc123",
                    "test_command": "old-cmd",
                    "scope": "",
                },
                "cycle": {"current": 2},
                "coverage": {
                    "baseline": 40,
                    "current": 55,
                    "tool": "pytest-cov",
                    "history": [],
                },
                "tests_created": [],
                "untestable_code": [],
                "refactor_findings": [],
                "bugs_discovered": [],
                "cycle_history": [],
                "test_results": {
                    "last_full_run": None,
                    "last_run_output_summary": None,
                },
                "termination": {"reason": None, "message": None},
            },
            None,
        )
        result = main(["--project-dir", str(tmp_path), "--resume", "--no-commit"])
        assert result == 0
        # Verify test_command was synced from freshly detected value
        resumed_progress = mock_resume.return_value[0]
        assert resumed_progress["config"]["test_command"] == "pytest --cov"

    @patch("main._archive_progress")
    @patch("main.print_report")
    @patch("main._run_cycle_loop")
    @patch("main._print_startup_info")
    @patch("main.git_diff_has_changes", return_value=False)
    @patch("main.make_initial_progress")
    @patch("main._validate_environment", return_value=("pytest", None))
    def test_overwrite_existing_progress(
        self,
        mock_validate,
        mock_init,
        mock_diff,
        mock_startup,
        mock_loop,
        mock_report,
        mock_archive,
        tmp_path,
        capsys,
    ):
        # Create an existing progress file
        progress_file = tmp_path / ".claude" / "test-coverage-progress.json"
        progress_file.parent.mkdir(parents=True, exist_ok=True)
        progress_file.write_text("{}", encoding="utf-8")

        mock_init.return_value = {
            "config": {
                "max_cycles": 5,
                "base_commit": "abc123",
                "test_command": "pytest",
                "scope": "",
            },
            "cycle": {"current": 1},
            "coverage": {
                "baseline": None,
                "current": None,
                "tool": None,
                "history": [],
            },
            "tests_created": [],
            "untestable_code": [],
            "refactor_findings": [],
            "bugs_discovered": [],
            "cycle_history": [],
            "test_results": {"last_full_run": None, "last_run_output_summary": None},
            "termination": {"reason": None, "message": None},
        }
        result = main(["--project-dir", str(tmp_path), "--no-commit"])
        assert result == 0
        output = capsys.readouterr().out
        assert "Overwriting" in output
