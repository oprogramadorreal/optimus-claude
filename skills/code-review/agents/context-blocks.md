# Code-Review Context Injection Blocks

Read `$CLAUDE_PLUGIN_ROOT/references/context-injection-blocks.md` for the PR/MR
Context Block and Iteration Context Block templates, their injection conditions, and
the ordering rule when both blocks apply. Both blocks apply to this skill; the
`pr-description` is the one captured in Step 3 (scope determination).

The Iteration Context Block's status vocabulary (`fixed`, `reverted — test failure`,
`reverted — attempt 2`, `skipped — apply failed`, `persistent — fix failed`) is a
verbatim contract with the harness (`scripts/harness_common`) — reproduce those
status strings exactly, never paraphrase them.
