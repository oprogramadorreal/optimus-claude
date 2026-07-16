# Contributing to optimus-claude

## Project structure

```
optimus-claude/
├── .claude/                  # Claude Code settings, hooks, and contributor docs
├── .claude-plugin/           # Plugin manifests (plugin.json, marketplace.json)
├── agents/                   # Plugin-level agents (code-simplifier, test-guardian)
├── hooks/                    # Plugin-level hooks (SessionStart)
├── references/               # Shared reference docs consumed across skills
├── skills/<name>/            # One directory per skill
├── scripts/                  # Validation, hook tests, skill tests, harness CLI
│   └── harness_common/       # Orchestrator CLI + shared modules (/optimus:deep)
├── test/                     # pytest suites + expected outputs for skill tests
├── install.cmd / test.cmd / test-coverage.cmd
├── pyproject.toml            # pytest configuration
├── README.md / CONTRIBUTING.md / LICENSE
```

`.claude/docs/architecture.md` has the full directory map, the orchestrator
data flow, and the skill/agent/reference hierarchy.

## Skill anatomy

Every skill follows the same layout:

```
skills/<skill-name>/
├── SKILL.md                  # Step-by-step instructions (the skill's "source code")
├── README.md                 # User-facing documentation
├── templates/                # File templates the skill installs (optional)
├── agents/                   # Agent prompt files + shared-constraints.md (optional)
└── references/               # Reference docs loaded on demand (optional)
```

**`SKILL.md`** starts with YAML frontmatter and contains the instructions
Claude Code follows when the skill is invoked:

```yaml
---
description: Short third-person description — what the skill does and when to use it
disable-model-invocation: true
argument-hint: "[optional-args]"
---
```

All skills **must** use `disable-model-invocation: true` — skills are tools
users explicitly reach for, never auto-triggered. Skills that take arguments
should also set `argument-hint` (quoted — bare brackets parse as a YAML list).

