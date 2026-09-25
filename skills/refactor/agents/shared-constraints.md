# Refactor Agent Constraints

Read `$CLAUDE_PLUGIN_ROOT/references/shared-agent-constraints.md` first — it applies in full. Refactor addendums:

- Analyze the provided files, or the source files in the provided areas.
- Scope-expansion carve-out: cross-file consistency findings are a primary goal of refactor — report them even when the related file lies outside the original scope (the base rule's 3-extra-files-per-finding limit still applies).

## Output format

Report each finding in this exact format. Your agent prompt defines the **Category** values and any fields it adds or replaces.

- **File:** file:line
- **Category:** [per agent prompt]
- **Confidence:** High | Medium | Low — report a Low as Low; never round it up to Medium or drop the finding.
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
