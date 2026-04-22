# optimus:unit-test

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that improves unit test coverage for existing code — discovering gaps and generating tests that follow your project's conventions. Requires `/optimus:init` to have set up test infrastructure first.

Well-maintained code has [30%+ fewer AI-introduced defects](https://arxiv.org/abs/2601.02200), and tests are what make AI agents self-correcting: make change → run tests → see failure → fix. The plugin includes a test-guardian agent that monitors coverage gaps, but it doesn't write tests. `/optimus:unit-test` is the active complement: it fills gaps deliberately.

**Conservative by design** — only adds new test files, never refactors or restructures existing source code. If code is untestable as-is, it flags it rather than changing it. Refactoring is the domain of `/optimus:refactor`.

## Features

- **Pre-flight check** — verifies `/optimus:init` has been run and identifies available guideline documents
- **Project-wide discovery** — scans for test files, frameworks, coverage tooling; stops if no test framework found (recommends running `/optimus:init`)
- **Achievable threshold estimation** — analyzes testable vs untestable code to set realistic coverage targets without requiring refactoring
- **Prioritized test plan** — up to 10 items per run, highest-value targets first, user-approved before execution
- **Conservative test writing** — adds new test files only; may fix a newly-written test but never modifies existing tests or source code
- **Broken baseline handoff** — stops with a triage pointer when pre-existing tests fail; never modifies their logic
- **Bug discovery** — reports bugs found in existing code during test writing without fixing them
- **Monorepo & multi-repo workspace support** — detects subprojects and processes each independently
- **Submodule exclusion** — automatically skips git submodules during discovery

## Quick Start

This skill is part of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin. See the [main README](../../README.md) for installation instructions.

## Usage

In Claude Code, use any of these:

- `/optimus:unit-test` — full project test coverage improvement
- `/optimus:unit-test src/api` — scope to a specific directory
- `/optimus:unit-test packages/auth` — scope to a monorepo subproject
- `/optimus:unit-test deep` — iterative test-generation until converged (default 5 iterations, max 10)
- `/optimus:unit-test deep 8` — deep mode with custom iteration cap
- `/optimus:unit-test deep src/api` — deep mode with scope
- `/optimus:unit-test deep harness` — multi-cycle automated test coverage + testability refactoring with fresh context per phase; runs unit-test and refactor testability in alternating cycles, resetting context between phases to avoid degradation

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
- To address these, run /optimus:refactor testability to prioritize testability improvements.
```

## How It Works

1. Verifies project context exists and identifies available guideline documents
2. Discovers test infrastructure, runs existing tests, measures baseline coverage, and estimates achievable target (agent-assisted)
3. Presents prioritized test generation plan (capped at 10 items)
4. Writes tests following project conventions and mocking anti-patterns; self-reviews against a quality checklist before running each test
5. Runs the full test suite with evidence-based verification, then reports coverage impact, bugs discovered, and code flagged as untestable

## Deep Mode

Normal mode caps test generation at 10 items per run — one pass through discovery, plan, write. Deep mode loops the discovery-and-write cycle automatically, each iteration discovering new testable items not yet covered, until coverage converges, plateaus, or the iteration cap is reached.

### How it works

Deep mode runs the same discovery-and-write cycle repeatedly (default 5, up to 10 iterations) until coverage converges or plateaus. Before starting, it warns about credit/time consumption and context-accumulation risk on large codebases, and asks for explicit confirmation.

Each iteration:
1. Runs the Test Infrastructure Analyzer agent with an iteration-context block on iterations 2+ (prior test files, reverted items, flagged untestable code, cumulative coverage delta)
2. Auto-approves the test generation plan — skips the "Approve all / Selective / Skip" prompt
3. Writes tests for each planned item, running each test immediately and fixing or flagging failures (up to 3 attempts per test)
4. Runs the full test suite — reverts any newly-added test file that causes regressions
5. Presents an **iteration report** — a table showing each test attempted, target, coverage delta, and status (pass / reverted / bug-found / abandoned)
6. Loops back to discovery for the next pass, or stops when a termination condition is met

### Key differences from normal mode

| Aspect | Normal mode | Deep mode |
|--------|-------------|-----------|
| Iterations | 1 (single pass, 10 items) | Up to 10 (default 5) |
| Plan approval | User chooses (Approve all / Selective / Skip) | Automatic (confirmed upfront) |
| Test verification | After all tests written | After every iteration |
| Failed tests | Fixed up to 3 attempts, else flagged | Same per-test rule; additionally, any newly-added test causing full-suite regressions is reverted and tracked |
| Output | Single summary | Per-iteration report tables + cumulative summary table |
| Requirement | None | Test command in `.claude/CLAUDE.md` |

### Iteration context

On iterations 2+, the discovery agent receives a context block summarizing: test files added in prior iterations (to skip re-discovery), items previously reverted or abandoned (to avoid re-attempting), untestable code already flagged (to focus discovery on genuinely new items), and cumulative coverage delta so far. This keeps each iteration converging on new testable items rather than thrashing on items the previous pass already addressed.

### Stop conditions

Deep mode stops when any of the following conditions is met:

- **Convergence** — no new testable items discovered this iteration
- **All reverted** — every test added in an iteration caused failures
- **Coverage plateau** *(when coverage tool is available)* — this iteration's coverage delta is ≤ 0.5 percentage points in absolute value
- **Cap reached** — the iteration cap is reached (continue in a fresh conversation)

Exact messages and the "plateau is skipped when coverage tool is unavailable" rule are in [skills/unit-test/SKILL.md](SKILL.md) under "Deep mode loop" (Step 4).

From iteration 3 onward, a context-accumulation warning appears; if the cap is reached, all continuation options are framed under starting a fresh conversation. After all iterations complete, a **cumulative report** summarizes every test added across all iterations in a single table, plus aggregated Bugs Discovered and Not Testable Without Refactoring sections.

### Deep harness mode

For larger codebases or when context accumulation degrades quality, use deep harness mode. It alternates `/optimus:unit-test` and `/optimus:refactor testability` in a multi-cycle loop, launching a fresh `claude -p` session per phase — each runs a single unit-test or refactor pass with prior progress injected from a progress file, giving every phase a clean context window.

```bash
# Invoke from within a conversation:
/optimus:unit-test deep harness
/optimus:unit-test deep harness 5 "src/api"

# Or run the script directly:
python scripts/test-coverage-harness/main.py
python scripts/test-coverage-harness/main.py --scope "src/api" --max-cycles 8
python scripts/test-coverage-harness/main.py --timeout 1200
python scripts/test-coverage-harness/main.py --resume
```

The harness handles test execution, untestable-code handoff to refactor testability, checkpoint commits between phases, and termination detection externally. Press Ctrl+C at any time to stop safely; resume later with `--resume`.

**Security note:** By default, each `claude -p` session runs with `--dangerously-skip-permissions` because the harness is headless (no terminal for permission prompts). For a safer alternative, use `--allowed-tools` to restrict sessions to a specific tool whitelist. For OS-level isolation, use [built-in sandboxing](https://code.claude.com/docs/en/sandboxing) (macOS/Linux) or [devcontainers](https://code.claude.com/docs/en/devcontainer).

### Research context

Iterative LLM feedback loops with automated verification consistently improve output quality, with the largest gains in early iterations and diminishing returns in later stages ([LLMLOOP, ICSME 2025](https://valerio-terragni.github.io/assets/pdf/ravi-icsme-2025.pdf)).

## Relationship to Test-Guardian Agent

The test-guardian agent and this skill are complementary — both use `testing.md` as their source of truth but serve different roles:

| | Test-guardian agent | `/optimus:unit-test` |
|---|---|---|
| Trigger | Automatic, after code changes | On-demand, user-invoked |
| Scope | Current task changes | Full project or scoped directory |
| Action | Flags gaps, doesn't write tests | Writes and verifies new tests |
| Infrastructure | Requires existing setup | Requires `/optimus:init` setup |
| Coverage | Reports delta | Analyzes achievable threshold, moves toward it |
| Role | Passive monitoring | Active test generation |

## Relationship to Other Skills

| | `/optimus:unit-test` | `/optimus:refactor` |
|---|---|---|
| Scope | Test files only | Source code |
| When code is untestable | Flags it, suggests `/optimus:refactor testability` | Restructures code to make it testable |
| Modifies source? | Never | Yes, with approval |

| | `/optimus:unit-test` | `/optimus:init` |
|---|---|---|
| Test infrastructure | Requires init to set it up | Installs framework, coverage tooling, testing docs |
| Test files | Writes new tests | Does not write tests |
| Coverage analysis | Measures and reports | Does not analyze |

**Workflow**: `/optimus:init` (set up everything including test infrastructure) → `/optimus:unit-test` (write tests to increase coverage) → `/optimus:refactor testability` (restructure untestable code with testability focus) → `/optimus:unit-test` again (test the restructured code).

**Harness mode**: `/optimus:unit-test deep harness` automates this cycle — it runs unit-test and refactor testability in alternating phases, with fresh context per phase, committing progress after each. This is the automated alternative to manually running unit-test then refactor in a loop.

## Skill Structure

| File | Purpose |
|---|---|
| `SKILL.md` | Skill definition with 5-step workflow |
| `agents/` | Individual agent prompt files for Test Infrastructure Analysis subagent |
| *(shared)* `init/references/multi-repo-detection.md` | Multi-repo workspace detection algorithm |
| *(shared)* `init/references/constraint-doc-loading.md` | Constraint doc loading — Monorepo Scoping Rule |

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Git
- Project initialized with `/optimus:init` (required — skill stops if CLAUDE.md is not found)

## License

[MIT](../../LICENSE)
