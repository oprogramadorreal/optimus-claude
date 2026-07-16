# Code-Review Shared Constraints

Read `$CLAUDE_PLUGIN_ROOT/references/shared-agent-constraints.md` for the base agent
constraints, quality bar, exclusion rules, finding cap, related-file consistency
check, and false-positive guidance that apply to all analysis agents.

Code-review-specific addendums:

## Quality Bar (addition)

- Not be pre-existing (in unchanged code)

## All Agents Exclude (additions)

- Input-dependent issues
- Pre-existing issues in unchanged code (unless security/bug directly adjacent to
  changed lines)
- **Add-complexity suggestions without a specific bug or guideline.** Any finding
  whose suggested fix would *add* code (new helpers, abstractions, validation,
  branches, files, or net-add LOC) must cite either (a) a specific Critical-severity
  bug or security issue it prevents, or (b) an explicit project guideline rule it
  satisfies. Otherwise omit — code that is already simple is a valid outcome. Prefer
  findings that remove complexity over findings that add it. This does not block
  legitimate fixes for real defects; it blocks "this could be more thorough / more
  defensive" suggestions that resurface on repeat reviews.

## Cross-file consistency carve-out

The base Related-File Consistency Check applies, with one carve-out from the
pre-existing-issues exclusion above: consistency findings are allowed even when the
related file is outside the review scope. However, if the fix would *add* a pattern
to the related file rather than remove one, the add-complexity exclusion still
applies — and verify the target file's APIs actually support the proposed pattern
before reporting (never suggest "use flag `--X` on tool `Y`" without evidence that
`Y` accepts `--X`).

## Intent-vs-Implementation Check (PR/MR mode only)

When a PR/MR Context Block is present in your prompt, treat the description as the
author's stated intent and check whether the diff delivers its specific, testable
claims — what the change does, its scope, explicit non-goals, key decisions.
Findings of this kind use category `Intent Mismatch`.

**Flag:**

- A specific claim with no supporting code change (description says "rate-limit
  reset requests to 3 per hour" but the diff has no rate limiting).
- A change that contradicts a stated non-goal ("no schema migration in this PR" but
  the diff adds a migration file).
- An implementation delivering the wrong shape of the claim ("validate email
  format" but the code only checks for a non-empty string).

**Confidence:** High — the claim is specific and testable and the diff clearly does
not deliver it (or contradicts it). Medium — the claim is approximate or only
partially delivered.

**Severity:** Critical — a stated non-goal is contradicted. Warning — a stated
scope claim has no supporting code. Suggestion — partial match.

**Skip silently** when the description is empty or merely narrates the diff, when a
claim is ambiguous or aspirational ("improve performance" with no metric), or when
the claim is already satisfied elsewhere in the codebase (verify with Grep/Read
before flagging). Never invent intent to manufacture a mismatch — when in doubt,
omit.

**Budget:** Intent Mismatch findings do not count against the 15-finding cap; each
participating agent gets up to **+5** per pass (canonical rule in
`$CLAUDE_PLUGIN_ROOT/references/shared-agent-constraints.md` "Finding Cap").

**Fields:** category `Intent Mismatch`; quote the specific claim in `Intent claim:`;
agents whose format has a `Guideline:` field set it to `Author intent`.

**Fix the code, never the description.** A suggested fix must change code, tests, or
config to deliver the stated intent — never "update the PR description to match the
code" (fixes may be auto-applied by the harness; a description rewrite would
silently destroy the intent record). If you are confident the stated intent itself
is wrong, say so in `Suggested:` instead of proposing a fix.

**Stay in your lane** — each agent checks only claims in its own domain:

- **correctness-security** — behavior, correctness, and security claims
- **guideline-reviewer** — pattern, convention, and architectural-boundary claims
- **test-guardian** — test-coverage claims
- **contracts-reviewer** — API, contract, and backward-compatibility claims
- **code-simplifier** — does not run this check
