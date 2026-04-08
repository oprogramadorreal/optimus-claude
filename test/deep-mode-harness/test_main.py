import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
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
    _build_argument_parser,
    _capture_pr_description,
    _handle_interrupt,
    _handle_safe_exit,
    _load_resumed_progress,
    _mark_combined_regression,
    _populate_branch_scope,
    _print_startup_info,
    _promote_actionable_fixes,
    _record_iteration_history,
    _recover_from_missing_output,
    _register_iteration_findings,
    _run_session_with_retry,
    _should_soft_exit,
    _test_and_reconcile_fixes,
    _validate_environment,
    main,
)

# Fixtures are provided by conftest.py (sample_progress, sample_fix)

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
# _should_soft_exit
# ---------------------------------------------------------------------------


class TestShouldSoftExit:
    """Diminishing-returns soft-exit gate: stops the harness when yield
    plateaus at ≤1 new finding for two consecutive iterations after iter 3,
    with no active retry work in flight."""

    def test_fires_on_low_yield_plateau(self, sample_progress):
        # Iter 3 has 1 new finding, iter 4 has 1 new finding, no reverts
        _record_iteration_history(sample_progress, 3, 1, 1, 0, True)
        _record_iteration_history(sample_progress, 4, 1, 1, 0, True)
        assert _should_soft_exit(sample_progress, iteration=4, new_count=1, reverted_count=0)

    def test_does_not_fire_before_min_iteration(self, sample_progress):
        # Iter 1 + iter 2 low yield — still too early to soft-exit
        _record_iteration_history(sample_progress, 1, 1, 1, 0, True)
        _record_iteration_history(sample_progress, 2, 1, 1, 0, True)
        assert not _should_soft_exit(sample_progress, iteration=2, new_count=1, reverted_count=0)

    def test_does_not_fire_when_current_yield_exceeds_threshold(self, sample_progress):
        _record_iteration_history(sample_progress, 3, 1, 1, 0, True)
        _record_iteration_history(sample_progress, 4, 5, 5, 0, True)
        assert not _should_soft_exit(sample_progress, iteration=4, new_count=5, reverted_count=0)

    def test_does_not_fire_when_prior_yield_exceeds_threshold(self, sample_progress):
        # Prior iter had 3 findings — not a plateau yet
        _record_iteration_history(sample_progress, 3, 3, 3, 0, True)
        _record_iteration_history(sample_progress, 4, 1, 1, 0, True)
        assert not _should_soft_exit(sample_progress, iteration=4, new_count=1, reverted_count=0)

    def test_blocked_by_current_iter_reverts(self, sample_progress):
        # Even with low yield, active retry work must block the exit
        _record_iteration_history(sample_progress, 3, 1, 0, 1, False)
        _record_iteration_history(sample_progress, 4, 1, 0, 1, False)
        assert not _should_soft_exit(sample_progress, iteration=4, new_count=1, reverted_count=1)

    def test_blocked_by_prior_iter_reverts(self, sample_progress):
        # Prior iter had a reverted fix — harness is still recovering, don't exit
        _record_iteration_history(sample_progress, 3, 1, 0, 1, False)
        _record_iteration_history(sample_progress, 4, 1, 1, 0, True)
        assert not _should_soft_exit(sample_progress, iteration=4, new_count=1, reverted_count=0)

    def test_requires_window_of_history(self, sample_progress):
        # Only one iteration recorded — can't plateau without a prior entry
        _record_iteration_history(sample_progress, 3, 1, 1, 0, True)
        assert not _should_soft_exit(sample_progress, iteration=3, new_count=1, reverted_count=0)

    def test_zero_yield_also_qualifies_as_plateau(self, sample_progress):
        # 0 ≤ threshold — 0/0 across two iters still counts as plateau
        _record_iteration_history(sample_progress, 3, 0, 0, 0, True)
        _record_iteration_history(sample_progress, 4, 0, 0, 0, True)
        assert _should_soft_exit(sample_progress, iteration=4, new_count=0, reverted_count=0)


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
# _promote_actionable_fixes
# ---------------------------------------------------------------------------


def _make_finding(file, line, category, pre, post):
    return {
        "file": file,
        "line": line,
        "category": category,
        "summary": "x",
        "pre_edit_content": pre,
        "post_edit_content": post,
    }


