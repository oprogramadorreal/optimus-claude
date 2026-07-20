#!/usr/bin/env bash
# Unit tests for plugin hooks (session-start and formatter hooks).
# These are the only executable code in the plugin — they run on user machines.
# Run: bash scripts/test-hooks.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SESSION_START="$PLUGIN_ROOT/hooks/session-start"

errors=0
pass=0
tmpdir=""
rp_tmp=""
trap 'for _d in "$tmpdir" "$rp_tmp"; do [ -n "$_d" ] && [ -d "$_d" ] && rm -rf "$_d"; done' EXIT

# --- Helpers ---

setup_fixture() {
  tmpdir=$(mktemp -d)
  cd "$tmpdir"
  git init -q .
  git config user.email "test@test.com"
  git config user.name "Test"
  # Create a dummy commit so git log works
  git commit --allow-empty -m "initial" -q
}

cleanup_fixture() {
  if [ -n "$tmpdir" ] && [ -d "$tmpdir" ]; then
    rm -rf "$tmpdir"
  fi
  tmpdir=""
}

assert_output_contains() {
  local label="$1"
  local expected="$2"
  local actual="$3"
  if echo "$actual" | grep -qF "$expected"; then
    printf "  PASS  %s\n" "$label"
    ((pass++)) || true
  else
    printf "  FAIL  %s (expected to contain: %s)\n" "$label" "$expected"
    ((errors++)) || true
  fi
}

assert_output_empty() {
  local label="$1"
  local actual="$2"
  if [ -z "$actual" ]; then
    printf "  PASS  %s\n" "$label"
    ((pass++)) || true
  else
    printf "  FAIL  %s (expected empty, got: %s)\n" "$label" "$actual"
    ((errors++)) || true
  fi
}

assert_output_not_contains() {
  local label="$1"
  local unexpected="$2"
  local actual="$3"
  if ! echo "$actual" | grep -qF "$unexpected"; then
    printf "  PASS  %s\n" "$label"
    ((pass++)) || true
  else
    printf "  FAIL  %s (should NOT contain: %s)\n" "$label" "$unexpected"
    ((errors++)) || true
  fi
}

# Capture the hook's stdout and exit status separately. The bare
# `output=$(bash "$SESSION_START" || true)` form discards the status, so a hook
# that aborts (it runs under `set -euo pipefail`, and a find that errors would
# kill it) emits no output and every assert_output_empty below still passes.
run_session_start() {
  set +e
  output=$(bash "$SESSION_START" 2>/dev/null)
  hook_status=$?
  set -e
}

assert_exit_zero() {
  local label="$1"
  local status="$2"
  if [ "$status" -eq 0 ]; then
    printf "  PASS  %s\n" "$label"
    ((pass++)) || true
  else
    printf "  FAIL  %s (hook exited %s, expected 0)\n" "$label" "$status"
    ((errors++)) || true
  fi
}

echo "=== optimus-claude hook tests ==="
echo

# ============================================================
# Session-start hook tests
# ============================================================
echo "[session-start: uninitialized project]"
setup_fixture
run_session_start
assert_output_contains "Recommends /optimus:init when no .claude/" "/optimus:init" "$output"
assert_output_contains "Mentions CLAUDE.md" "CLAUDE.md" "$output"
cleanup_fixture

echo "[session-start: partially initialized (CLAUDE.md only)]"
setup_fixture
mkdir -p .claude
echo "# Project" > .claude/CLAUDE.md
run_session_start
assert_output_contains "Still recommends init when coding-guidelines missing" "/optimus:init" "$output"
cleanup_fixture

echo "[session-start: init done, no testing docs]"
setup_fixture
mkdir -p .claude/docs
echo "# Project" > .claude/CLAUDE.md
echo "# Guidelines" > .claude/docs/coding-guidelines.md
run_session_start
assert_output_contains "Suggests re-running init when testing.md missing" "/optimus:init" "$output"
assert_output_not_contains "Does not suggest unit-test for missing testing docs" "/optimus:unit-test" "$output"
cleanup_fixture

