# optimus:deep

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that runs a base skill in an iterative auto-fix loop: `/optimus:deep <review|refactor|coverage>`. Each iteration dispatches the base skill into a fresh subagent context — sidestepping single-conversation context decay — then the harness CLI applies fixes, runs the test suite, bisects failures, checkpoints a commit, and decides termination.

## Usage

| Command | Effect |
|---|---|
| `/optimus:deep review` | Iterative `/optimus:code-review` on the branch diff (default 8 iterations, hard cap 20) |
| `/optimus:deep refactor` | Iterative `/optimus:refactor` on the feature-branch diff (full project when no diff exists) |
| `/optimus:deep refactor --focus testability` | Prioritize findings that unblock unit testing (`--focus guidelines` prioritizes convention alignment) |
| `/optimus:deep coverage` | Paired cycles of `/optimus:unit-test` + testability refactoring (default 5 cycles, hard cap 10) |
| `... <path>` | Scope the run to an existing file or directory |
| `... --max-iterations 12` / `... --max-cycles 8` | Raise the cap (review/refactor vs. coverage) |
| `... --resume` | Continue an interrupted or soft-exited run |
| `... --no-commit` | Skip checkpoint commits (also allows starting with a dirty working tree) |
| `... --allow-red-baseline` | review/refactor only: proceed even if the pre-loop test baseline is red |
| `claude -p "/optimus:deep review --yes"` | Headless / CI; auto-confirms the upfront prompt |

Natural-language scope text is recorded as intent but does not filter — only an existing path restricts the run.

## Requirements

- Project initialized with `/optimus:init`, including a test command in `.claude/CLAUDE.md`
- Python 3.8+ and Git (the orchestrator drives `python -m harness_common.cli`)
- Clean working tree (or `--no-commit`); green test suite at start for review/refactor (or `--allow-red-baseline`)

## How a run behaves

- **Confirmation upfront, then autonomy.** One approval covers the whole loop; fixes and tests are applied without per-change confirmation.
- **Checkpoint commits.** Each iteration (or phase, for coverage) produces a tagged commit unless `--no-commit` is set.
- **Verification + bisection.** The full test suite runs after each iteration's fixes; on failure the CLI reverts everything and re-applies fixes one at a time, keeping only those that pass.
- **Coverage cycles.** The `coverage` target alternates a unit-test phase (write tests, measure coverage, flag untestable code) with a conditional testability-refactor phase, so neither concern can stall the other.

## Termination, resume, and archive

The run ends with a cumulative report naming a termination reason — the six reasons are documented in [`references/harness-mode.md`](../../references/harness-mode.md).

- A finished run is archived to the progress file's `.done.json` sibling; `--resume` refuses it — re-run fresh for a second-opinion pass.
- A `diminishing-returns` soft-exit stays un-archived so `--resume` can continue it; `--resume` can also raise the cap.
- Press Esc twice to interrupt. Progress is written before every dispatch, so interrupts between dispatches are fully recoverable via `--resume`; a mid-dispatch interrupt may leave partial edits — inspect with `git status`, then discard with `git restore .` **and** `git clean -fd -e .claude/` (tracked edits plus any new untracked files the subagent created — a fresh run's init gate counts both, and `-e .claude/` preserves the progress files) or `--resume` to keep them.

Progress files: `.claude/code-review-deep-progress.json`, `.claude/refactor-deep-progress.json`, `.claude/unit-test-deep-progress.json`.

## Migrating from 2.x

| 2.x command | 3.0 equivalent |
|---|---|
| `/optimus:code-review-deep` | `/optimus:deep review` |
| `/optimus:refactor-deep testability` | `/optimus:deep refactor --focus testability` |
| `/optimus:unit-test-deep` | `/optimus:deep coverage` |

Flags, progress files, and the harness CLI are unchanged; an in-flight 2.x run can be continued with the matching 3.0 target plus `--resume`. One scope-semantics upgrade: 3.0 only filters discovery on real paths, so a free-text 2.x coverage scope is migrated to recorded intent (`scope_text`) on first `--resume` and the run continues over the full project.

## Cost

Deep runs multiply credit and time with the iteration count — coverage is the most expensive target (up to two subagent dispatches plus a full suite run per cycle). Scope to a path or lower the cap to bound cost. Whether each dispatched subagent actually fans out into the base skill's parallel analysis agents is unverified; the loop is correct either way, only analysis breadth would differ.

## Skill Structure

| File | Purpose |
|---|---|
| `SKILL.md` | Orchestrator instructions (targets table + shared procedure) |
| *(shared)* `references/harness-init-resume.md` | CLI init/resume semantics (error recovery, `--force`, archival) |
| *(shared)* `references/orchestrator-loop-single.md` | Per-iteration loop (review, refactor) |
| *(shared)* `references/orchestrator-loop-paired.md` | Per-cycle loop (coverage) |
| *(shared)* `references/harness-mode.md`, `references/coverage-harness-mode.md` | Subagent-side single-pass protocols |

The loop primitives (snapshot, parse, deep-step, commit-checkpoint, check-termination, final-report) live in `scripts/harness_common/cli.py` — see [.claude/docs/architecture.md](../../.claude/docs/architecture.md) for the data flow.

## License

[MIT](../../LICENSE)
