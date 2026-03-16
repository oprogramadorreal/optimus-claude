# Deep Mode Fix Protocol

Stash-based snapshot/restore procedure for applying and validating fixes during deep mode iterations.

## Before applying fixes

1. On iteration 1 only, create a baseline snapshot: `git stash push --include-untracked -m "deep-mode-baseline"`, then immediately restore the working tree: `git stash apply stash@{0}`. This is the user's escape hatch if deep mode goes wrong across multiple iterations — document it in the iteration progress output.
2. Snapshot the current state: `git stash push --include-untracked -m "pre-iteration-N"` (using `--include-untracked` to capture new files), then immediately restore: `git stash apply stash@{0}`

## Apply and test

1. For each finding, apply the suggested fix
2. After applying all fixes for this iteration, run the project's test command (from `.claude/CLAUDE.md`)

## If tests pass

1. `git stash drop` the `pre-iteration-N` snapshot (find it by checking `git stash list` for the matching message before dropping)
2. Add this iteration's fixed count to `total-fixed`

## If tests fail — bisect

1. Discard the failed fixes and restore pre-iteration state: `git checkout .`, then `git stash apply $(git stash list | grep 'pre-iteration-N' | head -1 | cut -d: -f1)` (applies `pre-iteration-N` without removing it — preserves the entry for fallback). If the apply reports conflicts, abort the bisect: run `git checkout .`, restore from `deep-mode-baseline` (`git stash apply $(git stash list | grep 'deep-mode-baseline' | head -1 | cut -d: -f1)`), and report the iteration as fully reverted.
2. Re-apply fixes one at a time (in the same order they were originally applied), with a test run after each:
   - If the fix passes tests → keep it
   - If the fix fails tests → revert its changes (`git checkout -- <affected files>` and remove any new files it created) before proceeding to the next fix
   - If a fix fails to apply cleanly after an earlier fix was skipped → treat it as failed
3. After bisect completes, run the full test suite once more on the combined retained changes
   - If this combined run passes → `git stash drop` the `pre-iteration-N` entry. Add passing count to `total-fixed`, failing count to `total-reverted`
   - If this combined run fails → `git checkout .`, then `git stash apply $(git stash list | grep 'pre-iteration-N' | head -1 | cut -d: -f1)` to restore pre-iteration state, then `git stash drop` the same entry. If apply conflicts, run `git checkout .` and restore from `deep-mode-baseline`. Count all fixes as reverted in `total-reverted`
4. Mark reverted findings in `accumulated-findings` as "(reverted — test failure)"
