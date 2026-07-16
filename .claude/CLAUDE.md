# optimus-claude

GitHub: https://github.com/oprogramadorreal/optimus-claude

A Claude Code plugin — a collection of markdown-based skills plus a Python
orchestration harness. Most "source code" is SKILL.md files containing the
instructions Claude Code follows when a skill is invoked.

## Read before editing

- Skills, agents, or shared references (any `.md` under `skills/`, `agents/`,
  or `references/`): read `.claude/docs/skill-writing-guidelines.md` first.
- Python, shell, or hook code (`scripts/`, `hooks/`): read
  `.claude/docs/coding-guidelines.md`; testing conventions are in
  `.claude/docs/testing.md`.
- Orchestrator/harness data flow and the skill/agent/reference hierarchy:
  `.claude/docs/architecture.md`.
- Contribution process (skill anatomy, manifests, feature-branch testing,
  version bumping): `CONTRIBUTING.md`.

## Project layout

- `.claude-plugin/` — plugin manifests (plugin.json, marketplace.json)
- `agents/` — plugin-level agent definitions (code-simplifier, test-guardian)
- `hooks/` — plugin-level SessionStart hook
- `references/` — shared reference docs consumed across skills
- `skills/<name>/` — one directory per skill (SKILL.md + README.md + optional
  agents/, templates/, references/)
- `scripts/harness_common/` — shared modules + `cli.py` invoked by `/optimus:deep`
- `test/` — pytest suites (`harness-common/` for the CLI, plus the formatter
  hook test) and `expected-outputs.yaml` for skill execution tests

## Commands

```bash
bash scripts/validate.sh && bash scripts/test-hooks.sh && python -m pytest test/   # Run tests
```

For coverage: `python -m pytest test/harness-common/ --cov scripts/harness_common --cov-report=term-missing`

Or use the batch scripts: `test.cmd` (tests), `test-coverage.cmd` (coverage +
HTML report in htmlcov/). First-time setup: `install.cmd` (creates `.venv` and
installs dev dependencies).

## Key rules

- Never leave a `ref` field in `marketplace.json` on the master branch
- Bump the version in `.claude-plugin/plugin.json` for meaningful changes, and
  update the version badge in `README.md` to match
- Only `/optimus:init` writes `.claude/.optimus-version` in user projects —
  other skills must never touch it
- Harness protocol strings (JSON schemas in `references/harness-mode.md` /
  `coverage-harness-mode.md`, status vocabulary in
  `references/context-injection-blocks.md`) are machine contracts with
  `scripts/harness_common/` — change them only together with the CLI and its
  tests
