---
description: >-
  Generates or updates a project's HOW-TO-RUN.md — one document teaching a
  new developer to set up their environment and run the project locally.
  Detects toolchain, source dependencies, external services, and env config
  across stacks from web to embedded. Audits an existing file against actual
  project state and offers a guided in-chat walkthrough — the skill never
  executes commands itself. Writes only HOW-TO-RUN.md. Use after
  /optimus:init or when onboarding feels broken.
disable-model-invocation: true
---

# How to Run

Generate or update a `HOW-TO-RUN.md` at the project (or workspace) root that teaches a new developer who has just cloned the repo how to set up their environment and run the project locally — covering OS/hardware prerequisites, toolchain & SDKs, source dependencies (submodules, sibling repos), language-level install, external services, env config, build, run, and tests.

**Write scope:** The only file this skill is ever permitted to create or modify is `HOW-TO-RUN.md`. It never modifies `README.md`, `CONTRIBUTING.md`, `docs/*`, `BUILDING.md`, `INSTALL.md`, or any other file — not even to add a link. Existing docs are *input only*: the skill learns from them but always verifies every fact against the actual codebase before using it. The optional guided in-chat walkthrough (Step 3a) is display-only — it never executes commands; the user runs every step locally. The walkthrough procedure lives in `references/guided-walkthrough.md`.

## Step 1: Detect Full Project Context (agent-assisted)

Delegate project scanning to a detection agent to keep the main context clean for content generation.

Read `$CLAUDE_PLUGIN_ROOT/skills/how-to-run/agents/shared-constraints.md` for agent constraints.
Read `$CLAUDE_PLUGIN_ROOT/skills/how-to-run/agents/project-environment-detector.md` for the full prompt template, detection tasks, and return format for the Project Environment Detector Agent.

Read these reference files and provide their content to the agent as context before the agent prompt:
- `$CLAUDE_PLUGIN_ROOT/skills/init/references/multi-repo-detection.md` — workspace detection
- `$CLAUDE_PLUGIN_ROOT/skills/init/references/project-detection.md` — monorepo/single-project detection
- `$CLAUDE_PLUGIN_ROOT/skills/init/references/tech-stack-detection.md` — manifest → tech stack + package manager
- `$CLAUDE_PLUGIN_ROOT/skills/how-to-run/references/detection-signals.md` — signal-to-section mapping, build-system signals, source-dependency signals

The detector only needs to set `Triggered: yes` when no manifest or build-system signal matches; it does NOT execute the fallback procedure. The procedure itself is loaded by the main SKILL context only when the trigger fires (see Step 1 Checkpoint).

Launch 1 `general-purpose` Agent tool call using the prompt from project-environment-detector.md, prepended with the shared constraints and reference file contents above. The agent detects: build system & toolchain, source dependencies, SDKs & system packages, hardware/OS requirements, tech stack, package manager, project structure, external services, env config, infrastructure signals, and dev workflow signals.

Wait for the agent to complete. Use the agent's **Context Detection Results** to populate the Step 1 Checkpoint below.

### Step 1 Checkpoint

Print a **Context Summary** from the agent's Context Detection Results. The *External-service-default-endpoints* bullet below states how to derive the `Endpoint semantics` label per row.

