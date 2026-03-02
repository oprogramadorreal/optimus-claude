# claude-code-prime

What makes a good developer productive in a codebase also makes Claude Code productive: **clean code, good test coverage, and clear documentation.**

Research backs this up: AI tools introduce [30%+ more defects](https://arxiv.org/abs/2601.02200) on poorly maintained code, LLM performance [degrades up to 85%](https://arxiv.org/abs/2510.05381) as context length grows, and Anthropic's [#1 best practice](https://code.claude.com/docs/en/best-practices) for Claude Code is giving it a way to verify its own work.

- `/prime:init` sets up your project for LLM peak performance
- `/prime:unit-test` builds the feedback loop that makes AI self-correcting
- `/prime:simplify` reviews existing code against the guidelines they establish
- `/prime:code-review` catches issues in your changes before they enter the repo

## Why This Plugin?

When you join a new project, you need good test coverage (to change code safely), clean code (to understand what's going on), and documentation (for non-obvious decisions). Claude Code needs the same things — for similar reasons:

- **DRY code** avoids wasting context tokens with duplicate information
- **Meaningful names** give the LLM better semantic signals
- **Unit tests** enable self-correction: make change → run tests → see failure → fix
- **Focused documentation** keeps the context window efficient and contradiction-free

The LLM already knows best practices from training — but the trigger to apply them comes from the project context. `/prime:init` provides that trigger.

## Quick Start

**Install:**

```shell
/plugin marketplace add https://github.com/oprogramadorreal/claude-code-prime.git
/plugin install prime@claude-code-prime
```

**Run:** Start a new Claude Code session and type `/prime:init` in any project directory.

## Skills

| Skill | Invocation | Purpose | Needs init? |
|-------|-----------|---------|-------------|
| [Init](#primeinit) | `/prime:init` | CLAUDE.md, docs, formatter hooks, quality agents | — |
| [Unit Test](#primeunit-test) | `/prime:unit-test` | On-demand unit test coverage improvement | Recommended |
| [Simplify](#primesimplify) | `/prime:simplify` | Project-wide code simplification against coding guidelines | Recommended |
| [Code Review](#primecode-review) | `/prime:code-review` | Local-first code review with parallel agent-assisted analysis | Recommended |
| [Permissions](#primepermissions) | `/prime:permissions` | Allow/deny rules, path-restriction hook | No |
| [Commit Message](#primecommit-message) | `/prime:commit-message` | Conventional commit message suggester | No |

## Architecture: Project-Scoped by Design

Unlike most plugins that bundle hooks and agents at the plugin level, **prime writes everything into the project's `.claude/` directory**. This is an intentional design choice:

- **Hooks, agents, docs, and settings travel with the repo via git** — any teammate who opens the project in Claude Code gets identical behavior, even without this plugin installed
- **The plugin is needed only for setup and maintenance**, not for day-to-day development
- **No hidden dependencies** — the automation is visible, auditable, and version-controlled alongside your code

The plugin is a **distribution wrapper** around project-setup skills. It makes installation easy (`/plugin install`), but the generated output is self-contained.

## Recommended Workflow

1. **Initial setup** — Run `/prime:init` to set up project context (audits and updates existing docs if already present)
2. **Test coverage** — Run `/prime:unit-test` to establish or improve unit test coverage
3. **After major changes** — Re-run `/prime:init` to audit and refresh docs
4. **Code quality review** — Run `/prime:simplify` for a full codebase analysis against your coding guidelines

**During development** — use `/prime:code-review` before committing to catch bugs and guideline violations, and `/prime:commit-message` for conventional commit messages.

**Complementary tools** (optional):
- **Inner-loop cleanup** — The builtin `/simplify` cleans up recent changes after each feature or bug fix. `/prime:simplify` (step 4) covers the full project periodically; the builtin handles the per-change inner loop.
- **PR code review** — Anthropic's official [code-review](https://github.com/anthropics/claude-code/tree/main/plugins/code-review) plugin reviews PRs against CLAUDE.md. Use it alongside `/prime:code-review` for full coverage: prime for pre-commit, official for post-push. Install: `claude plugin add code-review`
- **Doc quality** — Anthropic's [claude-md-management](https://claude.com/plugins/claude-md-management) plugin provides `claude-md-improver` for scoring and targeted improvements, and `/revise-claude-md` to capture discoveries from real usage. Install: `claude plugin add claude-md-management`

## /prime:init

Analyzes your project and sets up five pillars: context architecture (CLAUDE.md + progressive disclosure docs), code consistency (auto-format hooks), code quality (code-simplifier agent), test coverage (test-guardian agent), and documentation freshness (audit against source code). Supports monorepos, 7 formatter stacks, and intelligent audit on re-run.

See [skills/init/README.md](skills/init/README.md) for full documentation.

## /prime:unit-test

Discovers test coverage gaps, provisions test infrastructure if needed, estimates achievable coverage targets, and generates tests that follow your project's conventions. Conservative by design — only adds new test files, never refactors source code. Flags untestable code and reports bugs found during test writing.

See [skills/unit-test/README.md](skills/unit-test/README.md) for full documentation.

## /prime:simplify

Analyzes existing code against your project's coding guidelines with emphasis on cross-file issues — duplication across modules, pattern inconsistency, architectural drift. Presents a prioritized plan (capped at 12 findings), applies only what you approve, and runs the test suite to verify nothing broke. Flexible scope: full project, directory, or changed files.

See [skills/simplify/README.md](skills/simplify/README.md) for full documentation.

## /prime:code-review

Reviews uncommitted changes (or PRs) against your project's coding guidelines using up to 6 parallel agents — bug detection, security/logic, guideline compliance (×2), code-simplifier, and test-guardian. High-signal findings only: bugs, security issues, logic errors, guideline violations. Use alongside Anthropic's official [code-review](https://github.com/anthropics/claude-code/tree/main/plugins/code-review) plugin: prime for pre-commit, official for post-push.

See [skills/code-review/README.md](skills/code-review/README.md) for full documentation.

## /prime:permissions

Configures allow/deny rules that eliminate routine prompts, plus a PreToolUse hook that enforces tiered path-based security — writes outside the project require approval, deletes are blocked. Especially useful on native Windows where OS-level sandboxing is not yet available. Merges safely with `/prime:init`.

See [skills/permissions/README.md](skills/permissions/README.md) for full documentation.

## /prime:commit-message

Analyzes local git changes and suggests [conventional commit](https://www.conventionalcommits.org/) messages — without committing anything. Suggests splitting into multiple commits when changes span different concerns.

See [skills/commit-message/README.md](skills/commit-message/README.md) for full documentation.

## Research & References

The principles behind this plugin are supported by research and industry practice:

- **Anthropic** — [Claude Code Best Practices](https://code.claude.com/docs/en/best-practices): testing as #1 practice, compact CLAUDE.md, deterministic hooks, custom subagents
- **Borg et al. (2026)** — [Code for Machines, Not Just Humans](https://arxiv.org/abs/2601.02200) (3rd ACM FORGE): LLM-based refactoring on 5,000 Python files; AI defect risk increases 30%+ on unhealthy code (CodeHealth < 7.0)
- **Thoughtworks Technology Radar Vol. 32 (2025)** — [AI-friendly code design](https://www.thoughtworks.com/radar/techniques/ai-friendly-code-design) (Assess ring): "good software design for humans also benefits AI"
- **Du et al. (2025)** — [Context Length Alone Hurts LLM Performance](https://arxiv.org/abs/2510.05381) (Findings of EMNLP): even with perfect retrieval, 13.9%–85% performance degradation as input length increases
- **HumanLayer (2025)** — [Writing a Good CLAUDE.md](https://www.humanlayer.dev/blog/writing-a-good-claude-md): WHAT/WHY/HOW structure, progressive disclosure, <60 lines ideal

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Git

## License

[MIT](LICENSE)
