# spec

The design front door. `/optimus:spec` turns an idea, a JIRA ticket, or a
blank greenfield repo into an explored, approved engineering spec in
`docs/specs/` — the artifact `/optimus:tdd` picks up and implements
test-first. It designs; it never implements.

## Usage

```
/optimus:spec "add rate limiting to the public API"
/optimus:spec PROJ-123
/optimus:spec docs/specs/2026-07-10-rate-limiting.md
/optimus:spec
```

## Three ways in

- **An idea** — describe what you want to build or change, inline or when
  asked.
- **A JIRA ticket key** — the ticket is fetched read-only through whatever
  JIRA MCP tools are configured and distilled into the design conversation
  (Given/When/Then acceptance criteria carry straight into the spec's
  Scenarios). No JIRA MCP server? Paste the ticket content instead.
- **Greenfield** — no code yet, or you want product direction on paper first:
  the skill scaffolds a `docs/product/` steering cascade (product vision, MVP
  PRD, target tech stack) as skeletons with TODO markers, then stops so you
  can fill them. Re-run `/optimus:spec` afterwards; it reads the filled
  cascade as steering context for every future design.

You can also pass the path of an existing spec or draft to iterate on it.

## What it does

1. Loads project context — `.claude/CLAUDE.md`, coding guidelines, and any
   `docs/product/` steering docs.
2. Resolves the input (idea, ticket, draft, or greenfield scaffold).
3. Explores the codebase, proposes 2-3 approaches with trade-offs and a
   recommendation, and iterates with you until the design is approved.
4. Writes the spec to `docs/specs/YYYY-MM-DD-<topic-slug>.md` with
   **Status: Approved**.

## The contract with /optimus:tdd

Run `/optimus:tdd` in a fresh conversation and it auto-detects the newest
approved spec in `docs/specs/`. For stakeholder-facing or
acceptance-criteria-driven work, the spec includes a `## Scenarios` section of
`### Scenario:` headings in Given/When/Then form — tdd maps each scenario to
one Red-Green-Refactor cycle. For a large spec with independent components, a
native Claude Code dynamic workflow pointed at the spec file is an
alternative implementation route.

## What it never does

- **No implementation** — no production code, no scaffolding of source trees,
  no test writing. The deliverable is the spec.
- **No JIRA writes** — tickets are read, never created, updated, transitioned,
  or commented on.
- **No product authorship** — the greenfield cascade is emitted as neutral
  skeletons for a human to fill; the skill invents no personas, metrics, or
  technology choices, and never overwrites an existing cascade doc.

## Prerequisites

`/optimus:init` first is recommended — the generated CLAUDE.md and coding
guidelines shape design decisions. The skill still runs without them, on
generic fallbacks.

## Reference files

- `references/spec-format.md` — the spec template and the Scenarios contract
- `references/cascade-templates.md` — the greenfield `docs/product/` skeletons
