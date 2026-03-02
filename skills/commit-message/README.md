# prime:commit-message

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that analyzes your local git changes and suggests [conventional commit](https://www.conventionalcommits.org/) messages — without committing anything.

Consistent commit messages improve repository navigability for both humans and LLMs. Conventional Commits provide a structured format that tools can parse programmatically — changelogs, release notes, and semantic versioning all benefit from uniform commit types and scopes.

## Features

- Analyzes staged, unstaged, and untracked changes
- Generates messages following the Conventional Commits spec
- Suggests splitting into multiple commits when changes span different concerns
- Read-only — never stages, commits, or modifies files

## Quick Start

This skill is part of the [prime](https://github.com/oprogramadorreal/claude-code-prime) plugin. See the [main README](../../README.md) for installation instructions.

## Usage

In Claude Code, use any of these:

- `/prime:commit-message`
- "suggest a commit message"
- "generate commit message"
- "summarize my changes"

The skill will analyze your local changes and output a suggested commit message in a copyable code block.

## When to Run

- **Before committing** — get a well-structured message instead of writing one manually
- **After `/prime:code-review`** — once your changes pass review, generate the commit message
- **When changes span multiple concerns** — the skill suggests how to split into separate commits
- **Quick message for small changes** — faster than crafting a conventional commit message by hand

## Example Output

Given staged changes that add email validation and update related tests:

```
feat(auth): add email format validation to signup form

Validates email format before API call to prevent invalid submissions.
Includes unit tests for common invalid formats (missing @, double dots,
trailing dots).
```

When changes span multiple concerns, the skill suggests separate commits with staging instructions:

```
# Commit 1 — stage with: git add src/auth/validate.ts src/auth/__tests__/validate.test.ts
feat(auth): add email format validation

# Commit 2 — stage with: git add src/components/SignupForm.tsx
refactor(signup): extract form field components
```

## How It Works

The skill runs `git diff` (staged and unstaged) and `git status` to collect all local changes, then analyzes the diff to infer intent, scope, and type. It follows the [Conventional Commits](https://www.conventionalcommits.org/) specification for the output format. No files are read beyond what git provides — it operates entirely on diff output.

## Relationship to Other Skills

| | `/prime:commit-message` | `/prime:code-review` |
|---|---|---|
| Analyzes | Changed code intent | Changed code quality |
| Output | Commit message suggestion | Findings with fixes |
| Workflow | Run after review passes | Run before committing |
| Scope | All local changes | All local changes (or PR) |

**Recommended sequence**: `/prime:code-review` first (catch issues), then `/prime:commit-message` (describe what you did).

## Skill Structure

| File | Purpose |
|---|---|
| `SKILL.md` | Skill definition with step-by-step instructions |

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Git

## License

[MIT](../../LICENSE)
