# Quality Gate

Runs project-level quality agents after all TDD cycles complete. Running agents here — not per-cycle — catches cross-cycle issues (duplication between behaviors, naming drift, accumulated pattern violations, edge-case coverage gaps) that are invisible within a single cycle.

## Pre-flight

Check whether these project-level agent files exist:
- `.claude/agents/code-simplifier.md`
- `.claude/agents/test-guardian.md`

Record which are available — they will be used in the Quality Gate step after cycling completes. If neither exists, the quality gate will be skipped. This is not a blocker; recommend `/optimus:init` if missing and the user wants agent-backed quality checks.

## Execution

### Gather changed files

Collect all files changed during the TDD session: `git diff --name-only <original-branch>...HEAD` (where `<original-branch>` is provided by the caller). This is the scope for both agents.

### Launch parallel agents

Launch up to 2 `general-purpose` Agent tool calls simultaneously — one per available agent. Only launch agents whose definition files exist (checked in Pre-flight above).

Read `$CLAUDE_PLUGIN_ROOT/skills/tdd/references/agent-prompts.md` for the full prompt templates for both agents.

### Present findings

After both agents complete, present a consolidated quality report:

```
## Quality Gate

### Code Simplifier
[Findings from code-simplifier, or "No issues found — code follows project guidelines."]

### Test Guardian
[Findings from test-guardian, or "All code has test coverage. No structural barriers detected."]
```

If no agents produced findings, report "Quality gate passed — no issues found" and proceed silently to Step 9.

### Act on findings

If either agent produced findings, apply fixes for each one. After all fixes are applied, run the test suite:

- **All tests pass** — stage and commit with a conventional message (e.g., `refactor(scope): address quality gate findings`). Proceed to Step 9.
- **Tests fail** — revert all fixes, then re-apply one at a time with a test run after each. Keep fixes that pass, revert those that fail. Present a fix summary listing which fixes were applied and which were reverted (with reason "fix broke tests"). Stage and commit kept fixes with a conventional message (e.g., `refactor(scope): address quality gate findings`). Proceed to Step 9.
