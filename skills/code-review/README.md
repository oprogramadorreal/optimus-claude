# prime:code-review

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that reviews local changes (or PRs) against your project's coding guidelines — using up to 6 parallel review agents for comprehensive coverage. High-signal findings only: bugs, logic errors, security issues, guideline violations.

Well-maintained code has [30%+ fewer AI-introduced defects](https://arxiv.org/abs/2601.02200). `/prime:init` sets up quality infrastructure with agents that guard new code automatically, and `/prime:simplify` reviews existing code across the project. `/prime:code-review` is the inner-loop complement: a focused review of your changes before they enter the repo.

## Features

- **Local-first** — reviews uncommitted changes by default (staged + unstaged + untracked); PR and branch-diff modes available on request
- **Up to 6 parallel agents** — bug detection, security/logic, guideline compliance (×2 for cross-validation), plus code-simplifier and test-guardian when project agents are available
- **Project-aware** — evaluates against your coding-guidelines.md, testing.md, architecture.md, and styling.md
- **High signal only** — bugs, security issues, logic errors, explicit guideline violations; excludes style concerns and subjective suggestions
- **Validation step** — each finding is independently verified (context check, intent check, pre-existing check, cross-agent consensus) before reporting
- **Actionable output** — findings include file:line references, before/after code sketches, guideline citations, and severity levels
- **Works without `/prime:init`** — falls back to generic coding guidelines when project-specific docs are not available

## Quick Start

This skill is part of the [prime](https://github.com/oprogramadorreal/claude-code-prime) plugin. See the [main README](../../README.md) for installation instructions.

## Usage

In Claude Code, use any of these:

- `/prime:code-review` — review local uncommitted changes
- `/prime:code-review` "review PR #42"
- `/prime:code-review` "review changes since main"
- `/prime:code-review` "focus on src/auth"
- "review my changes"
- "code review before I commit"

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
4. Validates each finding (context check, intent check, pre-existing check, cross-agent consensus)
5. Consolidates, deduplicates, and presents structured report (capped at 10 findings)
6. Offers actions: fix issues, post PR comment, or skip

## Relationship to Official /code-review

Anthropic's official [code-review](https://github.com/anthropics/claude-code/tree/main/plugins/code-review) plugin and this skill are complementary — both review code with parallel agents but serve different workflows:

| | Official `/code-review:code-review` | `/prime:code-review` |
|---|---|---|
| Default target | Pull requests | Local uncommitted changes |
| Guidelines | CLAUDE.md only | coding-guidelines.md, testing.md, styling.md, architecture.md |
| Agents | 4 (parallel review agents) | Up to 6 (parallel review agents) |
| Agent types | 2 CLAUDE.md compliance + 1 bug + 1 security | 2 guideline compliance + 1 bug + 1 security + code-simplifier + test-guardian |
| Validation | Sub-agent validation + confidence scoring | Inline validation (context, intent, pre-existing, consensus) |
| Output | Terminal + inline PR comments | Terminal + optional PR comment or fix-in-place |
| Install | `claude plugin add code-review` | Part of prime plugin |

**How to use both**: `/prime:code-review` for the inner development loop (before committing), official `/code-review:code-review` for PR review (after pushing). Prime catches issues against your full project guidelines; the official plugin catches CLAUDE.md violations on the PR diff.

## Relationship to Other Skills

| | `/prime:code-review` | `/prime:simplify` |
|---|---|---|
| Scope | Changed files only | Full project or directory |
| Focus | Bugs, security, guideline compliance | Cross-file patterns, duplication, drift |
| Trigger | Before commit/PR | Periodic or after major milestones |
| Action | Report + optional fix | Plan + apply on approval |
| Agents | Up to 6 parallel (bug, security, guidelines ×2, simplifier, test-guardian) | None (direct analysis) |

| | `/prime:code-review` | `/prime:commit-message` |
|---|---|---|
| Analyzes | Changed code quality | Changed code intent |
| Output | Findings with fixes | Commit message suggestion |
| Workflow | Run first | Run after review passes |

## Skill Structure

| File | Purpose |
|---|---|
| `SKILL.md` | Skill definition with 6-step review workflow |

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Git
- Project primed with `/prime:init` (recommended, not required — enables all 6 agents and project-specific guidelines)
- GitHub CLI (`gh`) for PR review mode (optional)

## License

[MIT](../../LICENSE)
