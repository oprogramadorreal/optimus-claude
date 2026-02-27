---
description: Suggest conventional commit messages by analyzing staged, unstaged, and untracked git changes — read-only, never commits
disable-model-invocation: true
---

# Commit Message Suggester

Generate a conventional commit message by analyzing all local git changes (staged, unstaged, and untracked) without performing any commit.

## Workflow

### 1. Gather Change Context

Run the following git commands to understand all local changes:

```bash
# Staged changes
git diff --cached --stat
git diff --cached

# Unstaged changes to tracked files
git diff --stat
git diff

# Untracked files
git status --short
```

### 2. Analyze Changes

Review the gathered information to understand:

- **What changed**: Files added, modified, or deleted
- **Why it changed**: Infer purpose from code context (new feature, bug fix, refactor, etc.)
- **Scope**: Identify the affected component or area of the codebase

### 3. Generate Conventional Commit Message

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
- If changes span multiple concerns, suggest separate commits with guidance on how to stage them
- Never include `Co-Authored-By` or other attribution trailers in the commit message

### 4. Present the Message

Output the suggested commit message in a copyable code block. Do NOT run `git commit`. If the changes naturally split into multiple commits, present each message separately with instructions on which files to stage for each.

## Important

- Never commit, stage, or modify any files
- This skill is read-only — it only analyzes and suggests
- When changes are too broad for a single commit, recommend splitting
