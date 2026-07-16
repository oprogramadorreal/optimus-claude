---
description: Prepares a project for Claude Code — analyzes the codebase with a detection agent, then generates a compact CLAUDE.md plus scoped docs, coding guidelines, auto-format hooks, and test infrastructure, with optional safety guardrails (branch-protection and precious-file PreToolUse hook plus permission defaults) and a HOW-TO-RUN.md onboarding doc. Offers new-project scaffolding in empty directories. Re-runs audit the existing setup and sync stale project docs against source code. Supports single projects, monorepos, and multi-repo workspaces. Writes under .claude/ (CLAUDE.md, docs, hooks, merged settings.json) and may update README testing sections and .gitignore; installs frameworks and formatters only with approval. Use to bootstrap a project for Claude Code, or re-run to refresh an outdated setup. Replaces /init.
disable-model-invocation: true
---

# Initialize Project for Claude Code

Analyze the project, then set it up for Claude Code: a compact CLAUDE.md with progressive-disclosure docs, coding guidelines, auto-format hooks, test infrastructure, and optionally safety guardrails and a HOW-TO-RUN.md onboarding doc. Everything lands in the project directory so it travels with the repo.

## Ground rules

Read `$CLAUDE_PLUGIN_ROOT/skills/init/references/claude-md-best-practices.md` before generating any CLAUDE.md. Constraints that always apply: every CLAUDE.md targets 60 lines or fewer, uses file:line references instead of code snippets, and contains only universally-applicable instructions.

**Preserve user content.** Never silently drop CLAUDE.md or doc content that cannot be re-derived from the codebase. Classify content as outdated only when source code directly contradicts it, and confirm with the user before removing user-added items. When unsure, preserve. Never discard user content to meet a line target — exceed the target and say so in the final report instead.

**Three write policies:**

- **Generated content** — formatter hooks and `coding-guidelines.md` are verbatim plugin output: always overwrite silently, never audit.
- **Customizable docs** — `testing.md`, `styling.md`, `architecture.md`, `skill-writing-guidelines.md`: create from template when missing; when one exists, review it against the template and propose changes — never silently overwrite.
- **`settings.json`** — always merge into the existing file, never overwrite it. Preserve sections init doesn't manage.

Write new files directly without asking — files under `.claude/` are plugin-managed output, and the detection gate below is the approval point. Only pause when replacing user-customized content.

## Step 1: Detect

**Empty directory:** if the directory has no manifest file at any depth and no source directories (at most `.git/`, `.gitignore`, `LICENSE`, and a stub README), offer to scaffold a new project first. If accepted, follow `$CLAUDE_PLUGIN_ROOT/skills/init/references/new-project-scaffolding.md`; for stacks it doesn't cover, apply `$CLAUDE_PLUGIN_ROOT/skills/init/references/unsupported-stack-fallback.md` to find the official scaffolding command via web search, and if that also fails, create a minimal manifest plus hello-world entry point with user approval. After scaffolding, restart detection from scratch in the new project root.

**Analysis agent:** delegate codebase analysis to one agent to keep this context clean for generation. Read `$CLAUDE_PLUGIN_ROOT/skills/init/agents/shared-constraints.md` and `$CLAUDE_PLUGIN_ROOT/skills/init/agents/project-analyzer.md`, plus the two reference files the agent needs as context:

- `$CLAUDE_PLUGIN_ROOT/skills/init/references/tech-stack-detection.md`
- `$CLAUDE_PLUGIN_ROOT/skills/init/references/project-detection.md`

Launch one `general-purpose` agent with the shared constraints, both reference contents, and the analyzer prompt. Its Detection Results drive everything below: project name, tech stack, package manager, commands, structure (single project / monorepo / multi-repo workspace / ambiguous), subprojects or repos, existing-file inventory, test infrastructure (yes/no), skill authoring (yes/no), and doc-sourced insights. If the structure comes back ambiguous, ask the user to resolve it.

**Confirmation gate:** present a detection summary and confirm it with the user before writing anything (AskUserQuestion works well here — let the user proceed, correct details, or abort). If no test infrastructure was detected, mention that Step 5 will offer to install it and that several optimus skills depend on it.

## Step 2: Audit existing setup (re-runs)

Skip this step when the inventory found no existing `.claude/` docs or CLAUDE.md files.

Otherwise launch one `general-purpose` agent from `$CLAUDE_PLUGIN_ROOT/skills/init/agents/documentation-auditor.md`, prepended with the shared constraints and Step 1's Detection Results. It classifies existing content as Outdated / Missing / Accurate / User-added — Outdated only when source code directly contradicts a specific claim.

