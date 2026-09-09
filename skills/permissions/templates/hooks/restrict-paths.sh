#!/usr/bin/env bash
# ============================================================================
# restrict-paths.sh — Claude Code PreToolUse hook
# Installed by: /optimus:permissions (optimus-claude plugin)
# Source:       https://github.com/oprogramadorreal/optimus-claude
# Docs:         skills/permissions/README.md
# ============================================================================
# HOOK_VERSION: 11
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
# COMMAND PARSING:
#   A Bash tool call arrives as ONE string that may hold many commands. Both
#   Bash-side guards (delete protection, git branch protection) work on it in
#   four stages, each of which exists because skipping it turned the guard off
#   for an ordinary spelling rather than an exotic one:
#     1. Join backslash-newline line continuations (a continuation is one
#        command, not two), then split on the shell's command operators — '&&',
#        '||', ';', '|', '&' and newline — then peel any leading keyword ('do ',
#        'then ', '{ ') the split left at the front of a fragment. A subshell's
#        parens are counted, not just stripped, so a `cd` inside one does not
#        outlive it.
#     2. shell_split() each fragment into words, honouring quotes and escapes and
#        expanding '~' and every SET $VAR, so a gate compares the path the shell
#        will act on rather than the characters as typed. A name this hook cannot
#        see (a caller's shell variable is not exported) stays literal — see
#        expand_word.
#     3. cmd_word_index() locates the fragment's command word THROUGH a wrapper
#        prefix (sudo, command, env VAR=val, xargs and its flags — including a
#        flag's separate-word value, as in `sudo -u root` — /bin/rm, \rm), and
#        stops at the first token that is a real command, so an argument that
#        merely reads 'rm' is never mistaken for one.
#     4. `sh -c <string>`, `bash -c <string>` and `eval` carry a whole command
#        inside a single ARGUMENT, which stage 3 can never reach. unwrap_shell_c()
#        pulls the string out and feeds it back through stage 1, depth-bounded.
#   Two things a fragment's words are NOT: a redirection operator or its target
#   ('> /dev/null' is a stream, not a file to delete or a refspec to push), and a
#   relative path meaning what it says — a target is resolved against the chain's
#   own `cd` first, so `cd /etc && rm passwd` is judged as /etc/passwd.
#   Not covered, by design: command substitution (`rm $(cat list)`) and
#   `find -exec`, where the delete is not the fragment's own command. This is a
#   guardrail against accidents, not a sandbox against a determined bypass.
#
#   Known false positive, and deliberately kept: stage 1 splits on operators
#   BEFORE stage 2 parses quotes, so an operator INSIDE a quoted argument
#   (`echo "a; rm /etc/passwd"`) leaves a fragment that reads as a real command,
#   and it is denied. Stage 4 inherits the same wart — a mangled fragment
#   beginning `eval` gets unwrapped too. Quote-aware splitting would remove it,
#   and would also turn today's denies into silent allows: that same mangling is
#   the only reason `sh -c "cd /etc; rm passwd"` is caught, since the payload
#   reaches stage 4 as `cd /etc` and the delete arrives as its own fragment.
#   An over-eager prompt is recoverable; a missed delete is not.
#
# TO DISABLE OR REMOVE:
#   1. Delete this file: rm .claude/hooks/restrict-paths.sh
#   2. Remove the PreToolUse hook entry from .claude/settings.json
#   Or simply ignore it — the hook only runs when Claude Code invokes tools.
# ============================================================================

# Every top-level variable this hook owns carries the '_rp_' prefix, and that is
# load-bearing rather than cosmetic: the environment snapshot below resolves each
# exported name with an indirect expansion, which reads the SHELL namespace, so a
# hook global sharing a name with an exported variable wins. Unprefixed, `root`
# was one of them — with `root=/etc` exported, `rm -rf $root/passwd` expanded to
# the PROJECT directory, passed every gate as an in-project delete, and the shell
# removed /etc/passwd. Same for `input`, `cmd` and `tool_name`.
_rp_input=$(cat)

_rp_root="${CLAUDE_PROJECT_DIR}"
# Fail-open: if project root is unknown, allow rather than block all tool use
[[ -z "$_rp_root" ]] && exit 0

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

# basename without the fork. The precious tests below run on EVERY Edit, Write
# and NotebookEdit, so a `$(basename ...)` here is a subshell on the hook's
# hottest path — and the `basename | tr` pipeline this replaces measured ~109 ms
# per call on Windows, where nothing else on that path forks at all.
_basename=""
basename_of() {
  local p="$1"
  # Both separators end a segment on Windows. Claude Code spells file_path as
  # 'C:\Users\me\proj\.env', which holds no '/' at all — so splitting on '/'
  # alone left the WHOLE path as the basename, and no prefix or exact pattern
  # ('.env*', 'credentials.*', 'local.settings.json', 'appsettings.*.json') can
  # match that. Precious-file protection was silently off for every
  # backslash-spelled path, on both the edit ask and the delete block; only the
  # suffix-anchored patterns ('*.key', '*.pem', '*.sqlite') still matched, by
  # accident. Platform-gated because a backslash is a legal FILENAME character
  # elsewhere: on Linux 'a\b' is one file, and splitting it would drop the
  # protection this restores.
  case "${OSTYPE:-}" in msys*|cygwin*) p="${p//\\//}" ;; esac
  while [[ "$p" == */ && "$p" != "/" ]]; do p="${p%/}"; done
  _basename="${p##*/}"
}

# Case-fold ONCE, here, and hand the folded basename to both list tests. Folding
# separately inside each let the two disagree about the same file: this rule is
# platform-gated, and the recoverable test used to fold unconditionally, so on
# Linux 'NOTES.TXT.BAK' was recoverable to one entry point and unknown to the other.
precious_basename() {
  basename_of "$1"
  # Case-insensitive matching for Windows (NTFS) and macOS (APFS)
  if [[ "${OSTYPE:-}" == msys* || "${OSTYPE:-}" == cygwin* || "${OSTYPE:-}" == darwin* ]]; then
    if (( BASH_VERSINFO[0] >= 4 )); then
      _basename="${_basename,,}"
    else
      _basename="$(printf '%s' "$_basename" | tr '[:upper:]' '[:lower:]')"
    fi
  fi
}

is_precious() {
  precious_basename "$1"
  local lname="$_basename"
  is_precious_name "$lname" && return 0
  is_recoverable_precious_name "$lname"
}

# What the DELETE gate tests: the hard list, and nothing else.
#
# Deliberately NOT `is_precious && ! is_recoverable_precious`. is_precious is
# itself (hard || recoverable), so that expression expands to
# (hard || recoverable) && !recoverable — and any name on BOTH lists
# short-circuits to unprotected. '.env.suo', '.env.<x>.user', 'credentials.suo'
# and 'secrets.user' each match a hard pattern ('.env*', 'credentials.*',
# 'secrets.*') AND a recoverable one ('*.suo', '*.user'), so every one of them
# became silently deletable — the exact opposite of the intent.
#
# A stem re-test inside is_recoverable_precious_name cannot fix it either:
# 'credentials.suo' matches 'credentials.*' as a WHOLE name, not through a stem,
# so there is nothing to strip. Hard-precious has to win at the gate.
is_hard_precious() {
  precious_basename "$1"
  is_precious_name "$_basename"
}

# Strip ONE trailing backup or rotation suffix from a name. Result in _stripped;
# returns 1 when the name carries none. Shared by is_precious_name so the whole
# CLASS of backup suffixes is closed rather than one instance of it.
_stripped=""
strip_backup_suffix() {
  local n="$1"
  case "$n" in
    *'~') _stripped="${n%\~}"; return 0 ;;
    *.bak|*.backup|*.old|*.orig|*.save|*.saved|*.copy|*.prev) _stripped="${n%.*}"; return 0 ;;
    # Rotation: 'server.key.1', 'db.sqlite.02', 'prod.dump.003'.
    *.[0-9]|*.[0-9][0-9]|*.[0-9][0-9][0-9]) _stripped="${n%.*}"; return 0 ;;
  esac
  return 1
}

