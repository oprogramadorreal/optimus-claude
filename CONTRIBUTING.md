# Contributing to optimus-claude

## Project structure

```
optimus-claude/
├── skills/
│   ├── init/                 # /optimus:init
│   ├── how-to-run/           # /optimus:how-to-run
│   ├── unit-test/            # /optimus:unit-test
│   ├── refactor/             # /optimus:refactor
│   ├── code-review/          # /optimus:code-review
│   ├── deep/                 # /optimus:deep (review | refactor | coverage)
│   ├── gauntlet/             # /optimus:gauntlet
│   ├── tdd/                  # /optimus:tdd
│   ├── pr/                   # /optimus:pr
│   ├── prompt/               # /optimus:prompt
│   ├── permissions/          # /optimus:permissions
│   ├── reset/                # /optimus:reset
│   ├── worktree/             # /optimus:worktree
│   ├── commit/               # /optimus:commit (default | suggest | branch)
│   ├── brainstorm/           # /optimus:brainstorm (design | scaffold)
│   ├── handoff/              # /optimus:handoff
│   ├── dream/                # /optimus:dream
│   ├── jira/                 # /optimus:jira
│   └── paper-init/           # /optimus:paper-init
└── scripts/harness_common/    # orchestrator CLI: cli.py plus findings, convergence,
                              # fixes, git, parser, progress, runner, reporting, constants
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
├── agents/
│   ├── openai.yaml           # Codex twin of disable-model-invocation (required; validate.sh checks it)
│   └── *.md                  # Agent prompt files, one per agent plus shared-constraints.md (optional)
└── references/               # Technical reference docs consumed by the skill (optional)
```

**`SKILL.md`** is the key file. It starts with YAML frontmatter and contains the instructions Claude Code follows when the skill is invoked:

Frontmatter rules — including why there is no `name:` field — are in `.claude/docs/skill-writing-guidelines.md` under Structure, and `scripts/validate.sh` enforces them.

## Agent architecture

Two tiers, no inheritance. The rules — and the dispatch-time path-substitution requirement — are in `.claude/docs/skill-writing-guidelines.md` under Agents and in `references/agent-architecture.md`.

## Adding or modifying a skill

1. Create `skills/<skill-name>/SKILL.md` with YAML frontmatter and step-by-step instructions
2. Create `skills/<skill-name>/README.md` with user-facing documentation
3. Copy any sibling's `agents/openai.yaml` — it tells Codex the skill never auto-triggers, the way `disable-model-invocation: true` tells Claude Code
4. Add templates and references as needed in subdirectories
5. Add the skill to the Skills section in the root `README.md`
6. Add the skill directory to the project-structure tree in this file — `scripts/validate.sh` asserts every `skills/` directory appears in both the root `README.md` and this tree

Follow the conventions visible in existing skills — study `skills/worktree/` for a minimal example or `skills/init/` for a full-featured one.

## Skill-authoring projects as a stack

`/optimus:init` detects **skill authoring** as a first-class stack alongside Python, Node, Rust, Go, UI frameworks, and so on. The detection signal is structural: a directory named `skills/`, `agents/`, `prompts/`, `commands/`, or `instructions/` at the repo root — and for monorepos, also at each detected subproject root — containing ≥2 subdirectories, every such subdirectory holding a file named `SKILL.md`, `AGENT.md`, `PROMPT.md`, `COMMAND.md`, or `INSTRUCTION.md` (case-insensitive). When detected, init installs `.claude/docs/skill-writing-guidelines.md` from its framework-agnostic template, and the shared `skills/init/references/constraint-doc-loading.md` reference automatically routes review/refactor skills to use that lens for markdown instruction files while keeping `coding-guidelines.md` as the lens for code files.

This means optimus supports Claude Code plugins (including optimus-claude itself), Codex skill repos, prompt libraries, custom agent frameworks, and any other project whose "source code" is markdown instructions authored for an AI agent.

The routing rule itself lives in `references/shared-agent-constraints.md` under Dual Lens; the template installed into skill-authoring projects is `skills/init/templates/docs/skill-writing-guidelines.md`.

## Plugin manifests

`.claude-plugin/plugin.json` carries the plugin identity and version; bump it for any meaningful change and update the version badge in `README.md` to match — `validate.sh` asserts the two agree on PR branches.

`.claude-plugin/marketplace.json` is how Claude Code discovers the plugin. Its `source` object accepts an optional `ref` to pin plugin code to a branch, tag, or SHA; that is only for the feature-branch testing flow below, and `validate.sh` fails while it is present.

`.agents/plugins/marketplace.json` is the same catalog for OpenAI Codex. Codex reads it before the Claude one, installs the plugin from `./`, and accepts `.claude-plugin/plugin.json` as a legacy manifest — one manifest, one version. `validate.sh` pins the plugin name across the catalogs. Codex runs the shared `hooks/hooks.json` after the user trusts it. Its command launches Bash directly, falling back to Git for Windows' bundled shell when necessary. The fallback restores the invoking directory through `GIT_PREFIX`; `.claude/docs/architecture.md` explains the cross-host constraints on this command.

## Testing

This plugin is mostly markdown-based. Testing is split into layers: fast structural checks, hook tests, and Python unit tests that run in CI, and slower skill execution tests that run locally.

**Before merging significant changes**, run the full skill test suite from a clean slate:

```shell
bash scripts/test-skills.sh --fresh --all --worktree
```

This removes existing fixtures, regenerates them, and runs all skill/fixture combinations end-to-end via `claude -p`. The `--worktree` flag runs everything in `.worktrees/skill-tests` inside the project directory so you can freely switch branches or edit files in the main tree while tests execute in the isolated worktree — and easily inspect the worktree from your IDE. See the subsections below for individual test layers and finer-grained options.

