# optimus:code-review

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that reviews local changes (or PRs/MRs) against your project's coding guidelines — using 5 to 7 parallel review agents for comprehensive coverage. High-signal findings only: bugs, logic errors, security issues, guideline violations. Supports **deep mode** for iterative auto-fix (in-conversation or via external **deep harness** with fresh context per iteration).

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
- **Deep mode** — iterative review-fix loop (max 8 iterations) with automatic fix application and test verification; catches issues that single-pass review misses due to LLM attention limitations. Each sub-agent surfaces up to 15 distinct findings per pass, and structural-neighbor expansion lets agents catch consistency gaps in sibling files before they leak into later iterations
- **Deep harness** — `/optimus:code-review deep harness` launches an external orchestrator with fresh `claude -p` sessions per iteration, eliminating context bloat for large codebases
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
- `/optimus:code-review deep` — iterative review-fix until clean (max 8 passes)
- `/optimus:code-review deep` "review PR #42" — deep mode on a PR
- `/optimus:code-review deep --branch` — deep mode against the branch diff
- `/optimus:code-review deep harness` — deep harness mode (external, fresh context per iteration)
- `/optimus:code-review deep harness` "focus on src/auth" — deep harness with scope

## When to Run

- **Before committing** — catch issues before they enter the repo
- **Before creating a PR** — self-review your branch changes
- **On a teammate's PR** — review PR changes with project-specific context
- **After major changes** — verify new code follows project patterns
- **For thorough cleanup** — use `deep` mode to catch issues that single-pass review misses

## Recommended Workflow — the implement → commit → pr → code-review chain

This skill produces the strongest intent-aware findings when paired with the **continuation skills** (`/optimus:commit`, `/optimus:pr`) — they capture the implementation intent into commit messages and the PR description, and code-review reads those artifacts to ground its review against the *why*, not just the *what*. See [`references/skill-handoff.md`](../../references/skill-handoff.md) under "Continuation skills" for the rationale.

The canonical sequence:

1. **Implement** your changes in a conversation.
2. **Stay in that conversation** and run [`/optimus:commit`](../commit/README.md) — it captures the *why* into the commit message body.
3. **Still in the same conversation**, run [`/optimus:pr`](../pr/README.md) — it captures decisions, scope, non-goals, and trade-offs into the PR description.
4. **Switch to a fresh conversation** and run `/optimus:code-review` — it auto-detects the open PR and uses the description as author intent context. A fresh conversation keeps the review uncontaminated by the implementation discussion; intent travels via the PR description, not via chat history.

When a PR exists but has no intent context in its description (empty body, or no captured decisions), code-review notes this in the scope summary and the review proceeds without the intent-vs-implementation check.

**Pre-commit self-review (optional):** you can also run `/optimus:code-review` on local uncommitted changes before committing — it catches bugs and guideline violations without needing a PR. The post-PR review remains the canonical intent-vs-implementation check.

## Deep Mode

Deep mode addresses a fundamental limitation of single-pass LLM review: attention saturation on large diffs causes issues to be missed. Running the same review multiple times consistently finds new issues — deep mode automates this iteration.

### How it works

1. Confirms with the user (warns about credit/time cost)
2. Runs the full multi-agent review (same agents as normal mode)
3. Auto-applies all validated fixes (no per-change approval)
4. Runs tests — if failures occur, reverts all fixes and re-applies one at a time, keeping those that pass
5. Presents an **iteration report** — a table showing each finding attempted, what changed, why, and its status (fixed/reverted/persistent)
6. Checks termination: converged, all reverted, no actionable fixes, cap reached, or continues
7. Repeats from step 2 with awareness of prior findings
8. After all iterations, presents a **cumulative report** summarizing every change across all iterations in a single table, followed by the full detailed findings with code snippets

### Key differences from normal mode