**Note:** The `name` field is intentionally omitted from frontmatter. When
present, it strips the plugin namespace prefix — `/optimus:init` would appear
as just `/init`, shadowing the builtin command. See
[anthropics/claude-code#22063](https://github.com/anthropics/claude-code/issues/22063).

Before writing or changing any skill, agent, or shared reference, read
`.claude/docs/skill-writing-guidelines.md` — it is the authoring contract
(conciseness, degrees of freedom, what counts as a machine contract). For
non-markdown files (`scripts/`, `hooks/`), apply
`.claude/docs/coding-guidelines.md` instead.

## Agent architecture

The plugin uses a two-tier agent design — see
`references/agent-architecture.md`. In short: create a plugin-level agent
(`agents/`) for a reusable quality concern that multiple skills extend; create
a skill-level agent (`skills/<name>/agents/`) for one skill's workflow; extend
a plugin-level agent with a `Read $CLAUDE_PLUGIN_ROOT/agents/<name>.md` line.
Constraints shared by all analysis agents live in
`references/shared-agent-constraints.md`; skill-specific addendums go in the
skill's own `shared-constraints.md`.

## Adding or modifying a skill

1. Create `skills/<skill-name>/SKILL.md` and `README.md` (both required —
   `scripts/validate.sh` enforces it)
2. Add templates, references, and agents as needed in subdirectories — every
   file there must be referenced from a skill `.md` file (orphan check)
3. Add the skill to the Skills table in the root `README.md` —
   `scripts/validate.sh` asserts every `skills/` directory appears there
4. Run `bash scripts/validate.sh` before pushing

Study `skills/reset/` for a compact example or `skills/init/` for a
full-featured one (templates, references, agents).

## Plugin manifests

**`plugin.json`** — plugin identity and version (name, version, description,
author, license).

**`marketplace.json`** — how Claude Code discovers the plugin. Its `source`
object supports an optional `"ref"` field to pin plugin code to a branch, tag,
or SHA. This is only used during feature-branch testing (below) and **must not
be present on master** (validated).

## Testing

Testing is split into layers: fast structural checks, hook tests, and Python
unit tests run in CI; slower skill execution tests run locally. Commands live
in `.claude/CLAUDE.md` ("Commands") — the full suite is:

```shell
bash scripts/validate.sh && bash scripts/test-hooks.sh && python -m pytest test/
```

### Structural validation (CI) — `scripts/validate.sh`

Catches broken cross-references, invalid frontmatter, orphaned files, template
syntax errors, stale README entries, manifest problems, reference-depth
violations, and the spec↔tdd scenario heading contract.

### Hook execution tests (CI) — `scripts/test-hooks.sh`

Unit tests for the SessionStart hook, the formatter hook templates, and the
restrict-paths guardrail hook — the executable code that runs on user machines.

### Python unit tests (CI) — `python -m pytest test/`

The orchestrator CLI and its modules under `scripts/harness_common/`
(`test/harness-common/`), plus the repo's own `format-python.py` hook.
First-time setup: `install.cmd`. See `.claude/docs/testing.md` for conventions.

### Skill execution tests (local) — `scripts/test-skills.sh`

Runs skills against generated fixtures via `claude -p` (headless) and validates
results against `test/expected-outputs.yaml`. Requires an authenticated
`claude` CLI; not run in CI.

```shell
bash scripts/generate-fixtures.sh                        # generate fixtures (test/fixtures/, gitignored)
bash scripts/test-skills.sh                              # default: init on node + python fixtures
bash scripts/test-skills.sh --fresh --all --worktree     # clean + regenerate + all, in an isolated worktree
bash scripts/test-skills.sh --dry-run                    # show what would run
```

The `--worktree` flag runs everything in `.worktrees/skill-tests` so you can
keep working in the main tree; on failure the worktree is preserved for
debugging. Skills use `AskUserQuestion` for interactive decisions, which
doesn't work headless — the script uses `--append-system-prompt` to instruct
Claude to make default choices. Assertions in `expected-outputs.yaml` are
structural (`files_exist`, `files_not_modified`, …) — don't pin template prose.

**Before merging significant changes**, run
`bash scripts/test-skills.sh --fresh --all --worktree`.

## Testing a feature branch

The marketplace catalog and plugin code live in the same repository, and
Claude Code fetches them in two separate steps — testing from a feature branch
requires changes at both levels:

1. **Marketplace level** — the `#branch` suffix on the git URL tells Claude
   Code which branch to read `marketplace.json` from
2. **Plugin source level** — the `ref` field inside `marketplace.json` tells
   Claude Code which branch to fetch the plugin code from

### Setup (on the feature branch)

Add a `ref` to `.claude-plugin/marketplace.json` pointing to your branch:

```json
"source": {
  "source": "url",
  "url": "https://github.com/oprogramadorreal/optimus-claude.git",
  "ref": "your-branch-name"
}
```

Commit it to the feature branch — and **remove it before merging to master**.

### Install

```shell
/plugin marketplace remove optimus-claude
/plugin marketplace add https://github.com/oprogramadorreal/optimus-claude.git#your-branch-name
/plugin install optimus@optimus-claude
```

> **Note:** The `owner/repo#branch` shorthand is
> [not yet supported](https://github.com/anthropics/claude-code/issues/23551).
> Use the full `.git` URL with `#branch`.

To return to production, remove the marketplace and re-add it without the
`#branch` suffix.

### Local development (faster iteration)

For rapid iteration without pushing, add the repo as a local marketplace:

```shell
/plugin marketplace add ./path/to/optimus-claude
/plugin install optimus@optimus-claude
```

No `ref` field is needed for local paths — Claude Code reads the working tree.

## Version bumping

The version in `.claude-plugin/plugin.json` affects update behavior: if two
refs have the same manifest version, Claude Code may treat them as identical
and skip the update. Bump the version when publishing meaningful changes, and
update the version badge in `README.md` to match (validated on branches).
