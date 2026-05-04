# optimus:brainstorm

Guides structured design brainstorming — explores the codebase, asks clarifying questions, proposes multiple approaches with trade-offs, and writes an approved design doc to the project.

## When to Use

Before implementing a new feature or significant change. Especially valuable when:
- The feature touches multiple components or has unclear boundaries
- Multiple valid approaches exist and you want to compare trade-offs
- You want a persistent design artifact that survives conversation resets
- A JIRA ticket is too vague for direct implementation — brainstorm auto-detects JIRA context from `docs/jira/`

## When NOT to Use

- Simple, well-understood task — skip to `/optimus:tdd` directly
- Pure refactoring with no design decisions — use `/optimus:refactor`
- Quick prototyping — just code directly, plan mode is sufficient

## What it does

1. Scans the project for existing patterns and relevant code
2. Asks clarifying questions (up to 3) to fill gaps in the requirement
3. Proposes 2-3 approaches with trade-offs and a recommendation
4. Develops a detailed design for the chosen approach — including a conditional Given/When/Then **Scenarios** section that `/optimus:tdd` consumes as its behavior list when the work is stakeholder-facing or acceptance-criteria-driven.
5. Writes the design to `docs/design/YYYY-MM-DD-<topic-slug>.md`
6. Self-reviews the doc for completeness, contradictions, scenario discipline (when a Scenarios section is present), and YAGNI violations

## The hard gate

No implementation until the design is approved. The skill enforces a strict boundary between thinking and coding — even for "simple" tasks.

## Output

A markdown design document written to `docs/design/` covering goal, approach, components, interfaces, edge cases, explicit scope boundaries, and — for stakeholder-facing or acceptance-criteria-driven work — a Given/When/Then Scenarios section.

## Recommended workflow

| Task complexity | Workflow |
|----------------|----------|
| Small (1–2 components) | `/optimus:brainstorm` → `/optimus:tdd` (auto-detects design doc) |
| Medium-to-large (3+ components) | `/optimus:brainstorm` → plan mode (review-only, do not approve) → `/optimus:tdd` |
| From JIRA | `/optimus:jira` → `/optimus:brainstorm` (auto-detects JIRA context) → plan mode (review-only) → `/optimus:tdd` |

Brainstorm generates the plan-mode prompt inline — no need to run `/optimus:prompt` as a separate step. Each skill recommends the right next step based on design complexity.

## Relationship to Other Skills

| Skill | Relationship |
|-------|-------------|
| `/optimus:jira` | Brainstorm auto-detects JIRA task files in `docs/jira/`. Run jira first for JIRA-tracked work. |
| `/optimus:tdd` | TDD auto-detects design docs in `docs/design/`. Run brainstorm before TDD for complex features. |
| `/optimus:prompt` | Brainstorm generates plan-mode prompts inline for the brainstorm→plan→tdd chain. Use `/optimus:prompt` directly for other AI tools or non-brainstorm workflows. |
| `/optimus:refactor` | For refactoring tasks (restructuring without new behavior), use refactor instead of brainstorm. |

## Prerequisites

- `/optimus:init` should have been run (CLAUDE.md and coding guidelines inform design decisions)

## Skill Structure

| File | Purpose |
|------|---------|
| `SKILL.md` | Skill definition with 7-step brainstorming workflow |
| `references/design-doc-format.md` | Design document template (Scenarios section is conditional) |
| `references/scenario-style.md` | Given/When/Then phrasing discipline for the Scenarios section |

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)

## License

[MIT](../../LICENSE)
