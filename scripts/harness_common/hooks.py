import os
import subprocess
import sys
from pathlib import Path


def run_hook(hooks_dir, event, env_vars=None, prefix="[harness]"):
    """Run a lifecycle hook script if it exists.

    Looks for an executable file named *event* (e.g. ``pre-iteration``) in
    *hooks_dir*.  The hook receives context via environment variables.

    Design: **fail-open** — hook errors are logged as warnings and never
    abort the harness.  Timeout: 30 s.

    Returns True if the hook ran successfully, False on error, None if no
    hook was found.
    """
    if not hooks_dir:
        return None
    hooks_path = Path(hooks_dir)
    if not hooks_path.is_dir():
        return None

    # Look for the hook file (with or without extension on Windows)
    hook_file = hooks_path / event
    if not hook_file.exists():
        # Try common extensions on Windows
        for ext in (".cmd", ".bat", ".ps1", ".sh"):
            candidate = hooks_path / f"{event}{ext}"
            if candidate.exists():
                hook_file = candidate
                break
        else:
            return None

    env = os.environ.copy()
    env["HARNESS_EVENT"] = event
    if env_vars:
        env.update({k: str(v) for k, v in env_vars.items()})

    try:
        if sys.platform == "win32":
            cmd = [str(hook_file)]
        else:
            cmd = [str(hook_file)]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
        if result.returncode != 0:
            print(
                f"{prefix} Hook '{event}' exited with code {result.returncode}: "
                f"{result.stderr[:200]}"
            )
            return False
        return True
    except subprocess.TimeoutExpired:
        print(f"{prefix} Hook '{event}' timed out after 30s")
        return False
    except OSError as exc:
        print(f"{prefix} Hook '{event}' failed: {exc}")
        return False
