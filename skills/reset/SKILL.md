---
description: Uninstalls optimus-installed files from a project — inventories everything /optimus:init can install (CLAUDE.md files, guideline docs, formatter and guardrail hooks, settings.json entries, version marker, harness state), classifies each file against plugin templates as unmodified, likely generated, or user-modified, and deletes only what the user approves. User-modified files need explicit per-file approval, settings.json is cleaned surgically, and tests and approved specs are never touched. Monorepo and multi-repo aware. Deletes project files but does not uninstall the plugin itself. Use for a clean reinstall or to stop using optimus in a project.
disable-model-invocation: true
---

# Reset — remove optimus-installed files

Remove everything `/optimus:init` installed in the project. This does not uninstall
the plugin itself — that is `/plugin uninstall optimus@optimus-claude`, run afterwards
if the user wants optimus gone entirely.

## Safety rules

These are absolute and override everything else:

- **Never** touch test files, test directories, or test configuration — even tests
  written by `/optimus:unit-test`.
- **Never** touch `docs/specs/` or `docs/product/` — approved specs and product docs
  are user content. Leave them in place and say so in the final summary.
- **Never** delete or replace `.claude/settings.json` wholesale — surgical cleanup
  only (Step 5).
- **Never** delete anything before showing the classified inventory and getting the
  user's confirmation. User-modified files additionally require explicit per-file
  approval — a bulk "remove everything" answer never covers them.

## Step 1 — Detect context and inventory

Read `$CLAUDE_PLUGIN_ROOT/skills/init/references/multi-repo-detection.md` and
determine whether this is a single project, a monorepo, or a multi-repo workspace.
For multi-repo workspaces, run the whole reset per child repo (plus the
workspace-root `CLAUDE.md`); for monorepos, include subproject paths.

If no optimus files exist, tell the user there is nothing to reset and stop. If
files exist but `.claude/.optimus-version` is missing, warn that the project may not
have been initialized by optimus and proceed with classification anyway.

This is everything init can install — inventory only the files that actually exist:

- `.claude/CLAUDE.md`; the workspace-root `CLAUDE.md` in multi-repo workspaces;
  subproject `CLAUDE.md` files in monorepos
- `.claude/docs/`: `coding-guidelines.md`, `testing.md`, `styling.md`,
  `architecture.md`, `skill-writing-guidelines.md`; in monorepos, subproject `docs/`
  copies of testing/styling/architecture and per-subproject `coding-guidelines.md`
- `.claude/hooks/`: formatter hooks (`format-python.py`, `format-node.js`,
  `format-<language>.sh` — both plugin templates and custom fallbacks init wrote for
  unsupported stacks) and the guardrails hook `restrict-paths.sh`
- `.claude/settings.json` — optimus-added entries only, handled in Step 5
- `.claude/.optimus-version`
- `HOW-TO-RUN.md` at the project root — only if init generated it; it may be
  hand-written (see Step 2)
- Harness state from `/optimus:deep` runs: `.claude/*-deep-progress.json`,
  `.claude/*-deep-progress.json.bak`, `.claude/*-deep-progress.done.json`,
  `.claude/.deep-iteration-*`, `.claude/.unit-test-deep-*`

## Step 2 — Classify each file

Each inventoried file gets one of: **UNMODIFIED** (matches its plugin template —
safe to remove), **LIKELY_GENERATED** (optimus wrote it; content came from project
analysis), **MODIFIED** (user edits — or an older optimus install whose templates
have since drifted; if `.claude/.optimus-version` records an older plugin version,
note that in the plan as evidence of drift), or **COMPLEX** (`settings.json` only).
Also record whether each file is git-tracked (`git ls-files --error-unmatch <file>`,
run inside the owning repo) — tracked files are recoverable after deletion.

Strategies, by how much of the file init generates:

- **Exact templates — hooks.** Byte-compare each hook against its same-named
  template in `$CLAUDE_PLUGIN_ROOT/skills/init/templates/hooks/`. Identical →
  UNMODIFIED, different → MODIFIED. Custom fallback hooks have no template:
  LIKELY_GENERATED if they follow the template hooks' shape (shebang, JSON stdin
  parsed into a file path, extension guard, formatter invocation), else MODIFIED.
