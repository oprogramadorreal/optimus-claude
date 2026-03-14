# Contributing to optimus-claude

## Project structure

```
optimus-claude/
├── .claude/                    # Claude Code settings and hooks (for contributors)
│   ├── CLAUDE.md
│   ├── settings.json
│   └── hooks/
│       └── restrict-paths.sh
├── .claude-plugin/
│   ├── plugin.json           # Plugin metadata (name, version, author)
│   └── marketplace.json      # Marketplace catalog (how Claude Code discovers the plugin)
├── hooks/
│   ├── hooks.json            # Plugin-level hooks (SessionStart for skill awareness)
│   └── session-start         # Outputs dynamic project state on session start/resume/clear/compact
├── scripts/
│   ├── validate.sh           # Structural validation (CI)
│   ├── test-hooks.sh         # Hook execution tests (CI)
│   ├── generate-fixtures.sh  # Generates minimal project fixtures for testing (local)
│   └── test-skills.sh        # Automated skill execution tests via claude -p (local)
├── skills/
│   ├── init/                 # /optimus:init
│   ├── dev-setup/            # /optimus:dev-setup
│   ├── unit-test/            # /optimus:unit-test
│   ├── simplify/             # /optimus:simplify
│   ├── code-review/          # /optimus:code-review
│   ├── tdd/                  # /optimus:tdd
│   ├── verify/               # /optimus:verify
│   ├── pr/                   # /optimus:pr
│   ├── permissions/          # /optimus:permissions
│   ├── commit/               # /optimus:commit
│   └── commit-message/       # /optimus:commit-message
├── test/
│   ├── expected-outputs.yaml # Expected outputs for skill tests
│   └── fixtures/             # Generated project fixtures (gitignored)
├── README.md
├── CONTRIBUTING.md
└── LICENSE
```

## Skill anatomy

Every skill follows the same layout:

```
skills/<skill-name>/
├── SKILL.md                  # Step-by-step instructions (the skill's "source code")
├── README.md                 # User-facing documentation
├── templates/                # YAML, markdown, and shell templates (optional)
│   ├── hooks/                # PostToolUse hook scripts
│   ├── agents/               # Agent definition files
│   └── docs/                 # Documentation templates
└── references/               # Technical reference docs consumed by the skill (optional)
                              #   e.g., agent prompt templates — externalize here instead of inlining in SKILL.md
```

**`SKILL.md`** is the key file. It starts with YAML frontmatter and contains the instructions Claude Code follows when the skill is invoked:

```yaml
---
description: Short description shown in /plugin install output
disable-model-invocation: true
---

# Skill Title

Step-by-step instructions...
```

All skills **must** use `disable-model-invocation: true`. This is a core design principle: skills are tools the user explicitly reaches for, never behavior that Claude auto-triggers. The plugin enhances Claude Code without changing its default behavior behind the user's back.

**Shared references:** When a procedure is used by 2+ skills (e.g., multi-repo workspace detection, platform detection), extract it to a reference file owned by the canonical skill. Consuming skills read the reference and apply their own policy. This avoids logic duplication while keeping each skill self-contained. See `skills/init/references/multi-repo-detection.md` and `skills/pr/references/platform-detection.md` for examples.

