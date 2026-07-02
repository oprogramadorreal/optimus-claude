# optimus:unit-test-deep

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that runs an iterative test-coverage improvement loop. Each cycle is two subagent dispatches in fresh contexts: a **unit-test phase** that writes tests and measures coverage, and a **refactor phase** (only when the first phase flags untestable code) that unblocks testability barriers.

This is the orchestrator replacement for the previous `/optimus:unit-test deep` and `/optimus:unit-test deep harness` modes (removed in 2.0.0).

## Features

- **Paired cycles** — alternates writing tests and unblocking testability, so a single skill cannot stall on untestable code.
- **Fresh subagent per phase** — both the unit-test phase and the refactor phase run in their own isolated context windows.
- **Coverage tracking** — baseline coverage is captured on cycle 1; per-cycle deltas are recorded in the progress file's coverage history.
- **Automatic test verification + bisection** — after the refactor phase, the project test suite runs. If tests fail, the orchestrator reverts everything and re-applies fixes one at a time.
- **Per-phase checkpoint commits** — each phase produces a tagged commit (`test(coverage-orchestrator): cycle N — M tests written` or `refactor(coverage-orchestrator): cycle N — M fixed`).
- **Termination detection** — convergence (no new tests + no untestable / no coverage gained), cycle cap, coverage plateau (zero delta for 2 consecutive cycles).
- **Resumable** — `--resume` continues from `.claude/unit-test-deep-progress.json`.

## Quick Start

This skill is part of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin. See the [main README](../../README.md) for installation instructions.

## Usage

```
/optimus:unit-test-deep                          # 5 cycles, full project
/optimus:unit-test-deep --max-cycles 8           # 8 cycles
/optimus:unit-test-deep src/api                  # Scoped to a path
/optimus:unit-test-deep --resume                 # Continue from existing progress file
/optimus:unit-test-deep --no-commit              # Skip per-phase checkpoint commits
claude -p "/optimus:unit-test-deep --yes src/api"  # Headless / CI; auto-confirms Step 3
```

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Python 3.8+ (the orchestrator uses `python -m harness_common.cli`)
- Git
- Project initialized with `/optimus:init`
- Test command + coverage tooling in `.claude/CLAUDE.md`
- Clean working tree (or `--no-commit` to allow uncommitted state)

## Cycle Structure

Each cycle runs in this order:

1. **Snapshot** the pre-cycle git HEAD.
2. **Unit-test phase** — dispatch `/optimus:unit-test` as a subagent. It writes new tests for uncovered code paths, measures coverage delta, and flags code that cannot be tested without refactoring.
3. **Record** the unit-test outputs into the progress file. Commit a checkpoint (`test(coverage-orchestrator): cycle N`).
4. **Check** whether the unit-test phase flagged any untestable items still pending. If none, skip steps 5–6.
5. **Refactor phase** — dispatch `/optimus:refactor` with `testability` focus and a scope filter restricting it to the flagged files. It applies refactors that remove testability barriers.
6. **Test + bisect** — run the full test suite. On failure, the CLI bisects: reverts all fixes, re-applies one at a time, keeps only those that pass. Commit a checkpoint (`refactor(coverage-orchestrator): cycle N`).
7. **Record** the cycle history, advance the cycle counter, check termination.

## Termination Reasons

| Reason | Meaning |
|---|---|
| `convergence` | The unit-test phase reported no new tests possible + no untestable code (or no coverage gained); OR the refactor phase reported no testability findings. |
| `cap` | The cycle cap was reached. |
| `diminishing-returns` | Coverage delta was exactly 0 (zero coverage gain) for 2 consecutive cycles. |
| `parse-failure` | Two consecutive cycles produced no parseable JSON from a subagent. |

## Cancellation

Press Esc twice in Claude Code to interrupt. The orchestrator writes the progress file **before** every subagent dispatch — interrupting between phases is fully recoverable via `--resume`.

## Relationship to Other Skills

- `/optimus:unit-test-deep` orchestrates `/optimus:unit-test` and `/optimus:refactor` (with `testability` focus). The base skills themselves still work without it — use the base skills for a single pass; use the orchestrator when you want sustained coverage improvement.
- `/optimus:refactor-deep` with `testability` focus is a one-skill alternative: it unblocks testability barriers but does not write tests. Use `/optimus:unit-test-deep` when you want both, or when test coverage gaps and testability barriers reinforce each other.

## Skill Structure

| File | Purpose |
|---|---|
| `SKILL.md` | Orchestrator instructions |
| *(shared)* `references/harness-init-resume.md` | Shared CLI init/resume semantics (error recovery, `--force`, archival) |
| *(shared)* `references/orchestrator-loop-paired.md` | Per-cycle loop template |
| *(shared)* `references/coverage-harness-mode.md` | Single-pass protocol for the unit-test phase |
| *(shared)* `references/harness-mode.md` | Single-pass protocol for the refactor phase |

The orchestration loop's primitives (snapshot, parse, unit-test-step, refactor-step, record-cycle, commit-checkpoint, check-termination, final-report) are dispatched via the project-level `scripts/harness_common/cli.py` — see [.claude/docs/architecture.md](../../.claude/docs/architecture.md) for the data flow.

## Known Limitations

- **High per-cycle cost.** Each cycle is two subagent dispatches (unit-test, then a conditional refactor phase) plus a full test-suite run, making deep unit-test runs the most expensive of the three orchestrators. The default of 5 cycles suits most projects.
- **Subagent fan-out is unverified.** Each phase's subagent is expected to launch the base skill's parallel agents; whether nested subagent spawning actually occurs in practice (vs. collapsing to a single inline analysis) has not been confirmed empirically. The loop is correct either way — only the analysis breadth would differ. Tracked as a follow-up.

## License

[MIT](../../LICENSE)
