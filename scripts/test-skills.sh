#!/usr/bin/env bash
# Automated skill execution tests using claude -p (headless mode).
# Runs optimus skills against generated fixtures and validates expected outputs.
#
# Requirements: authenticated claude CLI, Python 3, and PyYAML (requirements-dev.txt).
# These are smoke checks; passing them is not a model-performance evaluation.
#
# Usage:
#   bash scripts/test-skills.sh --model claude-fable-5-1      # default: init + commit-suggest
#   bash scripts/test-skills.sh --model claude-fable-5-1 --skill init                 # test one skill
#   bash scripts/test-skills.sh --model claude-fable-5-1 --skill init --fixture node  # test one skill + one fixture
#   bash scripts/test-skills.sh --model claude-fable-5-1 --all                        # test all testable skills
#   bash scripts/test-skills.sh --model claude-fable-5-1 --fresh --all --worktree     # full run in isolated worktree
#   bash scripts/test-skills.sh --dry-run                    # show what would run

set -euo pipefail

ORIGINAL_ARGS=("$@")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FIXTURES_DIR="$PLUGIN_ROOT/test/fixtures"
EXPECTED_FILE="$PLUGIN_ROOT/test/expected-outputs.yaml"

# --- Defaults ---
MAX_TURNS=30
MODEL=""
PYTHON="${PYTHON:-python}"
SUPPORT="$SCRIPT_DIR/skill_test_support.py"
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
    --model)    [[ $# -ge 2 ]] || { echo "Error: --model requires a value"; exit 1; }; MODEL="$2"; shift 2 ;;
    --all)      ALL_MODE=true; shift ;;
    --fresh)    FRESH=true; shift ;;
    --worktree) WORKTREE=true; shift ;;
    --dry-run)  DRY_RUN=true; shift ;;
    --help|-h)
      echo "Usage: bash scripts/test-skills.sh [options]"
      echo "Options:"
      echo "  --skill <name>     Test specific skill (init, permissions, commit-suggest, commit-branch, how-to-run, prompt)"
      echo "  --fixture <name>   Test against specific fixture (node, python, go, rust, csharp, monorepo, empty, multi-repo)"
      echo "  --all              Test all skill/fixture combinations"
      echo "  --fresh            Remove and regenerate all fixtures before testing"
      echo "  --worktree         Run in an isolated git worktree (keeps main tree free)"
      echo "  --model <id>       Required for live runs; use the exact model being evaluated"
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
if ! $DRY_RUN && [ -z "$MODEL" ]; then
  echo "Error: --model is required for live smoke runs (no implicit model substitution)."
  exit 1
fi

# --- Worktree isolation ---
# Creates a new detached worktree inside .worktrees/ and re-invokes the
# script from there, so the user can keep working (switch branches, edit files)
# in the main tree while the worktree stays visible in the project directory.
if $WORKTREE; then
  WORKTREE_PARENT="$PLUGIN_ROOT/.worktrees"
  mkdir -p "$WORKTREE_PARENT"
  WORKTREE_DIR=$(mktemp -d "$WORKTREE_PARENT/skill-tests.XXXXXX")
  # Only this invocation's freshly allocated child may be cleaned up. Failed
  # runs from previous invocations remain available for inspection.
  case "$WORKTREE_DIR" in
    "$WORKTREE_PARENT"/skill-tests.*) ;;
    *) echo "Error: worktree path is outside the expected parent"; exit 1 ;;
  esac

  cleanup_worktree() {
    local rc=$?
    if [ "$rc" -ne 0 ]; then
      echo
      echo "Tests failed — worktree preserved at: $WORKTREE_DIR"
      echo "  To clean up after inspection: git worktree remove \"$WORKTREE_DIR\" --force"
    else
      echo
      echo "Cleaning up worktree..."
      if ! git -C "$PLUGIN_ROOT" worktree remove "$WORKTREE_DIR" --force; then
        echo "Cleanup failed; this run's worktree remains at: $WORKTREE_DIR"
      fi
    fi
  }
  trap cleanup_worktree EXIT

  COMMIT_SHORT=$(git -C "$PLUGIN_ROOT" rev-parse --short HEAD)
  echo "Creating worktree at $WORKTREE_DIR (from committed HEAD $COMMIT_SHORT)..."
  echo "Uncommitted source edits are excluded; omit --worktree to test the working checkout."
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
    "commit-suggest:node-project"
    "how-to-run:node-project"
    "how-to-run:python-project"
    "prompt:node-project"
    "commit-branch:node-project"
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
    commit-suggest) TEST_MATRIX=("commit-suggest:node-project") ;;
    how-to-run)     TEST_MATRIX=("how-to-run:node-project" "how-to-run:python-project") ;;
    prompt)         TEST_MATRIX=("prompt:node-project") ;;
    commit-branch)  TEST_MATRIX=("commit-branch:node-project") ;;
    *) echo "Unknown skill: $SKILL_FILTER. Supported: init, permissions, commit-suggest, commit-branch, how-to-run, prompt"; exit 1 ;;
  esac
else
  # Default: quick smoke test
  TEST_MATRIX=(
    "init:node-project"
    "init:python-project"
    "commit-suggest:node-project"
  )
fi

