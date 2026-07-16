---
description: Reviews local changes, PRs/MRs, or branch diffs against the project's own coding guidelines using up to 6 parallel review agents — the project-standards complement to Claude Code's built-in /code-review. Use before committing, on an open PR/MR, or on any branch diff. High signal only: bugs, logic errors, security issues, and guideline violations. Read-only by default — applies fixes or posts PR/MR comments only with explicit approval. PR/MR mode requires the gh or glab CLI. For iterative auto-fix in a loop, use /optimus:deep review.
disable-model-invocation: true
argument-hint: "[--pr N | --branch | path]"
---

# Code Review

Review changes against the project's own standards — the complement to Claude Code's
built-in review, which checks general code quality. This skill enforces the guidelines
`/optimus:init` generated and, in skill-authoring projects, judges markdown
instruction files by the skill-writing lens. High signal only: bugs, logic errors,
security issues, guideline violations — no style nits or linter-catchable issues.

## Step 1: Parse Arguments and Check Prerequisites

- `--pr N`, `#N`, or a PR/MR URL → explicit PR/MR mode
- `--branch` → branch diff against the detected base, skipping the PR auto-route
  (no effect when local changes exist or a PR is explicitly requested)
- A path → restrict the review to it; anything else → scope/focus instructions

Read `$CLAUDE_PLUGIN_ROOT/skills/init/references/multi-repo-detection.md` for
workspace detection. In a multi-repo workspace, run Step 3's git commands inside each
child repo (the workspace root has no `.git/`), resolve Step 4's docs per repo, and
require a named repo for PR/MR mode.

Read `$CLAUDE_PLUGIN_ROOT/skills/init/references/prerequisite-check.md` and apply
the prerequisite check (CLAUDE.md + coding-guidelines.md existence, fallbacks).

## Step 2: Inline Harness Mode Detection

If your invocation prompt body contains `HARNESS_MODE_INLINE`, you are running
inside the `/optimus:deep review` orchestrator as a single iteration. Read
`$CLAUDE_PLUGIN_ROOT/references/harness-mode.md` and follow its single-iteration
execution protocol: proceed through Steps 3–7, skip the Step 8 action prompt (the
orchestrator handles approval upfront), apply the fixes mechanically, emit the
structured JSON via the `json:harness-output` protocol, and stop. Do not use
`AskUserQuestion`. Do not loop.

If `HARNESS_MODE_INLINE` is NOT present, continue with the interactive flow below.

## Step 3: Determine Review Scope

**Local changes (default).** Gather staged (`git diff --cached`), unstaged
(`git diff`), and untracked (`git status --short`) changes; if anything is found,
review all of it.

**No local changes → PR auto-route or branch diff.**

1. Detect the platform per the Platform Detection Algorithm in
   `$CLAUDE_PLUGIN_ROOT/skills/code-review/references/platform-detection.md`.
2. Check for an open PR/MR on the current branch: `gh pr view --json
   number,state,baseRefName` (use only when `state` is `"OPEN"`) or `glab mr view
   --output json` (only when `"opened"`). Treat CLI failures as no open PR/MR, but
   surface apparent auth or connectivity errors to the user.
3. Base branch: the PR/MR target if one was found, otherwise detect via
   `$CLAUDE_PLUGIN_ROOT/skills/code-review/references/default-branch-detection.md`;
   if that fails too (e.g., no `origin`), ask the user for a base ref — never guess.
4. Route without prompting: `--branch` → branch diff against `origin/<base>`; open
   PR/MR with HEAD fully pushed (`git rev-list origin/<current-branch>..HEAD` is
   empty) → PR/MR mode for it (say so in one line; `--branch` overrides); open
   PR/MR but unpushed commits or undeterminable pushed state → branch diff (note
   `--pr N` reviews only the pushed state); otherwise → branch diff. No commits
   ahead of the base either → nothing to review; say so and stop.

