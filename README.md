<div align="center">
  <img src="assets/banner.png" alt="optimus-claude" width="600">
</div>

**A Claude Code plugin that sets up your project for effective AI-assisted development** — optimized CLAUDE.md files, effective coding guidelines, formatter hooks, quality agents, TDD and test coverage, all tailored to your actual codebase.

*Use it regularly and your project stays clean, consistent, tested, and well-documented — exactly the conditions where Claude Code performs at its prime.*

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

## Why This Plugin?

What makes a good developer productive also makes Claude Code productive: **clean code, good tests, and clear docs.**

Research backs this up: AI tools introduce [30%+ more defects](https://arxiv.org/abs/2601.02200) on poorly maintained code, and LLM performance [degrades up to 85%](https://arxiv.org/abs/2510.05381) as context length grows. Clean, DRY code with meaningful names keeps context lean and gives the LLM better semantic signals. The [2025 DORA report](https://cloud.google.com/discover/how-test-driven-development-amplifies-ai-success) puts it simply: AI amplifies existing practices, good or bad.

Another key point: [providing LLMs with tests alongside tasks consistently improves code generation](https://arxiv.org/abs/2402.13521). Tests enable self-correction. Anthropic's [#1 best practice](https://code.claude.com/docs/en/best-practices) for Claude Code reflects this: "make the AI self-verifying". Unit tests and TDD are the purest way to achieve it.

## How It Works

Every skill operates on the same shared foundation: **your project's coding guidelines**.

`/optimus:init` analyzes your codebase and generates constraint docs — coding guidelines, CLAUDE.md, quality agents, and formatter hooks — into your `.claude/` directory. From that point on, every optimus skill loads and enforces those same guidelines.

`/optimus:code-review` doesn't run a generic review — its agents check *your* naming conventions, *your* architectural patterns, and *your* DRY principles alongside bugs and security. `/optimus:tdd` applies them during the Refactor step. `/optimus:simplify` uses them as its quality lens. `/optimus:unit-test` follows them for test naming and structure.

The result: consistent patterns, meaningful names, and lean context across every operation — exactly the signals that keep Claude Code accurate and productive.

## Design Principles

**Explicit invocation** — Skills never auto-trigger. Claude Code's default behavior is never altered unless you explicitly call a skill.

**Project-scoped output** — Everything is written into the project's `.claude/` directory and travels with the repo via git — any teammate gets identical behavior, even without the plugin installed. Keep the plugin installed for daily skills like TDD, commit-message, and code-review.

**Session-start awareness** — A lightweight hook runs on every session start, resume, clear, and compact to check project state (init status, test infrastructure, quality agents, git state). Fully configured projects produce zero output — no context waste.

## Skills

### Core

| Skill | Description |
|-------|-------------|
| [`/optimus:init`](skills/init/README.md) | Project setup — CLAUDE.md, coding guidelines, formatter hooks, code-simplifier & test-guardian agents. Monorepos, multi-repo workspaces, intelligent audit on re-run (template files always refreshed, plugin version tracked in `.claude/.optimus-version` to detect template improvements across updates). Best-effort fallback for unsupported stacks via web search. |
| [`/optimus:unit-test`](skills/unit-test/README.md) | Fills test coverage gaps — discovers gaps, provisions infrastructure, writes convention-following tests. Never refactors source. *Requires init.* |
| [`/optimus:tdd`](skills/tdd/README.md) | Test-driven Red-Green-Refactor — feature branch, per-behavior commits, parallel agent quality gate, PR/MR. The [most effective discipline](https://code.claude.com/docs/en/best-practices) for reliable AI-assisted code. *Requires init.* |
| [`/optimus:simplify`](skills/simplify/README.md) | Cross-file code simplification — duplication, pattern inconsistency, architectural drift. Prioritized plan (capped at 12), test-verified. `deep` mode for iterative cleanup until clean (max 5 iterations). *Run init first (recommended).* |
| [`/optimus:code-review`](skills/code-review/README.md) | Pre-merge review with up to 6 parallel agents — bugs, security, guideline compliance, code-simplifier, test-guardian. GitHub & GitLab. *Run init first (recommended).* |
| [`/optimus:verify`](skills/verify/README.md) | Feature branch verification in an isolated sandbox — extracts/generates a test plan from the PR and branch diff, runs automated checks, launches up to 4 parallel agents for functional verification (tests, integration, mock projects, code tracing). Never pushes to remote. *Run init first (recommended).* |

### Utility

| Skill | Description |
|-------|-------------|
| [`/optimus:dev-setup`](skills/dev-setup/README.md) | Ensures the project README has comprehensive, accurate "how to run in dev mode" instructions — detects tech stack, external services (docker-compose), environment config, and generates step-by-step setup sections. Audits existing instructions against actual project state. Works standalone or after init. |
| [`/optimus:pr`](skills/pr/README.md) | Creates or updates PR/MR with [Conventional PR](skills/pr/references/pr-template.md) format — structured summary, changes, rationale, test plan. Offers CLI installation. Shared template used by TDD. |
| [`/optimus:permissions`](skills/permissions/README.md) | Allow/deny rules + PreToolUse hook for tiered path security and branch-aware git protection. Feature branches work freely; protected branches require PRs. Useful on native Windows. |
| [`/optimus:commit-message`](skills/commit-message/README.md) | [Conventional commit](https://www.conventionalcommits.org/) suggestions from local git changes. Splits multi-concern diffs. Multi-repo aware. |

## Recommended Workflow

1. **Initial setup** — `/optimus:init` to generate project context (audits and updates if already present)
2. **Test coverage** — `/optimus:unit-test` to establish or improve unit tests
3. **After major changes** — re-run `/optimus:init` to audit and refresh docs
4. **Code quality** — `/optimus:simplify` for full codebase analysis against your coding guidelines

**During development** — `/optimus:tdd` to build features test-first, `/optimus:commit-message` for conventional commits.

**Before merging** — `/optimus:pr` to create or update pull requests, `/optimus:verify` to prove the feature branch works in an isolated sandbox, `/optimus:code-review` for pre-merge code quality review.

**New to a codebase?** — `/optimus:dev-setup` ensures the README has accurate development setup instructions for onboarding.

**Complementary tools** — Anthropic's official [code-review](https://github.com/anthropics/claude-code/tree/main/plugins/code-review) plugin for post-push PR review, [claude-md-management](https://claude.com/plugins/claude-md-management) for CLAUDE.md scoring and revision, and the builtin `/simplify` for per-change cleanup.

## Troubleshooting

### Windows: SSL certificate error during install

If you see `SSL certificate OpenSSL verify result: unable to get local issuer certificate` when running `/plugin marketplace add`, Git for Windows is using an outdated OpenSSL CA bundle. Fix it by switching to the native Windows certificate store:

```shell
git config --global http.sslBackend schannel
```

Then retry the install command.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for project structure, skill anatomy, feature branch testing, and local development setup.

## Research & References

- [Claude Code Best Practices](https://code.claude.com/docs/en/best-practices) — Anthropic: testing as #1 practice, compact CLAUDE.md, deterministic hooks, custom subagents
- [How TDD Amplifies AI Success](https://cloud.google.com/discover/how-test-driven-development-amplifies-ai-success) — DORA Report 2025: AI adoption increases delivery instability; TDD provides the control system
- [Code for Machines, Not Just Humans](https://arxiv.org/abs/2601.02200) — Borg et al. 2026: AI defect risk increases 30%+ on unhealthy code
- [AI-Friendly Code Design](https://www.thoughtworks.com/radar/techniques/ai-friendly-code-design) — Thoughtworks Tech Radar Vol. 32: "good software design for humans also benefits AI"
- [Context Length Alone Hurts LLM Performance](https://arxiv.org/abs/2510.05381) — Du et al. 2025: 13.9%–85% degradation as input length increases
- [Writing a Good CLAUDE.md](https://www.humanlayer.dev/blog/writing-a-good-claude-md) — HumanLayer: WHAT/WHY/HOW structure, progressive disclosure, <60 lines
- [Test-Driven Development for Code Generation](https://arxiv.org/abs/2402.13521) — Mathews et al. 2024: providing LLMs with tests alongside problem statements consistently improves code generation outcomes
- [AI Makes Engineering Discipline More Important](https://codemanship.wordpress.com/2026/02/26/71-of-developers-and-engineering-leaders-believe-ai-makes-engineering-discipline-more-important/) — Codemanship 2026: 71% of developers say disciplined practices like TDD become more important with AI, not less

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Git

## License

[MIT](LICENSE)
