<div align="center">
  <img src="assets/banner.png" alt="optimus-claude" width="600">
</div>

<p align="center">
  <img src="https://img.shields.io/badge/version-1.74.0-blue" alt="Version">
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
| [`/optimus:brainstorm`](skills/brainstorm/README.md) | Guides structured design brainstorming — explores the codebase, proposes multiple approaches with trade-offs, and writes an approved design doc to the project. For stakeholder-facing or acceptance-criteria-driven tasks, the design doc includes a Given/When/Then Scenarios section that `/optimus:tdd` consumes as its behavior list. Use before implementation to think through design decisions. |
| [`/optimus:init`](skills/init/README.md) | Initializes effective project documentation, formatter hooks, and unit test infrastructure. Detects empty directories and offers new-project scaffolding. Intelligent audit on re-run. Flags broken test baselines in the summary; repairs build-level issues only (never test logic). |
| [`/optimus:unit-test`](skills/unit-test/README.md) | Discovers test coverage gaps and writes convention-following tests. Never refactors source code and never fixes pre-existing failing tests — stops with a triage pointer when the test baseline is broken. `deep` mode for iterative test generation. `deep harness` for multi-cycle test coverage + testability refactoring with fresh context per phase. *Requires init.* |
| [`/optimus:tdd`](skills/tdd/README.md) | Guides test-driven development through Red-Green-Refactor cycles with per-behavior commits, parallel quality gate, and PR/MR creation. *Requires init.* |
| [`/optimus:refactor`](skills/refactor/README.md) | Refactors code for guideline compliance and testability using 4 parallel agents. `testability` or `guidelines` focus mode to prioritize finding categories. `deep` mode for iterative refactoring. `deep harness` for multi-iteration analysis with fresh context per iteration. *Run init first (recommended).* |
| [`/optimus:code-review`](skills/code-review/README.md) | Reviews changes for bugs, security issues, and guideline compliance using 5 to 7 parallel agents. Auto-routes to PR mode on a clean branch with a fully-pushed open PR/MR. `deep` mode for iterative auto-fix. `deep harness` for multi-iteration analysis with fresh context per iteration. *Run init first (recommended).* |

### Utility

| Skill | Description |
|-------|-------------|
| [`/optimus:branch`](skills/branch/README.md) | Switches local changes to a new conventionally named branch derived from conversation context and git diffs. Never commits or pushes. |
| [`/optimus:worktree`](skills/worktree/README.md) | Creates an isolated git worktree for parallel development on a separate branch. Runs project setup and test baseline automatically. |
| [`/optimus:how-to-run`](skills/how-to-run/README.md) | Generates a `HOW-TO-RUN.md` that teaches a new developer how to set up their environment and run the project locally — works for web, C/C++, native mobile, JVM/Android, game engines, embedded/firmware, and backend stacks. Detects external services from docker-compose and from framework config files (`appsettings*.json`, `application.yml`, `config/*.exs`, Rails/Laravel configs) — config-file hits render with a `(candidate)` marker. For services not covered by docker-compose, classifies each as Docker-preferred, Shared-cloud primary, or Local install only and emits a vendor-cited `docker run` snippet; vendor-branded cloud services (AWS S3/SNS/SQS, Azure Blob/Cosmos, Firebase, Pub/Sub) resolve to their local emulators (LocalStack, Azurite, etc.) via a Vendor-Service → Emulator Index. Also detects schema-bootstrap scripts (raw SQL, seed files) and README-mentioned developer tools (IDEs, DB GUIs, browsers). Writes only `HOW-TO-RUN.md`; reports outdated info found elsewhere. When the file already exists, also offers a guided in-chat walkthrough of the documented steps with per-step user approval; safety overrides drop or rename "Run it" for matched long-running services, destructive verbs, remote-fetch executors, and platform mismatches, and per-step audit verdicts surface stale-doc warnings for steps that map to a tracked aspect. |
| [`/optimus:jira`](skills/jira/README.md) | Fetches and optimizes context from a JIRA issue — distills into a structured task saved to `docs/jira/` for downstream skills to auto-detect. Analyzes the codebase to surface missing criteria, scope, and risks. Recommends next skill based on codebase-assessed complexity. Optionally enriches the JIRA issue with a structured analysis comment. Re-runs reconcile existing context against the latest JIRA state; Complex-scope analyses can opt in to spawn implementation tickets in JIRA. |
| [`/optimus:pr`](skills/pr/README.md) | Creates or updates a PR/MR with structured summary, changes, rationale, and test plan. Supports GitHub and GitLab. |
| [`/optimus:permissions`](skills/permissions/README.md) | Configures branch protection, precious file safety, and auto-approved routine tool calls via allow/deny rules and a PreToolUse hook. |
| [`/optimus:commit`](skills/commit/README.md) | Stages, commits, and optionally pushes with a conventional commit message. Offers feature branch creation on protected branches. |
| [`/optimus:commit-message`](skills/commit-message/README.md) | Suggests conventional commit messages from local git changes. Recommends splitting multi-concern diffs. Read-only. |
| [`/optimus:prompt`](skills/prompt/README.md) | Crafts optimized, copy-ready prompts for any AI tool — extracts intent, selects from 13 templates, and audits for token efficiency. |
| [`/optimus:reset`](skills/reset/README.md) | Removes files installed by init and permissions. Classifies each file before deletion and always asks for confirmation. |

