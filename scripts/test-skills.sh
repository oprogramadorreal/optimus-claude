#!/usr/bin/env bash
# Automated skill execution tests using claude -p (headless mode).
# Runs optimus skills against generated fixtures and validates expected outputs.
#
# Requirements: claude CLI installed and authenticated (plan subscription or API key)
#
# Usage:
#   bash scripts/test-skills.sh                              # default: init + commit-message
#   bash scripts/test-skills.sh --skill init                 # test one skill
#   bash scripts/test-skills.sh --skill init --fixture node  # test one skill + one fixture
#   bash scripts/test-skills.sh --all                        # test all testable skills
#   bash scripts/test-skills.sh --fresh --all --worktree     # full run in isolated worktree
#   bash scripts/test-skills.sh --dry-run                    # show what would run

set -euo pipefail

ORIGINAL_ARGS=("$@")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FIXTURES_DIR="$PLUGIN_ROOT/test/fixtures"
EXPECTED_FILE="$PLUGIN_ROOT/test/expected-outputs.yaml"

# --- Defaults ---
MAX_TURNS=30
DRY_RUN=false
SKILL_FILTER=""
FIXTURE_FILTER=""
ALL_MODE=false
FRESH=false
WORKTREE=false

# --- Parse args ---
while [[ $# -gt 0 ]]; do
  case "$1" in
    --skill)    [[ $# -ge 2 ]] || { echo "Error: --skill requires a value"; exit 1; }; SKILL_FILTER="$2"; shift 2 ;;
    --fixture)  [[ $# -ge 2 ]] || { echo "Error: --fixture requires a value"; exit 1; }; FIXTURE_FILTER="$2"; shift 2 ;;
    --turns)    [[ $# -ge 2 ]] || { echo "Error: --turns requires a value"; exit 1; }; MAX_TURNS="$2"; shift 2 ;;
    --all)      ALL_MODE=true; shift ;;
    --fresh)    FRESH=true; shift ;;
    --worktree) WORKTREE=true; shift ;;
    --dry-run)  DRY_RUN=true; shift ;;
    --help|-h)
      echo "Usage: bash scripts/test-skills.sh [options]"
      echo "Options:"
      echo "  --skill <name>     Test specific skill (init, permissions, commit-message, how-to-run, prompt, branch)"
      echo "  --fixture <name>   Test against specific fixture (node, python, go, rust, csharp, monorepo, empty, multi-repo)"
      echo "  --all              Test all skill/fixture combinations"
      echo "  --fresh            Remove and regenerate all fixtures before testing"
      echo "  --worktree         Run in an isolated git worktree (keeps main tree free)"
      echo "  --turns <n>        Max agentic turns (default: 30)"
      echo "  --dry-run          Show what would run without executing"
      echo "  --help             Show this help"
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

# --- Validate flag combinations ---
if [ -z "$SKILL_FILTER" ] && [ -n "$FIXTURE_FILTER" ]; then
  echo "Error: --fixture requires --skill"; exit 1
fi

# --- Worktree isolation ---
# Creates a detached worktree inside .worktrees/skill-tests and re-invokes the
# script from there, so the user can keep working (switch branches, edit files)
# in the main tree while the worktree stays visible in the project directory.
if $WORKTREE; then
  WORKTREE_DIR="$PLUGIN_ROOT/.worktrees/skill-tests"
  mkdir -p "$PLUGIN_ROOT/.worktrees"

  # Remove stale worktree from previous run (may have been preserved for debugging)
  if [ -d "$WORKTREE_DIR" ]; then
    echo "Removing stale worktree (possibly from a previous failed run)..."
    git -C "$PLUGIN_ROOT" worktree remove "$WORKTREE_DIR" --force 2>/dev/null || true
    rm -rf "$WORKTREE_DIR" 2>/dev/null || true
  fi

  cleanup_worktree() {
    local rc=$?
    if [ "$rc" -ne 0 ]; then
      echo
      echo "Tests failed — worktree preserved at: .worktrees/skill-tests"
      echo "  To inspect: cd .worktrees/skill-tests/test/fixtures/"
      echo "  To clean up: git worktree remove .worktrees/skill-tests --force"
    else
      echo
      echo "Cleaning up worktree..."
      git -C "$PLUGIN_ROOT" worktree remove "$WORKTREE_DIR" --force 2>/dev/null || true
      rm -rf "$WORKTREE_DIR" 2>/dev/null || true
    fi
  }
  trap cleanup_worktree EXIT

  COMMIT_SHORT=$(git -C "$PLUGIN_ROOT" rev-parse --short HEAD)
  echo "Creating worktree at .worktrees/skill-tests (from $COMMIT_SHORT)..."
  git -C "$PLUGIN_ROOT" worktree add --detach "$WORKTREE_DIR" HEAD -q

  # Forward all args except --worktree
  FORWARDED_ARGS=()
  for arg in "${ORIGINAL_ARGS[@]}"; do
    [[ "$arg" == "--worktree" ]] && continue
    FORWARDED_ARGS+=("$arg")
  done

  bash "$WORKTREE_DIR/scripts/test-skills.sh" ${FORWARDED_ARGS[@]+"${FORWARDED_ARGS[@]}"}
  exit $?
