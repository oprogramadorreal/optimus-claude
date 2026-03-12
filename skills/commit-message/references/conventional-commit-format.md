# Conventional Commit Format

Shared reference for analyzing changes and generating conventional commit messages. Consumed by `commit-message` and `commit` skills.

## Analyze Changes

Review the gathered git diff information to understand:

- **What changed**: Files added, modified, or deleted
- **Why it changed**: Infer purpose from code context (new feature, bug fix, refactor, etc.)
- **Scope**: Identify the affected component or area of the codebase

In a multi-repo workspace, analyze each repo's changes independently — each repo may have different types, scopes, and purposes.

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
