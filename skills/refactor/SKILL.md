---
description: Refactors code toward two goals — project-guideline compliance and testability (so /optimus:unit-test can safely increase coverage) — using 4 parallel analysis agents. Supports "testability" or "guidelines" focus plus flexible scoping. Read-only until the user approves the plan; applied changes stay local for review. Use after /optimus:init, before /optimus:unit-test, or periodically; for an iterative loop use /optimus:deep refactor.
disable-model-invocation: true
argument-hint: "[testability|guidelines] [scope]"
---

# Project-Wide Code Refactoring

Analyze existing source code against the project's own guidelines using 4 parallel agents, present a prioritized refactoring plan, then apply only user-approved changes with test verification. Two goals:

1. **Guideline compliance** — align code with coding-guidelines.md, architecture.md, styling.md, and testing.md
2. **Testability** — restructure code so `/optimus:unit-test` can safely increase coverage without risky refactoring

## Step 1: Prerequisites and scope

If the current directory has no `.git/` directory, read `$CLAUDE_PLUGIN_ROOT/skills/init/references/multi-repo-detection.md` and apply it. In a multi-repo workspace, load each targeted repo's `.claude/CLAUDE.md` and `.claude/docs/` (not the workspace root's) and apply that repo's context to its files; if the scope doesn't determine a repo, ask which one.

If `.claude/CLAUDE.md` or `.claude/docs/coding-guidelines.md` is missing, recommend `/optimus:init` first; on the user's choice, continue with general best practices.

**Focus:** a standalone unquoted `testability` or `guidelines` token (case-insensitive) in the arguments sets the focus and is consumed from the scope text; keywords inside quoted strings stay scope text (`"improve testability in auth"` → focus=null). If both keywords appear, use the first and warn that separate passes cover each. Everything remaining is natural-language scope.

**Scope:** if the arguments describe a scope, map it to directory paths by scanning the project structure — no question needed. Otherwise use `AskUserQuestion` (header "Scope"):

- **Full project** — all source directories (default when the user just says "refactor")
- **Directory** — specific path(s) for targeted cleanup
- **Changed since** — files modified since a commit, tag, or date

For changed-since, use `git diff --name-only <ref>...HEAD` for commits, branches, and tags; for relative dates use `git log --no-merges --since="2 weeks ago" --format= --name-only` instead (`--since` is a `git log` flag, not `git diff`). Apply Step 3's exclusions to the result. In a monorepo with full-project scope, ask which subprojects to include (default: all).

## Step 2: Harness mode

If your invocation prompt contains `HARNESS_MODE_INLINE`, you are a single iteration inside the `/optimus:deep` orchestrator: read `$CLAUDE_PLUGIN_ROOT/references/harness-mode.md` and follow its single-iteration protocol, which overrides the interactive steps. In brief: treat a non-empty `scope_files.current` from the progress file as the pre-resolved scope, deriving analysis areas from its files' parent directories instead of resolving scope in Step 1; take focus from `config.focus`; skip every `AskUserQuestion` and confirmation; apply validated fixes mechanically, recording the exact `pre_edit_content`/`post_edit_content` pair for each edit location (empty post = deletion) so the orchestrator can bisect; NEVER run tests, lint, or builds — the orchestrator owns all verification; emit the `json:harness-output` block and stop without looping. On iterations 2+, prepend the Iteration Context Block from `$CLAUDE_PLUGIN_ROOT/references/context-injection-blocks.md` to every agent prompt before the file list; the PR/MR context block does not apply to refactor.

If `HARNESS_MODE_INLINE` is not present, continue with the interactive flow below.

## Step 3: Load project context and map analysis areas

Read `$CLAUDE_PLUGIN_ROOT/skills/init/references/constraint-doc-loading.md` and load the docs it lists, applying its skill-authoring lens (markdown instruction files are judged by skill-writing-guidelines.md, code by coding-guidelines.md — never cross-contaminate), its monorepo scoping rule, and its submodule exclusion. These docs define the rules: every suggestion must be justified by what they establish — never impose external preferences.

Within the scope, identify source directories. Skip non-source directories (dependencies, build output, framework caches, dot-directories), minified/lock/binary files, and the generated source files listed under "All Agents Exclude" in `$CLAUDE_PLUGIN_ROOT/references/shared-agent-constraints.md`. Group areas by top-level source directory (monorepo: by subproject, then directory) and rank by recent churn:

```bash
git log --no-merges --since="3 months" --format= --name-only -- <scope-path> | sort | uniq -c | sort -rn
```

Analyze highest-churn areas first; for full-project scope on a large codebase, start with the top 10. Briefly summarize docs loaded (and any missing, with fallback status), project type, and ranked areas, then proceed immediately — do not wait for confirmation.

## Step 4: Parallel analysis (4 agents)

Launch all 4 agents as `general-purpose` Agent tool calls in a **single** message so they run in parallel. The full fan-out is the design — do not reduce the count to save tokens or time.

| Agent | Prompt file | Finds |
|---|---|---|
| 1 — Guideline Compliance | `agents/guideline-reviewer.md` | Explicit doc violations with exact rule citations |
| 2 — Testability Analyzer | `agents/testability-analyzer.md` | Structural barriers to unit testing |
| 3 — Consistency Analyzer | `agents/consistency-analyzer.md` | Cross-file duplication, inconsistency, drift |
| 4 — Code Simplifier | `agents/code-simplifier.md` | Unnecessary complexity, naming, dead code |

