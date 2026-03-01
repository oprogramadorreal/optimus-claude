---
description: Configure Claude Code permissions for safe agent autonomy. Creates settings.json with allow/deny rules and a path-restriction hook.
disable-model-invocation: true
---

# Prime Permissions

Configure safe permission rules and a path-restriction hook so Claude Code agents can work autonomously inside the project without constant permission prompts, while blocking destructive operations outside the project.

## Security Model

| Operation | Inside Project | Outside Project |
|-----------|---------------|-----------------|
| Read/Search | Allow | Allow |
| Write/Edit | Allow | Ask user |
| Delete (rm/rmdir) | Allow | **BLOCKED** |

## Step 1: Detect Existing Configuration

1. Check if `.claude/settings.json` exists. If so, read its full content — it will be preserved during merge.
2. Check if `.claude/hooks/restrict-paths.sh` (or `restrict-paths.*`) already exists. If so, skip hook installation in Step 3.
3. Check if `.mcp.json` exists at the project root. If so, extract all MCP server names (top-level keys) for Step 4.

Print a brief detection summary to the user: what exists, what will be created/updated.

## Step 2: Create Directory Structure

```bash
mkdir -p .claude/hooks
```

## Step 3: Install Path-Restriction Hook

**Skip** if `.claude/hooks/restrict-paths.*` already exists.

Copy the hook template to the project:
- Source: `$CLAUDE_PLUGIN_ROOT/skills/permissions/templates/hooks/restrict-paths.sh`
- Destination: `.claude/hooks/restrict-paths.sh`

Copy the file contents exactly — do not modify the template.

## Step 4: Create or Update settings.json

Use the template from `$CLAUDE_PLUGIN_ROOT/skills/permissions/templates/settings.json` as the base configuration.

### If `.claude/settings.json` does NOT exist

Create it from the template. If `.mcp.json` was found in Step 1, add `mcp__<server-name>` entries to the `permissions.allow` list for each server.

### If `.claude/settings.json` already exists

**Merge** the template into the existing file:

1. **permissions.allow** — add any entries from the template that are not already present. If `.mcp.json` was found, also add `mcp__<server-name>` entries. Never remove existing entries.
2. **permissions.deny** — add any entries from the template that are not already present. Never remove existing entries.
3. **hooks.PreToolUse** — add the hook entry from the template. If a PreToolUse array already exists, append to it (avoid duplicates if an entry already references `restrict-paths.sh`).
4. **Preserve everything else** — existing `hooks.PostToolUse`, custom sections, and any other configuration must remain untouched.

### Merge principles

- Never remove existing allow/deny entries or hooks
- Never overwrite the file — read, merge, write
- The result must be valid JSON

## Step 5: Verify and Report

Run through this checklist. Fix any issues before reporting.

1. `.claude/hooks/restrict-paths.sh` exists and contains the hook logic
2. `.claude/settings.json` exists and contains:
   - `permissions.allow` with at least the 13 tool entries from the template
   - `permissions.deny` with at least the 18 deny patterns from the template
   - `hooks.PreToolUse` with an entry referencing `restrict-paths.sh`
3. If the file had existing PostToolUse hooks or other content, verify it is preserved

**Report to the user:**
- Files created or updated
- Number of tools in the allow list, number of deny patterns
- If MCP servers were detected, list them
- Brief security model reminder: writes outside project will prompt, deletes outside project are blocked, reads are unrestricted
