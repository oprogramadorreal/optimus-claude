"""Integration tests for the Claude and Codex SessionStart launchers."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from harness_common.runner import _find_bash, bash_environment

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOKS_PATH = REPO_ROOT / "hooks" / "hooks.json"
CODEX_MANIFEST_PATH = REPO_ROOT / ".codex-plugin" / "plugin.json"


def _session_start_command(host="claude", windows=None):
    hooks_path = HOOKS_PATH
    if host == "codex":
        manifest = json.loads(CODEX_MANIFEST_PATH.read_text(encoding="utf-8"))
        hooks_path = REPO_ROOT / manifest["hooks"]
    config = json.loads(hooks_path.read_text(encoding="utf-8"))
    hook = config["hooks"]["SessionStart"][0]["hooks"][0]
    if windows is None:
        windows = sys.platform == "win32"
    if host == "codex" and windows:
        return hook["commandWindows"]
    return hook["command"]


def _codex_windows_command():
    # Codex substitutes native Windows paths before invoking the shell.
    return (
        _session_start_command("codex")
        .replace("${PLUGIN_ROOT}", str(REPO_ROOT))
        .replace("${CLAUDE_PLUGIN_ROOT}", str(REPO_ROOT))
    )


def test_hosts_select_separate_hooks_with_matching_plugin_identity():
    claude = json.loads(
        (REPO_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    codex = json.loads(CODEX_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert (codex["name"], codex["version"]) == (claude["name"], claude["version"])
    # Claude must continue using its standard hooks/hooks.json discovery.
    assert "hooks" not in claude
    assert (REPO_ROOT / codex["hooks"]).resolve() != HOOKS_PATH.resolve()
    assert _session_start_command("claude").startswith("bash ")
    assert _session_start_command("codex", windows=False).startswith("bash ")
    assert "session-start.ps1" in _session_start_command("codex", windows=True)


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
    env.pop("CLAUDE_CODE_GIT_BASH_PATH", None)
    windows_root = Path(env.get("SystemRoot", "C:/Windows"))
    env["PATH"] = os.pathsep.join(
        [
            str(git_from_cmd.parent),
            str(windows_root / "System32"),
            str(windows_root / "System32" / "WindowsPowerShell" / "v1.0"),
        ]
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
    command = _codex_windows_command()
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
    command = _codex_windows_command()
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
    command = (
        _codex_windows_command()
        if sys.platform == "win32"
        else [bash, "-c", _session_start_command("codex", windows=False)]
    )
    result = subprocess.run(
        command,
        shell=sys.platform == "win32",
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


def test_codex_adapter_is_scoped_to_matching_host_environment(tmp_path):
    """Host adaptation must not add instructions to an initialized Claude run."""
    docs = tmp_path / ".claude" / "docs"
    docs.mkdir(parents=True)
    (docs.parent / "CLAUDE.md").write_text("# Project", encoding="utf-8")
    for name in ("coding-guidelines.md", "testing.md"):
        (docs / name).write_text("# Configured", encoding="utf-8")
    bash = _find_bash()
    for plugin_root in (None, "stray-plugin-root", REPO_ROOT.as_posix()):
        env = bash_environment(bash)
        env["CLAUDE_PLUGIN_ROOT"] = REPO_ROOT.as_posix()
        env.pop("PLUGIN_ROOT", None)
        if plugin_root:
            env["PLUGIN_ROOT"] = plugin_root
        result = subprocess.run(
            [bash, str(REPO_ROOT / "hooks" / "session-start")],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
        assert result.returncode == 0, result.stderr
        if plugin_root == REPO_ROOT.as_posix():
            assert "Running under Codex" in result.stdout
            assert REPO_ROOT.as_posix() in result.stdout
            assert not result.stdout.lstrip().startswith(("[", "{"))
        else:
            assert result.stdout == ""


def test_claude_launcher_delivers_context_without_git_on_path(tmp_path):
    bash = shutil.which(_find_bash())
    assert bash is not None
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = REPO_ROOT.as_posix()
    env.pop("PLUGIN_ROOT", None)
    env["OPTIMUS_TEST_BASH"] = Path(bash).as_posix()
    env["OPTIMUS_TEST_EMPTY_PATH"] = tmp_path.as_posix()
    # Keep only a Bash lookup helper: it runs the real executable and hook in
    # a child process, while every Git invocation encounters an empty PATH.
    command = (
        'bash() { "$OPTIMUS_TEST_BASH" "$@"; }; '
        'PATH="$OPTIMUS_TEST_EMPTY_PATH"; ' + _session_start_command()
    )
    result = subprocess.run(
        [bash, "-c", command],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert not result.stderr
    assert "/optimus:init" in result.stdout
    assert "Running under Codex" not in result.stdout


def test_claude_launcher_keeps_non_git_context_with_invalid_git_config(tmp_path):
    git = shutil.which("git")
    if git is None:
        pytest.skip("git is not installed")
    subprocess.run([git, "init", "-q", str(tmp_path)], check=True)
    (tmp_path / ".git" / "config").write_text("invalid config file\n", encoding="utf-8")
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = REPO_ROOT.as_posix()
    env.pop("PLUGIN_ROOT", None)
    result = subprocess.run(
        [_find_bash(), "-c", _session_start_command()],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert not result.stderr
    assert "/optimus:init" in result.stdout
