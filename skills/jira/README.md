# optimus:jira

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that fetches a JIRA issue and distills it into structured task context for AI-assisted development. It saves the result to `docs/jira/<ISSUE-KEY>.md`, analyzes the codebase to surface missing criteria, scope, and risks, and can optionally write an analysis comment or implementation tickets back to JIRA — always behind explicit confirmation.

## Features

- **Automatic MCP detection** — finds your configured JIRA MCP server (Atlassian Rovo, sooperset/mcp-atlassian, or generic) and guides first-time setup if none exists
- **Search or fetch** — fetch by key (`PROJ-123`), search your assigned issues, or browse by project
- **Structured distillation** — goal, acceptance criteria, context (sprint, links, subtasks), and key decisions from comments
- **Codebase impact analysis** — compares the requirements against actual code to surface missing criteria, scope (Simple/Medium/Complex), and risks
- **Optional JIRA enrichment** — posts an analysis comment, and for Complex scope can spawn linked implementation tickets (opt-in, default off)
- **Refresh-aware re-runs** — re-running on the same key reconciles the local file with JIRA, preserving prior enrichment and checking implementation tickets for drift
- **MCP safety** — read-only tool enforcement during extraction; writes happen only at explicit confirmation gates
- **Cross-skill flow** — recommends the next optimus skill based on assessed complexity

## Quick Start

This skill is part of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin. See the [main README](../../README.md) for installation.

A JIRA MCP server must be configured — the skill guides setup interactively if none is detected.

**Atlassian Rovo** (official, JIRA Cloud, OAuth):

```bash
claude mcp add --transport http --scope user atlassian https://mcp.atlassian.com/v1/mcp
```

Requires Rovo MCP Server enabled by your org admin (`admin.atlassian.com → Apps → AI settings`). Use `--transport http` — the older SSE transport is deprecated and flaky on Windows.

**sooperset/mcp-atlassian** (community, JIRA Cloud or Server/Data Center):

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

Get an API token at https://id.atlassian.com/manage-profile/security/api-tokens. For Server/DC, use `--jira-personal-token` instead of username/token.

## Usage

- `/optimus:jira PROJ-123` — fetch a specific issue by key
- `/optimus:jira` — search your assigned issues or browse by project

The skill fetches the issue, presents a structured task (goal, acceptance criteria, context, key decisions) for your confirmation, saves it to `docs/jira/<ISSUE-KEY>.md`, analyzes the codebase against it, and recommends the next skill. Re-running on the same key refreshes the local file from JIRA instead of regenerating it.

## When to Use

- **Before starting work** — get structured context before coding
- **Before TDD** — acceptance criteria map directly to testable behaviors
- **To enrich issues** — post codebase analysis findings back to JIRA

Skip it if your team doesn't use JIRA, or the task is already clear from conversation context.

## Writing JIRA Tickets for AI-Assisted Development

Explicit acceptance criteria in the ticket = accurate implementation; vague prose = the AI guesses what "done" means. A description template for ticket authors:

```
## Goal
[One sentence: what capability or fix, and why it matters.]

## Acceptance Criteria
1. [Verb + observable outcome — e.g., "Returns 200 with user profile when valid token is provided"]
2. [One behavior per criterion, independently testable]
3. [Include error/edge cases — e.g., "Returns 400 when token is expired"]

## Technical Notes (optional)
- [Constraints, dependencies, performance requirements]

## Out of Scope (optional)
- [What this ticket explicitly does NOT cover]
```

Given/When/Then criteria are extracted as-is. Use comments for decisions that affect implementation ("We chose JWT over sessions because...") — the skill distills them into a Key Decisions section and ignores status updates.

## Relationship to Other Skills

The saved `docs/jira/<ISSUE-KEY>.md` is auto-detected by downstream skills — no copy-paste needed.

| Task complexity | Workflow |
|----------------|----------|
| Simple | `/optimus:jira PROJ-123` → `/optimus:tdd` |
| Medium | `/optimus:jira PROJ-123` → plan mode (jira generates the prompt) → `/optimus:tdd` |
| Complex | `/optimus:jira PROJ-123` → `/optimus:brainstorm` → plan mode → `/optimus:tdd` |
| Tech debt | `/optimus:jira PROJ-123` → `/optimus:refactor` |

The skill recommends the right path based on codebase-assessed complexity. It never creates branches or writes code — its only side effects are the task file under `docs/jira/` and the opt-in JIRA writes.

In spec-driven-development terms, `/optimus:jira` is the supported path for PM-authored content (a JIRA issue, or an external PRD pasted into one), distilling it into engineering-shaped task context. See [`references/sdd-mapping.md`](../../references/sdd-mapping.md).

## Skill Structure

| File | Purpose |
|------|---------|
| `SKILL.md` | The step-by-step workflow |
| `references/jira-context-extraction.md` | MCP server detection, tool names, safety rules, fetch and output procedure |
| `references/jira-setup.md` | First-time MCP server setup (loaded only when no server is detected) |
| `references/jira-codebase-analysis.md` | Codebase impact analysis, scope assessment, task-file enrichment |
| `references/jira-refresh.md` | Re-run reconciliation — diff JIRA against the local file, preserve enrichment |
| `references/jira-implementation-tickets.md` | Opt-in implementation-ticket creation for Complex scope |

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- A JIRA MCP server configured in Claude Code (skill guides setup if missing)

## License

[MIT](../../LICENSE)
