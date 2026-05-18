---
description: Iterative project-wide refactoring — runs `/optimus:refactor` in a fresh subagent context per iteration, applies fixes, runs tests, bisects failures, and continues until convergence or the iteration cap (default 8, hard cap 20). Supports `testability` or `guidelines` focus to prioritize finding categories. Each iteration runs in an isolated subagent so context does not accumulate. Requires a test command in .claude/CLAUDE.md. Use for thorough guideline alignment, testability cleanup before /optimus:unit-test, or when context-bloat is degrading deep-mode output quality.
disable-model-invocation: true
---

# Project Refactor (Deep)

Orchestrate `/optimus:refactor` in an iterative cleanup loop. Each iteration runs in a fresh subagent context. All state lives in `.claude/refactor-deep-progress.json`. The orchestrator dispatches subagents, parses their structured output, and uses the `harness_common.cli` helper to apply fixes, run tests, bisect failures, and decide termination.

## Step 1: Parse Arguments and Guard Against Re-entry

### Re-entry guard

If your invocation prompt already contains `HARNESS_MODE_INLINE`, stop immediately with: *"Deep mode cannot run inside deep mode."*

### Parse invocation arguments

Extract from the user's arguments:
1. `--resume` flag (present/absent)
2. `--no-commit` flag (present/absent)
3. `--max-iterations N` (optional, default 8, hard cap 20)
4. Focus keyword (standalone unquoted token): `testability` or `guidelines` (the same detection rules as `/optimus:refactor` — see `skills/refactor/SKILL.md` Step 1)
5. Everything else → scope text

Examples:
- `/optimus:refactor-deep` → full project, 8 iterations, balanced focus
- `/optimus:refactor-deep testability` → focus on testability barriers
- `/optimus:refactor-deep guidelines "focus on backend"` → guidelines focus, scoped
- `/optimus:refactor-deep --max-iterations 12` → 12 iterations
- `/optimus:refactor-deep --resume` → continue from existing progress file
- `/optimus:refactor-deep --no-commit` → skip per-iteration checkpoint commits

## Step 2: Pre-flight Checks

### Plugin root

Run `echo $CLAUDE_PLUGIN_ROOT` via Bash. Store as `plugin_root`. If empty, stop: *"Cannot resolve plugin root — ensure optimus-claude is installed via the Claude Code plugin system."*

### Documentation prerequisites

Read `$CLAUDE_PLUGIN_ROOT/skills/init/references/prerequisite-check.md` and apply the prerequisite check. If `.claude/CLAUDE.md` is missing, stop: *"Deep mode requires `/optimus:init` to set up project context first."*

### Test command

Read `.claude/CLAUDE.md` and verify a test command is documented. If missing, stop and recommend `/optimus:init`.

### Git state

On a fresh (non-`--resume`) run, refuse to proceed if the working tree has uncommitted changes unless `--no-commit` is passed. On `--resume`, the existing progress file's `_snapshot.pre_head` is the recovery anchor.

## Step 3: User Confirmation

Skip this step entirely when `--resume` is given.

Warn the user with:

> **Deep refactor** runs up to [N] iterative refactor passes. Each iteration spawns a fresh subagent — credit and time consumption multiplies with iteration count. Fixes are applied automatically at each iteration without per-change approval. Low test coverage increases the chance of undetected breakage; consider running `/optimus:unit-test` first to strengthen the safety net. Press Esc twice to interrupt — state is saved per-iteration; resume with `/optimus:refactor-deep --resume`.
>
> Test command: `[test command]`
> Focus: `[focus or "balanced"]`

Use `AskUserQuestion` — header "Deep refactor", question "Proceed with deep refactor?":
- **Proceed** — "Run iterative refactor until clean (max [N] iterations)"
- **Cancel** — "Don't run deep mode"

If the user selects **Cancel**, stop.

## Step 4: Initialize or Resume Progress

### On `--resume`

```bash
python -m harness_common.cli resume \
    --progress-file ".claude/refactor-deep-progress.json" \
    --project-dir "."
```

### On fresh run

```bash
python -m harness_common.cli init \
    --skill refactor \
    --max-iterations [N] \
    [--focus testability | --focus guidelines] \
    [--scope "<scope>"] \
    --progress-file ".claude/refactor-deep-progress.json" \
    --project-dir "."
```

If `--focus` is supplied with anything other than `testability` or `guidelines`, the CLI rejects it.

## Step 5: Run the Iteration Loop

Read `$CLAUDE_PLUGIN_ROOT/references/orchestrator-loop-single.md` and follow its 8-step per-iteration body, with these parameters:

- `<base-skill>` = `refactor`
- `<progress-path>` = `.claude/refactor-deep-progress.json`
- `<max>` = the iteration cap from Step 1

When dispatching the refactor subagent, include the focus keyword in the prompt body if one was set:

```
... Phase: refactor
    Focus: <testability|guidelines>
...
```

The base skill reads `config.focus` from the progress file (the CLI's `init` recorded it there) and applies the finding-cap weighting accordingly — but echoing the focus into the dispatch prompt makes the intent visible to anyone reading the run trace.

## Step 6: Final Report

```bash
python -m harness_common.cli final-report \
    --progress-file ".claude/refactor-deep-progress.json" \
    --archive
```

## Important

User approval recorded at Step 3 stands for the entire loop — fixes are applied without per-change confirmation. Recommend `/optimus:commit` next. Tell the user: **Tip:** stay in this conversation when running `/optimus:commit` so the implementation context is captured. Other downstream skills (`/optimus:pr`, `/optimus:code-review`, `/optimus:unit-test`) should still run in fresh conversations.

## Tip

If the project has low test coverage and you suspect testability barriers are blocking better coverage, run with `testability` focus first; then re-run with `guidelines` focus (in a fresh conversation) to align style and convention violations once tests are in place.