echo "[session-start: fully configured, clean tree]"
setup_fixture
mkdir -p .claude/docs
echo "# Project" > .claude/CLAUDE.md
echo "# Guidelines" > .claude/docs/coding-guidelines.md
echo "# Testing" > .claude/docs/testing.md
# Stage and commit everything so the working tree is clean
git add -A && git commit -q -m "setup"
run_session_start
assert_output_empty "Zero output when fully configured and clean" "$output"
# Empty output is the expected result here, so it cannot distinguish "correctly
# silent" from "crashed before printing" — pin the exit status explicitly.
assert_exit_zero "Exits 0 when fully configured and clean" "$hook_status"
cleanup_fixture

echo "[session-start: fully configured, uncommitted changes]"
setup_fixture
mkdir -p .claude/docs
echo "# Project" > .claude/CLAUDE.md
echo "# Guidelines" > .claude/docs/coding-guidelines.md
echo "# Testing" > .claude/docs/testing.md
git add -A && git commit -q -m "setup"
# Create uncommitted change — git state is Claude Code's own gitStatus job, not the hook's
echo "new content" > dirty-file.txt
run_session_start
assert_output_empty "Stays silent on dirty tree (native gitStatus covers git state)" "$output"
assert_exit_zero "Exits 0 on a dirty tree" "$hook_status"
cleanup_fixture

echo "[session-start: multi-repo workspace, marker in one sub-repo]"
setup_fixture
mkdir -p sub-a/.claude
echo "1.64.2" > sub-a/.claude/.optimus-version
run_session_start
assert_output_not_contains "Suppresses init notice when sub-repo carries .optimus-version" "/optimus:init" "$output"
assert_exit_zero "Exits 0 when sub-repo carries .optimus-version" "$hook_status"
cleanup_fixture

echo "[session-start: multi-repo workspace, markers at different depths]"
setup_fixture
mkdir -p sub-a/.claude
mkdir -p sub-b/nested/.claude
echo "1.64.2" > sub-a/.claude/.optimus-version
echo "1.64.2" > sub-b/nested/.claude/.optimus-version
run_session_start
assert_output_not_contains "Suppresses init notice when markers are nested at depth 4" "/optimus:init" "$output"
assert_exit_zero "Exits 0 when markers are nested at depth 4" "$hook_status"
cleanup_fixture

echo "[session-start: workspace root with settings only, marker in sub-repo (mirrors audaces/isa)]"
setup_fixture
mkdir -p .claude
echo "{}" > .claude/settings.json
echo "# Workspace" > CLAUDE.md
mkdir -p sub/.claude
echo "1.64.2" > sub/.claude/.optimus-version
run_session_start
assert_output_not_contains "Suppresses init notice in audaces/isa-style layout" "/optimus:init" "$output"
assert_exit_zero "Exits 0 in audaces/isa-style layout" "$hook_status"
cleanup_fixture

echo "[session-start: no markers anywhere — regression for clean dir]"
setup_fixture
run_session_start
assert_output_contains "Still recommends init when no marker exists in workspace" "/optimus:init" "$output"
cleanup_fixture

echo "[session-start: marker beyond maxdepth]"
setup_fixture
mkdir -p a/b/c/d/.claude
echo "1.64.2" > a/b/c/d/.claude/.optimus-version
run_session_start
assert_output_contains "Recommends init when marker is deeper than maxdepth 4" "/optimus:init" "$output"
cleanup_fixture

# The find prunes node_modules/ and .git/ so a vendored marker cannot be mistaken
# for the workspace's own. A `-mindepth 2` here would suppress the prune at depth
# 1, letting a published package's .claude/.optimus-version (depth 4, inside
# maxdepth) silently cancel the init notice — and walk all of node_modules on
# every session start.
echo "[session-start: vendored marker inside root node_modules]"
setup_fixture
mkdir -p node_modules/some-pkg/.claude
echo "1.64.2" > node_modules/some-pkg/.claude/.optimus-version
run_session_start
assert_output_contains "Ignores .optimus-version vendored in root node_modules" "/optimus:init" "$output"
assert_exit_zero "Exits 0 with a root node_modules present" "$hook_status"
cleanup_fixture

echo "[session-start: marker inside root .git]"
setup_fixture
mkdir -p .git/vendored/.claude
echo "1.64.2" > .git/vendored/.claude/.optimus-version
run_session_start
assert_output_contains "Ignores .optimus-version inside root .git" "/optimus:init" "$output"
cleanup_fixture

