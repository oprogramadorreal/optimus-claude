# JIRA Implementation Ticket Creation

Create implementation tickets in JIRA after a Complex-scope codebase analysis. Called only from Step 5 of SKILL.md, only on the "Update JIRA and local context" branch, and only when the Scope Assessment is `Complex`. This is the only place in the skill that creates new JIRA issues — the **MCP Safety** table in [`jira-context-extraction.md`](jira-context-extraction.md) enumerates the write tools this procedure may call and at which gate.

Flow: [Entry condition](#entry-condition) → [Decomposition](#decomposition) → [Confirmation gate](#confirmation-gate) → [Creation procedure](#creation-procedure) → [Linking](#linking) → [Recording](#recording). Skip-mode jumps from the gate straight to Recording.

## Entry condition

All must be true, or do not invoke this procedure:

- Step 5 reached the "Update JIRA and local context" branch (user opted in to JIRA writes).
- The Scope Assessment is `Complex`.
- The detected server exposes a create-issue tool (`createJiraIssue` / `jira_create_issue` per the Tool Name Resolution table). If not, fall through to Skip-mode: run [Decomposition](#decomposition) and [Recording](#recording) in Proposed mode (no JIRA writes), then continue to Step 6.
- The local `docs/jira/<KEY>.md` has no `### Implementation Tickets` section containing one or more **real JIRA keys** — `Ticket` cells matching `^[A-Z][A-Z0-9]+-\d+$`. Parenthesized placeholders like `(proposed-1)` from a prior Skip-mode recording do NOT count. If real keys are present, skip creation, inform the user that existing tickets are managed by refresh, and continue to Step 6.

## Decomposition

Derive ticket boundaries from the Step 5 output already in `docs/jira/<KEY>.md` (`### Codebase Impact`, `### Suggested Approach`, `### Risks`) — do not re-analyze the codebase.

- One ticket per discrete unit of work in the Suggested Approach. Do NOT split per-file — multi-file changes sharing a goal stay in one ticket.
- A risk requiring its own implementation effort (e.g., a migration backfill) gets its own ticket; a risk that is just a caveat does not.
- Shared infrastructure that gates other work gets the lowest sequence number and is recorded as the prerequisite of dependent tickets.
- Maximum 12 tickets per batch. If decomposition produces more, ask the user whether to scope down or split into rounds.

For each proposed ticket, draft: `summary` (one imperative sentence, ≤ 80 chars), `description` (three sections — `Goal`, `Tied to parent acceptance criteria` with parent criterion numbers, `Prerequisites` listing other ticket keys from this batch or `None`), `issuetype: Task`. Everything, including the section headers, inherits the parent issue's language (the English names here are reference labels — translate from the local file's English content as needed). If the project schema requires `Sub-task` instead of `Task`, that is out of scope — the user creates those manually.

## Confirmation gate

Present the full proposed list before any JIRA write, as a table (`| # | Summary | Type | Prerequisites | Tied to AC |`), then ask the user (AskUserQuestion) — "Create these implementation tickets in JIRA?":

- **Skip — I'll create them manually** (default) — run [Recording](#recording) in Proposed mode (no JIRA writes), continue to Step 6.
- **Create all** — run the [Creation procedure](#creation-procedure) for the full list.
- **Review one-by-one** — per ticket, present the full payload and ask **Create** / **Skip** / **Stop batch** (which finalizes without prompting for the rest). After the loop, proceed to [Linking](#linking) and [Recording](#recording) with the keys created so far.

## Creation procedure

Create tickets in dependency order — prerequisites first (Decomposition already sorted them).

1. Call the create-issue tool with the parent's project key (e.g., `OPTS` for `OPTS-8`) and the drafted `summary`, `description`, `issuetype: Task`. No parent field is needed for `Task`.
2. On success, record the returned key and proceed.
3. On failure (permission, schema, validation), report the tool's error message plus the un-created remainder (drafted summaries and prerequisites), stop the batch, and run [Recording](#recording) for the tickets created so far in Created mode — never mix `(proposed-N)` placeholders into the same table. Do NOT retry automatically: the Entry condition guards real-key rows against duplicate creation, and schema/permission errors won't resolve on retry. The user creates the remainder manually from the drafts in this chat.

## Linking

Run only if the create-link tool is available; best-effort — failures never block the batch. For each created child, call the create-link tool with `inwardIssue` = parent key, `outwardIssue` = child key, `linkType` = `relates to`. If the get-link-types Read tool is available and `relates to` is absent from its schema, try in order: `relates`, `related to`, `is related to`. If none exist, skip that link and report it — do NOT fall back to directional or causal types (`blocks`, `is blocked by`, `duplicates`, `clones`, `causes`), which would misrepresent the relationship. On a failed link call, record the failure and continue; the local table is the source of truth.

## Recording

Always run after the batch completes or is skipped. Read `docs/jira/<KEY>.md` and append (or replace, if present) the `### Implementation Tickets` section immediately before `### Scope Assessment` (guaranteed present — Task File Update ran before this procedure). Exact format:

```markdown
### Implementation Tickets

| Ticket | Title | Prerequisites |
|--------|-------|---------------|
| <KEY-1> | <summary> | None |
| <KEY-2> | <summary> | <KEY-1> |
```

- **Created mode (Create all / Review one-by-one):** real JIRA keys in the `Ticket` column; note above the table: `Created on YYYY-MM-DD as part of /optimus:jira analysis.` Bump `description-refresh-date` to today (see `jira-refresh.md` "Frontmatter update").
- **Proposed mode (Skip):** `(proposed-N)` placeholders in the `Ticket` column; note above the table: `Proposed on YYYY-MM-DD; not yet created in JIRA.` Do NOT bump `description-refresh-date` — no JIRA-driven change occurred.

## Refresh interaction

On re-runs, the Entry condition blocks re-creation when real keys are recorded (even on Re-analyze); files with only `(proposed-N)` placeholders remain eligible for a fresh batch. Existing real-key tickets get a read-only drift review via `jira-refresh.md` "Sub-item walk". To spawn an additional batch on top of a real-key recording, the user must remove or rename the `### Implementation Tickets` section first, then re-run and re-analyze.
