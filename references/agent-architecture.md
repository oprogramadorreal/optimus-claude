# Agent Architecture

optimus-claude uses a two-tier agent design:

- **Plugin-level agents** (`agents/`): `code-simplifier.md` and `test-guardian.md` —
  reusable quality concerns with standard Claude Code agent frontmatter. They serve
  as base definitions that skill-level agents extend.
- **Skill-level agents** (`skills/<name>/agents/`): agent prompts scoped to one
  skill's workflow, launched explicitly by that skill via the Agent tool. Each
  directory typically holds one `.md` file per agent plus `shared-constraints.md`
  (skill-specific addendums to `references/shared-agent-constraints.md`) and
  optionally `context-blocks.md` (conditional context injection templates).

**The specialization pattern:** a skill-level agent extends a plugin-level one by
telling the subagent to read the plugin-level file (`agents/code-simplifier.md` or
`agents/test-guardian.md`, resolved from the plugin root) for its approach and
quality criteria, then layering skill-specific scope, output format, and exclusions
on top.
The dispatching prompt's constraints override the base file's operational sections;
only quality criteria and focus areas carry over.

## Prompt assembly at dispatch time

Skill-level agents run as `general-purpose` subagents, and a subagent inherits
neither the `$CLAUDE_PLUGIN_ROOT` variable nor the agent directory as its working
directory — unresolved paths in its prompt cannot be read. Whoever dispatches a
fan-out agent (a SKILL.md step, or a deep-mode iteration executing it) must, when
composing each agent prompt from these files:

- substitute the resolved absolute plugin root for every `$CLAUDE_PLUGIN_ROOT`
  reference the prompt carries, and
- inline the content of bare relative references such as `shared-constraints.md`, or
  rewrite them as absolute paths (they would otherwise resolve against the user
  project's cwd).
