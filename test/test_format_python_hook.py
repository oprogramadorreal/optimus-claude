"""Tests for .claude/hooks/format-python.sh PostToolUse hook.

The hook resolves black and isort from a virtualenv near the edited file, so
most tests here plant *stub* formatters that record their own argv. Asserting on
what the hook actually invoked — rather than on its exit status, which is 0 on
every path by design — is what makes the suite fail against a hook that silently
does nothing.

Requires ``bash``: Git Bash on Windows, resolved through the same ``_find_bash``
the orchestrator uses so a WSL ``bash`` on PATH cannot be picked up by accident.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from harness_common.runner import _find_bash, bash_environment

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK_PATH = str(REPO_ROOT / ".claude" / "hooks" / "format-python.sh")
TEMPLATE_PATH = (
    REPO_ROOT / "skills" / "init" / "templates" / "hooks" / "format-python.sh"
)
BASH = _find_bash()

# The hook probes the platform-native layout first so a stale POSIX shim in
# .venv/bin cannot shadow a working .venv/Scripts/black.exe on Windows.
VENV_FIRST = "Scripts" if sys.platform == "win32" else "bin"
VENV_SECOND = "bin" if sys.platform == "win32" else "Scripts"


def _stub_formatters(
    root, tools=("black", "isort"), subdir=VENV_FIRST, venv=".venv", tag=""
):
    """Plant argv-recording stubs for `tools` in <root>/<venv>/<subdir>."""
    target = Path(root) / venv / subdir
    target.mkdir(parents=True, exist_ok=True)
    for tool in tools:
        stub = target / tool
        stub.write_text(
            "#!/usr/bin/env bash\n"
            f'printf "%s\\n" "{tag}{tool} $*" >> "$FORMAT_PY_LOG"\n',
            encoding="utf-8",
            newline="\n",
        )
        stub.chmod(0o755)
    return target


def _run_hook(tool_input, project_dir, log, tool_name="Edit", cwd=None, timeout=30):
    """Run the hook with a full PostToolUse envelope, as Claude Code sends it.

    `project_dir` becomes CLAUDE_PROJECT_DIR; None leaves it unset.
    """
    file_path = tool_input.get("file_path", "") if isinstance(tool_input, dict) else ""
    payload = json.dumps(
        {
            "session_id": "test-session",
            "transcript_path": "/tmp/transcript.jsonl",
            "cwd": str(cwd or project_dir or REPO_ROOT),
            "hook_event_name": "PostToolUse",
            "tool_name": tool_name,
            "tool_input": tool_input,
            "tool_response": {"filePath": file_path, "success": True},
        },
        # Claude Code serializes with JSON.stringify, which emits non-ASCII as
        # raw UTF-8. json.dumps's default (ensure_ascii=True) escapes it to
        # \uXXXX — a payload shape production never sends, which the hook
        # deliberately does not decode.
        ensure_ascii=False,
    )
    env = {**os.environ, "FORMAT_PY_LOG": str(log)}
    if project_dir is None:
        env.pop("CLAUDE_PROJECT_DIR", None)
    else:
        env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    return subprocess.run(
        [BASH, HOOK_PATH],
        input=payload,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        cwd=str(cwd) if cwd else None,
        env=bash_environment(BASH, env),
    )


@pytest.fixture
def log(tmp_path):
    path = tmp_path / "invocations.log"
    path.write_text("", encoding="utf-8")
    return path


def _calls(log):
    return [
        line
        for line in log.read_text(encoding="utf-8", errors="replace").splitlines()
        if line
    ]


def _real_formatters_available():
    """True when the hook can resolve real formatters for a file in this repo."""
    for subdir in ("Scripts", "bin"):
        for ext in ("", ".exe"):
            if (REPO_ROOT / ".venv" / subdir / f"black{ext}").is_file():
                return True
    return shutil.which("black") is not None and shutil.which("isort") is not None


needs_real_formatters = pytest.mark.skipif(
    not _real_formatters_available(),
    reason="black/isort not installed in the repo .venv or on PATH",
)


# --- Dispatch ---------------------------------------------------------------


def test_invokes_both_formatters_on_a_python_file(tmp_path, log):
    _stub_formatters(tmp_path)
    py_file = tmp_path / "example.py"
    py_file.write_text("x=1\n", encoding="utf-8")

    result = _run_hook({"file_path": str(py_file)}, tmp_path, log)

    assert result.returncode == 0
    calls = _calls(log)
    assert len(calls) == 2, calls
    assert calls[0].startswith("black ") and str(py_file) in calls[0]
    assert calls[1].startswith("isort ") and str(py_file) in calls[1]


def test_does_not_invoke_formatters_for_a_non_python_file(tmp_path, log):
    _stub_formatters(tmp_path)
    js_file = tmp_path / "app.js"
    js_file.write_text("const x=1\n", encoding="utf-8")

    result = _run_hook({"file_path": str(js_file)}, tmp_path, log)

    assert result.returncode == 0
    assert _calls(log) == []


@pytest.mark.parametrize("tool_input", [{}, {"file_path": ""}], ids=["absent", "empty"])
def test_does_nothing_without_a_file_path(tmp_path, log, tool_input):
    _stub_formatters(tmp_path)

    result = _run_hook(tool_input, tmp_path, log)

    assert result.returncode == 0
    assert _calls(log) == []


@pytest.mark.parametrize(
    "content_first", [False, True], ids=["path-first", "content-first"]
)
def test_ignores_a_file_path_embedded_in_written_content(tmp_path, log, content_first):
    """A Write payload whose content mentions "file_path" must not redirect the hook.

    The regex scans the whole payload and takes the first match, so the decoy has
    to be tried on both sides of the real key. It cannot win from either: JSON
    escapes the inner quotes, and `"file_path"` followed by `\\` never matches.
    """
    _stub_formatters(tmp_path)
    py_file = tmp_path / "real.py"
    py_file.write_text("x=1\n", encoding="utf-8")
    decoy = '"file_path": "/etc/evil.py"\n'
    tool_input = (
        {"content": decoy, "file_path": str(py_file)}
        if content_first
        else {"file_path": str(py_file), "content": decoy}
    )

    result = _run_hook(tool_input, tmp_path, log, tool_name="Write")

    assert result.returncode == 0
    assert all("/etc/evil.py" not in call for call in _calls(log)), _calls(log)
    assert all(str(py_file) in call for call in _calls(log)), _calls(log)


# --- JSON string decoding ---------------------------------------------------


def test_handles_a_non_ascii_file_path(tmp_path, log):
    """JSON.stringify sends non-ASCII path characters as raw UTF-8."""
    package = tmp_path / "café"
    package.mkdir()
    py_file = package / "app.py"
    py_file.write_text("x=1\n", encoding="utf-8")

    _stub_formatters(tmp_path)
    result = _run_hook({"file_path": str(py_file)}, tmp_path, log)

    assert result.returncode == 0
    assert len(_calls(log)) == 2, result.stderr
    assert all(str(py_file) in call for call in _calls(log)), _calls(log)


@pytest.mark.skipif(
    sys.platform == "win32", reason='Windows filenames cannot contain "'
)
def test_decodes_an_escaped_quote_in_the_file_path(tmp_path, log):
    package = tmp_path / 'we"ird'
    package.mkdir()
    py_file = package / "app.py"
    py_file.write_text("x=1\n", encoding="utf-8")

    _stub_formatters(tmp_path)
    result = _run_hook({"file_path": str(py_file)}, tmp_path, log)

    assert result.returncode == 0
    assert len(_calls(log)) == 2, result.stderr
    assert all(str(py_file) in call for call in _calls(log)), _calls(log)


def test_decodes_escaped_backslashes_in_a_windows_style_path(tmp_path, log):
    """C:\\Users\\... arrives as C:\\\\Users\\\\...; collapsing it would break the walk."""
    package = tmp_path / "pkg"
    package.mkdir()
    py_file = package / "app.py"
    py_file.write_text("x=1\n", encoding="utf-8")
    windows_style = str(py_file).replace("/", "\\")

    _stub_formatters(tmp_path)
    result = _run_hook({"file_path": windows_style}, tmp_path, log)

    assert result.returncode == 0
    assert len(_calls(log)) == 2, result.stderr


# --- Environment resolution -------------------------------------------------


def test_walks_up_from_the_edited_file_to_the_project_venv(tmp_path, log):
    _stub_formatters(tmp_path)
    nested = tmp_path / "packages" / "api" / "src"
    nested.mkdir(parents=True)
    py_file = nested / "app.py"
    py_file.write_text("x=1\n", encoding="utf-8")

    result = _run_hook({"file_path": str(py_file)}, tmp_path, log)

    assert result.returncode == 0
    assert len(_calls(log)) == 2, result.stderr


def test_prefers_the_venv_nearest_the_edited_file(tmp_path, log):
    """Monorepos with per-package venvs must not be formatted by the root one."""
    _stub_formatters(tmp_path, tag="root-")
    package = tmp_path / "packages" / "api"
    package.mkdir(parents=True)
    _stub_formatters(package, tag="pkg-")
    py_file = package / "app.py"
    py_file.write_text("x=1\n", encoding="utf-8")

    result = _run_hook({"file_path": str(py_file)}, tmp_path, log)

    assert result.returncode == 0
    assert all(call.startswith("pkg-") for call in _calls(log)), _calls(log)


@pytest.mark.parametrize("venv_name", [".venv", "venv", "env"])
def test_recognizes_the_common_venv_directory_names(tmp_path, log, venv_name):
    _stub_formatters(tmp_path, venv=venv_name)
    py_file = tmp_path / "app.py"
    py_file.write_text("x=1\n", encoding="utf-8")

    result = _run_hook({"file_path": str(py_file)}, tmp_path, log)

    assert result.returncode == 0
    assert len(_calls(log)) == 2, result.stderr


def test_probes_the_platform_native_subdirectory_first(tmp_path, log):
    """A stale POSIX shim in .venv/bin must not shadow .venv/Scripts on Windows."""
    _stub_formatters(tmp_path, subdir=VENV_FIRST, tag="first-")
    _stub_formatters(tmp_path, subdir=VENV_SECOND, tag="second-")
    py_file = tmp_path / "app.py"
    py_file.write_text("x=1\n", encoding="utf-8")

    result = _run_hook({"file_path": str(py_file)}, tmp_path, log)

    assert result.returncode == 0
    assert all(call.startswith("first-") for call in _calls(log)), _calls(log)


def test_skips_a_directory_named_like_the_formatter(tmp_path, log):
    """[[ -x ]] alone is true for a directory, which the hook would then invoke."""
    (tmp_path / ".venv" / VENV_FIRST / "black").mkdir(parents=True)
    _stub_formatters(tmp_path, subdir=VENV_SECOND, tag="real-")
    py_file = tmp_path / "app.py"
    py_file.write_text("x=1\n", encoding="utf-8")

    result = _run_hook({"file_path": str(py_file)}, tmp_path, log)

    assert result.returncode == 0
    assert "Is a directory" not in result.stderr
    assert all(call.startswith("real-") for call in _calls(log)), _calls(log)


def test_falls_back_to_the_project_venv_for_a_file_outside_the_tree(tmp_path, log):
    project = tmp_path / "project"
    project.mkdir()
    _stub_formatters(project)
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    py_file = outside / "scratch.py"
    py_file.write_text("x=1\n", encoding="utf-8")

    result = _run_hook({"file_path": str(py_file)}, project, log)

    assert result.returncode == 0
    assert len(_calls(log)) == 2, result.stderr


def test_does_not_resolve_relative_to_the_working_directory(tmp_path, log):
    """With CLAUDE_PROJECT_DIR unset, a stray ./.venv must never be executed."""
    stray = tmp_path / "stray"
    stray.mkdir()
    _stub_formatters(stray)
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    py_file = outside / "app.py"
    py_file.write_text("x=1\n", encoding="utf-8")

    result = _run_hook({"file_path": str(py_file)}, None, log, cwd=stray)

    assert result.returncode == 0
    assert _calls(log) == []


def test_does_not_pair_a_venv_black_with_an_isort_from_path(tmp_path, log):
    """Mismatched versions produce an import order the project's own isort rejects."""
    _stub_formatters(tmp_path, tools=("black",))
    py_file = tmp_path / "app.py"
    py_file.write_text("x=1\n", encoding="utf-8")

    result = _run_hook({"file_path": str(py_file)}, tmp_path, log)

    assert result.returncode == 0
    assert [call.split()[0] for call in _calls(log)] == ["black"], _calls(log)
    assert "isort not found" in result.stderr


