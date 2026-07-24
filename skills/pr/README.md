# optimus:pr

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that creates or updates pull requests (GitHub) and merge requests (GitLab) using the **Conventional PR** format — a structured body with optional intent, summary, changes, rationale, and test plan sections.

## Why structured PRs

A well-structured description serves human reviewers and `/optimus:code-review` alike: the `## Intent` section records the problem, scope, non-goals, and key decisions from the implementation conversation, and code review later reads it back as author intent to check what was built against what was supposed to be built.

## Recommended workflow

`/optimus:pr` produces the highest-fidelity description when run in the same conversation as the implementation — that's where the decisions, non-goals, and trade-offs live.

1. Implement your changes (TDD, brainstorm-driven, or freeform).
2. In the same conversation, run `/optimus:commit` to land the commits (a `/optimus:tdd` run commits and pushes for you).
3. Still in the same conversation, run `/optimus:pr`.
4. In a fresh conversation, run `/optimus:code-review` — it reads the PR description you just wrote.

Standalone updates are fine from a fresh conversation: the Update Flow preserves the existing `## Intent` verbatim while regenerating the diff-derived sections.

## Prerequisites

- Git repository on a feature branch with at least one commit
- `gh` (GitHub CLI) or `glab` (GitLab CLI) — the skill offers to install if missing and verifies authentication

No `/optimus:init` required — this skill works standalone.

## Usage

- `/optimus:pr` — create or update the PR/MR for the current branch
- "create a PR for this branch" / "update the PR description"

The skill detects the hosting platform, pushes the branch if needed (asking before any force-push after a rebase), and checks for an existing open PR/MR. With none, it generates a Conventional PR, previews it for confirmation, and creates it ready to merge. With an existing one, it offers to regenerate the title, the description, or just the `## Intent` section — always preserving manually-added content (issue references, deployment notes) that can't be derived from the diff, while re-deriving everything that can.

In a multi-repo workspace it filters to repos with branches ready for a PR and offers to process all of them or just one.

### Example

```
> /optimus:pr

## PR Preview

**Title:** feat(auth): add password reset endpoint

---

## Summary

Adds a password reset endpoint that sends a reset email with a time-limited token. ...

[full body: Intent / Summary / Changes / Test plan]

Review the PR/MR title and description above. Proceed or adjust?
[Create PR / Adjust]

> Create PR

## PR/MR Created

- URL: https://github.com/owner/repo/pull/42
- Title: feat(auth): add password reset endpoint
- Target: main
- Status: Ready to merge
```

## Conventional PR format

| Section | Required | Content |
|---------|----------|---------|
| Title | Yes | `type(scope): description` — Conventional Commits |
| `## Intent` | When context available | Problem, scope, non-goals, key decisions — read back by `/optimus:code-review` as author intent; omitted entirely when no context exists |
| `## Summary` | Yes | 2–4 sentences on what and why |
| `## Changes` | Yes | Bulleted file list with descriptions |
| `## Rationale` | No | Design decisions; omitted for straightforward changes |
| `## Test plan` | Yes | Verification checklist |

## When to run

- After finishing work on a feature branch, before requesting review
- After a `/optimus:tdd` run, in the same conversation — the PR body is populated from the `## TDD Summary` block (behaviors, coverage delta, deferred work)
- After new commits or a rebase, to refresh an existing PR/MR description

## When not to run

- On the default branch, or with no commits — commit to a feature branch first
- For draft PRs — this skill creates ready-to-merge PRs only

## License

[MIT](../../LICENSE)
