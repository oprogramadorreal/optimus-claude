---
description: >-
  Guides structured design brainstorming — explores the codebase, asks clarifying
  questions, proposes multiple approaches with trade-offs, and writes an approved
  design doc to the project. Use before implementation to think through design
  decisions and avoid premature coding. Produces a persistent artifact that feeds
  into plan mode and TDD.
disable-model-invocation: true
---

# Brainstorm

Guide the user through a structured design conversation that produces a written, approved design document before any implementation begins. The output is a persistent file in the project that feeds into Claude Code plan mode and then into `/optimus:tdd` for test-first implementation.

### The Hard Gate

**No implementation until the design is approved.** Do not invoke any implementation skill, write any production code, scaffold any project structure, or take any implementation action until you have written a design doc and the user has approved it. This applies to all tasks — even seemingly simple ones. Unexamined assumptions in "simple" projects cause the most wasted effort.

## Step 1: Pre-flight

Read `$CLAUDE_PLUGIN_ROOT/skills/init/references/multi-repo-detection.md` for workspace detection. If a multi-repo workspace is detected, process within the repo the user is targeting. If ambiguous, ask which repo.

### Verify prerequisites

Check that `.claude/CLAUDE.md` exists. If it doesn't, stop and recommend running `/optimus:init` first — project context and coding guidelines shape design decisions.

Load these documents:

| Document | Role |
|----------|------|
| `.claude/CLAUDE.md` | Project overview, tech stack, architecture |
| `coding-guidelines.md` | Quality standards that constrain the design |

**Monorepo path note:** Read the "Monorepo Scoping Rule" section of `$CLAUDE_PLUGIN_ROOT/skills/init/references/constraint-doc-loading.md` for doc layout and scoping rules.

### Scan project structure

Explore the project's directory structure, key modules, and existing patterns. This grounds the design conversation in what actually exists — not assumptions.

## Step 2: Gather Intent

### JIRA context detection

Before asking the user for input, check for pre-existing JIRA context:

1. If the user's inline input matches a JIRA key pattern (`[A-Z][A-Z0-9]+-\d+`), check for `docs/jira/<key>.md`. If found, read it and use its Goal and Acceptance Criteria as the brainstorm input. If the file is not found, inform the user ("No task file found for [KEY] — run `/optimus:jira [KEY]` first to fetch it") and proceed with normal intent gathering below.

2. If no inline input (or no JIRA key match), check whether `docs/jira/` exists and contains `.md` files. If so, read each file's YAML frontmatter and select the one with the most recent `date` field. Extract the `issue` field and the Goal section. Present to the user via `AskUserQuestion` — header "JIRA context", question "Found JIRA context: [ISSUE-KEY] — [Goal]. Use this as the basis for design?":
   - **Use it** — "Design around this JIRA task"
   - **Ignore** — "Describe a different task"

   If the file's `date` frontmatter field is older than 7 days, add a note: "(This context is [N] days old — you may want to re-run `/optimus:jira` for fresh data.)"

   If **Use it**: use the file's Goal and Acceptance Criteria as the brainstorm input. Proceed to clarifying questions (skip the intent-gathering prompts below).
   If **Ignore**: proceed with normal intent gathering below.

3. If no `docs/jira/` directory or no files in it, proceed with normal intent gathering below.

### Gather from user

If the user provided a description inline (e.g., `/optimus:brainstorm "add authentication system"`), use it. Otherwise, use `AskUserQuestion` — header "Design scope", question "What do you want to build or change?":
- **New feature** — "Build something new (e.g., 'Add user authentication')"
- **Significant change** — "Rework or extend an existing part of the system"

If the description is longer than ~3 sentences (e.g., a pasted spec, ticket, or acceptance criteria), distill it into a **single-sentence goal** and confirm with `AskUserQuestion` — header "Distilled goal", question "I've distilled your input to: '[single-sentence summary]'. Is this accurate?":
- **Looks good** — "Proceed with this goal"
- **Adjust** — "Let me refine the focus"

### Clarifying questions

Before asking questions, identify your key assumptions about scope, constraints, and expected behavior. Surface them in your reply text before the first `AskUserQuestion` call so the user can correct or confirm them.

Ask up to **3 clarifying questions** to fill critical gaps — one per `AskUserQuestion` call, prefer multiple-choice options. Focus on:
- Constraints the user hasn't mentioned (performance, compatibility, security)
- Scope boundaries (what's in, what's explicitly out)
- Integration points with existing code

Skip questions if the intent is already clear. Three is the maximum, not the target.

## Step 3: Explore and Propose

### Explore relevant code

Based on the user's goal, explore the codebase areas that the design will touch:
- Existing modules, patterns, and conventions relevant to the goal
- Dependencies and integration points
- Related tests (if any) that reveal expected behavior

### Propose approaches

Present **2-3 approaches** to the user:

```
## Approaches

### A: [Name]
[Brief description — 2-3 sentences]
- **Pros:** [key advantages]
- **Cons:** [key disadvantages]
- **Effort:** [Low / Medium / High]
- **Alignment:** [how well it fits existing patterns]

### B: [Name]
...

### C: [Name] (optional — only if genuinely distinct)
...

**Recommendation:** [Approach letter] — [one-sentence rationale]
```

