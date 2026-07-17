---
description: >-
  Generates or updates a project's HOW-TO-RUN.md — one verified document
  teaching a new developer to set up their environment and run the project
  locally. Detects toolchain, source dependencies, external services, and env
  config via read-only agents; audits an existing file against actual project
  state and offers a display-only guided walkthrough. Never executes commands;
  writes only HOW-TO-RUN.md.
disable-model-invocation: true
---

# How to Run

Generate or update `HOW-TO-RUN.md` at the project (or workspace) root: OS/hardware prerequisites, toolchain and SDKs, source dependencies, install, external services, env config, build, run, and tests — every fact verified against the actual codebase.

**Write scope:** the only file this skill ever creates or modifies is `HOW-TO-RUN.md`. It never touches `README.md`, `CONTRIBUTING.md`, `BUILDING.md`, `INSTALL.md`, `docs/*`, or any other file — not even to add a link. Existing docs are input-only hypotheses. The guided walkthrough (Step 3a) is display-only — the skill never executes commands; the user runs every step locally.

## Step 1: Detect project context (agent)

Read `$CLAUDE_PLUGIN_ROOT/skills/how-to-run/agents/project-environment-detector.md` and `$CLAUDE_PLUGIN_ROOT/skills/how-to-run/agents/shared-constraints.md`. Launch 1 `general-purpose` Agent tool call whose prompt is, in order: the **Agent Constraints** section of `$CLAUDE_PLUGIN_ROOT/references/shared-agent-constraints.md`, the shared-constraints file, the contents of `$CLAUDE_PLUGIN_ROOT/skills/init/references/project-detection.md` and `$CLAUDE_PLUGIN_ROOT/skills/init/references/tech-stack-detection.md`, and the detector prompt. If the current directory has no `.git/` directory, also read `$CLAUDE_PLUGIN_ROOT/skills/init/references/multi-repo-detection.md` and include it — this skill supports multi-repo workspaces via a workspace-root file.

The detector only *flags* an unsupported stack (`Triggered: yes`); the fallback procedure runs here, not in the agent. Wait for the agent's **Context Detection Results**.

**Checkpoint.** Print a Context Summary from the detector's user-facing results: build system and toolchain, tech stacks and package managers, project structure, source dependencies, SDKs, external services (append the `(candidate)` marker for `Confidence: candidate` rows, with source), per-service endpoint semantics — flag `local-windows-auth` / `local-named-instance` / `local-socket` rows (they can trigger a Pre-Conditions Block; a misclassification is corrected via "Correct first") — environment config files, schema bootstrap scripts, recommended developer tools, runtime version constraints, hardware/OS requirements, and dev workflow signals. Do not print the detector-internal Workspace kind, Components, or Runtime Ports tables — Step 4 reads those directly.

Use `AskUserQuestion` — header "Context review", question "Does this capture the project correctly?":
- **Looks good** — "Proceed with detected context"
- **Correct first** — "Some details are wrong or missing"

If "Correct first": `AskUserQuestion` — header "Corrections", question "What should be changed?" (free text). Apply the corrections to the results in memory (recompute the fallback trigger if the stack changed), re-print, re-confirm.

**Unsupported-stack fallback.** If `Triggered: yes`, read `$CLAUDE_PLUGIN_ROOT/skills/init/references/unsupported-stack-fallback.md` and run its 5-step procedure with the reported language(s) and evidence: `WebSearch` for research, enforce its validation rules before presenting any command, `AskUserQuestion` for approval. Approved commands feed Step 4 as if from a recognized stack; skipped or declined ones render as `"not found"`. If WebSearch is unavailable, propose standard commands from general knowledge under the same validation rules, marked "inferred (not web-verified)"; if declined, skip gracefully.

## Step 2: Audit existing docs (agent)

Launch 1 `general-purpose` Agent tool call whose prompt is, in order: the Context Detection Results from Step 1, the Agent Constraints section of `$CLAUDE_PLUGIN_ROOT/references/shared-agent-constraints.md`, the shared-constraints file, and the prompt from `$CLAUDE_PLUGIN_ROOT/skills/how-to-run/agents/how-to-run-auditor.md`. Every file except `HOW-TO-RUN.md` is hypotheses only: facts contradicting the codebase are logged as outdated and reported in Step 6 — never corrected in their source files. Wait for the agent's **How-to-Run Audit Results**.

