# optimus-claude

GitHub: https://github.com/oprogramadorreal/optimus-claude

A Claude Code plugin — a collection of markdown-based skills, not a traditional coding project. All "source code" is SKILL.md files containing step-by-step instructions that Claude Code follows when a skill is invoked.

## Before making changes

Read the root README.md to understand the plugin's full capabilities — skills, agents, hooks, formatters, and how they interact. Then read CONTRIBUTING.md for project structure, skill anatomy, manifest conventions, feature branch testing, and version bumping.

## Project layout

- `.claude-plugin/` — plugin manifests (plugin.json, marketplace.json)
- `hooks/` — plugin-level hooks (SessionStart for project state awareness)
- `skills/<name>/` — one directory per skill (SKILL.md + README.md + optional templates/ and references/)
- `.claude/` — project-level Claude Code settings and hooks

## Skill-writing guidelines

See `.claude/docs/skill-writing-guidelines.md` for skill structure, design principles, and quality standards.

## Testing changes

Feature branch testing uses a two-level fetch — see CONTRIBUTING.md for the full workflow. For faster iteration, use local marketplace: `/plugin marketplace add ./path/to/optimus-claude`.

## Key rules

- Do not run `/optimus:init` on this repo — it is the plugin itself, not a target project
- Never leave a `ref` field in `marketplace.json` on the master branch
- Bump the version in `.claude-plugin/plugin.json` for meaningful changes
- Only `/optimus:init` writes `.claude/.optimus-version` in user projects — other skills that install template files must NOT update this file (it tracks init's full template audit, not individual file freshness)