class TestPromoteActionableFixes:
    def test_noop_when_flag_false(self):
        finding = _make_finding("a.md", 1, "doc", "old", "new")
        result = {
            "new_findings": [finding],
            "fixes_applied": [],
            "no_actionable_fixes": False,
        }
        assert _promote_actionable_fixes(result) == 0
        assert result["fixes_applied"] == []
        assert result["no_actionable_fixes"] is False

    def test_noop_when_no_findings_have_swap_pairs(self):
        # All findings are advisories with empty pre/post — typical
        # legitimate "no actionable" case on a real coding project.
        advisory = _make_finding("a.py", 1, "test-gap", "", "")
        result = {
            "new_findings": [advisory],
            "fixes_applied": [],
            "no_actionable_fixes": True,
        }
        assert _promote_actionable_fixes(result) == 0
        assert result["fixes_applied"] == []
        assert result["no_actionable_fixes"] is True

    def test_promotes_finding_with_valid_swap_pair(self):
        finding = _make_finding("a.md", 1, "doc", "old line", "new line")
        result = {
            "new_findings": [finding],
            "fixes_applied": [],
            "no_actionable_fixes": True,
        }
        assert _promote_actionable_fixes(result) == 1
        assert result["fixes_applied"] == [finding]
        assert result["no_actionable_fixes"] is False

    def test_promotes_only_actionable_in_mixed_set(self):
        actionable = _make_finding("a.md", 1, "doc", "old", "new")
        advisory = _make_finding("b.py", 2, "test-gap", "", "")
        result = {
            "new_findings": [actionable, advisory],
            "fixes_applied": [],
            "no_actionable_fixes": True,
        }
        assert _promote_actionable_fixes(result) == 1
        assert result["fixes_applied"] == [actionable]
        assert result["no_actionable_fixes"] is False

    def test_promotes_deletion_fix_with_empty_post(self):
        # Empty post_edit_content is valid per harness-mode.md — represents
        # a deletion fix (remove the matched code).
        deletion = _make_finding("a.py", 1, "dead-code", "dead_call()", "")
        result = {
            "new_findings": [deletion],
            "fixes_applied": [],
            "no_actionable_fixes": True,
        }
        assert _promote_actionable_fixes(result) == 1
        assert result["fixes_applied"] == [deletion]
        assert result["no_actionable_fixes"] is False

    def test_skips_finding_with_empty_pre(self):
        # Empty pre_edit_content cannot be applied — apply_single_fix
        # refuses empty find strings.
        no_pre = _make_finding("a.py", 1, "x", "", "new")
        result = {
            "new_findings": [no_pre],
            "fixes_applied": [],
            "no_actionable_fixes": True,
        }
        assert _promote_actionable_fixes(result) == 0
        assert result["fixes_applied"] == []
        assert result["no_actionable_fixes"] is True

    def test_skips_finding_with_none_post(self):
        no_post = _make_finding("a.py", 1, "x", "old", None)
        result = {
            "new_findings": [no_post],
            "fixes_applied": [],
            "no_actionable_fixes": True,
        }
        assert _promote_actionable_fixes(result) == 0
        assert result["fixes_applied"] == []
        assert result["no_actionable_fixes"] is True

    def test_skips_noop_swap(self):
        # pre == post is not a real edit.
        noop = _make_finding("a.py", 1, "x", "same", "same")
        result = {
            "new_findings": [noop],
            "fixes_applied": [],
            "no_actionable_fixes": True,
        }
        assert _promote_actionable_fixes(result) == 0
        assert result["fixes_applied"] == []
        assert result["no_actionable_fixes"] is True

    def test_does_not_double_register_already_applied(self):
        # If the finding somehow appears in both new_findings and
        # fixes_applied (model duplicated), don't re-add it.
        finding = _make_finding("a.md", 1, "doc", "old", "new")
        result = {
            "new_findings": [finding],
            "fixes_applied": [finding],
            "no_actionable_fixes": True,
        }
        assert _promote_actionable_fixes(result) == 0
        assert result["fixes_applied"] == [finding]
        # Flag stays True because we promoted nothing — but the regression
        # this guards against (silent drop of actionable fixes) doesn't
        # apply when fixes_applied already has the finding. Caller will
        # still hit the no_actionable_fixes branch with applied_count=1.

    def test_handles_missing_new_findings(self):
        result = {"no_actionable_fixes": True}
        assert _promote_actionable_fixes(result) == 0

    def test_handles_missing_fixes_applied_key(self):
        finding = _make_finding("a.md", 1, "doc", "old", "new")
        result = {
            "new_findings": [finding],
            "no_actionable_fixes": True,
        }
        assert _promote_actionable_fixes(result) == 1
        assert result["fixes_applied"] == [finding]
        assert result["no_actionable_fixes"] is False

    def test_logs_promotion_message(self, capsys):
        finding = _make_finding("a.md", 1, "doc", "old", "new")
        result = {
            "new_findings": [finding],
            "fixes_applied": [],
            "no_actionable_fixes": True,
        }
        _promote_actionable_fixes(result)
        out = capsys.readouterr().out
        assert "no_actionable_fixes=true" in out
        assert "1 finding" in out


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


# ---------------------------------------------------------------------------
# _build_argument_parser
# ---------------------------------------------------------------------------


class TestBuildArgumentParser:
    def test_default_values(self):
        parser = _build_argument_parser()
        args = parser.parse_args(["--skill", "code-review"])
        assert args.skill == "code-review"
        assert args.max_iterations == 8
        assert args.scope == ""
        assert args.resume is False
        assert args.no_commit is False
        assert args.verbose is False
        assert args.test_command == ""
        assert args.project_dir == "."

    def test_refactor_skill(self):
        parser = _build_argument_parser()
        args = parser.parse_args(["--skill", "refactor", "--max-iterations", "12"])
        assert args.skill == "refactor"
        assert args.max_iterations == 12

    def test_allowed_tools_default_const(self):
        parser = _build_argument_parser()
        args = parser.parse_args(["--skill", "code-review", "--allowed-tools"])
        assert "Read" in args.allowed_tools

    def test_allowed_tools_explicit(self):
        parser = _build_argument_parser()
        args = parser.parse_args(
            ["--skill", "code-review", "--allowed-tools", "Read,Grep"]
        )
        assert args.allowed_tools == "Read,Grep"

    def test_focus_testability(self):
        parser = _build_argument_parser()
        args = parser.parse_args(["--skill", "refactor", "--focus", "testability"])
        assert args.focus == "testability"

    def test_focus_guidelines(self):
        parser = _build_argument_parser()
        args = parser.parse_args(["--skill", "refactor", "--focus", "guidelines"])
        assert args.focus == "guidelines"

    def test_focus_default_empty(self):
        parser = _build_argument_parser()
        args = parser.parse_args(["--skill", "refactor"])
        assert args.focus == ""

    def test_focus_invalid_rejected(self):
        parser = _build_argument_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--skill", "refactor", "--focus", "invalid"])


# ---------------------------------------------------------------------------
# _print_startup_info
# ---------------------------------------------------------------------------


