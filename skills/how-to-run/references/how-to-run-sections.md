# How-to-Run Section Templates

Section templates and signal-to-content mapping for generating `HOW-TO-RUN.md`. Referenced by the Project Environment Detector agent (for signal detection) and Step 4 (for content generation).

## Contents

- [Signal → Section Mapping](#signal--section-mapping)
- [Section Skeletons](#section-skeletons) (Prerequisites, Toolchain & SDKs, Source Dependencies, Installation, External Services, Environment Setup, Build, Running in Development, Running Tests, Common Issues)
- [Scaling Guidance](#scaling-guidance)
- [Workspace-Kind Command Branches](#workspace-kind-command-branches)
- [Package Manager Command Forms](#package-manager-command-forms)
- [Additional Detection Hints](#additional-detection-hints)
- [Build System Detection](#build-system-detection)
- [Source Dependencies Detection](#source-dependencies-detection)
- [Schema Bootstrap](#schema-bootstrap)
- [Section Depends-On Graph](#section-depends-on-graph)
- [Diagnostic Ladders](#diagnostic-ladders)
- [Multi-Repo Workspace HOW-TO-RUN Template](#multi-repo-workspace-how-to-run-template)

## Signal → Section Mapping

| Signal | Section(s) to Generate |
|--------|----------------------|
| `engines.node`, `python_requires`, `rust-version`, `environment.sdk` | Prerequisites (runtime version) |
| `.nvmrc`, `.node-version`, `.python-version`, `.tool-versions`, `rust-toolchain.toml` | Prerequisites (version manager) |
| `CMakeLists.txt`, `meson.build`, `BUILD.bazel`, `*.sln`, `*.vcxproj`, `Makefile` (as build system) | Toolchain & SDKs (compiler), Build, Running in Development (produced artifact) |
| `vcpkg.json`, `conanfile.txt` / `conanfile.py` | Toolchain & SDKs (vcpkg / Conan bootstrap), Installation (vendored deps) |
| `.gitmodules` | Source Dependencies (`git clone --recursive` / `git submodule update --init --recursive`) |
| CMake `FetchContent_Declare`, `ExternalProject_Add`, `add_subdirectory(../*)`, hardcoded `../sibling` paths in build/CI files | Source Dependencies (sibling repos) |
| `*.uproject`, `ProjectSettings/ProjectVersion.txt` (Unity), `project.godot` | Toolchain & SDKs (engine version), Running in Development (engine launcher) |
| `*.xcodeproj`, `*.xcworkspace`, `Podfile`, `Package.swift` | Toolchain & SDKs (Xcode version), Build, Running in Development (simulator/device) |
| `build.gradle`, `settings.gradle`, `AndroidManifest.xml` | Toolchain & SDKs (JDK, Android SDK), Build, Running in Development |
| `platformio.ini`, `.ino` files | Toolchain & SDKs (PlatformIO / Arduino, target board), Prerequisites (target MCU hardware), Build, Running in Development (flash) |
| Vulkan / CUDA / Qt / JDK / .NET SDK / MSVC references in build files or existing READMEs | Toolchain & SDKs (SDK install) |
| GPU / USB / serial / specific OS hints in existing READMEs or build files | Prerequisites (hardware / OS) |
| README mentions of browsers (Chrome/Chromium), IDEs (Visual Studio, VS Code, IntelliJ family), DB GUI clients (SSMS, DBeaver, pgAdmin), API tools (Postman, ngrok) — see detector Task 0d2 | Prerequisites (recommended developer tools — bullet list separate from hardware/OS requirements) |
| `docker-compose.yml` / `compose.yml` with infrastructure services | External Services (docker compose up) |
| External service detected but no `docker-compose.yml` covers it | External Services (per-service Docker-vs-local decision via [`external-services-docker.md`](external-services-docker.md)) |
| Framework config file with service-shaped sections (`appsettings*.json`, `application.yml`, `config/*.exs`, `config/*.yml`, `config.yaml`, etc. — see detector Task 5b) | External Services (Branch B per-service subsections, rendered with a `(candidate)` marker; user can drop via Step 1 "Correct first") |
| `Dockerfile` / `Dockerfile.dev` without local-run scripts | Running in Development (Docker-based primary) |
| `.env.example` / `.env.sample` / `.env.template` | Environment Setup |
| `prisma/schema.prisma`, `alembic.ini`, migration directories | Installation (post-install: migrations) |
| `build_runner` in Dart dev_dependencies, protobuf configs, codegen configs | Installation (post-install: code generation) |
| `.npmrc`, `pip.conf`, `.pypirc`, Maven `settings.xml` | Prerequisites (private registry auth) |
| `Makefile` / `Justfile` with `dev`/`start`/`setup` targets | Running in Development (mention make target) |
| `Procfile` / `Procfile.dev` | Running in Development (process runner) |
| `.devcontainer/devcontainer.json` | Prerequisites (devcontainer as primary path), Running in Development (*Quick start (Dev Container)* subsection rendered ABOVE the per-component layout) |
| `flake.nix` / `shell.nix` / `default.nix` | Prerequisites + Installation (`nix develop` / `nix-shell` replaces manual toolchain setup) |
| `mise.toml` / `.mise.toml` | Prerequisites (version manager — alongside `.tool-versions`) |
| Setup scripts from Dev Workflow Signals (`bootstrap.sh`, `bin/setup`, `scripts/bootstrap.*`, etc.) | Installation (*One-shot setup* block rendered BEFORE the per-PM install commands — reader can run one script or follow the manual steps) |
| `.pre-commit-config.yaml` | Prerequisites (`pre-commit install` post-clone), Common Issues (CI will reject commits when hooks skipped) |
| `.envrc` (direnv) | Prerequisites (`direnv allow` post-clone), Common Issues (env vars only load inside project dir when direnv is active) |
| `mkcert` references in scripts | Prerequisites (`mkcert -install` once per dev machine), Common Issues (OAuth / webhook / SameSite cookie flows require local HTTPS) |
| `template.yaml` (AWS SAM) / `serverless.yml` / `serverless.ts` | Running in Development (`sam local start-api` / `serverless offline`) |
| Test framework in dependencies + test script in manifest | Running Tests |
| Detector's Components table (Task 5d) with ≥1 runnable component (`Microsoft.NET.Sdk.Web` + `Microsoft.NET.Sdk.Worker`, `cmd/*/main.go`, `[[bin]]` entries in Cargo, Procfile lines, Rails + Sidekiq, etc.) | Running in Development — layout selected by row count per the *Component count → layout* table below |
| Detector's Runtime Ports table (Task 5c) entry for a component | Running in Development (cited in that component's `Expected result:` URL — no port = omit URL, never substitute a framework default) |

## Section Skeletons

### Prerequisites

```markdown
### Prerequisites

- [OS version constraint — MANDATORY when Task 0d returned an OS-version token; render the canonical token verbatim as the first bullet (e.g., "Windows 10 or 11", "macOS 13+", "Ubuntu 22.04+"). Skip only when Task 0d returned no OS-version token.]
- [Hardware if detected — e.g., "NVIDIA GPU with CUDA 12+", "USB serial port for flashing"]
- [Runtime] [version constraint from manifest] ([version manager] recommended if config file detected)
- [Additional runtime for heterogeneous monorepo]
- [Docker](https://www.docker.com/) (if docker-compose detected — for running external services)
- [System tool] (if detected: make, protoc, etc.)

[If the detector's Recommended Developer Tools table has entries, render a separate sub-list under the bullets above:]

**Recommended developer tools**

- [Token] — [why it helps for this project, e.g., "Chrome / Chromium: the Karma test runner starts a headless Chrome", "SSMS: GUI browser for the SQL Server database", "Visual Studio: IDE the README assumes"].
```

Rendering rules for *Recommended developer tools*:
- Only emit when the detector produced at least one row. Never invent tools from general knowledge.
- One bullet per detected token, in the order the detector returned them. When 12+ tokens, render the first 12 plus a single "+N more — see READMEs" line.
- Keep each bullet short (one line). The "why" clause is optional — skip it when no obvious project-specific reason can be derived from detection context (e.g., a token found with no surrounding semantics).

### Toolchain & SDKs

```markdown
### Toolchain & SDKs

- **[Build tool]** [min version from build file] — [link or install hint]
- **[Compiler]** [min version] ([per-OS install notes])
- **[Domain SDK]** [version if detected] — [official install URL]

[If multiple OSes are plausible, group install commands per OS:]

**Windows**

\`\`\`powershell
<winget or choco install commands>
\`\`\`

**macOS**

\`\`\`bash
<brew install commands>
\`\`\`

**Linux**

\`\`\`bash
<apt / dnf / pacman install commands>
\`\`\`
```

Only include this section when the project has a non-trivial compile/build step or a detected SDK dependency. Pure web/script projects can usually skip it and rely on Prerequisites.

### Source Dependencies

Scope rule: **Source Dependencies is fix-after-clone only.** The primary `git clone` lives in the Installation section below; this section documents what must be pulled or initialized after the main clone.

```markdown
### Source Dependencies

[If .gitmodules detected:]

This repo uses git submodules. On a fresh clone, use the `--recursive` form shown in the Installation section below. If you already cloned without it, initialize the submodules now:

\`\`\`bash
git submodule update --init --recursive
\`\`\`

[If sibling repos detected — list each with path and clone URL:]

This project expects the following sibling repositories to be cloned alongside it:

| Repo | Expected path | Clone URL |
|------|---------------|-----------|
| [name] | `../[dir]` | [url if detected] |

Clone them before building:

\`\`\`bash
cd ..
git clone <url> [dir]
cd "<project-name>"
\`\`\`

[If CMake FetchContent/ExternalProject detected — note that deps are fetched automatically at configure time:]

External sources are fetched automatically by CMake during configuration — no manual cloning required.
```

### Installation

When the detector's *Setup scripts* signal is set, render a *One-shot setup* block IMMEDIATELY after the clone command and BEFORE the per-PM install commands. The reader can run one script or follow the manual steps below — both get to the same place.

```markdown
[One-shot setup block — render only when the detector's *Setup scripts* signal has entries. Use the first entry as the primary invocation; list any additional entries as alternatives.]

**One-shot setup (preferred):**

\`\`\`bash
<path from detector's Setup scripts signal, e.g., ./bootstrap.sh, bin/setup, ./setup.ps1>
\`\`\`

[If the signal lists >1 script, append: "Alternate setup scripts: `<script 2>`, `<script 3>`." — don't auto-pick between them.]

This runs the cumulative install + migrations + seeds pass in one command. If the script fails or you need to reproduce its individual steps, follow the manual flow below instead.

**Manual setup:**
```

```markdown
### Installation

[If .gitmodules is present at the repo root:]

Clone the repository with submodules:

\`\`\`bash
git clone --recursive <repo-url>
cd "<project-name>"
\`\`\`

[Otherwise:]

Clone the repository:

\`\`\`bash
git clone <repo-url>
cd "<project-name>"
\`\`\`

[For projects with language-level package managers:]

Install dependencies:

\`\`\`bash
<package-manager install command>
\`\`\`

[If vcpkg.json detected:]

Install C++ dependencies via vcpkg:

\`\`\`bash
vcpkg install
\`\`\`

[If conanfile detected:]

Install C++ dependencies via Conan:

\`\`\`bash
conan install . --build=missing
\`\`\`

[If code generation detected:]

Generate code:

\`\`\`bash
<codegen command>
\`\`\`

[If ORM migration tooling, raw SQL bootstrap scripts, or seed files detected — emit the Schema Bootstrap sub-block shown below inside the Installation section (no sub-heading; the block lives under Installation's H3). **Pick exactly one mechanism as primary** per the [§Schema Bootstrap](#schema-bootstrap) precedence rule and render the matching invocation. Demote any other detected mechanisms to a "Legacy / alternative" callout — never present two schema-creating mechanisms as fungible (applying both an ORM migration history and a hand-maintained `DatabaseNew.sql` against the same database usually produces a conflicting schema). For *Docker-preferred* destination DBs, render the **full host-side invocation** per [§Schema Bootstrap](#schema-bootstrap) §Connection-mode-aware invocation rather than the detector's bare hint.]

Initialize database schema:

- **Primary:** `<primary-invocation>`.
- [Optional: when ≥2 mechanisms detected, render the demoted one(s) as a 2-space-indented `  > **Legacy alternative:** <demoted-invocation> — pre-dates the migration tooling above and applying both can conflict; use only when explicitly instructed by the project's docs.` blockquote directly under the Primary bullet — the 2-space indent keeps the blockquote inside the Primary bullet's list item; an unindented `>` would terminate the list.]
- [If seed / fixture-load rows exist alongside an ORM or raw-SQL primary — they never compete with schema mechanisms — render them as a follow-up bullet: "After the schema is in place, populate seed data: `<seed-invocation>`".]
```

### External Services

When deciding Docker vs. local install vs. shared-cloud per service, follow the heuristics, web-search recipe, and snippet templates in [`external-services-docker.md`](external-services-docker.md). Docker is never forced — local installs and shared-cloud endpoints stay first-class options.

**Branch A — `docker-compose.yml` / `compose.yml` covers all infrastructure services:**

```markdown
### External Services

This project requires the following services for local development:

| Service | Port | Purpose |
|---------|------|---------|
| [service name] | [port from compose] | [role: database, cache, queue, etc.] |

Start all services:

\`\`\`bash
docker compose up -d
\`\`\`

Verify services are running:

\`\`\`bash
docker compose ps
\`\`\`
```

**Branch B — no compose file:** render a per-service overview table, then a per-service subsection per service using the templates in [`external-services-docker.md`](external-services-docker.md) — *Docker-preferred*, *Shared-cloud primary (Docker optional)*, *Shared-cloud, no Docker alternative*, or *Local install only*.

**Hybrid — compose covers only some services:** render Branch A (the `docker compose up -d` block) for the services the compose file includes, listing those services in the Service/Port/Purpose table. Then append Branch B (overview table + per-service subsections) scoped to the uncovered services only. Do not duplicate a compose-covered service as a standalone subsection.

```markdown
### External Services

[One-paragraph summary: how many services, where connection details live, which services use shared-cloud vs. local infrastructure.]

| Service | Recommended runtime | Alternative | Role |
|---------|---------------------|-------------|------|
| [service] | [Docker-preferred / Local install only / Shared-cloud primary (<provider>)] | [Docker (offline) / Local install / —] | [role] |

[Per service — render the matching template from `external-services-docker.md`. Cite every Docker image reference with a "- Source: [<title>](<url>)" line pointing at the vendor page. Never use a bare `:latest` tag when the vendor docs offer a stable versioned tag.]
```

Rules that apply to both branches:

- The detector's *External Services* table is the source of truth for which services exist.
- Service classification (Docker-preferred / Shared-cloud primary / Local install only) is owned by the Decision Heuristics in [`external-services-docker.md`](external-services-docker.md). Apply those rules; do not re-derive them here.
- For credentials, note that the service uses defaults from docker-compose or shared-cloud config — never copy actual password values into the file.
- **All-candidate compression.** When ≥3 services in the External Services table share `Confidence: candidate` AND no row is `confirmed`, drop the `(candidate)` marker from the per-service subsection headings and from the *Service* column of the overview table. Render a single overview sentence at the top of *External Services* instead — for example: "Services below were detected from `<config file>` rather than a compose file. Drop any incorrect rows via *Correct first* in Step 1." The marker discriminates only when mixed with confirmed rows; in an all-candidate table it conveys no signal.
- **Per-service "Update `<key>` in `<config file>`" consolidation.** When ≥3 shared-cloud services in this section share the same source config file, do NOT emit the per-service "Update `<ConfigKey>` in `<config file>` when pointing at a different environment" line under each per-service subsection. Instead, render a single overview sentence at the top of *External Services*: "The shared-cloud endpoints below come from `<config-file>`; swap them per environment by editing the matching config key listed in [Environment Setup](#environment-setup)." Keep the per-service line only when there are ≤2 services or when the services span multiple config files.

### Environment Setup

Pick the sub-template that matches the detector's Environment Setup table. When only one kind of file exists, render only that sub-template (including its `### Environment Setup` heading). When both a dotenv file AND framework config files exist, emit the `### Environment Setup` heading once at the top and then render (a)'s body and (b)'s body **without** their own headings — strip the `### Environment Setup` line from each inner template block before pasting its body.

**(a) Dotenv-driven environment**

Use when the detector reports at least one Environment Setup row with `Format: dotenv`.

```markdown
### Environment Setup

Copy the example environment file:

\`\`\`bash
cp .env.example .env
\`\`\`

[List key variables from .env.example with brief descriptions of what they configure. Do not include secret values — only describe what each variable is for.]
```

**(b) Config-file-driven environment (non-dotenv stacks)**

Use when the detector reports Environment Setup rows with `Format: json` / `yaml` / `properties` / `exs` / `php` / `toml`. When (a) is NOT rendered above (no dotenv file detected), open with the stand-alone sentence: `There is no <code>.env.example</code> template. Local configuration lives in...`. When (a) IS rendered above, drop the "There is no `.env.example` template." sentence and open with `Additionally, local configuration lives in...`.

```markdown
### Environment Setup

There is no `.env.example` template. Local configuration lives in `<config file>` (format: `<format>`). The file is committed with development defaults; override locally by editing it or by setting the matching runtime environment variables.

Top-level sections that require values before running locally:

- `<SectionName>` — <one-line description derived from section-name semantics>. Keys you will edit: `<leaf1>`, `<leaf2>`, `<leaf3>`.
- ...

[If the detector truncated the section list at 25 per file:] See `<config file>` for the full list of <N> sections.

[If the detector's *Secrets committed* field for this file is `yes`, render the Caution block below IMMEDIATELY after the section list:]

> **Caution: `<config file>` appears to contain live credentials.** Audit the file's values before running the project — the detector flagged credential-shape, not authenticity. Confirm whether the file is git-tracked with `git ls-files --error-unmatch <config file>` before treating this as a leaked-secret incident. If tracked, rotate the exposed keys, move local copies to a locally-ignored overlay (e.g., `appsettings.Local.json` / `.env.local`), and put the rotated production values in your team's secret store.

**Never commit real secrets.** Treat any key whose name matches `(?i)(key|secret|password|token|credential|private)` as sensitive.
```

Rendering rules:
- One bullet per detected top-level section, in the order the detector returned them (alphabetical when the detector truncated).
- Derive the one-line description from section-name semantics only — never from the file's values. Example hints: `AWS` → "AWS SDK credentials and region"; `RedisSettings` → "Redis connection string and pool sizing"; `OpenIdConnect` → "OIDC authority and client credentials". When the semantics are ambiguous, emit the section name with no description (a bare bullet is better than a wrong guess).
- **Keys you will edit:** append this clause only when the detector's `Key leaves` column has entries for the section — parse the cell by splitting on `; ` to isolate sections, then split each section's `<Section>: <leaf1>, <leaf2>, <leaf3>` on `:` to isolate its leaves, and render up to 3 leaves joined by `, ` for the matching section (the detector already caps at 3). Omit the clause entirely when the detector emitted `—` (dotenv files or sections with no first-level leaves worth surfacing).
- Include the "See `<config file>` for the full list of <N> sections." footnote only when the detector reports `Variable count` > 25. Omit otherwise.
- Render the Caution block only when the detector's `Secrets committed` column is `yes`. The block goes immediately after the section list and before the "Never commit real secrets" line — the Caution is specific to this file's observed state; the final line is the general rule.

### Build

**Default skeleton — multi-configuration build systems (CMake, MSBuild, .NET, Xcode).** Render BOTH Debug and Release code fences.

```markdown
### Build

Debug (for development):

\`\`\`bash
<build command --config Debug>
\`\`\`

Release (optimized):

\`\`\`bash
<build command --config Release>
\`\`\`
```

**Single-configuration skeleton — Cargo / Go / single-output build systems.** Render one fence.

```markdown
### Build

\`\`\`bash
<build command — e.g., cargo build --release, go build ./...>
\`\`\`
```

Include this section only for compiled stacks where build is distinct from run (C/C++, Rust release builds, Go with explicit compile, .NET publish, Java/Kotlin, Swift, Unreal/Unity cook, PlatformIO). Skip for interpreted stacks (Node, Python, Ruby) unless there is a distinct production build step useful for developers.

### Running in Development

Pick the sub-template that matches the detected run mode. **The `Expected result:` line is mandatory in every sub-template.** When no concrete check is available (no port, window, or stdout to assert), emit the literal placeholder `Expected result: <unknown — verify manually>`.

**Optional `Verify:` line.** Permitted only in the 1- and 2-component layouts. When the Components table has ≥3 rows, OMIT every `Verify:` line — individual probes belong in *Common Issues* per the *Component count → layout* rules below. Otherwise, append a single `Verify:` line below the `Expected result:` line when a natural health probe exists for the component. Keep it to one command the reader can run from their terminal:

- Web / API with an HTTP port (grounded via the Runtime Ports table) → `` Verify: `curl -fsS http://localhost:<port>/` `` — or the detected health endpoint if one is documented (`/healthz`, `/health`, `/_/health`, `/-/health`).
- Database service → `` Verify: `pg_isready -h localhost` `` (Postgres), `` Verify: `mysqladmin ping -h 127.0.0.1` `` (MySQL), `` Verify: `redis-cli ping` `` (Redis), `` Verify: `mongosh --eval 'db.runCommand({ ping: 1 })'` `` (Mongo).
- Frontend dev server → `Verify:` open `http://localhost:<port>/` in a browser; the dev server's hot-reload banner should appear within ~5 seconds.
- Worker / scheduler (no port) → OMIT the `Verify:` line. Workers' health is best observed through their own logs or the job-queue dashboard, not via a single probe command; offering a wrong probe is worse than offering none.

Never fabricate an endpoint path — when unsure, omit the `Verify:` line. The `Expected result:` line is the mandatory assertion; `Verify:` is the optional "how to confirm it".

**Quick start (Dev Container) — prepend when the detector's *Containerized dev env* signal is set.** Render this block as an H4 subsection INSIDE the `### Running in Development` H3, immediately under the section heading and above the per-component layout content selected by the *Component count → layout* table below. A single `### Running in Development` H3 wraps the whole section — never emit two sibling H3s. The dev container is usually the simplest path when one is provided.

```markdown
#### Quick start (Dev Container)

If you use VS Code, open the cloned repo and choose *Dev Containers: Reopen in Container* (requires the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) and Docker Desktop). The container build runs the setup steps in `.devcontainer/devcontainer.json`; you can skip the manual Installation and run the per-component commands below once it finishes.

For a terminal-only workflow (no VS Code), install the [dev container CLI](https://github.com/devcontainers/cli) and run `devcontainer up --workspace-folder .`.
```

**Component count → layout.** Pick the layout from the row count of the detector's Components table (excluding the `No runnable components detected.` sentinel and any `+N more` overflow row):

| Components | Layout |
|------------|--------|
| 0 | Omit the entire *Running in Development* section — the repo is a library. |
| 1-2 | *Flat layout* — sub-template (a) / (b) / (c); render one block per component. No `Boot order:` block. |
| 3-5 | *Compact multi-component layout* — numbered Boot-order list + flat per-component bullets. No per-component H4 subsections. |
| 6+ | *Scaling Guidance* quick-reference table from §[Scaling Guidance](#scaling-guidance) — one row per component (Subproject / Component, Path, Dev command, URL/port). No H4 subsections, no per-component bullets. |

**Compact multi-component layout (3-5 components).**

```markdown
### Running in Development

[Apply *Render once, not twice* (c) from SKILL.md Step 4: when every Components-table row shares the same parent directory, render `From <shared-parent>/` once here; otherwise omit this line and prepend `(from <component-path>/)` to each numbered bullet's start command below.]

**Boot order:** start external services first (`docker compose up -d` or the per-service snippets above), run any one-time migrations / schema bootstrap (from [Installation](#installation)), then start each component in a separate terminal in the order below. A component that lists `Requires: <other-component>` must start AFTER that other component.

1. **<Component A>** (`<kind>`) — `<start command>`. Expected result: <URL / port / stdout assertion>. Requires: <services + components, or "—">.
2. **<Component B>** (`<kind>`) — `<start command>`. Expected result: <URL / port / stdout assertion>. Requires: <services + components, or "—">.
3. **<Component C>** (`<kind>`) — `<start command>`. Expected result: <URL / port / stdout assertion>. Requires: <services + components, or "—">.
[continue for 4-5 components — never exceed 5 here; emit the Scaling Guidance table when the count reaches 6.]

[Wrapper-command expansion lines, if applicable — one `> <wrapper> runs: <expanded form>` line per component below the numbered list.]
```

**Flat layout (1-2 components).** Emit a single `### Running in Development` H3, render any Quick start block as an H4 nested under it, then fall through to sub-template (a) / (b) / (c) below with the sub-template's own `### Running in Development` line stripped. For the 2-component case, render two adjacent sibling blocks.

**(a) Script / dev server — web or interpreted backends**

```markdown
### Running in Development

\`\`\`bash
<dev command from manifest scripts>
\`\`\`

Expected result: <URL / port / stdout line the reader can check — e.g., "Server listening on http://localhost:3000" — or the placeholder above when unknowable>.

[If the detected dev command is a wrapper (a shell script / npm-script alias that executes additional steps beyond the idiomatic tool invocation), add a single-line explanation below the code block:]

> `<wrapper command>` runs: `<expanded form, e.g., "npm run export-scss-vars && ng serve">`.

[For monorepos — workspace-level:]

Run everything:

\`\`\`bash
<workspace dev command if available>
\`\`\`

Run a specific subproject:

\`\`\`bash
<per-subproject command, e.g., "pnpm --filter @scope/app dev">
\`\`\`

[For Docker-based primary:]

\`\`\`bash
docker compose up
\`\`\`

Expected result: <service list or URL the reader can check>.
```

**(b) Compiled artifact — C/C++, Rust, Go binary, .NET, Swift**

```markdown
### Running in Development

Run the produced binary:

\`\`\`bash
<path/to/built/binary [args]>
\`\`\`

Where it lands: <e.g., "build/Debug/myapp.exe" on Windows, "build/myapp" on Linux/macOS>.

Expected result: <window / console output / port the reader can check — or the placeholder above>.

[Common command-line flags if documented or obvious from source]
```

**(c) Engine launcher — Unreal / Unity / Godot**

```markdown
### Running in Development

Open the project in [engine]:

1. Launch [engine] [version]
2. Open `<project file>` (e.g., `MyProject.uproject`, the project folder for Unity/Godot)
3. [Engine-specific run step — e.g., "Press Play in the editor" or "Click Play button"]

Expected result: <viewport content / PIE-mode indicator / title-screen stanza the reader can check — or the placeholder above>.
```

### Running Tests

```markdown
### Running Tests

\`\`\`bash
<test command>
\`\`\`

[If coverage command available:]

With coverage:

\`\`\`bash
<coverage command>
\`\`\`
```

### Common Issues

Only include if clear signals exist. Examples:

- `.nvmrc` detected → "Run `nvm use` before installing dependencies to ensure the correct Node.js version."
- `.mise.toml` / `.tool-versions` detected → "Run `mise install` (or `asdf install`) to activate the correct runtime versions."
- Docker services required → "Ensure `docker compose up -d` is running before starting the application."
- Private registry → "Authenticate with the private registry before running install: `<auth command>`."
- Code generation → "If you see missing file errors after pulling, re-run `<codegen command>`."
- Git submodules → "After pulling, run `git submodule update --init --recursive` if submodule contents appear stale."
- Sibling repos → "Build will fail if the expected sibling repo is not cloned at the documented path."
- Multiple build configurations (C/C++, .NET) → "Use `--config Debug` for development or `--config Release` for optimized builds."
- Python virtualenv → "Activate the virtual environment before running commands: `source .venv/bin/activate` (Linux/macOS) or `.venv\Scripts\activate` (Windows)."
- Windows host + Docker service published with `-p 127.0.0.1:<port>:<port>` → "Host can't reach `localhost:<port>` but `docker exec` works. Windows resolves `localhost` to `::1` (IPv6); the container is bound to `127.0.0.1` (IPv4) only. Use `127.0.0.1` explicitly in connection strings, or rebind the container with `-p <port>:<port>` to drop the IPv4-only restriction." Render this single-bullet form only when (a) the detector's *Hardware / OS Requirements* table contains `Windows 10`, `Windows 11`, or `Windows`, AND (b) at least one service in External Services rendered a Docker snippet using the `-p 127.0.0.1:<host-port>:<container-port>` form (the §Snippet Templates default for both *Docker-preferred* and *Shared-cloud primary (Docker optional)* templates), AND (c) the [§Diagnostic Ladders](#diagnostic-ladders) "Container running but host can't connect" ladder did NOT fire (when the ladder fires, its step 3 already covers the same IPv4/IPv6 advice — emitting both produces duplicate bullets in Common Issues). The rule fires once per project regardless of how many services use the form — list affected service names parenthetically when more than one.

For multi-layer failure modes that benefit from a symptom→layered-checks playbook (e.g., "container running but host can't connect" — single-bullet preventive form is too thin), render a [diagnostic ladder](#diagnostic-ladders) instead of a single-line bullet. Ladders fire conditionally on the detector's outputs (Docker-mapped service, schema-bootstrap row, etc.) per §Diagnostic Ladders.

## Scaling Guidance

Quick-reference table skeleton for the 6+ row case selected by *Component count → layout* above — replaces inline per-component listings entirely (no H4 subsections, no per-component bullets).

```markdown
| Subproject | Path | Dev command | URL / port |
|------------|------|-------------|------------|
| [name] | `<path>` | `<command>` | [URL or port — from the Runtime Ports table; omit when no port is grounded] |
```

## Workspace-Kind Command Branches

When the detector sets `Workspace kind` to something other than `none`, use the workspace-aware commands below instead of (or in addition to) the per-package PM commands. The point of these branches is correctness: `cargo build --workspace` builds all crates in a Cargo workspace; `cargo build` in the root builds only the root crate. `go work sync` resolves modules referenced by `go.work`; `go mod download` does not. Writing the wrong form is a silent failure — the build succeeds but only half the code compiled.

| Workspace kind | Install | Build (all) | Build (one) | Run (one) | Test (all) |
|----------------|---------|-------------|-------------|-----------|------------|
| `npm-workspaces` | `npm install` (at root) | `npm run build --workspaces --if-present` | `npm run build --workspace=<pkg>` | `npm run <script> --workspace=<pkg>` | `npm test --workspaces --if-present` |
| `pnpm-workspaces` | `pnpm install` (at root) | `pnpm -r build` | `pnpm --filter <pkg> build` | `pnpm --filter <pkg> <script>` | `pnpm -r test` |
| `yarn-workspaces` | `yarn install` (at root) | `yarn workspaces foreach -A run build` | `yarn workspace <pkg> build` | `yarn workspace <pkg> <script>` | `yarn workspaces foreach -A run test` |
| `lerna` | `npm install` (root) | `npx lerna run build` | `npx lerna run build --scope=<pkg>` | `npx lerna run <script> --scope=<pkg>` | `npx lerna run test` |
| `nx` | `npm install` (root) | `npx nx run-many -t build` | `npx nx build <pkg>` | `npx nx serve <pkg>` / `npx nx run <pkg>:<target>` | `npx nx run-many -t test` |
| `turbo` | `npm install` (root) | `npx turbo run build` | `npx turbo run build --filter=<pkg>` | `npx turbo run <script> --filter=<pkg>` | `npx turbo run test` |
| `cargo-workspace` | — (Cargo resolves automatically) | `cargo build --workspace` | `cargo build -p <crate>` | `cargo run -p <crate>` | `cargo test --workspace` |
| `go-workspace` | `go work sync` (at root — resolves modules declared in `go.work`) | `go build ./...` (at root — walks every module in `go.work` on Go ≥1.18) | `go build ./<module>/...` | `go run ./<module>` (or `./cmd/<name>`) | `go test ./...` |
| `gradle-multi-module` | — (Gradle resolves automatically) | `./gradlew build` | `./gradlew :<module>:build` | `./gradlew :<module>:run` | `./gradlew test` |
| `maven-multi-module` | — (Maven resolves automatically) | `mvn install` (from repo root; `-DskipTests` for a faster dev build) | `mvn -pl <module> -am install` | `mvn -pl <module> exec:java` (if configured) | `mvn test` |

Render the Install row under Installation, the Build-all row under Build, and the per-module Run rows under Running in Development (one per component from the detector's Components table). Fall back to the per-package `Package Manager Command Forms` table below only when `Workspace kind: none`.

## Package Manager Command Forms

Use the detected PM from `tech-stack-detection.md`. Common mappings:

| PM | Install | Run script | Run dev | Run tests | Run build |
|----|---------|-----------|---------|-----------|-----------|
| npm | `npm install` | `npm run <script>` | `npm run dev` | `npm test` | `npm run build` |
| pnpm | `pnpm install` | `pnpm run <script>` | `pnpm run dev` | `pnpm test` | `pnpm run build` |
| yarn | `yarn install` | `yarn <script>` | `yarn dev` | `yarn test` | `yarn build` |
| bun | `bun install` | `bun run <script>` | `bun run dev` | `bun test` | `bun run build` |
| pip | `pip install -r requirements.txt` | — | varies | `pytest` | — |
| poetry | `poetry install` | `poetry run <cmd>` | varies | `poetry run pytest` | `poetry build` |
| uv | `uv sync` | `uv run <cmd>` | varies | `uv run pytest` | `uv build` |
| cargo | — | `cargo <cmd>` | `cargo run` | `cargo test` | `cargo build` |
| go | `go mod download` | `go <cmd>` | `go run .` | `go test ./...` | `go build` |
| dotnet | `dotnet restore` | `dotnet <cmd>` | `dotnet run` | `dotnet test` | `dotnet build` |
| flutter | `flutter pub get` | `flutter <cmd>` | `flutter run` | `flutter test` | `flutter build` |
| dart | `dart pub get` | `dart run <cmd>` | `dart run` | `dart test` | `dart compile` |
| bundler | `bundle install` | `bundle exec <cmd>` | varies | `bundle exec rspec` | — |
| cmake | — | — | — | `ctest` | `cmake --build build` |
| gradle | — | `./gradlew <task>` | `./gradlew run` | `./gradlew test` | `./gradlew build` |
| nx | — | `npx nx run <project>:<target>` | `npx nx serve <project>` | `npx nx test <project>` | `npx nx build <project>` |
| turbo | — | `npx turbo run <script>` | `npx turbo dev` | `npx turbo test` | `npx turbo build` |

Use the actual script names from the project's manifest (e.g., `pnpm run start:dev` not `pnpm run dev` if the script is named `start:dev`).

## Additional Detection Hints

These are additional detection signals beyond `tech-stack-detection.md`. The detector should also identify any other build system, SDK, or tooling it recognizes from the project structure — **the reference tables are not exhaustive**. For any unrecognized manifest or build file, identify the stack from general knowledge and report it in the same structured format.

Build-system detection rules are in the *Build System Detection* table below. The additions listed here supplement that table with signals not covered by manifest-driven detection:

- **C/C++ dependency managers:** vcpkg, Conan
- **Toolchain SDKs:** JDK (from `sourceCompatibility` in the Gradle row), MSVC Build Tools (from `<PlatformToolset>` in the MSBuild row). For `.NET SDK`, see init's `tech-stack-detection.md` (`*.csproj`, `*.sln`) — the baseline detection handles it.
- **CMake `find_package` libraries:** For any `find_package(X)` call in CMakeLists.txt, report X as a potential SDK/library dependency with its source location. The main skill will determine which require explicit install documentation in the Toolchain & SDKs section.

## Build System Detection

Common build-system signals and what to extract:

| File | Build system | Extract |
|------|-------------|---------|
| `CMakeLists.txt` | CMake | `cmake_minimum_required(VERSION ...)`, `project(... LANGUAGES ...)`, `find_package(...)` calls (→ SDKs) |
| `meson.build` | Meson | `project('name', ['cpp'], meson_version : '...')` |
| `BUILD.bazel`, `WORKSPACE` | Bazel | Root `WORKSPACE` dependencies |
| `*.sln`, `*.vcxproj` | MSBuild / Visual Studio | `<PlatformToolset>`, `<WindowsTargetPlatformVersion>` |
| `*.xcodeproj`, `*.xcworkspace` | Xcode | Scheme names, deployment target |
| `build.gradle`, `settings.gradle`, `AndroidManifest.xml` | Gradle / Android | `sourceCompatibility` (JDK), `compileSdkVersion`, `minSdkVersion` |
| `*.uproject` | Unreal Engine | `EngineAssociation` field (engine version) |
| `ProjectSettings/ProjectVersion.txt` | Unity | `m_EditorVersion` field |
| `project.godot` | Godot | `config/features=PackedStringArray("4.2", ...)` |
| `platformio.ini` | PlatformIO | `platform`, `board`, `framework` |
| `*.ino` | Arduino | Board from comment headers or `arduino-cli.yaml` |
| `Package.swift` | Swift Package Manager | `swift-tools-version` |
| `Podfile` | CocoaPods | `platform :ios, 'X.Y'` |
| `Makefile` (as build system, not task runner) | make | Default target, compiler inference |

## Source Dependencies Detection

Patterns to detect source dependencies that must be cloned or initialized before building:

| Source | Pattern | Meaning |
|--------|---------|---------|
| `.gitmodules` at repo root | Any content | Git submodules present — recommend `git clone --recursive` and document submodule update |
| `CMakeLists.txt` / `*.cmake` | `FetchContent_Declare` | CMake auto-fetches at configure time — document that network is required for first configure |
| `CMakeLists.txt` / `*.cmake` | `ExternalProject_Add` | Same as FetchContent but heavier |
| `CMakeLists.txt` | `add_subdirectory(../<name>)` or `add_subdirectory(${CMAKE_SOURCE_DIR}/../<name>)` | Sibling repo expected — document path + clone URL (if grep'd from CI/README) |
| CI files (`.github/workflows/*.yml`, `azure-pipelines.yml`, `.gitlab-ci.yml`) | `git clone ... ../<name>` or hardcoded `../<name>` in working-directory | Sibling repo expected — document |
| Existing `README.md` / `BUILDING.md` / `INSTALL.md` | Phrases: "clone alongside", "sister repo", "requires the X repo", "must be checked out at ../" | Sibling repo expected — document (treat as candidate, cross-check with build-file signals) |
| `west.yml` (Zephyr) | `manifest: projects:` blocks | West workspace — document `west init` / `west update` |
| `repo` tool / `default.xml` (Android AOSP-style) | Any content | Document `repo sync` flow |

**Precision rule:** Sibling-repo detection from a `../[A-Za-z0-9_][A-Za-z0-9._-]*` path grep WILL produce false positives (e.g., `../node_modules/...`, `../dist/`). Report findings as *candidates* in the detector's Source Dependencies table with their source line and let the user confirm via Step 3's assessment — do not treat them as facts without cross-file corroboration.

## Schema Bootstrap

Precedence rule and connection-mode-aware invocation forms for the Installation section's Schema Bootstrap sub-block. Two principles drive the design: (a) **Pick exactly one mechanism as primary** — applying two schema-creating mechanisms against the same database usually produces conflicting schemas (a hand-maintained `DatabaseNew.sql` and an ORM migration history rarely produce the same shape, and re-running an ORM migration after the SQL bootstrap leaves the migration table out of sync). (b) **Connection-mode-aware invocation** — the detector's bare `<tool> -i <file>` hint defaults to the local-default-instance + Windows-auth / peer-auth path, which is the wrong default when the destination DB lives in Docker.

### Pick-one rule

Inputs:

- Detector's *Database migrations* row in *Dev Workflow Signals* (e.g., `prisma`, `alembic`, `flyway`, `ef`, `liquibase`, `knex`, `sequelize`, `typeorm`, `gorm`, `rails`, `phoenix-ecto`).
- Detector's *Schema Bootstrap* table rows, with their `Bootstrap mechanism` field set to `raw-sql`, `seed-script`, or `fixture-load`.

Precedence (apply in order; first match selects the **primary** mechanism):

1. **ORM migration tool detected.** When *Database migrations* is set to a recognized tool, render the ORM's migrate command from the table below as the primary mechanism. Demote any `raw-sql` rows in *Schema Bootstrap* to a "Legacy / alternative — superseded by ORM migrations" callout.
2. **Raw-SQL bootstrap detected (no ORM).** When *Schema Bootstrap* contains `raw-sql` rows and no ORM is detected, the first row by detector report order is primary. Demote any further `raw-sql` rows to "Alternative bootstrap script" callouts.
3. **Seed / fixture only.** When only `seed-script` / `fixture-load` rows exist, render them as the primary "after schema is in place, populate seed data: …" step. Seeds populate data, not schema, so they never compete with ORM/raw-SQL mechanisms — when both seeds AND a schema mechanism exist, render the schema mechanism first and the seed step as a follow-up bullet (the Installation template already shows this two-bullet layout).

ORM migrate-command catalog (consumed by precedence rule 1):

| ORM tool | Migrate command |
|---|---|
| `prisma` | `npx prisma migrate deploy` |
| `alembic` | `alembic upgrade head` |
| `flyway` | `flyway migrate` |
| `ef` / Entity Framework Core | `dotnet ef database update` |
| `liquibase` | `liquibase update` |
| `knex` | `npx knex migrate:latest` |
| `sequelize` | `npx sequelize db:migrate` |
| `typeorm` | `npm run typeorm migration:run` (or the project's `package.json` script that wraps `typeorm migration:run`) |
| `gorm` | (no CLI — schema is migrated in code via `db.AutoMigrate(...)`; render the callout `> Schema is migrated in application code via GORM \`AutoMigrate\` — there is no separate migrate command.` instead of an invocation) |
| `rails` | `bundle exec rails db:migrate` |
| `phoenix-ecto` | `mix ecto.migrate` |

Demoted mechanisms render as a 2-space-indented blockquote directly under the primary bullet (the 2-space indent keeps the blockquote inside the Primary bullet's list item; an unindented `>` would terminate the list) using this exact form:

  > **Legacy alternative:** `<demoted-invocation>` — pre-dates the migration tooling above and applying both can conflict; use only when explicitly instructed by the project's docs.

### Connection-mode-aware invocation

When the destination DB row's *Recommended runtime* (per the Step 3 assessment table; see [`external-services-docker.md`](external-services-docker.md) §Decision Heuristics) is `Docker-preferred` OR `Shared-cloud primary` with the *Docker (offline)* alternative kept by the user via the Step 4 multi-select downgrade prompt, replace the detector's bare invocation hint with the full host-side form below. For *Local install only* services, keep the bare form — the local default-instance + Windows-auth / peer-auth path is correct in those cases.

**Password handling (Docker-preferred / Docker (offline) forms below).** Each `sqlcmd` / `psql` / `mysql` row takes its password via the per-tool env var named in the *Password env var* column below; export it in the surrounding shell (`export <VAR>='<password-placeholder>'` in bash/zsh; `$env:<VAR> = '<password-placeholder>'` in PowerShell) before running the command. Use the per-tool command-line fallback flag (`sqlcmd -P`, `psql -W` interactive prompt, `mysql -p<pass>`) only when an env-var-based flow is not viable. `mongosh` keeps the password inside the connection URI — no env-var alternative.

| CLI | Bare form (Local install only) | Docker-preferred / Docker (offline) form | Password env var |
|---|---|---|---|
| `sqlcmd` (SQL Server) | `sqlcmd -i <file>` | `sqlcmd -S "<host>,<host-port>" -U <user> -C [-d <db>] -i <file>` | `SQLCMDPASSWORD` |
| `psql` (PostgreSQL) | `psql -f <file>` | `psql -h <host> -p <host-port> -U <user> -d <db> -f <file>` | `PGPASSWORD` |
| `mysql` (MySQL/MariaDB) | `mysql < <file>` | `mysql -h <host> -P <host-port> -u <user> <db> < <file>` | `MYSQL_PWD` |
| `mongosh` (MongoDB) | `mongosh --file <file>` | `mongosh "mongodb://<user>:<password-placeholder>@<host>:<host-port>/<db>?authSource=admin" --file <file>` | (password in URI) |

The `mongosh` form keeps the password inside the connection URI, which is visible in the host's process listing (`ps -ef`, `Get-Process | Select-Object CommandLine`) for the duration of the command — there is no env-var alternative the `mongosh` URI shape supports. On shared dev hosts (CI runners, multi-user VMs) prefer the per-tool secure-credential mechanisms even for the `psql` / `sqlcmd` / `mysql` env-var forms above — `~/.pgpass` (mode `0600`) for `psql` per [libpq docs](https://www.postgresql.org/docs/current/libpq-pgpass.html), `~/.my.cnf` (mode `0600`) for `mysql`, an `.sqlcmdrc` or shell-profile-scoped `SQLCMDPASSWORD` for `sqlcmd`. The env-var form is narrower than the command-line form (visible only in `/proc/<pid>/environ` on Linux, not in `ps`), but the credential-file form is narrower still.

ORM migrate commands from the catalog above are NOT enriched with connection flags — ORM tools read their connection details from the project's config files (`prisma/schema.prisma`, `alembic.ini`, `appsettings.json`, etc.) which Step 6's connection-string-shift audit already verifies match the recommended runtime. Substituting host/port into an ORM command would conflict with the ORM's own config-file connection.

Substitute every placeholder from the matching External Services snippet (the same snippet the External Services per-service subsection already rendered):

- `<host>` → `127.0.0.1` when the detector's *Hardware / OS Requirements* table contains `Windows 10`, `Windows 11`, or `Windows` (per [§Common Issues](#common-issues) IPv4/IPv6 caveat); else `localhost`.
- `<host-port>` → the port from the snippet's `-p <host>:<host-port>:<container-port>` line.
- `<user>` → the username from the snippet's matching `-e '<USER_VAR>=<value>'` line, OR the image's documented default — `sa` for SQL Server, `postgres` for Postgres, `root` for MySQL/MariaDB, the value of `MONGO_INITDB_ROOT_USERNAME` for MongoDB.
- `<password-placeholder>` → the placeholder from the snippet's matching `-e '<PASSWORD_VAR>=<placeholder>'` line, kept as a placeholder (`<MSSQL_SA_PASSWORD>`, `<POSTGRES_PASSWORD>`, etc.) — do NOT substitute a real value, since `HOW-TO-RUN.md` is committed.
- `<db>` → the schema-bootstrap target DB. Render as a placeholder `<db-name>` and let the reader fill it in; the bootstrap file's content (which the detector never reads) determines what's correct.

The Step 6 audit re-checks every rendered invocation: flags must come from the per-tool flag set above; placeholders must match the snippet's `-e` lines verbatim; `<host>` must follow the OS-aware substitution rule.

## Section Depends-On Graph

Cross-section dependency edges consumed by Step 6's *Section ordering audit*. Each edge says "the dependent section's actionable content must NOT appear before the prerequisite section's content in the rendered file when the trigger condition fires." The audit walks the file's catalog headings in render order — H3 in single-project / monorepo, H2 in multi-repo workspace (same topology-aware aliasing the TOC count rule uses) — and applies the row's *Resolution* on violation.

| Dependent | Prerequisite | Trigger condition | Resolution |
|---|---|---|---|
| Installation (Schema Bootstrap sub-block — ORM migrate, `<tool> -i <file>` / `<tool> -f <file>` / equivalent) | External Services | Destination DB row's Recommended runtime is `Docker-preferred` (or *Docker (offline)* was kept by the user) | **Auto-callout.** The DB container must be running before the bootstrap connects. When the rendered section order has Installation before External Services (the catalog default for single-project / monorepo, where item 4 precedes item 5), emit a `> **Pre-condition:** start the External Services Docker containers below before running the schema bootstrap commands above.` blockquote above the Schema Bootstrap sub-block. |
| Installation (Schema Bootstrap sub-block) | External Services (Pre-Conditions Block) | Destination DB row's Recommended runtime is `Docker-preferred` (or *Docker (offline)* was kept by the user) AND (`Endpoint semantics` is in `{local-windows-auth, local-named-instance, local-socket}` OR (`local-default` with the snippet's host-port differing from the committed port)) — mirrors `external-services-docker.md` §Pre-Conditions Block §Trigger | **Auto-callout.** The committed connection-string change must precede any schema-bootstrap command that connects to the DB. Emit a `> **Pre-condition:** apply the connection-string change shown in the External Services Pre-Conditions block before running the schema bootstrap commands above.` blockquote above the Schema Bootstrap sub-block. |
| Installation (language-level install commands — `npm install`, `pip install`, `dotnet restore`, `bundle install`, etc.) | Environment Setup | Detector's *Private registry* signal is set (`.npmrc`, `pip.conf`, `.pypirc`, Maven `settings.xml`) OR detector's *Local TLS cert* signal is `mkcert` | **Auto-callout.** Some installs require credentials or trusted root certs to be present first. Emit a `> **Pre-condition:** complete the auth / cert steps in Environment Setup before running the install commands above.` blockquote above the install commands. |
| Running in Development | Setup / Installation, External Services | Always | **Surface-to-user.** Dev server cannot start without deps installed and services running. Catalog order (item 8 follows items 4 and 5) enforces this in single-project / monorepo templates, so violations only fire when a topology template reorders sections. Surfacing avoids an auto-rewrite that could break the topology layout. |
| Build | Installation | Always | **Surface-to-user.** Compile / link needs dependencies installed. Catalog order (item 7 follows item 4) enforces this; violations are topology-driven. |
| Build | Source Dependencies | Detector's *Source Dependencies* table has submodules / FetchContent / approved sibling-repo rows | **Surface-to-user.** Submodule contents and sibling repos must be present before compile. Catalog order (item 7 follows item 3) enforces this; violations are topology-driven. |

The Pre-condition callouts the audit auto-renders are **idempotent** — a second audit pass on the same file detects an existing matching `> **Pre-condition:** …` line directly above the dependent's actionable content (line-after-trim equality match against the auto-callout text recorded in the audit's working set) and skips re-emitting it. This lets the audit re-run after a user fix-up without producing duplicate callouts.

### Audit-flow summary

1. Walk the rendered file's catalog headings in document order at the topology-appropriate level (H3 in single-project / monorepo, H2 in multi-repo workspace); build a `section-position` map (`<section-name> → integer index`).
2. For each row in the table above whose *Trigger condition* is satisfied by the detector's outputs:
   - Resolve the *Dependent* and *Prerequisite* sections to their positions.
   - When the dependent's position ≤ the prerequisite's position (i.e., dependent appears at or before prerequisite), fire the row's *Resolution*:
     - **Auto-callout** rows: emit (or verify the presence of) a `> **Pre-condition:** …` blockquote directly above the dependent's first actionable line. Record the callout text in the audit's working set so a re-run is idempotent.
     - **Surface-to-user** rows: report the conflict via the standard Step 6 fix-up flow with no auto-rewrite — reordering a topology template's section layout is an editorial decision the user needs to make.
3. Include any auto-rendered callouts in Step 6's "what was created/updated" report under a "Pre-condition callouts" sub-section.

## Diagnostic Ladders

For multi-layer failure modes that don't fit the single-sentence preventive bullet form of [§Common Issues](#common-issues) — typically "container is up but host can't connect", "tests pass locally but fail in CI", "auth flow returns 200 but the session is empty" — render a *diagnostic ladder*: a numbered list of symptom→check→action steps the reader walks top-down until one matches. Ladders fire conditionally on the detector's outputs and never replace the single-bullet form for simple gotchas (a `.nvmrc` ladder would be overkill for "run `nvm use`").

### Format

```markdown
- **<Symptom sentence ending with a question mark — what the reader observes>** Walk down this ladder:
  1. **<Check 1 — most common cause first>** — `<concrete diagnostic command>`. If <observable result>, <concrete action>.
  2. **<Check 2>** — `<command>`. If <result>, <action>.
  3. **<Check 3>** — `<command>`. If <result>, <action>.
```

Render the ladder as a top-level bullet under `### Common Issues`, sharing the bullet list with single-line entries. Every step's *check* must be a concrete diagnostic command (not a leading question), every *result* must be observable from the command's output, every *action* must be specific (not "investigate further").

### Library

#### Container running but host can't connect

**Trigger.** External Services has at least one service whose Recommended runtime is `Docker-preferred` (or *Docker (offline)* was kept).

```markdown
- **Host can't connect to <Service> on `<host>:<host-port>` but `docker ps` shows the container as `Up`?** Walk down this ladder:
  1. **Did the container actually finish starting?** `docker logs --tail 50 <project-slug>-<service-slug>`. First-boot for `<Service>` typically takes 10–20s; if the log shows recent startup messages but no readiness signal yet, wait 10s and retry the host connection.
  2. **Does the connection work from inside the container?** Run the `**Verify <service> is reachable.**` bullet from this section above. If it succeeds inside but the host still fails, the container is up — the problem is between the host and the published port (steps 3–5 below).
  3. **(Windows hosts) Is `localhost` resolving to IPv6?** Replace `localhost` with `127.0.0.1` explicitly in your client / connection string. The snippet publishes the container as `-p 127.0.0.1:<host-port>:<container-port>` (IPv4-only); Windows resolves `localhost` to `::1` (IPv6) first and the IPv6 lookup times out before falling back. (Render this step only when the detector's *Hardware / OS Requirements* table contains Windows.)
  4. **Is the host port actually mapped?** `docker port <project-slug>-<service-slug>`. The output should include `<container-port>/tcp -> 127.0.0.1:<host-port>` (or `0.0.0.0:<host-port>` if the snippet was rebound). If the listed mapping doesn't match what your connection string uses, recreate the container with the correct `-p`.
  5. **Is a non-Docker process holding the port?** `Get-NetTCPConnection -LocalPort <host-port>` (PowerShell) / `lsof -i :<host-port>` (macOS / Linux) / `netstat -ano | findstr :<host-port>` (Windows cmd). If the port is bound by a non-Docker process (e.g., a local install of `<Service>`), stop that process or republish the container on a different host-port.
```

Substitute `<service>`, `<host>`, `<host-port>`, `<project-slug>-<service-slug>`, and the per-Windows step from the rendered snippet's values. Step 2's *Verify* pointer references the bullet rendered earlier in the section (rendered from the matching §Verify Commands seed, which includes the `-e` env-var prefix when one applies — e.g., `-e SQLCMDPASSWORD='<password>'` for SQL Server); no command is re-rendered inside the ladder, so the env-var prefix is preserved by reference. Step 3 is rendered only when *Hardware / OS Requirements* contains Windows; on pure-Unix projects, drop step 3 and renumber.

#### Test command fails with database connection / authentication error

**Trigger.** External Services has at least one row whose `Type` is `database` AND the detector's *Commands* table has a non-empty `test` row (so a `<test command>` exists to render).

```markdown
- **`<test command>` fails with a database connection / authentication error?** Walk down this ladder:
  1. **Is the DB container running?** `docker ps --filter name=<project-slug>-<db-service-slug>`. The test run typically expects the same DB container as the dev environment; start it via the External Services snippet first if missing.
  2. **Did you apply schema bootstrap?** Tests run against either an empty schema or a seeded one — see Installation §Schema Bootstrap for the project's primary bootstrap command. Missing tables / fixtures often surface as authentication errors or `relation does not exist` rather than "table missing", because the framework's connection check runs before the query.
  3. **Does the test config override the dev connection string?** Frameworks commonly carry a separate test profile (Spring `application-test.yml`, Rails `database.yml` test env, ASP.NET `appsettings.Test.json`, Django `DATABASES['test']`). Verify it points at the same host:port as the rendered snippet — when the test profile inherits the committed default (e.g., `localhost\SQLEXPRESS` Windows-auth), apply the same connection-string change the External Services Pre-Conditions block describes for the dev profile.
  4. **(Docker-preferred DB) Did the bootstrap run with the host-side flags, not the bare form?** Per the host-side schema-bootstrap invocation in Installation, the destination DB in Docker requires the per-CLI full-flag form from §Schema Bootstrap §Connection-mode-aware invocation (`sqlcmd -S "<host>,<host-port>" …`, `psql -h <host> -p <host-port> …`, `mysql -h <host> -P <host-port> …`, or `mongosh "mongodb://…@<host>:<host-port>/…"`), not the bare `<tool> -i <file>` / `<tool> -f <file>` form; if the bootstrap silently used the bare form, it created the schema in a different DB (or failed silently against the local default instance) and the test connect doesn't see it.
```

Substitute `<test command>` from the detector's *Commands* table `test` row, `<project-slug>-<db-service-slug>` from the External Services row whose `Type` is `database` (kebab-cased per the slug rules in [`SKILL.md`](../SKILL.md) Step 4 item 5), and `<tool>` / `<host>` / `<host-port>` / `<user>` / `<password-placeholder>` from the matching [§Schema Bootstrap](#schema-bootstrap) §Connection-mode-aware invocation row already rendered in Installation. The ladder's step 3 references the Pre-Conditions block from [`external-services-docker.md`](external-services-docker.md) §Pre-Conditions Block; step 4 references the connection-mode-aware invocation table from §Schema Bootstrap above. Both are conditional renders driven by detector signals, so the ladder coheres with the rest of the rendered file.

## Multi-Repo Workspace HOW-TO-RUN Template

For workspace root (not version-controlled):

```markdown
# [Workspace Name] — How to Run

## Repositories

| Repo | Path | Purpose |
|------|------|---------|
| [name] | `./[dir]` | [brief purpose] |

## Source Dependencies / Clone All

[If the workspace has a meta-repo with submodules:]

\`\`\`bash
git clone --recursive <meta-repo-url>
\`\`\`

[Otherwise — list per-repo clones:]

\`\`\`bash
[clone commands for each repo]
\`\`\`

## Prerequisites

[Aggregated from all repos — OS, hardware, toolchain & SDKs]

## Environment Setup

[Per-repo env files and shared config keys to set before running Setup. Override any committed defaults that conflict with External Services choices (e.g., connection strings when a service runs in Docker but the committed default points at a local daemon).]

## Setup

[Per-repo install commands, or a setup script if one exists]

## External Services

[Shared infrastructure from docker-compose across repos]

## Running Everything

[How to start all services/apps together]
```

The catalog order (single-project / monorepo: items 1-10 in `SKILL.md` Step 4) places Environment Setup AFTER Installation and External Services. The multi-repo template intentionally lifts Environment Setup BEFORE Setup because per-repo Setup commands (language-level install, schema migrations, seed scripts, asset compilation) frequently read connection strings and credentials whose committed defaults must be overridden first — e.g., a private-registry token for `npm install`, a connection string for `dotnet ef database update` or `rails db:migrate`, an OAuth client secret for a build-time codegen step. The [§Section Depends-On Graph](#section-depends-on-graph) above catches the analogous case for single-project / monorepo templates without reordering them; in multi-repo the reorder is unconditional because workspace-level Setup typically aggregates per-repo migration commands across multiple language stacks, so the precondition risk is high enough to warrant the order change by default.
