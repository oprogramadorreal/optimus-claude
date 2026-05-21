import json
from unittest.mock import MagicMock, patch

from harness_common.git import (
    _clean_working_tree,
    _fetch_open_pr_data,
    git_current_branch,
    git_diff_has_changes,
    git_restore_snapshot,
    git_restore_to,
    git_rev_parse_head,
    git_stash_snapshot,
    restore_working_tree,
)


class TestGitRevParseHead:
    @patch("harness_common.git.subprocess.run")
    def test_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="abc123\n")
        assert git_rev_parse_head("/tmp") == "abc123"

    @patch("harness_common.git.subprocess.run")
    def test_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        assert git_rev_parse_head("/tmp") is None


class TestCleanWorkingTree:
    @patch("harness_common.git.subprocess.run")
    def test_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        _clean_working_tree("/tmp/project")
        assert mock_run.call_count == 2

    @patch("harness_common.git.subprocess.run")
    def test_clean_failure_prints_warning(self, mock_run, capsys):
        mock_run.side_effect = [
            MagicMock(returncode=0),
            MagicMock(returncode=1, stderr="permission denied"),
        ]
        _clean_working_tree("/tmp/project")
        assert "WARNING" in capsys.readouterr().out

    @patch("harness_common.git.subprocess.run")
    def test_checkout_failure_prints_warning(self, mock_run, capsys):
        mock_run.side_effect = [
            MagicMock(returncode=1, stderr="error: checkout failed"),
            MagicMock(returncode=0),
        ]
        _clean_working_tree("/tmp/project")
        output = capsys.readouterr().out
        assert "WARNING" in output
        assert "git checkout" in output

    @patch("harness_common.git.subprocess.run")
    def test_clean_excludes_harness_state_files(self, mock_run):
        # Regression: orchestrator progress files / per-iteration temp files
        # must survive the restore-to-HEAD fallback path so the user can
        # --resume after a failed iteration.
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        _clean_working_tree("/tmp/project")
        clean_call = mock_run.call_args_list[1]
        clean_args = clean_call.args[0]
        # The clean command must carry -e patterns covering the progress file
        # families and per-iteration temp files.
        assert "-e" in clean_args
        # Each excluded pattern must appear as its own token (so a stale
        # `.json.done.json` typo cannot pass via substring match).
        excludes = [
            arg for arg, prev in zip(clean_args[1:], clean_args) if prev == "-e"
        ]
        assert ".claude/*-deep-progress.json" in excludes
        assert ".claude/*-deep-progress.json.bak" in excludes
        # The archived filename is `*-deep-progress.done.json` (Path.with_suffix
        # strips `.json` then appends `.done.json`); the pattern must match it.
        assert ".claude/*-deep-progress.done.json" in excludes
        assert ".claude/.deep-iteration-*" in excludes
        assert ".claude/.unit-test-deep-*" in excludes


class TestGitRestoreTo:
    @patch("harness_common.git._clean_working_tree")
    @patch("harness_common.git.subprocess.run")
    def test_success(self, mock_run, mock_clean):
        mock_run.return_value = MagicMock(returncode=0)
        git_restore_to("abc123", "/tmp")
        mock_clean.assert_called_once()

    @patch("harness_common.git.subprocess.run")
    def test_failure_raises(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="error: pathspec")
        import pytest

        with pytest.raises(RuntimeError, match="git checkout .* failed"):
            git_restore_to("abc123", "/tmp")


class TestGitCurrentBranch:
    @patch("harness_common.git.subprocess.run")
    def test_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="feature/foo\n")
        assert git_current_branch("/tmp") == "feature/foo"

    @patch("harness_common.git.subprocess.run")
    def test_failure_returns_empty(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        assert git_current_branch("/tmp") == ""


class TestGitDiffHasChanges:
    @patch("harness_common.git.subprocess.run")
    def test_unstaged_changes(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        assert git_diff_has_changes("/tmp") is True

    @patch("harness_common.git.subprocess.run")
    def test_staged_changes(self, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=0),
            MagicMock(returncode=1),
        ]
        assert git_diff_has_changes("/tmp") is True

    @patch("harness_common.git.subprocess.run")
    def test_untracked_files(self, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=0),
            MagicMock(returncode=0),
            MagicMock(returncode=0, stdout="new_file.txt\n"),
        ]
        assert git_diff_has_changes("/tmp") is True

    @patch("harness_common.git.subprocess.run")
    def test_no_changes(self, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=0),
            MagicMock(returncode=0),
            MagicMock(returncode=0, stdout=""),
        ]
        assert git_diff_has_changes("/tmp") is False


