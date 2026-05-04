# Design doc format

Use this template when writing the design document. Omit sections that don't apply — a focused design is better than a padded one.

```markdown
# Design: <Title>

**Date:** YYYY-MM-DD
**Status:** Draft | Approved
**Goal:** <Single sentence — what and why>

## Context

<Why this change is needed — the problem or opportunity. Include relevant
existing state: what exists today, what's missing, what's broken.>

## Approach

<How the solution works. Key decisions and their rationale. Reference
existing patterns being followed or extended.>

## Components

| Component | Responsibility | New / Modified |
|-----------|---------------|----------------|
| ... | ... | New |
| ... | ... | Modified |

## Interfaces

<How components interact — APIs, data flow, function signatures, contracts.
Focus on public boundaries, not internal implementation.>

## Edge Cases and Risks

| Risk | Mitigation |
|------|------------|
| ... | ... |

## Scenarios

<Conditional section — see `scenario-style.md` for inclusion signals, the
3–7-scenario format, and phrasing discipline.>

### Scenario: <Concrete user-observable outcome>
**Given** <starting state in business language>
**When** <single user action>
**Then** <observable outcome>

### Scenario: <Next user-observable outcome>
...

## Out of Scope

- <What this design explicitly does NOT cover>
- <Prevents scope creep during implementation>

## Open Questions

- <Decisions deferred or needing more information — remove this section if none>
```

## Guidelines

- **Goal** must be a single sentence — if it takes a paragraph, the scope is too broad
- **Components** table helps TDD decomposition — each component maps to one or more testable behaviors
- **Interfaces** section is critical for multi-component designs — skip for single-file changes
- **Scenarios** section is conditional — see `scenario-style.md` for inclusion criteria
- **Out of Scope** prevents the implementation phase from expanding beyond the design
- Keep the entire document under 200 lines — design docs that rival the implementation are a smell
