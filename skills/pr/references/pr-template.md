# Conventional PR Format

A structured PR/MR body format inspired by [Conventional Commits](https://www.conventionalcommits.org/), extended with a top-of-body `## Intent` section that carries author intent into the artifact `/optimus:code-review` later consumes.

## Title

Conventional Commit format: `type(scope): description` — imperative mood, lowercase, no period. Example: `feat(auth): add password reset endpoint`.

## Body Sections (in order)

### `## Intent` (optional — only when intent context is available)

Author intent captured from the implementation conversation (or preserved from the existing PR body during an update). This is the primary anchor `/optimus:code-review` reads to check whether the implementation delivers what was supposed to be built.

Omit the section entirely (no stub, no placeholder) when no intent context exists. **Never invent intent from commit messages or the diff alone** — a fabricated Intent produces false intent-vs-implementation findings downstream.

Sub-fields (each optional — include only the ones the source actually answers):

- **Problem** — what was broken, missing, or worth changing (the motivation, not the diff).
- **Scope** — what this PR delivers.
- **Non-goals** — what was intentionally excluded.
- **Key decisions** — trade-offs accepted, alternatives considered and rejected.

Example:

```
## Intent

- **Problem:** Password reset endpoint was missing; locked-out users had no self-service path.
- **Scope:** New POST /auth/reset-password endpoint with email-link flow; rate-limited to 3 requests/hour per email.
- **Non-goals:** Multi-factor reset (next sprint); SMS-based reset.
- **Key decisions:** Time-limited token in URL rather than session cookie (stateless reset); 30-min expiry chosen over 24h to limit the attack window.
```

Detection rule: an existing body has an Intent section when a line starts at column 0 with `## Intent` (case-insensitive) and nothing but whitespace or anchor punctuation (e.g. `{`) follows the word — rejecting `## Intentional X` or `## Intents` — outside fenced code blocks and blockquotes.

### `## Summary`

2–4 sentences: what the PR does and why. The diff shows the how.

### `## Changes`

Bulleted list of changed files (or cohesive groups), each with a brief description of what the change accomplishes.

### `## Rationale` (optional)

Key design decisions and trade-offs. **Omit the section entirely** when the changes are straightforward and the Summary already covers the reasoning.

### `## Test plan`

Checklist (`- [ ]`) of verification steps: automated test commands, manual checks, edge cases.
