---
description: Creates a git worktree for isolated parallel development — new branch in a separate directory with project setup and test baseline. Enables multiple Claude Code sessions on different tasks simultaneously. Multi-repo aware. Use when you need to work on something else without disturbing current work.
disable-model-invocation: true
argument-hint: "[description]"
---

# Worktree

Create a git worktree under `.worktrees/` on a new branch, with project setup and a test baseline. The main workspace stays on its original branch, so each worktree can host an independent Claude Code session.

## Workflow

### 1. Target repo

If the current directory has no `.git/` directory, read `$CLAUDE_PLUGIN_ROOT/skills/init/references/multi-repo-detection.md` and apply it. In a multi-repo workspace, run all git commands inside the target child repo: use the repo the user specified; if ambiguous, use `AskUserQuestion` — header "Target repo", question "Which repo should the worktree be created for?", one option per repo.

### 2. Detection guard

Read `$CLAUDE_PLUGIN_ROOT/skills/worktree/references/worktree-setup.md` and run its **worktree detection guard**. If already inside a linked worktree, tell the user:

```
Already running inside a worktree (`<worktree-path>`).
To create another worktree, run this skill from the main workspace instead.
```

Then stop — never create nested worktrees.

### 3. Branch

Note the current branch as `<original-branch>`. Derive the task description from the invocation argument or the conversation; if neither gives enough signal, ask what the user will work on — follow up until you have a concrete description, not a category. Read `$CLAUDE_PLUGIN_ROOT/skills/commit/references/branch-naming.md` for the `<type>/<slug>` convention and collision handling, then create the branch without switching:

```bash
git branch <branch-name>
```

### 4. Create worktree

Follow the **Setup** procedure from worktree-setup.md with `<branch-name>` and `<original-branch>`. On failure, follow its **Failure handling**, then stop.

### 5. Report

```
## Worktree Created

Working directory: `.worktrees/<worktree-dir>`
Branch: `<branch-name>` (from `<original-branch>`)
Main workspace: `<original-branch>` (unchanged)
Tests: passing / failing (pre-existing — N failures) / no test command detected

Open it: `code .worktrees/<worktree-dir>` (VSCode) or `cd .worktrees/<worktree-dir> && claude`
Cleanup when done: `git worktree remove .worktrees/<worktree-dir>`
```

If Setup modified `.gitignore`, add after "Main workspace": `.gitignore updated to ignore .worktrees/ (staged, not committed)`. In a multi-repo workspace, prefix all report paths with the target repo directory.

Never commit or push in the main workspace; it must end on `<original-branch>`.

Recommend starting a Claude Code session inside the new worktree to begin the work there.
