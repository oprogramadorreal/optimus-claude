#!/usr/bin/env bash
# PostToolUse hook: run goimports (or gofmt) on .go files after Edit/Write.

input=$(cat)
[[ "$input" =~ \"file_path\"[[:space:]]*:[[:space:]]*\"([^\"]+)\" ]] || exit 0
file_path="${BASH_REMATCH[1]}"

[[ "$file_path" == *.go ]] || exit 0

# Prefer goimports (formats + organizes imports), fall back to gofmt (format only)
if command -v goimports &>/dev/null; then
  if ! output=$(goimports -w "$file_path" 2>&1); then
    echo "[format-go] goimports failed: $(echo "$output" | head -1)" >&2
  fi
elif ! output=$(gofmt -w "$file_path" 2>&1); then
  echo "[format-go] gofmt failed: $(echo "$output" | head -1)" >&2
fi
