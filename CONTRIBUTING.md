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
├── skills/
│   ├── init/                 # /optimus:init
│   ├── unit-test/            # /optimus:unit-test
│   ├── simplify/             # /optimus:simplify
│   ├── code-review/          # /optimus:code-review
│   ├── tdd/                  # /optimus:tdd
│   ├── permissions/          # /optimus:permissions
│   └── commit-message/       # /optimus:commit-message
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

All current skills use `disable-model-invocation: true` — they operate through structured, human-reviewed templates rather than dynamic LLM generation.

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
