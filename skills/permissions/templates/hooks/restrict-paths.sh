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
# MULTI-REPO WORKSPACE SUPPORT:
#   When the project root is not itself a git repo (e.g., a directory
#   containing multiple independent git repos), the hook resolves the git
#   context per-file and per-command. This ensures precious file protection
#   and branch protection work correctly in each sub-repo.
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

# --- Git repo resolution (per-path, with caching) ---
# In multi-repo workspaces the project root may not be a git repo.
# We resolve the git toplevel from each file's directory instead.
declare -A _git_root_cache 2>/dev/null || true  # associative array; ignore if bash < 4

find_git_root() {
  # Returns the git toplevel for a given path, or empty string if not in a repo.
  # Results are cached to avoid repeated git calls.
  local target_dir="$1"
  [[ -d "$target_dir" ]] || target_dir="$(dirname "$target_dir")"
  [[ -d "$target_dir" ]] || { echo ""; return; }

  # Check cache (bash 4+ associative arrays)
  if declare -p _git_root_cache &>/dev/null 2>&1; then
    if [[ -n "${_git_root_cache[$target_dir]+_}" ]]; then
      echo "${_git_root_cache[$target_dir]}"
      return
    fi
  fi

  local result
  result="$(git -C "$target_dir" rev-parse --show-toplevel 2>/dev/null)" || result=""
  # Normalize on Windows
  if [[ -n "$result" ]] && command -v cygpath &>/dev/null; then
    result="$(cygpath -u "$result" 2>/dev/null || echo "$result")"
  fi

  # Cache result
  if declare -p _git_root_cache &>/dev/null 2>&1; then
    _git_root_cache[$target_dir]="$result"
  fi
  echo "$result"
}

is_git_tracked() {
  # Check if a file is tracked by git in its containing repo.
  # Fail-open: if not in a git repo or git unavailable, assume tracked (allow).
  local filepath="$1"
  local repo_root
  repo_root="$(find_git_root "$filepath")"
  [[ -n "$repo_root" ]] || return 0  # fail-open: no repo → assume tracked
  git -C "$repo_root" ls-files --error-unmatch "$filepath" &>/dev/null
}

is_precious() {
  local lname
  lname="$(basename "$1")"
  # Case-insensitive matching for Windows (NTFS) and macOS (APFS)
  [[ "${OSTYPE:-}" == msys* || "${OSTYPE:-}" == cygwin* || "${OSTYPE:-}" == darwin* ]] && lname="${lname,,}"
  case "$lname" in
    # Secrets / credentials
    .env*) return 0 ;;
    local.settings.json|credentials.*|secrets.*) return 0 ;;
    docker-compose.override.yml) return 0 ;;
    appsettings.*.json)
      # appsettings.json (no dot-suffix) is usually tracked; variants are not
      [[ "$lname" != "appsettings.json" ]] && return 0 ;;
    # Service account / API keys
    *keyfile*.json) return 0 ;;
    # Monitoring agent configs (may contain license keys)
    newrelic.config) return 0 ;;
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
  git -C "${1:-$root}" rev-parse --abbrev-ref HEAD 2>/dev/null
}