fi

# --- Skill/fixture matrix ---
# Each entry: skill_name:fixture_name
if $ALL_MODE; then
  TEST_MATRIX=(
    "init:node-project"
    "init:python-project"
    "init:go-project"
    "init:rust-project"
    "init:csharp-project"
    "init:monorepo-project"
    "init:empty-project"
    "permissions:node-project"
    "commit-message:node-project"
    "how-to-run:node-project"
    "how-to-run:python-project"
    "prompt:node-project"
    "branch:node-project"
  )
elif [ -n "$SKILL_FILTER" ] && [ -n "$FIXTURE_FILTER" ]; then
  # Map fixture shorthand to directory name
  if [[ "$FIXTURE_FILTER" == "multi-repo" ]]; then
    TEST_MATRIX=("$SKILL_FILTER:multi-repo-workspace")
  elif [[ "$FIXTURE_FILTER" == *-project ]] || [[ "$FIXTURE_FILTER" == *-workspace ]]; then
    TEST_MATRIX=("$SKILL_FILTER:$FIXTURE_FILTER")
  else
    TEST_MATRIX=("$SKILL_FILTER:${FIXTURE_FILTER}-project")
  fi
elif [ -n "$SKILL_FILTER" ]; then
  # All fixtures for the given skill
  case "$SKILL_FILTER" in
    init) TEST_MATRIX=(
      "init:node-project" "init:python-project" "init:go-project"
      "init:rust-project" "init:csharp-project" "init:monorepo-project" "init:empty-project"
    ) ;;
    permissions)    TEST_MATRIX=("permissions:node-project") ;;
    commit-message) TEST_MATRIX=("commit-message:node-project") ;;
    how-to-run)     TEST_MATRIX=("how-to-run:node-project" "how-to-run:python-project") ;;
    prompt)         TEST_MATRIX=("prompt:node-project") ;;
    branch)         TEST_MATRIX=("branch:node-project") ;;
    *) echo "Unknown skill: $SKILL_FILTER. Supported: init, permissions, commit-message, how-to-run, prompt, branch"; exit 1 ;;
  esac
else
  # Default: quick smoke test
  TEST_MATRIX=(
    "init:node-project"
    "init:python-project"
    "commit-message:node-project"
  )
fi

# --- Helpers ---

errors=0
pass=0
skipped=0
CURRENT_WORK_DIR=""
trap 'if [ -n "$CURRENT_WORK_DIR" ] && [ -d "$CURRENT_WORK_DIR" ]; then rm -rf "$CURRENT_WORK_DIR"; fi' EXIT INT TERM

# System prompt that makes skills non-interactive
NONINTERACTIVE_PROMPT="IMPORTANT: Do NOT use the AskUserQuestion tool under any circumstances. For every decision point where the skill instructs you to ask the user, always choose the default or most common option and continue automatically. Never stop to ask for confirmation — just proceed. If the skill presents options like 'Fresh start' vs 'Update', choose 'Fresh start'. If asked about scope, choose 'Full project'. If asked about approval, approve all."

