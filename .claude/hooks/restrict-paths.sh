#!/usr/bin/env bash
# ============================================================================
# restrict-paths.sh — Claude Code PreToolUse hook
# Installed by: /optimus:permissions (optimus-claude plugin)
# Source:       https://github.com/oprogramadorreal/optimus-claude
# Docs:         skills/permissions/README.md
# ============================================================================
# HOOK_VERSION: 3
# ^ Bump on every behavioural change. The plugin's SessionStart hook compares
#   this against the copy installed in a project and recommends re-running
#   /optimus:permissions when the project's copy is older — a plugin update
#   never re-copies an already-installed hook on its own.
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
#   - Creating a NEW file under the OS temp root → prompts you, and tells Claude
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
#   (an invented temp dir) still prompts you — the nudge never decides for you,
#   so a temp path you asked for yourself still comes to you for approval.
#
#   TWO AUDIENCES, TWO FIELDS. For a PreToolUse "ask", Claude Code shows
#   permissionDecisionReason to the USER, while additionalContext injects
#   information for CLAUDE alongside the tool decision. Only "deny" sends its
#   reason to the model. So the prompt text is
#   written for you, and the scratchpad reminder — the part only Claude can act
#   on — rides additionalContext. Putting the reminder in the reason instead
#   would deliver it to the one party who cannot act on it.
#
#   The reminder deliberately does NOT name a scratchpad path: only the harness
#   knows it, and it already gives it to Claude in the system prompt. A path
#   built here from the project basename would name a look-alike directory the
#   harness neither creates nor cleans up.
#
#   Scope: a file that ALREADY EXISTS keeps the plain prompt (existence is
#   tested on the NORMALIZED path, so a phantom intermediate dir cannot make an
#   existing file look new), and ~/.claude keeps its own — it is Claude's
#   config, not scratch, and it can sit under the temp root in CI images. The
#   nudge is skipped when the path contains a ".." this platform's realpath left
#   unresolved. The ~/.claude veto is deliberately NOT a whole-$HOME veto, which
#   would disable the nudge wherever the temp root lives under the home dir
#   (TMPDIR=$HOME/tmp, MSYS2/Cygwin default mounts) — the common case.
#
# PATH NORMALIZATION:
#   normalize() lowercases on Windows, resolves "..", collapses repeated slashes
#   and drops a trailing one, so every spelling of a path compares equal. The
#   collapse is load-bearing: macOS TMPDIR ends in '/', a non-GNU realpath that
#   rejects '-m' returns the string untouched, and the cd/pwd fallback splices
#   '//tmp' when the parent is '/' — each would otherwise leave a base that stops
#   matching paths written the ordinary way, silently killing an exemption.
#
#   A leading '//' is preserved only when it is present BOTH in the path as the
#   OS spells it (i.e. after cygpath, which is what turns '\\server\share' into
#   '//server/share' — probing the raw argument would miss every natively spelled
#   UNC path) AND in the post-realpath string. That is a UNC network root on
#   MSYS/Cygwin, genuinely distinct from '/'. Requiring both readings matters in
#   both directions: on Linux realpath collapses '//x' to '/x' (POSIX leaves
#   exactly two leading slashes implementation-defined) and the platform's answer
#   is respected, while the cd/pwd fallback's spliced '//tmp' is NOT mistaken for
#   a UNC root. Three or more leading slashes are plain '/'.
#
#   normalize() also resolves '.' and '..' ITSELF (collapse_dot_segments) when
#   the steps above left them in place — a realpath that rejects '-m', or the
#   cd/pwd fallback. Doing so is what lets an ordinary in-project 'a/../b' stay
#   allowed on those platforms: the alternative, failing closed on any '..',
#   turns it into a hard DENY that goes to the model and can never be approved.
#   An absolute path cannot climb above its own root (POSIX: '/..' is '/').
#
#   Exemption gates take an ALREADY normalized path (the `_n` suffix), so a
#   caller normalizes once and consults all of them. Every gate that can reach an
#   auto-allow keeps a has_unresolved_traversal backstop for the one case the
#   resolution above cannot settle — a RELATIVE path, which has no root to anchor
#   '..' against — so such a path can never pass a prefix test.
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
# Resolve '.' and '..' segments lexically, preserving a leading '/' or '//'.
# Pure bash (result in a global, no fork). `realpath -m` already does this, but a
# realpath that REJECTS '-m' (macOS/BSD) and the cd/pwd fallback both leave the
# segments in place — and a gate that cannot resolve '..' has to fail closed,
# which would turn an ordinary in-project 'a/../b' into an unapprovable deny.
_collapsed=""
collapse_dot_segments() {
  local p="$1" seg lead="" n
  case "$p" in
    //[!/]*) lead="//"; p="${p#//}" ;;
    /*)      lead="/";  p="${p#/}"  ;;
  esac
  local -a parts=()
  local IFS='/'
  # noglob around the split. `for seg in $p` is unquoted — it MUST be, that is
  # what splits on IFS — so without this every segment is also pathname-expanded
  # against the hook's CWD (the project root). A '*' segment then becomes N
  # segments here but stays ONE for the OS, and the extra segments absorb the
  # following '..', so '<proj>/*/../../../etc/evil' looks in-project to every
  # gate while the OS resolves it outside: a silent allow on the write AND an
  # escape from the rm hard-block. has_unresolved_traversal cannot backstop it,
  # since the '..' are gone by then. Restored only if we set it, so an outer
  # `set -f` survives.
  local _noglob_set=""
  [[ -o noglob ]] || { _noglob_set=1; set -f; }
  for seg in $p; do
    case "$seg" in
      ""|.) ;;
      ..)
        n=${#parts[@]}
        if [[ $n -gt 0 && "${parts[$((n-1))]}" != ".." ]]; then
          unset "parts[$((n-1))]"
          parts=(${parts[@]+"${parts[@]}"})
        elif [[ -z "$lead" ]]; then
          # A relative path may legitimately keep leading '..'; an absolute one
          # cannot go above its root (POSIX: '/..' is '/').
          parts+=("..")
        fi
        ;;
      *) parts+=("$seg") ;;
    esac
  done
  [[ -n "$_noglob_set" ]] && set +f
  _collapsed="$lead${parts[*]-}"
}

