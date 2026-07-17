---
description: >-
  Runs a structured design conversation — clarifies intent, proposes 2-3 approaches
  with trade-offs, iterates the design — and writes a user-approved engineering spec
  to docs/specs/ that /optimus:tdd auto-detects. No implementation happens until the
  spec is approved. With the scaffold argument, creates docs/product/ steering
  skeletons instead (never overwrites, authors no content). Run /optimus:init first.
disable-model-invocation: true
argument-hint: "[topic, JIRA key, or scaffold]"
---

# Brainstorm

Guide the user through a design conversation that produces a written, approved spec before any implementation begins.

**The hard gate: no implementation until the design is approved.** Do not invoke an implementation skill, write production code, or scaffold project structure until a spec is written and the user has approved it — even for seemingly simple tasks.

## Scaffold mode

When invoked with the `scaffold` argument, or when the user asks to set up the docs-first steering cascade, run this flow instead of the design conversation:

1. Target the current repo root. If the current directory has no `.git/` directory, read `$CLAUDE_PLUGIN_ROOT/skills/init/references/multi-repo-detection.md` and apply it — when a workspace is detected, ask which repo the product lives in and scaffold there (a cascade outside the target repo never auto-loads as steering).
2. For each of `docs/product/product-context.md`, `mvp-prd.md`, and `tech-stack.md`: if it exists, never overwrite — skip it. If missing, copy the matching file from `$CLAUDE_PLUGIN_ROOT/skills/brainstorm/templates/product/` verbatim, creating `docs/product/` if needed. Write nothing else — no `docs/specs/` file (the design flow authors that later), nothing under `.claude/`.
3. **Emit skeletons with TODO markers only — author no product content (no personas, KPIs, business-value prose, or technology choices) and never fill a TODO; that is the human's job.**
4. Report created vs skipped files. Tell the user to fill the TODOs top-down (vision → MVP PRD → target stack), then run `/optimus:brainstorm` in a fresh conversation to design the first build.

## Step 1: Pre-flight

If `.claude/CLAUDE.md` or `.claude/docs/coding-guidelines.md` is missing, recommend `/optimus:init` first; on the user's choice, continue with general best practices.

Load `.claude/CLAUDE.md` and `.claude/docs/coding-guidelines.md`, plus — only if present — the steering cascade `docs/product/product-context.md`, `mvp-prd.md`, and `tech-stack.md`. Steering is higher-altitude direction that informs the design, never the task itself or content to copy; the spec stays engineering-focused, with no PM prose (personas, KPIs, business value). Precedence contract: `$CLAUDE_PLUGIN_ROOT/references/sdd-mapping.md`. In a monorepo, load the subproject's own `docs/` files (testing, architecture, styling) and shared guidelines from the root `.claude/docs/`.

If the current directory has no `.git/` directory, read `$CLAUDE_PLUGIN_ROOT/skills/init/references/multi-repo-detection.md` and apply it — operate within the repo the user is targeting; ask which repo if ambiguous.

Scan the project's directory structure, key modules, and existing patterns to ground the conversation in what actually exists.

## Step 2: Gather Intent

Check for JIRA context before prompting the user:

1. Inline input matching `[A-Z][A-Z0-9]+-\d+` → read `docs/jira/<key>.md` and use its Goal and Acceptance Criteria as the brainstorm input. If the file is missing, tell the user to run `/optimus:jira <KEY>` first, then gather intent normally.
2. No inline input and `docs/jira/` contains `.md` files → pick the one with the newest frontmatter `date` and offer it via AskUserQuestion (Use it / Ignore), noting when the date is over 7 days old that re-running `/optimus:jira` refreshes it. **Use it** consumes the file's Goal and Acceptance Criteria and skips the prompts below.

Otherwise use the inline description; if none, ask what to build or change. Distill input longer than ~3 sentences into a single-sentence goal and confirm it with the user.

Surface your key assumptions about scope, constraints, and expected behavior in reply text before the first clarifying question. Then ask at most 3 clarifying questions — a maximum, not a target; one per AskUserQuestion call, preferring multiple-choice — and skip them entirely when intent is already clear.

## Step 3: Explore and Propose

Explore the code the design will touch: relevant modules and conventions, dependencies and integration points, related tests. Then present 2-3 approaches (a third only if genuinely distinct), each with a name, a 2-3 sentence description, pros/cons, effort (Low / Medium / High), and alignment with existing patterns — plus a recommendation with a one-sentence rationale.

The user selects via AskUserQuestion, one option per approach with the recommendation marked. If they want to combine aspects or redirect, incorporate the feedback and present a revised approach before proceeding.

## Step 4: Design

