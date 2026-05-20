# Design: Brainstorm → TDD handoff auto-detection fix

**Date:** 2026-05-20
**Status:** Approved
**Goal:** Fix the brainstorm→TDD handoff so `/optimus:tdd` reliably auto-detects a recent design doc even when the user provides an inline task description.

## Context

A user ran `/optimus:brainstorm` (Small branch) on 2026-05-19, producing `docs/design/2026-05-19-catalog-pdf-shape-images.md`. The brainstorm closing tip (`skills/brainstorm/SKILL.md`:182) explicitly promises:

> "It will auto-detect the design doc at `<file-path>`."

The next day, the user started a fresh Claude Code conversation and invoked `/optimus:tdd`. The skill did not surface the design doc — the user had to point at the file manually.

Static reading of `skills/tdd/SKILL.md` confirms the discovery step exists: Step 2 → "Gather the task" → "Context detection" → item 2 "Design doc auto-discovery" (line 54). It performs a "most recent by filename date prefix" lookup and gates on a 7-day freshness window. The 1-day-old design doc satisfied every precondition, so the contract should have fired.

**Root cause.** Item 2 is gated by the ambiguous phrase *"if no explicit reference but `docs/design/` exists with `.md` files…"* The intended meaning is "item 1 above did not match a `.md` file path in the user's input." But the phrase is equally readable as "the user supplied no explicit reference (no inline content at all)." When the user invoked `/optimus:tdd` with an inline task string that did not contain a `.md` path, item 1 did not match, and item 2 *should* have fired — but the model interpreted "no explicit reference" as "no inline input," found inline input present, and jumped past items 2–3 straight to the inline-task branch at line 62. Discovery never ran. Item 3 (JIRA discovery) uses the unambiguous phrase *"if no design doc found (or user ignored it)"*, so it's not affected and inherits the fix once item 2 is repaired.

## Approach

Two surgical edits in `skills/tdd/SKILL.md`. No other file changes. Brainstorm's `auto-detect` promise stays intact and is now honored.

**Why option (a) — fix TDD's discovery — over (b)/(c) — tighten brainstorm's wording.** Brainstorm's contract is `auto-detect`. Requiring the user to paste the file path with the invocation (option b) or copy a one-line pointer (option c) is a workaround that breaks the advertised contract and adds friction. It also does not generalize to users who run `/optimus:tdd` in a separate session after a previous brainstorm run. The two-edit fix in TDD's Step 2 honors the contract at the root cause.

**Why two edits, not one.** Edit 2 alone tightens the gate, but Edit 1 reinforces the intent in the preamble so the model is steered consistently when it parses the section. Either edit alone is weaker than the pair.

## Components

| Component | Responsibility | New / Modified |
|-----------|---------------|----------------|
| `skills/tdd/SKILL.md` Step 2 → Context detection (lines 50–58) | Resolve task source (explicit reference, design-doc discovery, JIRA discovery, or task gathering) before consuming the user's inline task description | Modified |

## Interfaces

**Edit 1 — preamble (line 50).** Replace:

> **Context detection** (runs before the task-gathering prompts below — first match wins):

with:

> **Context detection** (runs at Step 2 entry — items 1–3 are evaluated in order regardless of whether the user provided an inline task description; first match wins):

**Edit 2 — item 2 condition (line 54).** Replace the opening clause:

> **Design doc auto-discovery** — if no explicit reference but `docs/design/` exists with `.md` files…

with:

> **Design doc auto-discovery** — if item 1 did not fire (the user did not reference a `docs/design/` or `docs/jira/` `.md` file path) and `docs/design/` exists with `.md` files…

The remainder of item 2 (date-prefix lookup, 7-day window, `AskUserQuestion` prompt, age note) is unchanged. Items 1, 3, and 4 are unchanged.

## Edge Cases and Risks

| Risk | Mitigation |
|------|------------|
| `/optimus:tdd "some inline task"` now triggers the design-doc confirmation prompt when one exists, even if the user did not intend to use it. | The `AskUserQuestion` already offers "Ignore — describe a different task" as an option. One extra prompt, but matches brainstorm's documented contract. |
| Fix could regress the "no docs/design/ at all" case. | Item 2's `and \`docs/design/\` exists with \`.md\` files` clause is preserved — discovery still short-circuits when the directory is missing. |
| Fix could regress the explicit-reference case (item 1). | Item 1 is unchanged. Edit 2's new condition "if item 1 did not fire" explicitly defers to item 1's match. |
| Fix could regress the JIRA branch (item 3). | Item 3's existing condition (*"if no design doc found (or user ignored it)"*) is already unambiguous and inherits the fix automatically. No edits to item 3 are needed. |
| Item 2 still relies on the model reading prose; a sufficiently distracted model might still skip. | Edits 1 and 2 reinforce each other — preamble + condition both call out "regardless of inline input" / "if item 1 did not fire." This is the minimal pair that closes the loophole without a structural rewrite. |

## Out of Scope

- Rewriting `docs/design/` or `docs/jira/` schemas.
- Changing TDD's Red-Green-Refactor flow.
- Adding new metadata files or cross-skill orchestration.
- Modifying brainstorm's closing tip — the `auto-detect` promise stays as-is.
- Adding automated tests for this handoff — no `test/` fixtures exist for tdd or brainstorm context-detection paths today, and adding tests is outside the scope of this fix. Verification is manual (see below).

## Verification

Manual end-to-end testing in a scratch project:

1. **Brainstorm → TDD (no inline input).** Run `/optimus:brainstorm` (Small branch) to produce a recent `docs/design/YYYY-MM-DD-*.md`. Start a fresh conversation, invoke `/optimus:tdd` (no args). Expect: `AskUserQuestion` with `Found design doc <path> — use it as the basis for TDD?`.
2. **Brainstorm → TDD (with inline task — the failing case in the user's report).** Same setup, but invoke `/optimus:tdd "implement the catalog feature"`. Expect: the same auto-detection prompt appears before any task gathering.
3. **No design doc.** In a project without `docs/design/`, invoke `/optimus:tdd "add a thing"`. Expect: item 2 silently skipped; flow proceeds to item 3 or task gathering. No false prompt.
4. **Explicit reference.** Invoke `/optimus:tdd docs/design/X.md`. Expect: item 1 matches; item 2 is skipped (no double prompt).
5. **JIRA branch (regression check).** In a project with only `docs/jira/<key>.md`, invoke `/optimus:tdd`. Expect: item 3 fires as before.
