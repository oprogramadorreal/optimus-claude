# Spec-driven development in optimus

This doc maps the spec-driven development (SDD) vocabulary popularised by GitHub Spec Kit, Kiro, and similar frameworks onto the existing optimus chain, **and** defines the contract for the docs-first cascade that `/optimus:spec-init` scaffolds. It exists so users coming from those tools recognise that optimus already implements the same workflow — and so the scaffolder, `brainstorm`, and `tdd` share one precedence model instead of three.

## What this doc is

A framing reference **and** a shared contract. Two audiences:

- **Discoverability** — read it if you have heard of SDD or PRDs and want to know where they fit in optimus.
- **Contract** — `skills/spec-init/SKILL.md`, `skills/brainstorm/SKILL.md`, and `skills/tdd/SKILL.md` point here for the single canonical precedence order, the spec-location rules, and the architecture-name disambiguation. Keep those rules defined **only** here so the skills never duplicate (or drift from) them.

It is not a SKILL.md, and no skill loads it for *behavior* — the skills implement the contract this doc describes.

## The optimus scope boundary (unchanged)

Optimus is an engineering tool. It does **not author** PM content — no personas, no success metrics or KPIs, no business-value framing. PRDs are PM artifacts; optimus stays out of PM territory.

What changed (2026-05-31): optimus now **scaffolds an empty, product-neutral docs-first cascade** and **reads it as steering**, but it still authors nothing PM-flavored. `/optimus:spec-init` stamps blank skeletons with `TODO` markers for a human to fill; `brainstorm` and `tdd` read the filled docs as higher-altitude context. The authoring boundary is intact: optimus writes engineering specs (in `docs/design/`), never product prose. See the durable rationale in `docs/design/prd-spec-skill-evaluation.md`.

When PM-authored content needs to enter the workflow, the supported path is still `/optimus:jira`. The jira skill distills an issue into a fixed engineering shape — Goal, Acceptance Criteria, Context, Key Decisions — at `docs/jira/<KEY>.md`. The jira skill is, in effect, optimus's PM-firewall. If a user has a PRD authored externally (Notion, Confluence, a Markdown file), the path is to paste the relevant parts into a JIRA issue (then `/optimus:jira`) or describe the intent directly to `/optimus:brainstorm`. Optimus never authors a PRD itself.

## The cascade (what spec-init scaffolds)

`/optimus:spec-init` scaffolds three **steering** documents under the project root — empty skeletons a human fills:

| Doc | Altitude | Holds |
|---|---|---|
| `docs/product/product-context.md` | highest | Long-term product vision — the destination. |
| `docs/product/mvp-prd.md` | middle | The first product slice (MVP) — still product/PM language. |
| `docs/architecture/tech-stack.md` | lower | The **target** technologies the product grows toward (not a constraint on the current build). |

