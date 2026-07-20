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
#   - Creating a NEW file under the OS temp root → prompts, with a reminder that
#                                                 the session scratchpad is exempt
#   - Edit/Write/delete in Claude's memory store → silently allowed
#   - Edit/Write/delete in Claude's scratchpad   → silently allowed
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
# CLAUDE MEMORY STORE (always-allowed):
#   Claude Code keeps a per-project auto-memory store under
#   <home>/.claude/projects/<project>/memory/. Although that path is outside
#   CLAUDE_PROJECT_DIR, it is Claude's own scratchpad (plain markdown, designed
#   to be written and pruned by Claude), so writes AND deletes there are allowed
#   without a prompt. The exemption is scoped to a single-segment memory/ subtree
#   only — the rest of ~/.claude (settings.json, etc.) is NOT exempt and still
#   prompts on out-of-project write / is blocked on out-of-project delete.
#
# CLAUDE SESSION SCRATCHPAD (always-allowed):
#   The harness gives each session a scratchpad under
#   <temp>/claude/<project>/<session>/scratchpad/ (temp root taken from
#   TMPDIR/TEMP/TMP, or /tmp). Like the memory store it is Claude's own throwaway
#   working area, so writes AND deletes there are allowed without a prompt. The
#   match requires the full <temp>/claude/<project>/<session>/scratchpad shape
#   (both <project> and <session> are single path segments), so it can't stretch
#   to an unrelated 'scratchpad' dir elsewhere under the temp root. If the temp
#   root can't be resolved, the path falls back to the normal out-of-project prompt.
#
#   TEMP-WRITE NUDGE: creating a NEW file under the temp root WITHOUT this shape
#   (an invented temp dir) still prompts you, but with a reason that reminds
#   Claude the session scratchpad is exempt (see nudge_temp_write). It only ever
#   changes the WORDING of a prompt you were already going to see — it never
#   decides for you. This hook deliberately does NOT synthesize the scratchpad
#   path: only the harness knows it (it is already in Claude's system prompt),
#   and a path built here from the project basename would name a look-alike
#   directory the harness neither creates nor cleans up.
#
#   Scope: a file that ALREADY EXISTS keeps the plain out-of-project prompt, and
#   ~/.claude keeps its own (it is Claude's config, not scratch, and it can sit
#   under the temp root in CI images). The nudge is skipped when the path
#   contains a ".." this platform's realpath left unresolved. Note the veto is
#   scoped to ~/.claude, NOT to all of $HOME: vetoing $HOME would silently
#   disable the nudge wherever the temp root lives under the home dir
#   (TMPDIR=$HOME/tmp, MSYS2/Cygwin default mounts), which is the common case.
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
  # Convert Windows paths on MSYS/Cygwin. '--' so a path that looks like a flag
  # ('-n', '-e') is not eaten as one, which would hand the gates an empty string.
  command -v cygpath &>/dev/null && p="$(cygpath -u -- "$p" 2>/dev/null || printf '%s\n' "$p")"
  # Resolve ../ traversal without requiring path to exist
  if command -v realpath &>/dev/null; then
    p="$(realpath -m -- "$p" 2>/dev/null || printf '%s\n' "$p")"
  elif [[ -d "$(dirname "$p")" ]]; then
    p="$(cd "$(dirname "$p")" 2>/dev/null && pwd)/$(basename "$p")"
  fi
  # Collapse repeated slashes and drop a trailing one (pure bash, no fork) so
  # every spelling of a path compares equal whichever branch above ran. This is
  # load-bearing, not cosmetic: macOS TMPDIR ends in '/', a non-GNU realpath
  # that rejects '-m' returns the string untouched, and the cd/pwd fallback
  # splices '//tmp' when the parent is '/' — each would otherwise leave a temp
  # base that stops matching paths written the ordinary way, silently killing
  # the scratchpad exemption.
  # EXACTLY TWO leading slashes are preserved: that is a UNC network root on
  # MSYS/Cygwin (//server/share) and is implementation-defined under POSIX, so
  # collapsing it would make a remote path compare equal to an unrelated local
  # one and let it pass a project/exemption prefix test. Three or more leading
  # slashes are plain '/' per POSIX and do collapse.
  local lead=""
  [[ "$p" == //[!/]* ]] && { lead="/"; p="${p#/}"; }
  while [[ "$p" == *//* ]]; do p="${p//\/\//\/}"; done
  [[ "$p" == "/" ]] || p="${p%/}"
  p="$lead$p"
  # Case-insensitive on Windows (NTFS)
  [[ "${OSTYPE:-}" == msys* || "${OSTYPE:-}" == cygwin* ]] && p="${p,,}"
  # printf, not echo: a path of exactly '-n'/'-e'/'-E' is an echo FLAG and would
  # come back as the empty string, silently dropping the path from every gate.
  printf '%s\n' "$p"
}

# --- Shared path predicates (used by every exemption gate below) ---
# Fail closed on an unresolved ".." (e.g. a non-GNU realpath that ignored '-m'):
# a traversal like memory/../../settings.json must never reach an auto-allow.
# Defined once so the gates cannot drift apart — a weaker copy in any one of
# them would silently reopen the escape the others reject.
has_unresolved_traversal() {
  case "$1" in */../*|*/..|../*|..) return 0 ;; esac
  return 1
}

# POSIX absolute or Windows drive-qualified. Used to reject a RELATIVE temp root:
# normalize() would resolve it against this hook's current directory, turning an
# arbitrary sibling of the project into an auto-allowed subtree and silently
# defeating the rm hard-block. Deliberately strict: a bare leading backslash is
# drive-RELATIVE on Windows, and a UNC share (\\server\share) is not recognized
# either — a temp root is effectively never one, and the only cost of rejecting
# one is that its paths keep the normal out-of-project prompt.
is_absolute_path() {
  case "$1" in
    /*) return 0 ;;
    [A-Za-z]:[/\\]*) return 0 ;;
  esac
  return 1
}

# One path segment an exemption shape can match: non-empty, separator-free, and
# not a dot-segment. Every exemption gate below runs its extracted segments
# through this one predicate so they cannot drift apart — a bare `[[ -n ]]`
# would accept a literal '.' that a non-GNU realpath left uncollapsed, letting
# <store>/./memory pass a shape that is supposed to be exact.
is_single_segment() {
  case "$1" in
    ""|.|..) return 1 ;;
    */*|*\\*) return 1 ;;
  esac
  return 0
}

norm_root="$(normalize "$root")"
# Ensure trailing slash for prefix matching (avoids /project-other matching /project)
[[ "$norm_root" != */ ]] && norm_root="${norm_root}/"

# The exemption gates take an ALREADY normalized path (the `_n` suffix), so a
# caller can normalize once and consult all of them: an out-of-project write now
# pays one normalize() (two forks) instead of four. Raw-path wrappers exist only
# where a caller genuinely starts from an unnormalized string — see
# is_exempt_out_of_project and is_inside_project, used by the Bash rm branch,
# which parses paths out of a command string.
is_inside_project_n() {
  [[ "$1" == "${norm_root}"* || "$1" == "${norm_root%/}" ]]
}

is_inside_project() {
  is_inside_project_n "$(normalize "$1")"
}

# --- Claude Code auto-memory store (see header: CLAUDE MEMORY STORE) ---
# norm_home is resolved lazily on first use: this hook fires on every tool call,
# but only structured writes ever consult the store, so we skip the normalize()
# fork on the common read/search/Bash/in-project paths.
_norm_home=""
_norm_home_resolved=""
resolve_norm_home() {
  [[ -n "$_norm_home_resolved" ]] && return
  _norm_home="$(normalize "${HOME:-${USERPROFILE:-}}")"
  _norm_home_resolved=1
}

# True when a normalized path sits inside Claude's own config dir (~/.claude).
# The temp-write nudge consults this so ~/.claude keeps its plain prompt: it is
# config, not scratch, and it can itself sit under the temp root (CI images).
# Scoped to ~/.claude and NOT to all of $HOME on purpose — a whole-$HOME veto
# would silently disable the nudge on every machine whose temp root lives under
# the home dir (TMPDIR=$HOME/tmp, MSYS2/Cygwin default mounts).
# `${_norm_home%/}` so a home of "/" yields "/.claude", not "//.claude" — the
# latter is a UNC root that normalize() now preserves and would never match.
is_under_claude_config() {
  resolve_norm_home
  [[ -n "$_norm_home" ]] || return 1
  local home="${_norm_home%/}"
  [[ "$1" == "$home/.claude" || "$1" == "$home/.claude/"* ]]
}

is_claude_memory_n() {
  resolve_norm_home
  [[ -n "$_norm_home" ]] || return 1
  local norm_path="$1"
  # Fail closed on an unresolved ".." (shared guard): a traversal like
  # memory/../../settings.json must not reach the auto-allow below.
  has_unresolved_traversal "$norm_path" && return 1
  # Match exactly <home>/.claude/projects/<project>/memory[/...]. <project> must be
  # a SINGLE path segment: a bare case-glob '*' also spans '/', which would stretch
  # the exemption to a 'memory' dir nested arbitrarily deep under projects/. Every
  # project's store shares this shape and stays allowed — they are all Claude's own
  # recoverable scratchpad; the rest of ~/.claude (settings.json, etc.) is not.
  local prefix="${_norm_home%/}/.claude/projects/"
  [[ "$norm_path" == "$prefix"* ]] || return 1
  local rest="${norm_path#"$prefix"}"
  local seg="${rest%%/*}"
  is_single_segment "$seg" || return 1
  case "${rest#"$seg"}" in
    /memory|/memory/*) return 0 ;;
  esac
  return 1
}

# --- Claude Code session scratchpad (see header: CLAUDE SESSION SCRATCHPAD) ---
# Resolved lazily like the memory store: only out-of-project writes/deletes consult
# it, so the common in-project paths skip the normalize() work. The OS temp root
# varies (TMPDIR on macOS/Linux, TEMP/TMP on Windows, /tmp as a POSIX fallback), so
# each candidate is normalized once — a Windows temp mounted at /tmp then compares
# equal to a normalized file_path.
_scratch_bases_resolved=""
_scratch_bases=()
resolve_scratch_bases() {
  [[ -n "$_scratch_bases_resolved" ]] && return
  local candidate norm_candidate seen entry
  local -a raws=()
  for candidate in "${TMPDIR:-}" "${TEMP:-}" "${TMP:-}" /tmp; do
    [[ -n "$candidate" ]] || continue
    # A RELATIVE temp root is not a temp root: normalize() would resolve it
    # against this hook's working directory, so `TMPDIR=../scratch` would make
    # an arbitrary sibling of the project an auto-allowed subtree — exempt from
    # the out-of-project prompt AND from the rm hard-block.
    is_absolute_path "$candidate" || continue
    # Dedup the RAW spelling before paying for normalize(): on Windows TEMP and
    # TMP are routinely the identical string, and each normalize() forks twice.
    seen=""
    for entry in "${raws[@]}"; do [[ "$entry" == "$candidate" ]] && { seen=1; break; }; done
    [[ -n "$seen" ]] && continue
    raws+=("$candidate")
    norm_candidate="$(normalize "$candidate")"
    [[ -n "$norm_candidate" ]] || continue
    # A filesystem root is not a usable temp root — treating "/" as one would
    # make every absolute path "under the temp root".
    [[ "$norm_candidate" == "/" ]] && continue
    # Dedup again after normalize: cygpath maps the Windows temp dir onto the
    # /tmp mount, so distinct raw spellings collapse onto one base.
    seen=""
    for entry in "${_scratch_bases[@]}"; do [[ "$entry" == "$norm_candidate" ]] && { seen=1; break; }; done
    [[ -n "$seen" ]] && continue
    _scratch_bases+=("$norm_candidate")
  done
  _scratch_bases_resolved=1
}

# True when a normalized path sits under any resolved temp root.
is_under_temp_root() {
  resolve_scratch_bases
  local base
  for base in "${_scratch_bases[@]}"; do
    [[ "$1" == "$base/"* ]] && return 0
  done
  return 1
}

is_claude_scratchpad_n() {
  resolve_scratch_bases
  local norm_path="$1"
  # Fail closed on an unresolved ".." (shared guard): a traversal like
  # scratchpad/../../settings.json must not reach the auto-allow below.
  has_unresolved_traversal "$norm_path" && return 1
  # Match exactly <temp>/claude/<project>/<session>/scratchpad[/...]. <project> and
  # <session> must each be a SINGLE path segment so the exemption can't stretch to a
  # 'scratchpad' dir nested arbitrarily deep under <temp>/claude/.
  local base prefix rest proj after sess
  for base in "${_scratch_bases[@]}"; do
    prefix="$base/claude/"
    [[ "$norm_path" == "$prefix"* ]] || continue
    rest="${norm_path#"$prefix"}"          # <project>/<session>/scratchpad/...
    proj="${rest%%/*}"
    after="${rest#"$proj"}"                 # /<session>/scratchpad/...
    is_single_segment "$proj" || continue
    [[ "$after" == /* ]] || continue
    after="${after#/}"                      # <session>/scratchpad/...
    sess="${after%%/*}"
    is_single_segment "$sess" || continue
    case "${after#"$sess"}" in
      /scratchpad|/scratchpad/*) return 0 ;;
    esac
  done
  return 1
}

# --- Temp-write nudge (see header: CLAUDE SESSION SCRATCHPAD) ---
# Creating a NEW file under the temp root outside the exempt scratchpad shape
# still prompts — this only swaps in a reason that reminds Claude the scratchpad
# exists. It never converts a prompt into a decision made without you.
#
# It deliberately does NOT name a scratchpad path. Only the harness knows that
# path (it already gives it to Claude in the system prompt); a path built here
# from the project basename would name a look-alike directory the harness never
# created and never cleans up, and would contradict the one Claude was given.
#
# Either prompts (exits via ask_permission) or returns 1 — never prints otherwise.
nudge_temp_write() {
  local filepath="$1" norm_path="$2"
  # Only a NEW file is nudged: an Edit of an existing temp file has nothing to do
  # with choosing a scratch location, so it keeps the plain prompt. -L as well as
  # -e, because -e follows symlinks and would call a dangling one "new".
  [[ -e "$filepath" || -L "$filepath" ]] && return 1
  # Shared fail-closed guard: don't reason about a path whose '..' went unresolved.
  has_unresolved_traversal "$norm_path" && return 1
  # ~/.claude is Claude's config, not scratch — it keeps the plain prompt even
  # when HOME sits under the temp root (CI images). Scoped to ~/.claude and not
  # to all of $HOME: see the header note on TMPDIR=$HOME/tmp.
  is_under_claude_config "$norm_path" && return 1
  is_under_temp_root "$norm_path" || return 1
  ask_permission "File '$filepath' is a new file outside the project, under the OS temp root. This session's scratchpad (its path is in Claude's system prompt) is exempt from these prompts and is the better place for scratch files. Allow this write?"
}

# --- JSON response helpers ---
# Escape a reason for embedding in a JSON string. Backslash and quote are the
# obvious ones; the control characters matter because a reason can carry raw
# environment values (a temp root or directory name may legally contain a tab,
# CR or newline — a CRLF-sourced TEMP on Windows is the easy way to get one),
# and a bare control character makes the whole decision unparseable JSON, which
# the harness reads as "no decision" — silently dropping the deny or the ask.
# Result goes to a global rather than stdout: a `$(json_escape ...)` would fork a
# subshell on every prompt, where the whole function is fork-free parameter
# expansion. Same memoize-into-a-global idiom as resolve_scratch_bases.
_json_escaped=""
json_escape() {
  local s="${1//\\/\\\\}"
  s="${s//\"/\\\"}"
  s="${s//$'\n'/\\n}"
  s="${s//$'\r'/\\r}"
  s="${s//$'\t'/\\t}"
  # \n, \r and \t are gone by now, so what remains of C0 is one contiguous range
  # with no short escape — drop it. (DEL is legal raw in JSON, so it can stay.)
  s="${s//[$'\001'-$'\037']/}"
  _json_escaped="$s"
}

ask_permission() {
  json_escape "$1"
  cat <<JSONEOF
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"$_json_escaped"}}
JSONEOF
  exit 0
}

deny_operation() {
  json_escape "$1"
  cat <<JSONEOF
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"$_json_escaped"}}
JSONEOF
  exit 0
}

# --- Shared exemption ladder ---
# Locations that may be written/deleted without an out-of-project prompt: inside
# the project, Claude's own auto-memory store, and the session scratchpad. Every
# gate consults THIS function — the structured-write branch and the Bash rm
# branch alike — so adding an exemption is a one-line change here rather than
# edits to two ladders that must be kept in step. (Callers still run their own
# precious-file check afterwards, so this is not a blanket bypass.)
is_exempt_out_of_project_n() {
  is_inside_project_n "$1" && return 0
  is_claude_memory_n "$1" && return 0
  is_claude_scratchpad_n "$1" && return 0
  return 1
}

is_exempt_out_of_project() {
  is_exempt_out_of_project_n "$(normalize "$1")"
}

# --- Out-of-project gate for the structured write tools ---
# Returns 0 when the write may continue to the precious-file check;
# ask_permission exits the script.
guard_out_of_project_write() {
  local filepath="$1" noun="${2:-File}"
  local norm_path
  norm_path="$(normalize "$filepath")"
  is_exempt_out_of_project_n "$norm_path" && return 0
  # A new file under the temp root prompts with a scratchpad reminder; the plain
  # prompt below covers everything else.
  nudge_temp_write "$filepath" "$norm_path"
  ask_permission "$noun '$filepath' is outside project root. Allow this write?"
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
    guard_out_of_project_write "$filepath" "File"
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
    guard_out_of_project_write "$filepath" "Notebook"
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
          # Claude's own auto-memory store and session scratchpad are writable AND
          # prunable by design, so deletes there are allowed like writes — via the
          # SAME ladder the write gate uses (is_exempt_out_of_project), so the two
          # can never disagree about what is exempt. Everything else outside the
          # project root is hard-blocked. The shared ".." guard keeps a traversal
          # like memory/../../settings.json from slipping through.
          if ! is_exempt_out_of_project "$word"; then
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
