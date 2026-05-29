# Spec-driven development in optimus

This doc maps the spec-driven development (SDD) vocabulary popularised by GitHub Spec Kit, Kiro, and similar frameworks onto the existing optimus chain. It exists so users coming from those tools can recognise that optimus already implements the same workflow — just under different names. No new skill is planned for SDD support.

## What this doc is

A discoverability / framing reference. Read it if you have heard of SDD or PRDs and want to know where they fit in optimus. It is not a SKILL.md, and no skill loads it operationally.

## PRDs are out of scope; PM content has a supported path

Optimus is an engineering tool. It does not generate PRD content — no personas, no success metrics or KPIs, no business-value framing. PRDs are PM artifacts; optimus stays out of PM territory.

When PM-authored content does need to enter the workflow, the supported path is `/optimus:jira`. The jira skill fetches an issue and distills it into a fixed engineering-focused shape — Goal, Acceptance Criteria, Context, Key Decisions — saved at `docs/jira/<KEY>.md`. PM-flavored sections that don't fit those buckets are folded into Goal/Context as engineering-relevant signal or dropped. Downstream skills (`/optimus:brainstorm`, `/optimus:tdd`) treat the distilled file as engineering spec input, not as a PRD. The jira skill is, in effect, optimus's PM-firewall.

If a user has a PRD authored externally (Notion, Confluence, a Markdown file), the path is to either paste the relevant parts into a JIRA issue (then `/optimus:jira`) or describe the intent directly to `/optimus:brainstorm`. Optimus never authors a PRD itself.

## The brainstorm design doc IS the SDD spec

`/optimus:brainstorm` writes `docs/design/<slug>.md`. That doc — Goal, Context, Approach, Components, Interfaces, Edge Cases and Risks, Scenarios, Out of Scope, Open Questions — is optimus's SDD spec. The Scenarios section, in particular, is the acceptance criteria; `skills/brainstorm/references/scenario-style.md` already calls this section "the specification."

Coming from Spec Kit terminology, you do not need a separate "spec" artifact. The design doc is it.

## Phase mapping

| Stage | Spec Kit phase | Optimus equivalent |
|---|---|---|
| (Optional) | **Ingest** | `/optimus:jira` distills a PM-authored issue into `docs/jira/<KEY>.md` |
| 1 | **Specify** | `/optimus:brainstorm` Step 4 writes `docs/design/<slug>.md` with Goal, Context, Out of Scope, and conditional Scenarios (Given/When/Then) |
| 2 | **Plan** | Same brainstorm doc covers Approach, Components, Interfaces. Plan mode iteration refines it into an appended "Refined plan" section (see `references/skill-handoff.md`) |
| 3 | **Tasks** | `/optimus:tdd` Step 3 decomposes the goal into behaviors. When the design doc has a `## Scenarios` section, each `### Scenario:` maps directly to one Red-Green-Refactor cycle — the scenarios are the stakeholder-approved acceptance criteria; tdd does not re-derive a parallel behavior list |
| 4 | **Implement & Verify** | `/optimus:tdd` Red-Green-Refactor cycles, then `/optimus:pr` → `/optimus:code-review` |

The full chain from PM artifact to verified implementation: *external PM artifact (optional) → `/optimus:jira` (optional) → `/optimus:brainstorm` → plan mode (optional) → `/optimus:tdd` → `/optimus:pr` → `/optimus:code-review`*.

## When you already have a spec authored elsewhere

If you arrive with a spec written outside optimus (Spec Kit output, a Markdown doc, an external PRD), three paths exist:

- **PM-authored content in a JIRA issue** — start with `/optimus:jira <KEY>`. The jira skill distills it and recommends the next skill based on scope.
- **An engineering spec or design intent** — pass it to `/optimus:brainstorm`. Brainstorm will distill the intent, ask clarifying questions if needed, and write `docs/design/<slug>.md`.
- **A complete, decomposable spec** — reference it directly when invoking `/optimus:tdd`. The tdd skill's context-detection cascade reads `.md` files in `docs/design/` or `docs/jira/`; the scenario-driven shortcut applies if the doc contains a `## Scenarios` section in Given/When/Then form.

## What this doc is not

A positioning / discoverability doc. It does not change behavior — it only renames existing capability into vocabulary that may be more familiar to users arriving from Spec Kit or similar frameworks. If a future trend introduces a new term for the same workflow, this doc updates; the chain does not.
