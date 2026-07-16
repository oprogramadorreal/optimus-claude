# optimus:reset

Removes files installed by [`/optimus:init`](../init/README.md) from your project. Use it for a clean reinstall or to stop using optimus in a project.

It does **not** uninstall the plugin itself — that is `/plugin uninstall optimus@optimus-claude`, run afterwards if you want optimus gone entirely.

## Quick Start

Part of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin — see the [main README](../../README.md) for installation. **Run:** type `/optimus:reset` in any project directory.

## How It Works

The skill inventories every file init can install, classifies each one against the plugin's templates, presents the categorized plan, and asks before removing anything.

| Classification | Meaning | How determined |
|---|---|---|
| **Unmodified** | Matches the plugin template | Byte comparison for hooks; body comparison from line 2 for guideline docs (init only substitutes the project name on line 1) |
| **Likely generated** | Written by optimus, content filled in from project analysis | Fingerprinting — `CLAUDE.md` files are checked for the template's line-1 HTML comment; `testing.md`/`styling.md`/`architecture.md` for the template's `##` heading skeleton |
| **Modified** | User edits, or an older optimus install whose templates have since changed | Content differs from the template, or fingerprints don't match |

Each file is also checked for git tracking — tracked files are noted as recoverable via `git checkout`, which makes bulk removal safe in version-controlled projects.

**Confirmation is mandatory.** A single answer can approve removing all unmodified and likely-generated files, but modified files are only ever deleted with explicit per-file approval, and aborting is always an option.

## What Gets Removed

- `.claude/CLAUDE.md` — plus subproject `CLAUDE.md` files in monorepos and the workspace-root `CLAUDE.md` in multi-repo workspaces
- `.claude/docs/` — `coding-guidelines.md`, `testing.md`, `styling.md`, `architecture.md`, `skill-writing-guidelines.md`, plus subproject `docs/` copies and per-subproject `coding-guidelines.md` in monorepos
- `.claude/hooks/` — formatter hooks (template and custom fallback) and the `restrict-paths.sh` guardrails hook
- `.claude/settings.json` — optimus-added entries only (surgical cleanup, see below)
- `.claude/.optimus-version`
- `HOW-TO-RUN.md` — only if init generated it; the skill asks, since it may be hand-written
- Harness state from `/optimus:deep` — `.claude/*-deep-progress.json` (with `.bak` and `.done.json` siblings) and `.claude/.deep-iteration-*` / `.claude/.unit-test-deep-*` scratch files

## settings.json Handling

The file is never deleted outright. The skill removes only what optimus added, at command-object granularity:

- Formatter hook commands whose hook file was removed (a kept hook file keeps its entry and stays active)
- The `restrict-paths.sh` PreToolUse command, again only if the hook file was removed
- Permission allow/deny entries that exactly match the guardrails template

Everything else — user hooks, user permissions, other config — is preserved. The file is deleted only if it ends up completely empty.

## What Is Never Touched

- **Tests** — even tests written by `/optimus:unit-test`
- **`docs/specs/` and `docs/product/`** — approved specs and product docs are your content; they are left in place
- **User-added configuration** in `settings.json`
- **Anything outside the inventoried set** above

## Monorepos and Multi-Repo Workspaces

Monorepos include subproject `CLAUDE.md` and `docs/` files in the inventory. Multi-repo workspaces are processed per child repo, with files grouped by repo in the plan, plus the local workspace-root `CLAUDE.md`.

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support) and git (for tracked-file detection)

## License

[MIT](../../LICENSE)
