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
# Separate from tmpdir, which setup_fixture/cleanup_fixture create and destroy
# around each case: these fixtures are read by assertions that stand outside any
# one fixture's lifetime.
ss_tmp=""
trap 'for _d in "$tmpdir" "$rp_tmp" "$ss_tmp"; do [ -n "$_d" ] && [ -d "$_d" ] && rm -rf "$_d"; done' EXIT

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
    # Leave the directory before deleting it. The shell's CWD is inside the
    # fixture, and everything after the LAST cleanup_fixture would otherwise run
    # from a deleted directory — where a relative path resolves against nothing,
    # so those cases exercise a getcwd failure rather than the guard under test.
    cd "$PLUGIN_ROOT" || return
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
  # CLAUDE_PLUGIN_ROOT is what hooks.json passes in production; the hook needs it
  # to find the shipped template it compares the installed hook against.
  output=$(CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT" bash "$SESSION_START" 2>/dev/null)
  hook_status=$?
  set -e
}

# Same, but with CLAUDE_PLUGIN_ROOT genuinely unset. The variable reads empty on
# some platforms (notably Windows), which is why the hook falls back to its own
# location; every other case here hardcodes it, so without this one the fallback
# is untested and the drift notice could be dead in production with a green suite.
run_session_start_no_plugin_root() {
  set +e
  output=$(env -u CLAUDE_PLUGIN_ROOT bash "$SESSION_START" 2>/dev/null)
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

assert_equals() { # $1=label $2=expected $3=actual
  if [ "$2" = "$3" ]; then
    printf "  PASS  %s\n" "$1"
    ((pass++)) || true
  else
    printf "  FAIL  %s (expected %s, got %s)\n" "$1" "$2" "$3"
    ((errors++)) || true
  fi
}

# Assertions about the REASON text of the last rp_run. Both first require that a
# decision was actually emitted: a crashed or silent run carries no reason, and a
# bare "does not contain" would pass vacuously against one — which is exactly how
# a dead hook used to score green on every negative assertion in this file.
_rp_reason_guard() {
  if [ "$rp_last_status" -ne 0 ] || [ -z "$rp_out" ]; then
    printf "  FAIL  %s (no decision emitted: exit=%s, output empty=%s)\n" \
      "$1" "$rp_last_status" "$([ -z "$rp_out" ] && echo yes || echo no)"
    ((errors++)) || true
    return 1
  fi
  return 0
}

assert_reason_has() { # $1=label $2=expected substring
  if _rp_reason_guard "$1"; then assert_output_contains "$1" "$2" "$rp_out"; fi
}

assert_reason_lacks() { # $1=label $2=unexpected substring
  if _rp_reason_guard "$1"; then assert_output_not_contains "$1" "$2" "$rp_out"; fi
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
assert_output_not_contains "No Codex line under Claude Code" "Running under Codex" "$output"
cleanup_fixture

# Codex loads the same hooks.json and sets PLUGIN_ROOT next to
# CLAUDE_PLUGIN_ROOT (Claude Code sets only the latter). Under Codex the
# suggestions take the `$optimus:` form and one line names the plugin root;
# the Claude Code cases above pin that nothing else changes.
run_session_start_codex() {
  set +e
  output=$(PLUGIN_ROOT="$PLUGIN_ROOT" CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT" bash "$SESSION_START" 2>/dev/null)
  hook_status=$?
  set -e
}

echo "[session-start: uninitialized project under Codex]"
setup_fixture
run_session_start_codex
assert_output_contains "Recommends \$optimus:init under Codex" "\$optimus:init" "$output"
assert_output_not_contains "Drops the /optimus: form under Codex" "/optimus:init" "$output"
assert_output_contains "Names the plugin root under Codex" "Plugin root: $PLUGIN_ROOT" "$output"
assert_output_contains "Names slash-form skill mentions in the Codex mapping" "/optimus:<skill>" "$output"
assert_output_contains "Names dollar-form skill mentions in the Codex mapping" "\$optimus:<skill>" "$output"
assert_output_contains "Maps AskUserQuestion to plain text under Codex" "AskUserQuestion" "$output"
assert_output_not_contains "Does not promise formatter hooks under Codex" "and auto-format hooks." "$output"
assert_exit_zero "Exits 0 under Codex" "$hook_status"
cleanup_fixture

echo "[session-start: fully configured, clean tree, under Codex]"
setup_fixture
mkdir -p .claude/docs
echo "# Project" > .claude/CLAUDE.md
echo "# Guidelines" > .claude/docs/coding-guidelines.md
echo "# Testing" > .claude/docs/testing.md
git add -A && git commit -q -m "setup"
run_session_start_codex
# The plugin root is the one line a configured project still needs under Codex —
# every skill resolves $CLAUDE_PLUGIN_ROOT through it — so silence here is wrong.
assert_output_contains "Still names the plugin root when configured" "Plugin root: $PLUGIN_ROOT" "$output"
assert_output_not_contains "No init nag when configured under Codex" "optimus:init" "$output"
assert_exit_zero "Exits 0 when configured under Codex" "$hook_status"
cleanup_fixture

echo "[session-start: Claude-only hook update is not recommended under Codex]"
setup_fixture
mkdir -p .claude/hooks
printf '#!/usr/bin/env bash\n# HOOK_VERSION: 0\nexit 0\n' > .claude/hooks/restrict-paths.sh
run_session_start_codex
assert_output_not_contains "Does not recommend an unsupported permissions skill" '$optimus:permissions' "$output"
assert_output_not_contains "Does not report an inactive Claude hook as stale" 'older than the plugin' "$output"
assert_exit_zero "Exits 0 with a stale Claude hook under Codex" "$hook_status"
cleanup_fixture

echo "[session-start: stray PLUGIN_ROOT that is not the plugin's is not Codex]"
setup_fixture
# Prefix assignments expand left to right, so `PLUGIN_ROOT=/x CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"`
# would hand the hook two equal values and test nothing — capture the real root first.
real_root="$PLUGIN_ROOT"
set +e
output=$(PLUGIN_ROOT="/somewhere/else" CLAUDE_PLUGIN_ROOT="$real_root" bash "$SESSION_START" 2>/dev/null)
hook_status=$?
set -e
assert_output_contains "Keeps the /optimus: form for a stray PLUGIN_ROOT" "/optimus:init" "$output"
assert_output_not_contains "No Codex line for a stray PLUGIN_ROOT" "Running under Codex" "$output"
assert_exit_zero "Exits 0 with a stray PLUGIN_ROOT" "$hook_status"
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

# The path-restriction hook is COPIED into a project by /optimus:permissions and
# is never re-copied by a plugin update, so a project can keep running a hook
# that predates a security fix. HOOK_VERSION makes that drift visible.
# Each case builds a fully initialized fixture so the init notice stays silent
# and the assertion is about the freshness check alone.
setup_versioned_fixture() { # $1=installed hook version, or "none" for no marker
  setup_fixture
  mkdir -p .claude/docs .claude/hooks
  echo "# Project"    > .claude/CLAUDE.md
  echo "# Guidelines" > .claude/docs/coding-guidelines.md
  echo "# Testing"    > .claude/docs/testing.md
  if [ "$1" = "none" ]; then
    printf '#!/usr/bin/env bash\n# no version marker\n' > .claude/hooks/restrict-paths.sh
  else
    printf '#!/usr/bin/env bash\n# HOOK_VERSION: %s\n' "$1" > .claude/hooks/restrict-paths.sh
  fi
  git add -A && git commit -q -m setup
}
# Derived the way the HOOK derives it — stop at the first non-comment line —
# rather than by scanning the whole file. An oracle that reads further than the
# reader under test agrees with it only while the marker stays in the banner, so
# the two could disagree exactly when the bound is exceeded, with the suite
# green.
ss_plugin_ver="$(sed -n '/^[^#]/q;p' \
  "$PLUGIN_ROOT/skills/permissions/templates/hooks/restrict-paths.sh" \
  | sed -n 's/^# HOOK_VERSION:[[:space:]]*\([0-9][0-9]*\).*/\1/p' | head -1)"

# Drive read_hook_version directly. The decision-level tests below can only see
# the marker through a full session-start run, which cannot distinguish "read 0"
# from "read the right number and chose not to warn" — and the direction that
# matters (a TEMPLATE whose marker is unreachable) is silent by construction.
ss_tmp=$(mktemp -d)
ss_read_version() { # $1=file -> the version the hook would read
  local f="$ss_tmp/drive-ssver.sh"
  {
    awk '/^read_hook_version\(\) \{/,/^\}/' "$SESSION_START"
    printf 'read_hook_version "$1"; printf %%s "$_hook_version"\n'
  } > "$f"
  bash "$f" "$1"
}

echo "[session-start: installed restrict-paths hook is stale]"
setup_versioned_fixture 1
run_session_start
assert_output_contains "Flags a hook older than the plugin's" "/optimus:permissions" "$output"
assert_output_contains "Names the stale file" ".claude/hooks/restrict-paths.sh" "$output"
assert_exit_zero "Exits 0 when flagging a stale hook" "$hook_status"
cleanup_fixture

echo "[session-start: stale hook, CLAUDE_PLUGIN_ROOT unset]"
setup_versioned_fixture 1
run_session_start_no_plugin_root
assert_output_contains "Locates the template via its own path when the env var is unset" "/optimus:permissions" "$output"
assert_exit_zero "Exits 0 with CLAUDE_PLUGIN_ROOT unset" "$hook_status"
cleanup_fixture

echo "[session-start: installed hook predates versioning]"
setup_versioned_fixture none
run_session_start
assert_output_contains "Treats a missing marker as v0" "/optimus:permissions" "$output"
cleanup_fixture

echo "[session-start: version read bound]"
# The version is read with a bounded loop — the hook is 1800+ lines and the read
# runs twice on every session start, so scanning the whole file with sed was most
# of this hook's runtime. The bound is the BANNER, not a line count: a literal
# was a magic number duplicated in validate.sh, and a marker one line past it
# read as v0 on BOTH sides, which `[ want -gt have ]` can never act on — the
# staleness warning would go silent for every project instead of failing loudly.
ss_marker_fixture() { # $1=body $2=name -> a file with that body, path echoed
  local f="$ss_tmp/ssver-$2.sh"
  printf '%s\n' "$1" > "$f"
  printf '%s' "$f"
}
assert_equals "Marker deep in a long banner is still read" "7" \
  "$(ss_read_version "$(ss_marker_fixture '#!/usr/bin/env bash
# ============================================================
# a banner
# that runs
# on for
# a while
# ============================================================
# HOOK_VERSION: 7' banner)")"
assert_equals "Marker below the first line of CODE reads as v0" "0" \
  "$(ss_read_version "$(ss_marker_fixture '#!/usr/bin/env bash
set -e
# HOOK_VERSION: 999' belowcode)")"
assert_equals "No marker at all reads as v0" "0" \
  "$(ss_read_version "$(ss_marker_fixture '#!/usr/bin/env bash
# nothing to see' nomarker)")"
# ...and v0 has to fail in the SAFE direction end-to-end: suggest re-running,
# never go silent. The fixture's 999 would out-rank the plugin if it were read.
setup_fixture
mkdir -p .claude/docs .claude/hooks
echo "# Project"    > .claude/CLAUDE.md
echo "# Guidelines" > .claude/docs/coding-guidelines.md
echo "# Testing"    > .claude/docs/testing.md
{
  printf '#!/usr/bin/env bash\n'
  printf 'set -euo pipefail\n'
  printf '# HOOK_VERSION: 999\n'
} > .claude/hooks/restrict-paths.sh
git add -A && git commit -q -m setup
run_session_start
assert_output_contains "A marker below the banner reads as v0, not as current" \
  "/optimus:permissions" "$output"
cleanup_fixture

echo "[session-start: installed hook is current]"
setup_versioned_fixture "$ss_plugin_ver"
run_session_start
assert_output_empty "Silent when the installed hook matches the plugin" "$output"
assert_exit_zero "Exits 0 when the installed hook is current" "$hook_status"
cleanup_fixture

echo "[session-start: no restrict-paths hook installed]"
setup_fixture
mkdir -p .claude/docs
echo "# Project"    > .claude/CLAUDE.md
echo "# Guidelines" > .claude/docs/coding-guidelines.md
echo "# Testing"    > .claude/docs/testing.md
git add -A && git commit -q -m setup
run_session_start
assert_output_empty "Silent when the project never installed the hook" "$output"
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
# format-rust.sh stands in for the hooks whose only logic is parse-guard-invoke.
# format-python.sh resolves its formatters from a virtualenv and gets its own
# section below.
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

echo "[formatter hooks: python hook resolves formatters from a project venv]"
setup_fixture
# The TEMPLATE is what users install. test/test_format_python_hook.py exercises
# the dogfooded .claude/ copy and scripts/validate.sh pins the two together, so
# between them both copies are covered.
FORMAT_PY_HOOK="$PLUGIN_ROOT/skills/init/templates/hooks/format-python.sh"
export FORMAT_PY_LOG="$tmpdir/formatters.log"
: > "$FORMAT_PY_LOG"

# Windows probes Scripts/ first and POSIX probes bin/ first — plant both so the
# case runs identically either way.
for sub in bin Scripts; do
  mkdir -p ".venv/$sub"
  for tool in black isort; do
    printf '#!/usr/bin/env bash\nprintf "%%s\\n" "%s $*" >> "$FORMAT_PY_LOG"\n' "$tool" > ".venv/$sub/$tool"
    chmod +x ".venv/$sub/$tool"
  done
done

# Nested file, venv at the project root: the walk up has to find it.
mkdir -p pkg/src
echo "x=1" > pkg/src/app.py
output=$(printf '{"tool_input":{"file_path":"%s/pkg/src/app.py"}}' "$tmpdir" |
  CLAUDE_PROJECT_DIR="$tmpdir" bash "$FORMAT_PY_HOOK" 2>&1 || true)
assert_output_empty "Python hook is silent when both formatters resolve" "$output"
assert_output_contains "Python hook runs black from the project venv" \
  "black --quiet" "$(cat "$FORMAT_PY_LOG")"
assert_output_contains "Python hook runs isort from the same venv" \
  "isort --quiet --profile black" "$(cat "$FORMAT_PY_LOG")"

# Non-ASCII arrives as raw UTF-8 (JSON.stringify does not escape it), and must
# pass through the regex and the *.py guard intact.
: > "$FORMAT_PY_LOG"
mkdir -p "café"
echo "x=1" > "café/app.py"
printf '{"tool_input":{"file_path":"%s/café/app.py"}}' "$tmpdir" |
  CLAUDE_PROJECT_DIR="$tmpdir" bash "$FORMAT_PY_HOOK" >/dev/null 2>&1 || true
assert_output_contains "Python hook handles a raw non-ASCII file_path" \
  "café/app.py" "$(cat "$FORMAT_PY_LOG")"

# A non-.py file must not reach a formatter at all.
: > "$FORMAT_PY_LOG"
echo "hello" > notes.txt
output=$(printf '{"tool_input":{"file_path":"%s/notes.txt"}}' "$tmpdir" |
  CLAUDE_PROJECT_DIR="$tmpdir" bash "$FORMAT_PY_HOOK" 2>&1 || true)
assert_output_empty "Python hook skips a non-.py file" "$output$(cat "$FORMAT_PY_LOG")"

# A venv holding only black must not borrow isort from PATH — mismatched
# versions produce an import order the project's own isort then rejects.
: > "$FORMAT_PY_LOG"
mkdir -p solo/.venv/bin solo/.venv/Scripts
for sub in bin Scripts; do
  printf '#!/usr/bin/env bash\nprintf "%%s\\n" "black $*" >> "$FORMAT_PY_LOG"\n' > "solo/.venv/$sub/black"
  chmod +x "solo/.venv/$sub/black"
done
echo "x=1" > solo/app.py
output=$(printf '{"tool_input":{"file_path":"%s/solo/app.py"}}' "$tmpdir" |
  CLAUDE_PROJECT_DIR="$tmpdir/solo" bash "$FORMAT_PY_HOOK" 2>&1 || true)
assert_output_contains "Python hook reports isort missing instead of pairing with PATH" \
  "isort not found" "$output"
assert_output_not_contains "Python hook does not invoke an unpaired isort" \
  "isort " "$(cat "$FORMAT_PY_LOG")"
unset FORMAT_PY_LOG
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

# Run one tool call through the hook, capturing stdout AND exit status into
# globals. The status is captured in the CALLER's shell rather than discarded by
# a command substitution, because an ALLOW verdict is inferred from SILENT
# stdout: without it, a hook that died before printing would be scored "allowed"
# and every exemption assertion in this file would pass vacuously.
# Usage: rp_run <env-operand>... -- <tool> <input-field> <path>
rp_out=""
rp_last_status=0
rp_run() {
  local -a envargs=()
  while [ "$#" -gt 0 ] && [ "$1" != "--" ]; do envargs+=("$1"); shift; done
  [ "$#" -gt 0 ] || { echo "rp_run: missing '--' separator" >&2; exit 2; }
  shift  # drop the '--' separator
  set +e
  rp_out=$(rp_json "$1" "$2" "$3" | env "${envargs[@]+"${envargs[@]}"}" bash "$RESTRICT" 2>/dev/null)
  rp_last_status=$?
  set -e
}

# Verdict of the last rp_run. A non-zero exit is CRASH, never ALLOW — that is the
# whole point of threading the status through.
rp_verdict() {
  [ "$rp_last_status" -eq 0 ] || { echo "CRASH"; return; }
  rp_classify "$rp_out"
}

# Classify one tool call. Safe to use inside `$( )`: rp_run and rp_verdict both
# execute in that same subshell, so the exit status still reaches the verdict.
# rp_decision_env takes explicit `env` operands before a literal '--', for the
# fail-closed cases needing a non-standard environment (a non-resolving realpath
# stub on PATH, or HOME unset). rp_decision is the common case.
# Usage: rp_decision_env <env-operand>... -- <tool> <input-field> <path>
rp_decision_env() {
  rp_run "$@"
  rp_verdict
}

rp_decision() { # $1=tool $2=input-field $3=path  ->  ALLOW | ASK | DENY | OTHER
  rp_decision_env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" -- "$1" "$2" "$3"
}

# Simulate a platform with NO realpath and NO cygpath (older macOS, distroless
# images) — the only way to reach normalize()'s cd/pwd fallback, which is where
# the '//tmp' splice happens. Done by overriding the `command` builtin rather
# than stripping PATH: on Windows a bash reached through a stripped PATH cannot
# load its own DLLs, so the hook would die instead of taking the fallback.
# (The existing $rp_stub_bin models a DIFFERENT platform: a realpath that exists
# but rejects GNU's '-m'. Both shapes need coverage; neither implies the other.)
RP_NO_PATH_TOOLS='command() { if [ "$1" = "-v" ]; then case "$2" in realpath|cygpath) return 1 ;; esac; fi; builtin command "$@"; }'

# Extract one function from the hook and drive it directly. Used where the
# behaviour under test is a pure function of a string: a full tool call would
# return the same verdict with or without the guard, so it could not detect a
# regression in it.
# $1=prelude, $2=comma-separated function names to extract, $3=driver, $4...=args.
# Every helper the extracted function calls must be listed, or it dies with
# "command not found" and returns empty.
#
# Mind the failure mode that costs you: for a driver printing a VALUE (rp_collapse,
# rp_normalize_*) empty is a wrong answer and the assertion fails, as you want.
# But a driver shaped `pred "$1" && echo YES || echo NO` prints the FALSE token
# when the predicate is missing — bash returns 127, the `||` branch runs — so
# every negative assertion passes against a hook that does not exist. That is why
# each predicate below also carries at least one POSITIVE assertion: those are the
# ones that actually pin it. Do not add a predicate here with negatives only.
rp_drive_fn() {
  local prelude="$1" fns="$2" driver="$3"; shift 3
  local f="$rp_tmp/drive-fn.sh" fn
  {
    if [ -n "$prelude" ]; then printf '%s\n' "$prelude"; fi
    local IFS=','
    for fn in $fns; do awk "/^${fn}\\(\\) \\{/,/^\\}/" "$RESTRICT"; done
    printf '%s\n' "$driver"
  } > "$f"
  bash "$f" "$@"
}

rp_abs_path() { # $1=candidate -> ACCEPT | REJECT
  rp_drive_fn "" is_absolute_path 'is_absolute_path "$1" && echo ACCEPT || echo REJECT' "$1"
}

rp_normalize_no_realpath() { # $1=path -> normalized on a realpath-less platform
  rp_drive_fn "$RP_NO_PATH_TOOLS" collapse_dot_segments,normalize 'normalize "$1"' "$1"
}

# Normalize as MSYS/Cygwin would: a cygpath that maps backslashes to slashes and
# a realpath that PRESERVES a distinct '//' root. Stubbed rather than relying on
# the host, so the case is exercised on Linux CI too — and it is the only way to
# reach the branch where the OS spelling ('\\server\share') differs from the raw
# argument, which is exactly where probing "$1" instead of the post-cygpath
# string silently collapses a remote path onto an unrelated local one.
rp_collapse() { # $1=path -> lexically resolved, driving the function directly
  rp_drive_fn "" collapse_dot_segments \
    'collapse_dot_segments "$1"; printf "%s" "$_collapsed"' "$1"
}

# As rp_collapse, but from a CWD holding three known entries. The splitting loop
# is necessarily unquoted (that is what splits on IFS), so without `set -f` each
# segment is also pathname-expanded against the CWD — and a '*' segment that
# expands to N names absorbs N of the following '..'. The plain rp_collapse
# above cannot see this: it inherits the caller's CWD, so the match count (and
# therefore the resolved path) would depend on whatever the repo happens to
# contain that day.
rp_glob_cwd="$rp_tmp/globcwd"
mkdir -p "$rp_glob_cwd"
: > "$rp_glob_cwd/aaa"; : > "$rp_glob_cwd/bbb"; : > "$rp_glob_cwd/ccc"
rp_collapse_globcwd() { # $1=path -> lexically resolved, CWD = 3 known entries
  (cd "$rp_glob_cwd" && rp_drive_fn "" collapse_dot_segments \
    'collapse_dot_segments "$1"; printf "%s" "$_collapsed"' "$1")
}

# The two defensive predicates, driven directly. normalize() resolves '.' and
# '..' before any gate sees them, so these can no longer be reached through a
# tool call — removing either leaves the suite green. That is what makes a
# direct test the only thing standing between them and silent rot.
rp_has_traversal() { # $1=path -> YES | NO
  rp_drive_fn "" has_unresolved_traversal \
    'has_unresolved_traversal "$1" && echo YES || echo NO' "$1"
}

rp_single_segment() { # $1=segment -> YES | NO
  rp_drive_fn "" is_single_segment \
    'is_single_segment "$1" && echo YES || echo NO' "$1"
}

rp_normalize_msys() { # $1=path -> normalized with cygpath+distinct-// realpath
  local d="$rp_tmp/msysbin"
  if [ ! -x "$d/cygpath" ]; then
    mkdir -p "$d"
    printf '#!/bin/sh\neval last=\\${$#}\nprintf "%%s\\n" "$last" | tr "\\\\\\\\" "/"\n' > "$d/cygpath"
    printf '#!/bin/sh\neval last=\\${$#}\nprintf "%%s\\n" "$last"\n' > "$d/realpath"
    chmod +x "$d/cygpath" "$d/realpath"
  fi
  rp_drive_fn "export PATH=\"$d:\$PATH\"" collapse_dot_segments,normalize 'normalize "$1"' "$1"
}

# A copy of the hook that believes realpath and cygpath do not exist.
rp_make_norp_hook() {
  local out="$rp_tmp/hook-no-realpath.sh"
  { head -1 "$RESTRICT"; printf '%s\n' "$RP_NO_PATH_TOOLS"; tail -n +2 "$RESTRICT"; } > "$out"
  printf '%s\n' "$out"
}

# The verdict assertions read as `assert_decision <label> DENY <actual>`, which is
# worth its own name at the call site; the comparison itself is assert_equals'.
assert_decision() { # $1=label $2=expected $3=actual
  assert_equals "$1" "$2" "$3"
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
# The standard scratchpad environment, which most cases below use.
rp_run_scratch() { # $1=tool $2=input-field $3=path
  rp_run HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" TMPDIR="$scratch_root" -- "$1" "$2" "$3"
}

# Guard the guard: prove a dead hook scores CRASH, not ALLOW. Every ALLOW
# assertion in this file rests on rp_verdict consulting the exit status, so if
# this regressed they would all silently pass against a hook that never ran.
rp_saved_restrict="$RESTRICT"
RESTRICT="$rp_tmp/definitely-not-a-hook.sh"
assert_decision "Dead hook scores CRASH, not ALLOW (guard is not vacuous)" CRASH \
  "$(rp_decision_env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" -- Write file_path /nope)"
RESTRICT="$rp_saved_restrict"
assert_decision "Restore check: real hook scores again" ASK \
  "$(rp_decision_env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" -- Write file_path /nope)"

# A new file in an invented temp dir asks, and the reason carries the reminder.
rp_run_scratch Write file_path "$scratch_root/scratch-foo/x.md"
assert_decision "Invented temp dir write asks"        ASK "$(rp_verdict)"
assert_reason_has "Nudge reason mentions the scratchpad" "scratchpad"
assert_output_contains "Nudge reason names the file"  "$scratch_root/scratch-foo/x.md" "$rp_out"
assert_exit_zero "Nudge is a real decision, not a crash" "$rp_last_status"
# The nudge must NEVER deny — a deny cannot be approved by the user.
assert_reason_lacks "Nudge never denies" "deny"

rp_run_scratch NotebookEdit notebook_path "$scratch_root/scratch-foo/nb.ipynb"
assert_decision "Notebook in invented temp dir asks"  ASK "$(rp_verdict)"
rp_run_scratch Write file_path "$scratch_root/claude/E--proj/scratchpad/x.md"
assert_decision "Shallow scratchpad asks (not exempt)" ASK "$(rp_verdict)"

# A user-requested temp path must stay approvable — this is the case a deny broke.
rp_run_scratch Write file_path "$scratch_root/report.csv"
assert_decision "User-requested temp file asks"       ASK "$(rp_verdict)"

echo "[restrict-paths: nudge scope]"
# An EXISTING temp file, ~/.claude, and non-temp outside paths keep the plain
# prompt: the reminder is only meaningful when choosing where to put a new file.
rp_existing="$scratch_root/pre-existing/tool-output.md"
mkdir -p "$scratch_root/pre-existing"
: > "$rp_existing"
rp_run_scratch Edit file_path "$rp_existing"
assert_decision "Existing temp file edit asks"        ASK "$(rp_verdict)"
assert_reason_lacks "Existing temp file gets no nudge" "scratchpad"
rp_run_scratch Write file_path "$scratch_root/pre-existing/new.md"
assert_decision "New file in the same dir asks"       ASK "$(rp_verdict)"
rp_run HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" TMPDIR="$scratch_root" -- \
  Write file_path "/var/opt/optimus-not-temp/a.txt"
assert_decision "Non-temp outside path asks"          ASK "$(rp_verdict)"
assert_reason_lacks "Non-temp path gets no nudge" "scratchpad"

# ~/.claude is config, not scratch: it keeps the plain prompt even when HOME
# itself sits under the temp root (CI images), while the memory store stays exempt.
rp_temp_home="$scratch_root/ci-home"
mkdir -p "$rp_temp_home/.claude/projects/hash/memory"
rp_run HOME="$rp_temp_home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" TMPDIR="$scratch_root" -- \
  Write file_path "$rp_temp_home/.claude/settings.json"
assert_decision "HOME under temp root: settings.json asks" ASK "$(rp_verdict)"
assert_reason_lacks "settings.json gets no nudge" "scratchpad"
rp_run HOME="$rp_temp_home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" TMPDIR="$scratch_root" -- \
  Write file_path "$rp_temp_home/.claude/projects/hash/memory/M.md"
assert_decision "HOME under temp root: memory store allowed" ALLOW "$(rp_verdict)"
assert_exit_zero "Memory-store allow is real, not a crash" "$rp_last_status"

# REGRESSION: the veto is scoped to ~/.claude, NOT to all of $HOME. A whole-$HOME
# veto silently disabled the nudge wherever the temp root lives under the home
# dir (TMPDIR=$HOME/tmp, MSYS2/Cygwin default mounts) — the common case, not a
# rare one. The nudge must still fire there.
mkdir -p "$rp_tmp/home/tmp"
rp_run HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" TMPDIR="$rp_tmp/home/tmp" -- \
  Write file_path "$rp_tmp/home/tmp/invented/x.md"
assert_decision "Temp root under HOME still asks"     ASK "$(rp_verdict)"
assert_reason_has "Temp root under HOME still nudges" "scratchpad"

# A traversal the platform's realpath cannot resolve must not be reasoned about.
rp_run HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" TMPDIR="$scratch_root" PATH="$rp_stub_bin:$PATH" -- \
  Write file_path "$scratch_root/scratch-foo/../../x.md"
assert_decision "Unresolved traversal asks"           ASK "$(rp_verdict)"

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
  Write file_path "$scratch_root/scratch-foo/x.md"
assert_reason_has "Trailing-slash temp root still nudges" "scratchpad"
rp_run HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" TMPDIR="$scratch_root/" PATH="$rp_stub_bin:$PATH" -- \
  Write file_path "$scratch_root/scratch-foo/x.md"
assert_reason_has "Non-GNU realpath still nudges" "scratchpad"

# A RELATIVE temp root must be rejected outright: normalize() resolves it against
# the hook's working directory, which would make an arbitrary sibling of the
# project an auto-allowed subtree — exempt from the prompt AND the rm hard-block.
# The hook's CWD is what makes '../relbase' dangerous, so it has to be controlled
# here: run from $rp_tmp/cwd, where '../relbase' really does name the scratchpad
# tree below. Without the cd these two cases pass for the wrong reason — the
# generic out-of-project rules answer DENY/ASK whether or not the guard exists.
mkdir -p "$rp_tmp/relbase/claude/a/b/scratchpad" "$rp_tmp/cwd"
assert_decision "Relative temp root cannot exempt a delete" DENY \
  "$(cd "$rp_tmp/cwd" && rp_decision_env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" TMPDIR="../relbase" -- \
     Bash command "rm $rp_tmp/relbase/claude/a/b/scratchpad/f.txt")"
assert_decision "Relative temp root cannot exempt a write" ASK \
  "$(cd "$rp_tmp/cwd" && rp_decision_env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" TMPDIR="../relbase" -- \
     Write file_path "$rp_tmp/relbase/claude/a/b/scratchpad/f.md")"
# Control: the SAME tree named by an absolute temp root IS exempt, which is what
# proves the two assertions above are answering about the relative-path guard.
assert_decision "Same tree via an absolute temp root is exempt" ALLOW \
  "$(cd "$rp_tmp/cwd" && rp_decision_env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" TMPDIR="$rp_tmp/relbase" -- \
     Write file_path "$rp_tmp/relbase/claude/a/b/scratchpad/f.md")"

# A UNC temp root (\\server\share) must still resolve: cygpath maps it to
# //server/share. Rejecting it silently disables the scratchpad exemption AND
# turns every scratchpad cleanup delete into a hard block.
assert_decision "UNC temp root is accepted as absolute" ACCEPT \
  "$(rp_abs_path '\\server\share\temp')"
assert_decision "Drive-relative \\temp is still rejected" REJECT \
  "$(rp_abs_path '\temp')"
assert_decision "Relative ../scratch is still rejected" REJECT \
  "$(rp_abs_path '../scratch')"

# A filesystem root is not a usable temp root — treating '/' as one would make
# every absolute path "under the temp root".
rp_run HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" TMPDIR="/" -- \
  Write file_path "$scratch_root/scratch-foo/x.md"
assert_decision "Root temp dir degrades to a plain ask" ASK "$(rp_verdict)"

# The reason interpolates raw environment values, so a control character in the
# temp root (a CRLF-sourced TEMP on Windows is the easy way to get one) must not
# reach the output: a bare control char makes the decision unparseable JSON,
# which the harness reads as "no decision" — silently dropping the prompt.
rp_tab_root="$(printf '%s/tab\there' "$scratch_root")"
rp_run HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" TMPDIR="$rp_tab_root" -- \
  Write file_path "$rp_tab_root/inv/x.md"
assert_decision "Control char in temp root still asks" ASK "$(rp_verdict)"
assert_reason_lacks "Reason escapes control characters" "$(printf '\t')"

# Deletes under the temp root stay hard-blocked — the nudge is for writes only.
rp_run_scratch Bash command "rm $scratch_root/scratch-foo/x.md"
assert_decision "Temp-root delete stays blocked"      DENY "$(rp_verdict)"
assert_reason_has "Delete block is a plain block" "Cannot delete"

echo "[restrict-paths: Bash command extraction and git protection]"
# The command value is a JSON string: extraction must walk over escaped quotes,
# not stop at the first \" — truncating there silently skipped EVERY Bash guard
# for commands as ordinary as `git commit -m "msg" && ...`.
assert_decision "Guard survives a quoted prefix" DENY \
  "$(rp_decision Bash command 'echo \"hi\" && rm /outside/victim.txt')"
# A pipe hands the delete to xargs; the rm guard must see through the wrapper.
assert_decision "Piped xargs rm outside project denied" DENY \
  "$(rp_decision Bash command "find . | xargs rm $rp_tmp/outside/a.txt")"
assert_decision "Piped xargs -0 rm outside project denied" DENY \
  "$(rp_decision Bash command "find . -print0 | xargs -0 rm $rp_tmp/outside/a.txt")"
assert_decision "Piped xargs rm inside project allowed" ALLOW \
  "$(rp_decision Bash command "find . | xargs rm $rp_tmp/proj/src/a.txt")"

# Branch protection resolves the CURRENT branch via git, so these fixtures need
# a real checkout on a protected branch — a bare directory cannot exercise them.
rp_git="$rp_tmp/gitrepo"
mkdir -p "$rp_git"
git -C "$rp_git" init -q -b master 2>/dev/null \
  || { git -C "$rp_git" init -q && git -C "$rp_git" checkout -q -b master; }
git -C "$rp_git" -c user.email=t@t -c user.name=t -c commit.gpgsign=false \
  commit -q --allow-empty -m init
rp_git_decision() { # $1=raw JSON command value
  rp_decision_env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_git" -- Bash command "$1"
}
assert_decision "Push to protected branch denied"      DENY  "$(rp_git_decision 'git push origin master')"
# HEAD/@ name the current branch indirectly — they must resolve, not fail open.
assert_decision "Push via HEAD refspec denied"         DENY  "$(rp_git_decision 'git push origin HEAD')"
assert_decision "Push via @ refspec denied"            DENY  "$(rp_git_decision 'git push origin @')"
assert_decision "Push to feature branch allowed"       ALLOW "$(rp_git_decision 'git push origin feature-x')"
assert_decision "Push HEAD to feature refspec allowed" ALLOW "$(rp_git_decision 'git push origin HEAD:feature-x')"
# -Df bundles --delete and --force into one short-flag cluster.
assert_decision "Bundled -Df branch delete denied"     DENY  "$(rp_git_decision 'git branch -Df master')"
assert_decision "Bundled -Df feature delete allowed"   ALLOW "$(rp_git_decision 'git branch -Df feature-x')"
assert_decision "Commit with quoted message still guarded" DENY \
  "$(rp_git_decision 'git commit -m \"fix: something\"')"

echo "[restrict-paths: command-parsing bypasses]"
# Every case here is the SAME command a plain-spelling assertion above already
# blocks, respelled the way a shell ordinarily lets you spell it. Each one used
# to be allowed silently, so the hard blocks were one quote / one '&' / one
# wrapper word away from being no-ops. Both guards are covered: a regression in
# the fragment splitter or the command-word walk breaks rm AND git at once.

# Quotes and expansions. `read -ra` performs no quote removal, so the word kept
# its quote marks and normalize() resolved it RELATIVE to the project root.
assert_decision "Double-quoted out-of-project rm denied" DENY \
  "$(rp_decision Bash command "rm \\\"$rp_tmp/outside/a.txt\\\"")"
assert_decision "Single-quoted out-of-project rm denied" DENY \
  "$(rp_decision Bash command "rm '$rp_tmp/outside/a.txt'")"
assert_decision "Quoted path containing a space denied" DENY \
  "$(rp_decision Bash command "rm \\\"$rp_tmp/outside/a b.txt\\\"")"
