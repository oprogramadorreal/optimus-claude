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

## Writing JIRA Issues for AI-Assisted Development

This section is a guide for **Product Owners, Product Managers, and anyone who writes JIRA tickets** that developers will implement with AI assistance. The `/optimus:jira` skill extracts structured context from your JIRA issues — when you write well-structured tickets, the skill extracts your intent directly. When tickets are vague, the skill has to *infer* acceptance criteria, which is less accurate and may miss your actual requirements.

**The rule is simple:** explicit acceptance criteria in your ticket = accurate implementation. Vague prose = the AI guesses what "done" means.

### Recommended Description Template

Use this structure in the JIRA issue description field. Copy it as a template for your team.

```
## Goal
[One sentence: what capability is being added or what problem is being fixed, and why it matters.]

## Acceptance Criteria
1. [Verb + observable outcome — e.g., "Returns 200 with user profile when valid token is provided"]
2. [Verb + observable outcome]
3. [Verb + observable outcome]
4. [Error/edge case — e.g., "Returns 400 with error message when token is expired"]
5. [Error/edge case]

## Technical Notes (optional)
- [Constraints, dependencies, or architecture decisions — e.g., "Must use the existing AuthService, not a new implementation"]
- [Performance requirements — e.g., "Response time under 200ms at p95"]
- [References — e.g., "See RFC-042 for the token format specification"]

## Out of Scope (optional)
- [What this ticket explicitly does NOT cover — e.g., "Email notifications will be handled in PROJ-456"]
```

### Field-by-Field Guidance

| JIRA Field | What the skill does with it | How to fill it well |
|---|---|---|
| **Summary** | Becomes the task title and is used to generate a one-sentence goal | Write a clear action phrase: "Add password reset endpoint", not "Password stuff" or "Auth work" |
| **Description** | Primary source for goal and acceptance criteria extraction | Use the template above. Structure with headers and numbered lists |
| **Acceptance Criteria** | Extracted directly if present as numbered lists, checkboxes, or Given/When/Then blocks. Inferred from prose if missing | Always include explicit criteria — this is the single most impactful field for AI-assisted development |
| **Issue Type** | Determines which downstream skill is recommended (TDD for stories/bugs, refactor for tech debt) | Set accurately — it affects the development workflow suggestion |
| **Priority** | Included in the structured context for the developer | Set to reflect actual business priority |
| **Sprint** | The skill fetches sprint name, goal, and sibling issues to give developers broader context | Assign to a sprint with a meaningful sprint goal |
| **Epic / Parent** | Linked in the context output so the developer sees the bigger picture | Link to the parent epic — it helps the AI understand scope boundaries |
| **Labels** | Included in context output | Use labels consistently (e.g., `api`, `frontend`, `security`) — they help scope the work |
| **Issue Links** | The skill fetches linked issue summaries and link types (blocks, relates to, etc.) | Link related issues — especially blockers and dependencies. The AI uses these to avoid conflicting implementations |
| **Comments** | The skill distills "Key Decisions" from the last 10 comments. Ignores status updates and @mentions without substance | Use comments for **decisions and clarifications** that affect implementation: "We decided to use JWT instead of session tokens because..." Status updates like "Started working on this" are ignored |

### Writing Good Acceptance Criteria

Each criterion should be **independently testable** — a developer (or AI) should be able to write one test per criterion.

| Rule | Bad | Good |
|---|---|---|
| Use verb + observable outcome | "Handle errors" | "Return 400 with JSON error body when request payload is missing required fields" |
| One behavior per criterion | "User can register and log in" | "1. POST /register creates account and returns 201" (separate criterion for login) |
| Include boundary and error cases | (just the happy path) | "Return 404 when user ID does not exist in the database" |
| Specify formats when relevant | "Return the data" | "Return JSON array of user objects, each containing id, name, and email" |
| Avoid implementation details | "Use a Redis cache with 5-minute TTL" | "Response time under 200ms for repeated queries within 5 minutes" |
| Be specific about quantities | "Support pagination" | "Accept `page` and `per_page` query parameters; default to page 1, 20 items per page; return total count in `X-Total-Count` header" |

**Given/When/Then** format also works well and is extracted automatically:

```
Given a registered user with a valid email
When they request a password reset
Then they receive an email with a reset link that expires in 1 hour
```

