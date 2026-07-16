# Quality gate

Runs the quality-gate agents after TDD cycles complete. Running them here rather than per-cycle catches cross-cycle issues — duplication between behaviors, naming drift, accumulated pattern violations, coverage gaps — that are invisible within a single cycle.

## Scope

Collect the files changed during the session: `git diff --name-only <original-branch>...HEAD`, where `<original-branch>` is the branch the feature branch was created from. This is the scope for both agents.

## Launch

The code-simplifier agent always runs. The test-guardian agent runs only when test infrastructure docs exist (`.claude/docs/testing.md`, or the subproject's `docs/testing.md` in a monorepo). Launch every applicable agent as a `general-purpose` Agent tool call in a single message so they run in parallel.

The agent prompts are `code-simplifier.md` and `test-guardian.md` in this skill's `agents/` directory, each layered on `shared-constraints.md`. Compose each prompt per "Prompt assembly at dispatch time" in `$CLAUDE_PLUGIN_ROOT/references/agent-architecture.md`: substitute the resolved absolute plugin root for every `$CLAUDE_PLUGIN_ROOT` reference the prompt files carry, and inline or absolutize the bare `shared-constraints.md` reference — subagents inherit neither the variable nor this directory as their cwd.

## Act on findings

Present the consolidated findings to the user, then apply a fix for each one. When done, run the test suite:

- **All green** — commit the fixes with a conventional message.
- **Tests fail** — revert all the fixes, then re-apply them one at a time with a test run after each: keep the ones that pass, drop the ones that fail, and tell the user which were dropped and why. Commit the kept fixes.

If neither agent found anything, say so and move on to the wrap-up.
