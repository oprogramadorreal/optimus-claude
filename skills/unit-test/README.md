# optimus:unit-test

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that improves unit test coverage for existing code — discovering gaps, provisioning test infrastructure, and generating tests that follow your project's conventions.

Well-maintained code has [30%+ fewer AI-introduced defects](https://arxiv.org/abs/2601.02200), and tests are what make AI agents self-correcting: make change → run tests → see failure → fix. `/optimus:init` installs a test-guardian agent that monitors coverage gaps, but it doesn't write tests. `/optimus:unit-test` is the active complement: it fills gaps deliberately.

**Conservative by design** — only adds new test files, never refactors or restructures existing source code. If code is untestable as-is, it flags it rather than changing it. Refactoring is the domain of `/optimus:simplify`.

## Features

- **Pre-flight check** — verifies `/optimus:init` has been run and identifies available guideline documents
- **Project-wide discovery** — scans for test files, frameworks, coverage tooling, and optimus infrastructure status
- **Framework recommendation** — analyzes tech stack and recommends the most popular test framework with coverage tooling
- **Coverage tooling setup** — detects when a framework exists but coverage measurement is missing
- **Infrastructure provisioning** — installs test-guardian agent, creates testing.md, updates CLAUDE.md if init skipped them
- **Achievable threshold estimation** — analyzes testable vs untestable code to set realistic coverage targets without requiring refactoring
- **Prioritized test plan** — up to 10 items per run, highest-value targets first, user-approved before execution
- **Conservative test writing** — adds new test files only; fixes failing tests, not source code
- **Bug discovery** — reports bugs found in existing code during test writing without fixing them
- **Monorepo & multi-repo workspace support** — detects subprojects and processes each independently

## Quick Start

This skill is part of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin. See the [main README](../../README.md) for installation instructions.

## Usage

In Claude Code, use any of these:

- `/optimus:unit-test` — full project test coverage improvement
- `/optimus:unit-test src/api` — scope to a specific directory
- `/optimus:unit-test packages/auth` — scope to a monorepo subproject
- "improve test coverage"
- "add unit tests for this project"
- "set up testing and write tests"

## When to Run

- **After `/optimus:init`** — establish test coverage for a newly initialized project
- **On established projects** — fill coverage gaps in codebases that grew without systematic testing
- **Before releases** — strengthen test coverage before shipping
- **After major refactors** — verify refactored code with new tests
- **Periodic maintenance** — incrementally improve coverage over multiple runs (10 tests per run)

## Example Output

The skill produces a structured summary after completing:

```
## Unit Test Summary

### Infrastructure Provisioned
- Installed test-guardian agent (.claude/agents/test-guardian.md)
- Created testing.md (.claude/docs/testing.md)
- Added test commands to CLAUDE.md

### Coverage
- Coverage tooling: vitest --coverage
- Before: 23% → After: 41%
- Achievable target (without refactoring): ~58%

### Tests Created
| # | File | Target | Status |
|---|------|--------|--------|
| 1 | src/__tests__/auth.test.ts | auth module exports | ✓ Pass |
| 2 | src/__tests__/validate.test.ts | validation utilities | ✓ Pass |
| 3 | src/__tests__/transform.test.ts | data transformations | ✓ Pass |
| 4 | src/__tests__/config.test.ts | config loader | ✓ Pass |
| 5 | src/__tests__/router.test.ts | route handlers | ✓ Pass (bug found) |

### Bugs Discovered
- router.test.ts: GET /users/123 returns 500 when user has no email field (expects 200 with null email)

### Not Testable Without Refactoring
- src/services/payment.ts — inline Stripe API calls without injection
- src/db/migrate.ts — direct database connection, no repository pattern
- To address these, run /optimus:simplify to review and restructure the code first.
```

## How It Works

1. Verifies project context exists and identifies available guideline documents
2. Discovers existing test infrastructure, framework, coverage tooling, and gaps
3. Recommends and installs test framework + coverage tooling if missing (with approval)
4. Provisions optimus infrastructure (test-guardian, testing.md, CLAUDE.md updates)
5. Measures baseline coverage and estimates achievable target without refactoring
6. Presents prioritized test generation plan (capped at 10 items)
7. Writes tests following project conventions; runs each immediately
8. Reports coverage impact, bugs discovered, and code flagged as untestable

## Relationship to Test-Guardian Agent

The test-guardian agent and this skill are complementary — both use `testing.md` as their source of truth but serve different roles:

| | Test-guardian agent | `/optimus:unit-test` |
|---|---|---|
| Trigger | Automatic, after code changes | On-demand, user-invoked |
| Scope | Current task changes | Full project or scoped directory |
| Action | Flags gaps, doesn't write tests | Writes and verifies new tests |
| Infrastructure | Requires existing setup | Provisions if missing |
| Coverage | Reports delta | Analyzes achievable threshold, moves toward it |
| Role | Passive monitoring | Active test generation |

## Relationship to Other Skills

| | `/optimus:unit-test` | `/optimus:simplify` |
|---|---|---|
| Scope | Test files only | Source code |
| When code is untestable | Flags it, suggests `/optimus:simplify` | Restructures code to make it testable |
| Modifies source? | Never | Yes, with approval |

| | `/optimus:unit-test` | `/optimus:init` |
|---|---|---|
| Test infrastructure | Provisions if missing | Installs test-guardian agent |
| Test files | Writes new tests | Does not write tests |
| Coverage tooling | Recommends and installs | Does not handle |

**Workflow**: `/optimus:init` (set up infrastructure) → `/optimus:unit-test` (write tests) → `/optimus:simplify` (restructure untestable code) → `/optimus:unit-test` again (test the restructured code).

## Skill Structure

| File | Purpose |
|---|---|
| `SKILL.md` | Skill definition with 8-step workflow |
| `references/framework-recommendations.md` | Stack-specific test framework and coverage tooling recommendations |

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Git
- Project initialized with `/optimus:init` (recommended, not required)

## License

[MIT](../../LICENSE)
