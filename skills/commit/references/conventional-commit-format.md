# Conventional Commit Format

Shared reference for analyzing changes and generating conventional commit messages. Consumed by the commit and tdd skills.

## Analyze

Infer type, scope, and purpose from the gathered diffs. Untracked files appear only as names (`git status --short` produces no diff) — read their contents when needed. In a multi-repo workspace, analyze each repo independently.

## Capture implementation context

When run in the conversation where the changes were implemented, put the *why* the diff cannot show into the commit body: design decisions, trade-offs, alternatives rejected, deliberate non-goals. Omit process narration, restatement of what the diff already shows, and anything speculative. If no such context exists (e.g., a fresh conversation against pre-existing changes), rely on the diff alone — never fabricate context.

## Format

Always produce a Conventional Commits message, regardless of the repository's existing commit style:

```
<type>(<optional scope>): <description>

<optional body>
```

- Types: `feat`, `fix`, `refactor`, `docs`, `style`, `test`, `chore` (includes build, CI, dependencies), `perf`
- Subject under 72 characters, imperative mood; add a body only when the subject alone is insufficient
- Never include `Co-Authored-By` or other attribution trailers

## Splitting

When changes span distinct concerns, propose separate commits — never force artificial splits when everything serves one purpose. Each proposal specifies the commit message and the exact files to stage.
