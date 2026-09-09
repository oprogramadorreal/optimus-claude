# optimus:init

The main skill of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin. Analyzes your project and sets up Claude Code for optimal performance — documentation, formatter hooks, and test infrastructure, all scoped to the project directory so they travel with the repo via git.

The design emphasizes readable code, project-specific guidance, and reproducible checks. Research on [code health](https://arxiv.org/abs/2601.02200) and [long contexts](https://arxiv.org/abs/2510.05381), plus Anthropic's [verification guidance](https://code.claude.com/docs/en/best-practices), motivates those choices. The studies concern their own tasks and models; they do not measure Optimus or establish a GPT-6 Astra/Claude Fable 5.1 performance improvement.

## Features

- **New project scaffolding** — in an empty or near-empty directory, offers to scaffold a new project using official stack tooling (Vite, Next.js, Cargo, Flutter, .NET CLI, ...), then continues with full init setup. Unsupported stacks get a best-effort web-search fallback with strict command validation.
- **Context architecture** — CLAUDE.md files following [research-backed practices](https://www.humanlayer.dev/blog/writing-a-good-claude-md): a compact ~60-line root file with details in separate docs loaded only when needed (progressive disclosure).
- **Code consistency** — PostToolUse hooks that auto-format code after every edit, preventing formatting drift.
- **Code quality** — installs [coding guidelines](templates/docs/coding-guidelines.md) that the plugin's [code-simplifier](../../agents/code-simplifier.md) agent, `/optimus:refactor`, and `/optimus:code-review` enforce.
- **Skill-authoring projects as a first-class stack** — detects AI-agent instruction projects (Claude Code plugins, prompt libraries, agent frameworks) via a structural signal and installs [`skill-writing-guidelines.md`](templates/docs/skill-writing-guidelines.md); review/refactor skills then route markdown instruction files through that lens via the shared [`constraint-doc-loading.md`](references/constraint-doc-loading.md) contract.
- **Test infrastructure** — detects or installs (with approval) a test framework and coverage tooling, runs a health check, and provisions testing docs. Enables the plugin's [test-guardian](../../agents/test-guardian.md) agent and the skills that depend on a test command.
- **Documentation freshness** — audits generated docs on re-run (Outdated / Missing / Accurate / User-added, with user-added content always preserved) and syncs project docs (README, CONTRIBUTING, ...) against source code, fixing only factual contradictions.
- **Monorepo & multi-repo workspace support** — hierarchical CLAUDE.md files for monorepos; fully self-contained `.claude/` per repo plus workspace-root context pointers in multi-repo workspaces.

## Quick Start

Part of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin — see the [main README](../../README.md) for installation. Then run `/optimus:init` in any project directory (optionally with a focus hint, e.g. `/optimus:init "focus on the backend services"`).

## When to Run

- **New project** — initial setup of context, consistency, quality, tests, and docs
- **Re-runs** — audit and refresh docs after major changes, new stack components, or plugin updates (tracked via `.claude/.optimus-version`)
- **Onboarding** — consistent Claude Code behavior for the whole team via git-tracked `.claude/`

## How It Works

1. **Detects project context** — tech stack, package manager, structure (single / monorepo / multi-repo workspace), existing docs, test infrastructure, skill-authoring stack (offers scaffolding first in empty directories)
2. **Audits existing documentation** (if present) — you choose what to update; user-added content survives even "Fresh start"
3. **Creates directory structure** — `.claude/docs/`, `.claude/hooks/`
4. **Generates CLAUDE.md** — identity, commands, a doc-routing table, and the gotchas detection turned up; <=60 lines (soft limit when preserving user content)
5. **Installs formatter hooks** — per detected stack, asking before installing anything new; skipped under Codex
6. **Sets up test infrastructure** — framework/coverage install (with approval), health check, testing docs
7. **Creates scoped documentation** — coding guidelines (always); styling, architecture, skill-writing guidelines (when detected)
8. **Syncs project docs** — surgical fixes for claims the source code contradicts, with your approval

File-write safety: init refreshes recorded, unchanged template copies. Customized guidance/hooks remain subject to review even after an approved merge updates their recorded hash. Unrecorded user files stay unowned after ordinary init edits; only explicit whole-file adoption/replacement changes that. Customizable documents are reconciled with approval, and `settings.json` is merged. A small `.claude/.optimus-managed.json` record tracks installed file hashes, refresh eligibility, and only settings entries actually added.

## Formatter Hooks

Claude Code only. Under Codex, init preserves existing hooks/settings and documents the project's formatter/check command for task boundaries and editor/CI use. This plugin does not install its Claude PostToolUse formatters in Codex. Documentation and test-infrastructure setup still run.

Existing formatter configuration, pinned versions, ignore rules, and editor/CI integration take priority. If a new integration is appropriate, defaults are available for Python (black + isort), Node.js (prettier), Rust (rustfmt with an explicit project edition), Go (gofmt), C#/.NET (local csharpier), Java, C/C++, and Dart/Flutter. Other stacks use a reviewed fallback. Setup does not reformat the repository or replace a competing formatter silently. See [`references/formatter-setup.md`](references/formatter-setup.md) for requirements and legacy `.js`/Python migrations.

## Generated Files

| File | Purpose |
|------|---------|
| `.claude/CLAUDE.md` | Project overview, commands, doc references |
| `.claude/settings.json` | Formatter hook configuration (merged, never overwritten) |
| `.claude/docs/coding-guidelines.md` | Coding baseline; existing customizations are preserved and reviewed |
| `.claude/docs/skill-writing-guidelines.md` | Markdown-instruction standards (when skill authoring detected) |
| `.claude/docs/testing.md` | Testing conventions (when test infrastructure exists) |
| `.claude/docs/styling.md` | UI/CSS guidelines (when frontend detected) |
| `.claude/docs/architecture.md` | Architecture map (complex structure or skill authoring; optional Skill Architecture section) |
| `.claude/hooks/` | Auto-format hooks per detected stack |
| `.claude/.optimus-version` | Plugin version that last generated these files (written only by init) |
| `.claude/.optimus-managed.json` | Installed file hashes, refresh eligibility, and settings additions; shared with permissions/reset |
| `AGENTS.md` | Codex pointer to the applicable project/workspace CLAUDE.md and nested package instructions; existing marked blocks are refreshed without changing surrounding user content |

**Monorepo:** each subproject also gets its own `CLAUDE.md` and scoped `docs/`; the root Codex pointer explicitly routes to those instructions because Codex does not load them automatically. **Multi-repo workspace:** each repo gets its own complete `.claude/` and, when Codex use is detected, a pointer (version-controlled), plus lightweight local-only workspace `CLAUDE.md` and `AGENTS.md` pointer files.

## Customization

`.claude/docs/coding-guidelines.md` is the baseline used by code-simplifier, refactor, and code-review. Init refreshes recorded unchanged template copies; customized, changed, or unrecorded versions are reviewed. Keep project-specific rules there or in an existing routed guide, with key gotchas in `.claude/CLAUDE.md`. Architecture documentation stays conditional and records non-obvious boundaries and rationale rather than prescribing a new design.

Templates live in [`templates/`](templates/) — CLAUDE.md variants, doc skeletons, and hook scripts.

## Relationship to Other Skills

init is the foundation: `/optimus:unit-test` and `/optimus:deep` require an initialized project (CLAUDE.md — deep additionally requires a documented test command); `/optimus:tdd` and `/optimus:brainstorm` recommend it and, on the user's choice, continue with general best practices; `/optimus:refactor` and `/optimus:code-review` use its guidelines (falling back to general best practices when missing); `/optimus:permissions` shares `.claude/settings.json`. After init, `/optimus:how-to-run` generates the human-facing onboarding doc.

## Requirements

- A plugin-capable [Claude Code](https://code.claude.com/docs/en/plugins) or Codex host (see the [supported hosts and versions](../../README.md#supported-hosts-and-versions))
- Git

## License

[MIT](../../LICENSE)
