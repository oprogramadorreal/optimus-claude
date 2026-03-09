# Multi-Repo Workspace Detection

Shared detection algorithm referenced by multiple skills. Each consuming skill applies its own policy after detection.

> **Note:** This algorithm is a portable subset of `project-detection.md` Step 0. Changes to the core detection logic should be synchronized between both files.

## Detection Algorithm

A **multi-repo workspace** is a directory that meets ALL of these conditions:

1. No `.git/` directory at the root (i.e., it is not itself a git repository)
2. Two or more immediate child directories contain a `.git` **directory** (not `.git` files, which indicate submodules)

### Steps

1. Check whether `.git/` exists in the current directory
   - If it exists → **not a multi-repo workspace** — stop detection, proceed with normal single-repo flow
2. Scan immediate subdirectories (skip dot-directories like `.git`, `.vscode`, etc.)
   - For each subdirectory, check if it contains a `.git` **directory** (use `test -d "$child/.git"`)
   - Ignore `.git` **files** — those indicate git submodules, not independent repos
3. Count qualifying subdirectories:
   - **2+** → confirmed multi-repo workspace. Enumerate repos with their paths
   - **1** → not a workspace. The single repo is the likely target — suggest the user `cd` into it
   - **0** → not a recognized project structure

### Output

When a multi-repo workspace is detected, produce a list of repos with their directory names and relative paths. This list is used by the consuming skill to determine which repo(s) to operate on.
