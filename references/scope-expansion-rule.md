# Structural-Neighbor Scope Expansion Rule

Shared procedure used by analysis agents in `/optimus:code-review` and `/optimus:refactor` to catch cross-file consistency gaps. Each consuming skill's `shared-constraints.md` links to this file and may add a skill-specific carve-out sentence.

## Rule

When you flag an issue in file `X`, before returning your findings also open and inspect these related files for the **same pattern** (or the same pattern being **missing** where it should mirror `X`):

1. **Sibling files** in `X`'s directory (or a parallel directory one level up) whose filename shares a **≥50% prefix** with `X` — e.g., `scripts/deep-mode-harness/main.py` ↔ `scripts/test-coverage-harness/main.py`.
2. **Files that import or re-export** any symbol named in your finding.

If the same pattern appears (or is **missing**) in a related file, report it as a **new consistency finding** — reference the original finding as its trigger.

## Limits (do not violate)

- Open at most **3** extra files per original finding.
- Only expand when the link is **structural and explicit** — same name prefix, direct import, or shared symbol. No fuzzy "semantically related" expansion. No browsing the codebase for unrelated issues.
- Do not duplicate the original finding — only report the *related-file* occurrence (or gap) as the new finding.
- If no related file matches, do nothing. Expansion is opportunistic, not mandatory.
