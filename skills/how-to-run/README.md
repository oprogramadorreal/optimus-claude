# optimus:how-to-run

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that generates a `HOW-TO-RUN.md` teaching a new developer how to set up their environment and run the project locally. Writes only `HOW-TO-RUN.md` — never modifies any other file.

Many projects lack step-by-step "how to get this running on my machine" instructions, or have instructions scattered across `README.md`, `CONTRIBUTING.md`, and `docs/` that have drifted from the actual codebase. This skill detects the project's build system, toolchain, SDKs, source dependencies (git submodules, sibling repos), external services, environment config, and hardware/OS requirements, then generates (or updates) `HOW-TO-RUN.md` with user approval when overwriting an existing file.

## Features

- **Stack-agnostic.** Covers web apps, C/C++ desktop apps, native mobile, JVM/Android, game engines, embedded/firmware, and backend services with external infra. See [`references/how-to-run-sections.md`](references/how-to-run-sections.md) §*Additional Detection Hints* for the full catalog.
- Detects build system, toolchain, SDKs, runtime version constraints, and dev commands from manifests and build files
- Discovers source dependencies — git submodules from `.gitmodules`, sibling repos from CMake `FetchContent`/`ExternalProject`/hardcoded `../sibling` paths in build & CI files
- Discovers external services from docker-compose (databases, queues, caches) and generates startup instructions
- Also discovers external services from framework config files (`appsettings*.json`, `application.yml`, `config/*.exs`, Rails `config/*.yml`, Laravel `config/*.php`) — rendered with a `(candidate)` marker so compose-confirmed and config-file-inferred services are distinguishable
- When no `docker-compose.yml` covers a service, classifies each one as **Docker-preferred**, **Shared-cloud primary** (with Docker as offline alternative when a vendor image exists, otherwise shared-cloud only), or **Local install only**, and emits a `docker run` snippet with a vendor-cited image reference (never guessed from model memory). Vendor-branded cloud services (AWS S3/SNS/SQS, Azure Cosmos DB, Firebase, GCP Pub/Sub) resolve to their local emulators (LocalStack, Azurite, Firebase Local Emulator Suite, etc.) via the Vendor-Service → Emulator Index. GUI tools and CLI tools (see [`references/external-services-docker.md`](references/external-services-docker.md) §Service Classification Tables) always render as local install. Registry allowlist bounds supply-chain risk.
- Detects required SDKs and system packages (Vulkan, CUDA, Qt, JDK, .NET SDK, MSVC Build Tools) and hardware/OS requirements
- Detects schema-bootstrap scripts (raw `.sql` files, `db/seeds.rb`, `priv/repo/seeds.exs`, Django fixtures, Prisma seed scripts) alongside ORM migrations
- Detects recommended developer tools (browsers, IDEs, DB GUIs, API debuggers) mentioned in existing READMEs and surfaces them under Prerequisites
- Scans existing docs (`HOW-TO-RUN.md`, `README.md`, `CONTRIBUTING.md`, `BUILDING.md`, `INSTALL.md`, `docs/*`) as hypotheses and verifies every fact against the actual codebase
- Generates only applicable sections from a 10-item catalog: prerequisites, toolchain & SDKs, source dependencies, installation, external services, environment, build, running, testing, common issues
- **Write-only to `HOW-TO-RUN.md`** — never modifies any other file. Outdated info found elsewhere is reported to the user at the end so they can fix it manually.
- Cautious editing: first run writes directly, updates to an existing `HOW-TO-RUN.md` show the full diff and wait for approval
- Supports single projects, monorepos (whole-project scope), and multi-repo workspaces
- Works standalone or as a complement to `/optimus:init`

## Quick Start

This skill is part of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin. See the [main README](../../README.md) for installation instructions.

## Usage

In Claude Code:

- `/optimus:how-to-run`

The skill analyzes your project, scans existing documentation as hypotheses, and proposes a `HOW-TO-RUN.md`. First-run writes go through directly; updates to an existing `HOW-TO-RUN.md` require your approval.

## When to Run

- **After `/optimus:init`** — init sets up Claude Code; how-to-run creates the human-readable onboarding doc
- **When onboarding new developers** — ensure they can get started without tribal knowledge
- **After adding services, SDKs, submodules, or dependencies** — re-run to update `HOW-TO-RUN.md` and surface stale info elsewhere
- **On any project with missing or drifted setup docs** — even without running init first

## What It Creates / Modifies

| Topology | Target file | Version-controlled? |
|----------|------------|-------------------|
| Single project | Root `HOW-TO-RUN.md` (new or updated) | Yes |
| Monorepo | Root `HOW-TO-RUN.md` (whole-project scope) | Yes |
| Multi-repo workspace | Workspace root `HOW-TO-RUN.md` | No (workspace root has no `.git`) |

