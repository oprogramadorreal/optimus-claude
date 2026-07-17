# JIRA MCP Setup

Read only when the Detection Procedure in `jira-context-extraction.md` found no JIRA MCP server. Guides first-time setup, then re-runs detection.

## Choose a server

Ask the user (AskUserQuestion) which server to set up:

- **Atlassian Rovo (recommended)** — official, cloud-hosted, OAuth 2.1; JIRA Cloud only (`*.atlassian.net`)
- **mcp-atlassian (community)** — open-source (sooperset); JIRA Cloud AND Server/Data Center; runs locally via uvx or Docker
- **Skip setup** — stop the skill and tell the user to re-run `/optimus:jira` after configuring a server (setup commands are also in this skill's README)

## Atlassian Rovo

```
claude mcp add --transport http --scope user atlassian https://mcp.atlassian.com/v1/mcp
```

- Use `--transport http` (Streamable HTTP) with the `/v1/mcp` endpoint — the older SSE transport (`/v1/sse`) is deprecated by Atlassian and has reconnect issues on Windows. If tools never appear after an apparently successful setup, an SSE registration is the likely cause: remove and re-add with `--transport http`.
- The org admin must enable the server first: `admin.atlassian.com → Apps → AI settings → Rovo MCP server`.
- Auth is OAuth 2.1 — the first JIRA tool use opens a browser consent flow. All actions respect the user's existing JIRA permissions.
- Team-shared config: use `--scope project` to write `.mcp.json` instead. Safe to commit — OAuth tokens are never stored in `.mcp.json`; each teammate completes their own consent flow.

## mcp-atlassian

For JIRA Cloud (API token from https://id.atlassian.com/manage-profile/security/api-tokens):

```
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

For JIRA Server/Data Center: same command with `--jira-url=https://your-jira-server.com` (base URL, include the port if non-standard) and `--jira-personal-token=YOUR_PAT` (Personal Access Token from the JIRA profile page) replacing the username/token args.

- **Token hygiene:** the token lands in shell history — clear the entry afterwards, or hand-write `.mcp.json` with `${JIRA_USERNAME}`/`${JIRA_API_TOKEN}` environment-variable placeholders so no real token is ever committed.
- Docker alternative: `"command": "docker"`, `"args": ["run", "-i", "--rm", "-e", "JIRA_URL=...", "-e", "JIRA_USERNAME=...", "-e", "JIRA_API_TOKEN=...", "ghcr.io/sooperset/mcp-atlassian:latest"]` (use `JIRA_PERSONAL_TOKEN` for Server/DC).

## Verify

When the user reports setup complete, run the Detection Procedure again. If tools are still missing, suggest restarting Claude Code (MCP servers may need a fresh session) and checking `claude mcp list`; troubleshoot from the actual error output. If the user gives up or skips, stop the skill.
