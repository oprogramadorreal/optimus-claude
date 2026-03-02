# prime:simplify

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that analyzes your codebase against the project's coding guidelines — with emphasis on issues that span multiple files — and presents a prioritized simplification plan. You choose what to apply; the test suite verifies nothing broke.

Well-maintained code has [30%+ fewer AI-introduced defects](https://arxiv.org/abs/2601.02200). `/prime:init` sets up quality infrastructure with agents that guard new code automatically, but existing code can still accumulate technical debt. `/prime:simplify` is the on-demand complement: a deliberate, project-wide review you run when you want to actively improve existing code.

## Features

- **Cross-cutting focus** — prioritizes issues that span multiple files: duplication across modules, pattern inconsistency, architectural drift, missing shared abstractions
- **Flexible scope** — full project, specific directory, or files changed since a commit/date
- **Two-phase workflow** — presents a simplification plan first, then applies only what you approve
- **Test verification** — runs the test suite after applying changes; reverts any change that causes failures
- **Conservative by default** — only suggests changes justified by the project's own guidelines
- **Prioritized findings** — High/Medium/Low impact with concrete before/after sketches, capped at 12 per run for actionable output
- **Works without `/prime:init`** — falls back to generic coding guidelines when project-specific docs aren't available

## Quick Start

This skill is part of the [prime](https://github.com/oprogramadorreal/claude-code-prime) plugin. See the [main README](../../README.md) for installation instructions.

## Usage

In Claude Code, use any of these:

- `/prime:simplify` — full project review
- `/prime:simplify` "focus on the auth module"
- `/prime:simplify` "review changes since last week"
- "simplify existing code against guidelines"
- "find code quality issues across the project"
- "review code quality across the project"

## When to Run

- **After `/prime:init`** — review existing code against the newly established guidelines
- **After major features** — check that new code follows established patterns
- **Before releases** — catch quality issues before they ship
- **Periodic cleanup** — schedule regular reviews to prevent tech debt accumulation
- **Onboarding** — familiarize yourself with a codebase by seeing what the guidelines flag

## Example Output

The skill presents a structured plan before making any changes:

```
## Simplification Plan

### Summary
- Scope: full project
- Areas analyzed: 4
- Total findings: 8 shown (of ~14 detected) — High: 3, Medium: 4, Low: 1
- Cross-cutting findings: 2
- Top recommendation: Consolidate duplicated validation logic across auth routes

### Cross-Cutting Findings

**1. Inconsistent error handling across API routes** (High)
- Files: src/routes/users.ts:34, src/routes/orders.ts:28, src/routes/products.ts:41
- Guideline: Follow Existing Patterns
- Pattern: Three different error response formats across route handlers
- Suggested: Extract shared error handler following the pattern in src/middleware/errors.ts

### Findings by Area

#### auth — src/auth/

**2. Duplicated validation logic** (High)
- File: src/auth/login.ts:42
- Guideline: DRY / Small, Focused Functions (SRP)
- Current: Email validation repeated in login.ts, register.ts, reset.ts
- Suggested: Extract to shared validateEmail() in src/auth/validate.ts
```

You then choose: **Apply all**, **Selective** (pick by number), or **Skip**.

## How It Works

1. Verifies project docs exist (falls back to generic guidelines if missing)
2. Asks you to choose scope: full project, directory, or changed files
3. Loads all constraint docs and maps source directories, prioritized by git activity
4. Analyzes code with emphasis on patterns that span multiple files
5. Presents findings as a prioritized plan (capped at 12 per run)
6. Applies only user-approved changes, runs tests, reverts any that cause failures

## Relationship to Code-Simplifier Agent

The code-simplifier agent and this skill are complementary — both use `coding-guidelines.md` as their source of truth but operate independently:

| | Code-simplifier agent | `/prime:simplify` |
|---|---|---|
| Trigger | Automatic, after every edit | On-demand, user-invoked |
| Scope | Recently modified code | Full project, directory, or changed files |
| Focus | Per-file clarity and simplicity | Patterns across multiple files |
| Action | Applies changes directly | Plan first, apply on approval |
| Role | Passive quality guardian | Active codebase review |

## Relationship to Builtin /simplify

Claude Code includes a builtin `/simplify` command. This follows the same pattern as `/init`:

| | Builtin `/simplify` | `/prime:simplify` |
|---|---|---|
| Scope | Recently modified code within a session | Full project, directory, or changed files |
| Guidelines | General best practices | Project-specific `coding-guidelines.md` |
| Workflow | Direct application | Plan first, apply on approval |
| Focus | Per-file simplification | Cross-file patterns: duplication, inconsistency, architectural drift |
| Verification | — | Runs test suite, reverts failures |
| Finding cap | — | 12 per run, prioritized by impact |

`/prime:simplify` is the enhanced, project-aware complement — just as `/prime:init` extends the builtin `/init` with progressive disclosure docs, formatter hooks, and quality agents.

## Skill Structure

| File | Purpose |
|---|---|
| `SKILL.md` | Skill definition with two-phase workflow |

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Git
- Project primed with `/prime:init` (recommended, not required)

## License

[MIT](../../LICENSE)
