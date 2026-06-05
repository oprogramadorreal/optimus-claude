# optimus:code-review-deep

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that runs `/optimus:code-review` in an iterative auto-fix loop. Each iteration runs in a fresh subagent context — fixing the context-decay problem that limits single-conversation deep modes — and applies fixes, runs tests, and bisects failures automatically.

This is the orchestrator replacement for the previous `/optimus:code-review deep` (in-conversation loop) and `/optimus:code-review deep harness` (external Python orchestrator) modes. The two old modes were removed in 2.0.0; the iterative auto-fix experience now lives entirely behind this slash command.

## Features

- **Fresh subagent per iteration** — each pass spawns a new `general-purpose` subagent. The base skill's analysis runs in an isolated context window; the orchestrator's own conversation stays slim.
- **Automatic test verification + bisection** — after each iteration's fixes, the project test suite runs. If tests fail, the orchestrator reverts everything and re-applies fixes one at a time, keeping only those that pass.
- **Per-iteration checkpoint commits** — unless `--no-commit` is passed, each iteration produces a tagged commit (`fix(deep-orchestrator): iteration N — M fixed`) that lists the applied fixes in its body.
- **Termination detection** — convergence (no new findings), no-actionable-fixes, all-reverted, iteration cap, and diminishing-returns soft-exit.
- **Resumable** — interrupted runs can be resumed with `--resume`. Progress lives in `.claude/code-review-deep-progress.json`.
- **Branch-aware scope** — pre-populates the scope from `git diff --name-only origin/<base>...HEAD` with optional path filtering.
- **PR description capture** — when invoked on a branch with an open PR, the orchestrator captures the PR title/body for intent-aware review.

## Quick Start

This skill is part of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin. See the [main README](../../README.md) for installation instructions.

## Usage

```
/optimus:code-review-deep                           # 8 iterations on the branch diff
/optimus:code-review-deep --max-iterations 12       # 12 iterations
/optimus:code-review-deep src/auth                  # Scope to an existing path
/optimus:code-review-deep --resume                  # Continue from existing progress file
/optimus:code-review-deep --no-commit               # Skip per-iteration checkpoint commits
claude -p "/optimus:code-review-deep --yes 'src/auth'"   # Headless / CI; auto-confirms Step 3
```

Scope accepts an existing path (file or directory) to restrict the review to it. Natural-language text is recorded as intent but does not filter the diff — the full branch diff is reviewed unless the scope resolves to a real path.

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Python 3.8+ (the orchestrator uses `python -m harness_common.cli`)
- Git
- Project initialized with `/optimus:init`
- Test command in `.claude/CLAUDE.md`
- Clean working tree (or `--no-commit` to allow uncommitted state)

## Termination Reasons

| Reason | Meaning |
|---|---|
| `convergence` | The base skill reported `no_new_findings` — the codebase looks clean. |
| `no-actionable` | Findings exist but none had concrete code edits to apply. |
| `all-reverted` | Every fix in the most recent iteration caused test failures. |
| `cap` | The iteration cap was reached. Resume with a higher cap if needed. |
| `diminishing-returns` | After iteration 4, two consecutive iterations produced ≤1 new finding and 0 reverted fixes. The remaining issues, if any, can be resumed in a fresh conversation via `--resume`. |
| `parse-failure` | Two consecutive iterations produced no parseable JSON from the subagent. |

## How It Differs from `/optimus:code-review`

| Aspect | `/optimus:code-review` | `/optimus:code-review-deep` |
|---|---|---|
| Iterations | 1 (single pass) | Up to 20 (default 8) |
| Fix approval | User chooses (Fix / Post / Skip) | Confirmed once upfront |
| Test verification | After user-approved fixes | After every iteration, with bisection on failure |
| Output | Immediate report | Cumulative report covering every iteration |
| Conversation context | Holds the analysis | Stays slim — each iteration runs in a fresh subagent |
| Requirement | None | Test command in `.claude/CLAUDE.md`, clean working tree |

## Cancellation

Press Esc twice in Claude Code to interrupt. The orchestrator writes the progress file **before** every subagent dispatch — interrupting between dispatches is fully recoverable via `--resume`. Interrupting mid-dispatch (while a subagent is running) may leave the working tree with partial edits from that iteration; in that case, run `git status` to inspect, then either `git restore .` to discard the partial work or `--resume` to keep it.

## Skill Structure

| File | Purpose |
|---|---|
| `SKILL.md` | Orchestrator instructions |
| *(shared)* `references/orchestrator-loop-single.md` | Per-iteration loop template |
| *(shared)* `references/harness-mode.md` | Single-iteration protocol for the base `/optimus:code-review` skill |

The orchestration loop's primitives (snapshot, parse, deep-step, commit-checkpoint, check-termination, advance, final-report) are dispatched via the project-level `scripts/harness_common/cli.py` — see [.claude/docs/architecture.md](../../.claude/docs/architecture.md) for the data flow.

## Known Limitations

- **Per-iteration latency can be high.** Each iteration dispatches a fresh subagent that runs the base skill's full analysis, so a multi-iteration run over a large diff can take a long time (one observed run took ~45 min for a single iteration over an 18-file diff). Budget time and credits, or scope the run to a path.
- **Subagent fan-out is unverified.** The per-iteration subagent is expected to launch the base skill's parallel analysis agents; whether nested subagent spawning actually occurs in practice (vs. collapsing to a single inline analysis) has not been confirmed empirically. The loop is correct either way — only the analysis breadth would differ. Tracked as a follow-up.

## License

[MIT](../../LICENSE)
