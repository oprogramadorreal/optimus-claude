# optimus:deep

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that runs a resumable multi-iteration auto-fix loop. Each iteration dispatches a base skill into a fresh subagent context — sidestepping the context decay that limits single-conversation loops — then applies its fixes, runs the project test suite, and bisects failures so only fixes that keep tests green survive.

One command, three modes. It replaces the 2.x `code-review-deep`, `refactor-deep`, and `unit-test-deep` skills — those slash-command entry points no longer exist (headless scripts should call `claude -p "/optimus:deep <mode> --yes"` instead).

## Modes

| Mode | Runs | Loop shape | Good for |
|---|---|---|---|
| `review` | `/optimus:code-review` per iteration | Single skill, up to 20 iterations (default 8) | Thorough cleanup of a branch before release or PR |
| `refactor` | `/optimus:refactor` per iteration; optional `testability` or `guidelines` focus | Single skill, up to 20 iterations (default 8) | Project-wide guideline alignment or testability cleanup |
| `coverage` | `/optimus:unit-test`, then `/optimus:refactor` (testability) when untestable code is flagged | Paired cycles, up to 10 (default 5) | Driving coverage up on a codebase with testability barriers |

## Usage

```
/optimus:deep review                       # 8 iterations on the branch diff
/optimus:deep review src/auth              # scoped to an existing path
/optimus:deep refactor testability         # focus on testability barriers
/optimus:deep refactor guidelines --max 12 # guidelines focus, raised cap
/optimus:deep coverage                     # paired test + refactor cycles
/optimus:deep <mode> --resume              # continue an interrupted run
/optimus:deep <mode> --no-commit           # skip checkpoint commits
claude -p "/optimus:deep review --yes"     # headless / CI; auto-confirms the upfront prompt
```

Scope accepts an existing path (file or directory). Other text is recorded as intent but does not filter what gets analyzed.

## How a run works

**Review / refactor** — each iteration: snapshot git state, dispatch the base skill into a fresh subagent, parse its structured JSON, apply the fixes, run the test suite (reverting fix-by-fix via bisection on failure), commit a checkpoint, check termination, advance.

**Coverage** — each cycle is up to two dispatches: a unit-test phase that writes tests, measures coverage, and flags untestable code (a red suite rolls the whole cycle back rather than committing it), then — only when untestable items are pending — a refactor phase scoped to the flagged files, with bisection on failure. Each phase gets its own checkpoint commit.

Fixes are applied automatically: one upfront confirmation stands for the whole run. State is written to a progress file in `.claude/` before every dispatch, so interrupting (Esc twice) between dispatches is fully recoverable with `--resume`; interrupting mid-dispatch may leave partial edits in the working tree.

## Requirements

- Project initialized with `/optimus:init` (`.claude/CLAUDE.md` present)
- A test command documented in `.claude/CLAUDE.md` (or supplied when asked)
- Python 3.8+ and Git
- Clean working tree (or `--no-commit`)
- Review / refactor: a green test suite at the start — a red baseline stops the run before the loop
- Coverage: a project with no tests yet may start red; a project whose existing tests fail stops before the loop

## Termination reasons

| Reason | Meaning |
|---|---|
| `convergence` | Review/refactor: the base skill reported no new findings. Coverage: the unit-test phase plateaued (no new tests + no untestable code, or no coverage gained), or the refactor phase found nothing actionable. |
| `no-actionable` | Findings exist but none had concrete code edits to apply (review/refactor only). |
| `all-reverted` | Every fix in the latest iteration broke tests and was reverted (review/refactor only). |
| `cap` | The iteration/cycle cap was reached. Re-run with a higher `--max` for another pass. |
| `diminishing-returns` | Review/refactor: from iteration 4 on, the last two iterations each yielded at most one new finding with zero reverted fixes. Coverage: zero coverage gain for two consecutive cycles. A soft exit — the run stays resumable with `--resume`. |
| `parse-failure` | Two consecutive subagent dispatches produced no parseable output (in coverage mode the counter spans phases, so a refactor failure followed by the next cycle's unit-test failure qualifies). |

## Resuming

`--resume` continues a run whose progress file is still on disk: an interrupt or a `diminishing-returns` soft exit. Pass `--max N` alongside it to raise the cap. Runs that finished cleanly are archived to a `.done.json` sibling, which `--resume` refuses — just re-run `/optimus:deep <mode>` for a fresh pass.

## Relationship to the base skills

The base skills work standalone: use `/optimus:code-review`, `/optimus:refactor`, or `/optimus:unit-test` for a single supervised pass where you approve each change. Use `/optimus:deep` when you want sustained, unattended progress — it trades per-change approval for test-verified automation. Each iteration re-runs the base skill's full analysis in a fresh subagent, so multi-iteration runs over large diffs take real time and credits; scope to a path or lower `--max` to budget.

## Skill structure

| File | Purpose |
|---|---|
| `SKILL.md` | Orchestrator instructions (modes, pre-flight, baseline gate, loop dispatch) |
| *(shared)* `references/harness-init-resume.md` | CLI init/resume semantics (error recovery, `--force`, archival) |
| *(shared)* `references/orchestrator-loop.md` | Single-skill and paired-cycle loop templates |
| *(shared)* `references/harness-mode.md` | Single-iteration protocol for the code-review / refactor phases |
| *(shared)* `references/coverage-harness-mode.md` | Single-pass protocol for the unit-test phase |

The loop's primitives (snapshot, parse, deep-step, unit-test-step, refactor-step, record-cycle, commit-checkpoint, check-termination, advance, final-report) live in `scripts/harness_common/cli.py` — see [.claude/docs/architecture.md](../../.claude/docs/architecture.md) for the data flow.

## License

[MIT](../../LICENSE)
