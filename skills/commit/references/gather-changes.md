# Gather Change Context

Change-collection procedure for the commit skill's Default and Suggest modes.

Run inside the repo — in a multi-repo workspace, inside each child repo (the workspace root has no `.git/`):

```bash
git diff --cached   # staged
git diff            # unstaged
git status --short  # untracked files (names only)
```

Add `--stat` passes first when the diffs are large. Skip repos with no staged, unstaged, or untracked changes. If there are no local changes anywhere, inform the user and stop.