# ============================================================
# Formatter hook tests (conditional on tool availability)
# ============================================================
echo
echo "[formatter hooks: shell-based hooks parse JSON input correctly]"
setup_fixture
# Test with format-rust.sh (representative of all bash-based hooks)
# Create a dummy rustfmt that just succeeds
mkdir -p bin
cat > bin/rustfmt <<'MOCK'
#!/usr/bin/env bash
exit 0
MOCK
chmod +x bin/rustfmt
export PATH="$tmpdir/bin:$PATH"

echo "fn main() {}" > test.rs
exit_code=0
output=$(echo '{"tool_input":{"file_path":"test.rs"}}' | bash "$PLUGIN_ROOT/skills/init/templates/hooks/format-rust.sh" 2>&1) || exit_code=$?
# Hook should exit 0 (no error output) for a .rs file
if [ $exit_code -eq 0 ] && [ -z "$output" ]; then
  printf "  PASS  Rust hook processes .rs file without error\n"
  ((pass++)) || true
else
  printf "  FAIL  Rust hook error: %s\n" "$output"
  ((errors++)) || true
fi

# Test that non-.rs file is skipped
echo "hello" > test.txt
output=$(echo '{"tool_input":{"file_path":"test.txt"}}' | bash "$PLUGIN_ROOT/skills/init/templates/hooks/format-rust.sh" 2>&1 || true)
assert_output_empty "Rust hook skips non-.rs file" "$output"
cleanup_fixture

echo "[formatter hooks: node hook parses JSON input correctly]"
if command -v node &>/dev/null; then
  setup_fixture
  # Create a dummy prettier that just succeeds
  mkdir -p node_modules/.bin
  cat > node_modules/.bin/prettier <<'MOCK'
#!/usr/bin/env bash
exit 0
MOCK
  chmod +x node_modules/.bin/prettier
  export PATH="$tmpdir/node_modules/.bin:$PATH"

  echo "const x = 1" > test.js
  output=$(echo '{"tool_input":{"file_path":"test.js"}}' | node "$PLUGIN_ROOT/skills/init/templates/hooks/format-node.js" 2>&1 || true)
  # The node hook may fail if prettier isn't really there, but it shouldn't crash on JSON parsing
  # Just verify it doesn't throw a JSON parse error
  if echo "$output" | grep -q "SyntaxError"; then
    printf "  FAIL  Node hook JSON parsing error\n"
    ((errors++)) || true
  else
    printf "  PASS  Node hook parses JSON input without crash\n"
    ((pass++)) || true
  fi
  cleanup_fixture
else
  echo "  SKIP  Node hook tests (node not installed)"
fi

# ============================================================
# Path-restriction hook tests (restrict-paths.sh)
# ============================================================
# Exercises the tiered path model via the PreToolUse JSON protocol: in-project
# writes pass silently, out-of-project writes ask, deletes outside the project
# are denied, and Claude's own auto-memory store under
# ~/.claude/projects/<project>/memory/ (and the per-session scratchpad under
# <temp>/claude/<project>/<session>/scratchpad/) is exempted from the out-of-project
# ask while the rest of ~/.claude (e.g. settings.json) still prompts.
echo
echo "[restrict-paths: memory-store + scratchpad exemptions + tiered model]"
RESTRICT="$PLUGIN_ROOT/skills/permissions/templates/hooks/restrict-paths.sh"
rp_tmp=$(mktemp -d)
mkdir -p "$rp_tmp/home/.claude/projects/hash/memory/topics" "$rp_tmp/proj/src" "$rp_tmp/outside"

# Build a PreToolUse payload (rp_json) and classify the hook's JSON decision — or
# silence — into a single token (rp_classify). Kept as separate primitives so both
# the common-case runner (rp_decision) and the fail-closed runner (rp_decision_env,
# which takes a custom environment: stubbed realpath, unset HOME) can share them.
rp_json() { # $1=tool $2=input-field $3=path
  printf '{"tool_name":"%s","tool_input":{"%s":"%s"}}' "$1" "$2" "$3"
}

rp_classify() { # $1=hook stdout  ->  ALLOW | ASK | DENY | OTHER
  if [ -z "$1" ]; then echo "ALLOW"
  elif echo "$1" | grep -q '"permissionDecision":"ask"'; then echo "ASK"
  elif echo "$1" | grep -q '"permissionDecision":"deny"'; then echo "DENY"
  else echo "OTHER"; fi
}

