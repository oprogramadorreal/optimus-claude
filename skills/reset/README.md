# optimus:reset

Removes files installed by [`/optimus:init`](../init/README.md) and [`/optimus:permissions`](../permissions/README.md) from your project. Use this when you want a clean reinstall or want to stop using optimus in a project.

This skill does **not** uninstall the optimus plugin itself — it only removes files from the project's `.claude/` directory (and subproject docs for monorepos).

## Quick Start

This skill is part of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin. See the [main README](../../README.md) for installation instructions.

**Run:** Type `/optimus:reset` in any project directory.

## How It Works

The skill scans for all files that optimus may have installed, classifies each one, presents a categorized list, and asks before removing anything.

### File Classification

Every file is analyzed and placed into one of three categories:

| Classification | Meaning | How determined |
|---|---|---|
| **Unmodified** | Exact match with plugin template | Byte-for-byte comparison against the template file in the plugin |
| **Likely generated** | Created by optimus but content was filled in from project analysis | Heuristic fingerprinting — checks for template HTML comments and matching section headings |
| **Modified** | User has customized the file | Content differs from template, or fingerprints don't match |

### Git-Tracked Awareness

For each file, the skill checks whether it is tracked by git. Git-tracked files are noted as **recoverable** via `git checkout` — this makes the "Remove all" option safe for version-controlled projects.

### User Confirmation

The skill **always** asks before removing anything. After presenting the categorized list, it offers four choices:

1. **Remove all** (Recommended) — removes all optimus files (unmodified + likely generated + modified). Safe when git-tracked
2. **Keep modified** — removes unmodified and likely generated files, keeps user-modified files
3. **Unmodified only** — removes only exact template matches (most conservative)
4. **Abort** — cancel, remove nothing

## What Gets Removed

### Files from `/optimus:init`

| File | Classification method |
|---|---|
| `.claude/CLAUDE.md` | Heuristic (template comment + section headings) |
| `.claude/.optimus-version` | Always unmodified (pure tracking file) |
| `.claude/docs/coding-guidelines.md` | Near-exact (template body comparison, line 2+) |
| `.claude/docs/testing.md` | Heuristic (section headings) |
| `.claude/docs/styling.md` | Heuristic (section headings) |
| `.claude/docs/architecture.md` | Heuristic (section headings) |
| `.claude/agents/code-simplifier.md` | Exact match *(legacy)* |
| `.claude/agents/test-guardian.md` | Exact match *(legacy)* |
| `.claude/hooks/format-*.{py,js,sh}` | Exact match (one per detected tech stack) |

### Files from `/optimus:permissions`

| File | Classification method |
|---|---|
| `.claude/hooks/restrict-paths.sh` | Exact match |

### Shared file: `.claude/settings.json`

Both `/optimus:init` and `/optimus:permissions` merge configuration into `.claude/settings.json`. The reset skill does **not** delete this file outright — it surgically removes optimus-contributed entries while preserving user-added configuration:

- **PostToolUse hooks** referencing formatter scripts → removed
- **PreToolUse hooks** referencing `restrict-paths.sh` → removed
- **Permission allow/deny entries** matching the permissions template → removed
- **MCP server allow entries** (`mcp__*`) added by permissions → removed (only when `.mcp.json` exists in the relevant project root — per child repo for multi-repo workspaces; preserved otherwise)
- **User-added hooks, permissions, and other config** → preserved

If the file becomes empty after cleanup, it is deleted. Otherwise, the cleaned JSON is written back.

## What Is Never Touched

- **Test files** — even if created by `/optimus:unit-test`, tests are never removed
- **Files outside `.claude/`** — only optimus-managed paths are scanned (with the exception of monorepo subproject docs and multi-repo workspace root `CLAUDE.md`)
- **User-added configuration** — custom entries in `settings.json` are preserved during surgical cleanup

## Monorepo Support

For monorepos, the skill also scans for:
- Subproject `CLAUDE.md` files (e.g., `packages/auth/CLAUDE.md`)
- Subproject `docs/` directories (`testing.md`, `styling.md`, `architecture.md`)

Each subproject file is classified using the same heuristic fingerprinting and included in the categorized list.

## Multi-Repo Workspace Support

For multi-repo workspaces (a directory containing multiple independent git repos):
- Each child repo is processed independently
- Files are grouped by repo in the categorized list
- The workspace root `CLAUDE.md` (local-only, not version-controlled) is also detected and classified

## Skill Structure

| File | Purpose |
|---|---|
| `SKILL.md` | Step-by-step reset instructions |

No templates or references — this skill removes files, it does not install them.

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Git (for git-tracked status detection)

## License

[MIT](../../LICENSE)
