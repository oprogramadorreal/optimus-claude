#!/usr/bin/env bash
# PostToolUse hook: run gofmt on .go files after Edit/MultiEdit/Write.
# Uses gofmt (format only). goimports is intentionally excluded — its import
# removal conflicts with in-progress edits (imports removed before code using
# them is written, causing a destructive add/remove loop).

input=$(cat)
[[ "$input" =~ \"file_path\"[[:space:]]*:[[:space:]]*\"([^\"]+)\" ]] || exit 0
file_path="${BASH_REMATCH[1]}"

[[ "$file_path" == *.go ]] || exit 0

if ! output=$(gofmt -w "$file_path" 2>&1); then
  echo "[format-go] gofmt failed: $(echo "$output" | head -1)" >&2
fi
