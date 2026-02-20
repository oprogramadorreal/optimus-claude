#!/usr/bin/env bash
# PostToolUse hook: run rustfmt on .rs files after Edit/Write.

input=$(cat)
[[ "$input" =~ \"file_path\"[[:space:]]*:[[:space:]]*\"([^\"]+)\" ]] || exit 0
file_path="${BASH_REMATCH[1]}"

[[ "$file_path" == *.rs ]] || exit 0

rustfmt "$file_path" >/dev/null 2>&1 || true
