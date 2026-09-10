---
description: Removes selected Optimus project artifacts, or only the permissions setup with the permissions argument. Reviews ownership, current content, and Git recoverability; preserves ambiguous user content and backs up selected changes when needed. Requires a concrete deletion selection. Tests are never touched. Monorepo and multi-repo aware.
disable-model-invocation: true
argument-hint: "[permissions]"
---

# Reset — Remove optimus-generated files

Remove selected project artifacts, not the plugin installation itself.

## Scope

Parse `$ARGUMENTS` before inventorying: empty → the existing full inventory; `permissions` → only the permissions setup. Any other argument → show usage `/optimus:reset [permissions]` and stop without changes. Keep every later selection, edit, and cleanup within the chosen scope.

The `permissions` scope removes Claude Code configuration from either host; it does not configure Codex permissions. It removes additions, without restoring previously replaced hook contents or git deny rules removed during setup: the ownership record contains no such history.

## Safety Rules

- Never touch tests, test directories, or test configuration, even if Optimus created them.
- Stay within `.claude/`, subproject `CLAUDE.md`/`docs/`, workspace-root `CLAUDE.md`, and marked `optimus:pointer` blocks in root `AGENTS.md`. Resolve every target inside the intended root; do not follow symlinks outside it.
- `.claude/settings.json` is merged surgically. Filename, matching permission values, Git tracking, and template-like headings do not prove ownership or current-byte recoverability.
- Preserve `.claude/.optimus-reset-backups/` from this and earlier runs; never include it in the removal inventory.

## Step 1 — Detect and inventory

If `git rev-parse --is-inside-work-tree` returns `true`, resolve `git rev-parse --show-toplevel` (including linked worktrees). Otherwise apply `$CLAUDE_PLUGIN_ROOT/skills/init/references/multi-repo-detection.md`. Process each selected child repo independently; include workspace-root context files only when applicable.

Read `$CLAUDE_PLUGIN_ROOT/skills/init/references/managed-files.md` and any `.claude/.optimus-managed.json`.

**`permissions` scope:** inventory only `.claude/hooks/restrict-paths.sh`, its `hooks.PreToolUse` registrations, and recorded `permissions.allow` / `permissions.deny` additions (including recorded MCP allowances). Include their ownership entries even when the hook or settings additions are already missing. Shared settings and ownership files are entry-edit targets, not whole-file candidates. Preserve unrelated hook commands in shared matcher groups. Unrecorded permission rules stay unless the user identifies the exact entries for review; template equality or current MCP names never establish ownership. Do not inventory init's docs, formatters, pointers, or `.optimus-version`.

**Full scope only:** inventory existing candidates:

- `.claude/CLAUDE.md`, `.claude/.optimus-version`, `.claude/settings.json`, and the ownership record.
- `.claude/docs/{coding-guidelines,testing,styling,architecture,skill-writing-guidelines}.md`.
- `.claude/hooks/format-*`, including retired `format-python.py` and `format-node.js`, and `.claude/hooks/restrict-paths.sh`.
- Legacy `.claude/agents/{code-simplifier,test-guardian}.md`.
- Root `AGENTS.md` only when it contains a well-formed `optimus:pointer` block.
- Monorepo: applicable subproject `CLAUDE.md` and `docs/{coding-guidelines,testing,styling,architecture}.md`.
- Multi-repo: the above per child repo, plus workspace-root `CLAUDE.md` and pointer block.

No in-scope candidates, including stale ownership entries → report nothing to reset and stop, even if init artifacts or unrelated settings remain. Missing provenance means an older or unrelated installation, not permission to delete every candidate.

## Step 2 — Classify content and recoverability

Show two independent dimensions for each candidate:

| Content / ownership | Meaning |
|---|---|
| `UNMODIFIED` | Current SHA-256 matches a valid recorded file entry's `sha256`. Show whether that baseline is a template or an approved customization (`refresh: "review"`). |
| `MODIFIED` | Recorded file differs from its entry's `sha256`. Read it before proposing removal. |
| `UNKNOWN` | No usable record; may be legacy Optimus content or independently authored. |
| `COMPLEX` | Shared settings.json, AGENTS.md, or ownership record; propose exact entry/block edits. |

For UNKNOWN legacy files, compare against current templates to inform the plan. An existing user file stays UNKNOWN after ordinary init edits; only explicit whole-file adoption/replacement establishes ownership. Verbatim hook equality or coding-guide equality apart from the project heading is useful evidence, but do not promote unknown ownership to recorded ownership. Generated-document headings and identity comments can suggest `LIKELY_GENERATED`; this is an annotation under UNKNOWN, not proof that the prose is unchanged. Retired hooks remain UNKNOWN unless provenance establishes them; their names alone do not authorize deletion.

