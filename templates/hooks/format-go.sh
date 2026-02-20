#!/usr/bin/env bash
# PostToolUse hook: run gofmt on .go files after Edit/Write.

input=$(cat)
[[ "$input" =~ \"file_path\"[[:space:]]*:[[:space:]]*\"([^\"]+)\" ]] || exit 0
file_path="${BASH_REMATCH[1]}"

[[ "$file_path" == *.go ]] || exit 0

gofmt -w "$file_path" >/dev/null 2>&1 || true
