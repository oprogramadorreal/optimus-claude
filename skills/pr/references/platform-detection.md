# Platform Detection & CLI Management

Shared detection algorithm referenced by multiple skills. Each consuming skill reads the sections it needs and applies its own policy (e.g., whether to offer CLI installation or skip).

## Platform Detection Algorithm

Determine the hosting platform for the current repository:

1. **Check the `origin` remote URL:** `git remote get-url origin`
   - Contains `gitlab` → **GitLab**
   - Contains `github` → **GitHub**

2. **If neither matches, check other remotes:** `git remote -v`
   - If multiple remotes point to different platforms, ask the user which one to use (via `AskUserQuestion` — header "Platform", question "Multiple platforms detected. Which one should be used for the PR/MR?" with the detected platforms as options)

3. **If no remote matches, fall back to CI file detection:**
   - `.gitlab-ci.yml` at repo root → **GitLab**
   - `.github/` directory → **GitHub**

4. **If platform is still unknown** → platform could not be determined. The consuming skill decides how to handle this (stop, skip, or ask the user).

### Signal Conflict Resolution

If signals conflict (e.g., GitHub remote URL but `.gitlab-ci.yml` exists), use the **remote URL as authoritative** and note the discrepancy to the user.

## CLI Verification

Check that the required CLI tool is installed and authenticated:

### Availability check

- **GitHub** → run `gh --version`
- **GitLab** → run `glab --version`

### Authentication check

- **GitHub:** `gh auth status`. If not authenticated → inform the user: "Run `gh auth login` to authenticate."
- **GitLab:** `glab auth status`. If not authenticated → inform the user: "Run `glab auth login` to authenticate."

## CLI Installation

If the CLI is not installed and the consuming skill offers installation:

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
1. `gh --version` / `glab --version` — if the command still fails, inform the user the installation did not succeed and provide manual instructions
2. `gh auth status` / `glab auth status` — if not authenticated, inform the user to run the auth login command
