# Spec format

The template for files written to `docs/specs/`. Omit sections that don't
apply — a focused spec beats a padded one. Keep the whole document under 200
lines; a spec that rivals its implementation is a smell.

```markdown
# Spec: <Title>

**Date:** YYYY-MM-DD
**Status:** Draft | Approved
**Goal:** <Single sentence — what and why>

## Context

<Why this change is needed — the problem or opportunity, and the relevant
existing state: what exists today, what's missing, what's broken.>

## Approaches Considered

<The 2-3 approaches explored during design, one short paragraph each with the
key trade-off. Mark the chosen one; give each rejected one its one-line
why-not so the decision survives the conversation.>

## Chosen Design

<How the solution works: key decisions and their rationale, the components
created or modified and their responsibilities, and how they interact —
public interfaces, data flow, contracts. Include edge cases and risks with
mitigations where they shaped the design. Reference existing patterns being
followed or extended.>

## Scenarios

<Conditional — see "The Scenarios contract" below for when to include this
section and how /optimus:tdd consumes it. Remove it entirely when no
inclusion signal applies.>

### Scenario: <Concrete user-observable outcome>
**Given** <starting state in business language>
**When** <single user action>
**Then** <observable outcome>

## Out of Scope

- <What this design explicitly does NOT cover — prevents scope creep during
  implementation>

## Open Questions

- <Decisions deferred or needing more information — remove if none>
```

## The Scenarios contract

`/optimus:tdd` reads the `## Scenarios` section and maps each `### Scenario:`
heading to one Red-Green-Refactor cycle, so the headings and the
Given/When/Then lines are a machine contract — keep them exactly as shown.
The spec specifies; tdd tests. Never write tests, step definitions, or
`.feature` files here. A scenario whose Then implies multiple sub-behaviors
may be further decomposed by tdd — that's expected.

**Include the section when** the work is stakeholder-facing or
acceptance-criteria-driven: the input ticket carries explicit acceptance
criteria, the goal names a user-visible flow, or the design conversation kept
returning to observable outcomes rather than internal mechanics. **Omit it**
for internal refactors, infrastructure changes, and developer-only tooling —
the Chosen Design section covers internal work.

Writing them well: 3-7 scenarios per feature (more means the feature should be
split); one observable behavior per scenario, one `When` each (setup actions
belong in Given; `And`/`But` may chain conditions or outcomes); business
language over implementation language ("total drops to $90", not "the endpoint
returns 200"); concrete values over abstract ones ("a $100 cart" beats "a
non-empty cart"); each scenario independent of the others.
