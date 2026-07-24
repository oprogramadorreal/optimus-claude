---
description: >-
  Compacts the current conversation into one self-contained, tool-agnostic handoff document at
  docs/handoffs/<slug>.md so any fresh agent or teammate can resume the work from that file
  alone. References pushed artifacts by path or URL, inlines anything not on the remote, and
  redacts secrets and PII. Re-running on an existing handoff offers enhance or overwrite.
  Writes only that one file; never commits.
disable-model-invocation: true
argument-hint: "[topic]"
---

# Handoff

## Step 1: Slug and focus

Derive a kebab-case `<slug>` from the user's arguments if given (e.g., "finish the migration tests" → `migration-tests`), otherwise from the conversation's most recent active thread; with no arguments, state the inferred topic and slug in one line before continuing. Record a **Focus for next session** only on a clear signal — verbatim user arguments or an explicitly stated next objective. Never manufacture one: with no signal, omit it and leave direction to the resumer.

## Step 2: Locate the doc; create, enhance, or overwrite

Resolve the root: the repo root, or the workspace root in a multi-repo workspace. If the current directory has no `.git/` directory, read `$CLAUDE_PLUGIN_ROOT/skills/init/references/multi-repo-detection.md` and apply it, then cover both of its non-workspace answers: when it finds **exactly one child repo**, treat that child repo as the root — writing above it would put the handoff outside version control, where the Step 5 `/optimus:commit` recommendation cannot reach it; when it finds **no recognized structure**, use the current directory. The handoff folder is `docs/handoffs/` under that root. Then branch:

