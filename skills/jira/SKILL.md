---
description: Fetches and optimizes context from a JIRA issue for AI-assisted development. Searches assigned issues or fetches by key. Distills title, description, acceptance criteria, sprint context, and comments into a structured task description. Optionally improves the JIRA issue itself. Use before /optimus:tdd or /optimus:branch to pull task context from JIRA.
disable-model-invocation: true
---

# JIRA Context

Fetch a JIRA issue, distill it into an optimized task description for Claude Code, and optionally improve the issue's description in JIRA. The skill works with any JIRA MCP server (Atlassian Rovo or community servers like sooperset/mcp-atlassian) and guides first-time setup when no server is configured.

## Step 1: Detect JIRA MCP Server

Read `$CLAUDE_PLUGIN_ROOT/skills/jira/references/jira-mcp-detection.md` and follow the **Detection Procedure**.

- **Server detected** → record `jira-server-name` and tool prefix, proceed to Step 2
- **No server detected** → follow the **Guided Setup Procedure** in the same reference. If setup completes successfully, proceed to Step 2. If the user skips setup, stop

## Step 2: Find the Issue

Two modes based on whether the user provided an issue key inline.

### Direct fetch

If the user provided an issue key inline (e.g., `/optimus:jira PROJ-123`):
1. Validate format — must match `[A-Z][A-Z0-9]+-\d+` (e.g., `PROJ-123`, `AB-1`)
2. If valid → proceed to Step 3 with this key
3. If invalid → inform the user and use `AskUserQuestion` to request a corrected key

### Search mode

If no issue key was provided (e.g., `/optimus:jira` with no argument), use `AskUserQuestion` — header "Find issue", question "How would you like to find your JIRA issue?":
- **Enter issue key** — "I know the key (e.g., PROJ-123)"
- **My open issues** — "Search my assigned open issues"
- **Search by project** — "List recent issues in a specific project"

**Enter issue key:** Use `AskUserQuestion` — header "Issue key", question "Enter the JIRA issue key:". Validate and proceed to Step 3.

**My open issues:** Read `$CLAUDE_PLUGIN_ROOT/skills/jira/references/jira-context-extraction.md`, section **Search: Assigned Issues**. Execute the JQL search, present results as a numbered list (max 10). Use `AskUserQuestion` — header "Select issue", question "Which issue are you working on?" with each issue as an option (label: `KEY — Summary`, description: `[Type, Priority]`). Proceed to Step 3 with the selected key.

**Search by project:** Use `AskUserQuestion` — header "Project", question "Enter the JIRA project key (e.g., PROJ):". Execute the project search from the extraction reference. Present results and let the user pick, same as above. Proceed to Step 3 with the selected key.

## Step 3: Fetch Issue Context

Read `$CLAUDE_PLUGIN_ROOT/skills/jira/references/jira-context-extraction.md` and follow the **Fetch Procedure** for the selected issue key:

1. Fetch issue details (summary, description, type, status, priority, assignee, sprint, parent/epic)
2. Fetch linked issues and subtasks (keys + summaries only)
3. Fetch recent comments (last 10, truncated to 2000 characters total)
4. Fetch sprint context (sprint name, goal, sibling issues)

Handle errors according to the **Error Handling** table in the reference. If a critical error occurs (401, 403, 404), report it to the user with the specified message and stop.

## Step 4: Distill into Structured Task

Assemble the fetched data into the **Structured Output Format** from the extraction reference:

```
## Task: [Issue Key] — [Summary]

### Goal
[Single-sentence distilled goal]

### Acceptance Criteria
[Extracted or inferred acceptance criteria as a numbered list]

### Context
- Type: [Issue type]
- Status: [Current status]
- Priority: [Priority]
- Assignee: [Name]
- Sprint: [Sprint name — sprint goal]
- Parent: [Epic key — Epic summary]
- Linked issues: [KEY — summary (link type)]
- Subtasks: [KEY — summary (status)]
- Related sprint work: [Sibling issues in the same sprint]

### Key Decisions (from comments)
[Distilled decisions and context from comments]
```

Omit sections that have no data (e.g., no sprint, no linked issues, no comments with decisions).

Present the structured task to the user. Use `AskUserQuestion` — header "Task review", question "Does this capture the task correctly?":
- **Looks good** — "Use this task description"
- **Adjust** — "I want to refine before continuing"

If "Adjust": use `AskUserQuestion` — header "Refinement", question "What would you like to change?" (free text). Apply the changes and present the updated version. Re-confirm.

## Step 5: Improve JIRA Issue (optional)

Use `AskUserQuestion` — header "Improve issue", question "Would you like to improve this JIRA issue's description? This adds structured acceptance criteria and better formatting directly in JIRA.":
- **Improve description** — "Update the JIRA issue with the structured content above"
- **Skip** — "Keep the JIRA issue as-is"

If **Skip** → proceed to Step 6.

If **Improve description**:

1. Generate an improved description for the JIRA issue:
   - Preserve the original description's intent and content
   - Add structured acceptance criteria (if not already present)
   - Improve formatting (headers, lists, clear sections)
   - Do not remove any information from the original

2. Present a before/after comparison to the user:

```
## Proposed JIRA Update: [Issue Key]

### Current Description
[Original description, truncated to 1000 chars if longer]

### Proposed Description
[Improved description]

### Changes
- [What was added/restructured — e.g., "Added 5 acceptance criteria",
  "Restructured into Goal/Criteria/Notes sections"]
```

3. Use `AskUserQuestion` — header "Confirm update", question "Apply this update to the JIRA issue?":
   - **Apply** — "Update the JIRA issue now"
   - **Edit first** — "Let me adjust the proposed description"
   - **Cancel** — "Don't update the JIRA issue"

4. If **Apply**: use the MCP update tool to write the improved description. Report success or failure.
5. If **Edit first**: let the user describe changes, regenerate, and re-confirm.
6. If **Cancel**: proceed to Step 6 without writing.

## Step 6: Recommend Next Step

Based on the issue type and context, recommend the next skill:

- **Story / Feature / New capability** → "Recommend running `/optimus:tdd` to implement this feature test-first."
- **Bug** → "Recommend running `/optimus:tdd` to reproduce the bug with a failing test, then fix it."
- **Refactoring / Tech debt** → "Recommend running `/optimus:refactor` to restructure the code."
- **Any task** → also mention `/optimus:branch` if the user hasn't created a feature branch yet

Tell the user: **Tip:** for best results, start a fresh conversation for the next skill — each skill gathers its own context from scratch. Copy the task description above and paste it as input (e.g., `/optimus:tdd "Task: PROJ-123 — [summary]"`).
