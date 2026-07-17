# optimus-claude 3.0 — plan

Written 2026-07-16 on `feat/v3-lean`, from a 26-agent audit of master (29e96a5) against
Anthropic's [Claude Code best practices](https://code.claude.com/docs/en/best-practices) and
[skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices),
compared afterwards against PR #163 (`feat/v3-modernization`, never merged, superseded by this branch).

## Diagnosis

The skills over-prescribe judgment tasks current models handle natively, and the connective
tissue built to coordinate 22 skills — verbatim closing-tip variants pinned by ~700 lines of
literal-string checks in `validate.sh`, a two-tier agent inheritance pattern that loads dead
base text on every dispatch, unconditional reads of cross-cutting references — costs more
context than the skills' actual payloads. The genuinely fragile machinery (harness protocol,
JSON ABI with the Python CLI, git bisection choreography) is correctly low-freedom and stays.

## Lineup: 22 → 16 skills

Every 2.x capability survives. Only `workflow` is dropped (native dynamic workflows cover it).

| v3 skill | Absorbs | Notes |
|---|---|---|
| `init` | — | Flagship; stays standalone |
| `brainstorm` | `spec-init` | Greenfield cascade scaffold becomes a brainstorm mode |
| `jira` | — | Radically slimmed |
| `tdd` | — | |
| `unit-test` | — | Harness inner engine (coverage-harness-mode) |
| `refactor` | — | Harness inner engine (harness-mode) |
| `code-review` | — | Harness inner engine (harness-mode); PR description = intent input |
| `deep` *(new)* | `code-review-deep`, `refactor-deep`, `unit-test-deep` | `/optimus:deep <review\|refactor\|coverage>`; CLI unchanged |
| `pr` | — | Keeps the `## Intent` template code-review consumes |
| `commit` | `commit-message`, `branch` | `suggest` = read-only message; `branch` = branch-only move |
| `worktree` | — | |
| `handoff` | — | |
| `how-to-run` | — | Biggest single shrink (2,301 → ~950 lines); validator pins die |
| `permissions` | — | |
| `prompt` | — | |
| `reset` | — | Classification via `cmp -s`, not full-file reads |

**Differences from PR #163 (and why):**
- #163 dropped `branch`, `commit`, `commit-message`, `worktree`, `prompt`, `pr`, `handoff`
  and folded `permissions`/`how-to-run`/`jira` away. Mandate for this branch: everything
  survives (merged or slimmed) except `workflow`. Also on the merits: `pr` ↔ `code-review`
  intent flow is worth two skills; `how-to-run`'s deliverable is defensible once its 500
  lines of validator pins die; folding `permissions` + `how-to-run` into `init` would make
  the flagship skill sprawl.
- #163 merged the two orchestrator-loop references into one file. Kept separate here: a
  merged file makes every `deep` run load both variants' step lists; separate files load
  only the needed one. Disk-level duplication is free; runtime loading is not.
- #163 trimmed harness Python internals (legacy bisect path, `mark-termination`,
  `--include-stash`, CLAUDE.md test-command parser). Not done here: Python never loads
  into model context, so it contributes nothing to the size goal, and the recent hardening
  commits (7d9d13f, f445255, 237653d) live exactly there. Only user-visible strings that
  name dead skills (cli.py docstring/help) are touched.
- Adopted from #163 (validated independently by this branch's audit): single `deep` skill;
  deletion of the closing-tip machinery + `validate.sh` check 17; SessionStart hook git-state
  block removal; PR-description-as-intent for code-review.

## Cross-cutting reforms (phase 1, before any skill rewrite)

