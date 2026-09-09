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
if ! local_tools=$(dotnet tool list --local 2>&1); then
  echo "[format-csharp] cannot inspect local dotnet tools — skipped." >&2
  exit 0
fi
# The local manifest supplies both the pinned version and command: 0.x uses
# dotnet-csharpier, while 1.x uses csharpier. Match the package row, not the
# localized table headings or a dotnet first-run banner's version numbers.
tool_re='^[[:space:]]*csharpier[[:space:]]+([0-9]+)\.[^[:space:]]+[[:space:]]+(dotnet-csharpier|csharpier)[[:space:]]'
major=""
tool_command=""
while IFS= read -r line || [[ -n "$line" ]]; do
  [[ "$line" =~ $tool_re ]] || continue
  major="${BASH_REMATCH[1]}"
  tool_command="${BASH_REMATCH[2]}"
  break
done <<< "$local_tools"
if [[ -z "$tool_command" ]]; then
  echo "[format-csharp] local csharpier unavailable — check this package's tool manifest and run dotnet tool restore." >&2
  exit 0
fi
args=()
[[ "$major" == 0 ]] || args=(format)

if ! output=$(dotnet tool run "$tool_command" -- ${args[@]+"${args[@]}"} "$file_path" 2>&1); then
  echo "[format-csharp] csharpier failed: $(echo "$output" | head -1)" >&2
fi
exit 0
