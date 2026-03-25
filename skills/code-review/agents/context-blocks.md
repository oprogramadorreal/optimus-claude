# Code-Review Context Injection Blocks

Read `$CLAUDE_PLUGIN_ROOT/references/context-injection-blocks.md` for the PR/MR Context Block and Iteration Context Block templates.

## Usage Notes

- **PR/MR mode**: When reviewing a PR/MR and a `pr-description` was captured in Step 1, inject the **PR/MR Context Block** before the file list line in every agent prompt. If the PR/MR has no description (empty body), omit the block entirely.
- **Deep mode (iterations 2+)**: When `iteration-count` > 1, inject the **Iteration Context Block** before the file list line in every agent prompt.
- **Both apply**: If both PR/MR context and iteration context apply (deep mode on a PR), inject PR/MR context first, then iteration context, both before the file list line.