Read the prompt files from `$CLAUDE_PLUGIN_ROOT/skills/refactor/agents/` (shared rules and the canonical output format live in `agents/shared-constraints.md`) and give every agent the Step 3 file list. Construct Agent 1's prompt dynamically from Step 3's doc-loading results (single-project vs monorepo paths). Assemble each prompt per "Prompt assembly at dispatch time" in `$CLAUDE_PLUGIN_ROOT/references/agent-architecture.md`: substitute the resolved absolute plugin root for every `$CLAUDE_PLUGIN_ROOT` reference and inline or absolutize the bare `shared-constraints.md` reference. Wait for all 4 to complete.

## Step 5: Validate findings and present the plan

Treat agent findings as claims requiring independent evidence, not ground truth. For each finding:

- **Context** — read ±30 lines around the flagged location to confirm the issue exists in context
- **Intent** — comments, test assertions, or established patterns may show the code is deliberate
- **Consensus** — Agents 1 and 3 flagging the same location raises confidence
- **Runtime assumptions** — unvalidated assumptions about inputs, dependencies, or environment strengthen a finding

**Change-intent awareness:** for each file with findings, run `git log --no-merges --format="%h %s" -5 -- <file>`. If a recent commit deliberately introduced what a finding would revert (e.g., "add dependency injection"), reduce that finding's confidence one level (High → Medium, Medium → Low). When messages are uninformative, inspect the diff with `git show <sha> -- <file>` for deliberate structural intent and apply the same reduction.

Keep **High**-confidence findings, keep **Medium** with a note, drop **Low**.

**Deduplicate and resolve:** same file/line-range/category from two agents → keep the more detailed version; an Agent 1 + Agent 3 overlap → merge and note "confirmed by independent review". Contradictory findings on the same region (opposite directions) → higher severity wins; tie → active focus wins; no focus → testability wins.

**Cap:** at most **15 findings**, each a distinct root cause — never pad. With an active focus, reserve 12 slots for the focused category and 3 for the rest, prioritizing by severity then confidence within each group; unused slots flow to the other group. Category mapping: `testability` → Testability Barrier findings plus any finding with a Testability impact line; `guidelines` → every other category. Without focus, rank by severity then confidence across all categories. If more issues exist, disclose it ("15 of ~24 detected") and suggest a narrower scope or `/optimus:deep refactor`.

### Output format

```
## Refactoring Plan

### Summary
- Scope: [full project / directory / changed since X] | Focus: [testability / guidelines / balanced]
- Areas analyzed: [N] | Findings: [N] shown (of ~[M] detected) — Critical: [N], Warning: [N], Suggestion: [N]
- Testability improvements: [N] findings will make code testable for /optimus:unit-test
- Top recommendation: [one-sentence highest-impact finding]

### Cross-Cutting Findings

### Findings by Area

#### [Area] — [path]

**[N]. [Finding title]** (Critical/Warning/Suggestion)
- **File:** `file:line` — cross-cutting findings list **Files:** `file1:line`, `file2:line`, ...
- **Category:** [Guideline Violation | Testability Barrier | Code Quality | Duplication | Inconsistency | Missing Abstraction | Architectural Drift]
- **Guideline:** [which project guideline this addresses]
- **Current:** / **Suggested:** [code sketches in fenced blocks, max 5 lines each — cross-cutting findings may use **Pattern:** / **Suggested:** prose instead]
- **Testability impact:** [what becomes testable — omit if not applicable]

### Areas with No Findings
- [Area name] — reviewed, code follows project guidelines
```

Severity: **Critical** — testability barrier blocking unit testing, cross-cutting pattern, or significant duplication; **Warning** — guideline violation or consistency issue of limited scope; **Suggestion** — minor clarity or hygiene.

**No findings:** report a positive result — code follows project guidelines and is well-structured for testing — skip Step 6, and close with the recommendation below.

## Step 6: Approve, apply, verify

Use `AskUserQuestion` (header "Action"): **Apply all** / **Selective** — ask which finding numbers / **Skip** — keep the report as reference.

Apply each approved finding with Edit, then run the project's test command from `.claude/CLAUDE.md` if one exists: run it fresh, read the complete output, and report the actual result with evidence (e.g. "14 passed, 1 failed") — never claim "should pass". If tests fail, revert ALL changes, then re-apply one at a time with a test run after each, keeping only the changes that pass. If no test command exists, warn the user that the changes were applied without automated verification and carry higher risk.

Close with a final summary: scope analyzed, changes applied/skipped/reverted (with file references), test results, findings beyond the cap, and how many changes made code testable for `/optimus:unit-test`.

## Important

- NEVER modify files, commit, push, or post comments without explicit user approval — all changes stay local for `git diff` review; this skill is read-only by default
- When the scope is too broad for effective analysis, recommend narrowing it

If fixes were applied, recommend `/optimus:commit` next — the user should stay in this conversation so the implementation context is captured — then `/optimus:unit-test` in a fresh conversation to cover the restructured code. For iterative refactoring in an automated loop, mention `/optimus:deep refactor` (requires a test command in `.claude/CLAUDE.md`).
