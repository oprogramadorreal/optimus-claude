# Harness Mode — Single-Iteration Execution

When running under the external deep-mode harness (detected by `HARNESS_MODE_ACTIVE` in the system prompt), execute exactly **one iteration** of the deep mode cycle, then exit. The harness handles the iteration loop, test execution, bisection, termination detection, and final reporting.

## Contents

1. [Read progress file](#1-read-progress-file)
2. [Build iteration context](#2-build-iteration-context-iterations-2)
3. [Run one analysis cycle](#3-run-one-analysis-cycle)
4. [Validate findings](#4-validate-findings)
5. [Consolidate and deduplicate findings](#5-consolidate-and-deduplicate-findings)
6. [Apply fixes](#6-apply-fixes)
7. [Do NOT run tests](#7-do-not-run-tests)
8. [Output structured JSON](#8-output-structured-json)
9. [Exit](#9-exit)

## Execution Steps

### 1. Read progress file

Read the JSON progress file at the path specified in the system prompt. Extract:
- `iteration.current` — which iteration this is
- `findings` — accumulated findings from prior iterations (with status)
- `scope_files.current` — file paths to analyze
- `config.test_command` — the test command (for reference only — do NOT run it)
- `config.max_iterations` — the iteration cap (for reference only — do NOT check it)

Initialize from the progress file:
- `deep-mode` = true
- `iteration-count` = `iteration.current`
- `accumulated-findings` = `findings` array (restoring cross-session state from disk)
- File list for agents = `scope_files.current`

### 2. Build iteration context (iterations 2+)

If `iteration-count` > 1, construct the Iteration Context Block from the accumulated findings using the same template as `$CLAUDE_PLUGIN_ROOT/references/context-injection-blocks.md`:

```
## Prior Findings (iterations 1–[N-1])

| File | Line | Category | Summary | Status |
|------|------|----------|---------|--------|
[one row per finding from accumulated-findings]
```

Use only compact fields (file, line, category, summary, status) — do NOT include code content (`pre_edit_content` / `post_edit_content`) in the context block, as that would recreate context bloat.

### 3. Run one analysis cycle

Launch all agents in parallel — same agents, same prompts, same parallelism as the skill's normal agent step. Inject the iteration context block (from step 2) into agent prompts before the file list, following the same injection order as interactive mode.

### 4. Validate findings

Apply the same validation protocol as the skill's normal validation step. Independently verify each finding, check for false positives, apply change-intent awareness from git history.

### 5. Consolidate and deduplicate findings

Apply the same deduplication rules as interactive deep mode, matching against `accumulated-findings` by file + line range + category:
- If existing finding is `"fixed"` → skip new entry (code was intentionally changed)
- If existing finding is `"persistent—fix failed"` → annotate new as `"persistent—fix failed"`
- If existing finding is `"reverted—test failure"` → annotate new as `"reverted—attempt 2"` (the harness will promote to `"persistent—fix failed"` if it fails again)

### 6. Apply fixes

Apply all validated findings using Edit or MultiEdit — same as normal mode. Skip any annotated `"persistent—fix failed"`.

**Critical for harness bisection**: For EACH fix applied, record:
- `pre_edit_content` — the exact original code before editing (the string that was replaced)
- `post_edit_content` — the exact code after editing (the replacement string)

These content pairs enable the harness to mechanically apply/revert individual fixes during test bisection without needing another Claude session. Each pair must be precise enough that `content.replace(pre_edit_content, post_edit_content)` produces the same result as the Edit tool call.

For fixes that span multiple locations in a single file, output one entry per edit location.

### 7. Do NOT run tests

The harness handles test execution and bisection externally. This keeps test output (stack traces, assertion failures) out of the context window. Do not run the test command.

### 8. Output structured JSON

At the end of the response, output the iteration results in this exact format:

````
```json:harness-output
{
  "iteration": <number>,
  "new_findings": [
    {
      "file": "<path>",
      "line": <number>,
      "end_line": <number>,
      "category": "<Bug | Security | Guideline Violation | Code Quality | Test Coverage Gap | Contract Quality>",
      "guideline": "<specific rule or 'General: ...'>",
      "summary": "<one-sentence, max 120 chars>",
      "fix_description": "<brief description of the fix applied>",
      "severity": "<Critical | High | Medium>",
      "confidence": "<High | Medium>",
      "agent": "<agent-name>",
      "pre_edit_content": "<exact original code>",
      "post_edit_content": "<exact replacement code>"
    }
  ],
  "fixes_applied": [
    <same structure as new_findings — the subset that were actually applied via Edit/MultiEdit>
  ],
  "fixes_skipped_persistent": ["<id of findings skipped due to persistent status>"],
  "no_new_findings": <true if zero new findings discovered>,
  "no_actionable_fixes": <true if findings exist but none had actionable code edits>
}
```
````

### 9. Exit

Stop immediately after outputting the JSON block. Do NOT:
- Loop back to the analysis step
- Present a cumulative or per-iteration markdown report
- Recommend next steps
- Use `AskUserQuestion`
- Check termination conditions (convergence, cap, all-reverted)

The harness reads the JSON output, runs tests, updates the progress file, and decides whether to launch another iteration.
