# How-to-Run Section Templates

Section templates and signal-to-content mapping for generating `HOW-TO-RUN.md`. Referenced by the Project Environment Detector agent (for signal detection) and Step 4 (for content generation).

## Contents

- [Signal → Section Mapping](#signal--section-mapping)
- [Section Skeletons](#section-skeletons) (Prerequisites, Toolchain & SDKs, Source Dependencies, Installation, External Services, Environment Setup, Build, Running in Development, Running Tests, Common Issues)
- [Scaling Guidance](#scaling-guidance)
- [Package Manager Command Forms](#package-manager-command-forms)
- [Additional Detection Hints](#additional-detection-hints)
- [Build System Detection](#build-system-detection)
- [Source Dependencies Detection](#source-dependencies-detection)
- [External Services Detection](#external-services-detection)
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
| `docker-compose.yml` / `compose.yml` with infrastructure services | External Services (docker compose up) |
| External service detected but no `docker-compose.yml` covers it | External Services (per-service Docker-vs-local decision via [`external-services-docker.md`](external-services-docker.md)) |
| `Dockerfile` / `Dockerfile.dev` without local-run scripts | Running in Development (Docker-based primary) |
| `.env.example` / `.env.sample` / `.env.template` | Environment Setup |
| `prisma/schema.prisma`, `alembic.ini`, migration directories | Installation (post-install: migrations) |
| `build_runner` in Dart dev_dependencies, protobuf configs, codegen configs | Installation (post-install: code generation) |
| `.npmrc`, `pip.conf`, `.pypirc`, Maven `settings.xml` | Prerequisites (private registry auth) |
| `Makefile` / `Justfile` with `dev`/`start`/`setup` targets | Running in Development (mention make target) |
| `Procfile` / `Procfile.dev` | Running in Development (process runner) |
| `.devcontainer/devcontainer.json` | Prerequisites (devcontainer as primary path), Running in Development (devcontainer launch) |
| `flake.nix` / `shell.nix` / `default.nix` | Prerequisites + Installation (`nix develop` / `nix-shell` replaces manual toolchain setup) |
| `mise.toml` / `.mise.toml` | Prerequisites (version manager — alongside `.tool-versions`) |
| `template.yaml` (AWS SAM) / `serverless.yml` / `serverless.ts` | Running in Development (`sam local start-api` / `serverless offline`) |
| Test framework in dependencies + test script in manifest | Running Tests |

## Section Skeletons

### Prerequisites

```markdown
### Prerequisites

- [OS version constraint if detected — e.g., "Windows 11 22H2 or later", "macOS 13+"]
- [Hardware if detected — e.g., "NVIDIA GPU with CUDA 12+", "USB serial port for flashing"]
- [Runtime] [version constraint from manifest] ([version manager] recommended if config file detected)
- [Additional runtime for heterogeneous monorepo]
- [Docker](https://www.docker.com/) (if docker-compose detected — for running external services)
- [System tool] (if detected: make, protoc, etc.)
```

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

```markdown
### Source Dependencies

[If .gitmodules detected — recommend recursive clone:]

Clone with all submodules:

\`\`\`bash
git clone --recursive <repo-url>
cd "<project-name>"
\`\`\`

If you already cloned without `--recursive`:

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

```markdown
### Installation

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

[If database migrations detected:]

Run database migrations:

\`\`\`bash
<migration command>
\`\`\`
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

**Branch B — no compose file:** render a per-service overview table, then an H3 subsection per service using the templates in [`external-services-docker.md`](external-services-docker.md) — *Docker-preferred*, *Shared-cloud primary, Docker optional*, or *Local install only*.

**Hybrid — compose covers only some services:** render Branch A (the `docker compose up -d` block) for the services the compose file includes, listing those services in the Service/Port/Purpose table. Then append Branch B (overview table + per-service H3 subsections) scoped to the uncovered services only. Do not duplicate a compose-covered service as a standalone H3 subsection.

```markdown
### External Services

[One-paragraph summary: how many services, where connection details live, which services use shared cloud vs. local infrastructure.]

| Service | Recommended runtime | Alternative | Role |
|---------|---------------------|-------------|------|
| [service] | [Docker-preferred / Local install only / Shared-cloud primary (<provider>)] | [Docker (offline) / Local install / —] | [role] |

[Per service — render ONE of the three templates from `external-services-docker.md`. Cite every Docker image reference with a "- Source: [<title>](<url>)" line pointing at the vendor page. Never use a bare `:latest` tag when the vendor docs offer a stable versioned tag.]
```

Rules that apply to both branches:

- The detector's *External Services* table is the source of truth for which services exist.
- Service classification (GUI / CLI / cloud-native-only short-circuits, localhost-daemon → Docker-preferred, cloud-endpoint → Shared-cloud primary) is owned by the Decision Heuristics in [`external-services-docker.md`](external-services-docker.md). Apply those rules; do not re-derive them here.
- For credentials, note that the service uses defaults from docker-compose or shared-cloud config — never copy actual password values into the file.

### Environment Setup

```markdown
### Environment Setup

Copy the example environment file:

\`\`\`bash
cp .env.example .env
\`\`\`

[List key variables from .env.example with brief descriptions of what they configure. Do not include secret values — only describe what each variable is for.]
```

### Build

```markdown
### Build

\`\`\`bash
<build command — e.g., cmake --build build --config Debug>
\`\`\`
```

For build systems with multiple configurations (CMake, MSBuild, .NET), show both Debug and Release:

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

Include this section only for compiled stacks where build is distinct from run (C/C++, Rust release builds, Go with explicit compile, .NET publish, Java/Kotlin, Swift, Unreal/Unity cook, PlatformIO). Skip for interpreted stacks (Node, Python, Ruby) unless there is a distinct production build step useful for developers.

### Running in Development

Pick the sub-template that matches the detected run mode:

**(a) Script / dev server — web or interpreted backends**

```markdown
### Running in Development

\`\`\`bash
<dev command from manifest scripts>
\`\`\`

[Expected result: URL, port, or output to verify it works]

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

[Expected result]
```

**(b) Compiled artifact — C/C++, Rust, Go binary, .NET, Swift**

```markdown
### Running in Development

Run the produced binary:

\`\`\`bash
<path/to/built/binary [args]>
\`\`\`

[Where the binary lands — e.g., "build/Debug/myapp.exe" on Windows, "build/myapp" on Linux/macOS]

[Expected result: window, console output, or port]

[Common command-line flags if documented or obvious from source]
```

**(c) Engine launcher — Unreal / Unity / Godot**

```markdown
### Running in Development

Open the project in [engine]:

1. Launch [engine] [version]
2. Open `<project file>` (e.g., `MyProject.uproject`, the project folder for Unity/Godot)
3. [Engine-specific run step — e.g., "Press Play in the editor" or "Click Play button"]

[Expected result: what you should see]
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

## Scaling Guidance

**Monorepo with many subprojects:** When a monorepo has more than 5 subprojects, use a quick-reference table in "Running in Development" instead of inline per-subproject listings:

```markdown
| Subproject | Dev command | URL / port |
|------------|-------------|------------|
| [name] | `<command>` | [URL or port] |
```

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

## External Services Detection

Common docker-compose image patterns → human-readable names. The *Docker suitability* column is a lookup table consulted by the Decision Heuristics in [`external-services-docker.md`](external-services-docker.md) at Step 3 — the detector does not emit this field; Step 3 derives it by matching service name / image pattern against the rows below. This lets Step 4 skip a web search for obvious GUI tools and short-circuit classification for well-known server daemons.

| Image pattern | Service name | Docker suitability |
|---------------|-------------|-------------------|
| `postgres`, `postgis` | PostgreSQL | daemon |
| `mysql`, `mariadb` | MySQL/MariaDB | daemon |
| `mongo` | MongoDB | daemon |
| `redis` | Redis | daemon |
| `mcr.microsoft.com/mssql/server`, any `mssql`-prefixed name | SQL Server | daemon |
| `elasticsearch`, `opensearch` | Elasticsearch/OpenSearch | daemon |
| `rabbitmq` | RabbitMQ | daemon |
| `kafka`, `confluentinc` | Kafka | daemon |
| `memcached` | Memcached | daemon |
| `minio` | MinIO (S3-compatible storage) | daemon |
| `localstack` | LocalStack (AWS services) | daemon |
| `mailhog`, `mailpit` | Mail server (dev) | daemon |
| `keycloak` | Keycloak (auth) | daemon |
| `nginx`, `traefik`, `caddy` | Reverse proxy | daemon |

Service-name-only patterns (no image) that Step 4 encounters when the detector found them from config files rather than compose. **Match whole tokens, not substrings** — a pattern hits only when it matches a word bounded by whitespace, punctuation, or start/end of the service name. Examples: `Thumb` must not match `thumbor`; `CLI` matches `AWS CLI` but not `AppServiceCLI`; `Studio` matches `Azure Data Studio` but not `StudioBuilder`.

| Service name pattern (case-insensitive) | Docker suitability |
|----------------------------------------|-------------------|
| `SSMS`, `Management Studio`, `Compass`, `Workbench`, `DBeaver`, `Azure Data Studio`, `Studio 3T`, `RedisInsight`, `pgAdmin` | gui-client |
| `AWS CLI`, `Azure CLI`, `gcloud CLI`, `kubectl`, or any name ending with a standalone `CLI` token (whitespace- or punctuation-bounded) | cli-tool |
| `Firebase`, `Firestore`, `License Manager`, or any internal-sounding name without a public image | cloud-native-only |
| Any other unknown name | unknown — web-search recipe decides |

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

## Setup

[Per-repo install commands, or a setup script if one exists]

## External Services

[Shared infrastructure from docker-compose across repos]

## Running Everything

[How to start all services/apps together]
```
