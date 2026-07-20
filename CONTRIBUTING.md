# Contributing to optimus-claude

## Project structure

```
optimus-claude/
├── .claude/                    # Claude Code settings and hooks (for contributors)
│   ├── CLAUDE.md
│   ├── settings.json
│   ├── docs/                  # Contributor guidelines (skill-writing, coding, architecture, testing)
│   └── hooks/
│       ├── format-python.py
│       └── restrict-paths.sh
├── .claude-plugin/
│   ├── plugin.json           # Plugin metadata (name, version, author)
│   └── marketplace.json      # Marketplace catalog (how Claude Code discovers the plugin)
├── agents/                    # Plugin-level agents — standalone, user-invokable quality agents
│   ├── code-simplifier.md     # Code simplification agent
│   ├── test-guardian.md       # Test coverage monitoring agent
├── references/                # Shared reference docs consumed across skills (see the Reference Hierarchy in .claude/docs/architecture.md)
├── hooks/
│   ├── hooks.json            # Plugin-level hooks (SessionStart for skill awareness)
│   └── session-start         # Outputs dynamic project state on session start/resume/clear/compact
├── scripts/
│   ├── validate.sh           # Structural validation (CI)
│   ├── test-hooks.sh         # Hook execution tests (CI)
│   ├── generate-fixtures.sh  # Generates minimal project fixtures for testing (local)
│   ├── test-skills.sh        # Automated skill execution tests via claude -p (local)
│   └── harness_common/       # Shared modules + cli.py invoked by the /optimus:deep orchestrator skill
│       ├── cli.py            # Subcommand CLI (init, snapshot, deep-step, etc.)
│       ├── findings.py       # Status escalation state machine
│       ├── convergence.py    # Coverage convergence checks
│       ├── fixes.py          # Apply / revert / bisect (mechanical, content-based)
│       ├── git.py            # Checkpoint commits, stash, branch-base detection, PR fetch
│       ├── parser.py         # JSON-block extraction from subagent output
│       ├── progress.py       # JSON read/write/backup
│       ├── runner.py         # Test runner with platform-aware bash routing
│       ├── reporting.py      # Cumulative report printing + commit-body builders (also test-command detection)
│       └── constants.py      # Shared status / cap constants
├── skills/
│   ├── init/                 # /optimus:init
│   ├── how-to-run/           # /optimus:how-to-run
│   ├── unit-test/            # /optimus:unit-test
│   ├── refactor/             # /optimus:refactor
│   ├── code-review/          # /optimus:code-review
│   ├── deep/                 # /optimus:deep (review | refactor | coverage)
│   ├── tdd/                  # /optimus:tdd
│   ├── pr/                   # /optimus:pr
│   ├── prompt/               # /optimus:prompt
│   ├── permissions/          # /optimus:permissions
│   ├── reset/                # /optimus:reset
│   ├── worktree/             # /optimus:worktree
│   ├── commit/               # /optimus:commit (default | suggest | branch)
│   ├── brainstorm/           # /optimus:brainstorm (design | scaffold)
│   ├── handoff/              # /optimus:handoff
│   └── jira/                 # /optimus:jira
├── test/
│   ├── expected-outputs.yaml # Expected outputs for skill tests
│   ├── harness-common/       # Python unit tests for the harness CLI and shared modules
│   └── fixtures/             # Generated project fixtures (gitignored)
├── requirements-dev.txt      # Python dev dependencies (pytest, pytest-cov, black, isort)
├── install.cmd               # Create .venv and install dev dependencies
├── test.cmd                  # Run Python unit tests
├── test-coverage.cmd         # Run Python tests with coverage report
├── pyproject.toml            # pytest configuration (importlib import mode)
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
│   └── docs/                 # Documentation templates
├── agents/                   # Individual agent prompt files, one per agent plus shared-constraints.md (optional)
└── references/               # Technical reference docs consumed by the skill (optional)
```

**`SKILL.md`** is the key file. It starts with YAML frontmatter and contains the instructions Claude Code follows when the skill is invoked:

```yaml
---
description: Short description shown in /plugin install output
disable-model-invocation: true
argument-hint: "[optional-args]"
---

# Skill Title

Step-by-step instructions...
```

All skills **must** use `disable-model-invocation: true`. Skills that take arguments should also set `argument-hint` (quoted — bare brackets parse as a YAML list); it is shown in the `/` menu autocomplete. The rationale for this rule lives in `.claude/docs/skill-writing-guidelines.md` under Structure.