assert_decision "Tilde-relative rm denied" DENY \
  "$(rp_decision Bash command 'rm ~/.bashrc')"
assert_decision "\$HOME-relative rm denied" DENY \
  "$(rp_decision Bash command 'rm $HOME/.ssh/id_rsa')"
assert_decision "\${HOME}-relative rm denied" DENY \
  "$(rp_decision Bash command 'rm ${HOME}/.ssh/id_rsa')"
# Quoting must not create a FALSE block either: a message that merely reads
# like a delete is an argument of git, not a command.
assert_decision "Quoted 'rm' inside a commit message allowed" ALLOW \
  "$(rp_decision Bash command 'git commit -m \"rm /etc/passwd from the docs\"')"
assert_decision "Quoted \$HOME inside a commit message allowed" ALLOW \
  "$(rp_decision Bash command 'git commit -m \"drop $HOME handling\"')"

# The single '&' background operator, and the keywords a compound command
# leaves at the head of a fragment. The old sed splitter emitted no newline for
# a lone '&', and every guard was anchored at the fragment's first token.
assert_decision "Backgrounded rm outside project denied" DENY \
  "$(rp_decision Bash command "true & rm $rp_tmp/outside/a.txt")"
assert_decision "rm inside a for-loop body denied" DENY \
  "$(rp_decision Bash command "for f in a; do rm $rp_tmp/outside/a.txt; done")"
