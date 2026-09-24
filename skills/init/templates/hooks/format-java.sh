#!/usr/bin/env bash
# PostToolUse hook: run google-java-format on .java files after Edit/MultiEdit/Write.

input=$(cat)
_fp_re='"file_path"[[:space:]]*:[[:space:]]*"(([^"\]|\\.)*)"'
[[ "$input" =~ $_fp_re ]] || exit 0
file_path="${BASH_REMATCH[1]}"
file_path="${file_path//\\\\/$'\001'}"
file_path="${file_path//\\\"/\"}"
file_path="${file_path//\\\//\/}"
file_path="${file_path//$'\001'/\\}"

[[ "$file_path" == *.java ]] || exit 0

if ! output=$(google-java-format --replace "$file_path" 2>&1); then
  echo "[format-java] google-java-format failed: $(echo "$output" | head -1)" >&2
fi
