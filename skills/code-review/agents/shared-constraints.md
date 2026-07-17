# Code-Review Shared Constraints

Read `$CLAUDE_PLUGIN_ROOT/references/shared-agent-constraints.md` for the base agent constraints, quality bar, exclusion rules, scope-expansion procedure, and false-positive guidance that apply to all analysis agents. The following are code-review addendums.

## Quality Bar (addition)

- Not be pre-existing (in unchanged code)

## All Agents Exclude (additions)

- Input-dependent issues
- Pre-existing issues in unchanged code (unless security/bug directly adjacent to changed lines)
- **Add-complexity suggestions without a specific bug or guideline.** Any finding whose suggested fix would *add* code (new helpers, abstractions, validation, branches, files, or net-add LOC) must cite either (a) a specific Critical-severity bug or security issue it prevents, or (b) an explicit project guideline rule it satisfies. Otherwise omit — code that is already simple is a valid outcome. Prefer findings that remove complexity over findings that add it. This blocks "could be more thorough / more abstracted / more defensive" suggestions, not legitimate fixes for real defects.

## Scope-expansion carve-out

The base "Structural-Neighbor Scope Expansion" procedure applies, with one carve-out: cross-file consistency findings are allowed **even when the related file is outside the original scope** — an explicit exception to the pre-existing-code exclusion above. If the consistency fix would *add* a pattern to the related file rather than remove one, the Add-complexity bar still applies — and verify that the target file's APIs/dependencies actually support the pattern before reporting (never propose "use flag `--X` on tool `Y`" without evidence that `Y` accepts `--X`).

## Output format (all agents)

Report each finding in this exact shape. Every agent uses `Current:`/`Suggested:` — never `Code:`/`Fix:`:

- **File:** file:line
- **Category:** [agent-specific — see your prompt file]
- **Confidence:** High | Medium
- **Guideline:** [exact project-doc rule, "General: <domain>", or for Intent Mismatch the literal `Intent (see Intent claim)`]
- **Intent claim:** [Intent Mismatch only — the quoted claim from `## Intent`]
- **Issue:** [concrete description]
- **Current:** [relevant snippet — max 5 lines]
- **Suggested:** [fix or recommendation — max 5 lines]

Per-agent extras: security-reviewer and contracts-reviewer add **Severity:** (Critical | Warning | Suggestion); test-guardian adds **Test file:** (recommended test file path); code-simplifier and test-guardian may omit **Current:** when no snippet clarifies the finding (always include it for Intent Mismatch).

## Intent-vs-Implementation Check (PR/MR mode only)

When a PR/MR Context Block is present in your prompt **and** the description includes a populated `## Intent` section (one or more of Problem / Scope / Non-goals / Key decisions filled in), also check whether the diff delivers each claim **within your lane** (table below). These findings use **Category: `Intent Mismatch`**.

**Flag:**

- A claim with no supporting code change (e.g., Intent says "rate-limit reset requests to 3 per hour per email" but the diff has no rate-limiting middleware or counter).
- A code change that contradicts a stated non-goal (e.g., Non-goals says "no schema migration in this PR" but the diff adds a migration file).
- An implementation delivering the wrong shape of the claim (e.g., Intent says "validate email format" but the code only checks for a non-empty string).

**Confidence:** High — the claim is specific and testable and the diff clearly does not deliver it (or contradicts it); Medium — the claim is approximate or only partially delivered.

**Severity** (agents with a Severity field): Critical — a stated non-goal is contradicted; Warning — a stated scope claim has no supporting code; Suggestion — partial match.

**Skip silently** when: there is no populated `## Intent` section — **never invent intent** from the Summary, commit messages, or diff; the claim is ambiguous or aspirational (e.g., "improve performance" with no metric) — omit rather than flag; or the claim is already satisfied elsewhere in the codebase — verify with Grep/Read before flagging.

**Budget:** Intent Mismatch findings do not count against the 15-finding cap — up to **+5 per agent per pass** (canonical rule: `$CLAUDE_PLUGIN_ROOT/references/shared-agent-constraints.md` "Per-category budget exceptions").

**Fix the code, never the PR description.** A suggested fix MUST edit code (or tests, or config — anything that ships in the diff) to deliver the stated intent. Never propose updating the PR description to match the code — that silently rewrites the author's stated intent and defeats the check, and the harness auto-applies emitted fixes, so a description fix would destroy the intent record. If you are confident the intent itself is wrong, write in `Suggested:` that *"the author should reconsider the stated intent"* instead.

## Agent lanes

Each agent reports Intent Mismatch findings only within its own domain:

| Agent | Lane (claims about…) |
|-------|----------------------|
| bug-detector | behavior/correctness — "validates input", "handles null", "no behavior change" |
| security-reviewer | security — "rotated tokens on logout", "requires admin role", boundary validation, abuse prevention |
| guideline-reviewer | patterns/conventions — "follows repository pattern", "uses standard error shape", architectural boundaries |
| test-guardian | test coverage — "tests for the new flow", "covers edge case X", test non-goals |
| contracts-reviewer | API/contracts — "preserves backwards compat", "no public API change", versioning/deprecation |
| code-simplifier | *does not run the check* |
