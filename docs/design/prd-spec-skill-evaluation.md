# PRD / SDD skill evaluation

**Date:** 2026-05-28
**Status:** Decided — no new skill; ship `references/sdd-mapping.md`

This file is the durable audit record for whether optimus-claude should add a dedicated PRD or spec-driven-development (SDD) skill. It exists so future maintainers can see how the question was framed, what was considered, and why the call was made. New iterations append below; nothing is overwritten.

## Refined plan

### Context

The maintainer saw industry buzz around spec-driven development (SDD) — GitHub Spec Kit, AWS Kiro, Tessl — and asked whether optimus-claude should add a `/optimus:prd` or `/optimus:spec` skill, or whether existing skills (`/optimus:brainstorm`, `/optimus:tdd`) already absorb that workflow. The decision must balance discovery overhead from a larger skill catalog against scope dilution if existing skills are overloaded.

Clarifying signals from the maintainer:
- **Trigger:** industry buzz (Spec Kit / Kiro). Not user-driven demand, not felt pain.
- **README line 111 stance** ("no new skill, no Cucumber/Gherkin tooling") is about a different question (formal acceptance-criteria tooling), not about PRD/SDD as an upstream planning workflow. Analyze both fresh.
- **PRD vs. spec scope (load-bearing):** PRD content (personas, KPIs, business-value framing) is **not optimus's concern** — optimus is an engineering tool, PRDs are PM territory. The **engineering-facing SDD spec** IS in optimus's mandate, and `/optimus:brainstorm` already produces it. The plan should lean into that framing rather than treat PRD/SDD as a single combined question.
- **JIRA is optimus's PM-to-engineering bridge.** The closest thing to PM-territory content that optimus interacts with is the body of a JIRA issue, and `/optimus:jira` is the canonical bridge that pulls it in. The plan must analyze where the PM/engineering boundary sits inside that skill.
- **Docs clarification is approved** as part of this plan (not deferred as a follow-up).

---

### 1. Concepts primer

#### PRD vs. SDD spec — the distinction that matters here

| | PRD | SDD spec |
|---|---|---|
| **What** | Product-facing artifact: what to build and *why*, in user-centric terms | Engineering-facing artifact: what to build in enough detail for an AI agent to implement, with verifiable acceptance criteria |
| **Author** | PM (or whoever holds the product hat) | Tech lead, often co-written with AI |
| **Audience** | Stakeholders, design, engineering | The implementing agent + reviewers |
| **Typical sections** | Problem, target users / personas, user stories, success metrics / KPIs, scope, open questions, timeline | Goal, context, approach, components, interfaces, acceptance criteria (Given/When/Then), out-of-scope, open questions |
| **Lifecycle slot** | `idea → PRD → design → engineering` | `design → spec → implementation` (or, in SDD, the spec drives implementation directly) |
| **Optimus relevance** | **Out of scope.** PM ceremony; not what optimus is for. | **In scope.** Brainstorm already produces this as `docs/design/<slug>.md`. |

