# Shared constraints — TDD quality gate

Read `$CLAUDE_PLUGIN_ROOT/references/shared-agent-constraints.md` for the base constraints (read-only rules, quality bar, exclusions, false positives).

Additional rules for this gate:

- At most 5 findings per agent.
- Scope strictly to the changed files provided in the prompt; do not suggest changes outside them.
- Do not flag style/formatting, bugs, or security — this gate is about simplification and test quality only.
