# Code Simplifier (Quality Gate)

Read `$CLAUDE_PLUGIN_ROOT/agents/code-simplifier.md` for your role and approach.
Read `.claude/docs/coding-guidelines.md` and `.claude/CLAUDE.md` for project standards.

Review ALL of the following files for cross-cycle simplification opportunities:
[list of changed file paths]

This code was written incrementally across multiple TDD cycles. Look for issues
that emerge from incremental development:
- Duplication across behaviors (e.g., similar handlers that should share logic)
- Naming inconsistencies between code written in different cycles
- Dead code introduced early then superseded by later cycles
- Pattern violations that accumulated gradually
- Abstractions that should be extracted now that the full feature shape is visible

Apply the focus areas from your role definition and the project's coding guidelines.

## Tool Allowlist

Read, Edit, Write, Grep, Glob, Bash

## Output Format

For each finding: file:line, guideline violated, brief description, suggested improvement.
Do NOT suggest changes outside the changed files. Do NOT flag style/formatting, bugs, or security.
Maximum 5 findings. Report as a structured list.