Sources: [Atlassian — Product requirements documentation](https://www.atlassian.com/agile/product-management/requirements), [Productboard — PRD vs Product Spec](https://www.productboard.com/glossary/prd-vs-product-spec/).

#### SDD (Spec-Driven Development) — LLM-era sense

The 2025 industry usage refers to a workflow where a human writes a detailed, structured natural-language specification that an AI agent then implements. The spec is the durable contract; code is the (regeneratable) output. [Thoughtworks](https://www.thoughtworks.com/en-us/insights/blog/agile-engineering-practices/spec-driven-development-unpacking-2025-new-engineering-practices) defines it as *"a development paradigm that uses well-crafted software requirement specifications as prompts, aided by AI coding agents, to generate executable code."* (An older, pre-LLM sense — formal-methods specification languages — also exists but is not what the buzz is about.)

The reference framework is [GitHub's Spec Kit](https://github.com/github/spec-kit), which formalizes SDD into four gated phases:
1. **Specify** — write a natural-language spec describing the *what* and *why*.
2. **Plan** — derive a technical plan from the spec.
3. **Tasks** — decompose the plan into individually testable units.
4. **Implement & Verify** — the agent implements each unit, verifying against the spec.

SDD's contrast: **vibe coding** (prompt-and-pray, no durable artifact, drift). SDD's value: the spec is durable, the agent's output is verifiable against it, and re-running the agent produces consistent results.

Other named tools in this space: AWS Kiro, Tessl, Google Antigravity [uncertain] — adjacent reference points, not directly verified for this primer.

#### How this maps onto optimus

Optimus's chain already implements all four Spec Kit phases without using SDD vocabulary:

| Spec Kit phase | Optimus equivalent |
|---|---|
| **Specify** | `/optimus:brainstorm` Step 4 writes `docs/design/<slug>.md` with Goal, Context, Out of Scope, and conditional **Scenarios** (Given/When/Then) |
| **Plan** | Same brainstorm doc covers Approach, Components, Interfaces. Plan mode iteration refines it into an appended "Refined plan" section (`references/skill-handoff.md`, "Plan mode" section — the `/optimus:tdd` carve-out) |
| **Tasks** | `/optimus:tdd` Step 3 decomposes the goal into behaviors. The scenario-driven shortcut (`skills/tdd/SKILL.md` line 136) maps each `### Scenario:` directly to one Red-Green-Refactor cycle — *the scenarios are the stakeholder-approved acceptance criteria; do not re-derive a parallel behavior list* |
| **Implement & Verify** | `/optimus:tdd` Red-Green-Refactor cycles, then `/optimus:pr` → `/optimus:code-review` |

The plugin already calls the design doc the specification, in its own words: `skills/brainstorm/references/scenario-style.md` line 52 — *"The Scenarios section is the **specification**. It belongs in the design doc, alongside Goal/Approach/Components/Interfaces."*

---

### 2. Current state assessment

**Optimus already implements an SDD workflow for engineering specs. It does not — and should not — generate PRD content.**

**What `/optimus:brainstorm` produces today** (`skills/brainstorm/references/design-doc-format.md`):
- **Spec-shaped:** Context (problem statement), Goal, Approach, Components, Interfaces, Edge Cases and Risks, Scenarios (acceptance criteria), Out of Scope, Open Questions.
- **Not PRD-shaped:** no personas, no KPIs / success metrics, no business-value framing, no timeline. The doc is engineering-facing.

**What `/optimus:tdd` does with it** (`skills/tdd/SKILL.md` lines 50–60, 136):
- Auto-discovers `docs/design/<slug>.md` via context cascade.
- Uses Scenarios as the verbatim behavior list (one scenario = one Red-Green-Refactor cycle).
- Falls back to its own behavior decomposition when no spec is present.

**What `/optimus:jira` does upstream** (`skills/jira/SKILL.md`):
- Distills JIRA tickets into `docs/jira/<KEY>.md` with Goal and Acceptance Criteria.
- Feeds the same context cascade as brainstorm's output.

#### JIRA is the PM-to-engineering bridge

JIRA is the only place in optimus's chain where PM-territory content enters. A JIRA issue authored by a PM may contain PRD-flavored content — user stories, business-value framing, sometimes personas or KPIs in the description — alongside acceptance criteria and technical notes. `/optimus:jira` translates that content into the engineering domain:

- **Step 4 distillation** (`skills/jira/SKILL.md` lines 69–99) extracts a fixed structured shape: **Goal** (1 sentence), **Acceptance Criteria** (numbered list), **Context** (type, status, sprint, parent, linked issues), **Key Decisions** (from comments). PM-flavored sections that don't fit those buckets are folded into Goal/Context as engineering-relevant signal or dropped.
- **The output is engineering-focused by design.** No personas section, no KPIs section, no business-value section. The fixed shape enforces the scope boundary: PM content goes in; only engineering-relevant signal comes out.
- **Downstream consumers (`/optimus:brainstorm`, `/optimus:tdd`) treat the distilled file as engineering spec input**, not as a PRD. The jira skill's distillation is what makes that safe.

This means optimus's scope principle ("optimus doesn't author PM content") is reinforced by the architecture — the only ingestion path for PM content is through `/optimus:jira`, which strips PM noise before anything else in the chain sees it. The jira skill is, in effect, optimus's PM-firewall. No change needed to the skill itself for the PRD/SDD question; it already implements the right boundary.

The implication for the SDD-mapping doc: it should explicitly name `/optimus:jira` as the supported path for users who *do* have PM-authored content (a JIRA ticket, a PRD authored externally) so they don't reach for a non-existent `/optimus:prd`. The full ingestion-to-implementation flow becomes: *external PM artifact (JIRA or other) → `/optimus:jira` distillation (optional) → `/optimus:brainstorm` spec authoring → plan mode → `/optimus:tdd` → `/optimus:pr` → `/optimus:code-review`*.

**Where current coverage is strong:**
- Spec authoring: brainstorm's design doc template covers all engineering-facing spec sections.
- Spec-to-implementation handoff: tdd's auto-discovery + scenario-driven shortcut implements SDD's "tasks" phase precisely.
- External requirements ingestion: jira's distillation feeds the same cascade, so externally-sourced specs also work.

**Where coverage is thinner (and intentionally so):**
- No PRD-flavored sections (personas, KPIs, business-value). This is **a deliberate scope boundary**, not a gap. Optimus is for engineers; PRDs are PM artifacts.
- SDD's "the spec is the durable contract" framing is not made explicit in the current docs. The brainstorm design doc serves this role, but a reader coming from Spec Kit may not recognize the equivalence. **This is a discoverability gap, not a capability gap.**

---

### 3. Options comparison

| Option | Discoverability impact | Scope-dilution risk | Redundancy w/ existing | Chain impact | Aligns with optimus scope? |
|---|---|---|---|---|---|
| **A. Add `/optimus:prd`** | -1 (17→18 skills; PRD content drags optimus into PM territory) | High — pulls optimus into PM artifacts (personas, KPIs) | Some overlap with brainstorm | Adds a step upstream of brainstorm | **No** — explicitly outside optimus's engineering-facing mandate |
| **A'. Add `/optimus:spec`** | -1 (17→18 skills; two overlapping spec authors) | Low | **High** — brainstorm already authors specs | Adds a step upstream of brainstorm, or replaces it | Partial — but redundant with brainstorm |
| **B. Extend `/optimus:brainstorm`** | 0 (same skill) | Medium — adds a mode and decision point | Low | None | Yes, but unnecessary — brainstorm already produces a spec |
| **C. Extend `/optimus:tdd`** | 0 (no new skill) | None | **Already implemented** | None | Yes — done |
| **D. No new skill; add SDD-mapping doc** | +1 (clarifies existing capability for SDD-aware users without growing catalog) | None | None | None | Yes — frames existing chain in SDD vocabulary |

**Option A — Add `/optimus:prd`:** Rejected. PRD content is PM territory; optimus is an engineering tool. Adding a skill that asks users to fill in personas, KPIs, and business-value statements would push optimus outside its mandate and create a maintenance burden for PM-flavored content that no engineering user actually wants.

**Option A' — Add `/optimus:spec`:** Rejected. Two overlapping spec authors (`spec` and `brainstorm`) is a real discoverability tax; users have to learn the difference and choose. The brainstorm doc *is* the spec — naming a second skill the same thing creates confusion, not clarity.

**Option B — Extend `/optimus:brainstorm`:** Rejected. Brainstorm already covers SDD's Specify and Plan phases. The only thing that could be added is PRD content, which Option A already ruled out. No actionable extension remains.

**Option C — Extend `/optimus:tdd`:** Already done. Lines 52–60 (context cascade), line 136 (scenario-driven shortcut). No work needed.

**Option D — No new skill; ship an SDD-mapping doc:** Recommended. The maintainer's concern is partly real ("Spec Kit users coming to optimus may not recognize that the design doc is the spec") and partly not ("optimus is missing SDD support"). The right response is to fix the discoverability problem without inflating the catalog.

---

### 4. Recommendation

**Option D — no new skill; ship a small SDD-mapping doc that:**
1. Names PRD content explicitly out of scope for optimus (engineering tool, not PM tool).
2. Names the brainstorm design doc as optimus's SDD spec.
3. Maps Spec Kit's four phases onto the existing brainstorm → plan-mode → tdd → pr → code-review chain.

The trigger is industry buzz, not user pain. Adding a skill in response to a trend — when the existing chain already delivers the value the trend names — would be the worst kind of catalog growth: more surface area, no new capability, mounting confusion as users wonder which spec author to pick. The skill-writing guidelines (`.claude/docs/skill-writing-guidelines.md` lines 16–29) explicitly warn against this.

The discoverability problem is real, though, and a single new reference doc fixes it cheaply. It also lets the maintainer respond to future "do you support SDD?" questions with a link instead of a discussion.

---

### 5. Implementation sketch

A single new reference doc that explains the positioning. Per the open-question decision below, the doc lives at the project root because it spans skills (brainstorm + jira + tdd), not just brainstorm.

**File:** `references/sdd-mapping.md` (project root, alongside `references/skill-handoff.md`).

**Contents (one-paragraph outline of each section):**

1. **What this doc is.** A one-paragraph framing: optimus is engineering-facing, and this doc maps the spec-driven development (SDD) vocabulary onto the existing optimus chain so users coming from Spec Kit, Kiro, or similar tools can recognize the equivalence.

2. **PRDs are out of scope, but PM content has a supported ingestion path.** A short, principled paragraph: optimus does not generate PRD content (personas, success metrics, KPIs, business-value framing). PRDs are PM artifacts; optimus is for engineers. **However, optimus does have a supported path for consuming PM-authored content: `/optimus:jira` is the canonical bridge.** It distills JIRA tickets (or any PM-authored issue body) into an engineering-focused task file (`docs/jira/<KEY>.md`) that downstream skills consume as spec input. If the user has a PRD authored externally, the path is: paste the relevant parts into a JIRA issue (or pass them as intent to `/optimus:brainstorm` directly). Optimus does not author PRDs; it consumes them through the jira firewall.

3. **The brainstorm design doc IS the SDD spec.** State the equivalence directly. The design doc's Goal + Context + Scenarios + Out of Scope correspond to what SDD calls "the spec." The Scenarios section is the acceptance criteria (`scenario-style.md` already calls this section "the specification").

4. **Phase mapping.** A table of Spec Kit's four phases (Specify, Plan, Tasks, Implement & Verify) against the existing optimus chain. Includes an optional **Ingest** row above Specify, mapped to `/optimus:jira`, for users starting from a JIRA ticket or other PM-authored content.

5. **When to use external specs.** Three paths: (a) start with `/optimus:jira` if the content lives in a JIRA issue, (b) hand the spec to `/optimus:brainstorm` directly, or (c) reference it from `/optimus:tdd` via the explicit-reference context cascade (`skills/tdd/SKILL.md` lines 52, 136).

6. **What this doc is not.** Not a SKILL.md, not loaded operationally by any skill, not a contract. Purely a positioning / discoverability doc.

#### Verification

- Read the new doc end to end after writing. Confirm:
  - PRDs explicitly named out of scope.
  - The "design doc IS the spec" claim is consistent with `scenario-style.md` line 52 and the existing brainstorm template.
  - The Spec Kit phase mapping matches the actual behavior of brainstorm and tdd (cross-check against `skills/brainstorm/SKILL.md` Step 4 and `skills/tdd/SKILL.md` lines 50–60, 136).
- Run the existing validation suite (`bash scripts/validate.sh && bash scripts/test-hooks.sh && python -m pytest test/...`) to confirm the new doc doesn't break any reference-link checker.
- No functional behavior changes; nothing to test in a running app.

---

### 6. Open questions

1. **Doc location:** decided — `references/sdd-mapping.md` at project root (topic spans skills).
2. **Pointers from skill READMEs:** open — adding a one-line link from `skills/brainstorm/README.md` and `skills/jira/README.md` would aid discoverability; not strictly required. Maintainer's call.
3. **Does `/optimus:jira`'s self-description need to name its bridging role?** Open — the skill's frontmatter describes what it does mechanically (fetch + distill + analyze) but does not name its architectural role as optimus's PM-to-engineering bridge. Out of this plan's scope; maintainer may want a follow-up sentence in `skills/jira/README.md`.
4. **Future trigger to revisit:** if a user *does* request a separate PRD or pure-spec artifact later, what threshold triggers a re-evaluation? Suggested: ≥3 distinct users asking for the same thing in a 60-day window, or a deliberate strategy change about optimus's target persona (e.g., expanding to PM-led teams). Below that, hold the line.

---

### Sources

- [Atlassian — Product requirements documentation](https://www.atlassian.com/agile/product-management/requirements)
- [Productboard — PRD vs Product Spec](https://www.productboard.com/glossary/prd-vs-product-spec/)
- [Thoughtworks — Spec-Driven Development: Unpacking 2025's New Engineering Practices](https://www.thoughtworks.com/en-us/insights/blog/agile-engineering-practices/spec-driven-development-unpacking-2025-new-engineering-practices)
- [GitHub Spec Kit (github/spec-kit)](https://github.com/github/spec-kit)
- [Augment Code — What is Spec-Driven Development?](https://www.augmentcode.com/guides/what-is-spec-driven-development)
- Optimus internals: `README.md`, `skills/brainstorm/SKILL.md`, `skills/brainstorm/references/design-doc-format.md`, `skills/brainstorm/references/scenario-style.md`, `skills/tdd/SKILL.md`, `references/skill-handoff.md`, `.claude/docs/skill-writing-guidelines.md`.

---

## Iteration — 2026-05-31

**Status:** Decided — scope extended (narrowly); ship `/optimus:spec-init` + cascade read-wiring.

### Trigger

The 2026-05-28 decision held the "no new skill" line because the driver was industry buzz, not concrete demand, and it set an explicit revisit threshold (open question #4): concrete repeated demand, or a deliberate change in optimus's target persona. That threshold is now met. A real, in-use project (the maintainer's own, docs-only with no code yet) adopts a docs-first SDD cascade — `docs/product/product-context.md` (vision) → `docs/product/mvp-prd.md` (PRD) → `docs/architecture/tech-stack.md` (target stack) → a buildable spec — authored before any code, and the maintainer asked optimus to support that flow.

### What changed, and what did NOT

The engineering-only **authoring** boundary from 2026-05-28 still holds in full: optimus authors no PM content (no personas, KPIs, or business-value prose) and writes nothing into `docs/specs/`. What changed is narrow: optimus now (a) **scaffolds empty, product-neutral skeletons** for the cascade — `TODO`-marked docs a human fills, exactly as a real docs-first project ships its `mvp-prd.md` as a skeleton — and (b) **reads** the filled cascade as higher-altitude steering in `brainstorm` and `tdd`. Scaffolding empty skeletons is not authoring PM content.

### Mechanism (chosen): A — dedicated lean skill + additive reads

- **`/optimus:spec-init`** — a new lean skill (one `SKILL.md` + one template reference + `README.md`; no agents, no hooks) scaffolds the three steering docs non-destructively and hands off to `/optimus:brainstorm`.
- **`brainstorm` / `tdd`** — additive, load-if-present steering reads. The `docs/design/` output, `docs/jira/` detection, the tdd context cascade, and the scenario/TDD-summary contracts are unchanged when the cascade is absent.
- **`references/sdd-mapping.md`** — promoted from framing doc to the shared contract: the single canonical altitude order, the `docs/design/` (optimus-authored) vs `docs/specs/` (human-authored) spec-location rule, and the architecture-name disambiguation.

**Invariant (hard boundary):** optimus AUTHORS only the engineering spec (`docs/design/`, via brainstorm) and READS product-context / mvp-prd / tech-stack as steering. It scaffolds EMPTY steering skeletons and authors NOTHING into `docs/specs/`. This narrow extension is **not** license to author PM content (personas, KPIs, business-value).

### Why not the alternatives

- **Extend `/optimus:init`** — rejected: init owns `.claude/` agent-conventions; folding root-`docs/` product planning in mixes concerns and forces both "architecture" artifacts (`.claude/docs/architecture.md` and `docs/architecture/tech-stack.md`) into one code path.
- **Extend `/optimus:brainstorm`** — rejected for the scaffold half: a once-per-project bootstrap inside a per-feature authoring skill is a cadence / single-responsibility mismatch (the read half is kept).
- **Do nothing** — rejected: the revisit threshold is met.

### Naming-collision resolution

`.claude/docs/architecture.md` (init-owned, post-code structure conventions) and `docs/architecture/tech-stack.md` (human-owned, pre-code target stack) are kept distinct by tree, basename, and lifecycle; they never meet in one code path. Keep the `tech-stack.md` basename — do not rename to `architecture.md`.

### Decision deltas vs. the 2026-05-28 record

- Options table row **D** ("No new skill; add SDD-mapping doc") remains shipped, but is now the *foundation* of the contract rather than the whole answer.
- Row **A' (`/optimus:spec` / spec authoring)** stays rejected — the buildable spec is still brainstorm's `docs/design/` doc; `spec-init` scaffolds *steering*, not the spec.
- New: a dedicated **scaffold-only** skill was previously unconsidered because no concrete demand existed; a real docs-first project now supplies it.

### Refinement — `docs/specs/` auto-discovery added (same branch)

After an independent reconsideration of the engineer-only decision (run without sight of this branch, it reached a leaner "consume-only, no scaffolder" conclusion), the maintainer chose to **keep `/optimus:spec-init` and graft one addition**: `/optimus:tdd` now **auto-discovers** a human-authored `docs/specs/` build spec, not only consumes it by explicit reference. A new context-cascade rung fires when no `docs/design/` or `docs/jira/` context resolves (precedence: design → jira → specs), offers the most recent spec via `AskUserQuestion`, and applies the `## Scenarios` shortcut if present. This **supersedes the "the tdd context cascade … unchanged" clause above.** The authoring boundary is untouched — optimus reads and now auto-detects `docs/specs/`, but still writes nothing there. Files updated: `skills/tdd/SKILL.md` (cascade rung + scenario-shortcut generalization + precedence note), `references/sdd-mapping.md` (spec-location and external-spec sections), `skills/tdd/README.md`.
