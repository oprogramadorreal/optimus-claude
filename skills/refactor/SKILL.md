---
description: Refactors code toward project-guideline compliance and testability (so /optimus:unit-test can safely increase coverage) across four analysis lenses, fanned out to parallel agents when the scope warrants it. Supports "testability" or "guidelines" focus plus flexible scoping. Read-only until the user approves the plan; applied changes stay local. Use after /optimus:init, before /optimus:unit-test, or for an iterative loop /optimus:deep refactor.
disable-model-invocation: true
argument-hint: "[testability|guidelines] [scope]"
---

# Project-Wide Code Refactoring

Analyze existing source code against the project's own guidelines across four lenses — inline for a small scope, fanned out to parallel agents otherwise — present a prioritized refactoring plan, then apply only user-approved changes with test verification. Two goals:

1. **Guideline compliance** — align code with coding-guidelines.md, architecture.md, styling.md, and testing.md
2. **Testability** — restructure code so `/optimus:unit-test` can safely increase coverage without risky refactoring

## Step 1: Prerequisites and scope

If `git rev-parse --is-inside-work-tree` does not return `true`, read `$CLAUDE_PLUGIN_ROOT/skills/init/references/multi-repo-detection.md` and apply it. When it returns `true`, resolve the repository root with `git rev-parse --show-toplevel`, including in a linked worktree or subdirectory. In a multi-repo workspace, load each targeted repo's `.claude/CLAUDE.md` and `.claude/docs/` (not the workspace root's) and apply that repo's context to its files; if the scope doesn't determine a repo, ask which one.

If `.claude/CLAUDE.md` or `.claude/docs/coding-guidelines.md` is missing, recommend `/optimus:init` first. On the user's choice to continue, fall back to the bundled baseline: read `$CLAUDE_PLUGIN_ROOT/skills/init/templates/docs/coding-guidelines.md` and work against it plus general best practices, and note in the report that findings are generic, not project-specific.

**Focus:** a bare `testability` or `guidelines` argument sets the focus and is consumed from the scope text — a keyword inside a quoted string is scope, not focus (`"improve testability in auth"` → no focus). If both appear, take the first and say the other needs its own pass. Everything remaining is natural-language scope.

**Scope:** if the arguments describe a scope, map it to directory paths by scanning the project structure — no question needed. Otherwise use `AskUserQuestion` (header "Scope"):

- **Full project** — all source directories (default when the user just says "refactor")
- **Directory** — specific path(s) for targeted cleanup
- **Changed since** — files modified since a commit, tag, or date

For changed-since, use `git diff --name-only <ref>...HEAD` for commits, branches, and tags; for relative dates use `git log --no-merges --since="2 weeks ago" --format= --name-only` instead (`--since` is a `git log` flag, not `git diff`). Apply Step 3's exclusions to the result. In a monorepo with full-project scope, ask which subprojects to include (default: all).

## Step 2: Harness mode

If your invocation prompt contains `HARNESS_MODE_INLINE`, you are a single iteration inside the `/optimus:deep` orchestrator: read `$CLAUDE_PLUGIN_ROOT/references/harness-mode.md` and follow its single-iteration protocol, which overrides the interactive steps — it covers progress-file reading, scope and file-list rules, agent-prompt overrides (including the Iteration Context Block on iterations 2+), and the apply/output protocol.

Before interpreting the progress file's iteration and findings fields, inspect its `harness` field. Only when `harness` equals `"test-coverage"`, load the **Refactor Phase Execution** section of `$CLAUDE_PLUGIN_ROOT/references/coverage-harness-mode.md` and apply its field mapping and overrides to the shared protocol. Standalone refactor progress has no such marker and uses the shared protocol's normal mapping; both dispatches use `Phase: refactor`.

Refactor's deltas, which that reference defers back to this note:

- **Scope**: when `scope_files.current` is non-empty, treat it as the pre-resolved scope and derive analysis areas from its files' parent directories rather than resolving scope in Step 1; when empty, run Step 3's normal directory scan at full-project scope.
- **Focus**: take the finding-cap allocation from `config.focus` (empty string = balanced).
- **No PR/MR block**: the PR/MR context block does not apply to refactor — ignore `config.pr_description`.

If `HARNESS_MODE_INLINE` is not present, continue with the interactive flow below.

## Step 3: Load project context and map analysis areas

Read `$CLAUDE_PLUGIN_ROOT/skills/init/references/constraint-doc-loading.md` and load the docs it lists, applying its skill-authoring lens, its monorepo scoping rule, and its submodule exclusion. These docs define the rules: every suggestion must be justified by what they establish — never impose external preferences.

