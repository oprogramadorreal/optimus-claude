# optimus:tdd

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that guides test-driven development — decompose a feature or bug fix into behaviors, then cycle through Red (failing test) → Green (minimal implementation) → Refactor for each one.

Tests give an AI agent a binary feedback loop to self-correct: write test → see failure → implement → verify. Writing the test first also keeps it an independent specification instead of a rubber stamp for whatever was just written. `/optimus:unit-test` adds tests to existing code retroactively; `/optimus:tdd` builds new code test-first.

## Usage

- `/optimus:tdd` — start a session (asks what to implement)
- `/optimus:tdd "Add user authentication endpoint"`
- `/optimus:tdd "Fix: login fails when email has uppercase letters"`

A brief description is enough — the skill decomposes the task into testable behaviors and confirms the list before writing any code. Long specs are distilled to a single-sentence goal for confirmation.

TDD auto-detects context from upstream skills:

| Path | When to use |
|------|-------------|
| `/optimus:tdd "description"` | Simple task, well-understood scope |
| `/optimus:jira PROJ-123` → `/optimus:tdd` | JIRA-tracked work (auto-detects `docs/jira/`) |
| `/optimus:brainstorm` → plan mode → `/optimus:tdd` | Complex feature (auto-detects `docs/specs/`) |

When the spec has a `## Scenarios` section (Given/When/Then), the scenarios become the behavior list directly — one Red-Green-Refactor cycle per scenario.

### Example

```
> /optimus:tdd "Add password reset endpoint"

## Behaviors to Implement

1. Returns 404 when email is not registered
2. Sends reset email with valid token when email exists
3. Returns 400 when email format is invalid
4. Rate-limits to 3 requests per hour per email

Start cycling? [Start cycling / Adjust]
```

Each behavior runs one cycle: a failing test, the minimum code to pass it, a cleanup pass against your `coding-guidelines.md`, then an automatic conventional commit. Bug fixes start with a test that reproduces the bug, verified by a regression gate (fix reverted → test fails; fix restored → test passes). If a decomposition exceeds 10 behaviors, the skill splits it into milestones (~5-8 each) with a checkpoint at every boundary.

## Prerequisites

1. **`/optimus:init`** — recommended; without it the skill continues with general best practices on your choice. Installs `CLAUDE.md`, `coding-guidelines.md`, test infrastructure, and `testing.md`
2. **`/optimus:permissions`** — recommended. Branch-aware git protection: TDD always works on a feature branch, so it commits and pushes freely while main/master stay protected
3. **`gh` or `glab` CLI** — optional; needed by `/optimus:pr` afterwards (which offers to install it)

## When to run

- Starting a new feature or API endpoint — define expected behavior as tests first
- Fixing a bug — reproduce it with a test before fixing
- Implementing business logic — capture edge cases as tests before coding

## When NOT to run

- Refactoring existing code → `/optimus:refactor` (existing tests verify behavior is preserved)
- Adding tests to existing code → `/optimus:unit-test`
- Docs, styling, or configuration changes — no testable behavior (the skill detects these and redirects)
- Exploratory prototyping — TDD needs describable expected behavior upfront

## Git workflow

1. Creates `<type>/<slug>` (e.g., `feat/add-password-reset`) from the current branch; optionally isolates work in a `.worktrees/` git worktree. The original branch is never modified
2. Commits after each completed cycle with a conventional message; commits any remaining task-owned work at the end, leaving unrelated changes untouched
3. Pushes the branch to `origin`
4. Recommends `/optimus:code-review` for the cross-cycle pass, then `/optimus:pr` in the same conversation — the latter reads the `## TDD Summary` block to populate the PR's Intent and per-behavior Test plan

Earlier versions ran a two-agent quality gate inline at the end of the run. That reviewed work this same conversation had just written, and duplicated a weaker version of `/optimus:code-review`; the review now happens in the skill built for it, where the full agent fan-out and finding validation apply.

## Skill structure

| File | Purpose |
|---|---|
| `SKILL.md` | The 8-step TDD workflow |
| `references/testing-anti-patterns.md` | Mocking discipline and gate questions (read before writing mocks) |
| `references/spec-context-detection.md` | Spec/JIRA context cascade + long-spec distillation |
| *(shared)* `init/references/multi-repo-detection.md` | Multi-repo workspace detection |
| *(shared)* `commit/references/branch-naming.md` | Branch naming convention |
| *(shared)* `commit/references/conventional-commit-format.md` | Commit message format |
| *(shared)* `worktree/references/worktree-setup.md` | Worktree setup and cleanup |

## Requirements

- Optimus installed in a [supported host](../../README.md#supported-hosts-and-versions)
- Git
- Working test infrastructure with a passing baseline; `/optimus:init` is recommended, with the skill's general-guidance fallback available

## License

[MIT](../../LICENSE)
