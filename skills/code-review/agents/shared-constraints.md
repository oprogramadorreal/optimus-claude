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

## Intent-vs-Implementation Check (PR/MR mode only)

When a PR/MR Context Block is present in your prompt **and** the description includes a populated `## Intent` section (with one or more of Problem / Scope / Non-goals / Key decisions filled in), you must also check whether the diff delivers each claim. Findings of this kind go under a new category — `Intent Mismatch`.

**What to flag:**

- A claim in `## Intent` that has no supporting code change. Example: Intent says "rate-limit reset requests to 3 per hour per email" but the diff has no rate-limiting middleware or counter.
- A code change that **contradicts a stated non-goal**. Example: Intent's Non-goals says "no schema migration in this PR" but the diff adds a migration file.
- An implementation that delivers the wrong shape of the stated intent. Example: Intent says "validate email format" but the code only checks for non-empty string.

**Confidence:**

- **High** — the Intent claim is specific and testable, and the diff clearly does not deliver it (or actively contradicts it).
- **Medium** — the Intent claim is approximate, or the diff partially delivers it.

**Severity** (for agents whose output format includes a `Severity:` field — currently security-reviewer and contracts-reviewer):

- **Critical** — a stated non-goal is contradicted by the diff (e.g., Non-goals says "no public API change" but the diff renames a public endpoint).
- **Warning** — a stated scope claim has no supporting code (e.g., Scope says "adds `OrderResponse` type" but no such type exists).
- **Suggestion** — the implementation only partially matches the claim.

**Skip silently** when:

- The PR has no `## Intent` section, or the section is empty. **Never invent intent** from the Summary, commit messages, or diff to manufacture a mismatch.
- The Intent claim is ambiguous or aspirational (e.g., "improve performance" with no specific metric). When ambiguous, omit rather than flag.
- The Intent claim is already satisfied elsewhere in the codebase (not in the diff) — verify with `Grep` / `Read` before flagging.

**Finding budget:** Intent Mismatch findings do NOT count against the per-agent 15-finding cap. Each agent that runs this check gets an additional **+5 Intent Mismatch findings per pass**. See `$CLAUDE_PLUGIN_ROOT/references/shared-agent-constraints.md` "Per-category budget exceptions" for the canonical rule.

**Fix the code, never the PR description.** When suggesting a fix for an Intent Mismatch, the fix MUST edit code (or tests, or config — anything that ships in the diff) to deliver the stated intent. Do NOT propose "update the PR description to match the code" as a fix — that would silently rewrite the author's stated intent and defeat the entire intent-vs-implementation check. If the implementation deliberately diverges from the stated intent and you are confident the intent itself is wrong, flag the finding with a note in the agent's `Suggested:` field saying *"the author should reconsider the stated intent"* rather than emitting a description-rewriting fix. (All agents emit `Current:`/`Suggested:` for Intent Mismatch findings — bug-detector and security-reviewer override their default `Code:`/`Fix:` per their PR/MR addendums.) The harness will auto-apply any fix you emit; emitting a PR-description fix would silently destroy the intent record.

**Stay in your lane:** Each agent reports Intent Mismatch findings only within its existing domain. Read each agent's `PR/MR mode addendum` for the specific scope:

- **bug-detector** — behavior / correctness claims (e.g., "rate-limits", "validates input", "handles null").
- **guideline-reviewer** — pattern / guideline / convention claims (e.g., "follows repository pattern", "uses standard error shape").
- **security-reviewer** — security claims (e.g., "rotated tokens on logout", "validates authorization on protected endpoints").
- **test-guardian** — test-coverage claims (e.g., "tests for the new flow", "covers edge case X").
- **contracts-reviewer** — API / contract claims (e.g., "preserves backwards compat", "no public API change", stated contract non-goals).
- **code-simplifier** — *does not run* the Intent Mismatch check in this release (simplicity intent claims are rarely specific enough to flag mechanically).
