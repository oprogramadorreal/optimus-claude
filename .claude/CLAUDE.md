# optimus-claude

GitHub: https://github.com/oprogramadorreal/optimus-claude

A Claude Code plugin — a collection of markdown-based skills, not a traditional coding project. All "source code" is SKILL.md files containing step-by-step instructions that Claude Code follows when a skill is invoked.

## Before making changes

Read the root README.md to understand the plugin's full capabilities — skills, agents, hooks, formatters, and how they interact. Then read CONTRIBUTING.md for project structure, skill anatomy, manifest conventions, feature branch testing, and version bumping.

## Project layout

- `.claude-plugin/` — plugin manifests (plugin.json, marketplace.json)
- `agents/` — plugin-level agent definitions (code-simplifier, test-guardian)
- `hooks/` — plugin-level hooks (SessionStart for project state awareness)
- `references/` — shared reference docs consumed across skills (agent-architecture, shared-agent-constraints, context-injection-blocks, harness-mode, coverage-harness-mode, scope-expansion-rule)
- `skills/<name>/` — one directory per skill (SKILL.md + README.md + optional agents/, templates/, and references/)
- `scripts/` — validation and test scripts (CI and local)
- `scripts/harness_common/` — shared modules used by both harnesses
- `scripts/deep-mode-harness/` — deep-mode harness orchestrator
- `scripts/test-coverage-harness/` — test-coverage harness orchestrator
- `test/` — expected outputs and generated fixtures for skill tests
- `test/harness-common/` — tests for shared harness modules
- `test/deep-mode-harness/` — tests for the deep-mode harness
- `test/test-coverage-harness/` — tests for the test-coverage harness
- `.claude/` — project-level Claude Code settings and hooks

## Commands

```bash
bash scripts/validate.sh && bash scripts/test-hooks.sh && python -m pytest test/harness-common/ test/deep-mode-harness/ test/test-coverage-harness/   # Run tests
```

For coverage: `python -m pytest test/harness-common/ test/deep-mode-harness/ test/test-coverage-harness/ --cov scripts/harness_common --cov scripts/deep-mode-harness/impl --cov scripts/test-coverage-harness --cov-report=term-missing`

Or use the batch scripts: `test.cmd` (tests), `test-coverage.cmd` (coverage + HTML report in htmlcov/).
First-time setup: `install.cmd` (creates `.venv` and installs dev dependencies).

## Skill-writing guidelines

See `.claude/docs/skill-writing-guidelines.md` for skill structure, design principles, and quality standards. `.claude/docs/coding-guidelines.md` covers code quality principles for non-markdown files (scripts, hooks, harness code). `.claude/docs/architecture.md` documents the directory map, harness data flow, module dependencies, and skill/agent/reference hierarchy. A `.claude/docs/testing.md` bridge file also exists so that `/optimus:unit-test`, the code-review test-guardian agent, and the SessionStart hook can discover this repo's pytest conventions through the standard doc-loading path.

## Testing changes

See CONTRIBUTING.md for the full testing workflow (validation, hooks, fixtures, skill execution) and the feature branch testing workflow.

## Key rules

- Never leave a `ref` field in `marketplace.json` on the master branch
- Bump the version in `.claude-plugin/plugin.json` for meaningful changes, and update the version badge in `README.md` to match
- Only `/optimus:init` writes `.claude/.optimus-version` in user projects — other skills that install template files must NOT update this file (it tracks init's full template audit, not individual file freshness)
