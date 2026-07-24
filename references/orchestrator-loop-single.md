# Orchestrator Loop — Single Skill (Deep Variant)

## Contents
1. [Per-iteration body](#per-iteration-body) — steps 1–8
2. [Loop control invariants](#loop-control-invariants)
3. [Parse-failure recovery](#parse-failure-recovery)
4. [After the loop](#after-the-loop)

Shared iteration template for `/optimus:deep review` and `/optimus:deep refactor`. The orchestrator dispatches its base skill into a fresh subagent context per iteration, parses the structured JSON the base skill emits, and uses the harness CLI to manage state, test/bisect, and decide termination. All state lives in the progress file — the orchestrator never holds findings or fixes in conversation prose; it reads the CLI's stdout to make decisions.

**Plugin root.** Every command below writes `$CLAUDE_PLUGIN_ROOT` to mean the plugin root the orchestrator skill resolved in its Step 2. Bash-tool environment variables do **not** persist across separate Bash calls and may read empty on some platforms (notably Windows); if `echo $CLAUDE_PLUGIN_ROOT` was empty there, substitute the resolved absolute path **literally** into every `PYTHONPATH=...` command and into every dispatch prompt in this file.

## Per-iteration body

The orchestrator skill repeats steps 1–8 below until step 7 (`check-termination`) returns anything other than `continue`. Steps 1–6 and 8 mutate the progress file on disk; step 7 reads it.

### 1. Snapshot pre-iteration git state

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli snapshot --progress-file "<progress-path>"
```

Records `HEAD` into `progress["_snapshot"]["pre_head"]` and stamps the current iteration into `progress["_snapshot"]["iteration_token"]`. In no-commit mode — the run was started `--no-commit`, or a prior commit failed — `snapshot` also captures a working-tree stash automatically, so the iteration stays restorable; you do **not** need to pass `--include-stash` (it remains an explicit override).

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
    Phase: <base-skill>

    Read the base SKILL.md at
    `<absolute-plugin-root>/skills/<base-skill>/SKILL.md` and execute its
    harness-mode protocol from
    `<absolute-plugin-root>/references/harness-mode.md` exactly. Wherever the
    base SKILL.md, harness-mode.md, or the agent prompt files they load
    reference `$CLAUDE_PLUGIN_ROOT`, substitute the absolute plugin root
    above — your environment may not export it:
    - Read the progress file above for accumulated findings and scope.
    - Run the analysis cycle once.
    - Apply fixes. Do NOT run the test command, any `scripts/*.sh`, or any
      lint/build — the orchestrator owns all test execution and bisection.
    - Emit a single ```json:harness-output fenced block and stop.
    - Do not use AskUserQuestion. Do not loop.
```

Where `<base-skill>` is `code-review` or `refactor`, and `<absolute-plugin-root>` is the root resolved in Step 2 (the subagent does not inherit `$CLAUDE_PLUGIN_ROOT`, so it must be passed as an absolute path — and the subagent must substitute it onward into the fan-out agent prompts it composes, per "Prompt assembly at dispatch time" in `$CLAUDE_PLUGIN_ROOT/references/agent-architecture.md`). The subagent inherits the working tree and applies edits via `Edit`/`MultiEdit`; on return, the working tree carries the iteration's changes and the subagent's final message contains the structured JSON.

### 3. Save the subagent return to a temp file

Write the subagent's final message text to a temp file **verbatim** — never summarize, abbreviate, or re-type any part of it: the `pre_edit_content`/`post_edit_content` strings inside the JSON are the bisect's apply/revert data, and a corrupted copy makes its fix unrecoverable (`skipped — apply failed`). Saving to a file also keeps the raw output out of the orchestrator's parent context:

```bash
TMP_RAW=".claude/.deep-iteration-raw.txt"
TMP_RESULT=".claude/.deep-iteration-result.json"
```

These files must live in `.claude/` and carry these exact filename prefixes (`.deep-iteration-` and `.unit-test-deep-`) — the checkpoint commit's un-stage step (`commit_checkpoint` in `scripts/harness_common/git.py`) matches the `.claude/`-anchored patterns `.claude/.deep-iteration-*` and `.claude/.unit-test-deep-*` to keep harness state out of the commit, and `final-report`'s scratch cleanup only sweeps the progress file's own directory.

### 4. Extract the structured JSON

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli parse \
    --input-file "$TMP_RAW" \
    --output-file "$TMP_RESULT" \
    --progress-file "<progress-path>"
```

Errors on missing `json:harness-output` block. Passing `--progress-file` lets the CLI track consecutive parse failures across iterations (and across `--resume`) — see "Parse-failure recovery" below.

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

Possible values: `continue`, `convergence`, `no-actionable`, `all-reverted`, `cap`, `diminishing-returns`, `parse-failure`. If the value is anything other than `continue`, exit the loop.

### 8. Advance the iteration counter

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli advance --progress-file "<progress-path>"
```

Increments `iteration.current`. Then loop back to step 1.

## Loop control invariants

- **Snapshot before dispatch.** The CLI's `deep-step` needs a fresh `pre_head` to recover from test failures, and verifies the snapshot's `iteration_token` matches the current iteration — a skipped snapshot makes `deep-step` exit non-zero rather than restore to a stale commit.
- **Always write progress before dispatching.** Cancellation between dispatches is recoverable via `--resume`; cancellation mid-dispatch leaves the progress file valid as of the prior iteration.
- **Slice-only progress reads.** Never read the full progress file's `findings` array in the orchestrator's own context. `check-termination` returns a single word; trust it.
- **Subagent output is text, not state.** Save each subagent's return to a temp file verbatim, parse it, then forget it — do not keep the raw output in the orchestrator's conversation.
- **Re-entry guard.** If the orchestrator's own invocation prompt body already contains `HARNESS_MODE_INLINE`, stop with `"Deep mode cannot run inside deep mode"` — this prevents a misbehaving subagent from triggering recursion.
- **Don't end a turn on a promise.** Mid-loop, if the next step is a tool call, issue it — end only at termination or when blocked on input only the user can provide.
- **Report only what the CLI confirmed.** Per-iteration status comes from `deep-step` / `check-termination` stdout — if a step was skipped or a count is unverified, say so.

## Parse-failure recovery

If the CLI's `parse` subcommand exits non-zero, the subagent emitted no `json:harness-output` block. Common causes: the subagent hit its tool or token budget mid-response; the base SKILL.md lost its `HARNESS_MODE_INLINE` detection (regression — see `references/harness-mode.md`); the subagent fell into interactive mode and hung on `AskUserQuestion`.

On a single failure: warn the user but continue — the iteration is a no-op (the CLI rolls the failed dispatch's partial edits back to the iteration snapshot, so nothing half-done is left for a later checkpoint to commit). Skip steps 5–6 for this iteration — `parse` only rewrites `$TMP_RESULT` on success, so it still holds the previous iteration's JSON and `deep-step` would silently re-process it — and continue at step 7 (`check-termination`) then step 8 (`advance`). On two consecutive failures: `check-termination` at step 7 returns `parse-failure` automatically; exit the loop and surface the error for the user to investigate.

The counter lives in the progress file under `parse_failure_count`, resets to 0 on every successful parse, and survives `--resume`.

## After the loop

Print the final report:

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli final-report --progress-file "<progress-path>" --archive
```

The `--archive` flag moves the progress file to its `.done.json` sibling (the `.json` suffix is replaced — e.g. `.claude/code-review-deep-progress.done.json`) and removes the backup; a subsequent `--resume` refuses the archived path. **Exception**: when the run ended in `diminishing-returns`, a resumable soft-exit, the CLI leaves the active progress file in place (prints `not-archived`) so `--resume` can continue it.