class TestPrintStartupInfo:
    def test_prints_key_info(self, capsys, sample_progress):
        args = SimpleNamespace(skill="code-review")
        _print_startup_info(args, sample_progress)
        output = capsys.readouterr().out
        assert "code-review" in output
        assert "npm test" in output
        assert "abc12345" in output
        assert "Estimated messages" in output

    def test_refactor_estimates_fewer_agents(self, capsys, sample_progress):
        args = SimpleNamespace(skill="refactor")
        _print_startup_info(args, sample_progress)
        output = capsys.readouterr().out
        # refactor = 4 agents/iter vs code-review = 7; estimated messages differ
        assert "Estimated messages" in output

    def test_prints_focus_when_active(self, capsys, sample_progress):
        sample_progress["config"]["focus"] = "testability"
        args = SimpleNamespace(skill="refactor")
        _print_startup_info(args, sample_progress)
        output = capsys.readouterr().out
        assert "Focus: testability" in output

    def test_omits_focus_when_empty(self, capsys, sample_progress):
        args = SimpleNamespace(skill="refactor")
        _print_startup_info(args, sample_progress)
        output = capsys.readouterr().out
        assert "Focus:" not in output


# ---------------------------------------------------------------------------
# _handle_safe_exit
# ---------------------------------------------------------------------------


class TestHandleSafeExit:
    @patch("main.git_diff_has_changes", return_value=False)
    @patch("main.write_progress")
    def test_no_changes_sets_termination(
        self, mock_write, mock_diff, sample_progress, tmp_path
    ):
        args = SimpleNamespace(no_commit=False)
        _handle_safe_exit(
            sample_progress,
            tmp_path / "progress.json",
            args,
            "npm test",
            tmp_path,
            None,
            "abc123",
            reason="convergence",
            message="No new findings",
            log_message="Convergence",
            new_count=0,
        )
        assert sample_progress["termination"]["reason"] == "convergence"
        assert len(sample_progress["iteration_history"]) == 1

    @patch("main.git_commit_checkpoint", return_value=True)
    @patch("main.git_diff_has_changes", side_effect=[True, True])
    @patch("main.run_tests", return_value=(True, "all pass"))
    @patch("main.record_test_result")
    @patch("main.write_progress")
    def test_changes_with_passing_tests_commits(
        self,
        mock_write,
        mock_record,
        mock_run_tests,
        mock_diff,
        mock_commit,
        sample_progress,
        tmp_path,
    ):
        args = SimpleNamespace(no_commit=False)
        _handle_safe_exit(
            sample_progress,
            tmp_path / "progress.json",
            args,
            "npm test",
            tmp_path,
            None,
            "abc123",
            reason="convergence",
            message="No new findings",
            log_message="Convergence",
            new_count=0,
        )
        mock_commit.assert_called_once()

    @patch("main.restore_working_tree")
    @patch("main.git_diff_has_changes", return_value=True)
    @patch("main.run_tests", return_value=(False, "FAIL"))
    @patch("main.record_test_result")
    @patch("main.write_progress")
    def test_changes_with_failing_tests_reverts(
        self,
        mock_write,
        mock_record,
        mock_run_tests,
        mock_diff,
        mock_restore,
        sample_progress,
        tmp_path,
    ):
        args = SimpleNamespace(no_commit=False)
        _handle_safe_exit(
            sample_progress,
            tmp_path / "progress.json",
            args,
            "npm test",
            tmp_path,
            "stash-ref",
            "abc123",
            reason="no-actionable",
            message="No fixes",
            log_message="No actionable fixes",
            new_count=2,
        )
        mock_restore.assert_called_once_with("stash-ref", "abc123", tmp_path)


# ---------------------------------------------------------------------------
# _run_session_with_retry
# ---------------------------------------------------------------------------


class TestRunSessionWithRetry:
    @patch("main.run_skill_session", return_value="output")
    def test_success_first_attempt(self, mock_session, sample_progress, tmp_path):
        args = SimpleNamespace(timeout=900)
        result = _run_session_with_retry(
            args, sample_progress, tmp_path / "p.json", None, "abc", tmp_path, 1
        )
        assert result == "output"
        assert mock_session.call_count == 1

    @patch("main.write_progress")
    @patch("main.restore_working_tree")
    @patch(
        "main.run_skill_session",
        side_effect=[RuntimeError("crash"), "output"],
    )
    def test_retries_on_first_failure(
        self, mock_session, mock_restore, mock_write, sample_progress, tmp_path
    ):
        args = SimpleNamespace(timeout=900)
        result = _run_session_with_retry(
            args, sample_progress, tmp_path / "p.json", None, "abc", tmp_path, 1
        )
        assert result == "output"
        assert mock_session.call_count == 2

    @patch("main.write_progress")
    @patch("main.restore_working_tree")
    @patch(
        "main.run_skill_session",
        side_effect=[RuntimeError("crash"), RuntimeError("crash2")],
    )
    def test_returns_none_after_two_failures(
        self, mock_session, mock_restore, mock_write, sample_progress, tmp_path
    ):
        args = SimpleNamespace(timeout=900)
        result = _run_session_with_retry(
            args, sample_progress, tmp_path / "p.json", None, "abc", tmp_path, 1
        )
        assert result is None
        assert sample_progress["termination"]["reason"] == "crash"

    @patch("main.write_progress")
    @patch("main.restore_working_tree")
    @patch(
        "main.run_skill_session",
        side_effect=subprocess.TimeoutExpired("claude", 900),
    )
    def test_handles_timeout(
        self, mock_session, mock_restore, mock_write, sample_progress, tmp_path
    ):
        args = SimpleNamespace(timeout=900)
        result = _run_session_with_retry(
            args, sample_progress, tmp_path / "p.json", None, "abc", tmp_path, 1
        )
        assert result is None


