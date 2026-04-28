# JIRA Refresh Procedure

Procedure for re-running `/optimus:jira` on a key whose `docs/jira/<KEY>.md` already exists. Reconciles the local file with the latest JIRA state — does NOT regenerate from scratch.

The skill calls this from Step 3.5 after a fresh fetch of the issue. The fresh fetch is already in hand; the refresh procedure compares it against what is on disk and decides what to update.

## Contents

1. [Refresh Procedure](#refresh-procedure) — entry guard and flow order
2. [Comparison rules](#comparison-rules) — what to diff
3. [Decision matrix](#decision-matrix) — what to do for each kind of divergence
4. [Update procedure](#update-procedure) — how to merge while preserving enrichment
5. [Sub-item walk](#sub-item-walk) — review the local Implementation Tickets table
6. [No-change short circuit](#no-change-short-circuit) — exit cleanly when nothing diverged
7. [Frontmatter update](#frontmatter-update) — bump `description-refresh-date`

## Refresh Procedure

Enter only when `docs/jira/<KEY>.md` already exists at the project root. If it does not, the skill is on a first-run path — return immediately and let Step 4 of SKILL.md proceed.

The fresh fetch from Step 3 (issue details, linked issues, comments, sprint context) is the canonical "what JIRA says now". The local file is "what JIRA said the last time the skill ran, plus any enrichment". The job is to reconcile.

Run the sub-procedures below in order: [Comparison rules](#comparison-rules) → [Decision matrix](#decision-matrix), then the matrix routes to [Update procedure](#update-procedure) (and [Sub-item walk](#sub-item-walk) when Goal/AC diverged) or to [No-change short circuit](#no-change-short-circuit) when nothing diverged. The [Frontmatter update](#frontmatter-update) is invoked from the Update procedure on every refresh that writes. Exit to Step 6 of SKILL.md when the chosen path completes.

## Comparison rules

Compare the freshly fetched JIRA against the local file. Diff these fields only:

| Field | Local file location | Fresh fetch source | Diff style |
|-------|---------------------|--------------------|------------|
| Goal | `### Goal` section body | Issue summary + description | Semantic |
| Acceptance Criteria | `### Acceptance Criteria` numbered list | Description (extracted criteria) | Item-by-item semantic |
| Status | `### Context` → `Status:` line | `status` field | Exact |
| Priority | `### Context` → `Priority:` line | `priority` field | Exact |
| Sprint | `### Context` → `Sprint:` line | sprint name | Exact |

Do NOT diff: comments, sub-task statuses, sibling issues, key decisions, refined description, suggested approach, codebase impact, risks, scope assessment, implementation tickets. Comments are read-only context. Enrichment sections are owned by prior analysis runs and are preserved unless explicitly re-analysed.

**Semantic diff for Goal and Acceptance Criteria:** Compare for material change in meaning, not byte-exact text. Whitespace, punctuation, and rewordings that preserve meaning do not count as divergence. A criterion that gains a new constraint (e.g., "max 3 reset requests per hour" added to a previously open-ended criterion) IS divergence. A new numbered criterion appearing in JIRA IS divergence. A criterion disappearing from JIRA IS divergence.

## Decision matrix

| Diff outcome | Action |
|--------------|--------|
| Nothing diverged | [No-change short circuit](#no-change-short-circuit) — report and exit to Step 6 |
| Status / Priority / Sprint changed only | Run [Update procedure](#update-procedure) for the diverged `### Context` lines, skip the re-analysis prompt and the [Sub-item walk](#sub-item-walk), continue to Step 6 |
| Goal and/or Acceptance Criteria changed (with or without metadata changes) | Run [Update procedure](#update-procedure) for every diverged section, then prompt for re-analysis once |

When prompting for re-analysis, use `AskUserQuestion` — header "Re-analyse", question "JIRA criteria changed since the last run. Would you like to re-run codebase analysis against the new criteria?":
- **Skip** — "Update the local file only" (default)
- **Re-analyse** — "Run Step 5 again with the new criteria"

If "Re-analyse": jump to Step 5 of SKILL.md using the freshly diffed Goal and Acceptance Criteria. The existing enrichment sections from the prior run get replaced by Step 5's output via the existing Task File Update procedure.

If "Skip": continue to Step 6.

## Update procedure

Apply changes in place; preserve everything else.

1. Read the existing `docs/jira/<KEY>.md` in full.
2. Replace the body of any diverged section (`### Goal`, `### Acceptance Criteria`, or `### Context` lines) with the fresh content. For Acceptance Criteria, preserve any items previously marked `(from codebase analysis)` — these were added during enrichment and do not come from JIRA. New JIRA criteria slot before the `(from codebase analysis)` items, keeping numbering continuous.
3. Do NOT touch `### Refined Description`, `### Suggested Approach`, `### Codebase Impact`, `### Risks`, `### Scope Assessment`, or `### Implementation Tickets`. These belong to enrichment runs.
4. Update frontmatter per [Frontmatter update](#frontmatter-update).
5. Write the file.
6. Report to the user which sections changed, one line each: e.g., `Updated: ### Acceptance Criteria (1 new criterion, 1 reworded)`.

If the diff is so large that preservation makes no sense (e.g., all criteria changed AND the goal changed), still preserve enrichment but flag in the report that enrichment may now be stale: `Note: enrichment sections may no longer match. Consider running re-analysis.`

## Sub-item walk

Run after the [Update procedure](#update-procedure) completes, before exiting to Step 6. Only entered when Goal and/or Acceptance Criteria diverged — metadata-only diffs (Status/Priority/Sprint) skip this section.

If the local file has no `### Implementation Tickets` section, skip this step.

Otherwise:

1. Parse the markdown table under `### Implementation Tickets` to extract the list of `Ticket` cell values. Skip rows whose value is parenthesised (e.g., `(proposed-1)`) — these are placeholders from a Skip-mode recording, not real keys. If no real keys remain after filtering, skip this step.
2. For each remaining key, fetch the issue using the get-single-issue tool from the Tool Name Resolution table in `jira-context-extraction.md` (Read-only — no writes). Cap the walk at 15 sub-items; if more, fetch the first 15 and report the rest as unwalked.
3. For each fetched sub-item, compare its summary and (if available) acceptance criteria against the parent's now-updated `### Acceptance Criteria` only. Do NOT use `### Codebase Impact` — that section is enrichment owned by prior analysis runs and is not refreshed here, so on Skip-re-analyse paths it would be stale.
4. Flag a sub-item as drifted only when:
   - The parent gained or removed an acceptance criterion AND no sub-item's stated scope clearly maps to the change, OR
   - A sub-item's summary references a parent criterion that no longer exists.
5. Do NOT auto-edit sub-items. Report drift only — present a summary and ask the user via `AskUserQuestion` whether to:
   - **Continue** — "Note the drift in the local file and proceed" (default)
   - **Stop** — "Pause so I can update sub-items manually first"
6. Write the `### Sub-item Drift` block to `docs/jira/<KEY>.md`. This is a separate write after the Update procedure's write — the Update procedure does not own this section. Insert it immediately before `### Scope Assessment` (always present after enrichment); if the section is unexpectedly absent, append at end of file.
   - **If drift detected and user chose Continue:** body is a bullet list of `<sub-key>: <reason>` entries. Replace any prior `### Sub-item Drift` block — it represents the latest refresh only.
   - **If no drift detected:** remove any prior `### Sub-item Drift` block; do not insert a new one.

If "Stop": exit the skill without progressing to Step 6. Do not write the drift block on Stop — the user resumes by re-running `/optimus:jira <KEY>` after they've updated the sub-items.

## No-change short circuit

When the diff finds nothing material:

1. Report to the user: `No changes detected since description-refresh-date: <date>. Skipping update.` Use the `description-refresh-date` value from the local file's frontmatter.
2. Do NOT bump `description-refresh-date` — nothing changed.
3. Do NOT post a JIRA comment.
4. Skip directly to Step 6 of SKILL.md (recommend the next step).

The sub-item walk is also skipped on no-change exits — there is no parent diff to drive flagging.

## Frontmatter update

Bump `description-refresh-date` to today's date (YYYY-MM-DD) on every refresh write — this includes Goal/AC divergence updates, Status/Priority/Sprint-only updates, sub-task creation Recording, and re-analyse runs that re-execute the Task File Update procedure. The field name preserves the original artefact's wording for backward compatibility with existing local files; semantically it tracks "the most recent skill run that wrote to this file", not just description-driven refreshes. Leave `date` and `enriched-date` unchanged — `date` records the original first-run date, `enriched-date` records the most recent codebase-analysis enrichment.

If the existing frontmatter does not yet have a `description-refresh-date` field (artifacts from earlier skill versions), add it. Place it directly after `enriched-date` if that field exists, otherwise after `date`.

Example after refresh:

```yaml
---
source: jira
issue: OPTS-8
date: 2026-04-23
enriched-date: 2026-04-23
description-refresh-date: 2026-04-28
---
```
