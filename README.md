# claude-code-bootstrap

What makes a good developer productive in a codebase also makes Claude Code productive: **clean code, good test coverage, and clear documentation.**

Research backs this up: AI tools introduce [30%+ more defects](https://arxiv.org/abs/2601.02200) on poorly maintained code, LLM performance [degrades up to 85%](https://arxiv.org/abs/2510.05381) as context length grows, and Anthropic's [#1 best practice](https://code.claude.com/docs/en/best-practices) for Claude Code is giving it a way to verify its own work.

`/bootstrap:init` sets up your project for LLM peak performance, `/bootstrap:unit-test` builds the feedback loop that makes AI self-correcting, and `/bootstrap:simplify` reviews existing code against the guidelines they establish.

## Why This Plugin?

When you join a new project, you need good test coverage (to change code safely), clean code (to understand what's going on), and documentation (for non-obvious decisions). Claude Code needs the same things — for similar reasons:

- **DRY code** avoids wasting context tokens with duplicate information
- **Meaningful names** give the LLM better semantic signals
- **Unit tests** enable self-correction: make change → run tests → see failure → fix
- **Focused documentation** keeps the context window efficient and contradiction-free

The LLM already knows best practices from training — but the trigger to apply them comes from the project context. `/bootstrap:init` provides that trigger.

## Quick Start

**Install:**

```shell
/plugin marketplace add https://github.com/oprogramadorreal/claude-code-bootstrap.git
/plugin install bootstrap@claude-code-bootstrap
```

**Run:** Start a new Claude Code session and type `/bootstrap:init` in any project directory.

## Skills

| Skill | Invocation | Purpose |
|-------|-----------|---------|
| [Init](#bootstrapinit) | `/bootstrap:init` | CLAUDE.md, docs, formatter hooks, quality agents |
| [Unit Test](#bootstrapunit-test) | `/bootstrap:unit-test` | On-demand unit test coverage improvement |
| [Simplify](#bootstrapsimplify) | `/bootstrap:simplify` | Project-wide code simplification against coding guidelines |
| [Permissions](#bootstrappermissions) | `/bootstrap:permissions` | Allow/deny rules, path-restriction hook |
| [Commit Message](#bootstrapcommit-message) | `/bootstrap:commit-message` | Conventional commit message suggester |

## Architecture: Project-Scoped by Design

Unlike most plugins that bundle hooks and agents at the plugin level, **bootstrap writes everything into the project's `.claude/` directory**. This is an intentional design choice:

- **Hooks, agents, docs, and settings travel with the repo via git** — any teammate who opens the project in Claude Code gets identical behavior, even without this plugin installed
- **The plugin is needed only for setup and maintenance**, not for day-to-day development
- **No hidden dependencies** — the automation is visible, auditable, and version-controlled alongside your code

The plugin is a **distribution wrapper** around project-setup skills. It makes installation easy (`/plugin install`), but the generated output is self-contained.

## Recommended Workflow

1. **Initial setup** — Run `/bootstrap:init` to set up project context (audits and updates existing docs if already present)
2. **Test coverage** — Run `/bootstrap:unit-test` to establish or improve unit test coverage
3. **After major changes** — Re-run `/bootstrap:init` to audit and refresh docs
4. **Code quality review** — Run `/bootstrap:simplify` for a full codebase analysis against your coding guidelines

**During development** — use the builtin `/simplify` after each feature or bug fix to clean up recent changes before committing. `/bootstrap:simplify` (step 4) covers the full project periodically; the builtin handles the inner loop.

**Complementary tools** (optional — from Anthropic's [claude-md-management](https://claude.com/plugins/claude-md-management) plugin):
- **Periodic quality checks** — Use `claude-md-improver` for scoring and targeted improvements
- **After work sessions** — Use `/revise-claude-md` to capture discoveries from real usage

Install: `claude plugin add claude-md-management`

## /bootstrap:init

The main skill. Analyzes your project and sets up five pillars designed to maximize Claude Code's performance:

1. **Context Architecture** — CLAUDE.md with progressive disclosure docs (~60-line root file, details loaded on demand)
2. **Code Consistency** — PostToolUse hooks that auto-format code after every edit
3. **Code Quality** — code-simplifier agent enforcing project coding guidelines
4. **Test Coverage** — test-guardian agent monitoring coverage gaps (when test infrastructure detected)
5. **Documentation Freshness** — audits existing docs against source code for contradictions

Additional capabilities: intelligent audit on re-run (classifies docs as Outdated / Missing / Accurate), monorepo auto-detection with scoped docs, and formatter hooks for Python, Node.js, Rust, Go, C#, Java, and C/C++.

See [skills/init/README.md](skills/init/README.md) for full documentation including formatter hooks, agents, generated files, and customization.

## /bootstrap:unit-test

Tests are the feedback loop that makes AI agents self-correcting — but many codebases start with gaps. `/bootstrap:unit-test` fills them deliberately: it discovers what's missing, provisions test infrastructure if needed, estimates an achievable coverage target, and generates tests that follow your project's conventions.

**Conservative by design** — only adds new test files, never refactors or restructures existing source code. If code is untestable as-is, it flags it rather than changing it. Discovers and reports bugs in existing code without fixing them. Refactoring is the domain of `/bootstrap:simplify`.

Key capabilities:
- **Infrastructure provisioning** — installs test-guardian agent, creates testing.md, updates CLAUDE.md if init skipped them
- **Framework and coverage tooling** — recommends and installs the right tools for your stack (with explicit approval)
- **Achievable threshold estimation** — analyzes testable vs untestable code to set realistic coverage targets
- **Prioritized test plan** — up to 10 items per run, highest-value targets first, user-approved before execution

See [skills/unit-test/README.md](skills/unit-test/README.md) for full documentation.

## /bootstrap:simplify

Well-maintained code has [30%+ fewer AI-introduced defects](https://arxiv.org/abs/2601.02200). `/bootstrap:init` sets up quality infrastructure with agents that guard new code automatically — but existing code can still accumulate technical debt. `/bootstrap:simplify` is the on-demand complement: a deliberate review you run when you want to actively improve existing code.

Analyzes source code against your project's coding guidelines with emphasis on **issues that span multiple files** — duplication across modules, inconsistent patterns between areas, architectural drift. Presents a prioritized simplification plan (capped at 12 findings per run), then applies only what you approve. The test suite runs automatically to verify nothing broke.

**Flexible scope** — review the full project, a specific directory, or only files changed since a commit/date. **Conservative by design** — only suggests changes justified by the project's own guidelines. Works without `/bootstrap:init` by falling back to generic coding guidelines.

Claude Code includes a builtin `/simplify` command. `/bootstrap:simplify` is the enhanced, project-aware complement — just as `/bootstrap:init` extends the builtin `/init`. Key differences: full project scope vs per-session, project-specific guidelines vs general best practices, plan-then-apply workflow, and cross-file pattern detection.

See [skills/simplify/README.md](skills/simplify/README.md) for full documentation.

## /bootstrap:permissions

Configures Claude Code permissions for safe agent autonomy — allow/deny rules that eliminate routine prompts, plus a PreToolUse hook that enforces tiered path-based security. Writes outside the project require approval; deletes outside the project are blocked.

Especially useful on **native Windows** where OS-level sandboxing is not yet available, or as a **complementary layer** alongside sandboxing to reduce noise.

Merges safely with `/bootstrap:init` — both share `.claude/settings.json` without conflicts.

See [skills/permissions/README.md](skills/permissions/README.md) for full documentation, security model, enforcement reliability, and known limitations.

## /bootstrap:commit-message

Analyzes local git changes (staged, unstaged, and untracked) and suggests [conventional commit](https://www.conventionalcommits.org/) messages — without committing anything. Suggests splitting into multiple commits when changes span different concerns.

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
