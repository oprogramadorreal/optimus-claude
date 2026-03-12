---
description: This skill stages, commits, and optionally pushes local changes with a conventional commit message — analyzes diffs, generates the message, confirms with the user, and commits on the current branch. Multi-repo aware. Use when you want to commit your work in one step.
disable-model-invocation: true
---

# Commit

Stage, commit, and optionally push local changes with a conventional commit message. Never creates or switches branches — commits on the current branch.

## Workflow

### 1. Gather Change Context

#### Multi-repo workspace detection

Read `$CLAUDE_PLUGIN_ROOT/skills/init/references/multi-repo-detection.md` for workspace detection. If a multi-repo workspace is detected:
- Run the git commands below inside each child repo (the workspace root has no `.git/`, so git commands must target individual repos)
- Track which repos have changes and which are clean
- Skip repos with no local changes (no staged, unstaged, or untracked files)
- If no repos have changes at all, inform the user and stop

#### Gather changes

Run the following git commands to understand all local changes (in a multi-repo workspace, run these inside each child repo that was detected above):

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

### 2. Analyze Changes and Generate Conventional Commit Message

Read `$CLAUDE_PLUGIN_ROOT/skills/commit-message/references/conventional-commit-format.md` and follow its instructions to analyze the gathered changes and generate a conventional commit message.

If changes span multiple concerns, use `AskUserQuestion` to ask whether to commit everything together or split into separate commits. If splitting, process each commit separately through steps 3–7.

In a multi-repo workspace, process each repo with changes through steps 2–7 independently.

### 3. Handle Untracked Files

If `git status --short` shows untracked files (`??`):
- List them for the user
- Warn about any that look like secrets (`.env`, `*.key`, `*.pem`, `*.pfx`, `credentials.*`, `secrets.*`, `*.sqlite`, `*.db`)
- Use `AskUserQuestion` — header "Untracked files", question "Include these untracked files in the commit?":
  - **"Include all"** — stage all untracked files
  - **"Exclude all"** — stage only tracked files with changes
  - **"Let me choose"** — present each file individually

### 4. Branch and Push-Safety Check

Get the current branch:

```bash
git rev-parse --abbrev-ref HEAD
```

Check if `.claude/hooks/restrict-paths.sh` exists in the project. If it does, read the file and extract the `PROTECTED_BRANCHES` array to determine whether the current branch is protected. Remember this result for step 5.

If the hook file does not exist, assume the branch is safe for all operations.

### 5. Preview and Confirm

Present a summary for each repo (in multi-repo, use a heading per repo — e.g., `## repo-name`):

- **Branch**: current branch name
- **Commit message**: the generated conventional commit message
- **Files**: list of files that will be staged

Then use `AskUserQuestion` — header "Action", question "How would you like to proceed?":

- **"Commit and push"** — if step 4 determined the current branch is protected, set this option's description to: "⚠ Current branch `<branch>` is protected — push will likely be blocked by the permissions hook."
- **"Commit only"** — commit without pushing
- **"Edit message"** — let the user provide an adjusted message, then re-present this step
- **"Cancel"** — abort without making any changes

### 6. Stage and Commit

Stage the files determined in steps 1 and 3:

```bash
git add <specific files>
```

Prefer `git add <specific files>` over `git add -A`. Never stage files that look like secrets.

Commit with the confirmed message:

```bash
git commit -m "<message>"
```

If the commit is blocked (e.g., by the permissions hook on a protected branch), report the error and suggest: "Switch to a feature branch to commit your changes."

### 7. Push (if requested)

Only if the user chose "Commit and push" in step 5:

```bash
git push
```

If there is no upstream tracking branch:

```bash
git push -u origin <branch>
```

If the push is blocked (e.g., by the permissions hook), report: "Commit succeeded but push was blocked on protected branch `<branch>`. Switch to a feature branch or use `/optimus:pr`."

### 8. Report and Next Step

Present a summary of what was done (in a multi-repo workspace, show a combined summary across all repos):
- Committed: `<short-hash> <commit message>` (per repo in multi-repo)
- Pushed to: `origin/<branch>` (if push was performed)

Recommend the next step based on readiness:
- If a pull request is needed → `/optimus:pr` to create or update a PR
- If validation is needed → `/optimus:verify` to validate end-to-end

Tell the user: **Tip:** for best results, start a fresh conversation for the next skill — each skill gathers its own context from scratch.
