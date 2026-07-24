---
description: Improves unit test coverage on demand — discovers testing gaps via a reconnaissance agent and writes new tests that follow project conventions. Requires /optimus:init to have set up test infrastructure. Conservative — only adds new tests, never modifies existing test logic or source code; untestable code is flagged for /optimus:refactor. For an automated multi-cycle coverage loop, use /optimus:deep coverage.
disable-model-invocation: true
argument-hint: "[path]"
---

# Unit Test Coverage Improvement

Improve unit test coverage for existing code. Conservative by design — only adds new tests (new files, or new cases appended to existing test files), never modifies existing test logic or source code. Untestable code is flagged, not changed — refactoring is the domain of `/optimus:refactor`. An optional path argument scopes the run.

## Step 1: Pre-flight

### Inline harness mode detection

If your invocation prompt body contains `HARNESS_MODE_INLINE`, you are running inside the `/optimus:deep coverage` orchestrator as a single cycle (unit-test phase). Read `$CLAUDE_PLUGIN_ROOT/references/coverage-harness-mode.md` and follow its "Unit-Test Phase Execution" section: skip user confirmation, run Steps 2–4 exactly once, then output structured JSON via Step 6 and stop. Do not use `AskUserQuestion`. Do not loop.

### Prerequisites and project docs

If the current directory has no `.git/` directory, read `$CLAUDE_PLUGIN_ROOT/skills/init/references/multi-repo-detection.md` and apply it. In a multi-repo workspace, run Steps 1–5 independently inside each repo that has `.claude/CLAUDE.md` and report results per repo; if no repo is initialized, suggest running `/optimus:init` first from the workspace root.

Check that `.claude/CLAUDE.md` exists. If it doesn't, stop and recommend running `/optimus:init` first — the project needs baseline context before test generation can be effective.

Load `.claude/CLAUDE.md`, `.claude/docs/coding-guidelines.md`, and `testing.md` where present; if `testing.md` is missing, derive testing conventions from existing test files. In a monorepo (read `$CLAUDE_PLUGIN_ROOT/skills/init/references/project-detection.md` if the structure is unclear), process each subproject independently and load that subproject's own `docs/testing.md` / `docs/` files — never another subproject's; shared guidelines come from root `.claude/docs/`.

## Step 2: Discovery & Coverage Analysis (agent-assisted)

For each subproject (or the single project), read `$CLAUDE_PLUGIN_ROOT/skills/unit-test/agents/test-infrastructure-analyzer.md` and launch one `general-purpose` agent with that prompt, prepended with the "Agent Constraints" section of `$CLAUDE_PLUGIN_ROOT/references/shared-agent-constraints.md`. Assemble the prompt per "Prompt assembly at dispatch time" in `$CLAUDE_PLUGIN_ROOT/references/agent-architecture.md`. Under `HARNESS_MODE_INLINE` on cycles 2+, also prepend the cycle context block from the "Run discovery and coverage analysis" section of coverage-harness-mode.md.

Present the agent's Discovery Results and Coverage Analysis to the user.

### Stop gates (evaluated from agent results)

**Harness mode:** when a stop gate fires, do not print the conversational messages below — follow the "Stop gates under harness mode" rule in coverage-harness-mode.md: emit the Step 6 JSON immediately with a non-null `blocked` field and stop.

**If no test framework is detected** in the agent's Discovery Results, stop and report: "No test framework found. Run `/optimus:init` (or re-run it) to install a test framework and set up test infrastructure before using this skill. For a project with no code or detectable stack yet, pick **Scaffold new project** when init asks." Never generate tests without a working framework.

**If the agent's Test Suite Execution reports failures**, stop — this skill never fixes failing tests or build-level issues.

- **Fail - assertion** (tests compile and run, but some fail): print the quote below, then append a `### Bugs Discovered` section listing each failing test as `[test file] — [test name] — [one-line failure excerpt]` (prefix entries with repo name/path in multi-repo workspaces; omit the excerpt if the runner output did not expose it).

  > Pre-existing tests are failing. A green baseline is required before adding new tests, and this skill does not modify existing tests or source code. Stay in this conversation and ask Claude to triage the failing tests listed in Bugs Discovered; once the baseline is green, re-run `/optimus:unit-test` in a fresh conversation.

