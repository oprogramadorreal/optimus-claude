"""PostToolUse hook: run black + isort on .py files after Edit/Write."""

import json
import subprocess
import sys

data = json.load(sys.stdin)
file_path = data.get("tool_input", {}).get("file_path", "")

if not file_path or not file_path.endswith(".py"):
    sys.exit(0)

for cmd in [["black", "--quiet", file_path], ["isort", "--quiet", "--profile", "black", file_path]]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            msg = (result.stderr or "").split("\n")[0]
            print(f"[format-python] {cmd[0]} failed: {msg}", file=sys.stderr)
    except FileNotFoundError:
        pass
    except Exception as exc:
        print(f"[format-python] {cmd[0]} error: {exc}", file=sys.stderr)
