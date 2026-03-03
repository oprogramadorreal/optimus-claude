---
description: This skill configures Claude Code permissions for safe agent autonomy. Creates settings.json with allow/deny rules, a path-restriction hook, and precious file protection for non-regenerable gitignored files.
disable-model-invocation: true
---

# Optimus Permissions

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

## Step 1b: Detect Precious Files

Scan for non-regenerable files that are gitignored — these are "precious" because they can't be recovered from git if accidentally modified or deleted.

**Multi-repo workspace detection:** If the current directory has no `.git/` but 2+ child directories with `.git/`, this is a multi-repo workspace. Scan each sub-repo independently.

**For each git repo** (or the single project if not a multi-repo workspace):

1. Parse `.gitignore` to identify ignored patterns
2. Search for existing files that match common precious file patterns:
   - `appsettings.*.json` — .NET local configuration (often contains secrets)
   - `.env`, `.env.*` — environment variables
   - `*.mdf`, `*.ldf` — SQL Server local database files
   - `*.pfx`, `*.key`, `*.pem` — certificates and private keys
   - `credentials.*`, `secrets.*` — credential files
   - `*.sqlite`, `*.db` — local database files (when gitignored)
3. Report any found precious files to the user

**If precious files found:** Use `AskUserQuestion` — header "Precious", question "I found these non-regenerable gitignored files. Which patterns should I protect?":
- **Protect all detected** (Recommended) — "Add all detected patterns to precious file protection"
- **Customize** — "Let me choose which patterns to protect"
- **Skip** — "No precious file protection"

If the user selects **Customize**, present the detected patterns and let the user select by number. Also allow them to add custom patterns.

If the user selects **Skip**, do not set `OPTIMUS_PRECIOUS_PATTERNS`. The hook still provides path restriction and deny list protection.

Store the approved patterns for Step 4 (settings.json configuration).

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

Create it from the template. If `.mcp.json` was found in Step 1, add `mcp__<server-name>` entries to the `permissions.allow` list for each server. If precious patterns were approved in Step 1b, set the `OPTIMUS_PRECIOUS_PATTERNS` env var in the hook command.

### If `.claude/settings.json` already exists

**Merge** the template into the existing file:

1. **permissions.allow** — add any entries from the template that are not already present. If `.mcp.json` was found, also add `mcp__<server-name>` entries. Never remove existing entries.
2. **permissions.deny** — add any entries from the template that are not already present. Never remove existing entries.
3. **hooks.PreToolUse** — add the hook entry from the template. If a PreToolUse array already exists, append to it (avoid duplicates if an entry already references `restrict-paths.sh`). If precious patterns were approved in Step 1b, set the `OPTIMUS_PRECIOUS_PATTERNS` env var in the hook command (see template for format). If a hook entry already references `restrict-paths.sh`, update its `command` to include the env var prefix.
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
   - `permissions.deny` with at least the 27 deny patterns from the template
   - `hooks.PreToolUse` with an entry referencing `restrict-paths.sh`
3. If the file had existing PostToolUse hooks or other content, verify it is preserved

**Report to the user:**
- Files created or updated
- Number of tools in the allow list, number of deny patterns
- If MCP servers were detected, list them
- If precious file patterns were configured, list the patterns and explain they will be protected from accidental modification
- Brief security model reminder: writes outside project will prompt, deletes outside project are blocked, reads are unrestricted
- Trust model reminder: commands not on the deny list will execute without prompts inside the project (database operations, file deletions, network requests, etc.). See the skill's README for the full trust model
- Mention legacy opt-in unversioned file protection: set `OPTIMUS_PROTECT_UNVERSIONED=1` to prompt before modifying ALL unversioned files (broader than precious patterns, more false positives)
