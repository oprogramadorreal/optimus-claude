# Harness CLI — Initialize or Resume a Run

Shared `harness_common.cli` init/resume semantics for the `/optimus:deep` orchestrator skill. Its SKILL.md (Step 4) supplies these parameters per target:

- `<progress-path>` — the target's progress file (e.g. `.claude/code-review-deep-progress.json`)
- `<cap-flag>` — `--max-iterations` (review, refactor targets) or `--max-cycles` (coverage target)

Per-target deltas stay inline in the deep SKILL.md: the `init` invocation itself (its `--skill`, cap, `--focus`, and `--scope` flags differ) and the baseline `--allow-red` policy. Wherever the commands below write `$CLAUDE_PLUGIN_ROOT`, use the plugin root the skill resolved in its Step 2.

## On `--resume`

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli resume \
    --progress-file "<progress-path>" \
    [<cap-flag> N] \
    --project-dir "."
```

If exit code is non-zero, surface the error and stop. Pass `<cap-flag> N` through whenever the user supplied it on `--resume` — the CLI clamps it to the hard cap and, when the prior run ended at its cap, refuses a value at or below the completed count. `resume` persists the new cap (and clears a prior soft-exit stop) so the loop can continue past the previous limit.

`--resume` only continues a run whose progress file is still on disk: an interrupt, or one of the two soft exits the CLI leaves un-archived — `diminishing-returns`, and `blocked` (coverage target only, once you have cleared the prerequisite that stopped it). A run that finished cleanly was archived to `.done.json`, which `resume` refuses — for a fresh pass after that, re-run the skill without `--resume` so `init` starts a new run.

## On fresh run

Run the skill's `init` invocation from its SKILL.md. Pass `--no-commit` through to `init` when the user supplied it — the mode is persisted in the progress file, so `--resume` keeps it without re-passing the flag (and `commit-checkpoint` self-skips regardless).

If exit code is non-zero, surface the error and stop. Likely errors:

- *"progress file already exists"* — a prior run has not been archived. Tell the user to either pass `--resume` to continue the prior run, or re-invoke the CLI `init` subcommand with `--force` to discard the prior progress and start fresh. `--force` is a flag of `cli.py init`, not of the skill — no user-visible orchestrator flag exists or is needed. Note that `resume` never re-runs the baseline: if the prior run stopped at its baseline, never completed an iteration, or recorded `_safety_error`, apply the skill's baseline step's `--resume` rule before entering the loop.
- *"No test command"* — `.claude/CLAUDE.md` does not document a test command and `--test-command` was not supplied. Recommend `/optimus:init`.
- *"Working tree has uncommitted changes"* — the CLI re-enforces the Step 2 clean-tree check (it also protects direct CLI callers). Commit or stash first, or run with `--no-commit`.
- *"Cannot determine HEAD commit"* — the project is not a git repository or has no commits.

Dirty nested repositories (including submodules) must be handled inside their own repository, even with `--no-commit`; a parent snapshot cannot preserve those edits. Child assume-unchanged or skip-worktree index flags also block the run, even on currently clean files, because they can hide edits; resolve them in that repository first. A recovery error naming a changed child checkout requires restoring that child's recorded commit separately before retrying. Preserve the files and progress on these errors.

The CLI records exact regular files first created by tests as test outputs, including during failed runs and bisection. It excludes those paths from later input comparisons and checkpoints, persisting them across resume. Do not manually classify pre-existing files as outputs; use the project's ignore rules for existing disposable reports before starting. If generated source belongs in the change, deliberately stage it and validate again; staging revokes its output exclusion.
