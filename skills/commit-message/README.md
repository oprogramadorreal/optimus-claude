# bootstrap:commit-message

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that analyzes your local git changes and suggests [conventional commit](https://www.conventionalcommits.org/) messages — without committing anything.

## Features

- Analyzes staged, unstaged, and untracked changes
- Generates messages following the Conventional Commits spec
- Suggests splitting into multiple commits when changes span different concerns
- Read-only — never stages, commits, or modifies files

## Quick Start

This skill is part of the [bootstrap](https://github.com/oprogramadorreal/claude-code-bootstrap) plugin. See the [main README](../../README.md) for installation instructions.

## Usage

In Claude Code, use any of these:

- `/bootstrap:commit-message`
- "suggest a commit message"
- "generate commit message"
- "summarize my changes"

The skill will analyze your local changes and output a suggested commit message in a copyable code block.

## Example

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

## Skill Structure

| File | Purpose |
|---|---|
| `SKILL.md` | Skill definition with step-by-step instructions |

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
- Git

## License

[MIT](../../LICENSE)
