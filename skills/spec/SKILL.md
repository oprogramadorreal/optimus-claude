---
description: >-
  Turns an idea, a JIRA ticket, or a greenfield product brief into an explored,
  approved engineering spec in docs/specs/ — the design front door before any
  implementation. Takes an inline idea, a JIRA-style ticket key (fetched
  read-only through an available JIRA MCP tool; it never creates, updates, or
  comments on tickets), or nothing (it asks). On greenfield projects it can
  instead scaffold the docs/product/ steering cascade (product vision, MVP PRD,
  tech stack) as human-fillable skeletons. Explores the codebase, proposes 2-3
  approaches with trade-offs, and iterates to an approved design; for
  acceptance-criteria-driven work the spec carries Given/When/Then Scenarios
  that /optimus:tdd consumes directly. Writes only under docs/ — no
  implementation. Running /optimus:init first is recommended so project
  guidelines shape the design.
disable-model-invocation: true
argument-hint: "[idea, ticket key, or spec path]"
---

# Spec

Guide the user through a design conversation that ends in a written, approved
spec — the single design front door. The output is a file in `docs/specs/` that
`/optimus:tdd` auto-detects and implements test-first.

**The hard gate:** no implementation in this skill. Do not write production
code, scaffold source trees, or start an implementation skill — the deliverable
is an approved spec, nothing more. This holds even for tasks that look trivial:
unexamined assumptions in "simple" work cause the most wasted effort.

## Step 1: Load project context

If this directory is part of a multi-repo workspace, detect it per
`$CLAUDE_PLUGIN_ROOT/skills/init/references/multi-repo-detection.md` and work
within the repo the user is targeting; ask if ambiguous.

Read `.claude/CLAUDE.md` and `.claude/docs/coding-guidelines.md` — project
architecture and quality standards constrain the design. If either is missing,
apply the fallbacks in
`$CLAUDE_PLUGIN_ROOT/skills/init/references/prerequisite-check.md` and
recommend `/optimus:init`.

If `docs/product/*.md` steering docs exist (product vision, MVP PRD, tech
stack), read them as higher-altitude direction that informs the design — never
as the task itself, and never as product prose to copy into the spec. In a
monorepo, scope doc loading per the "Monorepo Scoping Rule" in
`$CLAUDE_PLUGIN_ROOT/skills/init/references/constraint-doc-loading.md`.

## Step 2: Resolve the input

Route on what the user gave:

- **An inline idea or task description** — use it directly.
- **A JIRA-style ticket key** (matches `[A-Z][A-Z0-9]+-\d+`) — fetch the ticket
  with whatever JIRA MCP tools are available, **read-only**: never create,
  update, transition, or comment on tickets from this skill. Pull the summary,
  description, acceptance criteria, and any decision-bearing comments, and
  distill them into the design conversation. Preserve Given/When/Then phrasing
  in acceptance criteria — it maps directly to the spec's Scenarios section. If
  no JIRA MCP tool is available, ask the user to paste the ticket content
  instead.
- **A path to an existing spec or draft** — read it and treat it as the
  starting design to iterate on.
- **Nothing** — ask what they want to build or change.

**Greenfield route:** when there is no code yet, or the user wants product
direction on paper before designing a build, offer to scaffold the
`docs/product/` steering cascade instead of writing a spec. Read
`$CLAUDE_PLUGIN_ROOT/skills/spec/references/cascade-templates.md` and write
each missing file verbatim — never overwrite one that exists. The skeletons'
TODO markers are for a human to fill: author no product content — no personas,
no metrics, no technology picks. Then stop; tell the user to fill the cascade
top-down (vision → MVP PRD → tech stack) and re-run `/optimus:spec` when they
are ready to design the first build.

## Step 3: Explore and design

Explore the parts of the codebase the design will touch — modules, patterns,
integration points, and any tests that reveal expected behavior. Ground the
conversation in what actually exists, not assumptions. Surface the assumptions
you are making about scope and constraints, and ask clarifying questions where
the answer would genuinely change the design.

Propose 2-3 genuinely distinct approaches with their trade-offs (effort, risk,
fit with existing patterns) and recommend one. Iterate with the user — combine
approaches, adjust scope, revisit constraints — until they approve a design.
Keep the design engineering-focused: steering docs set direction, but the
approved task defines the work.

## Step 4: Write the spec

Write the approved design to `docs/specs/YYYY-MM-DD-<topic-slug>.md` following
`$CLAUDE_PLUGIN_ROOT/skills/spec/references/spec-format.md`, with **Status:
Approved**. Slug: lowercase, hyphen-separated, at most 5 words. Create
`docs/specs/` if needed; if the target file already exists, ask before
overwriting or pick a suffixed name.

For stakeholder-facing or acceptance-criteria-driven work, include a
`## Scenarios` section with `### Scenario:` headings in Given/When/Then form —
`/optimus:tdd` consumes those headings directly as its behavior list, so keep
the format exact. The reference carries the contract and the inclusion signals.

Read the file back before finishing: no TODOs or placeholders, no
contradictions between sections, no scope the user did not approve. If fixing
an issue would change a design decision, ask first.

## Next step

Suggest `/optimus:tdd` in a fresh conversation — it auto-detects the newest
approved spec in `docs/specs/` and implements it test-first. For a large spec
with independent, parallelizable components, a native Claude Code dynamic
workflow pointed at the spec is a reasonable alternative to supervised TDD.
