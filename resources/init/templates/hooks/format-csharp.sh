#!/usr/bin/env bash
# PostToolUse hook: run csharpier on .cs files after Edit/Write.

input=$(cat)
[[ "$input" =~ \"file_path\"[[:space:]]*:[[:space:]]*\"([^\"]+)\" ]] || exit 0
file_path="${BASH_REMATCH[1]}"

[[ "$file_path" == *.cs ]] || exit 0

# Resolve absolute path, run from file's directory for local dotnet tool discovery
abs_dir="$(cd "$(dirname "$file_path")" 2>/dev/null && pwd)"
[[ -n "$abs_dir" ]] || exit 0

if ! output=$(dotnet csharpier "$abs_dir/$(basename "$file_path")" 2>&1); then
  echo "[format-csharp] csharpier failed: $(echo "$output" | head -1)" >&2
fi
