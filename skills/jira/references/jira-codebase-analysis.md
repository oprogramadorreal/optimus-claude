# JIRA Codebase Impact Analysis

Procedure for comparing a JIRA issue's requirements against the actual codebase to surface missing criteria, scope, and risks. Called by the jira skill after the structured task has been confirmed (Step 4) and saved to `docs/jira/<KEY>.md`.

## Contents

1. [Analysis Procedure](#analysis-procedure) — explore the codebase against each acceptance criterion
2. [Impact Summary Format](#impact-summary-format) — output template
3. [Scope Assessment](#scope-assessment) — derive complexity from code, not just criteria count
4. [Criteria Suggestion Heuristics](#criteria-suggestion-heuristics) — when to suggest additions
5. [Context File Update](#context-file-update) — enrich the saved task file with findings

## Analysis Procedure

Using the Goal and Acceptance Criteria from the confirmed structured task, explore the codebase to answer three questions:

1. **What code does each criterion touch?** — For each acceptance criterion, identify the files and modules that need to change. Use targeted searches (Grep, Glob, Read) driven by keywords from the criterion (function names, endpoint paths, component names, domain terms).

2. **What does the code require that the JIRA issue doesn't mention?** — Look for:
   - Components that must change to satisfy a criterion but aren't named in the issue (e.g., a cache layer that needs invalidation, a database migration required by a schema change)
   - Cross-cutting concerns the criteria don't cover (error handling contracts, logging, permissions checks already enforced by middleware)
   - Integration points with other modules that will need updates (imports, shared types, API contracts)

3. **Are there risks the JIRA author couldn't see without reading the code?** — Look for:
   - Tightly coupled modules where a change will cascade
   - Deprecated or fragile code in the affected paths
   - Missing test coverage in areas that will change
   - Patterns or conventions in the codebase that the criteria implicitly assume but don't state

### Exploration Strategy

- **Start narrow**: search for the most specific terms from the acceptance criteria (endpoint names, class names, feature flags)
- **Expand as needed**: follow dependencies and imports from the files found
- **Cap exploration**: read at most 15 files in depth. If the task touches more than 15 files, note this as a complexity signal and summarize by module rather than by file
- **Skip unrelated code**: do not explore areas the acceptance criteria clearly don't touch

## Impact Summary Format

Present the analysis to the user as:

```
## Codebase Impact: [Issue Key]

### Files Affected
[Group by module/directory. For each file, one line:]
- `[path]` — [what changes and why, tied to which criterion]

### Suggested Criteria
[Only if gaps were found. Each item is a candidate acceptance criterion
the JIRA issue doesn't have but the code requires:]
1. [Criterion text] — _[why: brief explanation of what in the code makes this necessary]_

### Scope Assessment
[Simple / Medium / Complex] — [N] files across [N] modules
[One sentence explaining why, e.g., "Touches 3 modules with shared types
that need coordinated changes" or "Isolated to a single service with
good test coverage"]

### Risks
[Only if risks were found. Bullet list:]
- [Risk] — [which files/modules, and why it matters]
```

Omit any section that has nothing to report (e.g., no suggested criteria means the JIRA issue is well-specified).

## Scope Assessment

Derive complexity from the codebase analysis, not from criteria count alone:

| Signal | Simple | Medium | Complex |
|--------|--------|--------|---------|
| Files affected | 1–3 | 4–8 | 9+ |
| Modules/layers touched | 1 | 2–3 | 4+ |
| Shared types or contracts to update | None | 1–2 | 3+ |
| Database migration needed | No | Maybe | Yes |
| Cross-cutting concerns (auth, logging, caching) | None | 1 | 2+ |
| Existing test coverage in affected area | Good | Partial | Sparse/none |

Use the table as a guide, not a rigid formula. A 2-file change that requires a database migration is medium; a 10-file change that's all leaf-node additions is also medium. Explain your reasoning in the summary.

**When codebase assessment disagrees with criteria count**: flag this explicitly. For example: "JIRA has 2 criteria (suggesting simple), but the code reveals 6 files across 3 modules — this is medium complexity."

## Criteria Suggestion Heuristics

Only suggest additional criteria when the code makes them genuinely necessary. Do not pad the list.

**Suggest a criterion when:**
- A module that must change has an existing behavior contract (tests, types, API schema) that the criteria don't account for
- The change requires a migration, backfill, or data transformation step
- An error path or edge case is enforced by existing code (e.g., rate limiting, input validation) but not mentioned in acceptance criteria
- A dependency or integration point needs coordinated changes

**Do NOT suggest a criterion when:**
- It's a nice-to-have that goes beyond the JIRA issue's stated goal
- It's an implementation detail (e.g., "use a factory pattern") rather than an observable behavior
- It duplicates an existing criterion in different words
- It's covered by the codebase's existing infrastructure (e.g., "add logging" when logging middleware is automatic)

## Context File Update

When the user chooses to update the local context file:

1. Read the existing `docs/jira/<KEY>.md`
2. Add a new section after the existing content:

```markdown

### Codebase Impact
[Files Affected section from the impact summary]

### Additional Criteria (from codebase analysis)
[Numbered list of suggested criteria, if any]

### Scope Assessment
[Simple/Medium/Complex with explanation]
```

3. Add an `enriched-date: [YYYY-MM-DD]` field to the YAML frontmatter (preserve the original `date` field unchanged — downstream skills use it for recency ordering)
4. Write the updated file

When the user also chooses to update JIRA, merge the suggested criteria into the improved JIRA description (Step 6 of the skill handles the JIRA write).
