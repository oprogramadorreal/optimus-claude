# /optimus:brainstorm

Guides structured design brainstorming — explores the codebase, asks clarifying questions, proposes multiple approaches with trade-offs, and writes an approved design doc to the project.

## When to use

Before implementing a new feature or significant change. Especially valuable when:
- The feature touches multiple components or has unclear boundaries
- Multiple valid approaches exist and you want to compare trade-offs
- You want a persistent design artifact that survives conversation resets

## What it does

1. Scans the project for existing patterns and relevant code
2. Asks clarifying questions (up to 3) to fill gaps in the requirement
3. Proposes 2-3 approaches with trade-offs and a recommendation
4. Develops a detailed design for the chosen approach
5. Writes the design to `docs/design/YYYY-MM-DD-<topic-slug>.md`
6. Self-reviews the doc for completeness, contradictions, and YAGNI violations

## The hard gate

No implementation until the design is approved. The skill enforces a strict boundary between thinking and coding — even for "simple" tasks.

## Output

A markdown design document written to `docs/design/` covering goal, approach, components, interfaces, edge cases, and explicit scope boundaries.

## Recommended workflow

```
/optimus:brainstorm → /optimus:prompt (plan-mode prompt) → plan mode → /optimus:tdd
```

1. **Brainstorm** produces a design doc
2. **Prompt** generates a plan-mode prompt referencing the design doc
3. **Plan mode** (Claude Code built-in) explores the codebase and creates an implementation plan
4. **TDD** implements the plan test-first with Red-Green-Refactor cycles

For small tasks (single component, few behaviors), skip plan mode and go directly to `/optimus:tdd`.

## Prerequisites

- `/optimus:init` should have been run (CLAUDE.md and coding guidelines inform design decisions)
