---
description: This skill verifies a feature branch in an isolated sandbox — extracts the test plan from the PR, generates verification items from the branch diff, creates a git worktree sandbox, runs automated checks, launches parallel agents for functional verification, and reports results. Never pushes to remote.
disable-model-invocation: true
---

# Verify Feature Branch

Prove that a feature branch works as described. Extract or generate a verification plan, create an isolated sandbox (git worktree), run automated checks and functional verifications, report results. All work happens inside the sandbox — the main workspace and remote repository are never modified.

This skill complements `/optimus:code-review` (static analysis) by adding dynamic execution — it actually runs the code to confirm behavioral claims.

## Step 1: Pre-flight

Read `$CLAUDE_PLUGIN_ROOT/skills/init/references/multi-repo-detection.md` for workspace detection. If a multi-repo workspace is detected, process each repo independently: run Steps 1–9 inside the repo the user is targeting. If ambiguous, ask which repo.

### Verify branch state

1. Confirm the current directory is inside a git repository
2. Detect the default branch: check `origin/main`, then `origin/master`, then `git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's|refs/remotes/origin/||'`
3. Get the current branch: `git rev-parse --abbrev-ref HEAD`
4. **If on the default branch** — stop and explain:

```
## Not on a feature branch

/optimus:verify validates feature branches against their test plan in an isolated sandbox.

**Usage:** Switch to a feature branch and run `/optimus:verify`.

**What it does:**
1. Extracts the test plan from the PR description (or generates one from the branch diff)
2. Creates an isolated sandbox (git worktree)
3. Runs automated checks (tests, build, lint, type-check)
4. Launches parallel agents for functional verification
5. Reports results and offers to fix issues

**When to use:** After development, before or alongside `/optimus:code-review`.
```

5. Check for commits ahead of the target branch: `git log --oneline <default-branch>..HEAD`
   - If no commits ahead → stop: "Branch has no changes to verify. Commit your changes first."
6. Check for dirty working tree: `git status --short`
   - If uncommitted changes → warn: "Uncommitted changes detected. They will not be included in sandbox verification. Consider committing or stashing first." Proceed after warning.

### Load project context

Load these documents (same fallback pattern as `/optimus:code-review`):

| Document | Role | Fallback if missing |
|----------|------|---------------------|
| `.claude/CLAUDE.md` | Project overview, tech stack, commands | Detect tech stack from manifests |
| `coding-guidelines.md` | Quality criteria for agents | Read `$CLAUDE_PLUGIN_ROOT/skills/init/templates/docs/coding-guidelines.md` as generic baseline |
| `testing.md` | Testing conventions, framework, runner | Detect test runner from manifests |

**Monorepo path note:** `coding-guidelines.md` is shared at root (`.claude/docs/coding-guidelines.md`). `testing.md` is scoped per subproject (`<subproject>/docs/testing.md`).

If both `CLAUDE.md` and `coding-guidelines.md` are missing, warn and recommend `/optimus:init`.

### Detect commands

Locate these commands from `testing.md`, `CLAUDE.md`, or project manifests (`package.json` scripts, `Makefile`, `Cargo.toml`, `pyproject.toml`, etc.):

- **Test runner** — the command to run the test suite
- **Build** — the command to compile/build the project
- **Lint** — the linter command
- **Type-check** — the type checker command (e.g., `tsc --noEmit`, `cargo check`, `go vet`, `mypy`)

Record which commands are available — unavailable commands will be skipped in Step 4.

### Pre-flight summary

```
## Pre-flight

- Branch: `<current-branch>` (target: `<default-branch>`)
- Commits ahead: [N]
- Tech stack: [detected stack]
- Commands: test ✓/✗, build ✓/✗, lint ✓/✗, type-check ✓/✗
- Docs: CLAUDE.md ✓/✗, coding-guidelines.md ✓/✗, testing.md ✓/✗
```

## Step 2: Gather Verification Plan

### Check for PR/MR

Read `$CLAUDE_PLUGIN_ROOT/skills/pr/references/platform-detection.md` and use the **Platform Detection Algorithm** to determine the hosting platform. Then check for an existing PR/MR:

**GitHub** (if `gh` is available):
- `gh pr view --json number,state,title,body,baseRefName,headRefName`
- If found and open → extract PR metadata (number, title, body, base branch)
- If found but closed/merged → warn, proceed without PR data
- If `gh` not available or not authenticated → skip PR extraction, proceed with diff-only

**GitLab** (if `glab` is available):
- `glab mr view --output json`
- Same logic as above