## Step 3: Assess and plan

Present a per-aspect status table from the audit. Expand **External Services** into a sub-table — Service | Recommended runtime | Alternative | Reason — by reading `$CLAUDE_PLUGIN_ROOT/skills/how-to-run/references/external-services-docker.md` and applying its Decision Heuristics to the endpoint labels. No per-service prompt here — the single exception is Step 4's multi-select downgrade prompt.

**Caution rule:** existing content that seems intentionally unusual or whose purpose is beyond what the codebase reveals (custom flags, unexplained env vars, references to invisible external systems, unconfirmable hardware claims) — flag explicitly and ask; never silently include or exclude.

**Branch on whether `HOW-TO-RUN.md` exists:**

- **Absent:** run the per-item unverifiable prompts below, then go to Step 4. Step 5 writes directly without re-asking — the user approved the plan here.
- **Exists** (accurate, partial, or stale): `AskUserQuestion` — header "How to Run Documentation", question "HOW-TO-RUN.md already exists (audit findings above). How would you like to proceed?":
  - **Walk through it** — "I'll guide you through each step in-chat — show each command, what it does, and the audit verdict. You run the commands locally; I never execute anything for you." → Step 3a.
  - **Regenerate** — "Show the diff and rewrite HOW-TO-RUN.md to match the current project state." → show current content vs proposed correction per outdated item, then the per-item prompts below, then Step 4.
  - **Skip** — "No changes. Print the audit findings and stop." → Step 6 (report only).

**Per-item unverifiable prompts (Regenerate path or fresh write).** For each "Documented but unverifiable" audit item, `AskUserQuestion` whether to include it, showing the source file and heading. On approval, record `{aspect, source_file, source_heading, text, rendered_line}` into an in-memory `approved-unverifiable-items` list, applying every rule in `$CLAUDE_PLUGIN_ROOT/skills/how-to-run/references/step6-verification-audits.md` §Record-time validation before storing. `rendered_line` is filled in at Step 4 — it is the exact line Step 6 exempts.

## Step 3a: Guided walkthrough

Read `$CLAUDE_PLUGIN_ROOT/skills/how-to-run/references/guided-walkthrough.md` and follow it. Display-only; the user runs each command locally. When it finishes (or the user picks **Stop the walkthrough**), jump to Step 6 — this branch never writes.

## Step 4: Generate content

Read `$CLAUDE_PLUGIN_ROOT/skills/how-to-run/references/how-to-run-sections.md` (signal→section digest, section shapes, workspace commands, schema bootstrap, multi-repo template) — `external-services-docker.md` is already loaded from Step 3.

Run the §Web-Search Recipe for every service whose Recommended runtime is **Docker-preferred** or whose Alternative is **Docker (offline)**. If any service was downgraded per Decision Heuristics rule 5, emit ONE `AskUserQuestion` with `multiSelect: true` — header "Docker alternative", question "The Docker alternative failed validation for these services. Keep Docker anyway or fall back?" — one option per downgraded service labelled `<service>: <one-line failure reason>` (the specific validation that tripped); each option's description states checked = Docker alternative kept, unchecked = Shared-cloud no-Docker template. Skip the prompt when nothing failed.

Generate only sections with at least one detected signal (per the digest), in catalog order: **Prerequisites, Toolchain & SDKs, Source Dependencies, Installation, External Services, Environment Setup, Build, Running in Development, Running Tests, Common Issues** — shapes and per-section rules in `how-to-run-sections.md`.

**Content principles:**

