from unittest.mock import MagicMock, patch

from harness_common.git import (
    _clean_working_tree,
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
