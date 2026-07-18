---
description: Configures Claude Code permissions for safe agent autonomy. Creates settings.json with allow/deny rules and a hook enforcing path restrictions, git branch protection (commit/push blocked on master/main), and precious-file safeguards. Use after /optimus:init to enable autonomous agent workflows, or standalone to lock down a project's permission boundaries.
disable-model-invocation: true
---

# Optimus Permissions

Configure permission rules and a path-restriction hook so Claude Code agents can work autonomously inside the project without constant prompts, while destructive operations outside it stay gated.

Security model in brief: the installed hook prompts on writes and blocks deletes outside the project (Claude's memory store and session scratchpad are exempt — writes to an invented temp dir are redirected to the scratchpad instead of prompting), asks before editing and blocks deleting precious unversioned files, and blocks history-modifying git operations on protected branches. Inside the project, operations not on the deny list run without prompts.

## Step 1: Detect existing configuration

1. If `.claude/settings.json` exists, read it in full — it will be preserved during the merge.
2. Note whether `.claude/hooks/restrict-paths.sh` already exists (fresh install vs update — report which in Step 4).
3. If `.mcp.json` exists at the project root, extract the top-level MCP server names for Step 3.

## Step 2: Install the path-restriction hook

If an existing `.claude/hooks/restrict-paths.sh` differs from the template, list the user's modifications (e.g., a customized `PROTECTED_BRANCHES` array or extra `is_precious()` patterns) and use `AskUserQuestion`: **Re-apply (Recommended)** — install the fresh template, then re-apply the listed customizations (and only those) on top — or **Discard** them.

Copy `$CLAUDE_PLUGIN_ROOT/skills/permissions/templates/hooks/restrict-paths.sh` to `.claude/hooks/restrict-paths.sh` (creating the directory if needed), overwriting any existing version. Copy the contents exactly — never modify the template during copy.

## Step 3: Create or update settings.json

Base configuration: `$CLAUDE_PLUGIN_ROOT/skills/permissions/templates/settings.json`.

If `.claude/settings.json` does not exist, create it from the template. If it exists, **merge** — read, merge, write, never blind-overwrite:

1. **permissions.allow** — add template entries not already present. Never remove existing entries.
2. **permissions.deny** — add template entries not already present. If the existing settings have git deny entries (git as a command, not part of words like `github`) beyond the template's set, they may block the feature-branch workflow (commit/push) that skills like /optimus:tdd need — list them and use `AskUserQuestion`: **Replace with template set (Recommended)** — remove only the extra git deny entries and use the template's (branch protection is still enforced by the hook); non-git deny entries untouched — or **Keep all**.
3. **hooks.PreToolUse** — add the template's hook entry, appending to any existing array; skip if an entry already references `restrict-paths.sh`.
4. **Preserve everything else** — existing PostToolUse hooks, custom sections, all unrelated configuration.

In either case, if `.mcp.json` was found, add `mcp__<server-name>` entries to `permissions.allow` for each server. The result must be valid JSON. If the existing file is not valid JSON, do not repair or overwrite it silently — show the parse problem and ask the user how to proceed.

## Step 4: Verify and report

Fix any issue before reporting:

1. `.claude/hooks/restrict-paths.sh` is an exact copy of the template — `diff` against it and run `bash -n` on the installed copy. The only acceptable differences are customizations the user chose to re-apply in Step 2; on any other mismatch, re-copy the template (a mangled hook fails open at runtime).
2. `.claude/settings.json` contains every template allow entry, every template deny pattern, and a PreToolUse entry referencing `restrict-paths.sh`; pre-existing content is preserved.
3. Scan for precious unversioned files: derive the patterns from the `is_precious()` function in the just-installed hook (the single source of truth — never hardcode the list) and run `find . -maxdepth 4` with one `-name` clause per pattern, excluding `.git/`, `node_modules/`, `obj/`, and `bin/`. Report untracked matches as protected. If the scan finds sensitive-looking unversioned files no pattern matches, offer to add custom patterns to `is_precious()` in the installed hook — a re-run detects and offers to re-apply such edits, but permanent patterns belong in the plugin-source template.

Report: files created or updated (fresh install vs update), allow/deny counts, detected MCP servers, and a one-line security summary — writes outside the project prompt, deletes outside are blocked, reads are free; Claude's memory store and session scratchpad are exempt (writes to an invented temp dir are redirected to the scratchpad, not prompted); inside the project, commands off the deny list run unprompted; branch protection (`PROTECTED_BRANCHES`, customizable in the installed hook) and precious-file protection are always on. Point to the README sections "PreToolUse Hook", "Trust Model and Assumptions", "Where This Fits", "Relationship with auto mode", and "Interaction with Claude Code's native protected paths" for details, including the not-OS-sandboxing caveat and auto-mode layering.

If `.claude/CLAUDE.md` does not exist, recommend `/optimus:init` next; otherwise `/optimus:unit-test` to establish coverage or `/optimus:tdd` to start developing. Suggest a fresh conversation for it.
