---
description: On-demand code review — run after /bootstrap:init, when code quality drifts, or for periodic cleanup. Analyzes the codebase against project coding guidelines, surfaces issues that span multiple files (duplication across modules, pattern inconsistency, architectural drift), and presents a simplification plan for approval before changes are applied.
disable-model-invocation: true
---

# Project-Wide Code Simplification

Analyze source code against the project's coding guidelines to find issues that span multiple files: duplication across modules, inconsistent patterns between areas, architectural drift, and dead code. Present a prioritized simplification plan, then apply only user-approved changes with test verification.

The code-simplifier agent guards new code after every edit — this skill is the on-demand complement for reviewing existing code across the project.

## Step 1: Verify Prerequisites and Determine Scope

Check that these files exist:
- `.claude/CLAUDE.md`
- `.claude/docs/coding-guidelines.md`

**If either is missing**, warn the user and recommend running `/bootstrap:init` first. Use these fallbacks so the skill can still run:
- `CLAUDE.md` missing → detect tech stack from manifest files (`package.json`, `Cargo.toml`, `pyproject.toml`, etc.) for basic context
- `coding-guidelines.md` missing → read `$CLAUDE_PLUGIN_ROOT/skills/init/templates/docs/coding-guidelines.md` as a generic baseline; inform the user that findings are based on generic guidelines, not project-specific ones
- Both missing → apply both fallbacks, strongly recommend `/bootstrap:init`

**Ask the user to choose a scope:**

| Scope | What gets analyzed | Best for |
|-------|-------------------|----------|
| **Full project** | All source directories | First run, periodic review |
| **Directory / module** | Specific path(s) the user provides | Targeted cleanup |
| **Changed since** | Files modified since a commit, tag, or date | Incremental review |

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

`/bootstrap:init` places docs differently in monorepos — `coding-guidelines.md` is shared at root, but `testing.md`, `styling.md`, and `architecture.md` are scoped per subproject:

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

- **Duplication across modules** — Repeated logic in different files/directories that could be consolidated (only when consolidation improves clarity)
- **Pattern inconsistency** — Code in one area that deviates from patterns established elsewhere in the same codebase (e.g., error handling done three different ways, inconsistent service layer patterns)
- **Architectural drift** — Code that has evolved away from the boundaries defined in `architecture.md` (e.g., direct DB access in a controller when the project uses a repository pattern)
- **Missing shared abstraction** — Multiple files working around the absence of a common utility or type that would clarify intent across the codebase

### Per-file analysis

These supplement cross-cutting findings with localized improvements:

- **Complexity** — Functions too long, deeply nested, or violating SRP
- **Naming** — Variables, functions, or types with unclear or misleading names
- **Dead code** — Unused functions, unreachable branches, commented-out blocks
- **Unnecessary abstraction** — Over-engineered patterns, premature generalizations
- **Comment quality** — Comments narrating what code expresses; missing comments on non-obvious intent

### Finding quality bar

Only surface findings that meet ALL of these criteria:
- Justified by a specific guideline from the project's docs (Step 2)
- Respects architectural boundaries, test conventions, and styling conventions
- The fix is concrete and demonstrable (not vague "consider refactoring")
- The improvement is meaningful enough that a reviewer would approve the change

When in doubt, don't flag it. Prefer small, safe changes over ambitious restructuring. Never change what the code does — only how it expresses it.

**Monorepo:** Apply each subproject's own constraint docs to its code. The shared `coding-guidelines.md` applies everywhere, but `testing.md`, `styling.md`, and `architecture.md` are subproject-scoped — don't apply backend testing conventions to frontend code or vice versa.

### Finding caps

Surface at most **12 findings per run** and **5 per area**, prioritized by impact. If more issues exist, note the count (e.g., "12 of ~25 findings shown") and suggest re-running with a narrower scope — e.g., `/bootstrap:simplify` "focus on src/auth" or "review only the api module".

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

Present three options:
- **Apply all** — apply every recommendation
- **Selective** — user specifies finding numbers to apply (e.g., "1, 3, 5")
- **Skip** — no changes; keep the report as reference

Remember the user's choice and approved finding numbers for Step 6.

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