# Run one tool call through the hook and classify its decision. rp_decision_env takes
# explicit `env` operands before a literal '--', for the fail-closed cases that need a
# non-standard environment (a non-resolving realpath stub on PATH, or HOME unset).
# rp_decision is the common case: the standard test env.
# Usage: rp_decision_env <env-operand>... -- <tool> <input-field> <path>
rp_decision_env() {
  local -a envargs=()
  while [ "${1:-}" != "--" ]; do envargs+=("$1"); shift; done
  shift  # drop the '--' separator
  rp_classify "$(rp_json "$1" "$2" "$3" | env "${envargs[@]}" bash "$RESTRICT" 2>/dev/null)"
}

rp_decision() { # $1=tool $2=input-field $3=path  ->  ALLOW | ASK | DENY | OTHER
  rp_decision_env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" -- "$1" "$2" "$3"
}

assert_decision() { # $1=label $2=expected $3=actual
  if [ "$2" = "$3" ]; then
    printf "  PASS  %s\n" "$1"
    ((pass++)) || true
  else
    printf "  FAIL  %s (expected %s, got %s)\n" "$1" "$2" "$3"
    ((errors++)) || true
  fi
}

mem="$rp_tmp/home/.claude/projects/hash/memory"
assert_decision "In-project write allowed"             ALLOW "$(rp_decision Write file_path "$rp_tmp/proj/src/a.txt")"
assert_decision "Outside-project write asks"           ASK   "$(rp_decision Write file_path "$rp_tmp/outside/a.txt")"
assert_decision "Memory-store write allowed"           ALLOW "$(rp_decision Write file_path "$mem/MEMORY.md")"
assert_decision "Memory-store subdir write allowed"    ALLOW "$(rp_decision Edit file_path "$mem/topics/x.md")"
assert_decision "Memory-store notebook allowed"        ALLOW "$(rp_decision NotebookEdit notebook_path "$mem/nb.ipynb")"
assert_decision "Global ~/.claude/settings.json asks"  ASK   "$(rp_decision Write file_path "$rp_tmp/home/.claude/settings.json")"

# Negative boundary: only a single-segment projects/<project>/memory subtree is
# exempt. Traversal out of it, a sibling of memory/, a look-alike dir name, and a
# 'memory' dir nested at arbitrary depth must all still hit the ask. (The exemption
# spans any project's store by design — the memory dir 'hash' above is unrelated to
# CLAUDE_PROJECT_DIR yet allowed — so there is no per-project negative case here.)
assert_decision "Memory traversal to settings asks"    ASK   "$(rp_decision Write file_path "$mem/../../../settings.json")"
assert_decision "Sibling of memory/ asks"              ASK   "$(rp_decision Write file_path "$rp_tmp/home/.claude/projects/hash/notes.txt")"
assert_decision "Look-alike my-memory/ asks"           ASK   "$(rp_decision Write file_path "$rp_tmp/home/.claude/projects/hash/my-memory/x.md")"
assert_decision "Nested memory/ (deep) asks"           ASK   "$(rp_decision Write file_path "$rp_tmp/home/.claude/projects/hash/sub/memory/x.md")"
assert_decision "Bare memory/ dir allowed"             ALLOW "$(rp_decision Edit file_path "$mem")"

# Delete protection (Bash branch) — reuse rp_decision; the Bash path only ever
# denies or falls through, so the shared classifier suffices. The memory store is
# writable AND prunable by design, so deletes there are allowed like writes — but a
# traversal that escapes the store is still blocked.
assert_decision "Delete outside project denied"        DENY  "$(rp_decision Bash command "rm $rp_tmp/outside/a.txt")"
assert_decision "Delete inside project allowed"        ALLOW "$(rp_decision Bash command "rm $rp_tmp/proj/src/a.txt")"
assert_decision "Delete in memory store allowed"       ALLOW "$(rp_decision Bash command "rm $mem/stale.md")"
assert_decision "Delete traversal out of memory denied" DENY "$(rp_decision Bash command "rm $mem/../../../settings.json")"

