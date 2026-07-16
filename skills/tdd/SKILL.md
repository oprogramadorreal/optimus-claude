---
description: Implements a feature or bug fix test-first through Red-Green-Refactor cycles — decomposes the task into small observable behaviors, writes a failing test before any production code, implements the minimum to pass, then refactors against the project's coding guidelines. Auto-detects approved specs in docs/specs/ and uses their Given/When/Then scenarios as the behavior list. Creates a feature branch, commits after each behavior, runs quality-gate agents, and pushes at the end. Requires /optimus:init context (CLAUDE.md, coding guidelines, testing conventions) and a green test suite as the starting baseline. Use when starting a new feature or bug fix with test-first discipline; for restructuring without behavior change, use /optimus:refactor.
disable-model-invocation: true
argument-hint: "[task description or spec path]"
---

# Test-Driven Development

Implement a feature or bug fix through Red-Green-Refactor cycles: write a failing test (Red), write the minimum code to pass it (Green), clean up while tests stay green (Refactor). One behavior per cycle.

**The Iron Law: no production code without a failing test first.** If implementation code gets written before its test exists, delete it entirely — don't keep it as reference, don't adapt it — and restart the cycle from the failing test.

## Suitability

TDD fits work with testable behavior: new features, bug fixes, API endpoints, business logic. Redirect what doesn't fit:

- **Refactoring** (restructuring without behavior change) — recommend `/optimus:refactor`, where existing tests verify preservation.
- **Documentation, configuration, or pure styling changes** — nothing testable; say TDD doesn't fit and why.
- **Mixed or unclear tasks** — ask the user whether to proceed with the testable parts.

## Prerequisites

- `.claude/CLAUDE.md` and `.claude/docs/coding-guidelines.md` must exist — if either is missing, stop and recommend `/optimus:init`; the guidelines drive the Refactor step.
- Read the project's `testing.md` for framework, test file locations, naming, and mocking conventions. In a multi-repo workspace or monorepo, scope to the repo or subproject being targeted and load its docs — see `$CLAUDE_PLUGIN_ROOT/skills/init/references/multi-repo-detection.md` and the Monorepo Scoping Rule in `$CLAUDE_PLUGIN_ROOT/skills/init/references/constraint-doc-loading.md`.
- **Green baseline:** run the project's test command once. If tests fail, stop and report — a failing suite makes Red and Green indistinguishable. If no test runner exists, stop and recommend `/optimus:init` to set up test infrastructure.
- If a coverage command is configured, run it now and record the baseline percentage; the wrap-up reports the before/after delta. If none is configured, omit coverage from the report.

Every claim about a test run in this skill follows the gate function in `$CLAUDE_PLUGIN_ROOT/skills/init/references/verification-protocol.md`: run the command fresh, read the output, state the actual result with evidence — never "should pass".

## Resolve the task

In order, first match wins:

1. The user's input references a spec file (a `.md` under `docs/specs/`) — read it and use it.
2. `docs/specs/` exists with specs — take the newest whose `Status` is Approved and confirm with the user that it's the intended basis.
3. The user gave an inline task description — use it.
4. Otherwise, ask what feature or bug fix to implement.

If the resolved description runs long (a pasted spec or ticket), distill it to a single-sentence goal and confirm it before proceeding.

## Branch

Create a conventionally named feature branch from the current branch, and record the original branch name — it scopes the quality-gate diff and is the eventual PR target. All work happens on the new branch.

## Decompose into behaviors

Break the goal into small, individually testable behaviors:

- **Observable** — a clear expected output or side effect; phrase as "When [input/action], then [outcome]".
- **Independent** — testable and implementable without the other behaviors being done.
- **Small** — one test, one assertion focus.

**Scenario shortcut:** if the spec contains a `## Scenarios` section with `### Scenario:` headings in Given/When/Then form, use those scenarios as the behavior list in the order they appear — one cycle per scenario. They are the stakeholder-approved acceptance criteria; don't re-derive a parallel list. Split a scenario only if it bundles unrelated outcomes.

For bug fixes, the first behavior is always a test that reproduces the bug; prepend one if the list doesn't start with it.

Present the behavior list and confirm it with the user before cycling.

