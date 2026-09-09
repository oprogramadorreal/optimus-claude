---
description: Guides test-driven development — decomposes a feature or bug fix into testable behaviors, then runs Red-Green-Refactor cycles with a failing test before every implementation. Auto-detects specs from docs/specs/ or docs/jira/, creates a feature branch (optional worktree), commits per cycle, and pushes. Recommends /optimus:init (falls back to general best practices on your choice); requires a passing test suite.
disable-model-invocation: true
argument-hint: "[task description]"
---

# Test-Driven Development

Implement a feature or bug fix test-first: for each behavior, write a failing test (Red), write the minimum code to pass it (Green), then clean up while tests stay green (Refactor). This skill builds new behavior — for restructuring without behavior change, use `/optimus:refactor`.

**The Iron Law: no production code without a failing test first.** If this cycle's implementation is written before its test, undo only that implementation using the ownership record below and begin the cycle fresh. Preserve pre-existing code and user edits; write the cycle's implementation once the failing test exists.

Coming from plan mode? TDD runs in normal mode in a fresh conversation; plan-mode iterations that feed it are review-only — see `$CLAUDE_PLUGIN_ROOT/skills/brainstorm/references/plan-mode-handoff.md`.

## Step 1: Pre-flight

If `git rev-parse --is-inside-work-tree` does not return `true`, read `$CLAUDE_PLUGIN_ROOT/skills/init/references/multi-repo-detection.md` and apply it; if a multi-repo workspace is detected, work inside the repo the user is targeting — ask which one if ambiguous. When it returns `true`, resolve the repository root with `git rev-parse --show-toplevel`, including in a linked worktree or subdirectory.

### Preserve starting work

Record the current branch/HEAD and staged, unstaged, and untracked paths before setup or edits. These changes belong to the user unless the conversation explicitly includes them in this task. Existing authorization persists; ask only when ownership or scope is genuinely ambiguous. A new branch does not isolate dirty work, and a new worktree starts from committed state rather than carrying the user's dirty changes.

Before each cycle, record its owned paths. Before the first edit to each file in that cycle, preserve its exact bytes and existence in the private session scratchpad, outside staged project paths; verify the copy before editing, and keep it until the cycle is committed or safely rolled back. Record the last version written by the cycle too. If the file changes independently, reconcile that work before restoring anything. Do not use whole-file Git checkout, hard reset, broad stash/pop, or cleanup as a substitute for this boundary.

Rollback restores the pre-cycle copy only when the current file is still the cycle's last written version; otherwise remove only identifiable cycle changes. Remove a newly created file only when it did not exist at the boundary and contains no independent work. If separation is uncertain, preserve it and show the ambiguity. Never replace the user's starting index with a scratch index or stage unrelated work.

If `.claude/CLAUDE.md` or `.claude/docs/coding-guidelines.md` is missing, recommend `/optimus:init` first; on the user's choice, continue with general best practices. Load:

- `.claude/CLAUDE.md` — project overview, tech stack, test runner command
- `.claude/docs/coding-guidelines.md` — applied during Refactor
- `testing.md` — test conventions: framework, file location, naming, mocking patterns. In a monorepo, load the target subproject's own `docs/testing.md` / `docs/` files; shared guidelines come from root `.claude/docs/`
- `docs/product/tech-stack.md` and `docs/product/mvp-prd.md`, only if present — low-priority steering that informs decomposition and Refactor but never overrides the task source (precedence: `$CLAUDE_PLUGIN_ROOT/references/sdd-mapping.md`)

### Verify test infrastructure

Locate the test runner command (from `testing.md`, `CLAUDE.md`, or project manifests) and run it once:

- **Tests pass** — proceed
- **Tests fail** — stop and report; a failing baseline makes Red/Green indistinguishable
- **No runner found** — stop and recommend `/optimus:init` to set up test infrastructure (its Scaffold option covers projects with no code yet)

