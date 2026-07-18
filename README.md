<div align="center">
  <img src="assets/banner.png" alt="optimus-claude" width="600">
</div>

<p align="center">
  <img src="https://img.shields.io/badge/version-3.1.0-blue" alt="Version">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/Claude_Code-1.0.33+-blueviolet" alt="Claude Code">
  <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey" alt="Platform">
</p>

**A Claude Code plugin that sets up your project for effective AI-assisted engineering.**

---

**The problem:** AI amplifies whatever it finds. Messy code leads to messier AI-generated code, which becomes the new context for even worse output — a vicious cycle that compounds faster than any human could create technical debt. Without maintained context, any AI coding tool's quality degrades with every file it reads.

**The solution:** Optimus Claude generates tailored CLAUDE.md files, coding guidelines, formatter hooks, and test infrastructure from your actual codebase, then enforces those standards in every quality pass — code review, refactoring, TDD, and a resumable deep-fix loop. Use it regularly and your project stays clean, consistent, tested, and well-documented: exactly the conditions where Claude Code performs at its prime.

**The philosophy:** It's all about perfecting context. The codebase, prompts, unit tests, docs, commit messages, PR descriptions — it all adds up to shape how well Claude Code performs. Every skill is lean by design: 3.0 cut the plugin's own instruction footprint by more than half so the skills spend your context window on your project, not on themselves.

## Quick Start

Run these commands inside Claude Code:

```shell
/plugin marketplace add https://github.com/oprogramadorreal/optimus-claude.git
/plugin install optimus@optimus-claude
```

