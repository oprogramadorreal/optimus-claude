<div align="center">
  <img src="assets/banner.png" alt="optimus-claude" width="600">
</div>

<p align="center">
  <img src="https://img.shields.io/badge/version-3.12.0-blue" alt="Version">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/Claude_Code-plugin-blueviolet" alt="Claude Code">
  <img src="https://img.shields.io/badge/OpenAI_Codex-experimental-orange" alt="OpenAI Codex: experimental">
  <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey" alt="Platform">
</p>

**A plugin that sets up your project for effective AI-assisted engineering in Claude Code, with [experimental OpenAI Codex support](#using-with-openai-codex).**

---

Optimus records project conventions, non-obvious constraints, test commands, and workflow state so they can be reused across coding sessions. Its shared skills cover initialization, review, refactoring, testing, and resumable fix loops. Claude Code also gets optional formatter hooks; Codex uses `AGENTS.md` pointers to the same project guidance.

The design favors project-specific evidence and deterministic checks. Generated guidance still needs maintenance, and skill instructions do not guarantee correct model behavior. Release 3.0 reduced the instruction footprint substantially; smaller prompts alone are not evidence of better results.

## Quick Start

### Claude Code

Run these commands inside Claude Code:

```shell
/plugin marketplace add https://github.com/oprogramadorreal/optimus-claude.git
/plugin install optimus@optimus-claude
```

Then start a new session and type `/optimus:init` in any project directory. Having trouble? See [Troubleshooting](#troubleshooting).

### OpenAI Codex (experimental)

Use a plugin-capable Codex CLI with Bash available (Git for Windows supplies it on Windows). Git is also needed for the GitHub installation below and Git workflows, but is optional for the session-start hook. From a terminal, add the marketplace and install the plugin:

```shell
codex plugin marketplace add oprogramadorreal/optimus-claude
codex plugin add optimus@optimus-claude
```

(`/plugins` inside a Codex session lists the same marketplace and can install or enable `optimus` instead.) Open `/hooks` in a Codex session to **review and trust its session-start hook**, then start a new session in your project directory. Plugin installation alone does not trust hooks, and an untrusted hook delivers no `[optimus] Running under Codex` context — confirm the hook shows as trusted before invoking `$optimus:init`. See [Codex hook trust](https://learn.chatgpt.com/docs/hooks#review-and-trust-hooks).

Use `$optimus:<skill>` mentions in Codex, for example `$optimus:commit suggest`. **Skip `permissions` and `dream`; formatter installation is also unsupported.** Configure Codex's own sandbox and approval policy for guardrails. Desktop use remains unverified for this plugin; see the [support matrix and validation status](#support-matrix).

## How It Works

`/optimus:init` in Claude Code, or `$optimus:init` in Codex, analyzes your codebase and generates coding guidelines, CLAUDE.md instructions, and test infrastructure, detecting your stacks (Python, Node, Rust, UI frameworks, and more). Shared project docs live under `.claude/`, with package-specific docs in monorepos. Claude Code also gets formatter hooks. Under Codex, init preserves existing hooks/settings, skips formatter installation, and creates or refreshes `AGENTS.md` pointers so Codex reads the shared instructions. It also recognizes **skill authoring** as a stack: if your project's "source code" includes markdown instructions authored for an AI agent (a Claude Code plugin, a Codex skill repo, a prompt library), init installs `skill-writing-guidelines.md`, and the review/refactor skills route markdown instruction files through that lens while code files go through `coding-guidelines.md`.

**Command notation:** shared examples and skill links below use Claude Code's `/optimus:<skill>` form. In Codex, use `$optimus:<skill>` with the same arguments for supported workflows. The [support matrix](#support-matrix) lists partial and unsupported features; changing the prefix does not make Claude-only features portable.

From then on, the quality skills use your project standards as review criteria: `/optimus:code-review` checks your naming conventions and architectural patterns alongside bugs and security; `/optimus:tdd` applies your guidelines during the Refactor step; `/optimus:refactor` uses them as its quality lens; `/optimus:unit-test` follows your testing conventions. `/optimus:deep` sustains any of those passes across iterations — a fresh subagent per pass, tests and deterministic bisection between passes, resumable on-disk state.

**Design principles:** skills never auto-trigger. A lightweight read-only SessionStart hook surfaces project state and, under Codex, compatibility guidance once trusted. Generated repo docs travel via git and remain usable without the plugin; formatter hooks apply to Claude Code, while Codex follows the shared docs through `AGENTS.md`. Multi-repo workspace-root pointers are local-only.

## Skills

### Core

| Skill | Description |
|-------|-------------|
| [`/optimus:init`](skills/init/README.md) | Initializes project documentation and test infrastructure from your actual codebase, plus formatter hooks in Claude Code or `AGENTS.md` pointers in Codex. Offers new-project scaffolding on empty directories; audits and syncs on re-run. |
| [`/optimus:brainstorm`](skills/brainstorm/README.md) | Structured design brainstorming — explores the codebase, proposes approaches with trade-offs, writes an approved spec to `docs/specs/` that `/optimus:tdd` consumes. `scaffold` mode stamps an empty docs-first steering cascade (product vision, MVP PRD, tech stack) for a human to fill. |
| [`/optimus:jira`](skills/jira/README.md) | Fetches a JIRA issue via MCP and distills it into a structured task at `docs/jira/` that downstream skills auto-detect. Analyzes the codebase for missing criteria and risks; recommends the next skill by complexity. |
| [`/optimus:tdd`](skills/tdd/README.md) | Test-driven development through Red-Green-Refactor cycles with per-behavior commits and branch push. Auto-detects specs from `docs/specs/` or `docs/jira/`. *Init recommended; working tests required.* |
| [`/optimus:unit-test`](skills/unit-test/README.md) | Discovers coverage gaps and writes convention-following tests. Never refactors source code; stops with a triage pointer when the test baseline is broken. *Requires init.* |
| [`/optimus:refactor`](skills/refactor/README.md) | Refactors for guideline compliance and testability through four analysis lenses, with `testability` and `guidelines` focus modes. *Run init first.* |
| [`/optimus:code-review`](skills/code-review/README.md) | Reviews changes for bugs, security issues, and guideline compliance through 5 to 7 review lenses. Auto-routes to PR mode on a clean branch with an open PR/MR and reads the PR description as author intent. *Run init first.* |
| [`/optimus:deep`](skills/deep/README.md) | Iterative auto-fix orchestrator: `deep review`, `deep refactor`, or `deep coverage`. Runs the base skill in a fresh subagent per iteration, applies fixes, runs tests, bisects failures, and resumes across sessions. *Requires init + test command.* |
| [`/optimus:paper-init`](skills/paper-init/README.md) | Builds a self-contained context bundle for implementing a research paper — pristine sources, faithful transcription, annotated references (blocking citations fetched), an implementation spec with the reported results, open questions, and dataset provenance under `paper/`, with datasets in a gitignored `data/`. Warns when reproduction outstrips local hardware. Stack-agnostic; writes no implementation code — hands off to `/optimus:gauntlet`. |
| [`/optimus:gauntlet`](skills/gauntlet/README.md) | Runs a Gauntlet Loop: turns an ambitious goal into a builder/critic improvement loop judged against a concrete quality bar — fresh-context critics compare the real output against the bar and return either *beats the bar* or the biggest remaining gap, with no fixed round count, until the output beats the bar or you stop the run. Confirms before starting the long multi-agent run. *Run init first.* |

### Utility

| Skill | Description |
|-------|-------------|
| [`/optimus:commit`](skills/commit/README.md) | Stages, commits, and optionally pushes with a conventional commit message; captures the "why" from the implementation conversation. `suggest` mode is read-only; `branch` mode moves local changes to a conventionally named branch without committing. |
| [`/optimus:pr`](skills/pr/README.md) | Creates or updates a PR/MR with a structured description — intent, scope, non-goals, test plan — that `/optimus:code-review` consumes. Supports GitHub and GitLab. |
| [`/optimus:worktree`](skills/worktree/README.md) | Creates an isolated git worktree for parallel development, running project setup and a test baseline automatically. |
| [`/optimus:handoff`](skills/handoff/README.md) | Compacts the current conversation into a self-contained, redacted handoff doc under `docs/handoffs/` so any fresh agent can resume the work. |
| [`/optimus:how-to-run`](skills/how-to-run/README.md) | Generates a `HOW-TO-RUN.md` that teaches a new developer how to set up and run the project locally; audits it against actual project state on re-run. |
| [`/optimus:permissions`](skills/permissions/README.md) | **Claude Code only.** Configures branch protection, precious-file safety, and auto-approved routine tool calls via allow/deny rules and a PreToolUse hook. Use Codex's own sandbox and approval policy in Codex. |
| [`/optimus:prompt`](skills/prompt/README.md) | Crafts optimized, copy-ready prompts for any AI tool — extracts intent, selects a template, audits for token efficiency. |
| [`/optimus:reset`](skills/reset/README.md) | Cleans up Optimus-managed project docs, hooks/settings entries, and `AGENTS.md` pointer blocks; preserves tests and test configuration. Classifies each file before deletion and always asks for confirmation. Does not uninstall the plugin. |
| [`/optimus:dream`](skills/dream/README.md) | **Claude Code only.** Prunes and consolidates the project's auto-memory — deletes stale, wrong, or redundant memories and merges overlaps into existing files, never creating new ones. Verifies staleness against the codebase and always asks before deleting. |

## Recommended Workflow

### Claude Code

1. **Setup** — `/optimus:permissions` for guardrails, then `/optimus:init` to generate project context and test infrastructure.
2. **Strengthen** — `/optimus:unit-test` for coverage (or `/optimus:deep coverage` for the automated loop), `/optimus:refactor` for code quality.
3. **Build** — pick the entry point that matches the task: `/optimus:tdd "description"` directly for small clear work; `/optimus:jira PROJ-123` first for tracked work; `/optimus:brainstorm` first when design decisions are needed (greenfield products start with `/optimus:brainstorm scaffold`); `/optimus:paper-init <paper>` first when implementing a research paper; `/optimus:gauntlet <goal>` for ambitious long-horizon goals judged against a concrete quality bar.
4. **Ship** — `/optimus:commit` → `/optimus:pr` → `/optimus:code-review` in a fresh conversation (or `/optimus:deep review` for iterative auto-fix).

### Codex (experimental)

1. **Setup** — configure Codex's sandbox and approval policy, then run `$optimus:init` to generate shared project context, `AGENTS.md` pointers, and test infrastructure. `permissions` and formatter installation are Claude-only.
2. **Strengthen** — `$optimus:unit-test` for coverage and `$optimus:refactor` for code quality.
3. **Build** — `$optimus:tdd "description"` for clear work; `$optimus:brainstorm` for design decisions; `$optimus:jira PROJ-123` for tracked work after configuring a compatible Jira MCP server in Codex; `$optimus:paper-init <paper>` for research preparation. Claude-specific plan-mode handoffs need manual adaptation.
4. **Ship** — `$optimus:commit` → `$optimus:pr` → `$optimus:code-review` in a fresh conversation.

`deep` and `gauntlet` orchestration need additional Codex execution testing before unattended use; see the [support matrix](#support-matrix) and [headless requirements](#headless-runs). Claude's `/goal`, `/workflows`, and `/effort` → ultracode handoffs do not apply.

**On either host, keep intent flowing from implementation to review:** stay in the implementation conversation when running `commit` and `pr` — they capture *why* the change was made into the commit message and PR description. Then review in a fresh conversation: `code-review` reads the PR description as author intent and checks whether the implementation delivers what it claims, not just whether it follows style rules. (`tdd` auto-commits per cycle and pushes at the end, so its flow collapses to `tdd` → `pr` → review.)

**Maintenance on either host** — re-run `init` after major changes to audit and refresh generated docs; use `how-to-run` when new to a codebase, and `reset` to clean up Optimus-managed project files. Use your host's skill prefix. For stale auto-memory in **Claude Code only**, run `/optimus:dream`. To uninstall the plugin itself, follow the [reset documentation](skills/reset/README.md).

## Design rationale and evidence

Useful conventions, testable acceptance criteria, and maintained documentation can help agents work within a project's constraints. Optimus records those facts, keeps reusable protocols shared, and uses deterministic test and rollback mechanisms where the workflow calls for them.

Research motivates this approach without validating this plugin's present performance. [Code Health research](https://arxiv.org/abs/2601.02200) found an association with semantic preservation in a 5,000-file Python refactoring dataset. [Context-length research](https://arxiv.org/abs/2510.05381) found degradation on selected tasks and five models; it does not establish that every additional instruction harms every model. [Test-driven code-generation research](https://arxiv.org/abs/2402.13521) reports gains in its evaluated settings, and [Anthropic recommends giving Claude Code a way to verify its work](https://code.claude.com/docs/en/best-practices).

These results are reasons to test the design, not measurements of Optimus on GPT-6 Astra or Claude Fable 5.1. Compare correctness, completion, regressions, intervention, and cost on representative tasks before removing useful procedures or adding more review loops. Independent review and evidence requirements can help catch mistakes; they do not guarantee freedom from sycophancy or errors.

## Complementary Tools

### Claude Code

optimus-claude works alongside official tools, not against them. Use Anthropic's official [code-review](https://github.com/anthropics/claude-code/tree/main/plugins/code-review) plugin for post-push PR review, the builtin `/simplify` for per-change cleanup (complemented by `/optimus:refactor` for project-wide restructuring), Claude Code's native [dynamic workflows](https://code.claude.com/docs/en/workflows) for one-off background multi-agent builds and sweeps, and [built-in sandboxing](https://code.claude.com/docs/en/sandboxing) for autonomous execution with OS-level isolation.

Claude Code's [`/goal`](https://code.claude.com/docs/en/goal) is complementary to `/optimus:deep`: reach for `/goal` for lightweight "work until a condition holds" in a single session; reach for `/optimus:deep` for the deterministic, resumable fix loop — fresh subagent per iteration, test bisection that reverts the exact fix that broke the build, and on-disk state that survives across sessions.

### Codex

Use Codex's own sandbox and approval policy for execution controls, a compatible MCP server for Jira, and editor formatting or pre-commit hooks for formatting. The Claude Code commands and plugins above are not Codex setup instructions; Optimus's Codex limits are listed below.

## Using with OpenAI Codex

Codex support is experimental and opt-in. Claude Code remains the primary host: both hosts share one set of 19 skill sources and the session-start script, with separate manifests and hook configurations. Claude Code launches Bash directly through `hooks/hooks.json`; Codex's `.codex-plugin/plugin.json` selects `hooks/codex-hooks.json`. No additional setup is required for Claude Code. The integration targets plugin-capable Codex CLI and desktop releases. Codex CLI 0.153.4 has native Windows installation, discovery, and launcher evidence. No universal minimum is established; full desktop workflows remain unverified. See [Codex plugin availability](https://learn.chatgpt.com/docs/plugins).

Follow the [Codex Quick Start](#openai-codex-experimental) to install, enable, trust the hook, and initialize your project.

The session-start hook supplies the plugin path and compatibility guidance. If the `[optimus] Running under Codex` line is missing from the agent's session context in a fresh session (ask it what its session context says), check `/hooks` before running skills. Codex's hook-path substitution does not safely handle shell metacharacters such as `$` or backticks in the installation path; use a path without them (spaces are supported).

Invoke skills with a `$` mention: `$optimus:init`, `$optimus:commit suggest`, `$optimus:deep review`.

### Supported hosts and versions

This is the version reference for all skill READMEs. Versions below identify actual tested runtimes, not a universal minimum. Current host documentation describes features that older clients may lack. In particular, Claude Code 1.0.33 predates the plugin system and is not a supported floor.

| Surface | Version/evidence as of 2026-09-09 | Support boundary |
|---|---|---|
| Claude Code, native Windows CLI | 2.1.263: local plugin validation, all 19 skills, both plugin agents, and startup hook loaded | Primary host. This audit did not complete an authenticated Claude Fable 5.1 workflow; use the execution tests before certifying changed skill behavior |
| Codex, native Windows CLI/app-server | 0.153.4: isolated local marketplace installation, all 19 enabled skills, cache/source prompt comparison, and launcher tests | Experimental. Loader success does not establish init, delegation, deep resume, or GPT-6 Astra task correctness |
| Codex desktop/local | Existing cached plugin startup context observed; desktop version not recorded | Full controlled desktop skill workflows and updates unverified |
| macOS/Linux CLI, including WSL as a separate environment | Host plugin support is documented; this audit did not execute these surfaces | Native Windows results do not certify their shell, permissions, or filesystem behavior |
| Codex IDE extension | Current OpenAI documentation does not support plugins in this surface | Separately copying skills is a different setup and is not plugin support |
| Remote/cloud sessions | Not exercised in this release audit | No support claim beyond each host's documented availability |

See [Claude plugin documentation](https://code.claude.com/docs/en/plugins) and [Codex plugin availability](https://learn.chatgpt.com/docs/plugins). Optional Claude `/goal`, `/workflows`, plan transitions, and nested agents depend on the installed version, settings, and available tools; do not infer their availability from a model name. Codex uses its own permissions, question tools, agents, and memory facilities. The workflow matrix below records deliberate exclusions.

### Support matrix

All Codex workflows below remain experimental. **Portable** means code review found no known host-specific dependency in the core workflow; it is not an end-to-end execution result. **Partial** excludes the named features. Agent-based workflows still need execution verification, and available subagent capacity can reduce parallelism. **Experimental orchestration** needs separate execution testing before relying on it unattended.

| Skill or feature | Codex status | Limits and requirements |
|---|---|---|
| `commit`, `pr`, `handoff` | Portable | Git and any required hosting CLI/authentication must be available; host permissions still apply |
| `worktree`, `how-to-run`, `paper-init` | Portable | Project setup, services, downloads, and extraction tools retain their normal prerequisites |
| `code-review`, `refactor`, `unit-test`, `tdd` | Portable | Follow the skill's init/test prerequisites; agent execution needs smoke verification |
| `init` | Partial | Shared docs, test infrastructure, and `AGENTS.md` pointers; skips formatter installation under Codex and preserves existing hooks/settings |
| `reset` | Portable | Cleans up selected Optimus-managed docs, hooks/settings entries, and pointer blocks after confirmation; preserves tests/test configuration and user content outside pointer blocks; does not uninstall the plugin |
| `brainstorm`, `jira`, `prompt` | Partial | Core design, issue, and prompt work; Jira requires a compatible MCP server already configured in Codex (bundled setup is Claude-only). Claude-specific plan-mode handoffs require manual adaptation; `prompt`'s `/workflows` handoff is unsupported |
| `deep` | Experimental orchestration | Nested agents, multiple iterations, resume, and headless execution need Codex smoke verification; see headless requirements below |
| `gauntlet` | Partial; experimental orchestration | In-session lead-agent path only; Claude's `/effort` → ultracode prerequisite and "Copy as /goal prompt" handoff do not apply |
| `permissions` | Unsupported | Writes Claude rules and parses Claude tool inputs. Configure Codex's own sandbox and approval policy instead |
| `dream` | Unsupported | Operates on Claude auto-memory. Use Codex's memory controls instead |
| Formatter hooks | Unsupported | Codex edit events supply patch text rather than the file-path payload these hooks expect. Use editor formatting or pre-commit hooks |
| Standalone `optimus:code-simplifier` / `optimus:test-guardian` agents | Unsupported | Codex custom agents use TOML configuration; use the portable `refactor` / `unit-test` workflows instead |

Prior-release observations (3.11.3, Windows, 2026-09-08), retained as historical results rather than evidence that changed 3.12.0 skills passed. The current audit repeated loader checks but could not complete authenticated model tasks:

- **Automated gates recorded then:** structural and Python checks passed; the hook suite had one UNC-path assertion failure on unchanged `master` with that Git Bash. Release 3.12.0 fixes the failed-directory-change fallback and requires the combined suites to be rerun.
- **Claude Code 2.1.263:** loaded all 19 skills and both agents, completed Python init while preserving custom settings/hooks, created no `AGENTS.md`, formatted an actual Write-tool edit, and ran read-only commit suggest.
- **Codex CLI 0.153.4:** installed the local plugin and ran the session hook exactly once through the Windows launcher, also with only `System32` and `Git\cmd` on PATH, delivering the compatibility context from a nested directory. An earlier snapshot passed init, repeat init, root/nested instruction routing, reset preservation, and the permissions/dream/missing-Jira checks, and the documented GitHub install commands fetched the expected branch revision. The interactive `/hooks` trust UI was not exercised.
- **Unverified:** native Linux/macOS workflows, desktop use, live Jira, multi-repo init, and deep/gauntlet orchestration. See the [contributor smoke test](CONTRIBUTING.md#codex-smoke-test-local) for the remaining checks.

What differs under Codex:

- Skills never auto-trigger on either host (`agents/openai.yaml` carries the Codex-side flag), and they stay out of the model's skill list until you mention one.
- Questions use a native host question tool when it is available in the current mode; otherwise answer the plain-text question in chat. Prior authorization remains applicable; a plugin prompt does not override host permissions.
- Codex uses Bash directly on macOS/Linux and a PowerShell launcher on Windows. The Windows launcher finds native Bash, honors `CLAUDE_CODE_GIT_BASH_PATH`, and skips WSL's `bash.exe`; Git for Windows is the recommended provider. Both launchers preserve the starting directory without running a Git alias. Git is optional for startup and needed for Git workflows.
- `$optimus:init` writes or refreshes root `AGENTS.md` pointers when Codex use is detected. They route to existing CLAUDE.md files, including package-specific instructions in monorepos. Multi-repo workspaces get pointers at the workspace root and in each child repo. User content outside the marked blocks is preserved; `$optimus:reset` removes only Optimus's blocks from those files (deleting a pointer-only file). An `AGENTS.override.md` in the same directory takes precedence in Codex: add an equivalent pointer there yourself if you use it; init/reset manage only `AGENTS.md`.
- Subagent parallelism depends on Codex's version and configuration. Current releases use `agents.max_concurrent_threads_per_session` (`agents.max_threads` is a legacy alias); no fixed concurrency is guaranteed. See [Codex subagent configuration](https://learn.chatgpt.com/docs/agent-configuration/subagents#global-settings).

### Headless runs

After installation, hook trust, project trust, and initialization, an experimental Bash/PowerShell example is:

```shell
codex exec --model gpt-6-astra --sandbox workspace-write '$optimus:deep review --yes'
```

`codex exec` defaults to read-only, so editing workflows need an explicit write-capable sandbox. `--yes` answers Optimus confirmations only; it does not grant filesystem, Git, network, or subagent permissions. Deep writes state under `.claude/`, uses Git snapshots, and checkpoint-commits: preconfigure the permissions needed for the run, since headless execution cannot obtain fresh interactive approvals. `--no-commit` disables checkpoints but still uses Git snapshots. See [Codex non-interactive execution](https://learn.chatgpt.com/docs/non-interactive-mode).

On native Windows, complete [Codex's sandbox setup](https://learn.chatgpt.com/docs/windows/windows-sandbox) as well. A fresh configuration can block even read commands; trusting a plugin hook does not configure the project or its sandbox. Check the session's effective permissions before starting a long run.

Supported CLIs offer `--approve-for-me` for automatic permission review, in place of `--sandbox workspace-write`; the two flags cannot be combined. The Windows init smoke needed this review for protected `.claude/` writes. This grants no blanket approval and does not establish that deep orchestration works unattended.

## Troubleshooting

### Codex: skills or compatibility context missing

Confirm `optimus` is installed and enabled in `/plugins`, review/trust its session-start hook in `/hooks`, and start a fresh session. Bash must be available; on Windows, install Git for Windows or point `CLAUDE_CODE_GIT_BASH_PATH` at a native `bash.exe`. A plugin update that changes the hook definition resets its trust, so review it again if `/hooks` marks it as untrusted. Use `$optimus:<skill>` mentions rather than `/optimus:<skill>`. If installing from a feature branch, follow the [Codex feature-branch testing instructions](CONTRIBUTING.md#codex) to select the intended branch.

### Windows: SSL certificate error during install

If you see `SSL certificate OpenSSL verify result: unable to get local issuer certificate` when running `/plugin marketplace add`, Git for Windows is using an outdated OpenSSL CA bundle. Switch to the native Windows certificate store, then retry:

```shell
git config --global http.sslBackend schannel
```

### Upgrading from 3.5.0 or earlier

**Claude Code formatter migration only.** Codex init preserves existing hooks/settings and does not perform this migration; run it from Claude Code if the project also uses Claude formatting.

3.5.1 replaced the Python formatter hook `.claude/hooks/format-python.py` with a portable bash one, `format-python.sh`, because the Python version needed a `python` on PATH — which on Windows hits the Store alias stub and fails on every edit.

Re-running `/optimus:init` performs the swap, including deleting the old file and its `settings.json` entry. To do it by hand instead: delete `.claude/hooks/format-python.py` and remove the `PostToolUse` entry whose command references it. Leaving it in place means two Python hooks fire per edit.

The replacement resolves `black` and `isort` from a `.venv`, `venv`, or `env` directory at or above the edited file, then from PATH — so a virtualenv kept outside the project (Poetry's default, pipenv, conda) needs the formatters on PATH instead. The hook prints a one-line notice to stderr when it cannot find them.

### Upgrading from 2.x

These are historical Claude Code migration instructions. Codex users should follow the [Codex Quick Start](#openai-codex-experimental), [support matrix](#support-matrix), and [Codex headless example](#headless-runs).

3.0 consolidated 22 skills into 16 with no functionality loss except `/optimus:workflow` (Claude Code's native dynamic workflows cover it):

| Removed in 3.0 | Use instead |
|----------------|-------------|
| `/optimus:code-review-deep` | `/optimus:deep review` |
| `/optimus:refactor-deep` | `/optimus:deep refactor` |
| `/optimus:unit-test-deep` | `/optimus:deep coverage` |
| `/optimus:branch` | `/optimus:commit branch` |
| `/optimus:commit-message` | `/optimus:commit suggest` |
| `/optimus:spec-init` | `/optimus:brainstorm scaffold` |
| `/optimus:workflow` | Claude Code's native dynamic workflows |

Headless entry points move accordingly, e.g. `claude -p "/optimus:deep review --yes 'src/auth'"`. Progress files are unchanged and 2.x runs remain resumable — an in-flight 2.x `*-deep` run can be resumed with the matching `/optimus:deep <target> --resume` (one scope-semantics upgrade: a free-text 2.x coverage scope is migrated to recorded intent on first resume, since 3.0 only filters on real paths).

### Upgrading from 1.x

In Claude Code, the two terminal-run Python harnesses were replaced in 2.0 by in-conversation orchestration — now `/optimus:deep` (see the 2.x table above). This migration does not establish Codex orchestration support.

## Release notes — 3.12.0

- Preserve pre-existing user work at snapshot, rollback, initialization, reset, TDD, and handoff boundaries; reject incomplete harness results before accepting edits or checkpoints.
- Make smoke checks select the local plugin and an explicit model, reject host failures, and inspect file bytes and Git state. Add a separate isolated Codex installation/discovery check.
- Correct Windows Bash utility lookup and installer quoting; update Claude formatter compatibility while retaining Codex's formatter-installation exclusion.
- Correct onboarding commands and vendor runtime guidance, consolidate tested host/version information, and qualify instruction-performance claims. Shared skill sources remain the default.

These changes repair reproduced failures and confirmed instruction contradictions. They do not establish model-performance gains or untested host compatibility.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for project structure, skill anatomy, and local development setup, including feature-branch testing in [Claude Code](CONTRIBUTING.md#testing-a-feature-branch) and [Codex](CONTRIBUTING.md#codex).

## Acknowledgements

The `/optimus:prompt` skill's prompt engineering techniques are adapted from [prompt-master](https://github.com/nidhinjs/prompt-master) by [@nidhinjs](https://github.com/nidhinjs).

The `/optimus:gauntlet` skill implements the [Gauntlet Loop](https://somethingbig.ai/gauntlet-loop) method by Matt Shumer.

## Research & References

- [Claude Code Best Practices](https://code.claude.com/docs/en/best-practices) — Anthropic: verification as #1 practice, compact CLAUDE.md, deterministic hooks
- [Skill Authoring Best Practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) — Anthropic: concise is key; Claude is already smart
- [How TDD Amplifies AI Success](https://cloud.google.com/discover/how-test-driven-development-amplifies-ai-success) — DORA Report 2025
- [Code for Machines, Not Just Humans](https://arxiv.org/abs/2601.02200) — Borg et al. 2026: AI defect risk increases 30%+ on unhealthy code
- [Context Length Alone Hurts LLM Performance](https://arxiv.org/abs/2510.05381) — Du et al. 2025: 13.9%–85% degradation as input length increases
- [Test-Driven Development for Code Generation](https://arxiv.org/abs/2402.13521) — Mathews et al. 2024
- [AI-Friendly Code Design](https://www.thoughtworks.com/radar/techniques/ai-friendly-code-design) — Thoughtworks Tech Radar Vol. 32
- [AI Developer Productivity: Perception vs. Reality](https://arxiv.org/abs/2507.09089) — METR 2025: developers 19% slower with AI while believing they were faster
- [Sycophancy in AI: The Risk of Complacency](https://blog.scielo.org/en/2026/03/13/sycophancy-in-ai-the-risk-of-complacency/) — SciELO 2026

## Testing

Run from the repository root with the development environment activated:
```shell
bash scripts/validate.sh && bash scripts/test-hooks.sh && python -m pytest test/
python -m pytest test/harness-common/ --cov scripts/harness_common --cov-report=term-missing
```
Python tests live in `test/`, with orchestrator tests under `test/harness-common/`. On Windows, `test-coverage.cmd` also generates `htmlcov/index.html`.
See [CONTRIBUTING.md](CONTRIBUTING.md#testing) for setup and the separate skill execution tests.
