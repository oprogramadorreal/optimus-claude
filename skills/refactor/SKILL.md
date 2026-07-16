---
description: Refactors code toward project-guideline compliance and testability (so /optimus:unit-test can safely increase coverage) using 4 parallel analysis agents. Analyzes the whole project by default or a user-provided scope, presents a prioritized plan, and applies only user-approved changes as local uncommitted edits verified against the test suite. Supports "testability" or "guidelines" focus to prioritize finding categories. Works best after /optimus:init (falls back to generic guidelines without it); run before /optimus:unit-test or periodically to prevent tech debt. For an iterative apply-test-repeat loop, use /optimus:deep refactor.
disable-model-invocation: true
argument-hint: "[testability|guidelines] [scope]"
---

# Project-Wide Code Refactoring

Analyze existing source code against the project's own coding guidelines using 4 parallel agents, present a prioritized refactoring plan, then apply only user-approved changes with test verification. Two goals drive every finding:

1. **Guideline compliance** — align code with coding-guidelines.md, architecture.md, styling.md, and testing.md
2. **Testability** — restructure code so `/optimus:unit-test` can safely increase coverage without risky refactoring

## Step 1: Verify Prerequisites and Determine Scope

If the invocation prompt contains `HARNESS_MODE_INLINE`, read Step 2 first — scope is pre-resolved by the orchestrator.

### Multi-repo workspaces

Read `$CLAUDE_PLUGIN_ROOT/skills/init/references/multi-repo-detection.md` for workspace detection. In a multi-repo workspace, resolve prerequisites per-repo: load `.claude/CLAUDE.md` and `.claude/docs/` from each repo the scope targets (not the workspace root) and apply each repo's context to its own files. If no target repo can be determined, ask the user which repo to analyze.

### Prerequisite check

Read `$CLAUDE_PLUGIN_ROOT/skills/init/references/prerequisite-check.md` and apply it (CLAUDE.md + coding-guidelines.md existence, fallback logic).

### Arguments

- **Focus** — a standalone unquoted `testability` or `guidelines` token (case-insensitive) sets the focus mode used in Step 6 and is consumed from the arguments. A keyword inside a quoted scope string is scope text, not focus (`/optimus:refactor "improve testability in auth"` has no focus). If both keywords appear, use the first and suggest separate passes for each.
- **Everything else** — natural-language scope instructions.

### Scope resolution

Default to the full project. If the user described a scope, map it to directory paths by scanning the project structure. If they asked for changes since some point in history, use `git diff --name-only <ref>...HEAD` for commits, branches, and tags — but `git log --no-merges --since="..." --format= --name-only` for relative dates (`--since` is a `git log` flag, not `git diff`) — then filter to source files per Step 3. Ask only when the scope is genuinely ambiguous. For monorepos: with full-project scope, ask which subprojects to include (default all); with a directory scope, auto-detect the owning subproject.

## Step 2: Inline Harness Mode Detection

If your invocation prompt body contains `HARNESS_MODE_INLINE`, you are running as a single iteration inside the `/optimus:deep` orchestrator. Read `$CLAUDE_PLUGIN_ROOT/references/harness-mode.md` and follow its single-iteration execution protocol — progress-file reading, state initialization, scope and file-list rules, and step overrides (including the apply/output protocol). If `scope_files.current` in the progress file is non-empty, treat it as the pre-resolved scope (the orchestrator pre-populates it) and skip Step 1's scope resolution entirely. Proceed through Steps 3–6, skip the Step 7 confirmation (the orchestrator handles approval upfront), apply the fixes mechanically per Step 8's harness-mode paragraph, emit the structured JSON via the harness-mode output protocol, and stop. Do not use `AskUserQuestion`. Do not loop.

If `HARNESS_MODE_INLINE` is NOT present, continue with the interactive flow below.

## Step 3: Load Project Context and Map Analysis Areas

Read `$CLAUDE_PLUGIN_ROOT/skills/init/references/constraint-doc-loading.md` and apply it — the document-loading procedure for single projects and monorepos, plus the Submodule Exclusion rule. The loaded docs define the rules: every suggestion must be justified by what they establish — never impose external preferences.

Within the chosen scope, identify source directories. Skip non-source directories (dot-directories, dependency dirs such as `node_modules`/`vendor`/virtualenvs, build output, framework caches), non-source file types (minified files, lock files, generated `*.d.ts`, binary and data files), and generated source that must never be hand-edited (`*.g.dart`, `*.freezed.dart`, `*.mocks.dart`, `*.Designer.cs`, and files under `Migrations/` directories).

Group files by top-level source directory; in a monorepo, by subproject first.

**Harness mode:** when `scope_files.current` is non-empty, derive analysis areas from the unique parent directories of those files instead of scanning the whole project.

Rank directories by recent change frequency and analyze the highest-churn areas first (top ~10 for a full-project pass on a large codebase):

```bash
git log --no-merges --since="3 months" --format= --name-only -- <scope-path> | sort | uniq -c | sort -rn
```

Briefly summarize the docs loaded (and any missing, with fallback status), the project layout, and the analysis areas, then proceed straight to Step 4 without waiting for confirmation.

## Step 4: Parallel Multi-Agent Analysis (4 agents)

Launch all 4 agents as `general-purpose` Agent tool calls in a **single** message so they run in parallel. The full fan-out is the design — do not reduce the count to save tokens or time.

