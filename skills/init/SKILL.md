---
description: Bootstraps a project for Claude Code — detects tech stack and structure (single project, monorepo, or multi-repo workspace), generates CLAUDE.md plus progressive-disclosure docs, installs auto-format hooks and test infrastructure, and audits/syncs existing documentation against source code. Writes files under .claude/ and subproject docs/; offers official-CLI scaffolding in empty directories. Replaces /init; safe to re-run.
disable-model-invocation: true
---

# Initialize Project for Claude Code

## File semantics

Three classes govern every file this skill writes. Later steps name the class instead of restating the rules.

- **Generated** — `.claude/hooks/*` and `.claude/docs/coding-guidelines.md`: verbatim templates (or fallback hooks), never user-authored. Always overwrite silently, regardless of audit status.
- **Customizable** — all `CLAUDE.md` files, `testing.md`, `styling.md`, `architecture.md`, `skill-writing-guidelines.md`: never silently overwrite. When the file exists, review-and-propose — compare against the template and detected state, apply only user-approved changes, preserve user-added sections.
- **settings.json** — always merge, never overwrite: preserve `permissions` and any other custom sections. Do not create it when no hooks are installed and it doesn't already exist.

New files of any class are written directly — no confirmation prompts. **Preserve when unsure:** content not derivable from the codebase is never discarded, not even to meet size targets. Mark content outdated only when source code directly contradicts it, and confirm with the user before removing user-added items. The same semantics apply to subproject docs in monorepos and to each repo's `.claude/` in multi-repo workspaces.

## CLAUDE.md authoring rules

CLAUDE.md is loaded into every conversation — every line must earn its place.

- Target <= 60 lines. The limit is soft: condense template-generated content first; if user-added content still pushes it over, exceed the limit and note the overage in the Step 7 summary.
- WHAT/WHY/HOW: tech stack and codebase map; purpose and reasoning behind decisions; build/test/lint commands with the detected package-manager prefix.
- Only universally-applicable instructions — task-specific content distracts the model and degrades instruction-following.
- Progressive disclosure: details live in separate docs referenced with one-line descriptions, loaded on demand.
- `file:line` references, not code snippets — snippets go stale.
- No code-style rules — the formatter hooks installed in Step 5 enforce style deterministically.
- Nothing generic: every line reflects the actual project, as if hand-crafted.
- Monorepo: root CLAUDE.md is an orchestrator — subproject table, workspace-wide commands, links to each subproject's own <= 60-line CLAUDE.md (auto-discovered when working there). Shared guidelines stay at root `.claude/docs/`; `testing.md`/`styling.md`/`architecture.md` are scoped per subproject.
- Multi-repo workspace: each repo is fully self-contained (own `.claude/`); the parent CLAUDE.md is a lightweight local-only map — nothing is shared at root.

## Step 1: Detect Project Context

### Empty-directory check

A directory is **near-empty** when it contains at most `.git/`, `.gitignore`, `LICENSE`, and/or a stub `README.md` (under 5 lines of non-empty content), with no manifest files at any depth and no source directories (`src/`, `lib/`, `app/`, `pkg/`, `cmd/`). If empty or near-empty, use `AskUserQuestion` — header "Empty Project", question "This directory appears to be empty. Would you like to scaffold a new project?":
- **Scaffold new project** — "Set up a new project from scratch, then continue with full init setup"
- **Continue anyway** — "Proceed with init as-is (I'll add code myself later)"

On **Scaffold**: read and execute `$CLAUDE_PLUGIN_ROOT/skills/init/references/new-project-scaffolding.md`. If it returns an unsupported-stack signal, apply `$CLAUDE_PLUGIN_ROOT/skills/init/references/unsupported-stack-fallback.md` (steps 1-4) to find the stack's official scaffolding CLI; if that reaches graceful skip, instead create a minimal project manually (manifest + hello-world entry point + `.gitignore`) with user approval. After scaffolding, discard all prior detection state and restart Step 1's project detection from scratch.

### Project detection (agent-assisted)

Read `$CLAUDE_PLUGIN_ROOT/skills/init/agents/project-analyzer.md` and launch 1 `general-purpose` agent with that prompt, prepended with the "Agent Constraints" section of `$CLAUDE_PLUGIN_ROOT/references/shared-agent-constraints.md`. Assemble the prompt per "Prompt assembly at dispatch time" in `$CLAUDE_PLUGIN_ROOT/references/agent-architecture.md` — the agent reads the detection references itself via the absolutized paths its prompt carries.

