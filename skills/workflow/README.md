# optimus:workflow

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that implements an approved spec by having Claude **design and run its own [dynamic workflow](https://code.claude.com/docs/en/workflows)** — an orchestration of real parallel subagents that build the spec in the background.

You hand the skill a spec, a goal, and the constraints; Claude decides the phases, how many agents to run, and how they divide and cross-check the work. Intermediate results stay inside the workflow, so your main conversation stays clean and only the final, verified result returns. It is the self-orchestrated, parallel counterpart to `/optimus:tdd`'s supervised Red-Green-Refactor — pick it for large or parallelizable specs where one linear pass is slow.

Two facts to expect: Claude Code shows the planned phases for you to **approve before the run starts**, and a workflow uses **meaningfully more tokens** than a normal conversation (it spawns many agents).

## Workflow vs. TDD — which to use

Both implement an approved spec and hand off to `/optimus:pr`. They differ in *how* they build:

| | `/optimus:workflow` | `/optimus:tdd` |
|---|---|---|
| Shape | Parallel fan-out — Claude designs its own dynamic workflow | Sequential Red-Green-Refactor, one behavior per cycle |
| Who designs the build | Claude (phases, agent counts, cross-checking) | The skill (fixed cycle); you approve the behavior list |
| Test-first | Quality bar — tests accompany/precede code, suite left green | Enforced ceremony — failing test first (the Iron Law), then minimal pass, then refactor |
| Failing-test-first guarantee | No | Yes (per behavior) |
| User input | Launch-time phase approval only; none mid-run | Interactive checkpoints throughout |
| Best for | Large or parallelizable specs; many independent components; speed via fan-out | Tight test-first guarantee; bug fixes (reproduce-first); incremental, reviewable cycles |
| Commits | One (or few) after the fan-out | One per cycle |
| Token cost | Meaningfully higher (many parallel agents) | Normal session |
| Both | Require `/optimus:init`; auto-detect a spec in `docs/specs/`/`docs/jira/`; create a feature branch; push; hand off to `/optimus:pr` in the same conversation |

Rule of thumb: if the spec's value hinges on a failing-test-first proof — most bug fixes, anything where an after-the-fact test would just confirm the bug — use `/optimus:tdd`. Reach for `/optimus:workflow` when the spec is large or parallelizable and a verified-green suite produced by fan-out is the right trade of rigor for speed.

## Prerequisites

1. **`/optimus:init`** — required. Installs `CLAUDE.md`, `coding-guidelines.md`, the test framework/runner, and `testing.md` — these become the workflow's quality bar.
2. **Dynamic workflows enabled** — the Workflow tool available in your session (on some plans it must be turned on in `/config`).
3. **`/optimus:permissions`** — recommended. Branch-aware git protection so the workflow builds on a feature branch while protecting main/master. (Workflow agents auto-approve file edits, so bounding the branch and the edit scope matters.)
4. **`gh` or `glab` CLI** — optional. Needed when you run `/optimus:pr` afterward.

**Setup workflow**: `/optimus:init` → (`/optimus:brainstorm` to write a spec) → `/optimus:workflow`

## Usage

In Claude Code:

- `/optimus:workflow` — auto-detects the most recent spec in `docs/specs/` (or `docs/jira/`) and asks to confirm
- `/optimus:workflow docs/specs/2026-06-04-import-pipeline.md` — point it at a specific spec
- `/optimus:workflow "Build the CSV import pipeline with validation and dedupe"` — describe the goal inline

It is strongest right after `/optimus:brainstorm` writes a spec with a clear Components list and Out-of-Scope section — those become the workflow's scope bounds.

## How It Works

1. Verifies project context (`CLAUDE.md`, `coding-guidelines.md`, `testing.md`) and a **green** test baseline.
2. Acquires the spec via the shared context-detection cascade (explicit path → `docs/specs/` auto-discovery → `docs/jira/` → inline → ask), distilling a long spec to a single-sentence goal.
3. Creates a feature branch from the current branch — requires a clean working tree (commit or stash first), since everything uncommitted after this point is treated as workflow output. The workflow builds here; your original branch stays clean.
4. Hands Claude a natural-language brief and **runs the workflow** — Claude designs the orchestration (phases, agent counts, cross-checking) and builds in the background. You approve the planned phases first.
5. **Independently re-verifies** the result: runs the full suite fresh and confirms it is green (plus lint/type-check if configured). Never trusts the workflow's self-report.
6. Emits an `## Implementation Summary` block (components, tests, verification, coverage).
7. Commits, pushes, and recommends `/optimus:pr` in the same conversation.

## What You Control vs. What Claude Controls

- **You control:** the spec and goal, the in-scope/out-of-scope bounds, and the edit-forbidden paths. These are guardrails the workflow must respect.
- **Claude controls:** the orchestration shape — how many agents, what phases, where to fan out vs. pipeline, and where to cross-check. The skill deliberately does **not** prescribe phases or agent counts; Anthropic's guidance is that Claude chooses the shape that fits the task.

## Example Output

```
## Implementation Summary

### Components Built
| # | Component | Tests | Status |
|---|-----------|-------|--------|
| 1 | CSV parser | src/import/__tests__/parser.test.ts | ✓ Complete |
| 2 | Row validator | src/import/__tests__/validator.test.ts | ✓ Complete |
| 3 | Dedupe pass | src/import/__tests__/dedupe.test.ts | ✓ Complete |
| 4 | Bulk-upsert sink | — | Deferred — needs schema sign-off |

### Stats
- Orchestration: fan-out by component (4 agents), then 1 integration pass
- Tests: 18 written, all passing ✓
- Files created: src/import/parser.ts, validator.ts, dedupe.ts (+ tests)
- Files modified: src/import/index.ts

### Verification
- Test suite: `npm test` — 142 passed, exit 0
- Type-check: `tsc --noEmit` — clean

### Coverage
- Before: 44%
- After: 51%
- Delta: +7%

### Git Activity
- Branch: `feat/csv-import-pipeline` (from `main`)
- Commits: 1
- Pushed: ✓
```

## Caveats

- **No mid-run input.** A workflow runs to completion; for sign-off between stages you would run separate workflows. The skill's checkpoints are *before* (phase approval) and *after* (green-suite verification).
- **Edits are auto-approved.** Workflow subagents edit with `acceptEdits` regardless of your session mode. The feature branch and the brief's edit-mode boundary are what keep changes in scope — `/optimus:permissions` is recommended. Under Claude Code's [auto mode](https://code.claude.com/docs/en/permission-modes#eliminate-prompts-with-auto-mode), this `acceptEdits` does not bypass safety: the classifier still reviews each subagent action (and the delegated task at spawn), and subagent permission modes are ignored — so the feature branch and the permissions hook remain the deterministic boundary.
- **Higher token use.** Run it on a small slice first to gauge spend on a large spec; you can stop a run from `/workflows` without losing completed work.
- **The green suite is the completion gate.** The skill re-runs the suite itself and will not commit a red or partial result.
- **`/optimus:workflow` (the skill) vs. "run a workflow" (the feature).** Invoking this skill is an explicit `/optimus:` command. Asking Claude to "run a workflow" in chat triggers the raw dynamic-workflow feature for an ad-hoc task — a different thing. For implementing a tracked spec, prefer this skill.

## Relationship to Other Skills

| | `/optimus:workflow` | `/optimus:brainstorm` |
|---|---|---|
| Purpose | Implement a spec via a parallel build | Explore design approaches and write the spec |
| Context flow | Consumes the spec in `docs/specs/` | Writes the spec `/optimus:workflow` consumes |

| | `/optimus:workflow` | `/optimus:pr` |
|---|---|---|
| Role | Builds, verifies green, emits `## Implementation Summary` | Reads that summary to populate `## Intent` and the per-component `## Test plan` |
| Handoff | Recommends `/optimus:pr` in the same conversation | Full Conventional PR flow (default-branch detection, CLI install, preview/confirm) |

For `/optimus:workflow` vs. `/optimus:tdd`, see the **Workflow vs. TDD — which to use** table at the top of this README.

**Full workflow**: `/optimus:init` → `/optimus:brainstorm` (write the spec) → `/optimus:workflow` (parallel build — creates branch, commits, pushes) → `/optimus:pr` in the same conversation (create the PR/MR, Intent/Test-plan from the summary) → `/optimus:code-review` in a fresh conversation. `/optimus:tdd` is the supervised, test-first alternative to `/optimus:workflow` at the build step.

## Skill Structure

| File | Purpose |
|---|---|
| `SKILL.md` | Skill definition — 7-step workflow-driven implementation |
| *(shared)* `tdd/references/spec-context-detection.md` | Spec/JIRA context-detection cascade + distillation (shared with `/optimus:tdd`) |
| *(shared)* `tdd/references/coverage-detection.md` | Coverage-command detection + omit rule (shared with `/optimus:tdd`) |
| *(shared)* `init/references/multi-repo-detection.md` | Multi-repo workspace detection |
| *(shared)* `init/references/constraint-doc-loading.md` | Constraint doc loading — Monorepo Scoping Rule |
| *(shared)* `init/references/verification-protocol.md` | Verification gate for the post-workflow green-suite check |
| *(shared)* `commit/references/branch-naming.md` | Branch naming convention |
| *(shared)* `commit-message/references/conventional-commit-format.md` | Conventional commit message format |

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) with dynamic workflows available
- Git
- Project initialized with `/optimus:init` (required — provides `coding-guidelines.md` and `testing.md` as the quality bar)
- Working test infrastructure (framework, runner) — run `/optimus:init` first if missing

## License

[MIT](../../LICENSE)