Develop a detailed design covering the spec template sections in Step 5, omitting those that don't apply. Before writing a Scenarios section, read `$CLAUDE_PLUGIN_ROOT/skills/brainstorm/references/scenario-style.md` for inclusion signals and Given/When/Then discipline — `/optimus:tdd` consumes each scenario as one Red-Green-Refactor cycle.

Present the design in conversation and iterate through an Approve / Adjust AskUserQuestion until the user approves.

## Step 5: Write the Spec

Write to `docs/specs/YYYY-MM-DD-<topic-slug>.md` (lowercase hyphenated slug from the goal, max 5 words; create `docs/specs/` if needed). If the file already exists, ask the user whether to overwrite or append a `-2`, `-3`, … suffix; on overwrite, carry any existing `### Refined plan` section into the new file — it holds plan-mode iteration. Set Status to `Approved`. Keep the spec under 200 lines.

```markdown
# Spec: <Title>

**Date:** YYYY-MM-DD
**Status:** Approved
**Goal:** <single sentence — what and why>

## Context
<Why the change is needed; relevant existing state.>

## Approach
<How it works; key decisions and their rationale.>

## Components
| Component | Responsibility | New / Modified |
|-----------|----------------|----------------|

## Interfaces
<How components interact — APIs, data flow, signatures. Skip for single-file changes.>

## Edge Cases and Risks
| Risk | Mitigation |
|------|------------|

## Scenarios
<Conditional — 3-7 Given/When/Then scenarios per scenario-style.md; remove the section if none apply.>

### Scenario: <concrete user-observable outcome>
**Given** <starting state in business language>
**When** <single user action>
**Then** <observable outcome>

## Out of Scope
- <What this design explicitly does not cover>

## Open Questions
- <Deferred decisions — remove if none>
```

Self-review the written file for: TODOs or placeholders; internal contradictions; ambiguity that could lead to building the wrong thing; YAGNI violations; scenario discipline (against scenario-style.md's Discipline and Anti-patterns) when Scenarios are present. Fix what you find, but ask the user before any fix that changes a design decision.

## Step 6: Report

```
## Design Complete

**Spec:** `<spec-path>`
**Goal:** <single-sentence goal>
**Approach:** <chosen approach name>
**Components:** <count> (<count> new, <count> modified)
```

## Step 7: Next Step

Route by task type. Substitute the actual spec path into every recommendation and emitted block — `/optimus:refactor` and `/optimus:unit-test` do not read `docs/specs/` on their own. Recommend running the routed skill in a fresh conversation.

| Task | Route |
|------|-------|
| Refactoring | `/optimus:refactor`, passing the scope and key decisions from `<spec-path>` as the scope argument |
| Test-only | `/optimus:unit-test`, passing the target paths from `<spec-path>` |
| Small implementation (1-2 components, <5 behaviors) | `/optimus:tdd` directly — it auto-detects the spec at `<spec-path>` |
| Medium-to-large implementation | Plan-mode handoff below |
| Prose deliverable (zero code components, or the goal names a written artifact) | Prose flow below |

### Plan-mode handoff (medium-to-large)

Read `$CLAUDE_PLUGIN_ROOT/skills/brainstorm/references/plan-mode-handoff.md`. Emit a copyable plan-mode prompt pre-filled from the spec:

````
```
## Goal
[Goal from the spec]

## Context
[Synthesized from the spec's Context and Approach — key decisions, constraints, chosen-approach rationale.]

## Starting Hints
- Spec: <spec-path>
- [Key files/modules from Step 3 exploration]

## Scope
- Focus on: [components from the spec]
- Out of scope: [from the spec's Out of Scope section]

[Close with the canonical block from plan-mode-handoff.md "Carve-out canonical blocks", substituting <doc-path> = <spec-path>.]
```
````

Then tell the user the three carve-out steps from plan-mode-handoff.md (substituting `<doc-path>` = `<spec-path>`), and emit the execution prompt as a second copyable block:

````
```
## Goal
Run /optimus:tdd to implement the refined plan in <spec-path> test-first.

## Starting Hints
- Spec (with "Refined plan" section): <spec-path>
- Components: [names from the spec's Components table]

## Scope
- Focus on: [components from the spec]
- Out of scope: [from the spec's Out of Scope section]
```
````

### Prose flow

`/optimus:tdd` does not apply — use the default flow from plan-mode-handoff.md. Emit the same plan-mode prompt, but close it with a `## How this conversation should run` section saying: iterate on the plan against the actual codebase; once the user approves the plan, implement it in that same conversation to produce the deliverable; afterwards recommend `/optimus:commit` in that same conversation so the implementation context is captured. Tell the user: start a fresh conversation in plan mode, paste the prompt, iterate, and approve the plan when satisfied. Skip the execution prompt.
