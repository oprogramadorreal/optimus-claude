# optimus:init

The main skill of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin. Analyzes your project and sets up Claude Code for optimal performance by generating documentation, installing formatter hooks, and deploying quality agents — all scoped to the project directory so they travel with the repo via git.

What makes a good developer productive in a codebase also makes Claude Code productive: clean code, good test coverage, and clear documentation. Research backs this up: AI tools introduce [30%+ more defects](https://arxiv.org/abs/2601.02200) on poorly maintained code, LLM performance [degrades up to 85%](https://arxiv.org/abs/2510.05381) as context length grows, and Anthropic's [#1 best practice](https://code.claude.com/docs/en/best-practices) for Claude Code is giving it a way to verify its own work.

## Features

- **New Project Scaffolding** — when run in an empty or near-empty directory, offers to scaffold a new project from scratch using official stack tooling (Vite, Next.js, Cargo, Flutter, .NET CLI, etc.), then continues with full init setup. One command to go from empty folder to a buildable, runnable project with CLAUDE.md, hooks, agents, and docs. Unsupported stacks are handled via best-effort web search fallback.
- **Context Architecture** — creates CLAUDE.md files following [research-backed practices](https://www.humanlayer.dev/blog/writing-a-good-claude-md): a compact ~60-line root file within the LLM's peak attention window, with details in separate docs loaded only when needed. Just like you don't keep all backend details in your head while fixing a frontend bug, Claude shouldn't load everything into context at once.
- **Code Consistency** — installs PostToolUse hooks that auto-format code every time Claude modifies a file. This prevents formatting drift — different styles introduce unnecessary token variation that adds no information.
- **Code Quality** — deploys a [code-simplifier](templates/agents/code-simplifier.md) agent that enforces your project's [coding guidelines](templates/docs/coding-guidelines.md) — clean code, small functions, clear naming, proper abstractions. This isn't about aesthetics: well-maintained code has [30%+ fewer AI-introduced defects](https://arxiv.org/abs/2601.02200). The agent guards new code proactively; for a full project review, see `/optimus:simplify`.
- **Test Coverage** — installs a [test-guardian](templates/agents/test-guardian.md) agent that monitors coverage gaps when test infrastructure is detected — flagging untested code, verifying that existing tests still pass, and checking that test commands are runnable. It doesn't write tests or install frameworks; it ensures the project maintains its testing standards as it evolves. This directly enables Anthropic's [#1 best practice](https://code.claude.com/docs/en/best-practices): giving Claude a way to verify its work.
- **Documentation Freshness** — reviews existing documentation (README, CONTRIBUTING, etc.) for contradictions against the actual source code. Stale docs in context degrade LLM performance — if documentation says one thing and the code says another, you're actively harming output quality.
- **Audit on re-run** — compares docs against current project state, classifies sections as Outdated / Missing / Accurate / User-added (always preserved), and lets you choose what to update. User-added content (custom conventions, workflow rules, architecture decisions not derivable from the codebase) is never discarded — even on "Fresh start". Tracks plugin version in `.claude/.optimus-version` — when the plugin has been updated, the audit also compares generated docs against current templates to surface plugin-side improvements
- **Monorepo & multi-repo workspace support** — auto-detects monorepos and multi-repo workspaces (separate git repos under a shared parent); generates fully self-contained `.claude/` per repo

## Quick Start

This skill is part of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin. See the [main README](../../README.md) for installation instructions.

**Run:** Start a new Claude Code session and type `/optimus:init` in any project directory.

## Usage

In Claude Code, use any of these:

- `/optimus:init` — full project setup
- `/optimus:init` "focus on the backend services"

## When to Run

- **New project** — initial setup of all five pillars (context, consistency, quality, tests, docs)
- **After major changes** — re-run to audit and refresh docs (agents, hooks, and coding-guidelines are always refreshed from templates; other docs use intelligent diff)
- **After adding new stack components** — picks up new dependencies, adds formatter hooks for newly detected stacks
- **Periodic maintenance** — keeps docs in sync with evolving codebase; stale docs actively degrade LLM performance
- **Onboarding new teammates** — ensures consistent Claude Code behavior via git-tracked config in `.claude/`

## How It Works

1. **Detects project context** — tech stack, package manager, project structure (single / monorepo / multi-repo workspace), existing docs, test infrastructure
2. **Audits existing documentation** (if present) — classifies as Outdated / Missing / Accurate / User-added; you choose what to update
3. **Creates directory structure** — `.claude/docs/`, `.claude/hooks/`, `.claude/agents/`
4. **Generates CLAUDE.md** — WHAT/WHY/HOW structure, progressive disclosure, <=60 lines (soft limit when preserving user content)
5. **Installs formatter hooks** — per detected stack; deploys code-quality agents
6. **Sets up test infrastructure** — installs test framework and coverage tooling (with approval), runs health check, provisions test-guardian agent, testing docs, and README testing section
7. **Creates scoped documentation** — coding guidelines (always), styling, architecture (when detected)
8. **Syncs existing project docs** — cross-checks README, CONTRIBUTING, etc. against source code for factual contradictions

## Formatter Hooks

PostToolUse hooks that auto-format files after every Edit/MultiEdit/Write, installed per detected stack:

| Hook | Formatter | Installed when |
|------|-----------|----------------|
| `format-python.py` | black + isort | Python project detected |
| `format-node.js` | prettier | Node.js project detected |
| `format-rust.sh` | rustfmt | Rust project detected (built-in) |
| `format-go.sh` | gofmt | Go project detected (built-in) |
| `format-csharp.sh` | csharpier | C#/.NET project detected |
| `format-java.sh` | google-java-format | Java project detected |
| `format-cpp.sh` | clang-format | C/C++ project detected |
| `format-dart.sh` | dart format | Dart/Flutter project detected (built-in) |
| *(custom)* | Web search result | Other stacks (best-effort with user approval) |

For stacks requiring external formatters (Python, Node.js, C#, Java, C/C++), `/optimus:init` checks your dependencies and asks before installing anything. For other stacks, it searches for the most popular formatter and creates a custom hook with user approval.

## Agents

| Agent | Purpose | Installed when |
|-------|---------|----------------|
| [code-simplifier](templates/agents/code-simplifier.md) | Enforces coding guidelines on every change — direct simplifications automatic, structural changes as suggestions | Always |
| [test-guardian](templates/agents/test-guardian.md) | Flags untested code, verifies test suite passes | Test infrastructure detected |

Both agents reference your project's `.claude/CLAUDE.md` and `.claude/docs/` files, so they follow your established conventions rather than imposing external rules. The code-simplifier activates proactively after code changes — applying direct simplifications (renaming, dead code removal, flattening) automatically and presenting structural changes (extracting functions, changing abstractions) as suggestions for approval. The test-guardian operates at the end of logical tasks to verify test coverage.

## Generated Files

| File | Purpose |
|------|---------|
| `.claude/CLAUDE.md` | Project overview, commands, doc references |
| `.claude/settings.json` | Formatter hook configuration |
| `.claude/docs/coding-guidelines.md` | Coding standards and quality guidelines |
| `.claude/docs/testing.md` | Testing conventions (when test framework detected) |
| `.claude/docs/styling.md` | UI/CSS guidelines (when frontend detected) |
| `.claude/docs/architecture.md` | Project structure (when complex structure detected) |
| `.claude/hooks/` | Auto-format hooks per detected stack |
| `.claude/agents/code-simplifier.md` | Code quality agent |
| `.claude/agents/test-guardian.md` | Test coverage agent (when test infrastructure detected) |
| `.claude/.optimus-version` | Plugin version that last generated these files |

**Monorepo:** each subproject also gets its own `CLAUDE.md` and scoped `docs/`.

**Multi-repo workspace:** each repo gets its own complete `.claude/` (version-controlled). A lightweight parent `CLAUDE.md` provides cross-repo context (local-only).

## Skill Structure

| File | Purpose |
|---|---|
| `SKILL.md` | Skill definition with step-by-step instructions |
| `references/claude-md-best-practices.md` | Research-backed guidance for CLAUDE.md authoring |
| `references/project-detection.md` | Project structure detection algorithm |
| `references/multi-repo-detection.md` | Shared multi-repo workspace detection (used by 6 skills) |
| `references/formatter-setup.md` | Formatter hook installation guidance |
| `references/unsupported-stack-fallback.md` | Shared best-effort fallback for unsupported stacks (used by init, dev-setup, verify) |
| `references/verification-protocol.md` | Cross-cutting verification discipline for completion claims |
| `references/prerequisite-check.md` | Shared prerequisite check with fallbacks (used by code-review, simplify, verify) |
| `references/constraint-doc-loading.md` | Shared constraint doc loading for single project and monorepo (used by 5 skills) |
| `references/new-project-scaffolding.md` | New project scaffolding procedure for empty directories |
| `references/test-infra-provisioning.md` | Test infrastructure provisioning procedure (framework, coverage, health check, docs) |
| `references/test-framework-recommendations.md` | Stack-specific test framework, coverage tooling, and report tool recommendations |
| `templates/` | CLAUDE.md templates, doc templates, hook scripts, agent definitions |

## Customization

To understand or modify how the skill works, start with `SKILL.md`. Key customization points:

- **CLAUDE.md templates**: `templates/single-project-claude.md`, `templates/monorepo-claude.md`, `templates/subproject-claude.md`, `templates/multi-repo-claude.md`
- **Coding guidelines**: `templates/docs/coding-guidelines.md`
- **Formatter hooks**: `templates/hooks/` (Python, Node.js, Rust, Go, C#, Java, C/C++, Dart/Flutter)
- **Agents**: `templates/agents/` (code-simplifier, test-guardian)

### Tuning coding guidelines

The coding guidelines file (`.claude/docs/coding-guidelines.md` in your project) is the primary control surface for how the code-simplifier agent, `/optimus:simplify`, and `/optimus:code-review` evaluate your code. Every principle you add, remove, or edit directly changes what these tools flag.

Note: re-running `/optimus:init` always overwrites `coding-guidelines.md`, agents, and hooks from the latest plugin templates — use `git diff` to review changes. When the plugin version has increased since the last run, the audit also compares generated docs against current templates to detect improvements. To add project-specific rules that survive re-runs, put them in `.claude/CLAUDE.md` instead.

## Relationship to Other Skills

`/optimus:init` is the foundation that other skills build on:

| Skill | Uses from init | What it adds |
|---|---|---|
| `/optimus:unit-test` | test-guardian agent, testing.md, CLAUDE.md, test framework, coverage tooling | Writes test files to increase coverage |
| `/optimus:simplify` | coding-guidelines.md, code-simplifier agent | Full-project code review against guidelines |
| `/optimus:code-review` | All docs + both agents | Pre-commit review with up to 6 parallel agents |
| `/optimus:tdd` | CLAUDE.md, coding-guidelines.md, testing.md, both agents | Red-Green-Refactor TDD with feature branch workflow |
| `/optimus:permissions` | Shares `.claude/settings.json` | Permission rules + path-restriction hook |
| `/optimus:commit` | Independent | Stage, commit, and optionally push with conventional message |
| `/optimus:commit-message` | Independent | Conventional commit message suggestion (read-only) |

commit, commit-message, and permissions are fully independent of init. simplify and code-review fall back to generic guidelines when project docs are missing. tdd and unit-test require init — both stop if CLAUDE.md is not found.

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Git

## License

[MIT](../../LICENSE)
