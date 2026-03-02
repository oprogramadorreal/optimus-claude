# prime:init

The main skill of the [prime](https://github.com/oprogramadorreal/claude-code-prime) plugin. Analyzes your project and sets up Claude Code for optimal performance by generating documentation, installing formatter hooks, and deploying quality agents — all scoped to the project directory so they travel with the repo via git.

What makes a good developer productive in a codebase also makes Claude Code productive: clean code, good test coverage, and clear documentation. Research backs this up: AI tools introduce [30%+ more defects](https://arxiv.org/abs/2601.02200) on poorly maintained code, LLM performance [degrades up to 85%](https://arxiv.org/abs/2510.05381) as context length grows, and Anthropic's [#1 best practice](https://code.claude.com/docs/en/best-practices) for Claude Code is giving it a way to verify its own work.

## Features

- **Context Architecture** — creates CLAUDE.md files following [research-backed practices](https://www.humanlayer.dev/blog/writing-a-good-claude-md): a compact ~60-line root file within the LLM's peak attention window, with details in separate docs loaded only when needed. Just like you don't keep all backend details in your head while fixing a frontend bug, Claude shouldn't load everything into context at once.
- **Code Consistency** — installs PostToolUse hooks that auto-format code every time Claude modifies a file. This prevents formatting drift — different styles introduce unnecessary token variation that adds no information.
- **Code Quality** — deploys a [code-simplifier](templates/agents/code-simplifier.md) agent that enforces your project's [coding guidelines](templates/docs/coding-guidelines.md) — clean code, small functions, clear naming, proper abstractions. This isn't about aesthetics: well-maintained code has [30%+ fewer AI-introduced defects](https://arxiv.org/abs/2601.02200). The agent guards new code proactively; for a full project review, see `/prime:simplify`.
- **Test Coverage** — installs a [test-guardian](templates/agents/test-guardian.md) agent that monitors coverage gaps when test infrastructure is detected — flagging untested code, verifying that existing tests still pass, and checking that test commands are runnable. It doesn't write tests or install frameworks; it ensures the project maintains its testing standards as it evolves. This directly enables Anthropic's [#1 best practice](https://code.claude.com/docs/en/best-practices): giving Claude a way to verify its work.
- **Documentation Freshness** — reviews existing documentation (README, CONTRIBUTING, etc.) for contradictions against the actual source code. Stale docs in context degrade LLM performance — if documentation says one thing and the code says another, you're actively harming output quality.
- **Audit on re-run** — compares docs against current project state, classifies sections as Outdated / Missing / Accurate, and lets you choose what to update
- **Monorepo support** — auto-detects monorepos via workspace tools and manifest scanning, generates scoped docs per subproject

## Quick Start

This skill is part of the [prime](https://github.com/oprogramadorreal/claude-code-prime) plugin. See the [main README](../../README.md) for installation instructions.

**Run:** Start a new Claude Code session and type `/prime:init` in any project directory.

## Usage

In Claude Code, use any of these:

- `/prime:init` — full project setup
- `/prime:init` "focus on the backend services"
- "prime this project"
- "set up Claude Code for this project"
- "initialize project documentation and hooks"

## When to Run

- **New project** — initial setup of all five pillars (context, consistency, quality, tests, docs)
- **After major changes** — re-run to audit and refresh docs (intelligent diff, not overwrite)
- **After adding new stack components** — picks up new dependencies, adds formatter hooks for newly detected stacks
- **Periodic maintenance** — keeps docs in sync with evolving codebase; stale docs actively degrade LLM performance
- **Onboarding new teammates** — ensures consistent Claude Code behavior via git-tracked config in `.claude/`

## How It Works

1. **Detects project context** — tech stack, package manager, monorepo status, existing docs, test infrastructure
2. **Audits existing documentation** (if present) — classifies as Outdated / Missing / Accurate; you choose what to update
3. **Creates directory structure** — `.claude/docs/`, `.claude/hooks/`, `.claude/agents/`
4. **Generates CLAUDE.md** — WHAT/WHY/HOW structure, progressive disclosure, <=60 lines
5. **Installs formatter hooks** — per detected stack; deploys code-quality agents
6. **Creates scoped documentation** — coding guidelines (always), testing, styling, architecture (when detected)
7. **Syncs existing project docs** — cross-checks README, CONTRIBUTING, etc. against source code for factual contradictions

## Formatter Hooks

PostToolUse hooks that auto-format files after every Edit/MultiEdit/Write, installed per detected stack:

| Hook | Formatter | Installed when |
|------|-----------|----------------|
| `format-python.py` | black + isort | Python project detected |
| `format-node.js` | prettier | Node.js project detected |
| `format-rust.sh` | rustfmt | Rust project detected (built-in) |
| `format-go.sh` | goimports / gofmt | Go project detected (built-in) |
| `format-csharp.sh` | csharpier | C#/.NET project detected |
| `format-java.sh` | google-java-format | Java project detected |
| `format-cpp.sh` | clang-format | C/C++ project detected |

For stacks requiring external formatters (Python, Node.js, C#, Java, C/C++), `/prime:init` checks your dependencies and asks before installing anything.

## Agents

| Agent | Purpose | Installed when |
|-------|---------|----------------|
| [code-simplifier](templates/agents/code-simplifier.md) | Enforces coding guidelines on every change | Always |
| [test-guardian](templates/agents/test-guardian.md) | Flags untested code, verifies test suite passes | Test infrastructure detected |

Both agents reference your project's `.claude/CLAUDE.md` and `.claude/docs/` files, so they follow your established conventions rather than imposing external rules. The code-simplifier activates proactively after code changes; the test-guardian operates at the end of logical tasks to verify test coverage.

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

**Monorepo:** each subproject also gets its own `CLAUDE.md` and scoped `docs/`.

## Skill Structure

| File | Purpose |
|---|---|
| `SKILL.md` | Skill definition with step-by-step instructions |
| `references/claude-md-best-practices.md` | Research-backed guidance for CLAUDE.md authoring |
| `templates/` | CLAUDE.md templates, doc templates, hook scripts, agent definitions |

## Customization

To understand or modify how the skill works, start with `SKILL.md`. Key customization points:

- **CLAUDE.md templates**: `templates/single-project-claude.md`, `templates/monorepo-claude.md`, `templates/subproject-claude.md`
- **Coding guidelines**: `templates/docs/coding-guidelines.md`
- **Formatter hooks**: `templates/hooks/` (Python, Node.js, Rust, Go, C#, Java, C/C++)
- **Agents**: `templates/agents/` (code-simplifier, test-guardian)

## Relationship to Other Skills

`/prime:init` is the foundation that other skills build on:

| Skill | Uses from init | What it adds |
|---|---|---|
| `/prime:unit-test` | test-guardian agent, testing.md, CLAUDE.md | Writes test files, provisions coverage tooling |
| `/prime:simplify` | coding-guidelines.md, code-simplifier agent | Full-project code review against guidelines |
| `/prime:code-review` | All docs + both agents | Pre-commit review with up to 6 parallel agents |
| `/prime:permissions` | Shares `.claude/settings.json` | Permission rules + path-restriction hook |
| `/prime:commit-message` | Independent | Conventional commit message suggestion |

All skills work without init (commit-message and permissions are fully independent; the others produce better results with project-specific docs and agents in place).

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Git

## License

[MIT](../../LICENSE)