| Agent prompt file | Role |
|---|---|
| `agents/guideline-reviewer.md` | Explicit violations of project docs with exact rule citations |
| `agents/testability-analyzer.md` | Structural barriers to unit testing — hardcoded deps, tight coupling, global state |
| `agents/consistency-analyzer.md` | Cross-file duplication, pattern inconsistency, missing abstractions, architectural drift |
| `agents/code-simplifier.md` | Unnecessary complexity, naming, dead code, pattern violations |

Prompt files live in `$CLAUDE_PLUGIN_ROOT/skills/refactor/agents/`, alongside `shared-constraints.md` (shared quality bar, exclusions, false-positive guidance). Each agent receives the Step 3 file list. The guideline-reviewer prompt is constructed dynamically from Step 3's doc-loading results (single-project vs monorepo paths).

Compose each prompt per "Prompt assembly at dispatch time" in `$CLAUDE_PLUGIN_ROOT/references/agent-architecture.md`: substitute the resolved absolute plugin root for every `$CLAUDE_PLUGIN_ROOT` reference the prompt files carry, and inline or absolutize the bare `shared-constraints.md` reference — subagents inherit neither the variable nor the agents directory as cwd.

**Iteration context (harness mode, iterations 2+):** when the progress file's `iteration.current` is greater than 1, prepend the Iteration Context Block to every agent prompt before the file list — see `$CLAUDE_PLUGIN_ROOT/skills/refactor/agents/context-blocks.md` for the template.

Wait for all launched agents to complete before proceeding.

## Step 5: Validate Findings

Apply the verification protocol from `$CLAUDE_PLUGIN_ROOT/skills/init/references/verification-protocol.md` — agent findings are claims requiring independent evidence, not ground truth. For each finding: read enough surrounding code (±30 lines) to confirm the issue exists in context; look for comments, test assertions, or established patterns showing the code is intentional; and note when the guideline-reviewer and consistency-analyzer flagged the same location (consensus raises confidence). Unvalidated runtime assumptions (inputs, dependencies, environment) that could cause failures strengthen a finding.

Check change intent with `git log --no-merges --format="%h %s" -5 -- <file>` for each file with findings. If recent history shows the flagged code was introduced deliberately — a commit like "add dependency injection", or (when the message is uninformative) a diff adding the very structure a finding wants to undo — reduce that finding's confidence one level. Skip gracefully when git history is unavailable.

Assign confidence: **High** (clear evidence) and **Medium** (plausible, some evidence) proceed to Step 6; **Low** (uncertain, likely false positive) is dropped.

## Step 6: Present Refactoring Plan

Merge and deduplicate: same file + line range + category → keep the more detailed finding; flagged by both guideline-reviewer and consistency-analyzer → merge into one and note the independent confirmation.

**Contradictions:** when two findings target the same code but recommend opposite directions (e.g., "extract to reduce duplication" vs "inline for clarity"), keep the higher-severity one. At equal severity, keep the one matching the active focus; with no focus, keep the testability finding — testability is a primary goal of this skill.

**Finding cap:** at most **15 findings** per run, each a distinct root cause with supporting evidence — never pad to reach the cap. When a focus is active, reserve 12 slots for the focused category and 3 for the rest, redistributing unused slots either way; order within each group by severity, then confidence. Category mapping: `testability` focus → Testability Barrier findings (and any finding with a testability impact) fill the reserved slots; `guidelines` focus → all categories except Testability Barrier fill them. With no focus, order all findings by severity then confidence. If more issues exist than the cap, say so and suggest a narrower scope or `/optimus:deep refactor`.

Severity scale: **Critical** (testability barrier blocking unit testing, cross-cutting pattern, significant duplication, or SRP violation affecting readability/safety), **Warning** (guideline or consistency issue in limited scope), **Suggestion** (minor clarity or hygiene).

Present the plan with a short summary (scope, focus, areas analyzed, finding counts by severity, top recommendation), then the numbered findings — each with file:line, category, the guideline it addresses, a brief current/suggested sketch, and a testability-impact note where the fix unlocks coverage. Lead with cross-cutting findings, and list areas that came back clean so the user knows they were reviewed, not skipped.

If nothing survives validation, report that as a positive result and skip to the closing recommendation.

## Step 7: Ask How to Proceed

Ask the user whether to apply everything, a selection of findings by number, or nothing (keeping the plan as reference). Record the choice for Step 8.

## Step 8: Apply Approved Changes and Verify

**Under harness mode (`HARNESS_MODE_INLINE`), skip all verification in this step.** Apply the fixes, record the `pre_edit_content`/`post_edit_content` pairs, and emit the JSON — the orchestrator owns all test execution and bisection (see `$CLAUDE_PLUGIN_ROOT/references/harness-mode.md` §7). Do not run the test command or revert anything yourself.

Otherwise (interactive mode): apply each approved finding, then run the project's test command (from `.claude/CLAUDE.md`) if one exists, following the verification protocol — fresh run, complete output, results reported with evidence. If tests fail, revert all changes and re-apply one finding at a time with a test run after each: keep what passes, skip what fails. If no test command is available, warn the user that the changes were applied without automated verification.

Close with a brief summary: what was applied and skipped (with file references), test results, anything reverted, and findings beyond the cap that remain.

## Important

- Never commit, push, or modify files beyond the user-approved findings — all changes stay as local modifications the user can review with `git diff` before committing.
- When the scope is too broad for effective analysis, recommend narrowing it.

When changes were applied, suggest reviewing them with `/optimus:code-review` or committing them, and `/optimus:unit-test` to cover code the testability fixes unlocked. A single pass can miss issues — for an apply-test-repeat loop that runs until clean, suggest `/optimus:deep refactor` (requires a test command in `.claude/CLAUDE.md`).
