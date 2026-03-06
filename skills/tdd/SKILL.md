---
description: This skill guides test-driven development — decompose a feature or bug fix into behaviors, then cycle through Red (failing test) → Green (minimal implementation) → Refactor for each one. Requires /optimus:init and working test infrastructure.
disable-model-invocation: true
---

# Test-Driven Development

Guide the user through Red-Green-Refactor cycles to implement a feature or fix a bug test-first. Each cycle: write a failing test (Red), write the minimum code to pass it (Green), clean up while tests stay green (Refactor). One behavior per cycle.

This skill is for **new features** and **bug fixes** — not refactoring. For restructuring existing code without changing behavior, use `/optimus:simplify` instead (existing tests verify behavior is preserved).

### The Iron Law

**No production code without a failing test first.** If implementation code is written before its test, delete it entirely and begin the cycle fresh. Do not preserve it as reference, do not adapt it — write the implementation from scratch once the failing test exists. This is the non-negotiable foundation of every step that follows.

## Step 1: Pre-flight

If the current directory is a multi-repo workspace (no `.git/` at root, 2+ child directories containing a `.git` *directory* — not `.git` files, which indicate submodules), process each repo independently: run Steps 1–9 inside the repo the user is targeting. If ambiguous, ask which repo.

### Verify prerequisites

Check that `.claude/CLAUDE.md` exists. If it doesn't, stop and recommend running `/optimus:init` first — coding guidelines and project context are essential for the Refactor step.

Load these documents (they affect quality at every step):

| Document | Role | Effect on skill |
|----------|------|-----------------|
| `.claude/CLAUDE.md` | Project overview | Tech stack, test runner command |
| `coding-guidelines.md` | Code quality reference | Applied during Refactor step |
| `testing.md` | Testing conventions | Test file location, naming, framework, mocking patterns |

**Monorepo path note:** `coding-guidelines.md` is shared at root (`.claude/docs/coding-guidelines.md`). `testing.md` is scoped per subproject (`<subproject>/docs/testing.md`). For root-as-project, scoped docs are in `.claude/docs/` alongside the shared guidelines. When running TDD inside a subproject, load that subproject's `testing.md`, not another subproject's.

### Verify test infrastructure

Locate the test runner command from `testing.md`, `CLAUDE.md`, or project manifests (`package.json` scripts, `Makefile`, `Cargo.toml`, etc.). Run it once to confirm it works.

- **Tests pass** — proceed to Step 2 (Suitability Analysis)
- **Tests fail** — stop and report. Existing failures must be resolved before TDD can begin (a failing suite makes Red/Green indistinguishable)
- **No test runner found** — stop and recommend running `/optimus:unit-test` first to provision test infrastructure (framework, runner, coverage tooling, `testing.md`)

### Check quality agents (optional)

Check whether these project-level agent files exist:
- `.claude/agents/code-simplifier.md`
- `.claude/agents/test-guardian.md`

Record which are available — they will be used in the Quality Gate step after cycling completes. If neither exists, the quality gate will be skipped. This is not a blocker; recommend `/optimus:init` if missing and the user wants agent-backed quality checks.

## Step 2: Suitability Analysis

Before starting TDD cycles, analyze whether the user's task is a good fit for test-driven development.

### Gather the task

If the user provided a task description inline (e.g., `/optimus:tdd "Add auth endpoint"`), use it. Otherwise, use `AskUserQuestion` — header "TDD scope", question "What feature or bug fix do you want to implement with TDD?":
- **New feature** — "Implement a new capability (e.g., 'Add user authentication endpoint')"
- **Bug fix** — "Fix a bug by reproducing it with a test first (e.g., 'Login fails when email has uppercase')"

If the task description is longer than ~2-3 sentences (e.g., a pasted spec, Jira ticket, or acceptance criteria list), distill it into a **single-sentence goal** and confirm with `AskUserQuestion` — header "Distilled goal", question "I've distilled your spec to: '[single-sentence summary]'. Is this accurate?":
- **Looks good** — "Proceed with this goal"
- **Adjust** — "Let me refine the focus"

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

### Create feature branch

Always create a new branch from the current branch for TDD work. This keeps the user's original branch clean — all changes happen on the new branch.

1. Record the current branch name (this becomes the PR/MR target later): `git rev-parse --abbrev-ref HEAD`
2. Derive a branch name from the task description:
   - For features: `tdd/<feature-slug>` (e.g., `tdd/add-password-reset-endpoint`)
   - For bug fixes: `tdd/fix-<bug-slug>` (e.g., `tdd/fix-login-uppercase-email`)
   - Slug rules: lowercase, hyphens for spaces, strip special characters, max 50 chars
3. Create and switch to the branch: `git checkout -b <branch-name>`
4. Report the branch name to the user:

```
## Branch

Created branch `<branch-name>` from `<original-branch>`.
All TDD work will be committed to this branch.
```

### Decompose into behaviors