Then find a coverage command — first match wins: the coverage section of `testing.md`, a runner flag (`vitest --coverage`, `pytest --cov=.`, `go test -cover`, `dotnet test --collect:"XPlat Code Coverage"`), or a `package.json` coverage script. If found, run it once and record the `Before` percentage; Step 8 runs only the `After` measurement.

## Step 2: Task and Suitability

Resolve the task with the cascade in `$CLAUDE_PLUGIN_ROOT/skills/tdd/references/spec-context-detection.md`. If nothing resolves and no inline argument was given, use `AskUserQuestion` — header "TDD scope", question "What feature or bug fix do you want to implement with TDD?", options **New feature** / **Bug fix**. Whatever the source, apply the reference's **Distillation** step to the final description. Resolved context feeds this step — it does not bypass Step 3 decomposition (except the scenario-driven shortcut).

Classify the task:

- **Suitable** — new features with testable behavior, bug fixes reproducible with a test, capabilities added to existing modules, large multi-component features (they just need careful decomposition). Proceed silently.
- **Not suitable** — stop and report the task, the reason, and the recommended alternative: refactoring → `/optimus:refactor`; documentation-only, pure styling, configuration changes, code deletion, or generated code → no testable behavior to build.
- **Ambiguous** — use `AskUserQuestion` — header "TDD fit", stating the specific concern, options **Proceed with TDD** / **Use [alternative]**.

## Step 3: Branch, Worktree, Decompose

### Feature branch

All work happens on a new branch; the user's original branch is never modified.

1. Record the current branch (`git rev-parse --abbrev-ref HEAD`) — it becomes the PR/MR target.
2. Name the branch per `$CLAUDE_PLUGIN_ROOT/skills/commit/references/branch-naming.md` — type `feat` or `fix` from Step 2's classification.
3. Create and switch: `git checkout -b <branch-name>`. Report the new branch and its origin branch.

### Worktree isolation (optional)

Run `git worktree list`; if the current directory is inside a linked worktree, skip this offer — the environment is already isolated. Otherwise use `AskUserQuestion` — header "Workspace", question "Use a git worktree for isolated development? Your main workspace stays on the original branch.", options **Use worktree (Recommended)** / **Stay on branch**. On yes, follow the **Setup** section of `$CLAUDE_PLUGIN_ROOT/skills/worktree/references/worktree-setup.md` with `<branch-name>` and `<original-branch>`; if creation fails, fall back to the branch workflow and say so. All subsequent commands run inside the worktree.

### Decompose into behaviors

Each behavior must be **observable** (phrase as "When [input/action], then [outcome]"), **independent** (testable without the others being done), and **small** (one test, one assertion focus).

**Scenario-driven shortcut:** if the build spec contains a `## Scenarios` section with `### Scenario:` headings in Given/When/Then form, use those scenarios directly as the behavior list, in order — one cycle per scenario. They are stakeholder-approved acceptance criteria; do not re-derive a parallel list. Split a scenario only when a compound Then implies multiple sub-behaviors. For scenario-driven bug fixes, verify Scenario 1 reproduces the bug; prepend one if missing.

Otherwise decompose by task type: API endpoints — one behavior per response scenario; business logic — one per rule or edge case; bug fixes — the first behavior is always "reproduce the bug"; data transformations — one per step or boundary.

If more than 10 behaviors result, split into milestones of ~5-8 that each deliver a coherent slice; present the first as the current scope and list the rest as future milestones (the boundary prompt is in Step 7).

Present the numbered behavior list, then use `AskUserQuestion` — header "Behaviors", question "Does this decomposition look right?", options **Start cycling** / **Adjust**.

**Anti-pattern — horizontal slicing.** Never write all tests first, then all implementations: bulk-written tests check imagined shape, not behavior, and go insensitive to real changes. Work vertically — each cycle responds to what the previous one taught.

```
WRONG (horizontal):  RED: test1..test5   then   GREEN: impl1..impl5
RIGHT (vertical):    test1→impl1, test2→impl2, test3→impl3, ...
```

## Step 4: Red — Write a Failing Test

