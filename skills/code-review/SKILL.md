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

**If either is missing**, warn the user and recommend running `/bootstrap:init` first. Use these fallbacks so the skill can still run:
- `CLAUDE.md` missing → detect tech stack from manifest files (`package.json`, `Cargo.toml`, `pyproject.toml`, etc.) for basic context
- `coding-guidelines.md` missing → read `$CLAUDE_PLUGIN_ROOT/skills/init/templates/docs/coding-guidelines.md` as a generic baseline; inform the user that findings are based on generic guidelines, not project-specific ones
- Both missing → apply both fallbacks, strongly recommend `/bootstrap:init`

### Agent prerequisites

Check that these files exist:
- `.claude/agents/code-simplifier.md`
- `.claude/agents/test-guardian.md`

**If either is missing**, warn the user and recommend running `/bootstrap:init` to install them. Use these fallbacks so the skill can still run:
- `code-simplifier.md` missing → Agent 5 (Code Simplifier) will be skipped in Step 3; the review still covers bugs, security, and guidelines via Agents 1–4
- `test-guardian.md` missing → Agent 6 (Test Guardian) will be skipped in Step 3; test coverage gaps will not be analyzed
- Both missing → both agents skipped; only Agents 1–4 run (still provides bug, security, and guideline coverage); strongly recommend `/bootstrap:init` for full 6-agent review

### Load constraint docs

#### Single project

1. `.claude/CLAUDE.md` — project overview, conventions, tech stack, test commands
2. `.claude/docs/coding-guidelines.md` — coding standards (primary evaluation criteria)
3. `.claude/docs/testing.md` (if exists) — testing conventions
4. `.claude/docs/architecture.md` (if exists) — architectural boundaries
5. `.claude/docs/styling.md` (if exists) — UI/CSS conventions

#### Monorepo

`/bootstrap:init` places docs differently in monorepos — `coding-guidelines.md` is shared at root, but `testing.md`, `styling.md`, and `architecture.md` are scoped per subproject:

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

### Quality bar (all agents must follow)

- Every finding must have real impact, not be a nitpick
- Be specific and actionable (not vague "consider refactoring")
- Be high confidence
- Not be pre-existing (in unchanged code)

### All agents exclude

- Style/formatting concerns (linters handle these)
- Subjective suggestions ("I would prefer...")
- Performance micro-optimizations without clear impact
- Input-dependent issues
- Uncertain findings
- Pre-existing issues in unchanged code (unless security/bug directly adjacent to changed lines)

### False positives to avoid

- Pre-existing issues not introduced by the changes
- Apparently incorrect but actually correct code (intentional deviations)
- Pedantic nitpicks
- Linter-catchable issues
- General code quality concerns not tied to project guidelines
- Issues explicitly silenced in code (e.g., `// eslint-disable`, `# noqa`)

---

### Agent 1 — Bug Detector (always runs)

```
You are a bug detection specialist reviewing code changes.

Read `.claude/CLAUDE.md` for project context.

Review ONLY the diff/changed sections of these files:
[list of changed file paths from Step 1]

Focus exclusively on:
- Null/undefined access without checks
- Off-by-one errors
- Race conditions in async code
- Missing error handling on fallible operations
- Incorrect boolean logic (inverted conditions, missing edge cases)
- Resource leaks (unclosed handles, missing cleanup)
- Type mismatches and incorrect API usage
- Compilation/parse failures, syntax errors, missing imports

For each finding report: file:line, category (Bug/Logic Error), description, code snippet, suggested fix.
Do NOT flag style, guidelines, security, or test coverage — other agents handle those.
Maximum 5 findings. Report as a structured list.
```

### Agent 2 — Security & Logic Reviewer (always runs)

```
You are a security and logic reviewer analyzing code changes.

Read `.claude/CLAUDE.md` for project context.

Review ONLY the diff/changed sections of these files:
[list of changed file paths from Step 1]

Focus exclusively on:
- SQL injection, XSS, path traversal
- Hardcoded secrets or credentials
- Missing input validation on trust boundaries
- Unsafe deserialization
- Missing authentication/authorization checks
- Data integrity issues
- API contract violations
- Error propagation that hides failures

For each finding report: file:line, category (Security/Logic), severity, description, code snippet, suggested fix.
Do NOT flag bugs (Agent 1 handles that), guidelines (Agents 3–4), or code quality/test gaps (Agents 5–6).
Maximum 5 findings. Report as a structured list.
```

