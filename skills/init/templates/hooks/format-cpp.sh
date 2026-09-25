#!/usr/bin/env bash
# PostToolUse hook: run clang-format on C/C++ files after Edit/MultiEdit/Write.

input=$(cat)
_fp_re='"file_path"[[:space:]]*:[[:space:]]*"(([^"\]|\\.)*)"'
[[ "$input" =~ $_fp_re ]] || exit 0
file_path="${BASH_REMATCH[1]}"
file_path="${file_path//\\\\/$'\001'}"
file_path="${file_path//\\\"/\"}"
file_path="${file_path//\\\//\/}"
file_path="${file_path//$'\001'/\\}"

case "$file_path" in
  *.c|*.cpp|*.cc|*.cxx|*.h|*.hpp|*.hxx) ;;
  *) exit 0 ;;
esac

if ! output=$(clang-format -i "$file_path" 2>&1); then
  echo "[format-cpp] clang-format failed: $(echo "$output" | head -1)" >&2
fi
