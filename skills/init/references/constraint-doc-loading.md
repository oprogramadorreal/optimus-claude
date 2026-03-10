# Constraint Document Loading

Load project constraint documents that define the rules for analysis and code generation. Each consuming skill adds its own framing for how these docs are used (e.g., "review criteria", "simplification rules").

## Single Project

1. `.claude/CLAUDE.md` — project overview, conventions, tech stack, test commands
2. `.claude/docs/coding-guidelines.md` — coding standards (primary evaluation criteria)
3. `.claude/docs/testing.md` (if exists) — testing conventions, so analysis respects test patterns and established test helpers
4. `.claude/docs/architecture.md` (if exists) — architectural boundaries, so changes respect module structure and intended separation of concerns
5. `.claude/docs/styling.md` (if exists) — UI/CSS conventions, so frontend work stays consistent

## Monorepo

`/optimus:init` places docs differently in monorepos — `coding-guidelines.md` is shared at root, but `testing.md`, `styling.md`, and `architecture.md` are scoped per subproject:

1. `.claude/CLAUDE.md` — root overview, subproject table, workspace-level commands
2. `.claude/docs/coding-guidelines.md` — shared coding standards (applies to ALL subprojects)
3. For each subproject in scope:
   - `<subproject>/CLAUDE.md` — subproject-specific overview, commands, tech stack
   - `<subproject>/docs/testing.md` (if exists) — subproject-specific testing conventions
   - `<subproject>/docs/architecture.md` (if exists) — subproject-specific architecture
   - `<subproject>/docs/styling.md` (if exists) — subproject-specific UI/CSS conventions
4. For root-as-project: its scoped docs are in `.claude/docs/` alongside the shared `coding-guidelines.md`

## Monorepo Scoping Rule

When operating on a subproject's code, apply its own constraint docs — not another subproject's. The shared `coding-guidelines.md` applies everywhere, but `testing.md`, `styling.md`, and `architecture.md` are subproject-scoped — don't apply backend conventions to frontend code or vice versa.

**Compact form for skills that load only a subset of docs:** `coding-guidelines.md` is shared at root (`.claude/docs/coding-guidelines.md`). Scoped docs (`testing.md`, `styling.md`, `architecture.md`) are per subproject (`<subproject>/docs/<doc>.md`). For root-as-project, scoped docs are in `.claude/docs/` alongside the shared guidelines.

## Submodule Exclusion

Exclude git submodule directories from analysis. A directory is a git submodule if it contains a `.git` *file* (not a `.git` directory). Files inside submodules belong to an external repository and should be analyzed in that repository's context, not the parent project's.
