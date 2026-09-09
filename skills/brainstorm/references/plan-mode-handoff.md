# Plan-mode handoff

Shared procedure for skills that hand a design off through Claude Code's plan mode (`brainstorm`, `jira`). Owned by brainstorm.

## Codex handoff

Under Codex, use this branch instead of the Claude-specific toggle/approval steps
below. Keep the same Prompt skeleton and exact `### Refined plan` artifact heading,
using `$optimus:tdd` in the execution prompt.

Offer plan review in the host's available plan mode, or an ordinary conversation
explicitly scoped to reviewing the plan without implementation. Do not prescribe
Claude keyboard shortcuts, ExitPlanMode, or assume that approving a Codex plan
dispatches a skill. After review, save the refined plan to the actual source path
only in a write-enabled conversation with the user's authorization. If the host
cannot save it yet, provide a copyable refined plan and execution prompt containing
the unresolved decisions and source path; do not claim the file was updated.

For implementation, give a copyable `$optimus:tdd` prompt referencing the approved
plan in a fresh conversation. For prose, continue writing the approved deliverable
when authorized, then recommend `$optimus:commit` in that conversation. Use the
native host controls where available; the durable plan is the shared handoff.

## Plan-mode facts the handoff relies on

- **Approving a plan executes it immediately in the same conversation.** That is the intended flow and the right default for most deliverables.
- Plan mode is **read-only** — any file write ("append the refined plan") happens only after the user toggles plan mode off **and sends a follow-up message**; the toggle itself does not trigger Claude.
- Plan mode is a **client UI toggle** (CLI: `Shift+Tab`; other clients: their equivalent control) — no phrase exits it. Describe the action client-agnostically. An "Ultraplan" approval option executes the plan — treat it like approval.

## Choosing the flow

- **Default — prose deliverables, or any plan NOT routed to `/optimus:tdd`:** iterate in plan mode, then **approve the plan to implement in the same conversation**. After implementation, `/optimus:commit` and `/optimus:pr` should run in that same conversation so they can capture the implementation context.
- **Carve-out — work routed to `/optimus:tdd`:** treat plan mode as **review-only**. Approval would execute immediately and bypass TDD's Red-Green-Refactor discipline. Use the canonical blocks below.

## Prompt skeleton

Both the plan-mode prompt and the execution prompt use this shape. Fill each section from whatever source document the consuming skill holds (a `docs/specs/` spec, a `docs/jira/` task file), and substitute the real path so every pasted block is self-contained.

````
```
## Goal
[Plan-mode prompt: the goal from the source document.
 Execution prompt: "Run /optimus:tdd to implement the refined plan in <doc-path> test-first."]

## Context
[Plan-mode prompt only: key decisions, constraints, and the rationale for the chosen approach.
 Omit this section from the execution prompt.]

## Starting Hints
- <doc-path>  [execution prompt: note that it now carries a "Refined plan" section]
- [Key files, modules, or components the source document names]

## Scope
- Focus on: [components or area from the source document]
- Out of scope: [what the source document excludes]
```
````

## Carve-out canonical blocks

Close the generated plan-mode prompt with this section, substituting `<doc-path>` with the actual spec/task file path. The `### Refined plan` heading is exact — jira's refresh and enrichment procedures preserve that section by that literal string:

```
## How this conversation should run
Treat this conversation as a review loop — validate the plan against the actual codebase and iterate with me. When I say I'm done iterating, acknowledge but do not write yet — plan mode is read-only. I will then toggle plan mode off and send a short follow-up message (e.g. "go"). On that follow-up, append a `### Refined plan` section (heading exactly `### Refined plan`) to `<doc-path>` to capture the refined plan, and stop. I will start a fresh conversation to run `/optimus:tdd`.
```

After presenting the prompt, tell the user these three steps (substituting `<doc-path>`):

> 1. Start a fresh Claude Code conversation in **plan mode** (CLI: press `Shift+Tab` until the mode indicator shows plan mode; other clients: use the equivalent toggle). Paste the prompt above.
> 2. Iterate with Claude. **Do not approve the plan** — approval executes immediately and skips `/optimus:tdd`'s Red-Green-Refactor discipline. When you're satisfied, tell Claude you're done iterating; Claude will acknowledge. Then toggle plan mode off using the same control **and send a short follow-up message (e.g. "go")** — Claude will append a `### Refined plan` section to `<doc-path>` in response.
> 3. Start a **second fresh conversation** and paste the execution prompt below.
