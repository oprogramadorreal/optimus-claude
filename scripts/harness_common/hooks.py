import os
import subprocess
from pathlib import Path

DEFAULT_HOOKS_DIR = ".claude/harness-hooks"


def run_hook(hooks_dir, event, env_vars=None, prefix="[harness]"):
    """Run a hook script for the given event, if it exists.

    Looks for an executable file named ``event`` (e.g. ``pre-iteration``)
    in ``hooks_dir``.  Passes context via environment variables.

    Fail-open: a missing hook, non-zero exit, or execution error is logged
    as a warning but never aborts the harness.

    Returns True if the hook ran successfully, False otherwise (including
    when no hook exists).
    """
    if not hooks_dir:
        return False
    hook_path = Path(hooks_dir) / event
    if not hook_path.exists():
        return False

    env = os.environ.copy()
    env["HARNESS_EVENT"] = event
    if env_vars:
        for key, value in env_vars.items():
            env[key] = str(value)

    try:
        result = subprocess.run(
            [str(hook_path)],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
        if result.returncode != 0:
            print(f"{prefix} Hook '{event}' exited with code {result.returncode}")
            if result.stderr:
                print(f"{prefix}   {result.stderr.strip()[:200]}")
            return False
        return True
    except FileNotFoundError:
        print(f"{prefix} Hook '{event}' not found or not executable")
        return False
    except subprocess.TimeoutExpired:
        print(f"{prefix} Hook '{event}' timed out after 30s")
        return False
    except OSError as exc:
        print(f"{prefix} Hook '{event}' error: {exc}")
        return False
