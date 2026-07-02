---
description: Suggests conventional commit messages by analyzing staged, unstaged, and untracked git changes — read-only, never commits. Use when a commit message suggestion is needed without actually committing. Best run in the conversation where the changes were implemented, so the message body captures the why.
disable-model-invocation: true
---

# Commit Message Suggester

Generate a conventional commit message by analyzing all local git changes (staged, unstaged, and untracked) without performing any commit.

## Workflow

### 1. Gather Change Context

Read `$CLAUDE_PLUGIN_ROOT/skills/commit/references/gather-changes.md` and follow the procedure (multi-repo detection + git commands).

### 2. Analyze Changes and Generate Conventional Commit Message

Read `$CLAUDE_PLUGIN_ROOT/skills/commit-message/references/conventional-commit-format.md` and follow its instructions to analyze the gathered changes and generate a conventional commit message.

### 3. Present the Message

Output the suggested commit message in a copyable code block. Do NOT run `git commit`. If the changes span multiple concerns, present each message separately with instructions on which files to stage for each.

In a multi-repo workspace, present each repo's commit message under a heading with the repo directory name (e.g., `## isa-server`). If a repo's changes span multiple concerns, suggest separate commits within that repo's section. If only one repo has changes, still label it with the repo name for clarity.

## Important

- Never commit, stage, or modify any files
- This skill is read-only — it only analyzes and suggests

Recommend the next step based on readiness:
- If the user wants to commit now → `/optimus:commit` to commit (and optionally push)
- If the feature is ready → commit first (`/optimus:commit`), then `/optimus:pr` to create a pull request — pr never commits working-tree changes

Tell the user the closing tip per `$CLAUDE_PLUGIN_ROOT/references/skill-handoff.md` "Closing tip wording" — use **Variant A** with `<continuation-skill(s)>` = `` `/optimus:commit` or `/optimus:pr` `` and `<non-continuation-examples>` = `/optimus:code-review`, `/optimus:unit-test`, etc.
