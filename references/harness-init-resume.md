# Harness CLI — Initialize or Resume a Run

Shared `harness_common.cli` init/resume semantics for the three `*-deep` orchestrator skills. Each consuming SKILL.md (Step 4) supplies these parameters:

- `<progress-path>` — the skill's progress file (e.g. `.claude/code-review-deep-progress.json`)
- `<cap-flag>` — `--max-iterations` (code-review-deep, refactor-deep) or `--max-cycles` (unit-test-deep)

Per-skill deltas stay inline in each SKILL.md: the `init` invocation itself (its `--skill`, cap, `--focus`, and `--scope` flags differ) and the baseline `--allow-red` policy. Wherever the commands below write `$CLAUDE_PLUGIN_ROOT`, use the plugin root the skill resolved in its Step 2 — substitute the absolute path literally if the env var read empty.

## On `--resume`

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli resume \
    --progress-file "<progress-path>" \
    [<cap-flag> N] \
    --project-dir "."
```

If exit code is non-zero, surface the error and stop. Pass `<cap-flag> N` through whenever the user supplied it on `--resume` — the CLI clamps it to the hard cap and, when the prior run ended at its cap, refuses a value at or below the completed count. `resume` persists the new cap (and clears a prior `diminishing-returns` stop) so the loop can continue past the previous limit.

`--resume` only continues a run whose progress file is still on disk: an interrupt, or a `diminishing-returns` soft-exit (the CLI leaves that run un-archived). A run that finished cleanly was archived to `.done.json`, which `resume` refuses — for a fresh pass after that, re-run the skill without `--resume` so `init` starts a new run.

## On fresh run

Run the skill's `init` invocation from its SKILL.md. Pass `--no-commit` through to `init` when the user supplied it — the mode is persisted in the progress file, so `--resume` keeps it without re-passing the flag (and `commit-checkpoint` self-skips regardless).

If exit code is non-zero, surface the error and stop. Likely errors:

- *"progress file already exists"* — a prior run has not been archived. Tell the user to either pass `--resume` to continue the prior run, or re-invoke the CLI `init` subcommand with `--force` to discard the prior progress and start fresh. `--force` is a flag of `cli.py init`, not of the skill — no user-visible orchestrator flag exists or is needed. Note that `resume` never re-runs the baseline: if the prior run stopped at its baseline or never completed an iteration, apply the skill's baseline step's `--resume` rule before entering the loop.
- *"No test command"* — `.claude/CLAUDE.md` does not document a test command and `--test-command` was not supplied. Recommend `/optimus:init`.
- *"Working tree has uncommitted changes"* — the CLI re-enforces the Step 2 clean-tree check (it also protects direct CLI callers). Commit or stash first, or run with `--no-commit`.
- *"Cannot determine HEAD commit"* — the project is not a git repository or has no commits.
