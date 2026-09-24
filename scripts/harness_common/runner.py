import errno
import os
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

from .constants import DEFAULT_TEST_TIMEOUT


def _find_bash(platform=None, which_fn=None, run_fn=None):
    """Return the path to a usable bash executable, preferring Git Bash on Windows."""
    which_fn = which_fn or shutil.which
    run_fn = run_fn or subprocess.run
    if (platform or sys.platform) != "win32":
        return "bash"

    # Match Claude Code's documented override, including installations outside
    # Program Files. An invalid explicit choice should produce an error, not
    # silently run a different shell.
    override = os.environ.get("CLAUDE_CODE_GIT_BASH_PATH")
    if override:
        if not os.path.isfile(override):
            raise FileNotFoundError(
                errno.ENOENT,
                "CLAUDE_CODE_GIT_BASH_PATH does not point to a Bash executable",
                override,
            )
        return override

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
            encoding="utf-8",
            errors="replace",
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


def bash_environment(bash, env=None, platform=None):
    """Give native Windows Bash its own utilities without changing the caller."""
    environment = dict(os.environ if env is None else env)
    if (platform or sys.platform) != "win32":
        return environment
    executable = Path(bash)
    # Git for Windows ships bash in bin or usr/bin. Merely locating bash.exe
    # does not add cat, dirname, etc. when the user installed only git/cmd on PATH.
    root = executable.parent.parent
    if root.name.lower() == "usr":
        root = root.parent
    paths = [root / "usr" / "bin", root / "bin", root / "cmd"]
    paths = [str(path) for path in paths if path.is_dir()]
    if paths and executable.is_absolute():
        path_keys = [key for key in environment if key.lower() == "path"]
        inherited = environment[path_keys[-1]] if path_keys else ""
        for key in path_keys:
            del environment[key]
        environment["PATH"] = ";".join([*paths, inherited])
    return environment


def _kill_tree(proc):
    """Kill the test shell and, best effort, every process it started."""
    try:
        if sys.platform == "win32":
            # /T follows Windows parent PIDs; an MSYS fork+exec can break that
            # link, which is why run_tests never waits on a pipe afterwards.
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True,
                timeout=30,
            )
        else:
            os.killpg(proc.pid, signal.SIGKILL)
    except (OSError, subprocess.SubprocessError):
        pass
    proc.kill()


def _read_output(log):
    # Decode as UTF-8, never the locale codec (cp1252 on Windows), and
    # normalize newlines the way text mode would.
    log.seek(0)
    text = log.read().decode("utf-8", errors="replace")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def run_tests(test_command, cwd, timeout=DEFAULT_TEST_TIMEOUT, prefix="[harness]"):
    """Run the project's test command. Returns (passed: bool, output: str)."""
    print(f"{prefix} Running tests: {test_command}")
    # shell=True would mean cmd.exe on Windows and /bin/sh (dash on
    # Debian/Ubuntu) elsewhere; run the documented command under bash on every
    # platform so &&, $(...), $VAR, 2> and `source` behave as in the Bash tool.
    try:
        bash = _find_bash()
    except FileNotFoundError as exc:
        msg = f"{exc.strerror}: {exc.filename}"
        print(f"{prefix} {msg}")
        return False, msg
    # Capture to files, not pipes: after a timeout, draining a pipe waits for
    # every process still holding it open, so one surviving grandchild would
    # make the timeout unbounded.
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        try:
            proc = subprocess.Popen(
                [bash, "-c", test_command],
                shell=False,
                stdout=out,
                stderr=err,
                cwd=str(cwd),
                env=bash_environment(bash),
                # POSIX: own process group, so a timeout kills the whole tree.
                start_new_session=sys.platform != "win32",
            )
        except FileNotFoundError as exc:
            # Most commonly: bash not on PATH on Windows when Git Bash is missing.
            # Surface a clear, actionable message instead of letting the harness crash.
            msg = f"Command not found: {exc.filename or 'bash'}"
            if sys.platform == "win32":
                msg += " (install Git Bash and ensure 'bash' is on PATH)"
            print(f"{prefix} {msg}")
            return False, msg
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            _kill_tree(proc)
            proc.wait()
            print(f"{prefix} Tests timed out after {timeout}s")
            partial = "\n".join(
                filter(None, [_read_output(out), _read_output(err)])
            ).strip()
            tail = "\n".join(partial.split("\n")[-5:]) if partial else ""
            summary = f"Test command timed out after {timeout}s"
            return False, f"{summary}\n{tail}" if tail else summary
        except BaseException:
            _kill_tree(proc)
            raise
        stdout, stderr = _read_output(out), _read_output(err)
    passed = proc.returncode == 0
    combined = "\n".join(filter(None, [stdout, stderr])).strip()
    summary = "\n".join(combined.split("\n")[-5:])
    status = "PASS" if passed else "FAIL"
    print(f"{prefix} Tests: {status}")
    return passed, summary
