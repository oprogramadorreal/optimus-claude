# optimus:tdd

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that guides test-driven development — decompose a feature or bug fix into behaviors, then cycle through Red (failing test) → Green (minimal implementation) → Refactor for each one.

TDD is [more important with AI, not less](https://code.claude.com/docs/en/best-practices). Tests give the AI agent a feedback loop to self-correct: write test → see failure → implement → verify. Without tests, every change is a gamble. `/optimus:unit-test` adds tests to existing code retroactively. `/optimus:tdd` is the complement: build new code test-first.

## Why TDD Matters More with AI

Anthropic's [#1 best practice](https://code.claude.com/docs/en/best-practices) for Claude Code is giving it a way to verify its own work. TDD is the purest form of this — every behavior starts with a test that the agent must make pass. Three properties make TDD uniquely effective with AI:

- **Binary feedback loop** — A test either passes or fails. This is the clearest possible signal for an LLM. "This test fails — make it pass" is precise and verifiable, unlike open-ended instructions. The agent cannot hallucinate its way past a failing test.
- **Scope constraint** — TDD forces one behavior per cycle. Without it, AI agents tend to implement entire features in one shot, producing plausible-looking code with subtle bugs. One-behavior-at-a-time prevents errors from compounding.
- **Independent specification** — When tests are written *after* implementation, the AI tends to write tests that confirm whatever it just wrote — including bugs. Test-first means the expected behavior is defined before the code exists, so the test is an independent specification, not a rubber stamp.

The [2025 DORA report](https://cloud.google.com/discover/how-test-driven-development-amplifies-ai-success) confirms this pattern: AI adoption increases perceived code quality but also increases delivery instability. TDD is the control system that makes AI-assisted development reliable rather than risky.

## Features

- **Suitability analysis** — analyzes the task against the codebase before starting; redirects unsuitable tasks (refactoring, docs, styling) to the right skill
- **Behavior decomposition** — breaks features or bug fixes into small, independently testable behaviors before writing any code
- **Red-Green-Refactor cycles** — enforces the classic TDD discipline: failing test → minimal pass → clean up
- **Guideline-aware refactoring** — applies your project's `coding-guidelines.md` during the Refactor step
- **Convention-aware tests** — follows your `testing.md` for framework, file location, naming, and mocking patterns
- **Test verification at every step** — runs the full test suite after Red, Green, and Refactor to catch regressions instantly
- **Lint/type-check verification** — runs lint or type-check commands (if configured) during the Green step to catch type errors that passing tests might miss
- **Quality gate** — after cycling completes, launches code-simplifier and test-guardian agents in parallel to catch cross-cycle issues (duplication between behaviors, naming drift, edge-case coverage gaps) before pushing
- **Feature branch workflow** — creates a dedicated branch, commits after each cycle, pushes and creates a PR/MR at the end
- **Automatic PR/MR creation** — detects GitHub/GitLab and creates a pull/merge request using the [Conventional PR](../pr/README.md) format (structured summary, changes, rationale, test plan). Suggests `/optimus:pr` if the CLI is missing
- **Coverage tracking** — detects coverage commands from testing.md, test runner flags, or package scripts; reports delta
- **Multi-repo workspace support** — targets specific repos in multi-repo setups
- **Submodule exclusion** — skips git submodule directories

## Quick Start

This skill is part of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin. See the [main README](../../README.md) for installation instructions.

## Prerequisites

1. **`/optimus:init`** — required. Installs `CLAUDE.md` and `coding-guidelines.md` used during Refactor
2. **`/optimus:unit-test`** — recommended. Provisions test framework, coverage tooling, and `testing.md` if missing
3. **`/optimus:permissions`** — recommended. Enables branch-aware git protection so TDD can commit and push to feature branches while protecting main/master
4. **`gh` or `glab` CLI** — optional. Needed for automatic PR/MR creation (GitHub CLI or GitLab CLI)

**Workflow**: `/optimus:init` → `/optimus:unit-test` → `/optimus:permissions` → `/optimus:tdd`

## Usage

In Claude Code, use any of these:

- `/optimus:tdd` — start a TDD session (will ask what to implement)
- `/optimus:tdd` "Add user authentication endpoint"
- `/optimus:tdd` "Fix: login fails when email has uppercase letters"
- "implement with TDD"
- "let's do this test-first"

Provide a **brief description** (1-2 sentences). The skill analyzes the codebase and decomposes the task into specific testable behaviors — you don't need to specify every detail upfront. For lengthy specs (e.g., a pasted Jira ticket or acceptance criteria), the skill will distill the core goal and confirm before proceeding.

### Interactive Example

```
> /optimus:tdd

## TDD scope

What feature or bug fix do you want to implement with TDD?

- **New feature** — "Implement a new capability (e.g., 'Add user authentication endpoint')"
- **Bug fix** — "Fix a bug by reproducing it with a test first (e.g., 'Login fails when email has uppercase')"
```

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

Committed: a1b2c3d feat(auth): add password reset with 404 for unknown emails

Next step? [Next behavior / Stop here]
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

### Decomposition Example (Medium Feature)

For larger features, the skill decomposes into many small behaviors. Example:

```
> /optimus:tdd "Add shopping cart"

## Behaviors to Implement

1. POST /cart/items adds a product to the cart — returns 201 with cart contents
2. POST /cart/items returns 404 when product ID doesn't exist
3. POST /cart/items returns 400 when quantity is zero or negative
4. GET /cart returns current cart contents with product details and totals
5. GET /cart returns empty array when cart has no items
6. DELETE /cart/items/:id removes an item from the cart — returns updated cart
7. Cart total sums item prices multiplied by quantities
8. Cart total applies discount code when valid — reduces total by percentage

Start cycling? [Start cycling / Adjust]
```

Each behavior becomes one Red-Green-Refactor cycle. The feature is built incrementally — the first 3 cycles deliver a working "add to cart", cycles 4-5 add retrieval, and so on. If the decomposition exceeds 10 behaviors, the skill splits them into milestones (~5-8 behaviors each), presents the first milestone, and asks whether to continue after completing it.

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
- Quality gate: code-simplifier (1 finding), test-guardian (0 findings)

### Coverage
- Before: 41%
- After: 47%
- Delta: +6%

### Git Activity
- Branch: `tdd/add-password-reset-endpoint` (from `main`)
- Commits: 3
- Pushed: ✓
- PR: https://github.com/owner/repo/pull/42 (Conventional PR format)
```

## How It Works

1. Verifies project context (`CLAUDE.md`, `coding-guidelines.md`) and test infrastructure exist
2. Distills lengthy specs into a single-sentence goal for confirmation, then analyzes task suitability — redirects unsuitable tasks (refactoring, docs, styling) to the right skill
3. Creates a feature branch from the current branch (e.g., `tdd/add-password-reset`)
4. Decomposes the feature or bug fix into small, testable behaviors for user approval
5. For each behavior: Red (write failing test) → Green (minimal implementation) → Refactor (clean up against coding guidelines)
6. Runs the full test suite at every transition (Red, Green, Refactor) and lint/type-check during Green
7. Automatically commits on the feature branch after each cycle
8. Runs code-simplifier and test-guardian agents in parallel as a quality gate (if installed)
9. Reports summary, pushes the branch, and creates a PR/MR with task description and coverage delta

## Git Workflow

TDD automatically manages a feature branch for all work:

1. **Branch creation** — Creates `tdd/<slug>` (or `tdd/fix-<slug>`) from the current branch before any code changes
2. **Auto-commits** — After each completed Red-Green-Refactor cycle, TDD automatically stages and commits with a conventional message
3. **Final commit** — Any uncommitted work (e.g., stopped mid-cycle) is committed at the end of the session
4. **Push** — The feature branch is pushed to origin automatically
5. **PR/MR** — A pull request (GitHub) or merge request (GitLab) is created targeting the original branch

The user's original branch is never modified. All code review happens through the PR/MR.

**Platform detection:** TDD checks the `origin` remote URL for `github` or `gitlab`, falling back to CI file detection (`.github/` or `.gitlab-ci.yml`). Requires `gh` (GitHub CLI) or `glab` (GitLab CLI) for PR/MR creation — if unavailable, TDD pushes the branch and suggests running `/optimus:pr` (which can install the CLI).

**Works with `/optimus:permissions`:** The permissions skill's branch protection hook ensures git operations on protected branches (master, main, develop, dev, development, staging, stage, prod, production, release) are blocked. TDD always creates a feature branch, so it works seamlessly with branch protection enabled.

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
| Timing | During implementation | After implementation (PR/MR review) |
| Focus | Build correct code from the start | Catch issues in finished changes |
| Workflow | Use TDD to build, then code-review the PR/MR |

| | `/optimus:tdd` | `/optimus:pr` |
|---|---|---|
| PR creation | Automatic — side effect of TDD workflow | Dedicated — full Conventional PR flow |
| CLI missing | Skips PR, suggests `/optimus:pr` | Offers to install CLI |
| Update support | No | Yes — regenerate existing PR description |
| Format | Both use the shared Conventional PR template |

**Full workflow**: `/optimus:init` → `/optimus:unit-test` (provision infrastructure + retroactive tests) → `/optimus:permissions` (branch-aware git protection) → `/optimus:tdd` (build new features test-first — creates branch, commits, pushes, creates PR/MR) → `/optimus:code-review` (review the PR/MR). Use `/optimus:pr` to update the PR description later or to create PRs for non-TDD work.

## Skill Structure

| File | Purpose |
|---|---|
| `SKILL.md` | Skill definition with 9-step TDD workflow (includes quality gate) |
| `references/agent-prompts.md` | Prompt templates for quality gate agents (code-simplifier, test-guardian) |
| `references/testing-anti-patterns.md` | Mocking anti-patterns and gate questions — loaded during Red step to prevent bad test patterns |

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Git
- Project initialized with `/optimus:init` (required — provides `coding-guidelines.md` for Refactor step)
- Working test infrastructure (framework, runner) — run `/optimus:unit-test` first if missing

## License

[MIT](../../LICENSE)
