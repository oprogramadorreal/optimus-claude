#!/usr/bin/env bash
# ============================================================================
# restrict-paths.sh — Claude Code PreToolUse hook
# Installed by: /optimus:permissions (optimus-claude plugin)
# Source:       https://github.com/oprogramadorreal/optimus-claude
# Docs:         skills/permissions/README.md
# ============================================================================
#
# PURPOSE:
#   Prevents Claude Code from writing or deleting files outside your project
#   directory. This is a safety guardrail, not a permissions bypass — it adds
#   restrictions, not removes them.
#
# WHAT THIS SCRIPT DOES:
#   - Edit/Write operations inside the project  → silently allowed
#   - Edit/Write operations outside the project → prompts you for approval
#   - rm/rmdir commands outside the project     → hard blocked
#   - Everything else (reads, searches, etc.)   → passes through unchanged
#
# WHAT THIS SCRIPT DOES NOT DO:
#   - Does NOT send data anywhere (no network calls)
#   - Does NOT log or record file paths or commands
#   - Does NOT modify, read, or copy your files
#   - Does NOT run in the background or persist after Claude Code exits
#
# FAIL-OPEN DESIGN:
#   When the hook cannot determine whether an operation is safe (e.g.,
#   CLAUDE_PROJECT_DIR is unset, JSON parsing fails, or the file_path field
#   is missing), it allows the operation rather than blocking it. This avoids
#   breaking legitimate tool use when input formats change.
#
# PRECIOUS FILE PROTECTION (recommended):
#   Set OPTIMUS_PRECIOUS_PATTERNS to a comma-separated list of glob patterns
#   for files that are gitignored but non-regenerable (e.g., local config,
#   secrets, database files). The hook prompts before modifying or deleting
#   any matching unversioned file. Example:
#     OPTIMUS_PRECIOUS_PATTERNS="appsettings.*.json,.env,.env.*,*.mdf,*.ldf"
#   Works correctly in multi-repo workspaces — detects the git root for each
#   file individually rather than assuming a single git repo at project root.
#
# UNVERSIONED FILE PROTECTION (opt-in, legacy):
#   Set OPTIMUS_PROTECT_UNVERSIONED=1 to prompt before modifying or deleting
#   ANY file inside the project that is NOT tracked by git. This is broader
#   than precious patterns — it also prompts for regenerable files
#   (node_modules, dist, build output). Precious patterns is recommended
#   instead. Both can be used together.
#
# TO DISABLE OR REMOVE:
#   1. Delete this file: rm .claude/hooks/restrict-paths.sh
#   2. Remove the PreToolUse hook entry from .claude/settings.json
#   Or simply ignore it — the hook only runs when Claude Code invokes tools.
# ============================================================================

input=$(cat)

root="${CLAUDE_PROJECT_DIR}"
# Fail-open: if project root is unknown, allow rather than block all tool use
[[ -z "$root" ]] && exit 0

# --- Configuration ---
protect_unversioned="${OPTIMUS_PROTECT_UNVERSIONED:-0}"
precious_patterns="${OPTIMUS_PRECIOUS_PATTERNS:-}"

# --- Per-file git root detection (multi-repo workspace support) ---
# Walks up from the file's directory to find the nearest .git/ directory.
# In multi-repo workspaces, each sub-repo has its own .git/ — this ensures
# git operations target the correct repo instead of failing at the workspace root.
find_git_root() {
  local dir="$1"
  [[ ! -d "$dir" ]] && dir="$(dirname "$dir")"
  local prev=""
  while [[ "$dir" != "$prev" && -n "$dir" ]]; do
    [[ -d "$dir/.git" ]] && { echo "$dir"; return 0; }
    prev="$dir"
    dir="$(dirname "$dir")"
  done
  return 1
}

is_git_tracked() {
  # Fail-open: if no git root found (file outside any repo), assume tracked (allow)
  local filepath="$1"
  local git_root
  git_root="$(find_git_root "$filepath")" || return 0
  git -C "$git_root" ls-files --error-unmatch "$filepath" &>/dev/null
}

