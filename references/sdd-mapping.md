# Spec-driven development contract

The single canonical statement of how optimus's steering docs relate. Skills reference this file; they never restate it (the scaffolded doc headers are the one sanctioned copy — they ship into user repos that cannot read this file).

## Precedence

> **product vision → MVP PRD → target tech-stack → active build spec**

Higher docs (`docs/product/product-context.md`, `docs/product/mvp-prd.md`, `docs/product/tech-stack.md`) set long-term direction; the **active build spec** governs what to build right now. When they conflict about current work, the active build spec wins.

## Spec location and discovery

The active build spec lives in `docs/specs/` — written by `/optimus:brainstorm` (`docs/specs/<YYYY-MM-DD-slug>.md`) or dropped in from outside. Implement skills auto-discover the most recent file there (filename date prefix, else modification time). Discovery precedence, first match wins: `docs/specs/` build spec → `docs/jira/` context → none.

## Authoring boundary

optimus is an engineering tool: it scaffolds empty steering skeletons and reads them as context, but never authors PM content (personas, KPIs, business-value prose). PM-authored content enters via `/optimus:jira`, which distills an issue into an engineering shape at `docs/jira/<KEY>.md`. optimus authors only the engineering build spec (via `brainstorm`), never the product steering above it.
