# JIRA Refresh Procedure

Re-run reconciliation for `/optimus:jira` on a key whose `docs/jira/<KEY>.md` already exists (Step 3.5 guards entry). The fresh fetch from Step 3 is "what JIRA says now"; the local file is "what JIRA said last run, plus enrichment". Reconcile — never regenerate. Run [Comparison rules](#comparison-rules) → [Decision matrix](#decision-matrix); the chosen matrix row specifies the route.

## Comparison rules

Diff these fields only:

| Field | Local file location | Fresh fetch source | Diff style |
|-------|---------------------|--------------------|------------|
| Goal | `### Goal` section body | Issue summary + description | Semantic |
| Acceptance Criteria | `### Acceptance Criteria` numbered list | Description (extracted criteria) | Item-by-item semantic |
| Status | `### Context` → `Status:` line | `status` field | Exact |
| Priority | `### Context` → `Priority:` line | `priority` field | Exact |
| Sprint | `### Context` → `Sprint:` line | sprint name | Exact |

Do NOT diff: comments, sub-task statuses, sibling issues, key decisions, or any enrichment section — comments are read-only context, and enrichment is owned by prior analysis runs.

**Semantic diff:** compare for material change in meaning, not byte-exact text — whitespace, punctuation, and meaning-preserving rewordings are not divergence. A criterion gaining a new constraint IS divergence; a criterion appearing in or disappearing from JIRA IS divergence.

## Decision matrix

| Diff outcome | Action |
|--------------|--------|
| Nothing diverged | [No-change short circuit](#no-change-short-circuit) — its drift-pending guard handles re-entry |
| Metadata only (Status / Priority / Sprint), no `drift-pending` | [Update procedure](#update-procedure) for the diverged `### Context` lines, skip the re-analysis prompt, continue to Step 6 |
| Metadata only, `drift-pending: true` in frontmatter | [Update procedure](#update-procedure) for the diverged `### Context` lines, then the [Sub-item walk](#sub-item-walk) (drift-pending re-entry) |
| Goal and/or Acceptance Criteria changed | [Update procedure](#update-procedure) for every diverged section, then the [Sub-item walk](#sub-item-walk), then prompt for re-analysis once |

Re-analysis prompt — ask the user (AskUserQuestion): "JIRA criteria changed since the last run. Re-run codebase analysis against the new criteria?" **Skip** (default — update the local file only, continue to Step 6) or **Re-analyze** (jump to Step 5 of SKILL.md with the freshly diffed Goal and Acceptance Criteria; prior enrichment gets replaced via the Task File Update procedure).

## Update procedure

Apply changes in place; preserve everything else.

1. Read the existing `docs/jira/<KEY>.md` in full.
2. Replace diverged content per field type. For `### Goal` and `### Acceptance Criteria`, replace the entire section body. For `### Context`, replace ONLY the diverged lines (`Status:`, `Priority:`, or `Sprint:`) — preserve all other Context lines verbatim. In Acceptance Criteria, preserve items marked `(from codebase analysis)` (enrichment, not from JIRA); new JIRA criteria slot before the tagged items, keeping numbering continuous.
3. Do NOT touch `### Refined Description`, `### Suggested Approach`, `### Codebase Impact`, `### Risks`, or `### Scope Assessment` (owned by enrichment runs in `jira-codebase-analysis.md`); nor `### Implementation Tickets` (owned by `jira-implementation-tickets.md` Recording), `### Sub-item Drift` (owned by the Sub-item walk), or `### Refined plan` (written by plan-mode after Step 6 recommends it).
4. Update frontmatter per [Frontmatter update](#frontmatter-update).
5. Write the file.
6. Report which sections changed, one line each: e.g., `Updated: ### Acceptance Criteria (1 new criterion, 1 reworded)`. If the diff is so large that preservation makes little sense (all criteria AND the goal changed), still preserve enrichment but add: `Note: enrichment sections may no longer match. Consider running re-analysis.`

## Sub-item walk

Entered either **diff-driven** (from the decision matrix after Goal/Acceptance Criteria updates) or as **drift-pending re-entry** (`drift-pending: true` in frontmatter from a prior Stop — via the short circuit's guard or the metadata-only row). Either way `### Acceptance Criteria` is current: freshly updated on diff-driven entry, unchanged from disk on re-entry.

If the local file has no `### Implementation Tickets` section, skip the walk: remove any pre-existing `### Sub-item Drift` block, clear `drift-pending: true` if set, then route per entry path (step 8).

1. Parse `Ticket` cells from the `### Implementation Tickets` table; keep only values matching `^[A-Z][A-Z0-9]+-\d+$` (drops headers, blanks, placeholders like `(proposed-1)`, stray edits). If no keys remain, skip the walk exactly as for a missing section above.
2. Fetch each remaining key with the get-single-issue tool from the Tool Name Resolution table in `jira-context-extraction.md` (Read-only — no writes). Cap at 15 sub-items; report any beyond that as unwalked.
3. Compare each sub-item's summary and (if available) acceptance criteria against the parent's current `### Acceptance Criteria`. Do NOT use `### Codebase Impact` — it is enrichment and may be stale.
4. Flag a sub-item as drifted only when the parent gained or removed a criterion AND no sub-item's stated scope clearly maps to the change, OR a sub-item's summary references a parent criterion that no longer exists.
5. If nothing was flagged, go to step 6's no-drift branch. Otherwise do NOT auto-edit sub-items — present the drift summary and ask the user (AskUserQuestion): **Continue** (default — "Note the drift in the local file and proceed") or **Stop** ("Pause so I can update sub-items manually first"). On Stop: set `drift-pending: true` in frontmatter, do NOT write the `### Sub-item Drift` block, and exit the skill immediately (the user resumes by re-running `/optimus:jira <KEY>`).
6. On Continue with drift: insert a `### Sub-item Drift` block (replacing any prior one — it represents the latest refresh only), a bullet list of `<sub-key>: <reason>` entries, placed immediately after `### Implementation Tickets` and before `### Scope Assessment`. On no drift: remove any prior `### Sub-item Drift` block; write nothing new.
7. Clear `drift-pending: true` from frontmatter if present. Do NOT bump `description-refresh-date` (see [Frontmatter update](#frontmatter-update)).
8. Route per entry path: diff-driven → fall through to the re-analyze prompt; drift-pending re-entry → exit to Step 6 of SKILL.md.

## No-change short circuit

**Drift-pending guard:** if frontmatter has `drift-pending: true`, do NOT short-circuit — route to the [Sub-item walk](#sub-item-walk) (drift-pending re-entry), which owns its own routing.

Otherwise: report `No changes detected since description-refresh-date: <YYYY-MM-DD>. Skipping update.` (fall back to the `date` field for legacy files without `description-refresh-date`). Do NOT bump `description-refresh-date`, do NOT post a JIRA comment, and skip directly to Step 6 of SKILL.md.

## Frontmatter update

`description-refresh-date` tracks the most recent JIRA-driven write to this file. Bump it to today (YYYY-MM-DD) on: Goal/Acceptance Criteria updates, metadata-only updates ([Update procedure](#update-procedure)), Created-mode ticket Recording (`jira-implementation-tickets.md`), and Step 5 enrichment runs (`jira-codebase-analysis.md` Task File Update).

The [Sub-item walk](#sub-item-walk) never bumps it — on diff-driven entry the Update procedure already did; on drift-pending re-entry no JIRA-driven change occurred. Leave `date` and `enriched-date` unchanged. If a legacy file lacks the `description-refresh-date` field, add it directly after `enriched-date` if present, otherwise after `date`.

```yaml
---
source: jira
issue: OPTS-8
date: 2026-04-23
enriched-date: 2026-04-23
description-refresh-date: 2026-04-28
---
```
