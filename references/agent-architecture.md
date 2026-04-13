# Agent Architecture

Agents (subagents) are separate Claude instances spawned via the Agent tool, each running in its own context window. This isolates their work from the main conversation — keeping the primary context clean and focused — and enables multiple agents to run in parallel. Each agent receives a specific task, works autonomously with restricted tool access, and returns a focused result.

optimus-claude uses a two-tier agent architecture: **plugin-level agents** in the `agents/` directory and **skill-level agents** inside individual `skills/<name>/agents/` directories.

## Plugin-level agents (`agents/`)

| Agent | Purpose |
|-------|---------|
| `code-simplifier.md` | Simplifies code for clarity, consistency, and maintainability |
| `test-guardian.md` | Monitors test coverage gaps — flags what needs testing, does not write tests |

These are standard Claude Code agent definitions with frontmatter (`name`, `description`, `model`, `tools`). They serve two roles:

1. **Base definitions** — define the core approach, quality criteria, and methodology for a reusable concern
2. **Extended by skill-level agents** — skill-level agents read these files for their core approach, then layer skill-specific behavior on top (see [specialization pattern](#the-specialization-pattern) below)

Both agents read the target project's `.claude/docs/coding-guidelines.md` and `.claude/CLAUDE.md` for project-specific standards. In projects with a skill-authoring stack, the code-simplifier also reads `.claude/docs/skill-writing-guidelines.md` and routes each analyzed file to the correct lens (coding-guidelines for code files, skill-writing-guidelines for markdown instruction files) — it inlines the routing rules directly to stay within the reference-depth limit. The test-guardian checks for the file's existence to skip markdown instruction files (which are not testable code) rather than routing them to a lens.

## Skill-level agents (`skills/<name>/agents/`)

Skill-level agents are **agent definitions scoped to a specific skill**. They have the same frontmatter as plugin-level agents (`name`, `description`, `model`, `tools`), but they are not shared across skills — each skill's SKILL.md reads these files and launches them explicitly via the Agent tool.

Each skill-level agent directory typically contains:

- **Individual agent prompts** — one `.md` file per agent
- **`shared-constraints.md`** — skill-specific addendums to the base constraints in `references/shared-agent-constraints.md`
- **`context-blocks.md`** (optional) — conditional context injection templates for PR/MR context and iteration context

| Skill | Agents | Notes |
|-------|--------|-------|
| code-review | bug-detector, code-simplifier, contracts-reviewer, guideline-reviewer, security-reviewer, test-guardian | + context-blocks.md for PR/MR and iteration context |
| refactor | code-simplifier, consistency-analyzer, guideline-reviewer, testability-analyzer | + context-blocks.md for iteration context |
| tdd | code-simplifier, test-guardian | Quality gate after each TDD cycle |
| init | project-analyzer, documentation-auditor | Project analysis during setup |
| how-to-run | project-environment-detector, how-to-run-auditor | Project environment analysis |
| unit-test | test-infrastructure-analyzer | Test infrastructure analysis |

## The specialization pattern

Some skill-level agents **extend** a plugin-level agent rather than defining their approach from scratch. They do this by reading the plugin-level file for core behavior, then adding skill-specific scope, output format, and exclusion boundaries.

For example, the code-review skill's `code-simplifier.md` contains:

```
Read `$CLAUDE_PLUGIN_ROOT/agents/code-simplifier.md` for your approach and quality criteria.
```

This means:

- **Plugin-level** `code-simplifier.md` defines *what* code simplification means (quality criteria, operational principles, direct vs. structural changes)
- **Skill-level** `code-simplifier.md` defines *how* to apply it in that skill's context (which files to review, output format, coordination with other agents)

**Skills that use this pattern:**

| Plugin Agent | Extended By |
|-------------|------------|
| `code-simplifier.md` | code-review, refactor, tdd |
| `test-guardian.md` | code-review, tdd |

## Shared reference files

Base constraints and context templates that apply across all skill-level agents live in `references/`:

| File | Purpose |
|------|---------|
| `shared-agent-constraints.md` | Read-only analysis rules, quality bar (High/Medium only), exclusion rules, false-positive guidance |
| `context-injection-blocks.md` | PR/MR context and iteration context templates used by code-review and refactor |

Review-oriented skills (code-review, refactor, tdd) have their `shared-constraints.md` read the base constraints and add skill-specific addendums (e.g., TDD limits findings to 5 per agent and scopes to changed files only). Other skills define standalone constraints tailored to their detection or verification roles.
