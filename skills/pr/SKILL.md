---
description: Creates or updates a pull request (GitHub) or merge request (GitLab) for the current branch using the Conventional PR format — structured summary, changes, rationale, and test plan.
disable-model-invocation: true
---

# Pull Request / Merge Request

Create or update a PR (GitHub) or MR (GitLab) for the current branch using the Conventional PR format. Detects the hosting platform, checks for an existing PR/MR, and either creates a new one or offers to update the existing one. Always targets the repository's default branch. PRs/MRs are created as ready to merge (not draft).

## Step 1: Pre-flight

If the current directory is a multi-repo workspace (no `.git/` at root, 2+ child directories containing a `.git` *directory* — not `.git` files, which indicate submodules), ask the user which repo to target using `AskUserQuestion` — header "Repository", question "This is a multi-repo workspace. Which repository should the PR/MR be created for?". List the child repos as options. Run all subsequent steps inside the selected repo.

### Verify git state

1. Confirm the current directory is inside a git repository: `git rev-parse --is-inside-work-tree`. If not → inform the user and stop.
2. Get the current branch: `git rev-parse --abbrev-ref HEAD`.
3. Check that the current branch is not the default branch. Detect the default branch:
   - Try `git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@'`
   - If that fails, try common names: check if `origin/main` exists (`git rev-parse --verify origin/main 2>/dev/null`), then `origin/master`
   - If no default branch can be determined (all methods fail) → inform the user: "Could not detect the default branch. Ensure `origin` is configured and has been fetched." Stop.
   - If on the default branch → inform the user: "You're on the default branch (`<branch>`). Switch to a feature branch first." Stop.

## Step 2: Platform Detection

Determine the hosting platform:

1. Check the `origin` remote URL: `git remote get-url origin`
   - Contains `gitlab` → **GitLab**
   - Contains `github` → **GitHub**
2. If neither matches, check other remotes: `git remote -v`. If multiple remotes point to different platforms, use `AskUserQuestion` — header "Platform", question "Multiple platforms detected. Which one should be used for the PR/MR?" with the detected platforms as options.
3. If no remote matches → fall back to CI file detection:
   - `.gitlab-ci.yml` at repo root → **GitLab**
   - `.github/` directory → **GitHub**
4. If platform is still unknown → inform the user that the hosting platform could not be determined and stop.

## Step 3: CLI Availability

Check that the required CLI tool is installed:

- **GitHub** → run `gh --version`
- **GitLab** → run `glab --version`

### If CLI is installed

Verify authentication:
- **GitHub:** `gh auth status`. If not authenticated → inform the user: "Run `gh auth login` to authenticate." Stop.
- **GitLab:** `glab auth status`. If not authenticated → inform the user: "Run `glab auth login` to authenticate." Stop.

Proceed to Step 4.

### If CLI is not installed

Use `AskUserQuestion` — header "Install CLI", question "The [GitHub CLI (`gh`) / GitLab CLI (`glab`)] is required but not installed. Install it now?":
- **Install** — "Install automatically (requires [package manager])"
- **Cancel** — "I'll install it manually"

If the user chooses **Cancel** → provide manual installation instructions and stop.

If the user chooses **Install**, detect the OS/package manager and install:

**GitHub CLI (`gh`):**
- macOS: `brew install gh`
- Debian/Ubuntu: `sudo apt install gh` (if available) or install from GitHub releases
- Fedora/RHEL: `sudo dnf install gh`
- Arch: `sudo pacman -S github-cli`
- Windows: `winget install GitHub.cli`

**GitLab CLI (`glab`):**
- macOS: `brew install glab`
- Debian/Ubuntu: check if available via apt, otherwise `go install gitlab.com/gitlab-org/cli/cmd/glab@latest`
- Fedora/RHEL: `sudo dnf install glab`
- Arch: `sudo pacman -S glab`
- Windows: `winget install GLab.GLab`

After installation, verify:
1. `gh --version` / `glab --version` — if the command still fails, inform the user the installation did not succeed and provide manual instructions. Stop.
2. `gh auth status` / `glab auth status` — if not authenticated, inform the user: "CLI installed. Run `[gh/glab] auth login` to authenticate, then re-run `/optimus:pr`." Stop.

## Step 4: Branch and Existing PR/MR Check

### Push branch if needed

Check if the branch has been pushed: `git ls-remote --heads origin <branch> 2>/dev/null`

