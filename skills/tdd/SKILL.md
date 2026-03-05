---
description: This skill guides test-driven development — decompose a feature or bug fix into behaviors, then cycle through Red (failing test) → Green (minimal implementation) → Refactor for each one. Requires /optimus:init and working test infrastructure.
disable-model-invocation: true
---

# Test-Driven Development

Guide the user through Red-Green-Refactor cycles to implement a feature or fix a bug test-first. Each cycle: write a failing test (Red), write the minimum code to pass it (Green), clean up while tests stay green (Refactor). One behavior per cycle.

This skill is for **new features** and **bug fixes** — not refactoring. For restructuring existing code without changing behavior, use `/optimus:simplify` instead (existing tests verify behavior is preserved).

## Step 1: Pre-flight

If the current directory is a multi-repo workspace (no `.git/` at root, 2+ child directories containing a `.git` *directory* — not `.git` files, which indicate submodules), process each repo independently: run Steps 1–8 inside the repo the user is targeting. If ambiguous, ask which repo.

### Verify prerequisites

Check that `.claude/CLAUDE.md` exists. If it doesn't, stop and recommend running `/optimus:init` first — coding guidelines and project context are essential for the Refactor step.

Load these documents (they affect quality at every step):

| Document | Role | Effect on skill |
|----------|------|-----------------|
| `.claude/CLAUDE.md` | Project overview | Tech stack, test runner command |
| `.claude/docs/coding-guidelines.md` | Code quality reference | Applied during Refactor step |
| `.claude/docs/testing.md` | Testing conventions | Test file location, naming, framework, mocking patterns |

### Verify test infrastructure

Locate the test runner command from `testing.md`, `CLAUDE.md`, or project manifests (`package.json` scripts, `Makefile`, `Cargo.toml`, etc.). Run it once to confirm it works.

- **Tests pass** — proceed to Step 2 (Suitability Analysis)
- **Tests fail** — stop and report. Existing failures must be resolved before TDD can begin (a failing suite makes Red/Green indistinguishable)
- **No test runner found** — stop and recommend running `/optimus:unit-test` first to provision test infrastructure (framework, runner, coverage tooling, `testing.md`)

## Step 2: Suitability Analysis

Before starting TDD cycles, analyze whether the user's task is a good fit for test-driven development.

### Gather the task

If the user provided a task description inline (e.g., `/optimus:tdd "Add auth endpoint"`), use it. Otherwise, use `AskUserQuestion` — header "TDD scope", question "What feature or bug fix do you want to implement with TDD?":
- **New feature** — "Implement a new capability (e.g., 'Add user authentication endpoint')"
- **Bug fix** — "Fix a bug by reproducing it with a test first (e.g., 'Login fails when email has uppercase')"

### Analyze suitability

Examine the task description against the codebase and classify it:

**Suitable for TDD** — proceed silently to Step 3:
- New features with testable behavior (API endpoints, business logic, data transformations, utilities)
- Bug fixes where the bug can be reproduced with a test
- Adding capabilities to existing modules
- Large features (frontend + backend, multi-component) — these are suitable but need careful decomposition in Step 3

**Not suitable for TDD** — stop and redirect:
- **Refactoring** (restructuring code without changing behavior) → recommend `/optimus:simplify`
- **Documentation-only changes** (README, comments, CLAUDE.md) → no testable code
- **Pure styling/cosmetic changes** (CSS colors, spacing, fonts with no logic) → no testable logic
- **Configuration changes** (environment variables, CI/CD, linter config) → no testable behavior
- **Deleting code/features** without replacement → tests should be removed, not added
- **Generated code** (protobuf, OpenAPI, ORM migrations) → generated output, not hand-written behavior

If **not suitable**, report to the user:

```
## Task Analysis

**Task:** [user's description]
**Suitability for TDD:** Not recommended

**Reason:** [specific explanation — e.g., "This is a refactoring task — it changes code structure
without adding new behavior. TDD is for building new behavior test-first."]

**Recommended approach:** [specific skill or approach — e.g., "/optimus:simplify restructures code
while using existing tests as a safety net."]
```

