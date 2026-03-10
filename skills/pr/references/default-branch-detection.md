# Default Branch Detection

Detect the repository's default branch using this fallback chain:

1. **Symbolic ref** — `git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@'` — if this succeeds, use the result
2. **Try `main`** — if step 1 fails, check if `origin/main` exists: `git rev-parse --verify origin/main 2>/dev/null` — if it exists, use `main`
3. **Try `master`** — if step 2 fails, check if `origin/master` exists: `git rev-parse --verify origin/master 2>/dev/null` — if it exists, use `master`
4. **All failed** — if no default branch can be determined, detection has failed. The consuming skill decides how to handle this (stop, ask the user, etc.).
