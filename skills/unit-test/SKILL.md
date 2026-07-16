---
description: Improves unit test coverage on demand — discovers coverage gaps and writes new tests that follow project conventions. Conservative by design — only adds tests (new files, or new cases appended to existing test files), never modifies existing test logic or source code; structurally untestable code is flagged for /optimus:refactor instead of being changed. Requires /optimus:init to have set up test infrastructure. Use when coverage is low or after adding code that lacks tests; for an automated multi-cycle coverage loop, use /optimus:deep coverage.
disable-model-invocation: true
argument-hint: "[path]"
---

# Unit Test Coverage Improvement

Improve unit test coverage for existing code. Conservative by design: only add new tests — new files, or new cases appended to existing test files. Never refactor or restructure source code; if code is untestable as-is, flag it rather than change it. Refactoring is the domain of `/optimus:refactor`.

## Step 1: Pre-flight

Arguments are optional scope instructions (e.g. `/optimus:unit-test src/api` scopes discovery and planning to that path).

### Harness mode detection

If your invocation prompt body contains `HARNESS_MODE_INLINE`, you are running as a single unit-test-phase pass inside the `/optimus:deep coverage` orchestrator. Read `$CLAUDE_PLUGIN_ROOT/references/coverage-harness-mode.md` and follow its "Unit-Test Phase Execution" section: skip user confirmation, run Steps 2–4 exactly once, then emit the structured JSON from Step 6 and stop. Do not use `AskUserQuestion`. Do not loop.

### Prerequisites

Read `$CLAUDE_PLUGIN_ROOT/skills/init/references/multi-repo-detection.md` for workspace detection. In a multi-repo workspace, run Steps 1–5 independently inside each repo that has `.claude/CLAUDE.md` and report results per repo; if no repo is initialized, suggest running `/optimus:init` from the workspace root.

Check that `.claude/CLAUDE.md` exists. If it doesn't, stop and recommend running `/optimus:init` first — the project needs baseline context before test generation can be effective.

Locate the guideline documents that shape everything this skill writes: `coding-guidelines.md` (quality standards) and `testing.md` (framework, runner commands, mocking patterns, file organization). If `testing.md` is missing, derive conventions from the existing test suite; if guidelines are missing entirely, the skill still works with less project-specific guidance. In a monorepo, apply the "Monorepo Scoping Rule" from `$CLAUDE_PLUGIN_ROOT/skills/init/references/constraint-doc-loading.md` — load the target subproject's `testing.md`, not another subproject's — and process each subproject independently.

## Step 2: Discovery & Coverage Analysis (agent-assisted)

Delegate infrastructure scanning, test execution, and coverage analysis to a reconnaissance agent, keeping the main context clean for test writing.

For each subproject (or the single project), launch **one** `general-purpose` Agent using the prompt from `$CLAUDE_PLUGIN_ROOT/skills/unit-test/agents/test-infrastructure-analyzer.md`, prepended with `$CLAUDE_PLUGIN_ROOT/skills/unit-test/agents/shared-constraints.md`.

**Cycle context (harness mode, cycles 2+):** when the progress file's `cycle.current` is greater than 1, also prepend the cycle context block specified in coverage-harness-mode.md ("Run discovery and coverage analysis") so the agent proposes new targets instead of re-discovering prior ones.

### Stop gates (evaluated from the agent's Discovery Results)

**Harness mode:** when a gate fires, don't write conversational handoffs — follow the "Stop gates under harness mode" rule in coverage-harness-mode.md: emit the Step 6 JSON immediately with a non-null `blocked` field and stop.

**No test framework detected** — stop. Recommend `/optimus:init` (or re-running it) to install a test framework and set up test infrastructure; for a project with no detectable stack yet, init's scaffold option builds a starter stack first. Never proceed to test generation without a working framework.

**Baseline test suite fails** — stop. This skill never fixes pre-existing failing tests or build issues; a green baseline is required before adding tests. Distinguish the two failure kinds from the agent's report:

- *Assertion failures* (tests compile and run, but some fail): list each failing test with a one-line failure excerpt so the user can triage in this conversation. Once the baseline is green, re-run `/optimus:unit-test` in a fresh conversation.
- *Build/bootstrap failures* (the runner cannot start or test files fail to compile): these are build-level issues — recommend `/optimus:init`, whose health check owns that repair path, then re-running this skill.

### Data carried forward

