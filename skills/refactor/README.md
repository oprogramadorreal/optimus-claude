# optimus:refactor

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that refactors
your codebase using 4 parallel analysis agents, driven by your project's own
guidelines. It presents a prioritized refactoring plan, then applies only what you
approve — all changes stay local for review with `git diff`.

Two goals drive every finding:

1. **Guideline compliance** — align code with your project's quality docs
   (`coding-guidelines.md`, plus `architecture.md`, `styling.md`, `testing.md`, and
   `skill-writing-guidelines.md` where they apply)
2. **Testability** — restructure code so `/optimus:unit-test` can safely increase
   coverage without risky changes

## Usage

- `/optimus:refactor` — full project
- `/optimus:refactor "focus on the auth module"` — natural-language scoping
- `/optimus:refactor "review changes since last week"` — incremental review
- `/optimus:refactor testability` — prioritize testability barriers
- `/optimus:refactor guidelines "src/api"` — focus plus scope

## Focus modes

By default all analysis categories compete equally within the 15-finding cap. A
`testability` or `guidelines` keyword reserves 12 of the 15 slots for that category —
high-severity findings from other categories still surface in the remaining 3.

Use `testability` after `/optimus:unit-test` reports code it can't test without
refactoring; use `guidelines` after `/optimus:init` establishes new standards; omit
the keyword for periodic balanced cleanup.

## How it works

1. Verifies project docs exist (falls back to generic guidelines if missing) and
   resolves scope and focus from your arguments
2. Loads constraint docs and maps source directories, prioritized by git activity —
   skipping submodules, build output, and generated files
3. Launches 4 parallel agents: guideline compliance, testability, cross-file
   consistency, and code simplification
4. Independently validates every finding against the code and its git history
5. Presents a prioritized plan (Critical/Warning/Suggestion, capped at 15 per run)
   with before/after sketches and testability-impact notes
6. Applies only the findings you approve, runs the test suite, and reverts any
   change that breaks it

Works in multi-repo workspaces (per-repo docs) and monorepos (per-subproject docs).

## Relationship to the built-in /simplify

Claude Code's built-in `/simplify` cleans up code you just changed. `/optimus:refactor`
is the project-wide, guideline-driven complement: it analyzes the whole codebase (or
any scope) against your project's own documented standards, hunts cross-file issues
(duplication, pattern drift, missing abstractions) and testability barriers, and
verifies applied changes against your test suite. Use `/simplify` while iterating on
a change; use `/optimus:refactor` for deliberate restructuring passes.

## Iterative refactoring

A single pass can miss issues. [`/optimus:deep refactor`](../deep/README.md) wraps
this skill in a resumable loop: each iteration runs in a fresh subagent, fixes are
applied automatically, tests run after every iteration, and failing fixes are
reverted via bisection. Supports the same focus modes. Requires a test command in
`.claude/CLAUDE.md`.

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Git
- Project initialized with `/optimus:init` (recommended, not required)

## License

[MIT](../../LICENSE)
