# optimus-claude

GitHub: https://github.com/oprogramadorreal/optimus-claude

A Claude Code plugin — a collection of markdown-based skills, not a traditional coding project. All "source code" is SKILL.md files containing step-by-step instructions that Claude Code follows when a skill is invoked.

## Before making changes

Read the root README.md to understand the plugin's full capabilities — skills, agents, hooks, formatters, and how they interact. Then read CONTRIBUTING.md for project structure, skill anatomy, manifest conventions, feature branch testing, and version bumping.

## Project layout

- `.claude-plugin/` — plugin manifests (plugin.json, marketplace.json)
- `skills/<name>/` — one directory per skill (SKILL.md + README.md + optional templates/ and references/)
- `.claude/` — project-level Claude Code settings and hooks

## Skill conventions

- Every SKILL.md starts with YAML frontmatter: `description` and `disable-model-invocation: true`
- Skills are imperative step-by-step instructions, not conversational prose
- Study `skills/commit-message/` for a minimal example; `skills/init/` for a full one
- Templates go in `templates/`, reference docs in `references/`
- Add new skills to the table in `README.md`

## Testing changes

Feature branch testing uses a two-level fetch — see CONTRIBUTING.md for the full workflow. For faster iteration, use local marketplace: `/plugin marketplace add ./path/to/optimus-claude`.

## Key rules

- Do not run `/optimus:init` on this repo — it is the plugin itself, not a target project
- Never leave a `ref` field in `marketplace.json` on the master branch
- All skills must use `disable-model-invocation: true`
- Bump the version in `.claude-plugin/plugin.json` for meaningful changes
- Do not add a `name` field to SKILL.md frontmatter — it strips the plugin namespace prefix ([anthropics/claude-code#22063](https://github.com/anthropics/claude-code/issues/22063))
- `coding-guidelines.md` is the single source of truth for code quality rules — skills and agents must reference it, never duplicate its principles inline
- After any skill change, verify that the root README.md and the skill's README.md still reflect current behavior
