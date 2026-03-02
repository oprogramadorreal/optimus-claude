---
description: Local-first code review — analyzes uncommitted changes (or PRs) against project coding guidelines using up to 6 parallel review agents (bug detection, security/logic, guideline compliance ×2, code simplification, test coverage). HIGH SIGNAL only: real bugs, logic errors, security concerns, and guideline violations.
disable-model-invocation: true
---

# Code Review

Analyze local git changes (or a PR) against the project's coding guidelines, using up to 6 parallel review agents for comprehensive coverage. High-signal findings only: bugs, logic errors, security issues, guideline violations. Excludes style concerns, subjective suggestions, and linter-catchable issues.

## Step 1: Determine Review Scope

Parse arguments and detect what to review.

### Local changes (default — no arguments)

Run the following git commands to gather all local changes:

```bash
# Staged changes
git diff --cached --stat
git diff --cached

# Unstaged changes to tracked files
git diff --stat
git diff

# Untracked files
git status --short
```

- **If local changes found** → review them (staged + unstaged + untracked)
- **If no local changes** → check for commits ahead of the default branch:
  - Run `git log --oneline origin/main..HEAD` (try `main`, then `master` if no remote)
  - If commits found → offer to review the branch diff
  - Also check for a PR: `gh pr view --json number,state,title` (ignore errors if `gh` is not installed)
  - If PR found → offer to review it
- **If nothing at all** → inform the user there are no changes to review and suggest staging changes or specifying a PR

### PR mode (explicit request)

When the user says "review PR #42", passes `--pr`, `#123`, or a PR URL:
- Verify `gh` is available by running `gh --version`. If not available, inform the user that PR review requires the GitHub CLI and offer to review the branch diff instead
- Use `gh pr view <N> --json state,isDraft,title,body,baseRefName,headRefName` to get PR metadata
- Use `gh pr diff <N>` to get the actual diff
- If the PR is closed or merged → warn and stop

### Branch/ref mode

When the user says "review changes since main" or a similar reference:
- Use `git diff <ref>...HEAD` for the diff
- Use `git diff --name-only <ref>...HEAD` for the file list

### Path filter

When the user specifies a path (e.g., "review src/auth"):
- Filter local changes to that path using `git diff -- <path>` and `git diff --cached -- <path>`

### Scope summary

Present a brief summary before proceeding:

```
## Review Scope
- Mode: Local changes / PR #N / Branch diff since <ref>
- Files changed: [N]
- Lines: +[added] / -[removed]
```

### Large diff warning

If more than 50 files or 3000 lines are changed, warn the user and suggest narrowing the scope (e.g., specific path or directory).

## Step 2: Verify Prerequisites and Load Project Context

### Documentation prerequisites

Check that these files exist:
- `.claude/CLAUDE.md`
- `.claude/docs/coding-guidelines.md`

**If either is missing**, warn the user and recommend running `/prime:init` first. Use these fallbacks so the skill can still run:
- `CLAUDE.md` missing → detect tech stack from manifest files (`package.json`, `Cargo.toml`, `pyproject.toml`, etc.) for basic context
- `coding-guidelines.md` missing → read `$CLAUDE_PLUGIN_ROOT/skills/init/templates/docs/coding-guidelines.md` as a generic baseline; inform the user that findings are based on generic guidelines, not project-specific ones
- Both missing → apply both fallbacks, strongly recommend `/prime:init`

### Agent prerequisites

Check that these files exist:
- `.claude/agents/code-simplifier.md`
- `.claude/agents/test-guardian.md`

**If either is missing**, warn the user and recommend running `/prime:init` to install them. Use these fallbacks so the skill can still run:
- `code-simplifier.md` missing → Agent 5 (Code Simplifier) will be skipped in Step 3; the review still covers bugs, security, and guidelines via Agents 1–4
- `test-guardian.md` missing → Agent 6 (Test Guardian) will be skipped in Step 3; test coverage gaps will not be analyzed
- Both missing → both agents skipped; only Agents 1–4 run (still provides bug, security, and guideline coverage); strongly recommend `/prime:init` for full 6-agent review

### Load constraint docs

#### Single project

1. `.claude/CLAUDE.md` — project overview, conventions, tech stack, test commands
2. `.claude/docs/coding-guidelines.md` — coding standards (primary evaluation criteria)
3. `.claude/docs/testing.md` (if exists) — testing conventions
4. `.claude/docs/architecture.md` (if exists) — architectural boundaries
5. `.claude/docs/styling.md` (if exists) — UI/CSS conventions

#### Monorepo

`/prime:init` places docs differently in monorepos — `coding-guidelines.md` is shared at root, but `testing.md`, `styling.md`, and `architecture.md` are scoped per subproject:

1. `.claude/CLAUDE.md` — root overview, subproject table, workspace-level commands
2. `.claude/docs/coding-guidelines.md` — shared coding standards (applies to ALL subprojects)
3. For each subproject with changed files:
   - `<subproject>/CLAUDE.md` — subproject-specific overview, commands, tech stack
   - `<subproject>/docs/testing.md` (if exists) — subproject-specific testing conventions
   - `<subproject>/docs/architecture.md` (if exists) — subproject-specific architecture
   - `<subproject>/docs/styling.md` (if exists) — subproject-specific UI/CSS conventions
4. For root-as-project: its scoped docs are in `.claude/docs/` alongside the shared `coding-guidelines.md`

When reviewing a subproject's code, apply its own constraint docs — not another subproject's. The shared `coding-guidelines.md` applies everywhere.

These files define the review criteria. Every guideline-related finding must be justified by what these docs establish — never impose external preferences.