It deliberately does **not** scaffold a fourth "spec" file — see [Spec location](#spec-location-docsdesign-vs-docsspecs).

## Canonical precedence (the contract)

These docs describe **direction at decreasing altitude**:

> **product vision → MVP PRD → target tech-stack → active build spec**

Higher docs set long-term direction; the **active build spec** governs what to build *right now*. **When they conflict about current work, the active build spec wins.** There is exactly one precedence statement and it lives here — the scaffolded doc headers and the three skills all reference this line rather than restating their own.

(This resolves an ambiguity worth avoiding: cascades in the wild sometimes state a 4-level order in one doc and a 3-level order in another. optimus states it once, here.)

## Spec location: docs/design vs docs/specs

The lowest-altitude **active build spec** can live in either of two places, and both feed `/optimus:tdd`:

- **`docs/design/<slug>.md` — optimus-authored.** `/optimus:brainstorm` writes this. It *is* optimus's SDD spec: Goal, Context, Approach, Components, Interfaces, Edge Cases and Risks, **Scenarios** (Given/When/Then — the acceptance criteria), Out of Scope, Open Questions. `skills/brainstorm/references/scenario-style.md` already calls the Scenarios section "the specification." This is the canonical, recommended spec.
- **`docs/specs/<spec>.md` — human-authored (or from an external SDD tool).** optimus **authors nothing here.** `tdd` can consume it via its existing explicit-reference path (point tdd at the file). Use this slot if you arrive with a spec written outside optimus (Spec Kit output, a Markdown doc).

Coming from Spec Kit terminology: you do not need a separate optimus-written "spec" artifact — the brainstorm design doc is it. `docs/specs/` is the bring-your-own-spec slot, not something optimus populates.

## Architecture-name disambiguation

Two files contain "architecture" in their path. They never overlap:

| File | Owner | Lifecycle | Holds |
|---|---|---|---|
| `docs/architecture/tech-stack.md` | human (scaffolded empty by spec-init) | **pre-code** steering | the target stack the product grows toward |
| `.claude/docs/architecture.md` | `/optimus:init` | **post-code** conventions | the actual code-structure: directory map, data flow, module boundaries, skill/agent hierarchy |

Different trees, different basenames, disjoint lifecycles — and because all cascade scaffolding lives in `spec-init`, the two never meet in one code path. Keep the filename `tech-stack.md` (do **not** rename it to `architecture.md`). If a root-level architecture/solution-design doc is ever added later, name it `solution-design.md`, never `architecture.md`, to preserve the basename distinction.

## No separate "constitution" needed

Spec Kit adds a `constitution.md` and Kiro a `structure.md` to hold project-wide invariants. optimus already has that governance layer for the engineering side: `.claude/CLAUDE.md` plus `.claude/docs/coding-guidelines.md` (and `skill-writing-guidelines.md`) are authored by `/optimus:init` and loaded by the engineering skills. The cascade therefore needs no separate principles/constitution doc — the steering docs carry product *direction*, and `.claude/` carries engineering *governance*.

## The brainstorm design doc IS the SDD spec

`/optimus:brainstorm` writes `docs/design/<slug>.md`. That doc is optimus's SDD spec; its Scenarios section is the acceptance criteria. Coming from Spec Kit terminology, you do not need a separate "spec" artifact. The design doc is it.

## Phase mapping

| Stage | Spec Kit phase | Optimus equivalent |
|---|---|---|
| (Optional) | **Steering / Bootstrap** | `/optimus:spec-init` scaffolds empty `docs/product/` + `docs/architecture/tech-stack.md`; a human fills the vision, MVP PRD, and target stack |
| (Optional) | **Ingest** | `/optimus:jira` distills a PM-authored issue into `docs/jira/<KEY>.md` |
| 1 | **Specify** | `/optimus:brainstorm` Step 4 writes `docs/design/<slug>.md` (Goal, Context, Out of Scope, and conditional Scenarios), reading the cascade as steering |
| 2 | **Plan** | Same brainstorm doc covers Approach, Components, Interfaces. Plan mode iteration refines it into an appended "Refined plan" section (see `references/skill-handoff.md`) |
| 3 | **Tasks** | `/optimus:tdd` Step 3 decomposes the goal into behaviors. When the design doc has a `## Scenarios` section, each `### Scenario:` maps to one Red-Green-Refactor cycle |
| 4 | **Implement & Verify** | `/optimus:tdd` Red-Green-Refactor cycles, then `/optimus:pr` → `/optimus:code-review` |

The full chain: *`/optimus:spec-init` (scaffold steering, optional) → human fills the cascade → external PM artifact → `/optimus:jira` (optional) → `/optimus:brainstorm` (reads cascade as steering) → plan mode (optional) → `/optimus:tdd` (reads spec/design + cascade) → `/optimus:pr` → `/optimus:code-review`*.

## When you already have a spec authored elsewhere

If you arrive with a spec written outside optimus (Spec Kit output, a Markdown doc, an external PRD), three paths exist:

- **PM-authored content in a JIRA issue** — start with `/optimus:jira <KEY>`. The jira skill distills it and recommends the next skill based on scope.
- **An engineering spec or design intent** — pass it to `/optimus:brainstorm`. Brainstorm distills the intent, asks clarifying questions if needed, and writes `docs/design/<slug>.md`.
- **A complete, decomposable spec** — drop it at `docs/specs/<spec>.md` and reference it directly when invoking `/optimus:tdd`. The tdd context-detection cascade reads `.md` files via explicit reference; the scenario-driven shortcut applies if the doc contains a `## Scenarios` section in Given/When/Then form.

## What this doc is not

A SKILL.md. No skill loads it for behavior — it documents the contract the skills implement and frames existing capability in SDD vocabulary. If a future trend introduces a new term for the same workflow, this doc updates; the chain does not.
