---
description: This skill analyzes the codebase against project coding guidelines as on-demand code simplification — run after /optimus:init, when code quality drifts, or for periodic cleanup. Surfaces issues that span multiple files (duplication across modules, pattern inconsistency, architectural drift) and presents a simplification plan for approval before changes are applied.
disable-model-invocation: true
---

# Project-Wide Code Simplification

Analyze source code against the project's coding guidelines to find issues that span multiple files: duplication across modules, inconsistent patterns between areas, architectural drift, and dead code. Present a prioritized simplification plan, then apply only user-approved changes with test verification.

The code-simplifier agent guards new code after every edit — this skill is the on-demand complement for reviewing existing code across the project.

## Step 1: Verify Prerequisites and Determine Scope

### Multi-repo workspace detection

If the current directory is a multi-repo workspace (no `.git/` at root, 2+ child directories containing a `.git` *directory* — not `.git` files, which indicate submodules), resolve prerequisites per-repo:
- Determine which repo(s) the scope targets (from file paths, user selection, or changed files)
- Load that repo's `.claude/CLAUDE.md` and `.claude/docs/` as prerequisites (not the workspace root)
- If scope spans multiple repos, load each repo's docs independently and apply per-repo context when analyzing that repo's files
- If no repo can be determined, ask the user which repo to analyze

### Prerequisite check

