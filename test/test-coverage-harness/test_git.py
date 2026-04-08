from unittest.mock import MagicMock, patch

from impl.git import git_commit_checkpoint


class TestGitCommitCheckpoint:
    @patch("harness_common.git.subprocess.run")
    def test_unit_test_phase(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        progress = {
            "cycle_history": [
                {"cycle": 1, "unit_test": {"tests_written": 3, "coverage_delta": 10.0}}
            ],
            "tests_created": [],
            "refactor_findings": [],
        }
        ut_summary = {"tests_written": 3, "coverage_delta": 10.0}
        assert (
            git_commit_checkpoint(progress, 1, "unit-test", "/tmp", ut_summary) is True
        )
        # Should call: git add -A, git reset (x2), git commit
        assert mock_run.call_count == 4
        commit_call = mock_run.call_args_list[3]
        msg = commit_call[0][0][3]  # git commit -m <msg>
        assert "test(coverage-harness)" in msg
        assert "3 tests written" in msg

    @patch("harness_common.git.subprocess.run")
    def test_refactor_phase(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        progress = {
            "cycle_history": [{"cycle": 1, "refactor": {"fixed": 2, "reverted": 0}}],
            "tests_created": [],
            "refactor_findings": [],
        }
        rf_summary = {"fixed": 2, "reverted": 0}
        assert (
            git_commit_checkpoint(progress, 1, "refactor", "/tmp", rf_summary) is True
        )
        commit_call = mock_run.call_args_list[3]
        msg = commit_call[0][0][3]
        assert "refactor(coverage-harness)" in msg
        assert "2 fixed" in msg

    @patch("harness_common.git.subprocess.run")
    def test_add_failure(self, mock_run, capsys):
        mock_run.return_value = MagicMock(returncode=1, stderr="add failed")
        progress = {"cycle_history": [], "tests_created": [], "refactor_findings": []}
        assert git_commit_checkpoint(progress, 1, "unit-test", "/tmp") is False
        assert "WARNING" in capsys.readouterr().out

    @patch("harness_common.git.subprocess.run")
    def test_nothing_to_commit(self, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=0),  # git add
            MagicMock(returncode=0),  # git reset
            MagicMock(returncode=0),  # git reset
            MagicMock(
                returncode=1,
                stdout="nothing to commit, working tree clean\n",
                stderr="",
            ),
        ]
        progress = {"cycle_history": [], "tests_created": [], "refactor_findings": []}
        assert git_commit_checkpoint(progress, 1, "unit-test", "/tmp") is True

    @patch("harness_common.git.subprocess.run")
    def test_commit_failure(self, mock_run, capsys):
        mock_run.side_effect = [
            MagicMock(returncode=0),  # git add
            MagicMock(returncode=0),  # git reset
            MagicMock(returncode=0),  # git reset
            MagicMock(returncode=1, stdout="", stderr="fatal: error"),
        ]
        progress = {
            "cycle_history": [{"cycle": 1, "unit_test": {"tests_written": 1}}],
            "tests_created": [],
            "refactor_findings": [],
        }
        assert git_commit_checkpoint(progress, 1, "unit-test", "/tmp") is False
        assert "WARNING" in capsys.readouterr().out

    @patch("harness_common.git.subprocess.run")
    def test_empty_history(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        progress = {"cycle_history": [], "tests_created": [], "refactor_findings": []}
        assert git_commit_checkpoint(progress, 1, "unit-test", "/tmp") is True
        commit_call = mock_run.call_args_list[3]
        msg = commit_call[0][0][3]
        assert "0 tests written" in msg
