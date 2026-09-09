# Multi-Repo Workspace Detection

Canonical detection algorithm, read by every skill that needs it — including `project-detection.md` Step 0. Each consuming skill applies its own policy after detection. Change it here; there is no second copy to sync.

## Detection Algorithm

A **multi-repo workspace** is a directory that meets ALL of these conditions:

1. The current directory is outside a Git working tree and is not a bare repository.
2. Two or more immediate child directories are independent Git working-tree roots, including linked worktrees; confirmed submodules are excluded.

### Steps

1. Run `git rev-parse --is-inside-work-tree` in the current directory.
   - `true` → **not a multi-repo workspace**. Resolve `git rev-parse --show-toplevel` and proceed in that working tree. This covers normal checkouts, linked worktrees, and a session started in a subdirectory.
   - Otherwise check `git rev-parse --is-bare-repository`: `true` → stop and explain that a working checkout is required.
   - A Git access/configuration failure is not evidence that no repository exists. Report it and preserve files; do not repair Git configuration silently or infer submodules from `.git` file shape. If Git is unavailable, detection remains unverified.
2. Scan immediate subdirectories (skip dot-directories like `.git`, `.vscode`, and non-project directories like `node_modules`, `vendor`, `dist`, `build`, `target`, etc.)
   - For each candidate, run `git -C "<child>" rev-parse --is-inside-work-tree` and `git -C "<child>" rev-parse --show-toplevel`. Count it only when the resolved toplevel is that child, not an inherited ancestor repository.
   - Exclude confirmed submodules: `git -C "<child>" rev-parse --show-superproject-working-tree` is nonempty, or the containing repository's `.gitmodules` explicitly registers that path. A `.git` file alone proves neither submodule nor linked-worktree status.
3. Count qualifying subdirectories:
   - **2+** → confirmed multi-repo workspace. Enumerate repos with their paths
   - **1** → not a workspace. The single repo is the likely target — suggest the user `cd` into it
   - **0** → not a recognized project structure

### Output

When a multi-repo workspace is detected, produce a list of repos with their directory names and relative paths. This list is used by the consuming skill to determine which repo(s) to operate on.
