---
description: Creates or updates a pull request (GitHub) or merge request (GitLab) for the current branch in the Conventional PR format — intent, summary, changes, rationale, and test plan. Pushes the branch if needed (asks before any force-push) and captures the implementation conversation's intent into the PR description. Use when a feature branch is ready for review or to refresh an existing PR/MR description.
disable-model-invocation: true
---

# Pull Request / Merge Request

This skill never commits working-tree changes — it only pushes existing commits and manages the PR/MR.

## Step 1: Pre-flight

If the current directory has no `.git/` directory, read `$CLAUDE_PLUGIN_ROOT/skills/init/references/multi-repo-detection.md` and apply it. In a detected workspace:

- Filter to child repos on a non-default branch with commits ahead of the default branch (detect the default branch per `$CLAUDE_PLUGIN_ROOT/skills/pr/references/default-branch-detection.md`, run inside each repo). Warn and skip any repo whose default branch cannot be detected.
- 0 candidates → "No repositories in this workspace have branches with changes ready for a PR." Stop. 1 → announce which repo was detected and run Steps 2–7 inside it. Multiple → ask (AskUserQuestion): **All** or one specific repo.
- **All** → run Steps 2–7 per repo sequentially (show a `## <repo-name>` heading before Step 2; run all commands inside that repo). Any per-repo stop condition (unknown platform, CLI cancel, update-flow Cancel, …) stops only that repo — record the outcome for the Step 8 summary and continue with the next. Only the gates below halt the whole run.

**Verify git state** (stop gates):

1. Not inside a git repository → inform the user and stop.
2. Default-branch detection (reference above) fails → "Could not detect the default branch. Ensure `origin` is configured and has been fetched." Stop.
3. On the default branch → "You're on the default branch (`<branch>`). Switch to a feature branch first." Stop.

## Step 2: Platform Detection

Read `$CLAUDE_PLUGIN_ROOT/skills/pr/references/platform-detection.md` and apply the **Platform Detection Algorithm**. Unknown platform → inform the user and stop.

## Step 3: CLI Availability

Apply the reference's **CLI Verification** section. If the CLI is missing, offer to install it per its **CLI Installation** section (ask: **Install** / **Cancel**). On Cancel or install failure → provide manual installation instructions and stop. Installed but unauthenticated → "Run `gh/glab auth login` to authenticate, then re-run `/optimus:pr`." Stop.

## Step 4: Push and Existing PR/MR Check

If the branch is not on the remote (`git ls-remote --heads origin <branch>`): with no commits on the branch → "No commits on this branch yet. Commit your changes first." Stop. Otherwise `git push -u origin <branch>`.

If the branch is on the remote with unpushed commits, check divergence first: `git rev-list --count HEAD..origin/<branch>`

- Count `0` → fast-forward push: `git push origin <branch>`
- Count `> 0` → the remote has commits not in local history (typical after a rebase). NEVER plain-push. Ask (AskUserQuestion "Diverged branch"): **Force push** → run `git push --force-with-lease origin <branch>`; if the lease is rejected → "Force push rejected — the remote gained new commits since your last fetch. Review them before overwriting." Stop. **Cancel** → tell the user to reconcile and push manually, then re-run `/optimus:pr`. Stop.

Check for an existing PR/MR:

- **GitHub:** `gh pr view --json number,state,title,body,url,baseRefName 2>/dev/null`
- **GitLab:** `glab mr view --output json 2>/dev/null`

Open PR/MR → save its `baseRefName` / `target_branch` as the **target branch** and go to Step 6 (Update Flow). Closed/merged or none → Step 5 (Create Flow).

## Step 5: Create Flow

Default branch: on GitHub, `gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name'` is authoritative over Step 1's local detection (local `origin/HEAD` may be stale); on GitLab, use Step 1's detection.

Gather the branch's commits and diff vs `origin/<default-branch>`. No commits ahead → "This branch has no changes compared to `<default-branch>`." Stop.

### Detect intent context

Classify into one of three states before generating content:

1. **Conversation context** — this conversation implemented the branch: Edit/Write/NotebookEdit calls touched files in the diff, or the conversation discussed the problem, design decisions, or non-goals. A `## TDD Summary` block with `### Behaviors Implemented` (literal, case-sensitive — emitted by `/optimus:tdd`) is a strong state-1 signal; apply the population rule below.
2. **Existing PR body has `## Intent`** (Update Flow only — see the detection rule in the template).
3. **None** — when uncertain, prefer this state over fabricating. Ask (AskUserQuestion "Intent capture"): **Add intent now** → have the user reply with Problem / Scope / Non-goals / Key decisions on separate lines in a plain message (blank lines skip a sub-field); **Skip** → omit the section entirely, no stub.

Suppress the state-3 prompt in states 1 and 2. **Never infer Intent from commit messages or the diff alone** — a fabricated Intent creates false `Intent Mismatch` findings in `/optimus:code-review`.

### Generate content

