# optimus:commit

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that stages, commits, and optionally pushes your local git changes with a [conventional commit](https://www.conventionalcommits.org/) message — all in one step.

## Features

- Analyzes staged, unstaged, and untracked changes to generate a conventional commit message
- Confirms with the user before committing — shows the message, branch, and file list
- Offers "Commit and push" or "Commit only" — user decides per invocation
- Protected branch handling — detects protected branches and offers to create a feature branch automatically
- Handles untracked files — asks whether to include, exclude, or choose individually
- Supports multi-repo workspaces — detects repos with changes and commits each independently

## Quick Start

This skill is part of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin. See the [main README](../../README.md) for installation instructions.

## Usage

In Claude Code:

- `/optimus:commit`

The skill will analyze your local changes, generate a commit message, and ask you to confirm before committing. You choose whether to also push.

## When to Run

- **After making changes** — commit your work with a well-structured message without manual effort
- **After `/optimus:code-review`** — once fixes pass review, commit and push in one step
- **After `/optimus:simplify`** — commit the simplification changes
- **When you want to push immediately** — choose "Commit and push" to avoid a separate push step

## Example Flow

Given staged changes that add email validation:

```
Branch: feat/signup-validation
Commit message:
  feat(auth): add email format validation to signup form

Files to stage:
  src/auth/validate.ts
  src/auth/__tests__/validate.test.ts

Action: Commit and push / Commit only / Edit message / Cancel
```

After confirming "Commit and push":

```
Committed: a1b2c3d feat(auth): add email format validation to signup form
Pushed to: origin/feat/signup-validation
```

## How It Works

The skill runs `git diff` (staged and unstaged) and `git status` to collect all local changes, then analyzes the diff to generate a [Conventional Commits](https://www.conventionalcommits.org/) message. Before committing, it checks if the permissions hook (`.claude/hooks/restrict-paths.sh`) marks the current branch as protected and, if so, offers to create a feature branch automatically. The user always confirms via `AskUserQuestion` before any changes are made.

## Relationship to Other Skills

| | `/optimus:commit` | `/optimus:commit-message` |
|---|---|---|
| Purpose | Commit (and optionally push) changes | Suggest a commit message |
| Output | Git commit + optional push | Copyable code block |
| Modifies repo | Yes — stages, commits, pushes | No — read-only |
| User confirmation | Always asks before committing | N/A |
| When to use | Ready to commit | Want to preview the message first |

| | `/optimus:commit` | `/optimus:pr` |
|---|---|---|
| Scope | Individual commit(s) | Pull request creation |
| Complement | Commit first, then create PR | Expects changes already committed |
| Workflow | Run `/optimus:commit` first, then `/optimus:pr` | |

**Recommended sequence**: `/optimus:code-review` first (catch issues), then `/optimus:commit` (commit and push), then `/optimus:pr` (create a pull request). Use `/optimus:commit-message` if you only want to preview the message without committing.

## Skill Structure

| File | Purpose |
|---|---|
| `SKILL.md` | Skill definition with step-by-step workflow |
| `references/branch-naming.md` | Branch naming convention (shared with TDD) |
| *(shared)* `commit-message/references/conventional-commit-format.md` | Conventional commit format specification |
| *(shared)* `init/references/multi-repo-detection.md` | Multi-repo workspace detection algorithm |

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Git

## License

[MIT](../../LICENSE)