**Note:** The `name` field is intentionally omitted from frontmatter. When present, it strips the plugin namespace prefix — `/optimus:init` would appear as just `/init`, shadowing the builtin command. See [anthropics/claude-code#22063](https://github.com/anthropics/claude-code/issues/22063).

## Adding or modifying a skill

1. Create `skills/<skill-name>/SKILL.md` with YAML frontmatter and step-by-step instructions
2. Create `skills/<skill-name>/README.md` with user-facing documentation
3. Add templates and references as needed in subdirectories
4. Add the skill to the Skills section in the root `README.md`

Follow the conventions visible in existing skills — study `skills/commit-message/` for a minimal example or `skills/init/` for a full-featured one.

## Plugin manifests

**`plugin.json`** — plugin identity and version:

```json
{
  "name": "optimus",
  "version": "1.0.1",
  "description": "...",
  "author": { "name": "oprogramadorreal", "url": "..." },
  "license": "MIT"
}
```

**`marketplace.json`** — how Claude Code discovers the plugin in the marketplace:

```json
{
  "name": "optimus-claude",
  "plugins": [
    {
      "name": "optimus",
      "source": {
        "source": "url",
        "url": "https://github.com/oprogramadorreal/optimus-claude.git"
      }
    }
  ]
}
```

The `source` object supports an optional `"ref"` field to pin plugin code to a specific branch, tag, or SHA. This is only used during feature branch testing (see below) and must not be present on master.

## Testing

This plugin is markdown-based — traditional unit tests don't apply. Instead, testing is split into layers: fast structural checks that run in CI, and slower skill execution tests that run locally.

### Structural validation (CI)

Runs on every push and PR to master. Catches broken cross-references, syntax errors in templates, stale README entries, and other invariants.

```shell
bash scripts/validate.sh
```

Checks include:
- CRLF and shebang consistency in scripts
- SKILL.md frontmatter validity (`description`, `disable-model-invocation: true`, no `name:`)
- Every `$CLAUDE_PLUGIN_ROOT/...` path resolves to an existing file
- No orphaned files in `references/` or `templates/`
- Template scripts parse without syntax errors (bash, node, python)
- JSON templates are valid
- Every skill directory has both `SKILL.md` and `README.md`
- README lists all skills
- `hooks.json` references existing scripts
- Reference depth does not exceed 2 levels (SKILL → A → B max)

### Hook execution tests (CI)

Unit tests for the session-start hook and formatter hooks — the only executable code that runs on user machines.

```shell
bash scripts/test-hooks.sh
```

Tests all state combinations (uninitialized, partial, fully configured, dirty tree) and verifies:
- Correct recommendations for each project state
- Zero-output guarantee for fully configured projects
- Formatter hooks parse JSON input and filter by file extension correctly

### Fixture generator (local)

Generates minimal project fixtures for testing skills. No dependencies installed — just enough files for project detection to work. Output goes to `test/fixtures/` (gitignored).

```shell
bash scripts/generate-fixtures.sh              # generate all fixtures
bash scripts/generate-fixtures.sh node python   # generate specific ones
```

Available fixtures: `node`, `python`, `go`, `rust`, `csharp`, `monorepo`, `empty`, `multi-repo`.

### Skill execution tests (local)

Runs skills against generated fixtures via `claude -p` (headless mode) and validates expected outputs against `test/expected-outputs.yaml`. Requires the `claude` CLI installed and authenticated (plan subscription or API key).

```shell
bash scripts/test-skills.sh                              # default: init + commit-message
bash scripts/test-skills.sh --skill init                 # test one skill
bash scripts/test-skills.sh --skill init --fixture node  # test one skill + one fixture
bash scripts/test-skills.sh --all                        # test all skill/fixture combinations
bash scripts/test-skills.sh --dry-run                    # show what would run without executing
bash scripts/test-skills.sh --budget 2.00                # set max budget per skill invocation
```

Skills use `AskUserQuestion` for interactive decisions, which doesn't work in headless mode. The test script works around this by using `--append-system-prompt` to instruct Claude to make default choices automatically.

Not intended for CI — run locally before merging significant changes.

**Adding expected outputs:** Edit `test/expected-outputs.yaml` to define what files a skill should create and what content they should contain. The format supports `files_exist`, `files_contain`, `files_not_exist`, `files_not_modified`, and `output_contains` assertions.

## Testing a feature branch

This plugin's marketplace catalog and plugin code live in the same repository. Claude Code fetches them in two separate steps, which means testing from a feature branch requires changes at both levels:

1. **Marketplace level** — the `#branch` suffix on the git URL tells Claude Code which branch to read `marketplace.json` from
2. **Plugin source level** — the `ref` field inside `marketplace.json` tells Claude Code which branch to fetch the plugin code from

Without both, `/plugin install` would still pull plugin code from the default branch even though the marketplace was loaded from a feature branch.

### Setup (on the feature branch)

Add a `ref` to `.claude-plugin/marketplace.json` pointing to your branch:

```json
"source": {
  "source": "url",
  "url": "https://github.com/oprogramadorreal/optimus-claude.git",
  "ref": "your-branch-name"
}
```

Commit the change to your feature branch. (This change must NOT be merged to master — remove it before merging.)

### Install

Remove the existing marketplace first, then re-add with the branch suffix:

```shell
/plugin marketplace remove optimus-claude
/plugin marketplace add https://github.com/oprogramadorreal/optimus-claude.git#your-branch-name
/plugin install optimus@optimus-claude
```

> **Note:** The `owner/repo#branch` shorthand is [not yet supported](https://github.com/anthropics/claude-code/issues/23551). Use the full `.git` URL with `#branch`.

### Return to production

To switch back to the stable release from master:

```shell
/plugin marketplace remove optimus-claude
/plugin marketplace add https://github.com/oprogramadorreal/optimus-claude.git
/plugin install optimus@optimus-claude
```

### Before merging

Remove the `ref` field from `marketplace.json` so that production installs continue to use the default branch.

### Local development (faster iteration)

For rapid iteration without pushing to GitHub, add the repo as a local marketplace:

```shell
git clone https://github.com/oprogramadorreal/optimus-claude.git
cd optimus-claude && git checkout your-branch-name
# In Claude Code:
/plugin marketplace add ./path/to/optimus-claude
/plugin install optimus@optimus-claude
```

No `ref` field is needed for local paths — Claude Code reads directly from the working tree.

## Version bumping

The version in `.claude-plugin/plugin.json` affects update behavior. If two refs have the same manifest version, Claude Code may treat them as identical and skip the update. Bump the version in `plugin.json` when publishing meaningful changes.
