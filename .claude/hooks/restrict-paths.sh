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
#   - Edit/Write of precious unversioned files  → prompts you for approval
#   - rm/rmdir of precious unversioned files    → hard blocked
#   - Git operations on feature branches        → silently allowed
#   - Git operations on protected branches       → hard blocked
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
# PRECIOUS FILE PROTECTION (always-on):
#   Well-known sensitive files (.env, *.key, *.pem, *.sqlite, etc.) that are
#   not tracked by git receive extra protection: edits prompt for approval,
#   deletions are blocked. No configuration needed — patterns are hardcoded
#   in the is_precious() function. See the skill's README for the full list.
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

# --- Precious file protection (always-on) ---
is_git_repo=false
git -C "$root" rev-parse --is-inside-work-tree &>/dev/null && is_git_repo=true

is_git_tracked() {
  # Fail-open: if not a git repo or git unavailable, assume tracked (allow)
  [[ "$is_git_repo" == "true" ]] || return 0
  git -C "$root" ls-files --error-unmatch "$1" &>/dev/null
}

is_precious() {
  local lname
  lname="$(basename "$1")"
  # Case-insensitive matching for Windows (NTFS) and macOS (APFS)
  [[ "${OSTYPE:-}" == msys* || "${OSTYPE:-}" == cygwin* || "${OSTYPE:-}" == darwin* ]] && lname="${lname,,}"
  case "$lname" in
    # Secrets / credentials
    .env|.env.*) return 0 ;;
    local.settings.json|credentials.*|secrets.*) return 0 ;;
    docker-compose.override.yml) return 0 ;;
    appsettings.*.json)
      # appsettings.json (no dot-suffix) is usually tracked; variants are not
      [[ "$lname" != "appsettings.json" ]] && return 0 ;;
    # Certificates / keys
    *.key|*.pem|*.pfx|*.p12|*.cert|*.crt|*.jks) return 0 ;;
    # Database files
    *.sqlite|*.sqlite3|*.db|*.db-shm|*.db-wal|*.db-journal|*.mdf|*.ldf|*.ndf) return 0 ;;
    # Database backups
    *.bak|*.dump|*.sql.gz) return 0 ;;
    # IDE user settings
    *.suo|*.user) return 0 ;;
  esac
  return 1
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
  local reason="${1//\\/\\\\}"
  reason="${reason//\"/\\\"}"
  cat <<JSONEOF
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"$reason"}}
JSONEOF
  exit 0
}

deny_operation() {
  local reason="${1//\\/\\\\}"
  reason="${reason//\"/\\\"}"
  cat <<JSONEOF
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"$reason"}}
JSONEOF
  exit 0
}

# --- Git branch protection ---
# Customize this list to match your project's protected branches.
# These branches are shielded from commits, pushes, rebases, resets,
# and deletions. All other branches are treated as feature branches
# where git operations are allowed without prompts.
PROTECTED_BRANCHES=("master" "main" "develop" "dev" "development" "staging" "stage" "prod" "production" "release")

is_protected_branch() {
  local branch="$1"
  for pb in "${PROTECTED_BRANCHES[@]}"; do
    [[ "$branch" == "$pb" ]] && return 0
  done
  return 1
}

get_current_branch() {
  git -C "$root" rev-parse --abbrev-ref HEAD 2>/dev/null
}