# The hard list, matched on a basename the caller has already case-folded.
# Split out of is_precious so is_recoverable_precious can re-test a '.bak' stem
# against it without recursing back through the tail call below.
is_precious_name() {
  local lname="$1"
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
    # Database dumps
    *.dump|*.sql.gz) return 0 ;;
  esac
  # A backup copy holds exactly what it copied, so re-test the stem against the
  # same list. Without this, only the PREFIX patterns above ('.env*',
  # 'credentials.*') survived an appended suffix — 'id_rsa.pem.bak',
  # 'server.key.old' and 'app.sqlite~' matched nothing, and the suffix laundered
  # them off the list. Re-testing only '.bak' closed one instance of that and
  # left '.old', '.orig', '.backup', '~' and '.1' doing the same job. Each hop
  # strips at least one character, so the recursion is bounded by the name.
  if strip_backup_suffix "$lname"; then
    is_precious_name "$_stripped"
    return $?
  fi
  return 1
}

# Precious, but recoverable: worth an ask before overwriting, never worth an
# undeniable block on delete. A PreToolUse deny is delivered to the model, not
# the user, so there is no path to "yes, delete it" — and these are exactly the
# files a cleanup step legitimately removes (the harness writes
# .claude/<skill>-deep-progress.json.bak on every run).
is_recoverable_precious() {
  precious_basename "$1"
  is_recoverable_precious_name "$_basename"
}

# Matched on a basename the caller has already case-folded, like is_precious_name.
# The trigger list stays deliberately narrower than strip_backup_suffix: this one
# also decides which ORDINARY files prompt before an overwrite, so widening it to
# every rotation suffix would start prompting on 'access.log.1' and 'main.py.orig'.
# Laundering is closed in is_precious_name instead, where the wider set can only
# ever ADD protection.
is_recoverable_precious_name() {
  local lname="$1"
  case "$lname" in
    *.suo|*.user) return 0 ;;
    *.bak)
      # Only a backup OF something ordinary is recoverable. Matching the '.bak'
      # suffix alone made the suffix a laundering trick: '.env.bak',
      # 'id_rsa.pem.bak', 'credentials.json.bak' and 'app.sqlite.bak' hold
      # exactly the secrets of the file they copy, yet each dropped out of the
      # hard list the moment the suffix was appended. Re-test the stem.
      is_precious_name "${lname%.bak}" && return 1
      return 0 ;;
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
    local resolved_parent
    # -d does not imply traversal permission; preserve the input if cd fails.
    if resolved_parent="$(cd "$(dirname "$p")" 2>/dev/null && pwd)"; then
      p="$resolved_parent/$(basename "$p")"
    fi
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
  if [[ "${OSTYPE:-}" == msys* || "${OSTYPE:-}" == cygwin* ]]; then
    if (( BASH_VERSINFO[0] >= 4 )); then
      p="${p,,}"
    else
      p="$(printf '%s' "$p" | tr '[:upper:]' '[:lower:]')"
    fi
  fi
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
  _norm_root="$(normalize "$_rp_root")"
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
  # C locale pins the [$'\001'-$'\037'] range below to byte order: before bash
  # 4.3's globasciiranges default (stock macOS ships 3.2), bracket ranges follow
  # locale collation, which can let a control char through in a UTF-8 locale.
  local LC_ALL=C
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

