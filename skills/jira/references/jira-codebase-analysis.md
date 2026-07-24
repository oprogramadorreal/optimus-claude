# JIRA Codebase Impact Analysis

Compare a JIRA issue's requirements against the actual codebase to surface missing criteria, scope, and risks. Called by the jira skill at Step 5, after the structured task has been saved to `docs/jira/<KEY>.md`.

## Contents

1. [Analysis Procedure](#analysis-procedure)
2. [Impact Summary Format](#impact-summary-format)
3. [Scope Assessment](#scope-assessment)
4. [Criteria Suggestion Heuristics](#criteria-suggestion-heuristics)
5. [Task File Update](#task-file-update)
6. [JIRA Comment Format](#jira-comment-format)

## Analysis Procedure

Drive the analysis from the Goal and the ORIGINAL Acceptance Criteria (on re-analyze runs, exclude items tagged `(from codebase analysis)` — prior enrichment, not source criteria). Search outward from the criteria's most specific terms; read at most 15 files in depth — beyond that, treat the breadth as a complexity signal and summarize by module rather than by file. Answer three questions:

1. **What code does each criterion touch?** — the files and modules that must change, per criterion.
2. **What does the code require that the issue doesn't mention?** — unnamed components that must change (e.g., cache invalidation, database migrations), cross-cutting concerns the criteria skip (error contracts, permissions, logging middleware), integration points needing coordinated updates.
3. **What risks couldn't the JIRA author see without reading the code?** — tightly coupled modules where changes cascade, deprecated or fragile paths, missing test coverage, unstated conventions the criteria implicitly assume.

## Impact Summary Format

```
## Codebase Impact: [Issue Key]

### Files Affected
[Group by module/directory. One line per file:]
- `[path]` — [what changes and why, tied to which criterion]

### Suggested Criteria
[Only if gaps were found — candidate acceptance criteria the issue lacks but the code requires:]
1. [Criterion text] — _[why the code makes this necessary]_

### Scope Assessment
[Simple / Medium / Complex] — [N] files across [N] modules
[One sentence explaining why]

### Risks
[Only if risks were found:]
- [Risk] — [which files/modules, and why it matters]
```

Omit any section with nothing to report.

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

Use the table as a guide, not a formula — a 2-file change requiring a migration is medium; a 10-file change of leaf-node additions is also medium. When the codebase assessment disagrees with the criteria count, flag it explicitly (e.g., "JIRA has 2 criteria, but the code reveals 6 files across 3 modules — medium complexity").

## Criteria Suggestion Heuristics

Only suggest criteria the code makes genuinely necessary — never pad the list.

- **Suggest when:** an affected module has an existing behavior contract (tests, types, API schema) the criteria ignore; the change needs a migration, backfill, or data transformation; existing code enforces an error path or edge case (rate limiting, validation) the criteria omit; a dependency or integration point needs coordinated changes.
- **Do NOT suggest:** nice-to-haves beyond the issue's stated goal; implementation details (e.g., "use a factory pattern") rather than observable behavior; rewordings of existing criteria; anything the codebase's existing infrastructure already covers automatically.

## Task File Update

When the user chooses to update the local task file:

1. Read the existing `docs/jira/<KEY>.md`.
2. **Drop stale tagged items first (re-analyze runs only):** if `### Acceptance Criteria` already contains items tagged `(from codebase analysis)` from a prior enrichment, remove them — only the current run's tagged additions should remain.
3. Merge suggested criteria into `### Acceptance Criteria` — append each as a new numbered item with a `(from codebase analysis)` suffix. Where the codebase reveals existing criteria are vague or inaccurate, clarify them in place (preserve the original number; append a clarification note). Do not remove original criteria.
4. Write each enrichment section below. If a section already exists (re-analyze run), replace its body in place, preserving section order. Insert missing sections in canonical order before the first of `### Implementation Tickets`, `### Sub-item Drift`, or `### Refined plan` (whichever appears first); if none are present, append after the existing content. Preserve `### Implementation Tickets`, `### Sub-item Drift`, and `### Refined plan` verbatim if present — they are written by other procedures. Template:

```markdown

### Refined Description
[The issue's goal re-stated in concrete, actionable terms, correcting vagueness
based on what the codebase actually shows. Must be self-contained — downstream
skills read only this file, never JIRA.]

### Suggested Approach
[Concrete next steps and implementation sequence — what to do first, what
depends on what. Make the task directly workable for /optimus:brainstorm and
/optimus:tdd.]

### Codebase Impact
[Files Affected from the impact summary, grouped by module/directory.]

### Risks
[Only if risks were found — omit otherwise.]

### Scope Assessment
[Simple/Medium/Complex with explanation]
```

5. Update YAML frontmatter (set or overwrite — do not skip if already present): `enriched-date: [YYYY-MM-DD]` = today; `description-refresh-date: [YYYY-MM-DD]` = today (see `jira-refresh.md` "Frontmatter update"). Preserve `date` unchanged.
6. Write the file.

The local file is the single source of truth: self-contained, in English, directly consumable by `/optimus:brainstorm` and `/optimus:tdd` without cross-referencing JIRA. When the user also chose to update JIRA, Step 5 of the skill posts the comment using the format below.

## JIRA Comment Format

Wiki markup template for the analysis comment. Derive each section from the corresponding section just written to the local file; write the comment in the JIRA issue's original language.

```
h2. Codebase Analysis (automated)

h3. Refined Description
[Mirror the local file's Refined Description. Omit if not present.]

h3. Acceptance Criteria (refined)
[From the local file's ### Acceptance Criteria, including items marked
"(from codebase analysis)".]

h3. Suggested Approach
[Mirror the local file's Suggested Approach. Omit if not present.]

h3. Codebase Impact
[Mirror the local file's Codebase Impact. Omit if not present.]

h3. Risks
[Only if the local file has a Risks section. Omit otherwise.]

h3. Scope Assessment
[Mirror the local file's Scope Assessment.]

_Generated by optimus-claude on [YYYY-MM-DD]_
```
