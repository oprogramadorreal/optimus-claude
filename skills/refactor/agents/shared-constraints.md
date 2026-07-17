# Refactor Agent Constraints

Read `$CLAUDE_PLUGIN_ROOT/references/shared-agent-constraints.md` for the base constraints that apply to every refactor agent: read-only analysis, quality bar and confidence levels, the 15-finding cap, universal exclusions (including generated source files), structural-neighbor scope expansion, and false-positive guidance.

Refactor addendums:

- Every suggested fix must be concrete and demonstrable.
- Scope-expansion carve-out: cross-file consistency findings are a primary goal of refactor — report them even when the related file lies outside the original scope (the base rule's 3-extra-files-per-finding limit still applies).

## Output format

Report each finding in this exact format. Your agent prompt defines the **Category** values and any fields it adds or replaces.

- **File:** file:line
- **Category:** [per agent prompt]
- **Confidence:** High | Medium
- **Guideline:** [which project guideline this addresses]
- **Issue:** [what is wrong and why it matters]
- **Current:**
  ```
  [relevant snippet — max 5 lines]
  ```
- **Suggested:**
  ```
  [fix or refactoring approach — max 5 lines]
  ```
