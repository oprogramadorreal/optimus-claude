import subprocess
from unittest.mock import MagicMock, patch

from harness_common.runner import (
    _find_bash,
    retry_on_failure,
    run_tests,
    save_session_log,
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


class TestSaveSessionLog:
    def test_writes_stdout_log(self, tmp_path):
        save_session_log(str(tmp_path), "session-iter1", "hello stdout")
        log = tmp_path / "session-iter1.log"
        assert log.exists()
        assert log.read_text(encoding="utf-8") == "hello stdout"

    def test_writes_stderr_log(self, tmp_path):
        save_session_log(str(tmp_path), "session-iter1", "out", "err content")
        stderr_log = tmp_path / "session-iter1.stderr.log"
        assert stderr_log.exists()
        assert stderr_log.read_text(encoding="utf-8") == "err content"

    def test_no_stderr_file_when_empty(self, tmp_path):
        save_session_log(str(tmp_path), "session-iter1", "out", "")
        assert not (tmp_path / "session-iter1.stderr.log").exists()

    def test_no_stdout_file_when_empty(self, tmp_path):
        save_session_log(str(tmp_path), "session-iter1", "", "err")
        assert not (tmp_path / "session-iter1.log").exists()
        assert (tmp_path / "session-iter1.stderr.log").exists()

    def test_noop_when_log_dir_falsy(self, tmp_path):
        save_session_log("", "session-iter1", "data")
        save_session_log(None, "session-iter1", "data")
        # No files should be created anywhere

    def test_creates_nested_dirs(self, tmp_path):
        nested = tmp_path / "deep" / "nested"
        save_session_log(str(nested), "test", "content")
        assert (nested / "test.log").exists()


class TestRetryOnFailure:
    def _mock_rng(self):
        rng = MagicMock()
        rng.uniform.return_value = 0.0  # No jitter for deterministic tests
        return rng

    def test_success_on_first_attempt(self):
        result = retry_on_failure(lambda: "ok", max_retries=3, _sleep=lambda _: None)
        assert result == "ok"

    def test_success_after_retry(self):
        calls = {"count": 0}

        def flaky():
            calls["count"] += 1
            if calls["count"] < 2:
                raise RuntimeError("transient")
            return "recovered"

        result = retry_on_failure(
            flaky, max_retries=3, _sleep=lambda _: None, _random=self._mock_rng()
        )
        assert result == "recovered"
        assert calls["count"] == 2

    def test_raises_after_max_retries(self):
        import pytest

        def always_fail():
            raise RuntimeError("permanent")

        with pytest.raises(RuntimeError, match="permanent"):
            retry_on_failure(
                always_fail,
                max_retries=2,
                _sleep=lambda _: None,
                _random=self._mock_rng(),
            )

    def test_exponential_backoff_delays(self):
        delays = []

        def always_fail():
            raise RuntimeError("fail")

        try:
            retry_on_failure(
                always_fail,
                max_retries=3,
                base_delay=10.0,
                jitter_fraction=0.0,
                _sleep=lambda d: delays.append(d),
                _random=self._mock_rng(),
            )
        except RuntimeError:
            pass
        # 2 retries before the final raise: delays for attempt 0 and 1
        assert len(delays) == 2
        assert delays[0] == 10.0  # 10 * 2^0
        assert delays[1] == 20.0  # 10 * 2^1

    def test_on_retry_callback(self):
        callbacks = []

        def always_fail():
            raise RuntimeError("fail")

        def on_retry(attempt, exc, delay):
            callbacks.append((attempt, str(exc), delay))

        try:
            retry_on_failure(
                always_fail,
                max_retries=2,
                base_delay=5.0,
                on_retry=on_retry,
                _sleep=lambda _: None,
                _random=self._mock_rng(),
            )
        except RuntimeError:
            pass
        assert len(callbacks) == 1
        assert callbacks[0][0] == 0
        assert "fail" in callbacks[0][1]

    def test_non_retryable_exception_propagates(self):
        import pytest

        def raise_value_error():
            raise ValueError("not retryable")

        with pytest.raises(ValueError, match="not retryable"):
            retry_on_failure(
                raise_value_error,
                max_retries=3,
                _sleep=lambda _: None,
            )

    def test_jitter_applied(self):
        delays = []
        rng = MagicMock()
        rng.uniform.return_value = 0.1  # +10% of delay

        def always_fail():
            raise RuntimeError("fail")

        try:
            retry_on_failure(
                always_fail,
                max_retries=2,
                base_delay=10.0,
                jitter_fraction=0.25,
                _sleep=lambda d: delays.append(d),
                _random=rng,
            )
        except RuntimeError:
            pass
        # delay = 10.0 * 2^0 = 10.0, jitter = 10.0 * 0.1 = 1.0, total = 11.0
        assert len(delays) == 1
        assert delays[0] == 11.0

    def test_no_sleep_on_first_attempt_success(self):
        sleep_calls = []
        result = retry_on_failure(
            lambda: "fast",
            max_retries=3,
            _sleep=lambda d: sleep_calls.append(d),
        )
        assert result == "fast"
        assert len(sleep_calls) == 0
