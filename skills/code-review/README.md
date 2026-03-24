# optimus:code-review

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that reviews local changes (or PRs/MRs) against your project's coding guidelines — using up to 6 parallel review agents for comprehensive coverage. High-signal findings only: bugs, logic errors, security issues, guideline violations. Supports a **deep mode** for iterative auto-fix until zero findings remain.

Well-maintained code has [30%+ fewer AI-introduced defects](https://arxiv.org/abs/2601.02200). `/optimus:init` sets up quality infrastructure with agents that guard new code automatically, and `/optimus:refactor` restructures existing code across the project. `/optimus:code-review` is the inner-loop complement: a focused review of your changes before they enter the repo.

## Features

- **Local-first** — reviews uncommitted changes by default (staged + unstaged + untracked); PR/MR and branch-diff modes available on request
- **Up to 6 parallel agents** — bug detection, security/logic, guideline compliance (x2 for cross-validation), plus code-simplifier and test-guardian when project agents are available
- **Project-aware** — evaluates against your coding-guidelines.md, testing.md, architecture.md, and styling.md
- **High signal only** — bugs, security issues, logic errors, explicit guideline violations; excludes style concerns and subjective suggestions
- **Change-intent awareness** — checks recent git history and PR/MR descriptions to avoid flagging code that was deliberately introduced (e.g., a null check added for a bug fix), reducing false positives
- **PR/MR context awareness** — in PR/MR mode, agents receive the author's description as an intent signal (with explicit guardrails against bias) so they understand the "why" behind changes without suppressing genuine findings
- **Validation step** — each finding is independently verified (context check, intent check, pre-existing check, cross-agent consensus, runtime assumption check) using an evidence-based verification protocol before reporting
- **Contradiction resolution** — cross-agent contradictions (e.g., "add more validation" vs. "simplify this validation") are detected and resolved by severity to prevent circular fix loops
- **Deep mode** — iterative review-fix loop (max 5 iterations) with automatic fix application and test verification; catches issues that single-pass review misses due to LLM attention limitations
- **Actionable output** — findings include file:line references, confidence level (High/Medium), before/after code sketches, guideline citations, and severity levels
- **Works without `/optimus:init`** — falls back to generic coding guidelines when project-specific docs are not available
- **Multi-repo workspace support** — resolves per-repo documentation when opened from a workspace root containing multiple git repos
- **GitLab support** — PR/MR review via `glab` CLI alongside GitHub `gh` CLI
- **Submodule exclusion** — automatically skips files inside git submodules
- **Generated file exclusion** — skips machine-generated files (Dart build_runner output, Visual Studio Designer files, database migration directories)

## Quick Start

This skill is part of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin. See the [main README](../../README.md) for installation instructions.

## Usage

In Claude Code, use any of these:

- `/optimus:code-review` — review local uncommitted changes
- `/optimus:code-review` "review PR #42"
- `/optimus:code-review` "review changes since main"
- `/optimus:code-review` "focus on src/auth"
- `/optimus:code-review deep` — iterative review-fix until clean (max 5 passes)
- `/optimus:code-review deep` "review PR #42" — deep mode on a PR

## When to Run

- **Before committing** — catch issues before they enter the repo
- **Before creating a PR** — self-review your branch changes
- **On a teammate's PR** — review PR changes with project-specific context
- **After major changes** — verify new code follows project patterns
- **For thorough cleanup** — use `deep` mode to catch issues that single-pass review misses

## Deep Mode

Deep mode addresses a fundamental limitation of single-pass LLM review: attention saturation on large diffs causes issues to be missed. Running the same review multiple times consistently finds new issues — deep mode automates this iteration.

### How it works

1. Confirms with the user (warns about credit/time cost)
2. Runs the full multi-agent review (same 6 agents as normal mode)
3. Auto-applies all validated fixes (no per-change approval)
4. Runs tests — if failures occur, reverts all fixes and re-applies one at a time, keeping those that pass
5. Presents an **iteration report** — a table showing each finding attempted, what changed, why, and its status (fixed/reverted/persistent)
6. Checks termination: converged (zero findings), all reverted, cap reached (5), or continues
7. Repeats from step 2 with awareness of prior findings
8. After all iterations, presents a **cumulative report** summarizing every change across all iterations in a single table, followed by the full detailed findings with code snippets

### Key differences from normal mode

| Aspect | Normal mode | Deep mode |
|--------|-------------|-----------|
| Iterations | 1 (single pass) | Up to 5 |
| Fix approval | User chooses (Fix / Post / Skip) | Automatic (confirmed upfront) |
| Test verification | After user-approved fixes | After every iteration |
| Failed fixes | N/A | Reverted individually via bisect |
| Output | Immediate report | Per-iteration report tables + cumulative summary table + detailed consolidated report |
| Requirement | None | Test command in CLAUDE.md |

### Iteration context

On iterations 2+, each agent receives a table of prior findings with their status (fixed / reverted / persistent). This prevents re-flagging code that was intentionally modified by prior fixes and focuses agents on genuinely new issues.

### Stop conditions

- **Convergence** — zero new findings (code is clean)
- **All reverted** — every fix in an iteration caused test failures
- **No actionable fixes** — findings exist but lack concrete code edits
- **Cap reached** — 5 iterations completed (continue in a fresh conversation)

On iterations 3+, a context-accumulation warning notes that output quality may degrade and suggests finishing remaining findings in a fresh conversation.

### Research context

Iterative LLM feedback loops with automated verification (tests, static analysis) consistently improve output quality, with the largest gains in early iterations and diminishing returns in later stages ([LLMLOOP, ICSME 2025](https://valerio-terragni.github.io/assets/pdf/ravi-icsme-2025.pdf)).

## Example Output

The skill presents a structured review report:

```
## Code Review

### Summary
- Scope: Local changes
- Files reviewed: 5
- Lines changed: +142 / -28
- Findings: 3 (Critical: 1, Warning: 1, Suggestion: 1)
- Docs used: CLAUDE.md, coding-guidelines.md, testing.md
- Agents: bug-detector, security-reviewer, guideline-A, guideline-B, code-simplifier, test-guardian
- Verdict: ISSUES FOUND

### Findings

**1. Missing null check on user lookup result** (Critical — Bug)
- File: src/api/users.ts:47
- Category: Bug
- Guideline: General: bug
- Issue: `getUser(id)` can return undefined when user is deleted, but the result is
  used without a null check on line 48
- Current:
  const user = await getUser(id);
  return user.email;
- Suggested:
  const user = await getUser(id);
  if (!user) throw new NotFoundError(`User ${id} not found`);
  return user.email;

**2. API handler missing input validation** (Warning — Guideline Violation)
- File: src/api/orders.ts:23
- Category: Guideline Violation
- Guideline: coding-guidelines.md > "Validate at system boundaries"
- Issue: POST /orders accepts orderId from request body without validation
- Current:
  const { orderId } = req.body;
  await processOrder(orderId);
- Suggested:
  const { orderId } = req.body;
  if (!orderId || typeof orderId !== 'string') throw new BadRequestError('Invalid orderId');
  await processOrder(orderId);

**3. New calculateDiscount function has no test** (Suggestion — Test Gap)
- File: src/pricing/discount.ts:calculateDiscount
- Category: Test Coverage Gap
- What to test: Edge cases for zero amount, negative values, expired coupons
- Test location: src/pricing/__tests__/discount.test.ts
```

You then choose: **Fix issues**, **Post comment** (PR mode), or **Skip**.

In deep mode, each iteration presents a structured report table:

```
#### Iteration 1 — Report

| # | File | What Changed | Reason | Guideline / Category | Status |
|---|------|-------------|--------|---------------------|--------|
| 1 | src/api/users.ts:47 | Added null check | getUser() can return undefined | General: bug / Bug | fixed |
| 2 | src/api/orders.ts:23 | Added input validation | Request body used without validation | coding-guidelines.md > "Validate at boundaries" / Guideline Violation | reverted — test failure |
```

After all iterations, a cumulative summary table covers every change:

```
## Code Review — Deep Mode Cumulative Report

**Summary:**
- Total iterations: 3
- Total findings fixed: 8
- Total findings reverted (test failures): 1
- Total findings persistent (fix failed): 0
- Final test status: pass

**All Changes:**

| # | Iter | File | What Changed | Reason | Guideline / Category | Status |
|---|------|------|-------------|--------|---------------------|--------|
| 1 | 1 | src/api/users.ts:47 | Added null check | getUser() can return undefined | General: bug / Bug | fixed |
| 2 | 1 | src/api/orders.ts:23 | Added input validation | Request body used without validation | coding-guidelines.md > "Validate at boundaries" / Guideline Violation | reverted — test failure |
| ... | ... | ... | ... | ... | ... | ... |
```

This is followed by the full detailed findings with code snippets (same format as normal mode output, covering all iterations).

## How It Works

1. Gathers local changes (or PR diff) via git commands; in PR/MR mode, captures the author's description for intent context
2. Loads project docs (CLAUDE.md, coding-guidelines.md, testing.md, etc.) with fallbacks for missing docs
3. Activates deep mode if requested (requires test command, confirms with user)
4. Launches up to 6 parallel review agents (bug detection, security/logic, guideline compliance x2, code-simplifier, test-guardian)
5. Validates each finding using the verification protocol (context check, intent check, change-intent awareness, PR/MR context, pre-existing check, cross-agent consensus, runtime assumption check)
6. Consolidates, deduplicates, and presents structured report (capped at 15 findings)
7. Offers actions: fix issues, post PR comment, or skip (normal mode)
8. In deep mode: auto-applies fixes, runs tests, reverts failures via bisect, presents per-iteration report tables, repeats up to 5 iterations, then presents a cumulative summary table and detailed consolidated report

## Relationship to Official /code-review

Anthropic's official [code-review](https://github.com/anthropics/claude-code/tree/main/plugins/code-review) plugin and this skill are complementary — both review code with parallel agents but serve different workflows:

| | Official `/code-review:code-review` | `/optimus:code-review` |
|---|---|---|
| Default target | Pull requests | Local uncommitted changes |
| Guidelines | CLAUDE.md only | coding-guidelines.md, testing.md, styling.md, architecture.md |
| Agents | 4 (parallel review agents) | Up to 6 (parallel review agents) |
| Agent types | 2 CLAUDE.md compliance + 1 bug + 1 security | 2 guideline compliance + 1 bug + 1 security + code-simplifier + test-guardian |
| Validation | Sub-agent validation + confidence scoring | Inline validation (context, intent, change-intent, PR/MR context, pre-existing, consensus, runtime assumption check) |
| Deep mode | No | Yes — iterative auto-fix (max 5 iterations) |
| Output | Terminal + inline PR comments | Terminal + optional PR comment or fix-in-place |
| Install | `claude plugin add code-review` | Part of optimus plugin |

**How to use both**: `/optimus:code-review` for the inner development loop (before committing), official `/code-review:code-review` for PR review (after pushing). Optimus catches issues against your full project guidelines; the official plugin catches CLAUDE.md violations on the PR diff.

## Relationship to Other Skills

| | `/optimus:code-review` | `/optimus:refactor` |
|---|---|---|
| Scope | Changed files only | Full project or directory |
| Focus | Bugs, security, guideline compliance | Guideline compliance, testability, duplication, drift |
| Trigger | Before commit/PR | Periodic or before /optimus:unit-test |
| Action | Report + optional fix | Plan + apply on approval |
| Deep mode | Yes — iterative review-fix loop | Yes — iterative cleanup loop |
| Agents | Up to 6 parallel (bug, security, guidelines x2, simplifier, test-guardian) | Up to 4 parallel (guideline compliance, testability, duplication/consistency, code simplifier) |

| | `/optimus:code-review` | `/optimus:commit-message` |
|---|---|---|
| Analyzes | Changed code quality | Changed code intent |
| Output | Findings with fixes | Commit message suggestion |
| Workflow | Run first | Run after review passes |

## Skill Structure

| File | Purpose |
|---|---|
| `SKILL.md` | Skill definition with 8-step review workflow |
| `references/agents/` | Individual agent prompt files, shared constraints, and context blocks for parallel review agents |
| *(shared)* `init/references/multi-repo-detection.md` | Multi-repo workspace detection algorithm |
| *(shared)* `init/references/prerequisite-check.md` | Shared prerequisite check with fallbacks |
| *(shared)* `init/references/constraint-doc-loading.md` | Constraint doc loading (single project, monorepo) |
| *(shared)* `pr/references/platform-detection.md` | Platform detection and CLI management |
| *(shared)* `pr/references/default-branch-detection.md` | Default branch detection fallback |

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Git
- Project initialized with `/optimus:init` (recommended, not required — enables all 6 agents and project-specific guidelines)
- GitHub CLI (`gh`) or GitLab CLI (`glab`) for PR/MR review mode (optional)
- Test command in `.claude/CLAUDE.md` for deep mode (required)

## License

[MIT](../../LICENSE)
