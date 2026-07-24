# optimus:how-to-run

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that generates a `HOW-TO-RUN.md` teaching a new developer how to set up their environment and run the project locally. Writes only `HOW-TO-RUN.md` — never modifies any other file, and never executes commands itself.

Many projects have "how to get this running" instructions scattered across `README.md`, `CONTRIBUTING.md`, and `docs/` that have drifted from the actual codebase. This skill detects the real project state with two read-only agents, audits existing docs against it, and generates (or updates, with your approval) a single verified onboarding doc.

## Features

- **Stack-agnostic** — web apps, C/C++ desktop, native mobile, JVM/Android, game engines, embedded/firmware, and backend services with external infrastructure.
- Detects build system, toolchain, SDKs, runtime version constraints (manifests *and* version-manager pins like `.nvmrc` / `rust-toolchain.toml`), and dev commands.
- Discovers source dependencies (git submodules, sibling repos, CMake FetchContent) and external services — from docker-compose *and* from framework config files (`appsettings*.json`, `application.yml`, Rails/Phoenix/Laravel configs), the latter marked `(candidate)`.
- Classifies each un-composed service as **Docker-preferred**, **Shared-cloud primary**, or **Local install only**; `docker run` snippets use web-verified, vendor-cited image references (never model memory) behind a registry allowlist. Vendor cloud services resolve to their official local emulators (LocalStack, Azurite, Firebase Emulator Suite, DynamoDB Local).
- Enumerates every runnable component (web + workers + frontends) and bound runtime port from launch configs, so run instructions scale with the project and `Expected result:` URLs show real ports — never framework defaults.
- Renders workspace-aware commands (`cargo build --workspace`, `go work sync`, `npm --workspaces`, Gradle/Maven multi-module) instead of silently-wrong per-package forms.
- Anti-hallucination verification pass: every port, path, version, and count in the generated doc must be grounded in a detector citation or re-observable on disk; unverified numbers and prose are rejected before the file is finalized.
- Audits existing docs as hypotheses; stale info found elsewhere is reported for manual fixing — those files are never edited.
- Offers a display-only guided walkthrough of an existing `HOW-TO-RUN.md`: per-step pacing with audit verdicts and destructive/remote-fetch advisories. You run every command yourself.

## Usage

In Claude Code:

- `/optimus:how-to-run`

First-run writes go through directly after you approve the plan; updates to an existing `HOW-TO-RUN.md` show the full diff and wait for approval. When the file already exists you choose: **Walk through it** (guided, display-only), **Regenerate**, or **Skip**.

## When to Run

- **After `/optimus:init`** — init sets up Claude Code; how-to-run creates the human onboarding doc
- **When onboarding new developers** — no tribal knowledge required
- **After adding services, SDKs, submodules, or dependencies** — re-run to update and surface stale info elsewhere
- **On any project with missing or drifted setup docs**

## What It Creates / Modifies

| Topology | Target file | Version-controlled? |
|----------|------------|-------------------|
| Single project | Root `HOW-TO-RUN.md` | Yes |
| Monorepo | Root `HOW-TO-RUN.md` (whole-project scope) | Yes |
| Multi-repo workspace | Workspace-root `HOW-TO-RUN.md` | No (workspace root has no `.git`) |

**Never modified:** `README.md`, `CONTRIBUTING.md`, `BUILDING.md`, `INSTALL.md`, `docs/*`, or any other file.

Generated sections (only those with detected signals): Prerequisites, Toolchain & SDKs, Source Dependencies, Installation, External Services, Environment Setup, Build, Running in Development, Running Tests, Common Issues.

## Relationship to Other Skills

| Skill | Focus | Audience |
|-------|-------|----------|
| `/optimus:init` | `.claude/` setup for AI-assisted development | Claude Code |
| `/optimus:how-to-run` | `HOW-TO-RUN.md` onboarding doc | Developers |
| `/optimus:unit-test` | Test coverage improvement | Both |

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Git

## License

[MIT](../../LICENSE)
