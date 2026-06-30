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
trap 'if [ -n "$tmpdir" ] && [ -d "$tmpdir" ]; then rm -rf "$tmpdir"; fi' EXIT

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

echo "[session-start: fully configured, uncommitted changes]"
setup_fixture
mkdir -p .claude/docs
echo "# Project" > .claude/CLAUDE.md
echo "# Guidelines" > .claude/docs/coding-guidelines.md
echo "# Testing" > .claude/docs/testing.md
git add -A && git commit -q -m "setup"
# Create uncommitted change
echo "new content" > dirty-file.txt
output=$(bash "$SESSION_START" 2>/dev/null || true)
assert_output_contains "Reports uncommitted changes" "files changed" "$output"
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
# ~/.claude/projects/<project>/memory/ is exempted from the out-of-project ask
# while the rest of ~/.claude (e.g. settings.json) still prompts.
echo
echo "[restrict-paths: memory-store exemption + tiered model]"
RESTRICT="$PLUGIN_ROOT/skills/permissions/templates/hooks/restrict-paths.sh"
rp_tmp=$(mktemp -d)
mkdir -p "$rp_tmp/home/.claude/projects/hash/memory/topics" "$rp_tmp/proj/src" "$rp_tmp/outside"

# Map the hook's JSON decision (or silence) to a single token for assertions.
rp_decision() { # $1=tool $2=input-field $3=path  ->  ALLOW | ASK | DENY | OTHER
  local out
  out=$(printf '{"tool_name":"%s","tool_input":{"%s":"%s"}}' "$1" "$2" "$3" \
        | env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" bash "$RESTRICT" 2>/dev/null)
  if [ -z "$out" ]; then echo "ALLOW"
  elif echo "$out" | grep -q '"permissionDecision":"ask"'; then echo "ASK"
  elif echo "$out" | grep -q '"permissionDecision":"deny"'; then echo "DENY"
  else echo "OTHER"; fi
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

# Delete protection still holds (Bash branch).
rp_bash_decision() { # $1=command -> ALLOW | DENY | OTHER
  local out
  out=$(printf '{"tool_name":"Bash","tool_input":{"command":"%s"}}' "$1" \
        | env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" bash "$RESTRICT" 2>/dev/null)
  if [ -z "$out" ]; then echo "ALLOW"
  elif echo "$out" | grep -q '"permissionDecision":"deny"'; then echo "DENY"
  else echo "OTHER"; fi
}
assert_decision "Delete outside project denied"        DENY  "$(rp_bash_decision "rm $rp_tmp/outside/a.txt")"
assert_decision "Delete inside project allowed"        ALLOW "$(rp_bash_decision "rm $rp_tmp/proj/src/a.txt")"

rm -rf "$rp_tmp"

# ============================================================
# Summary
# ============================================================
echo
echo "=== Hook test results: $pass passed, $errors failed ==="
if [ "$errors" -gt 0 ]; then exit 1; else exit 0; fi