# --- Helpers ---

errors=0
pass=0
skipped=0
CURRENT_WORK_DIR=""
trap 'if [ -n "$CURRENT_WORK_DIR" ] && [ -d "$CURRENT_WORK_DIR" ]; then rm -rf "$CURRENT_WORK_DIR"; fi' EXIT INT TERM

# System prompt that makes skills non-interactive
NONINTERACTIVE_PROMPT="Run non-interactively: never call AskUserQuestion. Where the skill would put a choice to the user, take the option it marks as the default (or the first one listed) and continue."

run_skill_test() {
  local skill="$1"
  local fixture="$2"
  local fixture_dir="$FIXTURES_DIR/$fixture"

  if [ ! -d "$fixture_dir" ]; then
    echo "  FAIL  $skill:$fixture (fixture missing — run scripts/generate-fixtures.sh first)"
    ((errors++)) || true
    return
  fi

  # Reject absent or empty oracles before making a paid host invocation.
  if ! "$PYTHON" "$SUPPORT" expectation --expected "$EXPECTED_FILE" --skill "$skill" --fixture "$fixture"; then
    ((errors++)) || true
    return
  fi

  # Results and baseline stay outside the project, so read-only checks include
  # every project file without counting our own output as a model mutation.
  local work_root work_dir
  work_root=$(mktemp -d)
  work_dir="$work_root/project"
  mkdir "$work_dir"
  CURRENT_WORK_DIR="$work_root"
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
    commit-suggest)
      # Need some changes to analyze — test for file existence to avoid creating unexpected files
      if [ -f index.js ]; then
        echo "// new feature" >> index.js
      elif [ -f README.md ]; then
        echo "# new feature" >> README.md
      else
        echo "# new feature" > README.md
      fi
      prompt="Run /optimus:commit suggest — suggest a conventional commit message for the current changes without committing."
      ;;
    how-to-run)
      prompt="Run /optimus:how-to-run to generate a HOW-TO-RUN.md teaching a new developer how to set up their environment and run this project locally."
      ;;
    prompt)
      prompt="Run /optimus:prompt to craft an optimized prompt for the following idea: Write a Python function that parses CSV files and returns summary statistics."
      ;;
    commit-branch)
      # Need uncommitted changes for branch mode to have context
      if [ -f index.js ]; then
        echo "// add auth middleware" >> index.js
      elif [ -f README.md ]; then
        echo "# add auth middleware" >> README.md
      else
        echo "# add auth middleware" > README.md
      fi
      prompt="Run /optimus:commit branch — move the current changes to a properly named branch without committing."
      ;;
    *)
      echo "  ERROR  No prompt defined for skill: $skill"
      ((errors++)) || true
      cd "$PLUGIN_ROOT"
      rm -rf "$work_root"
      CURRENT_WORK_DIR=""
      return
      ;;
  esac

  if $DRY_RUN; then
    echo "  DRY   $skill:$fixture"
    echo "        dir: $work_dir"
    echo "        prompt: $prompt"
    cd "$PLUGIN_ROOT"
    rm -rf "$work_root"
    CURRENT_WORK_DIR=""
    return
  fi

  echo "  RUN   $skill:$fixture (max-turns: $MAX_TURNS)"

  "$PYTHON" "$SUPPORT" snapshot --root "$work_dir" > "$work_root/baseline.json"

  local model_args=()
  if [ -n "$MODEL" ]; then model_args=(--model "$MODEL"); fi
  local exit_code=0
  claude -p "$prompt" \
    --plugin-dir "$PLUGIN_ROOT" \
    --append-system-prompt "$NONINTERACTIVE_PROMPT" \
    --dangerously-skip-permissions \
    --max-turns "$MAX_TURNS" \
    --output-format json \
    ${model_args[@]+"${model_args[@]}"} \
    > "$work_root/result.json" 2> "$work_root/stderr.log" || exit_code=$?

  if [ "$exit_code" -ne 0 ]; then
    echo "  FAIL  $skill:$fixture (claude exited with code $exit_code)"
    head -5 "$work_root/stderr.log"
    ((errors++)) || true
  elif "$PYTHON" "$SUPPORT" validate --expected "$EXPECTED_FILE" \
      --skill "$skill" --fixture "$fixture" --root "$work_dir" \
      --output "$work_root/result.json" --baseline "$work_root/baseline.json"; then
    echo "  PASS  $skill:$fixture"
    ((pass++)) || true
  else
    echo "  FAIL  $skill:$fixture"
    ((errors++)) || true
  fi

  # Cleanup
  cd "$PLUGIN_ROOT"
  rm -rf "$work_root"
  CURRENT_WORK_DIR=""
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

if ! "$PYTHON" -c 'import yaml' >/dev/null 2>&1; then
  echo "ERROR: Python with PyYAML is required. Install requirements-dev.txt."
  exit 1
fi
echo "Host: $(claude --version)"
echo "Model: ${MODEL:-host default (not pinned)}"
echo "Plugin directory: $PLUGIN_ROOT"
echo "Plugin commit: $(git -C "$PLUGIN_ROOT" rev-parse HEAD)"
echo "Plugin working-tree state:"
git -C "$PLUGIN_ROOT" status --short --untracked-files=no

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
