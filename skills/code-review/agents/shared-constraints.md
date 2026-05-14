# Code-Review Shared Constraints

Read `$CLAUDE_PLUGIN_ROOT/references/shared-agent-constraints.md` for the base agent constraints, quality bar, exclusion rules, and false-positive guidance that apply to all analysis agents.

The following addendums are specific to code-review agents:

## Quality Bar (addition)

- Not be pre-existing (in unchanged code)

## All Agents Exclude (additions)

- Input-dependent issues
- Pre-existing issues in unchanged code (unless security/bug directly adjacent to changed lines)
- **Add-complexity suggestions without a specific bug or guideline.** Any finding whose suggested fix would *add* code (new helpers, abstractions, validation, branches, files, or net-add LOC) must cite either (a) a specific Critical-severity bug or security issue it prevents, or (b) an explicit project guideline rule it satisfies. Otherwise omit — code that is already simple is a valid outcome. Prefer findings that remove complexity over findings that add it. This does not block legitimate fixes for real defects; it blocks "this could be more thorough / more abstracted / more defensive" suggestions that surface on repeat reviews.

## Scope expansion rule (structural-neighbor consistency checking)

Read `$CLAUDE_PLUGIN_ROOT/references/scope-expansion-rule.md` for the shared procedure, including the sibling/import heuristics and the 3-file-per-finding limit.

**Code-review carve-out:** Cross-file consistency findings are allowed **even when the related file is outside the original scope** — this is an explicit carve-out from the "pre-existing issues in unchanged code" exclusion above. Consistency gaps that span files are a valid finding category. **However**, if the consistency fix would *add* a pattern to the related file (rather than remove one), the Add-complexity exclusion above still applies — and you must verify that the target file's APIs/dependencies actually support the pattern before reporting (for example, do not propose "use flag `--X` on tool `Y`" without evidence that `Y` accepts `--X`).
