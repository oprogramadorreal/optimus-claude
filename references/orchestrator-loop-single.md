# Orchestrator Loop — Single Skill (Deep Variant)

## Contents
1. [Per-iteration body](#per-iteration-body) — steps 1–8
2. [Loop control invariants](#loop-control-invariants)
3. [Parse-failure recovery](#parse-failure-recovery)
4. [After the loop](#after-the-loop)

Shared iteration template for `/optimus:code-review-deep` and `/optimus:refactor-deep`. Each orchestrator skill dispatches its base skill into a fresh subagent context per iteration, parses the structured JSON the base skill emits, and uses the harness CLI to manage state, test/bisect, and decide termination.

The orchestrator never holds findings or fixes in conversation prose. All state lives in the progress file. Each Bash invocation of the CLI is a discrete operation; the orchestrator skill reads the CLI's stdout to make decisions.

## Per-iteration body

The orchestrator skill repeats steps 1–8 below until step 7 (`check-termination`) returns anything other than `continue`. Steps 1–6 and 8 mutate the progress file on disk; step 7 reads it.

### 1. Snapshot pre-iteration git state

```bash
python -m harness_common.cli snapshot --progress-file "<progress-path>"
```

Records `HEAD` into `progress["_snapshot"]["pre_head"]`. Add `--include-stash` if running with `--no-commit` so the working tree can be restored after a failed iteration.

### 2. Dispatch the base skill into a fresh subagent

Use the `Agent` tool. The prompt **must** include the inline sentinel, the absolute progress-file path, the iteration counter, and instructions to read the base SKILL.md from disk:

```
Agent tool call:
  subagent_type: general-purpose
  description: "<base-skill> iteration <N>"
  prompt: |
    HARNESS_MODE_INLINE
    Progress file: <absolute-progress-path>
    Iteration: <N> of <max>
    Phase: <skill>

    Read the base SKILL.md at `skills/<base-skill>/SKILL.md` under the
    plugin root and execute its harness-mode protocol from
    `references/harness-mode.md` exactly:
    - Read the progress file above for accumulated findings and scope.
    - Run the analysis cycle once.
    - Apply fixes (do NOT run tests — the orchestrator handles tests).
    - Emit a single ```json:harness-output fenced block and stop.
    - Do not use AskUserQuestion. Do not loop.
```

Where `<base-skill>` is `code-review` or `refactor`. The subagent inherits the working tree and applies edits via `Edit`/`MultiEdit`; on return, the working tree carries the iteration's changes and the subagent's final message contains the structured JSON.

### 3. Save the subagent return to a temp file

Write the subagent's final message text to a temp file (the orchestrator's parent context should not hold the raw subagent output verbatim). A repo-local temp path is fine:

```bash
TMP_RAW=".claude/.deep-iteration-raw.txt"
TMP_RESULT=".claude/.deep-iteration-result.json"
```

The exact filenames are an implementation choice — the only requirement is that they live in the project directory (cross-platform), are reused per-iteration (not accumulated), and are gitignored or removed at end of run.

### 4. Extract the structured JSON

```bash
python -m harness_common.cli parse \
    --input-file "$TMP_RAW" \
    --output-file "$TMP_RESULT"
```

Errors on missing `json:harness-output` block. If the orchestrator's previous step produced no parseable result, treat this as a fatal iteration crash and stop.

### 5. Process the iteration

```bash
python -m harness_common.cli deep-step \
    --progress-file "<progress-path>" \
    --result-file "$TMP_RESULT"
```

This single subcommand: promotes actionable fixes, registers findings, runs tests, bisects on failure, updates per-finding statuses, appends iteration history, widens scope, and writes the result. Its stdout is one of:

| Output | Meaning |
|---|---|
| `converged` | Skill reported `no_new_findings` — loop terminates. |
| `no-actionable` | Skill reported `no_actionable_fixes` — loop terminates. |
| `all-reverted` | Every fix in this iteration was reverted — loop terminates. |
| `applied fixed=<N> reverted=<N> test_passed=<0\|1>` | Iteration completed normally — continue. |

### 6. Checkpoint commit (skip if `--no-commit`)

```bash
python -m harness_common.cli commit-checkpoint --progress-file "<progress-path>"
```

Returns `committed`, `nothing-to-commit`, or `commit-failed`. On `commit-failed`, the orchestrator should warn and switch the remaining iterations to `--no-commit` mode (skip commits going forward).

### 7. Check termination

```bash
TERMINATION=$(python -m harness_common.cli check-termination \
    --progress-file "<progress-path>")
```

Possible values: `continue`, `convergence`, `no-actionable`, `all-reverted`, `cap`, `diminishing-returns`. If the value is anything other than `continue`, exit the loop.

### 8. Advance the iteration counter

```bash
python -m harness_common.cli advance --progress-file "<progress-path>"
```

Increments `iteration.current`. Then loop back to step 1.

## Loop control invariants

- **Snapshot before dispatch.** The CLI's `deep-step` needs a known `pre_head` to recover from test failures.
- **Always write progress before dispatching.** Cancellation between dispatches is recoverable via `--resume`; cancellation mid-dispatch may leave the working tree inconsistent but the progress file remains valid as of the prior iteration.
- **Slice-only progress reads.** Do not read the full progress file's `findings` array between iterations in the orchestrator's own context. The CLI's `check-termination` returns a single word; trust it.
- **Subagent output is text, not state.** Treat each subagent's return as a one-time payload. Save it to a temp file, parse it, then forget it. Do not keep the raw output in the orchestrator's conversation.
- **Re-entry guard.** If the orchestrator's own invocation prompt already contains `HARNESS_MODE_INLINE`, stop with `"Deep mode cannot run inside deep mode"`. This prevents a misbehaving subagent from triggering recursion.

## Parse-failure recovery

If the CLI's `parse` subcommand exits non-zero, the subagent emitted no `json:harness-output` block. Common causes:
- The subagent hit its tool budget or token limit and stopped mid-response.
- The base SKILL.md does not detect `HARNESS_MODE_INLINE` in the prompt body (regression — see `references/harness-mode.md`).
- The subagent fell into interactive mode and hung on `AskUserQuestion`.

When this happens once: warn the user but continue (the iteration is a no-op, the loop moves on). When this happens twice in a row: stop, mark the termination reason as `parse-failure`, and surface the error for the user to investigate.

## After the loop

Print the final report:

```bash
python -m harness_common.cli final-report --progress-file "<progress-path>" --archive
```

The `--archive` flag moves the progress file to `<path>.done.json` and removes the backup, signaling that this run is complete (a subsequent `--resume` will refuse the archived path).