Within the scope, identify source directories. Skip non-source directories (dependencies, build output, framework caches, dot-directories), minified/lock/binary files, and the generated source files listed under "All Agents Exclude" in `$CLAUDE_PLUGIN_ROOT/references/shared-agent-constraints.md`. Group areas by top-level source directory (monorepo: by subproject, then directory) and rank by recent churn:

```bash
git log --no-merges --since="3 months" --format= --name-only -- <scope-path> | sort | uniq -c | sort -rn
```

Analyze highest-churn areas first; for full-project scope on a large codebase, start with the top 10. Briefly summarize docs loaded (and any missing, with fallback status), project type, and ranked areas, then proceed immediately — do not wait for confirmation.

## Step 4: Four-lens analysis

The four lenses below must all be covered. Size the fan-out to the scope: **for a handful of files, analyze them yourself in one pass** — four subagents over three files each re-read CLAUDE.md and the guideline docs to reach findings you can reach directly. Fan out for a directory or wider, where the lenses genuinely read different parts of the tree.

When you do fan out, launch all 4 agents as `general-purpose` Agent tool calls in a **single** message so they run in parallel — separate messages serialize them for no benefit.

| Agent | Prompt file | Finds |
|---|---|---|
| 1 — Guideline Compliance | `agents/guideline-reviewer.md` | Explicit doc violations, each citing the rule it breaks |
| 2 — Testability Analyzer | `agents/testability-analyzer.md` | Structural barriers to unit testing |
| 3 — Consistency Analyzer | `agents/consistency-analyzer.md` | Cross-file duplication, inconsistency, drift |
| 4 — Code Simplifier | `agents/code-simplifier.md` | Unnecessary complexity, naming, dead code |

Read the prompt files from `$CLAUDE_PLUGIN_ROOT/skills/refactor/agents/` (shared rules and the canonical output format live in `agents/shared-constraints.md`) and give every agent the Step 3 file list. Construct Agent 1's prompt dynamically from Step 3's doc-loading results (single-project vs monorepo paths). Assemble each prompt per "Prompt assembly at dispatch time" in `$CLAUDE_PLUGIN_ROOT/references/agent-architecture.md`: substitute the resolved absolute plugin root for every `$CLAUDE_PLUGIN_ROOT` reference and inline or absolutize the bare `shared-constraints.md` reference. Wait for all 4 to complete.

## Step 5: Validate findings and present the plan

Read `$CLAUDE_PLUGIN_ROOT/references/finding-validation.md` and apply it to every finding. Two refactor deltas: skip its **Pre-existing** check — this skill analyzes existing code by design, not a diff — and treat Agents 1 and 3 landing on the same location as corroboration.

Keep **High**-confidence findings, keep **Medium** with a note, drop what your own check could not confirm — and report how many you dropped, so filtered recall stays visible. An agent's **Low** label describes its evidence, not yours: promote it if your check confirms the issue.

**Deduplicate and resolve:** same file/line-range/category from two agents → keep the more detailed version; an Agent 1 + Agent 3 overlap → merge and note "confirmed by independent review". When two agents contradict each other on the same region, decide on the evidence in the code and say which you kept and why.

**Cap:** at most **15 findings**, each a distinct root cause — never pad. With an active focus, rank that category first and let only high-severity findings from the others take the remaining slots; without a focus, rank by severity then confidence across all categories. If more issues exist, disclose it ("15 of ~24 detected") and suggest a narrower scope or `/optimus:deep refactor`.

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

Apply each approved finding with Edit, then run the project's test command from `.claude/CLAUDE.md` if one exists and report the actual result. If tests fail, revert ALL changes, then re-apply one at a time with a test run after each, keeping only the changes that pass. If no test command exists, warn the user that the changes were applied without automated verification and carry higher risk.

Close with a final summary: scope analyzed, changes applied/skipped/reverted (with file references), test results, findings beyond the cap, and how many changes made code testable for `/optimus:unit-test`.

## Important

- Outside harness mode, never modify files, commit, or push without explicit user approval — all changes stay local for `git diff` review. Under `HARNESS_MODE_INLINE` the orchestrator holds that approval and Step 2's protocol governs instead.
- When the scope is too broad for effective analysis, recommend narrowing it

If fixes were applied, recommend `/optimus:commit` next — the user should stay in this conversation so the implementation context is captured — then `/optimus:unit-test` in a fresh conversation to cover the restructured code. For iterative refactoring in an automated loop, mention `/optimus:deep refactor` (requires a test command in `.claude/CLAUDE.md`).
