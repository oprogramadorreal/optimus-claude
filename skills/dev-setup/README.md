# optimus:dev-setup

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that ensures your project has comprehensive, accurate development setup instructions in the README — so any developer can clone the repo and get everything running.

Many projects lack step-by-step "how to run in dev mode" instructions, or have instructions that have drifted from the actual codebase. This skill detects the project's tech stack, external services, environment config, and generates (or updates) a complete development section in the README with user approval at every step.

## Features

- Detects tech stack, package manager, runtime version constraints, and dev commands from manifests
- Discovers external services from docker-compose (databases, queues, caches) and generates startup instructions
- Scans existing README sections and audits them against actual project state
- Generates only applicable sections: prerequisites, installation, external services, environment, running, building, testing, common issues
- Cautious editing: shows exact changes before writing, never deletes content outside the dev-setup section, asks when unsure
- Supports single projects, monorepos (whole-project scope), and multi-repo workspaces
- Works standalone or as a complement to `/optimus:init`

## Quick Start

This skill is part of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin. See the [main README](../../README.md) for installation instructions.

## Usage

In Claude Code:

- `/optimus:dev-setup`

The skill analyzes your project, scans existing documentation, and proposes development setup instructions. You review and approve before any file is modified.

## When to Run

- **After `/optimus:init`** — init sets up Claude Code; dev-setup sets up the human-readable README
- **When onboarding new developers** — ensure they can get started without tribal knowledge
- **After adding services or dependencies** — re-run to update instructions (e.g., new database added to docker-compose)
- **On any project with incomplete README** — even without running init first

## What It Creates / Modifies

| Topology | Target file | Version-controlled? |
|----------|------------|-------------------|
| Single project | Root `README.md` (new section or update) | Yes |
| Monorepo | Root `README.md` (whole-project scope) | Yes |
| Multi-repo workspace | Workspace root `README.md` | No (workspace root has no `.git`) |

### Generated sections (only applicable ones)

1. **Prerequisites** — runtimes with version constraints, system tools, version managers
2. **Installation** — clone, install dependencies, post-install steps (code generation, migrations)
3. **External Services** — docker-compose services with ports and purpose, startup commands
4. **Environment Setup** — copy `.env.example`, describe required variables
5. **Running in Development** — dev commands, expected URLs/ports, verification
6. **Building** — production build command (if distinct from dev)
7. **Running Tests** — test and coverage commands
8. **Common Issues** — version manager hints, service startup reminders, private registry auth

## How It Works

1. **Detect** — reads manifests, docker-compose, env files, Makefile, and other config to build a full picture of the project's dev requirements
2. **Scan** — finds existing dev instructions in README, CONTRIBUTING, or docs/ and classifies each aspect as accurate, outdated, partial, or missing
3. **Assess** — presents findings to the user with a clear status table
4. **Generate** — creates section content using detected commands, versions, and services
5. **Place** — shows exact proposed changes, waits for approval, writes to the correct file
6. **Verify** — reads back the file and validates all commands, versions, and paths against the actual project

## Relationship to Other Skills

| Skill | Focus | Audience |
|-------|-------|----------|
| `/optimus:init` | `.claude/` setup for AI-assisted development | Claude Code |
| `/optimus:dev-setup` | README setup instructions for humans | Developers |
| `/optimus:unit-test` | Test coverage improvement | Both |

**Recommended sequence**: `/optimus:init` first (AI context), then `/optimus:dev-setup` (human context), then `/optimus:unit-test` (test coverage).

## Skill Structure

| File | Purpose |
|------|---------|
| `SKILL.md` | Skill definition with step-by-step instructions |
| `agents/` | Individual agent prompt files for Dev Environment Detection and Dev Setup Audit subagents |
| `references/dev-setup-sections.md` | Section templates, signal-to-section mapping, PM command tables, external services detection |
| *(shared)* `init/references/readme-section-detection.md` | Algorithm for finding existing dev instructions in documentation |
| *(shared)* `init/references/tech-stack-detection.md` | Manifest → tech stack and package manager detection tables |
| *(shared)* `init/references/project-detection.md` | Monorepo/single-project detection algorithm |
| *(shared)* `init/references/multi-repo-detection.md` | Multi-repo workspace detection algorithm |
| *(shared)* `init/references/unsupported-stack-fallback.md` | Web search fallback for unknown tech stacks |

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Git

## License

[MIT](../../LICENSE)
