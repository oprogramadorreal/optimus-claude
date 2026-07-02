# How-to-Run Detection Signals

Detection tables for generating `HOW-TO-RUN.md`: signal-to-section mapping, build-system signals, and source-dependency signals. Provided to the Project Environment Detector agent as context in Step 1 and consulted by Step 4 to decide which sections to generate. Section render templates live in [`how-to-run-sections.md`](how-to-run-sections.md).

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
| Detector's Components table (Task 5d) with ≥1 runnable component (`Microsoft.NET.Sdk.Web` + `Microsoft.NET.Sdk.Worker`, `cmd/*/main.go`, `[[bin]]` entries in Cargo, Procfile lines, Rails + Sidekiq, etc.) | Running in Development — layout selected by row count per the *Component count → layout* table in [`how-to-run-sections.md`](how-to-run-sections.md) §Running in Development |
| Detector's Runtime Ports table (Task 5c) entry for a component | Running in Development (cited in that component's `Expected result:` URL — no port = omit URL, never substitute a framework default) |

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
