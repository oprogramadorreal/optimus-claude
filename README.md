# 🤖 optimus-claude

**A Claude Code plugin that sets up your project for effective AI-assisted development** — CLAUDE.md, coding guidelines, formatter hooks, quality agents, TDD, and test coverage, all tailored to your actual codebase.

## Quick Start

### Install

```shell
/plugin marketplace add https://github.com/oprogramadorreal/optimus-claude.git
/plugin install optimus@optimus-claude
```

### Run

Start a new Claude Code session and type `/optimus:init` in any project directory. See [Skills](#skills) for the full list.

## Why This Plugin?

What makes a good developer productive also makes Claude Code productive: **clean code, good tests, and clear docs.**

Research backs this up: AI tools introduce [30%+ more defects](https://arxiv.org/abs/2601.02200) on poorly maintained code, and LLM performance [degrades up to 85%](https://arxiv.org/abs/2510.05381) as context length grows. Clean, DRY code with meaningful names keeps context lean and gives the LLM better semantic signals. The [2025 DORA report](https://cloud.google.com/discover/how-test-driven-development-amplifies-ai-success) puts it simply: AI amplifies existing practices, good or bad.

Another key point: [providing LLMs with tests alongside tasks consistently improves code generation](https://arxiv.org/abs/2402.13521). Tests enable self-correction. Anthropic's [#1 best practice](https://code.claude.com/docs/en/best-practices) for Claude Code reflects this: "make the AI self-verifying". Unit tests and TDD are the purest way to achieve it.

## Architecture: Project-Scoped by Design

Unlike most plugins that bundle hooks and agents at the plugin level, **optimus writes everything into the project's `.claude/` directory**:

- **Hooks, agents, docs, and settings travel with the repo via git** — any teammate gets identical behavior, even without this plugin installed
- **Enforces standards linters can't check** — naming conventions, architectural patterns, DRY principles, guided by project-specific docs and agents
- **No hidden dependencies** — the generated output is self-contained, visible, auditable, and version-controlled. Keep the plugin installed for daily skills like TDD, commit-message, and code-review

## Skills

### Core

| Skill | Description |
|-------|-------------|
| [`/optimus:init`](skills/init/README.md) | Project setup — CLAUDE.md, coding guidelines, formatter hooks, code-simplifier & test-guardian agents. Monorepos, multi-repo workspaces, intelligent audit on re-run (template files always refreshed, plugin version tracked in `.claude/.optimus-version` to detect template improvements across updates). |
| [`/optimus:unit-test`](skills/unit-test/README.md) | Fills test coverage gaps — discovers gaps, provisions infrastructure, writes convention-following tests. Never refactors source. *Requires init.* |
| [`/optimus:tdd`](skills/tdd/README.md) | Test-driven Red-Green-Refactor — feature branch, per-behavior commits, parallel agent quality gate, PR/MR. The [most effective discipline](https://code.claude.com/docs/en/best-practices) for reliable AI-assisted code. *Requires init.* |
| [`/optimus:simplify`](skills/simplify/README.md) | Cross-file code simplification — duplication, pattern inconsistency, architectural drift. Prioritized plan (capped at 12), test-verified. *Run init first (recommended).* |
| [`/optimus:code-review`](skills/code-review/README.md) | Pre-merge review with up to 6 parallel agents — bugs, security, guideline compliance, code-simplifier, test-guardian. GitHub & GitLab. *Run init first (recommended).* |

### Utility

| Skill | Description |
|-------|-------------|
| [`/optimus:permissions`](skills/permissions/README.md) | Allow/deny rules + PreToolUse hook for tiered path security and branch-aware git protection. Feature branches work freely; protected branches require PRs. Useful on native Windows. |
| [`/optimus:commit-message`](skills/commit-message/README.md) | [Conventional commit](https://www.conventionalcommits.org/) suggestions from local git changes. Splits multi-concern diffs. Multi-repo aware. |

## Recommended Workflow

1. **Initial setup** — `/optimus:init` to generate project context (audits and updates if already present)
2. **Test coverage** — `/optimus:unit-test` to establish or improve unit tests
3. **After major changes** — re-run `/optimus:init` to audit and refresh docs
4. **Code quality** — `/optimus:simplify` for full codebase analysis against your coding guidelines

**During development** — `/optimus:tdd` to build features test-first, `/optimus:code-review` before merging, `/optimus:commit-message` for conventional commits.

**Complementary tools** — Anthropic's official [code-review](https://github.com/anthropics/claude-code/tree/main/plugins/code-review) plugin for post-push PR review, [claude-md-management](https://claude.com/plugins/claude-md-management) for CLAUDE.md scoring and revision, and the builtin `/simplify` for per-change cleanup.

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