# Parse git push arguments and deny if targeting a protected branch.
# Called with all tokens after "git push" as arguments.
# Calls deny_operation (which exits) if blocked; returns silently if allowed.
check_git_push() {
  local t
  for t in "$@"; do
    case "$t" in
      --all|--mirror) deny_operation "BLOCKED: 'git push $t' can affect protected branches." ;;
    esac
  done

  # Separate flags from positional args
  local -a positional=()
  local has_delete=false
  local i=1
  while (( i <= $# )); do
    local arg="${!i}"
    case "$arg" in
      --delete) has_delete=true ;;
      -f|--force|--force-with-lease*|--force-if-includes) ;;
      -u|--set-upstream|--no-verify|--dry-run|-n|--verbose|-v|--quiet|-q) ;;
      --atomic|--signed*|--no-signed|--thin|--no-thin|--tags|--prune) ;;
      --progress|--no-progress|--porcelain|--no-recurse-submodules) ;;
      --push-option|-o|--repo|--receive-pack|--exec) ((i++)) ;;
      --push-option=*|-o*|--repo=*) ;;
      -*) ;; # unknown flag, skip (fail-open)
      *) positional+=("$arg") ;;
    esac
    ((i++))
  done

  # Determine target branch(es)
  local -a targets=()
  if (( ${#positional[@]} <= 1 )); then
    # git push [remote] — pushes current branch
    local current
    current="$(get_current_branch)" || return 0
    [[ "$current" == "HEAD" ]] && return 0
    targets=("$current")
  else
    # git push <remote> <refspec>...
    local refspec target
    for refspec in "${positional[@]:1}"; do
      if [[ "$has_delete" == true ]]; then
        target="$refspec"
      elif [[ "$refspec" == *:* ]]; then
        target="${refspec#*:}"
      else
        target="${refspec#+}" # strip + force prefix
      fi
      target="${target#refs/heads/}" # strip refs/heads/ prefix
      [[ -n "$target" ]] && targets+=("$target")
    done
  fi

  # Check targets against protected branches
  local tgt
  for tgt in "${targets[@]}"; do
    if is_protected_branch "$tgt"; then
      deny_operation "BLOCKED: Cannot push to protected branch '$tgt'. Push to a feature branch instead."
    fi
  done
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
    # Precious file protection: prompt before modifying sensitive unversioned files
    if [[ -e "$filepath" ]] && is_precious "$filepath" && ! is_git_tracked "$filepath"; then
      ask_permission "File '$(basename "$filepath")' is a precious file not tracked by git. Changes may be permanent. Allow this write?"
    fi
    exit 0
    ;;
  NotebookEdit)
    # Fail-open: if notebook_path cannot be extracted, allow rather than block
    [[ "$input" =~ \"notebook_path\"[[:space:]]*:[[:space:]]*\"([^\"]+)\" ]] || exit 0
    filepath="${BASH_REMATCH[1]}"
    if ! is_inside_project "$filepath"; then
      ask_permission "Notebook '$filepath' is outside project root. Allow this edit?"
    fi
    # Precious file protection: prompt before modifying sensitive unversioned notebooks
    if [[ -e "$filepath" ]] && is_precious "$filepath" && ! is_git_tracked "$filepath"; then
      ask_permission "File '$(basename "$filepath")' is a precious file not tracked by git. Changes may be permanent. Allow this edit?"
    fi
    exit 0
    ;;
  Bash)
    # Fail-open: if command cannot be extracted, allow rather than block
    [[ "$input" =~ \"command\"[[:space:]]*:[[:space:]]*\"([^\"]+)\" ]] || exit 0
    cmd="${BASH_REMATCH[1]}"

    # --- Git branch protection (feature branches allowed, protected branches blocked) ---
    if [[ "$cmd" == git\ * ]]; then
      # Fail-open: if not a git repo, allow (no branches to protect)
      [[ "$is_git_repo" == "true" ]] || exit 0

      read -ra tokens <<< "$cmd"
      # Find git subcommand (skip global flags between 'git' and subcommand)
      git_subcmd=""
      git_subcmd_idx=0
      for ((i=1; i<${#tokens[@]}; i++)); do
        case "${tokens[i]}" in
          -C|-c|--git-dir|--work-tree|--namespace) ((i++)) ;;  # skip flag + its argument
          --git-dir=*|--work-tree=*|--namespace=*|-C=*) ;;      # skip =form (no extra arg)
          -*) ;;                                                 # skip other flags
          *) git_subcmd="${tokens[i]}"; git_subcmd_idx=$i; break ;;
        esac
      done

      case "$git_subcmd" in
        push)
          # Delegate to check_git_push with tokens after "git push"
          check_git_push "${tokens[@]:$((git_subcmd_idx+1))}"
          ;;
        commit|merge)
          current_branch="$(get_current_branch)" || exit 0
          [[ "$current_branch" == "HEAD" ]] && exit 0
          if is_protected_branch "$current_branch"; then
            deny_operation "BLOCKED: Cannot '$git_subcmd' on protected branch '$current_branch'. Switch to a feature branch first."
          fi
          ;;
        reset)
          # Only block 'reset --hard' on protected branches
          [[ "$cmd" == *--hard* ]] || exit 0
          current_branch="$(get_current_branch)" || exit 0
          [[ "$current_branch" == "HEAD" ]] && exit 0
          if is_protected_branch "$current_branch"; then
            deny_operation "BLOCKED: 'git reset --hard' on protected branch '$current_branch' is not allowed."
          fi
          ;;
        rebase)
          current_branch="$(get_current_branch)" || exit 0
          [[ "$current_branch" == "HEAD" ]] && exit 0
          if is_protected_branch "$current_branch"; then
            deny_operation "BLOCKED: 'git rebase' on protected branch '$current_branch' is not allowed."
          fi
          ;;
        checkout)
          # Check only tokens after the subcommand (avoids matching git global flags)
          sub_args="${tokens[*]:$((git_subcmd_idx+1))}"
          # Allow 'git checkout -b' (create new branch, fails if exists — always safe)
          [[ " $sub_args " == *" -b "* ]] && exit 0
          # 'git checkout -B <name>' force-resets a branch — block if target is protected
          if [[ " $sub_args " == *" -B "* ]]; then
            checkout_target="$(echo "$cmd" | sed -n 's/.* -B \+\([^ ]*\).*/\1/p')"
            if [[ -n "$checkout_target" ]] && is_protected_branch "$checkout_target"; then
              deny_operation "BLOCKED: 'git checkout -B $checkout_target' would reset protected branch '$checkout_target'."
            fi
            exit 0
          fi
          # Block 'git checkout -- <paths>' and 'git checkout .' on protected branches
          [[ "$cmd" == *" -- "* || "$cmd" == *" ." ]] || exit 0
          current_branch="$(get_current_branch)" || exit 0
          [[ "$current_branch" == "HEAD" ]] && exit 0
          if is_protected_branch "$current_branch"; then
            deny_operation "BLOCKED: Discarding changes on protected branch '$current_branch' is not allowed."
          fi
          ;;
        restore)
          current_branch="$(get_current_branch)" || exit 0
          [[ "$current_branch" == "HEAD" ]] && exit 0
          if is_protected_branch "$current_branch"; then
            deny_operation "BLOCKED: 'git restore' on protected branch '$current_branch' is not allowed."
          fi
          ;;
        switch)
          # Check only tokens after the subcommand (avoids matching git global -c flag)
          sub_args="${tokens[*]:$((git_subcmd_idx+1))}"
          # Allow 'git switch -c' (create new branch, fails if exists — always safe)
          [[ " $sub_args " == *" -c "* ]] && exit 0
          # 'git switch -C <name>' force-resets a branch — block if target is protected
          if [[ " $sub_args " == *" -C "* ]]; then
            switch_target="$(echo "$cmd" | sed -n 's/.* -C \+\([^ ]*\).*/\1/p')"
            if [[ -n "$switch_target" ]] && is_protected_branch "$switch_target"; then
              deny_operation "BLOCKED: 'git switch -C $switch_target' would reset protected branch '$switch_target'."
            fi
          fi
          exit 0
          ;;
        branch)
          # Block deletion of protected branches: -d, -D, --delete, or --force-delete flag
          [[ "$cmd" =~ \ -[dD]\ |\ -[dD]$|\ --delete\ |\ --delete$|\ --force-delete\ |\ --force-delete$ ]] || exit 0
          # Check ALL non-flag arguments (git branch -d accepts multiple branch names)
          for ((bi=git_subcmd_idx+1; bi<${#tokens[@]}; bi++)); do
            [[ "${tokens[bi]}" == -* ]] && continue
            if is_protected_branch "${tokens[bi]}"; then
              deny_operation "BLOCKED: Cannot delete protected branch '${tokens[bi]}'."
            fi
          done
          ;;
      esac
      exit 0
    fi

    # --- Delete protection (rm/rmdir outside project or precious unversioned) ---
    [[ "$cmd" =~ ^(rm|rmdir)[[:space:]] ]] || exit 0
    # Use read -ra to properly split into an array (handles the command as shell words)
    read -ra words <<< "$cmd"
    for word in "${words[@]}"; do
      [[ "$word" == rm || "$word" == rmdir || "$word" == -* ]] && continue
      if ! is_inside_project "$word"; then
        deny_operation "BLOCKED: Cannot delete '$word' — outside project root."
      fi
      # Precious file protection: block deletion of sensitive unversioned files
      if [[ -e "$word" ]] && is_inside_project "$word" && is_precious "$word" && ! is_git_tracked "$word"; then
        deny_operation "BLOCKED: '$(basename "$word")' is a precious file not tracked by git. Deletion denied."
      fi
    done
    exit 0
    ;;
  *)
    exit 0
    ;;
esac
