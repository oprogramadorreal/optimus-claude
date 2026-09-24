# Harness Mode (single-iteration protocol)

## Contents

1. [Single-Iteration Execution](#single-iteration-execution) — progress file, analysis cycle, fix application, structured JSON output (steps 1–9)
2. [Skill-step execution under harness mode](#skill-step-execution-under-harness-mode) — which base-skill steps run, per-skill scope rules, `pr_description` handling
3. [Termination reasons](#termination-reasons) — enum of exit reasons the orchestrator may record

## Single-Iteration Execution

When running under the `/optimus:deep` orchestrator (a `review` or `refactor` run, or the refactor phase of `deep coverage`), the base skill detects `HARNESS_MODE_INLINE` in its invocation prompt and executes exactly **one iteration** of the analysis cycle, then exits. The orchestrator handles the iteration loop, test execution, bisection, termination detection, and final reporting via `python -m harness_common.cli`.

### 1. Read progress file

Read the JSON progress file at the path specified in your invocation prompt and take:
- `iteration-count` = `iteration.current`
- `accumulated-findings` = the `findings` array, each with its status (cross-session state from prior iterations)
- `scope_files.current` — file paths to analyze
- `config.focus` — finding-cap priority mode for skills that support one (empty string = balanced)
- `config.pr_description` — optional `{"title", "body", "base_ref"}` dict the orchestrator captured for the current branch's open PR (null when no PR or `gh` unavailable)

If `scope_files.current` is non-empty, use it as the file list for agents — this overrides the skill's Step 3 file discovery (the orchestrator pre-populated the scope). If it is empty, fall back to the skill's Step 3 file discovery, restricted to the user's path scope in `config.scope.paths` when that list is non-empty (per-skill rules below).

### Skill-step execution under harness mode

After reading the progress file, run the skill's scope, context-loading, analysis, validation, and consolidation steps in order under the overrides below; skip every user prompt (the orchestrator handles approval upfront) and every summary, report, or next-step recommendation the skill would present — steps 6–9 of this protocol replace the skill's approval, apply, verification, and report steps. A missing-docs prerequisite takes its bundled-baseline fallback without asking. Scope handling is skill-specific:

- **code-review**: whatever the working tree holds, review in Step 3's **Branch/ref mode** with `<ref>` = `config.scope.base_ref`, else `config.pr_description.base_ref`, else `origin/<default branch>` per Step 3 item 3 (never ask the user; if none resolves, there is nothing to review — emit step 8's block with no findings), filtered to `config.scope.paths` when non-empty — never PR mode, never `gh pr view`; skip the large-diff warning.
- **refactor**: when `scope_files.current` is non-empty, it replaces Step 1's scope resolution — group its files by parent directory into analysis areas; when empty, run Step 3's normal directory scan over `config.scope.paths`, or the full project when that list is empty.

If `config.pr_description` is non-null and the skill defines a PR/MR context block (code-review does; refactor does not), treat it as the interactive `pr-description`: inject it per Step 5 "PR/MR context injection" and apply Step 6 "PR/MR description as intent signal".

### 2. Build iteration context (iterations 2+)

If `iteration-count` > 1, construct the Iteration Context Block from the accumulated findings using the "Iteration Context Block" template in `$CLAUDE_PLUGIN_ROOT/references/context-injection-blocks.md` — that file is the single source for the block, including the status-values legend, the empty-field fallbacks, and the closing "Focus your review on NEW issues only" instruction.

### 3. Run one analysis cycle

Run the skill's normal analysis step, inline or fanned out per its own sizing rule. On iterations 2+, inject the Iteration Context Block (step 2) into each agent prompt before the file list, in interactive mode's injection order. When analyzing inline, read it as your own context instead.

### 4. Validate findings

Apply the skill's normal validation protocol, with one override.

**Auto-apply gate.** Nothing here gets user review before it lands, so only findings your validation confirms earn a fix in step 6. But **do not drop a finding you could not confirm.** Record it in `new_findings` with its post-validation confidence, and set `pre_edit_content` and `post_edit_content` to empty strings rather than omitting them (the schema requires both). Dropping would hide it: an iteration whose findings were all unconfirmed would report `no_new_findings: true` and end the run as a clean `convergence`.

### 5. Consolidate and deduplicate findings

Apply the same deduplication rules as the skill's normal mode, then match each finding against `accumulated-findings` by file + line range + category:
- `fixed` → drop it (the code was intentionally changed)
- `persistent — fix failed` → drop it too (every fix attempt already failed); apply no fix
- any other status → keep it as a new finding; the orchestrator escalates repeat reverts itself

### 6. Apply fixes

Apply every confirmed finding left in `new_findings` using Edit — same as normal mode.

**Critical for orchestrator bisection**: For EACH fix applied, record:
- `pre_edit_content` — the exact original code before editing (the string that was replaced)
- `post_edit_content` — the exact code after editing (the replacement string)

These content pairs let the orchestrator bisect a test failure without another subagent dispatch: it rebuilds from the pre-iteration snapshot and re-applies the pairs in list order, skipping any whose `pre_edit_content` does not occur exactly once at that point. So list entries in the order you made the edits, and make each `pre_edit_content` unique in the file at the moment of its edit.

An empty `post_edit_content` is valid — it means the fix deletes the matched code (e.g., removing dead code or a redundant check).

For fixes that span multiple locations in a single file, output one entry per edit location.

### 7. Do NOT run tests

The orchestrator owns all test execution and bisection — running them here would pull stack traces and assertion failures into the subagent's context window. Do **not** run the project's test command, any `scripts/*.sh`, or any lint / build / coverage invocation — not even to "verify" your own fixes — and skip any such verification step the base skill's normal (interactive) flow would perform; finding validation (step 4) still applies. Apply your edits and emit the JSON.

### 8. Output structured JSON

Make your final message exactly one `json:harness-output` fenced block and nothing else — the orchestrator copies that message verbatim.

Read `$CLAUDE_PLUGIN_ROOT/references/schemas/harness-output.schema.json` — it is the contract, and it carries field names, types, which fields are required, the enums, and what `no_actionable_fixes` means. `$CLAUDE_PLUGIN_ROOT/test/harness-common/fixtures/harness-output.golden.json` is a complete worked instance to copy the shape from.

The one thing the schema cannot state: `category` values are skill-specific — use the category the agent that raised the finding assigned it.

### 9. Exit

Stop immediately after outputting the JSON block. Do NOT loop back to the analysis step, present a cumulative or per-iteration report, recommend next steps, use `AskUserQuestion`, or check termination conditions. The orchestrator parses the JSON output, runs tests via the harness CLI, updates the progress file, and decides whether to dispatch another iteration.

### Termination reasons

The orchestrator may record one of these reasons on exit:

- **`convergence`** — zero new findings
- **`no-actionable`** — findings exist but have no code edits
- **`all-reverted`** — every fix this iteration failed tests
- **`diminishing-returns`** — yield plateaued at ≤1 new finding for two consecutive iterations ending at iter 4 or later, with no reverted fixes in either window iteration; remaining issues may exist and can be resumed via `--resume`
- **`cap`** — max iterations hit
- **`parse-failure`** — subagent error (after two consecutive iterations produced no parseable JSON)
- **`blocked`** — coverage target only: the unit-test phase hit a stop gate it cannot work past (no test framework, red baseline). Like `diminishing-returns` it is a resumable soft exit — the orchestrator records it before leaving the loop, and the progress file is left un-archived so `--resume` works once the user clears the prerequisite
