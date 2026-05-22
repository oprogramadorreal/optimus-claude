---
description: Iterative test-coverage improvement loop — dispatches `/optimus:unit-test` (unit-test phase) and `/optimus:refactor` with testability focus (refactor phase) into fresh subagent contexts per cycle, applies tests, runs the test suite, bisects refactor failures, and continues until coverage plateaus or the cycle cap (default 5, hard cap 10). Use to drive coverage up on a codebase that has untestable barriers — the loop alternates between writing tests and unblocking testability so a single skill cannot stall.
disable-model-invocation: true
---

# Unit-Test Coverage Improvement (Deep)

Orchestrate paired cycles of test generation and testability refactoring. Each cycle is two subagent dispatches: first `/optimus:unit-test` (writes tests, measures coverage, flags untestable code), then `/optimus:refactor` with focus on testability (unblocks the flagged items so the next cycle can cover them). All state lives in `.claude/unit-test-deep-progress.json`.

## Step 1: Parse Arguments and Guard Against Re-entry

### Re-entry guard

If your invocation prompt body already contains `HARNESS_MODE_INLINE`, stop immediately with: *"Deep mode cannot run inside deep mode."*

### Parse invocation arguments

Extract from the user's arguments:
1. `--resume` flag (present/absent)
2. `--no-commit` flag (present/absent)
3. `--yes` flag (present/absent) — auto-confirm the Step 3 prompt; required when invoked under `claude -p` or any other non-interactive session that cannot answer `AskUserQuestion`.
4. `--max-cycles N` (optional, default 5, hard cap 10)
5. Everything else → scope text (optional path filter)

Examples:
- `/optimus:unit-test-deep` → 5 cycles, full project
- `/optimus:unit-test-deep --max-cycles 8` → 8 cycles
- `/optimus:unit-test-deep src/api` → scoped
- `/optimus:unit-test-deep --resume` → continue from existing progress file
- `/optimus:unit-test-deep --no-commit` → skip per-phase checkpoint commits
- `claude -p "/optimus:unit-test-deep --yes src/api"` → headless / CI usage; skips the Step 3 confirmation prompt

## Step 2: Pre-flight Checks

### Plugin root

Run `echo $CLAUDE_PLUGIN_ROOT` via Bash. Store as `plugin_root`. If empty, stop: *"Cannot resolve plugin root — ensure optimus-claude is installed via the Claude Code plugin system."*

### Documentation prerequisites

Read `$CLAUDE_PLUGIN_ROOT/skills/init/references/prerequisite-check.md` and apply the prerequisite check. If `.claude/CLAUDE.md` is missing, stop: *"Deep mode requires `/optimus:init` to set up project context first."*

### Test command

Read `.claude/CLAUDE.md` and verify a test command is documented. If missing, stop and recommend `/optimus:init` (the auto-fix loop has no safety net without a test command).

### Test infrastructure

The base `/optimus:unit-test` skill requires a test framework to be installed. If `/optimus:init` flagged the test framework as missing or "installed but no tests yet," warn the user but proceed — the unit-test phase will surface the gap.

### Git state

On a fresh (non-`--resume`) run, refuse to proceed if the working tree has uncommitted changes unless `--no-commit` is passed.

## Step 3: User Confirmation

Skip this step entirely when `--resume` is given, or when `--yes` is given (headless / CI: the caller has pre-approved the run).

Warn the user with:

> **Deep unit-test mode** runs up to [N] cycles. Each cycle is two subagent dispatches: a unit-test phase that writes tests + measures coverage, and a refactor phase (only when the first phase flags untestable code) that unblocks testability barriers. Credit and time consumption multiplies with cycle count. Tests and refactor fixes are applied automatically without per-change approval. Press Esc twice to interrupt — state is saved per-phase; resume with `/optimus:unit-test-deep --resume`.
>
> Test command: `[test command]`

Use `AskUserQuestion` — header "Deep unit-test", question "Proceed with deep unit-test?":
- **Proceed** — "Run the unit-test + refactor cycle loop (max [N] cycles)"
- **Cancel** — "Don't run deep mode"

If the user selects **Cancel**, stop.

## Step 4: Initialize or Resume Progress

### On `--resume`

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli resume \
    --progress-file ".claude/unit-test-deep-progress.json" \
    --project-dir "."
```

### On fresh run

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli init \
    --skill unit-test \
    --max-cycles [N] \
    [--scope "<scope>"] \
    --progress-file ".claude/unit-test-deep-progress.json" \
    --project-dir "."
```

If `init` reports *"progress file already exists"*, a prior un-archived run is on disk. Either run with `--resume` to continue it, or re-invoke `init` with `--force` to discard the prior progress.

## Step 5: Run the Cycle Loop

Read `$CLAUDE_PLUGIN_ROOT/references/orchestrator-loop-paired.md` and follow its 11-step per-cycle body, with these parameters:

- `<progress-path>` = `.claude/unit-test-deep-progress.json`
- `<max>` = the cycle cap from Step 1

The paired-loop template handles:
- Dispatching the unit-test subagent with `Phase: unit-test`
- Recording the unit-test phase outputs (tests, coverage history, untestable items)
- Checkpoint commit for the unit-test phase
- Conditionally dispatching the refactor subagent with `Phase: refactor` (only when pending untestable items exist)
- Recording the refactor phase outputs (with bisection on test failure)
- Checkpoint commit for the refactor phase
- Recording cycle history + advancing the cycle counter
- Termination check (`continue`, `convergence`, `cap`, `diminishing-returns`)

Brief per-phase status updates are appropriate (e.g., *"Cycle 2/5 unit-test: dispatching subagent…"*, *"Cycle 2/5 refactor: applied 3 fixes, tests pass."*). Do not narrate the subagent's findings in conversation prose — the report at Step 6 covers them.

## Step 6: Final Report

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli final-report \
    --progress-file ".claude/unit-test-deep-progress.json" \
    --archive
```

The report prints cycles completed, coverage baseline → final, total tests written (with file count), testability fixes applied, untestable items still pending, bugs discovered (if any), the termination reason, and git rollback guidance.

## Important

User approval recorded at Step 3 stands for the entire loop — tests and refactor fixes are applied without per-change confirmation. Recommend `/optimus:commit` next, followed by `/optimus:pr` once the branch is ready. Tell the user: **Tip:** for `/optimus:commit` and `/optimus:pr`, stay in this conversation so they can capture the implementation context. For other downstream skills (`/optimus:code-review`, `/optimus:unit-test`), start a fresh conversation — each gathers its own context from scratch.

## Tip

Unit-test-deep is the most expensive of the three orchestrator skills — each cycle is two subagent dispatches plus a full test-suite run after each. Default 5 cycles is appropriate for most codebases; raise it only when the project has substantial untestable code that takes multiple refactor rounds to unblock.