### Agent 3 — Guideline Compliance Reviewer A (always runs)
### Agent 4 — Guideline Compliance Reviewer B (always runs)

Both agents receive the **same task** — independent review reduces false negatives.

**Construct these prompts dynamically** based on Step 2's doc loading results. The doc paths differ between single projects and monorepos:

- **Single project**: include `.claude/CLAUDE.md`, `.claude/docs/coding-guidelines.md`, and any existing `.claude/docs/{architecture,testing,styling}.md`
- **Monorepo**: include `.claude/CLAUDE.md`, `.claude/docs/coding-guidelines.md` (shared), plus for each subproject with changed files: `<subproject>/CLAUDE.md`, `<subproject>/docs/{testing,architecture,styling}.md` (if they exist). Add this instruction: "When reviewing files in `<subproject>`, apply that subproject's own docs. The shared `coding-guidelines.md` applies to all subprojects. Do NOT apply one subproject's `testing.md` or `styling.md` to another subproject's code."

```
You are a guideline compliance reviewer.

Read these project docs for review criteria:
[list of doc paths from Step 2 — dynamically constructed based on project type]

Review ONLY the diff/changed sections of these files:
[list of changed file paths from Step 1]

[For monorepos: "When reviewing files in <subproject>, apply that subproject's own docs. The shared coding-guidelines.md applies to all subprojects. Do NOT apply one subproject's testing.md or styling.md to another subproject's code."]

Focus exclusively on:
- Explicit violations of rules in the loaded project docs
- Patterns that contradict architecture.md boundaries
- Testing convention violations per testing.md
- Styling convention violations per styling.md
- Unambiguous guideline violations with EXACT rule citations

Every finding MUST cite the specific rule from the project docs.
Do NOT flag bugs/logic/security (Agents 1–2 handle those) or code quality/test gaps (Agents 5–6).
Maximum 5 findings. Report as a structured list with exact rule citations.
```

### Agent 5 — Code Simplifier (only if `.claude/agents/code-simplifier.md` exists)

```
Read `.claude/agents/code-simplifier.md` for your role and approach.
Read `.claude/docs/coding-guidelines.md` and `.claude/CLAUDE.md` for project standards.

Review ONLY the following changed files for code simplification opportunities:
[list of changed file paths from Step 1]

Focus on: unnecessary complexity, naming clarity, violations of codebase patterns, dead code, misleading comments.

For each finding: file:line, guideline violated, brief description, suggested improvement.
Do NOT suggest changes outside the changed files. Do NOT flag style/formatting, bugs, security, or guidelines.
Maximum 5 findings. Report as a structured list.
```

### Agent 6 — Test Guardian (only if `.claude/agents/test-guardian.md` exists)

```
Read `.claude/agents/test-guardian.md` for your role and approach.
Read `.claude/CLAUDE.md` for project structure, then read the relevant testing.md.

Analyze ONLY the following changed files for test coverage gaps:
[list of changed file paths from Step 1]

Focus on: new public functions/methods/classes without tests, modified logic paths existing tests may not cover, test files that should have been updated alongside changes.

For each finding: source file and function name, what should be tested, recommended test file path.
Do NOT write test code. Only identify gaps.
Maximum 5 findings. Report as a structured list.
```

### Execution

Launch all available agents simultaneously (parallel, not sequential). Wait for all launched agents to complete before proceeding to Step 4.

**Agent availability summary**: Agents 1–4 always run (no project dependencies). Agents 5–6 depend on installed project agents. If neither project agent exists, note in the summary and recommend `/bootstrap:init` for full 6-agent review.

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

Maximum **10 findings** across all sources, prioritized by severity then confidence. If more issues exist, note the count (e.g., "10 of ~18 findings shown") and suggest re-running with a narrower scope — e.g., `/bootstrap:code-review` "focus on src/auth".

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