Write one minimal test for the current behavior: follow `testing.md` conventions, test exactly one behavior, and name it as a behavior specification (e.g., `"returns 401 when token is expired"`). Before writing mocks, read `$CLAUDE_PLUGIN_ROOT/skills/tdd/references/testing-anti-patterns.md` — prefer real code over mocks, never assert on mock behavior.

**Test-result honesty (every test run in Steps 4-8):** run the command fresh, read the complete output, and state the actual result (e.g., "14 passed, 1 failed") — never "should pass". Red and Green both turn on a real observed result, so a guessed one silently breaks the discipline.

Run the test suite. The new test **must fail on its assertion** for the right reason, and all other tests must still pass.

- **Fails for the wrong reason** (import error, syntax error, infrastructure) — fix the test, not the source.
- **Exception — the symbol under test doesn't exist yet:** for the first behavior of a new module, class, or function, create a minimal stub (empty function, class, or module) so the run fails on the assertion instead. The stub is scaffolding, not an Iron Law violation — the failing test already exists.
- **Passes unexpectedly** — the behavior may already exist. Use `AskUserQuestion` — header "Test passed", options **Skip this behavior** / **Strengthen the test** / **Investigate**.

## Step 5: Green — Minimal Implementation

For a bug reproduction, preserve the implementation state at the observed Red assertion failure, including any required stub, before making the fix. Step 5's regression gate restores this state temporarily using Step 1's ownership checks.

Write the **minimum code** to make the failing test pass: no untested edge cases, no premature abstraction, no "while I'm here" improvements. A hardcoded return that passes is valid — later tests force generalization.

Run the test suite — all tests must pass.

- **New test still fails** — fix the implementation, not the test. **Circuit breaker:** after 3 failed attempts, stop and use `AskUserQuestion` — header "Implementation stuck", question "The test has failed after 3 fix attempts — this usually signals a design problem, not a code problem.":
  - **Rethink the approach** — reconsider the behavior's design or decomposition
  - **Simplify the behavior** — break it into smaller sub-behaviors
  - **Skip for now** — restore only this cycle's implementation using the pre-cycle copies and ownership checks from Step 1, mark the test skipped per the project's convention, and move to the next behavior. Preserve the test and all earlier user/cycle work.
- **Other tests broke** — fix the regression before proceeding.

### Bug-fix regression gate

Only when the current behavior is a bug reproduction (skip for feature behaviors). This proves the test catches the bug and the fix resolves it:

1. Preserve the green implementation bytes in the scratchpad. Commit the test separately only when it can follow Step 7's ownership rules; the regression proof does not require a commit.
2. Restore the saved Red implementation state using Step 1's ownership checks, leaving the regression test in place. Confirm that only this cycle's fix was removed, not earlier user work.
3. Run the test — it **must fail**.
4. Restore the saved green implementation, applying the same independent-change check.
5. Run the test — it **must pass**.

If the test passes at step 3 with the fix reverted, it isn't catching the bug: restore the saved green implementation, then rewrite the test to target the actual failure condition.

### Lint / type-check

If a lint or type-check command is configured (`CLAUDE.md` or project manifest), run it — type errors can hide behind passing tests. Fix failures before proceeding.

## Step 6: Refactor — Clean Up While Green

Review this cycle's test and implementation against `coding-guidelines.md`. Scope: code written in this session plus the files it directly imports, calls, or inherits from — extract duplication with those files, align naming, adjust an existing method to cleanly serve old and new usage. Do not restructure beyond that scope, add features, or handle untested edge cases. Also check the test: behavior-spec name, focused assertions, `testing.md` conventions.

Run the test suite when the cycle's cleanup is done; if it goes red, undo the change that broke it. Re-run the Step 5 lint / type-check as well — it last ran *before* this cleanup edited the code, and Step 7 commits without checking again.

## Step 7: Commit and Loop

Auto-commit each completed cycle:

1. Identify files whose entire change is owned by this task; compare against the starting-work record and inspect the actual diff. Stage only these exact paths (`git add -- <owned-files>`), never `git add -A`. Never stage files that look like secrets (`.env`, credentials, keys) — warn the user if any appear in `git status`.
2. Commit only those paths with `git commit --only -m "<message>" -- <owned-files>`, using the conventional format in `$CLAUDE_PLUGIN_ROOT/skills/commit/references/conventional-commit-format.md`. This excludes unrelated entries already staged by the user. Check the resulting commit and that unrelated staged/unstaged work is preserved.
3. If a file mixes task changes with pre-existing user changes not already included in the task's authorization, do not stage or commit the whole file. Preserve both, show the concrete mixed diff, and resolve ownership with the user before including it. Keep the cycle's snapshots while its commit is deferred; continue independent work when possible. Do not claim an uncommitted cycle was delivered on the branch.

Then keep cycling — return to Step 4 for the next behavior without asking. Two things interrupt the loop:

- **Milestone boundary** — the completed behavior ends the current milestone and more remain: `AskUserQuestion` — header "Milestone complete", options **Next milestone** (present its behaviors for approval as in Step 3, then return to Step 4) / **Stop here**.
- **The decomposition turns out to be wrong** — a behavior that was really several, or one the implementation showed was misframed. Say what changed and confirm the revised list before continuing. (Step 5's circuit breaker covers the narrower case of a test that will not pass.)

Report at those boundaries rather than per cycle: which behaviors landed, their test names, and the commit hashes. If no behaviors remain, or the user stops, proceed to Step 8.

## Step 8: Summary, Push, and PR/MR

### Commit remaining work

If uncommitted **task-owned** changes remain (e.g., stopped mid-cycle), run the test suite first: mark a failing mid-cycle test skipped and note it in the summary — or surface the failure to the user before committing if skipping isn't appropriate. Apply Step 7's exact-path ownership rules. Leave unrelated starting work untouched and report any deferred mixed-file commit; do not push or describe that unfinished work as committed.

### Present summary

```
## TDD Summary

### Behaviors Implemented
| # | Behavior | Test | Status |
|---|----------|------|--------|
| 1 | [description] | [test file]:[test name] | ✓ Complete |
| 2 | [description] | — | Not started |

### Stats
- Cycles completed: [N] of [total]
- Tests passing: [actual last-run result — e.g., "14 passed, 1 skipped"]
- Files created / modified: [lists]

### Coverage
[Run the After measurement with the Step 1 coverage command. Include this section only when both
Before and After produced a real percentage — never a half-filled block. Omit it entirely when no
coverage command was found or either run produced no parseable number.]
- Before: [X]%
- After: [Y]%
- Delta: +[Z]%
```

### Push

If a mixed-file commit is still deferred, leave the branch local and report what decision is needed before delivery. Continue with a partial push only if the user explicitly chose that scope.

Push the branch: `git push -u origin <branch-name>`. If the push fails, report the error and stop — skip the rest of Step 8 and leave any worktree in place; the user must push manually, then run `/optimus:pr` (a new `/optimus:tdd` invocation starts fresh — it does not resume this one). On success, report the branch, its origin branch, and the commit count.

If behaviors remain unfinished, note them and suggest a follow-up `/optimus:tdd` run with them as the task, started from this feature branch — each run is a fresh decomposition; there is no resume.

### Next step

Recommend `/optimus:code-review` first: cross-cycle issues — duplication between behaviors, naming drift, coverage gaps that only surface once the whole feature shape exists — are invisible from inside a single cycle, and it reviews the branch diff with the full agent fan-out. Then `/optimus:pr` to create the PR/MR, which reads the `## TDD Summary` block above for implementation context. Run both in this same conversation; TDD never runs `gh`/`glab` itself.

### Worktree cleanup

Run this last — after the `/optimus:pr` recommendation, never before it. Removing the worktree deletes the directory this conversation is working in, so `/optimus:pr` must be able to run first.

If a worktree was used, **offer** cleanup rather than performing it: the user may want to keep the worktree for `/optimus:pr` or follow-up work. If they accept, follow the **Cleanup** section of `$CLAUDE_PLUGIN_ROOT/skills/worktree/references/worktree-setup.md`; if they decline, follow that section's keep-the-worktree note.