**Anti-pattern — horizontal slicing:** never write all the tests first and then all the implementations. Tests written in bulk specify imagined behavior — they check shapes (signatures, data structures) instead of outcomes, and they go insensitive to real changes. Work vertically: one test, one implementation, next test, so each cycle builds on what the previous one taught.

## The cycle

### Red — write a failing test

Write one minimal test for the current behavior, following `testing.md` conventions, with a name that reads as a behavior specification (e.g., "returns 401 when token is expired"). Before adding any mock, read `$CLAUDE_PLUGIN_ROOT/skills/tdd/references/testing-anti-patterns.md`.

Run the suite. The new test must fail on its assertion — because the behavior doesn't exist, not because of a syntax or import error — and every other test must stay green. If it fails for the wrong reason, fix the test, not the source. One exception: when the symbol under test doesn't exist yet, create a minimal stub (empty function, class, or module) so the failure lands on the assertion — the stub is scaffolding, not an Iron Law violation. If the test passes unexpectedly, the behavior may already exist: investigate, then ask the user whether to skip the behavior or strengthen the test.

### Green — minimum to pass

Write the minimum code that makes the failing test pass — no untested edge cases, no premature abstraction; a hardcoded return is legitimate if it passes, since later tests force generalization. Run the suite: all tests must pass. If other tests broke, fix the regression before moving on. If a lint or type-check command is configured, run it too — type errors can hide behind passing tests.

**Circuit breaker:** if the new test still fails after 3 implementation attempts, stop — that signals a design problem, not a coding problem. Ask the user whether to rethink the approach, split the behavior into smaller ones, or skip it (revert this cycle's implementation changes, including deleting files it newly created, mark the test skipped per the project's convention, and move on).

### Bug-fix regression gate

When the current behavior is a bug reproduction, prove the test and the fix are both genuine:

1. Commit the test on its own: `git add <test-file> && git commit -m "test: reproduce <bug>"`.
2. Stash only the fix: `git stash push -u -- <implementation-files>` (`-u` catches newly created files). Confirm via `git status`/`git diff` that the fix is really gone.
3. Run the test — it must **fail**. That proves the test catches the bug.
4. `git stash pop`, run again — it must **pass**. That proves the fix resolves it.

If the test passes with the fix stashed, it isn't catching the bug: pop the stash, then rewrite the test to target the actual failure condition.

### Refactor — clean up while green

Review the code this cycle produced (test and implementation) against `.claude/docs/coding-guidelines.md`. Scope: code touched this session plus the files it directly interacts with (imports, calls, inherits from) — eliminate duplication between them and align naming, but don't hunt the wider codebase for improvements and don't prepare for future behaviors. Check the test too: clear name, focused assertions, project conventions. Run the suite (and lint/type-check) after each change — everything must stay green; if a refactoring breaks a test, undo it.

## Commit and checkpoint

Commit the cycle's work with a conventional message covering the behavior — stage the specific files touched, and never stage anything that looks like a secret. Report the cycle's outcome with evidence (test name, suite result). Then, if behaviors remain, ask the user whether to continue to the next one or stop here.

## Quality gate

After the last cycle (or when the user stops), run the quality agents — they catch cross-cycle issues (duplication between behaviors, naming drift, coverage gaps) that are invisible inside a single cycle. Follow `$CLAUDE_PLUGIN_ROOT/skills/tdd/references/quality-gate.md`, using the agent prompts in `$CLAUDE_PLUGIN_ROOT/skills/tdd/agents/` (`code-simplifier.md`, `test-guardian.md`, `shared-constraints.md`) and the original branch name recorded at branch creation.

## Wrap up

If uncommitted work remains (the user stopped mid-cycle), run the suite first; mark a failing mid-cycle test skipped per project convention and note it in the summary, then commit.

Summarize in plain prose: behaviors implemented and deferred, the final test-suite result with evidence, and the coverage delta if a baseline was recorded. Push the branch with `git push -u origin <branch-name>`; if the push fails, report the error and stop so the user can resolve it.

If behaviors were deferred, a follow-up `/optimus:tdd` run started from this branch can pick them up — each run is a fresh decomposition; there is no resume. Suggest opening a PR (Claude Code drafts one on request) and then running `/optimus:code-review` on it in a fresh conversation.
