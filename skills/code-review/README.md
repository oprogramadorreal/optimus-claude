# optimus:code-review

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that reviews your changes against your project's own standards — the guidelines `/optimus:init` generated, not generic best practices. High-signal findings only: bugs, logic errors, security issues, and guideline violations. Read-only by default; it applies fixes or posts PR/MR comments only with your explicit approval.

## Relationship to the built-in /code-review

Claude Code ships a built-in `/code-review` that checks general code quality on your diff. This skill is its project-standards complement:

| | Built-in `/code-review` | `/optimus:code-review` |
|---|---|---|
| Review criteria | General code quality | Your `coding-guidelines.md`, `testing.md`, `architecture.md`, `styling.md` — and `skill-writing-guidelines.md` for markdown instruction files in skill-authoring projects |
| Default target | Current diff | Local changes; auto-routes to an open PR/MR on a clean, fully-pushed branch |
| Agents | General reviewers | Up to 6 project-aware agents, including guideline compliance run twice for cross-validation |
| Iterative auto-fix | No | Via `/optimus:deep review` |

Use both: the built-in for quick general passes, this skill to enforce your project's rules.

## Features

- **Local-first** — reviews staged + unstaged + untracked changes by default; PR/MR and branch-diff modes on request or by auto-route
- **Up to 6 parallel agents** — correctness & security, guideline compliance (dispatched twice — independent passes reduce false negatives), code simplifier, plus test-guardian (when test infrastructure is documented) and contracts-reviewer (when API/contract files changed)
- **Skill-authoring aware** — in projects with a skill-authoring stack, markdown instruction files under `skills/`, `agents/`, `prompts/`, `commands/`, or `instructions/` are judged by `skill-writing-guidelines.md`, never by code rules
- **Validated findings** — every agent finding is independently verified (context, intent, pre-existing, cross-agent consensus) before it reaches you; only High/Medium confidence survives
- **Change-intent awareness** — recent git history and the PR/MR description soften findings that would undo deliberate work, without ever hard-filtering a real issue
- **Intent-vs-implementation check** — in PR/MR mode, specific claims in the description ("rate-limits requests", "no public API change") are checked against what the diff actually does
- **Bounded output** — deduplicated, contradiction-resolved, capped at 15 findings (plus up to 5 intent mismatches), each with `file:line`, the issue, and a concrete fix
- **GitHub and GitLab** — PR review via `gh`, MR review via `glab`
- **Works without init** — falls back to generic guidelines when project docs are missing (and recommends `/optimus:init`)

## Usage

- `/optimus:code-review` — review local changes; with a clean tree it auto-routes to the open PR/MR (if fully pushed) or the branch diff
- `/optimus:code-review --pr 42` (or `#42`, or a PR URL) — review a specific PR/MR
- `/optimus:code-review --branch` — force the branch diff against the detected base
- `/optimus:code-review src/auth` — restrict the review to a path

## How it works

1. Resolves the review scope: local changes, PR/MR (with the description captured as author intent), or branch diff against the detected base.
2. Loads your project docs — with the skill-writing lens for markdown instruction files and submodules excluded.
3. Launches all applicable agents in parallel, each receiving the changed files and diff hunks.
4. Independently validates every finding against the codebase and git history.
5. Consolidates: dedupes, resolves cross-agent contradictions, assigns severity, caps at 15 findings.
6. Offers actions: fix the issues, post the review as a PR/MR comment, or stop with the report.

## Skill structure

| File | Purpose |
|---|---|
| `SKILL.md` | The 8-step review workflow |
| `agents/` | Agent prompts (`correctness-security`, `guideline-reviewer`, `code-simplifier`, `test-guardian`, `contracts-reviewer`), `shared-constraints.md`, `context-blocks.md` |
| `references/platform-detection.md` | GitHub/GitLab detection and CLI checks |
| `references/default-branch-detection.md` | Base-branch detection fallback chain |

Shared references from other skills: `init/references/{multi-repo-detection,prerequisite-check,constraint-doc-loading,verification-protocol}.md` and the plugin-level `references/harness-mode.md` (used when running inside `/optimus:deep review`).

## Requirements

- Git; GitHub CLI (`gh`) or GitLab CLI (`glab`) for PR/MR mode
- `/optimus:init` recommended (project-specific guidelines and conditional agents depend on its docs), not required
- A test command in `.claude/CLAUDE.md` if you want `/optimus:deep review`

## Installation

This skill is part of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin — see the [main README](../../README.md).

## License

[MIT](../../LICENSE)
