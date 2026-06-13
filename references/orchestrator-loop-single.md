# Orchestrator Loop — Single Skill (Deep Variant)

## Contents
1. [Per-iteration body](#per-iteration-body) — steps 1–8
2. [Loop control invariants](#loop-control-invariants)
3. [Parse-failure recovery](#parse-failure-recovery)
4. [After the loop](#after-the-loop)

Shared iteration template for `/optimus:code-review-deep` and `/optimus:refactor-deep`. Each orchestrator skill dispatches its base skill into a fresh subagent context per iteration, parses the structured JSON the base skill emits, and uses the harness CLI to manage state, test/bisect, and decide termination.

The orchestrator never holds findings or fixes in conversation prose. All state lives in the progress file. Each Bash invocation of the CLI is a discrete operation; the orchestrator skill reads the CLI's stdout to make decisions.

**Plugin root.** Every command below writes `$CLAUDE_PLUGIN_ROOT` to mean the plugin root the orchestrator skill resolved in its Step 2. Bash-tool environment variables do **not** persist across separate Bash calls and may read empty on some platforms (notably Windows); if `echo $CLAUDE_PLUGIN_ROOT` was empty there, substitute the resolved absolute path **literally** into every `PYTHONPATH=...` command and into every dispatch prompt in this file.

## Per-iteration body

The orchestrator skill repeats steps 1–8 below until step 7 (`check-termination`) returns anything other than `continue`. Steps 1–6 and 8 mutate the progress file on disk; step 7 reads it.

### 1. Snapshot pre-iteration git state

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli snapshot --progress-file "<progress-path>"
```

Records `HEAD` into `progress["_snapshot"]["pre_head"]` and stamps the current iteration into `progress["_snapshot"]["iteration_token"]` (step 5 errors out if a stale token reveals a skipped snapshot). In no-commit mode — the run was started `--no-commit`, or a prior commit failed — `snapshot` also captures a working-tree stash automatically, so the iteration stays restorable; you do **not** need to pass `--include-stash` (it remains an explicit override).

### 2. Dispatch the base skill into a fresh subagent

Use the `Agent` tool. The prompt **must** include the inline sentinel, the absolute progress-file path, the iteration counter, and instructions to read the base SKILL.md from disk:

```
Agent tool call:
  subagent_type: general-purpose
  description: "<base-skill> iteration <N>"
  prompt: |
    HARNESS_MODE_INLINE
    Plugin root: <absolute-plugin-root>
    Progress file: <absolute-progress-path>
    Iteration: <N> of <max>
    Phase: <skill>

    Read the base SKILL.md at
    `<absolute-plugin-root>/skills/<base-skill>/SKILL.md` and execute its
    harness-mode protocol from
    `<absolute-plugin-root>/references/harness-mode.md` exactly. Wherever the
    base SKILL.md or harness-mode.md reference `$CLAUDE_PLUGIN_ROOT`, substitute
    the absolute plugin root above — your environment may not export it:
    - Read the progress file above for accumulated findings and scope.
    - Run the analysis cycle once.
    - Apply fixes. Do NOT run the test command, any `scripts/*.sh`, or any
      lint/build — the orchestrator owns all test execution and bisection.
    - Emit a single ```json:harness-output fenced block and stop.
    - Do not use AskUserQuestion. Do not loop.
```

Where `<base-skill>` is `code-review` or `refactor`, and `<absolute-plugin-root>` is the root resolved in Step 2 (the subagent does not inherit `$CLAUDE_PLUGIN_ROOT`, so it must be passed as an absolute path). The subagent inherits the working tree and applies edits via `Edit`/`MultiEdit`; on return, the working tree carries the iteration's changes and the subagent's final message contains the structured JSON.

### 3. Save the subagent return to a temp file

Write the subagent's final message text to a temp file (the orchestrator's parent context should not hold the raw subagent output verbatim). A repo-local temp path is fine:

```bash
TMP_RAW=".claude/.deep-iteration-raw.txt"
TMP_RESULT=".claude/.deep-iteration-result.json"
```

These exact filename prefixes (`.deep-iteration-` and `.unit-test-deep-`) are required. The checkpoint commit's authoritative protection is the un-stage step in `commit_checkpoint` (`scripts/harness_common/git.py`), which resets `_HARNESS_STATE_EXCLUDES` back out of the index after `git add -A` — it does **not** rely on the user project's `.gitignore` carrying these patterns (`/optimus:init` does not provision them). This repo's own `.gitignore` mirrors the patterns as a convenience for harness development; renaming a prefix therefore requires synchronized updates to `_HARNESS_STATE_EXCLUDES` (authoritative) and this repo's `.gitignore` (the dev mirror).

### 4. Extract the structured JSON

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli parse \
    --input-file "$TMP_RAW" \
    --output-file "$TMP_RESULT" \
    --progress-file "<progress-path>"
```

Errors on missing `json:harness-output` block. Passing `--progress-file` lets the CLI track consecutive parse failures across iterations (and across `--resume`); a single failure is a no-op — the CLI also rolls the failed dispatch's partial edits back to the iteration snapshot so nothing half-done is left for a later checkpoint to commit — and the loop moves on, while two consecutive failures cause step 7 to return `parse-failure` and terminate the loop. See "Parse-failure recovery" below.

### 5. Process the iteration

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli deep-step \
    --progress-file "<progress-path>" \
    --result-file "$TMP_RESULT"
```

This single subcommand: promotes actionable fixes, registers findings, runs tests, bisects on failure, updates per-finding statuses, appends iteration history, widens scope, and writes the result. Its stdout is one of:

| Output | Meaning |
|---|---|
| `converged` | Skill reported `no_new_findings` — loop terminates. |
| `no-actionable` | Skill reported `no_actionable_fixes` — loop terminates. |
| `all-reverted` | Every fix in this iteration was reverted — loop terminates. |
| `applied fixed=<N> reverted=<N> test_passed=<0\|1\|->` | Iteration completed normally — continue. `test_passed` is `-` when the iteration applied no fixes (so no test ran). |

### 6. Checkpoint commit

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli commit-checkpoint --progress-file "<progress-path>"
```

Returns `committed`, `nothing-to-commit`, `commit-skipped`, or `commit-failed`. Call it every iteration — the CLI owns the decision: in no-commit mode it self-skips and prints `commit-skipped`. On `commit-failed`, the CLI durably disables commits for the rest of the run (persisted, so it survives `--resume`): later snapshots auto-stash and later checkpoints self-skip, keeping the accumulated uncommitted work restorable. Warn the user once that checkpoint commits have stopped.

### 7. Check termination

```bash
TERMINATION=$(PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli check-termination \
    --progress-file "<progress-path>")
```

Possible values: `continue`, `convergence`, `no-actionable`, `all-reverted`, `cap`, `diminishing-returns`, `parse-failure`. If the value is anything other than `continue`, exit the loop. (`parse-failure` is surfaced automatically when the CLI's `parse_failure_count` reaches its threshold — the orchestrator doesn't need to call `mark-termination` for it.)

### 8. Advance the iteration counter

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli advance --progress-file "<progress-path>"
```

Increments `iteration.current`. Then loop back to step 1.

## Loop control invariants

- **Snapshot before dispatch.** The CLI's `deep-step` needs a fresh `pre_head` to recover from test failures, and verifies the snapshot's `iteration_token` matches the current iteration — a skipped snapshot makes `deep-step` exit non-zero rather than restore to a stale commit.
- **Always write progress before dispatching.** Cancellation between dispatches is recoverable via `--resume`; cancellation mid-dispatch may leave the working tree inconsistent but the progress file remains valid as of the prior iteration.
- **Slice-only progress reads.** Do not read the full progress file's `findings` array between iterations in the orchestrator's own context. The CLI's `check-termination` returns a single word; trust it.
- **Subagent output is text, not state.** Treat each subagent's return as a one-time payload. Save it to a temp file, parse it, then forget it. Do not keep the raw output in the orchestrator's conversation.
- **Re-entry guard.** If the orchestrator's own invocation prompt body already contains `HARNESS_MODE_INLINE`, stop with `"Deep mode cannot run inside deep mode"`. This prevents a misbehaving subagent from triggering recursion.
- **Don't end a turn on a promise.** Mid-loop, if the next step is a tool call, issue it — never end a turn with a bare "I'll run X next" or a plan. End only at termination or when blocked on input only the user can provide.
- **Report only what the CLI confirmed.** Per-iteration status comes from `deep-step` / `check-termination` stdout — don't assert results the CLI did not return, and if a step was skipped or a count is unverified, say so.

## Parse-failure recovery

If the CLI's `parse` subcommand exits non-zero, the subagent emitted no `json:harness-output` block. Common causes:
- The subagent hit its tool budget or token limit and stopped mid-response.
- The base SKILL.md does not detect `HARNESS_MODE_INLINE` in the prompt body (regression — see `references/harness-mode.md`).
- The subagent fell into interactive mode and hung on `AskUserQuestion`.

When this happens once: warn the user but continue (the iteration is a no-op, the loop moves on — the CLI's `parse_failure_count` is now 1). When this happens twice in a row: `check-termination` at step 7 will return `parse-failure` automatically, and the orchestrator should exit the loop and surface the error for the user to investigate.

The counter lives in the progress file under `parse_failure_count` and is reset to 0 on every successful parse, so an isolated earlier failure cannot poison a later run. The counter also survives `--resume`, so a Ctrl-C between the failed parse and the next iteration's parse doesn't lose state.

If for some reason the orchestrator needs to record `parse-failure` explicitly (e.g., the parse subcommand wasn't called with `--progress-file`), use:

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli mark-termination \
    --progress-file "<progress-path>" \
    --reason parse-failure \
    --message "<short detail, e.g. 'two consecutive iterations produced no json:harness-output block'>"
```

This is an escape hatch — the standard recovery path is the automatic `check-termination` route above.

## After the loop

Print the final report:

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli final-report --progress-file "<progress-path>" --archive
```

The `--archive` flag moves the progress file to `<path>.done.json` and removes the backup, signaling that this run is complete (a subsequent `--resume` will refuse the archived path) — **except** when the run ended in `diminishing-returns`, a resumable soft-exit: the CLI then leaves the active progress file in place (prints `not-archived`) so `--resume` can continue it. The archived `.done.json` is a historical artifact the user may delete at any time; a later fresh run (`init`) checks only the active progress path and won't clean it up.
