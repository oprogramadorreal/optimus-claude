# Code-Review Shared Constraints

Read `$CLAUDE_PLUGIN_ROOT/references/shared-agent-constraints.md` for the base agent constraints, quality bar, exclusion rules, and false-positive guidance that apply to all analysis agents.

The following addendums are specific to code-review agents:

## Quality Bar (addition)

- Not be pre-existing (in unchanged code)

## All Agents Exclude (additions)

- Input-dependent issues
- Pre-existing issues in unchanged code (unless security/bug directly adjacent to changed lines)

## Scope expansion rule (structural-neighbor consistency checking)

Read `$CLAUDE_PLUGIN_ROOT/references/scope-expansion-rule.md` for the shared procedure, including the sibling/import heuristics and the 3-file-per-finding limit.

**Code-review carve-out:** Cross-file consistency findings are allowed **even when the related file is outside the original scope** — this is an explicit carve-out from the "pre-existing issues in unchanged code" exclusion above. Consistency gaps that span files are a valid finding category.
