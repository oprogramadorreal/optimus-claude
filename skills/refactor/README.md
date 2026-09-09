# optimus:refactor

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that refactors your codebase across four analysis lenses — focusing on guideline compliance and testability. It presents a prioritized refactoring plan, applies only what you approve, and keeps all changes local for your review.

Two primary goals:

1. **Guideline compliance** — align files with your project's quality docs: `coding-guidelines.md` for code, `skill-writing-guidelines.md` for markdown instruction files (in skill-authoring projects), plus `architecture.md`, `styling.md`, and `testing.md` where applicable
2. **Testability** — restructure code so `/optimus:unit-test` can safely increase coverage without risky changes

## Features

- **Four analysis lenses** — guideline compliance, testability barriers, cross-file duplication/consistency, and code simplification; applied inline for a handful of files, fanned out to parallel agents for a directory or wider
- **Two-phase workflow** — plan first, then apply only the findings you approve
- **Test verification** — runs your test suite after applying changes and reverts any change that causes failures
- **Conservative by default** — only suggests changes justified by the project's own guidelines; falls back to general best practices without `/optimus:init`
- **Prioritized findings** — Critical/Warning/Suggestion severity, capped at 15 per run with before/after sketches
- **Smart exclusions** — skips git submodules, generated sources (build_runner output, Designer files, migration directories), lock and minified files
- **Multi-repo and monorepo aware** — per-repo and per-subproject doc resolution

## Quick Start

This skill is part of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin. See the [main README](../../README.md) for installation instructions.

## Usage

- `/optimus:refactor` — full project
- `/optimus:refactor "focus on the auth module"` — natural-language scoping
- `/optimus:refactor "review changes since last week"` — incremental review
- `/optimus:refactor testability` — prioritize testability improvements
- `/optimus:refactor guidelines "src/api"` — prioritize guideline compliance in a directory

For iterative refactoring in an automated loop, use `/optimus:deep refactor`.

## Focus Mode

By default all analysis categories compete equally for the 15-finding cap. A focus keyword prioritizes that category; high-severity findings from other categories may still surface within the same cap:

- `testability` — after `/optimus:unit-test` flags "Not Testable Without Refactoring"
- `guidelines` — after `/optimus:init` establishes new guidelines
- no focus — balanced, for periodic cleanup

## When to Run

- **Before `/optimus:unit-test`** — make untestable code testable first
- **After `/optimus:init`** — review existing code against the newly established guidelines
- **After major features / before releases** — catch pattern drift and quality issues early
- **Periodically** — prevent tech debt accumulation

## How It Works

1. Verifies project docs exist (recommends `/optimus:init` or falls back to general best practices)
2. Parses arguments for focus keyword and scope
3. Loads constraint docs and maps source areas, prioritized by git churn
4. Applies the four analysis lenses — inline for a small scope, as parallel agents otherwise
5. Independently validates findings (context, intent, git history) and presents a prioritized plan
6. Applies only approved changes, runs tests, and reverts anything that breaks them

Example plan entry:

```
**2. Inline database calls in OrderService** (Critical)
- File: src/services/order.ts:42
- Category: Testability Barrier
- Guideline: SRP / Dependency Injection
- Suggested: Extract to OrderRepository, inject via constructor
- Testability impact: OrderService.calculateTotal() becomes unit-testable
```

You then choose: **Apply all**, **Selective** (pick by number), or **Skip**.

## Relationship to the Code-Simplifier Agent

The plugin's code-simplifier agent cleans up code you have just changed; `/optimus:refactor` is the on-demand complement for restructuring existing code:

| | Code-simplifier agent | `/optimus:refactor` |
|---|---|---|
| Trigger | Invoked on request, on recently modified code | On-demand, user-invoked |
| Scope | Recently modified code | Full project, directory, or changed files |
| Focus | Per-file clarity | Cross-file patterns + testability barriers |
| Action | Applies safe changes directly | Plan first, apply on approval |

## Requirements

- Optimus installed in a [supported host](../../README.md#supported-hosts-and-versions)
- Git
- Project initialized with `/optimus:init` (recommended, not required)
- Test command in `.claude/CLAUDE.md` for post-apply verification and `/optimus:deep refactor`

## License

[MIT](../../LICENSE)