# --- Command-line word splitting (see header: COMMAND PARSING) ---
# Split a command fragment into shell words, honouring single quotes, double
# quotes and backslash escapes, then expand '~' and $VAR. Result in _words.
#
# `read -ra` is not a substitute: it splits on whitespace and hands back the
# characters verbatim, quote marks included. `rm "<abs path>"` then arrives as
# the single word '"<abs path>"', which normalize() resolves as a RELATIVE path
# under the project root — so the out-of-project hard block never fires. Claude
# Code quotes any path containing a space, so that was the common case, not an
# exotic one. Same story for '~/x' and '$HOME/x'.
_words=()
shell_split() {
  # Byte semantics for the character walk below, like json_escape pins for its
  # bracket range. In a UTF-8 locale bash decodes ${s:i:1} as a CHARACTER, which
  # re-scans from the front of the string on every index — the walk is
  # superlinear, and past ~2 KB it costs more than the `sed` split it replaced
  # (about a second slower on a 16 KB one-liner). The loop only ever compares
  # against ASCII delimiters and reassembles the pieces in order, and a UTF-8
  # continuation byte can never equal one of those, so byte-wise walking yields
  # identical words.
  local LC_ALL=C
  # Two statements on purpose: bash expands a whole `local` line BEFORE binding
  # any of its names, so `local s="$1" n=${#s}` reads the OUTER s and sets n=0 —
  # the loop below then never runs and every fragment splits to nothing.
  local s="$1"
  local n=${#s} i=0 c d q="" cur="" started=""
  _words=()
  while (( i < n )); do
    c="${s:i:1}"
    if [[ "$q" == "'" ]]; then
      if [[ "$c" == "'" ]]; then q=""; else cur+="$c"; fi
    elif [[ "$q" == '"' ]]; then
      if [[ "$c" == '"' ]]; then
        q=""
      elif [[ "$c" == '\' ]]; then
        # Inside double quotes a backslash escapes only these four.
        d="${s:i+1:1}"
        case "$d" in
          '"'|'\'|'$'|'`') cur+="$d"; (( ++i )) ;;
          *) cur+="$c" ;;
        esac
      else
        cur+="$c"
      fi
    else
      case "$c" in
        "'"|'"') q="$c"; started=1 ;;
        '\') cur+="${s:i+1:1}"; (( ++i )); started=1 ;;
        ' '|$'\t'|$'\n')
          if [[ -n "$started" ]]; then _words+=("$cur"); cur=""; started=""; fi
          ;;
        *) cur+="$c"; started=1 ;;
      esac
    fi
    # PRE-increment, throughout. `(( i++ ))` evaluates to the OLD value, so on
    # the first pass it evaluates to 0 — and an arithmetic command whose result
    # is 0 returns exit status 1. Under an inherited errexit that aborts the
    # hook on the very first character of the very first fragment, before any
    # decision is emitted: both Bash-side guards silently stop existing. `++i`
    # increments identically and can never evaluate to 0 here.
    (( ++i ))
  done
  [[ -n "$started" ]] && _words+=("$cur")
  local _i=0
  while (( _i < ${#_words[@]} )); do
    expand_word "${_words[_i]}"
    _words[_i]="$_expanded"
    (( ++_i ))
  done
  return 0
}

# Expand a leading '~' and every $VAR / ${VAR} in a word. No eval, no forks.
# Result in _expanded.
#
# Expansion is applied to every word, including single-quoted ones the shell
# would keep literal. That over-expands in exactly one direction: a file
# literally named '$HOME' would be judged by where the variable points, which
# errs toward asking or blocking. Under-expanding is the hole this closes —
# `rm $HOME/.ssh/id_rsa` used to read as an in-project relative path and sail
# straight through the out-of-project block.
_expanded=""
expand_word() {
  local w="$1" out="" rest name literal ch
  case "$w" in
    "~")   w="${HOME:-\~}" ;;
    "~/"*) w="${HOME:-\~}/${w#\~/}" ;;
  esac
  while [[ "$w" == *'$'* ]]; do
    out+="${w%%\$*}"
    rest="${w#*\$}"
    name=""
    if [[ "$rest" == '{'* && "$rest" == *'}'* ]]; then
      name="${rest%%\}*}"; name="${name#\{}"
      literal="\${$name}"
      rest="${rest#*\}}"
    else
      while [[ -n "$rest" ]]; do
        ch="${rest:0:1}"
        case "$ch" in
          [a-zA-Z0-9_]) name+="$ch"; rest="${rest:1}" ;;
          *) break ;;
        esac
      done
      literal="\$$name"
    fi
    # Only a plain identifier the CALLER's shell would also see is resolved.
    # '$(...)', '$1', '${x:-y}' and the like stay literal — reading them needs an
    # eval this hook will not run, and a word the hook leaves literal is still
    # checked, just as written.
    #
    # The lookup is load-bearing in both directions. A shell variable assigned in
    # the caller (`BUILD_DIR=build && rm -rf $BUILD_DIR/x`) is not exported, so
    # the hook never sees it — substituting "" collapsed the word to '/x', which
    # every gate read as an absolute path outside the project and HARD DENIED.
    # A deny goes to the model with no prompt and no override, so ordinary
    # build-dir cleanup became impossible. Leaving the word literal matches the
    # file's fail-open rule (see header: FAIL-OPEN DESIGN): a name this hook
    # cannot resolve is a path it cannot judge. Exported and environment
    # variables — $HOME above all — are still expanded, so `rm $HOME/.ssh/id_rsa`
    # stays blocked.
    if lookup_env_value "$name"; then
      out+="$_env_value"
    else
      out+="$literal"
    fi
    w="$rest"
  done
  _expanded="$out$w"
}

# The caller's view of a $VAR, from a snapshot of the environment (see the
# populate step in the Bash branch at the bottom of this file).
#
# What this replaces: `-n "${!name+set}"` followed by `${!name}`. An indirect
# expansion resolves against the WHOLE shell namespace — this hook's own globals
# and, because bash scopes `local` dynamically, the locals of every function on
# the stack. expand_word's own `out`/`rest`/`ch` and shell_split's `q`/`cur`/`n`
# were all in scope, so a user command that merely mentioned one of those names
# was judged against the HOOK's value: `out=dist && rm -rf $out/assets` denied
# '/assets', `q=queue && rm -rf $q/tmp` denied '/tmp'. Unappealable, on commands
# that never named a path outside the project. Names the hook cannot see are
# exactly the ones that must stay literal, and only the environment is genuinely
# shared with the caller's shell.
#
# Parallel indexed arrays rather than one associative array: bash 3.2 (stock
# macOS) has no `declare -A`, and this must not quietly stop expanding $HOME
# there. A linear scan of ~100 names per '$' is nothing next to the forks the
# gates below already pay.
_env_keys=()
_env_vals=()
_env_value=""
lookup_env_value() {
  local i=0
  while (( i < ${#_env_keys[@]} )); do
    if [[ "${_env_keys[i]}" == "$1" ]]; then _env_value="${_env_vals[i]}"; return 0; fi
    (( ++i ))
  done
  return 1
}

# Locate the command word of an already-split fragment: sets _cmd_idx to the
# index of the first token whose basename matches one of the '|'-separated
# names in $1, and returns 1 when the fragment runs some other command.
#
# A guard anchored on the fragment's FIRST token misses every ordinary spelling
# of the same command — `sudo rm`, `command rm`, `env rm`, `/bin/rm`, `\rm`
# (which defeats an alias, not this hook), `xargs -n 1 rm`, `xargs -I {} rm`,
# `timeout 5 rm`. The walk steps over a wrapper, its flags, a flag's numeric or
# placeholder value, and VAR=val assignments, and it stops dead at the first
# token that is a real command, so `git commit -m "rm the old file"` can never
# be read as a delete.
#
# `sh -c <string>`, `bash -c <string>` and `eval <words>` are NOT wrappers in
# this sense and must not be added to the list below: their payload is a whole
# command string inside a single argument, not a token of this fragment, so no
# walk over these tokens can reach it. unwrap_shell_c() handles them instead, by
# handing the string back to the fragment splitter.
#
# Known limits, both pre-existing: a command reached through `find -exec` or a
# command substitution (`rm $(cat list)`) is not seen, because neither is a
# wrapper prefix — the fragment's command is `find` / the outer command.
_cmd_idx=-1
# The directory a wrapper option moved the command into (`sudo -D <dir>`,
# `env -C <dir>`, `--chdir=<dir>`), for the caller to resolve relative paths
# against. Set by the walk below, which already has to step over that value to
# reach the command word — it just used to throw it away, so `sudo -D /etc rm
# passwd` was judged as an in-project delete of <project>/passwd while the shell
# removed /etc/passwd.
_cmd_chdir=""
cmd_word_index() {
  local names="$1"; shift
  local -a t=("$@")
  local i tok base flag valflags="" chdirflags="" skip="" skip_is_chdir=""
  _cmd_chdir=""
  for ((i=0; i<${#t[@]}; i++)); do
    tok="${t[i]#\\}"
    base="${tok##*/}"
    # The previous token was a wrapper option that takes its value as a SEPARATE
    # word, so this token is that value and not a command. Consuming it is what
    # the walk was missing: it ended ON the value and reported "runs some other
    # command", which turned BOTH Bash guards off. `sudo rm <outside>` was denied
    # while `sudo -u root rm <outside>` was allowed — and the same one word
    # unguarded `sudo -u root git push origin master`.
    if [[ -n "$skip" ]]; then
      [[ -n "$skip_is_chdir" ]] && _cmd_chdir="${t[i]}"
      skip=""; skip_is_chdir=""; continue
    fi
    case "|$names|" in
      *"|$base|"*) _cmd_idx=$i; return 0 ;;
    esac
    case "$tok" in
      # Wrappers, each with the options that swallow the following word. Listing
      # them per wrapper rather than skipping any bare word after a flag keeps
      # `sudo -u root somecmd rm` from reading as a delete: 'somecmd' still ends
      # the walk.
      #
      # A flag belongs here ONLY if its value is REQUIRED and can arrive as a
      # separate word. A flag whose value is optional or attached-only takes no
      # following word, so listing it consumes the COMMAND — the walk ends on it
      # and reports "runs some other command", which turns both Bash guards off.
      # That is why `i` and `replace` are absent below while `I` is present: GNU
      # spells the required form `-I R` / `--replace=R` but the optional forms
      # `-i[R]` and `--replace[=R]` take nothing, and `xargs -i rm -rf <outside>`
      # — an entirely mainstream spelling — was allowed while a bare `xargs rm`
      # was denied. Same for `--max-lines` / `--eof` (optional) against `-L` /
      # `-E` (required), and for sudo's `-h`, which alone is `--help`.
      # --chroot is a chdir for this purpose: a relative target under it resolves
      # against the new root on the HOST filesystem, which is what the gates judge.
      sudo|doas) valflags="u|user|g|group|p|prompt|r|role|t|type|C|close-from|U|other-user|D|chdir|R|chroot"; chdirflags="D|chdir|R|chroot" ;;
      # -S/--split-string is deliberately NOT listed: it carries a whole command
      # in its value, so consuming it as a flag value ended the walk on the
      # payload and reported "runs some other command", turning both Bash guards
      # off. unwrap_shell_c claims that form before this walk ever runs.
      env) valflags="u|unset|C|chdir"; chdirflags="C|chdir" ;;
      timeout) valflags="s|signal|k|kill-after"; chdirflags="" ;;
      nice) valflags="n|adjustment"; chdirflags="" ;;
      ionice) valflags="c|class|n|classdata|p|pid|P|pgid|u|uid"; chdirflags="" ;;
      stdbuf) valflags="i|input|o|output|e|error"; chdirflags="" ;;
      xargs) valflags="n|max-args|L|I|a|arg-file|d|delimiter|E|P|max-procs|s|max-chars"; chdirflags="" ;;
      command|builtin|exec|nohup|time) valflags=""; chdirflags="" ;;
      -*)
        if [[ "$tok" == *=* ]]; then
          # An '=' carries the value in the same word, so nothing follows it —
          # but a --chdir=<dir> still moves the command, so record it.
          flag="${tok%%=*}"; flag="${flag#-}"; flag="${flag#-}"
          if [[ -n "$flag" && -n "$chdirflags" ]]; then
            case "|$chdirflags|" in *"|$flag|"*) _cmd_chdir="${tok#*=}" ;; esac
          fi
        else
          # A LONG option is one name, matched whole. A SHORT cluster is many
          # one-letter flags, and only the LAST of them can take a separate-word
          # value — so testing the whole post-dash remainder missed every bundled
          # spelling: `-Hu` never matched `u`, and `sudo -Hu root rm <outside>`
          # walked onto 'root', ended there, and lost both guards while the
          # unbundled `sudo -u root` was correctly denied.
          if [[ "$tok" == --?* ]]; then
            flag="${tok#--}"
          else
            flag="${tok#-}"; flag="${flag: -1}"
          fi
          # The emptiness guards matter: '--' strips to "", which would otherwise
          # match the empty valflags of a no-option wrapper and swallow the
          # command word.
          if [[ -n "$flag" && -n "$valflags" ]]; then
            case "|$valflags|" in *"|$flag|"*) skip=1 ;; esac
          fi
          if [[ -n "$flag" && -n "$skip" && -n "$chdirflags" ]]; then
            case "|$chdirflags|" in *"|$flag|"*) skip_is_chdir=1 ;; esac
          fi
        fi
        ;;
      # A VAR=val assignment, and the placeholder / count tokens of an xargs or
      # find invocation — none of them is a command word.
      *=*|'{}'|'%'|[0-9]*) ;;
      *) return 1 ;;
    esac
  done
  return 1
}

