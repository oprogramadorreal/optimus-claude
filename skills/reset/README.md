# optimus:reset

Removes files installed by [`/optimus:init`](../init/README.md) and [`/optimus:permissions`](../permissions/README.md) from your project. Use it for a clean reinstall or to stop using optimus in a project.

It does **not** uninstall the optimus plugin itself — it only removes optimus-managed files from the project (root `.claude/`, monorepo subproject docs, multi-repo workspace-root `CLAUDE.md`).

## Quick Start

This skill is part of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin. See the [main README](../../README.md) for installation instructions.

**Run:** Type `/optimus:reset` in any project directory.

## How It Works

The skill inventories every file optimus may have installed, classifies each one by comparing it against the plugin's own templates, and presents a categorized plan:

- **Unmodified** — exact match with a plugin template
- **Likely generated** — created by optimus, content filled in from project analysis (structure still matches the template)
- **Modified** — user edits, or installed by an older optimus version whose templates have since changed

Git-tracked files are flagged as recoverable via `git checkout`.

## Safety Guarantees

- **Always asks first.** Nothing is removed until you pick one of four options: **Remove all**, **Keep modified**, **Unmodified only**, or **Abort**. The recommended option depends on git tracking — "Remove all" only when every modified file is recoverable.
- **User-modified files are never deleted without your explicit approval.**
- **`.claude/settings.json` is never deleted outright.** Optimus-added hook entries, permissions, and MCP server allows are removed surgically; everything you added yourself is preserved. Hook entries whose hook file you chose to keep stay wired. The file is only deleted if it ends up completely empty.
- **Tests are never touched** — even tests created by `/optimus:unit-test`.
- **Nothing outside optimus-managed paths is scanned or removed.**

## Monorepo and Multi-Repo Support

- **Monorepo:** subproject `CLAUDE.md` and `docs/` files installed by init are classified and included in the plan.
- **Multi-repo workspace:** each child repo is processed independently, files are grouped by repo, and the local workspace-root `CLAUDE.md` is included.

After a reset, run `/optimus:init` (and `/optimus:permissions`) to reinstall, or `/plugin uninstall optimus@optimus-claude` to remove the plugin itself.

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Git (for git-tracked status detection)

## License

[MIT](../../LICENSE)