Break the user's description into small, individually testable behaviors. Each behavior should be:
- **Observable** — it has a clear expected output or side effect
- **Independent** — it can be tested and implemented without the other behaviors being done yet
- **Small** — one test, one assertion focus (a test may have supporting assertions, but tests one thing)

Decomposition strategies by task type:
- **API endpoints** — one behavior per response scenario (success case, each error code, each validation rule)
- **Business logic** — one behavior per business rule or edge case
- **Bug fixes** — first behavior is always "reproduce the bug" (a test that demonstrates the current broken behavior)
- **Data transformations** — one behavior per transformation step or boundary (empty input, boundary values, malformed data)

If the decomposition produces more than 10 behaviors, split into milestones. Present the first milestone (~5-8 behaviors that deliver a coherent slice of functionality) as the current scope, and list remaining behaviors as "Future milestones" with brief descriptions. After completing the last behavior of the current milestone, use `AskUserQuestion` — header "Milestone complete", question "Milestone [N] is done ([N] behaviors). Continue to the next milestone?":
- **Next milestone** — "Load the next milestone's behaviors for approval"
- **Stop here** — "Done for now — show summary"

If the user chooses to continue, present the next milestone's behaviors for approval (return to the "Behaviors" confirmation above), then resume Step 4. This prevents overwhelming behavior lists and gives natural stopping points.

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
- Avoids common testing anti-patterns — read `$CLAUDE_PLUGIN_ROOT/skills/tdd/references/testing-anti-patterns.md` before writing mocks; prefer real code over mocks, never assert on mock behavior, mock only external services or non-deterministic dependencies

Place the test file according to the project's convention (from `testing.md`). If adding to an existing test file, append; if the convention calls for a new file, create one.

### Run the test suite

**Verification protocol** — every test run in this skill (Steps 4, 5, 6) must be verified the same way: read the complete test output, check the exit code, and count pass/fail totals. Never claim "should pass" or "probably works" — state the actual result with evidence (e.g., "14 passed, 1 failed"). This protocol applies to every "Run the test suite" instruction below.

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

- **All pass** — proceed to lint/type-check below
- **New test still fails** — fix the implementation (not the test). The test defines the expected behavior; the code must meet it
  - **Circuit breaker** — if the test still fails after 3 implementation attempts, stop. Use `AskUserQuestion` — header "Implementation stuck", question "The test has failed after 3 fix attempts. This usually signals a design problem, not a code problem. How to proceed?":
    - **Rethink the approach** — "Step back and reconsider the behavior's design or decomposition"
    - **Simplify the behavior** — "Break this behavior into smaller, simpler sub-behaviors"
    - **Skip for now** — "Revert implementation changes from this cycle (`git checkout -- <implementation files>`), mark the test as skipped per the project's convention (e.g., `skip`/`xit`/`@pytest.mark.skip`), move to the next behavior"
  - **Bug-fix regression check** — when the current behavior is a bug reproduction (the first behavior in a bug-fix decomposition), verify the red-green cycle is genuine after the test passes: commit the test file first (`git add <test-file> && git commit -m "test: <behavior>"`), then revert only implementation files (`git stash push <implementation-files>`), run the test (it **must fail**), restore the fix (`git stash pop`), run again (it **must pass**). This proves the test catches the bug and the fix resolves it. If the test passes with the fix reverted, first restore the fix (`git stash pop`), then rewrite the test
- **Other tests broke** — the implementation introduced a regression. Fix it before proceeding — all tests must stay green

### Lint / type-check (if available)

If a lint or type-check command is configured in `CLAUDE.md` or the project manifest (e.g., `tsc --noEmit`, `cargo check`, `go vet`, `dotnet build`), run it. Type errors in implementation code can hide behind passing tests. If it fails, fix the implementation before proceeding to Step 6.

Report to the user:

```
## 🟢 Green — [Behavior description]

Test: [test file path]:[test name]
Status: PASSES ✓
Implementation: [file path]:[function/method]
All tests: passing ✓
Type-check: passing ✓ [or omit this line if no type-check command is available]
```

## Step 6: Refactor — Clean Up While Green

With all tests passing, review the code just written (both test and implementation) against `coding-guidelines.md`. Apply each principle as a lens — does the new code satisfy the guidelines? If not, refactor. Only extract abstractions if code written during this TDD session is already duplicated — don't search the entire codebase for extraction opportunities and don't extract speculatively.

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

## Step 7: Commit and Loop

After completing one Red-Green-Refactor cycle, automatically commit the work on the feature branch:

1. Stage changes: prefer `git add <specific files>` for the test and implementation files touched in this cycle. Use `git add -A` only if many files were changed (e.g., renames, moves). Never stage files that look like secrets (`.env`, credentials, keys) — warn the user if any appear in `git status`
2. Generate a conventional commit message following the format from `/optimus:commit-message` (type(scope): description) covering the behavior just completed
3. Commit: `git commit -m "<message>"`
4. Report the commit:

```
Committed: <short-hash> <commit message>
```

Then, if behaviors remain, use `AskUserQuestion` — header "Next step", question "Cycle complete for behavior #[N]. What next?":
- **Next behavior** — "Continue to behavior #[N+1]: [description]"
- **Stop here** — "Done for now — show summary"

If behaviors remain and the user chooses to continue, return to Step 4 (Red) for the next one.

If no behaviors remain, or the user chooses "Stop here", proceed to Step 8 (Quality Gate).

## Step 8: Quality Gate (parallel agents)

If no quality agents were found in Step 1, skip this step entirely and proceed to Step 9.

This step runs after all Red-Green-Refactor cycles are complete. It launches available project agents in parallel for a holistic review of all code written during the TDD session. Running agents here — not per-cycle — catches cross-cycle issues (duplication between behaviors, naming drift, accumulated pattern violations, edge-case coverage gaps) that are invisible within a single cycle.

### Gather changed files

Collect all files changed during the TDD session: `git diff --name-only <original-branch>...HEAD` (where `<original-branch>` is the branch recorded in Step 3). This is the scope for both agents.

### Launch parallel agents

Launch up to 2 `general-purpose` Agent tool calls simultaneously — one per available agent. Only launch agents whose definition files exist (checked in Step 1).

Read `$CLAUDE_PLUGIN_ROOT/skills/tdd/references/agent-prompts.md` for the full prompt templates for both agents.

### Present findings

After both agents complete, present a consolidated quality report:

```
## Quality Gate

### Code Simplifier
[Findings from code-simplifier, or "No issues found — code follows project guidelines."]

### Test Guardian
[Findings from test-guardian, or "All code has test coverage. No structural barriers detected."]
```

If no agents produced findings, report "Quality gate passed — no issues found" and proceed silently to Step 9.

### Act on findings

If either agent produced findings, apply fixes for each one. After all fixes are applied, run the test suite:

- **All tests pass** — stage and commit with a conventional message (e.g., `refactor(scope): address quality gate findings`). Proceed to Step 9.
- **Tests fail** — revert all fixes, then re-apply one at a time with a test run after each. Keep fixes that pass, revert those that fail. Present a fix summary listing which fixes were applied and which were reverted (with reason "fix broke tests"). Stage and commit kept fixes with a conventional message (e.g., `refactor(scope): address quality gate findings`). Proceed to Step 9.

## Step 9: Summary, Push, and PR/MR

After all behaviors are implemented (or the user stops early):

### Commit remaining work

If there are uncommitted changes (e.g., the user stopped mid-cycle before the auto-commit):
1. Stage the remaining files (prefer `git add <specific files>`; use `git add -A` only if many files changed) and commit: `git commit -m "<conventional message covering remaining work>"`

### Present summary

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
- Quality gate: code-simplifier ([N] findings), test-guardian ([N] findings) [or "skipped — agents not installed"]

### Coverage
[Detect coverage command from: testing.md coverage section, test runner built-in flag
(e.g., vitest --coverage, pytest --cov=., go test -cover, dotnet test --collect:"XPlat Code Coverage"),
or package.json coverage script. Run it before the first cycle and after the last cycle to measure delta.
If no coverage command is found, omit this section entirely.]
- Before: [X]%
- After: [Y]%
- Delta: +[Z]%
```

### Push and create PR/MR

If there are commits on the branch:

1. **Push** the feature branch: `git push -u origin <branch-name>`

2. **Detect the hosting platform** (reuse the pattern from `/optimus:code-review`):
   - Check the `origin` remote URL: contains `gitlab` → **GitLab**; contains `github` → **GitHub**
   - If neither matches, check for CI files: `.gitlab-ci.yml` → GitLab; `.github/` directory → GitHub
   - If platform is still unknown → skip PR/MR creation, report the push and suggest creating one manually

3. **Create a PR/MR** with a title and description:

   **GitHub** (requires `gh` CLI):
   - Verify `gh` is available: `gh --version`. If not, skip and tell the user to create the PR manually
   - `gh pr create --title "<conventional title>" --body "<description>" --base <original-branch>`

   **GitLab** (requires `glab` CLI):
   - Verify `glab` is available: `glab --version`. If not, skip and tell the user to create the MR manually
   - `glab mr create --fill --title "<conventional title>" --description "<description>" --target-branch <original-branch>`

   **PR/MR description** should include:
   - Task description (from Step 2)
   - List of behaviors implemented (from the summary table)
   - Test count and coverage delta (if available)

4. **Report** to the user:

```
### Git Activity
- Branch: `<branch-name>` (from `<original-branch>`)
- Commits: [N]
- Pushed: ✓
- PR/MR: [URL] (or "Create manually — `gh`/`glab` not available")
```

If behaviors remain unfinished, note them and suggest re-running `/optimus:tdd` to continue.

Remind the user that the PR/MR should be reviewed before merging, and suggest using `/optimus:code-review` to review it.
