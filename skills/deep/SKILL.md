---
description: Runs a resumable multi-iteration auto-fix loop in one of three modes — review (iterative /optimus:code-review of the branch diff), refactor (iterative /optimus:refactor, optional testability or guidelines focus), coverage (paired /optimus:unit-test + testability-refactor cycles) — dispatching the base skill into a fresh subagent per iteration, applying fixes automatically without per-change approval, running tests, and bisecting failures until convergence or the iteration cap. Creates a git checkpoint commit after each iteration unless --no-commit; interrupted runs continue with --resume. Requires /optimus:init project context and a test command in .claude/CLAUDE.md. Use when a single supervised pass is not enough — pre-release cleanup, project-wide guideline alignment, or sustained coverage improvement.
disable-model-invocation: true
argument-hint: "[review|refactor|coverage] [scope] [--resume] [--yes] [--no-commit] [--max N]"
---

# Deep Mode

Orchestrate a base skill in an iterative auto-fix loop. Each iteration runs in a fresh subagent context, so the loop is not bounded by single-conversation context decay. The orchestrator itself stays slim: it dispatches subagents, parses their structured output, and drives the `harness_common.cli` helper to apply fixes, run tests, bisect failures, and decide termination. All state lives in the mode's progress file.

## Modes

| Mode | Base skill | Loop variant | Progress file | CLI init |
|---|---|---|---|---|
| `review` | `skills/code-review/SKILL.md` | Single-skill loop | `.claude/code-review-deep-progress.json` | `--skill code-review --max-iterations N` (default 8, hard cap 20) |
| `refactor` | `skills/refactor/SKILL.md` | Single-skill loop | `.claude/refactor-deep-progress.json` | `--skill refactor --max-iterations N` (default 8, hard cap 20) |
| `coverage` | `skills/unit-test/SKILL.md`, plus `skills/refactor/SKILL.md` (testability) when untestable code is flagged | Paired-cycle loop | `.claude/unit-test-deep-progress.json` | `--skill unit-test --max-cycles N` (default 5, hard cap 10) |

The progress-file paths and CLI flag names are contracts with `scripts/harness_common` and its tests — never rename them.

## Step 1: Parse arguments

### Re-entry guard

If your invocation prompt body already contains `HARNESS_MODE_INLINE`, stop immediately with: *"Deep mode cannot run inside deep mode."* This prevents a misbehaving subagent from spawning a recursive deep run.

### Arguments

1. Mode keyword — `review`, `refactor`, or `coverage`, as the first standalone token. If missing, ask the user which mode they want.
2. `--resume` — continue the mode's existing progress file.
3. `--yes` — auto-confirm Step 3; required under `claude -p` or any other non-interactive session that cannot answer a question.
4. `--no-commit` — skip checkpoint commits (the CLI auto-stashes per iteration instead, so failed iterations stay restorable).
5. `--max N` — the iteration cap (review/refactor) or cycle cap (coverage); defaults and hard caps per the mode table.
6. Refactor mode only — an optional focus keyword, `testability` or `guidelines`: match standalone unquoted tokens case-insensitively; keywords inside quotes stay in the scope text; if both appear, use the first and tell the user to run separate passes for each.
7. Everything else → scope text. An existing path scopes the run to that path; any other text is recorded as intent only and does **not** filter. With no path scope:
   - `review` covers the full feature-branch diff;
   - `refactor` starts from the branch diff when one exists (otherwise the full project), then widens per iteration only to files with active findings and newly modified files;
   - `coverage` covers the full project.

Examples: `/optimus:deep review src/auth`, `/optimus:deep refactor testability --max 12`, `/optimus:deep coverage --resume`, `claude -p "/optimus:deep review --yes"` (headless / CI).

## Step 2: Pre-flight checks

### Plugin root

Resolve `plugin_root` (the absolute path to the installed plugin) and keep it for every CLI call and subagent dispatch below — the env var does not persist across separate Bash tool calls and reads empty on some platforms (notably Windows):

