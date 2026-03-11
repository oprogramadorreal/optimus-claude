# optimus:code-review

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that reviews local changes (or PRs/MRs) against your project's coding guidelines — using up to 6 parallel review agents for comprehensive coverage. High-signal findings only: bugs, logic errors, security issues, guideline violations.

Well-maintained code has [30%+ fewer AI-introduced defects](https://arxiv.org/abs/2601.02200). `/optimus:init` sets up quality infrastructure with agents that guard new code automatically, and `/optimus:simplify` reviews existing code across the project. `/optimus:code-review` is the inner-loop complement: a focused review of your changes before they enter the repo.

## Features

- **Local-first** — reviews uncommitted changes by default (staged + unstaged + untracked); PR/MR and branch-diff modes available on request
- **Up to 6 parallel agents** — bug detection, security/logic, guideline compliance (×2 for cross-validation), plus code-simplifier and test-guardian when project agents are available
- **Project-aware** — evaluates against your coding-guidelines.md, testing.md, architecture.md, and styling.md
- **High signal only** — bugs, security issues, logic errors, explicit guideline violations; excludes style concerns and subjective suggestions
- **Validation step** — each finding is independently verified (context check, intent check, pre-existing check, cross-agent consensus) using an evidence-based verification protocol before reporting
- **Contradiction resolution** — cross-agent contradictions (e.g., "add more validation" vs. "simplify this validation") are detected and resolved by severity to prevent circular fix loops
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

## When to Run

- **Before committing** — catch issues before they enter the repo
- **Before creating a PR** — self-review your branch changes
- **On a teammate's PR** — review PR changes with project-specific context
- **After major changes** — verify new code follows project patterns

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

## How It Works

1. Gathers local changes (or PR diff) via git commands
2. Loads project docs (CLAUDE.md, coding-guidelines.md, testing.md, etc.) with fallbacks for missing docs
3. Launches up to 6 parallel review agents (bug detection, security/logic, guideline compliance ×2, code-simplifier, test-guardian)
4. Validates each finding using the verification protocol (context check, intent check, pre-existing check, cross-agent consensus — agent findings are treated as claims requiring independent evidence)
5. Consolidates, deduplicates, and presents structured report (capped at 10 findings)
6. Offers actions: fix issues, post PR comment, or skip

## Relationship to Official /code-review

Anthropic's official [code-review](https://github.com/anthropics/claude-code/tree/main/plugins/code-review) plugin and this skill are complementary — both review code with parallel agents but serve different workflows:

| | Official `/code-review:code-review` | `/optimus:code-review` |
|---|---|---|
| Default target | Pull requests | Local uncommitted changes |
| Guidelines | CLAUDE.md only | coding-guidelines.md, testing.md, styling.md, architecture.md |
| Agents | 4 (parallel review agents) | Up to 6 (parallel review agents) |
| Agent types | 2 CLAUDE.md compliance + 1 bug + 1 security | 2 guideline compliance + 1 bug + 1 security + code-simplifier + test-guardian |
| Validation | Sub-agent validation + confidence scoring | Inline validation (context, intent, pre-existing, consensus) |
| Output | Terminal + inline PR comments | Terminal + optional PR comment or fix-in-place |
| Install | `claude plugin add code-review` | Part of optimus plugin |

**How to use both**: `/optimus:code-review` for the inner development loop (before committing), official `/code-review:code-review` for PR review (after pushing). Optimus catches issues against your full project guidelines; the official plugin catches CLAUDE.md violations on the PR diff.

## Relationship to Other Skills

| | `/optimus:code-review` | `/optimus:simplify` |
|---|---|---|
| Scope | Changed files only | Full project or directory |
| Focus | Bugs, security, guideline compliance | Cross-file patterns, duplication, drift |
| Trigger | Before commit/PR | Periodic or after major milestones |
| Action | Report + optional fix | Plan + apply on approval |
| Agents | Up to 6 parallel (bug, security, guidelines ×2, simplifier, test-guardian) | None (direct analysis) |

| | `/optimus:code-review` | `/optimus:commit-message` |
|---|---|---|
| Analyzes | Changed code quality | Changed code intent |
| Output | Findings with fixes | Commit message suggestion |
| Workflow | Run first | Run after review passes |

## Skill Structure

| File | Purpose |
|---|---|
| `SKILL.md` | Skill definition with 6-step review workflow |
| `references/agent-prompts.md` | Prompt templates for parallel review agents |
| *(shared)* `init/references/multi-repo-detection.md` | Multi-repo workspace detection algorithm |
| *(shared)* `init/references/prerequisite-check.md` | Shared prerequisite check with fallbacks |
| *(shared)* `init/references/constraint-doc-loading.md` | Constraint doc loading (single project, monorepo) |
| *(shared)* `pr/references/platform-detection.md` | Platform detection and CLI management |

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Git
- Project initialized with `/optimus:init` (recommended, not required — enables all 6 agents and project-specific guidelines)
- GitHub CLI (`gh`) or GitLab CLI (`glab`) for PR/MR review mode (optional)

## License

[MIT](../../LICENSE)