- Direct imperative instructions; exact commands with the detected package manager and build system; commands in the order a new developer runs them (prerequisites → toolchain → source deps → install → services → env → build → run).
- **Workspace-aware commands:** when `Workspace kind` is not `none`, use §Workspace-Kind Command Branches — the wrong per-package form is a silent failure.
- **Verify before including:** content sourced from existing docs must match the detector's results; contradictions go to the Step 6 "outdated elsewhere" report and are NOT copied.
- **Never guess runtime ports:** every port in an `Expected result:` line, troubleshooting bullet, or `http://localhost:<N>` URL must come from the detector's Runtime Ports table or External Services Port column. No bound port → omit the port ("see `<launch-config-file>` for the bound port") — never substitute a framework default.
- **Never assert an unobserved path:** render a filesystem path only when it appears verbatim in a detector table or is re-observable via `Glob` at Step 6. For "latest folder"-style references use generic phrasing — never extrapolate a leaf name from versions, dates, or general knowledge.
- **Reject unverifiable exact counts:** no "15 `.csproj` projects" unless Step 6 can re-derive the count via `Glob` or the detector reported it; otherwise "multiple" / "several" / omit.
- **Version numbers** from manifest, build-file, or version-manager constraints only — never guessed.
- **Never copy real secrets:** placeholders only in all snippets and env descriptions.
- **Candidate services:** render Task 5b rows with a `(candidate)` marker in the overview table and subsection headings (silent inclusion is disallowed — the reader must be able to tell a config-grep hit from a compose-confirmed service); no per-service prompt (Step 1 "Correct first" is the drop path); apply §External Services all-candidate compression when it triggers.
- **Render once, not twice:** when the same fact fits two adjacent sections, render it in the one closer to the action and link from the other (e.g., the primary clone lives in Installation — or the multi-repo *Clone All* — only; consolidation rules in §External Services).
- **Reconcile against script runners:** when a rendered command is `<tool> <subcmd> --<flag>` and a same-named script exists in `package.json` / `Justfile` / `Makefile` / launchSettings, open the script body — if the flag is absent, render the bare-tool form instead of the script wrapper.
- **Table of contents:** render a `## Contents` block after the H1 when 7 or more catalog sections rendered; omit otherwise.
- **Approved unverifiable items:** render each as `Per <source_file> "<source_heading>": <sanitized_text>` in the matching section, applying `step6-verification-audits.md` §Render-time sanitization first — entries failing any check are removed; entries that pass store their exact full rendered line (including list marker/indentation) into `rendered_line` for Step 6's exact-match exemption.

## Step 5: Place content

- **`HOW-TO-RUN.md` does not exist:** write directly — the plan was approved in Step 3 and nothing is overwritten.
- **`HOW-TO-RUN.md` exists:** show the full diff (section-by-section when updating) and wait for user approval before writing. Never silently replace existing content. Never delete content outside the sections being replaced; preserve formatting, badges, images, and links in untouched sections. If the existing structure is too unusual to update safely, show the generated content and ask where to place it.

Placement by topology: **single project / monorepo** → repo-root `HOW-TO-RUN.md` (monorepo: whole-project scope — workspace install, shared services, per-subproject and run-everything instructions); **multi-repo workspace** → workspace-root `HOW-TO-RUN.md` per §Multi-Repo Workspace Template (not version-controlled — no `.git` at workspace root).

When dev instructions already live in README/CONTRIBUTING/etc.: silently copy *verified* content (no prompt — verification happened in Steps 2 and 4), leave the originals untouched, and route *contradicting* content to the Step 6 report. *Unverifiable* content was already resolved per-item in Step 3.

## Step 6: Verify and report

If nothing was written (skip / walkthrough / no-action path), skip verification and go to the report.

Read back the written `HOW-TO-RUN.md` and verify against the detector state: package-manager prefixes, prerequisite versions vs manifest constraints, build commands vs detected build files, submodule paths vs `.gitmodules`, sibling-repo paths vs build/CI files, directory paths vs the filesystem, service names vs compose definitions, env-var names vs `.env.example`. Then read `$CLAUDE_PLUGIN_ROOT/skills/how-to-run/references/step6-verification-audits.md` and apply every Step 6 audit in it. On any failure: show the correction, wait for approval, apply, re-verify — never silently accept an ungrounded token.

**Report:** what was created or updated, sections included, aspects intentionally skipped (with reason).

**Outdated info found in other files (not modified):** grouped by source file, list every contradicting fact — heading, documented text, what the detector found, suggested manual fix. State explicitly: **"The skill did NOT modify any of these files. They are listed so you can update them yourself if you want them to match reality."** If none: "No stale setup info found in other files."

If `HOW-TO-RUN.md` was created or updated in a single project or monorepo, recommend `/optimus:commit` — and tell the user to stay in this conversation so the context is captured. Otherwise (multi-repo workspace file, or nothing written), recommend `/optimus:init` in a fresh conversation if it hasn't been run, or `/optimus:unit-test` if test instructions were thin.
