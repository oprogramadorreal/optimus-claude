# optimus-claude

**A Claude Code plugin that sets up your project for effective AI-assisted development** — CLAUDE.md, coding guidelines, formatter hooks, quality agents, TDD, and test coverage, all tailored to your actual codebase.

## Skills

### Core

**[`/optimus:init`](skills/init/README.md)** — Generates CLAUDE.md, coding guidelines, formatter hooks, and quality agents — all tailored to your codebase. Supports monorepos, 7 formatter stacks, and intelligent audit on re-run.

**[`/optimus:unit-test`](skills/unit-test/README.md)** — Fills test coverage gaps with generated tests that enable AI self-correction. Discovers gaps, provisions infrastructure, and writes convention-following tests. Never refactors source code. *Recommended: run init first.*

**[`/optimus:tdd`](skills/tdd/README.md)** — Test-driven development — Red-Green-Refactor cycles that give the AI a binary pass/fail feedback loop, the [most effective discipline](https://code.claude.com/docs/en/best-practices) for reliable AI-assisted code. Creates a feature branch, decomposes into behaviors, commits per cycle, pushes and opens a PR/MR. *Requires init.*

**[`/optimus:simplify`](skills/simplify/README.md)** — Finds and applies code simplifications with emphasis on cross-file issues: duplication, pattern inconsistency, architectural drift. Prioritized plan (capped at 12 findings), apply what you approve, test suite verifies nothing broke. *Recommended: run init first.*

**[`/optimus:code-review`](skills/code-review/README.md)** — Catches bugs and violations before they enter the repo using up to 6 parallel agents — bug detection, security/logic, guideline compliance, code-simplifier, test-guardian. High-signal only. Supports GitHub and GitLab. *Recommended: run init first.*

### Utility

**[`/optimus:permissions`](skills/permissions/README.md)** — Allow/deny rules that eliminate routine prompts, plus a PreToolUse hook enforcing tiered path security and branch-aware git protection. Feature branches work freely; protected branches require pull requests. Especially useful on native Windows.

**[`/optimus:commit-message`](skills/commit-message/README.md)** — Analyzes local git changes and suggests [conventional commit](https://www.conventionalcommits.org/) messages — without committing anything. Suggests splitting when changes span multiple concerns. Supports multi-repo workspaces.

## Quick Start

**Install:**

```shell
/plugin marketplace add https://github.com/oprogramadorreal/optimus-claude.git
/plugin install optimus@optimus-claude
```

**Run:** Start a new Claude Code session and type `/optimus:init` in any project directory.

## Why This Plugin?

What makes a good developer productive also makes Claude Code productive: **clean code, good tests, and clear docs.**

- **DRY code and meaningful names** avoid wasting context tokens and give the LLM better semantic signals
- **Unit tests** enable self-correction — TDD takes this further by writing tests *before* code, preventing the AI from rubber-stamping its own bugs

Research backs this up: AI tools introduce [30%+ more defects](https://arxiv.org/abs/2601.02200) on poorly maintained code, LLM performance [degrades up to 85%](https://arxiv.org/abs/2510.05381) as context length grows, and Anthropic's [#1 best practice](https://code.claude.com/docs/en/best-practices) for Claude Code is giving it a way to verify its own work.

## Architecture: Project-Scoped by Design

Unlike most plugins that bundle hooks and agents at the plugin level, **optimus writes everything into the project's `.claude/` directory**:

- **Hooks, agents, docs, and settings travel with the repo via git** — any teammate gets identical behavior, even without this plugin installed
- **Enforces standards linters can't check** — naming conventions, architectural patterns, DRY principles, guided by project-specific docs and agents
- **No hidden dependencies** — the plugin is needed only for setup; the generated output is self-contained, visible, auditable, and version-controlled

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

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Git

## License

[MIT](LICENSE)
