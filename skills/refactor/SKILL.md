---
description: Refactors code toward two goals — project-guideline compliance and testability (so /optimus:unit-test can safely increase coverage) — using 4 parallel analysis agents. Supports "testability" or "guidelines" focus to prioritize finding categories, plus flexible scoping. Use after /optimus:init, before /optimus:unit-test, or periodically to prevent tech debt. For iterative refactoring in a loop, use `/optimus:refactor-deep`.
disable-model-invocation: true
argument-hint: "[testability|guidelines] [scope]"
---

# Project-Wide Code Refactoring

Analyze existing source code against the project's coding guidelines using 4 parallel agents to find guideline violations, testability barriers, cross-file duplication, and pattern inconsistency. Present a prioritized refactoring plan, then apply only user-approved changes with test verification.

Two primary goals:
1. **Guideline compliance** — align code with coding-guidelines.md, architecture.md, styling.md, and testing.md
2. **Testability** — restructure code so `/optimus:unit-test` can safely increase coverage without risky refactoring

The code-simplifier agent guards new code after every edit — this skill is the on-demand complement for restructuring existing code across the project.

## Step 1: Verify Prerequisites and Determine Scope

If the invocation prompt contains `HARNESS_MODE_INLINE`, read Step 2 first — scope is pre-resolved by the orchestrator.

### Multi-repo workspace detection

Read `$CLAUDE_PLUGIN_ROOT/skills/init/references/multi-repo-detection.md` for workspace detection. If a multi-repo workspace is detected, resolve prerequisites per-repo:
- Determine which repo(s) the scope targets (from file paths, user selection, or changed files)
- Load that repo's `.claude/CLAUDE.md` and `.claude/docs/` as prerequisites (not the workspace root)
- If scope spans multiple repos, load each repo's docs independently and apply per-repo context when analyzing that repo's files
- If no repo can be determined, ask the user which repo to analyze

### Prerequisite check

Read `$CLAUDE_PLUGIN_ROOT/skills/init/references/prerequisite-check.md` and apply the prerequisite check (CLAUDE.md + coding-guidelines.md existence, fallback logic).

### Parse invocation arguments

Extract from the user's arguments:
1. Focus keyword detection — match only **standalone unquoted tokens** (not inside quotes or part of longer words):
   - If remaining unquoted text contains standalone `testability` (case-insensitive) → set `focus` = `"testability"`
   - If remaining unquoted text contains standalone `guidelines` (case-insensitive) → set `focus` = `"guidelines"`
   - Otherwise → `focus` = null (balanced — current behavior)
   - The focus keyword is consumed from the remaining text (not passed as scope)
   - If both keywords appear as standalone tokens, use the first one and warn: "Multiple focus keywords detected — using '[first]'. Run separate passes for each focus."
   - **Safe examples** (keyword NOT consumed — stays as scope):
     - `/optimus:refactor "improve testability in auth"` → focus=null, scope="improve testability in auth" (inside quotes)
     - `/optimus:refactor "fix guidelines compliance"` → focus=null, scope="fix guidelines compliance" (inside quotes)
2. Everything else → scope instructions (natural language)

Examples:
- `/optimus:refactor` → full project
- `/optimus:refactor "focus on auth module"` → scope to auth
- `/optimus:refactor testability` → full project, focus=testability
- `/optimus:refactor guidelines` → full project, focus=guidelines
- `/optimus:refactor testability "focus on src/api"` → scope to src/api, focus=testability

For iterative refactor in a loop, use `/optimus:refactor-deep` instead.

### Scope resolution

- **If scope provided in arguments** → use it directly. Map the user's description to directory paths by scanning the project structure. No `AskUserQuestion` needed.
- **If no scope provided** → use `AskUserQuestion` — header "Scope", question "What scope would you like to refactor?":
  - **Full project** — "All source directories — best for first run or periodic review"
  - **Directory** — "Specific path(s) — best for targeted cleanup"
  - **Changed since** — "Files modified since a commit, tag, or date — incremental review"

Default to **full project** if the user just says "refactor" without specifying.

For **changed since**: use `git diff --name-only <ref>...HEAD` for commit SHAs, branch names, and tags. For relative dates, use `git log --no-merges --since="2 weeks ago" --format= --name-only` instead (`--since` is a `git log` flag, not `git diff`). Filter to source files only (apply the exclusion rules from Step 3).

For monorepos with **full project** scope: ask which subprojects to include (default: all). For **directory** scope: auto-detect which subproject the path belongs to.

## Step 2: Inline Harness Mode Detection

