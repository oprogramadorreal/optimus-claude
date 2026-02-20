# claude-code-bootstrap

Initialize effective CLAUDE.md files using research-backed practices that help Claude Code deliver better, more context-aware assistance.

## Quick Start

**Install:** Clone to your Claude Code skills directory:

```bash
# macOS/Linux
git clone https://github.com/oprogramadorreal/claude-code-bootstrap ~/.claude/skills/claude-code-bootstrap

# Windows
git clone https://github.com/oprogramadorreal/claude-code-bootstrap %USERPROFILE%\.claude\skills\claude-code-bootstrap
```

**Run:** Start a new Claude Code session and type `/bootstrap` in any project directory. This slash command becomes available after installation, alongside built-in commands like `/init`.

> **What are skills?** Skills are reusable prompts that extend Claude Code with new slash commands. See [Claude Code documentation](https://docs.anthropic.com/en/docs/claude-code) for more.

## Why This Skill?

AI-assisted coding amplifies output — but also accelerates codebase quality degradation. The AI itself becomes a victim of this degradation: it reads sloppy patterns as context and reproduces them, compounding the problem faster than any team can review. A well-structured CLAUDE.md acts as an architectural anchor: a stable reference point that resists this drift.

Claude Code's built-in `/init` command creates basic documentation. This skill creates **effective** documentation using research-backed practices:

- **WHAT/WHY/HOW structure** - Organizes information for optimal LLM comprehension
- **60-line CLAUDE.md** - Keeps the main file within LLM's peak attention window
- **Progressive disclosure** - Details in separate docs, not one massive file
- **Pre-configured permissions** - Safe defaults for build/test/lint commands
- **Auto-format hooks** - Installs PostToolUse hooks for black, prettier, rustfmt, gofmt, csharpier (per detected stack)
- **Monorepo support** - Auto-detects monorepos via workspace tools and manifest scanning, with supporting signals from README and Docker Compose — generates scoped docs per subproject

## What Gets Generated

| File                                | Purpose                                                          | Source       |
| ----------------------------------- | ---------------------------------------------------------------- | ------------ |
| `.claude/CLAUDE.md`                 | Project overview, commands, doc references                       | Generated    |
| `.claude/settings.json`             | Command permissions and formatter hook configuration             | Template     |
| `.claude/docs/coding-guidelines.md` | Code style and architecture guidelines                           | Template     |
| `.claude/docs/testing.md`           | Testing conventions (if test framework detected)                 | Generated    |
| `.claude/docs/styling.md`           | UI/CSS guidelines (if frontend project)                          | Generated    |
| `.claude/docs/architecture.md`      | Project structure documentation                                  | Generated    |
| `.claude/hooks/format-*.{py,js,sh}` | Auto-format hooks for detected stacks (see below)                | Template     |

*Template* = copied from `templates/` and customized. *Generated* = created by Claude following `SKILL.md` instructions.

### Formatter Hooks

PostToolUse hooks that auto-format files after every Edit/Write, installed per detected stack:

| Hook | Formatter | Installed when |
|------|-----------|----------------|
| `format-python.py` | black + isort | Python project (in deps, or user approves) |
| `format-node.js` | prettier | Node.js project (in devDependencies, or user approves) |
| `format-rust.sh` | rustfmt | Rust project (built-in) |
| `format-go.sh` | gofmt | Go project (built-in) |
| `format-csharp.sh` | csharpier | C#/.NET project (in dotnet-tools.json, or user approves) |

### Monorepo Projects

For monorepos (auto-detected via workspace tools, independent manifests in subdirectories, README analysis, and Docker Compose services), the same root files above are generated with monorepo-aware content (orchestrator CLAUDE.md, aggregated permissions). In addition, each subproject gets scoped documentation:

| File | Purpose | Source |
|------|---------|--------|
| `<subproject>/CLAUDE.md` | Package-scoped overview, commands, local doc references | Generated |
| `<subproject>/docs/testing.md` | Package-specific testing conventions (if applicable) | Generated |
| `<subproject>/docs/styling.md` | Package-specific UI/CSS guidelines (if frontend) | Generated |
| `<subproject>/docs/architecture.md` | Package-specific structure documentation | Generated |

Claude Code automatically discovers subproject CLAUDE.md files when working with files in those directories, so each package gets focused, relevant context.

## Permission Philosophy

The generated `settings.json` allows development commands (build, test, lint) while requiring explicit approval for git operations (commit, push, rebase). This ensures Claude helps with coding while leaving version control decisions to you.

See `templates/settings.json` to customize defaults.

## Skill Structure

| File | Purpose |
|------|---------|
| `SKILL.md` | Skill definition with step-by-step generation instructions |
| `templates/settings.json` | Base permission settings (customize allowed/denied commands) |
| `templates/docs/coding-guidelines.md` | Coding guidelines template (customize style rules) |
| `templates/single-project-claude.md` | CLAUDE.md template for single projects |
| `templates/monorepo-claude.md` | Root CLAUDE.md template for monorepo projects |
| `templates/subproject-claude.md` | Per-subproject CLAUDE.md template |
| `templates/hooks/` | Formatter hook templates (Python, Node.js, Rust, Go, C#) |
| `references/` | Best practices guide (based on HumanLayer research) |

To understand or modify how the skill works, start with `SKILL.md`.

## Customization

- **Permission rules**: Edit `templates/settings.json` to change allowed/denied commands
- **Coding guidelines**: Edit `templates/docs/coding-guidelines.md` to customize style rules
- **Generation logic**: Edit `SKILL.md` to change how Claude generates the other documentation files
- **Single-project template**: Edit `templates/single-project-claude.md` to customize the CLAUDE.md structure for single projects
- **Monorepo templates**: Edit `templates/monorepo-claude.md` or `templates/subproject-claude.md` to customize monorepo documentation structure
- **Formatter hooks**: Edit files in `templates/hooks/` to customize auto-formatting behavior or add new formatters

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
- Git

## Credits

Best practices based on [Writing a Good CLAUDE.md](https://www.humanlayer.dev/blog/writing-a-good-claude-md) by HumanLayer.

## License

[MIT](LICENSE)