From the agent's Discovery Results, present the infrastructure findings and coverage analysis to the user, and carry forward: the test runner command and framework, coverage tooling, baseline coverage (for the before/after comparison), and the testability classification (testable items become plan candidates; untestable items are flagged, not attempted).

## Step 3: Test Generation Plan

Create a prioritized list, **capped at 10 items per run**:

1. Exported/public functions and classes — API surface, highest value
2. Pure functions and utility modules — easiest to test, highest ROI
3. Business logic with clear inputs/outputs
4. Complex branching logic — most likely to hide bugs
5. Internal/private helpers — lowest priority; test through the public API when possible

**Skip** (flag in the summary, don't attempt): code untestable without refactoring, generated code (protobuf, OpenAPI, ORM migrations), migration files, declarative configuration, thin wrappers with no logic.

**Harness mode:** auto-approve all planned items and proceed to Step 4 — the orchestrator decides whether to iterate.

**Normal mode:** present the plan and confirm with the user before writing anything — they may approve everything, pick specific items, or skip generation and keep the plan as reference.

## Step 4: Test Writing

### Quality standards

Tests must follow:

- `coding-guidelines.md` — naming, structure, clarity
- `testing.md` — framework idioms, file naming, directory structure
- `$CLAUDE_PLUGIN_ROOT/skills/tdd/references/testing-anti-patterns.md` — mocking discipline: prefer real code over mocks, never assert on mock behavior, mock only external services or non-deterministic dependencies
- Existing test files — extract concrete patterns (import style, assertion library, naming, placement, shared fixtures, test organization) **before writing the first test** and apply them consistently

### Before each test

1. **File placement** — if a test file for the module already exists, add cases there; new files follow the `testing.md` naming convention.
2. **Fixture reuse** — use existing fixtures and shared setup (conftest, helpers, factories) instead of duplicating them privately.
3. **Mocking discipline** — apply the gate questions from testing-anti-patterns.md.
4. **Setup DRY** — extract repeated setup into shared fixtures per `coding-guidelines.md`.

### Conservative constraint

Only add new tests. Never modify existing test logic or source code — refactoring is the domain of `/optimus:refactor`. If a function can't be tested without changing its signature or extracting dependencies, flag it as untestable instead of changing it. In harness mode, flagged items become `untestable_code` entries in the Step 6 JSON — they feed the orchestrator's refactor phase.

### Per-test workflow

For each approved item:

1. Write the test, self-review against the checks above, run it immediately.
2. If it fails, fix the **test** (never the source) — max 3 attempts. In harness mode, a test that needed fixes before passing is recorded as `fail-fixed` in the Step 6 JSON.
3. Still failing after 3 attempts — flag the item as untestable and revert the test file (or remove the appended cases): an abandoned failing test must not remain active in either mode. Harness mode: record it as `fail-abandoned`.
4. If the failure reveals a **bug in existing code**, report the bug but do not fix it — keep it in the bugs-discovered list (`bugs_discovered` in harness mode), then revert the failing test the same way. Harness mode: record the item as `fail-abandoned` with `failure_reason` naming the bug.

### Final verification (normal mode only)

Run the **full test suite** and follow `$CLAUDE_PLUGIN_ROOT/skills/init/references/verification-protocol.md` — fresh run, complete output read, evidence before any success claim. If a newly-added test causes regressions under the full suite, revert it. (Harness mode: skip this run — the orchestrator owns the full run and bisection.)

## Step 5: Summary (normal mode)

**Harness mode:** skip — Step 6 emits the structured JSON instead.

Report to the user (per repo, in multi-repo workspaces):

- Coverage before → after, and the achievable target without refactoring
- Tests created — file, target, pass status
- Bugs discovered in existing code — reported, not fixed
- Code not testable without refactoring — with the structural change each would need

Close with what fits the results: re-run `/optimus:unit-test` to keep improving coverage incrementally; if untestable code was flagged, `/optimus:refactor testability` restructures it (then re-run this skill against the result); for sustained automated alternation of both, `/optimus:deep coverage`. Each is best run in a fresh conversation.

## Step 6: Harness Output (harness mode only)

If running under `HARNESS_MODE_INLINE`, output structured JSON **instead** of the Step 5 summary. The exact schema lives in `$CLAUDE_PLUGIN_ROOT/references/coverage-harness-mode.md` "Output structured JSON" — read it and emit the fenced block specified there. Then stop — do not loop, do not present recommendations, do not use `AskUserQuestion`.