**Shared references:** when a procedure is used by 2+ skills, extract it to a reference file owned by the canonical skill — see `.claude/docs/skill-writing-guidelines.md` under Structure for the rule.

**Note:** The `name` field is intentionally omitted from frontmatter. When present, it strips the plugin namespace prefix — `/optimus:init` would appear as just `/init`, shadowing the builtin command. See [anthropics/claude-code#22063](https://github.com/anthropics/claude-code/issues/22063).

## Agent architecture

Two tiers, no inheritance. **Plugin-level agents** (`agents/`) are standalone, user-invokable quality agents. **Skill-level agents** (`skills/<name>/agents/`) are self-contained prompt files a SKILL.md launches via the Agent tool — each carries its own criteria inline. Shared behavioral rules live once in `references/shared-agent-constraints.md`; a skill's own `agents/shared-constraints.md` holds only genuine addendums plus the skill's canonical output format. The dispatch-time path-substitution rule is in `references/agent-architecture.md`.

## Adding or modifying a skill

1. Create `skills/<skill-name>/SKILL.md` with YAML frontmatter and step-by-step instructions
2. Create `skills/<skill-name>/README.md` with user-facing documentation
3. Add templates and references as needed in subdirectories
4. Add the skill to the Skills section in the root `README.md`
5. Add the skill directory to the project-structure tree in this file — `scripts/validate.sh` asserts every `skills/` directory appears in both the root `README.md` and this tree

Follow the conventions visible in existing skills — study `skills/worktree/` for a minimal example or `skills/init/` for a full-featured one.

### Output tone and formatting

The content rules for skill bodies (no decorative emoji in output templates, no hand-rolled "[Step N/M]" progress indicators, imperative fan-out counts for parallel-agent steps) live in `.claude/docs/skill-writing-guidelines.md` under "Writing Style".

## Skill-authoring projects as a stack

`/optimus:init` detects **skill authoring** as a first-class stack alongside Python, Node, Rust, Go, UI frameworks, and so on. The detection signal is structural: a directory named `skills/`, `agents/`, `prompts/`, `commands/`, or `instructions/` at the repo root — and for monorepos, also at each detected subproject root — containing ≥2 subdirectories, every such subdirectory holding a file named `SKILL.md`, `AGENT.md`, `PROMPT.md`, `COMMAND.md`, or `INSTRUCTION.md` (case-insensitive). When detected, init installs `.claude/docs/skill-writing-guidelines.md` from its framework-agnostic template, and the shared `skills/init/references/constraint-doc-loading.md` reference automatically routes review/refactor skills to use that lens for markdown instruction files while keeping `coding-guidelines.md` as the lens for code files.

This means optimus supports Claude Code plugins (including optimus-claude itself), Codex skill repos, prompt libraries, custom agent frameworks, and any other project whose "source code" is markdown instructions authored for an AI agent.

For the full routing rules, see the "Skill authoring lens" section of `skills/init/references/constraint-doc-loading.md`. For the template content installed into skill-authoring projects, see `skills/init/templates/docs/skill-writing-guidelines.md`.

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

This plugin is mostly markdown-based. Testing is split into layers: fast structural checks, hook tests, and Python unit tests that run in CI, and slower skill execution tests that run locally.

**Before merging significant changes**, run the full skill test suite from a clean slate:

```shell
bash scripts/test-skills.sh --fresh --all --worktree
```

This removes existing fixtures, regenerates them, and runs all skill/fixture combinations end-to-end via `claude -p`. The `--worktree` flag runs everything in `.worktrees/skill-tests` inside the project directory so you can freely switch branches or edit files in the main tree while tests execute in the isolated worktree — and easily inspect the worktree from your IDE. See the subsections below for individual test layers and finer-grained options.

### Structural validation (CI)

Runs on every push and PR to master. Catches broken cross-references, syntax errors in templates, stale README entries, and other invariants.

```shell
bash scripts/validate.sh
```

Checks include:
- CRLF and shebang consistency in scripts
- SKILL.md frontmatter validity (`description`, `disable-model-invocation: true`, no `name:`)
- Every `$CLAUDE_PLUGIN_ROOT/...` path resolves to an existing file
- No orphaned files in `references/`, `templates/`, or `agents/`
- Template scripts parse without syntax errors (bash, node, python)
- JSON templates are valid
- Every skill directory has both `SKILL.md` and `README.md`
- README lists all skills
- `hooks.json` references existing scripts
- Plugin-level agent files have required frontmatter fields
- Reference depth does not exceed 2 levels (SKILL → A → B max)
- `.claude/hooks/restrict-paths.sh` is byte-identical to the template users install
- The restrict-paths template declares a `HOOK_VERSION` (bump it on every behavioural change — the SessionStart hook uses it to spot projects running a stale copy)

### Hook execution tests (CI)

Unit tests for the session-start hook, formatter hooks, and the path-restriction hook — the hook scripts that run on user machines.

```shell
bash scripts/test-hooks.sh
```

Tests all state combinations (uninitialized, partial, fully configured, dirty tree) and verifies:
- Correct recommendations for each project state
- Zero-output guarantee for fully configured projects
- Formatter hooks parse JSON input and filter by file extension correctly
- restrict-paths hook enforces the tiered path model (in-project writes allowed, out-of-project writes ask, outside deletes denied) with memory-store/scratchpad exemptions and fail-closed fallbacks
- Temp-write nudge: a new file under the OS temp root still asks (never denies — a deny cannot be approved by the user) and carries the scratchpad reminder in `additionalContext`, the field Claude reads, not in the user-facing reason; existing files and `~/.claude` keep the plain prompt
- Platform path shapes the exemptions must survive: trailing-slash temp root, a realpath that rejects `-m`, and a realpath that is absent entirely (the cd/pwd fallback, reached by overriding the `command` builtin — a stripped PATH breaks bash on Windows)
- Fail-closed gates: unresolved `..` at every rung of the exemption ladder including the project root, relative and root temp roots rejected, UNC temp roots accepted, dot segments rejected in both single-segment slots, and an unset HOME that must not anchor the memory store on the hook's CWD
- `//`-leading paths follow the platform's own realpath rather than a hardcoded verdict, so the suite passes on both Cygwin and Linux
- SessionStart flags an installed `restrict-paths.sh` whose `HOOK_VERSION` is behind the plugin's
- Every verdict is scored from the hook's exit status as well as its output, so a hook that dies before printing scores CRASH rather than being mistaken for a silent allow; a self-check pins that guard

### Python unit tests (CI)

Unit tests for the Python code in the repo: the orchestrator CLI and its supporting modules under `scripts/harness_common/`, plus the `.claude/hooks/format-python.py` formatter hook.

**First-time setup:**

```shell
install.cmd                    # creates .venv and installs dev dependencies
```

**Run tests:**

```shell
test.cmd                       # run all Python unit tests
test-coverage.cmd              # run with coverage (HTML report in htmlcov/)
```

Or manually via pytest:

```shell
.venv\Scripts\activate
python -m pytest test/ -v
```

**Note:** The project uses `pyproject.toml` with `--import-mode=importlib` (kept for general robustness against same-name modules across test trees).

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
bash scripts/test-skills.sh                              # default: init + commit-suggest
bash scripts/test-skills.sh --skill init                 # test one skill
bash scripts/test-skills.sh --skill init --fixture node  # test one skill + one fixture
bash scripts/test-skills.sh --all                        # test all skill/fixture combinations
bash scripts/test-skills.sh --fresh --all                # clean + regenerate fixtures + test all
bash scripts/test-skills.sh --fresh --all --worktree     # same, in an isolated worktree
bash scripts/test-skills.sh --dry-run                    # show what would run without executing
```

Skills use `AskUserQuestion` for interactive decisions, which doesn't work in headless mode. The test script works around this by using `--append-system-prompt` to instruct Claude to make default choices automatically.

Not intended for CI — run locally before merging significant changes.

**`--worktree` flag:** Creates a detached git worktree at `.worktrees/skill-tests` from `HEAD`, runs the entire test suite there, and cleans up the worktree on success. On failure, the worktree is preserved for debugging — the script prints the path and a cleanup command. A subsequent run with `--worktree` automatically removes stale worktrees from previous failed runs. This snapshots the code at the current commit so you can freely switch branches, edit plugin files, or start new work in the main tree while the tests run — and the worktree stays visible in your IDE for easy inspection. Combine with any other flags (`--fresh`, `--all`, `--skill`, etc.).

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

The version in `.claude-plugin/plugin.json` affects update behavior. If two refs have the same manifest version, Claude Code may treat them as identical and skip the update. Bump the version in `plugin.json` when publishing meaningful changes, and update the version badge in `README.md` to match.
