# Constraint Document Loading

Load project constraint documents that define the rules for analysis and code generation. Each consuming skill adds its own framing for how these docs are used (e.g., "review criteria", "simplification rules").

## Single Project

1. `.claude/CLAUDE.md` — project overview, conventions, tech stack, test commands
2. `.claude/docs/coding-guidelines.md` — coding standards (primary evaluation criteria for code files)
3. `.claude/docs/skill-writing-guidelines.md` (if exists) — skill-writing standards, the evaluation criteria for markdown instruction files
4. `.claude/docs/testing.md` (if exists) — testing conventions, so analysis respects test patterns and established test helpers
5. `.claude/docs/architecture.md` (if exists) — architectural boundaries, so changes respect module structure and intended separation of concerns
6. `.claude/docs/styling.md` (if exists) — UI/CSS conventions, so frontend work stays consistent

## Monorepo

`/optimus:init` places docs differently in monorepos — `coding-guidelines.md` and `skill-writing-guidelines.md` are shared at root, but `testing.md`, `styling.md`, and `architecture.md` are scoped per subproject:

1. `.claude/CLAUDE.md` — root overview, subproject table, workspace-level commands
2. `.claude/docs/coding-guidelines.md` — shared coding standards (applies to code files in ALL subprojects)
3. `.claude/docs/skill-writing-guidelines.md` (if exists) — shared skill-writing standards, applying to markdown instruction files in every subproject
4. For each subproject in scope:
   - `<subproject>/CLAUDE.md` — subproject-specific overview, commands, tech stack
   - `<subproject>/docs/testing.md` (if exists) — subproject-specific testing conventions
   - `<subproject>/docs/architecture.md` (if exists) — subproject-specific architecture
   - `<subproject>/docs/styling.md` (if exists) — subproject-specific UI/CSS conventions
5. For root-as-project: its scoped docs are in `.claude/docs/` alongside the shared guidelines

## Skill authoring lens

The presence of `.claude/docs/skill-writing-guidelines.md` means the project authors markdown instructions for an AI agent, and those files are judged by that doc rather than by `coding-guidelines.md`. The routing rule itself is stated once, in `$CLAUDE_PLUGIN_ROOT/references/shared-agent-constraints.md` under **Dual Lens** — apply it there. A change touching both kinds of file gets both lenses, each on its own files. When the doc does not exist, the lens does not apply.

## Monorepo Scoping Rule

When operating on a subproject's code, apply its own constraint docs — not another subproject's. `coding-guidelines.md` and `skill-writing-guidelines.md` are shared at root (`.claude/docs/`) and apply everywhere; `testing.md`, `styling.md`, and `architecture.md` are per subproject (`<subproject>/docs/<doc>.md`), so backend conventions never govern frontend code or vice versa. For root-as-project, its scoped docs sit in `.claude/docs/` alongside the shared guidelines.

## Submodule Exclusion

Exclude confirmed git submodule directories from analysis of their parent project: `git -C "<directory>" rev-parse --show-superproject-working-tree` identifies the superproject, or the parent's `.gitmodules` registers that path. A `.git` file alone is insufficient — linked worktrees also use it. Analyze an explicitly targeted submodule in its own repository context.
