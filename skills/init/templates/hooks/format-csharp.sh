#!/usr/bin/env bash
# PostToolUse hook: run csharpier on .cs files after Edit/MultiEdit/Write.

input=$(cat)
_fp_re='"file_path"[[:space:]]*:[[:space:]]*"(([^"\]|\\.)*)"'
[[ "$input" =~ $_fp_re ]] || exit 0
file_path="${BASH_REMATCH[1]}"
file_path="${file_path//\\\\/$'\001'}"
file_path="${file_path//\\\"/\"}"
file_path="${file_path//\\\//\/}"
file_path="${file_path//$'\001'/\\}"
case "$OSTYPE" in msys*|cygwin*) file_path="${file_path//\\//}" ;; esac

[[ "$file_path" == *.cs ]] || exit 0

# Local tool discovery and version selection must run in the edited package.
if ! cd "$(dirname "$file_path")" 2>/dev/null; then
  echo "[format-csharp] cannot enter the edited file's directory — skipped." >&2
  exit 0
fi
file_path="$PWD/$(basename "$file_path")"
if ! version=$(dotnet tool run csharpier -- --version 2>&1); then
  echo "[format-csharp] local csharpier unavailable — run dotnet tool restore in this package." >&2
  exit 0
fi
version_re='(^|[[:space:]])([0-9]+)\.[0-9]+'
if [[ ! "$version" =~ $version_re ]]; then
  echo "[format-csharp] cannot determine the pinned csharpier version — skipped." >&2
  exit 0
fi
args=()
[[ "${BASH_REMATCH[2]}" == 0 ]] || args=(format)

if ! output=$(dotnet tool run csharpier -- ${args[@]+"${args[@]}"} "$file_path" 2>&1); then
  echo "[format-csharp] csharpier failed: $(echo "$output" | head -1)" >&2
fi
exit 0
