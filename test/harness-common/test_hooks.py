import os
import stat
import subprocess
import sys
from unittest.mock import MagicMock, patch

from harness_common.hooks import run_hook


class TestRunHook:
    def test_no_hooks_dir(self):
        assert run_hook("", "pre-iteration") is None
        assert run_hook(None, "pre-iteration") is None

    def test_nonexistent_dir(self, tmp_path):
        assert run_hook(str(tmp_path / "nope"), "pre-iteration") is None

    def test_no_matching_hook(self, tmp_path):
        assert run_hook(str(tmp_path), "pre-iteration") is None

    def test_successful_hook(self, tmp_path):
        hook = tmp_path / "pre-iteration"
        if sys.platform == "win32":
            hook = tmp_path / "pre-iteration.cmd"
            hook.write_text("@echo off\nexit /b 0\n", encoding="utf-8")
        else:
            hook.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            hook.chmod(hook.stat().st_mode | stat.S_IEXEC)
        assert run_hook(str(tmp_path), "pre-iteration") is True

    def test_failing_hook_returns_false(self, tmp_path, capsys):
        hook = tmp_path / "post-iteration"
        if sys.platform == "win32":
            hook = tmp_path / "post-iteration.cmd"
            hook.write_text("@echo off\nexit /b 1\n", encoding="utf-8")
        else:
            hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            hook.chmod(hook.stat().st_mode | stat.S_IEXEC)
        result = run_hook(str(tmp_path), "post-iteration")
        assert result is False
        assert "exited with code 1" in capsys.readouterr().out

    def test_env_vars_passed(self, tmp_path):
        if sys.platform == "win32":
            hook = tmp_path / "pre-iteration.cmd"
            hook.write_text(
                '@echo off\nif "%HARNESS_ITERATION%"=="3" (exit /b 0) else (exit /b 1)\n',
                encoding="utf-8",
            )
        else:
            hook = tmp_path / "pre-iteration"
            hook.write_text(
                '#!/bin/sh\n[ "$HARNESS_ITERATION" = "3" ] && exit 0 || exit 1\n',
                encoding="utf-8",
            )
            hook.chmod(hook.stat().st_mode | stat.S_IEXEC)
        result = run_hook(
            str(tmp_path),
            "pre-iteration",
            env_vars={"HARNESS_ITERATION": 3},
        )
        assert result is True

    def test_timeout_returns_false(self, tmp_path, capsys):
        hook = tmp_path / "slow-hook"
        if sys.platform == "win32":
            hook = tmp_path / "slow-hook.cmd"
            hook.write_text("@echo off\nping -n 40 127.0.0.1 > nul\n", encoding="utf-8")
        else:
            hook.write_text("#!/bin/sh\nsleep 40\n", encoding="utf-8")
            hook.chmod(hook.stat().st_mode | stat.S_IEXEC)
        with patch("harness_common.hooks.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("hook", 30)
            result = run_hook(str(tmp_path), "slow-hook")
        assert result is False
        assert "timed out" in capsys.readouterr().out

    def test_os_error_returns_false(self, tmp_path, capsys):
        hook = tmp_path / "bad-hook"
        hook.write_text("not executable", encoding="utf-8")
        with patch("harness_common.hooks.subprocess.run") as mock_run:
            mock_run.side_effect = OSError("Permission denied")
            result = run_hook(str(tmp_path), "bad-hook")
        assert result is False
        assert "failed" in capsys.readouterr().out
