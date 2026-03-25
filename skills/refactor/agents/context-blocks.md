# Refactor Context Injection Blocks

Read `$CLAUDE_PLUGIN_ROOT/references/context-injection-blocks.md` for the Iteration Context Block template.

## Usage Notes

- **Deep mode (iterations 2+)**: When `iteration-count` > 1, inject the **Iteration Context Block** before the file list line in every agent prompt. This gives agents awareness of prior findings so they focus on NEW issues only.

> **Note:** The PR/MR Context Block does not apply to refactor — this skill does not operate on PRs/MRs.
