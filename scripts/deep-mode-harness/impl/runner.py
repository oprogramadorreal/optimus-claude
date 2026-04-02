import shutil
import subprocess
import sys
from pathlib import Path

from .constants import DEFAULT_TEST_TIMEOUT, PREFIX


def _find_bash():
    """Return the path to a usable bash executable, preferring Git Bash on Windows."""
    if sys.platform != "win32":
        return "bash"

    # shutil.which respects PATH order — check if it resolves to WSL's bash
    candidate = shutil.which("bash")
    if candidate:
        normalized = candidate.replace("\\", "/").lower()
        if "system32" not in normalized:
            return candidate  # Not WSL — use it (likely Git Bash already on PATH)

    # WSL bash or no bash on PATH — look for Git Bash explicitly
    # Method 1: use git --exec-path to find Git's installation
    try:
        result = subprocess.run(
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


def run_tests(test_command, cwd, timeout=DEFAULT_TEST_TIMEOUT):
    """Run the project's test command. Returns (passed: bool, output: str)."""
    print(f"{PREFIX} Running tests: {test_command}")
    if sys.platform == "win32":
        # On Windows, shell=True uses cmd.exe which misparses bash operators
        # (&&, ||), subshells ($(...)), env vars ($VAR), and redirections (2>).
        # Always route through bash for consistent behavior.
        effective_command = [_find_bash(), "-c", test_command]
    else:
        effective_command = test_command
    try:
        result = subprocess.run(
            effective_command,
            shell=isinstance(effective_command, str),
            capture_output=True,
            text=True,
            cwd=str(cwd),
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        print(f"{PREFIX} Tests timed out after {timeout}s")
        return False, f"Test command timed out after {timeout}s"
    passed = result.returncode == 0
    combined = "\n".join(filter(None, [result.stdout, result.stderr])).strip()
    summary = "\n".join(combined.split("\n")[-5:])
    status = "PASS" if passed else "FAIL"
    print(f"{PREFIX} Tests: {status}")
    return passed, summary


def run_skill_session(progress, args, resolved_progress_path):
    """
    Launch a fresh claude -p session for one iteration.
    Returns the raw stdout output.
    """
    skill = progress["skill"]
    iteration = progress["iteration"]["current"]
    max_iter = progress["config"]["max_iterations"]
    # Use forward slashes for cross-platform compatibility in system prompt
    progress_path = str(resolved_progress_path).replace("\\", "/")

    # Build the skill invocation prompt (skill is validated by argparse choices)
    if skill == "code-review":
        prompt = "/optimus:code-review deep"
    else:
        prompt = f"/optimus:refactor deep {max_iter}"

    # Add scope hint
    scope_paths = progress["scope_files"]["current"]
    if scope_paths:
        paths_str = ", ".join(scope_paths[:20])
        prompt += f' "focus on: {paths_str}"'

    # Harness-mode system prompt
    harness_system = (
        f"HARNESS_MODE_ACTIVE: You are running inside the deep-mode harness. "
        f"Progress file: {progress_path}\n"
        f"This is iteration {iteration} of {max_iter}. "
        f"Do NOT use AskUserQuestion. Do NOT loop. Do NOT run tests. "
        f"Read the progress file for accumulated findings and scope. "
        f"After applying fixes, output structured JSON in a "
        f"```json:harness-output block and stop."
    )

    cmd = [
        "claude",
        "-p",
        prompt,
        "--append-system-prompt",
        harness_system,
    ]

    # Permission handling: --allowedTools (safer) or --dangerously-skip-permissions (default)
    if args.allowed_tools:
        cmd.extend(["--allowedTools", args.allowed_tools])
    else:
        cmd.append("--dangerously-skip-permissions")

    cmd.extend(
        [
            "--max-turns",
            str(args.max_turns),
            "--output-format",
            "json",
        ]
    )

    if args.verbose:
        print(f"{PREFIX} Command: {' '.join(cmd[:6])}...")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=progress["config"]["project_root"],
        timeout=args.timeout,
    )

    if args.verbose:
        print(f"{PREFIX} Exit code: {result.returncode}")
        if result.stderr:
            print(f"{PREFIX} Stderr: {result.stderr[:500]}")

    if result.returncode == 1:
        print(
            f"{PREFIX} WARNING: claude exited with code 1 (may indicate partial failure): {result.stderr[:200]}"
        )
    elif result.returncode > 1:
        raise RuntimeError(
            f"claude exited with code {result.returncode}: {result.stderr[:200]}"
        )

    return result.stdout
