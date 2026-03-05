# optimus:tdd

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that guides test-driven development — decompose a feature or bug fix into behaviors, then cycle through Red (failing test) → Green (minimal implementation) → Refactor for each one.

TDD is [more important with AI, not less](https://code.claude.com/docs/en/best-practices). Tests give the AI agent a feedback loop to self-correct: write test → see failure → implement → verify. Without tests, every change is a gamble. `/optimus:unit-test` adds tests to existing code retroactively. `/optimus:tdd` is the complement: build new code test-first.

## Features

- **Suitability analysis** — analyzes the task against the codebase before starting; redirects unsuitable tasks (refactoring, docs, styling) to the right skill
- **Behavior decomposition** — breaks features or bug fixes into small, independently testable behaviors before writing any code
- **Red-Green-Refactor cycles** — enforces the classic TDD discipline: failing test → minimal pass → clean up
- **Guideline-aware refactoring** — applies your project's `coding-guidelines.md` during the Refactor step
- **Convention-aware tests** — follows your `testing.md` for framework, file location, naming, and mocking patterns
- **Test verification at every step** — runs the full test suite after Red, Green, and Refactor to catch regressions instantly
- **Commit points** — suggests conventional commit messages after each cycle for small, focused commits
- **Coverage tracking** — reports coverage delta when coverage tooling is configured
- **Multi-repo workspace support** — targets specific repos in multi-repo setups
- **Submodule exclusion** — skips git submodule directories

## Quick Start

This skill is part of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin. See the [main README](../../README.md) for installation instructions.

## Prerequisites

1. **`/optimus:init`** — required. Installs `CLAUDE.md` and `coding-guidelines.md` used during Refactor
2. **`/optimus:unit-test`** — recommended. Provisions test framework, coverage tooling, and `testing.md` if missing

**Workflow**: `/optimus:init` → `/optimus:unit-test` → `/optimus:tdd`

## Usage

In Claude Code, use any of these:

- `/optimus:tdd` — start a TDD session (will ask what to implement)
- `/optimus:tdd` "Add user authentication endpoint"
- `/optimus:tdd` "Fix: login fails when email has uppercase letters"
- "implement with TDD"
- "let's do this test-first"

### New Feature Example

```
> /optimus:tdd "Add password reset endpoint"

## Behaviors to Implement

1. Returns 404 when email is not registered
2. Sends reset email with valid token when email exists
3. Returns 400 when email format is invalid
4. Rate-limits to 3 requests per hour per email

Start cycling? [Start cycling / Adjust]
```

Then for each behavior:

```
## 🔴 Red — Returns 404 when email is not registered

Test: src/__tests__/auth/reset-password.test.ts:"returns 404 when email is not registered"
Status: FAILS ✓ (expected)
Reason: POST /auth/reset-password returns 500 (route not implemented)
Other tests: all passing ✓

## 🟢 Green — Returns 404 when email is not registered

Test: PASSES ✓
Implementation: src/routes/auth.ts:resetPassword
All tests: passing ✓

## 🔄 Refactor — Returns 404 when email is not registered

Changes: Renamed handler to handlePasswordReset (matches existing naming pattern)
All tests: passing ✓

Next step? [Next behavior / Commit progress / Stop here]
```

### Bug Fix Example

```
> /optimus:tdd "Fix: login fails when email has uppercase letters"

## Behaviors to Implement

1. Reproduce: login with "User@Example.com" returns 401 (the bug)
2. Fix: login with "User@Example.com" succeeds and returns valid session
3. Edge case: login with "USER@EXAMPLE.COM" also succeeds

Start cycling? [Start cycling / Adjust]
```

The first behavior writes a test that **reproduces the bug** — proving it exists. Then the fix makes that test pass.

## When to Run

- **Starting a new feature** — build it test-first from the start
- **Fixing a bug** — reproduce it with a test before fixing
- **Adding an API endpoint** — define expected request/response behavior as tests first
- **Implementing business logic** — capture edge cases as tests before coding

## When NOT to Run

- **Refactoring existing code** — use `/optimus:simplify` instead (change structure, keep behavior, verify with existing tests)
- **Adding tests to existing code** — use `/optimus:unit-test` instead (retroactive test generation)
- **Exploratory prototyping** — TDD works best when you can describe expected behavior upfront

## Task Suitability Examples

The skill analyzes your task before starting and redirects unsuitable work to the right tool. Here's what fits and what doesn't:

| Task | Suitable? | Why / Alternative |
|---|---|---|
| "Add user authentication endpoint" | Yes | New testable behavior — API input/output |
| "Fix: login fails with uppercase email" | Yes | Bug → write reproducing test first |
| "Add pagination to product list API" | Yes | New testable behavior — query params, response shape |
| "Implement shopping cart (frontend + backend)" | Yes (decomposed) | Large feature — skill breaks it into small cycles per behavior |
| "Add rate limiting to all API endpoints" | Yes | New testable behavior per endpoint |
| "Refactor auth module into smaller files" | No → `/optimus:simplify` | No new behavior — restructuring only |
| "Update README documentation" | No | No testable code |
| "Change button color to blue" | No | Pure styling — no logic to test |
| "Update .env configuration" | No | Configuration — no testable behavior |
| "Delete the legacy billing module" | No | Removing code — tests should be removed, not added |

**Large features are welcome** — the skill decomposes them into small, independently testable behaviors. A full-stack feature like "build checkout flow" becomes 10-15 individual Red-Green-Refactor cycles (e.g., "POST /cart/items returns 201", "cart total includes tax", "checkout validates payment method"). Each cycle is tiny; the overall feature is built incrementally.

## Example Output

The skill produces a structured summary after completing:

```
## TDD Summary

### Behaviors Implemented
| # | Behavior | Test | Status |
|---|----------|------|--------|
| 1 | Returns 404 for unregistered email | reset-password.test.ts:"returns 404..." | ✓ Complete |
| 2 | Sends reset email with valid token | reset-password.test.ts:"sends reset..." | ✓ Complete |
| 3 | Returns 400 for invalid email format | reset-password.test.ts:"returns 400..." | ✓ Complete |
| 4 | Rate-limits to 3 per hour per email | reset-password.test.ts:"rate-limits..." | ⏸ Not started |

### Stats
- Cycles completed: 3 of 4
- Tests written: 3
- Tests passing: all ✓
- Files created: src/__tests__/auth/reset-password.test.ts
- Files modified: src/routes/auth.ts

### Coverage
- Before: 41%
- After: 47%
- Delta: +6%

### Suggested Commit
feat(auth): add password reset endpoint with email validation

Implements POST /auth/reset-password with 404 for unknown emails,
reset token generation, and email format validation. Rate limiting
pending (1 behavior remaining).
```

## How It Works

1. Verifies project context (`CLAUDE.md`, `coding-guidelines.md`) and test infrastructure exist
2. Analyzes task suitability — redirects unsuitable tasks (refactoring, docs, styling) to the right skill
3. Decomposes the feature or bug fix into small, testable behaviors for user approval
4. For each behavior: Red (write failing test) → Green (minimal implementation) → Refactor (clean up against coding guidelines)
5. Runs the full test suite at every transition (Red, Green, Refactor)
6. Suggests commit points after each cycle for small, focused commits
7. Reports summary with behaviors completed, tests written, and coverage delta

## Relationship to Other Skills

| | `/optimus:tdd` | `/optimus:unit-test` |
|---|---|---|
| Direction | Test-first (new code) | Test-after (existing code) |
| Scope | One feature or bug fix | Full project or directory |
| Cycle | Red-Green-Refactor per behavior | Discover → generate → verify |
| Infrastructure | Requires existing test setup | Provisions if missing |
| Refactoring | Applies guidelines in Refactor step | Never modifies source code |

| | `/optimus:tdd` | `/optimus:simplify` |
|---|---|---|
| Purpose | Implement new behavior test-first | Restructure existing code |
| Tests | Writes new tests | Uses existing tests as safety net |
| Behavior change | Adds new behavior | Preserves existing behavior |

| | `/optimus:tdd` | `/optimus:code-review` |
|---|---|---|
| Timing | During implementation | After implementation, before commit |
| Focus | Build correct code from the start | Catch issues in finished changes |
| Workflow | Use TDD to build, then code-review before committing |

**Full workflow**: `/optimus:init` → `/optimus:unit-test` (provision infrastructure + retroactive tests) → `/optimus:tdd` (build new features test-first) → `/optimus:code-review` (pre-commit review) → `/optimus:commit-message` (conventional commit).

## Skill Structure

| File | Purpose |
|---|---|
| `SKILL.md` | Skill definition with 8-step TDD workflow |

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Git
- Project initialized with `/optimus:init` (required — provides `coding-guidelines.md` for Refactor step)
- Working test infrastructure (framework, runner) — run `/optimus:unit-test` first if missing

## License

[MIT](../../LICENSE)