1. **Closing tips.** Delete `references/skill-handoff.md` and the three verbatim variants.
   Each skill ends with 1–2 plain lines recommending the next step; the one real rule
   ("stay in this conversation for `/optimus:commit`, `/optimus:pr`, `/optimus:handoff` —
   they capture it; start fresh for everything else") is stated inline where relevant.
   The plan-mode carve-out (review-only plan mode, `### Refined plan` exact-heading
   contract, canonical prompt-closing block) moves to
   `skills/brainstorm/references/plan-mode-handoff.md` (~45 lines), read by brainstorm and jira.
2. **Agent tier.** Kill the "extend plugin-level agent" pattern: skill-level agents inline
   their ~100-word criteria core instead of Read-ing the 65-line base (which self-voids half
   its content when extended). Plugin agents `code-simplifier`/`test-guardian` stay as
   standalone user-invocable agents, trimmed to ~35 lines. Merge
   `references/scope-expansion-rule.md` into `references/shared-agent-constraints.md`;
   delete the per-skill `shared-constraints.md` files that merely restate the base pair
   (init, unit-test); delete both `context-blocks.md` pointer files (double hop);
   hoist the ~10× repeated output-format skeleton into each skill's shared constraints;
   state Intent-vs-Implementation once (code-review shared-constraints), 1–2 lines per agent.
3. **Reference diet.** `agent-architecture.md` 78 → ~14 (keep only "Prompt assembly at
   dispatch time"); `sdd-mapping.md` 82 → ~15 (precedence contract only);
   delete `skills/init/references/prerequisite-check.md`, `verification-protocol.md`,
   `claude-md-best-practices.md`, `readme-section-detection.md` — consumers inline a 1–3
   line gist. Harness protocol files trimmed ~15% only (dup ToC, rationale echoes,
   mark-termination escape hatch) — every pytest-pinned literal survives.
4. **validate.sh** 1,117 → ~420: keep structural checks 1–16; delete check 17's literal
   prose pins and the closing-tip drift guard; port the genuine two-sided contracts:
   `## Scenarios`/`### Scenario:` (brainstorm ↔ tdd), `## TDD Summary`/`### Behaviors
   Implemented`/`### Coverage` (tdd ↔ pr), `### Refined plan` (plan-mode-handoff ↔ jira).
5. **Hooks.** session-start: drop the git-state block (native gitStatus covers it); prune
   heavy dirs from the depth-4 `find`s. Update the test-hooks.sh dirty-tree scenario.
6. **skill-writing-guidelines.md** (repo + init template): rewrite ~135 → ~80 lines.
   Delete the closing-tip mandate and Next Step section; keep smart-model principle,
   frontmatter rules (`disable-model-invocation`, no `name:`), 500-line cap, merge-vs-split
   criteria, degrees of freedom, shared-reference rule. New rule: cross-cutting references
   load conditionally (gate multi-repo detection behind "if cwd has no .git/").

## Per-skill targets (SKILL.md body; support files shrink per audit digests)

| Skill | Before | Target | Key cuts |
|---|---|---|---|
| init | 356 | ~180 | Inline claude-md-best-practices rules; one File-Semantics block; agents read refs themselves; 3 architecture templates → 1 |
| tdd | 413 | ~180 | Delete worktree-orchestration ref (6 lines inline); one per-phase report rule instead of 3 templates; agents fold into quality-gate.md; anti-patterns ref → ~60 |
| code-review | 366 | ~160 | Parameterize GitHub/GitLab blocks; compress Step 3 routing to decision list; agents −40% |
| refactor | 310 | ~150 | One harness paragraph; merge validate+present steps |
| unit-test | 215 | ~110 | Keep pinned Step-1 router verbatim; conditional anti-patterns read |
| deep (new) | 3×~145 | ~150 | One skill + parameter table (target → --skill, progress path, loop ref, cap flag, focus) |
| brainstorm | 261 | ~150 | Inline spec template (exact headings preserved); Step 7 router → table + 2 prompts; + scaffold mode from spec-init (templates as real files) |
| jira | 222 | ~110 | mcp-detection merges into context-extraction; setup extracted to conditional ref |
| pr | 277 | ~130 | Keep platform/default-branch refs (shared with code-review); simplify Intent heuristic |
| commit | 138 | ~100 | + suggest mode (from commit-message) + branch mode (from branch); refs trimmed |
| worktree | 108 | ~50 | Inline multi-repo gate; keep worktree-setup.md (tdd reads it) |
| handoff | 132 | ~95 | Merge redact/write/verify steps |
| how-to-run | 215 | ~110 | detector agent 466 → ~300 (keep every regex/allowlist byte); sections ref 680 → ~150 |
| permissions | 113 | ~70 | Replace security-model table with 2 sentences |
| prompt | 227 | ~140 | Fold diagnostic-patterns in; templates.md → ~300; tool-routing → ~220 |
| reset | 255 | ~120 | `cmp -s` classification; drop fingerprint table |

## Contract inventory — must survive byte-for-byte

- `HARNESS_MODE_INLINE` routing in code-review/refactor/unit-test SKILL.md +
  `references/harness-mode.md` / `references/coverage-harness-mode.md` paths
  (test_skill_contract.py).
- `json:harness-output` fence + field names (`iteration`, `new_findings`,
  `pre_edit_content`/`post_edit_content`, `fixes_applied`, `fixes_skipped_persistent`,
  `no_new_findings`, `no_actionable_fixes`) — parsed by cli.py.
- Progress files `.claude/{code-review,refactor,unit-test}-deep-progress.json`; scratch
  prefixes `.claude/.deep-iteration-*`, `.claude/.unit-test-deep-*` (git.py globs).
- Status vocabulary in `context-injection-blocks.md` = constants.py/findings.py strings.
- orchestrator-loop-single.md: `skills/<base-skill>/SKILL.md`, `references/harness-mode.md`,
  `HARNESS_MODE_INLINE`, "Read the base SKILL.md"; -paired.md additionally
  `skills/unit-test/SKILL.md`, `skills/refactor/SKILL.md`, `coverage-harness-mode.md`,
  and heading "Conditionally dispatch the refactor phase" followed by `cli snapshot`.
- Six termination reasons backticked in harness-mode.md.
- `## Scenarios`/`### Scenario:` headings (brainstorm spec template ↔ tdd);
  `## TDD Summary`/`### Behaviors Implemented`/`### Coverage` (tdd ↔ pr);
  `### Refined plan` exact heading (plan-mode-handoff ↔ jira refresh/codebase-analysis).
- Frontmatter: `description`, `disable-model-invocation: true`, no `name:`, quoted
  `argument-hint`; every skill dir keeps SKILL.md + README.md.
- expected-outputs.yaml behavioral pins (retargeted, not weakened): init artifacts +
  "Clarity over cleverness"; `.optimus-version` written only by init; restrict-paths.sh
  install path; HOW-TO-RUN.md "Prerequisites"; `feat/` branch prefix (now via
  `/optimus:commit branch`); read-only guarantees of `commit suggest` and `prompt`.

## Test/tooling alignment (phase 3)

- `test_skill_contract.py`: ORCHESTRATOR_CONTRACTS collapses to one `deep` entry
  (both loop refs, `### Plugin root`, `Re-entry guard`, `--test-command`, `cli baseline`,
  `--yes` bypass sentence); byte-identity test deleted; BASE_SKILL_ROUTES unchanged.
- `test-skills.sh` matrix + help: `branch` → `commit` (branch mode), `commit-message` →
  `commit` (suggest mode); expected-outputs.yaml keys follow.
- `test-hooks.sh`: dirty-tree scenario updated for the removed git-state line.
- cli.py docstring/help strings that name `*-deep` slash commands → `/optimus:deep`.
- Root README (rewrite, ~170 lines, 2.x→3.0 migration table), CONTRIBUTING tree,
  `.claude/docs/architecture.md`, `.claude/CLAUDE.md` skill count.
- `plugin.json` 3.0.0 + README badge.

## Execution order

1. Shared infra (serial, this session): references surgery, agents, hooks, validate.sh,
   skill-writing-guidelines.
2. Skill rewrites (parallel agents, one per skill dir; merge sources left on disk as
   reading material until phase 3).
3. Deletions (workflow, spec-init, branch, commit-message, 3× *-deep) + docs + manifests +
   test alignment (serial).
4. Full gate: `bash scripts/validate.sh && bash scripts/test-hooks.sh && python -m pytest test/`.
5. Adversarial verification fan-out; fix findings; final summary with before/after counts.

---

# Execution record

Executed 2026-07-16/17 on `feat/v3-lean` in one autonomous session; verified against tool output.

- **Audit:** 26-agent parallel workflow (one per skill + 4 infra auditors) against master 29e96a5, run BEFORE reading PR #163; per-skill digests with essential-behavior inventories drove every rewrite.
- **Phase 1 (orchestrating session, serial):** skill-handoff.md deleted (plan-mode carve-out preserved at brainstorm/references/plan-mode-handoff.md), scope-expansion-rule merged into shared-agent-constraints, agent-architecture/sdd-mapping shrunk to contracts, plugin agents trimmed + extension pattern removed, SessionStart hook git-state block dropped (test scenario updated), skill-writing-guidelines rewritten.
- **Phase 2 (parallel agents, one per skill dir):** 18 jobs — 16 skills + validate.sh + harness-reference trims. First run completed 10/18; 8 hit a session usage limit mid-run. Their partial edits were REVERTED to master state and re-run fresh after the limit reset (lesson inherited from PR #163: never trust a partially-completed fan-out). Second run: 8/8 clean.
- **Phase 3 (serial):** dead dirs deleted, orphaned cross-skill references deleted, test_skill_contract.py collapsed to one deep-orchestrator contract, test-skills.sh matrix retargeted (commit-suggest / commit-branch), cli.py user-visible strings, root README (with 2.x→3.0 migration table), CONTRIBUTING, .claude docs, plugin.json 3.0.0 + badge.
- **Verification:** 8 adversarial auditors (stale-sweep, contract chains, deep-vs-CLI, reset-vs-init, 3× dropped-behavior vs audit digests, fresh-user walkthrough) → 12 confirmed findings, all fixed. Notables: deep's coverage-target baseline resume-skip read a field that only exists for the other targets (`iteration.completed` vs `cycle.completed`); reset's architecture.md structure check misclassified every legitimately generated file; reset's monorepo inventory missed subproject coding-guidelines.md.
- **Gate at HEAD:** validate.sh 13/13, test-hooks.sh 45/45, pytest 442/442 (jq/python-dependent validate checks SKIP locally, CI covers them).
- **Sizes:** total instruction footprint (skills + references + agents + hooks + validate.sh) 17,940 → 9,511 lines (−47%); SKILL.md bodies 4,457 → 1,981 (−56%).
- **Open item:** `bash scripts/test-skills.sh --fresh --all --worktree` (paid, needs authenticated headless `claude`) not run — run before merging; matrix covers init, permissions, commit-suggest, commit-branch, how-to-run, prompt.
