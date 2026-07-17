---
description: Fetches a JIRA issue via a configured MCP server and distills it into a structured task file at docs/jira/<KEY>.md that downstream skills auto-detect. Analyzes the codebase to surface missing criteria, scope, and risks; optionally writes an analysis comment or implementation tickets back to JIRA after explicit confirmation. Re-runs reconcile the local file instead of regenerating. Guides MCP setup if none is configured.
disable-model-invocation: true
argument-hint: "[issue-key]"
---

# JIRA Context

Fetch a JIRA issue, distill it into a structured task file, analyze the codebase against it, and optionally enrich the issue in JIRA. Works with any JIRA MCP server (Atlassian Rovo, sooperset/mcp-atlassian, or generic).

## Safety

Steps 1–3.5 (including the refresh path) perform no MCP writes; local file writes are permitted. MCP writes are allowed only in Step 5 after explicit user confirmation. The **MCP Safety** section of `jira-context-extraction.md` is the single source of truth for which tools the skill may call and at which gate.

## Language

Content written back to JIRA MUST stay in the issue's original language — never translate it to English. All local files (`docs/jira/*.md`) and all user-facing output are in English; translate as needed while distilling.

## Step 1: Detect JIRA MCP Server

Read `$CLAUDE_PLUGIN_ROOT/skills/jira/references/jira-context-extraction.md` and follow its **Detection Procedure**. Server detected → record the server name and tool prefix, continue. None detected → read `$CLAUDE_PLUGIN_ROOT/skills/jira/references/jira-setup.md` and follow it; if the user skips setup, stop.

## Step 2: Find the Issue

If the user provided an issue key inline, validate it: the entire input must match `^[A-Z][A-Z0-9]+-\d+$` (e.g., `PROJ-123`). Ask for a corrected key if invalid, then continue to Step 3.

If no key was provided, ask the user (AskUserQuestion) whether to enter a key, search their assigned open issues, or browse by project:

- **Assigned issues** — JQL: `assignee = currentUser() AND resolution = Unresolved ORDER BY updated DESC`
- **By project** — ask for the project key and validate it against `^[A-Z][A-Z0-9]{1,9}$` before interpolating (JQL injection guard), then JQL: `project = {KEY} AND resolution = Unresolved ORDER BY updated DESC`

Present at most 10 results as a numbered list (`KEY — Summary [Type, Priority]`) and let the user pick.

## Step 3: Fetch Issue Context

Follow the **Fetch Procedure** in `jira-context-extraction.md` (read in Step 1): issue details, linked issues and subtasks, recent comments, sprint context. Handle failures per its **Error Handling** table — on 401/403/404, report the specified message and stop.

## Step 3.5: Detect Prior Run

If `docs/jira/<ISSUE-KEY>.md` exists at the project root, read `$CLAUDE_PLUGIN_ROOT/skills/jira/references/jira-refresh.md` and follow the **Refresh Procedure** instead of Step 4 — it owns its own routing on completion. Otherwise continue.

## Step 4: Distill into Structured Task

Assemble the fetched data into the **Structured Output Format** from `jira-context-extraction.md` — the single source for section names. Omit sections with no data. If the issue's acceptance criteria use Given/When/Then phrasing, preserve it verbatim in each entry — `/optimus:brainstorm` reformats those into `### Scenario:` blocks.

Present the structured task and confirm with the user, iterating on requested adjustments. Then save it to `docs/jira/<ISSUE-KEY>.md` and report the path:

```markdown
---
source: jira
issue: [ISSUE-KEY]
date: [YYYY-MM-DD]
description-refresh-date: [YYYY-MM-DD]
---

[The full structured task — Goal, Acceptance Criteria, Context, Key Decisions]
```

## Step 5: Analyze Against Codebase

Read `$CLAUDE_PLUGIN_ROOT/skills/jira/references/jira-codebase-analysis.md` and follow the **Analysis Procedure** using the Goal and the ORIGINAL Acceptance Criteria from the task file (exclude items tagged `(from codebase analysis)` — prior enrichment, not source criteria). Present the **Impact Summary**.

Verify with `ToolSearch` that the detected server's add-comment tool named in the MCP Safety permitted-write table (`addCommentToJiraIssue` for Rovo, `jira_add_comment` for sooperset) is in the runtime tool list — do not probe for other comment-like tools. Then ask the user (AskUserQuestion) how to use the findings:

- **Update JIRA and local context** (offer only if the add-comment tool is available) — enrich the local file and post an analysis comment to JIRA
- **Update local context only** — enrich `docs/jira/<ISSUE-KEY>.md` only
- **Skip** — proceed without changes

On either update choice, run the **Task File Update** procedure first — the local file is the single source of truth. On the JIRA branch, then post the comment per the **JIRA Comment Format**, translated to the issue's original language if it isn't English; comments are append-only, so no further confirmation is needed. If the tool call fails at runtime, inform the user and keep the local update.

**Complex scope, JIRA branch only:** if the Scope Assessment is `Complex` and the user chose "Update JIRA and local context", read `$CLAUDE_PLUGIN_ROOT/skills/jira/references/jira-implementation-tickets.md` and follow it to optionally spawn implementation tickets — it has its own confirmation gate defaulting to no JIRA writes.

## Step 6: Recommend Next Step

Route by issue type and the Step 5 Scope Assessment (fall back to acceptance-criteria count when inconclusive). If the user has no feature branch yet, also mention `/optimus:commit branch`. The recommended skill gathers its own context, so suggest a fresh conversation for it.

- **Tech debt / refactoring** (issue type, labels like `tech-debt`/`refactor`, or a goal that restructures code without changing behavior) → recommend `/optimus:refactor`.
- **Simple** (assessment simple, or 1–3 criteria in a single component) → recommend `/optimus:tdd` — it auto-detects `docs/jira/<ISSUE-KEY>.md`.
- **Complex** (assessment complex, or 7+ criteria, multiple components, architecture/migration concerns, unclear design) → recommend `/optimus:brainstorm` — it auto-detects the task file.
- **Medium** (between the two) → offer to generate a plan-mode prompt (below); if declined, recommend `/optimus:tdd` as for Simple.

### Medium path: plan-mode prompt

Read `$CLAUDE_PLUGIN_ROOT/skills/brainstorm/references/plan-mode-handoff.md` — this route ends in `/optimus:tdd`, so the review-only carve-out applies. Emit a copyable plan-mode prompt assembled from the task file:

- `## Goal` — from the structured task
- `## Context` — acceptance criteria, context fields, key decisions; plus Files Affected and Risks from Step 5 when available
- `## Starting Hints` — `docs/jira/<ISSUE-KEY>.md`, plus key files from the impact summary
- `## Scope` — focus area, and anything the JIRA issue excludes
- Close with the carve-out's `## How this conversation should run` block, substituting `<doc-path>` = `docs/jira/<ISSUE-KEY>.md`

Tell the user the carve-out's three numbered steps, then emit the execution prompt as a second copyable block:

````
```
## Goal
Run `/optimus:tdd` to implement the refined plan in `docs/jira/<ISSUE-KEY>.md` test-first.

## Starting Hints
- JIRA task (with "Refined plan" section): docs/jira/<ISSUE-KEY>.md
- Acceptance criteria: [carry forward from the task file]

## Scope
- Focus on: [component/area from the structured task]
- Out of scope: [anything the JIRA issue excludes]
```
````

Substitute `<ISSUE-KEY>` with the real key in both prompts so each pasted block is self-contained.
