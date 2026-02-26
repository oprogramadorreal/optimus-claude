#!/usr/bin/env bash
# PostToolUse hook: run rustfmt on .rs files after Edit/Write.

input=$(cat)
[[ "$input" =~ \"file_path\"[[:space:]]*:[[:space:]]*\"([^\"]+)\" ]] || exit 0
file_path="${BASH_REMATCH[1]}"

[[ "$file_path" == *.rs ]] || exit 0

if ! output=$(rustfmt "$file_path" 2>&1); then
  echo "[format-rust] rustfmt failed: $(echo "$output" | head -1)" >&2
fi
