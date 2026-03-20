# optimus:worktree

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that creates a git worktree for isolated parallel development — a new branch in a separate directory with project setup and test baseline. Enables multiple Claude Code sessions on different tasks simultaneously.

Git worktrees let you have multiple working directories for the same repository. Each worktree has its own branch and files, but they share the same git history. This means you can work on a bug fix in one terminal while a feature is in progress in another — no stashing, no context switching, no interference.

## Features

- **Isolated parallel development** — each worktree is a separate directory with its own branch, enabling truly independent Claude Code sessions
- **Automatic project setup** — detects and runs setup commands (npm install, pip install, cargo build, etc.) in the new worktree
- **Test baseline verification** — runs the test suite in the worktree to confirm a healthy starting point
- **Conventional branch naming** — follows `<type>/<slugified-description>` convention, consistent with all optimus skills
- **Recursive worktree guard** — detects if you are already inside a worktree and prevents nested worktree creation
- **VSCode native integration** — VSCode 1.103+ discovers worktrees automatically in the Source Control panel; open any worktree in a new window with one click
- **Multi-repo workspace support** — targets specific repos in multi-repo setups
- **Clean main workspace** — the original branch is restored; all new work happens in `.worktrees/`

## VSCode Integration

VSCode 1.103+ has native git worktree support. After creating a worktree with this skill:

- **Source Control panel** — worktrees appear in the Repositories view. Right-click → "Open Worktree in New Window"
- **Command Palette** — `Git: Open Worktree in New Window` or `Git: Open Worktree in Current Window`
- **Terminal** — `code .worktrees/<worktree-dir>` opens a new VSCode window directly

Each VSCode window gets its own file watchers, terminal, and extension context — no cross-branch interference.

## Quick Start

This skill is part of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin. See the [main README](../../README.md) for installation instructions.

## Usage

In Claude Code, use any of these:

- `/optimus:worktree` — asks what you will work on, then creates the worktree
- `/optimus:worktree "fix login timeout"` — uses the provided description directly
- `/optimus:worktree "add payment integration"` — explicit description for precise naming

### Examples

**With inline description:**

```
> /optimus:worktree "fix login timeout"

## Worktree Created

Working directory: `.worktrees/fix-login-timeout`
Branch: `fix/login-timeout` (from `main`)
Main workspace: `main` (unchanged)
Tests: passing

### Open the worktree

**VSCode**: Source Control panel → right-click → "Open Worktree in New Window"
Or from terminal: `code .worktrees/fix-login-timeout`

**Claude Code CLI**: `cd .worktrees/fix-login-timeout && claude`
```

**From conversation context:**

```
> I need to add a password reset endpoint while keeping my current auth refactor intact
> /optimus:worktree

## Worktree Created

Working directory: `.worktrees/feat-add-password-reset-endpoint`
Branch: `feat/add-password-reset-endpoint` (from `main`)
Main workspace: `main` (unchanged)
Tests: passing
```

**When already inside a worktree:**

```
> /optimus:worktree "another task"

Already running inside a worktree (`.worktrees/feat-add-auth`).
To create another worktree, run this skill from the main workspace instead.
```

## When to Use

- **Parallel Claude Code sessions** — work on multiple tasks simultaneously without interference
- **Urgent bug fix** — switch to a fix without stashing or losing current work
- **Code review** — check out a PR branch in isolation while keeping your work intact
- **Experimentation** — try an approach in isolation; delete the worktree if it does not work out

## When NOT to Use

- **Just need a branch** — use `/optimus:branch` for a quick local branch switch without the overhead of project setup
- **Starting TDD** — use `/optimus:tdd`, which offers worktree isolation as part of its workflow
- **Single-task workflow** — if you are only working on one thing, a regular branch is simpler

## Relationship to Other Skills

| | `/optimus:worktree` | `/optimus:branch` |
|---|---|---|
| Creates branch | Yes (inside a worktree) | Yes (in current directory) |
| Isolation | Full — separate directory | None — same directory |
| Project setup | Yes (npm install, etc.) | No |
| Speed | Slower (setup + test baseline) | Instant |

| | `/optimus:worktree` | `/optimus:tdd` |
|---|---|---|
| Worktree creation | Primary purpose | Optional feature (offered during TDD) |
| Scope | Just the worktree | Full TDD workflow with commits and PR |
| Recursive guard | Both use the shared worktree detection guard |

## Skill Structure

| File | Purpose |
|---|---|
| `SKILL.md` | Skill definition with 5-step workflow |
| `references/worktree-setup.md` | Shared worktree setup procedure (also consumed by `tdd`) |
| *(shared)* `init/references/multi-repo-detection.md` | Multi-repo workspace detection algorithm |
| *(shared)* `commit/references/branch-naming.md` | Branch naming convention |

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Git 2.5+ (worktree support)
- VSCode 1.103+ recommended (native worktree UI)

## License

[MIT](../../LICENSE)
