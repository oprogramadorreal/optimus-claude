# optimus:worktree

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that creates a git worktree for isolated parallel development — a new branch in a separate directory (`.worktrees/`) with project setup and a test baseline. The main workspace stays on its original branch, so each worktree can host an independent Claude Code session.

## Features

- **Isolated parallel development** — each worktree is a separate directory with its own branch
- **Automatic project setup** — detects and runs the project's setup command (npm install, pip install, etc.) inside the new worktree
- **Test baseline** — runs the test suite in the worktree; pre-existing failures are reported, never blocking
- **Conventional branch naming** — `<type>/<slugified-description>`, consistent with other optimus skills
- **Recursive worktree guard** — refuses to create a worktree from inside another worktree
- **Multi-repo workspace support** — targets a specific repo in multi-repo setups

VSCode 1.103+ discovers worktrees natively: open one from the Source Control panel (right-click → "Open Worktree in New Window") or with `code .worktrees/<worktree-dir>`.

## Quick Start

This skill is part of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin. See the [main README](../../README.md) for installation instructions.

## Usage

- `/optimus:worktree` — asks what you will work on, then creates the worktree
- `/optimus:worktree "fix login timeout"` — uses the provided description directly

Example:

```
> /optimus:worktree "fix login timeout"

## Worktree Created

Working directory: `.worktrees/fix-login-timeout`
Branch: `fix/login-timeout` (from `main`)
Main workspace: `main` (unchanged)
Tests: passing

Open it: `code .worktrees/fix-login-timeout` (VSCode) or `cd .worktrees/fix-login-timeout && claude`
Cleanup when done: `git worktree remove .worktrees/fix-login-timeout`
```

## When to Use

- Parallel Claude Code sessions on different tasks
- An urgent fix without stashing or disturbing work in progress
- Reviewing or experimenting in isolation — delete the worktree when done

## When NOT to Use

- **Just need a branch** — use `/optimus:commit branch` for a quick branch without a separate directory or setup
- **Starting TDD** — `/optimus:tdd` offers worktree isolation as part of its workflow
- **Single-task work** — a regular branch is simpler

## Skill Structure

| File | Purpose |
|---|---|
| `SKILL.md` | Skill definition |
| `references/worktree-setup.md` | Shared setup, failure handling, and cleanup procedure (also consumed by `tdd`) |
| *(shared)* `init/references/multi-repo-detection.md` | Multi-repo workspace detection |
| *(shared)* `commit/references/branch-naming.md` | Branch naming convention |

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Git 2.5+ (worktree support)

## License

[MIT](../../LICENSE)