- **`<slug>.md` exists** → read it, then `AskUserQuestion`: **Enhance** (merge new context; keep still-valid content and append a History line) or **Overwrite** (fresh rewrite; the prior version stays in git history).
- **No slug match but other handoffs exist** → list them (filename · title · Last updated), then `AskUserQuestion`: **Continue one** (pick via a follow-up question, adopt that file's slug as `<slug>`, treat as Enhance) or **Create new**.
- **Folder empty or absent** → create new.

## Step 3: Classify artifacts against version control

Per repo (per child repo in a multi-repo workspace, where paths and SHAs are also repo-qualified): find the branch and short HEAD SHA for **Origin**, each path's tracked / modified / staged / untracked status, and unpushed commits via `git log --oneline @{upstream}..HEAD` (fallback `origin/HEAD..HEAD`; no upstream or detached HEAD → treat local commits as unpushed). Not a git repo → note "not a git repo" in **Origin** and inline everything. Sort every artifact into three buckets:

1. **Tracked and pushed** → reference by repo-relative path / SHA / URL, never inline.
2. **Tracked-but-modified, staged-not-committed, or committed-not-pushed** → inline the relevant content (diff, file body, or commit message) — another clone will not have it.
3. **Untracked** → inline.

## Step 4: Draft or reconcile

If the conversation has not already established the codebase's current state, briefly verify it in the repo before asserting it. Fill the **Handoff document template**. **New or overwrite** → write fresh. **Enhance** → keep still-valid content; update **Current state** (and **Goal**/**Next steps** if present) to current reality, dropping completed steps; preserve and extend decisions and open questions, promoting any the new work resolved; add new artifacts; refresh **Last updated**; append one **History** line.

- Prioritize knowledge a fresh agent could not re-derive from code or git history — decisions and why, rejected alternatives, constraints, gotchas, open questions.
- Never duplicate tracked-artifact content — reference by path plus a one-line summary. Inline only bucket-2 and bucket-3 content.
- Trust git state over chat memory when they conflict; if the current state is ambiguous, say so in one line rather than guessing.
- Keep the document tool-agnostic: "a fresh agent" / "a new session" — never a named AI product.

## Step 5: Redact, write, verify, report

Scan the entire drafted body — authored prose as much as inlined content — against the **Redaction patterns** table and replace matches with the exact marker `[REDACTED: <kind>]`, preserving structure (e.g. `DATABASE_URL=postgres://app:[REDACTED: password]@db:5432/app`). Only reference lines (paths, SHAs, URLs) are exempt. A file whose name looks like a secret is never inlined with its values, regardless of tracked state — see the table's last two rows.

Write the document to `docs/handoffs/<slug>.md`, creating the folder if missing. Re-scan the written file against the same table (same exemption) and fix any hits before reporting; tell the user the re-scan ran clean.

Report the written path. If the resolved root is not itself a git repo — a multi-repo workspace root, or a directory with no recognized structure — note the file is not under version control; suggest committing it inside a child repo or initializing version control at the root. Recommend `/optimus:commit` so the handoff reaches the remote — staying in this conversation, so the context being handed off is captured — and that the resumer point a fresh session at the written file. This skill writes only that one file (`docs/handoffs/<slug>.md`, creating the folder if missing); it never stages, commits, or pushes.

## Handoff document template

Omit any section with nothing to say. Square-bracketed lines are author instructions — never emit them into the document.

````markdown
# Handoff: <short title of the work>

- **Created:** <YYYY-MM-DD> · **Last updated:** <YYYY-MM-DD>
- **Origin:** <repo> @ `<branch>` · commit `<short-sha>` (<pushed | NOT pushed>)
- **Focus for next session:** <one line — include only if the user passed args or the conversation states the next objective; otherwise omit this bullet>
- **How to use this doc:** Resume cold; read top to bottom — everything is here or linked by repo-relative path.

## Goal
<Include only if the conversation establishes a clear objective. 1-3 sentences: the outcome and why. Omit if not clear.>

## Current state
<2-6 bullets: what is done, in progress, blocked. Prioritize what a fresh agent could not re-derive — decisions made and why.>

**Decisions, constraints & gotchas** [omit if none]:
- <A decision made and why — and any alternative considered and rejected, with the reason.>
- <A non-obvious gotcha, or a constraint that gates the work.>

**Open questions** [omit if none]:
- <Something the conversation left unresolved — what is undecided and what depends on it.>

## Next steps
<Include only if the conversation points to concrete follow-up actions; otherwise omit and leave direction to the resumer.>
1. <Concrete first action on resume.>

## Relevant files & artifacts
> Committed/tracked → referenced by repo-relative path / SHA / URL.
> Uncommitted or unpushed → content inlined below (won't exist on another machine).
[Anchor each reference on a durable identifier (a type / function / config name the resumer can search for) and say why it matters; never cite line numbers — a bare path can move under a refactor.]

- `path/to/file.ts` — `SessionStore`: <why it matters> (tracked)
- Issue/PR: <URL> — <relevance>

### Inlined (not yet on remote)
[Omit this section if nothing is inlined.]
```diff
<the fragment that carries the decision — schema, type shape, state machine, or the changed lines that matter, not a full diff dump; or new-file body / unpushed commit message; secrets redacted>
```

## History (most recent first)
- <YYYY-MM-DD>: <one-line summary of what this session changed>

---
**Resume here:** open this file in a fresh session with any AI agent in this repo. If it has a Next steps section, begin at item 1; otherwise pick up from Current state and the decisions above.
````

## Redaction patterns

| Class | Catch | Marker |
|---|---|---|
| API keys / tokens | `sk-…`, `ghp_…`, `xox[bap]-…`, AWS `AKIA…`, Google `AIza…`, JWTs `eyJ…`, bearer | `[REDACTED: API key]` / `[REDACTED: token]` |
| Passwords / secrets | `password=`, creds in connection strings, `client_secret`, `-----BEGIN … PRIVATE KEY-----` | `[REDACTED: password]` / `[REDACTED: private key]` |
| Connection strings | `mongodb+srv://…:…@`, `mssql://…;Password=…` | `[REDACTED: connection string]` |
| PII | personal emails (keep role addresses like `support@`), phones, addresses, national IDs | `[REDACTED: PII]` |
| Env/secret files (text) | inlined `.env` / `*.key` / `*.pem` / `credentials.*` / `secrets.*` bodies | inline variable **names** only, never values |
| Binary/opaque secret files | `*.pfx` / `*.sqlite` / `*.db` bodies | **never inline** — reference by name with a "recreate from your secure source" note |
