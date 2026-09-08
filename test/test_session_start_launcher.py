"""Integration tests for the SessionStart command in hooks/hooks.json."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from harness_common.runner import _find_bash

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOKS_PATH = REPO_ROOT / "hooks" / "hooks.json"


def _session_start_command():
    config = json.loads(HOOKS_PATH.read_text(encoding="utf-8"))
    return config["hooks"]["SessionStart"][0]["hooks"][0]["command"]


@pytest.mark.skipif(sys.platform != "win32", reason="Windows cmd.exe behavior")
@pytest.mark.parametrize("location", ["outside-repo", "repo-root", "subdirectory"])
@pytest.mark.parametrize(
    "noisy_bash", [False, True], ids=["system-path", "utf16-error"]
)
def test_windows_launcher_uses_git_bash(tmp_path, location, noisy_bash):
    git = shutil.which("git")
    if git is None:
        pytest.skip("git is not installed")
    git_exec_path = subprocess.run(
        [git, "--exec-path"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    ).stdout.strip()
    git_from_cmd = Path(git_exec_path).parents[2] / "cmd" / "git.exe"
    if not git_from_cmd.is_file():
        pytest.skip("git on PATH is not a Git for Windows install")

    env = os.environ.copy()
    windows_root = Path(env.get("SystemRoot", "C:/Windows"))
    env["PATH"] = os.pathsep.join(
        [str(git_from_cmd.parent), str(windows_root / "System32")]
    )
    assert shutil.which("git", path=env["PATH"]) is not None
    # System32 may hold WSL's bash.exe, which cannot open C:/ paths. The
    # launcher must use Git's Bash instead, so its presence is not asserted away.
    if noisy_bash:
        # Reproduce WSL's UTF-16 stdout diagnostic without depending on whether
        # the machine has WSL or a Linux distribution installed.
        stub_dir = tmp_path / "bash stub"
        stub_dir.mkdir()
        (stub_dir / "bash.cmd").write_text(
            '@echo off\n"%COMSPEC%" /d /u /c echo Simulated WSL startup failure\n'
            "exit /b 1\n",
            encoding="utf-8",
        )
        env["PATH"] = os.pathsep.join([str(stub_dir), env["PATH"]])

    plugin_root = str(REPO_ROOT)
    env["PLUGIN_ROOT"] = plugin_root
    env["CLAUDE_PLUGIN_ROOT"] = plugin_root
    # Codex substitutes a native Windows path, including backslashes. Testing
    # only a normalized path misses quoting failures in the Git launcher.
    command = _session_start_command().replace("${CLAUDE_PLUGIN_ROOT}", plugin_root)
    cwd = tmp_path
    if location != "outside-repo":
        subprocess.run([git, "init", "-q", str(tmp_path)], check=True)
    if location == "subdirectory":
        # Only the child is initialized: running from Git's repository root
        # would report missing testing docs instead of the child's clean state.
        root_docs = tmp_path / ".claude" / "docs"
        root_docs.mkdir(parents=True)
        (tmp_path / ".claude" / "CLAUDE.md").write_text("# Root", encoding="utf-8")
        (root_docs / "coding-guidelines.md").write_text("# Code", encoding="utf-8")
        cwd = tmp_path / "nested project" / "app"
        child_docs = cwd / ".claude" / "docs"
        child_docs.mkdir(parents=True)
        (cwd / ".claude" / "CLAUDE.md").write_text("# Child", encoding="utf-8")
        (child_docs / "coding-guidelines.md").write_text("# Code", encoding="utf-8")
        (child_docs / "testing.md").write_text("# Tests", encoding="utf-8")

    direct_env = env.copy()
    git_root = git_from_cmd.parent.parent
    direct_env["PATH"] = os.pathsep.join(
        [str(git_root / "usr" / "bin"), str(git_root / "bin"), env["PATH"]]
    )
    direct = subprocess.run(
        [_find_bash(), str(REPO_ROOT / "hooks" / "session-start")],
        cwd=cwd,
        env=direct_env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    result = subprocess.run(
        command,
        shell=True,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert direct.returncode == 0, direct.stderr
    # Failed WSL startup must not contaminate model-visible hook context.
    assert result.stdout == direct.stdout
    assert not result.stderr
    if location == "subdirectory":
        assert "Testing docs missing" not in result.stdout
        assert "Not initialized" not in result.stdout
    else:
        assert "$optimus:init" in result.stdout
    assert "/optimus:<skill>" in result.stdout
    assert "$optimus:<skill>" in result.stdout


@pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell behavior")
@pytest.mark.parametrize("shell_name", ["powershell", "pwsh"])
def test_codex_powershell_launcher_delivers_context(tmp_path, shell_name):
    shell = shutil.which(shell_name)
    if shell is None:
        pytest.skip(f"{shell_name} is not installed")
    env = os.environ.copy()
    env["PLUGIN_ROOT"] = env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    command = _session_start_command().replace("${CLAUDE_PLUGIN_ROOT}", str(REPO_ROOT))
    result = subprocess.run(
        [shell, "-NoProfile", "-Command", command],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("Optimus session context:")
    assert "Running under Codex" in result.stdout
    assert f"Plugin root: {REPO_ROOT}" in result.stdout


@pytest.mark.parametrize("initialized", [False, True])
def test_codex_context_is_not_misdetected_as_json(tmp_path, initialized):
    bash = _find_bash()
    if initialized:
        docs = tmp_path / ".claude" / "docs"
        docs.mkdir(parents=True)
        (docs.parent / "CLAUDE.md").write_text("# Project", encoding="utf-8")
        for name in ("coding-guidelines.md", "testing.md"):
            (docs / name).write_text("# Configured", encoding="utf-8")
    env = os.environ.copy()
    env["PLUGIN_ROOT"] = env["CLAUDE_PLUGIN_ROOT"] = REPO_ROOT.as_posix()
    if sys.platform == "win32":
        git_root = Path(bash).parent.parent
        env["PATH"] = os.pathsep.join(
            [str(git_root / "usr" / "bin"), str(git_root / "bin"), env["PATH"]]
        )
    result = subprocess.run(
        [bash, str(REPO_ROOT / "hooks" / "session-start")],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "Running under Codex" in result.stdout
    assert f"Plugin root: {REPO_ROOT.as_posix()}" in result.stdout
    # Codex 0.153.4 routes leading '[' / '{' to its JSON parser. Plain text
    # starting with [optimus] exits successfully but loses all hook context.
    assert not result.stdout.lstrip().startswith(("[", "{"))


def test_bash_launcher_preserves_claude_cwd_and_output(tmp_path):
    bash = _find_bash()
    cwd = tmp_path / "child directory"
    cwd.mkdir()
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = REPO_ROOT.as_posix()
    env.pop("PLUGIN_ROOT", None)
    # An inherited Git variable must not affect the normal Bash launch path.
    env["GIT_PREFIX"] = "not-the-working-directory/"
    if sys.platform == "win32":
        git_root = Path(bash).parent.parent
        env["PATH"] = os.pathsep.join(
            [str(git_root / "usr" / "bin"), str(git_root / "bin"), env["PATH"]]
        )
    outputs = []
    for args in (
        [bash, str(REPO_ROOT / "hooks" / "session-start")],
        [bash, "-c", _session_start_command()],
    ):
        result = subprocess.run(
            args,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        assert result.returncode == 0, result.stderr
        assert not result.stderr
        outputs.append(result.stdout)
    assert outputs[0] == outputs[1]
    assert "/optimus:init" in outputs[1]
    assert "Running under Codex" not in outputs[1]
