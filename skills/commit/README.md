# optimus:commit

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) git-hygiene skill: commit local changes with a [Conventional Commits](https://www.conventionalcommits.org/) message, preview a message without committing, or create a conventionally named branch.

## Modes

| Invocation | What it does | Modifies repo |
|---|---|---|
| `/optimus:commit` | Stages, commits, and optionally pushes after you confirm | Yes |
| `/optimus:commit suggest` | Proposes a commit message in a copyable code block | No — read-only |
| `/optimus:commit branch "description"` | Creates and switches to a `<type>/<slug>` branch (description optional — falls back to conversation context, then local diffs) | Branch only — never commits, stashes, or touches files |

## Features

- Analyzes staged, unstaged, and untracked changes; asks before including untracked files and flags secret-looking ones (`.env`, keys, credentials) for individual confirmation
- Always previews the branch, full message, and file list before committing — commit and push, commit only, edit the message, or cancel
- Detects protected branches via `.claude/hooks/restrict-paths.sh` and offers to create a feature branch automatically
- Suggests splitting into separate commits when changes span multiple concerns, with the files to stage for each
- Captures the implementation conversation's *why* into the commit body — run it in the conversation where the work happened
- Multi-repo workspaces: detects repos with changes and processes each independently
- Branch mode preserves all local changes exactly as they are and stops rather than invent a meaningless name when there is no naming signal

## Example — default mode

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

## Example — branch mode

```
> /optimus:commit branch "fix login timeout"

## Branch

Created `fix/login-timeout` from `main`.
Local changes preserved (nothing committed or pushed).
```

## Related skills

- `/optimus:pr` — create a pull request after committing (commit first, then pr, in the same conversation)
- `/optimus:code-review` — review changes before committing
- `/optimus:worktree` — parallel work in an isolated directory (also creates a branch)

## Quick Start

This skill is part of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin. See the [main README](../../README.md) for installation instructions.

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Git

## License

[MIT](../../LICENSE)