If a PR/MR exists, use its `baseRefName`/target branch instead of the default branch for diff comparison (the PR target may differ from the default branch).

### Extract or generate test plan

Read `$CLAUDE_PLUGIN_ROOT/skills/verify/references/test-plan-extraction.md` for the full extraction and generation algorithm.

1. **If PR/MR found with `## Test plan` section** → extract items and classify as Automated/Functional/Manual
2. **Always generate diff-based items:**
   - `git diff --stat <target-branch>...HEAD` — file overview
   - `git diff <target-branch>...HEAD` — full diff
   - `git log --oneline <target-branch>..HEAD` — commit history
   - Apply the generation algorithm from the reference doc
3. **Merge** PR items with diff-derived items (PR items take priority, generated items fill gaps)
4. **Always include standard Automated checks** (test, build, lint, type-check) if commands were found in Step 1

### Present Verification Plan

```
## Verification Plan

### Automated Checks
- [ ] **Test suite** — Run `<test-command>` — all tests pass
- [ ] **Build** — Run `<build-command>` — exits cleanly
- [ ] **Lint** — Run `<lint-command>` — 0 errors
- [ ] **Type-check** — Run `<type-check-command>` — 0 errors

### Functional Checks
- [ ] **[behavior description]** — Method: [test / mock-project / integration / trace]
  [source: PR test plan | Generated from diff]
- [ ] ...

### Manual Checks (requires human judgment)
- [ ] **[description]** — [why it requires manual verification]
- [ ] ...

Source: [PR #N test plan + diff analysis | Diff analysis only (no PR found)]
```

Use `AskUserQuestion` — header "Verification plan", question "Review the plan. Adjust, approve, or add items?":
- **Approve** — "Plan looks good — start verification"
- **Adjust** — "I want to modify the plan before starting"
- **Add items** — "I want to add verification steps"

## Step 3: Create Sandbox

Create a git worktree for isolated verification. This keeps all verification work (test files, mock projects, dependency installs) separate from the main workspace.

### Worktree setup

1. Derive worktree directory name: replace `/` with `-` in the branch name (e.g., `feature/auth` → `verify-feature-auth`)
2. Check if `.worktrees/` exists — if not, create it: `mkdir -p .worktrees`
3. Ensure `.worktrees/` is gitignored: check if `.gitignore` contains `.worktrees/` or `.worktrees`. If not, append `.worktrees/` to `.gitignore` and stage it: `echo '.worktrees/' >> .gitignore && git add .gitignore`
4. Check if `.worktrees/verify-<slug>` already exists (from a previous run):
   - If exists → use `AskUserQuestion` — header "Existing sandbox", question "A sandbox from a previous run exists at `.worktrees/verify-<slug>`. Reuse it or start fresh?":
     - **Reuse** — "Use the existing sandbox (faster — dependencies already installed)"
     - **Fresh** — "Remove and recreate (clean start)"
   - If "Fresh" → remove: `git worktree remove --force .worktrees/verify-<slug>`
5. Create worktree: `git worktree add .worktrees/verify-<slug> <current-branch>`

### Install dependencies

Run project setup inside the worktree (detect from `CLAUDE.md` or manifests):

