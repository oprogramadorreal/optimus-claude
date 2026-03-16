# Deep Mode Fix Protocol

Stash-based snapshot/restore procedure for applying and validating fixes during deep mode iterations.

## Before applying fixes

1. On iteration 1 only, create a baseline snapshot: `git stash push --include-untracked -m "deep-mode-baseline-$(date +%s)"`, then immediately restore the working tree: `git stash apply --index stash@{0}`. If the apply fails, run `git stash pop stash@{0}` to restore the working tree and abort deep mode — report the failure. Record the exact stash message (including timestamp) for all subsequent baseline and pre-iteration lookups. This is the user's escape hatch if deep mode goes wrong across multiple iterations — document it in the iteration progress output.
2. Snapshot the current state: `git stash push --include-untracked -m "pre-iteration-N-<baseline-ts>"` (using `--include-untracked` to capture new files, and `<baseline-ts>` is the timestamp from the baseline message for session-unique naming), then immediately restore: `git stash apply --index stash@{0}`. If the apply fails, abort deep mode immediately — drop the pre-iteration stash: `git stash drop stash@{0}`, then restore from the baseline: `REF=$(git stash list | grep -F '<baseline-message>' | head -1 | cut -d: -f1); if [ -z "$REF" ]; then echo "ERROR: baseline stash not found"; exit 1; fi; git stash apply --index "$REF"`. Report the failure. If baseline restore also fails, instruct the user to run `git stash list` for manual recovery.

## Apply and test

1. For each finding, apply the suggested fix
2. After applying all fixes for this iteration, run the project's test command (from `.claude/CLAUDE.md`)

## If tests pass

1. Drop the pre-iteration snapshot: `REF=$(git stash list | grep -F 'pre-iteration-N-<baseline-ts>' | head -1 | cut -d: -f1) && git stash drop "$REF"`
2. Add this iteration's fixed count to `total-fixed`

## If tests fail — bisect

1. Discard the failed fixes and restore pre-iteration state: `git checkout .` and `git clean -fd` (removes untracked files left by fixes), then look up the pre-iteration stash: `REF=$(git stash list | grep -F 'pre-iteration-N-<baseline-ts>' | head -1 | cut -d: -f1)`. If `$REF` is empty, halt deep mode — the stash was unexpectedly removed; instruct the user to run `git stash list` for manual recovery. Otherwise run `git stash apply --index "$REF"` (applies without removing — preserves the entry for fallback). If the apply reports conflicts, abort the bisect: run `git checkout .` and `git clean -fd`, then `BREF=$(git stash list | grep -F '<baseline-message>' | head -1 | cut -d: -f1)`. If `$BREF` is empty, halt deep mode immediately. Otherwise `git stash apply --index "$BREF"` from the baseline. If the baseline restore also fails, do NOT run `git checkout .` — halt deep mode immediately and instruct the user to run `git stash list` for manual recovery (the baseline and pre-iteration stashes are preserved).
2. Re-apply fixes one at a time (in the same order they were originally applied), with a test run after each:
   - If the fix passes tests → keep it
   - If the fix fails tests → restore affected files from the pre-iteration snapshot: `REF=$(git stash list | grep -F 'pre-iteration-N-<baseline-ts>' | head -1 | cut -d: -f1)`, then `git show "$REF:<file>" > "<file>.tmp" && mv "<file>.tmp" "<file>"` (write to temp first to avoid truncation on failure). Remove any new files the fix created, before proceeding to the next fix
   - If a fix fails to apply cleanly after an earlier fix was skipped → treat it as failed
3. After bisect completes, run the full test suite once more on the combined retained changes
   - If this combined run passes → `REF=$(git stash list | grep -F 'pre-iteration-N-<baseline-ts>' | head -1 | cut -d: -f1) && git stash drop "$REF"`. Add passing count to `total-fixed`, failing count to `total-reverted`
   - If this combined run fails → `git checkout .` and `git clean -fd`, then `REF=$(git stash list | grep -F 'pre-iteration-N-<baseline-ts>' | head -1 | cut -d: -f1)`. If `$REF` is empty, halt deep mode — instruct user to run `git stash list`. Otherwise `git stash apply --index "$REF"` to restore pre-iteration state, then `git stash drop "$REF"`. If apply conflicts, do NOT run `git checkout .` — halt deep mode immediately and instruct the user to run `git stash list` for manual recovery. Count all fixes as reverted in `total-reverted`
4. Mark reverted findings in `accumulated-findings` as "(reverted — test failure)"

## Iteration Context Trimming

When `accumulated-findings` exceeds 30 entries, trim to 30 by evicting in this order:

1. `fixed` entries first (lowest forward risk)
2. Remaining entries by ascending severity (Suggestion → Warning → Critical)

Never evict `reverted` or `persistent` entries — they suppress retry attempts on known-unfixable issues. If non-evictable entries alone exceed 30, cap at 60 — summarize the oldest `reverted` entries beyond 60 into a single line: "N additional reverted findings omitted — agents should not re-flag code in [file list]."
