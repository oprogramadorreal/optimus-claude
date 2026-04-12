import subprocess
from unittest.mock import MagicMock, patch

from harness_common.runner import _find_bash, extract_test_summary, run_tests


class TestFindBash:
    @patch("harness_common.runner.sys")
    def test_non_windows(self, mock_sys):
        mock_sys.platform = "linux"
        assert _find_bash() == "bash"

    @patch("harness_common.runner.sys")
    @patch("harness_common.runner.shutil.which")
    def test_windows_git_bash_on_path(self, mock_which, mock_sys):
        mock_sys.platform = "win32"
        mock_which.return_value = "C:\\Program Files\\Git\\bin\\bash.exe"
        assert _find_bash() == "C:\\Program Files\\Git\\bin\\bash.exe"

    @patch("harness_common.runner.sys")
    @patch("harness_common.runner.shutil.which")
    def test_windows_wsl_fallback(self, mock_which, mock_sys):
        mock_sys.platform = "win32"
        mock_which.return_value = "C:\\Windows\\System32\\bash.exe"
        with patch("harness_common.runner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            with patch("harness_common.runner.Path") as mock_path_cls:
                mock_instance = MagicMock()
                mock_instance.exists.return_value = False
                mock_path_cls.return_value = mock_instance
                result = _find_bash()
                assert result == "bash"


class TestRunTests:
    @patch("harness_common.runner.sys")
    @patch("harness_common.runner.subprocess.run")
    def test_passing_tests_unix(self, mock_run, mock_sys):
        mock_sys.platform = "linux"
        mock_run.return_value = MagicMock(
            returncode=0, stdout="All tests passed\n", stderr=""
        )
        passed, summary = run_tests("npm test", "/tmp/project")
        assert passed is True
        assert "All tests passed" in summary

    @patch("harness_common.runner.sys")
    @patch("harness_common.runner.subprocess.run")
    def test_failing_tests(self, mock_run, mock_sys):
        mock_sys.platform = "linux"
        mock_run.return_value = MagicMock(
            returncode=1, stdout="1 test failed\n", stderr=""
        )
        passed, summary = run_tests("npm test", "/tmp/project")
        assert passed is False

    @patch("harness_common.runner.sys")
    @patch("harness_common.runner.subprocess.run")
    def test_timeout(self, mock_run, mock_sys):
        mock_sys.platform = "linux"
        mock_run.side_effect = subprocess.TimeoutExpired("npm test", 300)
        passed, summary = run_tests("npm test", "/tmp/project")
        assert passed is False
        assert "timed out" in summary

    @patch("harness_common.runner.sys")
    @patch("harness_common.runner.subprocess.run")
    def test_timeout_includes_partial_output_tail(self, mock_run, mock_sys):
        """Bytes stdout/stderr from TimeoutExpired are decoded and tail appended."""
        mock_sys.platform = "linux"
        mock_run.side_effect = subprocess.TimeoutExpired(
            "npm test",
            300,
            output=b"line1\nline2\nlast\n",
            stderr=b"err-tail\n",
        )
        passed, summary = run_tests("npm test", "/tmp/project")
        assert passed is False
        assert "timed out after 300s" in summary
        # Tail of decoded output should appear in summary (line 99 path)
        assert "last" in summary
        assert "err-tail" in summary

    @patch("harness_common.runner.sys")
    @patch("harness_common.runner.subprocess.run")
    def test_command_not_found_unix(self, mock_run, mock_sys, capsys):
        """FileNotFoundError surfaces an actionable error instead of crashing."""
        mock_sys.platform = "linux"
        mock_run.side_effect = FileNotFoundError(2, "No such file", "missing-bin")
        passed, summary = run_tests("missing-bin", "/tmp/project")
        assert passed is False
        assert "Command not found" in summary
        assert "missing-bin" in summary
        # The Git Bash hint is Windows-only
        assert "Git Bash" not in summary
        out = capsys.readouterr().out
        assert "Command not found" in out

    @patch("harness_common.runner._find_bash", return_value="bash")
    @patch("harness_common.runner.sys")
    @patch("harness_common.runner.subprocess.run")
    def test_command_not_found_windows_includes_git_bash_hint(
        self, mock_run, mock_sys, mock_find_bash
    ):
        """On Windows, missing bash mentions the Git Bash install hint."""
        mock_sys.platform = "win32"
        mock_run.side_effect = FileNotFoundError(2, "No such file", "bash")
        passed, summary = run_tests("npm test", "/tmp/project")
        assert passed is False
        assert "Command not found" in summary
        assert "Git Bash" in summary

    @patch("harness_common.runner.sys")
    @patch("harness_common.runner.subprocess.run")
    def test_command_not_found_no_filename(self, mock_run, mock_sys):
        """FileNotFoundError without a filename falls back to 'bash' label."""
        mock_sys.platform = "linux"
        mock_run.side_effect = FileNotFoundError()
        passed, summary = run_tests("npm test", "/tmp/project")
        assert passed is False
        assert "bash" in summary

    @patch("harness_common.runner._find_bash", return_value="C:\\Git\\bin\\bash.exe")
    @patch("harness_common.runner.sys")
    @patch("harness_common.runner.subprocess.run")
    def test_windows_routes_through_bash(self, mock_run, mock_sys, mock_find_bash):
        mock_sys.platform = "win32"
        mock_run.return_value = MagicMock(returncode=0, stdout="pass\n", stderr="")
        passed, summary = run_tests("npm test && npm run lint", "/tmp/project")
        assert passed is True
        call_args = mock_run.call_args
        assert call_args[0][0] == [
            "C:\\Git\\bin\\bash.exe",
            "-c",
            "npm test && npm run lint",
        ]
        assert call_args[1]["shell"] is False

    @patch("harness_common.runner.sys")
    @patch("harness_common.runner.subprocess.run")
    def test_custom_prefix(self, mock_run, mock_sys, capsys):
        mock_sys.platform = "linux"
        mock_run.return_value = MagicMock(returncode=0, stdout="ok\n", stderr="")
        run_tests("npm test", "/tmp", prefix="[custom]")
        output = capsys.readouterr().out
        assert "[custom]" in output

    @patch("harness_common.runner.sys")
    @patch("harness_common.runner.subprocess.run")
    def test_default_prefix(self, mock_run, mock_sys, capsys):
        mock_sys.platform = "linux"
        mock_run.return_value = MagicMock(returncode=0, stdout="ok\n", stderr="")
        run_tests("npm test", "/tmp")
        output = capsys.readouterr().out
        assert "[harness]" in output


class TestFindBashGitExecPath:
    @patch("harness_common.runner.sys")
    @patch("harness_common.runner.shutil.which")
    @patch("harness_common.runner.subprocess.run")
    def test_git_exec_path_success(self, mock_run, mock_which, mock_sys, tmp_path):
        mock_sys.platform = "win32"
        mock_which.return_value = "C:\\Windows\\System32\\bash.exe"
        git_bash = tmp_path / "bin" / "bash.exe"
        git_bash.parent.mkdir(parents=True)
        git_bash.write_text("fake", encoding="utf-8")
        exec_path = tmp_path / "mingw64" / "libexec" / "git-core"
        mock_run.return_value = MagicMock(returncode=0, stdout=str(exec_path) + "\n")
        result = _find_bash()
        assert result == str(git_bash)

    @patch("harness_common.runner.sys")
    @patch("harness_common.runner.shutil.which")
    @patch("harness_common.runner.subprocess.run")
    def test_git_exec_path_timeout(self, mock_run, mock_which, mock_sys):
        mock_sys.platform = "win32"
        mock_which.return_value = "C:\\Windows\\System32\\bash.exe"
        mock_run.side_effect = subprocess.TimeoutExpired("git", 5)
        with patch("harness_common.runner.Path") as mock_path_cls:
            mock_instance = MagicMock()
            mock_instance.exists.return_value = False
            mock_path_cls.return_value = mock_instance
            result = _find_bash()
        assert result == "bash"

    @patch("harness_common.runner.sys")
    @patch("harness_common.runner.shutil.which")
    @patch("harness_common.runner.subprocess.run")
    def test_git_exec_path_not_found(self, mock_run, mock_which, mock_sys):
        mock_sys.platform = "win32"
        mock_which.return_value = "C:\\Windows\\System32\\bash.exe"
        mock_run.side_effect = FileNotFoundError("git not installed")
        with patch("harness_common.runner.Path") as mock_path_cls:
            mock_instance = MagicMock()
            mock_instance.exists.return_value = False
            mock_path_cls.return_value = mock_instance
            result = _find_bash()
        assert result == "bash"

    @patch("harness_common.runner.sys")
    @patch("harness_common.runner.shutil.which")
    @patch("harness_common.runner.subprocess.run")
    def test_common_path_found(self, mock_run, mock_which, mock_sys):
        mock_sys.platform = "win32"
        mock_which.return_value = "C:\\Windows\\System32\\bash.exe"
        mock_run.return_value = MagicMock(returncode=1)
        with patch("harness_common.runner.Path") as mock_path_cls:
            mock_instance = MagicMock()
            mock_instance.exists.side_effect = [True]
            mock_path_cls.return_value = mock_instance
            result = _find_bash()
        assert result == str(mock_instance)

    @patch("harness_common.runner.sys")
    @patch("harness_common.runner.shutil.which")
    def test_windows_no_bash_on_path(self, mock_which, mock_sys):
        mock_sys.platform = "win32"
        mock_which.return_value = None
        with patch("harness_common.runner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            with patch("harness_common.runner.Path") as mock_path_cls:
                mock_instance = MagicMock()
                mock_instance.exists.return_value = False
                mock_path_cls.return_value = mock_instance
                result = _find_bash()
        assert result == "bash"


class TestExtractTestSummary:
    def test_empty_output(self):
        assert extract_test_summary("") == ""
        assert extract_test_summary(None) == ""

    def test_pytest_summary(self):
        output = (
            "test_app.py::test_login PASSED\n"
            "test_app.py::test_logout FAILED\n"
            "FAILED test_app.py::test_logout - AssertionError: expected 200\n"
            "======= 1 failed, 1 passed in 0.5s ======="
        )
        summary = extract_test_summary(output)
        assert "1 failed, 1 passed" in summary
        assert "First failure:" in summary
        assert "test_logout" in summary

    def test_pytest_all_pass(self):
        output = "test_app.py::test_login PASSED\n======= 1 passed in 0.1s ======="
        summary = extract_test_summary(output)
        assert "1 passed" in summary
        assert "First failure:" not in summary

    def test_jest_summary(self):
        output = (
            "PASS src/app.test.js\n"
            "FAIL src/auth.test.js\n"
            "Test Suites: 1 failed, 1 passed, 2 total\n"
            "Tests:       1 failed, 5 passed, 6 total\n"
            "Time:        2.3s\n"
        )
        summary = extract_test_summary(output)
        assert "Tests:" in summary

    def test_go_test_failure(self):
        output = (
            "--- FAIL: TestLogin (0.01s)\n"
            "    auth_test.go:15: expected true, got false\n"
            "FAIL\tgithub.com/user/pkg\t0.02s\n"
        )
        summary = extract_test_summary(output)
        assert "TestLogin" in summary
        assert "FAIL\t" in summary

    def test_cargo_test_failure(self):
        output = (
            "running 3 tests\n"
            "test tests::test_add ... ok\n"
            "test tests::test_sub ... FAILED\n"
            "failures:\n"
            "    tests::test_sub\n"
            "test result: FAILED. 1 passed; 1 failed;\n"
        )
        summary = extract_test_summary(output)
        assert "FAILED" in summary

    def test_fallback_uses_last_10_lines(self):
        lines = [f"line {i}" for i in range(20)]
        output = "\n".join(lines)
        summary = extract_test_summary(output)
        assert "line 10" in summary
        assert "line 19" in summary
        assert "line 9" not in summary
