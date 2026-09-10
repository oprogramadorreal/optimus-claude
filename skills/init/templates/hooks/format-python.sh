#!/usr/bin/env bash
# PostToolUse hook: run black + isort on .py files after Edit/MultiEdit/Write.

input=$(cat)

# Cheap prefilter before the regex: a payload that never mentions ".py" cannot
# name a Python file, and without this a multi-megabyte Write payload is scanned
# in full only to be thrown away by the extension guard below.
[[ "$input" == *.py* ]] || exit 0

# The value is a JSON string, so the match must walk over escaped quotes
# ([^"\]|\\.) — stopping at the first \" truncates the path, which then fails the
# *.py guard and skips formatting in silence. Same pattern as restrict-paths.sh.
_fp_re='"file_path"[[:space:]]*:[[:space:]]*"(([^"\]|\\.)*)"'
[[ "$input" =~ $_fp_re ]] || exit 0
file_path="${BASH_REMATCH[1]}"

# Undo the JSON escapes. \001 shields literal backslashes from the later passes
# (a Windows path arrives as C:\\Users\\...); file_path is never re-emitted as
# JSON, so the sentinel cannot leak into output.
file_path="${file_path//\\\\/$'\001'}"
file_path="${file_path//\\\"/\"}"
file_path="${file_path//\\\//\/}"
file_path="${file_path//\\n/$'\n'}"
file_path="${file_path//\\r/$'\r'}"
file_path="${file_path//\\t/$'\t'}"
# \uXXXX is deliberately NOT decoded: Claude Code serializes hook payloads with
# JSON.stringify, which emits non-ASCII path characters as raw UTF-8 and reserves
# \u escapes for control characters and lone surrogates — neither occurs in a
# file path. (Python's json.dumps escapes all non-ASCII by default; tests must
# use ensure_ascii=False to match what the hook actually receives.)
file_path="${file_path//$'\001'/\\}"

[[ "$file_path" == *.py ]] || exit 0

# --- Resolve black and isort -------------------------------------------------
# init installs them as dev dependencies, so on most machines they exist only in
# the project's virtualenv: Claude Code runs hooks with no venv activated, so
# PATH alone finds nothing. The search walks up from the edited file, which also
# makes per-package venvs in a monorepo resolve to the right one — the same
# approach format-node.cjs takes for node_modules.

# Separators are normalized for the walk only; the formatters get the path as it
# arrived. A relative file_path is CWD-relative by definition, so anchoring the
# walk at $PWD in that case resolves the same venv the path itself refers to.
_walk="${file_path//\\//}"
[[ "$_walk" == /* || "$_walk" == ?:/* ]] || _walk="${PWD//\\//}/$_walk"
_dir="${_walk%/*}"

# Stop at the project root when the file is inside it — a venv above the project
# is not this project's. Deliberately no `:-.` fallback: resolving relative to an
# unknown working directory would run a stray ./.venv binary from wherever the
# session happened to start.
_stop="${CLAUDE_PROJECT_DIR//\\//}"
_stop="${_stop%/}"

# Windows first on Windows: in a repo shared with WSL or a container, .venv/bin
# holds a POSIX shim whose Linux shebang cannot run here, yet [[ -x ]] accepts it
# (and accepts a directory), so probing bin first shadows a working black.exe.
case "$OSTYPE" in
  msys* | cygwin* | win32*) _subdirs=(Scripts bin) ;;
  *) _subdirs=(bin Scripts) ;;
esac

black_bin=""
isort_bin=""

# Sets black_bin/isort_bin from a virtualenv under $1, or returns 1.
probe_venv() {
  local venv sub ext
  for venv in "$1/.venv" "$1/venv" "$1/env"; do
    for sub in "${_subdirs[@]}"; do
      for ext in "" ".exe"; do
        # -f as well as -x: a directory passes -x on its own and is then invoked.
        [[ -f "$venv/$sub/black$ext" && -x "$venv/$sub/black$ext" ]] || continue
        black_bin="$venv/$sub/black$ext"
        # Both tools come from the SAME environment. A project-pinned black
        # paired with whatever isort is on PATH applies another version's
        # grouping rules, and only CI ever reports the resulting import order.
        [[ -f "$venv/$sub/isort$ext" && -x "$venv/$sub/isort$ext" ]] &&
          isort_bin="$venv/$sub/isort$ext"
        return 0
      done
    done
  done
  return 1
}

while [[ -n "$_dir" ]]; do
  probe_venv "$_dir" && break
  [[ "$_dir" == "$_stop" || "$_dir" != */* ]] && break
  _dir="${_dir%/*}"
done

# The edited file can sit outside the project tree — a scratch file, a sibling
# repo, a temp path under test. The project root's venv is still its environment.
[[ -n "$black_bin" || -z "$_stop" ]] || probe_venv "$_stop"

# No virtualenv anywhere — fall back to PATH, still resolved as a pair.
if [[ -z "$black_bin" ]]; then
  black_bin=$(command -v black) || black_bin=""
  isort_bin=$(command -v isort) || isort_bin=""
fi

_missing=""
[[ -n "$black_bin" ]] || _missing="black"
[[ -n "$isort_bin" ]] || _missing="${_missing:+$_missing and }isort"
if [[ -n "$_missing" ]]; then
  # Never fail silently: init reported that Python formatting was installed, so
  # without this the first sign it never ran is a lint failure in CI.
  echo "[format-python] $_missing not found in a .venv/venv/env above the file or on PATH — install as dev dependencies, or this hook does nothing." >&2
fi

# ${output%%$'\n'*} takes the first line without spawning echo|head per edit.
if [[ -n "$black_bin" ]] && ! output=$("$black_bin" --quiet -- "$file_path" 2>&1); then
  echo "[format-python] black failed: ${output%%$'\n'*}" >&2
fi

if [[ -n "$isort_bin" ]] && ! output=$("$isort_bin" --quiet --profile black -- "$file_path" 2>&1); then
  echo "[format-python] isort failed: ${output%%$'\n'*}" >&2
fi

exit 0
