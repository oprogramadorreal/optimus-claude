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

    @patch("impl.runner._find_bash", return_value="C:\\Git\\bin\\bash.exe")
    @patch("impl.runner.sys")
    @patch("impl.runner.subprocess.run")
    def test_windows_routes_through_bash(self, mock_run, mock_sys, mock_find_bash):
        mock_sys.platform = "win32"
        mock_run.return_value = MagicMock(returncode=0, stdout="pass\n", stderr="")
        passed, summary = run_tests("npm test && npm run lint", "/tmp/project")
        assert passed is True
        # Should call subprocess with bash -c, not shell=True
        call_args = mock_run.call_args
        assert call_args[0][0] == [
            "C:\\Git\\bin\\bash.exe",
            "-c",
            "npm test && npm run lint",
        ]
        assert call_args[1]["shell"] is False


class TestFindBashGitExecPath:
    @patch("impl.runner.sys")
    @patch("impl.runner.shutil.which")
    @patch("impl.runner.subprocess.run")
    def test_git_exec_path_success(self, mock_run, mock_which, mock_sys, tmp_path):
        mock_sys.platform = "win32"
        mock_which.return_value = "C:\\Windows\\System32\\bash.exe"  # WSL
        # Simulate git --exec-path returning a valid path
        git_bash = tmp_path / "bin" / "bash.exe"
        git_bash.parent.mkdir(parents=True)
        git_bash.write_text("fake", encoding="utf-8")
        # git --exec-path returns mingw64/libexec/git-core under the git root
        exec_path = tmp_path / "mingw64" / "libexec" / "git-core"
        mock_run.return_value = MagicMock(returncode=0, stdout=str(exec_path) + "\n")
        result = _find_bash()
        assert result == str(git_bash)

    @patch("impl.runner.sys")
    @patch("impl.runner.shutil.which")
    @patch("impl.runner.subprocess.run")
    def test_git_exec_path_timeout(self, mock_run, mock_which, mock_sys, tmp_path):
        """TimeoutExpired on git --exec-path falls through to common paths."""
        import subprocess

        mock_sys.platform = "win32"
        mock_which.return_value = "C:\\Windows\\System32\\bash.exe"
        mock_run.side_effect = subprocess.TimeoutExpired("git", 5)
        with patch("impl.runner.Path") as mock_path_cls:
            mock_instance = MagicMock()
            mock_instance.exists.return_value = False
            mock_path_cls.return_value = mock_instance
            result = _find_bash()
        assert result == "bash"  # ultimate fallback

    @patch("impl.runner.sys")
    @patch("impl.runner.shutil.which")
    @patch("impl.runner.subprocess.run")
    def test_git_exec_path_not_found(self, mock_run, mock_which, mock_sys, tmp_path):
        """FileNotFoundError on git --exec-path falls through to common paths."""
        mock_sys.platform = "win32"
        mock_which.return_value = "C:\\Windows\\System32\\bash.exe"
        mock_run.side_effect = FileNotFoundError("git not installed")
        with patch("impl.runner.Path") as mock_path_cls:
            mock_instance = MagicMock()
            mock_instance.exists.return_value = False
            mock_path_cls.return_value = mock_instance
            result = _find_bash()
        assert result == "bash"

    @patch("impl.runner.sys")
    @patch("impl.runner.shutil.which")
    @patch("impl.runner.subprocess.run")
    def test_common_path_found(self, mock_run, mock_which, mock_sys, tmp_path):
        """Falls through to common installation paths when git --exec-path fails."""
        mock_sys.platform = "win32"
        mock_which.return_value = "C:\\Windows\\System32\\bash.exe"
        mock_run.return_value = MagicMock(returncode=1)
        # Create a fake bash at the first common path
        git_bash = tmp_path / "Git" / "bin" / "bash.exe"
        git_bash.parent.mkdir(parents=True)
        git_bash.write_text("fake", encoding="utf-8")
        with patch("impl.runner.Path") as mock_path_cls:
            mock_instance = MagicMock()
            # First common path exists
            mock_instance.exists.side_effect = [True]
            mock_path_cls.return_value = mock_instance
            result = _find_bash()
        assert result == str(mock_instance)

    @patch("impl.runner.sys")
    @patch("impl.runner.shutil.which")
    def test_windows_no_bash_on_path(self, mock_which, mock_sys):
        """When shutil.which returns None, falls through to git --exec-path."""
        mock_sys.platform = "win32"
        mock_which.return_value = None
        with patch("impl.runner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            with patch("impl.runner.Path") as mock_path_cls:
                mock_instance = MagicMock()
                mock_instance.exists.return_value = False
                mock_path_cls.return_value = mock_instance
                result = _find_bash()
        assert result == "bash"