If **ambiguous** (the task has both testable and non-testable aspects, or it's unclear whether behavior changes), use `AskUserQuestion` — header "TDD fit", question "[specific concern about the task]. Proceed with TDD or use a different approach?":
- **Proceed with TDD** — "Focus on the testable parts and continue"
- **Use [recommended alternative]** — "[brief explanation of why the alternative fits better]"

## Step 3: Scope and Decompose

### Decompose into behaviors

Break the user's description into small, individually testable behaviors. Each behavior should be:
- **Observable** — it has a clear expected output or side effect
- **Independent** — it can be tested and implemented without the other behaviors being done yet
- **Small** — one test, one assertion focus (a test may have supporting assertions, but tests one thing)

Present the decomposition as a numbered list:

```
## Behaviors to Implement

1. [Behavior description] — [what the test will verify]
2. [Behavior description] — [what the test will verify]
3. [Behavior description] — [what the test will verify]
...
```

Use `AskUserQuestion` — header "Behaviors", question "Does this decomposition look right? Adjust, reorder, or approve to start cycling.":
- **Start cycling** — "Looks good — begin Red-Green-Refactor with behavior #1"
- **Adjust** — "I want to modify the list before starting"

For **bug fixes**: the first behavior is always "reproduce the bug" — a test that demonstrates the current broken behavior.

## Step 4: Red — Write a Failing Test

For the current behavior, write a minimal test that:
- Follows the project's testing conventions from `testing.md` (framework, file location, naming, mocking patterns)
- Tests exactly one behavior — clear expected input and output
- Uses descriptive test names that read as behavior specifications (e.g., `"returns 401 when token is expired"`, not `"test auth"`)

Place the test file according to the project's convention (from `testing.md`). If adding to an existing test file, append; if the convention calls for a new file, create one.

### Run the test suite

Run the project's test command. The new test **must fail**. Verify:

- **Test fails for the right reason** — the assertion fails because the behavior isn't implemented yet (not because of a syntax error, import error, or infrastructure problem)
- **All other tests still pass** — the new test didn't break existing tests

If the test **passes unexpectedly**, the behavior may already be implemented. Use `AskUserQuestion` — header "Test passed", question "The test passed without new code. The behavior may already exist. How to proceed?":
- **Skip this behavior** — "Move to the next behavior in the list"
- **Strengthen the test** — "Add edge cases or stricter assertions to find the real gap"
- **Investigate** — "Check if the behavior is truly complete or accidentally passing"

If the test **fails for the wrong reason** (import error, missing dependency, syntax error), fix the test — not the source code. The test itself must be valid; only the assertion should fail.

Report to the user:

```
## 🔴 Red — [Behavior description]

Test: [test file path]:[test name]
Status: FAILS ✓ (expected)
Reason: [why it fails — e.g., "function returns undefined, expected 'authenticated'"]
Other tests: all passing ✓
```

## Step 5: Green — Minimal Implementation

Write the **minimum code** to make the failing test pass. Resist the urge to implement more than what the test demands:
- No handling of edge cases that aren't tested yet (those are future behaviors)
- No premature abstractions or "while I'm here" improvements
- If a hardcoded return value passes the test, that's valid — later tests will force generalization

### Run the test suite

Run the project's test command. **All tests must pass** — including the new one.

- **All pass** — proceed to Step 6
- **New test still fails** — fix the implementation (not the test). The test defines the expected behavior; the code must meet it
- **Other tests broke** — the implementation introduced a regression. Fix it before proceeding — all tests must stay green

Report to the user:

```
## 🟢 Green — [Behavior description]

Test: [test file path]:[test name]
Status: PASSES ✓
Implementation: [file path]:[function/method]
All tests: passing ✓
```

## Step 6: Refactor — Clean Up While Green

With all tests passing, review the code just written (both test and implementation) against `.claude/docs/coding-guidelines.md`. Apply each principle as a lens:

- **Follow Existing Patterns** — does the new code match the codebase's style?
- **KISS** — is there anything simpler that still passes the test?
- **SRP** — is the function doing one thing?
- **Domain-Accurate Naming** — do names reflect the domain?
- **Pragmatic Abstractions** — is there duplication worth extracting? (Only if it's already duplicated — don't extract speculatively)

Also review the test:
- Is the test name a clear behavior specification?
- Are assertions focused and readable?
- Does it follow `testing.md` conventions?

Make improvements only if they genuinely simplify or clarify. **Do not add features, handle untested edge cases, or "prepare for" the next behavior.**

### Run the test suite

Run the project's test command after every refactoring change. **All tests must remain green.** If any test fails, undo the last refactoring change — the refactoring was incorrect.

Report to the user:

```
## 🔄 Refactor — [Behavior description]

Changes: [brief description of what was cleaned up, or "No changes needed — code is clean"]
All tests: passing ✓
```

## Step 7: Loop

After completing one Red-Green-Refactor cycle, use `AskUserQuestion` — header "Next step", question "Cycle complete for behavior #[N]. What next?":
- **Next behavior** — "Continue to behavior #[N+1]: [description]"
- **Commit progress** — "Commit the current work, then continue"
- **Stop here** — "Done for now — show summary"

If the user chooses **Commit progress**: suggest a conventional commit message following the format from `/optimus:commit-message` (type(scope): description). Present it in a copyable code block. Do NOT run `git commit` — let the user decide when to commit. Then continue to the next behavior.

If behaviors remain, return to Step 4 (Red) for the next one.

## Step 8: Summary

After all behaviors are implemented (or the user stops early), present:

```
## TDD Summary

### Behaviors Implemented
| # | Behavior | Test | Status |
|---|----------|------|--------|
| 1 | [description] | [test file]:[test name] | ✓ Complete |
| 2 | [description] | [test file]:[test name] | ✓ Complete |
| 3 | [description] | — | ⏸ Not started |

### Stats
- Cycles completed: [N] of [total]
- Tests written: [N]
- Tests passing: all ✓
- Files created: [list new files]
- Files modified: [list modified files]

### Coverage
[If coverage tooling is configured in testing.md, run coverage measurement and report delta]
- Before: [X]%
- After: [Y]%
- Delta: +[Z]%

### Suggested Commit
[If the user hasn't committed yet, suggest a conventional commit message covering all completed behaviors]
```

If behaviors remain unfinished, note them and suggest re-running `/optimus:tdd` to continue.
