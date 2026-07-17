# JIRA MCP: Detection, Safety, and Context Extraction

Server detection, tool name resolution, MCP safety rules, and the fetch/output procedure. Read by the jira skill at Step 1. The **MCP Safety** section is the single source of truth for which tools the skill may call and at which gate.

## Contents

1. [Detection Procedure](#detection-procedure)
2. [Tool Name Resolution](#tool-name-resolution)
3. [MCP Safety](#mcp-safety)
4. [Fetch Procedure](#fetch-procedure)
5. [Structured Output Format](#structured-output-format)
6. [Error Handling](#error-handling)

## Detection Procedure

1. **Check `.mcp.json`** at the project root, if present: scan `mcpServers` keys for `atlassian` (Rovo, official), `mcp-atlassian` (sooperset, community), `jira` (generic), or any key containing `jira` or `atlassian` (case-insensitive). A match becomes the candidate server name.
2. **Probe for tools** with `ToolSearch` (in order, stop at first match): query `jira` — look for `jira_search`, `jira_get_issue`, `searchJiraIssuesUsingJql`, or `getJiraIssue`; then query `atlassian` — look for tools containing `jira_` or `Jira`.
3. **Tools found** → record the server name and tool prefix (`mcp__atlassian__` = Rovo, `mcp__mcp-atlassian__` = sooperset, anything else = generic) and report: `Detected: [server name] ([N] JIRA tools available)`. **No tools found** → the skill routes to `jira-setup.md`.

## Tool Name Resolution

Use `ToolSearch` at runtime to discover available tools — never hard-code assumptions.

**Known tool names by server:**

| Operation | Rovo (`mcp__atlassian__`) | sooperset (`mcp__mcp-atlassian__`) | Safety |
|-----------|--------------------------|-----------------------------------|--------|
| Search issues (JQL) | `searchJiraIssuesUsingJql` or `search` | `jira_search` | Read |
| Get single issue | `getJiraIssue` | `jira_get_issue` | Read |
| Get projects | `getVisibleJiraProjects` | `jira_get_all_projects` | Read |
| Get transitions | `getTransitionsForJiraIssue` | `jira_get_transitions` | Read |
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
| Add comment | `addCommentToJiraIssue` | `jira_add_comment` | **Write** |
| Transition status | `transitionJiraIssue` | `jira_transition_issue` | **Write** |
| Create link | `createIssueLink` | `jira_create_issue_link` | **Write** |
| Add worklog | `addWorklogToJiraIssue` | `jira_add_worklog` | **Write** |

When a **Read** tool is unavailable, fall back to the search tool with targeted JQL (e.g., `key = PROJ-123` when the get-issue tool is missing). Write operations have no fallback — if the specified write tool is unavailable, inform the user and skip the write.

**Generic servers** (detection matched neither Rovo nor sooperset): map each **Read** operation by tool-name pattern via `ToolSearch`. Treat all writes as unavailable unless a discovered tool's name unambiguously matches one of the permitted purposes in the [MCP Safety](#mcp-safety) table (add comment, create issue, create link) — when in doubt, fail closed and skip the write.

## MCP Safety

During context extraction (Steps 1–3.5 of the jira skill, including the refresh path), only call tools marked **Read** in the table above.

**Hard rule:** NEVER call any tool whose name **starts with** `add`, `create`, `edit`, `update`, `transition`, or `delete` during context extraction (e.g., `addCommentToJiraIssue`, `editJiraIssue`, `transitionJiraIssue`).

**Comments:** comments are embedded in the get-issue response or in search results — there is no dedicated "get comments" tool. Do NOT use `addCommentToJiraIssue` to read comments; it is a write tool that creates a new comment on the issue.

Write tools are only permitted in Step 5 of the jira skill, after explicit user confirmation. The full set of writes the skill is allowed to call:

| Tool (Rovo / sooperset) | Purpose | Gate |
|------------------------|---------|------|
| `addCommentToJiraIssue` / `jira_add_comment` | Post the analysis comment | Step 5 user confirmation |
| `createJiraIssue` / `jira_create_issue` | Spawn implementation tickets | Step 5 user confirmation + ticket-creation confirmation gate (default Skip), Complex scope only |
| `createIssueLink` / `jira_create_issue_link` | Link new implementation tickets to the parent (best-effort) | Same gates as `createJiraIssue` |

All other write tools (`editJiraIssue`, `jira_update_issue`, `transitionJiraIssue`, `jira_transition_issue`, `addWorklogToJiraIssue`, `jira_add_worklog`, deletes, etc.) are forbidden by this skill regardless of branch.

## Fetch Procedure

Given an issue key, fetch in this order. If an optional field fails or returns empty, skip it silently — never fail on optional fields.

1. **Issue details** — get-single-issue tool (`getJiraIssue` / `jira_get_issue`); if unavailable, fall back to the search tool with JQL `key = {KEY}`. Capture summary, description, issue type, status, priority, assignee, sprint, epic/parent, and labels.
2. **Linked issues and subtasks** — from the issue details: link type + key + summary per linked issue; subtasks listed separately.
3. **Comments** — the last 10, from the issue data already fetched in step 1 (embedded — make no separate MCP call). Record author, relative date, and body.
4. **Sprint context** — if the issue has a sprint: record the sprint name and goal, then fetch sibling issues (keys + summaries) with JQL `sprint in openSprints() AND project = {PROJECT_KEY} ORDER BY rank ASC`. Skip entirely if sprint data is unavailable.

**Truncation limits:**

| Field | Limit |
|-------|-------|
| Description | 2000 characters (append "(truncated)" if truncated) |
| Comments | Max 10 comments, total text capped at 2000 characters (append "(older comments omitted)" if truncated) |
| Sprint siblings | Max 15 issues, keys + summaries only |
| Linked issues | Max 10, keys + summaries only |
| Subtasks | Max 10, keys + summaries only |

## Structured Output Format

After fetching, assemble the data into this format:

```
## Task: [Issue Key] — [Summary]

### Goal
[Single-sentence distilled goal — synthesized from the summary and description.
For bugs: "Fix [symptom] in [component]." For stories: "Implement [capability]
for [user/system]." For tasks: "Complete [action] for [purpose]."]

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
[Distill decisions, clarifications, or context from comments that would affect
implementation. Ignore routine status updates, @mentions without substance,
and automated comments. If no meaningful decisions found, omit this section.]
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