# --- Fail-closed defensive branches (not reachable through the standard env above) ---
# (1) When realpath cannot resolve '..' (non-GNU/BSD realpath — e.g. macOS, where
# 'realpath -m' is unsupported), normalize() leaves the traversal intact and the
# literal-'..' guard in is_claude_memory must still reject the exemption. Force that
# branch with a non-resolving 'realpath' stub on PATH. (Robust either way: if the
# stub is bypassed and realpath resolves '..', the path still misses the memory
# prefix and the expected ask/deny holds — only a wrongful allow would fail these.)
rp_stub_bin="$rp_tmp/stubbin"
mkdir -p "$rp_stub_bin"
printf '#!/bin/sh\nexit 1\n' > "$rp_stub_bin/realpath"
chmod +x "$rp_stub_bin/realpath"
assert_decision "Traversal asks when realpath can't resolve .."          ASK \
  "$(rp_decision_env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" PATH="$rp_stub_bin:$PATH" -- Write file_path "$mem/../../settings.json")"
assert_decision "Delete traversal denied when realpath can't resolve .." DENY \
  "$(rp_decision_env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" PATH="$rp_stub_bin:$PATH" -- Bash command "rm $mem/../../settings.json")"

# (2) When HOME and USERPROFILE are both unset, is_claude_memory can't resolve a
# home dir and must fail closed — memory paths fall back to the out-of-project gate.
assert_decision "Memory write asks when HOME unset"     ASK \
  "$(rp_decision_env -u HOME -u USERPROFILE CLAUDE_PROJECT_DIR="$rp_tmp/proj" -- Write file_path "$mem/MEMORY.md")"
assert_decision "Memory delete denied when HOME unset"  DENY \
  "$(rp_decision_env -u HOME -u USERPROFILE CLAUDE_PROJECT_DIR="$rp_tmp/proj" -- Bash command "rm $mem/stale.md")"

# --- Claude Code session scratchpad exemption ---
# The harness gives each session a scratchpad under <temp>/claude/<project>/<session>/
# scratchpad/. Like the memory store it is Claude's own throwaway working area, so
# writes and deletes there are allowed without the out-of-project ask. The temp root
# comes from TMPDIR/TEMP/TMP (with a /tmp fallback); we pin TMPDIR here so the tree is
# self-contained and the assertions don't depend on the host's real temp.
scratch_root="$rp_tmp/tmproot"
scratch="$scratch_root/claude/E--proj/session-uuid/scratchpad"
mkdir -p "$scratch/sub"
rp_decision_scratch() { # $1=tool $2=input-field $3=path
  rp_decision_env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" TMPDIR="$scratch_root" -- "$1" "$2" "$3"
}
assert_decision "Scratchpad write allowed"             ALLOW "$(rp_decision_scratch Write file_path "$scratch/notes.md")"
assert_decision "Scratchpad subdir write allowed"      ALLOW "$(rp_decision_scratch Edit file_path "$scratch/sub/x.md")"
assert_decision "Scratchpad notebook allowed"          ALLOW "$(rp_decision_scratch NotebookEdit notebook_path "$scratch/nb.ipynb")"
assert_decision "Scratchpad delete allowed"            ALLOW "$(rp_decision_scratch Bash command "rm $scratch/stale.md")"

# Negative boundary: the exemption needs the full <temp>/claude/<project>/<session>/
# scratchpad shape. A scratchpad missing the session segment, a look-alike sibling, a
# scratchpad nested deeper than two segments, and a traversal escape must all still
# ask (or, for a delete, be denied).
assert_decision "Shallow scratchpad asks"              ASK   "$(rp_decision_scratch Write file_path "$scratch_root/claude/E--proj/scratchpad/x.md")"
assert_decision "Look-alike my-scratchpad asks"        ASK   "$(rp_decision_scratch Write file_path "$scratch_root/claude/E--proj/session-uuid/my-scratchpad/x.md")"
assert_decision "Nested scratchpad (deep) asks"        ASK   "$(rp_decision_scratch Write file_path "$scratch_root/claude/E--proj/session-uuid/a/scratchpad/x.md")"
assert_decision "Scratchpad traversal escape asks"     ASK   "$(rp_decision_scratch Write file_path "$scratch/../../../../outside/x.md")"
assert_decision "Scratchpad delete traversal denied"   DENY  "$(rp_decision_scratch Bash command "rm $scratch/../../../../outside/x.md")"