# Recognize a redirection token. A redirection names a STREAM, never a path the
# command acts on or a refspec it pushes, and both spellings have to be caught:
# a lone operator ('rm x > /dev/null', 'git push > /dev/null') leaves its target
# in the NEXT word, while a glued one ('>/dev/null', '2>&1') carries it in the
# same word. Left unhandled, the first spelling made '/dev/null' look like a
# delete target — an unappealable deny on one of the most ordinary shell idioms
# there is — and made 'git push' look like it named an explicit refspec, which
# skipped the current-branch resolution and walked straight past the protected
# branch check. Sets _redir_takes_arg when the caller must also skip the next word.
_redir_takes_arg=""
is_redirection() {
  _redir_takes_arg=""
  local w="$1"
  # Drop a leading fd number ('2>', '10>&1') before matching the operator.
  w="${w#"${w%%[!0-9]*}"}"
  case "$w" in
    '>'|'>>'|'<'|'<<'|'<<<'|'>&'|'<&'|'<>'|'&>'|'&>>') _redir_takes_arg=1; return 0 ;;
    '>'*|'<'*|'&>'*) return 0 ;;
  esac
  return 1
}

# Extract the command string carried inside `sh -c <string>` / `bash -c <string>`
# (through any wrapper prefix) or concatenated after `eval`. Result in _unwrapped.
#
# Without this, one wrapper turned BOTH Bash-side guards off at once:
# `sh -c "rm -rf /etc"`, `eval rm /etc/passwd` and `bash -c "git push origin
# master"` all emitted nothing at all. The inner string is a single shell WORD to
# this fragment, so the only way to check it is to split it as a command in its
# own right — which is what the caller does with the result.
_unwrapped=""
unwrap_shell_c() {
  local -a t=("$@")
  local i
  # `env -S '<cmd>'` / `env --split-string=<cmd>` carry a whole command inside one
  # argument exactly as `sh -c` does, so they need the same treatment. Checked
  # BEFORE the shell names and falling through when no payload is found, so
  # `env FOO=bar sh -c '<cmd>'` still reaches the shell branch below.
  if cmd_word_index 'env' "${t[@]}"; then
    for ((i=_cmd_idx + 1; i<${#t[@]}; i++)); do
      case "${t[i]}" in
        -S|--split-string) _unwrapped="${t[i+1]:-}"; [[ -n "$_unwrapped" ]] && return 0 ;;
        --split-string=*)  _unwrapped="${t[i]#--split-string=}"; [[ -n "$_unwrapped" ]] && return 0 ;;
        -S?*)              _unwrapped="${t[i]#-S}"; [[ -n "$_unwrapped" ]] && return 0 ;;
      esac
    done
  fi
  cmd_word_index 'sh|bash|dash|ksh|zsh|eval' "${t[@]}" || return 1
  local base="${t[_cmd_idx]#\\}"; base="${base##*/}"
  local _oldifs flags
  if [[ "$base" == eval ]]; then
    # `eval a b c` joins its words with a space and runs the result.
    (( ${#t[@]} > _cmd_idx + 1 )) || return 1
    _oldifs="$IFS"; IFS=' '; _unwrapped="${t[*]:$((_cmd_idx + 1))}"; IFS="$_oldifs"
    [[ -n "$_unwrapped" ]] || return 1
    return 0
  fi
  # A shell's command string is the argument after -c, which may be bundled with
  # other short flags ('sh -ec', 'bash -lc', 'sh -cx').
  #
  # The bundle has to be tested for the LETTER. `-*c` — matching any flag that
  # merely ends in 'c' — claimed '--norc': it handed back the following token,
  # the literal '-c', as the payload and returned success, so the caller
  # re-scanned the string "-c" and skipped both guards for the real command.
  # `bash --norc -c "rm -rf <outside>"` was allowed while the plain `sh -c`
  # spelling was denied, and 'sh -cx' was missed from the other side: its 'c' is
  # in the bundle but not last.
  for ((i=_cmd_idx + 1; i<${#t[@]}; i++)); do
    case "${t[i]}" in
      # The two long options taking a separate-word value. Left unhandled, the
      # value read as a script path and ended the walk, so `bash --rcfile f -c
      # "<cmd>"` unwrapped nothing at all.
      --rcfile|--init-file) (( ++i )) ;;
      # Every other long option is a switch, and none of them is '-c'.
      --*) ;;
      -?*|+?*)
        flags="${t[i]#[-+]}"
        if [[ "$flags" == *c* ]]; then
          _unwrapped="${t[i+1]:-}"
          [[ -n "$_unwrapped" ]] && return 0
          return 1
        fi
        # '-o <shopt>' takes a separate-word value, like the long options above,
        # and so do '-O <shopt>' and its '+O' off-switch. Matching only lowercase
        # 'o' left the shopt name to be read as a script path, which ended the
        # walk: `bash -O extglob -c "rm -rf <outside>"` unwrapped nothing and lost
        # both guards, while the plain `bash -c` spelling was denied.
        if [[ "$flags" == *[oO] ]]; then (( ++i )); fi
        ;;
      # A bare '-' reads the script from stdin, and any other non-flag argument
      # is a SCRIPT PATH ('bash scripts/build.sh') — neither carries a command
      # string to unwrap.
      *) return 1 ;;
    esac
  done
  return 1
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
  git -C "${1:-$_rp_root}" rev-parse --abbrev-ref HEAD 2>/dev/null
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
      dir="$_rp_root/$dir"
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
  root_repo="$(find_git_root "$_rp_root")"
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
  local i=1 skip_next=""
  while (( i <= $# )); do
    local arg="${!i}"
    if [[ -n "$skip_next" ]]; then skip_next=""; i=$(( i + 1 )); continue; fi
    # A redirection is not a refspec. Counted as one, `git push > /dev/null`
    # reached the branch resolution below with TWO positionals, so it took the
    # 'git push <remote> <refspec>' path and checked '/dev/null' against the
    # protected list instead of resolving the current branch — a push to master
    # one space away from unguarded.
    if is_redirection "$arg"; then
      skip_next="$_redir_takes_arg"
      i=$(( i + 1 )); continue
    fi
    case "$arg" in
      -d|--delete) has_delete=true ;;
      -f|--force|--force-with-lease*|--force-if-includes) ;;
      -u|--set-upstream|--no-verify|--dry-run|-n|--verbose|-v|--quiet|-q) ;;
      --atomic|--signed*|--no-signed|--thin|--no-thin|--tags|--prune) ;;
      --progress|--no-progress|--porcelain|--no-recurse-submodules) ;;
      --push-option|-o|--repo|--receive-pack|--exec) skip_next=1 ;;
      --push-option=*|-o*|--repo=*) ;;
      -*) ;; # unknown flag, skip (fail-open)
      *) positional+=("$arg") ;;
    esac
    i=$(( i + 1 ))
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
      # 'git push origin HEAD' (or '@') pushes the CURRENT branch — resolve it,
      # or a protected branch is reachable by naming it indirectly.
      if [[ "$target" == "HEAD" || "$target" == "@" ]]; then
        target="$(get_current_branch "${git_repo_dir:-}")" || continue
        [[ "$target" == "HEAD" ]] && continue # detached — no branch to protect
      fi
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

