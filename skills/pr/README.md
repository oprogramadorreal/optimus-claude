# optimus:pr

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that creates or updates pull requests (GitHub) and merge requests (GitLab) using the **Conventional PR** format — a structured template with summary, changes, rationale, and test plan sections.

## Why Structured PRs Matter

Well-structured PR descriptions aren't just for human reviewers — they give Claude Code better context when reviewing code with `/optimus:code-review`. A clear summary of intent, a file-level change list, and explicit design rationale help the AI understand *why* changes were made, not just *what* changed. This aligns with the plugin's core principle: better context produces better AI-assisted development.

The **Conventional PR** format mirrors [Conventional Commits](https://www.conventionalcommits.org/) — standardized structure that's easy to read, easy to generate, and easy to review.

## Recommended Workflow — run pr in the implementation conversation

`/optimus:pr` is a **continuation skill** (see [`references/skill-handoff.md`](../../references/skill-handoff.md) under "Continuation skills"). It produces the highest-fidelity PR description when run in the same conversation as the implementation — the conversation contains the decisions, non-goals, and trade-offs that led to the diff. `/optimus:code-review` then reads the resulting PR description as author intent context.

The canonical chain — all three continuation steps in the same conversation, then `/optimus:code-review` in a fresh conversation:

1. **Implement** your changes (TDD, brainstorm-driven, or freeform).
2. **Stay in the implementation conversation** and run `/optimus:commit` — captures the *why* into the commit message body.
3. **Still in the same conversation**, run `/optimus:pr` — captures intent into the PR description. Upstream skills like `/optimus:commit` already nudge you to do this when they recommend pr.
4. Switch to a **fresh conversation** and run `/optimus:code-review`. It reads the PR description you just wrote to check whether the implementation delivers what was supposed to be built.

**Standalone updates (fresh conversation is fine):** if you only need to refresh a PR's title or description after a rebase — and the existing PR description already carries the original intent — you can re-run `/optimus:pr` from a fresh conversation. The Update Flow preserves the existing intent record while regenerating the diff-derived sections.

## Features

- **Platform detection** — automatically detects GitHub or GitLab from remote URLs, with CI file fallback
- **CLI installation** — offers to install `gh` (GitHub CLI) or `glab` (GitLab CLI) if not present, with authentication verification
- **Existing PR/MR detection** — checks if the current branch already has an open PR/MR before creating a duplicate
- **Create flow** — generates a Conventional PR from branch changes (commits, diff, file list) and previews before creating
- **Update flow** — regenerates title and/or description for an existing PR/MR with current branch state, preserving manually-added content (issue references, deployment notes, etc.) that can't be derived from code changes
- **Conventional PR format** — structured sections: Summary, Changes, Rationale (optional), Test plan
- **Default branch targeting** — new PRs target the repo's default branch (main/master); updates preserve the PR's existing target branch
- **Ready to merge** — PRs/MRs are created as ready (not draft)
- **User preview** — shows generated content before creating or updating, with option to adjust
- **Shared template** — the Conventional PR template is reusable by other skills (e.g., `/optimus:tdd`)
- **Multi-repo workspace support** — detects multi-repo workspaces, auto-filters to repos with changes, and offers to create PRs for all or a specific repo

## Quick Start

This skill is part of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin. See the [main README](../../README.md) for installation instructions.

## Prerequisites

1. **Git** — repository with at least one commit on a feature branch
2. **`gh` or `glab` CLI** — the skill offers to install if missing and verifies authentication
3. **Feature branch** — must be on a branch other than the default branch (main/master)

No `/optimus:init` required — this skill works standalone.

## Usage

In Claude Code, use any of these:

- `/optimus:pr` — create or update a PR/MR for the current branch
- `/optimus:pr` after completing work on a feature branch
- "create a PR for this branch"
- "update the PR description"

### Create Flow Example

```
> /optimus:pr

## PR Preview

**Title:** feat(auth): add password reset endpoint

---

## Summary

Adds a password reset endpoint that sends a reset email with a time-limited token.
Includes rate limiting (3 requests per hour per email) and input validation.
The implementation follows the existing auth module patterns.

## Changes

- `src/routes/auth.ts` — new POST /auth/reset-password route with validation and rate limiting
- `src/services/email.ts` — resetPassword email template and sending logic
- `src/__tests__/auth/reset-password.test.ts` — 4 test cases covering success, 404, 400, and rate limit scenarios

## Test plan

- [ ] Run `npm test` — all 4 new tests pass alongside existing suite
- [ ] POST /auth/reset-password with valid email — returns 200, check inbox
- [ ] POST /auth/reset-password with unknown email — returns 404
- [ ] POST /auth/reset-password 4 times — 4th request returns 429

---

Review the PR/MR title and description above. Proceed or adjust?
[Create PR / Adjust]

> Create PR

## PR/MR Created

- URL: https://github.com/owner/repo/pull/42
- Title: feat(auth): add password reset endpoint
- Target: main
- Status: Ready to merge

Recommend running `/optimus:code-review` for quality review before merging.
```

### Update Flow Example

```
> /optimus:pr

## Existing PR/MR

**#42:** feat(auth): add password reset endpoint
**URL:** https://github.com/owner/repo/pull/42

---

[current description]

---

A PR/MR already exists for this branch. What would you like to do?
[Regenerate title and description / Regenerate description only / Cancel]

> Regenerate description only

## PR/MR Updated

- URL: https://github.com/owner/repo/pull/42
- Title: feat(auth): add password reset endpoint
- Target: develop
- Status: Ready to merge
```

## When to Run

- **After finishing work on a feature branch** — create a well-structured PR before requesting review
- **After adding commits to an existing PR** — update the description to reflect new changes
- **After TDD cycles** — `/optimus:tdd` creates PRs automatically, but you can re-run `/optimus:pr` to regenerate the description
- **Before code review** — a structured PR description helps `/optimus:code-review` understand context

## When NOT to Run

- **On the default branch** — PRs are created from feature branches
- **Without any commits** — commit your changes first
- **For draft PRs** — this skill creates ready-to-merge PRs only

## How It Works

1. Detects multi-repo workspaces, auto-selects repos with changes ready for PRs
2. Detects the hosting platform (GitHub/GitLab) from remote URLs or CI files
3. Verifies the CLI (`gh`/`glab`) is installed and authenticated — offers installation if missing
4. Checks if the current branch already has an open PR/MR
5. **Create flow:** gathers branch changes (commits, diff), generates a Conventional PR (title + structured body), previews, and creates
6. **Update flow:** shows the existing PR/MR, asks what to regenerate, generates fresh content from diffs, scans the existing PR for manually-added information (issue references, deployment notes, etc.) to preserve, previews, and updates
7. Reports the PR/MR URL and recommends `/optimus:code-review`

## Conventional PR Format

The skill uses a structured template inspired by Conventional Commits, with a deliberate extension — an `## Intent` section that `/optimus:code-review` reads to check the implementation against author intent:

| Section | Required | Content |
|---------|----------|---------|
| **Title** | Yes | `type(scope): description` — conventional commit format |
| **Intent** | When context available | Problem, scope, non-goals, key decisions captured from the implementation conversation (or preserved from the existing PR body during an update). Omitted entirely when no intent context is detectable. |
| **Summary** | Yes | 2–4 sentences on what and why |
| **Changes** | Yes | Bulleted file list with descriptions |
| **Rationale** | No | Design decisions and trade-offs (omit for straightforward changes) |
| **Test plan** | Yes | Verification checklist |

The template is shared with `/optimus:tdd` via `references/pr-template.md`. The `## Intent` section is the load-bearing handoff between `/optimus:pr` (writer) and `/optimus:code-review` (reader).

## Relationship to Other Skills

| | `/optimus:pr` | `/optimus:tdd` |
|---|---|---|
| PR creation | Dedicated — full Conventional PR flow | Side effect of TDD workflow |
| CLI missing | Offers to install | Skips PR, suggests `/optimus:pr` |
| Update support | Yes — regenerate existing PR description | No |
| Timing | After all commits are ready | Automatically after TDD cycles |

| | `/optimus:pr` | `/optimus:code-review` |
|---|---|---|
| Purpose | Create/update the PR | Review the PR |
| Timing | Before review | After PR exists |
| Conversation | Run in the **same conversation** as the implementation (so it can capture intent) | Run in a **fresh conversation** (so it reads intent only from the PR description, not from chat noise) |

Workflow: run `/optimus:pr` first, then `/optimus:code-review`.

| | `/optimus:pr` | `/optimus:commit` |
|---|---|---|
| Scope | PR title + description | Local commits (stage + commit + optional push) |
| Timing | After commits exist, branch is pushed | Before pr — to land changes locally |
| Conversation | Same conversation as implementation (preserves intent) | Same conversation as implementation; recommends `/optimus:pr` afterwards with stay-in-conversation guidance |

| | `/optimus:pr` | `/optimus:commit-message` |
|---|---|---|
| Scope | PR title + description | Individual commit messages |
| Format | Conventional PR (structured body) | Conventional Commits (single line) |
| Complement | PR title follows commit message format | Commit messages feed into PR summary |

## Skill Structure

| File | Purpose |
|---|---|
| `SKILL.md` | Skill definition with 8-step workflow (pre-flight, platform detection, CLI check, PR check, create/update, per-repo report, final summary) |
| `references/pr-template.md` | Shared Conventional PR format template (used by this skill and `/optimus:tdd`) |
| `references/platform-detection.md` | Shared platform detection and CLI management reference (used by this skill, `/optimus:tdd`, and `/optimus:code-review`) |
| `references/default-branch-detection.md` | Shared default branch detection algorithm (used by this skill and `/optimus:code-review`) |
| *(shared)* `init/references/multi-repo-detection.md` | Multi-repo workspace detection algorithm |

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Git
- `gh` (GitHub CLI) or `glab` (GitLab CLI) — skill offers installation if missing

## License

[MIT](../../LICENSE)
