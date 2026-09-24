#!/usr/bin/env bash
# PostToolUse hook: run dart format on .dart files after Edit/MultiEdit/Write.
# Uses `dart format` (ships with both Dart and Flutter SDKs).

input=$(cat)
_fp_re='"file_path"[[:space:]]*:[[:space:]]*"(([^"\]|\\.)*)"'
[[ "$input" =~ $_fp_re ]] || exit 0
file_path="${BASH_REMATCH[1]}"
file_path="${file_path//\\\\/$'\001'}"
file_path="${file_path//\\\"/\"}"
file_path="${file_path//\\\//\/}"
file_path="${file_path//$'\001'/\\}"

[[ "$file_path" == *.dart ]] || exit 0

if ! output=$(dart format "$file_path" 2>&1); then
  echo "[format-dart] dart format failed: $(echo "$output" | head -1)" >&2
fi