1. Run `echo $CLAUDE_PLUGIN_ROOT` via Bash. If it is non-empty **and** `<value>/scripts/harness_common` exists (`test -d`), use it.
2. Otherwise derive the root from the "Base directory for this skill:" line in your invocation context — strip the trailing `/skills/...` segment (this skill's own directory) — and use it if `<derived>/scripts/harness_common` exists.
3. If neither candidate contains `scripts/harness_common`, stop: *"Cannot resolve plugin root — ensure optimus-claude is installed via the Claude Code plugin system."*

Wherever the steps below (and `references/orchestrator-loop.md`) write `$CLAUDE_PLUGIN_ROOT`, use this resolved `plugin_root`; if `echo $CLAUDE_PLUGIN_ROOT` was empty, substitute the absolute path literally.

### Documentation prerequisites

Read `$CLAUDE_PLUGIN_ROOT/skills/init/references/prerequisite-check.md` and apply the prerequisite check. If `.claude/CLAUDE.md` is missing, stop: *"Deep mode requires `/optimus:init` to set up project context first."*

### Test command

Read `.claude/CLAUDE.md` and capture the documented test command verbatim as `test_command` (e.g. `npm test`, `pytest`). The CLI requires `--test-command`, and always pass the command you captured rather than letting anything re-derive it — a human read is more reliable than any parser. If no test command is documented, ask the user for one (in a `--yes` run, stop instead) and recommend `/optimus:init` to document it — the auto-fix loop has no safety net without one.

### Git state

On a fresh (non-`--resume`) run, refuse to proceed if `git status --porcelain` shows uncommitted changes, unless `--no-commit` is passed — uncommitted state would be ambiguous with the orchestrator's own checkpoint commits. On `--resume`, the existing progress file's `_snapshot.pre_head` is the recovery anchor; uncommitted state is preserved.

## Step 3: Confirm the run

Skip when `--resume` or `--yes` was given. Otherwise confirm once with `AskUserQuestion`, making sure the user understands: the run makes up to N iterations (for coverage: N cycles of up to two subagent dispatches each), each dispatch is a fresh subagent so credit and time consumption multiply with the cap, fixes are applied automatically without per-change approval, and Esc-twice interrupts are recoverable with `--resume` (mid-dispatch interrupts may leave partial edits; clean iterations recover fully). State the test command — and, in refactor mode, the focus. This single confirmation stands for the whole run. If the user declines, stop.

## Step 4: Initialize or resume

Read `$CLAUDE_PLUGIN_ROOT/references/harness-init-resume.md` and apply its shared init/resume semantics — the `resume` invocation and cap raising, `init` error recovery (a prior run is discarded by re-invoking `init` with `--force`), `--no-commit` persistence, and `.done.json` archival — with `<progress-path>` and `<cap-flag>` from the mode table.

On a fresh run:

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli init \
    --skill <code-review|refactor|unit-test> \
    <--max-iterations|--max-cycles> [N] \
    --test-command "<test_command>" \
    [--focus testability|guidelines] \
    [--scope "<scope>"] \
    [--no-commit] \
    --progress-file "<progress-path>" \
    --project-dir "."
```

`--focus` is refactor mode only, passed only when a focus keyword was given (the CLI rejects other values). Coverage mode never passes it — the CLI pins the coverage refactor phase's focus to testability itself.

### Baseline gate

On a fresh run, after `init` succeeds, run the suite once before entering the loop:

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli baseline \
    --progress-file "<progress-path>"
```

`baseline` runs the test command once and calibrates the per-iteration test timeout from its duration (so a slow suite, re-run repeatedly during bisection, doesn't spuriously time out).

- **Review / refactor:** the suite must be green. On `baseline-red`, stop and show the user the failing tests — do not enter the loop, even under `--yes` (a red starting tree makes bisection blame the iteration's fixes and revert good work). Once the tests are fixed, the run continues with `--resume`.
- **Coverage:** pass `--allow-red` — a project with no tests yet legitimately starts red, and the timeout then stays at its default. But if the CLI prints `baseline-red-allowed` and the project already has tests (the suite is red because existing tests fail, not because none exist), stop and report the failures instead of looping: a failing suite trips the unit-test phase's `blocked` gate at cycle 1, so no cycle can make progress.
- **On `--resume`:** skip the baseline only when the prior run completed at least one iteration/cycle — check the progress file's single `iteration.completed` (or `cycle.completed`) field with a targeted read; do not load the `findings` array into context. If it is 0, the prior run never entered the loop and `resume` never re-checks the baseline — run it again (same rules as above) before looping.

## Step 5: Run the loop

Read `$CLAUDE_PLUGIN_ROOT/references/orchestrator-loop.md` and follow the mode's variant, with `<progress-path>` from the mode table and `<max>` from Step 1:

- **review** → "Single-skill loop" with `<base-skill>` = `code-review`.
- **refactor** → "Single-skill loop" with `<base-skill>` = `refactor`. When a focus was set, add a `Focus: <testability|guidelines>` line to each dispatch prompt body — the base skill reads `config.focus` from the progress file, but echoing it makes the intent visible in the run trace.
- **coverage** → "Paired-cycle loop" (unit-test phase, then a conditional testability-refactor phase, per cycle).

Brief one-line status updates per iteration are appropriate; don't narrate the subagent's findings in conversation prose — the final report covers them. Report only what the CLI's stdout confirmed: if a step was skipped or a count is subagent-reported rather than CLI-verified, say so.

## Step 6: Final report

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli final-report \
    --progress-file "<progress-path>" \
    --archive
```

This prints the cumulative report (fixed / reverted / persistent counts, coverage progression in coverage mode, termination reason, git rollback guidance) and archives the progress file to `.done.json` so a stray `--resume` cannot pick up a completed run. Exception: a `diminishing-returns` soft-exit is left un-archived (the CLI prints `not-archived`) so the run stays continuable with `--resume`. An archived run cannot be resumed — for a fresh second-opinion pass, re-run `/optimus:deep <mode>`; on a clean tree it converges on the first iteration.

## Wrapping up

The approval recorded at Step 3 stands for the entire loop — the base skill's harness-mode protocol is the source of truth for which fixes get applied. After the report, suggest looking over the accumulated changes — `/optimus:code-review` in a fresh conversation gives them a supervised second opinion — or committing the checkpointed work and opening a PR once the branch is ready.
