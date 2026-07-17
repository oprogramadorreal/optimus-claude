# Architecture

## Overview

A Claude Code plugin combining markdown-based skill authoring (16 skills invoked via `/optimus:<name>`) with one orchestrator skill (`deep`) that dispatches base skills into fresh subagent contexts and uses a small Python CLI under `scripts/harness_common/` for state, test, bisection, and commit primitives.

## Directory Map

| Directory | Purpose |
|-----------|---------|
| `.claude-plugin/` | Plugin manifests (plugin.json, marketplace.json) |
| `agents/` | Plugin-level agent definitions (code-simplifier, test-guardian) — standalone, user-invocable |
| `hooks/` | Plugin-level hooks (SessionStart for project state awareness) |
| `references/` | Shared reference docs consumed by multiple skills |
| `skills/<name>/` | One directory per skill (SKILL.md + README.md + optional agents/, references/, templates/) |
| `scripts/harness_common/` | Orchestrator CLI (`cli.py`) + shared modules invoked by `/optimus:deep` |
| `scripts/test-skills.sh` | Skill execution test runner |
| `test/harness-common/` | pytest suite for the CLI and shared modules |

## Code Architecture

### Data Flow

- Entry: `/optimus:deep <review|refactor|coverage>` runs in the user's conversation.
- The orchestrator invokes `python -m harness_common.cli init --skill <base>` to create a JSON progress file, then enters a per-iteration loop.
- Each iteration (review/refactor targets) or cycle (coverage target):
  1. `cli snapshot` records the pre-iteration git HEAD into the progress file.
  2. The skill dispatches the base skill (`code-review`, `refactor`, or `unit-test`) as a fresh `general-purpose` subagent via the Agent tool. The subagent prompt carries `HARNESS_MODE_INLINE`, the absolute progress-file path, and an instruction to read the base SKILL.md and follow `references/harness-mode.md` (or `references/coverage-harness-mode.md`).
  3. The subagent emits a `json:harness-output` fenced block in its final message.
  4. The orchestrator saves the subagent's output to a temp file, runs `cli parse` to extract the JSON, then `cli deep-step` (or `refactor-step` for the paired refactor phase) to apply fixes, run tests, bisect on failure, and update statuses; `unit-test-step` instead records tests + coverage, rolling the whole cycle back if the suite is red. The bisect rebuilds each candidate state from the pre-iteration git snapshot rather than trusting the reported `pre/post_edit_content` as revert data — a corrupt record can only fail loudly as `skipped`, never tear the tree.
  5. `cli commit-checkpoint` produces a per-iteration commit.
  6. Review/refactor targets: `cli check-termination`, then `cli advance` on `continue`. Coverage target: `cli record-cycle` first (it pre-increments `cycle.current`, which the cap check relies on), then `cli check-termination`.
  7. `check-termination` returns one of `continue | convergence | no-actionable | all-reverted | cap | diminishing-returns | parse-failure`; the loop repeats until it returns anything other than `continue`.
- `cli final-report --archive` prints the cumulative report and moves the progress file to `.done.json` (except after a `diminishing-returns` soft-exit, which stays un-archived so `--resume` can continue it).

### Key Patterns

- **Subagent isolation** — each iteration runs in a fresh subagent context via the Agent tool. The orchestrator skill itself stays slim: it sees the subagent's terse JSON return, not the subagent's full analysis trace.
- **File-based state** — all cross-iteration state lives in `.claude/<base>-deep-progress.json`. The orchestrator never holds findings in conversation prose.
- **JSON output protocol** — the base skill emits `json:harness-output`; the CLI parses it.
- **stdlib only** — no pip dependencies beyond the standard library (dev deps are test/formatting tools only).
- **UTF-8 pinned I/O** — every text-mode subprocess call passes `encoding="utf-8", errors="replace"` (never the locale codec — on cp1252 Windows a bare `text=True` silently loses child output on the first non-decodable byte), and `cli.main()` reconfigures its own stdout/stderr to UTF-8 so printing subagent-authored text through a pipe can't crash the run. Enforced by `test/harness-common/test_encoding_policy.py`.

### Dependencies Between Modules

- `harness_common/cli.py` → all sibling modules (`findings`, `convergence`, `fixes`, `git`, `parser`, `progress`, `runner`, `reporting`, `constants`).
- `harness_common` is otherwise self-contained with no intra-project dependencies.

## Skill Architecture

### Skill Organization

- 16 skills: brainstorm, code-review, commit, deep, handoff, how-to-run, init, jira, permissions, pr, prompt, refactor, reset, tdd, unit-test, worktree.
- Each directory contains `SKILL.md` (required) + `README.md` (required), with optional `agents/`, `references/`, `templates/` subdirectories.

### Agent Boundaries

- **Plugin-level** (`agents/`): code-simplifier, test-guardian — standalone, user-invocable quality agents.
- **Skill-level** (`skills/<name>/agents/`): self-contained prompt files scoped to the owning skill; each carries its criteria inline (no extension of plugin-level agents).
- The orchestrator skill (`deep`) has no agents directory — it dispatches the base skills, which own the analysis agents.

### Reference Hierarchy

- **Root** `references/`: harness protocol contracts (harness-mode, coverage-harness-mode, orchestrator-loop-single, orchestrator-loop-paired, harness-init-resume), shared agent rules (shared-agent-constraints, context-injection-blocks, agent-architecture), and the SDD precedence contract (sdd-mapping).
- **Skill-level** `references/`: supplemental docs scoped to one skill or shared under a canonical owner (e.g., `init/references/multi-repo-detection.md`, `commit/references/branch-naming.md`, `brainstorm/references/plan-mode-handoff.md`).
- Maximum depth: SKILL.md → reference → sub-reference (two levels). Cross-cutting references load conditionally (e.g., multi-repo detection only when the cwd has no `.git/`).

### Orchestration Patterns

- **Orchestrator dispatch** — `/optimus:deep` reads `references/orchestrator-loop-{single,paired}.md` per target and follows the per-iteration template, dispatching base skills via the Agent tool.
- **Harness-mode protocol** — base skills detect `HARNESS_MODE_INLINE` in their invocation prompt and follow `references/harness-mode.md` (or `coverage-harness-mode.md` for unit-test) to emit a single-pass JSON result.
- **Agent spawning** — base SKILL.md files instruct Claude to launch named subagents for specialized analysis passes.
- **User checkpoints** — skills use `AskUserQuestion` at genuine decision gates (destructive actions, scope approval, cost confirmation). The orchestrator confirms once before its loop (skipped on `--resume`/`--yes`); the confirmation stands for the whole run.