# Fail-closed: (1) the literal-'..' guard must reject the exemption when realpath
# can't resolve '..' (reuses the non-resolving realpath stub from the memory block),
# and (2) when no temp root can be resolved from the environment, scratchpad paths
# fall back to the out-of-project gate. (rp_stub_bin is defined in the memory block.)
assert_decision "Scratchpad traversal asks when realpath can't resolve .." ASK \
  "$(rp_decision_env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" TMPDIR="$scratch_root" PATH="$rp_stub_bin:$PATH" -- Write file_path "$scratch/../../settings.json")"
assert_decision "Scratchpad write asks when temp vars unset" ASK \
  "$(rp_decision_env -u TMPDIR -u TEMP -u TMP HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" -- Write file_path "$scratch/notes.md")"

# ============================================================
# Temp-write nudge tests (restrict-paths.sh nudge_temp_write)
# ============================================================
# Creating a NEW file under the temp root outside the exempt scratchpad shape
# still ASKS — the nudge only changes the prompt's wording, adding a reminder
# that the session scratchpad is exempt. It must never deny: a PreToolUse deny
# goes to the model and never to the user, so denying here would silently remove
# a decision (e.g. a user-requested /tmp/report.csv) that is the user's to make.
# The hook deliberately does not name a scratchpad path — only the harness knows
# it — so there is no advertised path to parse or replay.
# The nudge stays silent (plain prompt) for existing files, ~/.claude, unresolved
# ".." traversals, and paths outside the temp root.
# (Reuses the rp_tmp / rp_stub_bin / rp_decision_env / assert_decision fixtures.)
echo
echo "[restrict-paths: temp-write nudge]"
rp_json_sid() { # $1=session-id $2=tool $3=input-field $4=path
  printf '{"session_id":"%s","tool_name":"%s","tool_input":{"%s":"%s"}}' "$1" "$2" "$3" "$4"
}
# Run the hook and record BOTH stdout and exit status. The status is captured in
# the caller's shell (not a subshell) because an ALLOW verdict is inferred from
# SILENT stdout: without the status, a hook that died before printing would be
# scored "allowed" and every exemption assertion would pass vacuously. Results
# land in rp_out / rp_last_status rather than being echoed, precisely so no call
# site can wrap this in a command substitution and lose the status again.
# Usage: rp_run <env-operand>... -- <session-id> <tool> <input-field> <path>
rp_out=""
rp_last_status=0
rp_run() {
  local -a envargs=()
  while [ "$#" -gt 0 ] && [ "$1" != "--" ]; do envargs+=("$1"); shift; done
  [ "$#" -gt 0 ] || { echo "rp_run: missing separator" >&2; exit 2; }
  shift  # drop the '--' separator
  set +e
  rp_out=$(rp_json_sid "$1" "$2" "$3" "$4" | env "${envargs[@]+"${envargs[@]}"}" bash "$RESTRICT" 2>/dev/null)
  rp_last_status=$?
  set -e
}
# The standard scratchpad environment, which most cases below use.
rp_run_scratch() { # $1=session-id $2=tool $3=input-field $4=path
  rp_run HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" TMPDIR="$scratch_root" -- "$1" "$2" "$3" "$4"
}

# Guard the guard: prove rp_run actually propagates a non-zero status, so the
# assert_exit_zero calls below cannot silently become no-ops (they did once —
# the status was assigned inside a command substitution and never reached the
# caller, so a deleted hook still scored as a passing ALLOW).
rp_saved_restrict="$RESTRICT"
RESTRICT="$rp_tmp/definitely-not-a-hook.sh"
rp_run HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" -- s Write file_path /nope
assert_decision "rp_run reports a crashed hook (guard is not vacuous)" CRASH \
  "$(if [ "$rp_last_status" -ne 0 ]; then echo CRASH; else echo "VACUOUS"; fi)"
RESTRICT="$rp_saved_restrict"

# A new file in an invented temp dir asks, and the reason carries the reminder.
rp_run_scratch session-abc Write file_path "$scratch_root/scratch-foo/x.md"
assert_decision "Invented temp dir write asks"        ASK "$(rp_classify "$rp_out")"
assert_output_contains "Nudge reason mentions the scratchpad" "scratchpad" "$rp_out"
assert_output_contains "Nudge reason names the file"  "$scratch_root/scratch-foo/x.md" "$rp_out"
assert_exit_zero "Nudge is a real decision, not a crash" "$rp_last_status"
# The nudge must NEVER deny — a deny cannot be approved by the user.
assert_output_not_contains "Nudge never denies" "deny" "$rp_out"

