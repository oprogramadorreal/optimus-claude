# optimus:jira

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that fetches and optimizes context from a JIRA issue for AI-assisted development. Distills title, description, acceptance criteria, sprint context, and comments into a structured task description ready for other optimus skills. Optionally improves the JIRA issue itself.

JIRA issues are context — and like all context, their quality directly affects how well Claude Code performs. A vague ticket with no acceptance criteria produces vague implementations. This skill extracts the signal from JIRA and structures it for optimal AI consumption.

## Features

- **Automatic MCP detection** — finds your configured JIRA MCP server (Atlassian Rovo or community servers) automatically
- **Guided setup** — walks you through JIRA MCP server configuration step by step if none is detected
- **Search or fetch** — find issues by key (`PROJ-123`), search your assigned issues, or browse by project
- **Structured distillation** — transforms raw JIRA data into a goal, acceptance criteria, and context summary
- **Sprint awareness** — includes current sprint name, goal, and sibling issues for broader context
- **Improve JIRA issues** — optionally writes back structured acceptance criteria and better formatting to JIRA (double-confirmed before writing)
- **Cross-skill flow** — recommends the next optimus skill based on issue type (TDD for features/bugs, refactor for tech debt)

## Quick Start

This skill is part of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin. See the [main README](../../README.md) for installation instructions.

### Prerequisites

A JIRA MCP server must be configured in Claude Code. The skill supports:

- **[Atlassian Rovo MCP Server](https://www.atlassian.com/platform/remote-mcp-server)** (official, recommended) — cloud-hosted, OAuth 2.1, supports Jira Cloud
- **[sooperset/mcp-atlassian](https://github.com/sooperset/mcp-atlassian)** (community) — open-source, supports Jira Cloud AND Server/Data Center

If no server is configured, the skill guides you through setup interactively.

### Quick Setup: Atlassian Rovo (Cloud)

```bash
claude mcp add --transport sse atlassian https://mcp.atlassian.com/v1/mcp
```

Requires: Atlassian Cloud site with Rovo MCP Server enabled by your org admin (`admin.atlassian.com → Apps → AI settings → Rovo MCP server`).

### Quick Setup: mcp-atlassian (Cloud or Server)

```bash
claude mcp add-json mcp-atlassian '{
  "command": "uvx",
  "args": [
    "mcp-atlassian",
    "--jira-url=https://YOUR-COMPANY.atlassian.net",
    "--jira-username=your.email@company.com",
    "--jira-token=YOUR_API_TOKEN"
  ]
}'
```

Get your API token at https://id.atlassian.com/manage-profile/security/api-tokens

## Usage

In Claude Code:

- `/optimus:jira PROJ-123` — fetch a specific issue by key
- `/optimus:jira` — search your assigned issues or browse by project

### Examples

**Fetch a specific issue:**

```
> /optimus:jira AUTH-456

## JIRA MCP Server
Detected: mcp-atlassian (12 JIRA tools available)

## Task: AUTH-456 — Add password reset endpoint

### Goal
Implement a password reset flow that sends a reset link via email and allows
users to set a new password.

### Acceptance Criteria
1. POST /auth/reset-password accepts email, returns 200 if account exists
2. Reset token is generated with 1-hour expiration
3. GET /auth/reset-password/:token validates the token
4. PUT /auth/reset-password/:token accepts new password, updates account
5. Expired or invalid tokens return 400 with clear error message

### Context
- Type: Story
- Priority: High
- Sprint: Sprint 12 — Authentication hardening
- Parent: AUTH-400 — Authentication improvements epic
- Linked issues: AUTH-410 — Add rate limiting to auth endpoints (relates to)
- Related sprint work: AUTH-455 — Add MFA support, AUTH-457 — Audit auth logs
```

**Search assigned issues:**

```
> /optimus:jira

How would you like to find your JIRA issue?
> My open issues

1. AUTH-456 — Add password reset endpoint [Story, High]
2. AUTH-410 — Add rate limiting to auth endpoints [Task, Medium]
3. PAY-89  — Fix currency rounding in checkout [Bug, Critical]

Which issue are you working on?
> 1
```

**Improve a JIRA issue:**

```
> Would you like to improve this JIRA issue's description?
> Improve description

## Proposed JIRA Update: AUTH-456

### Changes
- Added 5 structured acceptance criteria (was: prose description only)
- Restructured into Goal / Criteria / Technical Notes sections
- Preserved all original content

Apply this update to the JIRA issue?
> Apply

✓ JIRA issue AUTH-456 updated successfully.
```

## When to Use

- **Before starting work** — fetch the JIRA issue to get structured context before coding
- **Before TDD** — get acceptance criteria that map directly to testable behaviors
- **Before branching** — the issue key and description inform the branch name
- **To improve tickets** — add structure to vague JIRA issues before implementation begins

## When NOT to Use

- **No JIRA** — your team doesn't use JIRA for issue tracking
- **Simple tasks** — if the task is obvious from conversation context, just describe it inline
- **Already have context** — if you've already pasted the JIRA content into the conversation

## Relationship to Other Skills

| Workflow | Skills |
|----------|--------|
| JIRA → TDD | `/optimus:jira PROJ-123` fetches context, then `/optimus:tdd` implements test-first |
| JIRA → Branch → TDD | `/optimus:jira` for context, `/optimus:branch` to create a named branch, `/optimus:tdd` to build |
| JIRA → Refactor | `/optimus:jira` for tech debt tickets, then `/optimus:refactor` to restructure |

The jira skill only fetches and structures context — it never creates branches, writes code, or modifies your project. It outputs a task description that subsequent skills consume naturally from the conversation.

## Supported MCP Servers

| Server | Jira Cloud | Jira Server/DC | Setup Complexity |
|--------|------------|----------------|------------------|
| [Atlassian Rovo](https://www.atlassian.com/platform/remote-mcp-server) | Yes | No | Low (one command + OAuth) |
| [sooperset/mcp-atlassian](https://github.com/sooperset/mcp-atlassian) | Yes | Yes | Medium (API token + Docker/uvx) |

The skill auto-detects which server is configured and adapts its tool calls accordingly.

## Skill Structure

| File | Purpose |
|------|---------|
| `SKILL.md` | Skill definition with 6-step workflow |
| `references/jira-mcp-detection.md` | MCP server detection and guided setup procedure |
| `references/jira-context-extraction.md` | Context fetching, search, and structuring procedure |

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- A JIRA MCP server configured in Claude Code (skill guides setup if missing)

## License

[MIT](../../LICENSE)
