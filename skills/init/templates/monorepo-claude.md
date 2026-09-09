<!-- Keep this file, .claude/docs/, and subproject CLAUDE.md files updated when project structure changes -->

# [MONOREPO NAME]

[One-line description]. Monorepo with [N] packages.

## Architecture

| Subproject | Purpose | Stack |
|---------|---------|-------|
| `[path]` | [purpose] | [stack] |

Read the applicable subproject CLAUDE.md before working there. Claude Code discovers these files natively; Codex follows the root AGENTS.md pointer and reads them explicitly.

## Commands

[Root-level / workspace-wide commands only: build all, test all, lint all]

## Documentation

Read the doc that matches the change — not all of them.

| Changing | Read first |
|---|---|
| Code | `.claude/docs/coding-guidelines.md` |

<!-- init adds one row per shared doc it actually created. When skill authoring was detected, it also adds:
| A skill, agent, prompt, or command (markdown instruction files) | `.claude/docs/skill-writing-guidelines.md` |
If >6 subprojects: | The subproject map | `.claude/docs/architecture.md` | -->

## Gotchas

[At most 5 bullets — a ceiling, not a target. Workspace-level only: cross-package invariants, a
build that must run from the root, a package that is generated, a version pinned across packages
for a reason, a task that silently skips packages. Subproject-specific gotchas belong in that
subproject's CLAUDE.md. Skip anything the workspace manifest or a directory listing would reveal.
Write none and delete this section rather than filler.]
