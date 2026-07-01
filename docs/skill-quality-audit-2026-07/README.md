# Skill quality audit — 2026-07-01 (working document)

Maintainer-facing work package. Not part of the plugin's runtime — none of the skills reference this folder. Delete the folder when the work is done.

## What this is

A full-plugin quality assessment of all 22 skills plus the repo's own authoring conventions, measured against:

- Anthropic, "Skill authoring best practices" — https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- Anthropic, "The Complete Guide to Building Skills for Claude" (PDF) — https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf

**Method:** 52 agents — one assessor per skill + 4 convention-level auditors, each followed by an adversarial verifier that (a) re-checked every quote against the files, (b) screened every redundancy claim against `scripts/validate.sh` and `test/expected-outputs.yaml` enforcement, (c) refuted taste-only findings, and (d) hunted for missed high-severity issues. 4 findings were refuted (listed per skill in [findings.md](findings.md) so they don't get re-raised). Snapshot: branch `chore/skills-quality-assessment` at `8cef3e4` (clean tree), 2026-07-01.

**Headline results:** no skill needs a rebuild — every diagnosis supports targeted refinement. The single highest-leverage fix is convention-level (see [C1](#c1-the-description-convention-optimizes-a-mechanism-the-plugin-disables) below). The collection's structure, progressive disclosure, and feedback-loop discipline are genuinely strong; the surviving problems concentrate in **edge-of-flow correctness** (failing-test/rollback paths in harness mode, safety promises without verification gates, destructive paths without precondition checks) and a handful of **cross-file contradictions**.

## How to work on these improvements (read this first)

1. **Read the prerequisites** before editing anything: `.claude/CLAUDE.md`, `.claude/docs/skill-writing-guidelines.md` (mandatory before skill/agent/reference edits), `CONTRIBUTING.md`. For changes to `scripts/` use `.claude/docs/coding-guidelines.md` instead.
2. **Pick a work item** from the ranked list below, then read only that item's section in [findings.md](findings.md) — it is large (~250k chars); never read it wholesale. Each section is self-contained: quotes, locations, problem statements, concrete fixes, and best-practice citations (BP ids resolve in the [reference section](#best-practice-reference) below).
3. **Re-locate every quote before editing.** Line numbers in findings were captured at `8cef3e4` and will drift; the verbatim quote is the anchor — grep for it. If a quote no longer exists, the finding may already be fixed or the file restructured: re-verify the problem before acting.
4. **Check token pinning before touching any quoted line.** Many contract strings are pinned by `scripts/validate.sh` or `test/expected-outputs.yaml` (e.g. tdd/workflow→pr summary headings, brainstorm↔tdd scenario tokens, how-to-run's "guided in-chat walkthrough", handoff's `### Inlined (not yet on remote)`). Grep both files for any phrase you're about to change; several fixes explicitly name tokens to preserve. Findings that *looked* like removable duplication but are test-enforced were already refuted — trust the surviving list, but re-check enforcement whenever your edit deviates from the proposed fix.
5. **Verifier verdict semantics:** `CONFIRMED` — implement the proposed fix. `ADJUSTED` — the verifier's revised severity/fix **supersedes** the assessor's; implement the revised version. `REFUTED` — do not implement (kept in findings.md for the record). `Found by verifier` items are as real as confirmed ones (they passed the same evidence bar).
6. **Diagnose before trusting, even here.** These findings were adversarially verified, but you are a third reader: if the code/markdown contradicts a finding, believe the file and note the discrepancy in this README's changelog rather than forcing the fix.
7. **Repo mechanics (non-negotiable):**
   - Run `bash scripts/validate.sh && bash scripts/test-hooks.sh && python -m pytest test/harness-common/` after every batch of edits.
   - Bump the version in `.claude-plugin/plugin.json` and the README badge together, once per meaningful published change.
   - Never leave a `ref` field in `marketplace.json` on master.
   - After any skill change, verify the skill's `README.md` and the root `README.md` row still match behavior (validate.sh checks listing, not wording — wording drift is on you, and several findings below are exactly that).
   - If you touch `skills/permissions/templates/hooks/restrict-paths.sh`, re-copy it into this repo's own `.claude/hooks/` — the live copy has drifted 3× before.
8. **Style of remedy:** diagnose honestly, remedy conservatively. Prefer the leanest fix that resolves the finding — when a finding offers two remedies, the maintainer's standing preference is the lean / high-model-latitude option. Don't restructure adjacent content while passing through (the guidelines' own "drive-by improvements" anti-pattern).
9. **Suggested batching:** one skill (or one convention) per commit/PR. Conventions first — C1 especially, since every future description edit should be written against the corrected standard. Within skills, follow the ranking. Cross-skill findings (C6) touch multiple files — keep each as its own coherent commit.
10. **Track progress in this file:** add a `## Changelog` entry per completed item (date, item id, commit) so a later session knows what's done.

## Ranking — improvement need, highest first

Scores are the adversarially verified 0–10 improvement-need scores (0–2 well-tuned, 3–4 minor polish, 5–6 moderate, 7–8 structural, 9–10 rebuild). No skill scored above 6; no rebuilds.

| # | Skill | Verified score | Dominant problem class |
|---|-------|:---:|------------------------|
| 1 | unit-test | 6 | missing guidance on failing-test paths (breaks harness contract) |
| 2 | permissions | 5 | unverified security-critical install; silent overwrite of user hook edits |
| 3 | handoff | 5 | redaction promise not actually enforced end-to-end |
| 4 | code-review | 5 | agents never given the diff; PR mode can review wrong local content |
| 5 | jira | 5 | factually wrong MCP tool tables disable features |
| 6 | init | 5 | monorepo testing.md placement contradiction |
| 7 | tdd | 5 | several advertised behaviors don't fire as written |
| 8 | how-to-run | 5 | over-specification; worst-in-repo description (1021/1024 chars) |
| 9 | workflow | 4 | destructive Discard advice without clean-tree precondition |
| 10 | reset | 4 | cleanup can disable hooks the user chose to keep |
| 11 | unit-test-deep | 4 | red-baseline silent rollback loop |
| 12 | refactor-deep | 4 | --resume bypasses the green-baseline gate |
| 13 | pr | 4 | post-rebase push has no failure-mode guidance |
| 14 | prompt | 4 | contradictory CoT guidance across references |
| 15 | spec-init | 4 | multi-repo branch silently breaks the core handoff promise |
| 16 | refactor | 4 | its guideline agent skips the skill-authoring lens |
| 17 | commit | 4 | secrets-rule conflict; message generated before untracked decision |
| 18 | worktree | 4 | shared guard embeds contradicting policy; failing baseline unhandled |
| 19 | brainstorm | 3.5 | well-tuned; prose-deliverable routing quirk; spec overwrite check |
| 20 | code-review-deep | 3 | well-tuned; `--force` self-contradiction |
| 21 | branch | 3 | well-tuned; next-step advice contradicts own README |
| 22 | commit-message | 3 | well-tuned; near-exemplary minimal skill |

Convention topics (full detail in findings.md under "Convention-level audits"): descriptions-layer 4, authoring-conventions 5, shared-architecture 5, cross-skill-redundancy 5.

## Convention-level findings (higher leverage than any single skill)

These repeat across every skill, so fix them first. Full verified findings for each live in findings.md; this is the synthesis.

### C1. The description convention optimizes a mechanism the plugin disables

`.claude/docs/skill-writing-guidelines.md` "Description Quality" says *"Claude uses descriptions to select the right skill from potentially many available skills"* / *"they are injected into the system prompt"*, and Progressive Disclosure says *"Load only metadata (description) at startup."* With `disable-model-invocation: true` on all 22 skills, none of that applies: descriptions' real audience is a **human scanning the truncating `/` menu**. The convention drives keyword-stuffed near-cap descriptions (how-to-run **1021/1024** chars — and validate.sh checks presence only, so the next added capability breaks the platform cap silently; jira 710, workflow 707, refactor 704).

**Fix:** rewrite the Description Quality section for the real audience — lead with the differentiating verb phrase, target ~250–450 chars, keep what+when accuracy against actual behavior — and correct the "Load only metadata at startup" bullet to the plugin's actual loading model (description surfaces in the `/` menu and listings; SKILL.md loads at explicit invocation).

**Scope caution:** this fix targets the repo's OWN `.claude/docs/skill-writing-guidelines.md`. The *template* at `skills/init/templates/docs/skill-writing-guidelines.md` ships to user projects where model invocation may be enabled — its upstream-style advice is correct there. At most add a conditional note to the template ("if your skills set disable-model-invocation, write descriptions for the human menu"); do not port the rewrite wholesale.

Then re-tune the worst descriptions against the corrected standard (each has a finding in its skill's section): how-to-run (cut to ~350–450 chars, keep the validate.sh-pinned "guided in-chat walkthrough" phrase), refactor (three restatements of the two-goal framing), tdd (undeclared git side effects: branch/auto-commit/push; no /optimus:workflow pointer), unit-test-deep (missing "Requires a test command in .claude/CLAUDE.md" its two siblings carry), refactor-deep + code-review-deep (fresh-subagent fact stated twice each), spec-init (only "Use when…"-first description in the set — flip to verb-first), brainstorm + jira (name `docs/specs/` / `docs/jira/` save locations, which sibling skills treat as public API).

### C2. Guideline text contradicts the collection it governs

(a) *"Prefer gerund form for skill names: `processing-pdfs`, `analyzing-code`"* — all 22 actual names are short verb/noun slash-commands. Codify the real convention (names surface as `/optimus:<name>`). (b) The guidelines' Next Step section (*"Every skill must end with a recommendation… increases plugin adoption"*) contradicts `references/skill-handoff.md`, which allows *"'none' if the chain ends here"*. Align on the handoff doc; replace the adoption rationale with the user-value rationale. (c) Three SKILL.md-content rules (emoji ban, no [Step N/M] progress lines, imperative fan-out counts) live only in CONTRIBUTING.md — move or cross-reference them into skill-writing-guidelines.md, which is what the doc-loading path actually routes to.

### C3. Closing-tip wording exists in two mechanisms with no guard

~12 skills use the pointer form ("use Variant A per skill-handoff.md") while **18 verbatim inline copies** sit across 8 skills, unpinned by validate.sh — the exact drift pattern skill-handoff.md exists to prevent. Fix: converge on the pointer form, or add a validate.sh assertion that every `**Tip:**` line in `skills/*/SKILL.md` matches a canonical variant. (All 18 copies currently match — the risk is future drift, so the check is the lean fix.)

### C4. The two-tier agent extension pattern has an unresolved semantics gap

Plugin-level `agents/code-simplifier.md` says *"Direct simplifications — apply automatically"*; `agents/test-guardian.md` says run the test suite. Every skill-level extender that does `Read $CLAUDE_PLUGIN_ROOT/agents/<name>.md for your approach` is read-only; only code-review's code-simplifier wrapper carves the conflict out. Fix: add a "when read as an extension base, the dispatching prompt's constraints override the operational sections here" note to both plugin agents (and drop the one-off carve-outs, or keep them as reinforcement). Relatedly: no interactive SKILL.md states the prompt-assembly rule for fan-out agents (substitute the resolved plugin root; inline or absolutize bare `shared-constraints.md` references) even though the deep-mode dispatch templates state subagents don't inherit `$CLAUDE_PLUGIN_ROOT`. State it once at the pattern's home (`references/agent-architecture.md`) and point the launch steps at it.

### C5. references/harness-mode.md contradicts itself — under all three *-deep skills

Section 7's *"Skip any verification or validation step the base skill's normal (interactive) flow would perform"* countermands its own step 4 (*"Apply the same validation protocol as the skill's normal validation step"*) — and finding-validation is the only false-positive gate before deep mode auto-applies fixes. Fix: rescope to execution-based checks only, mirroring coverage-harness-mode.md's phrasing ("test-running/build/lint verification is skipped; finding validation still applies"). Also: its skill-step guidance is written in code-review vocabulary (branch-diff path, PR-description injection) that maps to nothing in refactor's steps, while the CLI populates `pr_description` for refactor-deep runs and refactor's context-blocks.md says the block "does not apply" — split the guidance into per-skill bullets or scope the pr_description paragraph to skills that define a PR/MR block.

### C6. Same procedure, different statements across skills

- **Branch-name collision:** three policies among five `branch-naming.md` consumers (branch/worktree auto-append `-2` via verbatim-duplicated blocks; commit asks the user; tdd/workflow silent). Add a Collision handling section to `skills/commit/references/branch-naming.md` as the single default and convert inline copies to pointers. Also fix its stale consumer list (omits `workflow`) and commit/README's "(shared with TDD)".
- **tdd multi-repo chimera:** *"process each repo independently: run Steps 1–9 inside the repo the user is targeting"* fuses unit-test's all-repos policy with brainstorm's single-repo policy — self-contradictory in one clause. Adopt brainstorm's wording.
- **Deep-skill CLI init/resume docs diverge:** code-review-deep tells users to re-invoke *the skill* with `--force` (a flag its own Step 1 doesn't parse, contradicting its line 112); siblings say re-invoke `init` with `--force`. Hoist shared cli.py init/resume semantics into a shared reference parameterized by progress-file path; keep per-skill deltas inline.
- **prerequisite-check divergence:** the shared reference prescribes warn-and-continue fallbacks; the three -deep skills hard-stop; unit-test/tdd/brainstorm/workflow inline their own stops. Document the strictness split centrally in prerequisite-check.md rather than unifying behavior.
- **CONTRIBUTING.md drift:** its project tree lists 20/22 skills (missing `spec-init/`, `handoff/`) and omits `sdd-mapping.md`. Optionally extend validate.sh's stale-README check to cover it.

## Already well-tuned — do not churn

- **commit-message** — near-exemplary minimal skill; the model for lightweight skills.
- **branch, code-review-deep, brainstorm** — small targeted fixes only.
- **The descriptions as a set** — uniform verb-first voice, consistent side-effect declarations, base→deep cross-pointers on all three pairs. Fix the named outliers; don't restyle the rest.
- **Deliberate redundancy confirmed deliberate** (verified against validate.sh/expected-outputs): orchestrator-loop single/paired overlap (paired defers to single as canonical, deltas carry inline rationale), handoff/tdd token-pinned templates, most of init's point-of-action overwrite-rule restatements. Leave these alone.
- Widely-praised patterns worth preserving as-is: tdd's Iron Law + horizontal-slicing diagram, code-review's Step 3 auto-route table and Step 6 validation loop, jira's MCP-safety architecture, how-to-run's anti-hallucination audit pairing, reset's fingerprint tables, the -deep skills' CLI-contract fidelity (verified against cli.py).

## Best-practice reference

Findings cite these ids. Distilled from the two Anthropic sources; treat as the shared vocabulary, not new rules to enforce wholesale.

- **BP1 Conciseness** — context is a public good; only add what Claude can't infer; every paragraph must justify its token cost.
- **BP2 Degrees of freedom** — match specificity to fragility: high freedom (text guidance) when many approaches are valid; low freedom (exact commands) only where fragile/sequence-critical. Default high.
- **BP3 Cross-model robustness** — instructions must work for weaker models (enough guidance) and stronger ones (no over-explaining).
- **BP4 Description field** — WHAT + WHEN, third person, ≤1024 chars, specific key terms; negative triggers where confusable with a sibling. (In this repo, tuned for the human `/` menu — see C1.)
- **BP5 Naming** — specific verb/noun names, consistent across the collection.
- **BP6 Body size** — SKILL.md under 500 lines; split when approaching.
- **BP7 Progressive disclosure** — SKILL.md as overview/pointers; reference content organized by consumer so irrelevant context isn't loaded.
- **BP8 Reference depth** — official: one level from SKILL.md (partial-read risk); this repo deliberately allows two (validate.sh-checked). Flag >2 or demonstrated partial-read risk.
- **BP9 ToC for long references** — files >100 lines need a table of contents.
- **BP10 Workflows** — clear sequential steps; copyable checklist for complex flows.
- **BP11 Feedback loops** — validator → fix → repeat; validation as a gate.
- **BP12 No time-sensitive info** — no date-conditional logic; "old patterns" sections for deprecated behavior.
- **BP13 Consistent terminology** — one term per concept; no contradictory statements of the same rule.
- **BP14 Template pattern** — strict templates only where consistency is critical; flexible otherwise.
- **BP15 Examples pattern** — input/output pairs where style matters.
- **BP16 Conditional workflows** — explicit decision points; exhaustive branches; large branches in separate files.
- **BP17 One default, not many options** — a default plus an escape hatch.
- **BP18 Forward slashes** — no Windows-style paths.
- **BP19 Scripts** — solve don't punt; no unexplained constants; execute-vs-read intent explicit.
- **BP20 Plan-validate-execute** — verifiable intermediate plan before batch/destructive/high-stakes operations.
- **BP21 Specific and actionable** — exact command + expected output + failure fixes; no vague verbs.
- **BP22 Instruction placement** — critical rules near the top / at point of action; buried rules get missed.
- **BP23 Error handling** — common failure modes and recovery steps for operations that fail in known ways.
- **BP24 Evaluation-driven** — iterate from observed behavior, not assumptions.
- **BP25 Composability** — a skill works alongside other skills; handoffs must match the receiving skill's actual behavior.

**Finding categories:** over-specification, under-specification, ambiguity, redundancy, missing-guidance, weak-description, structure, doc-drift, convention-conflict, other. **D9** = README↔SKILL.md drift.

## Changelog

*(add entries here as items are completed: date — item — commit)*

- 2026-07-01 — **#1 unit-test** (all 9 findings; F2/F3 in ADJUSTED form) — commit hash added at wrap-up. F1+F8: abandon and bug branches of the per-test workflow now revert the failing test and record `fail-abandoned` (+`failure_reason` naming the bug); F2: Final verification marked normal-mode-only, harness recording moved into the per-test branches; F3: stop gates under harness mode now emit the Step 6 JSON with a new `blocked` schema field (coverage-harness-mode.md) and orchestrator-loop-paired.md step 3 got a blocked-gate termination rule (orchestrator-instruction variant chosen over a cli.py change — leaner, no code path touched); F9: one post-write coverage-instrumented run explicitly permitted as measurement for `coverage.after`, verification-gating still forbidden; F4: "only add new test files" → "only add new tests (new files or appended cases)" in constraint/intro/description/README; F5: cycle-context block spec moved to coverage-harness-mode.md §2, pointer left in SKILL.md; F6: duplicate scope sentence folded; F7: README "5-step"→"6-step" + full shared-references list.
- 2026-07-01 — **#2 permissions** (all 9 findings; F7 in ADJUSTED form) — commit hash added at wrap-up. F8: hook verify is now a concrete gate (diff against template + `bash -n`, re-copy on mismatch; re-applied Step 3 customizations are the only allowed delta); F9: Step 3 diffs an existing hook before overwriting and offers re-apply/discard via AskUserQuestion; the report bullet and skill README "Extending with custom patterns" note updated to match; F1: precious-file scan moved before the report so items 1–4 are one contiguous pre-report checklist; F3: the 29-pattern find command replaced with derive-from-`is_precious()` instruction (hook is single source of truth); F5: literal 13/30 counts → "every entry from the template", branch bullet reads `PROTECTED_BRANCHES` from the installed hook; F2: six paragraph report bullets compressed to one-liners + README section pointers (all topics kept); F4: description now names git branch protection and precious-file safeguards; F6: "see step 2 above" → "see the permissions.deny merge rule above"; F7: malformed-settings.json rule added to Merge principles. Hook template untouched — no `.claude/hooks/` re-copy needed.
- 2026-07-01 — **C1** (description convention + worst-description re-tunes) — commit hash added at wrap-up. Rewrote the guidelines' Description Quality section for the human `/`-menu audience and corrected the "Load only metadata at startup" bullet (auth F1+F8); added the conditional-note-only change to the init template per the scope caution. Re-tuned descriptions: how-to-run (1021→474 chars, kept validate.sh-pinned "guided in-chat walkthrough"), refactor (704→426), tdd (+side effects/spec detection/workflow pointer), unit-test-deep (+test-command prerequisite), refactor-deep (dup fresh-subagent sentence → auto-apply differentiator + /optimus:refactor pointer), code-review-deep (dup sentence deleted), spec-init (verb-first), brainstorm + jira (+docs/specs/ / docs/jira/ save locations, jira kept ~flat at 712). Added a description-length (≤1024) check to validate.sh (desc-audit F1 ADJUSTED). Trimmed the root README how-to-run row 1825→~540 chars (desc-audit F2) and aligned the brainstorm row's spec path. Not done here: gerund-naming bullet left in place (that's C2); refactor-deep's "project-wide" lead-in left for skill item #12 (tied to its Step 1/README scope-model fix F1).