If your invocation prompt body contains `HARNESS_MODE_INLINE`, you are running inside the `/optimus:refactor-deep` or `/optimus:unit-test-deep` orchestrator as a single iteration. Read `$CLAUDE_PLUGIN_ROOT/references/harness-mode.md` and follow its single-iteration execution protocol. The reference covers progress file reading, state initialization, scope and file-list rules, and step overrides (including the apply/output protocol). If `scope_files.current` is non-empty in the progress file, treat it as the pre-resolved scope (the orchestrator pre-populated it from the feature-branch diff) and skip the Step 1 scope resolution entirely. Proceed through Steps 3–6 — skip the Step 7 user confirmation (the orchestrator handles approval upfront), apply the fixes mechanically per Step 8's harness-mode paragraph, then emit the structured JSON via the harness-mode output protocol and stop. Do not use `AskUserQuestion`. Do not loop.

If `HARNESS_MODE_INLINE` is NOT present, continue with the standard interactive flow below.

## Step 3: Load Project Context and Map Analysis Areas

### Load constraint docs

Read `$CLAUDE_PLUGIN_ROOT/skills/init/references/constraint-doc-loading.md` for the full document loading procedure (single project and monorepo layouts, scoping rules).

These files define the rules. Every suggestion must be justified by what these docs establish — never impose external preferences.

### Exclude git submodules

Apply the "Submodule Exclusion" rule from `$CLAUDE_PLUGIN_ROOT/skills/init/references/constraint-doc-loading.md` — exclude submodule directories from the analysis.

### Map analysis areas

Within the chosen scope (Step 1), identify source directories. Skip non-source:

