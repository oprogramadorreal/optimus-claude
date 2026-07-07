---
description: >-
  Guides structured design brainstorming — explores the codebase, asks clarifying
  questions, proposes multiple approaches with trade-offs, and writes an approved
  spec to docs/specs/ for /optimus:tdd and /optimus:workflow to auto-detect.
  Use before implementation to think through design
  decisions and avoid premature coding. Produces a persistent artifact that feeds
  into plan mode and TDD. For stakeholder-facing or acceptance-criteria-driven
  work, the spec includes a Given/When/Then Scenarios section consumed by
  /optimus:tdd.
disable-model-invocation: true
argument-hint: "[topic or JIRA key]"
---

# Brainstorm

Guide the user through a structured design conversation that produces a written, approved spec before any implementation begins. The output is a persistent file in the project that feeds into Claude Code plan mode and then into `/optimus:tdd` for test-first implementation.

### The Hard Gate

**No implementation until the design is approved.** Do not invoke any implementation skill, write any production code, scaffold any project structure, or take any implementation action until you have written a spec and the user has approved it. This applies to all tasks — even seemingly simple ones. Unexamined assumptions in "simple" projects cause the most wasted effort.

## Step 1: Pre-flight

Read `$CLAUDE_PLUGIN_ROOT/skills/init/references/multi-repo-detection.md` for workspace detection. If a multi-repo workspace is detected, process within the repo the user is targeting. If ambiguous, ask which repo.

### Verify prerequisites

Check that `.claude/CLAUDE.md` exists. If it doesn't, stop and recommend running `/optimus:init` first — project context and coding guidelines shape design decisions.

Load these documents:

| Document | Role |
|----------|------|
| `.claude/CLAUDE.md` | Project overview, tech stack, architecture |
| `coding-guidelines.md` | Quality standards that constrain the design |
| `docs/product/product-context.md` *(if present)* | Product vision — steering context |
| `docs/product/mvp-prd.md` *(if present)* | MVP scope — steering context |
| `docs/product/tech-stack.md` *(if present)* | Target tech stack — steering context |

The three `docs/` rows are the optional spec-driven-development steering cascade (scaffolded by `/optimus:spec-init`). Load them **only if they exist**, and treat them as higher-altitude direction that *informs* the design — never as the task itself or as content to copy. The spec you write stays engineering-focused: do **not** author product/PM prose (personas, KPIs, business-value) into it. See `$CLAUDE_PLUGIN_ROOT/references/sdd-mapping.md` for the precedence contract.

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

- **Goal** — single sentence: what and why
- **Context** — why the change is needed and the relevant existing state (what exists today, what's missing, what's broken)
- **Approach** — how it works, key decisions and their rationale
- **Components** — what gets created or modified, each component's responsibility
- **Interfaces** — how components interact (APIs, data flow, contracts, function signatures)
- **Edge cases and risks** — what could go wrong, mitigations
- **Scenarios** — *conditional.* 3–7 Given/When/Then scenarios that `/optimus:tdd` consumes as the behavior list. See `$CLAUDE_PLUGIN_ROOT/skills/brainstorm/references/scenario-style.md` for inclusion signals and phrasing — read it before writing scenarios.
- **Out of scope** — explicit boundaries to prevent scope creep
- **Open questions** — decisions deferred or needing more information (omit if none)

Present the design in conversation. Use `AskUserQuestion` — header "Design review", question "Does this design look right?":
- **Approve** — "Write it to a spec"
- **Adjust** — "I have feedback before writing"

If the user has feedback, refine the design and present it again. Iterate until approved.

## Step 5: Write the Spec

Read `$CLAUDE_PLUGIN_ROOT/skills/brainstorm/references/spec-format.md` for the template.

### Write the file

- **Path:** `docs/specs/YYYY-MM-DD-<topic-slug>.md` — derive the slug from the goal (lowercase, replace non-alphanumeric characters with hyphens, collapse consecutive hyphens, strip leading/trailing hyphens, max 5 words). The slug must match `[a-z0-9]+(-[a-z0-9]+)*` — reject any slug that does not match this pattern
- Create the `docs/specs/` directory if it doesn't exist
- If the target file already exists (e.g., a same-day re-brainstorm of the same topic), ask the user via `AskUserQuestion` whether to overwrite it or write to a suffixed filename (append `-2`, `-3`, … to the slug); on overwrite, carry any existing `### Refined plan` section into the new file — it captures plan-mode iteration the append-not-overwrite rule exists to preserve
- Fill the template with the approved design content
- Set **Status** to `Approved`

### Self-review

After writing, read the file back and check for:
- TODOs, placeholders, or "TBD" markers
- Internal contradictions (e.g., a component listed in Components but missing from Interfaces)
- Requirements ambiguous enough to cause someone to build the wrong thing
- YAGNI violations — features or complexity the user didn't ask for
- If a Scenarios section was included: re-check it against `$CLAUDE_PLUGIN_ROOT/skills/brainstorm/references/scenario-style.md` (Discipline and Anti-patterns)

Fix any issues found. If a fix would change a design decision, ask the user first.

## Step 6: Report

Present the result:

```
## Design Complete

**Spec:** `<spec-path>`
**Goal:** <single-sentence goal>
**Approach:** <chosen approach name>
**Components:** <count> (<count> new, <count> modified)
```

