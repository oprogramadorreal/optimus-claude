#!/usr/bin/env bash
# PostToolUse hook: run google-java-format on .java files after Edit/Write.

input=$(cat)
[[ "$input" =~ \"file_path\"[[:space:]]*:[[:space:]]*\"([^\"]+)\" ]] || exit 0
file_path="${BASH_REMATCH[1]}"

[[ "$file_path" == *.java ]] || exit 0

if command -v google-java-format &>/dev/null; then
  if ! output=$(google-java-format --replace "$file_path" 2>&1); then
    echo "[format-java] google-java-format failed: $(echo "$output" | head -1)" >&2
  fi
fi