# Check one already-split command fragment for git branch protection violations.
# Called with an optional cd directory from a chained command, followed by the
# fragment's words as produced by shell_split.
# Calls deny_operation (exits the script) if blocked; returns 0 if allowed.
check_git_command() {
  local cd_dir="${1:-}"; shift
  local -a tokens=("$@")

  # Detect git through any wrapper prefix (sudo, env VAR=val, command, /usr/bin/git).
  cmd_word_index 'git' "${tokens[@]}" || return 0
  # Re-base the array on the git word so every index below still counts from 'git'.
  local -a _args=()
  (( ${#tokens[@]} > _cmd_idx + 1 )) && _args=("${tokens[@]:$((_cmd_idx + 1))}")
  tokens=(git ${_args[@]+"${_args[@]}"})

  # Rejoin for the '--hard' whole-string check further down. IFS is restored
  # immediately: the callees below run `read`.
  local git_portion _oldifs="$IFS"
  IFS=' '; git_portion="${tokens[*]}"; IFS="$_oldifs"

  # Find git subcommand (skip global flags between 'git' and subcommand)
  local git_subcmd="" git_subcmd_idx=0 git_dir=""
  local i
  for ((i=1; i<${#tokens[@]}; i++)); do
    case "${tokens[i]}" in
      -C) git_dir="${tokens[i+1]:-}"; (( ++i )) ;;          # capture -C target dir
      -c|--git-dir|--work-tree|--namespace) (( ++i )) ;;    # skip flag + its argument
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
      # Two destructive shapes, not one. Keying on the delete flags alone left
      # `git branch -f master HEAD~3` and `git branch -M feat master` free to
      # rewrite a protected branch's pointer — the same loss as a delete, and
      # the one way to do it that the Bash tool never had to ask about.
      #   delete:  -d/-D (also bundled with other short flags, e.g. -Df),
      #            --delete, --force-delete
      #   rewrite: -f/--force (force-create over an existing name), -m/-M/--move
      #            (rename onto one)
      # Read the options from the tokens AFTER the subcommand, splitting short
      # bundles from long names. Regexing the rejoined command instead made the
      # three tests below near-duplicate patterns that then drifted apart: 'c'/'C'
      # were simply missing from the rewrite one, so `git branch -C feature
      # master` overwrote master and was allowed. It also let git's own global
      # options leak in — the '-c' of `git -c user.name=x branch feature` belongs
      # to git, not to branch.
      local bi btok bshort="" blong="|"
      local -a bnames=()
      for ((bi=git_subcmd_idx+1; bi<${#tokens[@]}; bi++)); do
        btok="${tokens[bi]}"
        case "$btok" in
          --*) btok="${btok%%=*}"; blong+="${btok#--}|" ;;
          -?*) bshort+="${btok#-}" ;;
          # Everything else is a branch name. `git branch -d` accepts several,
          # and a rename's OLD name matters as much as its new one.
          *) bnames+=("$btok") ;;
        esac
      done
      local branch_op="" is_move="" is_copy=""
      if [[ "$bshort" == *[dD]* || "$blong" == *"|delete|"* || "$blong" == *"|force-delete|"* ]]; then
        branch_op=delete
      elif [[ "$bshort" == *[fmMcC]* || "$blong" == *"|force|"* \
              || "$blong" == *"|move|"* || "$blong" == *"|copy|"* ]]; then
        branch_op=rewrite
      fi
      [[ -n "$branch_op" ]] || return 0
      if [[ "$bshort" == *[mM]* || "$blong" == *"|move|"* ]]; then is_move=1; fi
      if [[ "$bshort" == *[cC]* || "$blong" == *"|copy|"* ]]; then is_copy=1; fi
      # Which of the branch names does the command WRITE?
      #   -m/-M/--move   rename: the old name is destroyed and the new one
      #                  overwritten, so BOTH matter — and with a single argument
      #                  the name it destroys is the CHECKED-OUT branch, which
      #                  never appears on the command line at all. Every sibling
      #                  arm resolves the current branch; this one did not, so on
      #                  master `git branch -m archived` renamed master out of
      #                  existence and was allowed.
      #   -c/-C/--copy   copy: only the DESTINATION (last) is written; the source
      #                  is read.
      #   -f/--force     force-create: only the NAME (first) is written; the
      #                  start-point after it is read. Without that, creating an
      #                  ordinary feature branch off master ('git branch -f
      #                  feature master') would be denied.
      if [[ "$branch_op" == rewrite ]]; then
        if [[ -n "$is_move" ]]; then
          if (( ${#bnames[@]} == 1 )); then
            current_branch="$(get_current_branch "$git_repo_dir")"
            if [[ -n "$current_branch" && "$current_branch" != "HEAD" ]]; then
              bnames+=("$current_branch")
            fi
          fi
        elif [[ -n "$is_copy" ]]; then
          (( ${#bnames[@]} > 1 )) && bnames=("${bnames[${#bnames[@]}-1]}")
        else
          (( ${#bnames[@]} > 1 )) && bnames=("${bnames[0]}")
        fi
      fi
      local bname
      for bname in ${bnames[@]+"${bnames[@]}"}; do
        bname="${bname#refs/heads/}"
        if is_protected_branch "$bname"; then
          if [[ "$branch_op" == delete ]]; then
            deny_operation "BLOCKED: Cannot delete protected branch '$bname'."
          fi
          deny_operation "BLOCKED: 'git branch' would rewrite protected branch '$bname'. Use a feature branch instead."
        fi
      done
      ;;
    update-ref)
      # `git update-ref refs/heads/master <sha>` moves a branch pointer with no
      # branch subcommand in sight — and it works even on the CHECKED-OUT
      # branch, where 'git branch -f' refuses. Same destruction, different door.
      local ui uref=""
      for ((ui=git_subcmd_idx+1; ui<${#tokens[@]}; ui++)); do
        case "${tokens[ui]}" in
          # --stdin takes the refs on stdin, which this hook cannot read: nothing
          # to check, so fail open as everywhere else.
          --stdin) return 0 ;;
          -m) (( ++ui )) ;;   # reflog message + its argument
          -*) ;;
          *) uref="${tokens[ui]}"; break ;;
        esac
      done
      [[ -n "$uref" ]] || return 0
      if is_protected_branch "${uref#refs/heads/}"; then
        deny_operation "BLOCKED: 'git update-ref' would rewrite protected branch '${uref#refs/heads/}'."
      fi
      ;;
  esac
  return 0
}

# --- Command scanning (see header: COMMAND PARSING) ---
# Walk ONE command string: split it on the shell's operators, then run both
# Bash-side guards over every fragment. Recurses, depth-bounded, into the command
# string carried by `sh -c` / `bash -c` / `eval`.
#
# 'cd <dir>' targets are tracked here because two guards need them: git context
# in multi-repo workspaces, where Claude Code writes "cd <repo> && git ...", and
# the base a RELATIVE delete target resolves against. _cd_dir is deliberately a
# global — a cd persists across the operator that follows it, and into a nested
# `sh -c`, exactly as it does for the shell.
_cd_dir=""
# Where `cd -` goes, and what `popd` pops. Tracking them is what lets the two
# spellings be resolved instead of guessed: the guess was "the project root",
# which is wrong for every chain that moved more than once.
_cd_prev=""
_cd_dirstack=()
_scan_depth=0

# Restore the `cd` that was in force before a subshell which has now CLOSED.
# Reads the paren bookkeeping declared local in scan_command_string, the way
# check_git_push reads git_repo_dir — so a nested `sh -c` scan pushes and pops
# its own parens instead of unwinding its caller's.
cd_pop_closed() {
  while (( _cd_pending_close > 0 )); do
    _cd_pending_close=$(( _cd_pending_close - 1 ))
    (( _cd_depth > 0 )) || continue
    _cd_depth=$(( _cd_depth - 1 ))
    _cd_dir="${_cd_stack[_cd_depth]}"
  done
}

# Count the parens in ONE fragment that close a subshell opened OUTSIDE it.
# Result in _frag_closes.
#
# Testing whether the fragment ENDS in ')' was wrong in both directions. It
# over-counted, because the ')' of a command substitution ends a fragment too:
# in `(cd /etc && echo $(date) && rm passwd)` the ` echo $(date) ` fragment
# banked a close, the deferred pop restored the pre-subshell directory, and the
# `rm passwd` still inside that subshell was judged against the project root
# while the shell deleted /etc/passwd. And it under-counted, because a real
# close need not be last: `(cd /etc && ls) 2>&1 && rm -rf build` ends in
# '2>&1', so no close was banked, /etc stayed in force, and an ordinary
# in-project cleanup was hard-DENIED with no way to override it.
#
# So: walk the fragment, skip quoted runs, and treat every '(' as opening a
# depth — which is exactly what makes '$(', '$((', '<(' and '>(' self-cancelling
# — counting only the ')' that runs out of depth.
_frag_closes=0
count_frag_closes() {
  # Byte semantics, for the same reason shell_split pins them: a UTF-8
  # continuation byte can never equal one of the ASCII delimiters below.
  local LC_ALL=C
  local s="$1"
  local n=${#s} i=0 c q="" depth=0
  _frag_closes=0
  while (( i < n )); do
    c="${s:i:1}"
    if [[ "$q" == "'" ]]; then
      [[ "$c" == "'" ]] && q=""
    elif [[ "$q" == '"' ]]; then
      if [[ "$c" == '\' ]]; then (( ++i ))
      elif [[ "$c" == '"' ]]; then q=""; fi
    else
      case "$c" in
        "'"|'"') q="$c" ;;
        '\') (( ++i )) ;;
        '(') depth=$(( depth + 1 )) ;;
        ')')
          if (( depth > 0 )); then depth=$(( depth - 1 ))
          else _frag_closes=$(( _frag_closes + 1 )); fi
          ;;
      esac
    fi
    (( ++i ))
  done
}

scan_command_string() {
  local _split="$1"
  local _subcmd _cd_tok _cd_target _cd_base _cd_noop word target nword skip_next
  local _saved_cd _saved_prev _wrap_base _wrap_cd _eff_cd _n_close
  local -a _frag
  local -a _saved_stack=()
  local -a _cd_stack=()
  local _cd_depth=0 _cd_pending_close=0

  # A backslash-newline is a LINE CONTINUATION, not a command separator: the
  # shell joins the two lines and runs ONE command. Splitting on the newline
  # first chopped
  #     rm -rf \
  #     <outside>
  # into a flagless `rm` and a bare path — the first has no argument the gate
  # looks at, the second has no command word — so neither half tripped the
  # delete gate while the shell went ahead and deleted. Join before splitting.
  _split="${_split//\\$'\n'/}"

  # Pure bash, and '&' is one of the operators. The `sed 's/&&/\n/g; ...'` this
  # replaces emitted no newline for a LONE '&', so `true & rm <outside>` stayed
  # a single fragment that no anchored guard matched — both hard blocks were
  # one background operator away from being no-ops. (It also relied on GNU
  # sed's \n in a replacement, which inserts a literal 'n' on macOS/BSD, and
  # forked a process per command.)
  _split="${_split//&&/$'\n'}"
  _split="${_split//||/$'\n'}"
  _split="${_split//;/$'\n'}"
  _split="${_split//|/$'\n'}"
  _split="${_split//&/$'\n'}"

  while IFS= read -r _subcmd; do
    # Apply any subshell close seen on the PREVIOUS fragment. Deferred by one
    # fragment on purpose: the ')' arrives glued to the subshell's own last
    # command, which still has to be judged against the cd that was in force
    # inside it.
    cd_pop_closed
    _subcmd="${_subcmd#"${_subcmd%%[![:space:]]*}"}"  # trim leading whitespace
    # Trailing whitespace too, and after each ')' below: the operator split
    # leaves a space in front of the next fragment, so ' ./deploy.sh) ' ends in a
    # SPACE and the close would go uncounted.
    _subcmd="${_subcmd%"${_subcmd##*[![:space:]]}"}"
    # Count the subshell parens rather than only stripping them — the count is
    # what scopes a `cd` to its subshell. Without it the cd in
    # `(cd /tmp && ./deploy.sh) && rm -rf build` stayed in force for the rest of
    # the chain, and an ordinary in-project cleanup resolved to /tmp/build and
    # was hard-DENIED.
    while [[ "$_subcmd" == '('* ]]; do
      _subcmd="${_subcmd#\(}"
      _subcmd="${_subcmd#"${_subcmd%%[![:space:]]*}"}"
      _cd_stack[_cd_depth]="$_cd_dir"
      _cd_depth=$(( _cd_depth + 1 ))
    done
    count_frag_closes "$_subcmd"
    _cd_pending_close=$(( _cd_pending_close + _frag_closes ))
    # Strip only as many trailing ')' as there are real closes, so the command
    # word stays reachable without eating the ')' of a `$(...)` target. A close
    # that is NOT last (a redirection follows it) keeps its paren glued to the
    # word; that costs a stray character in the deny message, never a verdict,
    # because the paren is on the far side of the path either way.
    _n_close=$_frag_closes
    while (( _n_close > 0 )) && [[ "$_subcmd" == *')' ]]; do
      _subcmd="${_subcmd%\)}"
      _subcmd="${_subcmd%"${_subcmd##*[![:space:]]}"}"
      _n_close=$(( _n_close - 1 ))
    done

    # Peel leading shell keywords. `for f in *; do rm <outside>; done` splits
    # into a fragment beginning 'do rm ...' and `if x; then rm <outside>; fi`
    # into one beginning 'then rm ...' — neither of which the guards below saw,
    # so a loop or an if was enough to walk both of them past an unwanted delete
    # and past the protected-branch check.
    # A case ARM and a function BODY leave the command behind punctuation rather
    # than behind a keyword, so neither was peeled: `case x in y) rm <outside>;;
    # esac` and `f() { rm <outside>; }` both left a first token that is not a
    # command word, cmd_word_index bailed, and every guard below was skipped. A
    # generated `cleanup() { rm -rf "$BUILD"; }` is an accident shape, not only
    # an adversarial one. Peeling only ever exposes MORE to the guards.
    while :; do
      case "$_subcmd" in
        do|then|else|elif|fi|done|esac|in|'{'|'}'|'!') _subcmd="" ;;
        do\ *|then\ *|else\ *|elif\ *|if\ *|while\ *|until\ *|'{'\ *|'!'\ *)
          _subcmd="${_subcmd#* }" ;;
        *'()'*'{'*) _subcmd="${_subcmd#*\{}" ;;
        case\ *')'*) _subcmd="${_subcmd#*\)}" ;;
        *) break ;;
      esac
      _subcmd="${_subcmd#"${_subcmd%%[![:space:]]*}"}"
      [[ -n "$_subcmd" ]] || break
    done
    [[ -n "$_subcmd" ]] || continue

    # One quote-aware split per fragment, shared by all the gates below.
    shell_split "$_subcmd"
    (( ${#_words[@]} )) || continue
    _frag=("${_words[@]}")

    # Track 'cd <dir>' to resolve context for subsequent commands — through a
    # wrapper prefix, like every other command word here. Matching a bare first
    # token was the only spelling recognized, so `builtin cd /etc && rm passwd`
    # judged 'passwd' as an in-project path while the shell removed /etc/passwd.
    if cmd_word_index 'cd|pushd|popd' "${_frag[@]}"; then
      _cd_base="${_frag[_cmd_idx]##*/}"
      _cd_target=""
      _cd_noop=""
      for _cd_tok in "${_frag[@]:$((_cmd_idx + 1))}"; do
        case "$_cd_tok" in
          '') continue ;;
          # `pushd -n <dir>` pushes WITHOUT changing directory — that is the
          # entire purpose of the flag — and `popd -n` pops without moving.
          # Reading the operand as a cd turned an ordinary in-project delete
          # after `pushd -n <elsewhere>` into an unappealable DENY.
          -n) _cd_noop=1; continue ;;
          # A '+N' / '-N' operand ROTATES the stack to an entry this hook never
          # saw. It is not a directory: composing it produced the nonsense base
          # '<project>/+1'.
          +[0-9]*|-[0-9]*) _cd_noop=1; continue ;;
          # A lone '-' is cd's OPERAND, not a flag. Letting the '-*' arm below
          # swallow it left no target at all, which reads as a bare `cd`.
          -) _cd_target="-"; break ;;
          -*) continue ;;
        esac
        _cd_target="$_cd_tok"
        break
      done
      # Each arm below answers ONE question: where is the shell standing after
      # this word? Answering "the project root" for every spelling the hook
      # could not resolve was the bug — `popd` with an empty stack, a bare `cd`
      # and `cd -P` do not go there, so a following relative `rm` was judged
      # in-project while the shell deleted outside it.
      if [[ -n "$_cd_noop" ]]; then
        :                       # the shell did not move
      elif [[ "$_cd_base" == popd ]]; then
        # popd returns to what pushd saved. With an EMPTY stack popd fails and
        # the shell stays exactly where it was: `cd /etc && popd && rm passwd`
        # removed /etc/passwd while the hook read it as <project>/passwd.
        if (( ${#_cd_dirstack[@]} > 0 )); then
          _cd_prev="$_cd_dir"
          _cd_dir="${_cd_dirstack[${#_cd_dirstack[@]}-1]}"
          unset "_cd_dirstack[${#_cd_dirstack[@]}-1]"
        fi
      elif [[ "$_cd_target" == - ]]; then
        # `cd -` returns to the PREVIOUS directory, which is only the project
        # root when the chain moved exactly once: after `cd /etc && cd /var`
        # it lands back in /etc.
        _cd_tok="$_cd_dir"; _cd_dir="$_cd_prev"; _cd_prev="$_cd_tok"
      elif [[ -z "$_cd_target" ]]; then
        if [[ "$_cd_base" == pushd ]]; then
          :                     # bare pushd swaps the top two — unresolvable
        else
          # A bare `cd`, `cd --` or `cd -P` goes HOME.
          _cd_prev="$_cd_dir"
          _cd_dir="${HOME:-$_cd_dir}"
        fi
      elif is_absolute_path "$_cd_target"; then
        [[ "$_cd_base" == pushd ]] && _cd_dirstack+=("$_cd_dir")
        _cd_prev="$_cd_dir"
        _cd_dir="$_cd_target"
      else
        [[ "$_cd_base" == pushd ]] && _cd_dirstack+=("$_cd_dir")
        _cd_prev="$_cd_dir"
        # COMPOSE, never replace. Replacing re-based every later relative target
        # on the LAST cd alone, so a chain that walked back out
        # (`cd frontend && npm run build && cd .. && rm -rf frontend/dist`) left
        # '..' as the base and resolved the delete outside the project — an
        # unappealable deny on an ordinary cleanup. normalize() collapses the
        # dot segments when the target is finally built.
        _cd_dir="${_cd_dir:+$_cd_dir/}$_cd_target"
      fi
      continue
    fi

    # A wrapper option can move the command without any `cd` in sight
    # (`sudo -D <dir>`, `env -C <dir>`, `--chdir=<dir>`). The walk above already
    # stepped over that value to reach the command word, so take it from there —
    # read BEFORE the walks below, each of which starts its own. It applies to
    # THIS fragment only: the wrapper chdirs the process it spawns, not the
    # shell, so nothing after the fragment inherits it.
    _wrap_cd="$_cmd_chdir"
    _eff_cd="$_cd_dir"
    if [[ -n "$_wrap_cd" ]]; then
      if is_absolute_path "$_wrap_cd"; then
        _eff_cd="$_wrap_cd"
      else
        _eff_cd="${_cd_dir:+$_cd_dir/}$_wrap_cd"
      fi
    fi

    # `sh -c <string>` / `bash -c <string>` / `eval <words>` carry a whole
    # command inside ONE argument, which no walk over these tokens can reach —
    # so a single wrapper switched BOTH guards off at once. Hand the string back
    # to this function instead. Depth-bounded so a self-referential command
    # (`sh -c "sh -c ..."`) cannot spin, and shallow because real commands nest
    # once, if at all.
    if unwrap_shell_c "${_frag[@]}"; then
      _wrap_base="${_frag[_cmd_idx]#\\}"; _wrap_base="${_wrap_base##*/}"
      _saved_cd="$_cd_dir"
      _saved_prev="$_cd_prev"
      _saved_stack=(${_cd_dirstack[@]+"${_cd_dirstack[@]}"})
      _cd_dir="$_eff_cd"
      if (( _scan_depth < 4 )); then
        _scan_depth=$(( _scan_depth + 1 ))
        scan_command_string "$_unwrapped"
        _scan_depth=$(( _scan_depth - 1 ))
      fi
      # A `cd` inside `sh -c` runs in a CHILD shell and dies with it, so it must
      # not re-base the fragments that follow — the same reason the paren stack
      # restores after a subshell, and the same unappealable deny it produced:
      # `bash -c "cd /var" ; rm -rf dist` blocked an in-project cleanup because
      # _cd_dir is global and the recursion left the child's cd in force. The
      # directory stack and the `cd -` target die with that child too. `eval` is
      # the exception — it runs in the CURRENT shell, so its cd genuinely
      # composes and must survive.
      if [[ "$_wrap_base" != eval ]]; then
        _cd_dir="$_saved_cd"
        _cd_prev="$_saved_prev"
        _cd_dirstack=(${_saved_stack[@]+"${_saved_stack[@]}"})
      fi
      continue
    fi

    # Git branch protection (feature branches allowed, protected branches blocked)
    check_git_command "$_eff_cd" "${_frag[@]}"

    # Delete protection (rm/rmdir outside project or precious unversioned).
    # cmd_word_index sees through wrapper prefixes — a pipe hands the post-'|'
    # fragment here on its own, so `find ... | xargs -n 1 rm <path>` and
    # `sudo rm <path>` have to be recognized as deletes just like a bare `rm`.
    if cmd_word_index 'rm|rmdir' "${_frag[@]}"; then
      skip_next=""
      for word in "${_frag[@]:$((_cmd_idx + 1))}"; do
        if [[ -n "$skip_next" ]]; then skip_next=""; continue; fi
        # Flags, and the placeholder/terminator tokens of an xargs or find
        # invocation — none of them name a file.
        case "$word" in -*|'{}'|'+'|';'|'') continue ;; esac
        # Neither does a redirection: `rm <in-project> > /dev/null` was denied
        # for deleting '/dev/null', with no prompt and no way to override it.
        if is_redirection "$word"; then skip_next="$_redir_takes_arg"; continue; fi
        # A word whose FIRST character is expansion syntax this hook does not
        # perform is not a safe relative path — it is an absolute target in
        # disguise. `rm $'/etc/passwd'`, `rm {,}/etc/passwd` and
        # `rm ~root/.ssh/id_rsa` each kept their leading '/' inside syntax
        # expand_word leaves alone, so is_absolute_path answered "relative",
        # normalize() re-based the word on the project root, and BOTH the
        # out-of-project block and the precious-file block were skipped — three
        # characters were enough to strip protection off an untracked .env. Ask
        # rather than deny: unresolvable is not the same as hostile, and an ask
        # is appealable.
        #
        # Anchored at the START on purpose, and tested BEFORE the word is
        # resolved. Only a LEADING expansion can hide the root: brace expansion
        # and $-expansion both keep whatever precedes them, so `build/{a,b}` and
        # `build/$(date)` yield relative words no matter what they expand to.
        # Matching them anywhere in the word did two wrong things at once — it
        # prompted on ordinary in-project cleanups like `rm -rf dist/{js,css}`,
        # and it DOWNGRADED settled hard denies, because `rm -rf /etc/$(whoami)`
        # is already absolute and already outside: asking there hands back a
        # bypass the deny below had closed.
        #
        # A bare unresolved $VAR keeps its documented fail-open (see
        # expand_word): it is the ordinary `rm -rf $BUILD_DIR/x` shape, and
        # denying that made build-dir cleanup impossible. The split is on what
        # FOLLOWS the '$'. shell_split strips the quotes of $'...', so the word
        # arrives as `$/etc/passwd` — a '$' followed by something that cannot
        # begin a variable name, which no ordinary $VAR or ${VAR} ever produces.
        if ! is_absolute_path "$word"; then
          case "$word" in
            \$\'*|'$'[!A-Za-z_{]*|'~'[!/]*|'{'*,*'}'*)
              ask_permission "Delete target '$word' carries a shell expansion this hook cannot resolve. Allow this delete?" ;;
          esac
        fi
        # Resolve a RELATIVE target against the chain's `cd`, not against this
        # hook's own working directory. `cd /etc && rm passwd` otherwise
        # normalized to <project>/passwd and read as an IN-project delete, while
        # the shell removed /etc/passwd — the tracked cd was right there, it
        # just never reached this gate. A relative cd resolves against the
        # project root, as it does in resolve_git_context.
        target="$word"
        if [[ -n "$_eff_cd" ]] && ! is_absolute_path "$target"; then
          if is_absolute_path "$_eff_cd"; then
            target="$_eff_cd/$target"
          else
            target="$_rp_root/$_eff_cd/$target"
          fi
        fi
        # Claude's own auto-memory store and session scratchpad are writable AND
        # prunable by design, so deletes there are allowed like writes — via the
        # SAME ladder the write gate uses. Everything else outside the project
        # root is hard-blocked. Normalize once and reuse: the two gates below
        # would otherwise resolve the same word twice, two forks apiece.
        nword="$(normalize "$target")"
        if ! is_exempt_out_of_project_n "$nword"; then
          deny_operation "BLOCKED: Cannot delete '$word' — outside project root."
        fi
        # Precious file protection: block deletion of sensitive unversioned files.
        # Recoverable ones (backups, IDE scratch) are excluded by is_hard_precious
        # testing the hard list alone — a deny here could never be overridden.
        if [[ -e "$target" ]] && is_inside_project_n "$nword" \
           && is_hard_precious "$target" && ! is_git_tracked "$target"; then
          deny_operation "BLOCKED: '$(basename "$word")' is a precious file not tracked by git. Deletion denied."
        fi
      done
    fi
  done <<< "$_split"
  # A subshell that closed on the LAST fragment has no next iteration to unwind
  # it, and _cd_dir is global — it would leak past the end of this scan.
  cd_pop_closed
  return 0
}

# --- Extract tool_name ---
# Fail-open: if tool_name cannot be extracted, allow rather than block
[[ "$_rp_input" =~ \"tool_name\"[[:space:]]*:[[:space:]]*\"([^\"]+)\" ]] || exit 0
_rp_tool_name="${BASH_REMATCH[1]}"

case "$_rp_tool_name" in
  Edit|MultiEdit|Write)
    # Fail-open: if file_path cannot be extracted, allow rather than block.
    # The value is a JSON string: walk over escaped quotes ([^"\]|\\.) as the
    # Bash branch does — stopping at the first \" judged only the path's prefix.
    _rp_path_re='"file_path"[[:space:]]*:[[:space:]]*"(([^"\]|\\.)*)"'
    [[ "$_rp_input" =~ $_rp_path_re ]] || exit 0
    filepath="${BASH_REMATCH[1]}"
    # Undo the JSON escapes the same way the Bash branch does, so a path that
    # contains an escaped quote is judged whole rather than on its prefix.
    filepath="${filepath//\\\\/$'\001'}"
    filepath="${filepath//\\\"/\"}"
    filepath="${filepath//\\\//\/}"
    filepath="${filepath//\\n/$'\n'}"
    filepath="${filepath//\\r/$'\r'}"
    filepath="${filepath//\\t/$'\t'}"
    filepath="${filepath//$'\001'/\\}"
    guard_out_of_project_write "$filepath" "File" "write"
    # Precious file protection: prompt before modifying sensitive unversioned files
    if [[ -e "$filepath" ]] && is_precious "$filepath" && ! is_git_tracked "$filepath"; then
      ask_permission "File '$(basename "$filepath")' is a precious file not tracked by git. Changes may be permanent. Allow this write?"
    fi
    exit 0
    ;;
  NotebookEdit)
    # Fail-open: if notebook_path cannot be extracted, allow rather than block
    _rp_path_re='"notebook_path"[[:space:]]*:[[:space:]]*"(([^"\]|\\.)*)"'
    [[ "$_rp_input" =~ $_rp_path_re ]] || exit 0
    filepath="${BASH_REMATCH[1]}"
    # Undo the JSON escapes the same way the Bash branch does, so a path that
    # contains an escaped quote is judged whole rather than on its prefix.
    filepath="${filepath//\\\\/$'\001'}"
    filepath="${filepath//\\\"/\"}"
    filepath="${filepath//\\\//\/}"
    filepath="${filepath//\\n/$'\n'}"
    filepath="${filepath//\\r/$'\r'}"
    filepath="${filepath//\\t/$'\t'}"
    filepath="${filepath//$'\001'/\\}"
    guard_out_of_project_write "$filepath" "Notebook" "edit"
    # Precious file protection: prompt before modifying sensitive unversioned notebooks
    if [[ -e "$filepath" ]] && is_precious "$filepath" && ! is_git_tracked "$filepath"; then
      ask_permission "File '$(basename "$filepath")' is a precious file not tracked by git. Changes may be permanent. Allow this edit?"
    fi
    exit 0
    ;;
  Bash)
    # Fail-open: if command cannot be extracted, allow rather than block.
    # The value is a JSON string, so the match must walk over escaped quotes
    # ([^"\]|\\.) — stopping at the first \" truncated the command and silently
    # skipped every guard for anything as ordinary as `git commit -m "msg"`.
    _bash_cmd_re='"command"[[:space:]]*:[[:space:]]*"(([^"\]|\\.)*)"'
    [[ "$_rp_input" =~ $_bash_cmd_re ]] || exit 0
    _rp_cmd="${BASH_REMATCH[1]}"
    # Undo the JSON escapes so the guards see what the shell will run. \001
    # shields literal backslashes from the later passes; cmd never reaches the
    # emitted JSON, so the sentinel cannot leak into output.
    _rp_cmd="${_rp_cmd//\\\\/$'\001'}"
    _rp_cmd="${_rp_cmd//\\\"/\"}"
    _rp_cmd="${_rp_cmd//\\\//\/}"
    _rp_cmd="${_rp_cmd//\\n/$'\n'}"
    _rp_cmd="${_rp_cmd//\\r/$'\r'}"
    _rp_cmd="${_rp_cmd//\\t/$'\t'}"
    _rp_cmd="${_rp_cmd//$'\001'/\\}"

    # --- Environment snapshot for expand_word (see lookup_env_value) ---
    # Taken HERE, at top level, because this is the only scope where the names in
    # play are the environment's own: read from inside expand_word, an indirect
    # expansion sees that function's locals and every caller's first. Taken in the
    # Bash branch only, so the Edit/Write path — which never splits a command —
    # keeps paying no forks at all.
    #
    # Top level is necessary but not sufficient: `${!_env_name}` still resolves
    # against this script's own globals, so an exported name matching one of them
    # was captured with the HOOK's value. That is why every global here is
    # `_rp_`-prefixed (see the top of the file) — no environment variable a user
    # exports can collide with a name in that namespace.
    #
    # Skipped entirely for a command with no '$' in it. `$(compgen -e)` is a
    # command substitution — a fork — and this is the synchronous PreToolUse path
    # of EVERY Bash tool call, including the overwhelming majority that never
    # expand anything: measured at ~34 ms per call against 0.8 ms for the builtin
    # without the subshell, on the platform whose fork cost is the stated reason
    # the rest of this file trades sed and head for shell builtins. The gate is
    # sound because it is the SAME condition expand_word's lookup loop is written
    # on (`while [[ "$w" == *'$'* ]]`): with no '$' anywhere in the command, no
    # word can reach a lookup, so an empty snapshot changes no decision. (A
    # leading '~' does not need it either — that arm reads $HOME directly.)
    if [[ "$_rp_cmd" == *'$'* ]]; then
      while IFS= read -r _env_name; do
        [[ "$_env_name" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]] || continue
        _env_keys+=("$_env_name")
        _env_vals+=("${!_env_name}")
      done <<< "$(compgen -e 2>/dev/null)"
      # A bash built without programmable completion has no `compgen`. Fall back
      # to the names the gates actually depend on rather than expanding nothing,
      # which would quietly unblock `rm $HOME/.ssh/id_rsa`.
      if (( ${#_env_keys[@]} == 0 )); then
        for _env_name in HOME USERPROFILE TMPDIR TEMP TMP CLAUDE_PROJECT_DIR; do
          [[ -n "${!_env_name+set}" ]] || continue
          _env_keys+=("$_env_name")
          _env_vals+=("${!_env_name}")
        done
      fi
    fi

    # --- Git branch protection + Delete protection ---
    # Both live in scan_command_string, which splits the string on the shell's
    # operators and checks each fragment — so chained commands like
    # "cd /repo && git commit" and "cd /tmp && rm file" are covered, as is a
    # command nested inside `sh -c`.
    scan_command_string "$_rp_cmd"
    exit 0
    ;;
  *)
    exit 0
    ;;
esac