# --- Precious file pattern matching ---
# Matches the file's basename against comma-separated glob patterns from
# OPTIMUS_PRECIOUS_PATTERNS. Only triggers for existing, unversioned files.
is_precious() {
  [[ -z "$precious_patterns" ]] && return 1
  local filepath="$1"
  local file_basename
  file_basename="$(basename "$filepath")"
  local IFS=','
  for pattern in $precious_patterns; do
    # Trim leading/trailing whitespace
    pattern="${pattern#"${pattern%%[![:space:]]*}"}"
    pattern="${pattern%"${pattern##*[![:space:]]}"}"
    [[ -z "$pattern" ]] && continue
    # shellcheck disable=SC2254
    if [[ "$file_basename" == $pattern ]]; then
      return 0
    fi
  done
  return 1
}

# Checks if a file is precious or (with legacy flag) any unversioned file.
# Calls ask_permission (which exits the script) if protection triggers.
check_file_protection() {
  local filepath="$1"
  local action="$2"  # "write" or "delete"
  # Only check existing files — new files are always allowed
  [[ -e "$filepath" ]] || return 0

  # Precious patterns: targeted protection for non-regenerable gitignored files
  if is_precious "$filepath" && ! is_git_tracked "$filepath"; then
    if [[ "$action" == "delete" ]]; then
      ask_permission "Precious file '$(basename "$filepath")' is not tracked by git. Deletion is permanent. Allow?"
    else
      ask_permission "Precious file '$(basename "$filepath")' is not tracked by git. Changes cannot be recovered. Allow this $action?"
    fi
  fi

  # Legacy: blanket unversioned file protection (opt-in via OPTIMUS_PROTECT_UNVERSIONED=1)
  if [[ "$protect_unversioned" != "0" ]] && ! is_git_tracked "$filepath"; then
    if [[ "$action" == "delete" ]]; then
      ask_permission "File '$filepath' is not tracked by git. Deletion is permanent. Allow?"
    else
      ask_permission "File '$filepath' is not tracked by git. Changes cannot be recovered. Allow this $action?"
    fi
  fi
}

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
# Fail-open: if tool_name cannot be extracted, allow rather than block
[[ "$input" =~ \"tool_name\"[[:space:]]*:[[:space:]]*\"([^\"]+)\" ]] || exit 0
tool_name="${BASH_REMATCH[1]}"

case "$tool_name" in
  Edit|MultiEdit|Write)
    # Fail-open: if file_path cannot be extracted, allow rather than block
    [[ "$input" =~ \"file_path\"[[:space:]]*:[[:space:]]*\"([^\"]+)\" ]] || exit 0
    filepath="${BASH_REMATCH[1]}"
    if ! is_inside_project "$filepath"; then
      ask_permission "File '$filepath' is outside project root. Allow this write?"
    fi
    check_file_protection "$filepath" "write"
    exit 0
    ;;
  NotebookEdit)
    # Fail-open: if notebook_path cannot be extracted, allow rather than block
    [[ "$input" =~ \"notebook_path\"[[:space:]]*:[[:space:]]*\"([^\"]+)\" ]] || exit 0
    filepath="${BASH_REMATCH[1]}"
    if ! is_inside_project "$filepath"; then
      ask_permission "Notebook '$filepath' is outside project root. Allow this edit?"
    fi
    check_file_protection "$filepath" "write"
    exit 0
    ;;
  Bash)
    # Fail-open: if command cannot be extracted, allow rather than block
    [[ "$input" =~ \"command\"[[:space:]]*:[[:space:]]*\"([^\"]+)\" ]] || exit 0
    cmd="${BASH_REMATCH[1]}"
    # Only intercept rm/rmdir commands (best-effort delete protection)
    [[ "$cmd" =~ ^(rm|rmdir)[[:space:]] ]] || exit 0
    # Use read -ra to properly split into an array (handles the command as shell words)
    read -ra words <<< "$cmd"
    for word in "${words[@]}"; do
      [[ "$word" == rm || "$word" == rmdir || "$word" == -* ]] && continue
      if is_inside_project "$word"; then
        check_file_protection "$word" "delete"
      else
        deny_operation "BLOCKED: Cannot delete '$word' — outside project root."
      fi
    done
    exit 0
    ;;
  *)
    exit 0
    ;;
esac