run_skill_test() {
  local skill="$1"
  local fixture="$2"
  local fixture_dir="$FIXTURES_DIR/$fixture"

  if [ ! -d "$fixture_dir" ]; then
    echo "  SKIP  $skill:$fixture (fixture not generated — run scripts/generate-fixtures.sh first)"
    ((skipped++)) || true
    return
  fi

  # For skills that modify files, work on a copy to keep fixtures clean
  local work_dir
  work_dir=$(mktemp -d)
  CURRENT_WORK_DIR="$work_dir"
  cp -r "$fixture_dir/." "$work_dir/"
  cd "$work_dir"

  # Determine the skill prompt
  local prompt
  case "$skill" in
    init)
      prompt="Run /optimus:init on this project. Analyze the project structure and set it up for AI-assisted development."
      ;;
    permissions)
      prompt="Run /optimus:permissions to set up branch protection and permission rules for this project."
      ;;
    commit-message)
      # Need some changes to analyze — test for file existence to avoid creating unexpected files
      if [ -f index.js ]; then
        echo "// new feature" >> index.js
      elif [ -f README.md ]; then
        echo "# new feature" >> README.md
      else
        echo "# new feature" > README.md
      fi
      prompt="Run /optimus:commit-message to suggest a conventional commit message for the current changes."
      ;;
    how-to-run)
      prompt="Run /optimus:how-to-run to generate a HOW-TO-RUN.md teaching a new developer how to set up their environment and run this project locally."
      ;;
    prompt)
      prompt="Run /optimus:prompt to craft an optimized prompt for the following idea: Write a Python function that parses CSV files and returns summary statistics."
      ;;
    branch)
      # Need uncommitted changes for branch to have context
      if [ -f index.js ]; then
        echo "// add auth middleware" >> index.js
      elif [ -f README.md ]; then
        echo "# add auth middleware" >> README.md
      else
        echo "# add auth middleware" > README.md
      fi
      prompt="Run /optimus:branch to create a properly named branch for the current changes."
      ;;
    *)
      echo "  ERROR  No prompt defined for skill: $skill"
      ((errors++)) || true
      cd "$PLUGIN_ROOT"
      rm -rf "$work_dir"
      CURRENT_WORK_DIR=""
      return
      ;;
  esac

  if $DRY_RUN; then
    echo "  DRY   $skill:$fixture"
    echo "        dir: $work_dir"
    echo "        prompt: $prompt"
    cd "$PLUGIN_ROOT"
    rm -rf "$work_dir"
    CURRENT_WORK_DIR=""
    return
  fi

  echo "  RUN   $skill:$fixture (max-turns: $MAX_TURNS)"

  # Snapshot git dirty count before claude runs (for files_not_modified checks)
  local git_dirty_before
  git_dirty_before=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')

  # Run claude in headless mode
  local claude_output
  local exit_code=0
  claude_output=$(claude -p "$prompt" \
    --append-system-prompt "$NONINTERACTIVE_PROMPT" \
    --dangerously-skip-permissions \
    --max-turns "$MAX_TURNS" \
    --output-format text \
    2>&1) || exit_code=$?

  if [ $exit_code -ne 0 ]; then
    if [ $exit_code -gt 1 ]; then
      echo "  FAIL  $skill:$fixture (claude exited with code $exit_code)"
      echo "        Output: $(echo "$claude_output" | head -5)"
      ((errors++)) || true
      cd "$PLUGIN_ROOT"
      rm -rf "$work_dir"
      CURRENT_WORK_DIR=""
      return
    else
      echo "  WARN  $skill:$fixture (claude exited with code $exit_code)"
    fi
  fi

  # Validate expected outputs
  validate_outputs "$skill" "$fixture" "$work_dir" "$claude_output" "$git_dirty_before"

  # Cleanup
  cd "$PLUGIN_ROOT"
  rm -rf "$work_dir"
  CURRENT_WORK_DIR=""
}