**Never modified by this skill:** `README.md`, `CONTRIBUTING.md`, `BUILDING.md`, `INSTALL.md`, `docs/*`, or any other file. Outdated setup info found in those files is reported to the user at the end for manual fixing.

### Generated sections (only applicable ones)

1. **Prerequisites** — OS version constraints, hardware requirements, system tools, version managers, plus a *Recommended developer tools* sub-list when browsers, IDEs, DB GUIs, or API tools are mentioned in existing docs
2. **Toolchain & SDKs** — compiler, build-tool versions, language SDKs, domain SDKs (Vulkan/CUDA/Qt/JDK/.NET). Per-OS install commands when multiple OSes are plausible.
3. **Source Dependencies** — git submodules, sibling repos, CMake FetchContent
4. **Installation** — clone, language-level deps, vendored deps (vcpkg/Conan), post-install (code generation, migrations)
5. **External Services** — docker-compose services with ports and purpose, or per-service Docker-preferred / Shared-cloud primary / Local install only rendering when compose does not cover the service (with vendor-cited image references). Framework-config-discovered services render with a `(candidate)` marker.
6. **Environment Setup** — either dotenv-driven (copy `.env.example`, describe variables) or config-file-driven (list top-level sections from `appsettings*.json` / `application.yml` / `config/*.exs` / etc.) — both templates render when both kinds of files exist
7. **Build** — explicit compile/link command for compiled stacks
8. **Running in Development** — dev command, produced-binary launcher, or engine launcher. Expected URL/port/window
9. **Running Tests** — test and coverage commands
10. **Common Issues** — version manager hints, service startup reminders, private registry auth, submodule reminders

## How It Works

1. **Detect** — reads manifests, build files (CMake, Meson, Bazel, Gradle, Xcode, etc.), `.gitmodules`, docker-compose, env files, Makefile, CI configs, and existing docs to build a full picture of the project's run requirements
2. **Scan** — finds existing setup instructions in `HOW-TO-RUN.md`, `README.md`, `CONTRIBUTING.md`, `BUILDING.md`, `INSTALL.md`, and `docs/` and classifies each aspect as accurate, outdated, partial, missing, or documented-but-unverifiable
3. **Assess** — presents findings to the user with a clear status table; asks per-item about unverifiable claims
4. **Generate** — creates section content using detected commands, versions, services, and dependencies — never trusting documented values that contradict the codebase
5. **Place** — writes `HOW-TO-RUN.md` directly on first run; shows exact diff and waits for approval on subsequent runs
6. **Verify & Report** — reads back and validates; reports any stale setup info found in other files (which the skill did NOT modify)

## Relationship to Other Skills

| Skill | Focus | Audience |
|-------|-------|----------|
| `/optimus:init` | `.claude/` setup for AI-assisted development | Claude Code |
| `/optimus:how-to-run` | `HOW-TO-RUN.md` onboarding doc for humans | Developers |
| `/optimus:unit-test` | Test coverage improvement | Both |

**Recommended sequence**: `/optimus:init` first (AI context), then `/optimus:how-to-run` (human onboarding), then `/optimus:unit-test` (test coverage).

## Skill Structure

| File | Purpose |
|------|---------|
| `SKILL.md` | Skill definition with step-by-step instructions |
| `agents/project-environment-detector.md` | Agent for build system, toolchain, source dependencies, SDKs, hardware, tech stack, services, and env detection |
| `agents/how-to-run-auditor.md` | Agent for scanning existing docs as hypotheses and classifying them against detected state |
| `agents/shared-constraints.md` | Skill-specific read-only analysis constraints for both agents |
| `references/how-to-run-sections.md` | Section templates, signal-to-section mapping, build-system/source-dependency detection, PM command tables |
| `references/external-services-docker.md` | Service classification tables, decision heuristics for Docker vs. local install vs. shared-cloud per service, web-search recipe for vendor images, canonical image catalogue (seeds), snippet templates, citation format, and registry allowlist |
| *(shared)* `init/references/readme-section-detection.md` | Algorithm for finding existing setup instructions in documentation |
| *(shared)* `init/references/tech-stack-detection.md` | Manifest → tech stack and package manager detection tables |
| *(shared)* `init/references/project-detection.md` | Monorepo/single-project detection algorithm |
| *(shared)* `init/references/multi-repo-detection.md` | Multi-repo workspace detection algorithm |
| *(shared)* `init/references/unsupported-stack-fallback.md` | Web search fallback for unknown tech stacks |

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Git

## License

[MIT](../../LICENSE)
