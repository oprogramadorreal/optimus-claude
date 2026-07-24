# Platform Detection & CLI Management

Shared reference (also consumed by `/optimus:code-review`). Each consuming skill reads the sections it needs and applies its own policy (e.g., whether to offer CLI installation, whether to stop on failure).

## Platform Detection Algorithm

1. **`origin` remote URL** (`git remote get-url origin`) — URL identifies GitHub or GitLab → use that platform.
2. **Other remotes** (`git remote -v`) — if multiple remotes point to different platforms, ask the user which one to use.
3. **CI-file fallback** — `.gitlab-ci.yml` at the repo root → GitLab; `.github/` directory → GitHub.
4. **Still unknown** → detection failed; the consuming skill decides how to handle it (stop, skip, or ask).

### Signal Conflict Resolution

If signals conflict (e.g., GitHub remote URL but `.gitlab-ci.yml` exists), the **remote URL is authoritative** — note the discrepancy to the user.

## CLI Verification

- Installed: `gh --version` / `glab --version`
- Authenticated: `gh auth status` / `glab auth status` — if not, tell the user to run `gh auth login` / `glab auth login`. The consuming skill decides whether to stop or continue.

## CLI Installation

Install via the OS package manager — e.g. `brew install gh|glab`, `winget install GitHub.cli` / `winget install GLab.GLab`, or the `apt`/`dnf`/`pacman` equivalents. Afterwards re-run both verification checks; if the command still fails, report that the installation did not succeed and provide manual instructions.
