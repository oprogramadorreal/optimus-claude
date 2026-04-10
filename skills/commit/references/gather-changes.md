# Gather Change Context

Shared procedure for collecting local git changes. Used by commit-message and commit skills.

## Multi-repo workspace detection

Read `$CLAUDE_PLUGIN_ROOT/skills/init/references/multi-repo-detection.md` for workspace detection. If a multi-repo workspace is detected:
- Run the git commands below inside each child repo (the workspace root has no `.git/`, so git commands must target individual repos)
- Track which repos have changes and which are clean
- Skip repos with no local changes (no staged, unstaged, or untracked files)
- If no repos have changes at all, inform the user and stop

## Gather changes

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
