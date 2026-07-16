# optimus:unit-test

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that improves unit test coverage for existing code — discovering gaps and writing tests that follow your project's conventions. Requires `/optimus:init` to have set up test infrastructure first.

**Conservative by design** — only adds new tests (new files, or new cases appended to existing test files), never refactors or restructures source code. If code is untestable as-is, it flags it rather than changing it; restructuring is the domain of `/optimus:refactor`.

## Features

- **Pre-flight check** — verifies `/optimus:init` has been run and locates the project's guideline documents
- **Agent-assisted discovery** — a reconnaissance agent scans test infrastructure, runs the existing suite, measures baseline coverage, and classifies code testability
- **Achievable threshold estimation** — separates testable from untestable code to set realistic coverage targets without requiring refactoring
- **Prioritized plan** — up to 10 items per run, highest-value targets first, user-approved before any test is written
- **Convention-following tests** — replicates existing patterns (fixtures, naming, placement) and applies mocking discipline; may fix a newly-written test, never existing test logic or source code
- **Broken baseline gate** — stops with a triage pointer when pre-existing tests fail; never fixes them
- **Bug discovery** — reports bugs surfaced during test writing without fixing them
- **Monorepo & multi-repo support** — detects subprojects and processes each independently, skipping git submodules

## Usage

- `/optimus:unit-test` — full project
- `/optimus:unit-test src/api` — scope to a directory or monorepo subproject

This skill is part of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin — see the [main README](../../README.md) for installation.

## When to Run

- After `/optimus:init`, to establish coverage on a newly initialized project
- On established codebases that grew without systematic testing
- Before releases or after major refactors
- As periodic maintenance — coverage improves incrementally, up to 10 items per run

## How It Works

1. Verifies project context exists and loads `coding-guidelines.md` / `testing.md`
2. Dispatches a discovery agent: infrastructure scan, baseline test run, coverage measurement, testability classification
3. Presents a prioritized test plan (capped at 10 items) for approval
4. Writes tests following project conventions, running each immediately; failing tests get fixed (test-side only) or abandoned and reverted
5. Runs the full suite with evidence-based verification, then reports coverage impact, bugs discovered, and code flagged as untestable

If pre-existing tests fail or no framework is found, the skill stops instead of proceeding — a green baseline and working infrastructure are prerequisites, and their repair paths (`/optimus:init`, in-conversation triage) are outside this skill's conservative scope.

## Relationship to Other Skills

| | `/optimus:unit-test` | `/optimus:refactor` |
|---|---|---|
| Modifies | Test files only (new tests) | Source code, with approval |
| Untestable code | Flags it | Restructures it (`testability` focus) |

The plugin's test-guardian agent passively flags coverage gaps after code changes; this skill is the active complement that writes the tests.

**Typical loop**: `/optimus:unit-test` → `/optimus:refactor testability` for the flagged barriers → `/optimus:unit-test` again. `/optimus:deep coverage` automates that alternation across resumable cycles with fresh context per phase.

## Skill Structure

| File | Purpose |
|---|---|
| `SKILL.md` | Skill definition with 6-step workflow |
| `agents/test-infrastructure-analyzer.md` | Discovery agent prompt |
| `agents/shared-constraints.md` | Read-only constraints for the discovery agent |
| *(shared)* `references/coverage-harness-mode.md` | Single-pass protocol under `/optimus:deep coverage` |
| *(shared)* `init/references/` | Multi-repo detection, monorepo doc scoping, verification protocol |
| *(shared)* `tdd/references/testing-anti-patterns.md` | Mocking and assertion discipline |

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Git
- Project initialized with `/optimus:init` (the skill stops if `.claude/CLAUDE.md` is not found)

## License

[MIT](../../LICENSE)