assert_decision "rm inside an if body denied" DENY \
  "$(rp_decision Bash command "if true; then rm $rp_tmp/outside/a.txt; fi")"
assert_decision "Backgrounded push to protected branch denied" DENY \
  "$(rp_git_decision 'true & git push origin master')"
assert_decision "Push to protected branch in a loop body denied" DENY \
  "$(rp_git_decision 'for f in a; do git push origin master; done')"
assert_decision "Quoted protected branch name denied" DENY \
  "$(rp_git_decision 'git push origin \"master\"')"
# A backslash-newline is a line CONTINUATION, not a separator. Split on the
# newline, the delete became a flagless `rm` (whose only argument the gate skips
# as a flag) plus a bare path with no command word — so neither half tripped the
# gate while the shell joined them and performed the delete.
assert_decision "Line-continued rm outside project denied" DENY \
  "$(rp_decision Bash command "rm -rf \\\\\\n$rp_tmp/outside/a.txt")"

# Wrapper prefixes. The rm guard recognized only a bare `xargs` with valueless
# flags, while the git guard already handled `command`/`env` — the two are now
# one walk, so they cannot drift apart again.
assert_decision "xargs with a valued flag denied" DENY \
  "$(rp_decision Bash command "find . | xargs -n 1 rm $rp_tmp/outside/a.txt")"
