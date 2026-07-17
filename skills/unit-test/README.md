# optimus:unit-test

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that improves unit test coverage for existing code — discovering gaps and generating tests that follow your project's conventions. Requires `/optimus:init` to have set up test infrastructure first.

**Conservative by design** — only adds new tests (new files, or new cases appended to existing test files), never refactors or restructures existing source code. If code is untestable as-is, it flags it rather than changing it; restructuring is the domain of `/optimus:refactor`.

## Features

- **Agent-assisted discovery** — a reconnaissance subagent scans test infrastructure, runs the existing suite, measures baseline coverage, and classifies code testability (git submodules excluded)
- **Achievable threshold estimation** — sets a realistic coverage target reachable without refactoring
- **Prioritized test plan** — up to 10 items per run, highest-value targets first, user-approved before execution
- **Broken baseline handoff** — stops with a triage pointer when pre-existing tests fail; never fixes them
- **Bug discovery** — bugs found in existing code are reported, not fixed
- **Monorepo & multi-repo workspace support** — processes each initialized repo/subproject independently

## Usage

- `/optimus:unit-test` — full project
- `/optimus:unit-test src/api` — scope to a directory or subproject

For an automated multi-cycle loop that alternates test generation with testability refactoring, use `/optimus:deep coverage`.

## When to Run

- After `/optimus:init` — establish coverage for a newly initialized project
- On established codebases that grew without systematic testing
- Before releases, or after major refactors
- Periodically — coverage improves incrementally (10 tests per run)

## How It Works

1. Verifies project context exists and loads guideline docs (`coding-guidelines.md`, `testing.md`)
2. Dispatches the Test Infrastructure Analyzer agent: discovery, suite run, coverage baseline, testability classification — stops if no framework is found or the baseline is red
3. Presents a prioritized test plan (capped at 10 items) for approval
4. Writes tests following project conventions and mocking discipline; each test runs immediately, failing tests are fixed (test only, max 3 attempts) or reverted
5. Runs the full suite as a regression gate, then reports coverage impact, bugs discovered, and code flagged as untestable

## Relationship to Other Skills

| Skill | Role |
|---|---|
| `/optimus:init` | Installs the framework, coverage tooling, and testing docs this skill requires |
| `/optimus:refactor testability` | Restructures the code this skill flags as untestable |
| `/optimus:deep coverage` | Automated loop alternating this skill with testability refactoring |
| test-guardian agent | Passive complement — flags coverage gaps after code changes but writes no tests |

**Typical cycle**: `/optimus:init` → `/optimus:unit-test` → `/optimus:refactor testability` → `/optimus:unit-test` again.

## Skill Structure

| File | Purpose |
|---|---|
| `SKILL.md` | Skill definition with 6-step workflow |
| `agents/test-infrastructure-analyzer.md` | Discovery/coverage/testability subagent prompt |
| *(shared)* `references/shared-agent-constraints.md` | Base agent constraints prepended at dispatch |
| *(shared)* `references/agent-architecture.md` | Prompt assembly rule for subagent dispatch |
| *(shared)* `references/coverage-harness-mode.md` | Single-pass protocol under `/optimus:deep coverage` |
| *(shared)* `init/references/multi-repo-detection.md` | Workspace detection (only when cwd has no `.git/`) |
| *(shared)* `init/references/project-detection.md` | Monorepo structure detection (only when unclear) |
| *(shared)* `tdd/references/testing-anti-patterns.md` | Mocking discipline (read before mock-dependent tests) |

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Git
- Project initialized with `/optimus:init` (required — the skill stops if `.claude/CLAUDE.md` is not found)
- Test command in `.claude/CLAUDE.md` if you want to use `/optimus:deep coverage`

## License

[MIT](../../LICENSE)
