# Code-Review Context Injection Blocks

Read `$CLAUDE_PLUGIN_ROOT/references/context-injection-blocks.md` for the PR/MR Context Block, User Intent Block, and Iteration Context Block templates.

## Usage Notes

- **PR/MR mode**: When reviewing a PR/MR and a `pr-description` was captured in Step 3, inject the **PR/MR Context Block** before the file list line in every agent prompt. If the PR/MR has no description (empty body), omit the block entirely.
- **Local / branch-diff mode (no PR description)**: When `user-intent-text` (from Step 1) or `branch-intent-text` (from Step 3) is non-empty, inject the **User Intent Block** before the file list line in every agent prompt. Skip when both are empty. Mutually exclusive with the PR/MR Context Block — never inject both.
- **Deep mode (iterations 2+)**: When `iteration-count` > 1, inject the **Iteration Context Block** before the file list line in every agent prompt.
- **Combined**: If an intent block (PR/MR or User Intent) and iteration context both apply, inject the intent block first, then iteration context, both before the file list line.
