"""Tests for .claude/hooks/format-python.py PostToolUse hook."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK_PATH = str(
    Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "format-python.py"
)


def _run_hook(tool_input, timeout=10):
    """Run the hook script with the given tool_input dict, return CompletedProcess."""
    payload = json.dumps({"tool_input": tool_input})
    return subprocess.run(
        [sys.executable, HOOK_PATH],
        input=payload,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def test_exits_zero_for_non_python_file():
    result = _run_hook({"file_path": "src/app.js"})
    assert result.returncode == 0


def test_exits_zero_for_empty_file_path():
    result = _run_hook({"file_path": ""})
    assert result.returncode == 0


def test_exits_zero_for_missing_file_path():
    result = _run_hook({})
    assert result.returncode == 0


def test_runs_black_and_isort_on_python_file(tmp_path):
    """When given a real .py file, the hook runs black and isort without error."""
    py_file = tmp_path / "example.py"
    py_file.write_text("import os\nimport sys\nx=1\n", encoding="utf-8")
    result = _run_hook({"file_path": str(py_file)})
    assert result.returncode == 0
    # Verify the file was actually formatted (black adds spaces around =)
    content = py_file.read_text(encoding="utf-8")
    assert "x = 1" in content


def test_reports_black_failure_on_invalid_syntax(tmp_path):
    """Black fails on invalid syntax; the hook prints a warning but doesn't crash."""
    py_file = tmp_path / "bad.py"
    py_file.write_text("def f(\n", encoding="utf-8")
    result = _run_hook({"file_path": str(py_file)})
    # Hook should still exit 0 (it catches errors gracefully)
    assert result.returncode == 0
    assert "[format-python] black failed" in result.stderr


def test_handles_nonexistent_python_file():
    """When the .py file doesn't exist, formatters fail but hook doesn't crash."""
    result = _run_hook({"file_path": "/nonexistent/path/file.py"})
    assert result.returncode == 0