## Recommended Workflow

1. **Safety guardrails** — `/optimus:permissions` for branch protection, precious file safety, and streamlined tool permissions
2. **Initial setup** — `/optimus:init` to generate project context and set up test infrastructure (audits and updates if already present)
3. **Test coverage** — `/optimus:unit-test` to write tests and improve coverage (or `/optimus:unit-test deep harness` for automated multi-cycle coverage + testability refactoring with fresh context per phase)
4. **Code quality** — `/optimus:refactor` for full codebase refactoring against your coding guidelines and testability (if unit-test flagged untestable code, use `/optimus:refactor testability` then re-run `/optimus:unit-test` after refactoring — or use `/optimus:unit-test deep harness` which automates this cycle)

**During development:**

| Task complexity | Workflow | Skills used |
|----------------|----------|-------------|
| Simple bug or small feature | `/optimus:tdd "description"` | 1 skill |
| JIRA-tracked work, clear requirements | `/optimus:jira PROJ-123` → `/optimus:tdd` | 2 skills |
| JIRA-tracked, moderate complexity | `/optimus:jira PROJ-123` → plan mode (jira generates prompt) → `/optimus:tdd` | 2 skills + plan mode |
| Complex feature, design decisions needed | `/optimus:jira` → `/optimus:brainstorm` → plan mode → `/optimus:tdd` | 3 skills + plan mode |
| Idea without JIRA | `/optimus:brainstorm` → plan mode → `/optimus:tdd` | 2 skills + plan mode |

Each skill recommends the next step based on task complexity — you don't need to memorize these paths. Also available: `/optimus:branch` to move work to a properly named branch, `/optimus:worktree` for parallel isolated workspaces, `/optimus:prompt` to craft optimized prompts for any AI tool, `/optimus:commit` for conventional commits (or `/optimus:commit-message` to preview).

> **Stakeholder-facing features?** Acceptance criteria are a first-class part of the design artifact (see `/optimus:brainstorm` in the [Skills](#skills) table above) — no new skill, no Cucumber/Gherkin tooling.

**Before merging** — `/optimus:pr` to create or update pull requests, `/optimus:code-review` for pre-merge code quality review.

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

## Troubleshooting

### Windows: SSL certificate error during install

If you see `SSL certificate OpenSSL verify result: unable to get local issuer certificate` when running `/plugin marketplace add`, Git for Windows is using an outdated OpenSSL CA bundle. Fix it by switching to the native Windows certificate store:

```shell
git config --global http.sslBackend schannel
```

Then retry the install command.

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
