---
description: Configures Claude Code permissions for safe agent autonomy. Creates settings.json with allow/deny rules and a hook enforcing path restrictions, git branch protection (commit/push blocked on master/main), and precious-file safeguards. Use after /optimus:init to enable autonomous agent workflows, or standalone to lock down a project's permission boundaries.
disable-model-invocation: true
---

# Optimus Permissions

Configure safe permission rules and a path-restriction hook so Claude Code agents can work autonomously inside the project without constant permission prompts, while blocking destructive operations outside the project.

## Security Model

| Operation | Inside Project | Outside Project |
|-----------|---------------|-----------------|
| Read/Search | Allow | Allow |
| Write/Edit | Allow | Ask user |
| Write/Edit precious unversioned file | **Ask user** | Ask user |
| Write/Edit/Delete Claude's own memory store (`~/.claude/projects/.../memory/`) | — | **Allow** |
| Write/Edit/Delete Claude's session scratchpad (`<temp>/claude/.../scratchpad/`) | — | **Allow** |
| Delete (rm/rmdir) | Allow | **BLOCKED** |
| Delete precious unversioned file | **BLOCKED** | **BLOCKED** |
| Git on feature branch | Allow | — |
| Git on protected branch | **BLOCKED** | — |

## Step 1: Detect Existing Configuration

1. Check if `.claude/settings.json` exists. If so, read its full content — it will be preserved during merge.
2. Check if `.claude/hooks/restrict-paths.sh` (or `restrict-paths.*`) already exists. Note whether this is a fresh install or an update — report this to the user in Step 5.
3. Check if `.mcp.json` exists at the project root. If so, extract all MCP server names (top-level keys) for Step 4.

Print a brief detection summary to the user: what exists, what will be created/updated.

## Step 2: Create Directory Structure

```bash
mkdir -p .claude/hooks
```

## Step 3: Install Path-Restriction Hook

If Step 1 detected an existing `.claude/hooks/restrict-paths.sh`, diff it against the template first. If it carries user modifications (e.g., a customized `PROTECTED_BRANCHES` array or extra `is_precious()` patterns), list them and use `AskUserQuestion` — header "Hook edits", question "Your restrict-paths.sh has local modifications: [list]. Installing overwrites the hook with the current template. Re-apply your modifications afterwards?":
- **Re-apply (Recommended)** — "Install the fresh template, then re-apply the listed customizations on top."
- **Discard** — "Install the fresh template as-is; local modifications are dropped."

Copy the hook template to the project (overwrites any existing version):
- Source: `$CLAUDE_PLUGIN_ROOT/skills/permissions/templates/hooks/restrict-paths.sh`
- Destination: `.claude/hooks/restrict-paths.sh`

Copy the file contents exactly — do not modify the template. If the user chose **Re-apply**, apply the listed customizations (and only those) to the installed copy afterwards.

## Step 4: Create or Update settings.json

Use the template from `$CLAUDE_PLUGIN_ROOT/skills/permissions/templates/settings.json` as the base configuration.

### If `.claude/settings.json` does NOT exist

Create it from the template. If `.mcp.json` was found in Step 1, add `mcp__<server-name>` entries to the `permissions.allow` list for each server.

### If `.claude/settings.json` already exists

**Merge** the template into the existing file:

1. **permissions.allow** — add any entries from the template that are not already present. If `.mcp.json` was found, also add `mcp__<server-name>` entries. Never remove existing entries.
2. **permissions.deny** — add any entries from the template that are not already present. Then check for **extra git deny patterns**: collect all deny entries containing the word `git` (as a command, not as part of words like `github`) from both the existing settings and the template. If the existing settings have git deny entries not present in the template, list them and use `AskUserQuestion` — header "Git patterns", question "Your settings have extra git deny patterns that may block feature-branch workflow (commit/push) needed by /optimus:tdd: [list patterns]. Replace with the template's set?":
   - **Replace with template set (Recommended)** — "Remove extra git deny patterns, keep the template's. Branch protection is still enforced by the hook."
   - **Keep all** — "Preserve existing patterns. Skills that need git commit/push may not work."

   If **Replace**: remove all existing git deny entries, add the template's git deny set. Non-git deny entries are untouched. If **Keep all**: no changes.