rp_run_scratch session-abc NotebookEdit notebook_path "$scratch_root/scratch-foo/nb.ipynb"
assert_decision "Notebook in invented temp dir asks"  ASK "$(rp_classify "$rp_out")"
rp_run_scratch session-abc Write file_path "$scratch_root/claude/E--proj/scratchpad/x.md"
assert_decision "Shallow scratchpad asks (not exempt)" ASK "$(rp_classify "$rp_out")"

# A user-requested temp path must stay approvable — this is the case a deny broke.
rp_run_scratch session-abc Write file_path "$scratch_root/report.csv"
assert_decision "User-requested temp file asks"       ASK "$(rp_classify "$rp_out")"

echo "[restrict-paths: nudge scope]"
# An EXISTING temp file, ~/.claude, and non-temp outside paths keep the plain
# prompt: the reminder is only meaningful when choosing where to put a new file.
rp_existing="$scratch_root/pre-existing/tool-output.md"
mkdir -p "$scratch_root/pre-existing"
: > "$rp_existing"
rp_run_scratch session-abc Edit file_path "$rp_existing"
assert_decision "Existing temp file edit asks"        ASK "$(rp_classify "$rp_out")"
assert_output_not_contains "Existing temp file gets no nudge" "scratchpad" "$rp_out"
rp_run_scratch session-abc Write file_path "$scratch_root/pre-existing/new.md"
assert_decision "New file in the same dir asks"       ASK "$(rp_classify "$rp_out")"
rp_run HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" TMPDIR="$scratch_root" -- \
  session-abc Write file_path "/var/opt/optimus-not-temp/a.txt"
assert_decision "Non-temp outside path asks"          ASK "$(rp_classify "$rp_out")"
assert_output_not_contains "Non-temp path gets no nudge" "scratchpad" "$rp_out"

# ~/.claude is config, not scratch: it keeps the plain prompt even when HOME
# itself sits under the temp root (CI images), while the memory store stays exempt.
rp_temp_home="$scratch_root/ci-home"
mkdir -p "$rp_temp_home/.claude/projects/hash/memory"
rp_run HOME="$rp_temp_home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" TMPDIR="$scratch_root" -- \
  session-abc Write file_path "$rp_temp_home/.claude/settings.json"
assert_decision "HOME under temp root: settings.json asks" ASK "$(rp_classify "$rp_out")"
assert_output_not_contains "settings.json gets no nudge" "scratchpad" "$rp_out"
rp_run HOME="$rp_temp_home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" TMPDIR="$scratch_root" -- \
  session-abc Write file_path "$rp_temp_home/.claude/projects/hash/memory/M.md"
assert_decision "HOME under temp root: memory store allowed" ALLOW "$(rp_classify "$rp_out")"
assert_exit_zero "Memory-store allow is real, not a crash" "$rp_last_status"

# REGRESSION: the veto is scoped to ~/.claude, NOT to all of $HOME. A whole-$HOME
# veto silently disabled the nudge wherever the temp root lives under the home
# dir (TMPDIR=$HOME/tmp, MSYS2/Cygwin default mounts) — the common case, not a
# rare one. The nudge must still fire there.
mkdir -p "$rp_tmp/home/tmp"
rp_run HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" TMPDIR="$rp_tmp/home/tmp" -- \
  session-abc Write file_path "$rp_tmp/home/tmp/invented/x.md"
assert_decision "Temp root under HOME still asks"     ASK "$(rp_classify "$rp_out")"
assert_output_contains "Temp root under HOME still nudges" "scratchpad" "$rp_out"

# A traversal the platform's realpath cannot resolve must not be reasoned about.
rp_run HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" TMPDIR="$scratch_root" PATH="$rp_stub_bin:$PATH" -- \
  session-abc Write file_path "$scratch_root/scratch-foo/../../x.md"
assert_decision "Unresolved traversal asks"           ASK "$(rp_classify "$rp_out")"

echo "[restrict-paths: platform path shapes]"
# macOS ships a TMPDIR ending in '/' and (13+) a realpath that rejects GNU's
# '-m'. Either shape used to leave the temp base unable to match ordinary paths,
# silently killing the scratchpad exemption. Replay the exemption on each.
assert_decision "Scratchpad write allowed with trailing-slash temp root" ALLOW \
  "$(rp_decision_env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" TMPDIR="$scratch_root/" -- Write file_path "$scratch/notes.md")"
