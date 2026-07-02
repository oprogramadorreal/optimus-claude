# optimus:refactor-deep

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that runs `/optimus:refactor` in an iterative cleanup loop. Each iteration runs in a fresh subagent context, so the loop is not bounded by single-conversation context decay. Fixes are applied automatically, the test suite runs after every iteration, and failed fixes are reverted via bisection.

This is the orchestrator replacement for the previous `/optimus:refactor deep` and `/optimus:refactor deep harness` modes (removed in 2.0.0).

## Features

- **Fresh subagent per iteration** — each pass spawns a new `general-purpose` subagent. Refactor agents (guideline-reviewer, testability-analyzer, consistency-analyzer, code-simplifier) run in an isolated context window.
- **Focus modes** — `testability` prioritizes barriers that block unit testing; `guidelines` prioritizes coding-guideline violations. The focus is recorded in the progress file and applied by the base skill's finding-cap weighting.
- **Automatic test verification + bisection** — fixes that break tests are reverted one at a time, leaving the working tree in the most-fixed state that passes tests.
- **Per-iteration checkpoint commits** — each iteration produces a tagged commit (`refactor(deep-orchestrator): iteration N — M fixed`) listing the applied fixes.
- **Termination detection** — convergence, no-actionable-fixes, all-reverted, iteration cap, diminishing-returns soft-exit.
- **Resumable** — `--resume` continues from `.claude/refactor-deep-progress.json`.

## Quick Start

This skill is part of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin. See the [main README](../../README.md) for installation instructions.

## Usage

```
/optimus:refactor-deep                                # Feature-branch diff (full project when no diff), 8 iterations, balanced
/optimus:refactor-deep testability                    # Focus on testability barriers
/optimus:refactor-deep guidelines src/backend         # Guidelines focus, scoped to a path
/optimus:refactor-deep --max-iterations 12            # Raise iteration cap (hard cap 20)
/optimus:refactor-deep --resume                       # Continue from existing progress file
/optimus:refactor-deep --no-commit                    # Skip per-iteration checkpoint commits
/optimus:refactor-deep --allow-red-baseline           # Proceed even if the pre-loop baseline suite is red
claude -p "/optimus:refactor-deep --yes testability"  # Headless / CI; auto-confirms Step 3
```

Scope accepts an existing path to restrict the refactor to it. Natural-language text is recorded as intent but does not filter. With no path scope, iteration 1 covers the feature-branch diff when one exists, otherwise the full project; scope then widens per iteration to files with active findings and newly modified files.

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Python 3.8+ (the orchestrator uses `python -m harness_common.cli`)
- Git
- Project initialized with `/optimus:init`
- Test command in `.claude/CLAUDE.md`
- Clean working tree (or `--no-commit` to allow uncommitted state)

## When to Use Which Focus

| Focus | When | Effect |
|---|---|---|
| `testability` | Before `/optimus:unit-test-deep`, when coverage is low and you suspect untestable code is blocking progress | Prioritizes findings that remove dependency injection barriers, hardcoded I/O, and other hooks-for-test |
| `guidelines` | After `/optimus:init` establishes coding-guidelines.md, when style/convention violations are widespread | Prioritizes findings that align code with project guidelines |
| *(none — balanced)* | General periodic cleanup | Even allocation across all finding categories |

## Termination Reasons

| Reason | Meaning |
|---|---|
| `convergence` | The base skill reported `no_new_findings` — no further refactor opportunities. |
| `no-actionable` | Findings exist but none had concrete code edits to apply. |
| `all-reverted` | Every fix in the most recent iteration caused test failures. |
| `cap` | The iteration cap was reached. |
| `diminishing-returns` | Yield plateaued at ≤1 finding/iteration for 2 consecutive iterations after iter 4. |
| `parse-failure` | Two consecutive iterations produced no parseable JSON. |

## Cancellation

Press Esc twice in Claude Code to interrupt. The orchestrator writes the progress file **before** every subagent dispatch — interrupting between dispatches is fully recoverable via `--resume`.

## Skill Structure

| File | Purpose |
|---|---|
| `SKILL.md` | Orchestrator instructions |
| *(shared)* `references/harness-init-resume.md` | Shared CLI init/resume semantics (error recovery, `--force`, archival) |
| *(shared)* `references/orchestrator-loop-single.md` | Per-iteration loop template |
| *(shared)* `references/harness-mode.md` | Single-iteration protocol for the base `/optimus:refactor` skill |

The orchestration loop's primitives (snapshot, parse, deep-step, commit-checkpoint, check-termination, advance, final-report) are dispatched via the project-level `scripts/harness_common/cli.py` — see [.claude/docs/architecture.md](../../.claude/docs/architecture.md) for the data flow.

## Known Limitations

- **Per-iteration latency can be high.** Each iteration dispatches a fresh subagent that runs the base skill's full analysis, so a multi-iteration run over a large diff can take a long time. Budget time and credits, or scope the run to a path.
- **Subagent fan-out is unverified.** The per-iteration subagent is expected to launch the base skill's parallel analysis agents; whether nested subagent spawning actually occurs in practice (vs. collapsing to a single inline analysis) has not been confirmed empirically. The loop is correct either way — only the analysis breadth would differ. Tracked as a follow-up.

## License

[MIT](../../LICENSE)