# ---------------------------------------------------------------------------
# _recover_from_missing_output
# ---------------------------------------------------------------------------


class TestRecoverFromMissingOutput:
    @patch("main.git_diff_has_changes", return_value=False)
    def test_no_changes_returns_convergence(self, mock_diff, sample_progress, tmp_path):
        result = _recover_from_missing_output(
            "", "npm test", tmp_path, None, "abc", sample_progress, tmp_path / "p.json"
        )
        assert result is not None
        assert result["no_new_findings"] is True

    @patch("main.restore_working_tree")
    @patch("main.record_test_result")
    @patch("main.run_tests", return_value=(True, "pass"))
    @patch("main.git_diff_has_changes", return_value=True)
    def test_changes_passing_tests_reverts_and_returns_no_actionable(
        self,
        mock_diff,
        mock_tests,
        mock_record,
        mock_restore,
        sample_progress,
        tmp_path,
    ):
        result = _recover_from_missing_output(
            "some output",
            "npm test",
            tmp_path,
            "stash-ref",
            "abc",
            sample_progress,
            tmp_path / "p.json",
        )
        assert result is not None
        assert result["no_actionable_fixes"] is True
        mock_restore.assert_called_once_with("stash-ref", "abc", tmp_path)

    @patch("main.write_progress")
    @patch("main.restore_working_tree")
    @patch("main.record_test_result")
    @patch("main.run_tests", return_value=(False, "FAIL\nerror details"))
    @patch("main.git_diff_has_changes", return_value=True)
    def test_changes_failing_tests_reverts(
        self,
        mock_diff,
        mock_tests,
        mock_record,
        mock_restore,
        mock_write,
        sample_progress,
        tmp_path,
    ):
        result = _recover_from_missing_output(
            "x",
            "npm test",
            tmp_path,
            "stash",
            "abc",
            sample_progress,
            tmp_path / "p.json",
        )
        assert result is None
        assert sample_progress["termination"]["reason"] == "parse-failure"
        mock_restore.assert_called_once()

    @patch("main.restore_working_tree")
    @patch("main.record_test_result")
    @patch("main.run_tests", return_value=(True, "pass"))
    @patch("main.git_diff_has_changes", return_value=True)
    def test_short_output_prints_hint(
        self,
        mock_diff,
        mock_tests,
        mock_record,
        mock_restore,
        sample_progress,
        tmp_path,
        capsys,
    ):
        _recover_from_missing_output(
            "hi",
            "npm test",
            tmp_path,
            None,
            "abc",
            sample_progress,
            tmp_path / "p.json",
        )
        assert "very short" in capsys.readouterr().out

    @patch("main.restore_working_tree")
    @patch("main.record_test_result")
    @patch("main.run_tests", return_value=(True, "pass"))
    @patch("main.git_diff_has_changes", return_value=True)
    def test_empty_output_prints_hint(
        self,
        mock_diff,
        mock_tests,
        mock_record,
        mock_restore,
        sample_progress,
        tmp_path,
        capsys,
    ):
        _recover_from_missing_output(
            "",
            "npm test",
            tmp_path,
            None,
            "abc",
            sample_progress,
            tmp_path / "p.json",
        )
        assert "no output" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# _test_and_reconcile_fixes
# ---------------------------------------------------------------------------


class TestTestAndReconcileFixes:
    def test_no_fixes_returns_early(self, sample_progress):
        fixed, reverted, passed, all_rev = _test_and_reconcile_fixes(
            [], "npm test", "/tmp", sample_progress, None, "abc"
        )
        assert fixed == 0 and reverted == 0 and passed is True and all_rev is False

    @patch("main.mark_all_fixed")
    @patch("main.record_test_result")
    @patch("main.run_tests", return_value=(True, "pass"))
    def test_all_pass(self, mock_tests, mock_record, mock_mark, sample_progress):
        fixes = [{"file": "a.js", "line": 1, "category": "bug", "summary": "x"}]
        fixed, reverted, passed, all_rev = _test_and_reconcile_fixes(
            fixes, "npm test", "/tmp", sample_progress, None, "abc"
        )
        assert fixed == 1
        assert reverted == 0
        assert passed is True
        mock_mark.assert_called_once()

    @patch("main.bisect_fixes", return_value=(1, 1, 0))
    @patch("main.record_test_result")
    @patch("main.run_tests", side_effect=[(False, "FAIL"), (True, "pass")])
    def test_bisect_on_failure(
        self, mock_tests, mock_record, mock_bisect, sample_progress
    ):
        fixes = [
            {"file": "a.js", "line": 1, "category": "bug", "summary": "x"},
            {"file": "b.js", "line": 2, "category": "bug", "summary": "y"},
        ]
        fixed, reverted, passed, all_rev = _test_and_reconcile_fixes(
            fixes, "npm test", "/tmp", sample_progress, None, "abc"
        )
        assert fixed == 1
        assert reverted == 1
        mock_bisect.assert_called_once()

    @patch("main._mark_combined_regression", return_value=2)
    @patch("main.restore_working_tree")
    @patch("main.bisect_fixes", return_value=(2, 0, 0))
    @patch("main.record_test_result")
    @patch("main.run_tests", side_effect=[(False, "FAIL"), (False, "FAIL combined")])
    def test_combined_interaction_bug_reverts_all(
        self,
        mock_tests,
        mock_record,
        mock_bisect,
        mock_restore,
        mock_mark_regression,
        sample_progress,
    ):
        fixes = [
            {"file": "a.js", "line": 1, "category": "bug", "summary": "x"},
            {"file": "b.js", "line": 2, "category": "bug", "summary": "y"},
        ]
        fixed, reverted, passed, all_rev = _test_and_reconcile_fixes(
            fixes, "npm test", "/tmp", sample_progress, "stash", "abc"
        )
        assert fixed == 0
        assert reverted == 2
        assert all_rev is True
        mock_restore.assert_called_once()

    @patch("main.bisect_fixes", return_value=(0, 2, 0))
    @patch("main.record_test_result")
    @patch("main.run_tests", return_value=(False, "FAIL"))
    def test_all_reverted_flag(
        self, mock_tests, mock_record, mock_bisect, sample_progress
    ):
        fixes = [
            {"file": "a.js", "line": 1, "category": "bug", "summary": "x"},
            {"file": "b.js", "line": 2, "category": "bug", "summary": "y"},
        ]
        fixed, reverted, passed, all_rev = _test_and_reconcile_fixes(
            fixes, "npm test", "/tmp", sample_progress, None, "abc"
        )
        assert all_rev is True
        assert fixed == 0