Use `AskUserQuestion` — header "Approach", question "Which approach should I design in detail?":
- One option per approach, with the recommendation marked

If the user wants to combine aspects of multiple approaches or suggests a different direction, incorporate their feedback and present a revised approach before proceeding.

## Step 4: Design

Based on the chosen approach, develop a detailed design. Cover each section as applicable — omit sections that don't apply to the task:

- **Goal** — single paragraph: what and why
- **Approach** — how it works, key decisions and their rationale
- **Components** — what gets created or modified, each component's responsibility
- **Interfaces** — how components interact (APIs, data flow, contracts, function signatures)
- **Edge cases and risks** — what could go wrong, mitigations
- **Out of scope** — explicit boundaries to prevent scope creep

Present the design in conversation. Use `AskUserQuestion` — header "Design review", question "Does this design look right?":
- **Approve** — "Write it to a design doc"
- **Adjust** — "I have feedback before writing"

If the user has feedback, refine the design and present it again. Iterate until approved.

## Step 5: Write Design Doc

Read `$CLAUDE_PLUGIN_ROOT/skills/brainstorm/references/design-doc-format.md` for the template.

### Write the file

- **Path:** `docs/design/YYYY-MM-DD-<topic-slug>.md` — derive the slug from the goal (lowercase, replace non-alphanumeric characters with hyphens, collapse consecutive hyphens, strip leading/trailing hyphens, max 5 words). The slug must match `[a-z0-9]+(-[a-z0-9]+)*` — reject any slug that does not match this pattern
- Create the `docs/design/` directory if it doesn't exist
- Fill the template with the approved design content
- Set **Status** to `Approved`

### Self-review

After writing, read the file back and check for:
- TODOs, placeholders, or "TBD" markers
- Internal contradictions (e.g., a component listed in Components but missing from Interfaces)
- Requirements ambiguous enough to cause someone to build the wrong thing
- YAGNI violations — features or complexity the user didn't ask for

Fix any issues found. If a fix would change a design decision, ask the user first.

## Step 6: Report

Present the result:

```
## Design Complete

**Design doc:** `<file-path>`
**Goal:** <single-sentence goal>
**Approach:** <chosen approach name>
**Components:** <count> (<count> new, <count> modified)
```

## Step 7: Next Step

Handle non-implementation tasks first:
- **Refactoring task** → tell the user: "Recommend running `/optimus:refactor` to restructure the code. **Tip:** for best results, start a fresh conversation for the next skill — each skill gathers its own context from scratch."
- **Test-only task** → tell the user: "Recommend running `/optimus:unit-test` to write tests for existing code. **Tip:** for best results, start a fresh conversation for the next skill — each skill gathers its own context from scratch."

For implementation tasks, assess complexity and deliverable shape from the Components table in the design doc.

**Prose deliverable detection.** If the Components table lists zero code components, or the Goal describes producing a written artifact (research note, audit report, investigation write-up) rather than shipping code, treat this as a **prose deliverable** and use the Prose-deliverable branch below instead of Small/Medium-to-large.

### Small (1–2 components, <5 behaviors implied)

Tell the user: "This is small enough to implement directly — run `/optimus:tdd` to build it test-first. It will auto-detect the design doc at `<file-path>`. **Tip:** for best results, start a fresh conversation for the next skill — each skill gathers its own context from scratch."

### Medium-to-large (3+ components or complex interfaces)

Generate a plan-mode prompt inline, pre-filled from the design doc. Present it as a single copyable block:

````
```
## Goal
[Goal from the design doc]

## Context
[Synthesize from the design doc's Context and Approach sections.
Include key decisions, constraints, and the chosen approach rationale.]

## Starting Hints
- Design doc: <file-path>
- [Key files/modules identified during codebase exploration in Step 3]

## What to Figure Out
1. Which existing files and modules need to be modified or extended?
2. What's the right implementation sequence given the component dependencies?
3. Are there existing patterns in the codebase to follow or reuse?
4. What are the risks or edge cases not covered in the design?

## Plan Deliverable
The plan should include:
- Proposed approach with rationale
- Files to create or modify, with what changes
- Implementation sequence and dependencies
- Test strategy mapped to each component

## Scope
- Focus on: [components from the design doc]
- Out of scope: [from the design doc's Out of Scope section]

## How this conversation should run
Treat this conversation as a review loop — validate the plan against the actual codebase and iterate with me. When I'm ready, I will toggle plan mode off in my client without approving. As soon as you observe the mode transition, append a "Refined plan" section to `<design-doc-path>` to capture the refined plan, then stop — I will start a fresh conversation to run `/optimus:tdd`.
```
````

When emitting the prompt, substitute `<design-doc-path>` with the actual path from Step 5 so the pasted block is self-contained.

Tell the user, quoting the canonical plan-mode handoff template from `$CLAUDE_PLUGIN_ROOT/references/skill-handoff.md`:

