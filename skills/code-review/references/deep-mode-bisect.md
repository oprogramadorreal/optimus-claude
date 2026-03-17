# Deep Mode Fix Protocol

Apply-test-bisect procedure for validating fixes during deep mode iterations.

## Apply and test

1. For each finding in this iteration, apply the suggested fix
2. After applying all fixes, run the project's test command (from `.claude/CLAUDE.md`)
3. Apply the verification protocol from `$CLAUDE_PLUGIN_ROOT/skills/init/references/verification-protocol.md` to validate test results

## If tests pass

All fixes are valid. Add this iteration's fixed count to `total-fixed`.

## If tests fail — bisect

1. Revert all changes from this iteration: `git checkout .` and `git clean -fd`
2. Re-apply fixes one at a time, running the test suite after each:
   - If tests pass → keep the fix
   - If tests fail → revert that fix (`git checkout -- <affected-files>`, remove any new files the fix created), record as reverted
3. Add passing count to `total-fixed`, failing count to `total-reverted`
4. Mark reverted findings in `accumulated-findings` as "(reverted — test failure)"