# ---------------------------------------------------------------------------
# _handle_interrupt
# ---------------------------------------------------------------------------


class TestHandleInterrupt:
    @patch("main.print_report")
    @patch("main.write_progress")
    @patch("main.git_commit_checkpoint")
    @patch("main.git_diff_has_changes", return_value=True)
    def test_commits_and_saves_on_interrupt(
        self, mock_diff, mock_commit, mock_write, mock_report, sample_progress, tmp_path
    ):
        args = SimpleNamespace(no_commit=False)
        progress_path = tmp_path / "progress.json"
        _handle_interrupt(args, sample_progress, progress_path, tmp_path)
        mock_commit.assert_called_once()
        mock_write.assert_called_once()
        assert sample_progress["termination"]["reason"] == "interrupted"
        mock_report.assert_called_once_with(sample_progress)

    @patch("main.print_report")
    @patch("main.write_progress")
    @patch("main.git_diff_has_changes", return_value=False)
    def test_skips_commit_when_no_changes(
        self, mock_diff, mock_write, mock_report, sample_progress, tmp_path
    ):
        args = SimpleNamespace(no_commit=False)
        _handle_interrupt(args, sample_progress, tmp_path / "p.json", tmp_path)
        assert sample_progress["termination"]["reason"] == "interrupted"

    @patch("main.print_report")
    @patch("main.write_progress")
    @patch("main.git_diff_has_changes", return_value=True)
    def test_skips_commit_when_no_commit_flag(
        self, mock_diff, mock_write, mock_report, sample_progress, tmp_path
    ):
        args = SimpleNamespace(no_commit=True)
        _handle_interrupt(args, sample_progress, tmp_path / "p.json", tmp_path)
        assert sample_progress["termination"]["reason"] == "interrupted"

    @patch("main.print_report")
    @patch("main.write_progress")
    @patch("main.git_commit_checkpoint")
    @patch("main.git_diff_has_changes", return_value=True)
    def test_records_history_when_missing(
        self, mock_diff, mock_commit, mock_write, mock_report, sample_progress, tmp_path
    ):
        """If interrupted before _record_iteration_history ran, it records a stub."""
        args = SimpleNamespace(no_commit=False)
        sample_progress["iteration"]["current"] = 3
        _handle_interrupt(args, sample_progress, tmp_path / "p.json", tmp_path)
        assert len(sample_progress["iteration_history"]) == 1
        assert sample_progress["iteration_history"][0]["iteration"] == 3

    @patch("main.print_report")
    @patch("main.write_progress")
    @patch("main.git_commit_checkpoint")
    @patch("main.git_diff_has_changes", return_value=True)
    def test_skips_history_when_already_recorded(
        self, mock_diff, mock_commit, mock_write, mock_report, sample_progress, tmp_path
    ):
        """If history was already recorded for this iteration, don't duplicate."""
        args = SimpleNamespace(no_commit=False)
        sample_progress["iteration"]["current"] = 2
        sample_progress["iteration_history"] = [{"iteration": 2}]
        _handle_interrupt(args, sample_progress, tmp_path / "p.json", tmp_path)
        # Should still have exactly 1 entry, not 2
        assert len(sample_progress["iteration_history"]) == 1


# ---------------------------------------------------------------------------
# _populate_branch_scope
# ---------------------------------------------------------------------------


def _empty_scope_progress():
    return {
        "scope_files": {"current": []},
        "config": {
            "scope": {"mode": "local-changes", "paths": [], "base_ref": None},
            "pr_description": None,
        },
    }


