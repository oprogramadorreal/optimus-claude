<!-- Keep this file, .claude/docs/, and subproject CLAUDE.md files updated when project structure changes -->

# [MONOREPO NAME]

[One-line description]. Monorepo with [N] packages.

## Architecture

| Subproject | Purpose | Stack |
|---------|---------|-------|
| `[path]` | [purpose] | [stack] |

## Commands

[Root-level / workspace-wide commands only: build all, test all, lint all]

## Subproject Docs

Each subproject has its own CLAUDE.md with subproject-specific guidance:
- `[path]/CLAUDE.md` - [one-line description]

## Documentation

Read the relevant doc before making changes:
- `.claude/docs/coding-guidelines.md` - For new features, refactoring, code structure
<!-- Only list docs that were actually created -->
<!-- If >6 subprojects: - `.claude/docs/architecture.md` - Full architecture map -->

## Agents

After implementing features or fixing bugs:
- `.claude/agents/code-simplifier.md` — simplifies recently changed code
<!-- Only list if test-guardian was installed:
- `.claude/agents/test-guardian.md` — flags missing test coverage
-->
