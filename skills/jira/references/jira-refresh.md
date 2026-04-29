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

Enter only when `docs/jira/<KEY>.md` already exists at the project root — Step 3.5 of SKILL.md guards this entry.

The fresh fetch from Step 3 (issue details, linked issues, comments, sprint context) is the canonical "what JIRA says now". The local file is "what JIRA said the last time the skill ran, plus any enrichment". The job is to reconcile.

Run [Comparison rules](#comparison-rules) → [Decision matrix](#decision-matrix) — the matrix row chosen specifies the next route.

## Comparison rules

Compare the freshly fetched JIRA against the local file. Diff these fields only:

| Field | Local file location | Fresh fetch source | Diff style |
|-------|---------------------|--------------------|------------|
| Goal | `### Goal` section body | Issue summary + description | Semantic |
| Acceptance Criteria | `### Acceptance Criteria` numbered list | Description (extracted criteria) | Item-by-item semantic |
| Status | `### Context` → `Status:` line | `status` field | Exact |
| Priority | `### Context` → `Priority:` line | `priority` field | Exact |
| Sprint | `### Context` → `Sprint:` line | sprint name | Exact |

Do NOT diff: comments, sub-task statuses, sibling issues, key decisions, refined description, suggested approach, codebase impact, risks, scope assessment, implementation tickets. Comments are read-only context. Enrichment sections are owned by prior analysis runs and are preserved unless explicitly re-analyzed.

**Semantic diff for Goal and Acceptance Criteria:** Compare for material change in meaning, not byte-exact text. Whitespace, punctuation, and rewordings that preserve meaning do not count as divergence. A criterion that gains a new constraint (e.g., "max 3 reset requests per hour" added to a previously open-ended criterion) IS divergence. A new numbered criterion appearing in JIRA IS divergence. A criterion disappearing from JIRA IS divergence.

## Decision matrix

| Diff outcome | Action |
|--------------|--------|
| Nothing diverged | [No-change short circuit](#no-change-short-circuit) — its drift-pending guard handles the re-entry case |
| Metadata only (Status / Priority / Sprint), no `drift-pending` | Run [Update procedure](#update-procedure) for the diverged `### Context` lines, skip the re-analysis prompt, continue to Step 6 |
| Metadata only, `drift-pending: true` in frontmatter | Run [Update procedure](#update-procedure) for the diverged `### Context` lines, then route to the [Sub-item walk](#sub-item-walk) (drift-pending re-entry) |
| Goal and/or Acceptance Criteria changed (with or without metadata changes) | Run [Update procedure](#update-procedure) for every diverged section, run the [Sub-item walk](#sub-item-walk), then prompt for re-analysis once |

When prompting for re-analysis, use `AskUserQuestion` — header "Re-analyze", question "JIRA criteria changed since the last run. Would you like to re-run codebase analysis against the new criteria?":
- **Skip** — "Update the local file only" (default)
- **Re-analyze** — "Run Step 5 again with the new criteria"

If "Re-analyze": jump to Step 5 of SKILL.md using the freshly diffed Goal and Acceptance Criteria. The existing enrichment sections from the prior run get replaced by Step 5's output via the existing Task File Update procedure.

If "Skip": continue to Step 6.

## Update procedure

Apply changes in place; preserve everything else.

1. Read the existing `docs/jira/<KEY>.md` in full.
2. Replace diverged content per field type. For `### Goal` and `### Acceptance Criteria`, replace the entire section body. For `### Context`, replace ONLY the diverged lines (`Status:`, `Priority:`, or `Sprint:`) in place — preserve all other Context lines (Type, Assignee, Parent, Labels, Linked issues, Subtasks, Related sprint work) verbatim. For Acceptance Criteria, preserve any items previously marked `(from codebase analysis)` — these were added during enrichment and do not come from JIRA. New JIRA criteria slot before the `(from codebase analysis)` items, keeping numbering continuous.
3. Do NOT touch `### Refined Description`, `### Suggested Approach`, `### Codebase Impact`, `### Risks`, or `### Scope Assessment` (owned by enrichment runs in `jira-codebase-analysis.md`); also do NOT touch `### Implementation Tickets` (owned by `jira-implementation-tickets.md` Recording), `### Sub-item Drift` (owned by the Sub-item walk below), or `### Refined plan` (written by plan-mode after `/optimus:jira` recommends it — see SKILL.md Step 6).
4. Update frontmatter per [Frontmatter update](#frontmatter-update).
5. Write the file.
6. Report to the user which sections changed, one line each: e.g., `Updated: ### Acceptance Criteria (1 new criterion, 1 reworded)`.

If the diff is so large that preservation makes no sense (e.g., all criteria changed AND the goal changed), still preserve enrichment but flag in the report that enrichment may now be stale: `Note: enrichment sections may no longer match. Consider running re-analysis.`

## Sub-item walk

**Entry paths:**
- **Diff-driven entry** — entered from the [Decision matrix](#decision-matrix) after the [Update procedure](#update-procedure) completes, when Goal and/or Acceptance Criteria diverged. Metadata-only diffs (Status/Priority/Sprint) without `drift-pending: true` skip this section.
- **Drift-pending re-entry** — entered when `drift-pending: true` is set in frontmatter (a prior Stop, see step 5 below). Source paths:
  - From the [No-change short circuit](#no-change-short-circuit)'s drift-pending guard.
  - From the [Decision matrix](#decision-matrix) metadata-only row after the Update procedure has modified only `### Context` lines.

  Either way, `### Acceptance Criteria` is unchanged from disk; use it as-is.

If the local file has no `### Implementation Tickets` section, skip the entire Sub-item walk: also remove any pre-existing `### Sub-item Drift` block (it was anchored to the now-absent `### Implementation Tickets`), clear `drift-pending: true` from frontmatter if set, then on diff-driven entry continue to the re-analyze prompt; on drift-pending re-entry exit to Step 6 of SKILL.md.

Otherwise:

1. Parse `Ticket` cells from the `### Implementation Tickets` table; filter to values matching `^[A-Z][A-Z0-9]+-\d+$` (drops headers, blanks, placeholders like `(proposed-1)`, and stray manual edits). If no keys remain, skip the entire Sub-item walk: remove any pre-existing `### Sub-item Drift` block (it was tied to the now-keyless table), clear `drift-pending: true` from frontmatter if set, then route per entry path (re-analyze prompt on diff-driven entry, Step 6 of SKILL.md on drift-pending re-entry).
2. For each remaining key, fetch the issue using the get-single-issue tool from the Tool Name Resolution table in `jira-context-extraction.md` (Read-only — no writes). Cap the walk at 15 sub-items; if more, fetch the first 15 and report the rest as unwalked.
3. For each fetched sub-item, compare its summary and (if available) acceptance criteria against the parent's current `### Acceptance Criteria` (freshly updated by the Update procedure on diff-driven entry; unchanged from disk on drift-pending re-entry). Do NOT use `### Codebase Impact` — that section is enrichment owned by prior analysis runs and is not refreshed here, so on Skip-re-analyze paths it would be stale.
4. Flag a sub-item as drifted only when:
   - The parent gained or removed an acceptance criterion AND no sub-item's stated scope clearly maps to the change, OR
   - A sub-item's summary references a parent criterion that no longer exists.
5. If no sub-items were flagged in step 4, skip the prompt — proceed directly to step 6's no-drift branch (remove any prior block, write nothing new). Otherwise, do NOT auto-edit sub-items. Report drift only — present a summary and ask the user via `AskUserQuestion` whether to:
   - **Continue** — "Note the drift in the local file and proceed" (default)
   - **Stop** — "Pause so I can update sub-items manually first"

   On "Stop": set `drift-pending: true` in the local file's frontmatter so the next `/optimus:jira <KEY>` run re-runs this walk even when JIRA hasn't moved since this Stop. Then exit the skill immediately without progressing to step 6 of this procedure or to Step 6 of SKILL.md. Do NOT write the `### Sub-item Drift` block on Stop — the user resumes by re-running `/optimus:jira <KEY>` after they've updated the sub-items.
6. On "Continue" (or the no-drift skip from step 5), update the `### Sub-item Drift` block.
   - **If drift detected and user chose Continue:** insert a new `### Sub-item Drift` block (replacing any prior one — the block represents the latest refresh only). Body is a bullet list of `<sub-key>: <reason>` entries. Place the block immediately after `### Implementation Tickets` and before `### Scope Assessment`.
   - **If no drift detected:** remove any prior `### Sub-item Drift` block; do not insert a new one.
7. Clear `drift-pending: true` from frontmatter if present. Do NOT bump `description-refresh-date` — see [Frontmatter update](#frontmatter-update).
8. Route per entry path: on diff-driven entry, fall through to the re-analyze prompt; on drift-pending re-entry, exit to Step 6 of SKILL.md.

## No-change short circuit

When the diff finds nothing material:

**Drift-pending guard:** If the local file's frontmatter has `drift-pending: true` (set by a prior Stop in the [Sub-item walk](#sub-item-walk)), do NOT short-circuit. Route directly to the Sub-item walk (drift-pending re-entry) — the walk owns its own routing on completion.

Otherwise, perform the short circuit:

1. Report to the user. If `description-refresh-date` is present in the local file's frontmatter, use: `No changes detected since description-refresh-date: <YYYY-MM-DD>. Skipping update.` If absent (legacy file from a pre-refresh skill version), use: `No changes detected since date: <YYYY-MM-DD> (legacy file, no refresh tracking). Skipping update.`
2. Do NOT bump `description-refresh-date` — nothing changed.
3. Do NOT post a JIRA comment.
4. Skip directly to Step 6 of SKILL.md (recommend the next step).

## Frontmatter update

`description-refresh-date` tracks the most recent JIRA-driven write to this file. Bump it to today's date (YYYY-MM-DD) on these writes:

1. Goal / Acceptance Criteria divergence updates ([Update procedure](#update-procedure)).
2. Metadata-only updates — Status / Priority / Sprint ([Update procedure](#update-procedure)).
3. Implementation-ticket creation Recording (`jira-implementation-tickets.md`).
4. Step 5 enrichment runs that execute the Task File Update procedure (`jira-codebase-analysis.md`) — both initial enrichment and re-analyze re-runs.

The [Sub-item walk](#sub-item-walk) does NOT bump `description-refresh-date`. On diff-driven entry the upstream Update procedure has already bumped; on drift-pending re-entry no JIRA-driven change has occurred. Leave `date` and `enriched-date` unchanged.

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
