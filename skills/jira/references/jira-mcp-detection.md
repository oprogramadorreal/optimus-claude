# JIRA MCP Server Detection & Guided Setup

Shared detection and setup procedure for JIRA MCP integration. Called by the jira skill to locate a configured JIRA MCP server or guide the user through first-time setup.

## Detection Procedure

### 1. Check `.mcp.json`

Read `.mcp.json` at the project root. If it exists, scan top-level keys for JIRA-related server entries:

- `atlassian` — Atlassian Rovo MCP Server (official)
- `mcp-atlassian` — sooperset/mcp-atlassian (community)
- `jira` — generic JIRA MCP server
- Any key containing `jira` or `atlassian` (case-insensitive)

If a matching key is found, record it as `jira-server-name` and proceed to step 2 to verify tools are available.

### 2. Probe for Available Tools

Use `ToolSearch` with these queries (try in order, stop at first match):

1. Query `jira` — look for tools containing `jira_search` or `jira_get_issue`
2. Query `atlassian` — look for tools containing `jira_`

**Known tool patterns by server:**

| Server | Tool prefix | Example tools |
|--------|-------------|---------------|
| Atlassian Rovo | `mcp__atlassian__` | `jira_search`, `jira_create_issue`, `jira_update_issue` |
| sooperset/mcp-atlassian | `mcp__mcp-atlassian__` | `jira_search`, `jira_get_issue`, `jira_update_issue`, `jira_transition_issue`, `jira_get_sprints_from_board` |
| Generic | `mcp__jira__` | Varies by implementation |

### 3. Report Result

**If tools found:** Record the server name and tool prefix. Report to the user:

```
## JIRA MCP Server

Detected: [server name] ([tool count] JIRA tools available)
```

Return success — the consuming skill can proceed.

**If no tools found:** Enter the guided setup procedure below.

---

## Guided Setup Procedure

When no JIRA MCP server is detected, guide the user through setup interactively.

### Step A: Choose Server Type

Use `AskUserQuestion` — header "JIRA server", question "No JIRA MCP server detected. Which would you like to set up?":
- **Atlassian Rovo (Recommended)** — "Official Atlassian MCP server. Cloud-hosted, supports Jira Cloud + Confluence. Requires Atlassian Cloud site (*.atlassian.net)."
- **mcp-atlassian (Community)** — "Open-source server by sooperset. Supports Jira Cloud AND Server/Data Center. Runs locally via Docker or uvx."
- **Skip setup** — "I'll configure a JIRA MCP server later."

If "Skip setup" → stop and inform the user: "Run `/optimus:jira` again after configuring a JIRA MCP server. See the skill's README for setup instructions."

### Step B (Rovo): Atlassian Rovo MCP Server Setup

Present these instructions to the user:

```
## Atlassian Rovo MCP Server Setup

### Prerequisites
- Atlassian Cloud site (*.atlassian.net) with Jira and/or Confluence
- Node.js v18+ installed (needed for the local MCP proxy)
- Your organization admin must have Rovo MCP Server enabled

### 1. Admin Setup (if not already done)
Ask your Atlassian org admin to:
1. Go to admin.atlassian.com → select your organization
2. Navigate to Apps → AI settings → Rovo MCP server
3. Enable the MCP server
4. (Optional) Enable API token authentication for headless/CLI use
   (Authentication section → turn "API token" ON)
5. (Optional) If your org uses IP allowlisting, add your AI tool's
   outbound IP ranges to the allowlist (Security → IP allowlists)

Note: The first user to complete the OAuth consent flow for your site
must have access to the Atlassian apps requested by the MCP scopes.
All actions respect the user's existing Jira/Confluence permissions.

### 2. Register with Claude Code

Run this command in your terminal:

    claude mcp add --transport sse atlassian https://mcp.atlassian.com/v1/mcp

> Important: The older /v1/sse endpoint is deprecated and will stop
> working after June 30, 2026. Always use the /v1/mcp endpoint.

### 3. Authenticate
1. Restart Claude Code (or start a new session)
2. The first time you use a JIRA tool, a browser window will open
3. Complete the OAuth 2.1 consent flow with your Atlassian account
4. Return to Claude Code — you're connected

### Alternative: API Token Authentication (for CLI/headless workflows)
If your admin enabled API token auth:
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token", name it (e.g., "Claude Code MCP")
3. Set expiration (1–365 days)
4. Copy the token immediately — you can't retrieve it later
5. Encode credentials:
       echo -n "your-email@company.com:your-api-token" | base64
6. Use the encoded token in your MCP configuration

### 4. Verify
Run: claude mcp list
You should see "atlassian" in the server list.
```

After presenting instructions, use `AskUserQuestion` — header "Setup status", question "Have you completed the Rovo MCP server setup?":
- **Done — verify connection** — "I've run the command and authenticated"
- **Need help** — "I ran into an issue"
- **Skip for now** — "I'll set it up later"

**If "Done":** Run the detection procedure again (steps 1–2 above). If tools are found → return success. If not → suggest: "Try restarting Claude Code (`/exit` and relaunch) then run `/optimus:jira` again. The MCP server may need a fresh session to initialize."

**If "Need help":** Use `AskUserQuestion` — header "Troubleshoot", question "What issue did you encounter?":
- **Server not listed** — "`claude mcp list` doesn't show 'atlassian'"
- **Auth failed** — "OAuth flow didn't open or failed in the browser"
- **Permission denied** — "Connected but JIRA tools return permission errors"
- **Admin hasn't enabled it** — "I need to ask my admin first"

