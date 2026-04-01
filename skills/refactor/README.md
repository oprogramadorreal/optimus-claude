# optimus:refactor

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that refactors your codebase using up to 4 parallel analysis agents — focusing on guideline compliance and testability. Presents a prioritized refactoring plan, then applies only what you approve. All changes stay local for your review.

Two primary goals:
1. **Guideline compliance** — align code with your project's coding-guidelines.md, architecture.md, styling.md, and testing.md
2. **Testability** — restructure code so `/optimus:unit-test` can safely increase coverage without risky changes

Well-maintained code has [30%+ fewer AI-introduced defects](https://arxiv.org/abs/2601.02200). `/optimus:init` sets up quality infrastructure with agents that guard new code automatically, but existing code can still accumulate technical debt. `/optimus:refactor` is the on-demand complement: a deliberate, project-wide restructuring you run when you want to actively improve existing code.

## Features

- **Parallel multi-agent analysis** — up to 4 specialized agents (guideline compliance, testability, duplication/consistency, code simplification) run simultaneously for comprehensive coverage
- **Testability focus** — explicitly identifies structural barriers that prevent `/optimus:unit-test` from increasing coverage, with "testability impact" lines showing what becomes testable after each refactoring
- **Cross-cutting focus** — prioritizes issues that span multiple files: duplication across modules, pattern inconsistency, architectural drift, missing shared abstractions
- **Flexible invocation** — natural language scoping with no rigid syntax: `/optimus:refactor backend only`, `/optimus:refactor "focus on auth module"`, or just `/optimus:refactor` for full project
- **Two-phase workflow** — presents a refactoring plan first, then applies only what you approve
- **Test verification** — runs the test suite after applying changes with evidence-based verification; reverts any change that causes failures
- **Conservative by default** — only suggests changes justified by the project's own guidelines
- **Prioritized findings** — Critical/Warning/Suggestion severity with concrete before/after sketches, capped at 8 per run for focused, manageable output
- **Deep mode** — iterative refactoring that loops analysis-apply cycles until zero findings remain (default 8 iterations, configurable up to 10), with explicit user consent and risk warnings
- **Deep harness** — `/optimus:refactor deep harness` launches an external orchestrator with fresh `claude -p` sessions per iteration, eliminating context bloat for large codebases
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
- `/optimus:refactor deep` — iterative refactoring (default 8 iterations)
- `/optimus:refactor deep 8` — deep mode with custom iteration cap
- `/optimus:refactor deep "focus on src/auth"` — deep mode with scope
- `/optimus:refactor deep harness` — deep harness mode (8 iterations, fresh context per iteration)
- `/optimus:refactor deep harness 8 "focus on backend"` — deep harness with options

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
2. Parses arguments for scope, deep mode flag, and iteration cap
3. Activates deep mode if requested (iterative refactoring with user consent)
4. Loads all constraint docs and maps source directories, prioritized by git activity
5. **Launches up to 4 parallel agents** — guideline compliance, testability, duplication/consistency, and code simplification (conditional)
6. Validates findings independently with evidence-based verification
7. Presents findings as a prioritized plan (capped at 8 per run)
8. Applies only user-approved changes, runs tests, reverts any that cause failures

## Deep Mode

By default, the skill caps findings at 8 per run. For exhaustive refactoring, use `deep` to loop automatically:

```
/optimus:refactor deep
/optimus:refactor deep 8        # custom iteration cap (default 8, max 10)
/optimus:refactor deep "backend" # deep mode with scope
```

**Key differences from normal mode:** Deep mode **applies changes automatically** at each iteration — it modifies your code, not just reports findings. It **requires a test command** (from `.claude/CLAUDE.md`) as its safety net; without one, it falls back to normal mode. All changes remain as local modifications — nothing is committed or pushed.

Deep mode runs the same multi-agent analysis-apply cycle repeatedly (default 8, up to 10 iterations) until zero findings remain. Before starting, it warns about credit/time consumption and breakage risk with low test coverage, and asks for explicit confirmation.

**Iteration memory:** On iterations 2+, all agents receive a table of prior findings with their status (fixed/reverted/persistent). This prevents circular fixes — agents focus on NEW issues only and do not undo work from previous iterations.

Each iteration:
1. Launches up to 4 parallel agents with iteration context (same cap: 8 findings per run)
2. Auto-applies all findings (test suite validates; failures trigger per-change bisect)
3. Runs the test suite — reverts any change that causes failures
4. Presents an **iteration report** — a table showing each finding attempted, what changed, why, and its status (fixed/reverted/persistent)
5. Loops back for the next pass, or stops when clean

Deep mode stops when: no findings remain, the iteration cap is reached, or all changes in an iteration fail tests. From iteration 3 onward, a context-accumulation warning appears; if the cap is reached, all continuation options are framed under starting a fresh conversation. All changes remain as local modifications — review the full diff and commit when satisfied. After all iterations complete, a **cumulative report** summarizes every change across all iterations in a single table.

Iterative LLM feedback loops with automated verification consistently improve output quality, with the largest gains in early iterations and diminishing returns in later stages ([LLMLOOP, ICSME 2025](https://valerio-terragni.github.io/assets/pdf/ravi-icsme-2025.pdf)).

### Deep harness mode

For larger codebases or when context accumulation degrades quality, use deep harness mode. It launches a fresh `claude -p` session per iteration (default 8, max 20) — each runs a normal-mode analysis pass with prior findings injected as context.

```bash
# Invoke from within a conversation:
/optimus:refactor deep harness
/optimus:refactor deep harness 10 "focus on backend"

# Or run the script directly:
python scripts/deep-mode-harness.py --skill refactor --scope "src/api"
python scripts/deep-mode-harness.py --skill refactor --max-iterations 10
python scripts/deep-mode-harness.py --skill refactor --timeout 1200 --scope "src/api"
python scripts/deep-mode-harness.py --skill refactor --resume
```

The harness handles test execution, fix bisection, checkpoint commits (with detailed per-fix messages), and termination detection externally. Press Ctrl+C at any time to stop safely; resume later with `--resume`.

**Security note:** By default, each `claude -p` session runs with `--dangerously-skip-permissions` because the harness is headless (no terminal for permission prompts). For a safer alternative, use `--allowed-tools` to restrict sessions to a specific tool whitelist. For OS-level isolation, use [built-in sandboxing](https://code.claude.com/docs/en/sandboxing) (macOS/Linux) or [devcontainers](https://code.claude.com/docs/en/devcontainer).

## Agent Architecture

4 specialized agents run in parallel, each with max 8 findings:

| Agent | Role | Runs when |
|-------|------|-----------|
| 1 — Guideline Compliance | Explicit violations of project docs with exact rule citations | Always |
| 2 — Testability Analyzer | Structural barriers to unit testing — hardcoded deps, tight coupling, global state | Always |
| 3 — Consistency Analyzer | Cross-file duplication, pattern inconsistency, missing abstractions, architectural drift | Always |
| 4 — Code Simplifier | Unnecessary complexity, naming, dead code, pattern violations | Always |

## Relationship to Code-Simplifier Agent

The code-simplifier agent and this skill are complementary — both use `coding-guidelines.md` as their source of truth but operate independently:

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
| Guidelines | General best practices | Project-specific `coding-guidelines.md` |
| Analysis | Single-pass | 4 parallel agents with cross-validation |
| Focus | Per-file simplification | Cross-file patterns, guideline compliance, testability |
| Verification | — | Runs test suite, reverts failures |
| Finding cap | — | 8 per run, prioritized by impact |

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
