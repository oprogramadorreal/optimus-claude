---
description: Configures Claude Code permissions for safe agent autonomy. Creates settings.json with allow/deny rules and a hook enforcing path restrictions, git branch protection (commit/push blocked on master/main), and precious-file safeguards. Use after /optimus:init to enable autonomous agent workflows, or standalone to lock down a project's permission boundaries.
disable-model-invocation: true
---

# Optimus Permissions

Under Codex, stop without changing files: this skill configures Claude Code only. Recommend configuring Codex's own sandbox and approval policy instead.

Configure permission rules and a path-restriction hook so Claude Code agents can work autonomously inside the project without constant prompts, while destructive operations outside it stay gated.

Read `$CLAUDE_PLUGIN_ROOT/skills/init/references/managed-files.md`. Record installed hashes, template/review refresh eligibility, and only settings entries actually added in `.claude/.optimus-managed.json`; preserve prior records on reruns. A customized hook remains review-only after an approved merge updates its hash. Do not write `.claude/.optimus-version`.

Security model in brief: the installed hook prompts on writes and blocks deletes outside the project (Claude's memory store and session scratchpad are exempt), asks before editing any precious unversioned file and blocks deleting the unrecoverable ones (a backup or IDE scratch file only asks), and blocks history-modifying git operations on protected branches. Inside the project, operations not on the deny list run without prompts.

## Step 1: Detect existing configuration

1. If `.claude/settings.json` exists, read it in full — it will be preserved during the merge.
2. Note whether `.claude/hooks/restrict-paths.sh` already exists (fresh install vs update — report which in Step 4).
3. If `.mcp.json` exists at the project root, extract the top-level MCP server names for Step 3.

## Step 2: Install the path-restriction hook

If an existing `.claude/hooks/restrict-paths.sh` differs from the template, read it and show a concrete comparison; differences may be customizations or older-template drift. For an unrecorded file, ownership is unknown. Use `AskUserQuestion`: **Merge** — install the new template with the listed customizations preserved; **Keep existing** — skip hook replacement and report the remaining version/behavior difference; or **Replace** — discard only the differences explicitly shown. Honor existing authorization for the exact proposed change without asking again.

When creating or replacing as selected, copy `$CLAUDE_PLUGIN_ROOT/skills/permissions/templates/hooks/restrict-paths.sh` to `.claude/hooks/restrict-paths.sh` exactly, then apply only approved customizations. Keep-existing does not authorize a later verification step to overwrite that file.

## Step 3: Create or update settings.json

Base configuration: `$CLAUDE_PLUGIN_ROOT/skills/permissions/templates/settings.json`.

If `.claude/settings.json` does not exist, create it from the template. If it exists, **merge** — read, merge, write, never blind-overwrite:

1. **permissions.allow** — add template entries not already present. Never remove existing entries.
2. **permissions.deny** — add template entries not already present. If the existing settings have git deny entries (git as a command, not part of words like `github`) beyond the template's set, they may block the feature-branch workflow (commit/push) that skills like /optimus:tdd need — list them and use `AskUserQuestion`: **Replace with template set (Recommended)** — remove only the extra git deny entries and use the template's (branch protection is still enforced by the hook); non-git deny entries untouched — or **Keep all**.
3. **hooks.PreToolUse** — add the template's hook entry as a separate matcher group, appending to any existing array; skip if an entry already references `restrict-paths.sh`. Record only a newly appended group, never adopt a preexisting registration as Optimus-owned.
4. **Preserve everything else** — existing PostToolUse hooks, custom sections, all unrelated configuration.

In either case, if `.mcp.json` was found, add `mcp__<server-name>` entries to `permissions.allow` for each server. The result must be valid JSON. If the existing file is not valid JSON, do not repair or overwrite it silently — show the parse problem and ask the user how to proceed.

## Step 4: Verify and report

Fix any issue before reporting:

1. For an installed/replaced hook, `.claude/hooks/restrict-paths.sh` matches the template plus only approved customizations — `diff` against it and run `bash -n` on the installed copy. Correct accidental copy errors; preserve a file the user chose to keep.
2. `.claude/settings.json` has a PreToolUse entry that resolves to the installed `restrict-paths.sh` — a merge that drops or misspells it leaves the project unprotected with no other symptom.
3. Scan for precious unversioned files: derive the patterns from `is_precious_name()` and `is_recoverable_precious_name()` and their backup-suffix rules in the installed hook; do not mistake the `is_precious()` wrapper for the pattern list. Exclude `.git/`, dependencies, build output, and local reset backups. Report untracked matches as protected, distinguishing the intentionally deletable backup/IDE category. Offer specific custom patterns for sensitive files the scan misses.
4. Verify the ownership record's hashes and settings additions against the files written. Existing identical permission rules stay unrecorded; they may predate Optimus.

Report: files created or updated (fresh install vs update), allow/deny counts, detected MCP servers, and the one-line security summary from the top of this skill. Point to this skill's README for the trust model, the auto-mode layering, and the not-OS-sandboxing caveat.

If `.claude/CLAUDE.md` does not exist, recommend `/optimus:init` next; otherwise `/optimus:unit-test` to establish coverage or `/optimus:tdd` to start developing. Suggest a fresh conversation for it.
