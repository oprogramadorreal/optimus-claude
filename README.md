<div align="center">
  <img src="assets/banner.png" alt="optimus-claude" width="600">
</div>

<p align="center">
  <img src="https://img.shields.io/badge/version-2.0.20-blue" alt="Version">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/Claude_Code-1.0.33+-blueviolet" alt="Claude Code">
  <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey" alt="Platform">
</p>

**A Claude Code plugin that sets up your project for effective AI-assisted engineering.**

---

**The problem:** AI amplifies whatever it finds. Messy code leads to messier AI-generated code, which becomes the new context for even worse output — a vicious cycle that compounds faster than any human could create technical debt. Without maintained context, any AI coding tool's quality degrades with every file it reads.

---

**The solution:** Optimus Claude generates tailored and optimized CLAUDE.md files, coding guidelines, formatter hooks, TDD and test coverage, all based on your actual codebase. Built-in quality agents (code simplifier, test guardian) run alongside every review and refactor.

*Use it regularly and your project stays clean, consistent, tested, and well-documented. Exactly the conditions where Claude Code performs at its prime.*

---

**The philosophy:** This is all about perfecting context. The codebase, prompts, unit tests, docs, commit messages, PR descriptions, branch names — it's all context and it all adds up to shape how well Claude Code performs. Optimus Claude provides developers ways to create and maintain optimal context for AI-assisted engineering across the entire development workflow.

## Quick Start

### Install

Run these commands inside Claude Code:

```shell
/plugin marketplace add https://github.com/oprogramadorreal/optimus-claude.git
/plugin install optimus@optimus-claude
```

