# optimus-claude 3.0 modernization — plan and execution record

Written 2026-07-16 on `feat/v3-modernization`. Part 1 (through "Considered and
rejected") is the plan as decided **before** execution, produced from a 27-agent
audit of every skill and cross-cutting area against Anthropic's current guidance
([Claude Code best practices](https://code.claude.com/docs/en/best-practices),
[skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices))
plus a top-down cohesion review. Part 2 (["Execution record"](#execution-record--what-actually-happened))
documents what was actually done, where execution diverged from the plan, how it was
verified, and what a future session needs to know before touching anything. The plan
sections are preserved as written — where reality differs, the execution record wins.

## Diagnosis

The 2.x plugin is two products fused together: a defensible core — project-tailored
context generation (guidelines, CLAUDE.md, hooks, test infra), guideline-enforced
quality loops, and a resumable deep-fix harness with deterministic test bisection —
and a grab-bag of git/PR/prompt conveniences that current Claude models handle natively.
The connective tissue built to make 22 skills feel coherent is itself the anti-pattern:
CI-pinned verbatim closing-tip wording (`references/skill-handoff.md` + 679 lines of
literal-string pins in `validate.sh`), scripted AskUserQuestion dialogs, hand-rolled
report templates, and per-edge-case conversational choreography. Skills written for
earlier models now over-prescribe capable ones and degrade output.

## The v3 lineup — 8 skills, one story

*Generate your project's standards, enforce them in every quality pass, sustain the
fix loop across sessions.*

| Skill | Role |
|-------|------|
| `/optimus:init` | Generate/audit project context: CLAUDE.md, coding guidelines (+ skill-writing lens), formatter hooks, test infrastructure. Optional steps absorbed from dropped skills: safety guardrails (branch-protection / precious-file PreToolUse hook, from `permissions`) and a HOW-TO-RUN.md onboarding doc (radically simplified from `how-to-run`). |
| `/optimus:spec` | One design front door (replaces `brainstorm` + `spec-init` + `jira`): inline idea, JIRA ticket via MCP, or greenfield steering-cascade scaffold → explored, approved spec at `docs/specs/` with optional Given/When/Then Scenarios that `/optimus:tdd` consumes directly. |
| `/optimus:tdd` | Red-Green-Refactor implementer: Iron Law, vertical slicing, bug-fix regression gate, per-behavior commits, quality gate agents. Consumes specs automatically. |
| `/optimus:unit-test` | Coverage-gap discovery + convention-following tests. Conservative (never refactors source). Harness-compatible (coverage-harness-mode). |
| `/optimus:refactor` | Project-wide refactor against the project's own guidelines + testability barriers. Harness-compatible (harness-mode). |
| `/optimus:code-review` | Guideline-aware diff/PR review — the project-standards complement to the built-in `/code-review`. Harness-compatible (harness-mode). |
| `/optimus:deep` | One resumable orchestrator (replaces `code-review-deep` + `refactor-deep` + `unit-test-deep`): `deep review` / `deep refactor` / `deep coverage` — fresh subagent per iteration, deterministic bisection, on-disk resumable state via `scripts/harness_common`. |
| `/optimus:reset` | Deterministic uninstall of everything init installs (manifest updated for v3: guardrail hook, HOW-TO-RUN.md, `.optimus-version`). |

## Per-skill verdicts (all 22)

**Dropped — a built-in or the bare model does it as well or better (8):**

| Skill | Replacement | Reason |
|-------|-------------|--------|
| `branch` | native git competence | Entire payload is `git checkout -b` with a sensible name — a one-line ask. |
| `commit` | native git competence | Claude Code already writes conventional commits capturing conversation context, splits multi-concern diffs, warns on secrets, branches off protected branches. |
| `commit-message` | native git competence | Read-only sibling of `commit`; same coverage. |
| `worktree` | native worktrees | Claude Code has per-session isolated worktrees and parallel desktop sessions; "install deps and run baseline in the new tree" is an ask, not a skill. |
| `prompt` | bare model | Prompt-crafting is core 2026 model competency; 1,225 lines of templates/diagnostics over-prescribe it. Also off-mission (targets "any AI tool", not this project). |
| `pr` | native gh/glab competence | Claude writes well-structured PR descriptions from the conversation natively. The pinned `## Intent` heading contract dies; code-review reads whatever PR description exists as a soft intent signal. |
| `workflow` | native dynamic workflows | The skill wrapped the native Workflow feature; its residual delta (green baseline, branch, verify) is one paragraph of prompt, not a skill. |
| `handoff` | bare model on request | "Write a redacted, self-contained handoff doc" is handled natively; session resume/fork covers same-tool continuation. Off-mission for a project-standards plugin. |

**Merged (7):** `brainstorm`, `spec-init`, `jira` → new `spec` (one front door; JIRA
write-back enrichment and implementation-ticket spawning are dropped as scope creep —
native MCP covers on request; distilled tickets are written to `docs/specs/` — the
separate `docs/jira/` location dies). `permissions`, `how-to-run` → optional init
steps (the tested restrict-paths hook survives as a template; HOW-TO-RUN.md becomes
a ~1-page grounded-generation step, down from 2,301 lines across 11 files).
`code-review-deep`, `refactor-deep`, `unit-test-deep` → new `deep` (the three
SKILL.mds were near-clones over the same loop references and CLI).

**Rewritten much smaller (4):** `init` (flagship; keeps detection→generate→audit→verify
flow, absorbs the two optional steps; scripted dialog choreography and rigid report
templates go), `tdd` (413→~150 lines; keeps Iron Law, vertical slicing, regression
gate, spec consumption, per-behavior commits, quality gate; drops AskUserQuestion
scripts, milestone choreography, worktree orchestration, verbatim report blocks),
`code-review` (keeps guideline agents ×2 + code-simplifier + conditional
test-guardian/contracts, PR mode with soft intent signal, validation pass, harness
routing; drops scripted templates and the `## Intent` heading machinery),
`spec`/`deep` (new files per above).

**Trimmed in place (3):** `refactor`, `unit-test` (harness inner engines — keep
HARNESS_MODE_INLINE routing and JSON contracts intact, cut scripted prose),
`reset` (keeps template-comparison classification; manifest updated for v3 files).

## Shared infrastructure

**references/ (11 → 7 files):**
- Keep (machine contracts, LOW freedom is correct here): `harness-mode.md`,
  `coverage-harness-mode.md`, `harness-init-resume.md`, `context-injection-blocks.md`
  (status vocabulary is a verbatim contract with `constants.py`/`findings.py`).
- Merge: `orchestrator-loop-single.md` + `orchestrator-loop-paired.md` →
  `orchestrator-loop.md` (shared body + paired-cycle delta section).
- Trim: `shared-agent-constraints.md` (absorbs the one non-default idea from
  `scope-expansion-rule.md`; drops the budget-registry meta-rule),
  `agent-architecture.md` (shrinks to the "prompt assembly at dispatch time" rule +
  short two-tier summary — the rest duplicated `.claude/docs/architecture.md`).
- Delete: `skill-handoff.md` (verbatim-tip machinery; plan-mode handoff choreography
  dies with brainstorm — the spec skill runs its design conversation in-conversation),
  `sdd-mapping.md` (3-line precedence rule folds into spec), `scope-expansion-rule.md`.

**agents/:** keep `code-simplifier.md` and `test-guardian.md`, trimmed to ~30 lines
each (quality criteria + autonomy split + missing-doc fallbacks; drop restatements of
default model behavior). Keep the two-tier architecture and the skill-writing lens
routing as a few lines.

**hooks/:** keep the SessionStart hook; drop its git-state block (Claude Code injects
gitStatus natively) and soften the init nag. `hooks.json` unchanged.

**Cross-skill reference moves:** `skills/pr/references/platform-detection.md` and
`default-branch-detection.md` → `skills/code-review/references/` (code-review's PR
mode needs them; pr dies). tdd's reads of `skills/commit/references/*` (branch naming,
commit format) are deleted — native competence. `skills/tdd/references/spec-context-detection.md`
simplifies to docs/specs/-only and moves to `skills/spec/references/` ownership if
cleaner (tdd may keep reading it cross-skill).

## Validation & tests

- `validate.sh` (1,116 → ~420 lines): keep structural checks 1–14 and 16 (frontmatter,
  cross-reference resolution, orphans, syntax, manifests, version bump, reference
  depth); generalize check 15 to iterate `agents/*.md`; **delete section 17
  ("load-bearing wiring", 679 lines of literal prose pins) and the closing-tip drift
  guard entirely**; drop the CONTRIBUTING.md tree assertion (tree collapses to
  top-level dirs). Keep exactly one tiny cross-skill contract check: `## Scenarios` /
  `### Scenario:` present in both `skills/spec/references/spec-format.md` and
  `skills/tdd/SKILL.md` (a real producer/consumer grep contract that survives v3).
- `test-hooks.sh`: keep formatter + restrict-paths suites (templates survive under
  init); update session-start scenarios for the hook's slimmed output.
- `test-skills.sh` + `expected-outputs.yaml`: remove rows/stanzas for deleted skills
  (commit-message, branch, prompt, how-to-run); collapse duplicate init stanzas;
  replace prose pins (e.g. 6× "Clarity over cleverness") with structural assertions.
  Fixtures stay (init still supports all those stacks).
- `test/harness-common/test_skill_contract.py`: repoint orchestrator pins to
  `skills/deep/SKILL.md` (three modes) and the merged `orchestrator-loop.md`.

## Harness code (scripts/harness_common/, ~10% trim)

Per the harness audit — the bisection/resume/state core is sound and stays. Cut dead
surface with its tests: legacy content-swap bisect in `fixes.py` (unreachable since
snapshot-based bisect), `mark-termination` subcommand, `snapshot --include-stash`
flag, `scope_text` provenance field, and `reporting.detect_test_command` (all three
orchestrator entry points pass `--test-command` explicitly; make it required).

## Documentation

Every doc rewritten to the new state in the same pass: root `README.md` (~150 lines,
one-line skill blurbs, one workflow paragraph instead of six chained tables, a 2.x→3.0
migration table like the existing 1.x one, updated Complementary Tools), `CONTRIBUTING.md`
(tree collapsed, testing deduped, stale version examples fixed), `.claude/CLAUDE.md`
(targeted read-pointers instead of mandatory full-README preload), `.claude/docs/architecture.md`
(de-hardcode counts, new lineup/dataflow), `.claude/docs/skill-writing-guidelines.md`
**rewritten** (~70 lines: delete the verbatim closing-tip mandate and fan-out-count
rule, replace with high-freedom guidance; keep the smart-model principle, 500-line cap,
plugin frontmatter rules, merge-vs-split criteria), the init **template**
`skill-writing-guidelines.md` mirrored, `.claude/docs/testing.md` (light touch),
per-skill READMEs for all 8 survivors. `coding-guidelines.md` (repo + template) is
healthy — unchanged.

## Version

`plugin.json` → `3.0.0`; README badge to match; no `ref` in `marketplace.json`.

## Execution order

1. **Shared infra first (serial):** reference merges/deletions, agents/ trim, hook
   trim, validate.sh rewrite — fixes the layout contract every rewriter depends on.
2. **Skill work (parallel agents, each confined to its own `skills/<name>/`):**
   init, spec, tdd, code-review, refactor, unit-test, deep, reset. Deletions of the
   13 dead skill directories happen with step 1.
3. **Docs pass (serial):** root README, CONTRIBUTING, .claude/*, version bump.
4. **Test alignment:** test-skills matrix, expected-outputs, test_skill_contract,
   session-start tests, harness code trims + their tests. Full suite green.
5. **Adversarial verification:** fresh agents audit every doc claim against the final
   tree; fix findings; evidence-audited summary.

## Risks & mitigations

- The closing-tip system spans validate.sh, skill-writing-guidelines, and 10+
  SKILL.mds — removed as a unit in step 1 so nothing half-enforces it.
- Surviving skills must not recommend deleted skills — step 5 greps for
  `/optimus:(branch|commit|commit-message|worktree|prompt|pr|workflow|handoff|brainstorm|spec-init|jira|how-to-run|permissions|.*-deep)` across the tree.
- 2.x scripted entry points (`claude -p "/optimus:code-review-deep --yes"`) break —
  acceptable per the no-backward-compat mandate; README migration table covers it.
- reset must learn init's expanded v3 manifest or uninstall is incomplete — its
  rewrite prompt includes the full v3 file inventory.
- The July 2026 51-finding audit backlog (memory) is superseded: most findings target
  deleted or rewritten files; the few that survive (e.g. init README reference-table
  drift) are subsumed by the rewrites.

## Considered and rejected

- **Keeping `pr` for the `## Intent` → code-review handoff:** the pinned-heading
  contract is machinery a model doesn't need — reviewers read PR descriptions
  naturally. Not worth two coupled skills.
- **Keeping `workflow` as the parallel implementer peer of tdd:** its delta over the
  native feature is a paragraph of prompt; tdd's closing guidance mentions the native
  option instead.
- **Keeping `handoff` (audit said keep-trim):** genuinely not covered by session
  resume, but a capable model writes the same doc on a one-line request; off-mission
  and cut for cohesion.
- **Standalone `how-to-run`:** the deliverable is defensible; 2,301 lines + ~500
  lines of validator pins to produce one markdown file is not. Survives as a lean
  init step.
- **Dropping go/rust/csharp fixtures:** they still serve surviving init behavior;
  kept.
- **Renaming progress files / CLI identifiers for the deep merge:** CLI contracts are
  stable and tested; the merge is markdown-layer only.

---

# Execution record — what actually happened

Everything below was executed on 2026-07-16 in a single autonomous session and is
verified against tool output from that session. Final state vs master:
**144 files changed, +3,252 / −15,823**. Test suite at HEAD: `validate.sh` 13/13,
`test-hooks.sh` 45/45, `pytest test/` 393/393 (the two `test_format_python_hook.py`
tests need the venv `Scripts` dir on PATH for black/isort — a machine quirk, not a
repo issue).

## Commit map (5 commits on `feat/v3-modernization`)

| Commit | Content |
|---|---|
| `8d336fd` | This plan file (pre-execution version). |
| `237276d` | **Phase 1 — shared infrastructure.** Deleted the 8 native-covered skills; deleted `skill-handoff.md`, `sdd-mapping.md`, `scope-expansion-rule.md`; merged the two orchestrator-loop refs into `references/orchestrator-loop.md`; trimmed `shared-agent-constraints.md`, `agent-architecture.md`, both plugin agents; slimmed `hooks/session-start` (git-state block removed — one test-hooks scenario flipped from "reports uncommitted changes" to "still silent"); rewrote `validate.sh` 1,116→413 lines; moved `platform-detection.md` + `default-branch-detection.md` from pr→code-review and the permissions templates under init (`templates/hooks/restrict-paths.sh`, `templates/permissions-settings.json` — test-hooks.sh path updated). |
| `e0b56c0` | **Main overhaul.** The 8 skill rewrites (see below), deletion of the 8 merge-source dirs, harness code trims + full test alignment, all root/meta docs rewritten, version 3.0.0. |
| `90da714` | Post-sweep fixes: `retained — revert failed` status removed from the two context-block docs (it died with the legacy bisect), `harness-init-resume.md` retargeted from "three `*-deep` skills" to `/optimus:deep`, guardrails-hook header comments repointed from the dead permissions skill to init. |
| `76aa633` | All 26 findings from the adversarial verification pass (list below). |

## How the work was executed

Four multi-agent operations, all with per-agent transcripts in the session's workflow
journals (not accessible to future sessions — the durable evidence is this file and
the commits):

1. **Audit workflow — 27 agents** (~1.7M tokens): one auditor per skill (22), four
   cross-cutting auditors (shared references/agents/hooks, validate.sh + test infra,
   Python harness, meta-docs), one top-down "cohesion critic" that designed the ideal
   lineup from first principles. Each returned a structured verdict
   (drop/merge/rewrite/keep-trim/keep) with cut/keep lists and dependency evidence.
   The per-skill (bottom-up) and critic (top-down) verdicts diverged on four skills —
   `workflow`, `pr`, `handoff` (bottom-up said rewrite/keep-trim, critic said drop)
   and `how-to-run` (standalone rewrite vs init merge). The orchestrating session
   adjudicated each; the critic's position won all four, for the reasons recorded in
   "Considered and rejected" above.
2. **Rewrite workflow — 8 agents in parallel**, each confined to its own
   `skills/<name>/` directory, all given the same shared contract: the new
   `.claude/docs/skill-writing-guidelines.md` (deliberately written *before* this
   phase so rewrites would embody it), the final lineup (so closing suggestions only
   name surviving skills), the exact machine-contract tokens to preserve, and
   validator invariants (orphan rule, path resolution, portable mktemp).
   Merge-source directories (brainstorm, jira, the *-deep trio, …) were left on disk
   as readable source material until all agents finished, then deleted.
3. **One synchronous agent** aligned `test/harness-common/` with the harness trims
   (387→393 tests over the session as contract tests were added).
4. **Verification workflow — 7 adversarial auditors** (root docs, init+reset,
   spec+tdd, review/refactor/unit-test, deep-vs-CLI-source, repo-wide stale sweep,
   fresh-user walkthrough), each returning findings with file:line evidence.

The orchestrating session did the cross-cutting surgery itself (phase 1, the harness
Python trims, `test_skill_contract.py` repointing, root docs, version bump) because
those define contracts the parallel agents depended on.

**Incident worth knowing about:** the first verification run returned
`{"findings": []}` — but all 7 agents had actually errored on a session usage limit,
so the empty list was *not* evidence of accuracy. It was treated as a failed run.
The mechanical half of the verification (stale-token greps, deep-vs-CLI flag/constant
comparison, init-vs-reset manifest diff) was done inline by the orchestrator, three
stragglers were fixed (`90da714`), and the LLM audit was re-run after the limit reset
— it then produced the 26 real findings fixed in `76aa633`. Lesson for future
sessions: an empty result from an errored fan-out is a failure, not a pass.

## Deviations from the plan

- **Sizes landed smaller than planned.** tdd 105 lines (plan said ~150), init 131
  (plan implied 170–200), spec 111, deep 127, code-review 204, refactor 117,
  unit-test 116, reset 137. Total SKILL.md footprint 4,457 → 1,037 lines; all
  skill/reference/agent markdown ~15,200 → ~4,885. Agents were explicitly told not to
  pad to targets.
- **`spec-context-detection.md` was deleted, not moved.** tdd inlined its 4-step
  resolution (explicit path → newest `docs/specs/` with `Status: Approved` → inline
  task → ask); spec owns the format contract in `skills/spec/references/spec-format.md`.
  Also deleted outright: tdd's `coverage-detection.md` (now two lines inline) and
  `tdd-worktree-orchestration.md`; init's `readme-section-detection.md` (sole
  consumer was the dead how-to-run); all five `skills/jira/references/*` (nothing
  ported — the spec skill's JIRA path is a read-only-MCP stance plus paste fallback,
  not a port of the extraction machinery).
- **code-review's bug-detector + security-reviewer merged into one
  `correctness-security.md` agent** (fan-out is now 4–6: correctness-security,
  guideline ×2, code-simplifier, + conditional test-guardian and contracts-reviewer).
  The Intent Mismatch category survives but is judged against the PR/MR description
  as a whole — the `## Intent` heading gate was fully removed (last remnant found by
  the verification pass in `references/context-injection-blocks.md`).
- **`test_skill_contract.py` was loosened where it pinned prose.** The old test
  demanded an exact `--yes` bypass sentence in each orchestrator; the new test checks
  `--yes` and `--resume` are documented — behavioral, not verbatim. The plugin-root
  byte-identity test across three orchestrators became a single existence check (one
  orchestrator now).
- **init landed with no argument handling** — the verification pass caught its README
  advertising a "focus" argument the SKILL never implemented; the example was dropped
  rather than the feature added (YAGNI).
- **`skills/init/templates/settings.json`** (formatter-hook wiring template) already
  existed and stayed; the permissions template landed beside it as
  `permissions-settings.json`. Both are referenced by reset's surgical cleanup.

## The 26 verification findings (all fixed in `76aa633` unless noted)

Themes, so a future session knows what class of drift to watch for:

1. **reset's manifest vs init's actual behavior** (5 findings): claimed
   per-subproject `coding-guidelines.md` copies init never creates (fixed in 3
   places); missed the workspace-root HOW-TO-RUN.md init generates for multi-repo
   workspaces; missed that init's guardrails step adds `mcp__<server>` allow entries
   beyond the permissions template (reset now removes those too).
2. **Deleted-era remnants** (6): the `## Intent` heading gate in
   `context-injection-blocks.md`; `test-skills.sh` help/usage text listing five dead
   skills; `cli.py` argparse description and `--allow-red` help naming
   `unit-test-deep` and a never-existed `--allow-red-baseline` flag; a stale
   quotation of the old base-agent wording in code-review's `code-simplifier.md`.
3. **Docstring/doc drift from my own harness trims** (4): `check-termination` enum
   missing `parse-failure`; missing `baseline` line in the CLI docstring;
   `cmd_baseline` "fresh run only" claim contradicting deep's resume-with-zero-
   iterations rule; `harness-init-resume.md` quoting an error string
   ("No test command") the CLI no longer emits.
4. **Cross-doc consistency** (5): README's "only automatic component" claim vs the
   two model-invocable plugin agents (softened to "only always-on component");
   unit-test README's "passively flags after code changes"; `.optimus-version`
   "never touch it" rule vs reset legitimately deleting it; quality-gate.md's
   "project-level agents" (a tier that doesn't exist); platform-detection.md's
   "shared by multiple skills" preamble (single consumer now).
5. **Stale pointers** (2): restrict-paths.sh header promising a pattern list "in the
   skill's README" that no README carries (both the template and this repo's
   installed copy now point at `is_precious()` itself); init README's unsupported
   usage example.

## Contract inventory — do not break these without updating their enforcers

| Contract | Enforced by |
|---|---|
| `## Scenarios` / `### Scenario:` literal headings in `skills/spec/references/spec-format.md` **and** `skills/tdd/SKILL.md` | `validate.sh` check 17 |
| `HARNESS_MODE_INLINE` + `references/harness-mode.md` routing in code-review/refactor SKILL.md; + `references/coverage-harness-mode.md` in unit-test | `test_skill_contract.py` |
| `skills/deep/SKILL.md` must name `references/orchestrator-loop.md`, all three base SKILL.md paths, `### Plugin root`, `Re-entry guard`, `--test-command`, `cli baseline`, `` `--yes` ``/`` `--resume` `` | `test_skill_contract.py` |
| Progress-file names `.claude/{code-review,refactor,unit-test}-deep-progress.json` | `constants.py` `DEFAULT_PROGRESS_FILES` + tests |
| Temp-file prefixes `.claude/.deep-iteration-*`, `.claude/.unit-test-deep-*` (in `orchestrator-loop.md`) | `git.py` `_HARNESS_STATE_EXCLUDES` un-stage patterns |
| Iteration-context status vocabulary (`fixed`, `reverted — test failure`, `reverted — attempt 2`, `skipped — apply failed`, `persistent — fix failed`) in `context-injection-blocks.md` | `constants.py` / `findings.py`; note `retained — revert failed` no longer exists |
| harness JSON output schema (`json:harness-output`, `pre/post_edit_content`, `no_new_findings`, …) in `harness-mode.md` / `coverage-harness-mode.md` | `cli.py parse` + `test_skill_contract.py` round-trip |
| SKILL.md frontmatter: `description` (≤1024), `disable-model-invocation: true`, **no** `name:` field, quoted `argument-hint` | `validate.sh` check 3 |
| Every skill dir has SKILL.md + README.md; README lists every skill; every `$CLAUDE_PLUGIN_ROOT` path resolves; refs ≤2 deep; no orphans in references/templates/agents dirs | `validate.sh` checks 8, 9, 12, 13, 16 |
| `cli init` requires `--test-command` (the CLAUDE.md parser is gone) | `cli.py` + `test_cli.py` |
| `bisect_fixes` requires `reset_to_clean` (raises ValueError; legacy content-swap bisect and `revert_single_fix` deleted) | `test_fixes.py` |

## Open items for the next session

- **`test-skills.sh` was updated but never executed** — it needs an authenticated
  `claude` CLI and real headless runs. Run
  `bash scripts/test-skills.sh --fresh --all --worktree` before merging; only init
  is in the matrix now (spec/deep/tdd are interactive or long-running by design).
- `validate.sh`'s jq-dependent checks (plugin.json validity, version-bump/badge,
  hooks.json) and the Python template-syntax check **SKIPped locally** (tools not on
  the Git Bash PATH of the machine used) — CI runs them; the version/badge pair was
  verified manually (`3.0.0` both places).
- Decide whether this V3-PLAN.md ships in the release or is dropped before merge.
- Feature-branch install testing (CONTRIBUTING's `ref` + `#branch` procedure) was not
  done; if wanted, remember the `ref` must be removed before merging (validate.sh
  enforces its absence).
- The branch is local-only — nothing was pushed.
- Session memory (`~/.claude/.../memory/`) was updated: the 51-finding July-7 audit
  backlog is marked superseded by this overhaul; a `v3-modernization-2026-07` entry
  points future sessions at this file.
