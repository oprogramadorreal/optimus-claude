import re
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


def build_claude_session_cmd(prompt, harness_system, allowed_tools, max_turns):
    """Assemble the claude CLI argument list for a harness session.

    Both harnesses launch ``claude -p`` the same way; this is the single
    source of truth for the option ordering, the allowed-tools/skip-permissions
    fork, and the JSON output format.
    """
    cmd = [
        "claude",
        "-p",
        prompt,
        "--append-system-prompt",
        harness_system,
    ]
    if allowed_tools:
        cmd.extend(["--allowedTools", allowed_tools])
    else:
        cmd.append("--dangerously-skip-permissions")
    cmd.extend(
        [
            "--max-turns",
            str(max_turns),
            "--output-format",
            "json",
        ]
    )
    return cmd


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
    except FileNotFoundError as exc:
        # Most commonly: bash not on PATH on Windows when Git Bash is missing.
        # Surface a clear, actionable message instead of letting the harness crash.
        msg = f"Command not found: {exc.filename or 'bash'}"
        if sys.platform == "win32":
            msg += " (install Git Bash and ensure 'bash' is on PATH)"
        print(f"{prefix} {msg}")
        return False, msg
    except subprocess.TimeoutExpired as exc:
        print(f"{prefix} Tests timed out after {timeout}s")

        def _decode(blob):
            if blob is None:
                return ""
            return blob.decode(errors="replace") if isinstance(blob, bytes) else blob

        partial = "\n".join(
            filter(None, [_decode(exc.stdout), _decode(exc.stderr)])
        ).strip()
        tail = "\n".join(partial.split("\n")[-5:]) if partial else ""
        summary = f"Test command timed out after {timeout}s"
        if tail:
            summary = f"{summary}\n{tail}"
        return False, summary
    passed = result.returncode == 0
    combined = "\n".join(filter(None, [result.stdout, result.stderr])).strip()
    summary = extract_test_summary(combined)
    status = "PASS" if passed else "FAIL"
    print(f"{prefix} Tests: {status}")
    return passed, summary


# ---------------------------------------------------------------------------
# Framework-aware test output extraction
# ---------------------------------------------------------------------------

# Patterns for summary lines emitted by common test frameworks.
_PYTEST_SUMMARY = re.compile(
    r"^[=]+ .*(passed|failed|error|warnings?).*[=]+\s*$", re.MULTILINE
)
_PYTEST_FAILURE = re.compile(r"^FAILED (.+?)(?:\s*-\s*(.+))?$", re.MULTILINE)
_JEST_SUMMARY = re.compile(
    r"^Tests?:\s+\d+.*(?:passed|failed)", re.MULTILINE | re.IGNORECASE
)
_GO_FAIL = re.compile(r"^--- FAIL:\s+(.+)", re.MULTILINE)
_CARGO_FAIL = re.compile(r"^test result: FAILED", re.MULTILINE)

_FALLBACK_TAIL_LINES = 10


def extract_test_summary(raw_output):
    """Extract a compact, diagnostic test summary from raw test output.

    Tries framework-specific heuristics (pytest, jest, go test, cargo test)
    to capture the summary line and first failure assertion.  Falls back to
    the last 10 lines for unknown frameworks.

    Returns a string suitable for storage in ``last_run_output_summary``.
    """
    if not raw_output:
        return ""

    lines = raw_output.split("\n")

    # --- pytest ---
    match = _PYTEST_SUMMARY.search(raw_output)
    if match:
        parts = [match.group(0).strip()]
        # Grab the first FAILED line for diagnostic context
        fail = _PYTEST_FAILURE.search(raw_output)
        if fail:
            parts.append(f"First failure: {fail.group(0).strip()}")
        return "\n".join(parts)

    # --- jest ---
    match = _JEST_SUMMARY.search(raw_output)
    if match:
        # Collect all "Tests:" and "Test Suites:" lines near the summary
        summary_lines = [
            line.strip()
            for line in lines
            if re.match(r"^\s*(Tests?|Test Suites?):", line, re.IGNORECASE)
        ]
        return "\n".join(summary_lines) if summary_lines else match.group(0).strip()

    # --- go test ---
    match = _GO_FAIL.search(raw_output)
    if match:
        parts = [f"First failure: {match.group(0).strip()}"]
        # Look for FAIL line with package
        for line in lines:
            if line.startswith("FAIL\t"):
                parts.append(line.strip())
                break
        return "\n".join(parts)

    # --- cargo test ---
    match = _CARGO_FAIL.search(raw_output)
    if match:
        parts = [match.group(0).strip()]
        # Look for "failures:" section entries
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("failures:"):
                parts.append(stripped)
                break
        return "\n".join(parts)

    # --- fallback: last N lines ---
    tail = lines[-_FALLBACK_TAIL_LINES:]
    return "\n".join(tail).strip()