class TestRestoreWorkingTree:
    @patch("harness_common.git.git_restore_to")
    @patch("harness_common.git.git_restore_snapshot", return_value=True)
    def test_stash_path(self, mock_snapshot, mock_restore_to):
        restore_working_tree("stash123", "head123", "/tmp")
        mock_snapshot.assert_called_once_with("stash123", "/tmp", _run=None)
        mock_restore_to.assert_not_called()

    @patch("harness_common.git.git_restore_to")
    @patch("harness_common.git.git_restore_snapshot", return_value=False)
    def test_stash_fails_falls_back_to_head(self, mock_snapshot, mock_restore_to):
        restore_working_tree("stash123", "head123", "/tmp")
        mock_restore_to.assert_called_once_with("head123", "/tmp", _run=None)

    @patch("harness_common.git.git_restore_to")
    def test_no_stash_uses_head(self, mock_restore_to):
        restore_working_tree(None, "head123", "/tmp")
        mock_restore_to.assert_called_once_with("head123", "/tmp", _run=None)

    @patch("harness_common.git.git_restore_to")
    def test_no_stash_no_head_returns_false(self, mock_restore_to, capsys):
        # Regression for c53086d: when both inputs are None, restore_working_tree
        # warns and returns False rather than raising on the missing fallback.
        result = restore_working_tree(None, None, "/tmp")
        assert result is False
        mock_restore_to.assert_not_called()
        assert "no snapshot to restore from" in capsys.readouterr().out


class TestGitStashSnapshot:
    @patch("harness_common.git.subprocess.run")
    def test_success(self, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc123\n"),
            MagicMock(returncode=0),
        ]
        assert git_stash_snapshot("/tmp") == "abc123"

    @patch("harness_common.git.subprocess.run")
    def test_no_changes(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        assert git_stash_snapshot("/tmp") is None

    @patch("harness_common.git.subprocess.run")
    def test_store_failure_returns_none(self, mock_run, capsys):
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc123\n"),
            MagicMock(returncode=1, stderr="error storing"),
        ]
        assert git_stash_snapshot("/tmp") is None
        assert "WARNING" in capsys.readouterr().out


class TestGitRestoreSnapshot:
    @patch("harness_common.git.subprocess.run")
    @patch("harness_common.git._clean_working_tree")
    def test_success(self, mock_clean, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        assert git_restore_snapshot("abc123", "/tmp") is True
        mock_clean.assert_called_once()

    @patch("harness_common.git.subprocess.run")
    @patch("harness_common.git._clean_working_tree")
    def test_failure(self, mock_clean, mock_run, capsys):
        mock_run.return_value = MagicMock(returncode=1, stderr="conflict")
        assert git_restore_snapshot("abc123", "/tmp") is False
        assert "WARNING" in capsys.readouterr().out

    @patch("harness_common.git.subprocess.run")
    @patch("harness_common.git._clean_working_tree")
    def test_success_drops_matching_stash(self, mock_clean, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=0),
            MagicMock(returncode=0, stdout="stash@{0} abc123\nstash@{1} def456\n"),
            MagicMock(returncode=0),
        ]
        assert git_restore_snapshot("abc123", "/tmp") is True
        drop_call = mock_run.call_args_list[2]
        assert drop_call[0][0] == ["git", "stash", "drop", "stash@{0}"]


class TestFetchOpenPrData:
    @patch("harness_common.git.subprocess.run")
    def test_decodes_non_latin1_body(self, mock_run):
        # Em-dash and accented chars would fail under Windows-default cp1252;
        # the encoding="utf-8" kwarg is what makes this work cross-platform.
        body = "Implements — feature: rotación de tokens"
        pr_json = json.dumps(
            {
                "title": "feat",
                "body": body,
                "baseRefName": "main",
                "state": "OPEN",
            }
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=pr_json)
        result = _fetch_open_pr_data("/tmp/project")
        assert result is not None
        assert result["body"] == body
        # Regression guard for commit 9e0553a — without these kwargs, Windows
        # would re-default to cp1252 and silently drop non-Latin-1 PR bodies.
        _args, kwargs = mock_run.call_args
        assert kwargs.get("encoding") == "utf-8"
        assert kwargs.get("errors") == "replace"

    @patch("harness_common.git.subprocess.run")
    def test_returns_none_when_pr_not_open(self, mock_run):
        pr_json = json.dumps(
            {
                "title": "feat",
                "body": "x",
                "baseRefName": "main",
                "state": "CLOSED",
            }
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=pr_json)
        assert _fetch_open_pr_data("/tmp/project") is None

    @patch("harness_common.git.subprocess.run")
    def test_returns_none_on_gh_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        assert _fetch_open_pr_data("/tmp/project") is None
