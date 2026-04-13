import subprocess
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from harness_common.runner import _find_bash
from harness_common.runner import build_claude_session_cmd as _build_cmd
from impl.runner import (
    _build_harness_system,
    _build_prompt,
    run_skill_session,
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
        # Should try git --exec-path fallback
        with patch("harness_common.runner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            with patch("harness_common.runner.Path") as mock_path_cls:
                # Make common paths not exist
                mock_path_instance = MagicMock()
                mock_path_instance.exists.return_value = False
                mock_path_cls.return_value = mock_path_instance
                result = _find_bash()
                assert result == "bash"  # fallback


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
        import subprocess

        mock_sys.platform = "linux"
        mock_run.side_effect = subprocess.TimeoutExpired("npm test", 300)
        passed, summary = run_tests("npm test", "/tmp/project")
        assert passed is False
        assert "timed out" in summary

    @patch("harness_common.runner._find_bash", return_value="C:\\Git\\bin\\bash.exe")
    @patch("harness_common.runner.sys")
    @patch("harness_common.runner.subprocess.run")
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
    @patch("harness_common.runner.sys")
    @patch("harness_common.runner.shutil.which")
    @patch("harness_common.runner.subprocess.run")
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

    @patch("harness_common.runner.sys")
    @patch("harness_common.runner.shutil.which")
    @patch("harness_common.runner.subprocess.run")
    def test_git_exec_path_timeout(self, mock_run, mock_which, mock_sys, tmp_path):
        """TimeoutExpired on git --exec-path falls through to common paths."""
        import subprocess

        mock_sys.platform = "win32"
        mock_which.return_value = "C:\\Windows\\System32\\bash.exe"
        mock_run.side_effect = subprocess.TimeoutExpired("git", 5)
        with patch("harness_common.runner.Path") as mock_path_cls:
            mock_instance = MagicMock()
            mock_instance.exists.return_value = False
            mock_path_cls.return_value = mock_instance
            result = _find_bash()
        assert result == "bash"  # ultimate fallback

    @patch("harness_common.runner.sys")
    @patch("harness_common.runner.shutil.which")
    @patch("harness_common.runner.subprocess.run")
    def test_git_exec_path_not_found(self, mock_run, mock_which, mock_sys, tmp_path):
        """FileNotFoundError on git --exec-path falls through to common paths."""
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
    def test_common_path_found(self, mock_run, mock_which, mock_sys, tmp_path):
        """Falls through to common installation paths when git --exec-path fails."""
        mock_sys.platform = "win32"
        mock_which.return_value = "C:\\Windows\\System32\\bash.exe"
        mock_run.return_value = MagicMock(returncode=1)
        # Create a fake bash at the first common path
        git_bash = tmp_path / "Git" / "bin" / "bash.exe"
        git_bash.parent.mkdir(parents=True)
        git_bash.write_text("fake", encoding="utf-8")
        with patch("harness_common.runner.Path") as mock_path_cls:
            mock_instance = MagicMock()
            # First common path exists
            mock_instance.exists.side_effect = [True]
            mock_path_cls.return_value = mock_instance
            result = _find_bash()
        assert result == str(mock_instance)

    @patch("harness_common.runner.sys")
    @patch("harness_common.runner.shutil.which")
    def test_windows_no_bash_on_path(self, mock_which, mock_sys):
        """When shutil.which returns None, falls through to git --exec-path."""
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


class TestBuildPrompt:
    def test_code_review_skill(self):
        result = _build_prompt("code-review", 8, [])
        assert result == "/optimus:code-review deep"

    def test_refactor_skill(self):
        result = _build_prompt("refactor", 5, [])
        assert result == "/optimus:refactor deep 5"

    def test_with_scope_paths(self):
        result = _build_prompt("code-review", 8, ["src/auth", "src/api"])
        assert "focus on: src/auth, src/api" in result

    def test_scope_paths_capped_at_20(self):
        paths = [f"path/{i}" for i in range(25)]
        result = _build_prompt("refactor", 8, paths)
        # Only first 20 paths should be included
        assert "path/19" in result
        assert "path/20" not in result

    def test_focus_testability(self):
        result = _build_prompt("refactor", 8, [], focus="testability")
        assert result == "/optimus:refactor deep 8 testability"

    def test_focus_guidelines(self):
        result = _build_prompt("refactor", 5, [], focus="guidelines")
        assert result == "/optimus:refactor deep 5 guidelines"

    def test_focus_with_scope(self):
        result = _build_prompt("refactor", 8, ["src/auth"], focus="testability")
        assert result == '/optimus:refactor deep 8 testability "focus on: src/auth"'

    def test_focus_empty_string(self):
        result = _build_prompt("refactor", 8, [])
        assert result == "/optimus:refactor deep 8"

    def test_focus_skipped_for_code_review(self):
        # Code-review doesn't support focus — _build_prompt should not append it
        result = _build_prompt("code-review", 8, [], focus="testability")
        assert "testability" not in result

    def test_invalid_focus_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid focus mode"):
            _build_prompt("refactor", 8, [], focus="invalid-mode")


class TestBuildHarnessSystem:
    def test_contains_required_fields(self):
        result = _build_harness_system("/tmp/progress.json", 3, 8)
        assert "HARNESS_MODE_ACTIVE" in result
        assert "/tmp/progress.json" in result
        assert "iteration 3 of 8" in result
        assert "AskUserQuestion" in result
        assert "json:harness-output" in result

    def test_includes_digest_and_coaching(self):
        progress = {
            "findings": [{"status": "fixed", "file": "a.py", "line": 1}],
            "config": {"max_iterations": 5},
            "scope_files": {"current": ["a.py"]},
            "test_results": {"last_full_run": "pass"},
        }
        result = _build_harness_system("/tmp/p.json", 2, 5, progress=progress)
        assert "--- Progress Digest ---" in result
        assert "--- Guidance ---" in result
        assert "1 fixed" in result


class TestBuildCmd:
    def test_with_allowed_tools(self):
        cmd = _build_cmd("prompt", "system", "Read,Edit", 30)
        assert "--allowedTools" in cmd
        assert "Read,Edit" in cmd
        assert "--dangerously-skip-permissions" not in cmd

    def test_without_allowed_tools(self):
        cmd = _build_cmd("prompt", "system", "", 30)
        assert "--dangerously-skip-permissions" in cmd
        assert "--allowedTools" not in cmd

    def test_none_allowed_tools(self):
        cmd = _build_cmd("prompt", "system", None, 30)
        assert "--dangerously-skip-permissions" in cmd

    def test_includes_prompt_and_system(self):
        cmd = _build_cmd("my prompt", "my system", "", 15)
        assert cmd[0] == "claude"
        assert "-p" in cmd
        assert "my prompt" in cmd
        assert "--append-system-prompt" in cmd
        assert "my system" in cmd
        assert "--max-turns" in cmd
        assert "15" in cmd
        assert "--output-format" in cmd
        assert "json" in cmd


class TestRunSkillSession:
    def _make_progress(self, iteration=1, max_iter=8, skill="code-review", scope=None):
        return {
            "skill": skill,
            "iteration": {"current": iteration},
            "config": {
                "max_iterations": max_iter,
                "project_root": "/tmp/project",
                "focus": "",
            },
            "scope_files": {"current": scope or []},
        }

    def _make_args(self, verbose=False, allowed_tools="", max_turns=30, timeout=900):
        return SimpleNamespace(
            verbose=verbose,
            allowed_tools=allowed_tools,
            max_turns=max_turns,
            timeout=timeout,
        )

    def test_returns_stdout(self):
        mock_run = MagicMock(
            return_value=MagicMock(returncode=0, stdout="output", stderr="")
        )
        progress = self._make_progress()
        args = self._make_args()
        result = run_skill_session(progress, args, "/tmp/progress.json", _run=mock_run)
        assert result == "output"

    def test_verbose_prints_command_and_exit_code(self, capsys):
        mock_run = MagicMock(
            return_value=MagicMock(returncode=0, stdout="out", stderr="")
        )
        progress = self._make_progress()
        args = self._make_args(verbose=True)
        run_skill_session(progress, args, "/tmp/progress.json", _run=mock_run)
        captured = capsys.readouterr().out
        assert "Command:" in captured
        assert "Exit code: 0" in captured

    def test_verbose_prints_stderr(self, capsys):
        mock_run = MagicMock(
            return_value=MagicMock(returncode=0, stdout="out", stderr="some warning")
        )
        progress = self._make_progress()
        args = self._make_args(verbose=True)
        run_skill_session(progress, args, "/tmp/progress.json", _run=mock_run)
        captured = capsys.readouterr().out
        assert "Stderr: some warning" in captured

    def test_verbose_no_stderr_skips_line(self, capsys):
        mock_run = MagicMock(
            return_value=MagicMock(returncode=0, stdout="out", stderr="")
        )
        progress = self._make_progress()
        args = self._make_args(verbose=True)
        run_skill_session(progress, args, "/tmp/progress.json", _run=mock_run)
        captured = capsys.readouterr().out
        assert "Stderr:" not in captured

    def test_exit_code_greater_than_1_raises(self):
        mock_run = MagicMock(
            return_value=MagicMock(returncode=2, stdout="", stderr="fatal error")
        )
        progress = self._make_progress()
        args = self._make_args()
        with pytest.raises(RuntimeError, match="claude exited with code 2"):
            run_skill_session(progress, args, "/tmp/progress.json", _run=mock_run)

    def test_exit_code_1_warns_but_returns(self, capsys):
        mock_run = MagicMock(
            return_value=MagicMock(returncode=1, stdout="partial", stderr="warn")
        )
        progress = self._make_progress()
        args = self._make_args()
        result = run_skill_session(progress, args, "/tmp/progress.json", _run=mock_run)
        assert result == "partial"
        assert "WARNING" in capsys.readouterr().out
