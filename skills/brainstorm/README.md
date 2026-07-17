# optimus:brainstorm

Guides structured design brainstorming — explores the codebase, asks clarifying questions, proposes 2-3 approaches with trade-offs, and writes a user-approved engineering spec to `docs/specs/YYYY-MM-DD-<slug>.md`. Enforces a hard gate: no implementation until the spec is approved, even for "simple" tasks.

## When to use

Before implementing a new feature or significant change — especially when the work touches multiple components, multiple valid approaches exist, you want a persistent spec that survives conversation resets, or a JIRA ticket is too vague for direct implementation (brainstorm auto-detects JIRA context from `docs/jira/`).

**When not:** simple, well-understood task → `/optimus:tdd` directly; pure refactoring → `/optimus:refactor`; quick prototyping → plan mode alone.

## What it does

1. Loads project context, coding guidelines, and the optional `docs/product/` steering cascade
2. Gathers intent — JIRA auto-detection, then up to 3 clarifying questions
3. Proposes 2-3 approaches with trade-offs and a marked recommendation
4. Iterates the design with you until approved
5. Writes the spec — including a conditional Given/When/Then **Scenarios** section that `/optimus:tdd` maps to Red-Green-Refactor cycles — and self-reviews it
6. Routes to the right next step (refactor, unit-test, TDD, or a plan-mode handoff)

## Scaffold mode

`/optimus:brainstorm scaffold` bootstraps spec-driven development on a greenfield project: it creates `docs/product/product-context.md`, `mvp-prd.md`, and `tech-stack.md` as empty TODO skeletons for a human to fill (replacing the 2.x spec-init skill). It never overwrites existing files and authors no product content. Fill the TODOs top-down, then re-run `/optimus:brainstorm` — the design flow reads the cascade as steering. See [`references/sdd-mapping.md`](../../references/sdd-mapping.md) for the precedence contract.

## Recommended workflow

| Situation | Workflow |
|-----------|----------|
| Small (1-2 components) | brainstorm → `/optimus:tdd` (auto-detects the spec) |
| Medium-to-large | brainstorm → plan mode (review-only, do not approve) → `/optimus:tdd` |
| From JIRA | `/optimus:jira` → brainstorm → plan mode → `/optimus:tdd` |
| Greenfield product | brainstorm scaffold → fill the cascade → brainstorm |

Brainstorm generates the plan-mode prompt inline — no separate `/optimus:prompt` step needed for this chain.

## Relationship to other skills

| Skill | Relationship |
|-------|--------------|
| `/optimus:jira` | Brainstorm auto-detects task files in `docs/jira/` — run jira first for JIRA-tracked work |
| `/optimus:tdd` | Auto-detects specs in `docs/specs/`; consumes each spec scenario as one Red-Green-Refactor cycle |
| `/optimus:refactor` | For restructuring without new behavior, use refactor instead of brainstorm |
| `/optimus:prompt` | For handoff prompts outside the brainstorm→plan→tdd chain |

## Prerequisites

- `/optimus:init` should have been run (CLAUDE.md and coding guidelines inform design decisions); scaffold mode has no prerequisites

## Skill structure

| File | Purpose |
|------|---------|
| `SKILL.md` | Design workflow, scaffold mode, and the spec template |
| `references/scenario-style.md` | Given/When/Then discipline for the Scenarios section |
| `references/plan-mode-handoff.md` | Plan-mode handoff procedure (shared — also read by `/optimus:jira`) |
| `templates/product/` | Steering-cascade skeletons emitted by scaffold mode |

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)

## License

[MIT](../../LICENSE)