@pytest.mark.skipif(
    shutil.which("black") is not None or shutil.which("isort") is not None,
    reason="a formatter is on PATH, so the hook legitimately finds one",
)
def test_reports_when_no_formatter_can_be_found(tmp_path, log):
    py_file = tmp_path / "app.py"
    py_file.write_text("x=1\n", encoding="utf-8")

    result = _run_hook({"file_path": str(py_file)}, tmp_path, log)

    assert result.returncode == 0
    assert "black and isort not found" in result.stderr


# --- Real formatters --------------------------------------------------------


@needs_real_formatters
def test_formats_and_sorts_with_the_real_formatters(tmp_path, log):
    py_file = tmp_path / "example.py"
    py_file.write_text("import sys\nimport os\nx=1\n", encoding="utf-8")

    result = _run_hook({"file_path": str(py_file)}, REPO_ROOT, log)

    assert result.returncode == 0, result.stderr
    content = py_file.read_text(encoding="utf-8")
    assert "x = 1" in content, content
    assert content.index("import os") < content.index("import sys"), content


@needs_real_formatters
def test_reports_black_failure_on_invalid_syntax(tmp_path, log):
    py_file = tmp_path / "bad.py"
    py_file.write_text("def f(\n", encoding="utf-8")

    result = _run_hook({"file_path": str(py_file)}, REPO_ROOT, log)

    assert result.returncode == 0
    assert "[format-python] black failed" in result.stderr


@needs_real_formatters
def test_survives_a_nonexistent_python_file(tmp_path, log):
    result = _run_hook({"file_path": str(tmp_path / "gone.py")}, REPO_ROOT, log)

    assert result.returncode == 0


# --- Shipped copy -----------------------------------------------------------


def test_the_shipped_template_is_the_hook_under_test():
    """Everything above exercises .claude/; users install the template copy."""
    assert TEMPLATE_PATH.read_bytes() == Path(HOOK_PATH).read_bytes()