Read `$CLAUDE_PLUGIN_ROOT/skills/pr/references/pr-template.md` and generate a title and body. Populate `## Intent` from the conversation (state 1) or the user's reply (state 3), including only sub-fields the source actually answers.

**TDD Summary population rule** — when the handoff signal fired, fill the body from the summary block:

- **Intent → Scope**: one bullet per `### Behaviors Implemented` row with Status `✓ Complete`, description verbatim.
- **Intent → Non-goals**: one bullet per `Not started` row; omit if none.
- **Intent → Key decisions**: refactor-step reasoning captured in the conversation; omit rather than invent.
- **Intent → Problem**: quote/summarize the spec or JIRA task file loaded in the conversation, else the initiating brief.
- **Test plan**: one verification item per `✓ Complete` row plus the project's test command; if a `### Coverage` section with `Before:` / `After:` / `Delta:` lines is present, append one line `Coverage: <Before> → <After> (<Delta>)`.

### Preview, confirm, create

Show the generated title and body under `## PR Preview` (append `— <repo-name>` in a multi-repo run). Ask (AskUserQuestion): **Create PR** → proceed; **Adjust** → ask what to change, apply, and preview again.

Write the body to a temp file at a relative path: `TMPFILE=$(mktemp ./pr-body-XXXXXX.md)` — never `/tmp` (on Windows, Git Bash's `/tmp` is unresolvable by native `gh.exe`/`glab.exe`, which would silently submit an empty body). Remove it with `rm -f "$TMPFILE"` after the attempt.

- **GitHub:** `gh pr create --title "<title>" --body-file "$TMPFILE" --base <default-branch>`
- **GitLab:** `glab mr create --title "<title>" --description "$(cat "$TMPFILE")" --target-branch <default-branch>`

PRs/MRs are created ready to merge (not draft). Proceed to Step 7.

## Step 6: Update Flow

Show the existing PR/MR (number, title, URL, current body), then ask (AskUserQuestion "Update PR"):

- **Regenerate title and description** — existing `## Intent` preserved verbatim.
- **Regenerate description only** — keep the title; existing `## Intent` preserved verbatim.
- **Regenerate Intent only** — replace just the `## Intent` section (or add one if missing); everything else untouched.
- **Cancel** — report the existing URL and stop.

**Regenerate Intent only:** re-detect intent context, treating the existing PR Intent as replaceable (the user opted in). Use conversation context when present; otherwise prompt directly for Problem / Scope / Non-goals / Key decisions in a plain reply (not the state-3 meta-prompt). Empty reply or all sub-fields blank → keep the existing Intent, report "No replacement Intent provided — existing `## Intent` kept as-is. No changes will be made." and stop (do not enter Phase 3). Otherwise replace `## Intent` in place (or insert it before `## Summary`), skip Phases 1–2, and jump to Phase 3.

**Phase 1 — fresh content.** Gather commits and diff against the PR's saved **target branch** (not the repo default) and generate new content from the template. This is the authoritative content; do not present yet.

**Phase 2 — preservation scan.** Review the existing title and body for information that cannot be derived from the code changes:

- **`## Intent`** — always preserve verbatim and re-insert before `## Summary`. Never silently overwrite it with fresh inference. If conversation context also exists, the existing section still wins; add a note to the Phase 3 preview: "Existing `## Intent` section preserved. The current conversation suggests possible updates — choose 'Regenerate Intent only' if you want to revise."
- Keep other non-diff information — issue/ticket references, deployment instructions, external links, reviewer notes, follow-ups — integrated into the matching section. Still-relevant non-standard sections go after `## Test plan`. When regenerating the title, carry issue references into the new title.
- **Never preserve diff-derivable facts** (version numbers, counts, symbol/path/file names) — always re-derive them from the current diff; rebases and force-pushes can change them. Discard anything outdated, wrong, or already covered by the fresh content.
- **Friction floor:** when the existing body has `## Intent` and the conversation has no implementation context, the update must complete without any intent-related prompting — only the Phase 3 preview runs.

**Phase 3 — preview.** If non-diff content was carried over, note it briefly above the preview. Ask (AskUserQuestion): **Update** → proceed; **Adjust** → apply changes and preview again.

Apply using the Step 5 temp-file pattern:

- **GitHub:** `gh pr edit <number> --title "<title>" --body-file "$TMPFILE"` (omit `--title` when keeping the title)
- **GitLab:** `glab mr update <number> --title "<title>" --description "$(cat "$TMPFILE")"`

## Step 7: Per-Repo Report

```
## PR/MR [Created / Updated] [— repo-name]

- URL: [url]
- Title: [title]
- Target: [target-branch]
- Status: Ready to merge
```

In a multi-repo run, continue with the next repo (back to Step 2); hold all recommendations until every repo is done.

## Step 8: Final Summary

After a multi-repo run, show a combined table: Repo | PR/MR | Status (Created / Updated / Skipped (reason)) | URL.

Recommend `/optimus:code-review` in a fresh conversation for a quality review before merging — it gathers its own context from the PR description.