- **Build system & toolchain** (e.g., CMake >= 3.20 with MSVC, cargo, npm scripts, Gradle 8.x)
- **Tech stack(s)** and **package manager(s)**
- **Project structure** (single / monorepo with subprojects / multi-repo with repos)
- **Source dependencies** (git submodules from `.gitmodules`, sibling repos detected in build/CI files, CMake `FetchContent` / `ExternalProject`)
- **SDKs & system packages** (Vulkan, CUDA, Qt, JDK, .NET SDK, MSVC Build Tools, etc. — only if detected)
- **External services detected** (list each service with a trailing `(candidate)` marker when the detector's `Confidence` column is `candidate`, and its source — e.g., "PostgreSQL — source: docker-compose.yml; OpenIdConnect (candidate) — source: appsettings.development.json:42"). Compose-confirmed services render with no marker; Task 5b framework-config candidates render with `(candidate)`.
- **External service default endpoints** (per service: raw default endpoint from the referenced config file + one `Endpoint semantics` label. For `database`-type services: the row's value from the detector (see `project-environment-detector.md` §External Services). For non-database services: `local-default` for `localhost` / empty / unknown, `remote` for any other hostname/FQDN, `ambiguous` if the config file is missing or unreadable.) Flag rows whose `Endpoint semantics` label is `local-windows-auth`, `local-named-instance`, or `local-socket` — these can trigger a Pre-Conditions Block (the full trigger is re-evaluated at Step 4, where `external-services-docker.md` is loaded) — so a misclassification can be corrected via the "Correct first" flow.
- **Environment config files found** — list each file reported by the detector's Environment Setup table with its format appended in brackets (e.g., `src/Web/config/appsettings.development.json [json]`, `config/application.yml [yaml]`, `.env.example [dotenv]`).
- **Schema bootstrap scripts** (list the detector's Schema Bootstrap table entries with their invocation hint — e.g., "db/DatabaseNew.sql (sqlcmd -i db/DatabaseNew.sql), db/seeds.rb (rails db:seed)" — or "none" when the detector reports none).
- **Recommended developer tools** (list the detector's Recommended Developer Tools entries — e.g., "Google Chrome, SSMS, Visual Studio" — or "none" when empty).
- **Runtime version constraints** (e.g., "Node.js >=18 (engines.node), Python >=3.11 (python_requires)")
- **Hardware / OS requirements** (GPU, USB/serial, OS version — only if detected)
- **Dev workflow signals** (Docker-based, Makefile-based, script-based, process runner, etc.)

Detector-internal fields (*Workspace kind*, *Components* table, *Runtime Ports* table) are read by Step 4 directly from the detector's return-format tables — do NOT print them as user-facing Context Summary bullets.

Use `AskUserQuestion` — header "Context review", question "Does this capture the project correctly?":
- **Looks good** — "Proceed with detected context"
- **Correct first** — "Some details are wrong or missing"

If "Correct first": use `AskUserQuestion` — header "Corrections", question "What should be changed?" (free text). Apply the corrections to the Context Detection Results in memory, recomputing the `Unsupported-Stack Fallback → Triggered` flag if the correction changes the detected language or stack, and re-print the updated Context Summary. Re-confirm.

**Unsupported-Stack Fallback.** If the Context Detection Results show `Unsupported-Stack Fallback → Triggered: yes`, read `$CLAUDE_PLUGIN_ROOT/skills/init/references/unsupported-stack-fallback.md` and run its 5-step procedure here, using the reported **Detected language(s)** and **Evidence** as input. Use `WebSearch` for fallback step 2 (research); enforce the fallback step 3 validation rules before presenting any command; use `AskUserQuestion` for fallback step 4 (approval). Commands approved in fallback step 4 feed Step 4 content generation as if from a recognized stack; commands skipped (search failed or user declined) render as `"not found"` in the affected sections.

**LLM-knowledge fallback (how-to-run only).** If WebSearch is unavailable or returns no results for the detected language, use general knowledge to propose standard install/build/run/test commands for that language. Inferred commands must pass the same fallback step 3 validation rules as web-sourced ones; mark them as "inferred (not web-verified)" when presenting them for user approval in fallback step 4. If the user declines, treat as a graceful skip.

## Step 2: Scan Existing Instructions (agent-assisted)

Delegate documentation scanning to an audit agent that cross-checks existing docs against the detected project state.

**Framing:** The auditor treats findings in every file *except* `HOW-TO-RUN.md` as hypotheses. Every fact will be verified against the detector's Context Detection Results before being used in generated content. Facts that contradict the codebase are logged as outdated and will be reported in Step 6 — they are NOT corrected in their source files.

Read `$CLAUDE_PLUGIN_ROOT/skills/how-to-run/agents/shared-constraints.md` for agent constraints.
Read `$CLAUDE_PLUGIN_ROOT/skills/how-to-run/agents/how-to-run-auditor.md` for the full prompt template, audit tasks, and return format for the How-to-Run Auditor Agent.

Read these reference files and provide their content to the agent as context before the agent prompt:
- `$CLAUDE_PLUGIN_ROOT/skills/init/references/readme-section-detection.md` — heading patterns, section boundary detection, classification rules

Launch 1 `general-purpose` Agent tool call using the prompt from how-to-run-auditor.md, prepended with the shared constraints and reference file contents above. **Provide the Context Detection Results from Step 1 as context** at the start of the agent prompt (before the shared constraints, readme-section-detection.md content, and agent template). The agent reads existing docs in priority order, applies heading detection, classifies each aspect against the detected state, and identifies outdated-elsewhere and unverifiable claims.

Wait for the agent to complete. Use the agent's **How-to-Run Audit Results** for the Step 3 assessment.

## Step 3: Present Assessment and Plan

Present findings as a table with status per aspect (use the classification from the How-to-Run Audit Results).

For the **External Services** aspect, expand it into a sub-table with columns **Service | Recommended runtime | Alternative | Reason**:

- Recommended runtime values: `Docker-preferred` / `Shared-cloud primary (<provider>)` / `Local install only`.
- Alternative values: `Docker (offline)` / `Local install` / `—`.
- Read `$CLAUDE_PLUGIN_ROOT/skills/how-to-run/references/external-services-docker.md` and produce one row per service by applying its Decision Heuristics to the Step 1 Checkpoint's endpoint labels.
- Do not emit a per-service `AskUserQuestion` here — the reference file documents the single exception (the Step 4 multi-select downgrade prompt for rule 5's post-web-search re-confirmation).

**Caution rule:** For existing content that seems intentionally unusual or whose purpose is beyond what the codebase reveals — **flag explicitly and ask** rather than silently including or excluding. Examples: custom startup scripts with non-obvious flags, environment variables with no clear source, instructions referencing external systems not visible in the codebase, documented hardware requirements the detector cannot confirm.

**Branching on whether `HOW-TO-RUN.md` exists:**

- **If `HOW-TO-RUN.md` does NOT exist:** skip the 3-option question below and proceed directly to the per-item unverifiable prompts paragraph, then Step 4. Step 5 writes directly without re-asking — the user already approved the plan in Step 3.
- **If `HOW-TO-RUN.md` exists** (whether all aspects are "Found & accurate", partial, or stale): use `AskUserQuestion` — header "How to Run Documentation", question "HOW-TO-RUN.md already exists (audit findings above). How would you like to proceed?":
  - **Walk through it** — "I'll guide you through each step in-chat — show each command, what it does, and the audit verdict. You run the commands locally; I never execute anything for you."
  - **Regenerate** — "Show the diff and rewrite HOW-TO-RUN.md to match the current project state."
  - **Skip** — "No changes. Print the audit findings and stop."

  Route on the answer:
  - **Walk through it** → jump to Step 3a.
  - **Regenerate** → show current content vs proposed correction for each outdated item, then run the per-item unverifiable prompts paragraph below, then continue with Step 4.
  - **Skip** → jump to Step 6 (report only).

**Per-item unverifiable prompts (Regenerate path or fresh write only).** For each "Documented but unverifiable" item from the audit, use `AskUserQuestion` to ask whether to include it in `HOW-TO-RUN.md`. Show the source file and heading so the user can judge. When the user approves an item, record it in an in-memory `approved-unverifiable-items` list as `{aspect, source_file, source_heading, text, rendered_line}`, validating `source_file` and sanitizing `source_heading` at record time per `$CLAUDE_PLUGIN_ROOT/skills/how-to-run/references/unverifiable-content-sanitization.md` §Record-time validation — apply every rule there before storing the entry. `rendered_line` is populated in Step 4 (it is the exact line Step 6 will exempt).

## Step 3a: Guided Walkthrough

Read `$CLAUDE_PLUGIN_ROOT/skills/how-to-run/references/guided-walkthrough.md` for the per-step procedure and follow it. The walkthrough is display-only — the user runs each command locally. When it finishes (or the user chooses **Stop the walkthrough**), jump to Step 6 — this branch does not write to `HOW-TO-RUN.md` and does not execute commands.

## Step 4: Generate Content

Read these reference files before generating content:

- `$CLAUDE_PLUGIN_ROOT/skills/how-to-run/references/detection-signals.md` — signal-to-section mapping (which detected signals generate which sections).
- `$CLAUDE_PLUGIN_ROOT/skills/how-to-run/references/how-to-run-sections.md` — section templates.
- `$CLAUDE_PLUGIN_ROOT/skills/how-to-run/references/external-services-docker.md` — Docker-vs-local-vs-shared-cloud decision heuristics, web-search recipe, snippet templates, citation format, and registry allowlist for the External Services section.

Before generating content, run `external-services-docker.md` §Web-Search Recipe for every Step 3 row whose Recommended runtime is **Docker-preferred** or whose Alternative is **Docker (offline)**. After the recipe runs, if at least one service was downgraded per §Decision Heuristics rule 5, emit a single **multi-select downgrade prompt** before Step 5 writes the file:

- `AskUserQuestion` with `multiSelect: true`, header `"Docker alternative"`, question `"The Docker alternative failed validation for these services. Keep Docker anyway or fall back?"`.
- One option per downgraded service, labelled `<service>: <one-line failure reason>` (examples: `Redis: Docker Hub page did not list port in structured form and no catalogue rescue`; `LocalStack: pro-tier signal detected — LOCALSTACK_AUTH_TOKEN listed in env-var names`). The failure reason comes from the specific validation that tripped in §Web-Search Recipe.
- Each option's description states what will be written if checked (Docker alternative kept) vs unchecked (Shared-cloud no-Docker template).
- Checked services render the Docker alternative template; unchecked render the [Shared-cloud, no Docker alternative](references/external-services-docker.md#shared-cloud-no-docker-alternative) template.
- Skip the prompt entirely if no services failed validation.

Generate only sections with at least one detected signal. Default order is the catalog below; Step 6's *Section ordering audit* may surface editorial reorder needs per `how-to-run-sections.md` §Section Depends-On Graph (the user resolves the conflict — no auto-rewrite). Full catalog:

1. **Prerequisites** — OS version constraints, hardware requirements (GPU, USB, serial), system tools (docker, make, etc.), version managers (nvm, pyenv, rustup) if config files detected. When the detector's *Hardware / OS Requirements* table contains an OS-version token, render it as the first bullet — see `how-to-run-sections.md` §Prerequisites for the rule (Step 6's *Template-shape audit* enforces it).
2. **Toolchain & SDKs** — compiler, build-tool, language SDK, and domain SDK requirements. See *Additional Detection Hints* in `detection-signals.md` for additional detection signals and the *Build System Detection* table below it for per-file extraction rules. Group per-OS install commands (Windows / macOS / Linux) when multiple OSes are plausible.
3. **Source Dependencies** — fix-after-clone only for single-project / monorepo: `git submodule update --init --recursive` when `.gitmodules` is present (the primary `git clone [--recursive]` lives in Installation, section 4), sibling repos that must be cloned alongside this one (list paths + clone URLs), CMake `FetchContent`/`ExternalProject` notes. (Multi-repo workspaces host the primary clone in the workspace template's *Source Dependencies / Clone All* H2 instead — see *Render once, not twice* (b) below.)
4. **Installation** — clone command (single-project / monorepo only; see item 3), language-level package install (correct PM and prefix), post-install steps (code generation, database migrations, raw-SQL schema bootstrap, seed scripts, asset compilation), vendored-dependency bootstrap (vcpkg, Conan).
5. **External Services** — render per `how-to-run-sections.md` §External Services (Branch A/B/Hybrid); apply `external-services-docker.md` for per-service classification, snippets, web-search recipe, citations, allowlist, sanitization, *PowerShell caveat*, *GUI-client connect note*, and §Pre-Conditions Block. For env-var name slots use `<REQUIRED_ENV_VAR>` or the actual vendor-documented name; for value slots use `<placeholder>` or a vendor-documented constant. Substitute every template placeholder before writing the file per `external-services-docker.md` §Snippet Templates *Placeholder substitution*. Never copy real secrets and never use model-memory image names.
6. **Environment Setup** — render the sub-template that matches the detector's Environment Setup table: (a) dotenv — `cp .env.example .env` plus variable descriptions for `.env.example` / `.env.sample` / `.env.template` rows; (b) config-file-driven — list top-level sections from rows whose Format is `json` / `yaml` / `properties` / `exs` / `php` / `toml`. When both kinds of rows exist, render (a) first and (b) second under the same H3. See `how-to-run-sections.md` §Environment Setup for the exact templates. Never include real secret values — only describe what each variable or section is for.
7. **Build** — explicit compile/link command for compiled stacks (e.g., `cmake --build build --config Debug`). Omit for interpreted stacks where build is conflated with run. **MUST render both Debug and Release code fences** when the detected build system is one of {CMake, MSBuild, .NET, Xcode}; Step 6 verification rejects a single-fence Build section. See `how-to-run-sections.md` §Build for the *Default skeleton — multi-configuration build systems*.
8. **Running in Development** — the primary dev command(s) OR the command to launch the produced binary OR the engine launcher. What URL/port to expect for web/server stacks, what window/output to expect for desktop/game stacks. **Pick the layout from the Components-table row count** per the *Component count → layout* table in `how-to-run-sections.md` §Running in Development; that section also documents when the optional `Verify:` line applies. For docker-only setups (Dockerfile + docker-compose + no obvious local-run scripts): Docker-based instructions as the primary path inside the chosen layout.
9. **Running Tests** — test command, coverage command if available.
10. **Common Issues** — only if clear signals exist (e.g., `.nvmrc` → mention `nvm use`; docker services → mention `docker compose up -d` must run first; private registry → mention authentication; submodules → mention `git submodule update --init --recursive` after pull). **Verify bullets:** when a service in External Services is *Docker-preferred* (or *Docker (offline)* was kept by the user via the Step 4 multi-select downgrade prompt) AND has an entry in `external-services-docker.md` §Verify Commands (seeds), emit a `**Verify <service> is reachable.**` bullet rendering that seed verbatim — placeholder substitution (`<name>`, `<password>`, `<user>`) and MongoDB row selection per `external-services-docker.md` §Verify Commands (seeds). Apply §Verify Commands' *Stale-tag re-validation rule* before rendering — drop the bullet entirely if validation fails or the catalogue row has no seed. **Diagnostic ladders:** when a ladder's *Trigger* in `how-to-run-sections.md` §Diagnostic Ladders fires (Docker-mapped service for the "Container running but host can't connect" ladder), render the ladder verbatim from `how-to-run-sections.md` with placeholder substitution from the matching detector outputs.

**Content principles:**
- Direct, imperative instructions ("Install dependencies:" not "You should install dependencies")
- Exact commands with detected package manager and build system (from `tech-stack-detection.md` prefix rules and `detection-signals.md` build-system rows)
- Version numbers from manifest / build-file constraints only — never guess versions
- Commands ordered as a new developer would run them (prerequisites → toolchain → source deps → install → services → env → build → run)
- For monorepos: workspace-level install first, then per-subproject run instructions. The 6+ component case is handled by item 8's *Component count → layout* table — do NOT also emit inline per-subproject listings.
- **Workspace-aware commands.** When the detector's *Workspace kind* field is not `none`, use the Install / Build / Run / Test commands from `how-to-run-sections.md` §Workspace-Kind Command Branches for that kind instead of the per-package PM forms in §Package Manager Command Forms. The wrong form is a silent failure — `cargo build` in the root of a Cargo workspace builds only the root crate, not all members.
- For docker-only dev setups: Docker-based instructions as primary path, bare-metal as secondary if discernible
- **Table of contents:** count the rendered catalog sections from items 1-10 above (each rendered as H3 in the single-project / monorepo template, or as H2 in the multi-repo workspace template under their topology-specific names — `## Setup` counts as item 4 *Installation*, `## Environment Setup` counts as item 6 *Environment Setup* (the multi-repo template renders this BEFORE `## Setup` — see `how-to-run-sections.md` §Multi-Repo Workspace HOW-TO-RUN Template for the rationale), `## Running Everything` counts as item 8 *Running in Development*; the workspace template's `## Repositories` topology header does NOT count). Per-service / per-component / Quick-start subheadings inside a catalog section do NOT count. When the count is 7 or more, render a `## Contents` block (linked bullet list) immediately after the H1 heading; otherwise omit it. Step 6's *Template-shape audit* matches the literal `## Contents` heading.
- **Verify before including:** any content sourced from existing docs (README.md, CONTRIBUTING.md, etc.) must match the detector's Context Detection Results. Contradictions go to the Step 6 "Outdated info elsewhere" report and are NOT copied into `HOW-TO-RUN.md`.
- **Candidate services** (detector Task 5b rows with `Confidence: candidate`): render in the External Services overview table with a `(candidate)` marker in the Service column (e.g., `OpenIdConnect (candidate)`), and in the per-service subsection heading. Do NOT emit a per-service `AskUserQuestion` prompt for candidates — the user already reviewed and approved the Context Summary in Step 1 and can drop any incorrect candidate via the Step 1 "Correct first" flow. Silent inclusion (no marker) is disallowed because the reader cannot otherwise distinguish a config-file grep hit from a compose-confirmed service. **Exception — all-candidate compression:** see `how-to-run-sections.md` §External Services for the canonical rule (threshold, marker drop, overview-sentence template).
- **Render once, not twice.** When the same fact would be expressed in two adjacent sections, render it in the section closer to the action and link from the other. Concretes:
  - (a) When ≥3 shared-cloud services share the same source config file, drop the per-service "Update `<key>` in `<config file>`" line and render a single overview sentence at the top of External Services — see `how-to-run-sections.md` §External Services rule **Per-service "Update `<key>` in `<config file>`" consolidation** for the canonical rule body and overview-sentence template.
  - (b) For multi-repo workspaces, render the primary `git clone` only in the workspace template's *Source Dependencies / Clone All* H2; do not re-emit clone instructions under the workspace template's *Setup* H2 (the multi-repo equivalent of Installation).
  - (c) When every Components-table row shares the same parent directory, drop the per-component `(from <component-path>/)` parentheticals — see `how-to-run-sections.md` §Running in Development *Compact multi-component layout* for the canonical `From <shared-parent>/` rendering.
  - (d) When `Verify:` would only re-state the `Expected result:` URL with no additional probe (e.g., `Verify: open http://...`), drop `Verify:`. A `curl -fsS …` probe adds a status-code check and is not "the same URL".
- **Humanize caveats.** Apply `external-services-docker.md` §Web-Search Recipe step 3 *Caveat rendering* for every Step-4-emitted caveat — that section owns the canonical phrasings and the full list of caveat kinds (moving-tag rejection, LocalStack tier gate, ARM fallback).
- **Reject unverifiable exact counts.** Do not write exact numeric counts ("15 `.csproj` projects", "23 services", "7 subprojects") unless Step 6 verification can re-derive the count from the filesystem via `Glob`. When the detector cannot confirm a count, use "multiple", "several", or omit the quantifier entirely. Exception: counts the detector explicitly reports (subproject enumeration, environment variable counts, repo counts in a multi-repo workspace) are verified by construction and may be cited verbatim.
- **Never assert an unobserved path.** Do not render a specific filesystem path (e.g., `scripts/database/26.10.00/`, `migrations/0042_add_users.py`, `docs/release/2026.03/`) in prose unless the path appears verbatim in one of the detector's return-format tables (Source Dependencies, Environment Setup, Schema Bootstrap, Subprojects, Repos) or the path can be re-observed via `Glob` at Step 6 time. When the doc needs to reference "the latest version folder" or "the newest migration", use a generic phrasing — "the latest folder under `scripts/database/`", "the newest file under `migrations/`" — and do NOT extrapolate a leaf name from the version string in package metadata, from the current date, or from general knowledge. Paths from manifests, lock files, and explicit detector enumerations are verified by construction and may be cited verbatim.
- **Never guess runtime ports.** Runtime port numbers in `Expected result:` lines, troubleshooting bullets, and any URL of the form `http://localhost:<N>` or `http://127.0.0.1:<N>` must come from the detector's Runtime Ports table (Task 5c) OR from the detector's External Services table Port column (compose / config-file ports). When no bound port is found for a component, OMIT the port from the `Expected result:` URL — write `Expected result: <component> starts listening (see <launch-config-file> for the bound port).` Never substitute a framework default port.
- **Schema Bootstrap.** When the detector emits ≥2 schema-bootstrap mechanisms targeting the same database, OR the destination DB row's *Recommended runtime* is `Docker-preferred` (or the user kept *Docker (offline)*), apply `how-to-run-sections.md` §Schema Bootstrap — that section owns the pick-one precedence (ORM > raw-SQL, with seed/fixture rows rendered as a follow-up bullet after schema) and the connection-mode-aware invocation forms. For *Local install only* services, keep the detector's bare invocation hint.
- **Reconcile rendered commands against project script runners.** When the rendered Running / Build / Test command is `<tool> <subcmd> --<flag>` AND a same-named script exists in `package.json` / `Justfile` / `Makefile` / `*.csproj` launchSettings, open the script body. If the flag is absent from the script, render the bare-tool form (e.g., `npx ng serve --configuration=local`) instead of `npm run <script>` — a same-named script with a different flag set is the doc-bug class behind "I ran what the doc said, got the wrong environment".
- **Explain non-idiomatic wrapper commands.** When the detected dev/build/test command is a wrapper that invokes non-obvious additional steps, render a single-line `> <wrapper> runs: <expanded form>` explanation below the code block. See `how-to-run-sections.md` §Running in Development for the exact template and when to skip (direct aliases like `npm run dev` → `next dev`).
- **Approved unverifiable items (from Step 3):** for each entry in the `approved-unverifiable-items` list, render it as a sentence or bullet in the matching aspect's section, with the inner content in the exact form `Per <source_file> "<source_heading>": <sanitized_text>` (e.g., `Per README.md "Source Dependencies": Developers without access can still build the frontend, but custom theming will be missing.`); `source_file` and `source_heading` were already validated/sanitized at record time and render as-is. Before rendering, sanitize `text` and screen every markdown construct (links, images, reference-style definitions) per `$CLAUDE_PLUGIN_ROOT/skills/how-to-run/references/unverifiable-content-sanitization.md` §Render-time sanitization — entries that fail any check there are **removed** from the list (so their `rendered_line` cannot remain unset and accidentally exempt blank lines in Step 6). If the entry passes every check, store the full rendered line — exactly as it will be written to `HOW-TO-RUN.md`, including any leading list marker (`- `, `* `, `1. `) or indentation — back into the entry's `rendered_line` field so Step 6 can exempt it by exact match.

## Step 5: Place Content

**Write scope (repeat):** The only file this skill is ever permitted to create or modify is `HOW-TO-RUN.md` at the project / workspace root. Never modify `README.md`, `CONTRIBUTING.md`, `docs/*`, `BUILDING.md`, `INSTALL.md`, or any other file — not even to add a link. Existing docs are input only.

**Approval rule:**
- **If `HOW-TO-RUN.md` does not exist yet:** write it directly without asking for approval. The user already approved the plan in Step 3 and there is nothing to overwrite.
- **If `HOW-TO-RUN.md` already exists:** show the full diff (section-by-section when updating, full content when replacing) and wait for user approval before writing. Never silently replace existing content in a file that already exists.

### Placement rules by topology

**Single project:** Create or update `HOW-TO-RUN.md` at the repo root.

**Monorepo:** Create or update `HOW-TO-RUN.md` at the repo root, covering whole-project scope — workspace-level install, how to start shared services, how to run specific subprojects, how to run everything together.

**Multi-repo workspace:** Create or update `HOW-TO-RUN.md` at the workspace root. Direct-to-the-point content: repo map (name, path, purpose), how to clone all repos (submodules if applicable), shared prerequisites, how to start shared external services, how to run the full system. This file is not version-controlled (the workspace root has no `.git`).

### When dev instructions already live in README.md / CONTRIBUTING.md / etc.

No `AskUserQuestion` prompt. The skill silently copies any *verified* content from those files into `HOW-TO-RUN.md` (verification happened in Step 2 + Step 4 against the detector's results). Source files are not modified and the original content stays where it is. Any *contradicting* content is logged for the Step 6 "Outdated info elsewhere" report and is NOT copied into `HOW-TO-RUN.md`. Any *unverifiable* content was already resolved in Step 3's per-item user prompts.

### Cautious editing rules (for existing HOW-TO-RUN.md)

- **Never delete** existing content outside the sections being replaced.
- Preserve formatting, badges, images, and links inside sections not being updated.
- If the existing `HOW-TO-RUN.md` structure is too unusual to safely update a section, show the generated content to the user and ask where to place it manually.

## Step 6: Verify and Report

If no files were modified (skip or no-action path), skip verification and proceed directly to the report.

- Read back the modified or created `HOW-TO-RUN.md`.
- **Verify:** all commands use the correct package manager prefix, prerequisite versions match manifest constraints, build-system commands correspond to the detected build files, submodule paths in `HOW-TO-RUN.md` actually exist in `.gitmodules`, sibling-repo paths actually appear in build/CI files, directory paths match the actual filesystem, external service names match docker-compose service definitions, environment variable names match `.env.example`.
- **Run the full audit suite** — read `$CLAUDE_PLUGIN_ROOT/skills/how-to-run/references/step6-verification-audits.md` now and apply every audit in it to the written file: Verify External Services subsections, Section ordering audit, Pre-Conditions Block audit, Re-validate detector-sourced tokens (incl. the `approved-unverifiable-items` / `rendered_line` exact-match exemption), Specific-Token Audit (the `grounded-tokens` set), Unverified-Count filter, and Template-shape audit (OS-version line in Prerequisites, Build Debug+Release pair, Running-in-Development layout vs Components-table row count, `Verify:` permitted only for ≤2 components, TOC threshold).
- **If any check fails:** show the correction to the user, wait for approval, apply it, then re-verify.

**Report** to the user: what was created or updated in `HOW-TO-RUN.md`, which sections were included, and any aspects that were intentionally skipped (with reason).

**Outdated info found in other files (not modified):** Grouped by source file, list every fact the auditor found in `README.md` / `CONTRIBUTING.md` / `BUILDING.md` / `INSTALL.md` / `docs/*` that contradicted the detector's Context Detection Results. For each entry show: source file + heading + the documented text + what the detector found instead + suggested fix for the user to apply manually. Make explicit: **"The skill did NOT modify any of these files. They are listed so you can update them yourself if you want them to match reality."** If no contradictions were found, state "No stale setup info found in other files."

**Recommend next skill:**
- If `HOW-TO-RUN.md` was created or updated in a single project or monorepo: recommend `/optimus:commit` to commit the new or modified file. Skip this bullet for multi-repo workspaces — the workspace-root `HOW-TO-RUN.md` is not version-controlled (Step 5) — and fall through to the next matching recommendation.
- If `/optimus:init` has not been run (no `.claude/.optimus-version`): recommend `/optimus:init` for AI-assisted development setup.
- If test instructions were thin or absent: recommend `/optimus:unit-test` to establish test coverage.
- Otherwise: recommend `/optimus:tdd` for new feature work.

Tell the user the closing tip per `$CLAUDE_PLUGIN_ROOT/references/skill-handoff.md` "Closing tip wording" — if the recommendation above is `/optimus:commit`, use **Variant B** with `<continuation-skill(s)>` = `/optimus:commit` and `<non-continuation-examples>` = `/optimus:init`, `/optimus:unit-test`, `/optimus:tdd`, etc. Otherwise, use **Variant C** (default).
