# optimus:refactor

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that refactors your codebase using 4 parallel analysis agents — focusing on guideline compliance and testability. Presents a prioritized refactoring plan, then applies only what you approve. All changes stay local for your review.

Two primary goals:
1. **Guideline compliance** — align files with your project's quality docs: `coding-guidelines.md` for code files, `skill-writing-guidelines.md` for markdown instruction files (in skill-authoring projects), plus `architecture.md`, `styling.md`, and `testing.md` where applicable
2. **Testability** — restructure code so `/optimus:unit-test` can safely increase coverage without risky changes

Well-maintained code has [30%+ fewer AI-introduced defects](https://arxiv.org/abs/2601.02200). `/optimus:init` sets up quality infrastructure with agents that guard new code automatically, but existing code can still accumulate technical debt. `/optimus:refactor` is the on-demand complement: a deliberate, project-wide restructuring you run when you want to actively improve existing code.

## Features

- **Parallel multi-agent analysis** — 4 specialized agents (guideline compliance, testability, duplication/consistency, code simplification) run simultaneously for comprehensive coverage
- **Testability focus** — explicitly identifies structural barriers that prevent `/optimus:unit-test` from increasing coverage, with "testability impact" lines showing what becomes testable after each refactoring
- **Cross-cutting focus** — prioritizes issues that span multiple files: duplication across modules, pattern inconsistency, architectural drift, missing shared abstractions
- **Flexible invocation** — natural language scoping with no rigid syntax: `/optimus:refactor backend only`, `/optimus:refactor "focus on auth module"`, or just `/optimus:refactor` for full project
- **Two-phase workflow** — presents a refactoring plan first, then applies only what you approve
- **Test verification** — runs the test suite after applying changes with evidence-based verification; reverts any change that causes failures
- **Conservative by default** — only suggests changes justified by the project's own guidelines
- **Prioritized findings** — Critical/Warning/Suggestion severity with concrete before/after sketches, capped at 15 per run for focused, manageable output
- **Works without `/optimus:init`** — falls back to generic coding guidelines when project-specific docs aren't available
- **Multi-repo workspace support** — resolves per-repo documentation when opened from a workspace root containing multiple git repos
- **Submodule exclusion** — automatically skips files inside git submodules
- **Generated file exclusion** — skips machine-generated files (Dart build_runner output, Visual Studio Designer files, database migration directories)

## Quick Start

This skill is part of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin. See the [main README](../../README.md) for installation instructions.

## Usage

In Claude Code, use any of these:

- `/optimus:refactor` — full project refactoring
- `/optimus:refactor backend only` — scope to a specific area
- `/optimus:refactor "focus on the auth module"` — natural language scoping
- `/optimus:refactor "review changes since last week"` — incremental review
- `/optimus:refactor testability` — prioritize testability improvements
- `/optimus:refactor guidelines` — prioritize guideline compliance

For iterative refactor in a loop, see [`/optimus:refactor-deep`](../refactor-deep/README.md).

## Focus Mode

By default, refactor balances all analysis categories equally within its 15-finding cap. Use a focus keyword to prioritize:

- `/optimus:refactor testability` — reserve 12 of 15 finding slots for testability barriers
- `/optimus:refactor guidelines` — reserve 12 of 15 finding slots for guideline compliance
- `/optimus:refactor` — balanced across all categories (default)

Combine with scope:
- `/optimus:refactor testability "backend only"`
- `/optimus:refactor guidelines`

For iterative refactor with focus, see [`/optimus:refactor-deep testability`](../refactor-deep/README.md).

Focus does NOT skip other categories — high-severity findings from non-focused categories still surface in the remaining 3 slots.

**When to use focus:**
- After `/optimus:unit-test` flags "Not Testable Without Refactoring" → use `testability`
- After `/optimus:init` establishes new guidelines → use `guidelines`
- For periodic cleanup → omit focus for balanced analysis

## When to Run

- **Before `/optimus:unit-test`** — make untestable code testable first, then increase coverage safely
- **After `/optimus:init`** — review existing code against the newly established guidelines
- **After major features** — check that new code follows established patterns
- **Before releases** — catch quality issues before they ship
- **Periodic cleanup** — schedule regular reviews to prevent tech debt accumulation
- **Onboarding** — familiarize yourself with a codebase by seeing what the guidelines flag

## Example Output

The skill presents a structured plan before making any changes:

```
## Refactoring Plan

### Summary
- Scope: full project
- Focus: balanced (default)
- Areas analyzed: 4
- Total findings: 6 shown (of ~12 detected) — Critical: 2, Warning: 3, Suggestion: 1
- Cross-cutting findings: 2
- Testability improvements: 3 findings will make code testable for /optimus:unit-test
- Top recommendation: Extract database access from OrderService to enable unit testing

### Cross-Cutting Findings

**1. Inconsistent error handling across API routes** (Critical)
- Files: src/routes/users.ts:34, src/routes/orders.ts:28, src/routes/products.ts:41
- Category: Inconsistency
- Guideline: Follow Existing Patterns
- Pattern: Three different error response formats across route handlers
- Suggested: Extract shared error handler following the pattern in src/middleware/errors.ts

### Findings by Area

#### services — src/services/

**2. Inline database calls in OrderService** (Critical)
- File: src/services/order.ts:42
- Category: Testability Barrier
- Guideline: SRP / Dependency Injection
- Current: Direct SQL queries inside business logic methods
- Suggested: Extract to OrderRepository, inject via constructor
- Testability impact: OrderService.calculateTotal() and processOrder() become unit-testable
```

You then choose: **Apply all**, **Selective** (pick by number), or **Skip**.

## How It Works

1. Verifies project docs exist (falls back to generic guidelines if missing)
2. Parses arguments for scope and focus keyword
3. Loads all constraint docs and maps source directories, prioritized by git activity
4. **Launches 4 parallel agents** — guideline compliance, testability, duplication/consistency, and code simplification
5. Validates findings independently with evidence-based verification
6. Presents findings as a prioritized plan (capped at 15 per run)
7. Applies only user-approved changes, runs tests, reverts any that cause failures

## Iterative Refactor

For exhaustive refactoring that loops automatically, use the dedicated orchestrator skill [`/optimus:refactor-deep`](../refactor-deep/README.md). Each iteration runs in a fresh subagent context, fixes are applied automatically, tests run after every iteration, and failed fixes are reverted via bisection. Supports the same `testability` and `guidelines` focus modes as this skill.

### Research context

Iterative LLM feedback loops with automated verification consistently improve output quality, with the largest gains in early iterations and diminishing returns in later stages ([LLMLOOP, ICSME 2025](https://valerio-terragni.github.io/assets/pdf/ravi-icsme-2025.pdf)).

## Agent Architecture

4 specialized agents run in parallel, each with up to 15 findings:

| Agent | Role | Runs when |
|-------|------|-----------|
| 1 — Guideline Compliance | Explicit violations of project docs with exact rule citations | Always |
| 2 — Testability Analyzer | Structural barriers to unit testing — hardcoded deps, tight coupling, global state | Always |
| 3 — Consistency Analyzer | Cross-file duplication, pattern inconsistency, missing abstractions, architectural drift | Always |
| 4 — Code Simplifier | Unnecessary complexity, naming, dead code, pattern violations | Always |

## Relationship to Code-Simplifier Agent

The code-simplifier agent and this skill are complementary — both route each file to the correct quality lens (`coding-guidelines.md` for code files, `skill-writing-guidelines.md` for markdown instruction files in skill-authoring projects), but operate independently. This skill references the shared `constraint-doc-loading.md`; the code-simplifier inlines the same routing rules to stay within reference-depth limits.

| | Code-simplifier agent | `/optimus:refactor` |
|---|---|---|
| Trigger | Automatic, after every edit | On-demand, user-invoked |
| Scope | Recently modified code | Full project, directory, or changed files |
| Focus | Per-file clarity and simplicity | Cross-file patterns + testability barriers |
| Action | Applies safe changes directly; suggests structural changes for approval | Multi-agent analysis, plan first, apply on approval |
| Role | Passive quality guardian | Active codebase restructuring |

## Relationship to Builtin /simplify

Claude Code includes a builtin `/simplify` command. `/optimus:refactor` is the enhanced, project-aware complement:

| | Builtin `/simplify` | `/optimus:refactor` |
|---|---|---|
| Scope | Recently modified code within a session | Full project, directory, or changed files |
| Guidelines | General best practices | Project-specific `coding-guidelines.md` (plus `skill-writing-guidelines.md` in skill-authoring projects, routed per file type) |
| Analysis | Single-pass | 4 parallel agents with cross-validation |
| Focus | Per-file simplification | Cross-file patterns, guideline compliance, testability |
| Verification | — | Runs test suite, reverts failures |
| Finding cap | — | 15 per run, prioritized by impact |

## Skill Structure

| File | Purpose |
|---|---|
| `SKILL.md` | Skill definition with 8-step parallel agent workflow |
| `agents/` | Individual agent prompt files for all 4 analysis agents, shared constraints, and context blocks |
| *(shared)* `init/references/multi-repo-detection.md` | Multi-repo workspace detection algorithm |
| *(shared)* `init/references/prerequisite-check.md` | Shared prerequisite check with fallbacks |
| *(shared)* `init/references/constraint-doc-loading.md` | Constraint doc loading (single project, monorepo) |
| *(shared)* `init/references/verification-protocol.md` | Evidence-based test verification protocol |
| *(shared)* `references/harness-mode.md` | Harness mode single-iteration execution protocol |

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Git
- Project initialized with `/optimus:init` (recommended, not required)

## License

[MIT](../../LICENSE)
