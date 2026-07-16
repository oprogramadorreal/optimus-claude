# optimus-claude 3.0 modernization plan

Written 2026-07-16 on `feat/v3-modernization`. Produced from a 27-agent audit of every
skill and cross-cutting area against Anthropic's current guidance
([Claude Code best practices](https://code.claude.com/docs/en/best-practices),
[skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)),
plus a top-down cohesion review. Full per-file audit evidence lives in the session
scratchpad (`audit-verdicts.json`); this file records the decisions and why.

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