### Context summary

Before proceeding to the review, present a brief summary:
- Docs loaded (with paths)
- Docs missing (with fallback status)
- Agents available (with skip status for missing ones)
- Project type (single project / monorepo)

Let the user confirm before launching agents.

## Step 3: Parallel Multi-Agent Review (up to 6 agents)

4 core review agents + 2 project-level agents, all launched in parallel for maximum coverage.

Launch up to 6 `general-purpose` Agent tool calls simultaneously. Agents 1–4 always run; Agents 5–6 only run if the corresponding project agent file exists (checked in Step 2).

Each agent receives the list of changed file paths from Step 1.

Read `$CLAUDE_PLUGIN_ROOT/skills/code-review/references/agent-prompts.md` for the full prompt templates, quality bar, exclusion rules, and false positive guidance for all 6 agents.

### Agent overview

| Agent | Role | Runs when |
|-------|------|-----------|
| 1 — Bug Detector | Null access, off-by-one, race conditions, resource leaks, type mismatches | Always |
| 2 — Security & Logic | SQL injection, XSS, hardcoded secrets, missing auth, API contract violations | Always |
| 3 — Guideline Compliance A | Explicit violations of project docs with exact rule citations | Always |
| 4 — Guideline Compliance B | Same task as Agent 3 — independent review reduces false negatives | Always |
| 5 — Code Simplifier | Unnecessary complexity, naming, dead code, pattern violations | `.claude/agents/code-simplifier.md` exists |
| 6 — Test Guardian | Test coverage gaps, structural barriers to testability | `.claude/agents/test-guardian.md` exists |

Each agent: max 5 findings, structured list format. Guideline agents (3–4) are constructed dynamically based on Step 2's doc loading results (single project vs monorepo paths).

### Execution

Launch all available agents simultaneously (parallel, not sequential). Wait for all launched agents to complete before proceeding to Step 4.

**Agent availability summary**: Agents 1–4 always run (no project dependencies). Agents 5–6 depend on installed project agents. If neither project agent exists, note in the summary and recommend `/prime:init` for full 6-agent review.

## Step 4: Validate Findings

Independently verify each finding to filter false positives.

For each finding from Step 3:
1. **Context check** — read ±30 lines around the flagged location to verify the issue exists in context
2. **Intent check** — look for comments, test assertions, or established patterns that explain the code's behavior (what looks like a bug may be intentional)
3. **Pre-existing check** — verify the issue was introduced by the changes, not pre-existing in unchanged code
4. **Cross-agent consensus** — for guideline findings, check if both Agents 3 and 4 flagged the same issue (consensus = higher confidence)

Assign confidence:
- **High** — clear issue with strong evidence → keep
- **Medium** — plausible issue, some evidence → keep with note
- **Low** — uncertain, likely false positive → drop

Only findings with High or Medium confidence proceed to Step 5.

## Step 5: Consolidate and Present Findings

Merge validated findings from Steps 3–4. Deduplicate: if two agents flagged the same file and line range for the same category, keep the more detailed version. For guideline findings flagged by both Agents 3 and 4, merge into one finding and note "confirmed by independent review".

### Severity

- **Critical** — Bugs, security vulnerabilities, runtime failures
- **Warning** — Guideline violations, missing error handling, test coverage gaps for critical paths
- **Suggestion** — Code quality improvements, minor guideline drift, test coverage gaps for non-critical paths

### Finding cap

Maximum **10 findings** across all sources, prioritized by severity then confidence. If more issues exist, note the count (e.g., "10 of ~18 findings shown") and suggest re-running with a narrower scope — e.g., `/prime:code-review` "focus on src/auth".

### Output format

```
## Code Review

### Summary
- Scope: [local changes / PR #N / branch diff since X]
- Files reviewed: [N]
- Lines changed: +[A] / -[R]
- Findings: [N] (Critical: [N], Warning: [N], Suggestion: [N])
- Docs used: [list of docs loaded]
- Agents: bug-detector, security-reviewer, guideline-A, guideline-B[, code-simplifier][, test-guardian]
- Verdict: CHANGES LOOK GOOD / ISSUES FOUND

### Findings

**[N]. [Finding title]** (Critical/Warning/Suggestion — [Bug/Security/Guideline/Quality/Test Gap])
- **File:** `file:line`
- **Category:** [Bug | Security | Guideline Violation | Code Quality | Test Coverage Gap]
- **Guideline:** [which project guideline, or "General: bug/security"]
- **Issue:** [concrete description]
- **Current:**
  ```
  [code snippet — max 5 lines]
  ```
- **Suggested:**
  ```
  [fix or recommendation — max 5 lines]
  ```

[Findings ordered: Critical → Warning → Suggestion, each sorted by file path]

### No Issues Found
[If applicable: "The changes follow project guidelines. No bugs, security issues, or guideline violations detected."]
```

For PR mode, include full-SHA code links: `https://github.com/owner/repo/blob/[full-sha]/path#L[start]-L[end]`

## Step 6: Offer Actions

Present options based on review mode:

**Local changes / branch diff**:
- **Fix issues** — apply suggested fixes directly (Edit tool). After applying, run the project's test command (from `.claude/CLAUDE.md`) if available to verify nothing broke
- **Skip** — keep the report as reference

**PR review**:
- **Post comment** — post the review summary as a PR comment (`gh pr comment <N> --body "..."`)
- **Skip** — keep the report as reference only

## Important

- Never modify files, commit, push, or post comments without explicit user approval
- This skill is read-only by default — it only analyzes and reports
- When changes are too broad for effective review, recommend narrowing scope
