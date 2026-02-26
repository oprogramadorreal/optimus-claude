# claude-code-bootstrap

What makes a good developer productive in a codebase also makes Claude Code productive: **clean code, good test coverage, and clear documentation.**

Research backs this up: AI tools introduce [30%+ more defects](https://arxiv.org/abs/2601.02200) on poorly maintained code, LLM performance [degrades up to 85%](https://arxiv.org/abs/2510.05381) as context length grows, and Anthropic's [#1 best practice](https://code.claude.com/docs/en/best-practices) for Claude Code is giving it a way to verify its own work.

`/bootstrap:init` replaces Claude Code's basic `/init` with a research-backed setup that keeps your project in the LLM's peak performance zone.

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
/plugin marketplace add https://github.com/oprogramadorreal/claude-code-bootstrap.git#plugin
/plugin install bootstrap@claude-code-bootstrap
```

**Run:** Start a new Claude Code session and type `/bootstrap:init` in any project directory.

## Skills

| Skill | Invocation | Purpose |
|-------|-----------|---------|
| [Init](#bootstrapinit) | `/bootstrap:init` | CLAUDE.md, docs, formatter hooks, quality agents |
| [Permissions](#bootstrappermissions) | `/bootstrap:permissions` | Allow/deny rules, path-restriction hook |
| [Commit Message](#bootstrapcommit-message) | `/bootstrap:commit-message` | Conventional commit message suggester |

## Architecture: Project-Scoped by Design

Unlike most plugins that bundle hooks and agents at the plugin level, **bootstrap writes everything into the project's `.claude/` directory**. This is an intentional design choice:

- **Hooks, agents, docs, and settings travel with the repo via git** — any teammate who opens the project in Claude Code gets identical behavior, even without this plugin installed
- **The plugin is needed only for setup and maintenance**, not for day-to-day development
- **No hidden dependencies** — the automation is visible, auditable, and version-controlled alongside your code

The plugin is a **distribution wrapper** around project-setup skills. It makes installation easy (`/plugin install`), but the generated output is self-contained.

## /bootstrap:init

The main skill. Analyzes your project and sets up five pillars designed to maximize Claude Code's performance:

### 1. Context Architecture

Creates CLAUDE.md files following [research-backed practices](https://www.humanlayer.dev/blog/writing-a-good-claude-md): a compact ~60-line root file within the LLM's peak attention window, with details in separate docs loaded only when needed. Just like you don't keep all backend details in your head while fixing a frontend bug, Claude shouldn't load everything into context at once.

### 2. Code Consistency

Installs PostToolUse hooks that auto-format code every time Claude modifies a file. This prevents formatting drift — different styles introduce unnecessary token variation that adds no information.

### 3. Code Quality

Deploys a [code-simplifier](skills/init/templates/agents/code-simplifier.md) agent that enforces your project's [coding guidelines](skills/init/templates/docs/coding-guidelines.md) — clean code, small functions, clear naming, proper abstractions. This isn't about aesthetics: well-maintained code has [30%+ fewer AI-introduced defects](https://arxiv.org/abs/2601.02200).

### 4. Test Coverage

Tests are the feedback loop that makes AI agents self-correcting: make change → run tests → see failure → fix. Without tests, Claude Code is flying blind. When test infrastructure is detected, `/bootstrap:init` installs a [test-guardian](skills/init/templates/agents/test-guardian.md) agent that monitors coverage gaps — flagging untested code, verifying that existing tests still pass, and checking that test commands are runnable. It doesn't write tests or install frameworks; it ensures the project maintains its testing standards as it evolves. This directly enables Anthropic's [#1 best practice](https://code.claude.com/docs/en/best-practices): giving Claude a way to verify its work.

### 5. Documentation Freshness

Reviews existing documentation (README, CONTRIBUTING, etc.) for contradictions against the actual source code. Stale docs in context degrade LLM performance — if documentation says one thing and the code says another, you're actively harming output quality.

**Additional features:**
- **Audit on re-run** — Compares docs against current project state, classifies sections as Outdated / Missing / Accurate, and lets you choose what to update
- **Monorepo support** — Auto-detects monorepos via workspace tools and manifest scanning, generates scoped docs per subproject

### Formatter Hooks

PostToolUse hooks that auto-format files after every Edit/Write, installed per detected stack:

| Hook | Formatter | Installed when |
|------|-----------|----------------|
| `format-python.py` | black + isort | Python project detected |
| `format-node.js` | prettier | Node.js project detected |
| `format-rust.sh` | rustfmt | Rust project detected (built-in) |
| `format-go.sh` | goimports / gofmt | Go project detected (built-in) |
| `format-csharp.sh` | csharpier | C#/.NET project detected |
| `format-java.sh` | google-java-format | Java project detected |
| `format-cpp.sh` | clang-format | C/C++ project detected |

For stacks requiring external formatters (Python, Node.js, C#, Java, C/C++), `/bootstrap:init` checks your dependencies and asks before installing anything.

### Agents

| Agent | Purpose | Installed when |
|-------|---------|----------------|
| [code-simplifier](skills/init/templates/agents/code-simplifier.md) | Enforces coding guidelines on every change | Always |
| [test-guardian](skills/init/templates/agents/test-guardian.md) | Flags untested code, verifies test suite passes | Test infrastructure detected |

Both agents read your project's `.claude/CLAUDE.md` and `.claude/docs/` at runtime, so they follow your established conventions rather than imposing external rules. The code-simplifier activates proactively after code changes; the test-guardian operates at the end of logical tasks to verify test coverage. For a project-wide code review:

> Use the code-simplifier agent to analyze this project against the standards in .claude/docs/coding-guidelines.md and suggest simplifications

### Keeping Docs Current

`/bootstrap:init` is not just for initial setup. Re-running it on an existing project triggers an intelligent audit that compares your docs against the current project state, classifies them as Outdated / Missing / Accurate, and lets you choose what to update.

For ongoing quality between audits, the official [claude-md-management](https://claude.com/plugins/claude-md-management) plugin (by Anthropic) provides complementary tools: `claude-md-improver` for scoring and targeted improvements, and `/revise-claude-md` for capturing session learnings.

**Recommended workflow:**

1. **Initial setup** — Run `/bootstrap:init` to generate documentation from scratch
2. **After major changes** — Re-run `/bootstrap:init` to audit and refresh docs
3. **Periodic quality checks** — Use `claude-md-improver` for scoring and targeted improvements
4. **After work sessions** — Use `/revise-claude-md` to capture discoveries from real usage

Install the plugin: `claude plugin add claude-md-management`

### Generated Files

| File | Purpose |
|------|---------|
| `.claude/CLAUDE.md` | Project overview, commands, doc references |
| `.claude/settings.json` | Formatter hook configuration |
| `.claude/docs/coding-guidelines.md` | Code style and architecture guidelines |
| `.claude/docs/testing.md` | Testing conventions (when test framework detected) |
| `.claude/docs/styling.md` | UI/CSS guidelines (when frontend detected) |
| `.claude/docs/architecture.md` | Project structure (when complex structure detected) |
| `.claude/hooks/` | Auto-format hooks per detected stack |
| `.claude/agents/code-simplifier.md` | Code quality agent |
| `.claude/agents/test-guardian.md` | Test coverage agent (when test infrastructure detected) |

**Monorepo:** each subproject also gets its own `CLAUDE.md` and scoped `docs/`.

## /bootstrap:permissions

Configures Claude Code permissions for safe agent autonomy — allow/deny rules that eliminate routine prompts, plus a PreToolUse hook that enforces tiered path-based security. Writes outside the project require approval; deletes outside the project are blocked.

Especially useful on **native Windows** where OS-level sandboxing is not yet available, or as a **complementary layer** alongside sandboxing to reduce noise.

Merges safely with `/bootstrap:init` — both share `.claude/settings.json` without conflicts.

See [skills/permissions/README.md](skills/permissions/README.md) for full documentation, security model, enforcement reliability, and known limitations.

## /bootstrap:commit-message

Analyzes local git changes (staged, unstaged, and untracked) and suggests [conventional commit](https://www.conventionalcommits.org/) messages — without committing anything. Suggests splitting into multiple commits when changes span different concerns.

See [skills/commit-message/README.md](skills/commit-message/README.md) for full documentation.

## Customization

To understand or modify how the plugin works, start with the skill's `SKILL.md`. Key files:

- **Init skill logic**: `skills/init/SKILL.md` — Step-by-step instructions Claude follows
- **CLAUDE.md templates**: `skills/init/templates/single-project-claude.md`, `skills/init/templates/monorepo-claude.md`, `skills/init/templates/subproject-claude.md`
- **Coding guidelines**: `skills/init/templates/docs/coding-guidelines.md` — Shared style rules template
- **Hook configuration**: `skills/init/templates/settings.json` — PostToolUse hook structure
- **Formatter hooks**: `skills/init/templates/hooks/` — Hook templates (Python, Node.js, Rust, Go, C#, Java, C/C++)
- **Agents**: `skills/init/templates/agents/` — code-simplifier and test-guardian templates
- **Best practices reference**: `skills/init/references/claude-md-best-practices.md` — Research-backed guidance
- **Permissions skill**: `skills/permissions/SKILL.md` — Permission rules and hook installation
- **Commit message skill**: `skills/commit-message/SKILL.md` — Git change analysis

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
