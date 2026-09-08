# optimus-claude

GitHub: https://github.com/oprogramadorreal/optimus-claude

A Claude Code plugin whose source is markdown: `SKILL.md` files are instructions a model executes, not documentation about code that runs. Edit them as prompts, not as prose.

Test command: `bash scripts/validate.sh && bash scripts/test-hooks.sh && python -m pytest test/`

## Where to look

Load the doc that matches the change — not all of them.

| Changing | Read first |
|---|---|
| A skill, agent, or shared reference (`skills/`, `agents/`, `references/`) | `.claude/docs/skill-writing-guidelines.md` |
| Scripts or hooks (`scripts/`, `hooks/`) | `.claude/docs/coding-guidelines.md` |
| Tests, or anything under `scripts/harness_common/` | `.claude/docs/testing.md` |
| Directory map, orchestrator data flow, reference hierarchy | `.claude/docs/architecture.md` |
| Contribution workflow, skill anatomy, feature-branch testing, version bumping | `CONTRIBUTING.md` |

## Key rules

- Never leave a `ref` field in `marketplace.json` on the master branch
- Bump the matching versions in `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` for meaningful changes, and update the version badge in `README.md` to match
- Only `/optimus:init` writes `.claude/.optimus-version` in user projects — other skills that install template files must NOT update this file (it tracks init's full template audit, not individual file freshness)