assert_decision "xargs -I placeholder denied" DENY \
  "$(rp_decision Bash command "find . | xargs -I {} rm $rp_tmp/outside/a.txt")"
assert_decision "sudo rm denied" DENY \
  "$(rp_decision Bash command "sudo rm $rp_tmp/outside/a.txt")"
assert_decision "command rm denied" DENY \
  "$(rp_decision Bash command "command rm $rp_tmp/outside/a.txt")"
assert_decision "env VAR=val rm denied" DENY \
  "$(rp_decision Bash command "env FOO=bar rm $rp_tmp/outside/a.txt")"
assert_decision "Absolute-path rm denied" DENY \
  "$(rp_decision Bash command "/bin/rm $rp_tmp/outside/a.txt")"
assert_decision "Backslash-escaped rm denied" DENY \
  "$(rp_decision Bash command "\\\\rm $rp_tmp/outside/a.txt")"
assert_decision "timeout-wrapped rm denied" DENY \
  "$(rp_decision Bash command "timeout 5 rm $rp_tmp/outside/a.txt")"
assert_decision "sudo-wrapped push to protected branch denied" DENY \
  "$(rp_git_decision 'sudo git push origin master')"
# A wrapper option whose value is a SEPARATE word. The walk used to end ON the
# value and report "runs some other command", so one such option turned both
# guards off while the bare spelling stayed blocked. The `xargs -n 1` and
# `-I {}` cases above passed only because a digit and '{}' have cases of their
# own — a value that is an ordinary word had none.
assert_decision "sudo with a valued flag still denies rm" DENY \
  "$(rp_decision Bash command "sudo -u root rm $rp_tmp/outside/a.txt")"
assert_decision "sudo with a valued LONG flag still denies rm" DENY \
  "$(rp_decision Bash command "sudo --user root rm $rp_tmp/outside/a.txt")"
assert_decision "xargs -a <file> still denies rm" DENY \
  "$(rp_decision Bash command "find . | xargs -a list.txt rm $rp_tmp/outside/a.txt")"
assert_decision "sudo with a valued flag still denies push" DENY \
  "$(rp_git_decision 'sudo -u root git push origin master')"
# Only the VALUE is skipped: a real command still ends the walk, or
# `sudo -u root somecmd rm` would read as a delete it is not.
assert_decision "a wrapper value does not swallow a real command" ALLOW \
  "$(rp_decision Bash command "sudo -u root somecmd rm $rp_tmp/outside/a.txt")"
# The walk must still stop at a real command: `grep` is not a wrapper, so its
# argument can never be read as a delete target.
assert_decision "grep for an rm pattern allowed" ALLOW \
  "$(rp_decision Bash command "grep -r \\\"rm -rf\\\" $rp_tmp/proj")"

# A shell invoked with -c carries its whole command inside ONE argument, so no
# walk over the fragment's tokens can reach it — the wrapper list is the wrong
# tool for the job and adding sh/bash to it would not have helped. One `sh -c`
# used to switch BOTH guards off at once.
assert_decision "sh -c rm outside project denied" DENY \
  "$(rp_decision Bash command "sh -c \\\"rm -rf $rp_tmp/outside/a.txt\\\"")"
assert_decision "bash -c rm outside project denied" DENY \
  "$(rp_decision Bash command "bash -c \\\"rm $rp_tmp/outside/a.txt\\\"")"
assert_decision "eval rm outside project denied" DENY \
  "$(rp_decision Bash command "eval rm $rp_tmp/outside/a.txt")"
assert_decision "sudo sh -c rm outside project denied" DENY \
  "$(rp_decision Bash command "sudo sh -c \\\"rm -rf $rp_tmp/outside/a.txt\\\"")"
assert_decision "sh -ec bundled flag denied" DENY \
  "$(rp_decision Bash command "sh -ec \\\"rm $rp_tmp/outside/a.txt\\\"")"
assert_decision "sh -c push to protected branch denied" DENY \
  "$(rp_git_decision 'sh -c \"git push origin master\"')"
# A non-flag argument to a shell is a SCRIPT PATH, not a command string, and an
# `echo` of one is neither — unwrapping either would be a false block.
assert_decision "bash <script> is not unwrapped" ALLOW \
  "$(rp_decision Bash command 'bash scripts/build.sh')"
assert_decision "echo of an sh -c string allowed" ALLOW \
  "$(rp_decision Bash command "echo sh -c \\\"rm $rp_tmp/outside/a.txt\\\"")"
assert_decision "sh -c rm inside project allowed" ALLOW \
  "$(rp_decision Bash command "sh -c \\\"rm $rp_tmp/proj/src/a.txt\\\"")"
# The bundle must be tested for the LETTER 'c', not for a flag that merely ENDS
# in one: '--norc' matched, so the payload handed back was the following token —
# the literal '-c' — and both guards were skipped for the real command.
assert_decision "bash --norc -c rm denied" DENY \
  "$(rp_decision Bash command "bash --norc -c \\\"rm -rf $rp_tmp/outside/a.txt\\\"")"
assert_decision "bash --norc -c push denied" DENY \
  "$(rp_git_decision 'bash --norc -c \"git push origin master\"')"
assert_decision "bash --rcfile takes a value, then -c" DENY \
  "$(rp_decision Bash command "bash --rcfile f -c \\\"rm $rp_tmp/outside/a.txt\\\"")"
# ...and the letter need not be LAST in the bundle.
assert_decision "sh -cx bundled flag denied" DENY \
  "$(rp_decision Bash command "sh -cx \\\"rm $rp_tmp/outside/a.txt\\\"")"
# '-O <shopt>' takes a separate-word value exactly as '-o' does. Matching only
# the lowercase letter left the shopt name to read as a script path, which ended
# the walk — one sibling option turned both guards off.
assert_decision "bash -O shopt then -c denied" DENY \
  "$(rp_decision Bash command "bash -O extglob -c \\\"rm -rf $rp_tmp/outside/a.txt\\\"")"
assert_decision "bash +O shopt then -c denied" DENY \
  "$(rp_decision Bash command "bash +O histexpand -c \\\"rm -rf $rp_tmp/outside/a.txt\\\"")"

# `env -S '<cmd>'` carries a whole command inside one argument exactly as
# `sh -c` does. Listing -S among the flags whose value is skipped ended the walk
# ON the payload, so the fragment reported "runs some other command".
assert_decision "env -S payload is unwrapped" DENY \
  "$(rp_decision Bash command "env -S \\\"rm -rf $rp_tmp/outside/a.txt\\\"")"
assert_decision "env --split-string= payload is unwrapped" DENY \
  "$(rp_decision Bash command "env --split-string=\\\"rm -rf $rp_tmp/outside/a.txt\\\"")"
# ...without claiming a fragment that merely sets variables before a real shell.
assert_decision "env VAR=val sh -c still reaches the shell branch" DENY \
  "$(rp_decision Bash command "env FOO=bar sh -c \\\"rm -rf $rp_tmp/outside/a.txt\\\"")"

# A wrapper flag belongs in the skip list ONLY if its value is required and can
# be a separate word. Listing an optional or attached-only flag consumes the
# COMMAND instead: the walk ends on it, reports "runs some other command", and
# BOTH guards go off for a spelling as ordinary as `find . | xargs -i rm ...`.
assert_decision "xargs -i does not swallow the command" DENY \
  "$(rp_decision Bash command "xargs -i rm -rf $rp_tmp/outside/a.txt")"
assert_decision "xargs --replace does not swallow the command" DENY \
  "$(rp_decision Bash command "xargs --replace rm -rf $rp_tmp/outside/a.txt")"
assert_decision "xargs --max-lines does not swallow the command" DENY \
  "$(rp_decision Bash command "xargs --max-lines rm -rf $rp_tmp/outside/a.txt")"
assert_decision "sudo -h is --help, not a host flag" DENY \
  "$(rp_decision Bash command "sudo -h rm $rp_tmp/outside/a.txt")"
assert_decision "xargs -i does not hide a protected push" DENY \
  "$(rp_git_decision 'xargs -i git push origin master')"
# ...and the flags whose value IS required must still be skipped, or the value
# itself ends the walk.
assert_decision "xargs -I {} still reaches the rm" DENY \
  "$(rp_decision Bash command "xargs -I {} rm -rf $rp_tmp/outside/a.txt")"
assert_decision "xargs -L 1 still reaches the rm" DENY \
  "$(rp_decision Bash command "xargs -L 1 rm -rf $rp_tmp/outside/a.txt")"
