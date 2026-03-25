# Shared Constraints (TDD Quality Gate)

Read `$CLAUDE_PLUGIN_ROOT/references/shared-agent-constraints.md` for base constraints (agent constraints, quality bar, exclusions, false positives).

## TDD-Specific Rules

- Maximum 5 findings per agent
- Scope to changed files only
- Do NOT suggest changes outside the changed files
- Do NOT flag style/formatting, bugs, or security