Present the audit report and let the user choose what to apply: everything, selected findings, or a fresh regeneration. All paths preserve user-added content — for fresh regeneration, extract user-added sections first and re-insert them into the regenerated files. Steps 3–6 then act on the choice: Accurate files are left alone, Outdated files get only the approved changes, Missing files are created normally. Generated content (hooks, `coding-guidelines.md`) is exempt and always refreshed.

## Step 3: Create CLAUDE.md

Create `.claude/docs/` and `.claude/hooks/` (plus `<subproject>/docs/` per monorepo subproject).

Pick the template and fill every placeholder with detected values: real commands with the detected package-manager prefix, actual directories, and a Conventions section drawn from doc-sourced insights or inferred from project structure. The templates' HTML comments carry their own conditional instructions (the skill-authoring sentence, what belongs in the Documentation section) — resolve each one and remove the comment.

- **Single project:** `$CLAUDE_PLUGIN_ROOT/skills/init/templates/single-project-claude.md`.
- **Monorepo:** `$CLAUDE_PLUGIN_ROOT/skills/init/templates/monorepo-claude.md` for the root — subproject table, workspace-wide commands only — plus `$CLAUDE_PLUGIN_ROOT/skills/init/templates/subproject-claude.md` for each subproject except root-as-project (the root file already covers it). With more than 6 subprojects, group by category in the root file and move the full table to `architecture.md`.
- **Multi-repo workspace:** run the full flow (Steps 3–9) independently inside each repo so each gets a complete, self-contained `.claude/` that works for a teammate who clones only that repo. Then create a lightweight workspace-root `CLAUDE.md` from `$CLAUDE_PLUGIN_ROOT/skills/init/templates/multi-repo-claude.md` — cross-repo context only, and local-only (tell the user it isn't version-controlled).

When updating an existing CLAUDE.md, edit it in place — apply approved audit changes and preserve everything else; don't regenerate from the template. If a nested app root was detected, make all commands reference the correct subdirectory. If a root-level `CLAUDE.md` exists outside `.claude/`, suggest removing it once `.claude/CLAUDE.md` is in place. When the detected structure changed scope since the last run (e.g., a single project became a monorepo), move scoped docs to their new location and remove the old copies — content moves, it doesn't duplicate.

## Step 4: Formatter hooks

Read `$CLAUDE_PLUGIN_ROOT/skills/init/references/formatter-setup.md` and install auto-format PostToolUse hooks for each detected stack (templates in `$CLAUDE_PLUGIN_ROOT/skills/init/templates/hooks/`; stacks without a template go through `unsupported-stack-fallback.md`). Always overwrite existing format hooks — they are generated content. Ask before installing any formatter that isn't already a project dependency. Register installed hooks in `.claude/settings.json` per the reference's merge rules; if no hooks were installed, don't create the file.

## Step 5: Test infrastructure

Read `$CLAUDE_PLUGIN_ROOT/skills/init/references/test-infra-provisioning.md` and follow it.

- **Test infrastructure detected:** run the health check, provision the docs (testing.md, CLAUDE.md references, README testing section, .gitignore entry), and close any coverage-tooling gap with user approval.
- **Not detected:** ask whether to install a framework, recommending yes — `/optimus:tdd` is non-functional without one and `/optimus:deep` cannot run safely without a test command. On yes, consult `$CLAUDE_PLUGIN_ROOT/skills/init/references/test-framework-recommendations.md`, get approval for the specific framework, install it, health-check, then provision. On no, skip provisioning and note the reduced skill functionality in the final report.

Be honest about broken baselines: init fixes build/bootstrap failures with approval but never fixes failing test logic — record failure counts and report them plainly at the end.

## Step 6: Guideline and doc files

Always create `.claude/docs/coding-guidelines.md` from `$CLAUDE_PLUGIN_ROOT/skills/init/templates/docs/coding-guidelines.md`, replacing `[PROJECT NAME]` (silent overwrite — verbatim template).

Create these based on detection (`testing.md` is Step 5's):

| File | Template (in `$CLAUDE_PLUGIN_ROOT/skills/init/templates/docs/`) | Create when |
|------|------|-------------|
| `styling.md` | `styling.md` | Manifest lists a UI framework or CSS tooling, stylesheets exist in `src/`, or the project is a Flutter app |
| `architecture.md` | `architecture.md`, `architecture-hybrid.md`, or `architecture-skill-authoring.md` | 3+ top-level source directories, recognized pattern directories (controllers/, services/, repositories/, handlers/, models/), or skill authoring detected |
| `skill-writing-guidelines.md` | `skill-writing-guidelines.md` | Skill authoring detected |

Architecture template variant: code-only for regular projects, skill-authoring when the project is purely markdown instruction files, hybrid when it has both. If an existing `architecture.md` came from a different variant than the project now needs, propose restructuring — don't silently switch.

Fill all placeholders with actual project details; leave no `[placeholder]` text. Existing files follow the customizable-docs policy from the ground rules. Monorepo placement: `coding-guidelines.md` and `skill-writing-guidelines.md` are shared at root `.claude/docs/` (skill-authoring detection applies at the repo level); `styling.md` and `architecture.md` go in each subproject's `docs/`, applying the detection rules per subproject; root-as-project keeps its scoped docs in `.claude/docs/`. After creating docs, list each in the Documentation section of the CLAUDE.md that scopes it.

## Step 7: Optional add-ons

Offer both add-ons and install whichever the user wants.

### Safety guardrails

A PreToolUse hook plus permission defaults for low-prompt autonomous work with hard rails: writes outside the project prompt for approval, deletes outside the project are blocked, well-known precious unversioned files (`.env`, keys, local databases) are protected, and git commit/push/rebase/merge are blocked on protected branches — enabling a feature-branch workflow. The permission defaults pre-approve routine tools and deny ~30 destructive command patterns.

To install:

1. Copy `$CLAUDE_PLUGIN_ROOT/skills/init/templates/hooks/restrict-paths.sh` to `.claude/hooks/restrict-paths.sh` verbatim — never modify the template content. If a previous copy carries local edits (a customized `PROTECTED_BRANCHES` array, extra `is_precious()` patterns), list them and ask whether to re-apply them on top of the fresh copy.
2. Merge `$CLAUDE_PLUGIN_ROOT/skills/init/templates/permissions-settings.json` into `.claude/settings.json`: add missing `permissions.allow` / `permissions.deny` entries and the PreToolUse hook entry (no duplicates), never remove existing entries, preserve everything else. If `.mcp.json` exists at the project root, add an `mcp__<server>` allow entry per server. If the existing file isn't valid JSON, show the problem and ask — don't repair silently.
3. Verify the installed hook matches the template (`diff`, allowing only user-chosen re-applied edits) and parses (`bash -n`) — a mangled hook fails open. Re-copy on any other mismatch.

When reporting, be clear this is defense-in-depth, not sandboxing: commands inside the project that miss the deny list run unprompted, and the deny list is a blocklist, not a policy. Protected branches are customizable via the hook's `PROTECTED_BRANCHES` array.

### HOW-TO-RUN.md

A developer onboarding doc: fresh clone to running project. If accepted, read `$CLAUDE_PLUGIN_ROOT/skills/init/references/how-to-run-generation.md` and follow it — it also covers auditing an existing HOW-TO-RUN.md instead of regenerating it.

## Step 8: Sync project documentation

Skip if the project has no documentation of its own. This step runs on project-owned files — README.md, CONTRIBUTING.md, ARCHITECTURE.md, and `docs/` files overlapping generated topics — independently of the Step 2 choice.

Cross-check them against source code (manifests, lock files, directory structure) and fix only genuine contradictions: wrong commands, references to removed tech, directories that don't exist, stale subproject lists. Surgical correction, not editorial improvement — leave tone, structure, and imprecise-but-not-wrong prose alone. Present each finding with its source-code evidence and apply only what the user approves.

## Step 9: Verify and report

Apply the gate function from `$CLAUDE_PLUGIN_ROOT/skills/init/references/verification-protocol.md`: verify each item below with fresh evidence and fix failures before reporting.

- Every expected file exists (per subproject and per repo where applicable).
- No `[placeholder]` text survives; each CLAUDE.md has the real project name, working commands, and project-specific conventions; line counts are within target or the overage is justified by preserved user content.
- `settings.json` is valid JSON, references every installed hook and vice versa, and its pre-existing sections survived the merge.
- Every doc listed in a CLAUDE.md Documentation section exists, and every created doc is listed in the CLAUDE.md that scopes it. Monorepo: every subproject in the root table has its CLAUDE.md. Multi-repo: every repo is self-contained.
- Installed hooks match their templates; any custom fallback hook follows the shell-hook pattern.

Then write the plugin version (from `$CLAUDE_PLUGIN_ROOT/.claude-plugin/plugin.json`) to `.claude/.optimus-version` — the version string only; one per repo in a multi-repo workspace. Only init ever writes this file.

Report in natural prose: what was detected, created, updated, and skipped, plus anything the user genuinely needs to know —

- a broken test baseline (init doesn't fix failing tests by design; suggest triaging them before running skills that need a green baseline)
- a freshly installed framework with zero test files (the test command passing with 0 tests is a false safety net)
- a scaffolded project living in a new subdirectory (future sessions must start there or none of this setup loads)
- declined test infrastructure (reduced skill functionality; re-run init to add it later)

Close by suggesting the natural next step: `/optimus:unit-test` to build real coverage, or `/optimus:spec` first when this is a fresh scaffold with no features yet. Either is best run in a fresh conversation.