| Aspect | Normal mode | Deep mode |
|--------|-------------|-----------|
| Iterations | 1 (single pass) | Up to 8 |
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
- **Diminishing returns** *(harness mode)* — yield has plateaued at ≤1 new finding for two consecutive iterations after iter 3, with no reverted fixes in either window iteration; remaining issues may exist and can be resumed in a fresh conversation via `--resume`
- **Cap reached** — 8 iterations completed (continue in a fresh conversation)

On iterations 3+, a context-accumulation warning notes that output quality may degrade and suggests finishing remaining findings in a fresh conversation.

### Deep harness mode

For larger codebases or when context accumulation degrades quality, use deep harness mode. It launches a fresh `claude -p` session per iteration (default 8, max 20) — each runs a normal-mode analysis pass with prior findings injected as context, giving every iteration a clean context window.

```bash
# Invoke from within a conversation:
/optimus:code-review deep harness
/optimus:code-review deep harness "focus on src/auth"

# Or run the script directly:
python scripts/deep-mode-harness/main.py --skill code-review
python scripts/deep-mode-harness/main.py --skill code-review --scope "src/auth" --max-iterations 10
python scripts/deep-mode-harness/main.py --skill code-review --timeout 1200
python scripts/deep-mode-harness/main.py --skill code-review --resume
```

The harness handles test execution, fix bisection, checkpoint commits (with detailed per-fix messages), and termination detection externally — the skill only needs to analyze and apply fixes in a single pass per session. Press Ctrl+C at any time to stop safely; resume later with `--resume`.

**Security note:** By default, each `claude -p` session runs with `--dangerously-skip-permissions` because the harness is headless (no terminal for permission prompts). For a safer alternative, use `--allowed-tools` to restrict sessions to a specific tool whitelist. For OS-level isolation, use [built-in sandboxing](https://code.claude.com/docs/en/sandboxing) (macOS/Linux) or [devcontainers](https://code.claude.com/docs/en/devcontainer).

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
- Confidence: High
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
2. Loads project docs (CLAUDE.md, coding-guidelines.md, skill-writing-guidelines.md (if present), testing.md, etc.) with fallbacks for missing docs. In skill-authoring projects, the shared `constraint-doc-loading.md` reference automatically routes markdown instruction files through the skill-writing lens.
3. Activates deep mode if requested (requires test command, confirms with user)
4. Launches 5 to 7 parallel review agents (bug detection, security/logic, guideline compliance x2, code-simplifier, test-guardian, contracts-reviewer)
5. Validates each finding using the verification protocol (context check, intent check, change-intent awareness, PR/MR context, pre-existing check, cross-agent consensus, runtime assumption check)
6. Consolidates, deduplicates, and presents structured report (capped at 15 findings)
7. Offers actions: fix issues, post PR comment, or skip (normal mode)
8. In deep mode: auto-applies fixes, runs tests, reverts failures via bisect, presents per-iteration report tables, repeats up to 8 iterations, then presents a cumulative summary table and detailed consolidated report

## Relationship to Official /code-review

Anthropic's official [code-review](https://github.com/anthropics/claude-code/tree/main/plugins/code-review) plugin and this skill are complementary — both review code with parallel agents but serve different workflows:

| | Official `/code-review:code-review` | `/optimus:code-review` |
|---|---|---|
| Default target | Pull requests | Local uncommitted changes |
| Guidelines | CLAUDE.md only | coding-guidelines.md, skill-writing-guidelines.md (for skill-authoring projects), testing.md, styling.md, architecture.md |
| Agents | 4 (parallel review agents) | 5 to 7 (parallel review agents) |
| Agent types | 2 CLAUDE.md compliance + 1 bug + 1 security | 2 guideline compliance + 1 bug + 1 security + code-simplifier + test-guardian (conditional) + contracts-reviewer (conditional) |
| Validation | Sub-agent validation + confidence scoring | Inline validation (context, intent, change-intent, PR/MR context, pre-existing, consensus, runtime assumption check) |
| Deep mode | No | Yes — iterative auto-fix (max 8 iterations) |
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
- Test command in `.claude/CLAUDE.md` for deep mode (required)

## License

[MIT](../../LICENSE)
