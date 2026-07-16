# Cascade templates

The product- and tool-neutral skeletons the greenfield route of `/optimus:spec`
emits. Each block below is written **verbatim** to its target path; a human
then fills the `TODO` markers. Write a file only when it does **not** already
exist — never overwrite a human-edited doc.

The templates carry no product names and no tool references; they cross-link
only to their sibling cascade docs, and each states the altitude/precedence
rule for the human reading their own repo: higher docs set long-term
direction, and the active build spec in `docs/specs/` wins when they conflict
about current work.

---

## Emit to `docs/product/product-context.md`

```markdown
# Product Context

> **Altitude & precedence.** Part of a docs-first cascade, in decreasing
> altitude: **product vision → MVP PRD → target tech-stack → active build
> spec**. Higher docs set long-term direction; the active build spec (in
> `docs/specs/`) governs what to build right now — when they conflict about
> current work, **the build spec wins.**
> Siblings: [MVP PRD](./mvp-prd.md) · [target tech-stack](./tech-stack.md).
>
> **This document** is the long-term product vision — the destination, not the
> next build.

## Big picture

> TODO — not yet decided. In one paragraph: what is the product, who is it
> for, and what does it let them do?

## Product vision

> TODO — not yet decided. The longer-term direction — what this becomes over
> time, and why it matters.

## Target users

> TODO — not yet decided. The primary users and what they care about. Note how
> technical they are.

## Core product principles

> TODO — not yet decided. The handful of principles every product decision
> should honor.

## What it is / what it is not

> TODO — not yet decided. Bullet what the product is, and — just as important —
> what it is not.

## North star

> TODO — not yet decided. One sentence: the single outcome everything built
> should support.

## Guidance for AI coding agents

> TODO — not yet decided. How an agent should treat this doc. Typically: this
> is vision, not current scope; build the smallest thing that validates the
> idea; when the vision and the active build spec conflict about what to build
> now, the spec wins.
```

---

## Emit to `docs/product/mvp-prd.md`

```markdown
# MVP — Product Requirements (PRD)

> **Altitude & precedence.** Part of a docs-first cascade, in decreasing
> altitude: **product vision → MVP PRD → target tech-stack → active build
> spec**. Higher docs set long-term direction; the active build spec (in
> `docs/specs/`) governs what to build right now — when they conflict about
> current work, **the build spec wins.**
> Siblings: [product vision](./product-context.md) · [target tech-stack](./tech-stack.md).
>
> **This document** is the first product slice (the MVP) — narrower than the
> vision, broader than any single build. Resolve a section by replacing its
> `TODO` with the decision and a short note on *why*.

## 1. Problem statement

> TODO — not yet decided. What exact problem does the MVP solve, and for which
> user first?

## 2. MVP scope

> TODO — not yet decided. The smallest slice that delivers and validates the
> core value.

## 3. Non-goals / out of scope

> TODO — not yet decided. What the MVP deliberately excludes (and defers to
> the vision).

## 4. Primary use cases

> TODO — not yet decided. The core things a user can do; mark the single
> "hero" use case to nail first.

## 5. Functional requirements

> TODO — not yet decided. What the system must *do*.

## 6. Non-functional / product requirements

> TODO — not yet decided. How the product must feel and behave, beyond
> features.

## 7. Success metrics

> TODO — not yet decided. How you will know the MVP is working — make each
> signal measurable.

## 8. Risks and open questions

> TODO — not yet decided.
```

---

## Emit to `docs/product/tech-stack.md`

```markdown
# Target Technology Stack

> **Altitude & precedence.** Part of a docs-first cascade, in decreasing
> altitude: **product vision → MVP PRD → target tech-stack → active build
> spec**. Higher docs set long-term direction; the active build spec (in
> `docs/specs/`) governs what to build right now — when they conflict about
> current work, **the build spec wins.**
> Siblings: [product vision](./product-context.md) · [MVP PRD](./mvp-prd.md).
>
> **This document** is the **target** stack the product grows toward — *not* a
> constraint on the current build, which uses only the small subset it needs.

## Core principles

> TODO — not yet decided. The few rules guiding technology choices (e.g.
> prefer popular, well-documented tools an AI agent can use reliably; keep the
> initial architecture simple).

## Selected stack

> TODO — not yet decided. Fill only the categories you need; leave the rest
> blank. For each, name the choice and one line on *why*.

- **Language:** TODO
- **Frontend:** TODO
- **Backend / API:** TODO
- **Data / persistence:** TODO
- **AI layer (if any):** TODO
- **Auth (if any):** TODO
- **Testing:** TODO
- **Observability:** TODO

## Architectural direction

> TODO — not yet decided. The shape of the system (e.g. modular monolith vs.
> separate services) and why.

## Adoption & phasing

> TODO — not yet decided. What to adopt now vs. add only when a real need
> appears.

## Notes for AI coding agents

> TODO — not yet decided. How an agent should use this doc. Typically: build
> to the current spec, not the full target; do not introduce major libraries
> without explaining why.
```
