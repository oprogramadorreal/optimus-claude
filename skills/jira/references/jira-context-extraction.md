# JIRA Context Extraction

Procedure for fetching, structuring, and searching JIRA data via MCP tools. Called by the jira skill after a server has been detected.

The skill passes two variables from detection: `jira-server-name` (the MCP server key) and the tool prefix (e.g., `mcp__atlassian__` or `mcp__mcp-atlassian__`).

## Contents

1. [Tool Name Resolution](#tool-name-resolution) — map operations to server-specific tool names
2. [Search Procedures](#search-procedures) — assigned issues, by project, sprint siblings
3. [Fetch Procedure (Single Issue)](#fetch-procedure-single-issue) — issue details, links, comments, sprint context
4. [Truncation Limits](#truncation-limits) — field-level size caps
5. [Structured Output Format](#structured-output-format) — assembled output template
6. [Error Handling](#error-handling) — error-to-message mapping

## Tool Name Resolution

Different MCP servers expose different tool names. Use `ToolSearch` at runtime to discover available tools — never hard-code assumptions.

**Known tool names by server:**

| Operation | Rovo (`mcp__atlassian__`) | sooperset (`mcp__mcp-atlassian__`) | Safety |
|-----------|--------------------------|-----------------------------------|--------|
| Search issues (JQL) | `searchJiraIssuesUsingJql` or `search` | `jira_search` | Read |
| Get single issue | `getJiraIssue` | `jira_get_issue` | Read |
| Get projects | `getVisibleJiraProjects` | — | Read |
| Get transitions | `getTransitionsForJiraIssue` | — | Read |
| Get link types | `getIssueLinkTypes` | — | Read |
| Get remote links | `getJiraIssueRemoteIssueLinks` | — | Read |
| Get issue type metadata | `getJiraIssueTypeMetaWithFields` | — | Read |
| Get project issue types | `getJiraProjectIssueTypesMetadata` | — | Read |
| Look up user | `lookupJiraAccountId` | — | Read |
| User info | `atlassianUserInfo` | — | Read |
| Get sprints | — | `jira_get_sprints_from_board` | Read |
| Get boards | — | `jira_get_agile_boards` | Read |
| Update issue | `editJiraIssue` | `jira_update_issue` | **Write** |
| Create issue | `createJiraIssue` | `jira_create_issue` | **Write** |
| Add comment | `addCommentToJiraIssue` | — | **Write** |
| Transition status | `transitionJiraIssue` | `jira_transition_issue` | **Write** |
| Create link | `createIssueLink` | — | **Write** |
| Add worklog | `addWorklogToJiraIssue` | — | **Write** |

When a **Read** tool is unavailable, fall back to the search tool with targeted JQL. For example, if `getJiraIssue` is unavailable, use `searchJiraIssuesUsingJql` with JQL `key = PROJ-123`. Write operations have no fallback — if the specified write tool is unavailable, inform the user and skip the write.

## MCP Safety

During context extraction (Steps 1–4 of the jira skill), only call tools marked **Read** in the table above.

**Hard rule:** NEVER call any tool whose name **starts with** `add`, `create`, `edit`, `update`, `transition`, or `delete` during context extraction (e.g., `addCommentToJiraIssue`, `editJiraIssue`, `transitionJiraIssue`).

**Comments:** Comments are embedded in the `getJiraIssue` response or in search results — there is no dedicated "get comments" tool. Do NOT use `addCommentToJiraIssue` to read comments; it is a write tool that creates a new comment on the issue.

Write tools are only permitted in Step 5 of the jira skill, after explicit user confirmation.

## Search Procedures

### Search: Assigned Issues

JQL: `assignee = currentUser() AND resolution = Unresolved ORDER BY updated DESC`

Present results as a numbered list (max 10):
```
1. PROJ-101 — Add user authentication endpoint [Story, High]
2. PROJ-98  — Fix login timeout on slow connections [Bug, Critical]
3. PROJ-95  — Refactor payment module for testability [Task, Medium]
...
```

### Search: By Project

Ask the user for the project key. Validate it matches `[A-Z][A-Z0-9]+` (1-10 uppercase alphanumeric characters, starting with a letter) — reject inputs containing spaces, operators, or special characters. Then use JQL: `project = {KEY} AND resolution = Unresolved ORDER BY updated DESC`

Present results in the same numbered list format (max 10).

### Search: Sprint Siblings

JQL: `sprint in openSprints() AND project = {PROJECT_KEY} ORDER BY rank ASC`

Used internally during context extraction (Step 3 of the skill) to provide sprint awareness. Not exposed as a user-facing search mode.

## Fetch Procedure (Single Issue)

Given an issue key (e.g., `PROJ-123`), fetch context in this order. If any step fails or returns empty, skip it silently — never fail on optional fields.

### 1. Issue Details

Fetch the issue using the get-single-issue tool from the Tool Name Resolution table (`getJiraIssue` for Rovo, `jira_get_issue` for sooperset). If unavailable, fall back to the search tool with JQL `key = {KEY}`.

Extract these fields:
- **Summary** (title)
- **Description** (full text)
- **Issue type** (Bug, Story, Task, Epic, Sub-task, etc.)
- **Status** (To Do, In Progress, Done, etc.)
- **Priority** (Critical, High, Medium, Low, Trivial)
- **Assignee**
- **Sprint** name (from the sprint field, if present)
- **Epic/Parent** link (parent issue key and summary)
- **Labels** (if present)

### 2. Linked Issues

Extract issue links from the issue details. For each linked issue, record:
- Link type (blocks, is blocked by, relates to, duplicates, etc.)
- Linked issue key and summary

Cap at 10 linked issues. For subtasks, list them separately.

### 3. Comments

Extract the last 10 comments from the issue data already fetched in step 1 (via `getJiraIssue` or search). Do not make a separate MCP call for comments — they are embedded in the issue response.

For each comment:
- Author display name
- Date (relative, e.g., "3 days ago")
- Body text

Truncate total comment text to 2000 characters. If truncated, append "(older comments omitted)".

### 4. Sprint Context

If the issue has a sprint field:
1. Record the sprint name and sprint goal (if available)
2. Fetch sibling issues in the same sprint using JQL: `sprint in openSprints() AND project = {PROJECT_KEY} ORDER BY rank ASC`
3. Record up to 15 sibling issues (keys + summaries only)

If sprint tools (`jira_get_sprints_from_board`) are unavailable, fall back to the JQL approach. If sprint data is unavailable entirely, skip this section.

## Truncation Limits

These limits match the PR context injection pattern from `references/context-injection-blocks.md`:

| Field | Limit |
|-------|-------|
| Description | 2000 characters (append "(truncated)" if truncated) |
| Comments | Max 10 comments, total text capped at 2000 characters |
| Sprint siblings | Max 15 issues, keys + summaries only |
| Linked issues | Max 10, keys + summaries only |
| Subtasks | Max 10, keys + summaries only |

## Structured Output Format

After fetching, assemble the data into this format:

```
## Task: [Issue Key] — [Summary]

### Goal
[Single-sentence distilled goal — synthesized from the summary and description.
For bugs: "Fix [symptom] in [component]."
For stories: "Implement [capability] for [user/system]."
For tasks: "Complete [action] for [purpose]."]

### Acceptance Criteria
[Extract from the description if structured criteria exist (numbered lists,
checkbox lists, "Given/When/Then" blocks). If the description has no explicit
criteria, infer 3–5 testable criteria from the description and linked context.
Present as a numbered list.]

### Context
- Type: [Issue type]
- Status: [Current status]
- Priority: [Priority]
- Assignee: [Name]
- Sprint: [Sprint name — sprint goal, if available]
- Parent: [Epic key — Epic summary, if applicable]
- Labels: [Comma-separated labels, if any]
- Linked issues: [KEY — summary (link type), for each. Omit if none.]
- Subtasks: [KEY — summary (status), for each. Omit if none.]
- Related sprint work: [KEY — summary, for sibling issues that may interact
  with this task. Omit if no sprint context or no relevant siblings.]

### Key Decisions (from comments)
[Distill key decisions, clarifications, or context from comments that would
affect implementation. Ignore routine status updates, @mentions without
substance, and automated comments. If no meaningful decisions found, omit
this section entirely.]
```

## Error Handling

| Error | User-facing message |
|-------|---------------------|
| 401 Unauthorized | "Your JIRA authentication has expired. For Rovo: restart Claude Code to re-authenticate via OAuth. For mcp-atlassian: verify your API token has not expired at id.atlassian.com/manage-profile/security/api-tokens and update your MCP configuration." |
| 403 Forbidden | "You don't have permission to view {KEY}. Check your JIRA project access with your JIRA admin." |
| 404 Not Found | "Issue {KEY} not found. Verify the key is correct (format: PROJECT-NUMBER) and that you have access to the project." |
| 429 Rate Limited | Retry once after 2 seconds. If still rate limited: "JIRA rate limit reached. Wait a moment and try `/optimus:jira {KEY}` again." |
| MCP tool error | "The JIRA MCP tool returned an error: {error message}. This may be a server configuration issue — verify the MCP server is running with `claude mcp list`." |
| Empty response | "The JIRA server returned no data for {KEY}. The issue may exist but have restricted visibility." |
