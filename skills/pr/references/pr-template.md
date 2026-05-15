# Conventional PR Format

A structured pull request / merge request format inspired by [Conventional Commits](https://www.conventionalcommits.org/), with a deliberate extension — a top-of-body `## Intent` section that carries author intent into the artifact `/optimus:code-review` later consumes. Both `/optimus:pr` and `/optimus:tdd` use this template.

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

### `## Intent` (optional — created when intent context is available)

Author intent captured from the implementation conversation (or preserved from the existing PR body during an update). This section is the primary anchor that `/optimus:code-review` reads to check whether the implementation delivers what was supposed to be built.

**Not required.** Created when intent context is available; omitted entirely (no stub, no placeholder) when it is not. Never invent intent from commit messages alone — a fabricated Intent section is worse than no section because it produces false intent-vs-implementation findings downstream.

Sub-prompts (all four optional within the section — include the ones the implementation conversation actually answers):

- **Problem** — what was broken, missing, or worth changing. The motivation, not the diff.
- **Scope** — what this PR delivers (the deliberate cut).
- **Non-goals** — what was intentionally not included or changed in this PR.
- **Key decisions** — architectural choices, trade-offs accepted, alternatives considered and rejected.

Example:

```
## Intent

- **Problem:** Password reset endpoint was missing; users locked out of their accounts had no self-service path.
- **Scope:** New POST /auth/reset-password endpoint with email-link flow; rate-limited to 3 requests per hour per email.
- **Non-goals:** Multi-factor reset (deferred to next sprint); SMS-based reset (out of scope for this PR).
- **Key decisions:** Time-limited token in URL rather than session cookie (stateless reset); link expires in 30 min (chosen over 24h to limit attack window).
```

#### Detecting `## Intent` in an existing PR body

Both `/optimus:pr` (Update Flow preservation) and `/optimus:code-review` (Intent-context check) need to detect whether a PR body already carries an `## Intent` section. Use this single heuristic — both halves of the handoff must agree on what counts:

A line is a real `## Intent` heading when **all** of these hold:
- It starts at column 0 with `## Intent` (case-insensitive).
- After `Intent`, the rest of the line is empty (only optional trailing whitespace before end-of-line), or starts with a trailing-anchor punctuation character (e.g., `{`, `<`). This rejects `## Intentional X` (word continues), `## Intent and rationale` (additional words follow), `## Intents` (plural).
- It is **not** inside a fenced code block (between matching ` ``` ` or `~~~` fences).
- It is **not** a blockquote line (prefixed with `>`).

This avoids false positives when the body quotes another PR's `## Intent`, embeds the template inside a code example, or shows it as a blockquoted reference.

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

