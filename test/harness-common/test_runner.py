import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from harness_common.runner import _find_bash, bash_environment, run_tests

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"


@pytest.fixture(autouse=True)
def isolate_bash_override(monkeypatch):
    """Discovery tests supply their own override instead of inheriting one."""
    monkeypatch.delenv("CLAUDE_CODE_GIT_BASH_PATH", raising=False)


def _popen(returncode=0, stdout=b"", stderr=b"", timeout=False):
    """Fake Popen that writes into run_tests' capture files."""

    def start(command, **kwargs):
        kwargs["stdout"].write(stdout)
        kwargs["stderr"].write(stderr)
        proc = MagicMock(returncode=returncode, pid=0)
        if timeout:
            proc.wait.side_effect = [subprocess.TimeoutExpired(command, 300), None]
        return proc

    return start


class TestFindBash:
    def test_explicit_windows_override(self, monkeypatch, tmp_path):
        bash = tmp_path / "Custom Git" / "bin" / "bash.exe"
        bash.parent.mkdir(parents=True)
        bash.write_bytes(b"")
        monkeypatch.setenv("CLAUDE_CODE_GIT_BASH_PATH", str(bash))
        assert _find_bash(platform="win32") == str(bash)

    def test_missing_windows_override_names_the_variable(self, monkeypatch, tmp_path):
        missing = tmp_path / "missing" / "bash.exe"
        monkeypatch.setenv("CLAUDE_CODE_GIT_BASH_PATH", str(missing))
        with pytest.raises(FileNotFoundError, match="CLAUDE_CODE_GIT_BASH_PATH"):
            _find_bash(platform="win32")

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
    @patch("harness_common.runner.subprocess.Popen")
    def test_passing_tests_unix(self, mock_run, mock_sys):
        mock_sys.platform = "linux"
        mock_run.side_effect = _popen(0, b"All tests passed\n", b"")
        passed, summary = run_tests("npm test", "/tmp/project")
        assert passed is True
        assert "All tests passed" in summary

    @patch("harness_common.runner.sys")
    @patch("harness_common.runner.subprocess.Popen")
    def test_failing_tests(self, mock_run, mock_sys):
        mock_sys.platform = "linux"
        mock_run.side_effect = _popen(1, b"1 test failed\n", b"")
        passed, summary = run_tests("npm test", "/tmp/project")
        assert passed is False

    @patch("harness_common.runner._kill_tree")
    @patch("harness_common.runner.sys")
    @patch("harness_common.runner.subprocess.Popen")
    def test_timeout(self, mock_run, mock_sys, mock_kill):
        mock_sys.platform = "linux"
        mock_run.side_effect = _popen(timeout=True)
        passed, summary = run_tests("npm test", "/tmp/project")
        assert passed is False
        assert "timed out" in summary

    @patch("harness_common.runner._find_bash", return_value="bash")
    @patch("harness_common.runner._kill_tree")
    @patch("harness_common.runner._windows_job")
    @patch("harness_common.runner.subprocess.Popen")
    def test_termination_signal_kills_the_tree_and_exits(
        self, mock_run, mock_job, mock_kill, mock_find_bash
    ):
        def start(command, **kwargs):
            proc = MagicMock(pid=0)
            proc.wait.side_effect = lambda timeout=None: (
                signal.raise_signal(signal.SIGTERM) if timeout is not None else None
            )
            return proc

        mock_run.side_effect = start
        # A stand-in handler keeps a missing fix from terminating pytest itself.
        # (Not a MagicMock: its __int__ makes signal.signal store SIG_IGN.)
        caller_calls = []

        def caller_handler(signum, frame):
            caller_calls.append(signum)

        previous = signal.signal(signal.SIGTERM, caller_handler)
        try:
            with pytest.raises(SystemExit) as exc:
                run_tests("npm test", "/tmp/project")
            assert signal.getsignal(signal.SIGTERM) is caller_handler
        finally:
            signal.signal(signal.SIGTERM, previous)
        assert exc.value.code == 128 + signal.SIGTERM
        mock_kill.assert_called_once()
        assert caller_calls == []

    @patch("harness_common.runner._kill_tree")
    @patch("harness_common.runner.sys")
    @patch("harness_common.runner.subprocess.Popen")
    def test_timeout_includes_partial_output_tail(self, mock_run, mock_sys, mock_kill):
        """Output captured before the timeout is decoded and its tail appended."""
        mock_sys.platform = "linux"
        mock_run.side_effect = _popen(
            stdout=b"line1\nline2\nlast\n", stderr=b"err-tail\n", timeout=True
        )
        passed, summary = run_tests("npm test", "/tmp/project")
        assert passed is False
        assert "timed out after 300s" in summary
        # Tail of decoded output should appear in summary
        assert "last" in summary
        assert "err-tail" in summary

    @patch("harness_common.runner.sys")
    @patch("harness_common.runner.subprocess.Popen")
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
    @patch("harness_common.runner._windows_job")
    @patch("harness_common.runner.sys")
    @patch("harness_common.runner.subprocess.Popen")
    def test_command_not_found_windows_includes_git_bash_hint(
        self, mock_run, mock_sys, mock_job, mock_find_bash
    ):
        """On Windows, missing bash mentions the Git Bash install hint."""
        mock_sys.platform = "win32"
        mock_run.side_effect = FileNotFoundError(2, "No such file", "bash")
        passed, summary = run_tests("npm test", "/tmp/project")
        assert passed is False
        assert "Command not found" in summary
        assert "Git Bash" in summary

    @patch("harness_common.runner.sys")
    @patch("harness_common.runner.subprocess.Popen")
    def test_command_not_found_no_filename(self, mock_run, mock_sys):
        """FileNotFoundError without a filename falls back to 'bash' label."""
        mock_sys.platform = "linux"
        mock_run.side_effect = FileNotFoundError()
        passed, summary = run_tests("npm test", "/tmp/project")
        assert passed is False
        assert "bash" in summary

    @patch("harness_common.runner._find_bash", return_value="C:\\Git\\bin\\bash.exe")
    @patch("harness_common.runner._windows_job")
    @patch("harness_common.runner.sys")
    @patch("harness_common.runner.subprocess.Popen")
    def test_windows_routes_through_bash(
        self, mock_run, mock_sys, mock_job, mock_find_bash
    ):
        mock_sys.platform = "win32"
        mock_run.side_effect = _popen(0, b"pass\n", b"")
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
    @patch("harness_common.runner.subprocess.Popen")
    def test_unix_routes_through_bash(self, mock_run, mock_sys):
        # /bin/sh is dash on Debian/Ubuntu, which has no `source`.
        mock_sys.platform = "linux"
        mock_run.side_effect = _popen(0, b"ok\n", b"")
        run_tests("source .venv/bin/activate && pytest", "/tmp/project")
        assert mock_run.call_args[0][0] == [
            "bash",
            "-c",
            "source .venv/bin/activate && pytest",
        ]
        assert mock_run.call_args[1]["shell"] is False

    @patch("harness_common.runner.sys")
    @patch("harness_common.runner.subprocess.Popen")
    def test_default_prefix(self, mock_run, mock_sys, capsys):
        mock_sys.platform = "linux"
        mock_run.side_effect = _popen(0, b"ok\n", b"")
        run_tests("npm test", "/tmp")
        output = capsys.readouterr().out
        assert "[harness]" in output

    @patch("harness_common.runner.subprocess.Popen")
    @patch("harness_common.runner.sys")
    def test_invalid_windows_override_fails_without_running(
        self, mock_sys, mock_run, monkeypatch, tmp_path
    ):
        mock_sys.platform = "win32"
        missing = tmp_path / "missing" / "bash.exe"
        monkeypatch.setenv("CLAUDE_CODE_GIT_BASH_PATH", str(missing))
        passed, summary = run_tests("npm test", tmp_path)
        assert passed is False
        assert "CLAUDE_CODE_GIT_BASH_PATH" in summary
        assert str(missing) in summary
        mock_run.assert_not_called()


