"""Load this checkout in an isolated Codex home, without invoking a model.

Requires Codex's plugin CLI and app-server skills/list API. Supply a native
codex executable with --codex-exe on Windows (not a .cmd/.ps1 launcher).
This checks local installation and discovery; it does not test skill execution.
"""

import argparse
import hashlib
import json
import os
import queue
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def discover(executable, env, project, timeout=30):
    """Request the host's actual skill inventory over its documented JSON API."""
    messages = queue.Queue()
    process = subprocess.Popen(
        [executable, "app-server"],
        cwd=project,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
    )

    def reader():
        for line in process.stdout:
            try:
                messages.put(json.loads(line))
            except ValueError:
                pass

    worker = threading.Thread(target=reader, daemon=True)
    worker.start()

    def request(payload):
        process.stdin.write(json.dumps(payload) + "\n")
        process.stdin.flush()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            message = messages.get(timeout=max(0.01, deadline - time.monotonic()))
            if message.get("id") == payload["id"]:
                if "error" in message:
                    raise ValueError(message["error"])
                return message["result"]
        raise TimeoutError("Codex app-server did not respond")

    try:
        initialization = request(
            {
                "id": 1,
                "method": "initialize",
                "params": {
                    "clientInfo": {"name": "optimus-loader-smoke", "version": "1"},
                    "capabilities": {"experimentalApi": True},
                },
            }
        )
        process.stdin.write(json.dumps({"method": "initialized", "params": {}}) + "\n")
        process.stdin.flush()
        inventory = request(
            {
                "id": 2,
                "method": "skills/list",
                "params": {
                    "cwds": [str(project)],
                    "forceReload": True,
                },
            }
        )
        return initialization, inventory
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        worker.join(timeout=2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--codex-exe", default=shutil.which("codex.exe") or shutil.which("codex")
    )
    parser.add_argument("--output", type=Path, help="Save the JSON evidence report")
    args = parser.parse_args()
    if not args.codex_exe or Path(args.codex_exe).suffix.lower() in (
        ".cmd",
        ".bat",
        ".ps1",
    ):
        parser.error("Supply --codex-exe with a native Codex executable")
    report = {
        "scope": "local installation and skill discovery only; no model invoked",
        "source": str(ROOT),
        "commands": [],
    }
    try:
        with tempfile.TemporaryDirectory(prefix="optimus-codex-loader-") as temp:
            scratch = Path(temp)
            project = scratch / "project"
            project.mkdir()
            home = scratch / "codex-home"
            home.mkdir()
            env = dict(os.environ, CODEX_HOME=str(home))
            # Loader needs no credentials; do not inherit API keys or a user's
            # CODEX_HOME. The temporary home is destroyed after this check.
            for key in ("OPENAI_API_KEY", "CODEX_API_KEY"):
                env.pop(key, None)

            def run(*argv):
                result = subprocess.run(
                    [args.codex_exe, *argv],
                    cwd=project,
                    env=env,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=30,
                )
                report["commands"].append(
                    {
                        "args": list(argv),
                        "exit_code": result.returncode,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                    }
                )
                if result.returncode:
                    raise ValueError(
                        f"Codex {' '.join(argv[:2])} failed with exit {result.returncode}"
                    )

            run("--version")
            run("plugin", "marketplace", "add", str(ROOT))
            run("plugin", "add", "optimus@optimus-claude")
            run("plugin", "list")
            initialization, inventory = discover(args.codex_exe, env, project)
            report["host"] = initialization
            actual = [
                skill
                for entry in inventory["data"]
                for skill in entry.get("skills", [])
                if skill.get("pluginId") == "optimus@optimus-claude"
            ]
            expected = {
                f"optimus:{path.parent.name}": path
                for path in (ROOT / "skills").glob("*/SKILL.md")
            }
            if set(expected) != {skill["name"] for skill in actual}:
                raise ValueError("Discovered skill names differ from checkout")
            for skill in actual:
                if not skill.get("enabled"):
                    raise ValueError(f"Disabled skill: {skill['name']}")
                cached = Path(skill["path"]).resolve()
                cached.relative_to(home.resolve())
                source = expected[skill["name"]]
                if cached.read_bytes() != source.read_bytes():
                    raise ValueError(f"Cached skill differs: {skill['name']}")
            report["skills"] = [
                {
                    "name": name,
                    "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
                for name, path in sorted(expected.items())
            ]
            report["result"] = "PASS"
    except (
        OSError,
        ValueError,
        AssertionError,
        KeyError,
        queue.Empty,
        subprocess.TimeoutExpired,
    ) as exc:
        report["result"] = "FAIL"
        report["error"] = str(exc) or type(exc).__name__
    rendered = json.dumps(report, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
