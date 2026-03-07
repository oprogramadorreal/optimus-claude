# Conventional PR Format

A structured pull request / merge request format inspired by [Conventional Commits](https://www.conventionalcommits.org/). Both `/optimus:pr` and `/optimus:tdd` use this template.

## Title

Use Conventional Commit format: `type(scope): description`

- **type** — `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`, `ci`, `style`, `build`
- **scope** — the module, component, or area affected (optional but recommended)
- **description** — imperative mood, lowercase, no period

Examples:
- `feat(auth): add password reset endpoint`
- `fix(cart): correct total calculation with discount codes`
- `refactor(api): extract validation middleware`
- `test(auth): add integration tests for OAuth flow`

## Body Sections

### `## Summary`

2–4 sentences describing what the PR does and why. Focus on the **what** and **why**, not the **how** (the diff shows the how). Start with a verb: "Adds…", "Fixes…", "Refactors…".

### `## Changes`

Bulleted list of changed files (or logical groups) with brief descriptions:

```
- `path/to/file.ts` — what changed and why
- `path/to/other.ts` — what changed and why
```

Group related files when changes are cohesive (e.g., "API route + handler + tests" as a single bullet).

### `## Rationale` (optional)

Explain key design decisions and trade-offs. Why this approach over alternatives? **Omit this section entirely** if the changes are straightforward and the Summary already covers the reasoning. Include it when the PR involves non-obvious choices, trade-offs, or architectural decisions that reviewers should understand.

### `## Test plan`

Bulleted checklist of verification steps:

```
- [ ] Step 1 — what to verify
- [ ] Step 2 — what to verify
```

Include: manual verification steps, automated test commands, edge cases to check.

### Footer

End the body with:

```
Generated with [Claude Code](https://claude.ai/code)
```
