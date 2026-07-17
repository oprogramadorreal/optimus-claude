# optimus:init

The main skill of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin. Analyzes your project and sets up Claude Code for optimal performance — documentation, formatter hooks, and test infrastructure, all scoped to the project directory so they travel with the repo via git.

What makes a good developer productive in a codebase also makes Claude Code productive: clean code, good test coverage, and clear documentation. AI tools introduce [30%+ more defects](https://arxiv.org/abs/2601.02200) on poorly maintained code, LLM performance [degrades up to 85%](https://arxiv.org/abs/2510.05381) as context grows, and Anthropic's [#1 best practice](https://code.claude.com/docs/en/best-practices) is giving Claude a way to verify its own work.

## Features

- **New project scaffolding** — in an empty or near-empty directory, offers to scaffold a new project using official stack tooling (Vite, Next.js, Cargo, Flutter, .NET CLI, ...), then continues with full init setup. Unsupported stacks get a best-effort web-search fallback with strict command validation.
- **Context architecture** — CLAUDE.md files following [research-backed practices](https://www.humanlayer.dev/blog/writing-a-good-claude-md): a compact ~60-line root file with details in separate docs loaded only when needed (progressive disclosure).
- **Code consistency** — PostToolUse hooks that auto-format code after every edit, preventing formatting drift.
- **Code quality** — installs [coding guidelines](templates/docs/coding-guidelines.md) that the plugin's [code-simplifier](../../agents/code-simplifier.md) agent, `/optimus:refactor`, and `/optimus:code-review` enforce.
- **Skill-authoring projects as a first-class stack** — detects AI-agent instruction projects (Claude Code plugins, prompt libraries, agent frameworks) via a structural signal and installs [`skill-writing-guidelines.md`](templates/docs/skill-writing-guidelines.md); review/refactor skills then route markdown instruction files through that lens via the shared [`constraint-doc-loading.md`](references/constraint-doc-loading.md) contract.
- **Test infrastructure** — detects or installs (with approval) a test framework and coverage tooling, runs a health check, and provisions testing docs. Enables the plugin's [test-guardian](../../agents/test-guardian.md) agent and the skills that depend on a test command.
- **Documentation freshness** — audits generated docs on re-run (Outdated / Missing / Accurate / User-added, with user-added content always preserved) and syncs project docs (README, CONTRIBUTING, ...) against source code, fixing only factual contradictions.
- **Monorepo & multi-repo workspace support** — hierarchical CLAUDE.md files for monorepos; fully self-contained `.claude/` per repo in multi-repo workspaces.

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
4. **Generates CLAUDE.md** — WHAT/WHY/HOW, <=60 lines (soft limit when preserving user content)
5. **Installs formatter hooks** — per detected stack, asking before installing anything new
6. **Sets up test infrastructure** — framework/coverage install (with approval), health check, testing docs
7. **Creates scoped documentation** — coding guidelines (always); styling, architecture, skill-writing guidelines (when detected)
8. **Syncs project docs** — surgical fixes for claims the source code contradicts, with your approval

File-write safety: hooks and `coding-guidelines.md` are always refreshed from templates; everything else (CLAUDE.md, testing.md, styling.md, architecture.md, skill-writing-guidelines.md) is never silently overwritten, and `settings.json` is always merged.

## Formatter Hooks

Auto-installed per detected stack: Python (black + isort), Node.js (prettier), Rust (rustfmt), Go (gofmt), C#/.NET (csharpier), Java (google-java-format), C/C++ (clang-format), Dart/Flutter (dart format). Other stacks get a custom hook via web-search fallback with user approval. External formatters are only installed after you approve. See [`references/formatter-setup.md`](references/formatter-setup.md) for the exact install conditions.

## Generated Files

| File | Purpose |
|------|---------|
| `.claude/CLAUDE.md` | Project overview, commands, doc references |
| `.claude/settings.json` | Formatter hook configuration (merged, never overwritten) |
| `.claude/docs/coding-guidelines.md` | Coding standards (always refreshed from template) |
| `.claude/docs/skill-writing-guidelines.md` | Markdown-instruction standards (when skill authoring detected) |
| `.claude/docs/testing.md` | Testing conventions (when test infrastructure exists) |
| `.claude/docs/styling.md` | UI/CSS guidelines (when frontend detected) |
| `.claude/docs/architecture.md` | Architecture map (complex structure or skill authoring; optional Skill Architecture section) |
| `.claude/hooks/` | Auto-format hooks per detected stack |
| `.claude/.optimus-version` | Plugin version that last generated these files (written only by init) |

**Monorepo:** each subproject also gets its own `CLAUDE.md` and scoped `docs/`. **Multi-repo workspace:** each repo gets its own complete `.claude/` (version-controlled), plus a lightweight local-only workspace CLAUDE.md.

## Customization

`.claude/docs/coding-guidelines.md` in your project is the primary control surface for what the code-simplifier agent, `/optimus:refactor`, and `/optimus:code-review` flag — every principle you add or edit changes their behavior. It is overwritten from the template on re-run, so put project-specific rules in `.claude/CLAUDE.md` (or, for skill-authoring projects, in `skill-writing-guidelines.md`, which is preserved across re-runs).

Templates live in [`templates/`](templates/) — CLAUDE.md variants, doc skeletons, and hook scripts.

## Relationship to Other Skills

init is the foundation: `/optimus:tdd`, `/optimus:unit-test`, `/optimus:brainstorm`, and `/optimus:deep` require an initialized project (CLAUDE.md — deep additionally requires a documented test command); `/optimus:refactor` and `/optimus:code-review` use its guidelines (falling back to general best practices when missing); `/optimus:permissions` shares `.claude/settings.json`. After init, `/optimus:how-to-run` generates the human-facing onboarding doc.

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Git

## License

[MIT](../../LICENSE)
