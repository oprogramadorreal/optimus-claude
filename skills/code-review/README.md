# optimus:code-review

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that reviews local changes (or PRs/MRs) against your project's coding guidelines — using 5 to 7 parallel review agents for comprehensive coverage. High-signal findings only: bugs, logic errors, security issues, guideline violations. For iterative auto-fix in a loop, use [`/optimus:code-review-deep`](../code-review-deep/README.md).

Well-maintained code has [30%+ fewer AI-introduced defects](https://arxiv.org/abs/2601.02200). `/optimus:init` sets up quality infrastructure with agents that guard new code automatically, and `/optimus:refactor` restructures existing code across the project. `/optimus:code-review` is the inner-loop complement: a focused review of your changes before they enter the repo.

## Features

- **Local-first** — reviews uncommitted changes by default (staged + unstaged + untracked); PR/MR and branch diff modes available on request
- **5 to 7 parallel agents** — bug detection, security/logic, guideline compliance (x2 for cross-validation), code-simplifier, test-guardian (when test infrastructure is detected), and contracts-reviewer (when API/contract files are changed)
- **Project-aware** — evaluates against your coding-guidelines.md, testing.md, architecture.md, and styling.md. For projects with a skill-authoring stack, markdown instruction files under `skills/`, `agents/`, `prompts/`, `commands/`, or `instructions/` are evaluated against `skill-writing-guidelines.md` instead of `coding-guidelines.md` — both lenses apply side-by-side on mixed changes, each to its own files.
- **High signal only** — bugs, security issues, logic errors, explicit guideline violations; excludes style concerns and subjective suggestions
- **Change-intent awareness** — checks recent git history and PR/MR descriptions to avoid flagging code that was deliberately introduced (e.g., a null check added for a bug fix), reducing false positives
- **PR/MR context awareness** — in PR/MR mode, agents receive the author's description as an intent signal (with explicit guardrails against bias) so they understand the "why" behind changes without suppressing genuine findings
- **Validation step** — each finding is independently verified (context check, intent check, pre-existing check, cross-agent consensus, runtime assumption check) using an evidence-based verification protocol before reporting
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

- `/optimus:code-review` — review local uncommitted changes (with no local changes, auto-routes to an open PR/MR when HEAD is fully pushed; otherwise reviews the branch diff)
- `/optimus:code-review` "review PR #42"
- `/optimus:code-review` "review changes since main"
- `/optimus:code-review` "focus on src/auth"
- `/optimus:code-review --branch` — force branch diff against the detected base, skipping PR auto-route

For iterative auto-fix in a loop, see [`/optimus:code-review-deep`](../code-review-deep/README.md).

## When to Run

- **Before committing** — catch issues before they enter the repo
- **Before creating a PR** — self-review your branch changes
- **On a teammate's PR** — review PR changes with project-specific context
- **After major changes** — verify new code follows project patterns
- **For thorough cleanup** — use [`/optimus:code-review-deep`](../code-review-deep/README.md) to catch issues that single-pass review misses

## Recommended Workflow — the implement → commit → pr → code-review chain

This skill produces the strongest intent-aware findings when paired with the **continuation skills** (`/optimus:commit`, `/optimus:pr`) — they capture the implementation context into commit messages and the PR description, and code-review reads those artifacts to ground its review against the *why*, not just the *what*. See [`references/skill-handoff.md`](../../references/skill-handoff.md) under "Continuation skills" for the rationale.

The canonical sequence:

1. **Implement** your changes in a conversation.
2. **Stay in that conversation** and run [`/optimus:commit`](../commit/README.md) — it captures the *why* into the commit message body.
3. **Still in the same conversation**, run [`/optimus:pr`](../pr/README.md) — it captures decisions, scope, non-goals, and trade-offs into the PR description.
4. **Switch to a fresh conversation** and run `/optimus:code-review` — it auto-detects the open PR and uses the description as author intent context. A fresh conversation keeps the review uncontaminated by the implementation discussion; intent travels via the PR description, not via chat history.

When a PR exists but has no intent context in its description (empty body, or no captured decisions), code-review notes this in the scope summary and the review proceeds without the intent-vs-implementation check.

**Pre-commit self-review (optional):** you can also run `/optimus:code-review` on local uncommitted changes before committing — it catches bugs and guideline violations without needing a PR. The post-PR review remains the canonical intent-vs-implementation check.

## Iterative Auto-Fix

For thorough cleanup, use the dedicated orchestrator skill [`/optimus:code-review-deep`](../code-review-deep/README.md) instead of running this skill repeatedly. Each iteration runs in a fresh subagent context, fixes are applied automatically, tests run after every iteration, and failed fixes are reverted via bisection. Termination triggers include convergence (no new findings), no-actionable-fixes, all-reverted, iteration cap, and diminishing-returns soft-exit. See its README for usage and configuration.

### Research context

Iterative LLM feedback loops with automated verification (tests, static analysis) consistently improve output quality, with the largest gains in early iterations and diminishing returns in later stages ([LLMLOOP, ICSME 2025](https://valerio-terragni.github.io/assets/pdf/ravi-icsme-2025.pdf)).

## Example Output

The skill presents a structured review report:

```
## Code Review

### Summary
- Scope: PR #42
- Files reviewed: 5
- Lines changed: +142 / -28
- Findings: 4 (Critical: 1, Warning: 2, Suggestion: 1)
- Docs used: CLAUDE.md, coding-guidelines.md, testing.md (plus skill-writing-guidelines.md in skill-authoring projects)
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

**4. Rate limiting claimed in PR Intent but not implemented** (Warning — Intent Mismatch)
- File: src/routes/auth.ts:23
- Category: Intent Mismatch
- Guideline: Intent (see Intent claim)
- Intent claim: PR description `## Intent` says "rate-limit reset requests to 3 per hour per email"
- Issue: The new POST /auth/reset-password handler adds validation and email send but no rate-limiting middleware or counter. The Intent claim has no supporting code.
- Current:
  router.post('/reset-password', validate, async (req, res) => {
    await sendReset(req.body.email);
    res.status(200).json({ ok: true });
  });
- Suggested:
  router.post('/reset-password', validate, rateLimit({ max: 3, windowMs: 3600_000 }), async (req, res) => {
    await sendReset(req.body.email);
    res.status(200).json({ ok: true });
  });
```

You then choose: **Fix issues**, **Post comment** (PR mode), or **Skip**.

For iterative auto-fix output (per-iteration report tables + cumulative summary), see [`/optimus:code-review-deep`](../code-review-deep/README.md).

## How It Works

1. Gathers local changes (or PR diff) via git commands; in PR/MR mode, captures the author's description for intent context
2. Loads project docs (CLAUDE.md, coding-guidelines.md, skill-writing-guidelines.md (if present), testing.md, etc.) with fallbacks for missing docs. In skill-authoring projects, the shared `constraint-doc-loading.md` reference automatically routes markdown instruction files through the skill-writing lens.
3. Launches 5 to 7 parallel review agents (bug detection, security/logic, guideline compliance x2, code-simplifier, test-guardian, contracts-reviewer)
4. Validates each finding using the verification protocol (context check, intent check, change-intent awareness, PR/MR context, pre-existing check, cross-agent consensus, runtime assumption check)
5. Consolidates, deduplicates, and presents structured report (capped at 15 findings)
6. Offers actions: fix issues, post PR comment, or skip

## Relationship to Official /code-review

Anthropic's official [code-review](https://github.com/anthropics/claude-code/tree/main/plugins/code-review) plugin and this skill are complementary — both review code with parallel agents but serve different workflows:

| | Official `/code-review:code-review` | `/optimus:code-review` |
|---|---|---|
| Default target | Pull requests | Local uncommitted changes |
| Guidelines | CLAUDE.md only | coding-guidelines.md, skill-writing-guidelines.md (for skill-authoring projects), testing.md, styling.md, architecture.md |
| Agents | 4 (parallel review agents) | 5 to 7 (parallel review agents) |
| Agent types | 2 CLAUDE.md compliance + 1 bug + 1 security | 2 guideline compliance + 1 bug + 1 security + code-simplifier + test-guardian (conditional) + contracts-reviewer (conditional) |
| Validation | Sub-agent validation + confidence scoring | Inline validation (context, intent, change-intent, PR/MR context, pre-existing, consensus, runtime assumption check) |
| Iterative auto-fix | No | Yes — via the companion `/optimus:code-review-deep` skill (default 8, hard cap 20) |
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
| Iterative auto-fix orchestrator | `/optimus:code-review-deep` | `/optimus:refactor-deep` |
| Agents | 5 to 7 parallel (bug, security, guidelines x2, simplifier, test-guardian, contracts-reviewer) | 4 parallel (guideline compliance, testability, duplication/consistency, code simplifier) |
| Focus modes | N/A | `testability` or `guidelines` keyword adjusts finding-cap priority |

| | `/optimus:code-review` | `/optimus:commit-message` |
|---|---|---|
| Analyzes | Changed code quality | Changed code intent |
| Output | Findings with fixes | Commit message suggestion |
| Workflow | Run first | Run after review passes |

## Skill Structure

| File | Purpose |
|---|---|
| `SKILL.md` | Skill definition with 8-step review workflow |
| `agents/` | Individual agent prompt files for parallel review agents, shared constraints, and context blocks |
| *(shared)* `init/references/multi-repo-detection.md` | Multi-repo workspace detection algorithm |
| *(shared)* `init/references/prerequisite-check.md` | Shared prerequisite check with fallbacks |
| *(shared)* `init/references/constraint-doc-loading.md` | Constraint doc loading (single project, monorepo) |
| *(shared)* `pr/references/platform-detection.md` | Platform detection and CLI management |
| *(shared)* `pr/references/default-branch-detection.md` | Default branch detection fallback |
| *(shared)* `references/harness-mode.md` | Harness mode single-iteration execution protocol |

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Git
- Project initialized with `/optimus:init` (recommended, not required — enables project-specific guidelines and all conditional agents that depend on project docs)
- GitHub CLI (`gh`) or GitLab CLI (`glab`) for PR/MR review mode (optional)
- Test command in `.claude/CLAUDE.md` if you want to use `/optimus:code-review-deep`

## License

[MIT](../../LICENSE)
