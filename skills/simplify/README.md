# optimus:simplify

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that analyzes your codebase against the project's coding guidelines — with emphasis on issues that span multiple files — and presents a prioritized simplification plan. You choose what to apply; the test suite verifies nothing broke.

Well-maintained code has [30%+ fewer AI-introduced defects](https://arxiv.org/abs/2601.02200). `/optimus:init` sets up quality infrastructure with agents that guard new code automatically, but existing code can still accumulate technical debt. `/optimus:simplify` is the on-demand complement: a deliberate, project-wide review you run when you want to actively improve existing code.

## Features

- **Cross-cutting focus** — prioritizes issues that span multiple files: duplication across modules, pattern inconsistency, architectural drift, missing shared abstractions
- **Flexible scope** — full project, specific directory, or files changed since a commit/date
- **Two-phase workflow** — presents a simplification plan first, then applies only what you approve
- **Test verification** — runs the test suite after applying changes with evidence-based verification; reverts any change that causes failures
- **Conservative by default** — only suggests changes justified by the project's own guidelines
- **Prioritized findings** — High/Medium/Low impact with concrete before/after sketches, capped at 12 per run for actionable output
- **Deep mode** — iterative cleanup that loops analysis-apply cycles until zero findings remain (max 5 iterations), with explicit user consent and risk warnings
- **Works without `/optimus:init`** — falls back to generic coding guidelines when project-specific docs aren't available
- **Multi-repo workspace support** — resolves per-repo documentation when opened from a workspace root containing multiple git repos
- **Submodule exclusion** — automatically skips files inside git submodules
- **Generated file exclusion** — skips machine-generated files (Dart build_runner output, Visual Studio Designer files, database migration directories)

## Quick Start

This skill is part of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin. See the [main README](../../README.md) for installation instructions.

## Usage

In Claude Code, use any of these:

- `/optimus:simplify` — full project review
- `/optimus:simplify` "focus on the auth module"
- `/optimus:simplify` "review changes since last week"
- `/optimus:simplify deep` — iterative cleanup until zero findings remain
- `/optimus:simplify deep` "focus on src/auth" — deep mode with a specific scope

## When to Run

- **After `/optimus:init`** — review existing code against the newly established guidelines
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
- Guideline: DRY / SRP
- Current: Email validation repeated in login.ts, register.ts, reset.ts
- Suggested: Extract to shared validateEmail() in src/auth/validate.ts
```

You then choose: **Apply all**, **Selective** (pick by number), or **Skip**.

## How It Works

1. Verifies project docs exist (falls back to generic guidelines if missing)
2. Asks you to choose scope: full project, directory, or changed files
3. Activates deep mode if requested (iterative cleanup with user consent)
4. Loads all constraint docs and maps source directories, prioritized by git activity
5. Analyzes code with emphasis on patterns that span multiple files
6. Presents findings as a prioritized plan (capped at 12 per run)
7. Applies only user-approved changes, runs tests with evidence-based verification, reverts any that cause failures

## Deep Mode

By default, the skill caps findings at 12 per run. For exhaustive cleanup, use `deep` to loop automatically:

```
/optimus:simplify deep
```

**Key differences from normal mode:** Deep mode **applies changes automatically** at each iteration — it modifies your code, not just reports findings. It **requires a test command** (from `.claude/CLAUDE.md`) as its safety net; without one, it falls back to normal mode. All changes remain as local modifications — nothing is committed or pushed.

Deep mode runs the same analysis-apply cycle repeatedly (max 5 iterations) until zero findings remain. Before starting, it warns about credit/time consumption and breakage risk with low test coverage, and asks for explicit confirmation.

Each iteration:
1. Analyzes code (same caps: 12 findings, 5 per area)
2. Auto-applies all findings (test suite validates; failures trigger per-change bisect)
3. Runs the test suite — reverts any change that causes failures
4. Loops back for the next pass, or stops when clean

Deep mode stops when: no findings remain, the iteration cap (5) is reached, or all changes in an iteration fail tests. All changes remain as local modifications — review the full diff and commit when satisfied.

Research confirms iterative analysis catches issues that single-pass review misses, with most value in the first 2–3 iterations ([LLMLOOP, ICSME 2025](https://valerio-terragni.github.io/assets/pdf/ravi-icsme-2025.pdf)).

## Relationship to Code-Simplifier Agent

The code-simplifier agent and this skill are complementary — both use `coding-guidelines.md` as their source of truth but operate independently:

| | Code-simplifier agent | `/optimus:simplify` |
|---|---|---|
| Trigger | Automatic, after every edit | On-demand, user-invoked |
| Scope | Recently modified code | Full project, directory, or changed files |
| Focus | Per-file clarity and simplicity | Patterns across multiple files |
| Action | Applies safe changes directly; suggests structural changes for approval | Plan first, apply on approval |
| Role | Passive quality guardian | Active codebase review |

## Relationship to Builtin /simplify

Claude Code includes a builtin `/simplify` command. This follows the same pattern as `/init`:

| | Builtin `/simplify` | `/optimus:simplify` |
|---|---|---|
| Scope | Recently modified code within a session | Full project, directory, or changed files |
| Guidelines | General best practices | Project-specific `coding-guidelines.md` |
| Workflow | Direct application | Plan first, apply on approval |
| Focus | Per-file simplification | Cross-file patterns: duplication, inconsistency, architectural drift |
| Verification | — | Runs test suite, reverts failures |
| Finding cap | — | 12 per run, prioritized by impact |

`/optimus:simplify` is the enhanced, project-aware complement — just as `/optimus:init` extends the builtin `/init` with progressive disclosure docs, formatter hooks, and quality agents.

## Skill Structure

| File | Purpose |
|---|---|
| `SKILL.md` | Skill definition with two-phase workflow |
| *(shared)* `init/references/multi-repo-detection.md` | Multi-repo workspace detection algorithm |
| *(shared)* `init/references/prerequisite-check.md` | Shared prerequisite check with fallbacks |
| *(shared)* `init/references/constraint-doc-loading.md` | Constraint doc loading (single project, monorepo) |

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Git
- Project initialized with `/optimus:init` (recommended, not required)

## License

[MIT](../../LICENSE)