If the agent reports the structure as **ambiguous**, resolve via `AskUserQuestion`: ask the user to confirm whether this is a monorepo and identify subproject directories.

### Checkpoint

Confirm the agent's Detection Results cover every field of its return format (project name through doc-sourced insights); re-examine the project for anything missing. Print the results as a **Detection Summary**. If no test infrastructure was detected, append:

> **Tests:** No test framework, test script, or test directory detected — Step 5b will offer to install one. Strongly recommended: multiple optimus skills depend on test infrastructure.

Then use `AskUserQuestion` — header "Detection", question "Does the detection summary look correct?":
- **Proceed** — "Everything looks right — continue with setup"
- **Correct** — "I need to fix something before continuing"
- **Abort** — "Cancel init"

On **Correct**: ask what to change, update the detection results, and re-present the same gate.

### Step 1b: Documentation audit (only when the inventory found existing docs)

Read `$CLAUDE_PLUGIN_ROOT/skills/init/agents/documentation-auditor.md` and launch 1 `general-purpose` agent with that prompt, prepended with the same "Agent Constraints" section plus the Detection Results from Step 1 (same prompt-assembly rule). Present the agent's **Audit Report** to the user.

**Standard of proof:** only content directly contradicted by source code is Outdated. When a user-added item looks outdated, confirm via `AskUserQuestion` before discarding — the user may have context the codebase doesn't show.

Use `AskUserQuestion` — header "Audit", question "How would you like to handle the documentation audit findings?":
- **Update all** — "Apply all recommended changes"
- **Selective** — "Pick which findings to apply by number" (then ask for the numbers; unapproved findings are left as-is)
- **Fresh start** — "Regenerate template content from scratch, but carry forward user-added sections"

Steps 2-6 apply this choice; Step 6b runs independently. **Fresh start preservation:** extract all User-added content first; after regenerating, re-insert it into the most appropriate sections and present the merged result before writing.

## Step 2: Handle Existing Files

Apply the audit choice through the File semantics classes: Accurate → skip the file; Outdated → apply only approved changes, preserve everything else; Missing or no audit → create normally; Fresh start → regenerate Customizable files, always carrying User-added content forward. Generated files are overwritten regardless.

**Relocate when scope changes** (e.g., root `.claude/docs/testing.md` → subproject-scoped in a monorepo): move the content, remove the old file. Only `coding-guidelines.md` and `skill-writing-guidelines.md` stay at root. If a root-level `CLAUDE.md` exists outside `.claude/`, suggest removing it once `.claude/CLAUDE.md` is created.

## Step 3: Create Directory Structure

```bash
mkdir -p .claude/docs .claude/hooks
# Monorepo: also mkdir -p <subproject>/docs per subproject
# Multi-repo workspace: run inside each repo (each gets its own .claude/)
```

## Step 4: Create CLAUDE.md

Fill every template placeholder with real detected values — no `[placeholder]` text may survive (Step 7 verifies). In each template that carries one (single-project, monorepo, and subproject CLAUDE.md templates — the multi-repo template has none), resolve the skill-authoring HTML comment: if skill authoring was detected in Step 1, replace it with the concrete sentence the comment carries; otherwise delete the comment. **When updating an existing CLAUDE.md** (not Fresh start): edit in place per File semantics — never regenerate from template.

**Single project** — template `$CLAUDE_PLUGIN_ROOT/skills/init/templates/single-project-claude.md`:
- Conventions: 2-5 bullets from doc-sourced insights, or inferred from structure (entry points, routing/layout patterns, non-obvious rules).
- Documentation section: list only non-guideline docs that actually exist — empty on a first run; Steps 5b/6 add entries as they create docs.
- No manifest detected → generic placeholders, and tell the user manual customization is recommended.

**Monorepo** — template `$CLAUDE_PLUGIN_ROOT/skills/init/templates/monorepo-claude.md`:
- Subproject table (path, purpose, stack); root/workspace-wide commands only; references to subproject CLAUDE.md files.
- Workspace tool detected → "managed by [tool]"; none → "Monorepo with [N] packages" without naming a tool.
- More than 6 subprojects → group by category in root CLAUDE.md and move the full table to `.claude/docs/architecture.md`.
- Root-as-project: also list its root-scoped docs in the Documentation section.

