# Cascade templates

The product- and tool-neutral skeletons that `/optimus:spec-init` emits. Each block below is written **verbatim** to its target path (a human then fills the `TODO` markers). The skill writes a file only when it does **not** already exist — it never overwrites a human-edited doc.

These templates are intentionally neutral: **no product names, no tool/command references.** They cross-link only to the user's own sibling cascade docs, and each carries a self-contained altitude/precedence note (the same order defined in `references/sdd-mapping.md`, restated here for the human reading their own repo).

## Contents

- [Emit to `docs/product/product-context.md`](#emit-to-docsproductproduct-contextmd)
- [Emit to `docs/product/mvp-prd.md`](#emit-to-docsproductmvp-prdmd)
- [Emit to `docs/architecture/tech-stack.md`](#emit-to-docsarchitecturetech-stackmd)

---

## Emit to `docs/product/product-context.md`

```markdown
# Product Context

> **Altitude & precedence.** This document is part of a docs-first cascade, in decreasing altitude:
> **product vision → MVP PRD → target tech-stack → active build spec**. Higher docs set long-term
> direction; the active build spec (in `docs/design/` or `docs/specs/`) governs what to build right
> now. When they conflict about current work, **the active build spec wins.**
> Siblings: [MVP PRD](./mvp-prd.md) · [target tech-stack](../architecture/tech-stack.md).
>
> **What this document is.** The long-term product vision — the destination, not the next build. For
> what to build now, follow the active build spec in `docs/design/` or `docs/specs/`; for the first
> product slice, see [mvp-prd.md](./mvp-prd.md).

## Big picture

> TODO — not yet decided. In one paragraph: what is the product, who is it for, and what does it let
> them do?

## Product vision

> TODO — not yet decided. The longer-term direction — what this becomes over time, and why it matters.

## Target users

> TODO — not yet decided. The primary users and what they care about. Note how technical they are.

## Core product principles

> TODO — not yet decided. The handful of principles every product decision should honor.

## What it is / what it is not

> TODO — not yet decided. Bullet what the product is, and — just as important — what it is not.

## North star

> TODO — not yet decided. One sentence: the single outcome everything built should support.

## Guidance for AI coding agents

> TODO — not yet decided. How an agent should treat this doc. Typically: this is vision, not current
> scope; build the smallest thing that validates the idea; when the vision and the active build spec
> conflict about what to build now, the spec wins.
```

---

## Emit to `docs/product/mvp-prd.md`

```markdown
# MVP — Product Requirements (PRD)

> **Altitude & precedence.** This document is part of a docs-first cascade, in decreasing altitude:
> **product vision → MVP PRD → target tech-stack → active build spec**. Higher docs set long-term
> direction; the active build spec (in `docs/design/` or `docs/specs/`) governs what to build right
> now. When they conflict about current work, **the active build spec wins.**
> Siblings: [product vision](./product-context.md) · [target tech-stack](../architecture/tech-stack.md).
>
> **What this document is.** The first product slice (the MVP) — narrower than the
> [product vision](./product-context.md), broader than any single build. What to build *right now* is
> the smaller active build spec in `docs/design/` or `docs/specs/`.
>
> **How to use it.** Each section holds a guiding question. Resolve a section by replacing its `TODO`
> with the decision and a short note on *why*.

## 1. Problem statement

> TODO — not yet decided. What exact problem does the MVP solve, and for which user first?

## 2. MVP scope

> TODO — not yet decided. The smallest slice that delivers and validates the core value.

## 3. Non-goals / out of scope

> TODO — not yet decided. What the MVP deliberately excludes (and defers to the vision).

## 4. Primary use cases

> TODO — not yet decided. The core things a user can do; mark the single "hero" use case to nail first.

## 5. Functional requirements

> TODO — not yet decided. What the system must *do*.

## 6. Non-functional / product requirements

> TODO — not yet decided. How the product must feel and behave, beyond features.

## 7. Success metrics

> TODO — not yet decided. How you will know the MVP is working — make each signal measurable.

## 8. Risks and open questions

> TODO — not yet decided.
```

---

## Emit to `docs/architecture/tech-stack.md`

```markdown
# Target Technology Stack

> **Altitude & precedence.** This document is part of a docs-first cascade, in decreasing altitude:
> **product vision → MVP PRD → target tech-stack → active build spec**. Higher docs set long-term
> direction; the active build spec (in `docs/design/` or `docs/specs/`) governs what to build right
> now. When they conflict about current work, **the active build spec wins.**
> Siblings: [product vision](../product/product-context.md) · [MVP PRD](../product/mvp-prd.md).
>
> **What this document is.** The **target** stack the product grows toward — *not* a constraint on the
> current build. The active build spec uses only the small subset it needs. This is forward-looking
> product/architecture *planning*; it is distinct from any post-code structure notes your engineering
> setup keeps about the code as it actually exists.

## Core principles

> TODO — not yet decided. The few rules guiding technology choices (e.g. prefer popular,
> well-documented tools an AI agent can use reliably; keep the initial architecture simple).

## Selected stack

> TODO — not yet decided. Fill only the categories you need; leave the rest blank. For each, name the
> choice and one line on *why*.

- **Language:** TODO
- **Frontend:** TODO
- **Backend / API:** TODO
- **Data / persistence:** TODO
- **AI layer (if any):** TODO
- **Auth (if any):** TODO
- **Testing:** TODO
- **Observability:** TODO

## Architectural direction

> TODO — not yet decided. The shape of the system (e.g. modular monolith vs. separate services) and why.

## Adoption & phasing

> TODO — not yet decided. What to adopt now vs. add only when a real need appears.

## Notes for AI coding agents

> TODO — not yet decided. How an agent should use this doc. Typically: build to the current spec, not
> the full target; do not introduce major libraries without explaining why.
```
