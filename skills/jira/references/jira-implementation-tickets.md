# JIRA Implementation Ticket Creation

Procedure for creating implementation tickets in JIRA after a Complex-scope codebase analysis. Called only from Step 5 of SKILL.md, only when the user has chosen "Update JIRA and local context", and only when the Scope Assessment is `Complex`.

This is the only place in the skill that creates new JIRA issues. See [`jira-context-extraction.md`](jira-context-extraction.md) section "MCP Safety" — that table enumerates the write tools this procedure is allowed to call and at which gate.

## Contents

1. [Implementation Ticket Creation Procedure](#implementation-ticket-creation-procedure) — flow order
2. [Entry condition](#entry-condition) — gating predicates for invocation
3. [Decomposition](#decomposition) — derive ticket boundaries from analysis output
4. [Confirmation gate](#confirmation-gate) — explicit per-batch user approval
5. [Tool resolution](#tool-resolution) — server-specific create + link tools
6. [Creation procedure](#creation-procedure) — order, payload, error handling
7. [Linking](#linking) — parent ↔ child relationship (best-effort)
8. [Recording](#recording) — write the resulting keys into the local file
9. [Refresh interaction](#refresh-interaction) — what happens on re-runs

## Implementation Ticket Creation Procedure

Normal flow: [Entry condition](#entry-condition) → [Decomposition](#decomposition) → [Confirmation gate](#confirmation-gate) → [Creation procedure](#creation-procedure) → [Linking](#linking) → [Recording](#recording). [Entry condition](#entry-condition) owns its own failure routing — see that section. On Skip-mode (Confirmation gate), jump directly to [Recording](#recording). [Refresh interaction](#refresh-interaction) is reference-only, not a step.

## Entry condition

All of the following must be true. If any one is false, do not invoke this procedure:

- Step 5 of SKILL.md reached the "Update JIRA and local context" branch (user opted in to JIRA writes).
- The Scope Assessment from the codebase analysis is `Complex`.
- The detected MCP server exposes a create-issue tool (see [Tool resolution](#tool-resolution)). If it does not, fall through to Skip-mode: run [Decomposition](#decomposition) and [Recording](#recording) in Proposed mode (no JIRA writes), then continue to Step 6.
- The local `docs/jira/<KEY>.md` has no `### Implementation Tickets` section with one or more **real JIRA keys** — `Ticket` cells matching `^[A-Z][A-Z0-9]+-\d+$`. Parenthesized placeholders like `(proposed-1)` from a prior Skip-mode recording do NOT count. If real keys are present, skip implementation ticket creation, inform the user that existing tickets are managed by refresh, and continue to Step 6.

## Decomposition

Derive ticket boundaries from the analysis output already produced in Step 5 — do not re-analyze the codebase.

Inputs (all already in `docs/jira/<KEY>.md` after Step 5's Task File Update):
- `### Codebase Impact` — modules and files grouped by concern.
- `### Suggested Approach` — ordered implementation sequence.
- `### Risks` — cross-cutting concerns that may need their own tickets.

Rules:
- One ticket per discrete unit of work in the Suggested Approach. Do NOT split per-file — multi-file changes that share a goal stay in one ticket.
- A risk that requires its own implementation effort (e.g., "add migration backfill") gets its own ticket. A risk that is just a caveat does not.
- A shared infrastructure piece that gates other work (e.g., a new reference, a shared type) gets the lowest sequence number and is recorded as the prerequisite of dependent tickets.
- Maximum 12 tickets per batch. If decomposition produces more, flag this to the user and ask whether to scope down or split into rounds.

For each proposed ticket, draft:
- `summary` — one short imperative sentence (≤ 80 chars). Inherit the parent issue's language.
- `description` — three sections: `Goal` (one sentence), `Tied to parent acceptance criteria` (numbered list referring to parent criterion numbers), `Prerequisites` (other ticket keys from this batch, or `None`). Inherit the parent issue's language for the entire description, including the section headers — the English names listed here are reference labels only; translate them along with the body text from the local file's English content as needed.
- `issuetype` — `Task`. The procedure does not auto-detect `Sub-task` schema requirements; if the user's project schema requires `Sub-task` instead, that's out of scope for this procedure — they should create the tickets manually.

## Confirmation gate

Present the full proposed list to the user before any JIRA write. Use `AskUserQuestion` — header "Create tickets", question "Create these implementation tickets in JIRA?":
- **Skip — I'll create them manually** (default) — "Emit the list to the local file only; no JIRA writes."
- **Create all** — "Create every ticket in the proposed list and link to the parent."
- **Review one-by-one** — "Confirm each ticket individually before creating."

The proposed list precedes the question as a markdown table:

```
| # | Summary | Type | Prerequisites | Tied to AC |
|---|---------|------|---------------|------------|
| 1 | <summary> | Task | None | #1, #3 |
| 2 | <summary> | Task | #1 | #2 |
...
```

If "Skip": run [Recording](#recording) in **Proposed** mode (no JIRA writes), continue to Step 6.

If "Create all": run [Creation procedure](#creation-procedure) for the full list.

If "Review one-by-one": for each ticket, present its full payload (summary + description) and use `AskUserQuestion` — header "Create #N", question "Create this ticket?" with options **Create**, **Skip**, **Stop batch**. On "Stop batch", finalize without prompting for the rest. After the loop ends (whether by reaching the end of the list or by "Stop batch"), proceed to [Linking](#linking) (if applicable) and [Recording](#recording) with the keys created so far.

## Tool resolution

Look up the create-issue and create-link tools in the [Tool Name Resolution table](jira-context-extraction.md#tool-name-resolution) — that table is the single source of truth for tool names.

If the create-issue tool is not in the available tool list, fall through to Skip-mode per [Entry condition](#entry-condition) — [Decomposition](#decomposition) and [Recording](#recording) still run in Proposed mode. If only the create-issue tool is available but not the create-link tool, create issues without linking — the local table remains the authoritative parent ↔ child record.

## Creation procedure

Create tickets in dependency order — prerequisites first. The Decomposition step already topologically sorts them via the `Prerequisites` field.

For each confirmed ticket:

1. Call the create-issue tool with the project key from the parent (e.g., `OPTS` for `OPTS-8`) and the drafted `summary`, `description`, and `issuetype: Task`. No parent field is required for `Task` issuetype.
2. On success, record the returned key (e.g., `OPTS-19`) and proceed.
3. On failure (permission, schema mismatch, validation error), report the failure to the user with the tool's error message and the un-created remainder (their drafted summaries and prerequisites), then stop the batch. Run [Recording](#recording) for the tickets created so far in Created mode — do NOT mix `(proposed-N)` placeholders into the same table. The un-created remainder must be created manually in JIRA by the user (copy the drafts from this chat log); the skill will NOT retry them automatically, because the Entry condition guards real-key rows from re-creation and bypassing that guard (e.g., by removing the `### Implementation Tickets` section per [Refresh interaction](#refresh-interaction)) would risk creating duplicates of the tickets that succeeded. Schema or permission errors will not resolve on retry anyway.

## Linking

Run only if the link tool is available. Best-effort — failures here do not block the batch.

For each successfully created child key, call the create-link tool from [Tool resolution](#tool-resolution) with:
- `inwardIssue`: parent key (e.g., `OPTS-8`)
- `outwardIssue`: child key (e.g., `OPTS-19`)
- `linkType`: `relates to`. If the get-link-types Read tool is available (see the Tool Name Resolution table) and `relates to` is absent from the schema it returns, try (in order) `relates`, `related to`, `is related to`. If none of those exist, skip the link for this child and report it — do NOT fall back to directional or causal types (`blocks`, `is blocked by`, `duplicates`, `clones`, `causes`), which would silently misrepresent the parent ↔ child relationship.

If a link call fails, record the failure but continue with the remaining links. The local table is the source of truth; the JIRA link is decoration.

## Recording

Always run after the batch completes (or is skipped), regardless of outcome.

Read the existing `docs/jira/<KEY>.md` and append (or replace, if already present) the `### Implementation Tickets` section immediately before `### Scope Assessment`. (SKILL.md Step 5's "Update JIRA and local context" branch runs Task File Update before invoking this procedure, so `### Scope Assessment` is guaranteed to be present here.) Use this exact format:

```markdown
### Implementation Tickets

| Ticket | Title | Prerequisites |
|--------|-------|---------------|
| <KEY-1> | <summary> | None |
| <KEY-2> | <summary> | <KEY-1> |
| ... | ... | ... |
```

Differences by recording mode:
- **Created (Create all / Review one-by-one):** `Ticket` column holds the real keys returned by JIRA. Add a one-line note above the table: `Created on YYYY-MM-DD as part of /optimus:jira analysis.`
- **Proposed (Skip):** `Ticket` column holds placeholders like `(proposed-1)`. Add a one-line note above the table: `Proposed on YYYY-MM-DD; not yet created in JIRA.`

In Created mode, bump `description-refresh-date` in frontmatter to today (a JIRA-driven write — see `jira-refresh.md` "Frontmatter update"). In Skip-mode, do NOT bump — only a local proposed list was emitted, no JIRA-driven change occurred.

## Refresh interaction

On a subsequent `/optimus:jira <KEY>` run with the local file already populated:

- New tickets are not created on refresh runs when real JIRA keys are already recorded — the [Entry condition](#entry-condition) check blocks re-creation even when the user chooses Re-analyze. Files with only `(proposed-N)` placeholders from a prior Skip-mode recording remain eligible for a fresh creation batch on Re-analyze. See `jira-refresh.md` "Sub-item walk" for the read-only drift review of existing real-key tickets.
- To spawn an additional batch on top of an existing real-key recording, remove or rename the existing `### Implementation Tickets` section first, then re-run `/optimus:jira` and re-analyze.