## Step 7: Next Step

Handle non-implementation tasks first. Neither skill below reads `docs/specs/` on its own — include the spec path in the handoff so the approved design isn't dropped:
- **Refactoring task** → tell the user: "Recommend running `/optimus:refactor` to restructure the code, passing the scope and key decisions from `<spec-path>` as the scope argument. **Tip:** for best results, start a fresh conversation for the next skill — each skill gathers its own context from scratch."
- **Test-only task** → tell the user: "Recommend running `/optimus:unit-test` to write tests for existing code, passing the target paths from `<spec-path>` as the path argument. **Tip:** for best results, start a fresh conversation for the next skill — each skill gathers its own context from scratch."

For implementation tasks, assess complexity from the Components table in the spec. If the Components table lists zero code components or the Goal names a written artifact (research note, audit report, investigation write-up), the deliverable is **prose** — read the "Prose deliverable" note at the end of this step first, then use the Medium-to-large branch below with its adjustments (they replace the prompt closer, the user steps, and the execution prompt).

### Small (1–2 components, <5 behaviors implied)

Tell the user: "This is small enough to implement directly — run **`/optimus:tdd`** to build it test-first (Red-Green-Refactor, interactive checkpoints). It auto-detects the spec at `<spec-path>`. (You can use **`/optimus:workflow`** instead for a self-orchestrated parallel build — test-first as a quality bar, no mid-run input, more tokens — but for a spec this small TDD is usually the better fit; `/optimus:workflow` shines on large or parallelizable specs.) **Tip:** for best results, start a fresh conversation for the next skill — each skill gathers its own context from scratch."

### Medium-to-large (3+ components, complex interfaces, or anything not matching Small)

**Alternative — a parallel build (code deliverables only):** if the user prefers a self-orchestrated parallel build over supervised TDD, they can run **`/optimus:workflow`** instead. It auto-detects the spec at `<spec-path>`, launches a Claude Code dynamic workflow directly (no plan-mode iteration, no "Refined plan" step), applies test-first as a quality bar, and uses meaningfully more tokens. **If the user takes this alternative, skip the plan-mode prompt and execution-prompt blocks below** — point them to `/optimus:workflow` (in a fresh conversation) and stop here. Otherwise the plan-mode → `/optimus:tdd` flow below remains the default for supervised, test-first work. For a **prose deliverable**, skip this alternative — `/optimus:workflow` is overkill for documentation-only work (see the "Prose deliverable" note below).

Generate a plan-mode prompt inline, pre-filled from the spec. Present it as a single copyable block:

````
```
## Goal
[Goal from the spec]

## Context
[Synthesize from the spec's Context and Approach sections.
Include key decisions, constraints, and the chosen approach rationale.]

## Starting Hints
- Spec: <spec-path>
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
- Focus on: [components from the spec]
- Out of scope: [from the spec's Out of Scope section]

[Close the prompt with the "## How this conversation should run" section from `$CLAUDE_PLUGIN_ROOT/references/skill-handoff.md` "Carve-out canonical blocks", substituting `<doc-path>` = `<spec-path>`.]
```
````

Substitute `<spec-path>` with the actual path from Step 5 wherever it appears in Steps 6–7 — the report, the branch texts, and every emitted prompt block — so each pasted block is self-contained.

Tell the user the three numbered plan-mode steps from `$CLAUDE_PLUGIN_ROOT/references/skill-handoff.md` "Carve-out canonical blocks" verbatim, substituting `<doc-path>` = `<spec-path>`.

Then emit the **execution prompt** as a second copyable block, pre-filled from the spec:

````
```
## Goal
Run `/optimus:tdd` to implement the refined plan in `<spec-path>` test-first.

## Starting Hints
- Spec (with "Refined plan" section): <spec-path>
- Components from the spec: [list component names from the Components table]

## Scope
- Focus on: [components from the spec]
- Out of scope: [from the spec's Out of Scope section]
```
````

**Prose deliverable:** if the design produces a written artifact rather than code, `/optimus:tdd` does **not** apply — follow the default plan-mode flow (approve the plan to implement in the same conversation; see `$CLAUDE_PLUGIN_ROOT/references/skill-handoff.md` "Plan mode") instead of the review-only carve-out. Adjust the Medium-to-large branch as follows:

- Close the plan-mode prompt with a `## How this conversation should run` section that says: iterate on the plan against the actual codebase; once the user approves the plan, implement it in this conversation to produce `<deliverable-path>`; after writing the deliverable, recommend `/optimus:commit` to commit it, followed by the closing tip. Substitute the tip text into the prompt — **Variant A** from skill-handoff.md "Closing tip wording" with `<continuation-skill(s)>` = `/optimus:commit` and `<non-continuation-examples>` = `/optimus:code-review`, `/optimus:unit-test` — so the executing conversation can emit it verbatim after the deliverable exists.
- Instead of the three carve-out steps, tell the user: start a fresh conversation in **plan mode**, paste the prompt, iterate, and **approve the plan** when satisfied — approval implements it in the same conversation (no `### Refined plan` append, no second conversation).
- Skip the execution prompt above entirely.

See `$CLAUDE_PLUGIN_ROOT/references/skill-handoff.md` for the full handoff convention and why plan mode is review-only on the `/optimus:tdd` path.
