---
description: 'Stages, commits, and optionally pushes local changes with a Conventional Commits message — always previews and confirms first, and offers a feature branch on protected branches. Modes: "suggest" proposes a message without committing (read-only); "branch [description]" creates and switches to a conventionally named branch, never committing or altering local changes. Multi-repo aware.'
disable-model-invocation: true
argument-hint: "[suggest | branch [description]]"
---

# Commit

Pick the mode from the arguments: `suggest` → Suggest mode; `branch` (optionally followed by a description) → Branch mode; anything else → Default mode.

**Multi-repo**: if the current directory has no `.git/` directory, read `$CLAUDE_PLUGIN_ROOT/skills/init/references/multi-repo-detection.md` and apply it. In a workspace, git commands run inside each child repo; Default and Suggest modes process each repo with changes independently (per-repo steps, per-repo preview under a `## <repo-name>` heading, one combined final summary); Branch mode targets a single repo (its step 1).

## Default mode — stage, commit, optionally push

1. **Gather changes**: read `$CLAUDE_PLUGIN_ROOT/skills/commit/references/gather-changes.md` and follow it.

2. **Untracked-file gate**: if `git status --short` shows untracked files (`??`):
   - List them and warn about any that look like secrets (`.env`, `*.key`, `*.pem`, `*.pfx`, `credentials.*`, `secrets.*`, `*.sqlite`, `*.db`).
   - `AskUserQuestion` — header "Untracked files": **"Include all"** / **"Exclude all"** / **"Let me choose"**. "Include all" never covers secret-looking files — each one requires individual confirmation.
   - Read the contents of the included untracked files — step 1 gathered only their names.

3. **Generate the message**: read `$CLAUDE_PLUGIN_ROOT/skills/commit/references/conventional-commit-format.md` and apply it to everything gathered. If changes span multiple concerns, `AskUserQuestion` whether to commit together or split; when splitting, run steps 4–6 once per commit with its pre-assigned files.

4. **Protected-branch check**: look for `.claude/hooks/restrict-paths.sh` — in a workspace check the child repo first, then the workspace root (first found wins). Parse its `PROTECTED_BRANCHES` array to decide whether the current branch is protected; no hook = unprotected; hook present but array unparseable = treat as unprotected and note it in the preview. If protected, generate a feature branch name per `$CLAUDE_PLUGIN_ROOT/skills/commit/references/branch-naming.md` — `<type>` from the commit message, slug from its subject line.

5. **Preview and confirm**: show the branch, the full commit message (subject and body — never truncate to subject-only), and the files to stage. `AskUserQuestion` — "How would you like to proceed?":
   - Not protected: **"Commit and push"** / **"Commit only"** / **"Edit message"** / **"Cancel"**
   - Protected: **"Create branch `<name>`, commit, and push"** / **"Create branch `<name>` and commit only"** / **"Edit message"** / **"Cancel"**
   - "Edit message" takes the user's adjusted message and re-presents this step (on a protected branch, regenerate the feature branch name from it). "Cancel" aborts with zero repo changes.

6. **Execute**:
   - If a "Create branch" option was chosen: `git checkout -b <name>`. If creation fails (name taken), report it and let the user pick a different name or cancel — never silently auto-suffix a name the user approved (deliberate divergence from branch-naming.md's Collision Handling).
   - Stage the specific files from steps 1–2 — never `git add -A`, and never a secret-looking file unless individually confirmed in step 2.
   - Commit with a heredoc to preserve the multi-line message:

     ```bash
     git commit -m "$(cat <<'EOF'
     <message>
     EOF
     )"
     ```

   - If the commit fails, report the error and stop — never proceed to push.
   - Push only if the user chose a push option; use `git push -u origin <branch>` when no upstream exists.

7. **Report**: created branch (if any), `Committed: <short-hash> <subject>` per repo, `Pushed to: origin/<branch>` if pushed. If a feature branch was created, tell the user they are now on it.

Recommend `/optimus:pr` when a pull request is next — stay in this conversation so the implementation context is captured.

## Suggest mode — message only, read-only

Never stages, commits, or modifies anything.

1. Gather changes per `$CLAUDE_PLUGIN_ROOT/skills/commit/references/gather-changes.md`.
2. Read `$CLAUDE_PLUGIN_ROOT/skills/commit/references/conventional-commit-format.md` and generate the message(s).
3. Present each message in a copyable code block. If changes span multiple concerns, propose separate commits, each with its message and the exact files to stage. In a workspace, put each repo's suggestion under a `## <repo-name>` heading (label even a single repo).

Recommend `/optimus:commit` to actually commit — stay in this conversation so the implementation context is captured.

## Branch mode — create a named branch, nothing else

A purely local move: `git checkout -b` only. Never commit, push, stage, stash, reset, or modify any file or the index — staged, unstaged, and untracked changes carry to the new branch untouched. Ask questions only for multi-repo ambiguity or missing naming signal.

1. **Target repo** (workspace only): one repo with local changes → target it silently, unless the description or conversation names a different repo (that repo's clean tree is the starting-fresh case; leave the dirty repo untouched). Multiple dirty repos → `AskUserQuestion` — header "Target repo", one option per repo. No dirty repos → pick the repo the description or conversation points to; ask if ambiguous; with no context at all, inform the user and stop.

2. **Derive the description**: record the current branch for the report. Use the first source with enough signal: (1) inline description from the arguments, (2) conversation context, (3) analysis of local changes, including untracked files. If none provides enough signal, print exactly:

   ```
   Could not determine a meaningful branch name from the conversation or local changes.
   Provide a description, e.g., `/optimus:commit branch "add user authentication"`
   ```

   and stop — never create a branch with a generic or meaningless name.

3. **Name and create**: read `$CLAUDE_PLUGIN_ROOT/skills/commit/references/branch-naming.md`; apply its Type Detection Keywords, Slug Rules, and Collision Handling. Then `git checkout -b <branch-name>` and report:

   ```
   ## Branch

   Created `<branch-name>` from `<original-branch>`.
   Local changes preserved (nothing committed or pushed).
   ```

   Omit the last line when the tree was clean; in a workspace, name the target repo.

When the work is ready to commit, run `/optimus:commit` in this conversation so the implementation context is captured.
