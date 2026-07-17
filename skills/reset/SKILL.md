---
description: Removes files installed by /optimus:init and /optimus:permissions from the project. Compares each file against plugin templates and classifies as unmodified, likely generated, or user-modified. Always asks before deleting. Git-tracked files are noted as recoverable. Tests are never touched. Monorepo and multi-repo aware. Use for clean reinstall or to stop using optimus.
disable-model-invocation: true
---

# Reset — Remove optimus-generated files

Remove files installed by `/optimus:init` and `/optimus:permissions`. Does NOT uninstall the plugin itself — it only removes files from the project.

## Safety Rules

These rules are absolute and override all other instructions:

- **NEVER** touch test files, test directories, or test configuration — even if created by `/optimus:unit-test`
- **NEVER** touch files outside `.claude/`, subproject `CLAUDE.md`, subproject `docs/`, and workspace-root `CLAUDE.md`
- **NEVER** delete a user-modified file without the user's explicit approval, and **NEVER** delete `.claude/settings.json` outright — surgically remove optimus entries, preserving user content (Step 4)
- **ALWAYS** classify every file first, present the categorized list, and get confirmation via AskUserQuestion before removing anything

## Step 1 — Detect and inventory

If the current directory has no `.git/` directory, read `$CLAUDE_PLUGIN_ROOT/skills/init/references/multi-repo-detection.md` and apply it; in a multi-repo workspace, process each child repo independently and also check for a workspace-root `CLAUDE.md` (local-only). Otherwise it is a single repo — possibly a monorepo whose subprojects have their own init-installed `CLAUDE.md` and `docs/` files.

Inventory optimus-managed files, listing only what exists:

