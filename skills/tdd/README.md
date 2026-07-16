# optimus:tdd

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that implements a feature or bug fix test-first through Red-Green-Refactor cycles.

Tests give an AI agent a feedback loop it cannot argue with: write a failing test, implement until it passes, verify. This skill enforces that discipline — **no production code without a failing test first** — and adds the project awareness that makes it stick: tests follow your `testing.md` conventions, refactoring applies your `coding-guidelines.md`, and every success claim is backed by a fresh test run.

## What it does

1. Checks prerequisites: project context from `/optimus:init` and a green test suite (a failing suite makes Red and Green indistinguishable)
2. Resolves the task: an explicit spec path, the newest approved spec in `docs/specs/`, an inline description, or it asks
3. Creates a feature branch from your current branch
4. Decomposes the task into small, independently testable behaviors — or takes the spec's Given/When/Then scenarios directly as the behavior list
5. For each behavior: Red (failing test) → Green (minimum code) → Refactor (against your coding guidelines), with the full suite run at every step and a checkpoint between cycles
6. Commits each behavior with a conventional message
7. Runs quality-gate agents in parallel to catch cross-cycle issues (duplication between behaviors, naming drift, coverage gaps)
8. Summarizes, pushes the branch, and suggests opening a PR followed by `/optimus:code-review`

## Usage

- `/optimus:tdd` — asks what to implement
- `/optimus:tdd "Add password reset endpoint"`
- `/optimus:tdd "Fix: login fails when email has uppercase letters"`
- `/optimus:tdd docs/specs/2026-07-10-password-reset.md`

A brief description is enough — the skill analyzes the codebase and proposes the decomposition for your approval:

```
> /optimus:tdd "Add password reset endpoint"

Behaviors to implement:
1. Returns 404 when the email is not registered
2. Sends a reset email with a valid token when the email exists
3. Returns 400 when the email format is invalid
```

Each behavior becomes one Red-Green-Refactor cycle with its own commit. For a bug fix, the first behavior is always a test that reproduces the bug.

## Discipline it enforces

- **The Iron Law** — implementation written before its test is deleted and the cycle restarts
- **Vertical slicing** — one test, one implementation, next test; never all tests up front
- **Right-reason failures** — a new test must fail on its assertion, not on a syntax or import error
- **Minimal Green** — only what the test demands, with a circuit breaker after 3 failed attempts (design problem, not coding problem)
- **Bug-fix regression gate** — the fix is stashed to prove the test fails without it, then restored to prove it passes
- **Mocking discipline** — [`references/testing-anti-patterns.md`](references/testing-anti-patterns.md) is read before any mock is written

## When to use it

- New features, API endpoints, business logic — anything with testable behavior
- Bug fixes — the bug is reproduced with a test before it's fixed

And when not to:

- **Refactoring** — use `/optimus:refactor` (restructures with existing tests as the safety net)
- **Adding tests to existing code** — use `/optimus:unit-test` (test-after, never touches source)
- **Docs, configuration, styling** — no testable behavior; the skill will say TDD doesn't fit

## Prerequisites

- **`/optimus:init`** — required. Provides `CLAUDE.md`, `coding-guidelines.md`, test infrastructure, and `testing.md`
- **A green test suite** — existing failures must be resolved first
- **`/optimus:spec`** — optional. Writes approved specs to `docs/specs/` that this skill picks up automatically, including Given/When/Then scenarios used directly as the behavior list

## Skill structure

| File | Purpose |
|---|---|
| `SKILL.md` | The Red-Green-Refactor workflow |
| `references/testing-anti-patterns.md` | Mocking anti-patterns and gate questions, read before writing mocks |
| `references/quality-gate.md` | Post-cycle parallel agent execution and fix protocol |
| `agents/` | Quality-gate agent prompts (code-simplifier, test-guardian, shared constraints) |

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Git
- Project initialized with `/optimus:init`

## License

[MIT](../../LICENSE)