Troubleshooting guidance:
- **Server not listed**: Verify the command was `claude mcp add --transport sse atlassian https://mcp.atlassian.com/v1/mcp`. Check for typos. Try `claude mcp remove atlassian` then re-add.
- **Auth failed**: Ensure Node.js v18+ is installed (`node --version`). Try a different browser. Clear browser cookies for `atlassian.com`. Ensure your Atlassian account has access to the site's Jira/Confluence.
- **Permission denied**: Your Atlassian account may lack project-level access. Check with your Jira admin that you have the necessary project roles.
- **Admin hasn't enabled it**: The user needs their org admin to enable the MCP server at `admin.atlassian.com → Apps → AI settings → Rovo MCP server`. Suggest the user share the setup instructions above with their admin.

**If "Skip for now":** Stop and inform: "Run `/optimus:jira` again after setup is complete."

### Step B (Community): sooperset/mcp-atlassian Setup

First, determine the deployment type. Use `AskUserQuestion` — header "Deployment", question "Is your Jira instance Cloud or Server/Data Center?":
- **Jira Cloud** — "Hosted at *.atlassian.net"
- **Server / Data Center** — "Self-hosted Jira instance"

Then present instructions (adapt token creation and args based on the user's choice):

```
## mcp-atlassian Setup (Community Server)

### Prerequisites
- Docker installed (recommended), OR Python 3.10+ with uv/pip
- Your Jira instance URL
- API token (Cloud) or Personal Access Token (Server/Data Center)

### 1. Create API Token

**For Jira Cloud:**
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Name it (e.g., "mcp-atlassian"), set expiration (max 365 days)
4. Copy the token immediately — you can't retrieve it later
5. Save it in a password manager

**For Jira Server/Data Center:**
1. Log in to your Jira instance
2. Go to Profile → Personal Access Tokens
3. Create a new token with appropriate permissions
4. Copy and save it securely

### 2. Register with Claude Code

**Option A — Using uvx (quickest):**

For Cloud:

    claude mcp add-json mcp-atlassian '{
      "command": "uvx",
      "args": [
        "mcp-atlassian",
        "--jira-url=https://YOUR-COMPANY.atlassian.net",
        "--jira-username=your.email@company.com",
        "--jira-token=YOUR_API_TOKEN"
      ]
    }'

For Server/Data Center:

    claude mcp add-json mcp-atlassian '{
      "command": "uvx",
      "args": [
        "mcp-atlassian",
        "--jira-url=https://your-jira-server.com",
        "--jira-personal-token=YOUR_PERSONAL_ACCESS_TOKEN"
      ]
    }'

**Option B — Using Docker (recommended for stability):**

    docker pull ghcr.io/sooperset/mcp-atlassian:latest

For Cloud:

    claude mcp add-json mcp-atlassian '{
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "JIRA_URL=https://YOUR-COMPANY.atlassian.net",
        "-e", "JIRA_USERNAME=your.email@company.com",
        "-e", "JIRA_API_TOKEN=YOUR_API_TOKEN",
        "ghcr.io/sooperset/mcp-atlassian:latest"
      ]
    }'

For Server/Data Center:

    claude mcp add-json mcp-atlassian '{
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "JIRA_URL=https://your-jira-server.com",
        "-e", "JIRA_PERSONAL_TOKEN=YOUR_PERSONAL_ACCESS_TOKEN",
        "ghcr.io/sooperset/mcp-atlassian:latest"
      ]
    }'

### 3. Verify
Restart Claude Code, then run: claude mcp list
You should see "mcp-atlassian" in the server list.

### Optional: Project-scoped config (.mcp.json)
To share the config with your team (without tokens), create .mcp.json
at the project root:

    {
      "mcpServers": {
        "mcp-atlassian": {
          "command": "uvx",
          "args": [
            "mcp-atlassian",
            "--jira-url=https://YOUR-COMPANY.atlassian.net",
            "--jira-username=${JIRA_USERNAME}",
            "--jira-token=${JIRA_API_TOKEN}"
          ]
        }
      }
    }

Team members set JIRA_USERNAME and JIRA_API_TOKEN as environment
variables. Add .mcp.json to version control but NEVER commit tokens.
```

After presenting instructions, use `AskUserQuestion` — header "Setup status", question "Have you completed the mcp-atlassian setup?":
- **Done — verify connection** — "I've configured the server"
- **Need help** — "I ran into an issue"
- **Skip for now** — "I'll set it up later"

**If "Done":** Run the detection procedure again (steps 1–2). If tools found → return success. If not → suggest restarting Claude Code.

**If "Need help":** Use `AskUserQuestion` — header "Troubleshoot", question "What issue did you encounter?":
- **Docker not running** — "Docker command failed or image not found"
- **Auth error** — "Connection refused or 401 Unauthorized"
- **uvx not found** — "Command 'uvx' not recognized"
- **URL issue** — "Connection timeout or hostname error"

Troubleshooting guidance:
- **Docker not running**: Ensure Docker Desktop is running. Verify with `docker info`. If not installed, try the uvx option instead.
- **Auth error**: For Cloud — verify your API token at `id.atlassian.com/manage-profile/security/api-tokens`. Tokens expire — check the expiration date. Ensure `JIRA_USERNAME` is your email address, not your display name. For Server — verify the PAT has not expired and has sufficient permissions.
- **uvx not found**: Install uv first: `curl -LsSf https://astral.sh/uv/install.sh | sh` (Linux/macOS) or `brew install uv` (macOS with Homebrew). Then retry the command.
- **URL issue**: For Cloud, use `https://COMPANY.atlassian.net` (not `https://COMPANY.atlassian.net/jira`). For Server, use the base URL including port if needed (e.g., `https://jira.company.com:8443`). Verify the URL is accessible from your machine with `curl -I YOUR_JIRA_URL`.

**If "Skip for now":** Stop and inform: "Run `/optimus:jira` again after setup is complete."