If the branch is not on the remote:
1. Check for commits: `git log --oneline HEAD --not --remotes 2>/dev/null | head -1`. If no commits → inform the user: "No commits on this branch yet. Commit your changes first." Stop.
2. Push: `git push -u origin <branch>`

If the branch is on the remote but has unpushed commits (`git log origin/<branch>..HEAD --oneline`), push them: `git push origin <branch>`

### Check for existing PR/MR

- **GitHub:** `gh pr view --json number,state,title,body,url 2>/dev/null`
  - If a PR exists and is **open** → go to Step 6 (Update Flow)
  - If a PR exists but is **closed/merged** → treat as no PR (create a new one)
  - If no PR exists → go to Step 5 (Create Flow)

- **GitLab:** `glab mr view --output json 2>/dev/null`
  - If an MR exists and is **opened** → go to Step 6 (Update Flow)
  - If an MR exists but is **closed/merged** → treat as no MR
  - If no MR exists → go to Step 5 (Create Flow)

## Step 5: Create Flow

### Detect default branch

- **GitHub:** `gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name'`
- **GitLab:** use the default branch detected in Step 1, or `git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@'`

### Gather change data

Collect information about the changes on the branch:

```bash
# Commit list
git log --oneline origin/<default-branch>..HEAD

# Changed files summary
git diff --stat origin/<default-branch>..HEAD

# Full diff for analysis
git diff origin/<default-branch>..HEAD
```

If there are no commits ahead of the default branch → inform the user: "This branch has no changes compared to `<default-branch>`." Stop.

### Generate PR content

Read the Conventional PR template: `$CLAUDE_PLUGIN_ROOT/skills/pr/references/pr-template.md`

Generate a title and body following the template. When filling in the sections:
- Synthesize the **Summary** from commit messages, changed files, and the diff
- Use `git diff --stat` output as a starting point for **Changes**, then describe what each file change accomplishes
- For the **Test plan**, look for: test files in the diff → "Run `<test command>` to verify"; CI configuration → "CI pipeline will run automatically"; manual verification → describe what to check

### Preview and confirm

Present the generated title and body to the user:

```
## PR Preview

**Title:** <title>

---

<body>
```

Use `AskUserQuestion` — header "PR preview", question "Review the PR/MR title and description above. Proceed or adjust?":
- **Create PR** — "Looks good — create the PR/MR"
- **Adjust** — "I want to modify the title or description"

If the user chooses **Adjust**, ask what to change, apply modifications, and preview again.

### Create PR/MR

Write the body to a secure temp file: `TMPFILE=$(mktemp /tmp/pr-body-XXXXXX.md)`. Clean up after the creation attempt: `rm -f "$TMPFILE"`.

- **GitHub:** `gh pr create --title "<title>" --body-file "$TMPFILE" --base <default-branch>`
- **GitLab:** `glab mr create --title "<title>" --description "$(cat "$TMPFILE")" --target-branch <default-branch>`

Proceed to Step 7.

## Step 6: Update Flow

### Show current PR/MR

Display the current title and body to the user:

```
## Existing PR/MR

**#<number>:** <title>
**URL:** <url>

---

<current body>
```

### Ask what to update

Use `AskUserQuestion` — header "Update PR", question "A PR/MR already exists for this branch. What would you like to do?":
- **Regenerate title and description** — "Regenerate both using the Conventional PR format based on current branch changes"
- **Regenerate description only** — "Keep the current title, regenerate the description"
- **Cancel** — "Keep the current PR/MR as-is"

If the user chooses **Cancel** → report the existing PR/MR URL and stop.

### Regenerate content

Gather change data (same as Step 5) and generate new content following the Conventional PR template.

Present the updated content for preview. Use `AskUserQuestion` — header "Update preview", question "Review the updated PR/MR. Proceed or adjust?":
- **Update** — "Apply changes to the PR/MR"
- **Adjust** — "I want to modify before updating"

### Apply update

Write the body to a secure temp file (same pattern as Step 5). Clean up after the update attempt.

- **GitHub:** `gh pr edit <number> --title "<title>" --body-file "$TMPFILE"`  (or `--body-file` only if keeping the title)
- **GitLab:** `glab mr update <number> --title "<title>" --description "$(cat "$TMPFILE")"`

Proceed to Step 7.

## Step 7: Report

```
## PR/MR [Created / Updated]

- URL: [PR/MR URL]
- Title: [title]
- Target: [default-branch]
- Status: Ready to merge

Recommend running `/optimus:code-review` before merging.
```
