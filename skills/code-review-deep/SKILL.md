---
description: Iterative auto-fix code review — runs `/optimus:code-review` in a fresh subagent context per iteration, applies fixes, runs tests, bisects failures, and continues until convergence or the iteration cap (default 8, hard cap 20). Each iteration runs in an isolated subagent so context does not accumulate. Requires a test command in .claude/CLAUDE.md. Use when single-pass review leaves issues or for thorough cleanup before a release.
disable-model-invocation: true
---

# Code Review (Deep)

Orchestrate `/optimus:code-review` in an iterative auto-fix loop. Each iteration runs in a fresh subagent context, so the loop is not bounded by single-conversation context decay. All state lives in `.claude/code-review-deep-progress.json`. The orchestrator skill itself stays slim — it dispatches subagents, parses their structured output, and uses the `harness_common.cli` helper to apply fixes, run tests, bisect failures, and decide termination.

## Step 1: Parse Arguments and Guard Against Re-entry

### Re-entry guard

If your invocation prompt body already contains `HARNESS_MODE_INLINE`, stop immediately with: *"Deep mode cannot run inside deep mode."* This prevents a misbehaving subagent from spawning a recursive deep run.

### Parse invocation arguments

Extract from the user's arguments:
1. `--resume` flag (present/absent)
2. `--no-commit` flag (present/absent)
3. `--yes` flag (present/absent) — auto-confirm the Step 3 prompt; required when invoked under `claude -p` or any other non-interactive session that cannot answer `AskUserQuestion`.
4. `--max-iterations N` (optional, default 8, hard cap 20)
5. Everything else → scope text (natural-language description or path; e.g., `"focus on src/auth"`)

Examples:
- `/optimus:code-review-deep` → 8 iterations on the branch diff
- `/optimus:code-review-deep --max-iterations 12` → 12 iterations
- `/optimus:code-review-deep "focus on src/auth"` → scoped
- `/optimus:code-review-deep --resume` → continue from existing progress file
- `/optimus:code-review-deep --no-commit` → skip per-iteration checkpoint commits
- `claude -p "/optimus:code-review-deep --yes 'src/auth'"` → headless / CI usage; skips the Step 3 confirmation prompt

## Step 2: Pre-flight Checks

### Plugin root

Run `echo $CLAUDE_PLUGIN_ROOT` via Bash. Store as `plugin_root`. If empty, stop: *"Cannot resolve plugin root — ensure optimus-claude is installed via the Claude Code plugin system."*

### Documentation prerequisites

Read `$CLAUDE_PLUGIN_ROOT/skills/init/references/prerequisite-check.md` and apply the prerequisite check. If `.claude/CLAUDE.md` is missing, stop: *"Deep mode requires `/optimus:init` to set up project context first."*

### Test command

Read `.claude/CLAUDE.md` and verify a test command is documented. If no test command can be detected (the CLI's `init` subcommand will fail explicitly), stop and recommend `/optimus:init` to set one up first.

### Git state

Run `git status --porcelain` via Bash. On a fresh (non-`--resume`) run, refuse to proceed if the working tree has uncommitted changes (except when `--no-commit` is passed) — uncommitted state would be ambiguous with the orchestrator's own per-iteration commits.

On `--resume`, the existing progress file's `_snapshot.pre_head` is the recovery anchor; uncommitted state is preserved.

## Step 3: User Confirmation

Skip this step entirely when `--resume` is given, or when `--yes` is given (headless / CI: the caller has pre-approved the run).

Warn the user with:

> **Deep mode** runs up to [N] iterative review-fix passes. Each iteration spawns a fresh subagent — credit and time consumption multiplies with iteration count. Fixes are applied automatically at each iteration without per-change approval. Low test coverage increases the chance of undetected breakage; consider running `/optimus:unit-test` first to strengthen the safety net. Press Esc twice to interrupt — state is saved per-iteration; resume with `/optimus:code-review-deep --resume`.
>
> Test command: `[test command]`
>
> Mid-iteration interrupts may leave the working tree inconsistent; clean iterations are fully recoverable via `--resume`.

Use `AskUserQuestion` — header "Deep code review", question "Proceed with deep code review?":
- **Proceed** — "Run iterative review-fix until clean (max [N] iterations)"
- **Cancel** — "Don't run deep mode"

If the user selects **Cancel**, stop.

## Step 4: Initialize or Resume Progress

### On `--resume`

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli resume \
    --progress-file ".claude/code-review-deep-progress.json" \
    --project-dir "."
```

If exit code is non-zero, surface the error and stop.

### On fresh run

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli init \
    --skill code-review \
    --max-iterations [N] \
    [--scope "<scope>"] \
    --progress-file ".claude/code-review-deep-progress.json" \
    --project-dir "."
```

If exit code is non-zero, surface the error and stop. Likely errors:
- *"progress file already exists"* — a prior run has not been archived. Tell the user to either pass `--resume` to continue the prior run, or re-invoke this skill with `--force` to discard the prior progress and start fresh.
- *"No test command"* — `.claude/CLAUDE.md` does not document a test command. Recommend `/optimus:init`.
- *"Cannot determine HEAD commit"* — the project is not a git repository or has no commits.

If the user explicitly wants to discard a prior run, pass `--force` to `cli.py init` (no separate user-visible orchestrator flag is needed — the CLI's `--force` is sufficient).

## Step 5: Run the Iteration Loop

Read `$CLAUDE_PLUGIN_ROOT/references/orchestrator-loop-single.md` and follow its 8-step per-iteration body, with these parameters:

- `<base-skill>` = `code-review`
- `<progress-path>` = `.claude/code-review-deep-progress.json`
- `<max>` = the iteration cap from Step 1

Brief, single-line status updates per iteration are appropriate (e.g., *"Iteration 3/8: dispatching subagent…"* then *"Iteration 3/8: applied 5 fixes, 2 reverted, tests pass."*). Do not narrate the subagent's findings in conversation prose — the report at Step 6 covers them.

## Step 6: Final Report

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli final-report \
    --progress-file ".claude/code-review-deep-progress.json" \
    --archive
```

This prints the cumulative report (fixed / reverted / persistent counts, per-finding table, termination reason, git rollback guidance) and moves the progress file to `.done.json` so a stray `--resume` cannot pick up a completed run.

## Important

The orchestrator skill applies fixes automatically across all iterations; user approval is recorded once at Step 3 and stands for the whole loop. The base skill's harness-mode protocol is the source of truth for which fixes get applied.

Recommend the user run `/optimus:commit` next, followed by `/optimus:pr` once the branch is ready. Tell the user: **Tip:** stay in this conversation when running `/optimus:commit` and `/optimus:pr` so the implementation context is captured. Other downstream skills (`/optimus:code-review`, `/optimus:unit-test`) should still run in fresh conversations.

## Tip

After completion, if you want a second-opinion pass, run `/optimus:code-review-deep --resume --max-iterations <new-cap>` in the same branch — but only if non-trivial new findings are likely (e.g., after pulling new changes). On clean trees, `--resume` will exit immediately with `convergence`.