- **Near-exact templates — guideline docs.** For `coding-guidelines.md` and
  `skill-writing-guidelines.md` (root and subproject copies), init substitutes
  `[PROJECT NAME]` on line 1 only. Compare from line 2 onward against the same-named
  template in `$CLAUDE_PLUGIN_ROOT/skills/init/templates/docs/`. Identical →
  UNMODIFIED, different → MODIFIED.
- **Fingerprinted generated docs.** Content is project-specific, so compare
  structure, not bytes:
  - `CLAUDE.md` files: LIKELY_GENERATED when line 1 is the HTML maintenance comment
    from the matching template in `$CLAUDE_PLUGIN_ROOT/skills/init/templates/`
    (`single-project-claude.md`, `monorepo-claude.md`, `subproject-claude.md`,
    `multi-repo-claude.md`); otherwise MODIFIED.
  - `testing.md`, `styling.md`, `architecture.md`: LIKELY_GENERATED when the `##`
    heading skeleton matches the corresponding template in
    `$CLAUDE_PLUGIN_ROOT/skills/init/templates/docs/` in order (architecture has
    three template variants — a match with any of them counts); otherwise MODIFIED.
- **HOW-TO-RUN.md** — no template or fingerprint exists. Ask the user whether init
  generated it; if it is hand-written or the user is unsure, leave it alone.
- **Always safe.** `.claude/.optimus-version` and the harness state files are pure
  machine state with no user content: UNMODIFIED.
- **settings.json** — COMPLEX; never a candidate for whole-file deletion here.

## Step 3 — Confirm

Present the plan grouped by classification (and by repo in multi-repo workspaces),
marking each file git-tracked (recoverable via `git checkout`) or not. Then ask what
to remove. A single answer may cover all UNMODIFIED and LIKELY_GENERATED files;
MODIFIED files are only ever deleted with explicit per-file approval. Always offer
aborting — on abort, change nothing and stop.

## Step 4 — Execute removals

Delete the approved files. In multi-repo workspaces process each repo independently;
in monorepos include the approved subproject `CLAUDE.md` and `docs/` files.

## Step 5 — settings.json surgical cleanup

Runs whenever the user did not abort — it removes only optimus-added entries, so it
applies regardless of which deletion mix was chosen. Edit the file in place:

1. In `hooks.PostToolUse`, remove individual command objects whose command
   references a `.claude/hooks/format-*` file that no longer exists. Command-object
   granularity matters: if the user kept a hook file, its command stays wired.
   The shape init installs is in `$CLAUDE_PLUGIN_ROOT/skills/init/templates/settings.json`.
2. In `hooks.PreToolUse`, remove the command object referencing
   `.claude/hooks/restrict-paths.sh` — likewise only if that file no longer exists.
3. In `permissions.allow` and `permissions.deny`, remove entries that exactly match
   the guardrails template lists in
   `$CLAUDE_PLUGIN_ROOT/skills/init/templates/permissions-settings.json`. Leave
   every other entry untouched — anything not in the template is the user's.
4. Prune empty containers bottom-up (empty `hooks` array → its entry → the
   `PostToolUse`/`PreToolUse` key → the `hooks` object; same for `permissions`). If
   the whole object ends up `{}`, delete the file; otherwise write it back with
   2-space indentation.

## Step 6 — Clean up and report

Remove directories the deletions left empty: `.claude/hooks/`, `.claude/docs/`,
subproject `docs/` in monorepos, and `.claude/` itself only if completely empty —
per repo in multi-repo workspaces.

Summarize what was removed, what was kept and why, and what changed in
`settings.json` (call it out when a kept hook's entry stays active). Note that
`docs/specs/` and `docs/product/` were left in place as user content.

If the goal was a clean reinstall, run `/optimus:init` next; if the goal is dropping
optimus entirely, finish with `/plugin uninstall optimus@optimus-claude`.
