# Agent Architecture

## Prompt assembly at dispatch time

Skill-level agents run as `general-purpose` subagents. A subagent inherits neither the `$CLAUDE_PLUGIN_ROOT` variable nor the agents directory as its working directory — unresolved paths in its prompt cannot be read. Whoever dispatches a fan-out agent (a SKILL.md step, or a deep-mode iteration executing it) must, when composing each agent prompt:

- substitute the resolved absolute plugin root for every `$CLAUDE_PLUGIN_ROOT` reference the prompt carries, and
- inline the content of bare relative references such as `shared-constraints.md`, or rewrite them as absolute paths (they would otherwise resolve against the user project's cwd).