# Resolve which git repo a git command targets.
# Uses -C <path> if present, otherwise tries the project root.
# Returns the repo directory suitable for get_current_branch, or empty if none.
resolve_git_context() {
  local dir="$1"  # from -C flag, or empty
  if [[ -n "$dir" ]]; then
    # Normalize Windows paths (d:/foo, D:\foo) to POSIX form (/d/foo)
    command -v cygpath &>/dev/null && dir="$(cygpath -u "$dir" 2>/dev/null || echo "$dir")"
    # -C was specified — resolve to an absolute path relative to project root
    if [[ "$dir" != /* ]]; then
      dir="$root/$dir"
    fi
    local repo_root
    repo_root="$(find_git_root "$dir")"
    if [[ -n "$repo_root" ]]; then
      echo "$repo_root"
      return
    fi
  fi
  # No -C or -C didn't resolve — try project root
  local root_repo
  root_repo="$(find_git_root "$root")"
  [[ -n "$root_repo" ]] && echo "$root_repo" && return
  # Multi-repo workspace: no git at root and no -C — can't determine context
  echo ""
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
      -d|--delete) has_delete=true ;;
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
    current="$(get_current_branch "${git_repo_dir:-}")" || return 0
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

# Check a single command string for git branch protection violations.
# Handles "git ...", "env ... git ...", and "command ... git ..." forms.
# Called with the sub-command string and an optional cd directory from a chained command.
# Calls deny_operation (exits the script) if blocked; returns 0 if allowed.
check_git_command() {
  local subcmd="$1"
  local cd_dir="${2:-}"

  # Detect git commands, including common wrappers (env VAR=val git ..., command git ...)
  [[ "$subcmd" == git\ * || "$subcmd" == env\ *git\ * || "$subcmd" == command\ *git\ * ]] || return 0

  # Normalize: extract the "git ..." portion for consistent token parsing
  local git_portion="git ${subcmd#*git }"

  local -a tokens
  read -ra tokens <<< "$git_portion"

  # Find git subcommand (skip global flags between 'git' and subcommand)
  local git_subcmd="" git_subcmd_idx=0 git_dir=""
  local i
  for ((i=1; i<${#tokens[@]}; i++)); do
    case "${tokens[i]}" in
      -C) git_dir="${tokens[i+1]:-}"; ((i++)) ;;            # capture -C target dir
      -c|--git-dir|--work-tree|--namespace) ((i++)) ;;      # skip flag + its argument
      --git-dir=*|--work-tree=*|--namespace=*) ;;            # skip =form (no extra arg)
      -*) ;;                                                  # skip other flags
      *) git_subcmd="${tokens[i]}"; git_subcmd_idx=$i; break ;;
    esac
  done

  # Resolve which git repo this command targets
  # Priority: explicit -C flag > cd directory from chain > project root
  local git_repo_dir
  if [[ -n "$git_dir" ]]; then
    git_repo_dir="$(resolve_git_context "$git_dir")"
  elif [[ -n "$cd_dir" ]]; then
    git_repo_dir="$(resolve_git_context "$cd_dir")"
  else
    git_repo_dir="$(resolve_git_context "")"
  fi
  # Fail-open: if we can't determine a git repo, allow (no branches to protect)
  [[ -n "$git_repo_dir" ]] || return 0

  local current_branch
  case "$git_subcmd" in
    push)
      # Delegate to check_git_push with tokens after "git push"
      check_git_push "${tokens[@]:$((git_subcmd_idx+1))}"
      ;;
    commit|merge)
      current_branch="$(get_current_branch "$git_repo_dir")" || return 0
      [[ "$current_branch" == "HEAD" ]] && return 0
      if is_protected_branch "$current_branch"; then
        deny_operation "BLOCKED: Cannot '$git_subcmd' on protected branch '$current_branch'. Switch to a feature branch first."
      fi
      ;;
    reset)
      # Only block 'reset --hard' on protected branches
      [[ "$git_portion" == *--hard* ]] || return 0
      current_branch="$(get_current_branch "$git_repo_dir")" || return 0
      [[ "$current_branch" == "HEAD" ]] && return 0
      if is_protected_branch "$current_branch"; then
        deny_operation "BLOCKED: 'git reset --hard' on protected branch '$current_branch' is not allowed."
      fi
      ;;
    rebase)
      current_branch="$(get_current_branch "$git_repo_dir")" || return 0
      [[ "$current_branch" == "HEAD" ]] && return 0
      if is_protected_branch "$current_branch"; then
        deny_operation "BLOCKED: 'git rebase' on protected branch '$current_branch' is not allowed."
      fi
      ;;
    checkout)
      # Scan tokens after the subcommand for -b/-B flags (handles both "-b name" and "-bname")
      local co_flag="" co_target="" ci
      for ((ci=git_subcmd_idx+1; ci<${#tokens[@]}; ci++)); do
        case "${tokens[ci]}" in
          -b) co_flag="-b"; co_target="${tokens[ci+1]:-}"; break ;;
          -b*) co_flag="-b"; co_target="${tokens[ci]#-b}"; break ;;
          -B) co_flag="-B"; co_target="${tokens[ci+1]:-}"; break ;;
          -B*) co_flag="-B"; co_target="${tokens[ci]#-B}"; break ;;
        esac
      done
      # Allow 'git checkout -b' (create new branch, fails if exists — always safe)
      [[ "$co_flag" == "-b" ]] && return 0
      # 'git checkout -B <name>' force-resets a branch — block if target is protected
      if [[ "$co_flag" == "-B" ]]; then
        if [[ -n "$co_target" ]] && is_protected_branch "$co_target"; then
          deny_operation "BLOCKED: 'git checkout -B $co_target' would reset protected branch '$co_target'."
        fi
        return 0
      fi
      # Block 'git checkout -- <paths>' and 'git checkout .' on protected branches
      local has_discard=false
      for ((ci=git_subcmd_idx+1; ci<${#tokens[@]}; ci++)); do
        case "${tokens[ci]}" in
          --|.) has_discard=true; break ;;
        esac
      done
      [[ "$has_discard" == true ]] || return 0
      current_branch="$(get_current_branch "$git_repo_dir")" || return 0
      [[ "$current_branch" == "HEAD" ]] && return 0
      if is_protected_branch "$current_branch"; then
        deny_operation "BLOCKED: Discarding changes on protected branch '$current_branch' is not allowed."
      fi
      ;;
    restore)
      current_branch="$(get_current_branch "$git_repo_dir")" || return 0
      [[ "$current_branch" == "HEAD" ]] && return 0
      if is_protected_branch "$current_branch"; then
        deny_operation "BLOCKED: 'git restore' on protected branch '$current_branch' is not allowed."
      fi
      ;;
    switch)
      # Scan tokens after the subcommand for -c/-C flags (handles both "-c name" and "-cname")
      local sw_flag="" sw_target="" si
      for ((si=git_subcmd_idx+1; si<${#tokens[@]}; si++)); do
        case "${tokens[si]}" in
          -c) sw_flag="-c"; sw_target="${tokens[si+1]:-}"; break ;;
          -c*) sw_flag="-c"; sw_target="${tokens[si]#-c}"; break ;;
          -C) sw_flag="-C"; sw_target="${tokens[si+1]:-}"; break ;;
          -C*) sw_flag="-C"; sw_target="${tokens[si]#-C}"; break ;;
        esac
      done
      # Allow 'git switch -c' (create new branch, fails if exists — always safe)
      [[ "$sw_flag" == "-c" ]] && return 0
      # 'git switch -C <name>' force-resets a branch — block if target is protected
      if [[ "$sw_flag" == "-C" ]]; then
        if [[ -n "$sw_target" ]] && is_protected_branch "$sw_target"; then
          deny_operation "BLOCKED: 'git switch -C $sw_target' would reset protected branch '$sw_target'."
        fi
      fi
      return 0
      ;;
    branch)
      # Block deletion of protected branches: -d, -D, --delete, or --force-delete flag
      [[ "$git_portion" =~ \ -[dD]\ |\ -[dD]$|\ --delete\ |\ --delete$|\ --force-delete\ |\ --force-delete$ ]] || return 0
      # Check ALL non-flag arguments (git branch -d accepts multiple branch names)
      local bi
      for ((bi=git_subcmd_idx+1; bi<${#tokens[@]}; bi++)); do
        [[ "${tokens[bi]}" == -* ]] && continue
        if is_protected_branch "${tokens[bi]}"; then
          deny_operation "BLOCKED: Cannot delete protected branch '${tokens[bi]}'."
        fi
      done
      ;;
  esac
  return 0
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

    # --- Git branch protection + Delete protection ---
    # Split command on shell operators (&&, ||, ;) and check each sub-command.
    # This handles chained commands like "cd /repo && git commit" and "cd /tmp && rm file".
    # Tracks 'cd <dir>' targets to resolve git context in multi-repo workspaces
    # where Claude Code uses "cd <repo> && git ..." patterns.
    _cd_dir=""
    while IFS= read -r _subcmd; do
      _subcmd="${_subcmd#"${_subcmd%%[![:space:]]*}"}"  # trim leading whitespace
      _subcmd="${_subcmd#\(}"                              # strip leading subshell paren
      _subcmd="${_subcmd%\)}"                              # strip trailing subshell paren

      # Track 'cd <dir>' to resolve context for subsequent commands
      if [[ "$_subcmd" == cd\ * || "$_subcmd" == cd ]]; then
        read -ra _cd_tokens <<< "$_subcmd"
        for _cd_tok in "${_cd_tokens[@]:1}"; do
          [[ "$_cd_tok" == -* ]] && continue
          _cd_dir="$_cd_tok"
          break
        done
        continue
      fi

      # Git branch protection (feature branches allowed, protected branches blocked)
      check_git_command "$_subcmd" "$_cd_dir"

      # Delete protection (rm/rmdir outside project or precious unversioned)
      if [[ "$_subcmd" =~ ^(rm|rmdir)[[:space:]] ]]; then
        read -ra words <<< "$_subcmd"
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
      fi
    done <<< "$(printf '%s' "$cmd" | sed 's/&&/\n/g; s/||/\n/g; s/;/\n/g; s/|/\n/g')"
    exit 0
    ;;
  *)
    exit 0
    ;;
esac