> Having trouble? See [Troubleshooting](#troubleshooting).

### Run

Start a new Claude Code session and type `/optimus:init` in any project directory. See [Skills](#skills) for the full list.

## How It Works

Every skill operates on the same shared foundation: **your project's quality guidelines** (coding guidelines for code, skill-writing guidelines for markdown instruction projects) and a **verification protocol** that demands evidence over confidence.

`/optimus:init` analyzes your codebase and generates constraint docs — coding guidelines, CLAUDE.md, formatter hooks, and test infrastructure (framework, coverage tooling, testing docs) — into your `.claude/` directory. It detects your project's stacks (Python, Node, Rust, UI frameworks, etc.) and installs the matching quality doc for each. This includes **skill authoring** as a recognized stack: if your project is a Claude Code plugin, a Codex skill repo, a prompt library, or any other project whose "source code" includes markdown instructions authored for an AI agent, init installs `skill-writing-guidelines.md` alongside `coding-guidelines.md`, and review/refactor skills route markdown instruction files through the skill-writing lens while routing code files through the coding lens. The plugin bundles quality agents at two levels: **plugin-level agents** (code-simplifier, test-guardian) that define reusable quality concerns, and **skill-level agents** that adapt them for specific workflows within skills like code-review, refactor, and tdd. Skill-level agents often extend the plugin-level definitions with skill-specific scope and output format — see [`references/agent-architecture.md`](references/agent-architecture.md) for the full architecture. From that point on, skills that analyze or modify code load the relevant guidelines, and skills that make completion claims apply the verification protocol as a gate before reporting.

`/optimus:code-review` doesn't run a generic review — its agents check *your* naming conventions, *your* architectural patterns, and *your* DRY principles alongside bugs and security. For projects with a skill-authoring stack, it also reviews markdown instruction files against *your* skill-writing conventions (progressive disclosure, writing style, reference-depth limits). `/optimus:tdd` applies `coding-guidelines.md` during the Refactor step. `/optimus:refactor` uses them as its quality lens. `/optimus:unit-test` follows them for test naming and structure.

Every skill is also conservative by default — `/optimus:unit-test` never refactors source code, and `/optimus:commit` warns about secret files before proceeding.

The result: consistent patterns, meaningful names, and lean context across every operation — exactly the signals that keep Claude Code accurate and productive.

## Design Principles

**Explicit invocation** — Skills never auto-trigger. Claude Code's default behavior is never altered unless you explicitly call a `/optimus` skill.

**Project-scoped output** — Formatter hooks and coding guidelines are installed into `.claude/` and travel with the repo via git — self-contained and working for every teammate without the plugin. The plugin layers development skills on top: TDD, code-review, commit, refactor, and more.

## Skills

### Core

| Skill | Description |
|-------|-------------|
| [`/optimus:init`](skills/init/README.md) | Initializes effective project documentation, formatter hooks, and unit test infrastructure. Detects empty directories and offers new-project scaffolding. Intelligent audit on re-run. Flags broken test baselines in the summary; repairs build-level issues only (never test logic). |
| [`/optimus:unit-test`](skills/unit-test/README.md) | Discovers test coverage gaps and writes convention-following tests. Never refactors source code and never fixes pre-existing failing tests — stops with a triage pointer when the test baseline is broken. *Requires init.* |
| [`/optimus:unit-test-deep`](skills/unit-test-deep/README.md) | Iterative test-coverage improvement — alternates `/optimus:unit-test` (writes tests + measures coverage) with `/optimus:refactor testability` (unblocks untestable code) per cycle, in fresh subagent contexts. Default 5 cycles, hard cap 10. *Requires init + test command.* |
| [`/optimus:tdd`](skills/tdd/README.md) | Guides test-driven development through Red-Green-Refactor cycles with per-behavior commits, parallel quality gate, and branch push. Recommends `/optimus:pr` as the explicit next step in the same conversation so the PR/MR captures TDD signals (behaviors, coverage delta) into the description. *Requires init.* |
| [`/optimus:workflow`](skills/workflow/README.md) | Implements a spec by having Claude design and launch a Claude Code dynamic workflow — parallel subagents that build in the background with test-first applied as a quality bar. The self-orchestrated, parallel counterpart to `/optimus:tdd`'s supervised Red-Green-Refactor; prefer it for large or parallelizable specs. No mid-run input; edits auto-approved; uses meaningfully more tokens. *Requires init.* |
| [`/optimus:spec-init`](skills/spec-init/README.md) | Scaffolds an empty, product-neutral docs-first SDD steering cascade (product vision, MVP PRD, target tech-stack) for a human to fill, then hands off to brainstorm. `brainstorm` and `tdd` read it as steering. Authors no PM content — emits skeletons only. |
| [`/optimus:brainstorm`](skills/brainstorm/README.md) | Guides structured design brainstorming — explores the codebase, proposes multiple approaches with trade-offs, and writes an approved spec to `docs/specs/`. For stakeholder-facing or acceptance-criteria-driven tasks, the spec includes a Given/When/Then Scenarios section that `/optimus:tdd` consumes as its behavior list. Use before implementation to think through design decisions. |
| [`/optimus:refactor`](skills/refactor/README.md) | Refactors code for guideline compliance and testability using 4 parallel agents. `testability` or `guidelines` focus mode to prioritize finding categories. *Run init first (recommended).* |
| [`/optimus:refactor-deep`](skills/refactor-deep/README.md) | Iterative project refactor — runs `/optimus:refactor` in a fresh subagent context per iteration, applies fixes, runs tests, bisects failures. Supports `testability` and `guidelines` focus. Default 8 iterations, hard cap 20. *Requires init + test command.* |
| [`/optimus:code-review`](skills/code-review/README.md) | Reviews changes for bugs, security issues, and guideline compliance using 5 to 7 parallel agents. Auto-routes to PR mode on a clean branch with a fully-pushed open PR/MR. *Run init first (recommended).* |
| [`/optimus:code-review-deep`](skills/code-review-deep/README.md) | Iterative auto-fix code review — runs `/optimus:code-review` in a fresh subagent context per iteration, applies fixes, runs tests, bisects failures. Default 8 iterations, hard cap 20. *Requires init + test command.* |

### Utility

| Skill | Description |
|-------|-------------|
| [`/optimus:branch`](skills/branch/README.md) | Switches local changes to a new conventionally named branch derived from conversation context and git diffs. Never commits or pushes. |
| [`/optimus:worktree`](skills/worktree/README.md) | Creates an isolated git worktree for parallel development on a separate branch. Runs project setup and test baseline automatically. |
| [`/optimus:handoff`](skills/handoff/README.md) | Compacts the current conversation into a single self-contained, tool-agnostic handoff document under `docs/handoffs/` so any fresh agent can resume the work by reading only that file. References committed artifacts by path/URL, inlines anything unpushed, and redacts secrets/PII. Re-run to enhance or overwrite the shared doc. |
| [`/optimus:how-to-run`](skills/how-to-run/README.md) | Generates a `HOW-TO-RUN.md` that teaches a new developer how to set up their environment and run the project locally — detects toolchain, source dependencies, external services, and env config across web, C/C++, native mobile, JVM/Android, game-engine, embedded/firmware, and backend stacks. When the file already exists, audits it against actual project state and offers a guided in-chat walkthrough of the documented steps (the skill never executes anything). Writes only `HOW-TO-RUN.md`; reports outdated info found elsewhere. |
| [`/optimus:jira`](skills/jira/README.md) | Fetches and optimizes context from a JIRA issue — distills into a structured task saved to `docs/jira/` for downstream skills to auto-detect. Analyzes the codebase to surface missing criteria, scope, and risks. Recommends next skill based on codebase-assessed complexity. Optionally enriches the JIRA issue with a structured analysis comment. Re-runs reconcile existing context against the latest JIRA state; Complex-scope analyses can opt in to spawn implementation tickets in JIRA. |
| [`/optimus:pr`](skills/pr/README.md) | Creates or updates a PR/MR with structured summary, changes, rationale, and test plan. Captures intent from the implementation conversation when run in the same session — `/optimus:code-review` consumes that intent. Supports GitHub and GitLab. |
| [`/optimus:permissions`](skills/permissions/README.md) | Configures branch protection, precious file safety, and auto-approved routine tool calls via allow/deny rules and a PreToolUse hook. |
| [`/optimus:commit`](skills/commit/README.md) | Stages, commits, and optionally pushes with a conventional commit message. Captures the "why" from the implementation conversation into the message body when run in the same session. Offers feature branch creation on protected branches. |
| [`/optimus:commit-message`](skills/commit-message/README.md) | Suggests conventional commit messages from local git changes. Benefits from running in the implementation conversation. Recommends splitting multi-concern diffs. Read-only. |
| [`/optimus:prompt`](skills/prompt/README.md) | Crafts optimized, copy-ready prompts for any AI tool — extracts intent, selects from 14 templates (including Claude Code dynamic-workflow orchestration), and audits for token efficiency. |
| [`/optimus:reset`](skills/reset/README.md) | Removes files installed by init and permissions. Classifies each file before deletion and always asks for confirmation. |

## Recommended Workflow

1. **Safety guardrails** — `/optimus:permissions` for branch protection, precious file safety, and streamlined tool permissions
2. **Initial setup** — `/optimus:init` to generate project context and set up test infrastructure (audits and updates if already present)
3. **Test coverage** — `/optimus:unit-test` to write tests and improve coverage (or `/optimus:unit-test-deep` for an automated multi-cycle coverage + testability refactoring loop with fresh context per phase)
4. **Code quality** — `/optimus:refactor` for full codebase refactoring against your coding guidelines and testability (if unit-test flagged untestable code, use `/optimus:refactor testability` then re-run `/optimus:unit-test` after refactoring — or use `/optimus:unit-test-deep` which automates this cycle)

**During development:**

| Task complexity | Workflow | Skills used |
|----------------|----------|-------------|
| Simple bug or small feature | `/optimus:tdd "description"` → `/optimus:pr` | 2 skills |
| JIRA-tracked work, clear requirements | `/optimus:jira PROJ-123` → `/optimus:tdd` → `/optimus:pr` | 3 skills |
| JIRA-tracked, moderate complexity | `/optimus:jira PROJ-123` → plan mode (jira generates prompt) → `/optimus:tdd` → `/optimus:pr` | 3 skills + plan mode |
| Complex feature, design decisions needed | `/optimus:jira` → `/optimus:brainstorm` → plan mode → `/optimus:tdd` → `/optimus:pr` | 4 skills + plan mode |
| Idea without JIRA | `/optimus:brainstorm` → plan mode → `/optimus:tdd` → `/optimus:pr` | 3 skills + plan mode |
| New product, docs-first (greenfield) | `/optimus:spec-init` → fill the cascade → `/optimus:brainstorm` → plan mode → `/optimus:tdd` → `/optimus:pr` | 4 skills + plan mode |

Each skill recommends the next step based on task complexity — you don't need to memorize these paths. Any `/optimus:tdd` step above can be swapped for `/optimus:workflow` to build the spec as a self-orchestrated parallel dynamic workflow (test-first as a quality bar) instead of supervised TDD cycles — `/optimus:workflow` launches directly in normal mode: where a flow above has a `plan mode → /optimus:tdd` sequence, it replaces both together; where it has a bare `/optimus:tdd` step, it simply takes that step's place (there is no plan-mode iteration before a workflow). Also available: `/optimus:branch` to move work to a properly named branch, `/optimus:worktree` for parallel isolated workspaces, `/optimus:prompt` to craft optimized prompts for any AI tool, `/optimus:commit` for conventional commits (or `/optimus:commit-message` to preview).

> **Stakeholder-facing features?** Acceptance criteria are a first-class part of the design artifact (see `/optimus:brainstorm` in the [Skills](#skills) table above) — no new skill, no Cucumber/Gherkin tooling.

**Before merging — keep intent flowing from implementation to review:**

The canonical chain is **implement (e.g., `/optimus:tdd`) → `/optimus:commit` → `/optimus:pr` → `/optimus:code-review`**. `/optimus:commit` and `/optimus:pr` are *continuation skills* — they capture the implementation conversation's context into durable artifacts (commit messages, PR description). When `/optimus:tdd` is the implement step, its per-cycle auto-commits replace the `/optimus:commit` step and its Step 9 pushes the branch automatically, so the flow collapses to **`/optimus:tdd` → `/optimus:pr` → `/optimus:code-review`** with the first two in the same conversation. `/optimus:code-review` gathers its own context from a fresh conversation.

`/optimus:commit-message` is the read-only sibling of `/optimus:commit` and is also a continuation skill; see [`references/skill-handoff.md`](references/skill-handoff.md) for the full list.

1. **Implement** your changes in a conversation (TDD, brainstorm-driven, or freeform).
2. **Stay in the implementation conversation** and run `/optimus:commit` — it can capture the "why" from the conversation into the commit message body, not just summarize the diff.
3. **Still in the same conversation**, run `/optimus:pr` — it captures decisions, scope, non-goals, and trade-offs into the PR description for downstream review.
4. **Switch to a fresh conversation** and run `/optimus:code-review`. It reads the PR description as author intent context and checks whether the implementation delivers what was supposed to be built, not just whether it follows style guidelines.

See [`references/skill-handoff.md`](references/skill-handoff.md) under "Continuation skills" for the full list. Each upstream skill's closing tip differentiates continuation skills (stay in conversation) from non-continuation skills (start fresh) so you don't have to remember the rule.

**After major changes** — re-run `/optimus:init` to audit and refresh guidelines.

**New to a codebase?** — `/optimus:how-to-run` generates a `HOW-TO-RUN.md` that teaches a new developer how to set up their environment and run the project locally.

**Removing optimus** — `/optimus:reset` to remove optimus-generated files from the project (for clean reinstall or to stop using optimus).

## Why It Works

What makes a good developer productive also makes Claude Code productive: **clean code, good tests, and clear docs.**

Research backs this up: AI tools introduce [30%+ more defects](https://arxiv.org/abs/2601.02200) on poorly maintained code, and LLM performance [degrades up to 85%](https://arxiv.org/abs/2510.05381) as context length grows. Clean, DRY code with meaningful names keeps context lean and gives the LLM better semantic signals. The [2025 DORA report](https://cloud.google.com/discover/how-test-driven-development-amplifies-ai-success) puts it simply: AI amplifies existing practices, good or bad.

Another key point: [providing LLMs with tests alongside tasks consistently improves code generation](https://arxiv.org/abs/2402.13521). Tests enable self-correction. Anthropic's [#1 best practice](https://code.claude.com/docs/en/best-practices) for Claude Code reflects this: "make the AI self-verifying". Unit tests and TDD are the purest way to achieve it.

AI assistants also tend toward [sycophancy](https://blog.scielo.org/en/2026/03/13/sycophancy-in-ai-the-risk-of-complacency/) — validating ideas without critical pushback. A [2025 METR trial](https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/) found developers using AI were [19% slower yet believed they were faster](https://arxiv.org/abs/2507.09089). This plugin counters that: every skill enforces project-defined standards as the source of truth, a shared [verification protocol](skills/init/references/verification-protocol.md) requires evidence before any completion claim and challenges assumptions before committing to an approach, code review runs independent duplicate guideline agents and verifies each finding against the actual code, and TDD ensures tests define what is correct instead of relying on the AI's confidence.

## Complementary Tools

optimus-claude is designed to work alongside official tools, not replace them. Use Anthropic's official [code-review](https://github.com/anthropics/claude-code/tree/main/plugins/code-review) plugin for post-push PR review, [claude-md-management](https://claude.com/plugins/claude-md-management) for CLAUDE.md scoring and revision, the builtin `/simplify` for per-change cleanup (complemented by `/optimus:refactor` for project-wide restructuring), and Claude Code's [built-in sandboxing](https://code.claude.com/docs/en/sandboxing) or [Docker containers](https://www.docker.com/blog/docker-sandboxes-run-claude-code-and-other-coding-agents-unsupervised-but-safely/) for fully autonomous agent execution with OS-level isolation.

Claude Code's [dynamic workflows](https://code.claude.com/docs/en/workflows) are complementary rather than competing. The `/optimus:*-deep` skills are slash-invoked auto-fix orchestrators that persist progress to disk and resume across sessions, with no dependency on a research-preview feature — while `/optimus:prompt` can emit prompts that *trigger* a native dynamic workflow for one-off background fan-outs (its Template N). Reach for a `*-deep` skill for the iterative fix loop; reach for a dynamic workflow for a one-off, background, multi-agent sweep.

Claude Code's [`/goal`](https://code.claude.com/docs/en/goal) command is similarly complementary, not a replacement for the `*-deep` skills. `/goal` sets a session-scoped completion condition and auto-iterates until a **read-only** evaluator judges it met — it never runs the test suite itself, isn't checked into the repo, and accumulates context within one session. The `*-deep` skills provide what that can't: deterministic test bisection (reverting the exact fix that broke the build), a fresh subagent per iteration so context never decays, resumable on-disk progress, and a checked-in, CI-gated contract. Reach for `/goal` for lightweight, autonomous "work until a verifiable end-state" in a single session; reach for a `*-deep` skill for the deterministic, resumable, team-shareable fix loop (`/optimus:workflow` remains the option for an autonomous parallel build, `/optimus:tdd` for supervised test-first). One caveat when pointing `/goal` at optimus: the skills set `disable-model-invocation: true`, so a goal condition that depends on a `/optimus:*` skill the model can't auto-invoke may never be satisfied and can loop — invoke the skill yourself and let the goal judge the result.

## Troubleshooting

### Windows: SSL certificate error during install

If you see `SSL certificate OpenSSL verify result: unable to get local issuer certificate` when running `/plugin marketplace add`, Git for Windows is using an outdated OpenSSL CA bundle. Fix it by switching to the native Windows certificate store:

```shell
git config --global http.sslBackend schannel
```

Then retry the install command.

### Upgrading from 1.x: `deep harness` mode and the Python harness scripts are gone

2.0 replaced the two terminal-run Python harnesses with three in-conversation orchestrator skills. If you scripted the old entry points, migrate:

| Removed in 2.0 | Use instead |
|----------------|-------------|
| `/optimus:code-review deep` / `… deep harness` | `/optimus:code-review-deep` |
| `/optimus:refactor deep` / `… deep harness` | `/optimus:refactor-deep` |
| `/optimus:unit-test deep` / `… deep harness` | `/optimus:unit-test-deep` |
| `python scripts/deep-mode-harness/main.py …` | `/optimus:code-review-deep` (or `/optimus:refactor-deep`) |
| `python scripts/test-coverage-harness/main.py …` | `/optimus:unit-test-deep` |

The `*-deep` skills run inside your Claude Code conversation, persist state to `.claude/*-deep-progress.json`, support `--resume`, and accept `--yes` for non-interactive/CI use (e.g. `claude -p "/optimus:code-review-deep --yes 'src/auth'"`).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for project structure, skill anatomy, feature branch testing, and local development setup.

## Acknowledgements

The `/optimus:prompt` skill's prompt engineering techniques (intent extraction, tool routing, diagnostic patterns, templates, safe/excluded technique classification) are adapted from [prompt-master](https://github.com/nidhinjs/prompt-master) by [@nidhinjs](https://github.com/nidhinjs).

## Research & References

- [Claude Code Best Practices](https://code.claude.com/docs/en/best-practices) — Anthropic: testing as #1 practice, compact CLAUDE.md, deterministic hooks, custom subagents
- [How TDD Amplifies AI Success](https://cloud.google.com/discover/how-test-driven-development-amplifies-ai-success) — DORA Report 2025: AI adoption increases delivery instability; TDD provides the control system
- [Code for Machines, Not Just Humans](https://arxiv.org/abs/2601.02200) — Borg et al. 2026: AI defect risk increases 30%+ on unhealthy code
- [AI-Friendly Code Design](https://www.thoughtworks.com/radar/techniques/ai-friendly-code-design) — Thoughtworks Tech Radar Vol. 32: "good software design for humans also benefits AI"
- [Context Length Alone Hurts LLM Performance](https://arxiv.org/abs/2510.05381) — Du et al. 2025: 13.9%–85% degradation as input length increases
- [Writing a Good CLAUDE.md](https://www.humanlayer.dev/blog/writing-a-good-claude-md) — HumanLayer: WHAT/WHY/HOW structure, progressive disclosure, <60 lines
- [Test-Driven Development for Code Generation](https://arxiv.org/abs/2402.13521) — Mathews et al. 2024: providing LLMs with tests alongside problem statements consistently improves code generation outcomes
- [AI Makes Engineering Discipline More Important](https://codemanship.wordpress.com/2026/02/26/71-of-developers-and-engineering-leaders-believe-ai-makes-engineering-discipline-more-important/) — Codemanship 2026: 71% of developers say disciplined practices like TDD become more important with AI, not less
- [AI Developer Productivity: Perception vs. Reality](https://arxiv.org/abs/2507.09089) — METR 2025: experienced developers were 19% slower with AI but believed they were 24% faster — a striking confirmation bias gap
- [Sycophancy in AI: The Risk of Complacency](https://blog.scielo.org/en/2026/03/13/sycophancy-in-ai-the-risk-of-complacency/) — SciELO 2026: AI sycophancy increases short-term productivity but reduces quality of collaborative work
- [LLM-Powered Devil's Advocate for Decision-Making](https://dl.acm.org/doi/fullHtml/10.1145/3640543.3645199) — IUI 2024: multi-agent debate reduces social influence bias and fosters balanced evaluation
