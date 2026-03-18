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
mkdir -p .claude/docs .claude/agents
echo "# Project" > .claude/CLAUDE.md
echo "# Guidelines" > .claude/docs/coding-guidelines.md
echo "# Simplifier" > .claude/agents/code-simplifier.md
output=$(bash "$SESSION_START" 2>/dev/null || true)
assert_output_contains "Suggests re-running init when testing.md missing" "/optimus:init" "$output"
assert_output_not_contains "Does not suggest unit-test for missing testing docs" "/optimus:unit-test" "$output"
cleanup_fixture

echo "[session-start: init done, has testing but missing test-guardian]"
setup_fixture
mkdir -p .claude/docs .claude/agents
echo "# Project" > .claude/CLAUDE.md
echo "# Guidelines" > .claude/docs/coding-guidelines.md
echo "# Testing" > .claude/docs/testing.md
echo "# Simplifier" > .claude/agents/code-simplifier.md
output=$(bash "$SESSION_START" 2>/dev/null || true)
assert_output_contains "Reports missing test-guardian agent" "test-guardian" "$output"
cleanup_fixture

echo "[session-start: init done, missing code-simplifier]"
setup_fixture
mkdir -p .claude/docs .claude/agents
echo "# Project" > .claude/CLAUDE.md
echo "# Guidelines" > .claude/docs/coding-guidelines.md
echo "# Testing" > .claude/docs/testing.md
echo "# Guardian" > .claude/agents/test-guardian.md
output=$(bash "$SESSION_START" 2>/dev/null || true)
assert_output_contains "Reports missing code-simplifier agent" "code-simplifier" "$output"
cleanup_fixture

echo "[session-start: fully configured, clean tree]"
setup_fixture
mkdir -p .claude/docs .claude/agents
echo "# Project" > .claude/CLAUDE.md
echo "# Guidelines" > .claude/docs/coding-guidelines.md
echo "# Testing" > .claude/docs/testing.md
echo "# Simplifier" > .claude/agents/code-simplifier.md
echo "# Guardian" > .claude/agents/test-guardian.md
# Stage and commit everything so working tree is clean and there's an upstream
git add -A && git commit -q -m "setup"
output=$(bash "$SESSION_START" 2>/dev/null || true)
assert_output_empty "Zero output when fully configured and clean" "$output"
cleanup_fixture

echo "[session-start: fully configured, uncommitted changes]"
setup_fixture
mkdir -p .claude/docs .claude/agents
echo "# Project" > .claude/CLAUDE.md
echo "# Guidelines" > .claude/docs/coding-guidelines.md
echo "# Testing" > .claude/docs/testing.md
echo "# Simplifier" > .claude/agents/code-simplifier.md
echo "# Guardian" > .claude/agents/test-guardian.md
git add -A && git commit -q -m "setup"
# Create uncommitted change
echo "new content" > dirty-file.txt
output=$(bash "$SESSION_START" 2>/dev/null || true)
assert_output_contains "Reports uncommitted changes" "files changed" "$output"
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
# Summary
# ============================================================
echo
echo "=== Hook test results: $pass passed, $errors failed ==="
if [ "$errors" -gt 0 ]; then exit 1; else exit 0; fi
