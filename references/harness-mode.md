# Harness Mode

## Contents

1. [Skill-Triggered Invocation](#skill-triggered-invocation) — prerequisite checks, user confirmation, command construction (steps 1–9)
2. [Single-Iteration Execution](#single-iteration-execution) — progress file, analysis cycle, fix application, structured JSON output (steps 1–9)

## Skill-Triggered Invocation

When a user invokes a skill with `deep harness` (e.g., `/optimus:code-review deep harness` or `/optimus:refactor deep harness 8 "focus on backend"`), the skill prepares and presents the harness command instead of entering in-conversation deep mode. Follow these steps in order:

### 1. Check test command

Check whether a test command is available (from `.claude/CLAUDE.md`). If no test command exists, stop with: "Deep harness requires a test command for safe auto-apply. Run `/optimus:init` to set up test infrastructure first." Do not proceed.

### 2. Warn and confirm

Present the following warning to the user:

> **Deep harness mode** launches an external orchestrator that runs up to [max_iterations, default 5] iterations. Each iteration spawns a fresh `claude -p` session that performs a full normal-mode analysis pass with prior findings injected as context — giving every iteration a clean context window without the context bloat of in-conversation deep mode.
>
> **What it does:**
> - Analyzes code and applies fixes automatically — no per-change approval
> - Runs the test suite after each iteration and reverts any fix that breaks tests (bisection)
> - Creates checkpoint commits after each successful iteration
> - Stops when no new findings are discovered (convergence) or the iteration cap is reached
>
> **Implications:**
> - Each iteration consumes a full `claude -p` session — credit and rate-limit usage multiplies with iteration count
> - Sessions run with `--dangerously-skip-permissions` by default (headless mode has no terminal for prompts). Use `--allowed-tools` for a safer alternative
> - Low test coverage increases the chance of undetected breakage; consider running `/optimus:unit-test` first
>
> Test command: `[test command from CLAUDE.md]`

Then use `AskUserQuestion` — header "Deep harness mode", question "Proceed with deep harness?":
- **Start deep harness** — "Launch external orchestrator (up to [max_iterations, default 5] iterations with fresh context)"
- **In-conversation deep mode** — "Run iterative analysis within this conversation instead"
- **Normal mode** — "Single pass with manual approval instead"

If the user selects **In-conversation deep mode**, fall through to the skill's interactive deep mode flow (set the `deep` flag and continue as if the user had invoked with `deep` only). If the user selects **Normal mode**, continue with the standard single-pass flow. If the user selects **Start deep harness**, proceed to step 3.

### 3. Resolve plugin root

Run `echo $CLAUDE_PLUGIN_ROOT` via Bash. Store the result as `plugin_root`. If the output is empty, stop with: "Cannot resolve plugin root — ensure optimus-claude is installed via the Claude Code plugin system."

### 4. Check Python

Run `python3 --version` via Bash. If it fails, try `python --version`. If neither returns Python 3.8+, stop with: "Harness requires Python 3.8+. Install Python and retry." Remember which command worked (`python3` or `python`) for step 7.

### 5. Check claude CLI

Run `claude --version` via Bash. If not available, stop with: "Harness requires the `claude` CLI. Install Claude Code and retry."

### 6. Check for existing progress

Run `ls .claude/deep-mode-progress.json 2>/dev/null` via Bash. If the file exists, use `AskUserQuestion` — header "Existing progress file", question "A progress file from a previous harness run exists. What would you like to do?":
- **Resume** — "Continue from the last completed iteration"
- **Start fresh** — "Delete and start a new run"

### 7. Build command

Construct the harness command using these parameters passed by the calling skill:
- `skill_name` — the skill identifier (e.g., `code-review`, `refactor`)
- `scope` — optional scope text from user arguments (omit `--scope` if empty)
- `max_iterations` — optional iteration cap (omit `--max-iterations` if using default 5)
- `resume` — whether user chose Resume in step 6

```
<python_cmd> "<plugin_root>/scripts/deep-mode-harness.py" \
  --skill <skill_name> \
  --progress-file .claude/deep-mode-progress.json \
  [--max-iterations <N>] \
  [--scope "<scope>"] \
  [--resume]
```

Where `<python_cmd>` is `python3` or `python` (whichever worked in step 4). Wrap `<plugin_root>` in quotes to handle paths with spaces.

### 8. Present command

> Run this in your terminal:
> ```bash
> <constructed command>
> ```
>
> **Additional options:** `--verbose` for detailed output, `--no-commit` to skip checkpoint commits, or `--allowed-tools Read,Edit,Write,MultiEdit,Glob,Grep,Bash,Agent` for safer permissions.
>
> After completion, return here and run `/optimus:commit` to commit the fixes.

### 9. Stop

Do not proceed to the skill's analysis steps. The harness runs externally.

---

## Single-Iteration Execution

When running under the external deep-mode harness (detected by `HARNESS_MODE_ACTIVE` in the system prompt), execute exactly **one iteration** of the analysis cycle, then exit. The harness handles the iteration loop, test execution, bisection, termination detection, and final reporting.

### Contents

1. [Read progress file](#1-read-progress-file)
2. [Build iteration context](#2-build-iteration-context-iterations-2)
3. [Run one analysis cycle](#3-run-one-analysis-cycle)
4. [Validate findings](#4-validate-findings)
5. [Consolidate and deduplicate findings](#5-consolidate-and-deduplicate-findings)
6. [Apply fixes](#6-apply-fixes)
7. [Do NOT run tests](#7-do-not-run-tests)
8. [Output structured JSON](#8-output-structured-json)
9. [Exit](#9-exit)

### Execution Steps

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
- If existing finding is `"persistent — fix failed"` → annotate new as `"persistent — fix failed"`
- If existing finding is `"reverted — test failure"` → annotate new as `"reverted — attempt 2"` (the harness will promote to `"persistent — fix failed"` if it fails again)

### 6. Apply fixes

Apply all validated findings using Edit or MultiEdit — same as normal mode. Skip any annotated `"persistent — fix failed"`.

**Critical for harness bisection**: For EACH fix applied, record:
- `pre_edit_content` — the exact original code before editing (the string that was replaced)
- `post_edit_content` — the exact code after editing (the replacement string)

These content pairs enable the harness to mechanically apply/revert individual fixes during test bisection without needing another Claude session. Each pair must be precise enough that `content.replace(pre_edit_content, post_edit_content)` produces the same result as the Edit tool call.

An empty `post_edit_content` is valid — it means the fix deletes the matched code (e.g., removing dead code or a redundant check). The harness supports this.

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
      "category": "<category from the agent finding — skill-specific>",
      "guideline": "<specific rule or 'General: ...'>",
      "summary": "<one-sentence, max 120 chars>",
      "fix_description": "<brief description of the fix applied>",
      "severity": "<Critical | Warning | Suggestion>",
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