> 1. Start a fresh Claude Code conversation and switch it into **plan mode** using your client's plan-mode toggle (on the Claude Code CLI, press `Shift+Tab` until the mode indicator reads "plan mode"; in the VSCode extension or other clients, use the equivalent control). Alternatively, launch with `claude --permission-mode plan` or prefix your first message with `/plan`. Paste the prompt above as the first message.
> 2. Iterate with Claude. **Do not approve the plan** (and ignore the "Ultraplan" option if offered — both execute immediately and skip `/optimus:tdd`'s Red-Green-Refactor discipline). When you're satisfied, **toggle plan mode off without approving** (CLI: press `Shift+Tab` again; other clients: use the equivalent toggle — the mode indicator confirms you've left plan mode). The pasted prompt has already told Claude to append a "Refined plan" section to `<design-doc-path>` — it will do so now, in the same conversation, in normal mode.
> 3. Start a **second fresh conversation** and paste the execution prompt below. (Each skill's Step 1 gathers context from scratch — a clean conversation keeps that honest.)

Then emit the **execution prompt** as a second copyable block, pre-filled from the design doc:

````
```
## Goal
Run `/optimus:tdd` to implement the refined plan in `<design-doc-path>` test-first.

## Starting Hints
- Design doc (with "Refined plan" section): <design-doc-path>
- Components from the design: [list component names from the Components table]

## Scope
- Focus on: [components from the design doc]
- Out of scope: [from the design doc's Out of Scope section]
```
````

See `$CLAUDE_PLUGIN_ROOT/references/skill-handoff.md` for the full handoff convention, client-specific plan-mode controls, and why plan mode is used review-only.

### Prose deliverable (design produces a written artifact, no code)

Generate a plan-mode prompt inline, pre-filled from the design doc. Present it as a single copyable block:

````
```
## Goal
[Goal from the design doc — typically "produce `<deliverable-path>`"]

## Context
[Synthesize from the design doc's Context and Approach sections.
Include key decisions, constraints, and the chosen approach rationale.]

## Starting Hints
- Design doc: <design-doc-path>
- [Key files/modules identified during codebase exploration in Step 3]

## What to Figure Out
1. What structure should `<deliverable-path>` have?
2. What source material (files, docs, external refs) must the write-up draw on?
3. What are the risks of misrepresenting or over-scoping?

## Plan Deliverable
The plan should include:
- Outline/section structure of `<deliverable-path>`
- Source material to consult
- Tone, length, and audience
- Open questions to resolve before writing

## Scope
- Focus on: [scope from the design doc]
- Out of scope: [from the design doc's Out of Scope section]

## How this conversation should run
Treat this conversation as a review loop — validate the plan against the actual codebase and iterate with me. When I'm ready, I will toggle plan mode off in my client without approving. As soon as you observe the mode transition, append a "Refined plan" section to `<design-doc-path>` to capture the refined plan, then stop — I will start a fresh conversation to produce `<deliverable-path>`.
```
````

Substitute `<design-doc-path>` and `<deliverable-path>` with the actual paths so the pasted block is self-contained.

Tell the user, quoting the canonical plan-mode handoff template from `$CLAUDE_PLUGIN_ROOT/references/skill-handoff.md`:

> 1. Start a fresh Claude Code conversation and switch it into **plan mode** using your client's plan-mode toggle (on the Claude Code CLI, press `Shift+Tab` until the mode indicator reads "plan mode"; in the VSCode extension or other clients, use the equivalent control). Alternatively, launch with `claude --permission-mode plan` or prefix your first message with `/plan`. Paste the prompt above as the first message.
> 2. Iterate with Claude. **Do not approve the plan** (and ignore the "Ultraplan" option if offered — both execute immediately and skip the prose-execution step). When you're satisfied, **toggle plan mode off without approving** (CLI: press `Shift+Tab` again; other clients: use the equivalent toggle — the mode indicator confirms you've left plan mode). The pasted prompt has already told Claude to append a "Refined plan" section to `<design-doc-path>` — it will do so now, in the same conversation, in normal mode.
> 3. Start a **second fresh conversation** and paste the execution prompt below. (Each skill's Step 1 gathers context from scratch — a clean conversation keeps that honest. Note: `/optimus:tdd` does **not** apply here — this is a prose deliverable, not code.)

Then emit the **execution prompt** as a second copyable block, pre-filled from the design doc:

````
```
## Goal
Execute the refined plan in `<design-doc-path>` to produce `<deliverable-path>`.

## Starting Hints
- Refined plan: `<design-doc-path>` (see "Refined plan" section)
- Design doc sections: Context, Approach, Components

## Scope
- Focus on: [scope from the design doc]
- Out of scope: [from the design doc's Out of Scope section]

## How this conversation should run
Read the refined plan, then produce `<deliverable-path>` in a single pass. Do not ask for clarification unless the plan is internally contradictory.
```
````

After `<deliverable-path>` is produced, recommend running `/optimus:commit` to commit the written artifact. **Tip:** for best results, start a fresh conversation for the next skill — each skill gathers its own context from scratch.

See `$CLAUDE_PLUGIN_ROOT/references/skill-handoff.md` for the full handoff convention, client-specific plan-mode controls, and why plan mode is used review-only.