class TestPopulateBranchScope:
    @patch("main.git_discover_branch_files")
    def test_populates_files_base_and_mode(self, mock_discover, capsys):
        mock_discover.return_value = (["src/a.py", "src/b.py"], "origin/main")
        progress = _empty_scope_progress()

        _populate_branch_scope(progress, "/tmp")

        assert progress["scope_files"]["current"] == ["src/a.py", "src/b.py"]
        assert progress["config"]["scope"]["base_ref"] == "origin/main"
        assert progress["config"]["scope"]["mode"] == "branch-diff"
        assert "Scope: 2 files changed vs origin/main" in capsys.readouterr().out

    @patch("main.git_discover_branch_files")
    def test_skips_when_scope_already_populated(self, mock_discover):
        progress = _empty_scope_progress()
        progress["scope_files"]["current"] = ["existing.py"]

        _populate_branch_scope(progress, "/tmp")

        mock_discover.assert_not_called()
        assert progress["scope_files"]["current"] == ["existing.py"]
        assert progress["config"]["scope"]["mode"] == "local-changes"

    @patch("main.git_discover_branch_files", return_value=([], None))
    def test_no_files_warns_and_leaves_scope_empty(self, mock_discover, capsys):
        progress = _empty_scope_progress()

        _populate_branch_scope(progress, "/tmp")

        assert progress["scope_files"]["current"] == []
        assert progress["config"]["scope"]["mode"] == "local-changes"
        assert "WARNING: No changed files detected" in capsys.readouterr().out

    @patch("main.git_discover_branch_files")
    def test_forwards_scope_path_as_filter(self, mock_discover, capsys):
        """--scope src/auth is forwarded to git_discover_branch_files as
        path_filter, and mode is set to 'directory' rather than 'branch-diff'."""
        mock_discover.return_value = (
            ["src/auth/login.py", "src/auth/session.py"],
            "origin/main",
        )
        progress = _empty_scope_progress()
        progress["config"]["scope"]["paths"] = ["src/auth"]
        progress["config"]["scope"]["mode"] = "directory"

        _populate_branch_scope(progress, "/tmp")

        mock_discover.assert_called_once_with("/tmp", path_filter="src/auth")
        assert progress["scope_files"]["current"] == [
            "src/auth/login.py",
            "src/auth/session.py",
        ]
        assert progress["config"]["scope"]["mode"] == "directory"
        assert "filtered by src/auth" in capsys.readouterr().out

    @patch("main.git_discover_branch_files")
    def test_no_scope_path_uses_branch_diff_mode(self, mock_discover):
        mock_discover.return_value = (["src/a.py"], "origin/main")
        progress = _empty_scope_progress()

        _populate_branch_scope(progress, "/tmp")

        mock_discover.assert_called_once_with("/tmp", path_filter=None)
        assert progress["config"]["scope"]["mode"] == "branch-diff"


# ---------------------------------------------------------------------------
# _capture_pr_description
# ---------------------------------------------------------------------------


class TestCapturePrDescription:
    @patch("main.git_fetch_open_pr_description")
    def test_stores_pr_info_when_available(self, mock_pr, capsys):
        mock_pr.return_value = {
            "title": "Fix auth bug",
            "body": "Adds null check.",
            "base_ref": "origin/main",
        }
        progress = _empty_scope_progress()

        _capture_pr_description(progress, "/tmp")

        assert progress["config"]["pr_description"] == {
            "title": "Fix auth bug",
            "body": "Adds null check.",
            "base_ref": "origin/main",
        }
        assert "Captured PR description: Fix auth bug" in capsys.readouterr().out

    @patch("main.git_fetch_open_pr_description", return_value=None)
    def test_no_pr_leaves_pr_description_null(self, mock_pr):
        progress = _empty_scope_progress()

        _capture_pr_description(progress, "/tmp")

        assert progress["config"]["pr_description"] is None

    @patch("main.git_fetch_open_pr_description")
    def test_skips_when_already_captured(self, mock_pr):
        """Resumed runs must not re-fetch or overwrite an existing PR
        description — protects against races where the PR was edited mid-run."""
        progress = _empty_scope_progress()
        progress["config"]["pr_description"] = {
            "title": "Original title",
            "body": "Original body",
            "base_ref": "origin/main",
        }

        _capture_pr_description(progress, "/tmp")

        mock_pr.assert_not_called()
        assert progress["config"]["pr_description"]["title"] == "Original title"

    @patch("main.git_fetch_open_pr_description")
    def test_long_title_stored_in_full(self, mock_pr, capsys):
        """Title is sliced only for the console preview, never for storage."""
        long_title = "A" * 90
        mock_pr.return_value = {
            "title": long_title,
            "body": "",
            "base_ref": "origin/main",
        }
        progress = _empty_scope_progress()

        _capture_pr_description(progress, "/tmp")

        assert progress["config"]["pr_description"]["title"] == long_title
        # Console preview must be truncated to the configured cap
        from main import _PR_TITLE_PREVIEW_CHARS

        out = capsys.readouterr().out
        assert f"Captured PR description: {long_title[:_PR_TITLE_PREVIEW_CHARS]}" in out


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------


