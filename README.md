# claude-code-bootstrap

Replace Claude Code's basic `/init` with research-backed CLAUDE.md files optimized for LLM comprehension and attention.

## Quick Start

**Install:** Clone to your Claude Code skills directory:

```bash
# macOS/Linux
git clone https://github.com/oprogramadorreal/claude-code-bootstrap ~/.claude/skills/claude-code-bootstrap

# Windows
git clone https://github.com/oprogramadorreal/claude-code-bootstrap %USERPROFILE%\.claude\skills\claude-code-bootstrap
```

**Run:** Start a new Claude Code session and type `/bootstrap` in any project directory.

## What It Does

AI-assisted coding amplifies output — but also amplifies drift from intended architecture. A well-structured CLAUDE.md acts as an anchor that resists this degradation.

`/bootstrap` analyzes your project and generates documentation following [research-backed practices](https://www.humanlayer.dev/blog/writing-a-good-claude-md):

- **WHAT/WHY/HOW structure** — Organizes information for optimal LLM comprehension
- **60-line CLAUDE.md** — Keeps the main file within LLM's peak attention window
- **Progressive disclosure** — Details in separate docs, not one massive file
- **Audit on re-run** — Compares docs against current project state, classifies sections as Outdated / Missing / Accurate, and lets you choose what to update
- **Auto-format hooks** — Installs PostToolUse hooks for black, prettier, rustfmt, gofmt, csharpier per detected stack
- **Code simplifier agent** — Proactively enforces your coding guidelines on every change, keeping code clean for better LLM comprehension
- **Monorepo support** — Auto-detects monorepos via workspace tools and manifest scanning, generates scoped docs per subproject
- **Documentation sync** — Cross-checks existing docs (README, CONTRIBUTING, etc.) against source code and fixes contradictions

**Generated files:**

- `.claude/CLAUDE.md` — Project overview, commands, doc references
- `.claude/settings.json` — Formatter hook configuration
- `.claude/docs/` — Coding guidelines, testing, styling, architecture (per detected stack)
- `.claude/hooks/` — Auto-format hooks for detected stacks (see below)
- `.claude/agents/` — Code simplifier agent aligned with your coding standards
- Monorepo: each subproject gets its own `CLAUDE.md` and `docs/` with scoped documentation

## Formatter Hooks

PostToolUse hooks that auto-format files after every Edit/Write, installed per detected stack:

| Hook | Formatter | Installed when |
|------|-----------|----------------|
| `format-python.py` | black + isort | Python project detected |
| `format-node.js` | prettier | Node.js project detected |
| `format-rust.sh` | rustfmt | Rust project detected (built-in) |
| `format-go.sh` | gofmt | Go project detected (built-in) |
| `format-csharp.sh` | csharpier | C#/.NET project detected |

For stacks requiring external formatters (Python, Node.js, C#), `/bootstrap` checks your dependencies and asks before installing anything.

## Code Quality Agent

LLM performance depends on what it reads: both documentation and source code. `/bootstrap` installs a [code-simplifier](templates/agents/code-simplifier.md) agent that proactively enforces your coding guidelines on every change — simplifying code for clarity, consistency, and maintainability while preserving functionality.

The agent reads your project's `.claude/docs/coding-guidelines.md` at runtime, so it always follows your established conventions rather than imposing external style rules. It activates automatically on recently modified code; for a broader review:

> Use the code-simplifier agent to analyze this project against the standards in .claude/docs/coding-guidelines.md and suggest simplifications

## Keeping Docs Current

`/bootstrap` is not just for initial setup. Re-running it on an existing project triggers an intelligent audit that compares your docs against the current project state, classifies them as Outdated / Missing / Accurate, and lets you choose what to update.

For ongoing quality between audits, the official [claude-md-management](https://claude.com/plugins/claude-md-management) plugin (by Anthropic) provides complementary tools: `claude-md-improver` for scoring and targeted improvements, and `/revise-claude-md` for capturing session learnings.

**Recommended workflow:**

1. **Initial setup** — Run `/bootstrap` to generate documentation from scratch
2. **After major changes** — Re-run `/bootstrap` to audit and refresh docs
3. **Periodic quality checks** — Use `claude-md-improver` for scoring and targeted improvements
4. **After work sessions** — Use `/revise-claude-md` to capture discoveries from real usage

Install the plugin: `claude plugin add claude-md-management`

## Customization

To understand or modify how the skill works, start with `SKILL.md`. Key files:

- **Generation logic**: `SKILL.md` — Step-by-step instructions Claude follows to generate docs
- **CLAUDE.md templates**: `templates/single-project-claude.md`, `templates/monorepo-claude.md`, `templates/subproject-claude.md`
- **Coding guidelines**: `templates/docs/coding-guidelines.md` — Shared style rules template
- **Hook configuration**: `templates/settings.json` — PostToolUse hook structure
- **Formatter hooks**: `templates/hooks/` — Hook templates (Python, Node.js, Rust, Go, C#)
- **Code simplifier agent**: `templates/agents/code-simplifier.md` — Agent template
- **Best practices reference**: `references/claude-md-best-practices.md` — Research-backed guidance

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) — `/bootstrap` is a [skill](https://docs.anthropic.com/en/docs/claude-code/skills) (reusable prompt that adds a slash command)
- Git

## Credits

Best practices based on [Writing a Good CLAUDE.md](https://www.humanlayer.dev/blog/writing-a-good-claude-md) by HumanLayer.

## License

[MIT](LICENSE)