### Good vs. Bad: Side-by-Side Comparison

**Vague ticket (skill must infer):**

```
Summary: Password stuff
Description: We need to do something about password resets.
             Users are asking for it. John mentioned it would be useful.
Acceptance Criteria: (none)
Comments: "Started working on this" / "Any updates?"
```

What the skill produces — inferred, possibly inaccurate:

```
### Goal
Implement password reset functionality.

### Acceptance Criteria
1. User can request a password reset via email
2. System sends a reset link to the registered email
3. Reset link allows setting a new password
4. Invalid or expired links are handled gracefully
5. User receives confirmation after successful reset
```

These criteria are generic. They miss specifics about token expiration, rate limiting, endpoint contracts, and error responses. The developer has to make assumptions.

---

**Well-structured ticket (skill extracts directly):**

```
Summary: Add password reset endpoint
Description:
  ## Goal
  Implement a password reset flow so users who forget their password
  can securely set a new one via email.

  ## Acceptance Criteria
  1. POST /auth/reset-password accepts email, returns 200 regardless
     of whether the account exists (no user enumeration)
  2. If account exists, generates a reset token with 1-hour expiration
     and sends an email with the reset link
  3. GET /auth/reset-password/:token returns 200 if token is valid,
     400 if expired or invalid
  4. PUT /auth/reset-password/:token accepts new password (min 8 chars),
     updates account, invalidates the token
  5. Rate limit: max 3 reset requests per email per hour

  ## Technical Notes
  - Use existing EmailService for sending (do not add a new mailer)
  - Token format: signed JWT with user ID and expiration
  - See AUTH-410 for rate limiting patterns already in the codebase

  ## Out of Scope
  - SMS-based reset (planned for AUTH-500)
  - Admin-triggered password reset

Comments: "Decided to use JWT tokens instead of random strings so we
           can embed the user ID without a DB lookup — see AUTH-410
           for precedent."
```

What the skill produces — extracted directly, accurate:

```
### Goal
Implement a password reset flow so users can securely set a new password via email.

### Acceptance Criteria
1. POST /auth/reset-password accepts email, returns 200 regardless of whether
   the account exists (no user enumeration)
2. If account exists, generates a reset token with 1-hour expiration and sends
   an email with the reset link
3. GET /auth/reset-password/:token returns 200 if valid, 400 if expired/invalid
4. PUT /auth/reset-password/:token accepts new password (min 8 chars), updates
   account, invalidates the token
5. Rate limit: max 3 reset requests per email per hour

### Key Decisions (from comments)
- Use JWT tokens instead of random strings to embed user ID without DB lookup
  (precedent: AUTH-410)
```

Every criterion is specific, testable, and maps to exactly one test case. The developer (and AI) knows precisely what to build.

### Tips for Comments

The skill extracts a **Key Decisions** section from your JIRA comments. To make this useful:

- **Do comment:** Decisions ("We chose approach A over B because..."), scope clarifications ("This does NOT need to handle X"), edge cases discovered during refinement, links to design docs or RFCs
- **Don't bother commenting for AI context:** Status updates ("Started this today"), @mentions without context ("@john can you look at this?"), automated transition messages

The skill ignores routine comments and only surfaces decisions that would affect implementation.

## Relationship to Other Skills

The skill saves structured task context to `docs/jira/<ISSUE-KEY>.md` — downstream skills auto-detect this file, no copy-paste needed.

| Task complexity | Workflow |
|----------------|----------|
| Simple (1–3 criteria) | `/optimus:jira PROJ-123` → `/optimus:tdd` (auto-detects task file) |
| Medium (4–6 criteria) | `/optimus:jira PROJ-123` → plan mode (jira generates prompt) → `/optimus:tdd` |
| Complex (7+ criteria) | `/optimus:jira PROJ-123` → `/optimus:brainstorm` (auto-detects task file) → plan mode → `/optimus:tdd` |
| Tech debt | `/optimus:jira PROJ-123` → `/optimus:refactor` |

The skill recommends the right path based on acceptance criteria count and task complexity — you don't need to memorize these.

The jira skill only fetches and structures context — it never creates branches, writes code, or modifies your project (except writing the task file to `docs/jira/`).

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