class TestRunTestsEndToEnd:
    """Real-subprocess checks — no mocks, exercising the actual decode path."""

    def test_captures_non_cp1252_utf8_output(self, tmp_path):
        # U+201D is E2 80 9D in UTF-8, and 0x9D is undefined in cp1252. Before
        # encoding= was pinned, a cp1252 locale (e.g. pt-BR Windows) lost the
        # child's entire output; pinning UTF-8 makes capture locale-independent.
        sample = tmp_path / "curly.txt"
        sample.write_bytes(b"\xe2\x80\x9d ok\n")
        posix_path = str(sample).replace("\\", "/")
        passed, summary = run_tests(f'cat "{posix_path}"; exit 0', tmp_path)
        assert passed is True
        assert "ok" in summary
        assert "”" in summary

    @pytest.mark.parametrize(
        "command", ["sleep 30", "sleep 30 && echo done", "(sleep 30 &); sleep 30"]
    )
    def test_timeout_stops_the_whole_process_tree(self, tmp_path, command):
        start = time.monotonic()
        passed, summary = run_tests(command, tmp_path, timeout=1)
        assert time.monotonic() - start < 15
        assert not passed and "timed out after 1s" in summary

    def test_timed_out_orphan_cannot_overwrite_restored_files(self, tmp_path):
        # The intermediate subshell exits before timeout. Windows taskkill /T
        # loses that ancestry, allowing the orphan to overwrite a later restore.
        passed, summary = run_tests(
            "(sleep 3 && printf late > restored.txt &); sleep 30",
            tmp_path,
            timeout=1,
        )
        restored = tmp_path / "restored.txt"
        restored.write_text("restored", encoding="utf-8")
        time.sleep(3)
        assert not passed and "timed out" in summary
        assert restored.read_text(encoding="utf-8") == "restored"

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows job assignment")
    def test_failed_assignment_kills_the_suspended_shell(self, tmp_path, monkeypatch):
        from harness_common import windows_job

        processes = []
        popen = subprocess.Popen

        def start(*args, **kwargs):
            process = popen(*args, **kwargs)
            if kwargs.get("creationflags", 0) & 0x00000004:
                processes.append(process)
            return process

        def fail_assignment(*args):
            raise OSError("job assignment refused")

        monkeypatch.setattr(subprocess, "Popen", start)
        monkeypatch.setattr(
            windows_job._kernel32, "AssignProcessToJobObject", fail_assignment
        )
        with pytest.raises(OSError, match="job assignment refused"):
            run_tests("printf unsafe > ran.txt", tmp_path)
        assert len(processes) == 1 and processes[0].poll() is not None
        assert not (tmp_path / "ran.txt").exists()

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX sessions and signals")
    def test_terminating_the_caller_stops_the_whole_process_tree(self, tmp_path):
        # The suite runs in its own session, so the SIGTERM never reaches it;
        # left running, it would create `survived` two seconds later.
        script = "\n".join(
            [
                "import sys",
                f"sys.path.insert(0, {str(_SCRIPTS)!r})",
                "from harness_common.runner import run_tests",
                "run_tests('touch ready; sleep 2; touch survived', sys.argv[1], 60)",
            ]
        )
        caller = subprocess.Popen([sys.executable, "-c", script, str(tmp_path)])
        deadline = time.monotonic() + 15
        while not (tmp_path / "ready").exists():
            assert time.monotonic() < deadline, "the test command never started"
            time.sleep(0.05)
        time.sleep(0.3)  # let the caller reach its wait
        caller.terminate()
        assert caller.wait(timeout=15) == 128 + signal.SIGTERM
        time.sleep(3)
        assert not (tmp_path / "survived").exists()

    @pytest.mark.skipif(sys.platform != "win32", reason="Git for Windows PATH")
    def test_native_utilities_with_only_git_cmd_on_path(self, tmp_path, monkeypatch):
        bash = _find_bash()
        root = Path(bash).parent.parent
        if root.name.lower() == "usr":
            root = root.parent
        if not (root / "cmd" / "git.exe").exists():
            pytest.skip("Git for Windows installation is unavailable")
        monkeypatch.setenv(
            "PATH", str(root / "cmd") + ";" + os.environ["SystemRoot"] + "/System32"
        )
        (tmp_path / "sample.txt").write_text("utility-ok", encoding="utf-8")
        passed, summary = run_tests("cat sample.txt && dirname sample.txt", tmp_path)
        assert passed, summary
        assert "utility-ok" in summary


