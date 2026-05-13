# Conventional Commit Format

Shared reference for analyzing changes and generating conventional commit messages. Consumed by `commit-message` and `commit` skills.

## Analyze Changes

Review the gathered git diff information to understand:

- **What changed**: Files added, modified, or deleted
- **Why it changed**: Infer purpose from code context (new feature, bug fix, refactor, etc.). When the conversation carries implementation context — design decisions, non-goals, trade-offs, "we decided against X" discussions — capture that rationale in the commit body (see "Capture conversation rationale" below). This is the load-bearing reason `/optimus:commit` and `/optimus:commit-message` are continuation skills.
- **Scope**: Identify the affected component or area of the codebase

In a multi-repo workspace, analyze each repo's changes independently — each repo may have different types, scopes, and purposes.

## Capture conversation rationale

When this skill runs in the conversation where the implementation happened, the conversation carries information the diff alone cannot record — *why* a design was chosen, what alternatives were considered, what was deliberately left out of scope. Translate that into the commit body so the message records both *what* and *why*.

What to inspect for rationale:
- Prior user messages stating the problem being solved, constraints, or success criteria.
- Prior Claude responses where alternatives were proposed and a decision was made (favored or rejected).
- Edit / Write / NotebookEdit tool calls that touch the staged files — the surrounding discussion often explains *why* that specific change was chosen over alternatives.
- Explicit non-goals, follow-ups deferred, or trade-offs accepted.

What to omit:
- Step-by-step narration of how the change was developed (commit messages record decisions, not process).
- Conversation context unrelated to the staged files.
- Re-statement of what the diff already shows clearly.
- Speculative or unverified rationale.

If no implementation context is available (e.g., invoked in a fresh conversation against pre-existing local changes), skip this step and rely on the diff alone — never fabricate rationale.

## Generate Conventional Commit Message

Always produce a message following the Conventional Commits specification, regardless of the commit style used in the repository:

```
<type>(<optional scope>): <description>

<optional body>
```

**Types:**
- `feat` — New feature or capability
- `fix` — Bug fix
- `refactor` — Code restructuring without behavior change
- `docs` — Documentation only
- `style` — Formatting, whitespace, semicolons (no logic change)
- `test` — Adding or updating tests
- `chore` — Build, CI, dependencies, tooling
- `perf` — Performance improvement

**Rules:**
- Keep the subject line under 72 characters
- Use imperative mood ("Add feature" not "Added feature")
- Add a body only when the subject line alone is insufficient to explain the change
- Never include `Co-Authored-By` or other attribution trailers in the commit message

## Splitting Into Multiple Commits

When changes span multiple concerns, they can be split into smaller, self-contained commits. Group files by concern — each commit should represent one logical unit of work (e.g., a feature, a fix, a refactor, a test addition).

- **Prefer splitting** when changes touch distinct concerns (different features, a fix alongside a refactor, new tests for unrelated modules, docs updates separate from code changes)
- **Keep as one commit** when all changes serve a single purpose — do not force artificial splits
- For each proposed commit, specify: the commit message and the list of files to stage
