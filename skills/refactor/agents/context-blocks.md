# Refactor Context Injection Blocks

Read `$CLAUDE_PLUGIN_ROOT/references/context-injection-blocks.md` for the Iteration Context Block template. The shared file also documents the PR/MR Context Block and User Intent Block; both apply to `code-review` only and do not apply here (see the note below).

## Usage Notes

- **Deep mode (iterations 2+)**: When `iteration-count` > 1, inject the **Iteration Context Block** before the file list line in every agent prompt. This gives agents awareness of prior findings so they focus on NEW issues only.

> **Note:** The PR/MR Context Block does not apply to refactor — this skill does not operate on PRs/MRs.