assert_decision "xargs -E END still reaches the rm" DENY \
  "$(rp_decision Bash command "xargs -E END rm -rf $rp_tmp/outside/a.txt")"

# Only the LAST flag of a short cluster can take a separate-word value, so the
# cluster has to be tested by its last letter. Testing the whole post-dash
# remainder meant `-Hu` never matched `u`: the walk stepped onto the username,
# ended there, and one extra letter disarmed both guards.
assert_decision "sudo -Hu bundled user flag denied" DENY \
  "$(rp_decision Bash command "sudo -Hu root rm $rp_tmp/outside/a.txt")"
assert_decision "sudo -Eu bundled user flag denied" DENY \
  "$(rp_decision Bash command "sudo -Eu root rm $rp_tmp/outside/a.txt")"
assert_decision "sudo -Hu does not hide a protected push" DENY \
  "$(rp_git_decision 'sudo -Hu root git push origin master')"
# The long spelling is still matched WHOLE — a long name is one option, not a
# cluster, so its last letter means nothing.
assert_decision "sudo --user long flag denied" DENY \
  "$(rp_decision Bash command "sudo --user root rm $rp_tmp/outside/a.txt")"

# An exported variable whose name matches one of the hook's own globals was
# captured with the HOOK's value by the environment snapshot — `${!name}` reads
# the shell namespace, not the environment. Every global is _rp_-prefixed so no
# user-exported name can collide.
assert_decision "exported 'root' is the caller's, not the hook's" DENY \
  "$(rp_decision_env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" \
     root="$rp_tmp/outside" -- Bash command 'rm -rf $root/a.txt')"
assert_decision "exported 'cmd' is the caller's, not the hook's" DENY \
  "$(rp_decision_env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" \
     cmd="$rp_tmp/outside" -- Bash command 'rm -rf $cmd/a.txt')"
assert_decision "exported 'tool_name' is the caller's, not the hook's" DENY \
  "$(rp_decision_env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" \
     tool_name="$rp_tmp/outside" -- Bash command 'rm -rf $tool_name/a.txt')"

# A redirection names a stream. Counted as a delete target it produced an
# unappealable deny on `rm <in-project> > /dev/null`; counted as a refspec it
# gave `git push` two positionals, so the guard checked '/dev/null' against the
# protected list instead of resolving the current branch.
assert_decision "rm with a spaced redirect allowed" ALLOW \
  "$(rp_decision Bash command "rm -rf $rp_tmp/proj/src/a.txt > /dev/null")"
assert_decision "rm with a glued redirect allowed" ALLOW \
  "$(rp_decision Bash command "rm -rf $rp_tmp/proj/src/a.txt >/dev/null")"
assert_decision "rm with an fd redirect allowed" ALLOW \
  "$(rp_decision Bash command "rm -rf $rp_tmp/proj/src/a.txt 2>/dev/null")"
assert_decision "rm with an append redirect allowed" ALLOW \
  "$(rp_decision Bash command "rm -rf $rp_tmp/proj/src/a.txt >> $rp_tmp/proj/log.txt")"
assert_decision "redirect does not excuse an outside rm" DENY \
  "$(rp_decision Bash command "rm -rf $rp_tmp/outside/a.txt > /dev/null")"
assert_decision "push with a spaced redirect denied"  DENY "$(rp_git_decision 'git push > /dev/null')"
assert_decision "push remote + spaced redirect denied" DENY "$(rp_git_decision 'git push origin > /dev/null')"
assert_decision "push with a glued redirect denied"   DENY "$(rp_git_decision 'git push >/dev/null')"
assert_decision "push --quiet + redirect denied"      DENY "$(rp_git_decision 'git push --quiet > /dev/null')"

# A relative delete target means "relative to the chain's cd", not to whatever
# directory the hook happens to run in. Resolved against the latter, every one
# of these read as an IN-project delete while the shell removed a file outside.
assert_decision "cd outside then relative rm denied" DENY \
  "$(rp_decision Bash command "cd $rp_tmp/outside && rm a.txt")"
assert_decision "cd outside then rm '.' denied" DENY \
  "$(rp_decision Bash command "cd $rp_tmp/outside && rm -rf .")"
assert_decision "subshell cd then relative rm denied" DENY \
  "$(rp_decision Bash command "(cd $rp_tmp/outside; rm a.txt)")"
assert_decision "cd in-project then relative rm allowed" ALLOW \
  "$(rp_decision Bash command "cd $rp_tmp/proj/src && rm a.txt")"
# As rp_decision, but with the PROJECT directory as CWD — which is how Claude
# Code invokes the hook, and the only setting in which a relative path in a
# command resolves to what the shell would actually act on. rp_decision inherits
# the suite's own CWD, so every relative path there lands outside the fixture
# project and denies for a reason that has nothing to do with the guard.
rp_decision_cwd() { # $1=command -> ALLOW | ASK | DENY | OTHER
  (cd "$rp_tmp/proj" && rp_decision Bash command "$1")
}
assert_decision "relative rm with no cd stays allowed" ALLOW \
  "$(rp_decision_cwd 'rm -rf build/out')"

# A variable this hook cannot see is a path it cannot judge. A caller's shell
# variable is not exported, so substituting the empty string collapsed the word
# to a leading '/', which every gate then read as an absolute path outside the
# project — a hard deny, with no prompt and no override, on ordinary
# build-directory cleanup.
assert_decision "unset var delete target allowed" ALLOW \
  "$(rp_decision_cwd 'RP_UNSET_DIR=build && rm -rf $RP_UNSET_DIR/x')"
assert_decision "unset braced var allowed" ALLOW \
  "$(rp_decision_cwd 'rm -rf ${RP_UNSET_DIR}/dist')"
assert_decision "unset var with a glob allowed" ALLOW \
  "$(rp_decision_cwd 'rm -rf $RP_UNSET_DIR/*')"
assert_decision "unset var inside a loop allowed" ALLOW \
  "$(rp_decision_cwd 'for d in a b; do rm -rf $d/tmp; done')"
# An EXPORTED name is one the hook can see, so it must still expand — that is
# the hole the literal fallback must not reopen.
assert_decision "\$HOME still expands to a denied path" DENY \
  "$(rp_decision_cwd 'rm -rf $HOME/.ssh/id_rsa')"
# "Can the hook see this name?" was answered with an INDIRECT expansion, which
# resolves against the whole shell namespace — the hook's own globals and,
# because bash scopes `local` dynamically, the locals of every function on the
# stack. A command that merely mentioned one of those names was judged against
# the HOOK's value and hard-denied a path the user never wrote. Only the
# environment is genuinely shared with the caller's shell.
assert_decision "a name shadowing a hook local stays literal" ALLOW \
  "$(rp_decision_cwd 'out=dist && rm -rf $out/assets')"
assert_decision "a set-but-empty hook local stays literal" ALLOW \
  "$(rp_decision_cwd 'q=queue && rm -rf $q/tmp')"
assert_decision "braced form stays literal too" ALLOW \
  "$(rp_decision_cwd 'rm -rf ${out}/dist')"
assert_decision "a mid-parse hook local stays literal" ALLOW \
  "$(rp_decision_cwd 'rm -rf $rest/x')"

# A LEADING expansion this hook does not perform can hide the root: the word
# keeps its '/' inside syntax expand_word leaves alone, so is_absolute_path
# answered "relative" and normalize() re-based it on the project root — both the
# out-of-project block and the precious-file block were skipped.
assert_decision "ANSI-C quoted absolute target asks" ASK \
  "$(rp_decision_cwd "rm \$'/etc/passwd'")"
assert_decision "brace-hidden absolute target asks" ASK \
  "$(rp_decision_cwd 'rm {,}/etc/passwd')"
assert_decision "~user home target asks" ASK \
  "$(rp_decision_cwd 'rm ~root/.ssh/id_rsa')"
# ...but ONLY leading. Brace and $-expansion both keep whatever precedes them, so
# a word with any prefix stays relative however it expands. Matching anywhere in
# the word prompted on ordinary in-project cleanups AND — worse — downgraded a
# settled hard deny, because an absolute out-of-project path that happens to
# contain '$(' is already denied and an ask hands back a bypass.
assert_decision "in-project brace expansion does not prompt" ALLOW \
  "$(rp_decision_cwd 'rm -rf dist/{js,css}')"
assert_decision "in-project command substitution does not prompt" ALLOW \
  "$(rp_decision_cwd 'rm -rf build/$(date +%Y)')"
assert_decision "outside path with a substitution stays DENIED" DENY \
  "$(rp_decision_cwd "rm -rf $rp_tmp/outside/\$(whoami)")"
assert_decision "outside path with a brace stays DENIED" DENY \
  "$(rp_decision_cwd "rm -rf $rp_tmp/outside/{a,b}")"

# A `cd` COMPOSES with the one before it. Replacing re-based every later relative
# target on the LAST cd alone, so a chain that walked back out resolved the
# delete outside the project and hard-DENIED an ordinary cleanup.
assert_decision "cd in, cd out, then relative rm allowed" ALLOW \
  "$(rp_decision_cwd 'cd src && cd .. && rm -rf build')"
assert_decision "cd in, cd out, then rm that subtree allowed" ALLOW \
  "$(rp_decision_cwd 'cd src && cd .. && rm -rf src/out')"
# A subshell's cd must not outlive its ')' — the fragment splitter used to strip
# the parens and let it stand for the rest of the chain.
assert_decision "subshell cd does not leak past ')'" ALLOW \
  "$(rp_decision_cwd '(cd /tmp && ./deploy.sh) && rm -rf build')"
# `cd -` returns to the PREVIOUS directory, so it is resolved rather than
# guessed. Guessing "the project root" was right only for a chain that had moved
# exactly once — and wrong in the unsafe direction for every chain that moved
# twice, where the shell lands back OUTSIDE and a relative rm went with it.
assert_decision "cd - returns to the project root" ALLOW \
  "$(rp_decision_cwd 'cd /tmp && cd - && rm -rf build')"
assert_decision "cd - after two moves lands outside" DENY \
  "$(rp_decision_cwd "cd $rp_tmp/outside && cd /tmp && cd - && rm a.txt")"
# The cd tracker walks a wrapper prefix like every other command word here.
# Matching a bare first token was the only spelling it knew.
assert_decision "builtin cd then relative rm denied" DENY \
  "$(rp_decision_cwd "builtin cd $rp_tmp/outside && rm a.txt")"
assert_decision "pushd then relative rm denied" DENY \
  "$(rp_decision_cwd "pushd $rp_tmp/outside && rm a.txt")"

# Every spelling below moves the shell somewhere the hook used to answer "the
# project root" for. Each one silently permitted an out-of-project delete: the
# guess was applied to `popd`, to a bare `cd` and to any `cd` whose arguments
# were all flags, none of which go there.
assert_decision "popd on an empty stack does not move" DENY \
  "$(rp_decision_cwd "cd $rp_tmp/outside && popd && rm a.txt")"
assert_decision "bare cd goes HOME, not to the project" DENY \
  "$(rp_decision_cwd "cd $rp_tmp/outside && cd && rm a.txt")"
assert_decision "cd -P goes HOME, not to the project" DENY \
  "$(rp_decision_cwd "cd $rp_tmp/outside && cd -P && rm a.txt")"
assert_decision "cd -- goes HOME, not to the project" DENY \
  "$(rp_decision_cwd "cd $rp_tmp/outside && cd -- && rm a.txt")"
# ...and the pairing has to work in the other direction too, or an ordinary
# push/pop around a build step hard-denies the cleanup after it.
assert_decision "pushd then popd returns to the project" ALLOW \
  "$(rp_decision_cwd "pushd $rp_tmp/outside && popd && rm -rf build")"
assert_decision "nested pushd unwinds one level per popd" DENY \
  "$(rp_decision_cwd "pushd $rp_tmp/outside && pushd /tmp && popd && rm a.txt")"
