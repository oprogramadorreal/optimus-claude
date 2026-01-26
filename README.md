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

Claude Code's built-in `/init` command creates basic documentation. This skill creates **effective** documentation using research-backed practices:

- **WHAT/WHY/HOW structure** - Organizes information for optimal LLM comprehension
- **60-line CLAUDE.md** - Keeps the main file within LLM's peak attention window
- **Progressive disclosure** - Details in separate docs, not one massive file
- **Pre-configured permissions** - Safe defaults for build/test/lint commands

## What Gets Generated

| File                                | Purpose                                                          |
| ----------------------------------- | ---------------------------------------------------------------- |
| `.claude/CLAUDE.md`                 | Project overview, commands, doc references                       |
| `.claude/settings.json`             | Command permissions (allow build/test, require approval for git) |
| `.claude/docs/coding-guidelines.md` | Code style and architecture guidelines                           |
| `.claude/docs/testing.md`           | Testing conventions (if test framework detected)                 |
| `.claude/docs/styling.md`           | UI/CSS guidelines (if frontend project)                          |
| `.claude/docs/architecture.md`      | Project structure documentation                                  |

## Permission Philosophy

The generated `settings.json` allows development commands (build, test, lint) while requiring explicit approval for git operations (commit, push, rebase). This ensures Claude helps with coding while leaving version control decisions to you.

See `templates/settings.json` to customize defaults.

## Skill Structure

| File | Purpose |
|------|---------|
| `SKILL.md` | Skill definition with step-by-step generation instructions |
| `templates/` | Base templates copied/customized for each project |
| `references/` | Best practices guide (based on HumanLayer research) |

To understand or modify how the skill works, start with `SKILL.md`.

## Customization

Edit files in `templates/` to change generated content. For deeper changes to the generation logic, edit `SKILL.md`.

## Credits

Best practices based on [Writing a Good CLAUDE.md](https://www.humanlayer.dev/blog/writing-a-good-claude-md) by HumanLayer.

## License

MIT