- **Dot-directories**: `.git`, `.github`, `.vscode`, `.idea`, `.claude`, `.husky`
- **Dependencies**: `node_modules`, `vendor`, `.venv`, `venv`, `env`
- **Build output**: `dist`, `build`, `out`, `target`, `bin`, `obj`, `coverage`
- **Framework/cache**: `.next`, `.nuxt`, `__pycache__`, `.cache`, `.tox`, `.turbo`
Also skip non-source **file types**: `*.min.js`, `*.min.css`, lock files (`package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, etc.), `*.d.ts` (unless hand-written), binary and data files.

Also skip **generated source files** that should never be manually edited: `*.g.dart`, `*.freezed.dart`, `*.mocks.dart` (Dart/Flutter build_runner output), `*.Designer.cs` (Visual Studio generated), and any file inside a directory named `Migrations/` (database migration files — EF Core, Django, Alembic, etc.).

**Single project:** Group files by top-level source directory.
**Monorepo:** Organize by subproject, then by source directory within each.

**Harness mode:** If `scope_files.current` from the progress file is non-empty, derive analysis areas from the unique parent directories of those files instead of scanning the whole project — this keeps the refactor pass focused on the feature branch's actual footprint.

### Prioritize by git activity

Rank directories by recent change frequency:

```bash
git log --no-merges --since="3 months" --format= --name-only -- <scope-path> | sort | uniq -c | sort -rn
```

Analyze highest-churn directories first. For full-project scope on large codebases, start with the top 10 most active areas.

### Context Summary

Before proceeding to analysis, present a brief summary: docs loaded (with paths), docs missing (with fallback status), project type (single/monorepo/multi-repo workspace), and analysis areas identified with their git activity rank. Proceed immediately to Step 4 — do not wait for user confirmation.

## Step 4: Parallel Multi-Agent Analysis (4 agents)

Launch all 4 agents as `general-purpose` Agent tool calls in a **single** message so they run in parallel. The full fan-out is the design — do not reduce the count to save tokens or time.

Each agent receives the list of source files/directories from Step 3.

Read the agent prompt files from `$CLAUDE_PLUGIN_ROOT/skills/refactor/agents/` for individual agent prompts. Read `$CLAUDE_PLUGIN_ROOT/skills/refactor/agents/shared-constraints.md` for the shared quality bar, exclusion rules, and false positive guidance.

Compose each agent prompt per "Prompt assembly at dispatch time" in `$CLAUDE_PLUGIN_ROOT/references/agent-architecture.md`: substitute the resolved absolute plugin root for every `$CLAUDE_PLUGIN_ROOT` reference the prompt files carry, and inline or absolutize the bare `shared-constraints.md` reference — subagents inherit neither the variable nor the agents directory as cwd.

### Iteration context injection (harness mode, iterations 2+)

When running under `HARNESS_MODE_INLINE` and the progress file's `iteration.current` is greater than 1, prepend the iteration context block to every agent prompt before the file list. Read `$CLAUDE_PLUGIN_ROOT/skills/refactor/agents/context-blocks.md` for the template and format.

### Agent overview

| Agent | Role | Runs when |
|-------|------|-----------|
| 1 — Guideline Compliance | Explicit violations of project docs with exact rule citations | Always |
| 2 — Testability Analyzer | Structural barriers to unit testing — hardcoded deps, tight coupling, global state | Always |
| 3 — Consistency Analyzer | Cross-file duplication, pattern inconsistency, missing abstractions, architectural drift | Always |
| 4 — Code Simplifier | Unnecessary complexity, naming, dead code, pattern violations | Always |

Each agent returns a structured list of findings, bounded by the Finding Cap rule in `$CLAUDE_PLUGIN_ROOT/references/shared-agent-constraints.md`. The Guideline Compliance agent (Agent 1) is constructed dynamically based on Step 3's doc loading results (single project vs monorepo paths).

Wait for all launched agents to complete before proceeding to Step 5.

## Step 5: Validate Findings

Independently verify each finding to filter false positives. Apply the verification protocol from `$CLAUDE_PLUGIN_ROOT/skills/init/references/verification-protocol.md` — treat agent-reported findings as claims that require independent evidence, not as ground truth.

For each finding from Step 4:
1. **Context check** — read ±30 lines around the flagged location to verify the issue exists in context
2. **Intent check** — look for comments, test assertions, or established patterns that explain the code's behavior (what looks like a violation may be intentional)
3. **Cross-agent consensus** — for guideline/duplication findings, check if Agents 1 and 3 flagged the same location (consensus = higher confidence)
4. **Runtime assumption check** — if an agent flagged a function or module, verify whether the code assumes something about inputs, dependencies, or environment that is not validated or documented. Unvalidated assumptions that could cause runtime failures strengthen the finding's confidence.

### Change-intent awareness

For each unique file that has findings, check recent git history for deliberate changes:

```bash
git log --no-merges --format="%h %s" -5 -- <file>
```

If a recent commit message clearly indicates deliberate code introduction (e.g., "add dependency injection", "extract service layer") **and** a finding suggests removing or reverting that code → reduce the finding's confidence by one level (High → Medium, Medium → Low → drop).

For uninformative commit messages (fewer than 15 characters, or generic like "fix", "update", "changes"), run `git show <sha> -- <file>` to examine the actual diff for intent patterns: added abstractions, validation logic, or architectural changes. Apply the same confidence reduction if the diff shows deliberate structural code that a finding wants to undo.

Skip gracefully if `git log` fails or returns no results (e.g., shallow clone, newly created file, or file outside the repository).

### Confidence assignment

Assign confidence:
- **High** — clear issue with strong evidence → keep
- **Medium** — plausible issue, some evidence → keep with note
- **Low** — uncertain, likely false positive → drop

Only findings with High or Medium confidence proceed to Step 6.

## Step 6: Present Refactoring Plan

Merge validated findings from Steps 4–5. Deduplicate: if two agents flagged the same file and line range for the same category, keep the more detailed version. For findings flagged by both Agents 1 and 3, merge into one finding and note "confirmed by independent review".

### Contradiction resolution

After deduplication, check for **cross-agent contradictions** — findings that target the same code region but recommend opposite directions (e.g., "extract this to reduce duplication" vs. "inline this for clarity"). Keep the higher-severity finding and drop the other. When severities are equal, keep the finding that matches the active focus (testability or guidelines). When no focus is active, keep the testability finding — testability is a primary goal of this skill.

### Finding caps

Maximum **15 findings** per run — only include findings that represent distinct root causes with supporting evidence. Do NOT pad to reach the cap: a focused plan of 3 strong findings is preferred over 15 weak ones.

**When focus is active** (testability or guidelines):
- Reserve **12 slots** for the focused category, **3 slots** for other categories
- Within each slot group, prioritize by severity then confidence
- If the focused category has fewer than 12 findings, redistribute unused slots to other categories
- If other categories have fewer than 3 findings, redistribute unused slots to the focused category
- Category mapping:
  - `testability` focus: Testability Barrier findings + any finding with a "Testability impact" line → reserved slots. All others → other slots.
  - `guidelines` focus: Guideline Violation, Inconsistency, Duplication, Missing Abstraction, Architectural Drift, Code Quality findings → reserved slots. Testability Barrier findings → other slots.

**When no focus is active** (default balanced mode):
- Prioritize by severity then confidence across all categories (current behavior)

If more issues exist, note the count (e.g., "15 of ~24 findings shown") and suggest re-running with a narrower scope or `/optimus:refactor-deep`.

Present findings using the output format below, then proceed to Step 7.

### Output format

```
## Refactoring Plan

### Summary
- Scope: [full project / directory / changed since X]
- Focus: [testability / guidelines / balanced (default)]
- Areas analyzed: [N]
- Total findings: [N] shown (of ~[M] detected) — Critical: [N], Warning: [N], Suggestion: [N]
- Cross-cutting findings: [N]
- Testability improvements: [N] findings will make code testable for /optimus:unit-test
- Top recommendation: [one-sentence summary of highest-impact finding]

### Cross-Cutting Findings

**[N]. [Finding title]** (Critical/Warning/Suggestion)
- **Files:** `file1:line`, `file2:line`, ...
- **Category:** [Guideline Violation | Testability Barrier | Duplication | Inconsistency | Missing Abstraction | Architectural Drift]
- **Guideline:** [which project guideline this addresses]
- **Pattern:** [brief description of the cross-file issue]
- **Suggested:** [brief description of the fix approach]
- **Testability impact:** [what becomes testable after this refactoring — omit if not applicable]

### Findings by Area

#### [Area/Module Name] — [path]

**[N]. [Finding title]** (Critical/Warning/Suggestion)
- **File:** `file:line`
- **Category:** [Guideline Violation | Testability Barrier | Code Quality | Duplication | Inconsistency | Missing Abstraction | Architectural Drift]
- **Guideline:** [which project guideline this addresses]
- **Current:**
  ```
  [code sketch — max 5 lines]
  ```
- **Suggested:**
  ```
  [code sketch — max 5 lines]
  ```
- **Testability impact:** [what becomes testable after this refactoring — omit if not applicable]

### Areas with No Findings
- [Area name] — code follows project guidelines
```

Prioritize by severity:
- **Critical** — Testability barrier blocking unit testing, cross-cutting pattern, significant duplication, or SRP violation affecting readability/safety
- **Warning** — Guideline violation or consistency improvement in limited scope
- **Suggestion** — Minor clarity or hygiene item

Include "Areas with No Findings" to confirm coverage — the user should know those areas were reviewed, not skipped.

**No findings at all:**

Report as a positive result ("code follows project guidelines and is well-structured for testing"). Suggest tightening guidelines or broadening scope if the user expected issues. Skip Steps 7–8 and proceed directly to the recommendation in the Important section below.

## Step 7: Ask User How to Proceed

Use `AskUserQuestion` — header "Action", question "How would you like to proceed with the refactoring findings?":
- **Apply all** — "Apply every recommendation"
- **Selective** — "Choose specific finding numbers to apply"
- **Skip** — "No changes — keep the report as reference"

If the user selects **Selective**, ask which finding numbers to apply (e.g., "1, 3, 5"). Remember the user's choice and approved finding numbers for Step 8.

## Step 8: Apply Approved Changes and Verify

For each approved finding:
1. Apply the refactoring using Edit or MultiEdit
2. Verify the change matches the suggestion from Step 6

**Under harness mode (`HARNESS_MODE_INLINE`), skip this entire verify-and-revert step.** Apply the fixes, record the `pre_edit_content`/`post_edit_content` pairs, and emit the JSON — the orchestrator owns all test execution and bisection (see `$CLAUDE_PLUGIN_ROOT/references/harness-mode.md` §7). Do not run the test command or revert anything yourself.

Otherwise (interactive mode), after applying all approved changes, run the project's test command (from `.claude/CLAUDE.md`) if available. Follow the verification protocol from `$CLAUDE_PLUGIN_ROOT/skills/init/references/verification-protocol.md` — run tests fresh, read complete output, report actual results with evidence:
- If tests pass → report success.
- If tests fail → revert all changes, then re-apply one at a time with a test run after each. Keep changes that pass, skip those that fail.

If no test command is available, warn the user that changes were applied without automated verification and carry higher risk.

### Final summary

- Scope analyzed (from Step 1)
- Changes applied (with file references)
- Changes skipped (with reasons if selective)
- Test results (pass/fail/not available)
- Any changes reverted due to test failures
- Remaining findings not shown in this run (if cap was hit)
- Testability improvements: [N] changes will make code testable — run `/optimus:unit-test` to cover the restructured code

## Important

- Never modify files, commit, push, or post comments without explicit user approval — all changes remain as local modifications for the user to review with `git diff` before committing
- This skill is read-only by default — it only analyzes and reports
- When changes are too broad for effective analysis, recommend narrowing scope

After the refactoring is complete, recommend the next step based on the outcome:
- If issues were found and fixed → `/optimus:commit` to commit the fixes, then `/optimus:unit-test` to cover the restructured code
- If no issues or user skipped fixes → consider `/optimus:unit-test` directly if coverage needs improvement

Tell the user:

- If the recommendation above includes `/optimus:commit` (first bullet), the closing tip per `$CLAUDE_PLUGIN_ROOT/references/skill-handoff.md` "Closing tip wording" — use **Variant B** with `<continuation-skill(s)>` = `/optimus:commit` and `<non-continuation-examples>` = `/optimus:unit-test`, etc. Otherwise (second bullet — no issues / fixes skipped), use **Variant C** (default).
- **Tip:** Single-pass analysis can miss issues due to LLM attention limits. Run `/optimus:refactor-deep` to iterate automatically — it applies, tests, and repeats until clean (default 8 passes, hard cap 20). Requires a test command in `.claude/CLAUDE.md`.
