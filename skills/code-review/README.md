# optimus:code-review

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that reviews local changes, an open PR/MR, or a branch diff against your project's coding guidelines using 5 to 7 parallel review agents. High-signal findings only: bugs, logic errors, security issues, guideline violations. For iterative auto-fix in a loop, use [`/optimus:deep review`](../deep/README.md).

## Features

- **Local-first** — reviews uncommitted changes by default; with a clean tree it auto-routes to the open PR/MR (when HEAD is fully pushed) or the branch diff against the detected base
- **5 to 7 parallel agents** — bug detection, security/logic, guideline compliance (x2 for cross-validation), code simplifier, plus test-guardian (when test infrastructure exists) and contracts-reviewer (when API/contract files changed)
- **Project-aware** — evaluates against your `coding-guidelines.md`, `testing.md`, `architecture.md`, `styling.md`; markdown instruction files in skill-authoring projects are judged by `skill-writing-guidelines.md` instead
- **Intent-aware** — in PR/MR mode, agents receive the author's description (with guardrails against bias) and check `## Intent` claims against the implementation; git history protects deliberately introduced code from false positives
- **Validated findings** — every agent finding is independently verified (context, intent, pre-existing, cross-agent consensus, runtime assumptions) before reporting; cross-agent contradictions are resolved by severity
- **Actionable output** — file:line references, confidence, before/after sketches, guideline citations, severity; capped at 15 findings (+5 Intent Mismatch)
- **GitHub and GitLab** — PR review via `gh`, MR review via `glab`; optional review comment posting
- **Safe by default** — read-only; fixes and comments only on explicit approval. Works without `/optimus:init` (generic guidelines fallback), supports multi-repo workspaces, and skips submodules and generated files

## Quick Start

This skill is part of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin. See the [main README](../../README.md) for installation instructions.

## Usage

- `/optimus:code-review` — review local uncommitted changes (clean tree: auto-routes to the open PR/MR or the branch diff)
- `/optimus:code-review --pr 42` or `"review PR #42"` — review a specific PR/MR
- `/optimus:code-review --branch` — force the branch diff against the detected base, skipping the PR auto-route
- `/optimus:code-review "changes since main"` — review against an explicit ref
- `/optimus:code-review src/auth` — scope to a path

## Recommended Workflow

Intent-aware review works best with the implement → commit → pr → review chain:

1. Implement your changes in a conversation.
2. Stay there and run [`/optimus:commit`](../commit/README.md) — it captures the *why* into the commit message.
3. Still in the same conversation, run [`/optimus:pr`](../pr/README.md) — it captures decisions, scope, and non-goals into the PR description.
4. In a fresh conversation, run `/optimus:code-review` — it auto-detects the open PR and reviews the implementation against the description's `## Intent` claims. Intent travels via the PR description, not chat history, keeping the review uncontaminated.

When the PR description is empty, the review proceeds normally and simply skips the intent-vs-implementation check.

Pre-commit self-review also works: run it on local uncommitted changes to catch bugs and guideline violations before committing.

## Example Output

```
## Code Review

### Summary
- Scope: PR #42
- Files reviewed: 5
- Lines changed: +142 / -28
- Findings: 2 (Critical: 1, Warning: 1, Suggestion: 0)
- Docs used: CLAUDE.md, coding-guidelines.md, testing.md
- Agents: bug-detector, security-reviewer, guideline-A, guideline-B, code-simplifier, test-guardian
- Verdict: ISSUES FOUND

### Findings

**1. Missing null check on user lookup result** (Critical — Bug)
- File: src/api/users.ts:47
- Category: Bug
- Issue: getUser(id) can return undefined for deleted users; the result is used without a check
- Current: return user.email;
- Suggested: if (!user) throw new NotFoundError(...); return user.email;

**2. Rate limiting claimed in PR Intent but not implemented** (Warning — Intent Mismatch)
- File: src/routes/auth.ts:23
- Intent claim: "rate-limit reset requests to 3 per hour per email"
- Issue: the new reset-password handler has no rate-limiting middleware or counter
```

You then choose: **Fix issues**, **Post comment** (PR/MR mode), or **Skip**.

## Requirements

- Git; [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- `/optimus:init` recommended (not required) — enables project-specific guidelines and the conditional agents
- GitHub CLI (`gh`) or GitLab CLI (`glab`) for PR/MR mode (optional)
- A test command in `.claude/CLAUDE.md` if you want `/optimus:deep review`

## License

[MIT](../../LICENSE)