Then start a new session and type `/optimus:init` in any project directory. Having trouble? See [Troubleshooting](#troubleshooting).

## How It Works

`/optimus:init` analyzes your codebase and generates constraint docs — coding guidelines, CLAUDE.md, formatter hooks, and test infrastructure — into your `.claude/` directory, detecting your stacks (Python, Node, Rust, UI frameworks, and more). It also recognizes **skill authoring** as a stack: if your project's "source code" includes markdown instructions authored for an AI agent (a Claude Code plugin, a prompt library), init installs `skill-writing-guidelines.md`, and the review/refactor skills route markdown instruction files through that lens while code files go through `coding-guidelines.md`.

From then on, the quality skills enforce *your* standards, not generic ones: `/optimus:code-review` checks your naming conventions and architectural patterns alongside bugs and security; `/optimus:tdd` applies your guidelines during the Refactor step; `/optimus:refactor` uses them as its quality lens; `/optimus:unit-test` follows your testing conventions. `/optimus:deep` sustains any of those passes across iterations — a fresh subagent per pass, tests and deterministic bisection between passes, resumable on-disk state.

**Design principles:** skills never auto-trigger (the only always-on component is a lightweight read-only SessionStart hook that surfaces project state), and generated output is project-scoped — guidelines and hooks travel with the repo via git and work for every teammate without the plugin.

## Skills

### Core

| Skill | Description |
|-------|-------------|
| [`/optimus:init`](skills/init/README.md) | Initializes project documentation, formatter hooks, and test infrastructure from your actual codebase. Offers new-project scaffolding on empty directories; audits and syncs on re-run. |
| [`/optimus:brainstorm`](skills/brainstorm/README.md) | Structured design brainstorming — explores the codebase, proposes approaches with trade-offs, writes an approved spec to `docs/specs/` that `/optimus:tdd` consumes. `scaffold` mode stamps an empty docs-first steering cascade (product vision, MVP PRD, tech stack) for a human to fill. |
| [`/optimus:jira`](skills/jira/README.md) | Fetches a JIRA issue via MCP and distills it into a structured task at `docs/jira/` that downstream skills auto-detect. Analyzes the codebase for missing criteria and risks; recommends the next skill by complexity. |
| [`/optimus:tdd`](skills/tdd/README.md) | Test-driven development through Red-Green-Refactor cycles with per-behavior commits, a parallel quality gate, and branch push. Auto-detects specs from `docs/specs/` or `docs/jira/`. *Requires init.* |
| [`/optimus:unit-test`](skills/unit-test/README.md) | Discovers coverage gaps and writes convention-following tests. Never refactors source code; stops with a triage pointer when the test baseline is broken. *Requires init.* |
| [`/optimus:refactor`](skills/refactor/README.md) | Refactors for guideline compliance and testability using parallel analysis agents, with `testability` and `guidelines` focus modes. *Run init first.* |
| [`/optimus:code-review`](skills/code-review/README.md) | Reviews changes for bugs, security issues, and guideline compliance using parallel review agents. Auto-routes to PR mode on a clean branch with an open PR/MR and reads the PR description as author intent. *Run init first.* |
| [`/optimus:deep`](skills/deep/README.md) | Iterative auto-fix orchestrator: `deep review`, `deep refactor`, or `deep coverage`. Runs the base skill in a fresh subagent per iteration, applies fixes, runs tests, bisects failures, and resumes across sessions. *Requires init + test command.* |

### Utility

| Skill | Description |
|-------|-------------|
| [`/optimus:commit`](skills/commit/README.md) | Stages, commits, and optionally pushes with a conventional commit message; captures the "why" from the implementation conversation. `suggest` mode is read-only; `branch` mode moves local changes to a conventionally named branch without committing. |
| [`/optimus:pr`](skills/pr/README.md) | Creates or updates a PR/MR with a structured description — intent, scope, non-goals, test plan — that `/optimus:code-review` consumes. Supports GitHub and GitLab. |
| [`/optimus:worktree`](skills/worktree/README.md) | Creates an isolated git worktree for parallel development, running project setup and a test baseline automatically. |
| [`/optimus:handoff`](skills/handoff/README.md) | Compacts the current conversation into a self-contained, redacted handoff doc under `docs/handoffs/` so any fresh agent can resume the work. |
| [`/optimus:how-to-run`](skills/how-to-run/README.md) | Generates a `HOW-TO-RUN.md` that teaches a new developer how to set up and run the project locally; audits it against actual project state on re-run. |
| [`/optimus:permissions`](skills/permissions/README.md) | Configures branch protection, precious-file safety, and auto-approved routine tool calls via allow/deny rules and a PreToolUse hook. |
| [`/optimus:prompt`](skills/prompt/README.md) | Crafts optimized, copy-ready prompts for any AI tool — extracts intent, selects a template, audits for token efficiency. |
| [`/optimus:reset`](skills/reset/README.md) | Removes files installed by init and permissions. Classifies each file before deletion and always asks for confirmation. |

## Recommended Workflow

1. **Setup** — `/optimus:permissions` for guardrails, then `/optimus:init` to generate project context and test infrastructure.
2. **Strengthen** — `/optimus:unit-test` for coverage (or `/optimus:deep coverage` for the automated loop), `/optimus:refactor` for code quality.
3. **Build** — pick the entry point that matches the task: `/optimus:tdd "description"` directly for small clear work; `/optimus:jira PROJ-123` first for tracked work; `/optimus:brainstorm` first when design decisions are needed (greenfield products start with `/optimus:brainstorm scaffold`).
4. **Ship** — `/optimus:commit` → `/optimus:pr` → `/optimus:code-review` in a fresh conversation (or `/optimus:deep review` for iterative auto-fix).

**Keep intent flowing from implementation to review:** stay in the implementation conversation when running `/optimus:commit` and `/optimus:pr` — they capture *why* the change was made into the commit message and PR description. Then review in a fresh conversation: `/optimus:code-review` reads the PR description as author intent and checks whether the implementation delivers what it claims, not just whether it follows style rules. (`/optimus:tdd` auto-commits per cycle and pushes at the end, so its flow collapses to `tdd` → `pr` → review.)

**After major changes** — re-run `/optimus:init` to audit and refresh the generated docs. **New to a codebase?** — `/optimus:how-to-run`. **Removing optimus** — `/optimus:reset`.

## Why It Works

What makes a good developer productive also makes Claude Code productive: **clean code, good tests, and clear docs.**

Research backs this up: AI tools introduce [30%+ more defects](https://arxiv.org/abs/2601.02200) on poorly maintained code, and LLM performance [degrades up to 85%](https://arxiv.org/abs/2510.05381) as context length grows. Clean, DRY code with meaningful names keeps context lean and gives the LLM better semantic signals. The [2025 DORA report](https://cloud.google.com/discover/how-test-driven-development-amplifies-ai-success) puts it simply: AI amplifies existing practices, good or bad.

Another key point: [providing LLMs with tests alongside tasks consistently improves code generation](https://arxiv.org/abs/2402.13521). Tests enable self-correction — Anthropic's [#1 best practice](https://code.claude.com/docs/en/best-practices) for Claude Code is giving it a way to verify its work, and unit tests and TDD are the purest way to achieve it.

AI assistants also tend toward [sycophancy](https://blog.scielo.org/en/2026/03/13/sycophancy-in-ai-the-risk-of-complacency/) — validating ideas without critical pushback. This plugin counters that: every skill enforces project-defined standards as the source of truth, quality claims require evidence from actual command output, code review runs independent duplicate guideline agents and verifies each finding against the code, and TDD ensures tests define what is correct instead of relying on the AI's confidence.

## Complementary Tools

optimus-claude works alongside official tools, not against them. Use Anthropic's official [code-review](https://github.com/anthropics/claude-code/tree/main/plugins/code-review) plugin for post-push PR review, the builtin `/simplify` for per-change cleanup (complemented by `/optimus:refactor` for project-wide restructuring), Claude Code's native [dynamic workflows](https://code.claude.com/docs/en/workflows) for one-off background multi-agent builds and sweeps, and [built-in sandboxing](https://code.claude.com/docs/en/sandboxing) for autonomous execution with OS-level isolation.

Claude Code's [`/goal`](https://code.claude.com/docs/en/goal) is complementary to `/optimus:deep`: reach for `/goal` for lightweight "work until a condition holds" in a single session; reach for `/optimus:deep` for the deterministic, resumable fix loop — fresh subagent per iteration, test bisection that reverts the exact fix that broke the build, and on-disk state that survives across sessions.

## Troubleshooting

### Windows: SSL certificate error during install

If you see `SSL certificate OpenSSL verify result: unable to get local issuer certificate` when running `/plugin marketplace add`, Git for Windows is using an outdated OpenSSL CA bundle. Switch to the native Windows certificate store, then retry:

```shell
git config --global http.sslBackend schannel
```

### Upgrading from 2.x

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

The two terminal-run Python harnesses were replaced in 2.0 by in-conversation orchestration — now `/optimus:deep` (see the 2.x table above).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for project structure, skill anatomy, feature branch testing, and local development setup.

## Acknowledgements

The `/optimus:prompt` skill's prompt engineering techniques are adapted from [prompt-master](https://github.com/nidhinjs/prompt-master) by [@nidhinjs](https://github.com/nidhinjs).

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