# `-n` pushes or pops WITHOUT changing directory — the whole point of the flag —
# and a '+N' operand rotates the stack rather than naming a directory. Reading
# either as a cd turned an in-project delete into an unappealable DENY.
assert_decision "pushd -n does not move the shell" ALLOW \
  "$(rp_decision_cwd "pushd -n $rp_tmp/outside && rm -rf build")"
assert_decision "popd -n does not move the shell" ALLOW \
  "$(rp_decision_cwd 'cd build && popd -n && rm -rf out')"
assert_decision "popd +1 is a rotation, not a directory" ALLOW \
  "$(rp_decision_cwd 'cd build && popd +1 && rm -rf out')"

# The subshell close is COUNTED, not inferred from a trailing ')'. That test was
# wrong both ways: it banked a close for the ')' of a command substitution, which
# released the subshell's cd early and allowed an out-of-project delete; and it
# missed a real close followed by a redirection, which kept the cd in force and
# hard-denied an ordinary in-project cleanup.
assert_decision "command substitution is not a subshell close" DENY \
  "$(rp_decision_cwd "(cd $rp_tmp/outside && echo \$(date) && rm a.txt)")"
assert_decision "arithmetic expansion is not a subshell close" DENY \
  "$(rp_decision_cwd "(cd $rp_tmp/outside && n=\$((1+2)) && rm a.txt)")"
assert_decision "process substitution is not a subshell close" DENY \
  "$(rp_decision_cwd "(cd $rp_tmp/outside && diff <(ls) <(ls) && rm a.txt)")"
assert_decision "single-quoted paren is not a subshell close" DENY \
  "$(rp_decision_cwd "(cd $rp_tmp/outside && echo 'a)b' && rm a.txt)")"
# The quote marks have to survive into the command string, so they are escaped
# for JSON here — an unescaped '\"' truncates the payload and the assertion
# passes for the wrong reason.
assert_decision "double-quoted paren is not a subshell close" DENY \
  "$(rp_decision_cwd "(cd $rp_tmp/outside && echo \\\"a)b\\\" && rm a.txt)")"
assert_decision "close followed by a redirection still closes" ALLOW \
  "$(rp_decision_cwd "(cd $rp_tmp/outside && ls) 2>&1 && rm -rf build")"

# A wrapper option can move the command with no `cd` in sight. The walk already
# had to step over the value to reach the command word; discarding it meant the
# relative target was resolved against the project root while the process ran
# somewhere else entirely.
assert_decision "sudo -D chdir is tracked" DENY \
  "$(rp_decision_cwd "sudo -D $rp_tmp/outside rm a.txt")"
assert_decision "sudo --chdir= chdir is tracked" DENY \
  "$(rp_decision_cwd "sudo --chdir=$rp_tmp/outside rm a.txt")"
assert_decision "env -C chdir is tracked" DENY \
  "$(rp_decision_cwd "env -C $rp_tmp/outside rm a.txt")"
# ...and it applies to THIS fragment only: the wrapper chdirs the process it
# spawns, not the shell, so nothing after the fragment inherits it.
assert_decision "wrapper chdir does not leak to the next fragment" ALLOW \
  "$(rp_decision_cwd "env -C $rp_tmp/outside ls && rm -rf build")"

# Deleting a protected branch was blocked; MOVING one was not, though it loses
# exactly as much. `git update-ref` does it with no branch subcommand at all,
# and works even on the checked-out branch, where `git branch -f` refuses.
assert_decision "branch -f onto protected denied"   DENY  "$(rp_git_decision 'git branch -f master HEAD~1')"
assert_decision "branch --force onto protected denied" DENY "$(rp_git_decision 'git branch --force master HEAD~1')"
assert_decision "branch -M rename onto protected denied" DENY "$(rp_git_decision 'git branch -M feature-x master')"
assert_decision "branch -m rename onto protected denied" DENY "$(rp_git_decision 'git branch -m feature-x master')"
assert_decision "update-ref on protected denied"    DENY  "$(rp_git_decision 'git update-ref refs/heads/master HEAD')"
# A start-point is READ, not written — creating a feature branch off master is
# the single most ordinary thing this rule could have broken.
assert_decision "branch -f feature FROM master allowed" ALLOW \
  "$(rp_git_decision 'git branch -f feature-x master')"
assert_decision "branch -f feature alone allowed"   ALLOW "$(rp_git_decision 'git branch -f feature-x')"
assert_decision "update-ref on feature allowed"     ALLOW "$(rp_git_decision 'git update-ref refs/heads/feature-x HEAD')"
assert_decision "update-ref --stdin fails open"     ALLOW "$(rp_git_decision 'git update-ref --stdin')"
# Read-only flags that merely contain an f/m/M must not read as a force.
assert_decision "branch --list is not a rewrite"    ALLOW "$(rp_git_decision 'git branch --list')"
assert_decision "branch -a is not a rewrite"        ALLOW "$(rp_git_decision 'git branch -a')"
assert_decision "branch --format is not a force"    ALLOW "$(rp_git_decision 'git branch --format=%(refname)')"
assert_decision "branch --merged is not a move"     ALLOW "$(rp_git_decision 'git branch --merged')"
# A copy (-c/-C/--copy) overwrites its DESTINATION exactly as a force-move does,
# and it was simply absent from the rewrite flags — `git branch -C feature
# master` rewrote master and was allowed.
assert_decision "branch -C copy onto protected denied" DENY \
  "$(rp_git_decision 'git branch -C feature-x master')"
assert_decision "branch --copy onto protected denied" DENY \
  "$(rp_git_decision 'git branch --copy feature-x master')"
# A copy writes its LAST argument; the source before it is only READ. The source
# has to be a PROTECTED branch for this to test anything — with two feature names
# the answer is ALLOW whichever end the copy arm picks, so the assertion passed
# against a hook that had no copy arm at all. Snapshotting master before a rebase
# is the ordinary shape it protects, and getting it wrong denies it unappealably.
assert_decision "branch -c copy FROM a protected branch allowed" ALLOW \
  "$(rp_git_decision 'git branch -c master backup-x')"
assert_decision "branch -c copy FROM a feature allowed" ALLOW \
  "$(rp_git_decision 'git branch -c feature-x backup-x')"
# `git branch -m <new>` renames the CHECKED-OUT branch — the name it destroys is
# never on the command line, so this arm has to resolve it like its siblings do.
assert_decision "single-arg -m rename off master denied" DENY \
  "$(rp_git_decision 'git branch -m archived')"
assert_decision "single-arg -M rename off master denied" DENY \
  "$(rp_git_decision 'git branch -M archived')"
# git's own global options are not the subcommand's: the '-c' of
# `git -c k=v branch <name>` configures git, and reading it as a branch copy
# would deny an ordinary branch create.
assert_decision "git -c global option is not a branch copy" ALLOW \
  "$(rp_git_decision 'git -c user.name=x branch feature-y')"

# A backup suffix must not launder a file off the hard precious list. These run
# against is_precious_name directly: the delete gate needs an untracked file to
# exist in a git repo, and the classification is what a regression would break.
rp_precious_name() { # $1=basename -> PRECIOUS | RECOVERABLE | ORDINARY
  rp_drive_fn "" strip_backup_suffix,is_precious_name,basename_of,precious_basename,is_recoverable_precious,is_recoverable_precious_name \
    'if is_precious_name "$1"; then echo PRECIOUS
     elif is_recoverable_precious "$1"; then echo RECOVERABLE
     else echo ORDINARY; fi' "$1"
}
assert_decision ".env is precious"              PRECIOUS    "$(rp_precious_name '.env')"
assert_decision ".env.bak stays precious"       PRECIOUS    "$(rp_precious_name '.env.bak')"
assert_decision "id_rsa.pem.bak stays precious" PRECIOUS    "$(rp_precious_name 'id_rsa.pem.bak')"
assert_decision "app.sqlite.bak stays precious" PRECIOUS    "$(rp_precious_name 'app.sqlite.bak')"
assert_decision "credentials.json.bak stays precious" PRECIOUS "$(rp_precious_name 'credentials.json.bak')"
# '.bak' was never the only laundering suffix — every one of these strips a
# suffix-anchored pattern ('*.key', '*.pem', '*.sqlite', '*.dump') off the hard
# list just as effectively, and re-testing the stem for '.bak' alone closed one
# instance of the trick rather than the trick.
assert_decision "id_rsa.pem.old stays precious"    PRECIOUS "$(rp_precious_name 'id_rsa.pem.old')"
assert_decision "server.key.backup stays precious" PRECIOUS "$(rp_precious_name 'server.key.backup')"
assert_decision "server.key.1 stays precious"      PRECIOUS "$(rp_precious_name 'server.key.1')"
assert_decision "db.sqlite~ stays precious"        PRECIOUS "$(rp_precious_name 'db.sqlite~')"
assert_decision "app.sqlite.orig stays precious"   PRECIOUS "$(rp_precious_name 'app.sqlite.orig')"
assert_decision "prod.dump.save stays precious"    PRECIOUS "$(rp_precious_name 'prod.dump.save')"
assert_decision "keystore.jks.backup stays precious" PRECIOUS "$(rp_precious_name 'keystore.jks.backup')"
assert_decision "appsettings.dev.json.old stays precious" PRECIOUS \
  "$(rp_precious_name 'appsettings.dev.json.old')"
assert_decision "stacked suffixes stay precious" PRECIOUS "$(rp_precious_name 'id_rsa.pem.old.bak')"
# The reason the recoverable class exists: a deny goes to Claude, not the user,
# so an ordinary backup must stay deletable — including the harness's own.
assert_decision "notes.txt.bak is recoverable"  RECOVERABLE "$(rp_precious_name 'notes.txt.bak')"
assert_decision "harness progress .bak is recoverable" RECOVERABLE \
  "$(rp_precious_name 'code-review-deep-progress.json.bak')"
assert_decision "*.suo is recoverable"          RECOVERABLE "$(rp_precious_name 'proj.suo')"
assert_decision "notes.txt is ordinary"         ORDINARY    "$(rp_precious_name 'notes.txt')"
# The wider suffix set belongs to is_precious_name ONLY. Widening the recoverable
# trigger list to match would start prompting before every overwrite of a rotated
# log or a merge leftover — files with nothing precious about them.
assert_decision "notes.txt.old is ordinary"     ORDINARY    "$(rp_precious_name 'notes.txt.old')"
assert_decision "access.log.1 is ordinary"      ORDINARY    "$(rp_precious_name 'access.log.1')"
assert_decision "main.py.orig is ordinary"      ORDINARY    "$(rp_precious_name 'main.py.orig')"
# A name that is nothing BUT a suffix must terminate the strip/re-test recursion.
assert_decision "bare '.bak' terminates"        RECOVERABLE "$(rp_precious_name '.bak')"
assert_decision "bare '~' terminates"           ORDINARY    "$(rp_precious_name '~')"

# The delete GATE, not the classifier above. What reached production was the
# gate's EXPRESSION — `is_precious && ! is_recoverable_precious`, which expands
# to (hard || recoverable) && !recoverable, so a name on BOTH lists resolved to
# unprotected. Every classifier assertion above kept passing while '.env.suo'
# was silently deletable, so these drive the real hook against real files.
for rp_pf in .env .env.suo .env.local.user credentials.suo secrets.user proj.suo notes.txt.bak; do
  : > "$rp_git/$rp_pf"
done
assert_decision "delete .env denied"            DENY  "$(rp_git_decision "rm $rp_git/.env")"
assert_decision "delete .env.suo denied"        DENY  "$(rp_git_decision "rm $rp_git/.env.suo")"
assert_decision "delete .env.local.user denied" DENY  "$(rp_git_decision "rm $rp_git/.env.local.user")"
assert_decision "delete credentials.suo denied" DENY  "$(rp_git_decision "rm $rp_git/credentials.suo")"
assert_decision "delete secrets.user denied"    DENY  "$(rp_git_decision "rm $rp_git/secrets.user")"
# ...and the recoverable class is still recoverable: a deny here reaches the
# model, not the user, so it could never be overridden.
assert_decision "delete proj.suo allowed"       ALLOW "$(rp_git_decision "rm $rp_git/proj.suo")"
assert_decision "delete notes.txt.bak allowed"  ALLOW "$(rp_git_decision "rm $rp_git/notes.txt.bak")"