Check HEAD, index, and working tree separately: use Git status/diffs for each path, and verify whether its current bytes equal a version in HEAD or the index. Report **clean recorded version**, **staged changes**, **unstaged changes**, or **untracked**. A tracked file with new edits is not wholly recoverable through checkout. Git errors mean recovery is unverified. Do not stage, restore, reset, or commit files during this check.

Read shared settings and show every proposed removal. Recorded additions may be removed only if they still exactly match; changed/unrecorded rules and groups stay unless the user explicitly selects those particular entries. Existing MCP names and today's permission template do not establish who added a rule. Retained hook files keep their registrations.

## Step 3 — Present a concrete deletion plan

List the chosen scope, file paths, ownership/content class, Git state, and exact settings/pointer edits, grouped by repo. Include proposed removal of stale in-scope ownership entries after verifying the corresponding file/setting is absent. Explain that legacy template drift and user edits cannot always be distinguished. Name selected content needing a local backup, since Git cannot recover those current bytes.

AskUserQuestion — header "Reset", question "Which parts of this reset plan should be applied?":

1. **Unmodified only (Recommended)** — remove recorded unchanged files and their unchanged recorded settings additions; keep MODIFIED and UNKNOWN content.
2. **Select files and entries** — identify exact candidates to remove, including any legacy files or shared settings entries.
3. **Remove all listed candidates** — explicitly includes modified/unknown files and only the settings edits shown in the plan; preserve backups and unrelated settings.
4. **Abort** — change nothing.

Existing explicit authorization for this exact displayed plan is sufficient. Do not infer approval to remove ambiguous settings from a general "Unmodified only" selection.

## Step 4 — Preserve current bytes and execute

Before changing a selected file whose current bytes are not verified recoverable from HEAD/index (including shared files about to be edited), make a byte-for-byte backup. Use a new timestamped directory under `.claude/.optimus-reset-backups/`, with original relative paths and an index of source paths. Create its local `.gitignore` containing `*` **before** copying. Inside a Git working tree, verify each backup path is untracked and ignored with Git. For a confirmed non-Git workspace root, verify the backup stays outside every child repository; the local ignore file also protects it if that workspace later becomes a repository. Never put secrets into a tracked backup or stage the backups. If repository status is uncertain, ignore/path verification fails, or copying fails, keep the affected originals and report the limitation instead of deleting them. Explain where local backups remain and that they may contain private settings; do not print their contents.

Compare each backup's hash to its original before proceeding. Recheck the original's hash immediately before deletion; if it changed since the approved plan, preserve it and obtain an updated selection. Clean recorded files do not need redundant backups.

1. Delete only the selected files whose recovery/backup checks passed. Do not recursively remove directories.
2. Apply only the settings edits shown and selected. Remove a recorded hook matcher group only when it still exactly matches and its referenced Optimus hook was deleted or already missing. Preserve groups containing retained hooks and all unrecorded/changed groups unless separately selected. Remove exact recorded permission additions only; never infer ownership from `.mcp.json`. Prune containers that became empty through these removals, preserving preexisting empty/custom sections; delete settings.json only when the approved edit leaves no content.
3. For selected root AGENTS.md pointers, remove only the complete marked block. Preserve every surrounding byte; delete the file only if it consisted entirely of that block. Malformed/multiple ambiguous markers need a concrete reviewed edit, not a broad regex deletion.
4. Update the ownership record to remove only completed removals and selected in-scope entries whose file/setting is verified absent; retain entries for kept files/settings. Remove the record only when empty and selected. In `permissions` scope, always preserve `.optimus-version` and init's records. In full scope, keep `.optimus-version` if the selected reset left managed artifacts in place; report that a later init is still needed to reconcile them.

## Step 5 — Clean up and report

Remove only managed directories made empty by this run, within the checked roots and chosen scope. Preserve backup directories and all unrelated files.

Report removed/kept paths with reasons, settings changes, and any backup/recovery locations. Explicitly note retained hook registrations and unresolved legacy ownership. A partial reset is reported as partial, not successful removal of everything.

After a permissions-only reset, report any retained init setup; if reinstalling, use `/optimus:permissions` in a fresh Claude Code conversation. Stop without recommending init or plugin uninstallation for this scope.

After a full-scope reset, recommend reinstalling in a fresh conversation using the current host: Claude Code → `/optimus:init` (plus `/optimus:permissions`); Codex → `$optimus:init` only, since permissions is Claude-only. To uninstall the plugin itself, give the host's command: Claude Code → `/plugin uninstall optimus@optimus-claude`; Codex CLI → `codex plugin remove optimus@optimus-claude` in the terminal. Do not execute plugin uninstallation as part of reset.
