# Worktree Setup Procedure

Shared reference consumed by the `worktree` and `tdd` skills. The caller runs the detection guard first, then the Setup procedure.

## Worktree detection guard

Run `git worktree list`. If the current working directory is inside a **linked** worktree (any entry other than the first, main one), skip worktree creation entirely and report the detection result — including `<worktree-path>` — to the calling skill, which defines the user-facing message and next action. This prevents recursive worktrees. Otherwise proceed with Setup.

## Setup

The caller provides `<branch-name>` (already created) and `<original-branch>` (the branch the main workspace must end on).

1. **Derive the worktree directory name**: `<worktree-dir>` = branch name with `/` replaced by `-` (e.g., `feat/add-login` → `feat-add-login`).

2. **Create `.worktrees/` and ensure it is gitignored** (staged, not committed):

   ```bash
   mkdir -p .worktrees
   grep -qF '.worktrees' .gitignore 2>/dev/null || (echo '.worktrees/' >> .gitignore && git add .gitignore)
   ```

3. **Switch the main workspace back** if the current branch is not `<original-branch>` (e.g., the caller used `git checkout -b`): `git checkout <original-branch>`. Skip if already on it.

4. **Create the worktree**:

   ```bash
   git worktree add .worktrees/<worktree-dir> <branch-name>
   ```

5. **Run project setup**: detect the project's setup command from `CLAUDE.md` or manifest files (`package.json`, `pyproject.toml`, `Makefile`, etc.) and run it inside the worktree directory. If none is detected, skip silently.

6. **Verify the test baseline**: run the test command inside the worktree. If no test command is detected, note "no test command detected" in the report. If the baseline fails, the failures are pre-existing — the worktree starts from the same commit as the main workspace. Do not block or remove the worktree; report "failing (pre-existing — N failures)" so the failures are not later attributed to new work.

## Failure handling

If worktree creation fails (git version too old, filesystem issues, branch already checked out elsewhere):

- Delete the orphaned branch if it was freshly created for this worktree: `git branch -d <branch-name>`
- Report the error with diagnostic information
- Suggest the fallback: "Worktree creation failed. You can work directly on the branch instead."
- Return to the caller so it can decide how to proceed

## Cleanup

When the caller offers cleanup (after the work is merged or pushed):

1. Switch to the main workspace directory (the parent of `.worktrees/`)
2. Remove the worktree: `git worktree remove .worktrees/<worktree-dir>`
   - If removal fails due to uncommitted changes, inform the user: commit or discard them first, or use `git worktree remove --force .worktrees/<worktree-dir>` to discard and remove
3. If `.worktrees/` is now empty, remove it: `rmdir .worktrees 2>/dev/null`

If the user prefers to keep the worktree, skip cleanup and note: "Worktree `.worktrees/<worktree-dir>` is still active. Remove it with `git worktree remove .worktrees/<worktree-dir>` when done."
