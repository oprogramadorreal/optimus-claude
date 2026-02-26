#!/usr/bin/env bash
# PostToolUse hook: run clang-format on C/C++ files after Edit/Write.

input=$(cat)
[[ "$input" =~ \"file_path\"[[:space:]]*:[[:space:]]*\"([^\"]+)\" ]] || exit 0
file_path="${BASH_REMATCH[1]}"

case "$file_path" in
  *.c|*.cpp|*.cc|*.cxx|*.h|*.hpp|*.hxx) ;;
  *) exit 0 ;;
esac

if command -v clang-format &>/dev/null; then
  if ! output=$(clang-format -i "$file_path" 2>&1); then
    echo "[format-cpp] clang-format failed: $(echo "$output" | head -1)" >&2
  fi
fi
