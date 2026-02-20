"""PostToolUse hook: run black + isort on .py files after Edit/Write."""

import json
import subprocess
import sys

data = json.load(sys.stdin)
file_path = data.get("tool_input", {}).get("file_path", "")

if not file_path or not file_path.endswith(".py"):
    sys.exit(0)

try:
    subprocess.run(["black", "--quiet", file_path])
except FileNotFoundError:
    pass
try:
    subprocess.run(["isort", "--quiet", "--profile", "black", file_path])
except FileNotFoundError:
    pass
