# optimus:branch

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that creates and switches to a new, conventionally named branch — deriving a meaningful name from an inline description, conversation context, or local git diffs. All local changes are preserved. Never commits or pushes.

Two common use cases:

1. **In-progress work** — you have uncommitted changes on main/develop and want to move them to a properly named branch before committing. All staged, unstaged, and untracked files are preserved exactly as they are.
2. **Starting fresh** — you are on a clean branch and want to create a new branch before starting work (e.g., `/optimus:branch "add user authentication"`).

Branch names are meaningful context. A well-named branch tells collaborators, CI systems, and your future self what the work is about before reading a single line of code. This skill automates the naming so you get consistent, descriptive branches without thinking about it.

## Features

- **Context-aware naming** — derives the branch name from inline descriptions, conversation context, or git diffs (in that priority order)
- **Conventional branch format** — follows `<type>/<slugified-description>` convention (feat, fix, refactor, docs, test, chore, perf, style)
- **Fast and safe** — no commits, no pushes, no staging, no file modifications. All local changes are preserved on the new branch
- **Smart type detection** — infers the branch type from keywords in context or the nature of changes (new files → feat, modifications → fix/refactor, test-only → test)
- **Collision handling** — if a branch name already exists, appends a numeric suffix automatically
- **Multi-repo workspace support** — detects which repo has changes and targets it; asks if multiple repos have changes

## Quick Start

This skill is part of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin. See the [main README](../../README.md) for installation instructions.

## Usage

In Claude Code, use any of these:

- `/optimus:branch` — analyzes conversation context or git diffs to derive the branch name
- `/optimus:branch "fix login timeout"` — uses the provided description directly
- `/optimus:branch "add user authentication endpoint"` — explicit description for precise naming

### Examples

**Starting fresh (no local changes, inline description):**

```
> /optimus:branch "add user authentication"

## Branch

Created `feat/add-user-authentication` from `main`.
```

**Moving in-progress work (inline description):**

```
> /optimus:branch "fix login timeout"

## Branch

Created `fix/login-timeout` from `main`.
Local changes preserved (nothing committed or pushed).
```

**From conversation context:**

```
> I need to add a password reset endpoint to the auth module
> [... discussion about the feature ...]
> /optimus:branch

## Branch

Created `feat/add-password-reset-endpoint` from `main`.
Local changes preserved (nothing committed or pushed).
```

**From git diffs (no conversation context):**

```
> /optimus:branch

[Analyzes git diff: modified files in src/auth/, new test file for login validation]

## Branch

Created `fix/auth-login-validation` from `develop`.
Local changes preserved (nothing committed or pushed).
```

**When no context is available:**

```
> /optimus:branch

Could not determine a meaningful branch name from the conversation or local changes.
Provide a description, e.g., `/optimus:branch "add user authentication"`
```

## When to Use

- **Moving uncommitted work** — you made changes on main/develop and want to move them to a properly named branch
- **Starting a new task** — you are on a clean main/develop and want to create a branch before beginning work
- **After discussing a task** — the conversation has enough context to auto-derive a meaningful name
- **Quick branch creation** — faster than thinking up a name and typing `git checkout -b`

## When NOT to Use

- **Starting TDD** — use `/optimus:tdd` instead, which creates its own branch as part of the TDD workflow
- **Committing** — use `/optimus:commit`, which can create a feature branch from a protected branch automatically
- **Need a worktree** — use `/optimus:worktree` for isolated parallel development

## Relationship to Other Skills

| | `/optimus:branch` | `/optimus:commit` |
|---|---|---|
| Branch creation | Always creates a new branch | Only creates a branch if on a protected branch |
| Commits | Never | Stages, commits, and optionally pushes |
| Primary use | Move work to a named branch | Commit finished work |

| | `/optimus:branch` | `/optimus:tdd` |
|---|---|---|
| Branch creation | Creates branch and stops | Creates branch as part of TDD workflow |
| Scope | Just the branch | Full Red-Green-Refactor cycles with commits and PR |
| Speed | Instant | Full development session |

| | `/optimus:branch` | `/optimus:worktree` |
|---|---|---|
| Creates branch | Yes | Yes (inside a worktree) |
| Isolation | No — works in current directory | Yes — separate directory with own project setup |
| Use case | Move changes to a branch | Parallel development in isolation |

## Skill Structure

| File | Purpose |
|---|---|
| `SKILL.md` | Skill definition with 5-step workflow |
| *(shared)* `init/references/multi-repo-detection.md` | Multi-repo workspace detection algorithm |
| *(shared)* `commit/references/branch-naming.md` | Branch naming convention |

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Git

## License

[MIT](../../LICENSE)
