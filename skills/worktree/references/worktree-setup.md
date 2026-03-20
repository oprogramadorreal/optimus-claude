# Worktree Setup Procedure

Shared reference for creating git worktrees. Consumed by `worktree` and `tdd` skills.

## Worktree Detection Guard

Before creating a worktree, check whether you are already inside one. This prevents recursive worktrees (e.g., user runs `/optimus:worktree`, opens a session in the worktree, then runs `/optimus:tdd` which also offers worktree isolation).

Run:

```bash
git worktree list
```

Parse the output: the first entry is the **main worktree**, subsequent entries are **linked worktrees**. Check whether the current working directory (`pwd`) matches or is inside a linked worktree path.

If already inside a linked worktree:
- **Skip worktree creation entirely**
- Return to the caller: "Already running inside a worktree (`<worktree-path>`). Skipping worktree creation — working directly on the current branch."
- The caller should proceed with the standard branch workflow (no worktree)

If inside the main worktree (or not inside any worktree): proceed with the setup procedure below.

## Setup Procedure

The caller provides `<branch-name>` (already created) and `<original-branch>` (the branch to restore on the main workspace).

### 1. Derive worktree directory name

Replace `/` with `-` in the branch name:
- `feat/add-password-reset` → `feat-add-password-reset`
- `fix/login-email-case` → `fix-login-email-case`

Use this as `<worktree-dir>` in all paths below.

### 2. Create `.worktrees/` directory

```bash
mkdir -p .worktrees
```

### 3. Ensure `.worktrees/` is gitignored

Check if `.gitignore` already contains `.worktrees/` or `.worktrees`. If not, append it and stage:

```bash
grep -qF '.worktrees' .gitignore 2>/dev/null || (echo '.worktrees/' >> .gitignore && git add .gitignore)
```

### 4. Switch main workspace back (if needed)

If the current branch is not `<original-branch>` (e.g., the caller used `git checkout -b`), switch back:

```bash
git checkout <original-branch>
```

If already on `<original-branch>` (e.g., the caller used `git branch` without switching), skip this step.

### 5. Create worktree

```bash
git worktree add .worktrees/<worktree-dir> <branch-name>
```

### 6. Run project setup (if applicable)

Detect setup commands from `CLAUDE.md` or manifest files (`package.json` scripts, `Makefile`, `Cargo.toml`, `pyproject.toml`, etc.) and run them inside the worktree directory. Common examples:

- Node.js: `cd .worktrees/<worktree-dir> && npm install` (or `yarn`, `pnpm install`)
- Python: `cd .worktrees/<worktree-dir> && pip install -e .`
- Rust: `cd .worktrees/<worktree-dir> && cargo build`

If no setup command is detected, skip silently.

### 7. Verify test baseline

Run the test command inside the worktree to confirm tests pass in the isolated environment. If no test command is detected (no `testing.md`, no obvious test script), skip and note "no test command detected" in the report.

### 8. Failure handling

If worktree creation fails (e.g., git version too old, filesystem issues, branch already checked out in another worktree):
- Clean up the orphaned branch if it was freshly created for this worktree: `git branch -d <branch-name>`
- Report the error with diagnostic information
- Suggest the standard branch workflow as a fallback: "Worktree creation failed. You can work directly on the branch instead."
- Return to the caller so it can decide how to proceed