3. **hooks.PreToolUse** — add the hook entry from the template. If a PreToolUse array already exists, append to it (avoid duplicates if an entry already references `restrict-paths.sh`).
4. **Preserve everything else** — existing `hooks.PostToolUse`, custom sections, and any other configuration must remain untouched.

### Merge principles

- Never remove existing allow/deny entries or hooks — except git deny patterns, which are reconciled with the user when existing patterns go beyond the template (see the permissions.deny merge rule above)
- Never overwrite the file — read, merge, write
- If the existing file is not valid JSON, do not repair or overwrite it silently — show the parse problem and ask the user how to proceed
- The result must be valid JSON

## Step 5: Verify and Report

Run through this checklist. Fix any issues before reporting.

1. `.claude/hooks/restrict-paths.sh` is an exact copy of the template — `diff` it against `$CLAUDE_PLUGIN_ROOT/skills/permissions/templates/hooks/restrict-paths.sh` and check it parses with `bash -n .claude/hooks/restrict-paths.sh`. The only acceptable differences are customizations the user chose to re-apply in Step 3; on any other mismatch, re-copy the template before reporting — a mangled hook fails open at runtime
2. `.claude/settings.json` exists and contains:
   - `permissions.allow` with every allow entry from the template
   - `permissions.deny` with every deny pattern from the template
   - `hooks.PreToolUse` with an entry referencing `restrict-paths.sh`
3. If the file had existing PostToolUse hooks or other content, verify it is preserved
4. Scan for precious unversioned files in the project. Derive the patterns from the `is_precious()` function in the just-installed `.claude/hooks/restrict-paths.sh` (the single source of truth — do not hardcode the list), one `-name` clause per pattern:
   ```bash
   find . -maxdepth 4 \( -name "<pattern-1>" -o -name "<pattern-2>" -o ... \) -not -path "./.git/*" -not -path "*/node_modules/*" -not -path "*/obj/*" -not -path "*/bin/*" 2>/dev/null
   ```
   - If any are found and not git-tracked, report them as protected files
   - If the scan discovers unversioned files that look sensitive but do not match built-in patterns (e.g., custom config files like `config.local.yaml`), ask the user if they want to add custom patterns to the `is_precious()` function in `.claude/hooks/restrict-paths.sh`. **Note:** on a re-run, Step 3 detects such edits and offers to re-apply them after reinstalling the template; to make them permanent, edit the template in the plugin source instead.

**Report to the user:**
- Files created or updated
- Number of tools in the allow list, number of deny patterns
- If MCP servers were detected, list them
- Brief security model reminder: writes outside project will prompt, deletes outside project are blocked, reads are unrestricted
- Memory-store exemption: Claude's per-project auto-memory store (`~/.claude/projects/.../memory/`) is writable and deletable without prompts even though it sits outside the project — see the README ("PreToolUse Hook") for scope and traversal guards
- Session-scratchpad exemption: likewise for the harness-provided session scratchpad (`<temp>/claude/<project>/<session>/scratchpad/`)
- Trust model reminder: commands not on the deny list execute without prompts inside the project — see the README ("Trust Model and Assumptions")
- Git branch protection is active — git commit/push/rebase/reset/merge are blocked on the branches in the installed hook's `PROTECTED_BRANCHES` array; customize that array in `.claude/hooks/restrict-paths.sh` (a re-run offers to re-apply the edit)
- Precious file protection is always active for well-known sensitive unversioned files — the full pattern list is `is_precious()` in the installed hook
- Sandboxing note: defense-in-depth, not OS-level isolation — see the README ("Where This Fits") for sandboxing options
- Auto mode note: the deny list is evaluated before auto mode's classifier and the hook runs in every permission mode; this skill does not configure auto mode — see the README ("Relationship with auto mode")
- Native protected paths note: Claude Code itself still prompts for writes to `.claude/`, `.git/`, `.mcp.json` and similar in every mode except `bypassPermissions` — see the README ("Interaction with Claude Code's native protected paths")

Recommend the next step based on project state:
- If `.claude/CLAUDE.md` does not exist → `/optimus:init` to set up coding guidelines and project structure
- If already initialized → `/optimus:unit-test` to establish test coverage, or `/optimus:tdd` to start developing with test-driven workflow

Tell the user: **Tip:** for best results, start a fresh conversation for the next skill — each skill gathers its own context from scratch.
