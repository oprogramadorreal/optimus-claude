# Code-Review Shared Constraints

Read `$CLAUDE_PLUGIN_ROOT/references/shared-agent-constraints.md` for the base agent constraints, quality bar, exclusion rules, and false-positive guidance that apply to all analysis agents.

The following addendums are specific to code-review agents:

## Quality Bar (addition)

- Not be pre-existing (in unchanged code)

## All Agents Exclude (additions)

- Input-dependent issues
- Pre-existing issues in unchanged code (unless security/bug directly adjacent to changed lines)
