from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from harness_common.runner import build_claude_session_cmd as _build_cmd
from impl.runner import (
    _build_harness_system,
    _build_refactor_prompt,
    _build_unit_test_prompt,
    run_coverage_session,
    run_tests,
)


class TestRunTests:
    @patch("impl.runner._shared_run_tests")
    def test_passes_prefix(self, mock_shared):
        mock_shared.return_value = (True, "ok")
        passed, summary = run_tests("pytest", "/tmp")
        assert passed is True
        # Verify the coverage prefix is passed
        mock_shared.assert_called_once()
        call_kwargs = mock_shared.call_args
        assert call_kwargs[1]["prefix"] == "[coverage]"


class TestBuildUnitTestPrompt:
    def test_basic(self):
        result = _build_unit_test_prompt(5, "")
        assert result == "/optimus:unit-test deep 5"

    def test_with_scope(self):
        result = _build_unit_test_prompt(3, "src/api")
        assert result == '/optimus:unit-test deep 3 "src/api"'


class TestBuildRefactorPrompt:
    def test_basic_no_items(self):
        result = _build_refactor_prompt(5, [])
        assert "testability" in result
        assert result == "/optimus:refactor deep 5 testability"

    def test_with_untestable_items(self):
        items = [
            {"file": "src/db.py"},
            {"file": "src/auth.py"},
            {"file": "src/db.py"},  # duplicate
        ]
        result = _build_refactor_prompt(5, items)
        assert "focus on:" in result
        assert "src/auth.py" in result
        assert "src/db.py" in result

    def test_empty_file_items_skipped(self):
        items = [{"file": ""}, {"file": "src/db.py"}]
        result = _build_refactor_prompt(5, items)
        assert "src/db.py" in result

    def test_caps_at_20_paths(self):
        items = [{"file": f"src/f{i:03d}.py"} for i in range(25)]
        result = _build_refactor_prompt(5, items)
        assert "f019" in result
        assert "f020" not in result


class TestBuildHarnessSystem:
    def _make_progress(self, untestable=None):
        return {
            "coverage": {"baseline": None, "current": None, "history": []},
            "tests_created": [],
            "untestable_code": untestable or [],
            "test_results": {"last_full_run": None, "last_run_output_summary": ""},
        }

    def test_unit_test_phase(self):
        result = _build_harness_system(
            "/tmp/progress.json", 2, 5, "unit-test", self._make_progress()
        )
        assert "HARNESS_MODE_ACTIVE" in result
        assert "test-coverage harness" in result
        assert "cycle 2 of 5" in result
        assert "unit-test" in result
        assert "Write tests" in result
        assert "Do NOT run tests" not in result

    def test_refactor_phase(self):
        result = _build_harness_system(
            "/tmp/progress.json", 1, 3, "refactor", self._make_progress()
        )
        assert "HARNESS_MODE_ACTIVE" in result
        assert "phase: refactor" in result
        assert "Do NOT run tests" in result
        assert "testability barriers" in result

    def test_includes_digest_and_coaching(self):
        result = _build_harness_system(
            "/tmp/progress.json", 1, 5, "unit-test", self._make_progress()
        )
        assert "Progress Digest" in result
        assert "Guidance" in result


class TestBuildCmd:
    def test_with_allowed_tools(self):
        cmd = _build_cmd("prompt", "system", "Read,Edit", 30)
        assert "--allowedTools" in cmd
        assert "Read,Edit" in cmd
        assert "--dangerously-skip-permissions" not in cmd

    def test_without_allowed_tools(self):
        cmd = _build_cmd("prompt", "system", "", 30)
        assert "--dangerously-skip-permissions" in cmd

    def test_includes_output_format(self):
        cmd = _build_cmd("prompt", "system", "", 15)
        assert "--output-format" in cmd
        assert "json" in cmd
        assert "--max-turns" in cmd
        assert "15" in cmd


class TestRunCoverageSession:
    def _make_progress(self, cycle=1, max_cycles=5, scope=""):
        return {
            "cycle": {"current": cycle},
            "config": {
                "max_cycles": max_cycles,
                "project_root": "/tmp/project",
                "scope": scope,
            },
            "untestable_code": [],
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
        result = run_coverage_session(
            progress, args, "/tmp/progress.json", "unit-test", _run=mock_run
        )
        assert result == "output"

    def test_refactor_phase(self):
        mock_run = MagicMock(
            return_value=MagicMock(returncode=0, stdout="refactor output", stderr="")
        )
        progress = self._make_progress()
        progress["untestable_code"] = [{"file": "src/db.py"}]
        args = self._make_args()
        result = run_coverage_session(
            progress, args, "/tmp/progress.json", "refactor", _run=mock_run
        )
        assert result == "refactor output"

    def test_verbose_prints(self, capsys):
        mock_run = MagicMock(
            return_value=MagicMock(returncode=0, stdout="out", stderr="warn")
        )
        progress = self._make_progress()
        args = self._make_args(verbose=True)
        run_coverage_session(
            progress, args, "/tmp/progress.json", "unit-test", _run=mock_run
        )
        captured = capsys.readouterr().out
        assert "Command:" in captured
        assert "Exit code: 0" in captured
        assert "Stderr: warn" in captured

    def test_verbose_no_stderr(self, capsys):
        mock_run = MagicMock(
            return_value=MagicMock(returncode=0, stdout="out", stderr="")
        )
        progress = self._make_progress()
        args = self._make_args(verbose=True)
        run_coverage_session(
            progress, args, "/tmp/progress.json", "unit-test", _run=mock_run
        )
        captured = capsys.readouterr().out
        assert "Stderr:" not in captured

    def test_exit_code_greater_than_1_raises(self):
        mock_run = MagicMock(
            return_value=MagicMock(returncode=2, stdout="", stderr="fatal")
        )
        progress = self._make_progress()
        args = self._make_args()
        with pytest.raises(RuntimeError, match="claude exited with code 2"):
            run_coverage_session(
                progress, args, "/tmp/progress.json", "unit-test", _run=mock_run
            )

    def test_exit_code_1_warns(self, capsys):
        mock_run = MagicMock(
            return_value=MagicMock(returncode=1, stdout="partial", stderr="warn")
        )
        progress = self._make_progress()
        args = self._make_args()
        result = run_coverage_session(
            progress, args, "/tmp/progress.json", "unit-test", _run=mock_run
        )
        assert result == "partial"
        assert "WARNING" in capsys.readouterr().out
