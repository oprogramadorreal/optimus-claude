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
│   ├── hooks/                # Hook script templates
│   └── docs/                 # Documentation templates
├── agents/
│   ├── openai.yaml           # Codex twin of disable-model-invocation (required; validate.sh checks it)
│   └── *.md                  # Agent prompt files, one per agent plus shared-constraints.md (optional)
└── references/               # Technical reference docs consumed by the skill (optional)
```

**`SKILL.md`** is the key file: YAML frontmatter plus the instructions Claude Code follows when the skill is invoked.

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

`.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` carry the same plugin identity and version. Every PR to master bumps both and updates the version badge in `README.md` to match; `validate.sh` fails a PR whose version equals master's or whose manifests and badge disagree. It SKIPs the bump and badge checks when `origin/master` is unavailable, so a local pass is not proof.

`.claude-plugin/marketplace.json` is how Claude Code discovers the plugin. Its `source` object accepts an optional `ref` to pin plugin code to a branch, tag, or SHA; that is only for the feature-branch testing flow below, and `validate.sh` fails while it is present.

`.agents/plugins/marketplace.json` is the same catalog for OpenAI Codex. Codex reads it before the Claude one and installs the plugin from `./`. `validate.sh` pins the plugin name across the catalogs and manifests. Per-host hook wiring (the default `hooks/hooks.json` for Claude Code, `hooks/codex-hooks.json` selected by the Codex manifest) and the launcher constraints are in `.claude/docs/architecture.md` under Two hosts, one plugin.

## Testing

This plugin is mostly markdown-based. Testing is split into layers: fast structural checks, hook tests, and Python unit tests that run in CI, and slower skill execution tests that run locally.

**Before merging significant changes**, run the automated gates below and the relevant authenticated [skill execution tests](#skill-execution-tests-local). Record any unavailable model or environment checks as unverified.

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

Covers the orchestrator CLI, the session-start, formatter and restrict-paths hooks, the installer, skill metadata and Git snippets, the smoke runner, and the evaluation scorers. Setup (`install.cmd` on Windows, or a `.venv` from `requirements-dev.txt` on macOS/Linux) and commands (`test.cmd`, `test-coverage.cmd`, `python -m pytest test/`) are in [.claude/docs/testing.md](.claude/docs/testing.md).

The formatter-hook tests and harness commands use Bash. Windows contributors need native Git Bash; the runner locates it separately from WSL and supplies utilities from the selected installation even when only Git's `cmd` directory is on PATH. `CLAUDE_CODE_GIT_BASH_PATH` can select a custom native installation. This does not convert PowerShell-only project commands into Bash syntax.

### Fixture generator (local)

Generates minimal project fixtures for testing skills. No dependencies installed — just enough files for project detection to work. Output goes to `test/fixtures/` (gitignored).

```shell
bash scripts/generate-fixtures.sh              # generate all fixtures
bash scripts/generate-fixtures.sh node python   # generate specific ones
```

Available fixtures: `node`, `python`, `go`, `rust`, `csharp`, `monorepo`, `empty`, `multi-repo`.

### Skill execution tests (local)

Runs skills against copied fixtures via `claude -p --plugin-dir <this-checkout>` and validates outputs against `test/expected-outputs.yaml`. Requires authenticated Claude Code, Python/PyYAML, and an explicit `--model` identifier; no host-default model is selected silently. The example target is Claude Fable 5.1 (`claude-fable-5-1`).

```shell
bash scripts/test-skills.sh --model claude-fable-5-1
bash scripts/test-skills.sh --model claude-fable-5-1 --skill init --fixture node
bash scripts/test-skills.sh --model claude-fable-5-1 --all
bash scripts/test-skills.sh --model claude-fable-5-1 --all --worktree
bash scripts/test-skills.sh --dry-run
```

The runner records the host version, requested model, checkout commit/dirty state, and result metrics when supplied by the host. Any nonzero exit, incomplete/error result envelope, or absent/empty expectation fails. Read-only checks compare project file bytes plus Git state, including changes to an already-dirty file. Branch tests inspect the actual branch. The empty-project init case is explicitly a weak completion-only smoke check.

The test prompt authorizes noninteractive default choices. It does not test interactive question UX or grant host permissions. The harness uses `--dangerously-skip-permissions` only inside disposable fixture copies; review fixture inputs and run these tests with appropriately scoped credentials. `--fresh` without `--worktree` replaces `test/fixtures/`; keep user work out of that generated directory.

Not intended for CI — run locally before merging significant changes.

**`--worktree` flag:** Creates a new detached git worktree at a unique `.worktrees/skill-tests.*` path from committed `HEAD` and cleans up only that worktree on success. On failure it is preserved for debugging; the script prints its path and cleanup command. Subsequent runs leave earlier failed worktrees untouched. Uncommitted source edits are excluded. This snapshots the code at the current commit so you can freely switch branches, edit plugin files, or start new work in the main tree while the tests run — and the worktree stays visible in your IDE for easy inspection. Combine with any other flags (`--all`, `--skill`, etc.).

**Adding expected outputs:** Edit `test/expected-outputs.yaml`. Supported assertions are `files_exist`, `files_contain`, `files_not_exist`, `files_not_modified`, `output_contains`, `output_nonempty`, and `branch_prefix`. Every selected pair must have a nonempty oracle. Add behavior regressions to `test/test_skill_smoke_runner.py` when changing the runner; string checks alone do not establish skill effectiveness.

### Codex smoke test (local)

Codex support is experimental. CI checks metadata and launcher behavior; it does not run model-driven workflows. Record the date, exact plugin commit/version, host version, OS, and pass/fail/untested results. No minimum Codex version is claimed.

For a model-free local loader check, run `python scripts/test-codex-plugin.py` with a native Codex executable on PATH, or supply `--codex-exe <absolute-native-executable>`. Windows `.cmd`/`.ps1` wrappers are not accepted by this helper. Optional `--output <report-path>` saves JSON evidence. The helper creates and cleans up a temporary `CODEX_HOME`, installs this checkout, requests the actual skill inventory, and compares every cached tracked file to source. It neither changes your installed plugin nor invokes a model. Successful discovery is separate from every semantic check below. Tested host versions are in the [support table](README.md#supported-hosts-and-versions).

Use an isolated Codex configuration and a disposable project. Trust the project and configure its native sandbox before model execution, in addition to reviewing the plugin hook. On Windows, follow [sandbox setup](https://learn.chatgpt.com/docs/windows/windows-sandbox). Record the effective sandbox and any tool denials: an exit-zero model response that reports blocked commands is not a passing workflow test. If automation uses the documented one-run hook-trust override for an already reviewed hook, record that separately from testing the interactive `/hooks` trust flow.

Before promoting the core workflows beyond experimental, run this core check:

1. **Install, trust, invoke** — with an authenticated Codex CLI, run `codex plugin marketplace add oprogramadorreal/optimus-claude` and `codex plugin add optimus@optimus-claude` from a terminal (or follow the [Codex feature-branch setup](#codex) to test another branch), then review/trust its hooks in `/hooks`. In a fresh session, confirm the agent received `[optimus] Running under Codex` and the installed plugin path without a hook error — ask it, or read the `developer` message in the session rollout under `~/.codex/sessions/`. In a disposable repo with a change, run `$optimus:commit suggest`; it must read its bundled references and suggest a message without writing. A separate plain "write a commit message for this" request must not auto-load the skill.
2. **Init, routing, preservation, reset** — generate fixtures with `bash scripts/generate-fixtures.sh monorepo multi-repo`. In `test/fixtures/monorepo-project`, run `$optimus:init`; add user text/comments outside its `AGENTS.md` block and custom Claude hooks/settings, then re-run init. Compare the original hook/settings bytes and surrounding user text; only one pointer block should remain. In fresh root and package sessions ask "Which test command applies here? Read the project instructions without editing." Confirm the applicable CLAUDE.md files were read. Run `$optimus:reset` and confirm only the managed pointer is removed from `AGENTS.md`. Repeat the routing/pointer check at `test/fixtures/multi-repo-workspace` and inside a child repo. Also verify `$optimus:jira TEST-1` without MCP tools stops at Codex setup guidance, and `permissions`/`dream` explain their exclusion without changing Claude state.
3. **Shared script and separate launcher regression** — run `bash scripts/validate.sh`, `bash scripts/test-hooks.sh`, and `python -m pytest test/`. Start `claude --plugin-dir <absolute-plugin-path> --debug-file <log> -p 'Reply OK.'` from root and nested disposable directories with different initialization state; compare hook events, confirm every `skills/*` skill and every `agents/*.md` agent loads, and verify a fully initialized Claude project adds no hook context. Check that Claude's Bash launcher works without Git on PATH. For Codex, verify the explicit manifest hook replaces the default and runs exactly once; exercise native Windows loading with restricted PATH and WSL interference. Verify `CLAUDE_CODE_GIT_BASH_PATH` selection and nested working-directory preservation. A hook that runs before an authentication failure is loader evidence only.

**Optional orchestration checks:** keep these unverified/experimental until needed; they are not prerequisites for the documented experimental core. Run `$optimus:code-review` with more lenses than available agent slots and verify no lens is dropped. For deep, run `$optimus:deep review --yes src/<path>` across multiple iterations, interrupt between iterations, then resume with `$optimus:deep review --yes --resume`; inspect checkpoints and the final report. Exercise coverage's paired phases separately. For unattended use, run the README's explicit-model `codex exec` example in an initialized fixture after granting the necessary host permissions, and verify actual edits, Git snapshots, and tests. Optimus `--yes` does not grant host permissions. Gauntlet's in-session and native Codex goal paths need the separate checks below; Claude `/workflows` and ultracode remain Claude-only.

#### Gauntlet goal handoff (manual)

The copy path is implemented for both hosts; that is not evidence that either host/model completed the candidate workflow. Structural, hook, and loader checks cannot establish prompt selection, critic independence, automatic continuation, or stopping behavior. Before claiming native execution support, run the applicable cases in disposable projects with bounded test goals and inspect the resulting transcript, progress files, verdict files, tests, and Git state.

Record exact plugin commit/version and cache path, host build/surface, OS, model, exposed goal/subagent/question tools, permissions, and pass/fail/untested per case. Use GPT-6 Astra (`gpt-6-astra`) and Claude Fable 5.1 (`claude-fable-5-1`) as distinct targets; do not substitute a model or label an unavailable run as passing. Any explicit limit used to bound a test is a suspension condition, not proof the quality bar was met.

| Case | Expected behavior |
|---|---|
| Offer in each host | Start the run, Adjust first, Copy as /goal prompt, and Cancel remain available after the bar/prompt preview. Codex's hook no longer suppresses goal export; question-tool restrictions do not silently drop choices. |
| Copy without execution | Selecting Copy seeds/preserves the progress file and returns a destination prompt. No builders/critics, feature branch, implementation edits, native goal creation/update, new session, or loop starts in the preparing session. Existing run state is not silently overwritten. |
| Fresh Claude session | The handoff contains the shared protocol and transcript-verifiable completion condition, fits 4,000 characters, and includes only Claude setup/control guidance. Pasting starts one goal; there is no second skill confirmation before already-authorized work. |
| Fresh Codex/Astra session | With native goals available, the handoff fits 4,000 characters and starts/reuses one lead goal through the supported command/tool path. The destination loads the referenced project guidance and state, preserves `gpt-6-astra`, and uses no Claude evaluator or ultracode assumptions. It does not recreate goals each round or in workers. |
| Codex without native goals | Copy still returns the native goal prompt for a capable destination. Its checklist offers setup or a separately labeled plain continuation fallback, with the cross-turn limitation explicit. No unavailable tool call, silent fallback, simulated goal API, or replacement automation is used. |
| Start in the current Codex session | The ordinary in-session path executes after authorization without implicitly creating a native goal. If a goal already exists, it is not silently replaced. |
| Longer export or existing progress | An objective over 4,000 characters uses the saved full protocol and concrete completion evidence without dropping the goal/bar. A second export preserves prior piece history, verdicts, and user edits; unrelated run state requires a deliberate choice. |
| Multiple rounds and critic isolation | A failing independent verdict returns to its builder unchanged and causes another round. Every critic receives the fixed remit and artifact/reference paths in fresh context (for example `fork_turns: "none"` when exposed), never builder history. Include a check for default inherited context. |
| Completion evidence | Passing requires nonempty piece results, independent piece and final integration passes, applicable green tests, and required commits on a clean feature branch. Missing/stale evidence keeps the goal incomplete; the builder cannot certify itself. |
| Plateau, blocker, and budget | A plateau or exhausted budget is never marked complete. The lead follows the destination's actual blockage contract and preserves unresolved work. Codex sets a token budget only when explicitly requested; an authorized bounded run is reported as incomplete if it hits that limit before passing. |
| Stop and resume | Exercise the host's documented pause/clear or interrupt controls and distinguish a stopped turn from a cleared goal. Resume from saved state in the same and a fresh session, recreating workers when needed; do not claim private worker history transfers. Claude impossible/error clearing and host permission/usage stops remain incomplete outcomes. |

Host references: [Claude goals](https://code.claude.com/docs/en/goal), [Codex goal commands](https://learn.chatgpt.com/docs/developer-commands?surface=cli#set-or-view-a-task-goal-with-goal), and [Codex long-running work](https://learn.chatgpt.com/docs/long-running-work). Keep recorded observations separate from these documented capabilities.

#### Native question UX (manual)

These are manual acceptance checks, not recorded passes. Use a disposable project and a fresh session with the candidate plugin. Record the exact plugin commit/version and loaded cache path, host build/surface, OS, model, current mode, exposed question tools and their purpose/schema restrictions. Do not enable tools or change modes merely to force a popup; mark unavailable cases untested. Save the tool call, visible question, answer, and resulting action. Loader and hook assertions do not verify this UI.

| Case | Expected behavior |
|---|---|
| Claude Code, interactive | A skill's decision uses `AskUserQuestion` as before; no Codex adapter context appears. |
| Codex desktop, Default, permitted async tool | An unresolved preference uses `request_user_input_async`; choices and free text reach the agent. Independent work may continue, but answer-dependent work waits. |
| Codex Plan, async unavailable, permitted synchronous tool | The same preference uses `request_user_input` with its current schema; the returned answer determines the next step. |
| No available/permitted native question tool | The question appears in chat with the original choices; no unavailable tool call or mode switch occurs. Include a question whose purpose the exposed tool forbids. |
| Unsupported multi-select or option shape | Exercise `how-to-run`'s Docker alternative choice with multiple services. Preserve all choices and multi-select meaning through chat when the native form cannot represent them; do not silently make the choice exclusive. |
| Existing authorization or noninteractive defaults | Reuse an explicit decision, and separately exercise an applicable `--yes`/noninteractive path. Neither repeats a resolved question nor treats those choices as host permission grants. |
| Unanswered, dismissed, or delayed async question | Withhold the answer, then reply later. A receipt, empty result, dismissal, or elapsed time never authorizes dependent work; the actual answer releases only that dependency. |

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

The current [marketplace documentation](https://code.claude.com/docs/en/plugin-marketplaces) also supports GitHub shorthand `owner/repo@ref`, for example `/plugin marketplace add oprogramadorreal/optimus-claude@your-branch-name`. The full Git URL with `#branch` above remains supported. The older issue about `owner/repo#branch` concerned a different syntax; do not use it to infer that current shorthand pinning is unavailable. The plugin source `ref` is still a separate choice for this repository's URL-based Claude marketplace entry.

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
codex plugin marketplace add oprogramadorreal/optimus-claude@your-branch-name
codex plugin add optimus@optimus-claude
```

A local checkout works too: `codex plugin marketplace add ./path/to/optimus-claude` registers the working tree as the marketplace, and Codex re-caches the plugin whenever the version in `plugin.json` changes.

## Version bumping

Manifest versions affect update/cache behavior. If two refs have the same version, a host may reuse the cached release. `.claude/.optimus-version` records this repository's last initialization; do not bump it merely to match a plugin release.
