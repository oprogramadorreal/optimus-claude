---
description: This skill improves unit test coverage on demand — discovers testing gaps, provisions test infrastructure, and generates tests that follow project conventions. Conservative: only adds new test files, never refactors existing source code.
disable-model-invocation: true
---

# Unit Test Coverage Improvement

Improve unit test coverage for existing code. Conservative by design — only adds new test files, never refactors or restructures existing source code. If code is untestable as-is, it flags it rather than changing it. Refactoring is the domain of `/optimus:simplify`.

## Step 1: Pre-flight

If the current directory is a multi-repo workspace (no `.git/` here, 2+ child directories with `.git/` — same multi-repo workspace detection as `/optimus:init`), process each repo independently: run Steps 1–8 inside each repo that has `.claude/CLAUDE.md`. Report results per repo. If no repos have been initialized, suggest running `/optimus:init` first from the workspace root.

Check that `.claude/CLAUDE.md` exists. If it doesn't, stop and recommend running `/optimus:init` first — the project needs baseline context before test generation can be effective.

Beyond the init check, identify which guideline documents are available — they directly affect the quality of everything this skill does:

| Document | Role | Effect on skill |
|----------|------|-----------------|
| `.claude/docs/coding-guidelines.md` | Primary quality reference | Tests follow naming conventions, code structure, quality standards |
| `.claude/docs/testing.md` | Testing conventions | Framework, runner commands, mocking patterns, file organization |
| `.claude/CLAUDE.md` | Project overview | Tech stack signals, test runner commands |

The skill operates differently depending on what exists:
- **All three docs** — matches existing conventions precisely
- **CLAUDE.md + coding-guidelines (no testing.md)** — derives conventions from the codebase, creates testing.md in Step 4
- **CLAUDE.md only (no guidelines either)** — still works, but with less project-specific guidance

### Scope

Parse optional path argument (e.g., `/optimus:unit-test src/api`) to limit scope. If no path is specified, default to the full project.

For monorepos and multi-repo workspaces, detect project structure using the same approach as `/optimus:init` — reference `$CLAUDE_PLUGIN_ROOT/skills/init/SKILL.md` Step 1 for detection logic (multi-repo workspace detection, workspace configs, manifest scanning, supporting signals). Process each project/repo independently.

## Step 2: Discovery

For each subproject (or the single project), scan for:

- **Existing test files** — `*.test.*`, `*.spec.*`, `*_test.*`, `__tests__/`, `tests/`, `test/`, `spec/`
- **Test framework** — configuration files and manifest dependencies (jest, vitest, mocha, pytest, junit, xunit, rspec, gtest, etc.)
- **Test runner commands** — from `testing.md`, `CLAUDE.md`, `package.json` scripts, `Makefile`, `Cargo.toml`, etc.
- **Coverage tooling** — whether coverage measurement is already configured and available
- **Optimus infrastructure status** — does `.claude/agents/test-guardian.md` exist? does `.claude/docs/testing.md` exist? does `.claude/CLAUDE.md` reference testing?

Present a summary table to the user:

```
## Discovery Summary

| Property | Status |
|----------|--------|
| Test framework | [framework name] / Not detected |
| Test files found | [N] files |
| Test runner command | [command] / Not found |
| Coverage tooling | [tool name] / Not configured |
| test-guardian agent | Installed / Missing |
| testing.md | Present / Missing |
| CLAUDE.md test refs | Present / Missing |
```

## Step 3: Framework and Coverage Tooling Installation (conditional)

### Subprojects without a test framework

Analyze the tech stack and recommend the most popular framework with appropriate coverage tooling. Consult `$CLAUDE_PLUGIN_ROOT/skills/unit-test/references/framework-recommendations.md` for stack-specific recommendations. These are starting points — analyze the actual project to decide. Ask for **explicit user approval** before installing anything.

If installation fails (network issues, version conflicts, incompatible environments), report the error to the user and stop — do not proceed to test generation without a working framework.

### Subprojects with framework but without coverage tooling

Detect this gap separately and recommend installing coverage tooling. Coverage measurement is essential for the skill to report meaningful results and set achievable targets. Ask for explicit user approval.

## Step 4: Optimus Infrastructure Provisioning

This phase runs **regardless** of whether Step 3 installed anything — test infrastructure may have been added manually after `/optimus:init` ran. When init ran on a project without test infrastructure, it correctly skipped test-guardian, testing.md, and CLAUDE.md testing references. Now that test infrastructure exists (pre-existing or just installed), this skill provisions what init would have created.

### 4a: Test-guardian agent

If `.claude/agents/test-guardian.md` doesn't exist, copy from `$CLAUDE_PLUGIN_ROOT/skills/init/templates/agents/test-guardian.md`. This is the same verbatim copy that init does — do not modify the template.

### 4b: Testing documentation