Check that these files exist:
- `.claude/CLAUDE.md` (or the target repo's `.claude/CLAUDE.md` in a multi-repo workspace)
- `.claude/docs/coding-guidelines.md` (or the target repo's)

**If either is missing**, warn the user and recommend running `/optimus:init` first. Use these fallbacks so the skill can still run:
- `CLAUDE.md` missing → detect tech stack from manifest files (`package.json`, `Cargo.toml`, `pyproject.toml`, etc.) for basic context
- `coding-guidelines.md` missing → read `$CLAUDE_PLUGIN_ROOT/skills/init/templates/docs/coding-guidelines.md` as a generic baseline; inform the user that findings are based on generic guidelines, not project-specific ones
- Both missing → apply both fallbacks, strongly recommend `/optimus:init`

Use `AskUserQuestion` to let the user choose a scope — header "Scope", question "What scope would you like to analyze?":
- **Full project** — "All source directories — best for first run or periodic review"
- **Directory** — "Specific path(s) — best for targeted cleanup"
- **Changed since** — "Files modified since a commit, tag, or date — incremental review"

Default to **full project** if the user just says "simplify" without specifying.

For **changed since**: use `git diff --name-only <ref>...HEAD` for commit SHAs, branch names, and tags. For relative dates, use `git log --since="2 weeks ago" --format= --name-only` instead (`--since` is a `git log` flag, not `git diff`). Filter to source files only (apply the exclusion rules from Step 2).

For monorepos with **full project** scope: ask which subprojects to include (default: all). For **directory** scope: auto-detect which subproject the path belongs to.

## Step 2: Load Project Context and Map Analysis Areas

### Load constraint docs

#### Single project

1. `.claude/CLAUDE.md` — project overview, conventions, tech stack, test commands
2. `.claude/docs/coding-guidelines.md` — coding standards (primary evaluation criteria)
3. `.claude/docs/testing.md` (if exists) — testing conventions, so simplifications don't break test patterns or established test helpers
4. `.claude/docs/architecture.md` (if exists) — architectural boundaries, so refactoring respects module structure and intended separation of concerns
5. `.claude/docs/styling.md` (if exists) — UI/CSS conventions, so frontend simplifications stay consistent

#### Monorepo

`/optimus:init` places docs differently in monorepos — `coding-guidelines.md` is shared at root, but `testing.md`, `styling.md`, and `architecture.md` are scoped per subproject:

1. `.claude/CLAUDE.md` — root overview, subproject table, workspace-level commands
2. `.claude/docs/coding-guidelines.md` — shared coding standards (applies to all subprojects)
3. For each subproject in scope:
   - `<subproject>/CLAUDE.md` — subproject-specific overview, commands, tech stack
   - `<subproject>/docs/testing.md` (if exists) — subproject-specific testing conventions
   - `<subproject>/docs/architecture.md` (if exists) — subproject-specific architecture
   - `<subproject>/docs/styling.md` (if exists) — subproject-specific UI/CSS conventions
4. For root-as-project: its scoped docs are in `.claude/docs/` alongside the shared `coding-guidelines.md`

When analyzing a subproject's code, apply its own constraint docs — not another subproject's. The shared `coding-guidelines.md` applies everywhere.

These files define the rules. Every suggestion must be justified by what these docs establish — never impose external preferences.

### Map analysis areas

Within the chosen scope (Step 1), identify source directories. Skip non-source:
- **Dot-directories**: `.git`, `.github`, `.vscode`, `.idea`, `.claude`, `.husky`
- **Dependencies**: `node_modules`, `vendor`, `.venv`, `venv`, `env`
- **Build output**: `dist`, `build`, `out`, `target`, `bin`, `obj`, `coverage`
- **Framework/cache**: `.next`, `.nuxt`, `__pycache__`, `.cache`, `.tox`, `.turbo`
- **Git submodules**: Any directory containing a `.git` *file* (not directory) — these belong to external repositories

Also skip non-source **file types**: `*.min.js`, `*.min.css`, lock files (`package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, etc.), `*.d.ts` (unless hand-written), binary and data files.

**Single project:** Group files by top-level source directory.
**Monorepo:** Organize by subproject, then by source directory within each.

### Prioritize by git activity

Rank directories by recent change frequency:

```bash
git log --since="3 months" --format= --name-only -- <scope-path> | sort | uniq -c | sort -rn
```

Analyze highest-churn directories first. For full-project scope on large codebases, start with the top 10 most active areas.

### Context Summary

Before proceeding to analysis, present a brief summary: docs loaded (with paths), docs missing (with fallback status), project type (single/monorepo), and analysis areas identified with their git activity rank. Let the user confirm before heavy analysis begins.

## Step 3: Analyze Source Code

For each area, evaluate source files against the constraints loaded in Step 2.

### Cross-cutting analysis (highest priority)

These findings span multiple files — the unique value of project-wide review that single-file analysis cannot provide:

- **Duplication across modules** — Repeated logic in different files/directories that could be consolidated (when consolidation improves clarity or reduces maintenance burden)
- **Pattern inconsistency** — Code in one area that deviates from patterns established elsewhere in the same codebase (e.g., error handling done three different ways, inconsistent service layer patterns)
- **Architectural drift** — Code that has evolved away from the boundaries defined in `architecture.md` (e.g., direct DB access in a controller when the project uses a repository pattern)
- **Missing shared abstraction** — Multiple files working around the absence of a common utility or type that would clarify intent across the codebase
- **Testability barriers** — Code with testable logic that cannot be unit-tested due to hardcoded dependencies or tight coupling, when the coding guidelines justify extraction

### Per-file analysis

These supplement cross-cutting findings with localized improvements. Apply each principle from the project's coding guidelines (loaded in Step 2) as an analysis lens — for each principle the guidelines establish, check whether the code follows it.

### Finding quality bar

Only surface findings that meet ALL of these criteria:
- Justified by a specific guideline from the project's docs (Step 2)
- Respects architectural boundaries, test conventions, and styling conventions
- The fix is concrete and demonstrable (not vague "consider refactoring")
- The improvement is meaningful enough that a reviewer would approve the change

When in doubt, don't flag it. Prefer well-justified, low-risk changes over speculative restructuring. Never change what the code does — only how it expresses it.

**Monorepo:** Apply each subproject's own constraint docs to its code. The shared `coding-guidelines.md` applies everywhere, but `testing.md`, `styling.md`, and `architecture.md` are subproject-scoped — don't apply backend testing conventions to frontend code or vice versa.

### Finding caps

Surface at most **12 findings per run** and **5 per area**, prioritized by impact. If more issues exist, note the count (e.g., "12 of ~25 findings shown") and suggest re-running with a narrower scope — e.g., `/optimus:simplify` "focus on src/auth" or "review only the api module".

## Step 4: Present Simplification Plan

Present findings as a structured report:

```
## Simplification Plan

### Summary
- Scope: [full project / directory / changed since X]
- Areas analyzed: [N]
- Total findings: [N] shown (of ~[M] detected) — High: [N], Medium: [N], Low: [N]
- Cross-cutting findings: [N]
- Top recommendation: [one-sentence summary of highest-impact finding]

### Cross-Cutting Findings

**[N]. [Finding title]** (High/Medium/Low)
- **Files:** `file1:line`, `file2:line`, ...
- **Guideline:** [which project guideline this addresses]
- **Pattern:** [brief description of the cross-file issue]
- **Suggested:** [brief description of the fix approach]

### Findings by Area

#### [Area/Module Name] — [path]

**[N]. [Finding title]** (High/Medium/Low)
- **File:** `file:line`
- **Guideline:** [which project guideline this addresses]
- **Current:**
  ```
  [code sketch — max 5 lines]
  ```
- **Suggested:**
  ```
  [code sketch — max 5 lines]
  ```

### Areas with No Findings
- [Area name] — code follows project guidelines
```

Prioritize by impact:
- **High** — Cross-cutting pattern, significant duplication, or SRP violation affecting readability/safety
- **Medium** — Clarity/consistency improvement in limited scope
- **Low** — Minor style or hygiene item

Include "Areas with No Findings" to confirm coverage — the user should know those areas were reviewed, not skipped.

**No findings at all:** Report as a positive result ("code follows project guidelines"). Suggest tightening guidelines or broadening scope if the user expected issues.

## Step 5: Ask User How to Proceed

Use `AskUserQuestion` — header "Action", question "How would you like to proceed with the simplification findings?":
- **Apply all** — "Apply every recommendation"
- **Selective** — "Choose specific finding numbers to apply"
- **Skip** — "No changes — keep the report as reference"

If the user selects **Selective**, ask which finding numbers to apply (e.g., "1, 3, 5"). Remember the user's choice and approved finding numbers for Step 6.

## Step 6: Apply Approved Changes and Report

For each approved finding:
1. Apply the simplification using Edit or MultiEdit
2. Verify the change matches the suggestion from Step 4

After applying all approved changes, run the project's test command (from `.claude/CLAUDE.md`) if available:
- If tests pass → report success
- If tests fail → revert all changes, then re-apply one at a time with a test run after each. Keep changes that pass, skip those that fail, and record each failure as "reverted due to test failure"

If no test command is available, warn the user that changes were applied without automated verification and carry higher risk.

### Final summary

- Scope analyzed (from Step 1)
- Changes applied (with file references)
- Changes skipped (with reasons if selective)
- Test results (pass/fail/not available)
- Any changes reverted due to test failures
- Remaining findings not shown in this run (if cap was hit)