### Structural validation (CI)

Runs on every push and PR to master. Catches broken cross-references, syntax errors in templates, stale README entries, and other invariants.

Install `requirements-dev.txt` in your development environment first and activate it. Skill frontmatter and `agents/openai.yaml` are parsed by `scripts/validate_skill_metadata.py`; missing Python or PyYAML fails this check rather than silently skipping invocation-policy validation. CI installs the same requirements.

```shell
bash scripts/validate.sh
```

Every check prints its own name as it runs, so the script is the list. Two invariants a contributor has to know before editing it: section 17 pins only strings a program parses or that cross a conversation boundary — never the wording of a skill's own instructions — and the dogfooded hooks must stay byte-identical to the templates users install — `.claude/hooks/restrict-paths.sh` (with `HOOK_VERSION` bumped on every behavioural change, so the SessionStart hook can spot projects running a stale copy) and `.claude/hooks/format-python.sh`. Fix both copies or neither: a template-only fix leaves this repo running stale logic, and a `.claude/`-only fix ships nothing to users.

### Hook execution tests (CI)

Unit tests for the session-start hook, formatter hooks, and the path-restriction hook — the hook scripts that run on user machines.

```shell
bash scripts/test-hooks.sh
```

Each assertion names itself in the output. The rationale for individual guards lives next to the code they protect — the `set -f` block in `collapse_dot_segments` is the one worth reading before touching path handling. Note that every verdict is scored from the hook's exit status as well as its output, so a hook that dies before printing scores CRASH rather than passing as a silent allow.

### Python unit tests (CI)

Unit tests for the orchestrator CLI and its supporting modules under `scripts/harness_common/`, plus the `.claude/hooks/format-python.sh` formatter hook.

**First-time setup:**

```shell
install.cmd                    # Windows: creates .venv and installs dev dependencies
```

There is no `install.sh`; on macOS/Linux run `python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt`. The formatter-hook tests shell out to `bash`, so Windows contributors need Git Bash on PATH — the module resolves it via `harness_common.runner._find_bash`, which deliberately skips a WSL `bash` since it cannot open Windows-style paths.

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

### Codex smoke test (local)

Codex support is best-effort and has no end-to-end model execution in CI; metadata and launcher tests do run there. Run this checklist on throwaway projects before the first Codex release, then once per minor release and whenever hooks, packaging, instruction routing, or agent dispatch changes. Record the date, plugin commit/version, Codex version, OS, and pass/fail/untested outcome for each item in the PR. Verify the advertised minimum CLI version as well as a current one before treating the minimum as tested.

1. **Install and trust** — `/plugin marketplace add oprogramadorreal/optimus-claude@<branch>`, enable `optimus` from `/plugins`, and review/trust its hooks. Start a fresh session and confirm the skill list and `[optimus] Running under Codex` line.
2. **Invocation and paths** — `$optimus:commit suggest` in a repo with a change: the skill loads, and the model finds `skills/commit/references/…` from its `$CLAUDE_PLUGIN_ROOT` reference.
3. **Hook and cwd** — start in an uninitialized repo, then in a nested directory with different project state: notices must describe the starting directory. On Windows, repeat with only `Git\cmd` and `System32` on PATH. No automatic-formatting promise or suggestion to run `$optimus:permissions` should appear.
4. **Init, routing, and reset** — run `$optimus:init` on a monorepo with distinct package commands. Start fresh sessions at root and inside a package; confirm both read the relevant existing CLAUDE.md files. Re-run init with an older pointer and user-authored `AGENTS.md` text/comments; verify the block is updated once and surrounding content survives. Repeat at a multi-repo workspace root and inside a child repo. Reset must remove the marked blocks and preserve all user content. Confirm Codex init installs no formatter hooks and leaves existing hooks/settings intact.
5. **Fan-out** — `$optimus:code-review` on a diff large enough for parallel lenses. Exercise more lenses than available subagent slots; verify no lens is lost when capacity is reached. Record the configured capacity and whether completed agents are closed/reused before later work.
6. **Harness and resume** — `$optimus:deep review --yes src/<path>`: verify plugin paths, nested dispatch, JSON parsing, fixes, test execution, and checkpoints across multiple iterations. Interrupt between iterations and resume in a fresh session with `--resume`; compare the on-disk state and final report. Exercise coverage's paired phases separately.
7. **Headless** — after granting the required hook trust and filesystem/Git permissions, run the README's `codex exec --sandbox workspace-write` example in an initialized fixture. Confirm writes and test runs actually happen; `--yes` must not be mistaken for a host permission grant. Record any remaining approval failure rather than bypassing the sandbox.
8. **Auto-trigger and exclusions** — ask a plain question matching a skill description ("write a commit message for this"); the skill must not auto-trigger. Explicit `permissions`/`dream` requests must explain the limitation without modifying Claude configuration or memory. Claude `/goal` and `/workflows` handoffs must not be offered as Codex features.
9. **Claude Code regression** — `claude --plugin-dir .` still fires the hook, including from a subdirectory. Check at least one Unix host and Windows; `bash scripts/validate.sh`, `bash scripts/test-hooks.sh`, and `python -m pytest test/` must pass apart from independently documented pre-existing failures.

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

### Codex

Codex takes the branch on the marketplace-add command and installs the plugin from that same checkout, so no `ref` edit is needed:

```shell
/plugin marketplace add oprogramadorreal/optimus-claude@your-branch-name
```

## Version bumping

The version in `.claude-plugin/plugin.json` affects update behavior. If two refs have the same manifest version, Claude Code may treat them as identical and skip the update. Bump the version in `plugin.json` when publishing meaningful changes, and update the version badge in `README.md` to match.
