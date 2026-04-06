import shutil
import subprocess
import sys
from pathlib import Path

from .constants import DEFAULT_TEST_TIMEOUT


def _find_bash(platform=None, which_fn=None, run_fn=None):
    """Return the path to a usable bash executable, preferring Git Bash on Windows."""
    which_fn = which_fn or shutil.which
    run_fn = run_fn or subprocess.run
    if (platform or sys.platform) != "win32":
        return "bash"

    # shutil.which respects PATH order — check if it resolves to WSL's bash
    candidate = which_fn("bash")
    if candidate:
        normalized = candidate.replace("\\", "/").lower()
        if "system32" not in normalized:
            return candidate  # Not WSL — use it (likely Git Bash already on PATH)

    # WSL bash or no bash on PATH — look for Git Bash explicitly
    # Method 1: use git --exec-path to find Git's installation
    try:
        result = run_fn(
            ["git", "--exec-path"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            # e.g. "C:/Program Files/Git/mingw64/libexec/git-core"
            git_exec = Path(result.stdout.strip())
            git_install_dir = (
                git_exec.parent.parent.parent
            )  # up from mingw64/libexec/git-core
            git_bash = git_install_dir / "bin" / "bash.exe"
            if git_bash.exists():
                return str(git_bash)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Method 2: check common installation paths
    for path in [
        Path("C:/Program Files/Git/bin/bash.exe"),
        Path("C:/Program Files (x86)/Git/bin/bash.exe"),
    ]:
        if path.exists():
            return str(path)

    # Fallback: return bare "bash" and let it fail with a clear error downstream
    return "bash"


def run_tests(test_command, cwd, timeout=DEFAULT_TEST_TIMEOUT, prefix="[harness]"):
    """Run the project's test command. Returns (passed: bool, output: str)."""
    print(f"{prefix} Running tests: {test_command}")
    if sys.platform == "win32":
        # On Windows, shell=True uses cmd.exe which misparses bash operators
        # (&&, ||), subshells ($(...)), env vars ($VAR), and redirections (2>).
        # Always route through bash for consistent behavior.
        effective_command = [_find_bash(), "-c", test_command]
        use_shell = False
    else:
        effective_command = test_command
        use_shell = True
    try:
        result = subprocess.run(
            effective_command,
            shell=use_shell,
            capture_output=True,
            text=True,
            cwd=str(cwd),
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        print(f"{prefix} Tests timed out after {timeout}s")
        return False, f"Test command timed out after {timeout}s"
    passed = result.returncode == 0
    combined = "\n".join(filter(None, [result.stdout, result.stderr])).strip()
    summary = "\n".join(combined.split("\n")[-5:])
    status = "PASS" if passed else "FAIL"
    print(f"{prefix} Tests: {status}")
    return passed, summary
