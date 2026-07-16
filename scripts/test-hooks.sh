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

echo "=== optimus-claude hook tests ==="
echo

# ============================================================
# Session-start hook tests
# ============================================================
echo "[session-start: uninitialized project]"
setup_fixture
output=$(bash "$SESSION_START" 2>/dev/null || true)
assert_output_contains "Recommends /optimus:init when no .claude/" "/optimus:init" "$output"
assert_output_contains "Mentions CLAUDE.md" "CLAUDE.md" "$output"
cleanup_fixture

echo "[session-start: partially initialized (CLAUDE.md only)]"
setup_fixture
mkdir -p .claude
echo "# Project" > .claude/CLAUDE.md
output=$(bash "$SESSION_START" 2>/dev/null || true)
assert_output_contains "Still recommends init when coding-guidelines missing" "/optimus:init" "$output"
cleanup_fixture

echo "[session-start: init done, no testing docs]"
setup_fixture
mkdir -p .claude/docs
echo "# Project" > .claude/CLAUDE.md
echo "# Guidelines" > .claude/docs/coding-guidelines.md
output=$(bash "$SESSION_START" 2>/dev/null || true)
assert_output_contains "Suggests re-running init when testing.md missing" "/optimus:init" "$output"
assert_output_not_contains "Does not suggest unit-test for missing testing docs" "/optimus:unit-test" "$output"
cleanup_fixture

echo "[session-start: fully configured, clean tree]"
setup_fixture
mkdir -p .claude/docs
echo "# Project" > .claude/CLAUDE.md
echo "# Guidelines" > .claude/docs/coding-guidelines.md
echo "# Testing" > .claude/docs/testing.md
# Stage and commit everything so working tree is clean and there's an upstream
git add -A && git commit -q -m "setup"
output=$(bash "$SESSION_START" 2>/dev/null || true)
assert_output_empty "Zero output when fully configured and clean" "$output"
cleanup_fixture

echo "[session-start: fully configured, uncommitted changes — still silent]"
setup_fixture
mkdir -p .claude/docs
echo "# Project" > .claude/CLAUDE.md
echo "# Guidelines" > .claude/docs/coding-guidelines.md
echo "# Testing" > .claude/docs/testing.md
git add -A && git commit -q -m "setup"
# Create uncommitted change — git state is Claude Code's job, not the hook's
echo "new content" > dirty-file.txt
output=$(bash "$SESSION_START" 2>/dev/null || true)
assert_output_empty "Zero output even with uncommitted changes (native gitStatus covers it)" "$output"
cleanup_fixture

echo "[session-start: multi-repo workspace, marker in one sub-repo]"
setup_fixture
mkdir -p sub-a/.claude
echo "1.64.2" > sub-a/.claude/.optimus-version
output=$(bash "$SESSION_START" 2>/dev/null || true)
assert_output_not_contains "Suppresses init notice when sub-repo carries .optimus-version" "/optimus:init" "$output"
cleanup_fixture

echo "[session-start: multi-repo workspace, markers at different depths]"
setup_fixture
mkdir -p sub-a/.claude
mkdir -p sub-b/nested/.claude
echo "1.64.2" > sub-a/.claude/.optimus-version
echo "1.64.2" > sub-b/nested/.claude/.optimus-version
output=$(bash "$SESSION_START" 2>/dev/null || true)
assert_output_not_contains "Suppresses init notice when markers are nested at depth 4" "/optimus:init" "$output"
cleanup_fixture

echo "[session-start: workspace root with settings only, marker in sub-repo (mirrors audaces/isa)]"
setup_fixture
mkdir -p .claude
echo "{}" > .claude/settings.json
echo "# Workspace" > CLAUDE.md
mkdir -p sub/.claude
echo "1.64.2" > sub/.claude/.optimus-version
output=$(bash "$SESSION_START" 2>/dev/null || true)
assert_output_not_contains "Suppresses init notice in audaces/isa-style layout" "/optimus:init" "$output"
cleanup_fixture

echo "[session-start: no markers anywhere — regression for clean dir]"
setup_fixture
output=$(bash "$SESSION_START" 2>/dev/null || true)
assert_output_contains "Still recommends init when no marker exists in workspace" "/optimus:init" "$output"
cleanup_fixture

echo "[session-start: marker beyond maxdepth]"
setup_fixture
mkdir -p a/b/c/d/.claude
echo "1.64.2" > a/b/c/d/.claude/.optimus-version
output=$(bash "$SESSION_START" 2>/dev/null || true)
assert_output_contains "Recommends init when marker is deeper than maxdepth 4" "/optimus:init" "$output"
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
RESTRICT="$PLUGIN_ROOT/skills/init/templates/hooks/restrict-paths.sh"
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
# Summary
# ============================================================
echo
echo "=== Hook test results: $pass passed, $errors failed ==="
if [ "$errors" -gt 0 ]; then exit 1; else exit 0; fi
