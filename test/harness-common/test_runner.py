import subprocess
from unittest.mock import MagicMock, patch

from harness_common.runner import (
    _find_bash,
    retry_on_failure,
    run_tests,
)


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


class TestRetryOnFailure:
    def test_success_no_retry(self):
        result = retry_on_failure(lambda: 42)
        assert result == 42

    def test_retries_on_failure(self):
        calls = []

        def flaky():
            calls.append(1)
            if len(calls) < 2:
                raise RuntimeError("fail")
            return "ok"

        result = retry_on_failure(flaky, max_retries=2, base_delay=0.01)
        assert result == "ok"
        assert len(calls) == 2

    def test_exhausted_returns_none(self):
        exhausted_called = []

        def always_fail():
            raise RuntimeError("always")

        result = retry_on_failure(
            always_fail,
            max_retries=1,
            base_delay=0.01,
            on_exhausted=lambda exc: exhausted_called.append(str(exc)),
        )
        assert result is None
        assert len(exhausted_called) == 1

    def test_on_retry_callback(self):
        retries = []

        def fail_once():
            if not retries:
                retries.append(1)
                raise RuntimeError("once")
            return "done"

        retry_on_failure(
            fail_once,
            max_retries=1,
            base_delay=0.01,
            on_retry=lambda attempt, exc, delay: retries.append(("retry", attempt)),
        )
        assert ("retry", 0) in retries

    def test_non_retryable_exception_propagates(self):
        def raise_value_error():
            raise ValueError("not retryable")

        try:
            retry_on_failure(raise_value_error, max_retries=2, base_delay=0.01)
            assert False, "Should have raised"
        except ValueError:
            pass

    def test_custom_retryable(self):
        calls = []

        def fail_with_value_error():
            calls.append(1)
            if len(calls) < 2:
                raise ValueError("custom")
            return "ok"

        result = retry_on_failure(
            fail_with_value_error,
            max_retries=2,
            base_delay=0.01,
            retryable=(ValueError,),
        )
        assert result == "ok"

    def test_retries_on_timeout_expired(self):
        """TimeoutExpired is part of the default retryable tuple."""
        calls = []

        def flaky_timeout():
            calls.append(1)
            if len(calls) < 2:
                raise subprocess.TimeoutExpired("claude", 900)
            return "ok"

        result = retry_on_failure(flaky_timeout, max_retries=2, base_delay=0.01)
        assert result == "ok"
        assert len(calls) == 2

    @patch("harness_common.runner.time.sleep")
    def test_jitter_delay_within_25_percent(self, mock_sleep):
        """Backoff delay passed to on_retry stays within ±25% of the exponential target."""
        captured = []

        def fail_twice():
            raise RuntimeError("fail")

        retry_on_failure(
            fail_twice,
            max_retries=2,
            base_delay=10.0,
            on_retry=lambda attempt, exc, delay: captured.append((attempt, delay)),
        )
        # attempt 0: target = 10.0, expect delay in [7.5, 12.5]
        # attempt 1: target = 20.0, expect delay in [15.0, 25.0]
        assert len(captured) == 2
        assert 7.5 <= captured[0][1] <= 12.5
        assert 15.0 <= captured[1][1] <= 25.0