validate_outputs() {
  local skill="$1"
  local fixture="$2"
  local work_dir="$3"
  local claude_output="$4"
  local git_dirty_before="${5:-0}"
  local test_failed=false

  cd "$work_dir"

  # Parse expected outputs from YAML (simple line-by-line parser — no yq dependency)
  local in_skill=false
  local in_fixture=false
  local current_section=""
  local current_file=""

  while IFS= read -r line; do
    # Skip comments and empty lines
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "$line" ]] && continue

    # Skill level (no indentation)
    if [[ "$line" =~ ^([a-z0-9_-]+):$ ]]; then
      if [[ "${BASH_REMATCH[1]}" == "$skill" ]]; then
        in_skill=true
      else
        in_skill=false
      fi
      in_fixture=false
      current_section=""
      continue
    fi

    $in_skill || continue

    # Fixture level (2-space indent)
    if [[ "$line" =~ ^[[:space:]]{2}([a-z0-9_-]+):$ ]]; then
      if [[ "${BASH_REMATCH[1]}" == "$fixture" ]]; then
        in_fixture=true
      else
        in_fixture=false
      fi
      current_section=""
      continue
    fi

    $in_fixture || continue

    # Section headers (4-space indent)
    if [[ "$line" =~ ^[[:space:]]{4}(files_exist|files_not_exist|files_contain|files_not_modified|output_contains):[[:space:]]*(.*) ]]; then
      current_section="${BASH_REMATCH[1]}"
      local inline_value="${BASH_REMATCH[2]}"
      # Handle inline values like "files_exist: []" or "files_not_modified: true"
      if [[ "$inline_value" == "[]" ]]; then
        current_section=""
        continue
      fi
      if [[ "$inline_value" == "true" ]]; then
        if [[ "$current_section" == "files_not_modified" ]]; then
          # Check git status for new modifications (compare against pre-claude baseline)
          local modified
          modified=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
          local new_changes=$((modified - git_dirty_before))
          if [ "$new_changes" -gt 0 ]; then
            echo "        FAIL  files_not_modified: $new_changes new files changed"
            test_failed=true
          fi
        fi
        current_section=""
        continue
      fi
      current_file=""
      continue
    fi

    # File path in files_contain (6-space indent, ends with colon)
    if [[ "$current_section" == "files_contain" ]] && [[ "$line" =~ ^[[:space:]]{6}([^:]+):$ ]]; then
      current_file="${BASH_REMATCH[1]}"
      continue
    fi

    # List items (6 or 8-space indent with dash)
    if [[ "$line" =~ ^[[:space:]]{6,8}-[[:space:]]+\"?([^\"]*)\"?$ ]]; then
      local value="${BASH_REMATCH[1]}"

      case "$current_section" in
        files_exist)
          if [ ! -f "$value" ]; then
            echo "        FAIL  files_exist: $value (not found)"
            test_failed=true
          fi
          ;;
        files_not_exist)
          if [ -f "$value" ]; then
            echo "        FAIL  files_not_exist: $value (exists but shouldn't)"
            test_failed=true
          fi
          ;;
        files_contain)
          if [ -n "$current_file" ]; then
            if [ ! -f "$current_file" ]; then
              echo "        FAIL  files_contain: $current_file (file not found)"
              test_failed=true
            elif ! grep -qF "$value" "$current_file" 2>/dev/null; then
              echo "        FAIL  files_contain: $current_file should contain '$value'"
              test_failed=true
            fi
          fi
          ;;
        output_contains)
          if ! echo "$claude_output" | grep -qFi "$value"; then
            echo "        FAIL  output_contains: '$value' not in output"
            test_failed=true
          fi
          ;;
      esac
    fi
  done < "$EXPECTED_FILE"

  if $test_failed; then
    echo "  FAIL  $skill:$fixture"
    ((errors++)) || true
  else
    echo "  PASS  $skill:$fixture"
    ((pass++)) || true
  fi
}

# --- Pre-flight checks ---

echo "=== optimus-claude skill tests ==="
echo

# Check claude CLI is available
if ! command -v claude &>/dev/null; then
  echo "ERROR: claude CLI not found. Install it first: https://docs.anthropic.com/en/docs/claude-code"
  echo "       These tests require the claude CLI installed and authenticated."
  exit 1
fi

# Remove fixtures if --fresh
if $FRESH && [ -d "$FIXTURES_DIR" ]; then
  echo "Removing existing fixtures (--fresh)..."
  rm -rf "$FIXTURES_DIR"
fi

# Check fixtures exist
if [ ! -d "$FIXTURES_DIR" ]; then
  echo "Fixtures not found. Generating..."
  bash "$SCRIPT_DIR/generate-fixtures.sh"
  echo
fi

# Check expected outputs file
if [ ! -f "$EXPECTED_FILE" ]; then
  echo "ERROR: Expected outputs file not found: $EXPECTED_FILE"
  exit 1
fi

# --- Run tests ---

for entry in "${TEST_MATRIX[@]}"; do
  skill="${entry%%:*}"
  fixture="${entry#*:}"
  run_skill_test "$skill" "$fixture"
done

# --- Summary ---
echo
if $DRY_RUN; then
  echo "=== Dry run: ${#TEST_MATRIX[@]} tests would execute ==="
else
  echo "=== Skill test results: $pass passed, $errors failed, $skipped skipped ==="
fi
if [ "$errors" -gt 0 ]; then exit 1; else exit 0; fi