**Multi-repo workspace** — run the full init flow (Steps 3-7) independently inside each repo, as if init were invoked there (single-project or monorepo template as appropriate; each repo's `.claude/` is version-controlled and self-contained). Then create a lightweight workspace-root `CLAUDE.md` (NOT inside `.claude/`) from `$CLAUDE_PLUGIN_ROOT/skills/init/templates/multi-repo-claude.md` — tell the user it is local-only and not version-controlled. If a repo has a nested app root, its CLAUDE.md must note the nested structure and point all commands at the correct subdirectory.

**Step 4b — subproject CLAUDE.md files (monorepo only):** for each subproject except root-as-project/root-as-member (root CLAUDE.md covers those), use `$CLAUDE_PLUGIN_ROOT/skills/init/templates/subproject-claude.md`: WHAT/WHY/HOW scoped to that subproject, commands run from its directory, local `docs/` references, parent monorepo named in the opening line.

## Step 5: Install Formatter Hooks

Read `$CLAUDE_PLUGIN_ROOT/skills/init/references/formatter-setup.md` and install the applicable hooks so files are auto-formatted after every Edit/Write (templates in `$CLAUDE_PLUGIN_ROOT/skills/init/templates/hooks/`; supported: Python, Node.js, Rust, Go, C#/.NET, Java, C/C++, Dart/Flutter — other stacks via `$CLAUDE_PLUGIN_ROOT/skills/init/references/unsupported-stack-fallback.md`). Hooks are Generated files; `settings.json` follows its merge semantics. External formatters not already in deps → ask the user before installing.

## Step 5b: Test Infrastructure Setup

Read `$CLAUDE_PLUGIN_ROOT/skills/init/references/test-infra-provisioning.md`.

**If test infrastructure was detected in Step 1:** run the full procedure — health check (run the suite; fix build/bootstrap failures only with user approval; record assertion failures as `{scope, failing_count}` for Step 7), coverage-tooling gap check, and provisioning (testing.md, CLAUDE.md refs, README section, .gitignore).

**If not detected:** use `AskUserQuestion` — header "Test Infrastructure", question "No test framework was detected. Would you like to install one?":
- **Yes (strongly recommended)** — "Install test framework and coverage tooling. Multiple optimus skills depend on it: `/optimus:tdd` is non-functional without tests, and `/optimus:deep` cannot run safely without a test command."
- **No** — "Skip test infrastructure setup — some optimus skills will have reduced functionality"

On **Yes**: follow the reference's installation section (framework recommendation, explicit user approval, install, health check), then the full provisioning. On **No**: skip all provisioning; Step 7's summary carries the declined-infra note.

## Step 6: Create Documentation Files

`coding-guidelines.md` (Generated) — always create in `.claude/docs/` from `$CLAUDE_PLUGIN_ROOT/skills/init/templates/docs/coding-guidelines.md`, replacing `[PROJECT NAME]`.

Conditional docs (Customizable; `testing.md` was handled in Step 5b). Fill all placeholders with actual project details:

| File | Template | Create when ANY of these hold |
|------|----------|-------------------------------|
| `styling.md` | `$CLAUDE_PLUGIN_ROOT/skills/init/templates/docs/styling.md` | Manifest lists a UI framework (react, vue, angular, svelte, solid) OR CSS tooling (tailwindcss, styled-components, sass, less, postcss) OR `.css`/`.scss`/`.less` files exist in `src/` OR `pubspec.yaml` has a Flutter SDK dependency |
| `architecture.md` | `$CLAUDE_PLUGIN_ROOT/skills/init/templates/docs/architecture.md` | 3+ top-level source directories (excluding config, tests, docs, build output) OR recognized pattern directories (controllers/, services/, repositories/, handlers/, models/) OR skill authoring detected |
| `skill-writing-guidelines.md` | `$CLAUDE_PLUGIN_ROOT/skills/init/templates/docs/skill-writing-guidelines.md` | Skill authoring detected in Step 1 (structural rule in project-analyzer.md task 9) |

The architecture template carries two HTML-comment-marked optional sections: keep **Skill Architecture** only when skill authoring was detected, and keep the code sections (Data Flow, Key Patterns, Dependencies Between Modules) only when the project has code components — delete whichever doesn't apply, and the comments themselves. On re-runs, the Customizable review-and-propose semantics cover section changes when the detected project type has shifted.

**Placement:** single project — everything in `.claude/docs/`. Monorepo — `styling.md`/`architecture.md` go in each subproject's `docs/`, applying the detection rules per subproject; `skill-writing-guidelines.md` is installed once at root when any subproject has a skill-authoring stack; root-as-project's scoped docs go in `.claude/docs/`; a subproject gets its own `coding-guidelines.md` only if its conventions differ significantly from root.

**Update the Documentation sections:** after creating `styling.md`/`architecture.md`, add each to the Documentation section of the CLAUDE.md that scopes it (`testing.md` references were added in Step 5b).

## Step 6b: Sync Existing Documentation

Skip when the project has no docs of its own (no README.md, CONTRIBUTING.md, ARCHITECTURE.md, or docs/ files). This step runs independently of the Step 1b audit choice (Fresh start governs only `.claude/` files) — it operates on project-owned files.

Cross-check README.md (root, and each subproject's in monorepos), CONTRIBUTING.md, ARCHITECTURE.md, and docs/ files that overlap generated topics against source code (manifests, lock files, directory structure). Fix only claims directly contradicted by source — wrong commands or package manager, tech no longer in deps, renamed directories, stale subproject lists, removed dependencies. Surgical, never editorial: leave prose, tone, structure, and imprecise-but-not-wrong descriptions untouched; never add sections or create files; touch nothing outside the project root.

**If contradictions found:** present a Sync Report (file, current content, proposed fix, source evidence), then use `AskUserQuestion` — header "Sync", question "How would you like to handle the documentation sync findings?": **Apply all** / **Selective** (ask which correction numbers) / **Skip sync**. Apply only approved changes. If none found, report that and continue.

## Step 7: Verify and Report

Run this checklist and fix any failure before reporting:

- **File existence** — every expected file exists: `.claude/` files (`*.md`, `*.json`, `hooks/*`); monorepo subproject `CLAUDE.md` + `docs/*.md`; multi-repo per-repo files.
- **Content** — no `[placeholder]` text and no unresolved template HTML comments anywhere (each file's line-1 identity comment is the only `<!--` allowed to remain); CLAUDE.md has the real project name, real commands, Conventions and Documentation sections, and <= 60 lines (soft — verify any overage isn't template bloat); `settings.json` `hooks.PostToolUse` ↔ installed hook files match in both directions and custom sections survived; each template-based hook matches its template; custom hooks follow the shell-hook pattern and unsupported-stack-fallback validation rules; each doc references the project's actual frameworks, tooling, and directories; applied sync edits left valid, untruncated markdown.
- **Cross-references** — every doc listed in a CLAUDE.md Documentation section exists, and every created `testing.md`/`styling.md`/`architecture.md` is listed in the CLAUDE.md that scopes it; monorepo: every subproject in the root table has its CLAUDE.md; multi-repo: every repo listed in the workspace CLAUDE.md has its own self-contained `.claude/`.

**Write the plugin version** to `.claude/.optimus-version` after all checks pass — version string only (e.g., `3.0.0`), read from `$CLAUDE_PLUGIN_ROOT/.claude-plugin/plugin.json`; per repo in multi-repo workspaces. Only init ever writes this file.

**Summary** — present the final report using this exact format:

```
### Optimus Init Complete

| Category | Details |
|----------|---------|
| **Project** | [project name] — [tech stack summary] |
| **Structure** | [Single project / Monorepo with N packages / Multi-repo workspace with N repos] |
| **Files created** | [count] files ([list]) |
| **Formatters** | [hooks installed, or "None"] |
| **Test infra** | [Pre-existing: framework / Installed: framework / Not installed] |
| **Doc sync** | [N corrections applied / No contradictions found / Skipped] |

[Monorepo: add subproject breakdown rows. Multi-repo: per-repo results + reminder to commit each repo's .claude/ separately.]
```

**Broken baseline:** if the Step 5b health check recorded failing tests, append `— baseline broken ([N] failing)` to the Test-infra value (per subproject/repo where applicable) and add immediately after the table:

> **Baseline broken** — init does not fix failing tests by design. Ask Claude to triage the failing tests before running skills that need a green baseline.

Conditional warnings after the table:

- Scaffolding created `<name>/` → "**New project root:** the project now lives in `<name>/` — start future Claude Code sessions from that directory, or the generated CLAUDE.md and hooks will not load."
- Test framework installed from scratch → "**Important:** the project has no test files yet, so the test command passes with 0 tests — a false safety net. Run `/optimus:unit-test` next to write initial tests and establish real coverage."
- Test infrastructure declined → "**Note:** test infrastructure was not installed — `/optimus:tdd` will not work, and `/optimus:code-review` and `/optimus:refactor` will have reduced functionality. Re-run `/optimus:init` to install it later."

Close with one line: if the project root has no `HOW-TO-RUN.md`, recommend running `/optimus:how-to-run` next; otherwise recommend `/optimus:unit-test` — in a fresh conversation either way.
