#!/usr/bin/env bash
# PreToolUse hook: tiered security for file operations.
#
# Structured tools (Edit/Write/MultiEdit/NotebookEdit):
#   Inside project  → allow (exit 0, no prompt)
#   Outside project → ask user permission (permissionDecision: "ask")
#
# Bash (rm/rmdir only):
#   Inside project  → allow (exit 0)
#   Outside project → HARD BLOCK (permissionDecision: "deny")
#
# All other tool calls pass through unchanged (exit 0).

input=$(cat)

root="${CLAUDE_PROJECT_DIR}"
[[ -z "$root" ]] && exit 0

# --- Path normalization (cross-platform) ---
normalize() {
  local p="$1"
  # Convert Windows paths on MSYS/Cygwin
  command -v cygpath &>/dev/null && p="$(cygpath -u "$p" 2>/dev/null || echo "$p")"
  # Resolve ../ traversal without requiring path to exist
  if command -v realpath &>/dev/null; then
    p="$(realpath -m "$p" 2>/dev/null || echo "$p")"
  elif [[ -d "$(dirname "$p")" ]]; then
    p="$(cd "$(dirname "$p")" 2>/dev/null && pwd)/$(basename "$p")"
  fi
  # Case-insensitive on Windows (NTFS)
  [[ "${OSTYPE:-}" == msys* || "${OSTYPE:-}" == cygwin* ]] && p="${p,,}"
  echo "$p"
}

norm_root="$(normalize "$root")"
# Ensure trailing slash for prefix matching (avoids /project-other matching /project)
[[ "$norm_root" != */ ]] && norm_root="${norm_root}/"

is_inside_project() {
  local norm_path
  norm_path="$(normalize "$1")"
  [[ "$norm_path" == "${norm_root}"* || "$norm_path" == "${norm_root%/}" ]]
}

# --- JSON response helpers ---
ask_permission() {
  cat <<JSONEOF
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"$1"}}
JSONEOF
  exit 0
}

deny_operation() {
  cat <<JSONEOF
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"$1"}}
JSONEOF
  exit 0
}

# --- Extract tool_name ---
[[ "$input" =~ \"tool_name\"[[:space:]]*:[[:space:]]*\"([^\"]+)\" ]] || exit 0
tool_name="${BASH_REMATCH[1]}"

case "$tool_name" in
  Edit|MultiEdit|Write)
    [[ "$input" =~ \"file_path\"[[:space:]]*:[[:space:]]*\"([^\"]+)\" ]] || exit 0
    is_inside_project "${BASH_REMATCH[1]}" && exit 0
    ask_permission "File '${BASH_REMATCH[1]}' is outside project root. Allow this write?"
    ;;
  NotebookEdit)
    [[ "$input" =~ \"notebook_path\"[[:space:]]*:[[:space:]]*\"([^\"]+)\" ]] || exit 0
    is_inside_project "${BASH_REMATCH[1]}" && exit 0
    ask_permission "Notebook '${BASH_REMATCH[1]}' is outside project root. Allow this edit?"
    ;;
  Bash)
    [[ "$input" =~ \"command\"[[:space:]]*:[[:space:]]*\"([^\"]+)\" ]] || exit 0
    cmd="${BASH_REMATCH[1]}"
    # Only intercept rm/rmdir commands (best-effort delete protection)
    [[ "$cmd" =~ ^(rm|rmdir)[[:space:]] ]] || exit 0
    # Use read -ra to properly split into an array (handles the command as shell words)
    read -ra words <<< "$cmd"
    for word in "${words[@]}"; do
      [[ "$word" == rm || "$word" == rmdir || "$word" == -* ]] && continue
      if ! is_inside_project "$word"; then
        deny_operation "BLOCKED: Cannot delete '$word' — outside project root."
      fi
    done
    exit 0
    ;;
  *)
    exit 0
    ;;
esac