class TestMain:
    @patch("main._validate_environment", return_value=("npm test", None))
    @patch("main.subprocess.run")
    def test_clamps_high_iterations(self, mock_run, mock_validate, capsys):
        """Iterations above hard cap are clamped."""
        mock_run.return_value = MagicMock(returncode=0)
        with patch("main._run_iteration_loop"), patch("main.print_report"), patch(
            "main._archive_progress"
        ), patch("main.make_initial_progress") as mock_init, patch(
            "main.git_diff_has_changes", return_value=False
        ), patch(
            "main.git_discover_branch_files", return_value=([], None)
        ), patch(
            "main.git_fetch_open_pr_description", return_value=None
        ):
            mock_init.return_value = {
                "skill": "code-review",
                "config": {
                    "max_iterations": 20,
                    "test_command": "npm test",
                    "base_commit": "abc123",
                    "focus": "",
                    "project_root": "/tmp",
                    "scope": {"mode": "local-changes", "paths": [], "base_ref": None},
                },
                "iteration": {"current": 1, "completed": 0},
                "findings": [],
                "scope_files": {"current": []},
                "test_results": {
                    "last_full_run": None,
                    "last_run_output_summary": None,
                },
                "iteration_history": [],
                "termination": {"reason": None, "message": None},
            }
            result = main(["--skill", "code-review", "--max-iterations", "50"])
        assert result == 0
        output = capsys.readouterr().out
        assert "clamped to 20" in output

    @patch("main._validate_environment", return_value=("npm test", None))
    @patch("main.subprocess.run")
    def test_clamps_low_iterations(self, mock_run, mock_validate, capsys):
        """Iterations below 1 are clamped."""
        mock_run.return_value = MagicMock(returncode=0)
        with patch("main._run_iteration_loop"), patch("main.print_report"), patch(
            "main._archive_progress"
        ), patch("main.make_initial_progress") as mock_init, patch(
            "main.git_diff_has_changes", return_value=False
        ), patch(
            "main.git_discover_branch_files", return_value=([], None)
        ), patch(
            "main.git_fetch_open_pr_description", return_value=None
        ):
            mock_init.return_value = {
                "skill": "code-review",
                "config": {
                    "max_iterations": 1,
                    "test_command": "npm test",
                    "base_commit": "abc123",
                    "focus": "",
                    "project_root": "/tmp",
                    "scope": {"mode": "local-changes", "paths": [], "base_ref": None},
                },
                "iteration": {"current": 1, "completed": 0},
                "findings": [],
                "scope_files": {"current": []},
                "test_results": {
                    "last_full_run": None,
                    "last_run_output_summary": None,
                },
                "iteration_history": [],
                "termination": {"reason": None, "message": None},
            }
            result = main(["--skill", "code-review", "--max-iterations", "0"])
        assert result == 0
        output = capsys.readouterr().out
        assert "clamped to 1" in output

    @patch("main._validate_environment", return_value=("npm test", None))
    @patch("main.subprocess.run")
    def test_populates_branch_scope_when_empty(self, mock_run, mock_validate):
        """main() wires git_discover_branch_files output into the progress dict.

        Regression guard for the iteration-1 quality gap fix — without this
        positive-path assertion, unpatching _populate_branch_scope would still
        leave every existing TestMain test passing.
        """
        mock_run.return_value = MagicMock(returncode=0)
        progress = {
            "skill": "code-review",
            "config": {
                "max_iterations": 8,
                "test_command": "npm test",
                "base_commit": "abc123",
                "focus": "",
                "project_root": "/tmp",
                "scope": {"mode": "local-changes", "paths": [], "base_ref": None},
            },
            "iteration": {"current": 1, "completed": 0},
            "findings": [],
            "scope_files": {"current": []},
            "test_results": {
                "last_full_run": None,
                "last_run_output_summary": None,
            },
            "iteration_history": [],
            "termination": {"reason": None, "message": None},
        }
        with patch("main._run_iteration_loop"), patch("main.print_report"), patch(
            "main._archive_progress"
        ), patch("main.make_initial_progress", return_value=progress), patch(
            "main.git_diff_has_changes", return_value=False
        ), patch(
            "main.git_discover_branch_files",
            return_value=(["src/a.py", "src/b.py"], "origin/main"),
        ), patch(
            "main.git_fetch_open_pr_description", return_value=None
        ):
            result = main(["--skill", "code-review"])
        assert result == 0
        assert progress["scope_files"]["current"] == ["src/a.py", "src/b.py"]
        assert progress["config"]["scope"]["base_ref"] == "origin/main"
        assert progress["config"]["scope"]["mode"] == "branch-diff"

    @patch("main._validate_environment", return_value=("npm test", None))
    @patch("main.subprocess.run")
    def test_captures_pr_description_end_to_end(self, mock_run, mock_validate):
        """main() wires git_fetch_open_pr_description output into progress."""
        mock_run.return_value = MagicMock(returncode=0)
        progress = {
            "skill": "code-review",
            "config": {
                "max_iterations": 8,
                "test_command": "npm test",
                "base_commit": "abc123",
                "focus": "",
                "project_root": "/tmp",
                "scope": {"mode": "local-changes", "paths": [], "base_ref": None},
                "pr_description": None,
            },
            "iteration": {"current": 1, "completed": 0},
            "findings": [],
            "scope_files": {"current": []},
            "test_results": {
                "last_full_run": None,
                "last_run_output_summary": None,
            },
            "iteration_history": [],
            "termination": {"reason": None, "message": None},
        }
        pr_info = {
            "title": "Fix auth bug",
            "body": "Adds null check.",
            "base_ref": "origin/main",
        }
        with patch("main._run_iteration_loop"), patch("main.print_report"), patch(
            "main._archive_progress"
        ), patch("main.make_initial_progress", return_value=progress), patch(
            "main.git_diff_has_changes", return_value=False
        ), patch(
            "main.git_discover_branch_files",
            return_value=(["src/a.py"], "origin/main"),
        ), patch(
            "main.git_fetch_open_pr_description", return_value=pr_info
        ):
            result = main(["--skill", "code-review"])
        assert result == 0
        assert progress["config"]["pr_description"] == pr_info

    def test_focus_with_non_refactor_returns_error(self, capsys):
        """--focus with code-review returns error code 1."""
        result = main(["--skill", "code-review", "--focus", "testability"])
        assert result == 1
        assert "--focus is only supported" in capsys.readouterr().out

    @patch("main._validate_environment", return_value=(None, "claude CLI not found"))
    def test_env_validation_error(self, mock_validate, capsys):
        result = main(["--skill", "code-review"])
        assert result == 1
        assert "claude CLI not found" in capsys.readouterr().out

    @patch("main.git_diff_has_changes", return_value=True)
    @patch("main._validate_environment", return_value=("npm test", None))
    def test_uncommitted_changes_guard(self, mock_validate, mock_diff, capsys):
        """Fresh run with uncommitted changes returns error."""
        result = main(["--skill", "code-review"])
        assert result == 1
        assert "Uncommitted changes detected" in capsys.readouterr().out

    @patch("main.git_diff_has_changes", return_value=True)
    @patch("main._validate_environment", return_value=("npm test", None))
    def test_uncommitted_changes_allowed_with_no_commit(
        self, mock_validate, mock_diff, capsys
    ):
        """--no-commit bypasses uncommitted changes check."""
        with patch("main._run_iteration_loop"), patch("main.print_report"), patch(
            "main._archive_progress"
        ), patch("main.make_initial_progress") as mock_init, patch(
            "main.git_discover_branch_files", return_value=([], None)
        ), patch(
            "main.git_fetch_open_pr_description", return_value=None
        ):
            mock_init.return_value = {
                "skill": "code-review",
                "config": {
                    "max_iterations": 8,
                    "test_command": "npm test",
                    "base_commit": "abc123",
                    "focus": "",
                    "project_root": "/tmp",
                    "scope": {"mode": "local-changes", "paths": [], "base_ref": None},
                },
                "iteration": {"current": 1, "completed": 0},
                "findings": [],
                "scope_files": {"current": []},
                "test_results": {
                    "last_full_run": None,
                    "last_run_output_summary": None,
                },
                "iteration_history": [],
                "termination": {"reason": None, "message": None},
            }
            result = main(["--skill", "code-review", "--no-commit"])
        assert result == 0

    @patch("main._validate_environment", return_value=("npm test", None))
    def test_missing_base_commit_returns_error(self, mock_validate, capsys):
        with patch("main.make_initial_progress") as mock_init, patch(
            "main.git_diff_has_changes", return_value=False
        ), patch("main.git_discover_branch_files", return_value=([], None)), patch(
            "main.git_fetch_open_pr_description", return_value=None
        ):
            mock_init.return_value = {
                "skill": "code-review",
                "config": {
                    "max_iterations": 8,
                    "test_command": "npm test",
                    "base_commit": "",
                    "focus": "",
                    "project_root": "/tmp",
                    "scope": {"mode": "local-changes", "paths": [], "base_ref": None},
                },
                "iteration": {"current": 1, "completed": 0},
                "findings": [],
                "scope_files": {"current": []},
                "test_results": {
                    "last_full_run": None,
                    "last_run_output_summary": None,
                },
                "iteration_history": [],
                "termination": {"reason": None, "message": None},
            }
            result = main(["--skill", "code-review"])
        assert result == 1
        assert "Cannot determine HEAD commit" in capsys.readouterr().out

    @patch("main._validate_environment", return_value=("npm test", None))
    def test_invalid_focus_in_progress_on_resume(self, mock_validate, capsys, tmp_path):
        import json

        progress_path = tmp_path / "progress.json"
        progress = {
            "skill": "refactor",
            "config": {
                "max_iterations": 8,
                "test_command": "npm test",
                "base_commit": "abc123",
                "focus": "bogus-mode",
                "project_root": str(tmp_path),
                "scope": {"mode": "local-changes", "paths": [], "base_ref": None},
            },
            "iteration": {"current": 1, "completed": 0},
            "findings": [],
            "scope_files": {"current": []},
            "test_results": {"last_full_run": None, "last_run_output_summary": None},
            "iteration_history": [],
            "termination": {"reason": None, "message": None},
        }
        progress_path.write_text(json.dumps(progress), encoding="utf-8")
        result = main(
            [
                "--skill",
                "refactor",
                "--resume",
                "--progress-file",
                str(progress_path),
                "--project-dir",
                str(tmp_path),
            ]
        )
        assert result == 1
        assert "Invalid focus mode" in capsys.readouterr().out

    @patch("main._archive_progress")
    @patch("main.print_report")
    @patch("main._run_iteration_loop")
    @patch("main.git_diff_has_changes", return_value=False)
    @patch("main._validate_environment", return_value=("npm test", None))
    def test_happy_path_fresh_run(
        self, mock_validate, mock_diff, mock_loop, mock_report, mock_archive
    ):
        """Fresh run calls loop, report, and archive."""
        with patch("main.make_initial_progress") as mock_init:
            mock_init.return_value = {
                "skill": "code-review",
                "config": {
                    "max_iterations": 8,
                    "test_command": "npm test",
                    "base_commit": "abc123",
                    "focus": "",
                    "project_root": "/tmp",
                    "scope": {"mode": "local-changes", "paths": [], "base_ref": None},
                },
                "iteration": {"current": 1, "completed": 0},
                "findings": [],
                "scope_files": {"current": []},
                "test_results": {
                    "last_full_run": None,
                    "last_run_output_summary": None,
                },
                "iteration_history": [],
                "termination": {"reason": None, "message": None},
            }
            result = main(["--skill", "code-review"])
        assert result == 0
        mock_loop.assert_called_once()
        mock_report.assert_called_once()
        mock_archive.assert_called_once()

    @patch("main._archive_progress")
    @patch("main.print_report")
    @patch("main._run_iteration_loop")
    @patch("main._validate_environment", return_value=("pytest", None))
    def test_resume_syncs_test_command_and_focus(
        self, mock_validate, mock_loop, mock_report, mock_archive, tmp_path
    ):
        """Resume syncs freshly detected test_command and explicit focus."""
        import json

        progress_path = tmp_path / "progress.json"
        progress = {
            "skill": "refactor",
            "config": {
                "max_iterations": 8,
                "test_command": "old-cmd",
                "base_commit": "abc123",
                "focus": "",
                "project_root": str(tmp_path),
                "scope": {"mode": "local-changes", "paths": [], "base_ref": None},
            },
            "iteration": {"current": 2, "completed": 1},
            "findings": [],
            "scope_files": {"current": []},
            "test_results": {"last_full_run": None, "last_run_output_summary": None},
            "iteration_history": [],
            "termination": {"reason": None, "message": None},
        }
        progress_path.write_text(json.dumps(progress), encoding="utf-8")
        result = main(
            [
                "--skill",
                "refactor",
                "--resume",
                "--focus",
                "testability",
                "--progress-file",
                str(progress_path),
                "--project-dir",
                str(tmp_path),
            ]
        )
        assert result == 0
        # Verify synced values by inspecting what _run_iteration_loop received
        call_args = mock_loop.call_args
        synced_progress = call_args[0][1]
        assert synced_progress["config"]["test_command"] == "pytest"
        assert synced_progress["config"]["focus"] == "testability"