assert_decision "Scratchpad write allowed under non-GNU realpath" ALLOW \
  "$(rp_decision_env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" TMPDIR="$scratch_root/" PATH="$rp_stub_bin:$PATH" -- Write file_path "$scratch/notes.md")"
# ...and the nudge on each, so a base that stops matching cannot go unnoticed.
rp_run HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" TMPDIR="$scratch_root/" -- \
  session-abc Write file_path "$scratch_root/scratch-foo/x.md"
assert_output_contains "Trailing-slash temp root still nudges" "scratchpad" "$rp_out"
rp_run HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" TMPDIR="$scratch_root/" PATH="$rp_stub_bin:$PATH" -- \
  session-abc Write file_path "$scratch_root/scratch-foo/x.md"
assert_output_contains "Non-GNU realpath still nudges" "scratchpad" "$rp_out"

# A RELATIVE temp root must be rejected outright: normalize() resolves it against
# the hook's working directory, which would make an arbitrary sibling of the
# project an auto-allowed subtree — exempt from the prompt AND the rm hard-block.
mkdir -p "$rp_tmp/relbase/claude/a/b/scratchpad"
rp_run HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" TMPDIR="../relbase" -- \
  session-abc Bash command "rm $rp_tmp/relbase/claude/a/b/scratchpad/f.txt"
assert_decision "Relative temp root cannot exempt a delete" DENY "$(rp_classify "$rp_out")"
rp_run HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" TMPDIR="../relbase" -- \
  session-abc Write file_path "$rp_tmp/relbase/claude/a/b/scratchpad/f.md"
assert_decision "Relative temp root cannot exempt a write" ASK "$(rp_classify "$rp_out")"

# A filesystem root is not a usable temp root — treating '/' as one would make
# every absolute path "under the temp root".
rp_run HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" TMPDIR="/" -- \
  session-abc Write file_path "$scratch_root/scratch-foo/x.md"
assert_decision "Root temp dir degrades to a plain ask" ASK "$(rp_classify "$rp_out")"

# The reason interpolates raw environment values, so a control character in the
# temp root (a CRLF-sourced TEMP on Windows is the easy way to get one) must not
# reach the output: a bare control char makes the decision unparseable JSON,
# which the harness reads as "no decision" — silently dropping the prompt.
rp_tab_root="$(printf '%s/tab\there' "$scratch_root")"
rp_run HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" TMPDIR="$rp_tab_root" -- \
  session-abc Write file_path "$rp_tab_root/inv/x.md"
assert_decision "Control char in temp root still asks" ASK "$(rp_classify "$rp_out")"
assert_output_not_contains "Reason escapes control characters" "$(printf '\t')" "$rp_out"

# Deletes under the temp root stay hard-blocked — the nudge is for writes only.
rp_run_scratch session-abc Bash command "rm $scratch_root/scratch-foo/x.md"
assert_decision "Temp-root delete stays blocked"      DENY "$(rp_classify "$rp_out")"
assert_output_contains "Delete block is a plain block" "Cannot delete" "$rp_out"

echo "[restrict-paths: path normalization]"
# EXACTLY two leading slashes are a UNC network root on MSYS/Cygwin and are
# implementation-defined under POSIX. Collapsing them would make a remote path
# compare equal to an unrelated local one and pass a project prefix test; three
# or more leading slashes are plain '/' and must still collapse.
assert_decision "UNC-style //path is not treated as in-project" ASK \
  "$(rp_decision_env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" -- Write file_path "/$rp_tmp/proj/x.txt")"
assert_decision "Triple-slash path collapses to in-project" ALLOW \
  "$(rp_decision_env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" -- Write file_path "//$rp_tmp/proj/x.txt")"
# A '.' segment must not satisfy a single-segment slot in the exemption shapes.
assert_decision "Dot segment cannot stand in for <project>" ASK \
  "$(rp_decision_env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" TMPDIR="$scratch_root" PATH="$rp_stub_bin:$PATH" -- Write file_path "$scratch_root/claude/./session-uuid/scratchpad/x.md")"

# ============================================================
# Summary
# ============================================================
echo
echo "=== Hook test results: $pass passed, $errors failed ==="
if [ "$errors" -gt 0 ]; then exit 1; else exit 0; fi
