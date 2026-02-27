# bootstrap:init

The main skill of the [bootstrap](https://github.com/oprogramadorreal/claude-code-bootstrap) plugin. Analyzes your project and sets up Claude Code for optimal performance by generating documentation, installing formatter hooks, and deploying quality agents — all scoped to the project directory so they travel with the repo via git.

## Quick Start

This skill is part of the [bootstrap](https://github.com/oprogramadorreal/claude-code-bootstrap) plugin. See the [main README](../../README.md) for installation instructions.

**Run:** Start a new Claude Code session and type `/bootstrap:init` in any project directory.

## What It Does

`/bootstrap:init` sets up five pillars designed to maximize Claude Code's performance:

1. **Context Architecture** — CLAUDE.md with progressive disclosure docs (WHAT/WHY/HOW structure, ~60 lines)
2. **Code Consistency** — PostToolUse hooks that auto-format code after every edit
3. **Code Quality** — [code-simplifier](templates/agents/code-simplifier.md) agent enforcing project coding guidelines
4. **Test Coverage** — [test-guardian](templates/agents/test-guardian.md) agent monitoring coverage gaps (when test infrastructure detected)
5. **Documentation Freshness** — Audits existing docs against source code for contradictions

Re-running on an existing project triggers an intelligent audit that classifies docs as Outdated / Missing / Accurate, letting you choose what to update.

## Generated Files

| File | Purpose |
|---|---|
| `.claude/CLAUDE.md` | Project overview, commands, doc references |
| `.claude/settings.json` | Formatter hook configuration |
| `.claude/docs/coding-guidelines.md` | Code style and architecture guidelines |
| `.claude/docs/testing.md` | Testing conventions (when test framework detected) |
| `.claude/docs/styling.md` | UI/CSS guidelines (when frontend detected) |
| `.claude/docs/architecture.md` | Project structure (when complex structure detected) |
| `.claude/hooks/` | Auto-format hooks per detected stack |
| `.claude/agents/code-simplifier.md` | Code quality agent |
| `.claude/agents/test-guardian.md` | Test coverage agent (when test infrastructure detected) |

## Skill Structure

| File | Purpose |
|---|---|
| `SKILL.md` | Skill definition with step-by-step instructions |
| `references/claude-md-best-practices.md` | Research-backed guidance for CLAUDE.md authoring |
| `templates/` | CLAUDE.md templates, doc templates, hook scripts, agent definitions |

## Customization

To understand or modify how the skill works, start with `SKILL.md`. Key customization points:

- **CLAUDE.md templates**: `templates/single-project-claude.md`, `templates/monorepo-claude.md`, `templates/subproject-claude.md`
- **Coding guidelines**: `templates/docs/coding-guidelines.md`
- **Formatter hooks**: `templates/hooks/` (Python, Node.js, Rust, Go, C#, Java, C/C++)
- **Agents**: `templates/agents/` (code-simplifier, test-guardian)

See the [main README](../../README.md) for full documentation including supported formatters, agent details, and monorepo support.

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Git

## License

[MIT](../../LICENSE)