| Stack | Install command |
|-------|----------------|
| Node.js | `npm install` / `pnpm install` / `yarn install` / `bun install` (match project's lock file) |
| Python | `pip install -e .` / `poetry install` / `uv sync` (match project's lock file) |
| Rust | `cargo build` |
| Go | `go mod download` |
| C#/.NET | `dotnet restore` |
| Java (Maven) | `mvn install -DskipTests` |
| Java (Gradle) | `gradle build -x test` |
| C/C++ | `cmake -B build && cmake --build build` (or project-specific) |

### Verify sandbox

Run the test suite inside the worktree as a baseline:
- **Tests pass** → sandbox is functional, record baseline results
- **Tests fail** → record failures as **pre-existing** (these are not caused by the feature branch). Note them for comparison in Step 4
- **Build fails** → this is a significant finding — record and continue with what is possible

### Worktree fallback

If `git worktree add` fails (git version < 2.15, filesystem issues, etc.):
1. Warn the user: "Git worktree creation failed. Falling back to running verification directly on the current branch. Verification tests and mock projects will be created in the working tree."
2. Create a temporary directory for verification artifacts: `mkdir -p .verify-sandbox`
3. Ensure `.verify-sandbox/` is gitignored
4. Proceed with Steps 4–9 using the current working directory instead of the worktree

Report:

```
## Sandbox

- Path: `.worktrees/verify-<slug>` [or fallback path]
- Dependencies: installed ✓/✗
- Baseline tests: [N] passed, [N] failed (pre-existing), [N] total
- Build: ✓/✗
```

## Step 4: Automated Verification

For each **Automated** item in the Verification Plan, run the corresponding command inside the sandbox. Follow the verification protocol from `$CLAUDE_PLUGIN_ROOT/skills/init/references/verification-protocol.md` for every command: identify, run, read, verify, claim.

### Standard checks

Run each available command inside the sandbox directory:

1. **Test suite** — run the test command, capture exit code, pass/fail counts, and any failure details
2. **Build** — run the build command, capture exit code and any errors
3. **Lint** — run the lint command, capture error/warning counts
4. **Type-check** — run the type-check command, capture errors

### Pre-existing failure detection

For test failures, distinguish between pre-existing and branch-introduced failures:
- Compare the sandbox baseline (from Step 3) with the current results
- If a test that failed in the baseline still fails → mark as **pre-existing** (not a finding)
- If a test that passed in the baseline now fails → mark as **branch-introduced** (this is a finding)
- If a new test (not in baseline) fails → mark as **branch-introduced**

### Record results

For each Automated check, record:
- **Status**: PASS / FAIL / SKIPPED (command not available)
- **Evidence**: exit code, pass/fail counts, specific error messages
- **Pre-existing**: whether failures existed before the branch

Do NOT fix anything in this step — it is strictly read-only observation.

```
## Automated Verification

| Check | Status | Evidence |
|-------|--------|----------|
| Test suite | PASS (47/47) | Exit code 0 |
| Build | PASS | Exit code 0, no warnings |
| Lint | FAIL (2 errors) | src/auth.ts:15 missing semicolon, src/auth.ts:22 unused import |
| Type-check | PASS | Exit code 0 |
```

## Step 5: Functional Verification (parallel agents)

For each **Functional** item in the Verification Plan, determine the best verification method and assign it to a specialized agent.

### Item assignment

Assign each Functional item to one of 4 agent types based on the verification method:

| Method | Agent | Use when |
|--------|-------|----------|
| Write verification test | Test Writer (Agent 1) | The behavior can be tested by a unit/integration test within the project's test framework |
| Integration scenario | Integration Verifier (Agent 2) | The behavior involves API endpoints, servers, CLI commands, or multi-component interaction |
| Mock consumer project | Mock Project Verifier (Agent 3) | The behavior is about a library/API/plugin consumed externally — read `$CLAUDE_PLUGIN_ROOT/skills/verify/references/mock-project-scaffolds.md` for detection heuristics |
| Code path tracing | Behavior Tracer (Agent 4) | The behavior is about internal logic, edge cases, or error handling that can be verified by reading/tracing code |

Distribute items across agents to maximize parallelism. If only 1-2 Functional items exist, launch only the needed agents (do not launch 4 agents for 1 item).

### Launch parallel agents

Read `$CLAUDE_PLUGIN_ROOT/skills/verify/references/agent-prompts.md` for the full prompt templates.

Launch up to 4 `general-purpose` Agent tool calls simultaneously — one per agent type that has assigned items. Each agent receives:
- The sandbox worktree path
- Its assigned Verification Plan items
- Project context (tech stack, test framework, conventions)

Wait for all launched agents to complete before proceeding to Step 6.

### Collect results

After all agents complete, consolidate their results. Apply the verification protocol: treat agent-reported results as claims and spot-check any surprising outcomes (e.g., an unexpected PASS on a behavior that seemed broken from the diff, or a FAIL with vague evidence).

## Step 6: Handle Limitations

For each **Manual** item in the Verification Plan, present it to the user for verification.

Use `AskUserQuestion` — header "Manual verification", question "[description of what needs human judgment]":
- **Verified** — "I've confirmed this works"
- **Failed** — "This doesn't work — describe what's wrong"
- **Skip** — "Can't verify right now"

For any Functional item that agents reported as **BLOCKED** (e.g., requires external services, credentials, hardware access), present the same AskUserQuestion pattern. Explain why automation failed and what the user can do to verify it manually.

Record all manual verification results.

## Step 7: Compile Report

Consolidate all results from Steps 4–6 into a structured report:

```
## Verification Report

### Summary
- Branch: `<branch-name>` (target: `<target-branch>`)
- PR/MR: #N [URL] (or "No PR/MR found")
- Sandbox: `.worktrees/verify-<slug>`
- Verdict: ALL PASSED | ISSUES FOUND | PARTIAL (manual items pending)

### Automated Verification
| Check | Status | Evidence |
|-------|--------|----------|
| Test suite | [status] | [evidence] |
| Build | [status] | [evidence] |
| Lint | [status] | [evidence] |
| Type-check | [status] | [evidence] |

### Functional Verification
| # | Item | Method | Status | Evidence |
|---|------|--------|--------|----------|
| 1 | [description] | [test/integration/mock/trace] | [status] | [evidence] |
| ... | | | | |

### Manual Verification
| # | Item | Status | Note |
|---|------|--------|------|
| 1 | [description] | [Verified/Failed/Skipped] | [user note] |
| ... | | | |

### Issues Found
[Detailed list of failures — only items with FAIL status]
For each:
- What failed and why
- File:line references where applicable
- Error output (trimmed to relevant lines)
- Severity: Critical (blocks merge) / Warning (should fix) / Info (cosmetic)

### Test Plan Coverage
- Total items: [N]
- Automated: [N] passed, [N] failed, [N] skipped
- Functional: [N] passed, [N] failed, [N] blocked
- Manual: [N] verified, [N] failed, [N] skipped
- Generated items (not in original PR plan): [N]
```

### Verdict logic

- **ALL PASSED** — every non-skipped item has status PASS or Verified
- **ISSUES FOUND** — at least one item has status FAIL or Failed
- **PARTIAL** — no failures, but some items are BLOCKED or Skipped

## Step 8: Offer Actions

Use `AskUserQuestion` — header "Action", question "How would you like to proceed?":

- **Fix issues** — "Attempt to fix failing items inside the sandbox, then re-verify" (only if ISSUES FOUND)
- **Update PR** — "Post the verification report as a PR/MR comment" (only if PR/MR exists)
- **Apply fixes to branch** — "Cherry-pick sandbox fixes back to the feature branch" (only after fixes are made in the sandbox)
- **Done** — "Keep the report as reference"

### Fix issues flow

If the user chooses "Fix issues":
1. For each failing item, attempt a fix **inside the sandbox only**
2. Re-run the failing verification to confirm the fix works
3. Follow the verification protocol for every re-verification
4. Present updated results showing which fixes succeeded
5. Offer "Apply fixes to branch" — use `git diff` in the sandbox to generate a patch, then apply it to the feature branch:
   - `cd <sandbox-path> && git diff > /tmp/verify-fixes.patch`
   - `cd <project-root> && git apply /tmp/verify-fixes.patch`
   - `rm -f /tmp/verify-fixes.patch`
6. Never push to remote — the user decides when to push

### Update PR flow

If the user chooses "Update PR":
1. Write the Verification Report to a temp file: `TMPFILE=$(mktemp /tmp/verify-report-XXXXXX.md)`
2. Post as a PR/MR comment:
   - **GitHub:** `gh pr comment <N> --body-file "$TMPFILE"`
   - **GitLab:** `glab api -X POST "projects/:id/merge_requests/<N>/notes" -F body=@"$TMPFILE"`
3. Clean up: `rm -f "$TMPFILE"`
4. Report the posted comment

## Step 9: Sandbox Cleanup

After all actions are complete, offer cleanup.

Use `AskUserQuestion` — header "Cleanup", question "Remove the sandbox worktree?":
- **Remove** — "Clean up `.worktrees/verify-<slug>` (recommended if verification is complete)"
- **Keep** — "Keep the sandbox for manual inspection or further work"

If "Remove":
1. Switch to the main workspace directory (parent of `.worktrees/`)
2. Remove the worktree: `git worktree remove .worktrees/verify-<slug>`
   - If removal fails due to changes: `git worktree remove --force .worktrees/verify-<slug>`
3. If `.worktrees/` is empty, remove it: `rmdir .worktrees 2>/dev/null`
4. If fallback was used (`.verify-sandbox/`): `rm -rf .verify-sandbox`

If "Keep":
- Note: "Sandbox at `.worktrees/verify-<slug>` is still active. Remove manually with `git worktree remove .worktrees/verify-<slug>` when done."

### Closing suggestions

Based on the verification results:
- If **ALL PASSED** → suggest `/optimus:code-review` for static quality review before merging
- If **ISSUES FOUND** and user fixed them → suggest committing the fixes and re-running `/optimus:verify` to confirm
- If **PARTIAL** → list the blocked/skipped items and suggest how to verify them

## Important

- Never push to remote — all sandbox work is strictly local
- Never modify the main workspace during verification (except when the user explicitly requests "Apply fixes to branch")
- The sandbox worktree is disposable — treat it as a scratch environment
- All claims of PASS/FAIL must follow the verification protocol: fresh evidence, not assumptions
