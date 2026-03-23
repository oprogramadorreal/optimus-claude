# TDD Worktree Orchestration

TDD-specific worktree setup and cleanup. The shared procedure lives in `$CLAUDE_PLUGIN_ROOT/skills/worktree/references/worktree-setup.md`.

## Setup

After branch creation, offer git worktree isolation so the user's main workspace stays clean.

First, read `$CLAUDE_PLUGIN_ROOT/skills/worktree/references/worktree-setup.md` for the shared worktree setup procedure. Run the **worktree detection guard** from that reference. If the guard detects you are already inside a linked worktree, skip this subsection entirely and proceed to "Decompose into behaviors" — the user is already in an isolated environment.

If the guard passes (not inside a worktree), derive a **worktree directory name** by replacing `/` with `-` in the branch name (e.g., `feat/add-password-reset` → `feat-add-password-reset`). Use this as `<worktree-dir>`.

Use `AskUserQuestion` — header "Workspace", question "Use a git worktree for isolated development? Your main workspace stays on the original branch.":
- **Use worktree (Recommended)** — "Work in `.worktrees/<worktree-dir>` — main workspace stays clean, enables parallel work"
- **Stay on branch** — "Work directly on the branch in the current directory (standard git workflow)"

If the user chooses worktree isolation, follow the **setup procedure** from the shared worktree reference using `<branch-name>` and `<original-branch>` from above. The procedure handles creating `.worktrees/`, ensuring it is gitignored, switching the main workspace back, creating the worktree, running project setup, and verifying the test baseline.

After successful worktree creation, report:

```
## Worktree

Working in: `.worktrees/<worktree-dir>`
Main workspace: `<original-branch>` (unchanged)
Tests: passing ✓
```

If worktree creation fails (e.g., git version too old, filesystem issues), fall back to the standard branch workflow silently and inform the user.

**Important**: When using a worktree, all subsequent steps (4–9) must run commands inside the worktree directory. Use `cd .worktrees/<worktree-dir>` before running tests, linting, or git commands. File paths in reports should be relative to the project root for clarity.

## Cleanup

If a worktree was used (see Setup above), offer cleanup after the PR/MR is created:

1. Switch to the main workspace directory (parent of `.worktrees/`)
2. Remove the worktree: `git worktree remove .worktrees/<worktree-dir>`
   - If removal **fails due to uncommitted changes**, inform the user: "Worktree has uncommitted changes. Commit or discard them first, or use `git worktree remove --force .worktrees/<worktree-dir>` to discard and remove."
3. If the `.worktrees/` directory is now empty, remove it: `rmdir .worktrees 2>/dev/null`

If the user prefers to keep the worktree (e.g., for further work), skip cleanup and note: "Worktree `.worktrees/<worktree-dir>` is still active. Remove it manually with `git worktree remove .worktrees/<worktree-dir>` when done."
