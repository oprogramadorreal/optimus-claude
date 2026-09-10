# optimus:reset

Removes files installed by [`/optimus:init`](../init/README.md) and [`/optimus:permissions`](../permissions/README.md) from your project. Use it for a clean reinstall, to stop using optimus in a project, or to remove only the permissions setup with `reset permissions`.

It does **not** uninstall the optimus plugin itself — it only removes optimus-managed files from the project (root `.claude/`, monorepo subproject docs, multi-repo workspace-root `CLAUDE.md`, and optimus pointer blocks in root `AGENTS.md` files).

## Quick Start

This skill is part of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin. See the [main README](../../README.md) for installation instructions.

Run from the project directory:

| Scope | Claude Code | Codex |
|---|---|---|
| All installed setup, with selective removal available | `/optimus:reset` | `$optimus:reset` |
| Permissions setup only | `/optimus:reset permissions` | `$optimus:reset permissions` |

Both hosts can remove the Claude Code permissions setup; installing it with `permissions` remains Claude Code only.

## How It Works

With no argument, the skill inventories every file optimus may have installed. With `permissions`, it inventories only `.claude/hooks/restrict-paths.sh`, its exact settings registration, recorded `permissions.allow` and `permissions.deny` additions (including MCP rules actually added), and the corresponding ownership entries.

The permissions scope preserves init's documents, formatter hooks, `AGENTS.md` pointers, version marker, and ownership entries, along with unrelated or user-owned settings. It can clean up recorded settings additions even if the hook is already absent. If only init's setup remains, or permissions removal is already complete, it makes no changes.

The skill classifies files by their recorded installed hash (template comparison only annotates files that have no record), and presents a categorized plan:

- **Unmodified** — bytes match a recorded installed hash
- **Modified** — bytes differ from the installed hash
- **Unknown** — no usable ownership record; template/heading similarity can suggest a legacy install but cannot rule out user edits
- **Complex** — shared settings, pointers, and ownership records need exact entry/block edits

HEAD, index, and working-tree content are checked separately. Tracking alone does not make uncommitted edits recoverable. Selected current bytes that cannot be recovered are copied to a verified local, Git-ignored backup before removal; failed backup checks preserve the originals.

Reset removes approved additions; the ownership record is not an undo history. It cannot restore earlier file contents replaced by permissions or git deny rules removed during installation.

## Safety Guarantees

- **Always asks first.** Choose **Unmodified only (Recommended)**, **Select files and entries**, **Remove all listed candidates**, or **Abort**, after seeing the concrete plan.
- **User-modified files are never deleted without your explicit approval.**
- **Shared settings are edited by recorded ownership.** Only unchanged recorded additions are removed by default; ambiguous legacy rules need an explicit selection. Matching today's template or a project's MCP server name is not proof of ownership. Retained hooks stay registered. The settings file is deleted only if the approved edits leave it empty.
- **Shared `AGENTS.md` files retain all content and whitespace outside Optimus's pointer markers.** A file containing only the pointer block is deleted.
- **Tests are never touched** — even tests created by `/optimus:unit-test`.
- **Nothing outside optimus-managed paths is scanned or removed.**
- **Local backups remain local.** `.claude/.optimus-reset-backups/` is excluded from reset and ignored before any content is copied. Backups may hold private settings; reset never stages them and reports their location without printing contents.

## Monorepo and Multi-Repo Support

- **Monorepo:** the default scope includes subproject `CLAUDE.md` and `docs/` files installed by init; `permissions` leaves them untouched.
- **Multi-repo workspace:** each child repo is processed independently and files are grouped by repo. The default scope also includes the local workspace-root `CLAUDE.md`; `permissions` leaves it untouched.

After a permissions-only reset, init's setup remains in place. To reinstall permissions, run `/optimus:permissions` in a fresh Claude Code conversation.

After a full-scope reset, start a fresh conversation to reinstall: `/optimus:init` (and `/optimus:permissions`) in Claude Code, or `$optimus:init` in Codex. The permissions skill is Claude-only. To uninstall the plugin itself, use `/plugin uninstall optimus@optimus-claude` in Claude Code, or run `codex plugin remove optimus@optimus-claude` in your terminal for Codex CLI. Reset does not run either uninstall command.

## Requirements

- A plugin-capable [Claude Code](https://code.claude.com/docs/en/plugins) or Codex host (see the [supported hosts and versions](../../README.md#supported-hosts-and-versions))
- Git (for git-tracked status detection)

## License

[MIT](../../LICENSE)