**PR/MR mode** (explicit request, or auto-routed above). Detect the platform if
needed; if unknown, ask. If the CLI is unavailable, offer the branch diff instead.
Fetch metadata and diff — `gh pr view <N> --json state,isDraft,title,body,baseRefName,headRefName,headRefOid`
+ `gh pr diff <N>`, or `glab mr view <N> --output json` + `glab mr diff <N>` — and
store the title and body/description as `pr-description` for Steps 5–6. Closed or
merged → warn and stop. If the PR/MR head SHA differs from `git rev-parse HEAD`,
offer `gh pr checkout <N>` / `glab mr checkout <N>` — agents and validation read the
local working tree, so a mismatched checkout silently reviews the wrong content; if
declined, proceed with that caveat stated.

**Branch/ref mode.** `git diff <ref>...HEAD` for the diff,
`git diff --name-only <ref>...HEAD` for the file list. When the user names a path,
restrict all diffs to it (`git diff -- <path>`, etc.).

In every mode, state the resolved scope in one line before proceeding; for very large diffs (over ~50 files or ~3000 lines), suggest narrowing the scope.

## Step 4: Load Project Context

Read `$CLAUDE_PLUGIN_ROOT/skills/init/references/constraint-doc-loading.md` and apply
it in full: doc lists for single-project and monorepo layouts, the skill-authoring
lens (markdown instruction files are judged by `skill-writing-guidelines.md`, not
`coding-guidelines.md`), and the Submodule Exclusion rule. These docs are the review
criteria — every guideline finding must cite what they establish, never external preferences.

## Step 5: Parallel Multi-Agent Review

Launch every applicable agent as a `general-purpose` Agent tool call in a
**single message** so they run in parallel. The full fan-out is the design — do not
reduce the count to save tokens or time. Up to 6 agents:

| Agent | Prompt file (in `$CLAUDE_PLUGIN_ROOT/skills/code-review/agents/`) | Runs |
|-------|-------------|------|
| Correctness & Security | `correctness-security.md` | always |
| Guideline Compliance A | `guideline-reviewer.md` | always |
| Guideline Compliance B | `guideline-reviewer.md` — same prompt, dispatched independently; the second pass reduces false negatives | always |
| Code Simplifier | `code-simplifier.md` | always |
| Test Guardian | `test-guardian.md` | when test infrastructure is documented (`.claude/docs/testing.md` or a subproject `docs/testing.md` exists) |
| Contracts Reviewer | `contracts-reviewer.md` | when any changed file path contains `api/`, `routes/`, `controllers/`, `endpoints/`, `handlers/`, `graphql/`, `proto/`, or `grpc/`, or a changed file name matches `*.dto.*`, `*.schema.*`, `*.contract.*`, `openapi.*`, `swagger.*`, `*.proto`, `*.graphql`, or `*.gql` — otherwise skip (zero cost) |

Compose each prompt per "Prompt assembly at dispatch time" in
`$CLAUDE_PLUGIN_ROOT/references/agent-architecture.md`: substitute the resolved plugin
root for `$CLAUDE_PLUGIN_ROOT`, inline or absolutize the bare `shared-constraints.md`
reference (the shared quality bar and exclusions), strip the file's YAML frontmatter,
and for the guideline agents replace the "Dynamic Prompt Construction" section with
the concrete doc paths loaded in Step 4. End every assembled prompt with the changed
file list **followed by the diff hunks** (or per-file changed line ranges when the
diff is too large to inline) — agents review only changed sections and cannot compute
the diff themselves; never send file paths alone.

### PR/MR context injection

If a non-empty `pr-description` was captured, prepend the PR/MR Context Block from
`$CLAUDE_PLUGIN_ROOT/skills/code-review/agents/context-blocks.md` to every agent prompt,
before the file list; the same file covers the harness-mode Iteration Context Block and the ordering when both apply.

## Step 6: Validate Findings

Independently verify each finding — agents' reports are claims, not ground truth.
Apply `$CLAUDE_PLUGIN_ROOT/skills/init/references/verification-protocol.md`, plus:

1. **Context check** — read ±30 lines around the flagged location.
2. **Intent check** — comments, test assertions, or established patterns may show the flagged behavior is deliberate.
3. **Pre-existing check** — the issue must be introduced by these changes.
4. **Cross-agent consensus** — a guideline finding flagged by both guideline agents carries higher confidence.
5. **Change-intent awareness** — for each file with findings, run
   `git log --no-merges --format="%h %s" -5 -- <file>`. If a recent commit shows
   the flagged code was deliberately introduced ("fix null check", "harden auth")
   and a finding wants to remove it, reduce its confidence one level; for
   uninformative messages, inspect `git show <sha> -- <file>` for deliberate
   defensive patterns. Skip when history is unavailable.

### PR/MR description as intent signal

When a `pr-description` exists, use it the same way: if it explains why a flagged
change was made and git history corroborates, reduce confidence one level; if it
contradicts git history, trust the code and history over the claims. A soft
adjustment only — it never hard-filters a finding.

Keep **High** (clear evidence) and **Medium** (plausible, some evidence) findings; drop Low.

## Step 7: Consolidate and Present

Deduplicate across agents: same file, line range, and category → keep the more
detailed version; guideline findings flagged by both guideline agents merge into one,
noted "confirmed by independent review". Then resolve cross-agent contradictions —
findings on the same code pulling opposite directions ("add validation" vs. "simplify
this validation"): keep the higher severity; on a tie, the security/correctness one.

Severity: **Critical** — bugs, security vulnerabilities, runtime failures.
**Warning** — guideline violations, missing error handling, coverage gaps on
critical paths, backward-incompatible contract changes. **Suggestion** — quality
improvements, minor drift. Intent Mismatch findings map per the Severity rules in
`$CLAUDE_PLUGIN_ROOT/skills/code-review/agents/shared-constraints.md`. Cap at
**15 findings**, prioritized by severity then confidence; Intent Mismatch findings
ride on top of the cap, up to 5 after cross-agent deduplication. If more issues
exist, say how many and suggest narrowing scope or `/optimus:deep review`.

Present the review plainly: a one-line summary (scope, files reviewed, finding counts
by severity, verdict), a 2–4 sentence description of what the changes accomplish (so
the user can confirm the review understood them), then each finding ordered by
severity — severity and category, `file:line`, the issue, a concrete suggested fix.
Guideline findings cite the specific rule; Intent Mismatch findings quote the claim;
short before/after snippets where they help. In PR/MR mode, link locations with
full-SHA URLs (GitHub `.../blob/<sha>/<path>#L<n>`; GitLab likewise under `/-/blob/`,
host from `git remote get-url origin`).

## Step 8: Offer Actions

No findings → say the changes look good and finish. Otherwise ask the user (a
genuine decision gate — `AskUserQuestion` works well): fix the issues now, post the
review as a PR/MR comment (PR/MR mode only), or stop with the report as reference.

**Posting a comment:** write the summary to a temp file in the current working
directory — `TMPFILE=$(mktemp ./review-summary-XXXXXX.md)` — not `/tmp`, which the
native `gh.exe`/`glab.exe` cannot resolve on Windows (it would silently post an empty
comment). Post with `gh pr comment <N> --body-file "$TMPFILE"`, or `glab api -X POST
"projects/:id/merge_requests/<N>/notes" -F body=@"$TMPFILE"` (avoids shell-metacharacter
issues with code snippets), then `rm -f "$TMPFILE"` whether or not posting succeeded.

## Ground Rules

Read-only by default: never modify files, commit, push, or post comments without
explicit user approval; approved fixes stay as uncommitted local modifications for the
user to inspect. If fixes were applied, suggest running the project's tests and
committing. For issues a single pass tends to miss, `/optimus:deep review` iterates
automatically — fix, test, repeat until clean (needs a test command in `.claude/CLAUDE.md`).