- `.claude/CLAUDE.md`, `.claude/.optimus-version`, `.claude/settings.json`
- `.claude/docs/{coding-guidelines,testing,styling,architecture,skill-writing-guidelines}.md`
- `.claude/hooks/format-*` — the plugin's template hooks plus any custom `format-<language>.sh` from init's unsupported-stack fallback
- `.claude/hooks/restrict-paths.sh`
- `.claude/agents/{code-simplifier,test-guardian}.md` (legacy — installed by older optimus versions)
- Monorepo: subproject `CLAUDE.md` and `docs/{coding-guidelines,testing,styling,architecture}.md` (subproject `coding-guidelines.md` exists only when init found the subproject's conventions differ from root — classify it via the near-exact-pair rule below)
- Multi-repo: the above per child repo, plus the workspace-root `CLAUDE.md`

If no optimus files are found anywhere → say "Nothing to reset — no optimus files found" and stop. If `.claude/.optimus-version` is missing, warn that the project may not have been initialized by optimus, but proceed.

## Step 2 — Classify each file

For each file, check git tracking with `git ls-files --error-unmatch <file>` (tracked → recoverable via `git checkout`).

Classify with shell comparison — do not read file bodies into context:

**Verbatim templates.** The template is the same-named file in the plugin: `format-*` hooks → `$CLAUDE_PLUGIN_ROOT/skills/init/templates/hooks/`, `restrict-paths.sh` → `$CLAUDE_PLUGIN_ROOT/skills/permissions/templates/hooks/`, legacy `.claude/agents/*.md` → `$CLAUDE_PLUGIN_ROOT/agents/`. Run `cmp -s <file> <template>`: identical → `UNMODIFIED`, else `MODIFIED`. A custom `format-<language>.sh` with no same-named template is `LIKELY_GENERATED` if it follows the shell-hook pattern (shebang, JSON stdin parsed into a file-path variable, file-extension guard, formatter invocation), else `MODIFIED`.

**Near-exact pair** — `docs/coding-guidelines.md` and `docs/skill-writing-guidelines.md`: line 1 carries init's `[PROJECT NAME]` substitution; the rest is verbatim from the same-named file under `$CLAUDE_PLUGIN_ROOT/skills/init/templates/docs/`. Run `tail -n +2 <file> | diff -q - <(tail -n +2 <template>)`: identical → `UNMODIFIED`, else `MODIFIED`.

**Generated docs** — content is filled in by init, so compare structure against the plugin's own templates at runtime (all under `$CLAUDE_PLUGIN_ROOT/skills/init/templates/`):

- CLAUDE.md files: compare line 1 (`head -n 1`) against the template's line-1 HTML comment. Root `.claude/CLAUDE.md` matches `single-project-claude.md` or `monorepo-claude.md`; subproject `CLAUDE.md` → `subproject-claude.md`; workspace-root `CLAUDE.md` → `multi-repo-claude.md`.
- `docs/testing.md`, `docs/styling.md`, `docs/architecture.md`: compare `##` headings against the same-named template under `templates/docs/`. For testing.md and styling.md the headings must match in order: `diff <(grep '^## ' <file>) <(grep '^## ' <template>)`. For architecture.md, init deletes the template's HTML-comment-marked conditional sections per project type, so require only that the file's `##` headings are an in-order subset of the template's headings.

Structure matches → `LIKELY_GENERATED`; otherwise → `MODIFIED`.

**Always:** `.claude/.optimus-version` → `UNMODIFIED` (pure tracking file). `.claude/settings.json` → `COMPLEX` (surgical handling in Step 4).

Summary: `UNMODIFIED` (exact template match), `LIKELY_GENERATED` (optimus structure, init-filled content), `MODIFIED` (user edits — or template drift from an older plugin version), `COMPLEX` (settings.json).

## Step 3 — Present plan and confirm

Show the file list grouped by classification (multi-repo: grouped by repo), each with its git-tracked status ("recoverable via `git checkout`"). If `.optimus-version` records an older plugin version, note it: MODIFIED files may reflect template drift since that install rather than user edits.

Then AskUserQuestion — header "Reset", question "Review the files above. Which should be removed?". Mark "Remove all" as "(Recommended)" only when every MODIFIED file is git-tracked; otherwise recommend "Keep modified" and name the untracked MODIFIED files in its option text:

1. "Remove all" — all optimus files; irreversible for untracked MODIFIED files
2. "Keep modified" — remove UNMODIFIED + LIKELY_GENERATED, keep MODIFIED
3. "Unmodified only" — most conservative
4. "Abort" — remove nothing

On Abort: confirm nothing was removed and stop.

## Step 4 — Execute

1. Delete the selected files. Monorepo: include selected subproject files; multi-repo: process each repo, plus the workspace-root `CLAUDE.md` if selected.
2. Clean `.claude/settings.json` surgically — for every non-Abort choice, since it preserves user content by construction. Read the project's settings.json and both templates (`$CLAUDE_PLUGIN_ROOT/skills/init/templates/settings.json`, `$CLAUDE_PLUGIN_ROOT/skills/permissions/templates/settings.json`), then:
   - `hooks.PostToolUse`: remove entries whose commands reference `.claude/hooks/format-` — but only if the referenced hook file was deleted or is missing. If the user kept a hook file, keep its entry: removing it would silently disable a hook the user elected to preserve.
   - `hooks.PreToolUse`: same rule for entries referencing `.claude/hooks/restrict-paths.sh`.
   - `permissions.allow` / `permissions.deny`: remove entries matching the permissions template's lists. Also remove server-level entries of the exact form `mcp__<server-name>` only for servers declared in the relevant project root's `.mcp.json` (per child repo in multi-repo workspaces). Preserve tool-level entries (e.g. `mcp__github__get_issue`) and entries for undeclared servers — those are the user's. If no `.mcp.json` exists, leave all `mcp__*` entries untouched.
   - Prune arrays, keys, and objects that became empty. If the whole object is now `{}`, delete the file; otherwise write it back with 2-space indentation.

## Step 5 — Clean up and report

Remove now-empty directories: `.claude/hooks`, `.claude/agents`, `.claude/docs`, and `.claude/` itself only if completely empty — per repo in multi-repo workspaces, plus subproject `docs/` in monorepos.

Report files removed, files kept (with reason), settings.json changes, and directories cleaned. If a kept hook file retained its settings entry, say so explicitly — that hook stays active.

Recommend the next step in a fresh conversation: `/optimus:init` (plus `/optimus:permissions`) to reinstall, or `/plugin uninstall optimus@optimus-claude` (a Claude Code command) to remove the plugin itself.
