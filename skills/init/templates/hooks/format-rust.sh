#!/usr/bin/env bash
# PostToolUse hook: run rustfmt on .rs files after Edit/MultiEdit/Write.

input=$(cat)
_fp_re='"file_path"[[:space:]]*:[[:space:]]*"(([^"\]|\\.)*)"'
[[ "$input" =~ $_fp_re ]] || exit 0
file_path="${BASH_REMATCH[1]}"
file_path="${file_path//\\\\/$'\001'}"
file_path="${file_path//\\\"/\"}"
file_path="${file_path//\\\//\/}"
file_path="${file_path//$'\001'/\\}"
case "$OSTYPE" in msys*|cygwin*) file_path="${file_path//\\//}" ;; esac

[[ "$file_path" == *.rs ]] || exit 0

# Direct rustfmt does not infer Cargo's edition. Require a project-owned config
# rather than parsing Cargo/workspace TOML or silently using Rust 2015.
if ! cd "$(dirname "$file_path")" 2>/dev/null; then
  echo "[format-rust] cannot enter the edited file's directory — skipped." >&2
  exit 0
fi
file_path="$PWD/$(basename "$file_path")"
dir="$PWD"
config=""
while :; do
  for candidate in "$dir/.rustfmt.toml" "$dir/rustfmt.toml"; do
    [[ -f "$candidate" ]] && { config="$candidate"; break; }
  done
  [[ -n "$config" || -d "$dir/.git" || -f "$dir/.git" || "$dir" == / ]] && break
  dir="$(dirname "$dir")"
done
edition_re="^[[:space:]]*edition[[:space:]]*=[[:space:]]*['\"](2015|2018|2021|2024)['\"][[:space:]]*(#.*)?$"
explicit_edition=""
if [[ -n "$config" ]]; then
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ $edition_re ]] && explicit_edition=1
  done < "$config"
fi
if [[ -z "$explicit_edition" ]]; then
  echo "[format-rust] no explicit edition in the nearest project rustfmt config — skipped. Use the project's cargo fmt command, or configure edition/style_edition to match its toolchain." >&2
  exit 0
fi

if ! output=$(rustfmt --config-path "$config" "$file_path" 2>&1); then
  echo "[format-rust] rustfmt failed: $(echo "$output" | head -1)" >&2
fi
exit 0
