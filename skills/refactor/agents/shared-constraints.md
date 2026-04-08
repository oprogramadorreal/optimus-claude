# Refactor Shared Constraints

Read `$CLAUDE_PLUGIN_ROOT/references/shared-agent-constraints.md` for the base agent constraints, quality bar, exclusion rules, and false-positive guidance that apply to all analysis agents.

The following addendum is specific to refactor agents:

## Quality Bar (addition)

- The fix must be concrete and demonstrable

## Scope expansion rule (structural-neighbor consistency checking)

When you flag an issue in file `X`, before returning your findings also open and inspect these related files for the **same pattern** (or the same pattern being **missing** where it should mirror `X`):

1. **Sibling files** in `X`'s directory (or a parallel directory one level up) whose filename shares a **≥50% prefix** with `X` — e.g., `scripts/deep-mode-harness/main.py` ↔ `scripts/test-coverage-harness/main.py`.
2. **Files that import or re-export** any symbol named in your finding.

If the same pattern appears (or is **missing**) in a related file, report it as a **new consistency finding** — reference the original finding as its trigger. Cross-file consistency findings are a primary goal of refactor; report them even when the related file is outside the initially listed scope.

**Limits (do not violate):**
- Open at most **3** extra files per original finding.
- Only expand when the link is **structural and explicit** — same name prefix, direct import, or shared symbol. No fuzzy "semantically related" expansion. No browsing the codebase for unrelated issues.
- Do not duplicate the original finding — only report the *related-file* occurrence (or gap) as the new finding.
- If no related file matches, do nothing. Expansion is opportunistic, not mandatory.
