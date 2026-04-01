from unittest.mock import MagicMock, patch

from impl.runner import _find_bash, run_tests


class TestFindBash:
    @patch("impl.runner.sys")
    def test_non_windows(self, mock_sys):
        mock_sys.platform = "linux"
        assert _find_bash() == "bash"

    @patch("impl.runner.sys")
    @patch("impl.runner.shutil.which")
    def test_windows_git_bash_on_path(self, mock_which, mock_sys):
        mock_sys.platform = "win32"
        mock_which.return_value = "C:\\Program Files\\Git\\bin\\bash.exe"
        assert _find_bash() == "C:\\Program Files\\Git\\bin\\bash.exe"

    @patch("impl.runner.sys")
    @patch("impl.runner.shutil.which")
    def test_windows_wsl_fallback(self, mock_which, mock_sys):
        mock_sys.platform = "win32"
        mock_which.return_value = "C:\\Windows\\System32\\bash.exe"
        # Should try git --exec-path fallback
        with patch("impl.runner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            with patch("impl.runner.Path") as mock_path_cls:
                # Make common paths not exist
                mock_path_instance = MagicMock()
                mock_path_instance.exists.return_value = False
                mock_path_cls.return_value = mock_path_instance
                result = _find_bash()
                assert result == "bash"  # fallback


class TestRunTests:
    @patch("impl.runner.sys")
    @patch("impl.runner.subprocess.run")
    def test_passing_tests_unix(self, mock_run, mock_sys):
        mock_sys.platform = "linux"
        mock_run.return_value = MagicMock(
            returncode=0, stdout="All tests passed\n", stderr=""
        )
        passed, summary = run_tests("npm test", "/tmp/project")
        assert passed is True
        assert "All tests passed" in summary

    @patch("impl.runner.sys")
    @patch("impl.runner.subprocess.run")
    def test_failing_tests(self, mock_run, mock_sys):
        mock_sys.platform = "linux"
        mock_run.return_value = MagicMock(
            returncode=1, stdout="1 test failed\n", stderr=""
        )
        passed, summary = run_tests("npm test", "/tmp/project")
        assert passed is False

    @patch("impl.runner.sys")
    @patch("impl.runner.subprocess.run")
    def test_timeout(self, mock_run, mock_sys):
        import subprocess

        mock_sys.platform = "linux"
        mock_run.side_effect = subprocess.TimeoutExpired("npm test", 300)
        passed, summary = run_tests("npm test", "/tmp/project")
        assert passed is False
        assert "timed out" in summary
