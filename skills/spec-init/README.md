# optimus:spec-init

Scaffolds an empty, product-neutral **docs-first cascade** — a long-term product vision, an MVP PRD, and a target tech-stack — for a human to fill before any code is written. It then hands off to `/optimus:brainstorm`, which reads the cascade as steering and authors the engineering spec.

This is optimus's entry point for **spec-driven development (SDD)**: capture product direction as durable documents first, then build against them.

## What it creates

| File | Holds |
|---|---|
| `docs/product/product-context.md` | Long-term product vision — the destination. |
| `docs/product/mvp-prd.md` | The first product slice (MVP PRD). |
| `docs/product/tech-stack.md` | The target technologies the product grows toward. |

Every file is an empty skeleton with `TODO` markers. The skill is **non-destructive** — it never overwrites a file that already exists.

## When to use

Once per project, at bootstrap — most valuable on a greenfield, docs-first project. Safe to run on an existing project too (it only creates missing files). A common greenfield order is `/optimus:permissions` → `/optimus:init` → `/optimus:spec-init` → fill the cascade → `/optimus:brainstorm`.

## Boundary

This skill **authors no PM content.** It emits empty skeletons only — no personas, no KPIs, no business-value prose, no technology choices. Those are the human's to write. The buildable spec is **not** created here either: it is authored by `/optimus:brainstorm` or supplied by a human, in `docs/specs/`. optimus stays an engineering tool that *reads* the cascade as steering and *authors* only the engineering spec.

## Related concepts

- [`references/sdd-mapping.md`](../../references/sdd-mapping.md) — the shared contract: the canonical altitude/precedence order and the `docs/specs` spec-location rule. `brainstorm` and `tdd` read the cascade this skill scaffolds.