normalize() {
  local p="$1"
  # Convert Windows paths on MSYS/Cygwin. '--' so a path that looks like a flag
  # ('-n', '-e') is not eaten as one, which would hand the gates an empty string.
  command -v cygpath &>/dev/null && p="$(cygpath -u -- "$p" 2>/dev/null || printf '%s\n' "$p")"
  # How the OS itself spells the path, before any resolution. The UNC probe below
  # reads THIS, not "$1": cygpath is what turns '\\server\share' into
  # '//server/share', so probing the raw argument would miss every UNC path
  # spelled the native Windows way and collapse it onto an unrelated local path.
  local spelled="$p"
  # Resolve ../ traversal without requiring path to exist
  if command -v realpath &>/dev/null; then
    p="$(realpath -m -- "$p" 2>/dev/null || printf '%s\n' "$p")"
  elif [[ -d "$(dirname "$p")" ]]; then
    p="$(cd "$(dirname "$p")" 2>/dev/null && pwd)/$(basename "$p")"
  fi
  # Collapse repeated slashes, drop a trailing one (see header: PATH
  # NORMALIZATION). Requiring the UNC shape in BOTH the OS spelling and the
  # post-realpath string keeps the cd/pwd fallback's spliced '//tmp' from being
  # mistaken for a UNC root, while respecting a realpath that already collapsed a
  # genuine '//' per its platform's rule.
  local lead=""
  [[ "$spelled" == //[!/]* && "$p" == //[!/]* ]] && { lead="/"; p="${p#/}"; }
  while [[ "$p" == *//* ]]; do p="${p//\/\//\/}"; done
  [[ "$p" == "/" ]] || p="${p%/}"
  p="$lead$p"
  # Resolve anything the steps above left behind. Skipped unless a dot-segment is
  # actually present, so the common path stays pure parameter expansion.
  case "$p" in
    */../*|*/..|../*|..|*/./*|*/.|./*|.) collapse_dot_segments "$p"; p="$_collapsed" ;;
  esac
  # Case-insensitive on Windows (NTFS)
  [[ "${OSTYPE:-}" == msys* || "${OSTYPE:-}" == cygwin* ]] && p="${p,,}"
  # printf, not echo: a path of exactly '-n'/'-e'/'-E' is an echo FLAG and would
  # come back as the empty string, silently dropping the path from every gate.
  printf '%s\n' "$p"
}

# --- Shared path predicates (see header: PATH NORMALIZATION) ---
# Backstop, not the primary defence: normalize() now resolves '..' itself, so an
# absolute path reaching a gate has none left. What can still arrive is a
# RELATIVE path, which has no root to anchor '..' against. Kept on every gate
# that can auto-allow because it is free and fails in the safe direction.
has_unresolved_traversal() {
  case "$1" in */../*|*/..|../*|..) return 0 ;; esac
  return 1
}

# Rejects a RELATIVE temp root, which normalize() would resolve against this
# hook's working directory — turning an arbitrary sibling of the project into an
# auto-allowed subtree, exempt from the prompt AND from the rm hard-block.
# A bare leading backslash stays rejected: it is drive-RELATIVE on Windows.
is_absolute_path() {
  case "$1" in
    /*) return 0 ;;              # POSIX absolute, incl. //server/share
    '\\'?*) return 0 ;;          # UNC \\server\share (cygpath maps it to //...)
    [A-Za-z]:[/\\]*) return 0 ;; # drive-qualified C:\ or C:/
  esac
  return 1
}

# One path segment an exemption shape may match. Like has_unresolved_traversal
# this is now a backstop: normalize() drops '.' segments before any gate sees
# them. Kept because it is free and the shapes are meant to be exact.
is_single_segment() {
  case "$1" in
    ""|.|..) return 1 ;;
    */*|*\\*) return 1 ;;
  esac
  return 0
}

# --- Project root ---
# Resolved lazily: this hook fires on EVERY tool call, but only the write and rm
# branches consult the root, so reads/searches skip the normalize() forks.
_norm_root=""
_norm_root_resolved=""
resolve_norm_root() {
  [[ -n "$_norm_root_resolved" ]] && return
  _norm_root="$(normalize "$root")"
  # Trailing slash for prefix matching (avoids /project-other matching /project)
  [[ "$_norm_root" != */ ]] && _norm_root="${_norm_root}/"
  _norm_root_resolved=1
}

is_inside_project_n() {
  has_unresolved_traversal "$1" && return 1
  resolve_norm_root
  [[ "$1" == "$_norm_root"* || "$1" == "${_norm_root%/}" ]]
}

# --- Claude Code auto-memory store (see header: CLAUDE MEMORY STORE) ---
_norm_home=""
_norm_home_resolved=""
resolve_norm_home() {
  [[ -n "$_norm_home_resolved" ]] && return
  _norm_home_resolved=1
  # Fail closed on an unset home rather than normalizing "": on a realpath-less
  # platform that resolves to this hook's working directory, which would anchor
  # the memory-store exemption on an arbitrary cwd.
  local raw="${HOME:-${USERPROFILE:-}}"
  [[ -n "$raw" ]] || return
  _norm_home="$(normalize "$raw")"
}

# `${_norm_home%/}` so a home of "/" yields "/.claude", not "//.claude".
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
  has_unresolved_traversal "$norm_path" && return 1
  # Match exactly <home>/.claude/projects/<project>/memory[/...]. A bare case-glob
  # '*' also spans '/', so <project> goes through is_single_segment or the
  # exemption would stretch to a 'memory' dir nested arbitrarily deep.
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
# Resolved lazily like the project root. The OS temp root varies (TMPDIR on
# macOS/Linux, TEMP/TMP on Windows, /tmp as a POSIX fallback), so each candidate
# is normalized once — a Windows temp mounted at /tmp then compares equal to a
# normalized file_path, and duplicate spellings collapse onto one base.
_scratch_bases_resolved=""
_scratch_bases=()
resolve_scratch_bases() {
  [[ -n "$_scratch_bases_resolved" ]] && return
  _scratch_bases_resolved=1
  local candidate norm_candidate entry seen
  local -a raws=()
  for candidate in "${TMPDIR:-}" "${TEMP:-}" "${TMP:-}" /tmp; do
    [[ -n "$candidate" ]] || continue
    is_absolute_path "$candidate" || continue
    # Dedup the RAW spelling before paying for normalize(): on Windows TEMP and
    # TMP are routinely the identical string, and each normalize() forks twice.
    seen=""
    for entry in ${raws[@]+"${raws[@]}"}; do [[ "$entry" == "$candidate" ]] && { seen=1; break; }; done
    [[ -n "$seen" ]] && continue
    raws+=("$candidate")
    norm_candidate="$(normalize "$candidate")"
    [[ -n "$norm_candidate" ]] || continue
    # A bare root is not a usable temp root — treating "/" (or the UNC namespace
    # root "//") as one would make every path "under the temp root".
    [[ "$norm_candidate" == "/" || "$norm_candidate" == "//" ]] && continue
    seen=""
    for entry in "${_scratch_bases[@]}"; do [[ "$entry" == "$norm_candidate" ]] && { seen=1; break; }; done
    [[ -n "$seen" ]] || _scratch_bases+=("$norm_candidate")
  done
}

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
  has_unresolved_traversal "$norm_path" && return 1
  # Match exactly <temp>/claude/<project>/<session>/scratchpad[/...]; both slots
  # go through is_single_segment so the exemption can't stretch to a 'scratchpad'
  # dir nested arbitrarily deep under <temp>/claude/.
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

# --- Temp-write nudge (see header: TEMP-WRITE NUDGE) ---
# Either prompts (exits via ask_permission) or returns 1 — never prints otherwise.
nudge_temp_write() {
  local filepath="$1" norm_path="$2" noun="$3" verb="$4"
  # Only a NEW file is nudged: an Edit of an existing temp file has nothing to do
  # with choosing a scratch location. Test the NORMALIZED path so a phantom
  # intermediate dir ('<temp>/a/../b.md') cannot make an existing file look new.
  # -L as well as -e, because -e follows symlinks and would call a dangling one new.
  [[ -e "$norm_path" || -L "$norm_path" ]] && return 1
  has_unresolved_traversal "$norm_path" && return 1
  is_under_claude_config "$norm_path" && return 1
  is_under_temp_root "$norm_path" || return 1
  ask_permission \
    "$noun '$filepath' is a new file outside the project, under the OS temp root. Allow this $verb?" \
    "This path is outside the exempt session scratchpad. Prefer the scratchpad directory given in your system prompt for throwaway files — writes there need no approval."
}

# --- JSON response helpers ---
# A reason can carry raw environment values (a temp root or directory name may
# legally contain a tab, CR or newline — a CRLF-sourced TEMP on Windows is the
# easy way to get one), and a bare control character makes the whole decision
# unparseable JSON, which the harness reads as "no decision" — silently dropping
# the deny or the ask. Every C0 code point JSON gives a short escape gets one;
# the rest are dropped. (DEL is legal raw in JSON, so it stays.)
# Writes to a global rather than stdout so the caller pays no subshell fork.
_json_escaped=""
json_escape() {
  local s="${1//\\/\\\\}"
  s="${s//\"/\\\"}"
  s="${s//$'\n'/\\n}"
  s="${s//$'\r'/\\r}"
  s="${s//$'\t'/\\t}"
  s="${s//$'\b'/\\b}"
  s="${s//$'\f'/\\f}"
  s="${s//[$'\001'-$'\037']/}"
  _json_escaped="$s"
}

# $1 = decision, $2 = reason for the USER, $3 = optional context for CLAUDE.
# The two audiences are distinct — see header: TEMP-WRITE NUDGE. printf, not a
# `cat` heredoc, so emitting a decision costs no fork.
emit_decision() {
  json_escape "$2"
  local reason="$_json_escaped" extra=""
  if [[ -n "${3:-}" ]]; then
    json_escape "$3"
    extra=",\"additionalContext\":\"$_json_escaped\""
  fi
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"%s","permissionDecisionReason":"%s"%s}}\n' \
    "$1" "$reason" "$extra"
  exit 0
}

ask_permission() { emit_decision ask "$1" "${2:-}"; }

# A deny already sends its reason to the model, so it needs no additionalContext.
deny_operation() { emit_decision deny "$1"; }

# --- Shared exemption ladder ---
# Locations that may be written/deleted without an out-of-project prompt. The
# structured-write branch and the Bash rm branch both consult THIS function, so
# the two can never disagree about what is exempt. Cheapest gate first: the
# project test is fork-free, the memory store costs one normalize, the scratchpad
# up to four. (Callers still run their own precious-file check afterwards, so
# this is not a blanket bypass.)
is_exempt_out_of_project_n() {
  is_inside_project_n "$1" && return 0
  is_claude_memory_n "$1" && return 0
  is_claude_scratchpad_n "$1" && return 0
  return 1
}

# --- Out-of-project gate for the structured write tools ---
# Returns 0 when the write may continue to the precious-file check;
# ask_permission exits the script.
guard_out_of_project_write() {
  local filepath="$1" noun="$2" verb="$3"
  local norm_path
  norm_path="$(normalize "$filepath")"
  is_exempt_out_of_project_n "$norm_path" && return 0
  # A new file under the temp root prompts with a scratchpad reminder for Claude;
  # the plain prompt below covers everything else. `|| true` so the expected
  # non-zero return cannot abort the script under an inherited errexit, which
  # would emit no decision at all.
  nudge_temp_write "$filepath" "$norm_path" "$noun" "$verb" || true
  ask_permission "$noun '$filepath' is outside project root. Allow this $verb?"
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
    guard_out_of_project_write "$filepath" "File" "write"
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
    guard_out_of_project_write "$filepath" "Notebook" "edit"
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
          # SAME ladder the write gate uses. Everything else outside the project
          # root is hard-blocked. Normalize once and reuse: the two gates below
          # would otherwise resolve the same word twice, two forks apiece.
          _nword="$(normalize "$word")"
          if ! is_exempt_out_of_project_n "$_nword"; then
            deny_operation "BLOCKED: Cannot delete '$word' — outside project root."
          fi
          # Precious file protection: block deletion of sensitive unversioned files
          if [[ -e "$word" ]] && is_inside_project_n "$_nword" && is_precious "$word" && ! is_git_tracked "$word"; then
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
