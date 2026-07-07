# Architecture

## Overview

A Claude Code plugin combining markdown-based skill authoring (22 skills invoked via `/optimus:<name>`) with three orchestrator skills (`*-deep`) that dispatch base skills into fresh subagent contexts and use a small Python CLI under `scripts/harness_common/` for state, test, bisection, and commit primitives.

## Directory Map

| Directory | Purpose |
|-----------|---------|
| `.claude-plugin/` | Plugin manifests (plugin.json, marketplace.json) |
| `agents/` | Plugin-level agent definitions (code-simplifier, test-guardian) |
| `hooks/` | Plugin-level hooks (SessionStart for project state awareness) |
| `references/` | Shared reference docs consumed by multiple skills |
| `skills/<name>/` | One directory per skill (SKILL.md + README.md + optional agents/, references/, templates/) |
| `scripts/harness_common/` | Orchestrator CLI (`cli.py`) + shared modules invoked by the `*-deep` skills |
| `scripts/test-skills.sh` | Skill execution test runner |
| `test/harness-common/` | pytest suite for the CLI and shared modules |

## Code Architecture

### Data Flow

- Entry: a `*-deep` skill (`/optimus:code-review-deep`, `/optimus:refactor-deep`, `/optimus:unit-test-deep`) runs in the user's conversation.
- The orchestrator skill invokes `python -m harness_common.cli init` to create a JSON progress file, then enters a per-iteration loop.
- Each iteration (deep variant) or cycle (paired variant):
  1. `cli snapshot` records the pre-iteration git HEAD into the progress file.
  2. The skill dispatches the base skill (`/optimus:code-review`, `/optimus:refactor`, or `/optimus:unit-test`) as a fresh `general-purpose` subagent via the Agent tool. The subagent prompt carries `HARNESS_MODE_INLINE`, the absolute progress-file path, and an instruction to read the base SKILL.md and follow `references/harness-mode.md` (or `references/coverage-harness-mode.md`).
  3. The subagent emits a `json:harness-output` fenced block in its final message.
  4. The orchestrator saves the subagent's output to a temp file, runs `cli parse` to extract the JSON, then `cli deep-step` (or `refactor-step` for the paired refactor phase) to apply fixes, run tests, bisect on failure, and update statuses; `unit-test-step` instead records tests + coverage, rolling the whole cycle back if the suite is red.
  5. `cli commit-checkpoint` produces a per-iteration commit.
  6. Deep variant: `cli check-termination`, then `cli advance` on `continue`. Paired variant: `cli record-cycle` first (it pre-increments `cycle.current`, which the cap check relies on), then `cli check-termination`.
  7. `check-termination` returns one of `continue | convergence | no-actionable | all-reverted | cap | diminishing-returns | parse-failure`; the loop repeats until it returns anything other than `continue`.
- `cli final-report --archive` prints the cumulative report and moves the progress file to `.done.json` (except after a `diminishing-returns` soft-exit, which stays un-archived so `--resume` can continue it).

### Key Patterns

- **Subagent isolation** — each iteration runs in a fresh subagent context via the Agent tool. The orchestrator skill itself stays slim: it sees the subagent's terse JSON return, not the subagent's full analysis trace.
- **File-based state** — all cross-iteration state lives in `.claude/<skill>-deep-progress.json` (or `unit-test-deep-progress.json`). The orchestrator skill never holds findings in conversation prose.
- **JSON output protocol** — the base skill emits `json:harness-output`; the CLI parses it.
- **stdlib only** — no pip dependencies beyond the standard library (dev deps are test/formatting tools only).

### Dependencies Between Modules

- `harness_common/cli.py` → all sibling modules (`findings`, `convergence`, `fixes`, `git`, `parser`, `progress`, `runner`, `reporting`, `constants`).
- `harness_common` is otherwise self-contained with no intra-project dependencies.

## Skill Architecture

### Skill Organization

- 22 skills: brainstorm, branch, code-review, code-review-deep, commit, commit-message, handoff, how-to-run, init, jira, permissions, pr, prompt, refactor, refactor-deep, reset, spec-init, tdd, unit-test, unit-test-deep, workflow, worktree.
- Each directory contains `SKILL.md` (required) + `README.md` (required), with optional `agents/`, `references/`, `templates/` subdirectories.

### Agent Boundaries

- **Plugin-level** (`agents/`): code-simplifier, test-guardian — available across all skills.
- **Skill-level** (`skills/<name>/agents/`): scoped to the owning skill (e.g., code-review has 6 specialized agents, refactor has 4).
- Orchestrator skills (`*-deep`) have no agents directory — they dispatch the base skill, which owns the analysis agents.

### Reference Hierarchy

- **Root** `references/`: agent-architecture, shared-agent-constraints, context-injection-blocks, harness-init-resume, harness-mode, coverage-harness-mode, orchestrator-loop-single, orchestrator-loop-paired, scope-expansion-rule, sdd-mapping, skill-handoff — cross-skill shared procedures.
- **Skill-level** `references/`: supplemental docs scoped to one skill (e.g., `init/references/`, `pr/references/`).
- Maximum depth: SKILL.md → reference → sub-reference (two levels).

### Orchestration Patterns

- **Orchestrator dispatch** — `*-deep` skills read `references/orchestrator-loop-{single,paired}.md` and follow the per-iteration template, dispatching base skills via the Agent tool.
- **Harness-mode protocol** — base skills detect `HARNESS_MODE_INLINE` in their invocation prompt and follow `references/harness-mode.md` (or `coverage-harness-mode.md` for unit-test) to emit a single-pass JSON result.
- **Agent spawning** — base SKILL.md files instruct Claude to launch named subagents for specialized analysis passes.
- **JSON output protocol** — each subagent emits structured `json:harness-output` blocks the orchestrator's CLI parses.
- **User checkpoints** — skills use `AskUserQuestion` at decision points. Orchestrator skills confirm once at Step 3 (skipped on `--resume`); the confirmation stands for the whole loop.