If `.claude/docs/testing.md` doesn't exist, create it using `$CLAUDE_PLUGIN_ROOT/skills/init/templates/docs/testing.md` as the skeleton. Fill in all placeholders with actual project details discovered in Steps 2-3 (framework name, test commands, directory structure, conventions from existing test files). Don't leave any `[placeholder]` text.

If `.claude/docs/testing.md` already exists, review it for accuracy. Propose updates if outdated — especially if a new framework was just installed in Step 3. Ask user approval before modifying.

### 4c: CLAUDE.md testing references

If `.claude/CLAUDE.md` doesn't reference testing, add test commands and a testing.md reference. Keep within init's compact ~60-line style — add to existing sections rather than creating new ones.

### 4d: Monorepo subprojects

For monorepos, update subproject-level `CLAUDE.md` files too. Each subproject should reference its own `docs/testing.md` and test commands.

## Step 5: Coverage Analysis and Achievable Threshold Estimation

Before writing any tests:

1. **Run existing test suite.** If tests fail, stop and report — a clean baseline is required before adding new tests.

2. **Measure baseline coverage:**
   - If coverage tooling is available → run coverage and record baseline numbers
   - If coverage tooling is NOT configured → do heuristic gap analysis (source files vs test files by naming convention)

3. **Estimate achievable coverage** without requiring risky refactoring:
   - **Testable code** — pure functions, exported APIs, business logic with clear inputs/outputs, utility modules, data transformations
   - **Untestable without refactoring** — hardcoded dependencies, tightly coupled modules, inline DB/HTTP calls without injection, deeply nested side effects, global state mutations

4. **Present to the user:**

```
## Coverage Analysis

- Current coverage: [X]%
- Estimated achievable without refactoring: ~[Y]%
- Gap requiring structural changes: ~[Z]%

The remaining ~[Z]% would require structural changes (dependency injection,
repository pattern extraction, etc.) — that's the domain of /optimus:simplify.
```

This sets clear expectations and reinforces the conservative constraint.

## Step 6: Test Generation Plan

Create a prioritized list, **capped at 10 items per run**:

1. **Exported/public functions and classes** — API surface, highest value
2. **Pure functions and utility modules** — easiest to test, highest ROI
3. **Business logic with clear inputs/outputs** — core functionality
4. **Complex branching logic** — high cyclomatic complexity, most likely to have bugs
5. **Internal/private helpers** — lower priority, test through public API when possible

**Skip** (flag in summary, don't attempt):
- Code that's untestable without refactoring
- Generated code (protobuf, OpenAPI, ORM migrations)
- Migration files
- Declarative configuration
- Thin wrappers with no logic

Present the plan, then use `AskUserQuestion` — header "Plan", question "How would you like to proceed with the test generation plan?":
- **Approve all** — "Generate tests for all planned items"
- **Selective** — "Choose specific items by number"
- **Skip** — "No tests — keep the plan as reference"

If the user selects **Selective**, ask which item numbers to proceed with (e.g., "1, 3, 5").

## Step 7: Test Writing

### Quality standards

Tests must follow:
- `coding-guidelines.md` for quality standards (naming, structure, clarity)
- `testing.md` for testing conventions (framework idioms, file naming, directory structure)
- Existing test files for patterns (imports, assertion style, describe/it structure, fixture handling)

### Conservative constraint

**Only add new test files.** Never refactor or modify existing source code — refactoring is the domain of `/optimus:simplify`. If a function can't be tested without changing its signature or extracting dependencies, flag it in the summary instead of changing it.

### Per-test workflow

For each approved item:
1. Write the test file
2. Run it immediately
3. If the test fails:
   - Fix the **test** (not the source code) — max 3 fix attempts
   - If still failing after 3 attempts, flag as untestable and move on
   - If the failure reveals an actual **bug in existing code**, report the bug but do not fix it
4. Move to the next item

### Final verification

After all tests are written, run the **full test suite** to ensure no regressions.

## Step 8: Summary

Report to the user:

```
## Unit Test Summary

### Infrastructure Provisioned
- [List of: test-guardian agent, testing.md, CLAUDE.md updates — or "None needed"]

### Coverage
- Coverage tooling: [tool name / not configured]
- Before: [X]% → After: [Y]%
- Achievable target (without refactoring): ~[Z]%

### Tests Created
| # | File | Target | Status |
|---|------|--------|--------|
| 1 | src/__tests__/auth.test.ts | auth module exports | ✓ Pass |
| 2 | src/__tests__/validate.test.ts | validation utilities | ✓ Pass |
| ... | ... | ... | ... |

### Bugs Discovered
- [List of bugs found in existing code — reported, not fixed]

### Not Testable Without Refactoring
- [List of code flagged as untestable — with brief explanation of what structural change would be needed]
- To address these, run `/optimus:simplify` to review and restructure the code first.
```

For multi-repo workspaces, present results per repo (one summary block per repo) and include the repo name/path in each section header.
