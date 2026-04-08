# Refactor Shared Constraints

Read `$CLAUDE_PLUGIN_ROOT/references/shared-agent-constraints.md` for the base agent constraints, quality bar, exclusion rules, and false-positive guidance that apply to all analysis agents.

The following addendum is specific to refactor agents:

## Quality Bar (addition)

- The fix must be concrete and demonstrable

## Scope expansion rule (structural-neighbor consistency checking)

Read `$CLAUDE_PLUGIN_ROOT/references/scope-expansion-rule.md` for the shared procedure, including the sibling/import heuristics and the 3-file-per-finding limit.

**Refactor carve-out:** Cross-file consistency findings are a primary goal of refactor — report them even when the related file is outside the initially listed scope.