- **Fail - build** (build/bootstrap failures): print the quote below and stop — no Bugs Discovered section (there are no per-test failures, only build errors the analyzer has already summarized).

  > The test runner cannot start or test files fail to compile. These are build-level issues, not test logic, and `/optimus:init` owns that repair path. Run `/optimus:init` in a fresh conversation — its health check proposes minimal fixes and re-runs the suite. Once the build is healthy, re-run `/optimus:unit-test` in another fresh conversation.

## Step 3: Test Generation Plan

Create a prioritized list, **capped at 10 items per run**: exported/public functions and classes → pure functions and utility modules → business logic with clear inputs/outputs → complex branching logic → internal/private helpers (test through the public API when possible).

**Skip** (flag in the summary, don't attempt): code untestable without refactoring, generated code, migration files, declarative configuration, thin wrappers with no logic.

Present the plan, then use `AskUserQuestion` — header "Plan", question "How would you like to proceed with the test generation plan?": **Approve all** (generate tests for all planned items) / **Selective** (ask which item numbers to proceed with) / **Skip** (no tests — keep the plan as reference). Harness mode: skip the question, auto-approve all items — the orchestrator decides whether to iterate after Step 6.

## Step 4: Test Writing

**Conservative constraint:** only add new tests — new files, or new cases appended to existing test files. Never modify existing test logic or source code. If a function can't be tested without changing its signature or extracting dependencies, flag it in the summary instead of changing it.

Test-writing rules:

- Follow `coding-guidelines.md` (quality, naming, DRY) and `testing.md` (framework idioms, file naming, directory structure). Before writing the first test, extract the concrete patterns of existing test files — imports, assertion style, naming, placement, shared fixtures, test organization — and replicate them consistently.
- Before writing any test that needs a mock or fixture, read `$CLAUDE_PLUGIN_ROOT/skills/tdd/references/testing-anti-patterns.md` — prefer real code over mocks, mock only external services or non-deterministic dependencies, never assert on mock behavior.
- If a test file for the module already exists, add cases there instead of creating a new file. Reuse existing fixtures, helpers, and factories; extract repeated setup into shared fixtures instead of duplicating it.

Per-test workflow, for each approved item:

1. Write the test and run it immediately.
2. If it fails, fix the **test** (never the source code) — max 3 attempts. Still failing after 3? Flag the item as untestable and revert the test file (or remove the appended cases) before moving on — an abandoned failing test must not remain active in either mode. In harness mode, record the item as `fail-abandoned` in the Step 6 JSON.
3. If the failure reveals an actual **bug in existing code**, report it under Bugs Discovered (`bugs_discovered` in harness mode) but do not fix it, then revert the failing test the same way (harness: `fail-abandoned` with `failure_reason` naming the bug).

### Final verification (normal mode only)

After all tests are written, run the **full test suite** to ensure no regressions: run it fresh, read the complete output, and report the actual result with evidence (e.g. "14 passed, 1 failed") — never claim "should pass". If a newly added test file causes regressions (itself failing under the full suite, or breaking other tests), revert it. Harness mode: skip this run and any `scripts/*.sh` wrappers — the orchestrator owns the full run and bisection.

## Step 5: Summary

**Harness mode:** skip this step — Step 6 emits the structured JSON instead.

**Normal mode** — report to the user (one block per repo in multi-repo workspaces, with the repo name/path in each section header):

```
## Unit Test Summary

### Coverage
- Coverage tooling: [tool name / not configured]
- Before: [X]% → After: [Y]%
- Achievable target (without refactoring): ~[Z]%

### Tests Created
| # | File | Target | Status |
|---|------|--------|--------|
| 1 | src/__tests__/auth.test.ts | auth module exports | Pass |

### Bugs Discovered
- [Bugs found in existing code — reported, not fixed]

### Not Testable Without Refactoring
- [Flagged code, with the structural change each item would need]
```

If untestable code was flagged, recommend `/optimus:refactor testability` in a fresh conversation to restructure it; otherwise recommend `/optimus:commit`, staying in this conversation so the context is captured. For an automated loop that alternates test generation with testability refactoring, mention `/optimus:deep coverage`.

## Step 6: Harness Output (harness mode only)

If running under `HARNESS_MODE_INLINE`, output structured JSON **instead** of the Step 5 summary — the exact schema lives in `$CLAUDE_PLUGIN_ROOT/references/coverage-harness-mode.md` "Output structured JSON". Emit the fenced block, then stop — do not loop, do not present recommendations, do not use `AskUserQuestion`.