# Claude Code spells file_path with backslashes on Windows, and splitting on '/'
# alone left the WHOLE path as the basename — which no prefix or exact precious
# pattern can match, so protection was silently off there for both the edit ask
# and the delete block. OSTYPE is forced rather than read, so both platform
# behaviours are pinned wherever this suite runs: off Windows a backslash is a
# legal FILENAME character and must NOT split.
rp_basename() { # $1=OSTYPE $2=path -> basename
  rp_drive_fn "OSTYPE=$1" basename_of 'basename_of "$1"; printf "%s" "$_basename"' "$2"
}
assert_decision "win basename splits on backslash"   '.env' \
  "$(rp_basename msys 'C:\Users\me\proj\.env')"
assert_decision "win basename of credentials.json"   'credentials.json' \
  "$(rp_basename msys 'C:\proj\credentials.json')"
assert_decision "win basename still splits on slash" '.env' \
  "$(rp_basename msys 'C:/Users/me/proj/.env')"
assert_decision "win basename with mixed separators" '.env' \
  "$(rp_basename cygwin 'C:\Users\me/proj\.env')"
assert_decision "posix keeps a backslash in the name" 'a\b' \
  "$(rp_basename linux-gnu 'a\b')"
assert_decision "posix basename unchanged"           '.env' \
  "$(rp_basename linux-gnu '/home/me/proj/.env')"

echo "[restrict-paths: path normalization]"
# EXACTLY two leading slashes are a UNC network root on MSYS/Cygwin, but plain
# '/' on Linux/glibc — POSIX leaves the case implementation-defined. normalize()
# must AGREE with whatever the platform's realpath does, so the expected verdict
# is DERIVED from a probe rather than hardcoded. Hardcoding ASK here passed on
# Cygwin and failed the whole suite on the ubuntu-latest CI runner.
if [ "$(realpath -m -- //probe/x 2>/dev/null)" = "/probe/x" ]; then
  rp_unc_expect=ALLOW    # '//' collapses to '/': //proj IS the project
else
  # Distinct root kept — or realpath ERRORED (present but no '-m', macOS 13+):
  # normalize() preserves the // root on failure, so only a positive collapse
  # predicts ALLOW. An empty probe result must never read as "collapsed".
  rp_unc_expect=ASK
fi
assert_decision "UNC-style //path follows the platform ($rp_unc_expect)" "$rp_unc_expect" \
  "$(rp_decision_env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" -- Write file_path "/$rp_tmp/proj/x.txt")"
assert_decision "Triple-slash path collapses to in-project" ALLOW \
  "$(rp_decision_env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" -- Write file_path "//$rp_tmp/proj/x.txt")"
# A '.' segment must not satisfy a single-segment slot in EITHER exemption shape.
# Both slots need their own case: they are separate call sites of the same
# predicate, so covering one leaves the other free to regress.
assert_decision "Dot segment cannot stand in for <project> (scratchpad)" ASK \
  "$(rp_decision_env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" TMPDIR="$scratch_root" PATH="$rp_stub_bin:$PATH" -- Write file_path "$scratch_root/claude/./session-uuid/scratchpad/x.md")"
assert_decision "Dot segment cannot stand in for <project> (memory store)" ASK \
  "$(rp_decision_env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" PATH="$rp_stub_bin:$PATH" -- Write file_path "$rp_tmp/home/.claude/projects/./memory/M.md")"

# The project-root gate is the FIRST rung of the exemption ladder, so a traversal
# that escapes it is never seen by the guarded gates below. On a platform whose
# realpath leaves '..' in place, a path that merely starts with the project
# prefix must not be auto-allowed — for writes OR for the rm hard-block.
mkdir -p "$rp_tmp/victim"
: > "$rp_tmp/victim/.env"
assert_decision "Project-root traversal cannot auto-allow a write" ASK \
  "$(rp_decision_env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" PATH="$rp_stub_bin:$PATH" -- Write file_path "$rp_tmp/proj/../victim/.env")"
assert_decision "Project-root traversal cannot bypass the rm block" DENY \
  "$(rp_decision_env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" PATH="$rp_stub_bin:$PATH" -- Bash command "rm -f $rp_tmp/proj/../victim/.env")"
# Control: the same gate must still recognise the project root spelled exactly.
assert_decision "Project root itself is in-project" ALLOW \
  "$(rp_decision_env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" -- Write file_path "$rp_tmp/proj")"

# ...and the same escape dressed up with a glob. The hook runs with its CWD set
# to the project root, so an unguarded split expands a '*' segment into one name
# per entry there; those extra segments swallow the '..' and the path reads as
# in-project to every gate while the OS still resolves it outside. Run from a CWD
# with three known entries so the assertion does not depend on the repo's shape.
# The '*' directory the OS needs is free: Write mkdir -p's its parent.
assert_decision "Glob segment cannot absorb a traversal (write)" ASK \
  "$(cd "$rp_glob_cwd" && rp_decision_env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" PATH="$rp_stub_bin:$PATH" -- Write file_path "$rp_tmp/proj/*/../../victim/.env")"
assert_decision "Glob segment cannot bypass the rm block" DENY \
  "$(cd "$rp_glob_cwd" && rp_decision_env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" PATH="$rp_stub_bin:$PATH" -- Bash command "rm -f $rp_tmp/proj/*/../../victim/.env")"
# Control: a literal '*' in a filename is an ordinary in-project write, not a
# traversal — the guard must not turn it into a prompt.
assert_decision "Literal '*' in an in-project filename still allowed" ALLOW \
  "$(cd "$rp_glob_cwd" && rp_decision_env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" PATH="$rp_stub_bin:$PATH" -- Write file_path "$rp_tmp/proj/star*file.txt")"

echo "[restrict-paths: no realpath at all (cd/pwd fallback)]"
# $rp_stub_bin models a realpath that EXISTS and rejects '-m'. A realpath that is
# absent entirely is a different platform (older macOS, distroless) and reaches
# normalize()'s cd/pwd branch, which splices '//tmp' when the parent is '/'.
# Nothing else in this file exercises that branch.
assert_decision "normalize collapses a spliced //tmp"  "/tmp"     "$(rp_normalize_no_realpath /tmp)"
assert_decision "normalize collapses a spliced //var"  "/var"     "$(rp_normalize_no_realpath /var)"
assert_decision "normalize leaves an ordinary path"    "/tmp/a/b" "$(rp_normalize_no_realpath /tmp/a/b)"
assert_decision "normalize collapses ///tmp/x"         "/tmp/x"   "$(rp_normalize_no_realpath ///tmp/x)"
assert_decision "normalize keeps a genuine UNC root"   "//srv/share" "$(rp_normalize_no_realpath //srv/share)"

# End-to-end on that platform: a project root whose parent is '/' must still be
# recognised. When the splice survived, every in-project write prompted and every
# in-project delete was hard-denied.
rp_norp_hook="$(rp_make_norp_hook)"
rp_saved_restrict="$RESTRICT"
RESTRICT="$rp_norp_hook"
assert_decision "Top-level project write allowed (no realpath)" ALLOW \
  "$(rp_decision_env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR=/proj -- Write file_path /proj/src/a.txt)"
assert_decision "Top-level project delete allowed (no realpath)" ALLOW \
  "$(rp_decision_env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR=/proj -- Bash command "rm /proj/src/a.txt")"
# With HOME and USERPROFILE both unset, normalize("") would resolve to the hook's
# own CWD on this platform. The memory-store exemption must fail CLOSED instead
# of anchoring itself on whatever directory the hook happened to run in.
mkdir -p "$rp_tmp/cwd/.claude/projects/x/memory"
assert_decision "Unset HOME cannot anchor the store on CWD (write)" ASK \
  "$(cd "$rp_tmp/cwd" && rp_decision_env -u HOME -u USERPROFILE CLAUDE_PROJECT_DIR="$rp_tmp/proj" -- \
     Write file_path "$rp_tmp/cwd/.claude/projects/x/memory/f.md")"
assert_decision "Unset HOME cannot anchor the store on CWD (delete)" DENY \
  "$(cd "$rp_tmp/cwd" && rp_decision_env -u HOME -u USERPROFILE CLAUDE_PROJECT_DIR="$rp_tmp/proj" -- \
     Bash command "rm $rp_tmp/cwd/.claude/projects/x/memory/f.md")"
RESTRICT="$rp_saved_restrict"

echo "[restrict-paths: prompt audiences and wording]"
# A PreToolUse "ask" shows permissionDecisionReason to the USER and gives
# additionalContext to CLAUDE. The scratchpad reminder is the part only Claude
# can act on, so it must ride additionalContext — carrying it in the reason
# delivers it to the one party that cannot act on it.
rp_run_scratch Write file_path "$scratch_root/scratch-foo/x.md"
assert_reason_has  "Nudge carries additionalContext for Claude" '"additionalContext"'
assert_reason_has  "additionalContext names the scratchpad" "scratchpad directory given in your system prompt"
assert_reason_has  "User-facing reason names the file" "$scratch_root/scratch-foo/x.md"
assert_decision    "Nudge is still only an ask"       ASK "$(rp_verdict)"
# The reminder must live ONLY in additionalContext. Asserting over the whole
# payload cannot see that — it contains both fields — so isolate the user-facing
# reason first. Checking for the pre-fix wording instead would be vacuous: that
# string no longer exists anywhere, so duplicating the reminder into the reason
# would still pass.
rp_reason_only() { # -> just the permissionDecisionReason value of the last run
  printf '%s' "$rp_out" | sed 's/.*"permissionDecisionReason":"//; s/","additionalContext".*//; s/"}}$//'
}
assert_output_not_contains "Reminder is not duplicated into the user reason" \
  "scratchpad directory given in your system prompt" "$(rp_reason_only)"
assert_output_contains "Isolated reason still names the file (extractor works)" \
  "$scratch_root/scratch-foo/x.md" "$(rp_reason_only)"

# The noun and verb belong to the tool, and must survive BOTH prompt paths.
# NOTE: $rp_tmp is itself under /tmp, so a path below it is under the temp root
# and takes the NUDGE path. The plain-prompt cases need a genuinely non-temp
# path, or they silently assert about the wrong branch.
rp_plain_out="/var/opt/optimus-not-temp"
rp_run HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" -- \
  NotebookEdit notebook_path "$rp_plain_out/nb.ipynb"
assert_reason_has   "Plain notebook prompt says 'Notebook'" "Notebook '"
assert_reason_has   "Plain notebook prompt says 'edit'"     "Allow this edit?"
assert_reason_lacks "Plain notebook prompt is not nudged"   "additionalContext"
rp_run HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" -- \
  Write file_path "$rp_plain_out/plain.txt"
assert_reason_has "Plain write prompt says 'File' and 'write'" \
  "File '$rp_plain_out/plain.txt' is outside project root. Allow this write?"
# ...and the same two words on the nudge path, which builds its own sentence.
rp_run_scratch NotebookEdit notebook_path "$scratch_root/scratch-foo/nb.ipynb"
assert_reason_has "Nudged notebook keeps its noun" "Notebook '"
assert_reason_has "Nudged notebook keeps its verb" "Allow this edit?"
assert_reason_has "Nudged notebook is really nudged" '"additionalContext"'

# A '..' that normalize() CAN resolve is judged on where it actually lands, not
# refused: '<temp>/scratch-foo/../../x.md' resolves to a path still under the
# temp root, so the nudge is correct there.
rp_run HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" TMPDIR="$scratch_root" PATH="$rp_stub_bin:$PATH" -- \
  Write file_path "$scratch_root/scratch-foo/../../x.md"
assert_decision "Resolvable traversal is judged on its target" ASK "$(rp_verdict)"
# ...but a path that stays unresolvable after normalize() — a RELATIVE one, which
# has no root to anchor '..' against — must never reach the nudge or an auto-allow.
rp_run HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" TMPDIR="$scratch_root" PATH="$rp_stub_bin:$PATH" -- \
  Write file_path "../../x.md"