def test_bash_environment_preserves_input_and_collapses_windows_path(tmp_path):
    bash = tmp_path / "usr" / "bin" / "bash.exe"
    bash.parent.mkdir(parents=True)
    bash.write_text("", encoding="utf-8")
    original = {"Path": "old-path", "PATH": "effective-path", "KEEP": "yes"}
    env = bash_environment(str(bash), original, platform="win32")
    assert original["Path"] == "old-path"
    assert "Path" not in env
    assert env["PATH"] == str(bash.parent) + ";effective-path"
    assert env["KEEP"] == "yes"


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

    def test_common_path_found(self):
        # Real Path objects: the loop must skip the missing first candidate and
        # return the specific one that exists, not just "some mocked Path".
        existing = "C:/Program Files (x86)/Git/bin/bash.exe"
        with patch.object(
            Path,
            "exists",
            autospec=True,
            side_effect=lambda p: p.as_posix() == existing,
        ):
            result = _find_bash(
                platform="win32",
                which_fn=lambda _name: None,
                run_fn=lambda cmd, **_kw: subprocess.CompletedProcess(cmd, 1, "", ""),
            )
        assert result == str(Path(existing))

    def test_git_exec_path_without_bash_falls_back(self, tmp_path):
        exec_path = tmp_path / "mingw64" / "libexec" / "git-core"
        with patch.object(Path, "exists", autospec=True, return_value=False):
            result = _find_bash(
                platform="win32",
                which_fn=lambda _name: None,
                run_fn=lambda cmd, **_kw: subprocess.CompletedProcess(
                    cmd, 0, f"{exec_path}\n", ""
                ),
            )
        assert result == "bash"

    @patch("harness_common.runner.sys")
    @patch("harness_common.runner.shutil.which")
    @patch("harness_common.runner.subprocess.run")
    def test_git_exec_path_forces_utf8(self, mock_run, mock_which, mock_sys):
        mock_sys.platform = "win32"
        mock_which.return_value = None
        mock_run.return_value = MagicMock(returncode=1)
        with patch("harness_common.runner.Path") as mock_path_cls:
            mock_instance = MagicMock()
            mock_instance.exists.return_value = False
            mock_path_cls.return_value = mock_instance
            _find_bash()
        _args, kwargs = mock_run.call_args
        assert kwargs.get("encoding") == "utf-8"
        assert kwargs.get("errors") == "replace"

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
