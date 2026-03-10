# Documentation Prerequisite Check

Shared prerequisite check referenced by multiple skills. Each consuming skill may extend this with additional skill-specific documents.

## Core Prerequisites

Check that these files exist:

- `.claude/CLAUDE.md` (or the target repo's `.claude/CLAUDE.md` in a multi-repo workspace)
- `.claude/docs/coding-guidelines.md` (or the target repo's)

## Fallback Behavior

**If either is missing**, warn the user and recommend running `/optimus:init` first. Use these fallbacks so the skill can still run:

- `CLAUDE.md` missing → detect tech stack from manifest files (`package.json`, `Cargo.toml`, `pyproject.toml`, etc.) for basic context
- `coding-guidelines.md` missing → read `$CLAUDE_PLUGIN_ROOT/skills/init/templates/docs/coding-guidelines.md` as a generic baseline; inform the user that findings are based on generic guidelines, not project-specific ones
- Both missing → apply both fallbacks, strongly recommend `/optimus:init`