assert_decision   "Unanchored relative traversal still asks" ASK "$(rp_verdict)"
assert_reason_lacks "Unanchored relative traversal is not nudged" "additionalContext"

# An existing file reached through a phantom intermediate directory is not new.
mkdir -p "$scratch_root/phantom-check"
: > "$scratch_root/phantom-check/real.md"
rp_run_scratch Write file_path "$scratch_root/phantom-check/nope/../real.md"
assert_reason_lacks "Existing file via a phantom dir is not called new" "is a new file"

echo "[restrict-paths: dot-segment resolution]"
# normalize() resolves '.' and '..' itself, so a gate never has to fail closed on
# an ORDINARY in-project path that contains them. Without that, on a platform
# whose realpath rejects '-m' an in-project 'a/../b' became an unapprovable hard
# DENY (a deny goes to the model, never the user). Both platform shapes below.
mkdir -p "$rp_tmp/proj/existing"
for rp_plat in "gnu-realpath" "no-dash-m"; do
  if [ "$rp_plat" = "no-dash-m" ]; then rp_env=(PATH="$rp_stub_bin:$PATH"); else rp_env=(); fi
  assert_decision "In-project '..' write allowed ($rp_plat)" ALLOW \
    "$(rp_decision_env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" ${rp_env[@]+"${rp_env[@]}"} -- \
       Write file_path "$rp_tmp/proj/existing/../src/a.txt")"
  assert_decision "In-project '..' delete allowed ($rp_plat)" ALLOW \
    "$(rp_decision_env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" ${rp_env[@]+"${rp_env[@]}"} -- \
       Bash command "rm $rp_tmp/proj/existing/../src/a.txt")"
  # ...while a '..' that genuinely ESCAPES the project is still caught on both.
  assert_decision "Escaping '..' write asks ($rp_plat)" ASK \
    "$(rp_decision_env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" ${rp_env[@]+"${rp_env[@]}"} -- \
       Write file_path "$rp_tmp/proj/../victim/.env")"
  assert_decision "Escaping '..' delete denied ($rp_plat)" DENY \
    "$(rp_decision_env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" ${rp_env[@]+"${rp_env[@]}"} -- \
       Bash command "rm -f $rp_tmp/proj/../victim/.env")"
done
# Through normalize() on a realpath-less platform...
assert_decision "normalize resolves a/../b"        "/x/b"  "$(rp_normalize_no_realpath /x/a/../b)"
assert_decision "normalize drops '.' segments"     "/x/b"  "$(rp_normalize_no_realpath /x/./b)"
assert_decision "normalize keeps a dotted filename" "/x/a..b" "$(rp_normalize_no_realpath /x/a..b)"
assert_decision "normalize resolves under a UNC root" "//srv/share/b" "$(rp_normalize_no_realpath //srv/share/a/../b)"
# ...and the resolver driven DIRECTLY. Going through normalize() cannot pin these:
# the cd/pwd fallback resolves many of them before collapse_dot_segments is even
# reached, so a broken resolver would still score green.
assert_decision "collapse: a/../b"                 "/x/b"      "$(rp_collapse /x/a/../b)"
assert_decision "collapse: drops '.'"              "/x/b"      "$(rp_collapse /x/./b)"
assert_decision "collapse: cannot climb above /"   "/b"        "$(rp_collapse /../../b)"
assert_decision "collapse: '/..' is '/'"           "/"         "$(rp_collapse /..)"
assert_decision "collapse: trailing '..'"          "/x"        "$(rp_collapse /x/y/..)"
assert_decision "collapse: keeps a dotted filename" "/x/a..b"  "$(rp_collapse /x/a..b)"
assert_decision "collapse: preserves a UNC root"   "//srv/share/b" "$(rp_collapse //srv/share/a/../b)"
# Climbing off the end of a UNC path lands on the bare namespace root '//'. That
# is degenerate rather than wrong, and resolve_scratch_bases refuses it as a temp
# root for the same reason it refuses '/': it would prefix-match everything.
assert_decision "collapse: UNC cannot climb above its root" "//" "$(rp_collapse //srv/../..)"
# A RELATIVE path has no root to anchor '..' against, so leading '..' must stay —
# that is what leaves has_unresolved_traversal a real case to fail closed on.
assert_decision "collapse: relative keeps leading '..'" "../x" "$(rp_collapse ../x)"
assert_decision "collapse: relative resolves what it can" "../b" "$(rp_collapse ../a/../b)"
# Glob metacharacters must survive the split as ONE literal segment. Without the
# `set -f` guard a '*' expands to every name in the CWD, so it consumes several
# '..' that were meant to climb — the resolved path then lands arbitrarily deep
# inside the project instead of outside it. (CWD here holds aaa, bbb, ccc.)
assert_decision "collapse: '*' segment stays literal"   "/x/*/y" "$(rp_collapse_globcwd '/x/*/y')"
assert_decision "collapse: '?' segment stays literal"   "/x/?bb/y" "$(rp_collapse_globcwd '/x/?bb/y')"
assert_decision "collapse: '[..]' segment stays literal" "/x/[ab]/y" "$(rp_collapse_globcwd '/x/[ab]/y')"
assert_decision "collapse: '*' consumes exactly one '..'" "/x/y" "$(rp_collapse_globcwd '/x/*/../y')"
assert_decision "collapse: '*' cannot absorb a climb out" "/y" "$(rp_collapse_globcwd '/x/*/../../y')"

echo "[restrict-paths: defensive predicates]"
# These two are backstops behind normalize()'s central resolution, so no tool
# call can reach them any more — delete either and every end-to-end assertion
# still passes. Pin them directly, or they rot silently while looking guarded.
assert_decision "traversal: bare '..'"            YES "$(rp_has_traversal '..')"
assert_decision "traversal: leading '../'"        YES "$(rp_has_traversal '../x')"
assert_decision "traversal: embedded '/../'"      YES "$(rp_has_traversal '/a/../b')"
assert_decision "traversal: trailing '/..'"       YES "$(rp_has_traversal '/a/..')"
assert_decision "traversal: ordinary path"        NO  "$(rp_has_traversal '/a/b')"
assert_decision "traversal: dotted filename"      NO  "$(rp_has_traversal '/a/b..c')"
assert_decision "traversal: filename ending '..'" NO  "$(rp_has_traversal '/a/b..')"
assert_decision "segment: ordinary"               YES "$(rp_single_segment 'proj-1')"
assert_decision "segment: empty"                  NO  "$(rp_single_segment '')"
assert_decision "segment: '.'"                    NO  "$(rp_single_segment '.')"
assert_decision "segment: '..'"                   NO  "$(rp_single_segment '..')"
assert_decision "segment: contains a slash"       NO  "$(rp_single_segment 'a/b')"
assert_decision "segment: dotted name is fine"    YES "$(rp_single_segment 'a..b')"

# A UNC root spelled the NATIVE Windows way. cygpath is what turns it into
# '//server/share', so the UNC probe has to read the post-cygpath spelling — not
# the raw argument, which never starts with '//'. Getting that wrong collapses
# every backslash-spelled UNC path onto an unrelated local path, so a remote
# \\server\share\x compares equal to a local /server/share/x and the scratchpad
# exemption dies whenever the two spellings disagree.
assert_decision "Backslash UNC keeps its // root" "//server/share/temp" \
  "$(rp_normalize_msys '\\server\share\temp')"
assert_decision "Slash UNC keeps its // root"     "//server/share/temp" \
  "$(rp_normalize_msys '//server/share/temp')"
assert_decision "Both UNC spellings normalize alike" "$(rp_normalize_msys '//server/share/x')" \
  "$(rp_normalize_msys '\\server\share\x')"
assert_decision "Remote UNC never collides with a local path" DIFFERENT \
  "$([ "$(rp_normalize_msys '\\server\share\x')" != "$(rp_normalize_msys '/server/share/x')" ] \
     && echo DIFFERENT || echo COLLIDED)"

echo "[restrict-paths: JSON escaping and errexit]"
# A reason interpolates raw environment values. Every C0 code point JSON gives a
# short escape must get one — dropping 0x08/0x0C instead silently rewrites the
# path the user is approving.
rp_bs="$(printf 'a\bb')"; rp_ff="$(printf 'a\fb')"
rp_run HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" -- Write file_path "/out/$rp_bs.md"
assert_reason_has "Backspace is escaped as \\b, not dropped" 'a\bb'
rp_run HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" -- Write file_path "/out/$rp_ff.md"
assert_reason_has "Formfeed is escaped as \\f, not dropped" 'a\fb'
# Every decision must be parseable JSON — that is what makes escaping load-bearing.
# Probe by RUNNING the interpreter, not `command -v`: on Windows a bare `python`
# can resolve to the Store alias stub, which exists but cannot run anything
# (same probe validate.sh uses).
rp_py=""
if python3 --version >/dev/null 2>&1; then rp_py="python3"
elif python --version >/dev/null 2>&1; then rp_py="python"
fi
if [ -n "$rp_py" ]; then
  rp_run HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" -- \
    Write file_path "$(printf '/out/q"b\\s %%s\t%%d\bx.md')"
  if printf '%s' "$rp_out" | "$rp_py" -c 'import json,sys; json.loads(sys.stdin.read())' 2>/dev/null; then
    printf "  PASS  %s\n" "Decision is valid JSON for a hostile path"; ((pass++)) || true
  else
    printf "  FAIL  %s (unparseable: %s)\n" "Decision is valid JSON for a hostile path" "$rp_out"; ((errors++)) || true
  fi
else
  echo "  SKIP  JSON parse check (python not installed)"
fi

# An inherited errexit must not turn a prompt into silence. nudge_temp_write
# returns non-zero on the common path; without `|| true` the script aborts having
# printed nothing, which the harness reads as "no decision" and the write proceeds.
set +e
rp_ee_out=$(rp_json Write file_path "/var/opt/optimus-not-temp/new.txt" \
  | env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$rp_tmp/proj" bash -e "$RESTRICT" 2>/dev/null)
rp_ee_status=$?
set -e
assert_decision "Out-of-project write still decides under errexit" ASK "$(rp_classify "$rp_ee_out")"
assert_exit_zero "Hook exits 0 under errexit" "$rp_ee_status"

# The Write path alone is not enough, and covering only it is how a regression
# scored green. EVERY Bash guard runs through shell_split, whose counters start
# at 0 — and `(( i++ ))` evaluating to 0 returns exit status 1, so under errexit
# the hook aborts on the FIRST character of the FIRST fragment, before any
# decision is printed. Both hard blocks then silently stop existing, and only a
# Bash-side case can see it.
rp_ee_bash() { # $1=command $2=project dir -> ALLOW | ASK | DENY | OTHER | CRASH
  local out status
  set +e
  out=$(rp_json Bash command "$1" \
    | env HOME="$rp_tmp/home" CLAUDE_PROJECT_DIR="$2" bash -e "$RESTRICT" 2>/dev/null)
  status=$?
  set -e
  [ "$status" -eq 0 ] || { echo "CRASH"; return; }
  rp_classify "$out"
}
assert_decision "Push to protected branch decides under errexit" DENY \
  "$(rp_ee_bash 'git push origin master' "$rp_git")"
assert_decision "Out-of-project rm decides under errexit" DENY \
  "$(rp_ee_bash "rm -rf $rp_tmp/outside/a.txt" "$rp_tmp/proj")"
assert_decision "In-project rm stays silent under errexit" ALLOW \
  "$(rp_ee_bash "rm -rf $rp_tmp/proj/src/a.txt" "$rp_tmp/proj")"
assert_decision "Escaped word decides under errexit" DENY \
  "$(rp_ee_bash "rm -rf \\\\$rp_tmp/outside/a.txt" "$rp_tmp/proj")"

# ============================================================
# Summary
# ============================================================
echo
echo "=== Hook test results: $pass passed, $errors failed ==="
if [ "$errors" -gt 0 ]; then exit 1; else exit 0; fi
