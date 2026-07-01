# Full verified findings — skill quality audit 2026-07-01

Read [README.md](README.md) first for method, ground rules (quote re-location, token pinning, verdict semantics), ranking, and the BP-id reference. This file is large — read only the section for the item you are working on.

Snapshot: branch `chore/skills-quality-assessment` @ `8cef3e4`, 2026-07-01. Line numbers are approximate anchors from that snapshot; the verbatim quote is authoritative.

## Contents

**Convention-level audits (fix first):**
- [Convention audit: Authoring conventions vs upstream best practices](#convention-audit-authoring-conventions-vs-upstream-best-practices)
- [Convention audit: The 22 frontmatter descriptions as a set](#convention-audit-the-22-frontmatter-descriptions-as-a-set)
- [Convention audit: Shared instruction architecture (references/, plugin agents/)](#convention-audit-shared-instruction-architecture-references-plugin-agents)
- [Convention audit: Cross-skill redundancy and divergence sweep](#convention-audit-cross-skill-redundancy-and-divergence-sweep)

**Skills (ranking order, most improvement-hungry first):**
- [1. unit-test — 6/10](#1-unit-test--610)
- [2. permissions — 5/10](#2-permissions--510)
- [3. handoff — 5/10](#3-handoff--510)
- [4. code-review — 5/10](#4-code-review--510)
- [5. jira — 5/10](#5-jira--510)
- [6. init — 5/10](#6-init--510)
- [7. tdd — 5/10](#7-tdd--510)
- [8. how-to-run — 5/10](#8-how-to-run--510)
- [9. workflow — 4/10](#9-workflow--410)
- [10. reset — 4/10](#10-reset--410)
- [11. unit-test-deep — 4/10](#11-unit-test-deep--410)
- [12. refactor-deep — 4/10](#12-refactor-deep--410)
- [13. pr — 4/10](#13-pr--410)
- [14. prompt — 4/10](#14-prompt--410)
- [15. spec-init — 4/10](#15-spec-init--410)
- [16. refactor — 4/10](#16-refactor--410)
- [17. commit — 4/10](#17-commit--410)
- [18. worktree — 4/10](#18-worktree--410)
- [19. brainstorm — 3.5/10](#19-brainstorm--3510)
- [20. code-review-deep — 3/10](#20-code-review-deep--310)
- [21. branch — 3/10](#21-branch--310)
- [22. commit-message — 3/10](#22-commit-message--310)

---

## Convention audit: Authoring conventions vs upstream best practices

**Improvement need:** assessor 5 → verified **5** / 10. Rebuild recommended: no.

**Topic summary:** The repo's authoring conventions are unusually mature — evidence-driven house rules (imperative fan-out counts, emoji/progress bans), honestly documented divergences from upstream, and wiring checks backing load-bearing text. The highest-leverage defect is that the description-writing convention is copied from upstream model-triggering guidance the plugin explicitly disables via disable-model-invocation, so it optimizes the wrong audience and has produced near-cap (1021-char) descriptions for a slash-menu. Secondary defects are consistency-level: gerund naming advice no skill follows, tip wording duplicated in two canonical docs plus 15 unguarded inline copies, an every-skill-vs-"none" contradiction on the Next Step mandate, and an overstated validate.sh mitigation for the two-level reference-depth divergence.

**Assessor score rationale:** The convention corpus is largely a faithful, well-engineered distillation of upstream best practices with honest divergences, and the challenged house rules (fan-out, emoji/progress bans, fresh-conversation tip) survive scrutiny. But the Description Quality section is mis-tuned for the plugin's core explicit-invocation design and has already produced near-cap descriptions across the most user-visible surface (all 22 skills), and four medium consistency defects (gerund advice nobody follows, dual-source tip wording with 15 unguarded copies, every-skill-vs-\"none\" contradiction, overstated depth-check mitigation) each replicate across the collection. Moderate, several targeted fixes — squarely a 5; nothing structural needs rebuilding.

**Verifier adjusted rationale:** All six findings survived adversarial verification with no adjustments: every quote is verbatim, every count checked out exactly (1021/710/707/704-char descriptions; 15 inline Variant C copies in 8 files vs 13+ pointer-form closings; the validate.sh leaf exemption at lines 355-356 with harness-mode.md line 50 disproving the leaf assumption), and none of the flagged duplication or conventions is test-enforced (validate.sh guards only the handoff skill's 'Variant A' token; expected-outputs.yaml has no tip assertions), so the deliberate-redundancy defense does not apply anywhere. The high finding is directly endorsed by rubric context #1. I found no missed high-severity problems — the two additions are medium doc-drift items (CONTRIBUTING's stale structure tree missing spec-init/handoff/sdd-mapping, and a second stale upstream-loading-model sentence at line 65 that the proposed Description Quality rewrite would strand). What survives is one high mis-tuned convention plus five consistency/accuracy defects and two medium drift items, all fixable via section-level rewrites plus a small validator extension — squarely the 5-6 'moderate, several targeted fixes' anchor; 5 stands.

### Findings to implement

#### F1. [high/convention-conflict] .claude/docs/skill-writing-guidelines.md — "Description Quality (frontmatter)", line 56

- **Quote:** "Claude uses descriptions to select the right skill from potentially many available skills."
- **Problem:** Every skill sets disable-model-invocation: true, so descriptions never compete for model selection (nor are they "injected into the system prompt", line 57) — the convention optimizes a mechanism the plugin disables, and in practice yields keyword-stuffed near-cap descriptions (how-to-run: 1021 chars; jira 710, workflow 707, refactor 704) that a truncating slash menu cannot show.
- **Fix:** Rewrite the section for the real audience: a human scanning the / menu and plugin listing — lead with the differentiating words, target roughly 200-300 chars, keep what+when accuracy against actual behavior; drop the model-selection and system-prompt-injection rationale sentences.
- **Best practice:** BP4
- **Verifier:** CONFIRMED — Quote is verbatim at .claude/docs/skill-writing-guidelines.md:56, and line 57 does claim system-prompt injection. All 22 skills set disable-model-invocation: true (validate.sh enforces it), so per rubric context #1 the description audience is the human slash menu, not model selection. Measured description lengths confirm the cited fallout exactly: how-to-run 1021 chars (cap 1024), jira 710, workflow 707, refactor 704. The convention section is copied upstream guidance optimizing a mechanism this plugin deliberately disables; the proposed rewrite (human-scannable, lead with differentiators, keep what+when accuracy) breaks no repo mechanics — validate.sh checks only description presence, not content.

#### F2. [medium/convention-conflict] .claude/docs/skill-writing-guidelines.md — "Description Quality (frontmatter)", line 60

- **Quote:** "Prefer gerund form for skill names when possible: `processing-pdfs`, `analyzing-code`."
- **Problem:** All 22 skills use short verb/noun slash-command names (init, commit, refactor, tdd, pr) — zero gerunds — so this upstream-copied advice contradicts the entire collection and the Foundation rule "Follow Existing Patterns", steering a future contributor toward an inconsistent /optimus:processing-x name.
- **Fix:** Codify the actual convention (short verb/noun slash-command-style names consistent with the existing set, since names surface as /optimus:<name>) and move naming guidance out of the Description Quality section into its own bullet.
- **Best practice:** BP5, BP13
- **Verifier:** CONFIRMED — Verbatim at line 60. All 22 skill directories (init, how-to-run, unit-test, refactor, tdd, pr, jira, spec-init, handoff, ...) use short verb/noun names — zero gerunds — so the advice contradicts both the entire collection and the doc's own Foundation rule 'Follow Existing Patterns ... don't leave skills in a mixed state'. Upstream BP5 permits noun phrases, so codifying the actual convention loses nothing. No mechanics affected (no name field in frontmatter; directory name determines /optimus:<name>). Medium is right.

#### F3. [medium/doc-drift] .claude/docs/skill-writing-guidelines.md — "Next Step", line 125 (and 8 SKILL.md files)

- **Quote:** "Always include the fresh-conversation tip as part of the recommendation to the user — e.g., "Recommend running `/optimus:X` to do Y."
- **Problem:** Canonical tip wording is duplicated: skill-handoff.md mandates verbatim variants, the guidelines restate the wording inline as an example, and 15 verbatim inline copies of Variant C sit in 8 SKILL.md files (jira x4, unit-test x3, brainstorm x3, etc.) with no validate.sh guard, while other skills use the pointer form ("use Variant A per skill-handoff.md") — a mixed state that is exactly the drift failure mode skill-handoff.md says it exists to prevent.
- **Fix:** Make references/skill-handoff.md the single source of tip wording: the guidelines' Next Step section should instruct "emit the applicable variant from skill-handoff.md" without restating it, and either convert inline copies to variant pointers or add a wiring check (like the existing handoff-token checks) asserting inline copies match Variant C verbatim.
- **Best practice:** BP13, BP14
- **Verifier:** CONFIRMED — All counts verified exactly: 15 verbatim copies of the Variant C sentence across 8 SKILL.md files (jira 4, unit-test 3, brainstorm 3, init/worktree/reset/spec-init/permissions 1 each), while 13+ closings in other skills (commit, commit-message, branch, pr, tdd, workflow, code-review, refactor, prompt, how-to-run, handoff) use the pointer form 'use Variant X per skill-handoff.md'. Checked the deliberate-redundancy exemption: validate.sh's only tip check is the handoff skill's 'Variant A' token (line 1024) and test/expected-outputs.yaml contains no tip assertions — the 15 copies are unguarded, so this is not enforced duplication. skill-handoff.md line 33 itself declares 'Drift is the failure mode this section exists to prevent.' The proposed wiring check matches the repo's existing load-bearing-token pattern.

#### F4. [medium/convention-conflict] .claude/docs/skill-writing-guidelines.md — "Next Step", line 121 vs references/skill-handoff.md line 7

- **Quote:** "Every skill must end with a recommendation for the next logical optimus skill. This guides the user through the workflow and increases plugin adoption."
- **Problem:** This contradicts the canonical handoff doc, which allows "the exact slash command to invoke, or 'none' if the chain ends here", and the "increases plugin adoption" motivation pushes authors of genuinely terminal skills to invent cross-promotional recommendations that spend closing tokens without user value and assume the optimus chain is the user's whole workflow.
- **Fix:** Align the guidelines with skill-handoff.md: require the three-part closing but explicitly allow "none" when no next skill genuinely helps, and replace "increases plugin adoption" with the user-value rationale (workflow guidance plus fresh-conversation context hygiene).
- **Best practice:** BP1, BP25
- **Verifier:** CONFIRMED — Both quotes verbatim (guidelines line 121; skill-handoff.md line 7 allows 'the exact slash command to invoke, or "none" if the chain ends here'). Two canonical docs give a fresh author conflicting rules on whether a terminal skill may close with 'none', and the 'increases plugin adoption' motivation is accurately quoted. No validate.sh check enforces a Next Step section (grep confirms), so aligning the guidelines with skill-handoff.md breaks nothing. The proposed change also correctly imports the three-part closing (conversation/mode/next skill) the guidelines currently omit.

#### F5. [medium/other] .claude/docs/skill-writing-guidelines.md — "Progressive Disclosure", line 68 (mitigation claim; cf. scripts/validate.sh ~line 356)

- **Quote:** "it is checked by `scripts/validate.sh` (the check follows `$CLAUDE_PLUGIN_ROOT` references — prose section references are not tracked)"
- **Problem:** The guideline understates the check's blind spots: validate.sh also exempts anything routed through top-level references/ and agents/ as "leaf files", an assumption already false — references/harness-mode.md loads references/context-injection-blocks.md — so a future 3-level chain through a shared reference (or via prose references like coverage-harness-mode.md line 100 pointing to harness-mode.md) would pass CI silently while the convention leans on this check to justify its BP8 divergence.
- **Fix:** Extend the depth check one hop through top-level references/ (or correct the guideline note to name both blind spots — prose references and the top-level leaf exemption) so the two-level divergence's advertised safety net matches what is actually enforced.
- **Best practice:** BP8
- **Verifier:** CONFIRMED — Verbatim at line 68. validate.sh lines 347-361 confirm two blind spots the note omits: (a) the level-1 scan only walks skills/*/references and skills/*/agents — top-level references/ files are never scanned as chain origins; (b) line 355-356 explicitly exempt onward refs into top-level agents/ and references/ as 'leaf files'. The leaf assumption is demonstrably false: references/harness-mode.md line 50 loads $CLAUDE_PLUGIN_ROOT/references/context-injection-blocks.md, and coverage-harness-mode.md line 100 chains to harness-mode.md via untracked prose. A 3-level chain through any top-level reference passes CI today while the convention cites the check to justify its BP8 divergence. Either proposed remedy (extend one hop or document both gaps) is sound.

#### F6. [low/structure] CONTRIBUTING.md — "Output tone and formatting", lines 138-142

- **Quote:** "Keep skill output templates plain: markdown headings, bold, and blockquotes — no decorative emoji"
- **Problem:** Three SKILL.md-content rules (emoji ban, no hand-rolled [Step N/M] progress lines, imperative fan-out counts) live only in CONTRIBUTING.md, while CLAUDE.md routes skill authors to skill-writing-guidelines.md, whose "Writing Style" section omits them — an author applying the designated guidelines doc can miss house rules that directly govern skill bodies.
- **Fix:** Move the three rules into skill-writing-guidelines.md's Writing Style section (or add a one-line cross-reference there), leaving CONTRIBUTING.md to contributor-workflow concerns.
- **Best practice:** BP22
- **Verifier:** CONFIRMED — Verbatim at CONTRIBUTING.md line 138; the three rules (emoji ban, no [Step N/M] lines, imperative fan-out counts, lines 138-142) appear nowhere in skill-writing-guidelines.md (full read confirms Writing Style omits them). CLAUDE.md's per-edit routing rule names only skill-writing-guidelines.md for skill changes, so the designated doc misses skill-body content rules. Mitigation exists — CLAUDE.md's 'Before making changes' also directs to CONTRIBUTING.md — which is why low severity is correct. The repo's guidelines doc is decoupled from the init template (diff confirms substantial divergence, no sync check), so adding a cross-reference breaks no template mechanics. Low, as filed.

#### F7. [medium/doc-drift] CONTRIBUTING.md — "Project structure" tree, lines 19 and 39-59
*Found by verifier (adversarial pass) — treat as confirmed*

- **Quote:** "references/                # Shared reference docs (agent-architecture, … scope-expansion-rule, skill-handoff)"
- **Problem:** The canonical contributor structure doc has drifted: its skills tree lists 20 of 22 skills (skills/spec-init/ and skills/handoff/ are missing) and its references/ line omits sdd-mapping.md, while CLAUDE.md's layout is current — and no validate.sh check covers CONTRIBUTING the way check 8 covers root README.
- **Fix:** Add spec-init/ and handoff/ to the skills tree and sdd-mapping to the references list; optionally extend validate.sh's stale-README check to assert every skills/<name>/ directory appears in CONTRIBUTING's structure block.
- **Best practice:** D9, BP13

#### F8. [medium/doc-drift] .claude/docs/skill-writing-guidelines.md — "Progressive Disclosure", line 65
*Found by verifier (adversarial pass) — treat as confirmed*

- **Quote:** "Load only metadata (description) at startup."
- **Problem:** Same root defect as the assessor's high finding but in a section its proposed fix would not touch: with disable-model-invocation: true on every skill the description is never loaded into the model's context at startup, so the doc teaches the upstream loading model the plugin disables.
- **Fix:** Correct the bullet to the plugin's actual loading model (description surfaces in the / menu and plugin listings; SKILL.md plus description load only at explicit invocation), and fix it in the same pass as the Description Quality rewrite so the doc is internally consistent.
- **Best practice:** BP4, BP13

### Already well-tuned (preserve; do not churn while fixing the above)

- references/skill-handoff.md's verbatim variant system (A/B/C with explicit placeholders, a documented continuation-skill criterion, and plan-mode carve-out) is a strict template correctly applied where consistency is critical (BP14) — strong anti-drift engineering at the design level.
- The imperative fan-out rule ("Launch all 4 agents in a single message") is evidence-driven (observed conservative under-spawning) and correctly applies low freedom to a genuinely fragile step — sound, not over-reach (BP2, BP24).
- The emoji and progress-indicator bans are scoped (output templates; hand-rolled status lines only), come with stated rationale, and match current Claude Code output tone — BP1-consistent, not over-reach.
- The ToC-for->100-line-references mitigation is actually applied: all four long shared references (harness-mode, coverage-harness-mode, both orchestrator loops) open with a Contents block (BP9), materially reducing the partial-read risk of the two-level allowance.
- The guidelines track upstream best practices closely (conciseness, degrees of freedom, 500-line cap, feedback loops, anti-patterns) and document every divergence with its reason and provenance ("Further Reading" note on omitted upstream sections).
- The Scope and Granularity section gives concrete extend-vs-create criteria balancing skill bloat against skill-count bloat — decision guidance most skill collections lack (BP16-style).

---

## Convention audit: The 22 frontmatter descriptions as a set

**Improvement need:** assessor 4 → verified **4** / 10. Rebuild recommended: no.

**Topic summary:** As a set, the 22 descriptions are unusually disciplined: consistent verb-first third-person voice in a shared "[What] — [details]. Use when [trigger]" shape, explicit base→deep cross-pointers for all three deep pairs, and side-effect/precondition flags surfaced consistently. Rendered lengths run 198–710 chars for 21 of 22 skills (median ~430); the one true outlier is how-to-run at 1021 chars — 3 chars under the 1024 platform cap with no CI length check — paired with an 1825-char root-README table cell that dwarfs every sibling row (119–483 chars). The other material gap is tdd, whose description omits spec auto-detection and branch/commit/push side effects that the README row does state.

**Assessor score rationale:** The layer is structurally sound — consistent voice, good disambiguation, accurate constraint flags — so most of the set needs nothing. The need concentrates in one accreting outlier (how-to-run: description 3 chars under the uncapped-by-CI 1024 platform limit, plus an 1825-char README cell) and one flagship under-description (tdd omitting commits/push/spec detection). These are a handful of targeted edits, not structural rework: minor-polish-to-moderate, hence 4.

**Verifier adjusted rationale:** All five findings survive verification (four CONFIRMED, one ADJUSTED only to protect validate.sh's 'guided in-chat walkthrough' discoverability string when trimming the how-to-run description). Every measurement reproduced exactly: how-to-run description 1021/1024 chars with no CI length check, README cell 1825 vs median 239.5, tdd's undeclared branch/commit/push side effects confirmed in the body and stated in the README row. My hunt for missed high-severity problems found none — descriptions are otherwise accurate against bodies (spot-checked unit-test's 'only adds new test files', prompt's 14 templates, deep-skill iteration caps, tdd's same-conversation /optimus:pr handoff, spec-init's brainstorm handoff). Two real but sub-high misses were added: unit-test-deep omits the prerequisite its two siblings declare (medium), and brainstorm omits its docs/specs/ save location, the counterpart of the jira gap (low). The layer remains structurally sound with a handful of targeted single-sentence edits plus one description rewrite and one README cell trim — squarely 'minor polish' at the top of the 3-4 band. Score stays 4.

### Findings to implement

#### F1. [high/weak-description] skills/how-to-run/SKILL.md, frontmatter description (lines 2–18)

- **Quote:** "Detects build system, toolchain, SDKs, source dependencies (git submodules, sibling repos), external services, environment config, and hardware/OS requirements."
- **Problem:** At 1021 rendered chars the description sits 3 chars under the 1024 platform cap (validate.sh checks only presence, not length, so the next capability added breaks it silently) and is 44% longer than the next-longest description (jira, 710) — a body-level feature inventory mis-tuned for the human slash-menu audience this repo's disable-model-invocation convention defines.
- **Fix:** Cut to ~350–450 chars: what (generates or audits HOW-TO-RUN.md), when (after /optimus:init or when onboarding is broken), key capabilities (multi-stack detection, audit mode, guided walkthrough), and the writes-only-HOW-TO-RUN.md constraint; move the detection taxonomy into the SKILL.md body and skill README.
- **Best practice:** BP4, BP1
- **Verifier:** ADJUSTED — Facts confirmed: rendered description measures exactly 1021 chars (cap 1024 per BP4), validate.sh checks only description presence (lines 66-68) with no length check, and repo context #1 explicitly calls a ~1000-char description mis-tuned for this human-menu-audience plugin. High severity stands. But the proposed change needs a correction: validate.sh (~line 899) enforces the literal discoverability string 'guided in-chat walkthrough' whose stated purpose is surfacing the walkthrough in the description — the grep covers the whole SKILL.md so the body occurrence keeps CI green, meaning a careless trim would pass CI while silently defeating the check's intent.
  - **Revised severity:** high
  - **Revised fix (implement this one):** Cut to ~350-450 chars as proposed, but retain the exact phrase 'guided in-chat walkthrough' in the trimmed description (validate.sh's discoverability check exists to keep it surfaced there), and add a description-length check to validate.sh so the 1024 cap can't be silently broken.

#### F2. [medium/structure] README.md line 88 (Utility skills table, /optimus:how-to-run row)

- **Quote:** "vendor-branded cloud services (AWS S3/SNS/SQS, Azure Blob/Cosmos, Firebase, Pub/Sub) resolve to their local emulators (LocalStack, Azurite, etc.) via a Vendor-Service → Emulator Index."
- **Problem:** The description cell is 1825 chars — 3.8x the next-largest row (jira, 483; median ~230) — packing implementation minutiae (emulator index, PowerShell quoting caveat, GUI-client guide, diagnostic ladders) into a scannability table, and each new feature has visibly accreted there, making it the layer's biggest drift magnet.
- **Fix:** Reduce to a 2–3 sentence summary proportionate to sibling rows and relocate the detail to skills/how-to-run/README.md, which the row already links to.
- **Best practice:** BP1, BP7
- **Verifier:** CONFIRMED — Quote verbatim at README.md line 88. Measured cell lengths: how-to-run 1825 chars vs jira 483 (next largest), median 239.5 — matches the claim. Not test-enforced: validate.sh only requires '/optimus:how-to-run' to appear in README.md, and expected-outputs.yaml checks fixture outputs only. The relocated detail already exists near-verbatim in skills/how-to-run/README.md (lines 14, 68, 73), so the change is safe and actually removes duplication.

#### F3. [medium/weak-description] skills/tdd/SKILL.md line 2 (frontmatter description)

- **Quote:** "Guides test-driven development — decompose a feature or bug fix into behaviors, then cycle through Red (failing test) → Green (minimal implementation) → Refactor"
- **Problem:** The description omits material behavior the body confirms — auto-detects specs from docs/specs//docs/jira/, creates a feature branch, auto-commits per behavior, pushes at the end — which the root README row does state ("per-behavior commits ... and branch push"), so the layers drift and the menu/invocation contract under-reports side effects; it also gives no pointer to its peer /optimus:workflow, whose description disambiguates only one-directionally ("A peer of /optimus:tdd ... prefer it for large or parallelizable specs").
- **Fix:** Add one sentence covering spec auto-detection and the branch/per-behavior-commit/push side effects, plus a trailing pointer: "For large or parallelizable specs, /optimus:workflow is the fan-out peer." (302 chars today — ample headroom).
- **Best practice:** BP4
- **Verifier:** CONFIRMED — Quote verbatim. Body confirms all omitted behavior: spec/JIRA auto-detection cascade (line 55), feature-branch creation (lines 106-118), per-behavior auto-commit (Step 7, lines 312-319), and push (Step 9, line 385). README row 72 states 'per-behavior commits ... and branch push', so the layers genuinely drift and the description under-reports side effects that sibling descriptions consistently declare. workflow's description points at tdd but not vice versa — verified one-directional. At 302 chars the proposed addition fits with huge headroom and breaks nothing.

#### F4. [low/structure] skills/spec-init/SKILL.md line 2 (frontmatter description)

- **Quote:** "Use when starting a new project or product and you want a docs-first plan before writing code — scaffolds an empty, product-neutral spec-driven-development cascade"
- **Problem:** This is the only description of the 22 that leads with "Use when ..." instead of the set's verb-first [What] — [When] shape, breaking set-level voice consistency and pushing the WHAT past the slash-menu truncation window.
- **Fix:** Invert to match the set: "Scaffolds an empty, product-neutral spec-driven-development cascade (product vision, MVP PRD, target tech-stack) for a human to fill, then hands off to brainstorm. Use when starting a new project ..."
- **Best practice:** BP4, BP13
- **Verifier:** CONFIRMED — Quote verbatim at skills/spec-init/SKILL.md line 2. Verified across all 22 skills: spec-init is the only description opening with 'Use when'; the other 21 open verb-first, so the set-consistency and menu-truncation (leading-words) claims are factually accurate under BP4/BP13 and rubric context #1. The inversion touches nothing enforced. Low severity is right.

#### F5. [low/weak-description] skills/jira/SKILL.md line 2 (frontmatter description)

- **Quote:** "Distills title, description, acceptance criteria, sprint context, and comments into a structured task description."
- **Problem:** The 710-char description never names the docs/jira/ save location, yet workflow's description ("auto-detects docs/specs/ or docs/jira/") and the root README row ("saved to docs/jira/ for downstream skills to auto-detect") both depend on the user knowing it — a cross-description coherence gap.
- **Fix:** Add "saves the distilled task under docs/jira/ for downstream skills to auto-detect", trimming an equivalent amount elsewhere to keep length flat.
- **Best practice:** BP4
- **Verifier:** CONFIRMED — Quote verbatim in jira's 710-char description, which indeed never names docs/jira/. Body writes docs/jira/<ISSUE-KEY>.md (SKILL.md lines 112-126), workflow's description says 'auto-detects docs/specs/ or docs/jira/', and the README jira row says 'saved to docs/jira/ for downstream skills to auto-detect' — the cross-description coherence gap is real. The additive change is safe; note trimming isn't strictly required since 710 leaves 314 chars of headroom, but keeping length flat is sensible.

#### F6. [medium/under-specification] skills/unit-test-deep/SKILL.md line 2 (frontmatter description)
*Found by verifier (adversarial pass) — treat as confirmed*

- **Quote:** "continues until coverage plateaus or the cycle cap (default 5, hard cap 10)"
- **Problem:** Unlike its two sibling deep skills (refactor-deep and code-review-deep both state 'Requires a test command in .claude/CLAUDE.md'), unit-test-deep's description declares no prerequisite at all, while the README row states '*Requires init + test command.*' — a set-consistency break and README↔description drift that contradicts the assessor's well_tuned claim that preconditions are 'consistently declared'.
- **Fix:** Append the sibling formula to the description: 'Requires a test command in .claude/CLAUDE.md.' (511 chars today — ample headroom).
- **Best practice:** BP4, BP13

#### F7. [low/weak-description] skills/brainstorm/SKILL.md, frontmatter description (lines 2-9)
*Found by verifier (adversarial pass) — treat as confirmed*

- **Quote:** "proposes multiple approaches with trade-offs, and writes an approved spec to the project"
- **Problem:** The description never names the docs/specs/ save location — the exact counterpart of the confirmed jira finding — yet workflow's description ('auto-detects docs/specs/ or docs/jira/'), tdd's auto-discovery cascade, and spec-init's handoff text ('writes the engineering spec to docs/specs/') all treat that path as public API.
- **Fix:** Change to 'writes an approved spec to docs/specs/ for /optimus:tdd and /optimus:workflow to auto-detect' (473 chars today — headroom is ample).
- **Best practice:** BP4

### Already well-tuned (preserve; do not churn while fixing the above)

- Voice is uniform: 21 of 22 descriptions open verb-first in third person with the payload in the first ~10 words, so the set survives slash-menu truncation; the three *-deep skills share a recognizable "Iterative X — runs /optimus:Y in a fresh subagent context per iteration ... (default N, hard cap M)" formula.
- Sibling disambiguation is largely solved where it matters: all three base skills point forward to their -deep variant, commit-message carries an explicit negative trigger ("read-only, never commits") against commit, workflow positions itself against tdd, and branch vs worktree have distinct, accurate "Use when" clauses.
- Side effects and preconditions are consistently declared ("Never commits or pushes", "Requires /optimus:init", "Requires a test command in .claude/CLAUDE.md", "uses meaningfully more tokens", "the skill never executes commands itself"), matching actual behavior in the spot-checked bodies.
- Length distribution is healthy apart from the single outlier: 21 of 22 under 710 rendered chars, median ~430, floor 198 — nothing vague or under-specified at the short end.
- README skills-table rows are accurate against the descriptions everywhere spot-checked except the two drift points reported (how-to-run cell size, tdd side effects), and every row links to a per-skill README.

---

## Convention audit: Shared instruction architecture (references/, plugin agents/)

**Improvement need:** assessor 4 → verified **5** / 10. Rebuild recommended: no.

**Topic summary:** The shared instruction architecture is deliberately engineered and mostly well-factored: the two orchestrator loops manage their duplication with explicit canonical pointers, coverage-harness-mode composes with harness-mode by delegation, all four >100-line references carry ToCs, and shared-agent-constraints is consistently consumed by the three review-oriented skills with the standalone split documented. The weak spots are concentrated in the two-tier agent extension pattern (base agents instruct mutation/test-running that every read-only extender must silently override, and subagent prompts carry unresolvable $CLAUDE_PLUGIN_ROOT / bare-relative paths) and one divergently forked template (iteration context block in harness-mode.md vs context-injection-blocks.md). Enforcement is strong for path resolution and depth but the orphan check is structurally vacuous for root references/ and agents/.

**Assessor score rationale:** The shared architecture's load-bearing core (orchestrator loops, harness protocols, constraint sharing) is well-factored, cross-referenced, and mechanically validated, so no structural work is needed. But three medium findings sit on high-traffic paths every review skill flows through: base-agent directives that contradict every read-only extender with undefined override semantics, unresolvable $CLAUDE_PLUGIN_ROOT/relative paths in fan-out subagent prompts that the repo's own deep-mode docs identify as a real failure mode, and a divergently forked iteration-context template that drops its load-bearing \"don't re-flag\" clause. All are small targeted edits to shared files — minor-to-moderate polish, not restructuring.

**Verifier adjusted rationale:** All six findings survived adversarial verification intact: every quote is verbatim, the three mediums sit on paths every review skill or deep-mode run traverses (base-agent mutation directives with undefined override semantics, unresolvable $CLAUDE_PLUGIN_ROOT/relative paths in fan-out prompts that the repo's own orchestrator docs identify as a real subagent failure mode, and a divergently forked iteration-context template that drops its load-bearing don't-re-flag clause and is enforced by neither validate.sh nor expected-outputs.yaml), and none of the proposed changes breaks frontmatter rules, path-resolution checks, or test-enforced invariants. Verification additionally surfaced two problems the assessor missed in the same shared harness reference: an internal contradiction where step 7's blanket 'skip any verification or validation step' collides with step 4's mandatory finding validation — the only false-positive gate before deep mode auto-applies and commits fixes, with the sibling coverage-harness-mode.md proving the intended narrow phrasing — and a pr_description instruction that orders refactor iterations to perform a PR/MR injection its own context-blocks.md explicitly rules out (the shared CLI populates pr_description for refactor-deep too). The architecture's core remains well-factored and mechanically validated, and every fix is a small targeted edit, but eight defensible defects concentrated in the shared, highest-traffic files moves this from minor polish (4) to moderate targeted-fix territory (5).

### Findings to implement

#### F1. [medium/ambiguity] agents/code-simplifier.md, "How You Operate" (~line 49); mirrored in agents/test-guardian.md "Verify Tests Pass"

- **Quote:** "Direct simplifications — apply automatically"
- **Problem:** The plugin-level base agents contain operational directives (apply edits automatically; run the project's test command) that contradict every skill-level extender's read-only role, and the extension instruction "Read ... for your approach and quality criteria" never defines which base sections are inert — while the extenders' `tools:` frontmatter is unenforced because SKILL.md dispatches them as `general-purpose` subagents, so only prose prevents a weaker model from editing files mid-review.
- **Fix:** Add a short "When read as an extension base" note to both plugin agents stating that the dispatching prompt's constraints (read-only, scope, test execution) override the operational sections here and only quality criteria/focus areas carry over; code-review's existing one-off carve-out ("ignore that file's under-abstraction framing") shows the mechanism but covers only one of the conflicts.
- **Best practice:** BP13, BP3, BP2, BP22
- **Verifier:** CONFIRMED — Quote verbatim at agents/code-simplifier.md:49; base also says 'Apply changes' (line 47) and test-guardian base mandates running the test command (line 23). All three code-simplifier extenders (code-review, refactor, tdd) say 'Do NOT modify any files', yet nothing defines which base sections are inert when extended — the extension line only says 'for your approach and quality criteria', and code-review's one-off carve-out ('ignore that file's under-abstraction framing') proves the authors handle such conflicts case-by-case for one conflict only. Verified the tools: frontmatter claim: SKILL.md dispatches extenders as `general-purpose` Agent calls (code-review SKILL.md:171, refactor:119, tdd quality-gate.md:13), so the Read/Glob/Grep restriction is decorative and only prose guards against mid-review edits. The proposed base-file note is cheap, does not affect standalone agent use, and passes validate.sh check 15.

#### F2. [medium/under-specification] skills/code-review/agents/code-simplifier.md line 12 (pattern documented in references/agent-architecture.md "The specialization pattern")

- **Quote:** "Read `$CLAUDE_PLUGIN_ROOT/agents/code-simplifier.md` for your approach and quality criteria."
- **Problem:** Fan-out agent prompts reference `$CLAUDE_PLUGIN_ROOT/...` and a bare relative `shared-constraints.md`, but no consuming SKILL.md instructs substituting the resolved absolute root or inlining the constraints when composing subagent prompts — even though the repo's own deep-mode dispatch templates state subagents "do not inherit $CLAUDE_PLUGIN_ROOT" and require literal substitution, and that substitution instruction names only "the base SKILL.md or harness-mode.md", leaving third-tier analysis agents unresolved on a literal reading.
- **Fix:** Add one sentence to the agent-launch step of the consuming skills (or state the convention once in the pattern's home) requiring the dispatcher to substitute the resolved absolute plugin root into every agent prompt and to inline or absolute-path `shared-constraints.md`; extend the deep-dispatch substitution clause to cover agent prompt files.
- **Best practice:** BP8, BP21, BP3
- **Verifier:** CONFIRMED — Quote verbatim at skills/code-review/agents/code-simplifier.md:12 (also tdd:12, refactor:12); bare 'shared-constraints.md' at code-review:16, tdd:25, refactor:18. Grepped all consuming SKILL.mds: no instruction to substitute the resolved root or inline constraints when composing fan-out agent prompts. The repo's own orchestrator-loop-single.md:46 and :56 state subagents 'do not inherit $CLAUDE_PLUGIN_ROOT' and require literal substitution — but that clause names only 'the base SKILL.md or harness-mode.md', not the agent prompt files, so the third-tier fan-out is uncovered on a literal reading. A subagent's Read tool cannot expand the variable and the bare relative path resolves against the user project's cwd. Change is prose-only; validate.sh check 8 unaffected.

#### F3. [medium/redundancy] references/harness-mode.md, "2. Build iteration context" (~line 50)

- **Quote:** "using the same template as `$CLAUDE_PLUGIN_ROOT/references/context-injection-blocks.md`"
- **Problem:** harness-mode.md restates an abbreviated fork of the Iteration Context Block that omits the canonical template's status-values legend and its closing "Focus your review on NEW issues only / Do NOT re-flag" instruction — the part that prevents re-flagging across iterations — creating two divergent build paths for the same block (SKILL.md Step 5 via context-blocks.md vs harness-mode step 2 inline); not enforced by validate.sh or test fixtures, so drift-prone.
- **Fix:** Replace the inline template copy with a pointer to context-injection-blocks.md plus only the harness-specific deltas (no pre/post_edit_content in the block, Failed Fix Attempts sourcing), or make the inline copy complete and declare it the single harness-mode source.
- **Best practice:** BP17, BP13
- **Verifier:** CONFIRMED — Quote verbatim at harness-mode.md:50. Verified the fork: the inline copy (lines 52-62) omits the canonical template's status-values legend, the empty-field fallbacks, and the closing 'Focus your review on NEW issues only / Do NOT re-flag' instruction (context-injection-blocks.md:43-56). Verified two live build paths: harness-mode step 2 builds inline, while SKILL.md Step 5 'Iteration context injection' (code-review:183, refactor:127) routes through agents/context-blocks.md → the canonical file — and harness-mode's own 'Skill-step execution' section says to proceed through all skill steps, so both paths fire in the same run. Checked validate.sh and test/expected-outputs.yaml: no token pins 'Prior Findings'/'Failed Fix Attempts', so the duplication is not test-enforced and is drift-prone. Pointer-plus-deltas change matches the repo's own canonical-pointer discipline (orchestrator-loop-paired precedent).

#### F4. [low/convention-conflict] references/shared-agent-constraints.md, "Agent Constraints" (line 7)

- **Quote:** "Do NOT modify any files, create any files, or run any commands that change state."
- **Problem:** The blanket read-only rule has no test-execution carve-out, yet the base test-guardian and the tdd/code-review test-guardian extenders that consume this file mandate running the full test suite (which writes caches/coverage artifacts) — a strict reader must violate one instruction or the other, and unit-test's standalone constraints ("Read-only analysis with one exception: you MAY run the existing test suite") show the authors already solved this shape elsewhere.
- **Fix:** Add the same explicit carve-out to shared-agent-constraints.md (running the project's existing test/coverage commands is permitted where the agent's role requires it) or add it as an addendum in the tdd and code-review shared-constraints files.
- **Best practice:** BP13, BP23
- **Verifier:** CONFIRMED — Quote verbatim at shared-agent-constraints.md:7. Verified the conflict: tdd's test-guardian extender says 'Run the full test suite to confirm everything passes' (line 24) while its shared-constraints.md:3 imports the base read-only rule; the base plugin test-guardian mandates running the test command (Verify Tests Pass, line 23). Verified the authors' existing solution: skills/unit-test/agents/shared-constraints.md:3 reads 'Read-only analysis with one exception: you MAY run the existing test suite and coverage measurement commands.' Low severity is right — most models read 'change state' as excluding test runs — and the proposed change already offers the safer skill-level-addendum variant, so it will not loosen read-only for agents that don't need test runs.

#### F5. [low/structure] references/harness-mode.md, Contents (lines 3–6) and inner Contents (lines 12–22)

- **Quote:** "Single-Iteration Execution — progress file, analysis cycle, fix application, structured JSON output (steps 1–9)"
- **Problem:** The "Skill-step execution under harness mode" section — which governs how the entire base skill executes (skip confirmation, forced branch-diff path, PR-description handling) — appears in neither the file-level ToC nor the steps-1–9 inner ToC, so a partial read navigating by ToC misses the file's most operationally sweeping rules.
- **Fix:** Add "Skill-step execution under harness mode" (and the pr_description handling note) as an explicit entry in both Contents lists, or renumber it as a step so the 1–9 list covers it.
- **Best practice:** BP9, BP22
- **Verifier:** CONFIRMED — Quote verbatim at harness-mode.md:5. Verified: the 'Skill-step execution under harness mode' section (lines 42-46) — which forces the branch-diff path, skips confirmation/scope offers, and governs pr_description handling — appears in neither the file-level Contents (lines 3-6) nor the steps-1-9 inner Contents (lines 14-22). The file is 155 lines, so BP9 applies, and a ToC-guided partial read misses the file's most sweeping rules. Adding two ToC entries breaks nothing.

#### F6. [low/convention-conflict] scripts/validate.sh, orphan detection check 9 (~line 178); demonstrated by references/agent-architecture.md

- **Quote:** "! grep -rq "$parent_dir/" skills/"
- **Problem:** The parent-directory fallback makes orphan detection vacuous for everything under root references/ and agents/ (the strings "references/" and "agents/" match trivially somewhere in skills/), so the convention that references/ holds skill-consumed procedures is unenforced — agent-architecture.md is consumed by zero skills (it is contributor documentation pointed at only by CONTRIBUTING.md and .claude/docs/) yet passes the check.
- **Fix:** Tighten check 9 for root references//agents/ files to require a full-path or basename match, and either move agent-architecture.md to .claude/docs/ (updating its four pointers) or annotate it as a contributor doc exempt from the runtime-consumption convention.
- **Best practice:** BP11, BP7
- **Verifier:** CONFIRMED — Quote verbatim at validate.sh:178. Verified vacuity: for any file under root references/ or agents/, parent_dir is 'references' or 'agents', and the strings 'references/' / 'agents/' trivially match somewhere in skills/, so the orphan check can never fail for those directories. Verified the demonstration: agent-architecture.md is referenced only by .claude/CLAUDE.md, .claude/docs/*, CONTRIBUTING.md, and README.md — zero matches under skills/ — yet passes check 9. If anything the finding understates the problem (the parent-dir fallback also trivializes skill-level reference dirs once any sibling is referenced by full path), but as stated it is accurate, and both proposed remedies (tighten the match, or relocate/annotate the contributor doc with its four pointers updated) are workable.

#### F7. [high/ambiguity] references/harness-mode.md, "7. Do NOT run tests" (~line 99)
*Found by verifier (adversarial pass) — treat as confirmed*

- **Quote:** "Skip any verification or validation step the base skill's normal (interactive) flow would perform"
- **Problem:** This blanket sentence directly contradicts harness-mode's own step 4 ('Apply the same validation protocol as the skill's normal validation step. Independently verify each finding') — code-review's normal flow names its Step 6 'Validate Findings', so a literal reader is told to both run and skip finding validation, and in deep mode validation is the only false-positive gate before fixes are auto-applied and committed.
- **Fix:** Rescope the sentence to execution-based verification only, mirroring coverage-harness-mode.md's precise phrasing ('Coverage measurement during analysis is fine; a final verification run is not') — e.g. 'Skip any test-running/build/lint verification step the interactive flow performs; finding validation (step 4) still applies.'
- **Best practice:** BP13, BP21, BP22

#### F8. [medium/convention-conflict] references/harness-mode.md, "Skill-step execution under harness mode" (~line 46)
*Found by verifier (adversarial pass) — treat as confirmed*

- **Quote:** "inject it into agent prompts per Step 5 "PR/MR context injection""
- **Problem:** The shared harness-mode reference instructs any base skill with non-null config.pr_description to inject the PR/MR block and apply the Step 6 intent-signal adjustment, but the CLI's shared _init_deep (cli.py:581-583) sets pr_description for refactor-deep runs too, while refactor's own agents/context-blocks.md:9 states 'The PR/MR Context Block does not apply to refactor' and its agents have no Intent Mismatch machinery — the two shared docs give a refactor iteration contradictory orders.
- **Fix:** Scope the pr_description paragraph to skills that define a PR/MR context block (one clause: 'refactor ignores config.pr_description — see its context-blocks.md'), or have the CLI omit pr_description for the refactor phase.
- **Best practice:** BP13, BP16

### Already well-tuned (preserve; do not churn while fixing the above)

- BP9 discipline is solid: all four >100-line references (harness-mode, coverage-harness-mode, both orchestrator loops) carry ToCs; sub-100-line files correctly omit them.
- orchestrator-loop-single vs -paired duplication is actively managed, not drift: paired defers to single as canonical with explicit pointers ("Same contract as orchestrator-loop-single.md step 6", "identical to the single-loop variant"), and its genuine deltas (mid-cycle re-snapshot, phase-shared parse counter, distinct raw-file names) each carry inline rationale.
- coverage-harness-mode composes by delegation — its refactor phase points at harness-mode.md rather than restating the single-iteration protocol, so the two harness docs share almost no duplicated content.
- shared-agent-constraints.md is consistently consumed by all three review-oriented skills via one-line pointers, the standalone-constraints split for init/how-to-run/unit-test is explicitly documented, and the per-category budget registry ("each must be listed here") prevents hidden cap exceptions.
- validate.sh mechanically enforces the reference architecture: check 8 resolves every $CLAUDE_PLUGIN_ROOT path and check 16 caps chains at two levels, and both deep skills independently restate the re-entry guard so the invariant survives partial reads.
- sdd-mapping.md and skill-handoff.md apply single-canonical-statement discipline ("There is exactly one canonical precedence statement and it lives here"; verbatim closing-tip variants with an explicit anti-paraphrase rule) — exactly the right anti-drift posture for shared docs.

---

## Convention audit: Cross-skill redundancy and divergence sweep

**Improvement need:** assessor 5 → verified **5** / 10. Rebuild recommended: no.

**Topic summary:** The collection has a mature anti-redundancy architecture: ten root-level shared references plus canonical per-skill references (multi-repo-detection, branch-naming, gather-changes, constraint-doc-loading, verification-protocol, orchestrator-loop-*), with validate.sh pinning the most fragile producer/consumer text contracts. Remaining redundancy concentrates in the three *-deep orchestrators, whose hand-copied harness/CLI scaffolding has measurably drifted, and in a few small verbatim blocks (branch-collision handling, plan-mode handoff steps, inline closing tips) that bypass their natural shared homes. One collection-level ambiguity (tdd's multi-repo sentence merging two sibling skills' opposing policies) is a live copy-paste defect.

**Assessor score rationale:** The collection's anti-redundancy machinery is genuinely strong — shared references are heavily used and the riskiest cross-file contracts are pinned by validate.sh — but the three -deep orchestrators hand-copy their harness scaffolding and have measurably drifted (error-recovery guidance, safety caveat), tdd carries a live copy-paste ambiguity in its Step 1, and collision handling diverges three ways across five skills. Several targeted consolidations are needed, none structural, placing this at the low end of the moderate band.

**Verifier adjusted rationale:** All seven findings survive adversarial verification — five confirmed outright, two adjusted only in their proposed change (finding 5's string-match must pattern-match the placeholder-bearing Variants A/B; finding 7's reroute-all-consumers over-corrects a likely-deliberate divergence that just needs its rationale documented). I checked every quote verbatim, and confirmed via scripts/validate.sh and test/expected-outputs.yaml that none of the flagged duplication is test-enforced (validate.sh pins only the how-to-run/handoff/tdd-workflow-pr contracts and the handoff 'Variant A' token — not the deep-skill init blocks, collision blocks, Step 3 warnings, inline tips, or plan-mode blocks). Two on-topic medium misses were added: branch-naming.md's stale consumer list (omits workflow) and unit-test-deep's description omitting the hard test-command prerequisite its siblings declare. Nothing rises to high severity: the worst defects (the --force contradiction, the tdd chimera) mislead but degrade gracefully. The anti-redundancy architecture is genuinely strong and the well-tuned list is accurate, so the fixes remain several targeted consolidations plus one validate.sh assertion — squarely the low end of the moderate band. Score stays 5; rebuild correctly rejected.

### Findings to implement

#### F1. [medium/ambiguity] skills/code-review-deep/SKILL.md — Step 4 "On fresh run", line 108 (vs skills/refactor-deep/SKILL.md line 109, skills/unit-test-deep/SKILL.md line 106)

- **Quote:** "or re-invoke this skill with `--force` to discard the prior progress and start fresh"
- **Problem:** The three -deep skills document the same shared `harness_common.cli init` differently: code-review-deep lists three likely errors ("No test command", "Cannot determine HEAD commit") and says re-invoke "this skill" with `--force` (a flag its Step 1 parser doesn't recognize, contradicting its own line 112), while refactor-deep/unit-test-deep say "re-invoke `init` with `--force`" and document only the already-exists error.
- **Fix:** Hoist the shared cli.py init/resume semantics (likely errors, --force recovery, .done.json archival) into a shared reference parameterized by progress-file path — the pattern orchestrator-loop-single.md already uses — keeping only per-skill deltas (focus flag, --allow-red policy) inline.
- **Best practice:** BP13, BP23, BP1
- **Verifier:** CONFIRMED — Quote verbatim at code-review-deep:108. Step 1 item 6 routes unrecognized tokens to scope text (no --force flag), and line 112 explicitly states no user-visible orchestrator flag is needed — a real internal contradiction. Siblings (refactor-deep:109, unit-test-deep:106) correctly say re-invoke `init` with --force and document only the already-exists error, confirming sibling drift. No validate.sh or expected-outputs.yaml pin on these blocks, so hoisting into a shared reference is safe (check 8 only requires the new file to exist).

#### F2. [medium/ambiguity] skills/tdd/SKILL.md — Step 1: Pre-flight, line 21 (vs skills/unit-test/SKILL.md line 28)

- **Quote:** "process each repo independently: run Steps 1–9 inside the repo the user is targeting"
- **Problem:** tdd's multi-repo sentence is a chimera of unit-test's all-repos policy ("run Steps 1-5 inside each repo that has `.claude/CLAUDE.md`") and brainstorm's single-repo policy ("process within the repo the user is targeting"), so "each repo independently" contradicts "the repo the user is targeting" in the same clause.
- **Fix:** Adopt brainstorm's wording in tdd: "process within the repo the user is targeting; if ambiguous, ask which repo" — dropping the copied "each repo independently" fragment.
- **Best practice:** BP13, BP21
- **Verifier:** CONFIRMED — Quote verbatim at tdd:21. unit-test:28 reads 'process each repo independently: run Steps 1-5 inside each repo that has .claude/CLAUDE.md' (all-repos) and brainstorm:24 reads 'process within the repo the user is targeting' (single-repo) — tdd's sentence splices the two into a self-contradicting clause. Adopting brainstorm's wording breaks nothing (no test enforcement on this sentence).

#### F3. [medium/ambiguity] skills/branch/SKILL.md — Step 3: Derive Branch Name, line 74 (vs skills/commit/SKILL.md line 89; verbatim twin at skills/worktree/SKILL.md line 51)

- **Quote:** "if `git show-ref --verify --quiet refs/heads/<branch-name>` succeeds (branch exists), append `-2` to the slug"
- **Problem:** Branch-name collision handling has three policies across the five branch-naming.md consumers: branch and worktree carry this verbatim-duplicated auto-suffix block, commit instead says "report the error and let the user choose a different name or cancel", and tdd/workflow don't handle collisions at all — while the shared branch-naming.md all five load omits the topic.
- **Fix:** Add a "Collision handling" section to skills/commit/references/branch-naming.md as the single default policy and replace the two inline copies with pointers; have commit/tdd/workflow follow it (or state their divergence explicitly).
- **Best practice:** BP13, BP17, BP23
- **Verifier:** CONFIRMED — Verbatim twins at branch:74 and worktree:51; commit:89 diverges to report-and-ask; tdd:111 and workflow:65 load branch-naming.md but have no collision handling at all; the shared reference omits the topic entirely. All five consumers verified; nothing in validate.sh or expected-outputs.yaml enforces the duplication. Note commit's divergence is plausibly deliberate (the user pre-approves the exact branch name via AskUserQuestion), which the finding's 'or state their divergence explicitly' clause already accommodates.

#### F4. [low/redundancy] skills/code-review-deep/SKILL.md — Step 3: User Confirmation, line 71

- **Quote:** "Mid-iteration interrupts may leave the working tree inconsistent; clean iterations are fully recoverable via `--resume`."
- **Problem:** This user-facing interrupt caveat survives in only one of the three hand-copied deep-skill warning blocks — refactor-deep and unit-test-deep run the identical loop/commit machinery with the same interrupt risk but their Step 3 warnings omit it.
- **Fix:** Either add the caveat to refactor-deep and unit-test-deep's warning blocks or move the invariant warning sentences into the shared harness reference and keep only the per-skill cost framing inline.
- **Best practice:** BP23, BP22
- **Verifier:** CONFIRMED — Verbatim at code-review-deep:71. refactor-deep (Step 3, lines 65-70) and unit-test-deep (Step 3, lines 66-70) run the same commit/bisect loop machinery (orchestrator-loop-single and -paired) with identical mid-iteration interrupt risk, yet their otherwise near-identical warning blocks omit the caveat. Not test-enforced; low severity appropriate.

#### F5. [low/convention-conflict] references/skill-handoff.md — "Closing tip wording", line 33 (inline copies: 18 sites across brainstorm, init, jira, permissions, reset, spec-init, unit-test, worktree, and the three -deep skills)

- **Quote:** "must use one of the variants below **verbatim** … Drift is the failure mode this section exists to prevent"
- **Problem:** The closing-tip convention is implemented by two coexisting mechanisms — 11 skills use the pointer form ("emit the closing tip per skill-handoff.md — use Variant X") while 18 sites inline the variant text verbatim — and although all inline copies currently match, no validate.sh check pins them, so the exact failure mode the reference names can occur silently.
- **Fix:** Add a validate.sh assertion that every `**Tip:**` line in skills/*/SKILL.md string-matches one of the three canonical variants (or converge the inline sites to the pointer form the majority already uses).
- **Best practice:** BP11, BP13
- **Verifier:** ADJUSTED — Facts all verified: 15 full-sentence Variant C inline copies across 8 skills plus 3 Variant A copies in the three -deep skills = 18 inline sites; ~12 files use the pointer form; validate.sh pins only the handoff skill's 'Variant A' token — no assertion covers any tip text. All inline copies currently match. But the proposed change needs correction: exact string-match works only for Variant C; Variants A and B contain substituted placeholders, so the validate.sh assertion must prefix/pattern-match those (or the repo should converge inline sites to the pointer form, the finding's own alternative).
  - **Revised severity:** low
  - **Revised fix (implement this one):** Add a validate.sh assertion that every closing **Tip:** line in skills/*/SKILL.md either exactly matches Variant C or begins with the fixed Variant A/B prefixes ('**Tip:** stay in this conversation when running' / '**Tip:** for `'), or converge the 18 inline sites to the pointer form the other ~12 skills use.

#### F6. [low/redundancy] skills/brainstorm/SKILL.md — Step 7 plan-mode block, lines 227 and 235–237 (near-verbatim twin at skills/jira/SKILL.md lines 216 and 224–226)

- **Quote:** "append a "Refined plan" section to `<spec-path>` to capture the refined plan, and stop"
- **Problem:** The ~150-word plan-mode carve-out block (the "How this conversation should run" paragraph plus the 3-step user instructions) is hand-duplicated between brainstorm and jira and has already diverged subtly — jira pins "heading exactly `### Refined plan`" (which jira-refresh.md protects by that exact string) while brainstorm leaves the heading level unspecified — and both copies must track skill-handoff.md's fragile plan-mode semantics in lockstep.
- **Fix:** Hoist the invariant paragraph and 3-step instruction block into references/skill-handoff.md (which both skills already cite) with placeholders for doc path and heading, keeping only the prompt-body fields inline per skill.
- **Best practice:** BP1, BP13, BP7
- **Verifier:** CONFIRMED — Quote verbatim at brainstorm:227; near-verbatim twin at jira:216 with the 3-step user-instruction blocks at brainstorm:235-237 / jira:224-226. Divergence confirmed: jira pins 'heading exactly `### Refined plan`' and jira-refresh.md:64 protects that exact string, while brainstorm leaves the heading level unspecified. Not pinned by validate.sh (only the '## Scenarios'/'### Scenario:' contract is). Low severity is right — tdd's spec-context-detection.md does not grep for the heading, so brainstorm's laxity is drift risk, not current breakage. Hoisting into skill-handoff.md (which both skills already cite, and whose line 78 would need a matching update) is mechanically safe.

#### F7. [low/ambiguity] skills/init/references/prerequisite-check.md — Fallback Behavior, line 14 (vs inline hard-stops at unit-test:30, tdd:25, brainstorm:28, workflow:21)

- **Quote:** "**If either is missing**, warn the user and recommend running `/optimus:init` first. Use these fallbacks so the skill can still run"
- **Problem:** The same prerequisite check exists in three forms with no documented rationale: the shared reference prescribes warn-and-continue with fallbacks (followed by code-review/refactor), the three -deep skills load it but override to hard-stop, and four skills (brainstorm, tdd, workflow, unit-test) inline a hard-stop paraphrase that never references the shared file — so a future change to the reference silently misses them.
- **Fix:** Route all consumers through prerequisite-check.md and add a one-line strictness note there ("analysis skills use fallbacks; generative skills hard-stop") so the per-skill policy divergence is deliberate and centrally maintained.
- **Best practice:** BP13, BP21
- **Verifier:** ADJUSTED — Facts verified: prerequisite-check.md:14 prescribes warn-and-continue; code-review:38 and refactor:29 apply it with fallback logic; the three -deep skills load it but hard-stop on missing CLAUDE.md; brainstorm:28, tdd:25, unit-test:30, workflow:21 inline hard-stops without referencing the file. But the proposed change over-corrects: routing the four generative skills through an 18-line fallback reference only to override it reproduces the deep skills' awkward load-plus-override pattern for a one-sentence check. The divergence looks deliberate (analysis skills can run on generic guidelines; generative skills need project context) — the real gap is that this rationale is undocumented.
  - **Revised severity:** low
  - **Revised fix (implement this one):** Add a one-line strictness note to prerequisite-check.md ('analysis skills use these fallbacks; generative and deep skills hard-stop on missing CLAUDE.md') so the divergence is documented centrally; leave the inline hard-stops in place rather than rerouting all consumers through the reference.

#### F8. [medium/doc-drift] skills/commit/references/branch-naming.md — header, line 3
*Found by verifier (adversarial pass) — treat as confirmed*

- **Quote:** "Consumed by `branch`, `commit`, `tdd`, and `worktree` skills."
- **Problem:** The shared reference's own consumer list omits `workflow` (skills/workflow/SKILL.md:65 loads it), so a maintainer editing the convention validates against the wrong consumer set — the exact silent-drift mechanism this topic targets.
- **Fix:** Update the consumer list to include `workflow` (and fold this into the finding-3 fix so the new Collision handling section is written against all five consumers); commit/README.md:94's '(shared with TDD)' should be corrected in the same pass.
- **Best practice:** BP13

#### F9. [medium/weak-description] skills/unit-test-deep/SKILL.md — frontmatter description, line 2
*Found by verifier (adversarial pass) — treat as confirmed*

- **Quote:** "Use to drive coverage up on a codebase that has untestable barriers"
- **Problem:** unit-test-deep's Step 2 hard-stops without a documented test command ('If none is documented, stop and recommend /optimus:init') yet its description omits the 'Requires a test command in .claude/CLAUDE.md' clause both sibling -deep descriptions carry — a sibling-inconsistent description that under-promises a hard prerequisite.
- **Fix:** Add the same 'Requires a test command in .claude/CLAUDE.md.' sentence to unit-test-deep's description so the three -deep skills declare the shared prerequisite identically.
- **Best practice:** BP4, BP13

### Already well-tuned (preserve; do not churn while fixing the above)

- Shared-reference architecture is genuinely load-bearing: multi-repo-detection, branch-naming, gather-changes, constraint-doc-loading, verification-protocol, prerequisite-check, and the orchestrator loop bodies are all consumed via pointers from many skills rather than copied.
- references/skill-handoff.md canonicalizes closing-tip wording with explicit variants and an anti-paraphrase rule — all 18 inline copies currently match a canonical variant verbatim, including the deep skills' Variant A substitutions.
- validate.sh pins dozens of cross-skill textual contracts (tdd/workflow→pr summary headings, brainstorm↔tdd scenario headings, how-to-run trigger keys, handoff tokens), making the riskiest couplings test-enforced rather than convention-only.
- Sibling analysis skills (code-review, refactor) use identical pointer framing for constraint-doc loading, submodule exclusion, and the verification protocol — consistent wording with zero drift between the pair.
- commit and commit-message split cleanly over gather-changes.md and conventional-commit-format.md with no duplicated procedure text.

---

## 1. unit-test — 6/10

Files: `skills/unit-test/SKILL.md` (222 lines) plus the skill's `agents/`, `references/`, `templates/`, `README.md`, and any shared references named in findings.

**Improvement need:** assessor 5 → verified **6** / 10. Rebuild recommended: no.

**Description assessment (433 chars):** Strong: leads with what ("Improves unit test coverage on demand"), states the when ("Use when test coverage is low or after adding new code that lacks tests"), the prerequisite (/optimus:init), the safety guarantee, and a negative trigger routing to the sibling /optimus:unit-test-deep — all in 433 chars, third person, scannable in a menu. One accuracy flaw: "only adds new test files" overstates the actual behavior, since Step 4 gate question 1 instructs appending tests to existing test files (see finding on the conservative constraint).

**Assessor score rationale:** The normal-mode path is well-built and needs almost nothing. The consequential defects cluster in harness-mode integration — a missing revert-on-abandon that lets one failing test trigger the CLI's whole-cycle rollback (discarding the cycle's good tests), a dead/conflicting full-suite clause in Final verification, and undefined stop-gate output that degrades to parse-failure termination on --allow-red baselines — plus one core-constraint contradiction that also touches the description and README. All are sentence-level targeted fixes to a load-bearing feature (unit-test-deep), which puts this at the low end of "moderate, several targeted fixes" rather than minor polish.

**Verifier adjusted rationale:** Every finding survived verification (5 confirmed, 2 adjusted for fix accuracy/sufficiency, none refuted — quotes verbatim, none test-enforced), and verification added a second high-severity gap in the same cluster: both the abandon branch AND the bug branch of the per-test workflow can leave a failing test active, and cli.py's cmd_unit_test_step provably responds by rolling back and discarding the entire cycle before convergence signals are even read — which also weakens the assessor's stop-gate fix (a red baseline burns to cap even with valid JSON). Add the coverage.after contradiction that can disable the plateau/diminishing-returns net, and the harness-mode integration of this load-bearing skill has roughly six consequential, mutually reinforcing defects, though each fix remains a sentence-level edit to SKILL.md, coverage-harness-mode.md, and README.md and the normal-mode path needs only minor polish. That lands at the top of 'moderate, several targeted fixes' (6) rather than the assessor's 5; structure and delegation are sound, so no rebuild.

### Findings to implement

#### F1. [high/missing-guidance] skills/unit-test/SKILL.md — Step 4 > Per-test workflow, line 175

- **Quote:** "If still failing after 3 attempts, flag as untestable and move on"
- **Problem:** The abandon path never says to revert/delete the failing test file; in normal mode Final verification's revert rescues this, but harness mode skips that run, while references/orchestrator-loop-paired.md line 204 requires fail-abandoned tests "not left active".
- **Fix:** Add to the abandon branch: "revert the test file (or remove the appended cases) before moving on — an abandoned failing test must not remain active", so the guarantee holds in both modes.
- **Best practice:** BP21, BP23
- **Verifier:** CONFIRMED — Quote verbatim at SKILL.md line 175. Harness mode skips Final verification (coverage-harness-mode.md section 3: 'Do NOT run the full test suite at the end'), so an abandoned failing test stays on disk. cli.py cmd_unit_test_step (lines 1002-1023) runs the full suite before merging and on red restores the pre-cycle snapshot and drops the whole session — one lingering failing test discards every good test the cycle wrote, and because the session is dropped the item is never recorded as fail-abandoned, so later cycles can re-attempt the same target. The 'not left active' contract lives only in orchestrator-loop-paired.md line 204, a file the executing subagent never reads. The proposed change is sound and breaks no pinned string.

#### F2. [medium/ambiguity] skills/unit-test/SKILL.md — Step 4 > Final verification, line 183

- **Quote:** "In harness mode, record the affected item's status as `fail-abandoned` in the JSON output at Step 6."
- **Problem:** This clause sits inside the Final verification section conditioned on "the full-suite run", but coverage-harness-mode.md section 3 explicitly prohibits that run in harness mode ("Do NOT run the full test suite at the end"), so a fresh instance must guess whether harness mode runs the suite.
- **Fix:** Mark Final verification "Normal mode only" and delete the harness clause (the fail-abandoned status is already produced by the per-test abandon path); optionally add a pointer that the orchestrator owns the full run.
- **Best practice:** BP13, BP21
- **Verifier:** ADJUSTED — The contradiction is real: the clause is conditioned on 'the full-suite run', which coverage-harness-mode.md section 3 explicitly prohibits in harness mode, so the clause is dead-or-misleading text that invites the subagent to run the forbidden suite. But the assessor's parenthetical is wrong — the per-test abandon path says 'flag as untestable' and never mentions fail-abandoned, so deleting the clause outright would remove SKILL.md's only explicit mapping of abandoned items to the fail-abandoned JSON status.
  - **Revised severity:** medium
  - **Revised fix (implement this one):** Mark Final verification 'Normal mode only' and MOVE (not delete) the fail-abandoned recording into the per-test abandon branch, merging it with finding 1's revert-on-abandon fix; optionally note the orchestrator owns the full run.

#### F3. [medium/under-specification] skills/unit-test/SKILL.md — Step 1 > Inline harness mode detection, line 24

- **Quote:** "skip user confirmation, run Steps 2–4 exactly once, then output structured JSON via Step 6 and stop"
- **Problem:** Neither SKILL.md nor coverage-harness-mode.md defines what a harness-mode pass does when a Step 2 stop gate fires — the gates emit user-facing markdown handoff messages the orchestrator cannot parse, and unit-test-deep's --allow-red baseline makes a red suite reaching this gate a supported scenario.
- **Fix:** Specify harness-mode stop-gate behavior, e.g. emit the Step 6 JSON with no_new_tests: true and a documented failure/blocked field naming the gate, instead of the conversational handoff text.
- **Best practice:** BP16, BP23
- **Verifier:** ADJUSTED — The gap is real: 'run Steps 2–4' includes Step 2's stop gates, whose only output is conversational markdown; unit-test-deep passes --allow-red unconditionally (SKILL.md line 118: 'a non-green baseline is not a reason to refuse') and its Step 2 explicitly expects the unit-test phase to 'surface the gap' for a missing framework — yet a gate firing in harness mode yields no json:harness-output block, and per orchestrator-loop-paired.md step 3 two consecutive parse failures terminate the run as a generic 'parse-failure'. However the proposed change is insufficient: cmd_unit_test_step runs the full suite BEFORE reading convergence signals and on red prints 'continue' (cli.py 1013-1023), so emitting no_new_tests:true JSON merely swaps parse-failure termination for burning every cycle to the cap on a red baseline.
  - **Revised severity:** medium
  - **Revised fix (implement this one):** Define harness-mode gate behavior as emitting the Step 6 JSON with a blocked/gate field AND give the orchestrator side a termination rule for it (check-termination or an explicit orchestrator instruction to stop the loop and surface the gate message when the unit-test phase reports blocked).

#### F4. [medium/ambiguity] skills/unit-test/SKILL.md — Step 4 > Conservative constraint, line 165 (vs gate question 1, line 158)

- **Quote:** "**Only add new test files.** Never refactor or modify existing source code"
- **Problem:** The headline constraint contradicts gate question 1 ("If yes, add tests there instead of creating a new file"), and the overstatement is repeated in the description and README ("adds new test files only... never modifies existing tests").
- **Fix:** Restate the constraint as "only add new tests — new files, or new cases appended to existing test files; never modify existing test logic or source code", and align the description and README feature bullet with that wording.
- **Best practice:** BP13, BP4
- **Verifier:** CONFIRMED — Quote verbatim at line 165; gate question 1 (line 158) directs 'If yes, add tests there instead of creating a new file', which requires modifying an existing test file — a direct contradiction of the headline. The overstatement is repeated in the description ('only adds new test files') and README.md line 15 ('adds new test files only; may fix a newly-written test but never modifies existing tests'). Grep of scripts/ and test/ shows none of these strings are test-enforced, so the reword is safe. Real BP13/BP4 inconsistency a literal executor could act on either way.

#### F5. [low/redundancy] skills/unit-test/SKILL.md — Step 2 > Cycle context injection, lines 62-71

- **Quote:** "prepend a concise context block to the agent prompt before the main instructions"
- **Problem:** This ~10-line harness-only spec duplicates coverage-harness-mode.md section 2's briefer version of the same rule ("include a brief context block listing previously created test files and known untestable items"), so every normal-mode run pays the tokens and the two copies can drift.
- **Fix:** Move the detailed bullet spec into coverage-harness-mode.md section 2 (already mandatory reading in harness mode) and leave a one-line pointer in SKILL.md.
- **Best practice:** BP1, BP7
- **Verifier:** CONFIRMED — Quote verbatim at line 64. The ~10-line harness-only spec sits inline while coverage-harness-mode.md section 2 carries a one-sentence version of the same rule — two statements of one rule at different granularity, driftable, and normal-mode invocations load the detail for nothing. Not enforced by validate.sh or expected-outputs.yaml (no matches). The harness subagent is always instructed to read coverage-harness-mode.md (dispatch prompt in orchestrator-loop-paired.md step 2), so relocating the detail there loses nothing. Low severity is right — this is BP7 placement more than harmful duplication.

#### F6. [low/redundancy] skills/unit-test/SKILL.md — Step 1 > Scope, line 49

- **Quote:** "Parse optional path argument (e.g., `/optimus:unit-test src/api`) to limit scope."
- **Problem:** Restates the "Parse invocation arguments" section from the top of the same step, including the same example and the same full-project default.
- **Fix:** Fold the default-scope sentence into "Parse invocation arguments" and keep the Scope section only for the monorepo/multi-repo detection paragraph.
- **Best practice:** BP1
- **Verifier:** CONFIRMED — Quote verbatim at line 49. Within the same Step 1, 'Parse invocation arguments' (lines 13-20) already states the optional path, the identical src/api example, and the full-project default. The Scope section's only novel content is the monorepo/project-detection paragraph. Nothing pins these strings; the fold-in is safe. Correctly rated low — a two-line saving.

#### F7. [low/doc-drift] skills/unit-test/README.md — Skill Structure table, line 124

- **Quote:** "`SKILL.md` | Skill definition with 5-step workflow"
- **Problem:** SKILL.md has six steps (Step 6: Harness Output), and the shared-file table omits the other consumed references (coverage-harness-mode.md, testing-anti-patterns.md, verification-protocol.md, skill-handoff.md, project-detection.md).
- **Fix:** Update to "6-step workflow" (or drop the count) and list, or generically mention, the remaining shared references.
- **Best practice:** D9 (rubric context #3)
- **Verifier:** CONFIRMED — Quote verbatim at README.md line 124. SKILL.md has six steps (Step 6: Harness Output), so the count is stale, and the Skill Structure table lists only two shared references while SKILL.md also consumes project-detection.md, verification-protocol.md, testing-anti-patterns.md, skill-handoff.md, and coverage-harness-mode.md. Genuine D9 drift under rubric context #3 (README existence is required; drift is flaggable). Low severity appropriate.

#### F8. [high/under-specification] skills/unit-test/SKILL.md — Step 4 > Per-test workflow, line 176
*Found by verifier (adversarial pass) — treat as confirmed*

- **Quote:** "If the failure reveals an actual **bug in existing code**, report the bug but do not fix it"
- **Problem:** The bug branch never says what to do with the still-failing test file — the assessor's finding-1 fix covers only the 3-attempts abandon branch, so in harness mode a bug-evidencing failing test still turns the CLI's post-phase suite red, rolling back the whole cycle and dropping the bug record with the session (cli.py 1013-1023).
- **Fix:** In the bug branch, instruct: revert or skip the failing test (keep the bug in Bugs Discovered / bugs_discovered JSON) and, in harness mode, record the item as fail-abandoned with failure_reason naming the bug — a failing test must not remain active in either mode.
- **Best practice:** BP21, BP23

#### F9. [medium/ambiguity] references/coverage-harness-mode.md — section 3 'Generate and write tests' vs section 5 JSON schema
*Found by verifier (adversarial pass) — treat as confirmed*

- **Quote:** "Do NOT run the full test suite at the end … Coverage measurement during analysis is fine; a final verification run is not"
- **Problem:** The schema in section 5 requires coverage.after/delta (feeding no_coverage_gained and check_coverage_plateau, which needs delta == 0), but the subagent is never told how to obtain 'after' when the end-of-pass suite run is forbidden — a conservative subagent reports after=null every cycle, null deltas never trip the plateau check (convergence.py line 44), and the diminishing-returns net is silently disabled so the loop runs to cap on the most expensive orchestrator skill.
- **Fix:** State explicitly whether one post-write coverage-instrumented run counts as permitted 'measurement' (recommended) or, if not, declare that after/delta may be null and have the CLI derive cross-cycle deltas from coverage.history so the plateau check still fires.
- **Best practice:** BP21, BP13

### Already well-tuned (preserve; do not churn while fixing the above)

- Description nails what+when+prerequisite+negative trigger to /optimus:unit-test-deep in 433 chars — well-tuned for the slash-menu audience.
- Step 2 stop gates are exemplary conditional workflows: two failure classes (Fail-assertion vs Fail-build) with exact verbatim user messages and correct skill-handoff routing (BP16/BP21/BP23).
- Per-test loop (write -> run immediately -> max 3 fix attempts -> report bugs without fixing) is a tight BP11 feedback loop with a clear escape hatch.
- Discovery is delegated to a single sonnet agent with a strict, parseable return format and hard caps (30 files/category); the "Data carried forward" table makes inter-step dependencies explicit.
- Heavy reuse of shared references (testing-anti-patterns, verification-protocol, multi-repo/project detection, monorepo scoping) instead of inlining keeps the body at 222 lines with genuine progressive disclosure.

---

## 2. permissions — 5/10

Files: `skills/permissions/SKILL.md` (109 lines) plus the skill's `agents/`, `references/`, `templates/`, `README.md`, and any shared references named in findings.

**Improvement need:** assessor 4 → verified **5** / 10. Rebuild recommended: no.

**Description assessment (256 chars):** At 256 chars it is concise, third person, leads with a strong verb, and covers what + when ("Use after /optimus:init ... or standalone"), which suits the human-scanned slash menu well. Its one gap: it frames the hook as only "path-restriction", underselling the two most surprising runtime effects — git branch protection (commits/pushes blocked on master/main) and precious-file protection — which a user would want to anticipate before invoking.

**Assessor score rationale:** The load-bearing parts — detection, exact-copy hook install, the careful non-destructive merge with a user-gated git-deny reconciliation, and the verify-before-report gate — are correct and well-calibrated, and I verified all counts and security-model claims match the actual templates. The real issues are second-order: an ambiguous step ordering in Step 5, a paragraph-heavy report duplicating README/hook-header content, and three drift-prone hardcoded copies of template values (precious patterns, 13/30 counts, branch list) in a repo with a documented history of exactly this drift. Several targeted fixes, none requiring restructuring: 4/10.

**Verifier adjusted rationale:** All seven findings survive (six CONFIRMED, one ADJUSTED for overstated framing) — I verified every quote verbatim, confirmed the 13/30/10/29 counts are accurate today (so the drift findings are about unsynced copies, not existing errors), and confirmed none of the flagged duplication is enforced by validate.sh or expected-outputs.yaml. But the assessor's 4 undercounts two high-severity robustness gaps on the skill's most fragile, most load-bearing operation: the hook install is verified only by a vague 'contains the hook logic' check even though a mangled copy fails open silently (the worst failure mode a security skill can have — user believes protections are active), and the unconditional overwrite in Step 3 silently destroys PROTECTED_BRANCHES customizations that the skill's own report tells users to make. Both are targeted one-step fixes, not structural — the core detect/install/merge/verify flow remains excellent, so this stays 'moderate, several targeted fixes' rather than 'significant': 5/10, rebuild not warranted.

### Findings to implement

#### F1. [medium/structure] skills/permissions/SKILL.md — Step 5: Verify and Report, line 98

- **Quote:** "Scan for precious unversioned files in the project:"
- **Problem:** Checklist item "4." (the precious-file scan) is placed after the "Report to the user" block even though the intro says "Fix any issues before reporting" and the scan's results feed the report ("report them as protected files"), so a fresh model must guess whether to scan before or after reporting.
- **Fix:** Move the scan (and its custom-pattern AskUserQuestion) before the "Report to the user:" block so items 1-4 form one contiguous pre-report checklist, or renumber it as an explicit post-report step with its own heading.
- **Best practice:** BP10, BP22
- **Verifier:** CONFIRMED — Quote verbatim at line 98. The numbered checklist runs 1-3, is interrupted by the unnumbered 'Report to the user:' bullet block (lines 84-96), then resumes with '4.' — yet the intro (line 75) says 'Fix any issues before reporting' and item 4's own text says 'report them as protected files', so the scan's output feeds a report that structurally precedes it. Real ordering ambiguity, not taste; the proposed reorder breaks no repo mechanics (nothing in validate.sh or expected-outputs.yaml pins this structure).

#### F2. [medium/redundancy] skills/permissions/SKILL.md — Step 5 "Report to the user", lines 89-96

- **Quote:** "Memory-store exemption: writes and deletes in Claude's own per-project auto-memory store (`~/.claude/projects/.../memory/`) are allowed without a prompt…"
- **Problem:** Six of the report bullets are 60-90-word fixed paragraphs (memory store, scratchpad, trust model, sandboxing, auto mode, native protected paths) that restate content already in the README and the hook's own header comments — three of them even end with a pointer to the README section containing the same text — producing a bloated verbatim report every run.
- **Fix:** Compress each note to a one-line summary plus its README section pointer (keep the full list of topics so the security-model communication is preserved); the paragraph-length exposition stays in README.md and the hook header.
- **Best practice:** BP1, BP14
- **Verifier:** CONFIRMED — Quote verbatim at line 89. Six report bullets (lines 89-96) are 60-90-word fixed paragraphs restating README sections nearly verbatim (README lines 101-103 for the exemptions; 'Where This Fits', 'Relationship with auto mode', 'native protected paths' sections) — three bullets even end with pointers to the README section carrying the same text. expected-outputs.yaml has no output_contains for permissions, so the report wording is not test-enforced. The compress-to-one-line-plus-pointer change preserves the security-model communication while cutting ~40% of the body (BP1).

#### F3. [medium/redundancy] skills/permissions/SKILL.md — Step 5 item 4, line 100

- **Quote:** "find . -maxdepth 4 \( -name ".env*" -o -name "local.settings.json""
- **Problem:** The hardcoded 29-pattern find command is a third independent copy of the precious-file list (hook is_precious(), README table, this command) with no sync check, so any pattern added to the hook template silently drops out of the scan — this repo has already seen exactly this class of copy drift three times with the hook itself.
- **Fix:** Instruct the model to derive the -name patterns from the is_precious() function in the just-installed .claude/hooks/restrict-paths.sh instead of hardcoding them, making the hook the single source of truth.
- **Best practice:** BP13, BP19
- **Verifier:** CONFIRMED — Quote verbatim at line 100. I verified the find command's 29 patterns match is_precious() one-to-one today — but there is genuinely no sync check anywhere (validate.sh has zero coupling between this SKILL.md and the hook template), it is a third independent copy (hook, README table, find command), and this repo has a documented history of exactly this copy-drift class with the hook itself. Deriving patterns from the just-installed hook is feasible (the appsettings.json exclusion maps naturally to -name "appsettings.*.json") and makes the hook the single source of truth.

#### F4. [low/weak-description] skills/permissions/SKILL.md — frontmatter, line 2

- **Quote:** "Creates settings.json with allow/deny rules and a path-restriction hook."
- **Problem:** The description omits git branch protection and precious-file protection, so a user scanning the menu cannot anticipate that after running it, git commit/push on master will be hard-blocked — the skill's most surprising side effect.
- **Fix:** Mention the hook's full scope, e.g. "...and a hook enforcing path restrictions, git branch protection, and precious-file safeguards" (fits well under 1024 chars).
- **Best practice:** BP4
- **Verifier:** CONFIRMED — Quote verbatim at line 2 (description is 256 chars, verified). The hook's most surprising runtime effects — git commit/push hard-blocked on master/main and precious-file protection — are absent from the description. Under repo context #1 the description's audience is a human scanning the slash menu who should be able to anticipate these side effects; the proposed addition fits easily under 1024 chars. Low severity is right.

#### F5. [low/doc-drift] skills/permissions/SKILL.md — Step 5 checklist item 2, lines 79-80

- **Quote:** "`permissions.allow` with at least the 13 tool entries from the template"
- **Problem:** The verification hardcodes the counts "13" and "30" (and line 92 hardcodes the 10-branch PROTECTED_BRANCHES list), duplicating template values that will silently go stale the next time templates/settings.json or the hook is edited.
- **Fix:** Replace the literal counts with "every allow entry / deny pattern from the template" and have the branch-protection bullet read the branch list from the installed hook rather than restating it.
- **Best practice:** BP13, BP12
- **Verifier:** CONFIRMED — Quote verbatim at line 79. Verified: template has exactly 13 allow entries, 30 deny patterns, and the hook has exactly the 10 branches restated at line 92 — accurate today but three more unsynced copies of template values with no CI coupling. The load-bearing check is 'the entries from the template' (which the model has just read in Step 4), so dropping the literal counts loses no verifiability and removes the drift surface. Not test-enforced anywhere.

#### F6. [low/ambiguity] skills/permissions/SKILL.md — Step 4 "Merge principles", line 69

- **Quote:** "which are reconciled with the user when existing patterns go beyond the template (see step 2 above)"
- **Problem:** "step 2 above" means numbered sub-item 2 of the merge list, but the skill also has a top-level "Step 2: Create Directory Structure", so the cross-reference collides with the skill's own step numbering.
- **Fix:** Say "see the permissions.deny merge rule above" or rename the merge list items (a/b/c) so sub-items can't be confused with the skill's Step N headings.
- **Best practice:** BP13
- **Verifier:** CONFIRMED — Quote verbatim at line 69. 'step 2' means numbered merge-list item 2 (permissions.deny), but the skill has a top-level 'Step 2: Create Directory Structure' heading — an objective numbering collision, not taste. A strong model resolves it from context; a weaker one may not (BP3). Low severity and the proposed disambiguation are both correct.

#### F7. [low/missing-guidance] skills/permissions/SKILL.md — Step 1, line 26

- **Quote:** "Check if `.claude/settings.json` exists. If so, read its full content — it will be preserved during merge."
- **Problem:** The merge workflow assumes the existing settings.json parses; there is no guidance for the common real-world case of a hand-edited, malformed file (trailing comma, comments), leaving the model to guess between overwriting, aborting, or asking.
- **Fix:** Add one line to Step 1 or the merge principles: if the existing file is not valid JSON, stop and ask the user how to proceed rather than overwriting it.
- **Best practice:** BP23
- **Verifier:** ADJUSTED — Quote verbatim at line 26 and the gap is real (no malformed-JSON branch), but the problem statement overstates the risk: the merge principles already state 'Never overwrite the file' and 'The result must be valid JSON', which fences off the destructive outcome — the plausible bad path is a silent best-effort repair-and-rewrite, not overwrite-vs-abort-vs-ask guessing. Keep severity low; the fix is worthwhile as a one-line hardening consistent with the skill's user-gated reconciliation pattern.
  - **Revised severity:** low
  - **Revised fix (implement this one):** Add one line to the Merge principles (not Step 1): 'If the existing file is not valid JSON, do not repair or overwrite it silently — show the parse problem and ask the user how to proceed.'

#### F8. [high/under-specification] skills/permissions/SKILL.md — Step 5: Verify and Report, checklist item 1, line 77
*Found by verifier (adversarial pass) — treat as confirmed*

- **Quote:** "`.claude/hooks/restrict-paths.sh` exists and contains the hook logic"
- **Problem:** The only verification of the security-critical hook install is the vague 'contains the hook logic' — a CRLF-mangled, truncated, or paraphrased copy passes it, and a broken PreToolUse hook fails OPEN at runtime, so every protection the report then claims (branch, precious-file, path restriction) is silently absent.
- **Fix:** Replace with a concrete gate: diff/cmp the installed hook against `$CLAUDE_PLUGIN_ROOT/skills/permissions/templates/hooks/restrict-paths.sh` (exact-copy is already the spec) and run `bash -n .claude/hooks/restrict-paths.sh`; re-copy on mismatch before reporting.
- **Best practice:** BP21, BP11, BP23

#### F9. [high/missing-guidance] skills/permissions/SKILL.md — Step 3: Install Path-Restriction Hook, line 40
*Found by verifier (adversarial pass) — treat as confirmed*

- **Quote:** "Copy the hook template to the project (overwrites any existing version):"
- **Problem:** On update runs Step 3 silently wipes user customizations the skill itself recommends — the line 92 report bullet says 'Customize the PROTECTED_BRANCHES array in .claude/hooks/restrict-paths.sh' with no replaced-on-re-run caveat (the warning at line 103 covers only the custom-precious-pattern flow) — so a user who added a protected branch and later re-runs the skill loses that protection with no signal, contradicting the skill's own user-gated preserve-user-config philosophy for settings.json.
- **Fix:** When Step 1 detected an existing hook, diff it against the template before overwriting; if user modifications exist (e.g., a changed PROTECTED_BRANCHES or is_precious), list them and AskUserQuestion (re-apply after install / discard), mirroring the git-deny reconciliation; also add the replaced-on-re-run caveat to the line 92 customization bullet.
- **Best practice:** BP20, BP16, BP23

### Already well-tuned (preserve; do not churn while fixing the above)

- Security Model table at the top gives the executing model the full behavioral contract at a glance before any step runs (BP22).
- Degrees of freedom are calibrated correctly: exact-copy, do-not-modify for the fragile hook install (BP2 low freedom), high freedom for detection and reporting prose.
- Step 4's merge instructions are exemplary plan-validate-execute: never remove entries, never overwrite, and the one destructive reconciliation (git deny patterns) goes through an explicit AskUserQuestion with recommended/keep options and stated consequences (BP16, BP20, BP21).
- Step 5 opens with a genuine verification gate ("Fix any issues before reporting") with concrete success criteria per file (BP11).
- Right-sized structure: 109-line body, zero reference chain, templates only — no progressive-disclosure debt (BP6-BP8).
- Ends with a conditional Next Step recommendation plus the fresh-conversation tip, matching house convention exactly.

---

## 3. handoff — 5/10

Files: `skills/handoff/SKILL.md` (131 lines) plus the skill's `agents/`, `references/`, `templates/`, `README.md`, and any shared references named in findings.

**Improvement need:** assessor 3 → verified **5** / 10. Rebuild recommended: no.

**Description assessment (603 chars):** Accurate to actual behavior, third person, and front-loaded — "Compacts the current conversation into a single self-contained handoff document" carries the meaning even under menu truncation. It covers what, when ("Use when pausing work…"), and the re-run enhance/overwrite behavior. At 603 chars it is mid-pack for this repo; slightly long for a slash menu but nothing is filler.

**Assessor score rationale:** The workflow, git classification, redaction spec, and house conventions are all well-executed in a compact 131-line body, so no structural work is needed. The two medium findings are targeted one-to-two-sentence fixes (a post-write redaction verification gate for the skill's central safety claim, and disambiguating emit-vs-guidance text in the template); the rest is polish (redundant restatements, one README claim, two rare-case clauses). That places it at minor-polish (3), not moderate.

**Verifier adjusted rationale:** Five of six findings survive adversarial checking (both mediums confirmed; three lows confirmed; the /optimus:commit-parenthetical redundancy refuted as a zero-cost, self-disambiguating cross-reference). Verification then surfaced a high-severity hole the assessor circled but never named: the redaction spec is textually scoped to inlined artifact content only ('Applied only to **inlined** content'), so conversation-derived prose is exempt from the scan that backs the unconditional 'redacted and safe to commit' claim — and the assessor's own proposed re-scan fix would inherit that scope bug. A second missed medium (the Continue-one branch never re-binds <slug>, so Step 6's write path can fork the handoff history) adds a real routing defect. The skill's architecture, git classification, and house-convention wiring remain excellent and every fix is a one-to-two-sentence edit that preserves all validate.sh tokens, so no structural work is needed — but with one high and three mediums clustered partly on the skill's load-bearing safety promise, this is 'moderate, several targeted fixes' (5), not the assessor's minor-polish 3.

### Findings to implement

#### F1. [medium/missing-guidance] skills/handoff/SKILL.md — Step 6: Write the document, then report and recommend (line 63)

- **Quote:** "tell the user the document is redacted and safe to commit"
- **Problem:** The skill's flagship safety promise (redaction) has no validate-fix-repeat gate — redaction happens pre-write in Step 5, then Step 6 declares the written file "safe to commit" without ever re-checking it.
- **Fix:** Add a post-write verification pass: re-scan the written docs/handoffs/<slug>.md against the Redaction patterns table and fix any hits before reporting; word the report as "redaction scan re-run clean" rather than an unconditional safety claim.
- **Best practice:** BP11, BP21
- **Verifier:** CONFIRMED — Quote verbatim at SKILL.md line 63. Redaction happens once, pre-write, in Step 5; Step 6 then makes an unconditional whole-document safety claim with no validate-fix-repeat gate — a textbook BP11 gap on the skill's flagship safety promise. Neither 'safe to commit' nor any Step 6 wording is a validate.sh token, so adding a post-write re-scan is safe. One correction: the fix must scan the FULL written file, because the Redaction patterns table self-scopes to 'inlined content' only (see missed finding M1) — a re-scan worded 'against the Redaction patterns table' would inherit that scope hole.

#### F2. [medium/ambiguity] skills/handoff/SKILL.md — Handoff document template, Relevant files & artifacts (lines 97-104)

- **Quote:** "### Inlined (not yet on remote) — omit if none"
- **Problem:** Inside the emit-verbatim template fence, author-only guidance is mixed into emitted text with inconsistent markers — an annotation appended to a real heading, "(omit if none)" in parentheses, and a third blockquote line ("Anchor each reference on a durable identifier … never cite line numbers") that is writer instruction sitting next to two reader-facing legend blockquotes — so a fresh Claude must guess what to copy into the document.
- **Fix:** Adopt one non-emit annotation convention (the [bracket] style used by tdd/workflow templates): move "— omit if none" off the heading (keeping the validate.sh token '### Inlined (not yet on remote)' intact) and either bracket the author-facing blockquote line or relocate it to a Step 4 bullet.
- **Best practice:** BP14, BP13
- **Verifier:** CONFIRMED — Quote verbatim at line 104. Inside the emit-verbatim ````markdown fence the skill mixes three annotation styles: '(omit if none)' on bold labels (lines 85, 89), an em-dash annotation on a real heading (line 104), and an author-facing blockquote line ('Anchor each reference on a durable identifier … never cite line numbers', line 99) sitting under two reader-facing legend blockquotes (lines 97-98) — a fresh Claude must guess what gets copied out. The repo-wide non-emit convention is bracket style ([If …] in how-to-run, jira, code-review, init, tdd quality-gate, workflow), so the proposed change matches house style. validate.sh checks '### Inlined (not yet on remote)' via substring grep -qF, which the change preserves.

#### F3. [low/redundancy] skills/handoff/SKILL.md — Step 4: Draft or reconcile the document (line 50)

- **Quote:** "Include **Goal**, **Focus for next session**, and **Next steps** only when the conversation makes them genuinely clear; otherwise omit them."
- **Problem:** The same omission rule is stated in Step 1 ("Never manufacture one"), this Step 4 bullet, the template intro (line 69), and again in the three template placeholders — four out-of-template/near-template restatements with slightly drifting formulations ("clear signal" vs "genuinely clear" vs "establishes a clear objective").
- **Fix:** Keep the policy once in Step 1 plus the in-template placeholder hints (where the model looks while filling), and drop the Step 4 restatement and the template-intro clause.
- **Best practice:** BP1, BP13
- **Verifier:** CONFIRMED — Verified: the omission policy appears at line 22 (Step 1, focus-only with 'Never manufacture one'), line 50 (Step 4), line 69 (template intro), and again in placeholders at lines 76, 80, 93 — with drifting phrasing ('clear signal' / 'genuinely clear' / 'establishes a clear objective'). Not test-enforced: validate.sh greps only the section headings ('## Goal', '## Next steps'), not the policy text, and expected-outputs.yaml has no handoff entries. Minor caveat that does not change the verdict: Step 1's line is focus-specific rather than a full restatement, and the general 'omit any section with nothing to say' clause in the template intro should be kept — only the three-section enumeration dropped, which is what the assessor proposed. Low severity is right.

#### F4. [low/under-specification] skills/handoff/SKILL.md — Step 2: Locate the doc; decide create, enhance, or overwrite (line 26)

- **Quote:** "the workspace root in a multi-repo workspace, otherwise the repo/project root"
- **Problem:** The shared detection algorithm yields four outcomes, but handoff's root policy only covers two — when the cwd is not a git repo and holds exactly one child repo (detection says "suggest the user cd into it"), whether the root is the cwd or the child repo is left to guessing.
- **Fix:** Add one clause resolving the leftover detection outcomes, e.g. "a single child repo → treat that repo as the root; no recognized structure → use the current directory and note it is not under version control (Step 6 already covers the reporting)."
- **Best practice:** BP16, BP21
- **Verifier:** CONFIRMED — Quote verbatim at line 26. multi-repo-detection.md yields four outcomes and states 'Each consuming skill applies its own policy after detection'; for exactly one child repo it says only 'suggest the user cd into it', and handoff's 'otherwise the repo/project root' does not resolve whether the root is the cwd or the child repo. The assessor's 'only covers two' framing slightly overstates (the 0-repo case is arguably covered by 'project root' plus Step 3's not-a-repo handling and Step 6's reporting), but the anchor defect — the single-child-repo case forces guessing — is real, the severity (low, rare case) is right, and the one-clause change breaks nothing (the 'multi-repo-detection.md' token is untouched).

#### F5. [low/doc-drift] skills/handoff/README.md — Usage (lines 28-30)

- **Quote:** "they're recorded as the next session's focus and the document is biased toward it"
- **Problem:** The README promises the document content is biased toward the passed arguments, but SKILL.md only uses args for the slug and the one-line Focus bullet — Step 4 fills the template "from what was actually discussed" with no weighting instruction.
- **Fix:** Either add a short clause to Step 4 ("when a Focus was recorded, weight Current state and Next steps toward that thread") or trim the README claim to "recorded as the next session's focus".
- **Best practice:** BP4 (accuracy vs behavior), D9
- **Verifier:** CONFIRMED — Quote verbatim at README.md lines 28-29. In SKILL.md, arguments feed only the slug derivation (Step 1, line 20) and the one-line 'Focus for next session' bullet (line 76); Step 4 fills the template 'from what was actually discussed' with no weighting instruction toward the recorded focus. Genuine D9 README-vs-SKILL drift; either direction of the proposed fix is sound and touches no validate.sh token. Low severity is correct — the practical gap is small since the slug already scopes the document's topic.

#### F6. [high/under-specification] skills/handoff/SKILL.md — Step 5 (line 57) and Redaction patterns intro (line 118)
*Found by verifier (adversarial pass) — treat as confirmed*

- **Quote:** "Applied only to **inlined** content."
- **Problem:** Redaction is explicitly scoped to bucket-2/3 inlined artifacts ('Scan everything you are about to inline'), so secrets the model writes into authored prose — Current state, Decisions/gotchas, Open questions (e.g. a connection string or sk- key quoted from the debugging conversation) — are never scanned, yet the description promises unscoped 'Redacts secrets and PII' and Step 6 declares the whole document 'safe to commit'; a literal (weaker) model commits the leak.
- **Fix:** Widen Step 5 to scan the entire drafted document body against the table (keeping the paths/references exemption for reference lines only) and change the table intro to 'Applied to everything written into the document'; combined with the assessor's post-write re-scan this closes the safety claim end-to-end. No validate.sh token is affected.
- **Best practice:** BP21, BP11, BP4

#### F7. [medium/ambiguity] skills/handoff/SKILL.md — Step 2 (line 29) vs Step 6 (line 61)
*Found by verifier (adversarial pass) — treat as confirmed*

- **Quote:** "**Continue one** (pick via a follow-up question, then treat as Enhance)"
- **Problem:** After 'Continue one', <slug> is never re-bound to the chosen file, and Step 6 still says write to docs/handoffs/<slug>.md with the Step-1-derived slug — a literal model writes the enhanced content of the picked doc to a NEW file under the Step 1 slug and leaves the picked handoff stale, silently forking the topic's history.
- **Fix:** Add one clause to the Continue-one branch: 'adopt the chosen file's slug as <slug> for the rest of the run.' Preserves the validate.sh tokens 'Continue one' and 'docs/handoffs/'.
- **Best practice:** BP16, BP13

### Refuted findings — do NOT implement

- [low/redundancy] skills/handoff/SKILL.md — Step 5: Redact inlined content (line 57) — "the same set `/optimus:commit` warns about"
  - **Refuted because:** Taste-level, below the 'real problem you'd defend under adversarial review' bar. The same sentence immediately designates the local table as the operative authority ('see the table's last two rows'), so the claimed misdirection (fresh Claude opening commit's SKILL.md) doesn't hold; the sets currently match exactly (commit line 28: .env, *.key, *.pem, *.pfx, credentials.*, secrets.*, *.sqlite, *.db vs the table's last two rows); and if commit's list ever drifts, handoff's runtime behavior is unchanged because the table remains the spec — no failure mode, only a stale 7-word aside. The parenthetical is an intentional cross-skill coherence pointer of negligible token cost, consistent with this repo's heavy cross-referencing style.

### Already well-tuned (preserve; do not churn while fixing the above)

- Step 3's git-state resolution puts low freedom exactly where the operation is fragile: exact commands (`git log --oneline @{upstream}..HEAD`, fallback `origin/HEAD..HEAD`) with explicit no-upstream/detached-HEAD/not-a-repo handling, all token-enforced by validate.sh.
- The three-bucket artifact classification (tracked+pushed → reference; modified/staged/unpushed → inline; untracked → inline) is decision-complete and directly serves the skill's core promise that the doc survives on another clone.
- The Redaction patterns table is a model BP21 artifact: concrete catches, exact marker format, a worked connection-string example, and distinct names-only vs never-inline rows for secret files.
- Tool-agnostic discipline is enforced at both layers and stated at the right moments: the emitted doc never names an AI product, and the /optimus: closing tip is explicitly "spoken to the user; never written into the document".
- Strong anti-hallucination posture throughout: "Never manufacture one" for focus, "Trust git state over chat memory", and omit-rather-than-guess defaults for Goal/Next steps.
- Right-sized structure: 131 lines, one-level references (shared multi-repo detection and the closing-tip convention are correctly outsourced), and the Enhance/Overwrite/Continue re-run routing is a clean BP16 conditional with test-enforced option labels.

---

## 4. code-review — 5/10

Files: `skills/code-review/SKILL.md` (362 lines) plus the skill's `agents/`, `references/`, `templates/`, `README.md`, and any shared references named in findings.

**Improvement need:** assessor 4 → verified **5** / 10. Rebuild recommended: no.

**Description assessment (454 chars):** 454 chars, third person, front-loaded ("Reviews local changes, PRs/MRs, or branch diffs...") so it scans well in a truncating slash menu. It states what + when + key capabilities, accurately matches actual behavior (5-7 agents, conditional test-guardian/contracts-reviewer, high-signal filter), and includes a negative trigger routing to the sibling `/optimus:code-review-deep`. Well tuned for this plugin's human-facing description audience; no change needed.

**Assessor score rationale:** The skill's core routing, validation loop, and progressive disclosure are strong and production-hardened, and the description/README need nothing. What it needs are a handful of targeted, localized fixes — the most load-bearing being the agent-prompt data flow (agents told to review only changed sections without being given the diff), which is partially compensated by the Step 6 pre-existing check but still degrades the fan-out's signal. No structural rework is warranted: every finding is a one-to-three-sentence edit.

**Verifier adjusted rationale:** Six of seven findings survive (5 confirmed, 1 adjusted on remedy, 1 refuted as taste), and verification added a second high-severity gap the assessor missed: explicit PR mode reviews the local working tree without ever ensuring it matches the PR head, compounding the confirmed agents-never-get-the-diff gap. Together these two defects sit in the skill's central data flow — what code the fan-out and the validation pass actually look at — which pushes the need past 'minor polish' (4) into 'moderate, several targeted fixes' (5). No structural rework is warranted: the routing table, validation pipeline, progressive disclosure, and description remain well-tuned, and every surviving fix is a localized one-to-three-sentence edit (diff delivery in Step 5, a prompt-assembly rule, a test-guardian carve-out, a PR-head checkout guard, stale step numbers, a base-detection fallback, one redundancy trim, one harness-mode sentence rescope).

### Findings to implement

#### F1. [high/under-specification] skills/code-review/SKILL.md — Step 5: Parallel Multi-Agent Review, ~line 173 (with skills/code-review/agents/*.md 'Review ONLY the diff/changed sections')

- **Quote:** "Each agent receives the list of changed file paths (from Step 3 in normal/interactive mode, or from `scope_files.current` in harness mode…"
- **Problem:** Every agent prompt orders 'Review ONLY the diff/changed sections of the provided files', but the assembly spec passes only file paths and never says to include the diff — and bug-detector is explicitly barred from any Bash beyond two git-log commands, so agents have no sanctioned way to learn what changed (no PR number, no base ref in their prompts).
- **Fix:** In Step 5, instruct including each file's diff hunks (or at minimum changed line ranges) in every agent prompt after the file list; alternatively add `git diff <base>...` to the agents' permitted commands and pass the base ref/PR number.
- **Best practice:** BP21, BP2
- **Verifier:** CONFIRMED — Quote verbatim at SKILL.md:173. All reviewer prompts order 'Review ONLY the diff/changed sections of the provided files' yet the assembly spec passes only file paths; the context blocks are injected 'before the file list line', confirming the designed prompt shape has no diff; bug-detector.md:31 bars Bash beyond two git-log commands and security/guideline/contracts/code-simplifier list no Bash tool at all, and neither the base ref nor PR number is passed. No compensating rule exists anywhere (checked SKILL.md, agent-architecture.md, harness-mode.md). Load-bearing BP21/BP2 gap in the fan-out's core data flow; proposed change breaks no validate.sh invariant.

#### F2. [medium/ambiguity] skills/code-review/agents/bug-detector.md line 14 (same line in all six agent prompt files); SKILL.md Step 5 ~line 175

- **Quote:** "Apply shared constraints from `shared-constraints.md`."
- **Problem:** SKILL.md never defines how agent prompts are assembled — passed verbatim, the subagent (whose cwd is the user's project) cannot resolve bare `shared-constraints.md` or `$CLAUDE_PLUGIN_ROOT/agents/...` references, the 'before the file list line' injection point presumes a prompt layout never specified, and guideline-reviewer's orchestrator-facing 'Construct this prompt dynamically' section ships inside an agent-facing prompt.
- **Fix:** Add a short prompt-assembly rule to Step 5: strip frontmatter, inline (or rewrite to absolute plugin paths) `shared-constraints.md` and referenced role files, resolve the Dynamic Prompt Construction section, and end each prompt with the file list line.
- **Best practice:** BP21, BP8
- **Verifier:** CONFIRMED — Line appears verbatim in all six agent prompt files. No prompt-assembly rule exists in SKILL.md Step 5, references/agent-architecture.md ('each skill's SKILL.md reads these files and launches them explicitly via the Agent tool' — nothing more), or .claude/docs/skill-writing-guidelines.md. A subagent whose cwd is the user's project cannot resolve bare `shared-constraints.md`, and `$CLAUDE_PLUGIN_ROOT` is not substituted in Agent-tool prompt text; guideline-reviewer.md:16-21 ('Construct this prompt dynamically') is orchestrator-facing text inside an agent-facing file, only partially covered by SKILL.md:197. Real ambiguity that yields run-to-run divergence in whether agents ever see the quality bar.

#### F3. [medium/ambiguity] skills/code-review/agents/test-guardian.md line 12

- **Quote:** "Read `$CLAUDE_PLUGIN_ROOT/agents/test-guardian.md` for your approach."
- **Problem:** The inherited plugin-level role file instructs 'Run the project's test command' and run coverage tooling, which is unscoped for a read-only review fan-out and directly contradicts harness mode's design goal of keeping test output out of subagent context — unlike code-simplifier's wrapper, which explicitly carves out inapplicable parts of its inherited role file.
- **Fix:** Add a carve-out sentence mirroring code-simplifier's: apply only the role file's gap-detection, anti-pattern, and test-quality rules; do not run the test suite or coverage tools in this review context (the skill/orchestrator owns test execution).
- **Best practice:** BP13, BP25
- **Verifier:** CONFIRMED — Quote verbatim at skills/code-review/agents/test-guardian.md:12. The inherited role file's items 3/5 and Process steps 5-6 instruct running the test suite and coverage tooling; the skill-level output format (Test Gap | Structural Barrier | Code Quality | Intent Mismatch) has no category for test failures or coverage deltas, so the instruction is unactionable in this context, and in harness mode it undercuts the orchestrator-owns-test-execution design. The sibling code-simplifier wrapper (line 12) proves the repo's carve-out pattern; adding the mirrored sentence breaks nothing.

#### F4. [low/ambiguity] skills/code-review/agents/context-blocks.md line 7 (also references/context-injection-blocks.md line 7 and its template placeholders)

- **Quote:** "When reviewing a PR/MR and a `pr-description` was captured in Step 1, inject the **PR/MR Context Block**"
- **Problem:** `pr-description` is captured in Step 3 per SKILL.md ('If a `pr-description` was captured in Step 3'), not Step 1 — a stale step number repeated in the shared template ('[PR/MR title from Step 1]'), and the injection conditions are restated in three files, which is how the drift arose.
- **Fix:** Replace 'Step 1' with 'Step 3' or step-neutral wording ('captured during scope determination') in both files, and trim the skill-level usage notes that duplicate the shared reference's own usage notes.
- **Best practice:** BP13, BP1
- **Verifier:** CONFIRMED — Verbatim at skills/code-review/agents/context-blocks.md:7; 'Step 1' also at references/context-injection-blocks.md:7 and in the template placeholders (lines 13, 15). SKILL.md captures pr-description in Step 3 and its own injection section says 'captured in Step 3' — genuine drift, and only code-review consumes the PR/MR block (refactor uses only the Iteration block), so no other skill's numbering justifies 'Step 1'. The usage-note duplication across three files is not enforced by validate.sh or expected-outputs.yaml; step-neutral wording is the right fix for the shared file.

#### F5. [low/missing-guidance] skills/code-review/SKILL.md — Step 3, Local changes flow, ~line 74

- **Quote:** "If no open PR/MR found or CLI unavailable → detect the default branch using `$CLAUDE_PLUGIN_ROOT/skills/pr/references/default-branch-detection.md`"
- **Problem:** The referenced algorithm's step 4 explicitly delegates failure handling to 'the consuming skill' (e.g., repo with no `origin` remote), but code-review defines no policy, so with a clean tree and no remote the skill must improvise; the subsequent `git log origin/<base-branch>..HEAD` would also fail.
- **Fix:** Add one fallback bullet: if default-branch detection fails, ask the user for a base ref (or report there is nothing to review) instead of proceeding.
- **Best practice:** BP23, BP16
- **Verifier:** CONFIRMED — Quote verbatim at SKILL.md:74. default-branch-detection.md step 4 explicitly delegates the all-failed case to 'the consuming skill' (stop, ask the user, etc.), and code-review defines no policy; the subsequent `git log --oneline origin/<base-branch>..HEAD` (line 75) fails with no origin remote, and the 'If nothing at all' fallthrough addresses no-changes, not failed detection. One fallback bullet is proportionate and breaks nothing.

#### F6. [low/redundancy] skills/code-review/agents/bug-detector.md — Output Format, line 69 (same pattern in security-reviewer.md)

- **Quote:** "(for Intent Mismatch findings, rename this field to `Current:`)"
- **Problem:** The Code:/Fix: → Current:/Suggested: renaming rule is stated three times within a single agent's assembled context — the PR/MR addendum paragraph, the per-field Output Format parentheticals, and shared-constraints.md 'Field names for Intent Mismatch findings' — and it is not test-enforced.
- **Fix:** State the rule once per agent context: keep the shared-constraints canonical rule plus the addendum pointer, and drop the per-field parentheticals from the Output Format sections.
- **Best practice:** BP1, BP13
- **Verifier:** ADJUSTED — The triple statement (addendum sentence, per-field parentheticals, shared-constraints canonical rule) is real in bug-detector and security-reviewer, and is NOT enforced by validate.sh or expected-outputs.yaml, so it is fair game — but the proposed trim removes the wrong copy: the Output Format parentheticals sit inside 'report in this exact format', the section agents follow most literally, and deleting them is the likeliest way to reintroduce Code:/Fix: drift in the aggregator contract.
  - **Revised severity:** low
  - **Revised fix (implement this one):** Keep the canonical shared-constraints.md rule plus the per-field parentheticals in each Output Format section, and instead drop the duplicate 'Rename the `Code:`/`Fix:` fields…' sentence from the PR/MR addendum paragraphs (which already point to shared-constraints.md).

#### F7. [high/missing-guidance] E:/workspace/claude-code/optimus-claude/skills/code-review/SKILL.md — Step 3 "PR mode (explicit request)", ~lines 89-101
*Found by verifier (adversarial pass) — treat as confirmed*

- **Quote:** "Use `gh pr diff <N>` to get the actual diff"
- **Problem:** Explicit PR mode never checks out (or verifies) the PR head, yet Step 5 agents receive local file paths and Step 6 validation reads ±30 lines from the local working tree — so reviewing a teammate's PR from another branch (a README-promised use case) silently reviews the wrong file content.
- **Fix:** After fetching PR metadata, compare local HEAD to the PR head (add `headRefOid` to the `gh pr view --json` fields) and offer `gh pr checkout <N>` when they differ — or explicitly instruct agents and Step 6 to work from the fetched diff text instead of the local tree.
- **Best practice:** BP23, BP21

#### F8. [medium/ambiguity] E:/workspace/claude-code/optimus-claude/references/harness-mode.md — section "7. Do NOT run tests", ~line 99
*Found by verifier (adversarial pass) — treat as confirmed*

- **Quote:** "Skip any verification or validation step the base skill's normal (interactive) flow would perform"
- **Problem:** Read literally this contradicts the same file's step 4 ('Apply the same validation protocol as the skill's normal validation step') and SKILL.md Step 2's 'Proceed through Steps 3, 4, 5, 6, and 7', inviting a harness iteration to skip Step 6 finding validation and mechanically auto-apply unvalidated findings.
- **Fix:** Rescope the sentence to execution-based checks only, e.g. 'Skip any verification step that would run tests, linters, builds, or coverage — the finding-validation step (step 4 above) still applies.'
- **Best practice:** BP13, BP21

### Refuted findings — do NOT implement

- [low/missing-guidance] skills/code-review/SKILL.md — Step 8: Offer Actions, ~line 334 — "**Fix issues** — "Apply suggested fixes directly, then run tests to verify""
  - **Refuted because:** Taste-level under BP1/BP2. Step 4 already loads `.claude/CLAUDE.md` — the repo-conventional home of the test command, a convention the skill's own closing tip states explicitly ('Requires a test command in `.claude/CLAUDE.md`') — so the source is inferable, not guessed. The quoted line is an AskUserQuestion option label in an interactive flow where the user is present and the Important section guarantees 'all changes remain as local modifications for the user to review'; prescribing a revert-on-failure policy adds hypothetical branching where high model freedom is appropriate and safe.

### Already well-tuned (preserve; do not churn while fixing the above)

- Step 3's PR auto-route decision table is exemplary conditional-workflow design: explicit git commands with exact success criteria (`git rev-list ... exits 0 with no output`), one route per state, and prescribed one-line user notices (BP16, BP21).
- Progressive disclosure is disciplined: a 362-line body delegates platform detection, doc loading, verification discipline, harness protocol, and handoff wording to shared references, staying within the repo's two-level depth budget (BP6-BP8).
- The Step 6 validation pipeline is a genuine feedback loop — five independent checks, change-intent awareness with concrete git commands and thresholds, and a 'code over claims' rule making the PR description a soft signal that can never hard-suppress a finding (BP11).
- Low freedom is applied exactly where operations are fragile and explained (the mktemp-in-cwd rule with the Windows /tmp + gh.exe rationale; the glab api form-post to dodge shell metacharacters) (BP2, BP19).
- Description and README are accurate and closely synced with SKILL.md behavior — no material D9 drift found; the README's comparison tables against the official plugin and sibling skills are a model for the collection.
- The Intent-Mismatch subsystem composes cleanly: per-agent lanes, a +5 budget registered canonically in shared-agent-constraints so it can't silently collide with the 15-cap, and the 'fix the code, never the PR description' guardrail.

---

## 5. jira — 5/10

Files: `skills/jira/SKILL.md` (253 lines) plus the skill's `agents/`, `references/`, `templates/`, `README.md`, and any shared references named in findings.

**Improvement need:** assessor 5 → verified **5** / 10. Rebuild recommended: no.

**Description assessment (710 chars):** Front-loaded and accurate: leading words ("Fetches and optimizes context from a JIRA issue...") scan well in a truncating menu, it is third person, and every clause maps to real behavior including the refresh semantics, Complex-scope ticket spawning, and explicit use-before triggers (/optimus:tdd, /optimus:brainstorm, /optimus:branch). At 710 chars it is on the long side for the human-menu audience this repo optimizes for, but the tail content is load-bearing at invocation time, so no change is needed.

**Assessor score rationale:** The skill is architecturally strong — safety gating, refresh idempotency, and handoff conventions are all carefully engineered — but it needs several targeted fixes, two of which affect advertised behavior: the wrong sooperset table cell silently disables the headline JIRA-enrichment feature for one of the two supported servers, and the detected-but-unsupported generic-server path forces guessing on both tool mapping and write permission. The remaining items (template drift on Labels, ToC omission of the safety section, three small clarity gaps) are quick edits. That lands at the low end of moderate (5): several targeted fixes, no structural rework.

**Verifier adjusted rationale:** All seven findings survive adversarial verification — six confirmed, one adjusted (the high sooperset add-comment finding is verified against the server's own tool docs but its fix must be broadened to the whole sooperset column and reworded to preserve the named-tool safety whitelist). I additionally found the same class of factual error on link creation: jira-implementation-tickets.md and the permitted-write table falsely assert sooperset lacks `jira_create_issue_link`, silently skipping parent-child linking for that server (medium). Nothing was refuted: none of the flagged duplication is enforced by validate.sh or expected-outputs.yaml, and every proposed change respects frontmatter rules, $CLAUDE_PLUGIN_ROOT paths, and the Next Step convention. The picture matches the assessor's: architecturally strong (safety whitelist, refresh idempotency, verbatim handoff conformance — which I spot-verified against references/skill-handoff.md), but one supported server is silently locked out of the headline enrichment and ticket-spawning features by wrong table cells, the generic-server path is unmapped, and there are several small drift/clarity edits. That is squarely 'moderate, several targeted fixes' with no structural rework — adjusted score stays 5.

### Findings to implement

#### F1. [high/other] skills/jira/references/jira-context-extraction.md § Tool Name Resolution, line 38

- **Quote:** "| Add comment | `addCommentToJiraIssue` | — | **Write** |"
- **Problem:** The table (and the mirrored MCP Safety permitted-writes row "addCommentToJiraIssue / —") wrongly claims sooperset has no add-comment tool — the server exposes `jira_add_comment` — so SKILL.md Step 5 hides the "Update JIRA and local context" option and silently disables the headline enrichment feature for all community-server users.
- **Fix:** Add `jira_add_comment` to the sooperset column in both the Tool Name Resolution and MCP Safety permitted-write tables, and make Step 5's gate a runtime ToolSearch probe for an add-comment tool (consistent with the table's own "never hard-code assumptions" rule).
- **Best practice:** BP21, BP13
- **Verifier:** ADJUSTED — Problem verified as real and high: sooperset/mcp-atlassian's tools reference confirms `jira_add_comment` exists, so the '—' cell is factually wrong; SKILL.md Step 5 gates the 'Update JIRA and local context' option on this table, and the MCP Safety permitted-write whitelist ('addCommentToJiraIssue / —') independently forbids the call — together they silently disable the enrichment-comment feature AND the only entry path to Complex-scope ticket creation for sooperset users. The proposed change is directionally right but incomplete and slightly unsafe: the sooperset column has more wrong '—' cells (jira_create_issue_link, jira_get_transitions, jira_get_all_projects, jira_add_worklog), and a bare 'runtime ToolSearch probe for an add-comment tool' would erode the deliberate named-tool whitelist (it could match Confluence or arbitrary write tools on generic servers).
  - **Revised severity:** high
  - **Revised fix (implement this one):** Fix the sooperset column in both the Tool Name Resolution table and the MCP Safety permitted-write table (at minimum add `jira_add_comment`; audit the other '—' cells against the server's tool list). Reword Step 5's gate as: the permitted add-comment tool named in the MCP Safety table for the detected server is present in the runtime tool list (ToolSearch) — keeping the whitelist normative rather than probing for any comment-like tool.

#### F2. [medium/missing-guidance] skills/jira/references/jira-mcp-detection.md § Detection Procedure step 2, line 39

- **Quote:** "| Generic | `mcp__jira__` | Varies by implementation |"
- **Problem:** Detection explicitly supports generic JIRA servers (any key containing `jira`/`atlassian`), but every downstream table — Tool Name Resolution, fetch tool hints, and the MCP Safety permitted-writes table — has only Rovo/sooperset columns, forcing a model with a generic server to guess tool mappings and whether any write is permitted.
- **Fix:** Add one short paragraph to jira-context-extraction.md: for generic servers, map operations by tool-name pattern via ToolSearch, and treat all writes as unavailable unless a discovered tool unambiguously matches a permitted purpose (comment/create/link).
- **Best practice:** BP16, BP21, BP23
- **Verifier:** CONFIRMED — Quote verbatim at jira-mcp-detection.md line 39. Detection step 1 explicitly matches `jira`-named keys and 'any key containing jira or atlassian', and step 3 returns success, but every downstream table (Tool Name Resolution, fetch tool hints, permitted-writes) has only Rovo/sooperset columns — a generic-server run must guess read-tool mappings and gets no ruling on writes. The generic 'use ToolSearch, never hard-code' preamble covers discovery but not the safety whitelist. The proposed one-paragraph fail-closed rule is sound, cheap, and consistent with the skill's safety posture; not test-enforced anywhere.

#### F3. [medium/redundancy] skills/jira/SKILL.md § Step 4: Distill into Structured Task, lines 72–96

- **Quote:** "Assemble the fetched data into the **Structured Output Format** from the extraction reference:"
- **Problem:** The inline copy of the template that follows has drifted from the reference's canonical version — it omits the `Labels:` Context line that the reference emits and that jira-refresh.md's Update procedure expects to preserve verbatim — so first-run files can lack a field the refresh machinery depends on.
- **Fix:** Delete the inline template (the reference is already loaded from Step 3) or keep only the top-level section names; if kept in full, sync it exactly with the reference, including Labels.
- **Best practice:** BP17, BP13, BP7
- **Verifier:** CONFIRMED — Quote verbatim at SKILL.md line 72. The inline copy genuinely drifted: it omits the `- Labels:` Context line that the reference's canonical template (jira-context-extraction.md line 174) emits, that the Fetch Procedure extracts ('Labels (if present)'), that README's field-by-field table promises ('Included in context output'), and that jira-refresh.md's Update procedure enumerates among preserve-verbatim lines. One nuance: the assessor's 'field the refresh machinery depends on' overstates — refresh preserves Labels only if present, nothing crashes — but the drift, the README contradiction, and the duplicated-template drift vector are real. Deleting the inline copy is safe: Step 3 already reads the full reference, and no test enforces this duplication (checked validate.sh and expected-outputs.yaml). Medium stands.

#### F4. [medium/structure] skills/jira/references/jira-context-extraction.md § Contents, lines 7–14

- **Quote:** "1. [Tool Name Resolution](#tool-name-resolution) — map operations to server-specific tool names"
- **Problem:** The Contents list omits the MCP Safety section that sits between Tool Name Resolution and Search Procedures — the very section SKILL.md designates "the single source of truth for which tools the skill is allowed to call" — so a ToC-guided partial read misses the safety rules entirely.
- **Fix:** Add "MCP Safety — read-only enforcement and the permitted-write table" as an entry in the Contents list.
- **Best practice:** BP9, BP22
- **Verifier:** CONFIRMED — Verified: the Contents list (lines 8–14) enumerates six sections and skips MCP Safety, which sits between Tool Name Resolution and Search Procedures and is designated by SKILL.md as 'the single source of truth' for permitted tools. The partial-read risk is concrete: SKILL.md Step 2 instructs reading only the 'Search: Assigned Issues' section, exactly the ToC-guided navigation that would skip the hard no-writes rule. Medium is right for a safety-adjacent structural gap with a one-line fix (BP9/BP22).

#### F5. [low/under-specification] skills/jira/SKILL.md § Step 6: Recommend Next Step, line 161

- **Quote:** "First, handle tech debt and refactoring tickets separately — they have a fixed route:"
- **Problem:** No criterion is given for classifying a ticket as tech debt/refactoring (issue type? labels? goal wording?), even though this route bypasses the whole scope-based branching; the README implies issue type drives it, but SKILL.md never says so.
- **Fix:** Add one clause, e.g. "identified by issue type, labels like tech-debt/refactor, or a goal that restructures code without changing behavior".
- **Best practice:** BP21, BP16
- **Verifier:** CONFIRMED — Quote verbatim at SKILL.md line 161. Borderline against BP2 model latitude — Claude can usually classify from Type/Labels/Goal — but the README explicitly states issue type drives this route ('TDD for stories/bugs, refactor for tech debt') while SKILL.md gives no signal, so there is mild doc inconsistency plus a route that bypasses the whole scope-based branch on a fuzzy call. The one-clause change is proportionate; low severity is correct.

#### F6. [low/ambiguity] skills/jira/references/jira-context-extraction.md § Search: By Project, line 79

- **Quote:** "Validate it matches `[A-Z][A-Z0-9]+` (1-10 uppercase alphanumeric characters, starting with a letter)"
- **Problem:** The prose gloss contradicts its own regex: the pattern requires at least 2 characters and imposes no 10-character cap, while the parenthetical says 1-10.
- **Fix:** Align them — e.g. use `^[A-Z][A-Z0-9]{1,9}$` and say "2-10 uppercase alphanumeric characters, starting with a letter".
- **Best practice:** BP13, BP21
- **Verifier:** CONFIRMED — Quote verbatim at jira-context-extraction.md line 79. The contradiction is real: the regex requires ≥2 characters and has no upper bound while the gloss says 1-10; the regex is also unanchored. The proposed `^[A-Z][A-Z0-9]{1,9}$` with '2-10' matches JIRA's actual project-key constraints and the skill's own issue-key regex in SKILL.md Step 2. Low severity is right.

#### F7. [low/under-specification] skills/jira/SKILL.md § Step 5 — If Update JIRA and local context, line 147

- **Quote:** "Report success or failure. No further confirmation needed for the comment — comments are append-only and non-destructive."
- **Problem:** This branch only routes to Step 6 inside the Complex-scope item 5, so for Simple/Medium scope there is no explicit "proceed to Step 6", unlike the sibling branches which both end with one — an asymmetry in an otherwise fully explicit routing scheme.
- **Fix:** Append "For non-Complex scope, proceed to Step 6." after item 4 (or restate item 5 as "If Complex ... otherwise proceed to Step 6").
- **Best practice:** BP16, BP10
- **Verifier:** CONFIRMED — Quote verbatim at SKILL.md line 147. The asymmetry is real: 'Then proceed to Step 6' appears only inside the Complex-only item 5, while both sibling branches ('Update local context only', 'Skip') end with an explicit 'Proceed to Step 6', and the refresh reference states exit routing exhaustively everywhere. Practical failure risk is near zero (sequential fall-through reaches Step 6), so this is correctly the weakest finding — low, one-line fix, no breakage.

#### F8. [medium/other] skills/jira/references/jira-implementation-tickets.md § Tool resolution (~line 79); also jira-context-extraction.md MCP Safety permitted-write table (line 59) and README.md Features bullet (line 17)
*Found by verifier (adversarial pass) — treat as confirmed*

- **Quote:** "the sooperset server does not expose link creation"
- **Problem:** This claim is factually false — sooperset/mcp-atlassian exposes `jira_create_issue_link` (verified against its tools reference) — and it is repeated normatively in the permitted-write table (`createIssueLink` / —) and README ('links them to the parent (Rovo)'), so even after the add-comment cell is fixed the safety whitelist still forbids linking spawned tickets to the parent for sooperset users, silently degrading the advertised parent↔child linking.
- **Fix:** Add `jira_create_issue_link` to the sooperset column in the Tool Name Resolution and permitted-write tables, delete the 'does not expose link creation' parenthetical (keep the create-without-link fallback for servers genuinely lacking a link tool), and drop the '(Rovo)' qualifiers from README and the Linking section's 'Rovo only' note.
- **Best practice:** BP21

### Already well-tuned (preserve; do not churn while fixing the above)

- MCP safety architecture is exemplary: a single-source permitted-write table, a name-prefix hard rule (never call add*/create*/edit*/update*/transition*/delete* during extraction), and an explicit gate for every write (BP20/BP22).
- The refresh reconciliation model assigns each ### section exactly one owning procedure and cross-references the description-refresh-date bump rules consistently across all three writer procedures — low freedom correctly applied to genuinely fragile multi-run file state (BP2).
- Error handling is concrete: an error-to-message table with exact user-facing text per HTTP status, including a 429 retry-once rule (BP23).
- Step 6 handoff follows references/skill-handoff.md's tdd carve-out precisely — review-only plan mode, verbatim tip wording, and self-contained prompts with <ISSUE-KEY> substitution.
- Implementation-ticket creation is a textbook plan-validate-execute flow: proposed table before any write, default Skip, dependency-ordered creation, and well-reasoned failure/duplicate-prevention rules (BP20/BP11).
- All five references have ToCs, the two-level reference depth is respected, and the 345-line README shows no material drift from SKILL.md behavior (D9 clean).

---

## 6. init — 5/10

Files: `skills/init/SKILL.md` (349 lines) plus the skill's `agents/`, `references/`, `templates/`, `README.md`, and any shared references named in findings.

**Improvement need:** assessor 4 → verified **5** / 10. Rebuild recommended: no.

**Description assessment (578 chars):** 578 chars, third person, accurate against actual behavior (scaffolding, audit/sync, monorepo/multi-repo, re-run), with a strong leading clause and a real [What]+[When] structure. Slightly long for slash-menu scanning and the key disambiguator "Replaces /init" sits mid-string, but there are no material inaccuracies — tuning optional, not finding-worthy.

**Assessor score rationale:** The skill is the plugin's foundation and is fundamentally well-built: correct structure, real feedback loops, careful preservation semantics, accurate description and README. The needed work is targeted, not structural: two medium gaps (created docs never reconciled into CLAUDE.md's Documentation section with only a one-directional Step 7 check; no user guidance that a scaffolded subdirectory becomes the new session root) plus six low-severity consistency/redundancy items (auditor launch omits shared constraints, an unexecutable Detection Summary note, a Dart entry missing from the settings.json template, detector/consumer criteria split, and two drift-prone duplications). That lands at the top of the minor-polish band.

**Verifier adjusted rationale:** All eight findings survive adversarial verification in substance — six CONFIRMED with quotes verbatim and mechanics checked against validate.sh/expected-outputs.yaml (neither redundancy is test-enforced), two ADJUSTED on the proposed change only (finding 7's fix should preserve point-of-action scope statements for the destructive overwrite rule; finding 8's fix must also remove the stale line-72 cross-pointer). Verification additionally surfaced a high-severity gap the assessor missed: the monorepo testing.md wiring is self-contradictory (SKILL.md defers placement to a reference that only creates root .claude/docs/testing.md yet demands subproject CLAUDE.md files reference their own docs/testing.md, and Step 2 says testing.md must not stay at root in monorepos) — on the advertised monorepo path this either trips Step 7's exists-gate or forces improvised placement of a doc that unit-test/tdd depend on. A related medium: the anchor-position overwrite rule's '(hooks, coding-guidelines.md, templates)' scope contradicts the four later never-silently-overwrite rules for template-derived docs. Two confirmed mediums, a new high on a first-class mode, and a cluster of consistency fixes move this from top-of-minor-polish (4) into the moderate band (5). The architecture remains sound — targeted edits suffice; the assessor's rebuild=false stands.

### Findings to implement

#### F1. [medium/missing-guidance] skills/init/SKILL.md — Step 4: Create CLAUDE.md (Single project), ~line 149; Step 7 cross-reference checks ~line 295

- **Quote:** "list only non-guideline docs that were actually created (testing.md, styling.md, architecture.md)"
- **Problem:** At Step 4 execution time none of these docs exist yet (Steps 5b/6 create them later), Step 6 never instructs updating the CLAUDE.md Documentation section afterward, and Step 7 only checks listed→exists — so styling.md/architecture.md can be created but never referenced, and all checks still pass.
- **Fix:** Add to Step 6: after creating styling.md/architecture.md, add them to the CLAUDE.md (and subproject CLAUDE.md) Documentation section. Add the reverse cross-check to Step 7: every created doc is listed.
- **Best practice:** BP11, BP21
- **Verifier:** CONFIRMED — Quote verbatim at SKILL.md line 149. Temporal gap is real: at Step 4 none of these docs exist yet; testing.md is reconciled later by test-infra-provisioning.md ('add test commands and a testing.md reference') but Step 6 never instructs updating the Documentation section for styling.md/architecture.md, and Step 7 line 295 only checks listed→exists, so orphaned docs pass all gates. The single-project template's own comment ('Only list docs that were actually created') reinforces the empty-list literal reading. Change is sound and breaks no validate.sh wiring. Medium is right — the Documentation section is the progressive-disclosure entry point.

#### F2. [medium/missing-guidance] skills/init/SKILL.md — Step 1: Empty-directory detection, ~line 30 (and new-project-scaffolding.md Section 3)

- **Quote:** "After scaffolding completes, discard all prior detection state and restart Step 1 from "Project detection" below"
- **Problem:** Scaffolding creates and cds into a `<name>/` subdirectory, so the generated `.claude/settings.json` hooks and CLAUDE.md only load for sessions started inside that subdirectory — in the current session hooks never fire, and nothing tells the user to reopen Claude Code there.
- **Fix:** When scaffolding created a subdirectory, add a Step 7 report line: the project root is now `<name>/` — start future Claude Code sessions from that directory for hooks and CLAUDE.md to take effect.
- **Best practice:** BP23, BP21
- **Verifier:** CONFIRMED — Quote verbatim at SKILL.md line 30. new-project-scaffolding.md Section 3 confirms every scaffold command creates a <name>/ subdirectory and instructs 'cd <name>'; the Claude Code session root stays the parent, so the generated .claude/settings.json hooks and CLAUDE.md never load in the current session or in future sessions started from the parent. Neither the scaffolding reference's closing print nor the Step 7 summary format mentions this. A one-line Step 7 report addition is minimal and safe. Medium justified — affects every scaffolded run and silently defeats the artifacts init just installed.

#### F3. [low/under-specification] skills/init/SKILL.md — Step 1b, ~line 94; agents/documentation-auditor.md line 12

- **Quote:** "Provide the Detection Results from Step 1 as context at the start of the agent prompt"
- **Problem:** Unlike the Step 1 launch ("prepended with the shared constraints"), Step 1b never instructs prepending shared-constraints.md, so the auditor subagent sees "Apply shared constraints from shared-constraints.md" — a bare relative path it cannot resolve from the user's project — and runs without the independent-validation/anti-speculation constraint.
- **Fix:** Mirror Step 1's wording in Step 1b (prepend shared-constraints.md content before Detection Results), or inline the two constraints directly into documentation-auditor.md.
- **Best practice:** BP21, BP13
- **Verifier:** CONFIRMED — Verbatim at SKILL.md line 94. Step 1's launch explicitly says 'prepended with the shared constraints' (line 45); Step 1b's launch does not, and documentation-auditor.md line 12 references bare 'shared-constraints.md' — unresolvable from the subagent's context. Low is correct because the read-only constraint is independently restated in the auditor file's closing line ('Do NOT modify any files'), so only the anti-speculation/independent-validation framing is lost. Proposed change mirrors an existing pattern and is safe.

#### F4. [low/ambiguity] skills/init/SKILL.md — Step 4: Multi-repo workspace, ~line 171

- **Quote:** "Note in the Detection Summary that this file is local-only and not version-controlled."
- **Problem:** The Detection Summary was printed and user-confirmed back in Step 1, so at Step 4 the instruction is unexecutable as written — Claude either silently drops the local-only note or improvises a re-print, and the note may never reach the user.
- **Fix:** Move the requirement into the Step 1 Detection Summary contents (multi-repo case), or reword to "inform the user when creating the file / in the Step 7 summary".
- **Best practice:** BP22, BP21
- **Verifier:** CONFIRMED — Verbatim at SKILL.md line 171. The Detection Summary is defined, printed, and user-confirmed in Step 1 (lines 75-80); a step-by-step executor reaches this instruction only in Step 4, after that summary is closed. A full-context model could bake the note in early, but the placement forces read-ahead or improvisation — a real BP22 problem, correctly rated low. Moving it into the Step 1 checkpoint contents or the Step 7 summary is sound.

#### F5. [low/other] skills/init/references/formatter-setup.md — Installation Steps item 3, ~line 34 (defect in templates/settings.json)

- **Quote:** "Keep only entries for hooks actually installed."
- **Problem:** This filter-down instruction assumes the settings.json template has an entry per supported stack, but the template omits format-dart.sh even though Dart/Flutter is an always-install stack — a literal reader installs the Dart hook file without registering it, caught only if Step 7's hooks↔settings cross-check is executed carefully.
- **Fix:** Add the format-dart.sh bash entry to templates/settings.json so the "keep only" semantics hold for every supported stack.
- **Best practice:** BP19, BP14
- **Verifier:** CONFIRMED — Verbatim at formatter-setup.md line 34. templates/settings.json (lines 7-13) has entries for 7 of the 8 supported stacks — format-dart.sh is missing despite Dart/Flutter being an 'Always' install in the formatter table and the hook template existing. Mitigations are real (the same sentence names Dart/Flutter among bash hooks, and Step 7's settings↔hooks check is bidirectional — 'and vice versa'), which the assessor acknowledged in rating it low. The 'keep only' filter-down semantics genuinely break for Dart; adding the entry is safe and correct.

#### F6. [low/ambiguity] skills/init/SKILL.md — Step 5b, ~line 202; agents/project-analyzer.md task 8

- **Quote:** "(test framework in dependencies, `test`/`test:*` script in manifest, or `tests/`/`test/`/`spec/`/`__tests__/`/`integration_test/` directory exists)"
- **Problem:** The precise detection criteria live where the flag is consumed (Step 5b), while the agent that actually performs the detection gets only the vague "test directory is present" version — e.g., a project with only an e2e/ directory can be flagged yes by the agent yet fail Step 5b's stricter list, forcing a guess about which definition governs.
- **Fix:** Move the precise script/directory list into project-analyzer.md task 8 (the detector), and have Step 5b simply branch on the Step 1 checkpoint flag.
- **Best practice:** BP13, BP21
- **Verifier:** CONFIRMED — Verbatim at SKILL.md line 202. project-analyzer.md task 8 and the Step 1 checkpoint (line 71) both carry only the vague 'test directory is present' version, so the detector and the consumer disagree — the e2e/ example is a genuine governs-which conflict (BP13). Moving the precise list into the detector and branching Step 5b on the checkpoint flag matches the pattern already used for skill-authoring detection and breaks no validate.sh check.

#### F7. [low/redundancy] skills/init/SKILL.md — Step 2 Audit-aware rule, ~line 117 (also lines 18, 70, 121, 189, 219)

- **Quote:** "hooks and `coding-guidelines.md` are generated content (verbatim templates or fallback hooks) — always overwrite regardless of audit status"
- **Problem:** The always-overwrite rule for hooks/coding-guidelines.md is stated in full roughly six times across the body and is not test-enforced — token load plus six sites a future policy edit must keep in sync.
- **Fix:** Keep the canonical statement in "Before You Start" and reduce later occurrences to brief pointers (e.g., "always overwritten — see Before You Start").
- **Best practice:** BP1, BP13
- **Verifier:** ADJUSTED — The count is accurate — six statement sites (lines 18, 70, 117, 121, 189, 219) — and none are test-enforced (validate.sh's 'Overwrite' token belongs to the handoff skill). But this is point-of-action restatement of a destructive rule's scope, the same pattern the assessor praised as 'deliberate, defensible redundancy' for the preservation rule; and Step 5 (line 189) carries unique scope info ('both template-based and custom fallback hooks'). Blanket reduction to pointers is over-corrective.
  - **Revised severity:** low
  - **Revised fix (implement this one):** Condense only the two non-load-bearing restatements — line 70's inventory parenthetical and line 121's Step 2 sentence — to pointers at 'Before You Start'; keep the point-of-action statements at Steps 2 (exception), 5, and 6 which each carry distinct scope. Also fix line 18's loose '(hooks, coding-guidelines.md, templates)' scope wording while touching these sites (see missed finding).

#### F8. [low/redundancy] skills/init/SKILL.md — Step 6 install table, ~line 227 (duplicates agents/project-analyzer.md task 9)

- **Quote:** "a directory named `skills/`, `agents/`, `prompts/`, `commands/`, or `instructions/` exists (at the repo root or, in monorepos, at any subproject root), contains ≥2 subdirectories"
- **Problem:** The full multi-condition skill-authoring predicate is stated verbatim in both project-analyzer.md (the detector) and the Step 6 table (a consumer), plus paraphrased at the Step 1 checkpoint — a two-file drift risk that invites the main context to re-derive and contradict the flag the agent already reported.
- **Fix:** Make the Step 6 row read "Skill authoring detected in Step 1 (structural rule in project-analyzer.md)" and keep the predicate only in the agent file.
- **Best practice:** BP1, BP13
- **Verifier:** ADJUSTED — Duplication verified: the full multi-condition predicate appears near-verbatim in both project-analyzer.md task 9 and the SKILL.md Step 6 table (line 227), plus a paraphrase at the line 72 checkpoint; not test-enforced. The change is directionally right but incomplete: line 72 explicitly says the rule is '(also applied in the Step 6 install table)' — after making Step 6 consume the flag, that parenthetical becomes false and must be removed in the same edit or a new self-contradiction is introduced.
  - **Revised severity:** low
  - **Revised fix (implement this one):** Make the Step 6 skill-writing-guidelines row read 'Skill authoring detected in Step 1 (structural rule in project-analyzer.md)', keep the predicate only in the agent file, and drop the now-stale '(also applied in the Step 6 install table)' parenthetical from the Step 1 checkpoint (line 72).

#### F9. [high/under-specification] skills/init/SKILL.md — Step 6 Placement rules (~line 242) vs references/test-infra-provisioning.md 'Monorepo subprojects' (~line 45) and Step 2 relocate rule (~line 123)
*Found by verifier (adversarial pass) — treat as confirmed*

- **Quote:** "`testing.md` placement is handled by Step 5b's provisioning reference."
- **Problem:** The provisioning reference only ever creates root `.claude/docs/testing.md` yet requires each subproject CLAUDE.md to 'reference its own `docs/testing.md`' — files whose creation is instructed nowhere — while Step 2 says only the two guidelines files stay at root in monorepos, so on a monorepo run Step 7's listed→exists cross-check trips on dangling subproject testing.md references and the model must improvise placement.
- **Fix:** In test-infra-provisioning.md, add explicit monorepo semantics: create `<subproject>/docs/testing.md` per subproject with test infrastructure (root `.claude/docs/testing.md` only for root-as-project), and update SKILL.md's Step 6 placement pointer to state this.
- **Best practice:** BP21, BP16, BP13

#### F10. [medium/ambiguity] skills/init/SKILL.md — Before You Start, line 18
*Found by verifier (adversarial pass) — treat as confirmed*

- **Quote:** "Generated content (hooks, `coding-guidelines.md`, templates) is always overwritten silently — these are not user-authored files."
- **Problem:** The word 'templates' in the anchor-position destructive rule contradicts the rest of the skill: styling.md, architecture.md, testing.md, and skill-writing-guidelines.md are all template-derived but governed by never-silently-overwrite / review-and-propose semantics (lines 121, 236, 238 and the Step 5b reference), so the highest-authority statement of the overwrite scope is the one loose formulation.
- **Fix:** Change the parenthetical to the precise scope used everywhere else — '(hooks and `coding-guidelines.md`)' — and optionally add 'template-derived docs like testing.md and styling.md are NOT generated content; see Step 6 install semantics'.
- **Best practice:** BP13, BP22

### Already well-tuned (preserve; do not churn while fixing the above)

- Checkpointed workflow with explicit AskUserQuestion gates at every destructive or ambiguous decision point (detection confirm, audit handling, test-infra install, doc sync) — strong BP10/BP16/BP20 discipline.
- User-content preservation is treated as a safety constraint with a clear standard of proof ("only when source code directly contradicts") and restated at each point of action — deliberate, defensible redundancy.
- Progressive disclosure is genuinely good: 349-line body (under the 500 cap) delegating detection algorithms, formatter setup, scaffolding, and test provisioning to focused references; the long references carry ToCs (BP6/BP7/BP9).
- Step 7 is a real validate-fix-repeat gate: concrete file/content/cross-reference checks with "do not proceed to the summary until all checks pass" (BP11).
- Agent delegation keeps the main context clean, and the shared-constraints "your results will be independently validated" framing is an effective anti-speculation device.
- README.md is closely aligned with SKILL.md behavior (overwrite vs intelligent-diff semantics, step order, generated-file inventory) — no material D9 drift found.

---

## 7. tdd — 5/10

Files: `skills/tdd/SKILL.md` (406 lines) plus the skill's `agents/`, `references/`, `templates/`, `README.md`, and any shared references named in findings.

**Improvement need:** assessor 4 → verified **5** / 10. Rebuild recommended: no.

**Description assessment (302 chars):** At 302 chars it is concise, third person, and states what (Red-Green-Refactor cycling with behavior decomposition), prerequisites, and when to use — it scans well in a slash menu with strong leading words. Two minor gaps: it is silent about the skill's significant git lifecycle (creates a branch, auto-commits every cycle, pushes to origin), and it offers no disambiguation from the confusable sibling /optimus:unit-test (test-after) even though the body handles the refactor redirect at runtime.

**Assessor score rationale:** The core Red-Green-Refactor loop, gating, and handoff machinery are well-engineered and mostly well-calibrated, with strong feedback loops and clean progressive disclosure. The needed work is a handful of surgical one-to-three-sentence edits: two advertised behaviors that don't reliably materialize (the coverage delta whose baseline instruction is buried in the final step's template; the nonexistent resume path claimed twice), one common-path trap (import-error rule dead-ends the first cycle of any new module), plus smaller ambiguity/redundancy cleanups. Nothing structural — targeted refinement clearly suffices, putting it at the top of the minor-polish band.

**Verifier adjusted rationale:** All eight findings survived adversarial verification verbatim — none refuted, none mislabeled as bloat, and every proposed change was checked safe against validate.sh's wiring tokens (scenario contract, '## TDD Summary'/'### Behaviors Implemented'/'### Coverage' handoff headings) and the pr consumer, which treats '### Coverage' as optional so the omit-rule fix composes cleanly. That leaves four confirmed mediums (buried coverage baseline, import-error dead-end on new modules, unimplemented resume claim stated twice, milestone-boundary prompt conflict that can even skip the quality gate) plus four confirmed lows. Verification added three more real issues the assessor missed: an ungated final commit-and-push path whose summary hardcodes 'Tests passing: all ✓' against the skill's own verification protocol (medium), a SKILL-vs-reference contradiction on worktree-cleanup ordering (low), and a README feature bullet ('Submodule exclusion') with no instruction surface — falsifying the report's 'no material D9 drift' bullet (low). The core Red-Green-Refactor machinery, gates, and handoff remain genuinely well-engineered and every fix is a one-to-three-sentence surgical edit, but five medium-grade defects — two of them advertised behaviors that don't materialize and one a common-path dead-end — is more than 'minor polish': this sits at the low end of the moderate band, so the score moves from 4 to 5.

### Findings to implement

#### F1. [medium/structure] skills/tdd/SKILL.md — Step 9 'Present summary', ~line 374

- **Quote:** "run it before the first cycle and after the last cycle to measure the delta"
- **Problem:** The only instruction to capture the coverage baseline 'before the first cycle' is buried inside a bracketed note in the Step 9 output template, after all cycles are done — and coverage-detection.md's omit rule then suppresses the section whenever the Before run is missing, so the advertised coverage delta silently never fires unless Claude pre-plans from a template comment.
- **Fix:** Add an explicit 'detect the coverage command per coverage-detection.md and record the baseline percentage' instruction at the end of Step 1 (test-infrastructure verification) or Step 3, leaving Step 9 to run only the After measurement and compute the delta.
- **Best practice:** BP22, BP10
- **Verifier:** CONFIRMED — Quote verbatim at SKILL.md:374, inside a bracketed comment in the Step 9 output template. coverage-detection.md line 3 explicitly delegates 'when to run it' to the consuming skill, yet the skill's only statement of 'when' is this template note in the final step; the reference's omit rule (line 15) then suppresses the section whenever the Before run is missing, so the README-advertised delta silently vanishes on any model that didn't pre-plan from a template comment (BP22/BP3). The proposed change keeps the '### Coverage' heading in Step 9, so the validate.sh handoff token (line 835) is untouched.

#### F2. [medium/missing-guidance] skills/tdd/SKILL.md — Step 4 'Run the test suite', line 206

- **Quote:** "fails for the wrong reason (import error, missing dependency, syntax error), fix the test — not the source code"
- **Problem:** For the first behavior of any new module/function, the test's import of the not-yet-existing symbol IS the unimplemented behavior, so this rule (plus line 198 excluding import errors from valid Red) dead-ends the cycle: the test cannot be 'fixed' without touching source, and the Iron Law forbids writing source before a failing test.
- **Fix:** Add the standard TDD escape hatch: when the failure is caused by the symbol under test not existing yet, create a minimal stub (empty function/class) so the run fails on the assertion, and state the stub counts as scaffolding, not the Iron-Law-violating implementation.
- **Best practice:** BP21, BP23, BP16
- **Verifier:** CONFIRMED — Verbatim at SKILL.md:206; line 198 confirms import errors are excluded from valid Red. For the first behavior of any new module the test's import of the not-yet-existing symbol necessarily ImportErrors, and 'fix the test — not the source code' is unsatisfiable without touching source. The stub escape hatch is standard TDD and does not violate the Iron Law's letter (the failing test already exists), so the change is sound and needed on a common path.

#### F3. [medium/under-specification] skills/tdd/SKILL.md — Step 9 'Push', line 385 (also line 396)

- **Quote:** "re-running `/optimus:tdd` resumes from the existing worktree"
- **Problem:** No step implements resume: Step 3 says 'Always create a new branch from the current branch' and nothing detects an in-progress TDD branch/worktree, so re-running actually restarts with a fresh branch and fresh decomposition, contradicting both this claim and Step 9's 'suggest re-running /optimus:tdd to continue'.
- **Fix:** Either add a lightweight resume check to Step 3 (existing TDD branch/worktree matching the task → offer to continue on it, skipping branch creation) or reword both claims to honestly describe a restart (new branch from the pushed feature branch or from the original branch).
- **Best practice:** BP21, BP10
- **Verifier:** CONFIRMED — Verbatim at SKILL.md:385 (and 'suggest re-running /optimus:tdd to continue' at 396). Step 3 line 108 unconditionally creates a new branch from the current branch; worktree-setup.md's detection guard only skips worktree creation and tells the caller to 'proceed with the standard branch workflow' — no branch reuse, no behavior-list carryover. Re-run from the main workspace even branches off the original branch, which lacks the TDD commits. The resume claim is genuinely unimplemented; either proposed remedy is safe.

#### F4. [medium/ambiguity] skills/tdd/SKILL.md — Step 3 'Decompose into behaviors', lines 141-145

- **Quote:** "present the next milestone's behaviors for approval (return to the "Behaviors" confirmation above)"
- **Problem:** The milestone-continuation logic executes during the Step 7 loop but lives in Step 3, competes with Step 7's own 'Next step — Next behavior / Stop here' question at the milestone boundary with no rule for which prompt fires, and its pointer says 'above' while the Behaviors confirmation actually appears below it in the file.
- **Fix:** Move the milestone-boundary branch into Step 7 ('if the completed behavior ends the current milestone, ask the Milestone-complete question instead of the Next-step question') and fix the above/below pointer; also disambiguate the doubled [N] placeholder (milestone number vs behavior count).
- **Best practice:** BP16, BP10, BP22
- **Verifier:** CONFIRMED — Verbatim at SKILL.md:145; the 'Behaviors' confirmation is at line 158 — below, not above, so the pointer is factually backwards. The milestone-boundary prompt (Step 3, line 141) and Step 7's Next-step prompt (line 325) genuinely compete with no precedence rule, and they route 'Stop here' differently: Step 7 routes through Step 8's quality gate (line 331) while Step 3's option says only 'show summary' — so which prompt fires can even decide whether the quality gate runs, and Step 7's 'Next behavior #[N+1]' could bypass milestone approval. Doubled [N] (milestone number vs behavior count) also real. Change is sound and touches no validated tokens; medium severity holds despite the >10-behavior gating because of the gate-skip wrinkle.

#### F5. [low/ambiguity] skills/tdd/agents/code-simplifier.md — line 12

- **Quote:** "Read `$CLAUDE_PLUGIN_ROOT/agents/code-simplifier.md` for your approach and quality criteria."
- **Problem:** The plugin-level role file's operating procedure says 'Apply changes, verifying all functionality remains unchanged' and lists 'Direct simplifications — apply automatically', directly contradicting this wrapper's 'Do NOT modify any files' and the read-only shared constraints — a weaker subagent (frontmatter pins sonnet) may follow the role file and edit files during the quality gate.
- **Fix:** Scope the read in the wrapper: 'Read ... for quality criteria and focus areas only — ignore its apply-changes operating procedure; you are strictly read-only,' or point to a criteria-only section of the role file.
- **Best practice:** BP13, BP3
- **Verifier:** CONFIRMED — Verbatim at skills/tdd/agents/code-simplifier.md:12. The plugin-level role file's operating procedure says 'Apply changes, verifying all functionality remains unchanged' and 'Direct simplifications — apply automatically' (agents/code-simplifier.md:47-49), directly contradicting the wrapper's 'Do NOT modify any files' (line 42) and shared-agent-constraints' 'Read-only analysis'. Since quality-gate.md launches these as general-purpose Agent calls, the wrapper's Read/Glob/Grep frontmatter is not a guaranteed enforcement layer, so the prompt-level contradiction is live. The test-guardian pair has no such conflict (its role file is already advisory-only), so scoping the fix to code-simplifier is correct. validate.sh only checks frontmatter fields on the plugin-level files — the wording change is safe.

#### F6. [low/missing-guidance] skills/tdd/SKILL.md — Step 5 'Bug-fix regression gate', line 245

- **Quote:** "**Revert only the fix**: `git stash push <implementation-files>`"
- **Problem:** When the fix added a new untracked file, `git stash push <pathspec>` without `-u` fails or stashes nothing, so the fix is still in place at gate step 3, the test passes, and the skill wrongly diagnoses 'the test is not actually catching the bug' and rewrites a correct test.
- **Fix:** Use `git stash push -u -- <implementation-files>` and add a verification beat: confirm via `git status`/`git diff` that the implementation actually reverted before running the must-fail test.
- **Best practice:** BP23, BP19
- **Verifier:** CONFIRMED — Verbatim at SKILL.md:245. At the gate the implementation is still uncommitted (gate step 1 commits only the test), so a newly created fix file is untracked; git stash push with a pathspec and no -u leaves it in place, gate step 3 then passes with the fix present, and line 261's rule misdiagnoses a correct test and orders a rewrite. The -u flag plus a verify-the-revert beat is the right fix; note the Step 5 circuit-breaker's `git checkout -- <implementation files>` revert shares the same untracked-file blindspot and deserves the same treatment.

#### F7. [low/redundancy] skills/tdd/SKILL.md — Step 3, line 162

- **Quote:** "For **bug fixes**: the first behavior is always "reproduce the bug" — a test that demonstrates the current broken behavior."
- **Problem:** This restates verbatim the 'Bug fixes — first behavior is always "reproduce the bug"' bullet 24 lines earlier in the same step's decomposition strategies (line 138), and neither copy is test-enforced (validate.sh guards only scenario tokens and summary headings).
- **Fix:** Delete the line-162 restatement; the strategies bullet and the scenario-driven shortcut's 'verify Scenario 1 is a reproduce-the-bug case' already cover both paths.
- **Best practice:** BP1
- **Verifier:** CONFIRMED — Verbatim at SKILL.md:162, a near-exact restatement of the line-138 strategies bullet. Checked enforcement: expected-outputs.yaml has zero tdd/reproduce entries, and validate.sh's tdd checks cover only the '## Scenarios'/'### Scenario:' tokens (lines 798-804) and the summary headings (line 835) — this duplication is not test-enforced. Both decomposition paths remain covered after deletion (line 138 for the generic path, line 133's reproduce-the-bug check for the scenario path), so removal is safe under BP1.

#### F8. [low/weak-description] skills/tdd/SKILL.md — frontmatter, line 2

- **Quote:** "Use when starting a new feature or bug fix with test-first discipline."
- **Problem:** The description omits the skill's consequential git side effects (creates a feature branch, auto-commits each cycle, pushes to origin) and gives the menu-scanning user no negative trigger against the confusable sibling /optimus:unit-test (adding tests to existing code).
- **Fix:** Append one sentence, e.g. 'Creates a feature branch, commits each cycle, and pushes for /optimus:pr; for adding tests to existing code use /optimus:unit-test.' — still well under length limits.
- **Best practice:** BP4
- **Verifier:** CONFIRMED — Description verbatim at SKILL.md:2. The skill creates a branch, auto-commits every cycle, and pushes to origin without confirmation — consequential side effects invisible at the slash-menu surface — and D1 explicitly asks for negative triggers on confusable siblings. The sibling /optimus:unit-test's own description already models the cross-reference pattern ('For an automated multi-cycle... use /optimus:unit-test-deep'), so the proposed sentence is house-style-consistent and stays far under 1024 chars. Low severity is right.

#### F9. [medium/missing-guidance] skills/tdd/SKILL.md — Step 9 'Commit remaining work' + Stats template, ~lines 347-367
*Found by verifier (adversarial pass) — treat as confirmed*

- **Quote:** "- Tests passing: all ✓"
- **Problem:** The stop-mid-cycle path commits and pushes uncommitted work (possibly a failing Red test) with no test run or quality-gate coverage, yet the Stats template unconditionally asserts 'Tests passing: all ✓' — contradicting the skill's own verification protocol ('never claim... state the actual result with evidence').
- **Fix:** In 'Commit remaining work', run the test suite first; if the mid-cycle test fails, mark it skipped per project convention (mirroring the circuit-breaker's skip option) or surface the failure, and make the Stats line report the actual last-run result instead of a hardcoded 'all ✓'.
- **Best practice:** BP11, BP20, BP13

#### F10. [low/convention-conflict] skills/tdd/references/tdd-worktree-orchestration.md — Cleanup, line 35 (vs SKILL.md Step 9 subsection order)
*Found by verifier (adversarial pass) — treat as confirmed*

- **Quote:** "offer cleanup after pushing the branch (before recommending `/optimus:pr`)"
- **Problem:** The reference mandates worktree cleanup before recommending /optimus:pr, but SKILL.md Step 9 orders Push → '### Next step — create the PR/MR with /optimus:pr' → '### Worktree cleanup' — a direct cross-file ordering contradiction.
- **Fix:** Pick one ordering: either move '### Worktree cleanup' above the '### Next step' subsection in SKILL.md, or reword the reference's parenthetical to match SKILL.md's actual sequence.
- **Best practice:** BP13

#### F11. [low/doc-drift] skills/tdd/README.md — Features, line 33
*Found by verifier (adversarial pass) — treat as confirmed*

- **Quote:** "**Submodule exclusion** — skips git submodule directories"
- **Problem:** No instruction in tdd's SKILL.md or its loaded references applies the Submodule Exclusion rule (Step 1 loads only the 'Monorepo Scoping Rule' section of constraint-doc-loading.md, unlike code-review's SKILL.md which applies the rule explicitly), so the README advertises behavior with no instruction surface — contradicting the assessor's 'no material D9 drift' claim.
- **Fix:** Either delete the README bullet or add one line to Step 1 applying the 'Submodule Exclusion' rule from `$CLAUDE_PLUGIN_ROOT/skills/init/references/constraint-doc-loading.md`.
- **Best practice:** D9 (BP24)

### Already well-tuned (preserve; do not churn while fixing the above)

- The Iron Law and the horizontal-slicing anti-pattern are placed up front with a memorable WRONG/RIGHT diagram — critical discipline rules exactly where BP22 wants them.
- Feedback loops are exemplary: the verification-protocol gate applied to every test run, the 3-attempt circuit breaker with structured options, the bug-fix regression gate's revert/restore proof, and the quality gate's revert-and-reapply-one-at-a-time fix flow (BP11, BP20).
- Progressive disclosure is well-calibrated: a 406-line body (under the cap) with tight single-purpose references (quality-gate, spec-context-detection, coverage-detection all under 40 lines), shared procedures reused across skills instead of duplicated, and a ToC on the one >100-line reference (testing-anti-patterns.md).
- Conditional workflows are explicit throughout — suitable/not-suitable classification with concrete redirects, the scenario-driven shortcut vs generic decomposition, and the test-passes-unexpectedly branch each guide the decision point rather than leaving it to guesswork (BP16).
- The /optimus:pr handoff contract is test-enforced (validate.sh checks the exact '## TDD Summary' / '### Behaviors Implemented' / '### Coverage' heading tokens on both producer and consumer), and the closing tip follows the shared skill-handoff Variant A verbatim.
- README.md is closely aligned with SKILL.md behavior — features, examples, suitability table, and git workflow all match the instruction surface (no material D9 drift found).

---

## 8. how-to-run — 5/10

Files: `skills/how-to-run/SKILL.md` (221 lines) plus the skill's `agents/`, `references/`, `templates/`, `README.md`, and any shared references named in findings.

**Improvement need:** assessor 5 → verified **5** / 10. Rebuild recommended: no.

**Description assessment (1021 chars):** Accurate and information-rich — it states what the skill does, its write-scope guarantee, and two explicit "Use…" triggers in third person — but at 1021 characters it is tuned like a model-triggering description even though the plugin disables model invocation; for the actual audience (a human scanning the truncating slash menu) roughly two thirds of it (stack enumeration, detection-signal list) is noise that belongs in README.md. The leading words are good ("Generates or updates a project's HOW-TO-RUN.md…").

**Assessor score rationale:** The skill's core loop (detect → audit → assess → generate → verify) is sound, internally consistent, and unusually well defended against hallucination and injection, so nothing structural is broken. But it needs several targeted fixes with real user impact: one conflicting instruction that sends multi-repo users to an impossible /optimus:commit, one audit rule that forces misleading build commands onto the common Linux single-config CMake class, a description ~4x too long for its actual slash-menu audience, and a per-run structural inefficiency (771 lines of render templates injected into the detection agent). That is squarely "moderate — several targeted fixes", not polish (multiple mediums touch the deliverable's correctness) and not structural (each fix is local and refinement-sized).

**Verifier adjusted rationale:** Seven of eight findings survive as reported and one downgrades from medium to low (the Step 1 §Trigger forward-pointer degrades gracefully — the reference loads at Step 3 and the trigger is re-evaluated at Step 4). What remains is exactly the assessor's core case: two deliverable-correctness mediums (the Template-shape audit forcing no-op --config fences onto the common single-config CMake class, and the unconditional /optimus:commit recommendation contradicting Step 5's own not-version-controlled statement for multi-repo workspaces), one rubric-explicit description mis-tuning (verified at 1021 chars against the 1024 cap, with README already carrying the trimmed material), and one genuine per-run BP7 inefficiency (~680 irrelevant render-template lines pasted into the sonnet detector's context), plus three confirmed low pointer/terminology cleanups. My hunt for missed high-severity problems came up empty: the description accurately mirrors behavior, the write-scope rule is top-placed and repeated, the Web-Search Recipe carries explicit per-step failure fallbacks, and the closest candidates (Step 5's factually-off 'already approved the plan in Step 3' clause on the fresh-write branch; no recovery guidance if the detector omits a hidden return table) degrade softly and would not survive adversarial scrutiny as highs. Every fix is local and refinement-sized, none structural, so 5 ('moderate — several targeted fixes') stands: multiple mediums touch the deliverable's correctness on common project classes, which rules out 3-4 polish, while the skill's architecture (agent delegation, generation-rules paired with Step 6 audits, CI-pinned wiring) is sound and rebuild is clearly unwarranted.

### Findings to implement

#### F1. [medium/over-specification] skills/how-to-run/references/step6-verification-audits.md — Template-shape audit, line 39 (paired with SKILL.md Step 4 item 7, line 146)

- **Quote:** "Match per build system: CMake / .NET — `--config Debug` / `--configuration Debug` (and the matching `Release` form)"
- **Problem:** The audit hard-requires literal `--config Debug/Release` fences for every CMake project, but `--config` is a no-op for single-config generators (Ninja/Unix Makefiles — the Linux default), where build type is set at configure time via `-DCMAKE_BUILD_TYPE`.
- **Fix:** For CMake, also accept a `-DCMAKE_BUILD_TYPE=Debug` / `=Release` configure-step pair as satisfying the Debug+Release check, or scope the mandatory `--config` pair to multi-config generators (Visual Studio / Xcode). Failure today: a Linux CMake+Ninja project's correct rendering fails the audit, and the forced rewrite documents `--config` commands that silently do not change the build type.
- **Best practice:** BP2, BP21
- **Verifier:** CONFIRMED — Quote verbatim at step6-verification-audits.md:39. `cmake --build --config` is a documented no-op on single-config generators (Ninja/Unix Makefiles — the Linux default), where build type is set at configure time via -DCMAKE_BUILD_TYPE; the how-to-run-sections.md §Build skeleton even labels CMake categorically 'multi-configuration'. The audit as written either rejects a correct -DCMAKE_BUILD_TYPE rendering or forces misleading --config fences into the deliverable. The fix leaves validate.sh's pinned tokens ('Build Debug+Release pair', 'Default skeleton — multi-configuration build systems') intact.

#### F2. [medium/ambiguity] skills/how-to-run/SKILL.md — Step 6 'Recommend next skill', line 216 (conflicts with Step 5 'Placement rules by topology', line 190)

- **Quote:** "If `HOW-TO-RUN.md` was created or updated: recommend `/optimus:commit` to commit the new or modified file."
- **Problem:** Step 5 states the multi-repo workspace HOW-TO-RUN.md 'is not version-controlled (the workspace root has no `.git`)', yet Step 6's first-match rule unconditionally recommends /optimus:commit, sending the user to commit a file in a directory that is not a git repo.
- **Fix:** Add a topology guard: for multi-repo workspaces skip the /optimus:commit bullet (fall through to the next recommendation) and use Variant C for the closing tip.
- **Best practice:** BP16, BP25
- **Verifier:** CONFIRMED — Verbatim at SKILL.md:216; directly conflicts with Step 5's statement (line 190) that the multi-repo workspace HOW-TO-RUN.md is not version-controlled (no .git at workspace root). The bullet is unconditional and not pinned by validate.sh; falling through to the next recommendation and using skill-handoff.md Variant C matches the existing 'Otherwise' convention, so the fix is sound and CI-safe.

#### F3. [medium/weak-description] skills/how-to-run/SKILL.md — frontmatter description, lines 2-17

- **Quote:** "Generates or updates a project's HOW-TO-RUN.md — a single document that teaches a new developer how to set up their environment…"
- **Problem:** At 1021 characters (3 under the hard cap) the description is optimized for model-trigger keywords, but with disable-model-invocation the audience is a human scanning a truncating slash menu, where only the first line or two is visible.
- **Fix:** Cut to roughly 350-450 chars: keep the leading WHAT, the never-modifies-other-files guarantee, the audit capability, and the test-enforced phrase 'guided in-chat walkthrough' (validate.sh greps SKILL.md for it); move the stack enumeration and detection-signal list to README.md, which already carries them.
- **Best practice:** BP4, BP1
- **Verifier:** CONFIRMED — I measured the folded description scalar: exactly 1021 characters (1027 bytes minus three multi-byte em-dashes) — the assessor's count is precise. Rubric context #1 explicitly rules a ~1000-char keyword-tuned description mis-tuned for this disable-model-invocation plugin. README.md (lines 9-23) already carries the stack enumeration and detection signals, and validate.sh greps the WHOLE SKILL.md for 'guided in-chat walkthrough' (the phrase also appears at body line 24), so the proposed trim is CI-compatible.

#### F4. [medium/structure] skills/how-to-run/SKILL.md — Step 1 reference list, line 37 (and references/how-to-run-sections.md, 771 lines)

- **Quote:** "`$CLAUDE_PLUGIN_ROOT/skills/how-to-run/references/how-to-run-sections.md` — signal-to-section mapping, build-system signals, source-dependency signals"
- **Problem:** The entire 771-line file — mostly Step-4 render templates, workspace command tables, diagnostic ladders, and the multi-repo template — is pasted wholesale into the sonnet detector agent's context, though the agent only needs the four detection sections.
- **Fix:** Split the detection tables (Signal → Section Mapping, Build System Detection, Source Dependencies Detection, Additional Detection Hints) into a separate detection reference passed to the agent, keeping render templates in the Step 4 file; update validate.sh's heading/token pins accordingly. Every run currently spends ~10k tokens of irrelevant render rules diluting an already regex-dense agent prompt.
- **Best practice:** BP7, BP1, BP3
- **Verifier:** CONFIRMED — Verbatim at SKILL.md:37, and Step 1 explicitly pastes the file's full content into the sonnet detector's context. The agent's tasks consume only ~90 of 771 lines (Signal→Section Mapping, Additional Detection Hints, Build System Detection, Source Dependencies Detection); the remaining ~680 lines are Step-4 render templates, workspace command tables, ladders, and the multi-repo template — irrelevant to detection and paid every run. Not test-enforced duplication; the split requires the validate.sh pin updates the assessor already names (the pinned headings/table tokens live in $sections_file). Textbook BP7.

#### F5. [medium/under-specification] skills/how-to-run/SKILL.md — Step 1 Checkpoint, 'External service default endpoints' bullet, line 55

- **Quote:** "Flag values that trigger a Pre-Conditions Block (per `external-services-docker.md` §Pre-Conditions Block §Trigger)"
- **Problem:** At Step 1 that reference has not been read yet (the first read instruction is Step 3), and the trigger's first condition (Recommended runtime per the Step 3 assessment) does not exist yet — a fresh Claude must either guess the flag semantics or interrupt the checkpoint to side-read a 394-line file.
- **Fix:** Inline the evaluable half of the trigger: 'Flag rows whose Endpoint semantics is local-windows-auth, local-named-instance, or local-socket', dropping the cross-file pointer at this step (the full trigger is re-evaluated at Step 4 where the file is loaded).
- **Best practice:** BP21, BP8
- **Verifier:** ADJUSTED — Real and accurately described: at Step 1 the 394-line reference has not been read (first read instruction is Step 3), and §Trigger's first condition (Step 3 Recommended runtime / Step 4 downgrade choice) cannot exist yet — only the three local-* endpoint labels are evaluable. But severity overstates it: the reference is loaded at Step 3 anyway, the trigger is fully re-evaluated at Step 4, and a missed Step-1 flag still surfaces through the Step 3 assessment table, so the failure degrades gracefully (a one-step-early file read or a soft flagging miss). Downgrade to low; the inline-the-three-labels fix is correct and CI-safe.
  - **Revised severity:** low
  - **Revised fix (implement this one):** Inline the evaluable condition at Step 1 — 'Flag rows whose Endpoint semantics is local-windows-auth, local-named-instance, or local-socket' — and drop the §Trigger cross-file pointer there; the full trigger is re-evaluated at Step 4 where external-services-docker.md is loaded.

#### F6. [low/ambiguity] skills/how-to-run/SKILL.md — Step 1 'Unsupported-Stack Fallback' and 'LLM-knowledge fallback' paragraphs, lines 71-73

- **Quote:** "use `AskUserQuestion` for step 4 (approval). Commands approved here feed Step 4 content generation"
- **Problem:** Lowercase 'step 4' (fallback procedure) and capitalized 'Step 4' (skill step) collide in one paragraph, and the LLM-knowledge paragraph ('user approval in step 4') never states whether the fallback's step-3 validation rules (no shell operators, bare PATH-resolvable command) also apply to knowledge-inferred commands.
- **Fix:** Write 'fallback step 2/3/4' for the procedure references, and add one clause to the LLM-knowledge paragraph: inferred commands must pass the same step-3 validation before being presented for approval.
- **Best practice:** BP13, BP21
- **Verifier:** CONFIRMED — Verbatim at SKILL.md:71. Lowercase 'step 2/3/4' (fallback-procedure steps) and capitalized 'Step 4' (skill step) collide in one paragraph — real BP13 friction. And the LLM-knowledge paragraph genuinely leaves validation unstated: unsupported-stack-fallback.md step 2 says search failure means 'skip to step 5', so the how-to-run override that instead routes knowledge-inferred commands to step-4 approval never says whether step-3's validation rules (no shell operators, bare PATH-resolvable command) apply to them. Low severity is right; the one-clause fix is sound.

#### F7. [low/redundancy] skills/how-to-run/SKILL.md — Step 4 catalog item 10 'Verify bullets', line 149

- **Quote:** "with `<name>` substituted to the rendered container name, `<password>` matched to the snippet's password placeholder"
- **Problem:** Item 10 restates the substitution mechanics and MongoDB row-selection rule that external-services-docker.md §Verify Commands (seeds) already owns — and then also defers to that section, creating two authoritative statements that can drift.
- **Fix:** Keep the test-enforced '**Verify bullets:**' trigger condition and the 'Stale-tag re-validation' pointer in SKILL.md, and replace the restated substitution mechanics with the existing pointer to §Verify Commands (seeds); validate.sh pins only the pointer tokens, so this is CI-compatible.
- **Best practice:** BP1, BP7
- **Verifier:** CONFIRMED — Verbatim at SKILL.md:149. The same substitution mechanics and MongoDB row-selection rule are owned by external-services-docker.md §Verify Commands (seeds) (line 158), and item 10 also defers to that section — two authoritative statements that can drift. CI check passes: validate.sh pins '**Verify bullets:**' and 'Stale-tag re-validation' in SKILL.md (both kept by the change) and 'MONGO_INITDB_ROOT_USERNAME' only in the reference file, so replacing the restated mechanics with the existing pointer is CI-compatible as the assessor claims.

#### F8. [low/structure] skills/how-to-run/SKILL.md — Step 4 catalog item 5 'External Services', line 144

- **Quote:** "both lowercased, ASCII-only, with `[^A-Za-z0-9]+` collapsed to a single `-`, and any leading/trailing `-` trimmed"
- **Problem:** The full placeholder-substitution and slug-derivation algorithm (~190 words) sits inline in the SKILL body's densest step, far from the snippet templates in external-services-docker.md that it parameterizes and from the Step 6 volume-path audit that re-checks the same shape.
- **Fix:** Move the substitution/slug rules into external-services-docker.md §Snippet Templates next to the templates they fill, leaving a one-line pointer in item 5 — the rules are only needed at render time when that reference is already loaded.
- **Best practice:** BP7, BP22
- **Verifier:** CONFIRMED — Verbatim at SKILL.md:144. The slug/substitution algorithm parameterizes the snippet templates that live in external-services-docker.md, which is guaranteed loaded at Step 4 render time, so co-locating the rules with the templates is a defensible BP7/BP22 move, not taste. No validate.sh pin covers the slug text in either file (the Step 6 volume-path regex in step6-verification-audits.md is self-contained), so the relocation is CI-safe. Borderline-low but survives adversarial review.

### Already well-tuned (preserve; do not churn while fixing the above)

- The write-scope guarantee (only HOW-TO-RUN.md, everything else input-only) is stated up top, repeated at the write step, and mirrored consistently in both agents, the walkthrough, and README — the skill's core safety property is impossible to miss.
- Anti-hallucination discipline is exemplary: every never-guess rule (ports, paths, versions, counts) pairs a Step 4 generation principle with a Step 6 audit that re-derives the token from the filesystem or a <file>:<line> citation — BP11/BP20 done right.
- Agent contracts are precise and drift-proof: exact return-format tables with enums (Confidence, Endpoint semantics, Bootstrap mechanism), an untrusted-data quoting rule, and validate.sh pinning every cross-file heading/token so pointers cannot silently detach.
- Conditional workflows are explicit and test-pinned: exists/doesn't-exist branching, Walk-through/Regenerate/Skip routing with literal jump targets, and the walkthrough's Done/Skip/Stop loop (BP16).
- Progressive disclosure is largely respected: walkthrough, sanitization rules, and Step 6 audit bodies live in dedicated references, and every >100-line file has a ToC (BP9).
- README.md tracks SKILL.md behavior closely — no material doc drift found (D9 clean).

---

## 9. workflow — 4/10

Files: `skills/workflow/SKILL.md` (202 lines) plus the skill's `agents/`, `references/`, `templates/`, `README.md`, and any shared references named in findings.

**Improvement need:** assessor 4 → verified **4** / 10. Rebuild recommended: no.

**Description assessment (707 chars):** At 707 chars it is long but dense: it leads with the strongest sentence (what + mechanism), then differentiation vs /optimus:tdd, when to prefer it, prerequisites, and the token-cost warning — well matched to the human slash-menu audience since menu truncation still leaves the best sentence first. One accuracy nit: "Requires /optimus:init and a spec" understates the supported inline-goal path (argument-hint "[spec path or goal]", Step 2 fallback, README usage example).

**Assessor score rationale:** A well-architected skill with excellent freedom calibration, verification gates, and reference reuse — most dimensions need nothing. The score sits at the top of the minor-polish band because one finding is load-bearing for safety: the missing clean-tree precondition turns the Step 5 Discard instruction (`git reset --hard` + `git clean -fd`) into a data-loss path for pre-existing user work, and the fix is a one-paragraph precondition. The remaining items (unresolvable bare doc filenames in the brief, a description accuracy nit, small redundancy, and a README table omission) are targeted single-line edits.

**Verifier adjusted rationale:** Four of five findings survive adversarial verification: the high dirty-tree/Discard finding is genuinely load-bearing (the skill's only data-loss path — pre-existing WIP carried onto the branch by Step 3, staged by Step 7's git add -A fallback, or destroyed by the Step 5 git clean -fd advice) and its fix is a one-paragraph precondition that no test pins; the medium brief-path finding is confirmed and slightly worsened by the .claude/ edit-forbidden list covering the very docs the brief tells agents to follow; two lows (description accuracy nit, distillation restatement) are confirmed. The README-table finding is refuted as the consistent house pattern across all skill READMEs, and my hunt found no additional high-severity problems — the skill's verification gate, freedom calibration, and test-enforced handoff headings are exemplary. Net: one contained safety fix plus three targeted single-spot edits keeps this at the top of the minor-polish band, matching the assessor's 4.

### Findings to implement

#### F1. [high/missing-guidance] skills/workflow/SKILL.md — Step 5, Discard bullet (line 148); root cause at Step 3 (lines 60-66)

- **Quote:** "have them run `git reset --hard` **and** `git clean -fd` to drop tracked and untracked changes"
- **Problem:** The skill never verifies a clean working tree before branching, yet the Discard path assumes everything uncommitted is workflow output — so a user who invoked the skill with uncommitted WIP is told to run commands that irrecoverably destroy it (and on the success path, Step 7's `git add -A` can stage that unrelated WIP into the feature commit).
- **Fix:** Add a dirty-tree precondition to Step 3 (or Step 1): if `git status` shows uncommitted changes, stop and have the user commit or stash before branching. Alternatively, scope the Discard advice to warn that reset/clean also drops any pre-existing uncommitted work.
- **Best practice:** BP20, BP23
- **Verifier:** CONFIRMED — Quote verbatim at SKILL.md line 148. No clean-tree check exists anywhere in the chain (grepped workflow SKILL.md, tdd SKILL.md, branch-naming.md, verification-protocol.md): Step 3's `git checkout -b` silently carries pre-existing uncommitted WIP onto the feature branch, Step 7 sanctions `git add -A` in exactly the many-files case a fan-out produces, and the Discard bullet asserts everything uncommitted is 'the workflow's output' before recommending `git clean -fd`, which unrecoverably deletes pre-existing untracked files. Showing `git status` first is a weak mitigation because the surrounding text tells the user those changes are workflow output. The fix is safe: validate.sh only pins the Implementation Summary headings for this skill (line 836); nothing in test/expected-outputs.yaml touches this text. High severity stands — it is the one data-loss path in an otherwise well-gated skill.

#### F2. [medium/under-specification] skills/workflow/SKILL.md — Step 4 brief, quality-bar block (line 111); also Step 1 doc table (lines 30-31)

- **Quote:** "Follow this project's testing conventions (framework, file location, naming, mocking) from testing.md, and its code quality rules from coding-guidelines.md."
- **Problem:** The brief hands workflow subagents bare filenames that are not bracketed slots (implying verbatim pass-through), but the docs actually live at `.claude/docs/testing.md` / per-subproject `docs/testing.md` — fresh agents may fail to find them or pick the wrong subproject's copy in a monorepo, and there is no fallback when a doc is absent.
- **Fix:** Show full paths in the Step 1 table and instruct Step 4 to substitute the resolved paths loaded in Step 1 into the brief (dropping the mention when a doc does not exist).
- **Best practice:** BP21, BP18
- **Verifier:** ADJUSTED — Real and verified: init installs these docs at `.claude/docs/testing.md` (root-as-project) or `<subproject>/docs/testing.md` (monorepo, per skills/init/references/constraint-doc-loading.md), and workflow subagents receive only the brief — a bare 'testing.md' forces them to guess, and in a monorepo the wrong subproject's copy is a live risk. But the proposed change is incomplete: the resolved path will typically sit inside `.claude/`, which the very same brief lists under 'Do NOT touch' in the Edit-mode block, so path substitution alone leaves a literal-minded agent unable to read the doc it must follow. Severity medium is correct; the change needs one more clause.
  - **Revised severity:** medium
  - **Revised fix (implement this one):** Show the actual install paths in the Step 1 table, instruct Step 4 to substitute the resolved paths into the brief (dropping the mention when a doc is absent), and clarify in the brief's Edit-mode block that the forbidden list is an edit boundary — agents may read the named constraint docs inside it (or inline the key conventions into the brief instead).

#### F3. [low/weak-description] skills/workflow/SKILL.md — frontmatter description (line 2)

- **Quote:** "Requires /optimus:init and a spec (auto-detects docs/specs/ or docs/jira/, or pass a path)."
- **Problem:** The description says a spec is required, but the skill explicitly supports running from an inline goal with no spec at all (Step 2: "if the user gave a task inline … use it"; argument-hint "[spec path or goal]"; README shows an inline-goal invocation).
- **Fix:** Reword to "Requires /optimus:init; takes a spec (auto-detects docs/specs/ or docs/jira/), a spec path, or an inline goal."
- **Best practice:** BP4
- **Verifier:** CONFIRMED — Verbatim in the frontmatter description. Contradicted by three surfaces: argument-hint "[spec path or goal]", Step 2's explicit inline fallback ('/optimus:workflow "Build the CSV import pipeline"'), and the README usage bullet showing an inline-goal invocation. Accuracy of the description against actual behavior is exactly what the repo's disable-model-invocation convention says to judge (rubric context #1, D1/BP4). The rewording is safe — no test pins the description text. Low severity is right: the argument-hint partially mitigates in the slash menu.

#### F4. [low/redundancy] skills/workflow/SKILL.md — Step 2 (line 53)

- **Quote:** "apply the shared reference's **Distillation** step to the final spec/goal: if it runs longer than ~2-3 sentences, distill it to a single-sentence goal"
- **Problem:** Step 2 restates the mechanics of the shared Distillation rule (threshold, single-sentence output, AskUserQuestion confirm) that it simultaneously delegates to skills/tdd/references/spec-context-detection.md, creating a drift risk if the tdd-owned reference changes.
- **Fix:** Keep only the consumer-specific framing ("apply the shared reference's Distillation step — the result becomes the brief's Goal: slot in Step 4") and drop the restated threshold/confirm mechanics.
- **Best practice:** BP1, D7
- **Verifier:** CONFIRMED — Verbatim at Step 2 line 53. Checked for deliberate enforcement per rubric context #5: no distillation tokens appear in scripts/validate.sh or test/expected-outputs.yaml, so this is not test-enforced duplication. The tdd-owned reference (skills/tdd/references/spec-context-detection.md, Distillation section) already defines the ~2-3-sentence threshold, single-sentence output, and AskUserQuestion confirm; Step 2 restates all three, and line 49 already summarizes the cascade a second time. Only the '(the brief's Goal: slot in Step 4)' pointer is consumer-specific. Real drift risk, correctly rated low, and the trim breaks no repo mechanics.

### Refuted findings — do NOT implement

- [low/doc-drift] skills/workflow/README.md — Skill Structure table (lines 119-130) — "*(shared)* `commit-message/references/conventional-commit-format.md` | Conventional commit message format"
  - **Refuted because:** The quote exists and the two references are indeed absent from the table, but this is the collection-wide house pattern, not workflow-specific drift: the sibling tdd/README.md Skill Structure table (lines 300-316) omits the same two references even though tdd/SKILL.md loads both (lines 17, 37, 406), and no skill README in the repo lists skill-handoff.md or sdd-mapping.md in a structure table — they are cited in prose where topically relevant (pr, code-review, brainstorm, spec-init READMEs). Under rubric context #7 (flag broken applications of a convention, not the convention) and D9's 'materially inconsistent' bar, a table that consistently inventories procedural/content references while omitting the meta-wording references across every skill is a convention choice, not doc drift in this skill.

### Already well-tuned (preserve; do not churn while fixing the above)

- Step 4's launch-now instruction ('launch the workflow now, in this live session… Do not emit the brief as a copy-paste block') pre-empts the exact failure mode a fresh Claude would hit, placed precisely where it matters (BP21, BP22).
- Degrees-of-freedom calibration is exemplary: authoring rules pin the fragile parts (scope, edit guardrail) while explicitly forbidding prescription of phases/agent counts, plus a 'trim the brief… never pad' escape hatch (BP2, BP14).
- Step 5 is a model feedback loop: independent re-verification via the verification-protocol evidence table, VCS-diff proof over agent self-report, and a red path that must re-run the gate before advancing (BP11, BP20).
- Progressive disclosure is clean — a 202-line body delegating cascade, coverage, branch naming, verification, and commit format to shared references, with the /optimus:pr heading contract test-enforced by validate.sh line 836 (BP6, BP7).
- Pre-flight fails fast on a missing Workflow tool with an explicit ordering rationale ('Do not proceed to create a branch in Step 3 for a launch that cannot run') (BP23).
- README is substantively accurate against SKILL.md, and the Workflow-vs-TDD table gives users a genuinely decision-grade comparison.

---

## 10. reset — 4/10

Files: `skills/reset/SKILL.md` (255 lines) plus the skill's `agents/`, `references/`, `templates/`, `README.md`, and any shared references named in findings.

**Improvement need:** assessor 3 → verified **4** / 10. Rebuild recommended: no.

**Description assessment (372 chars):** 372 chars, leads with the action ("Removes files installed by /optimus:init and /optimus:permissions"), third person, states what + when ("Use for clean reinstall or to stop using optimus"), and accurately summarizes the safety posture (always asks, tests never touched, git-recoverability). Well-tuned for a human-scanned slash menu; no change needed.

**Assessor score rationale:** Structurally sound with strong safety gating and verified-accurate fingerprints; needs targeted polish only. The three medium findings (version-skew mislabeling, custom-hook inventory gap, static destructive-default recommendation) are real behavioral gaps but each is a small wording/logic fix, and two of the three fail in the safe direction (files kept, not lost). No structural rework needed.

**Verifier adjusted rationale:** All six assessor findings survive adversarial checks (four confirmed, two adjusted on fix details/framing — none refuted): quotes are verbatim, cross-file evidence (formatter-setup.md custom hooks, permissions' server-level mcp entries, monorepo template headings) bears them out, and nothing proposed collides with validate.sh or expected-outputs.yaml enforcement. However the assessor missed the skill's most consequential defect: the unconditional Step 5 settings.json cleanup contradicts the 'Keep modified' choice by unhooking kept hook files — silently disabling a security guardrail the user elected to preserve, against the README's own 'preserved' promise — plus a misclassification channel where 'Keep modified' deletes user-edited skill-writing-guidelines.md because reset uses a heading heuristic on what is really a near-exact template. One high-severity semantic contradiction plus three real mediums moves this from 'minor polish' (3) to the top of that band / edge of moderate (4). Every fix remains a localized wording or logic edit; the safety framing, fingerprint accuracy, and step structure are sound, so refinement — not rebuild — is right.

### Findings to implement

#### F1. [medium/missing-guidance] skills/reset/SKILL.md — Step 2 > Classification summary (~line 144); mirrored in README.md classification table

- **Quote:** "`MODIFIED` — differs from template or lacks optimus fingerprints (user customized)"
- **Problem:** All verbatim comparisons run against the CURRENT plugin templates, so pristine files installed by an older optimus version (templates demonstrably drift — e.g. restrict-paths.sh changed 3x) are mislabeled "Modified by user" in the plan, misleading the user's keep/remove decision.
- **Fix:** Reword MODIFIED to "differs from current templates — user-modified or installed by an older optimus version" in the classification summary, Step 3 plan display, and the README table, and note `.claude/.optimus-version` can be shown as evidence of version skew.
- **Best practice:** BP21, BP23
- **Verifier:** CONFIRMED — Quote verbatim at line 144. All comparisons target CURRENT plugin templates; templates demonstrably drift (restrict-paths.sh changed 3x per project history, and the 'legacy' .claude/agents/* files are by definition from older versions, so they will near-always classify MODIFIED). Worse, permissions SKILL.md step 4 itself writes user-approved custom patterns into the installed restrict-paths.sh, so even optimus-managed divergence gets labeled 'user customized' in the Step 3 plan ('## Modified by user') and README table. Misleads the keep/remove decision; fails safe but the label is factually wrong. No test enforcement blocks the reword (checked validate.sh and expected-outputs.yaml).

#### F2. [medium/under-specification] skills/reset/SKILL.md — Step 1 inventory (lines 56-64) vs Step 4 (~line 195)

- **Quote:** "remove any entry whose `hooks` array contains commands referencing `.claude/hooks/format-` (init's formatter hooks)"
- **Problem:** Init's unsupported-stack fallback creates custom `format-<language>.sh` hooks not in reset's closed inventory list, so Step 4 strips their settings.json entry while the hook file itself is never listed or deleted — an orphaned file left behind.
- **Fix:** Change the hooks inventory from a fixed filename list to a pattern scan of `.claude/hooks/format-*` (classify against a template when one exists, else LIKELY_GENERATED via the shell-hook pattern), matching Step 4's prefix-based settings cleanup.
- **Best practice:** BP21, BP16
- **Verifier:** CONFIRMED — Quote verbatim at line 195. formatter-setup.md line 31 confirms init's unsupported-stack fallback creates custom `format-<language>.sh` files not in reset's closed Step 1 inventory (9 fixed names). Step 4's prefix-based cleanup removes their settings entry while the file is never listed, classified, or deleted — an orphaned file. Init SKILL.md line 189 explicitly treats custom fallback hooks as generated content ('Always overwrite existing hooks (both template-based and custom fallback hooks)'), so inventorying them by pattern is consistent with init's own model. Proposed pattern-scan change matches Step 4's existing prefix logic and breaks nothing.

#### F3. [medium/missing-guidance] skills/reset/SKILL.md — Step 3 AskUserQuestion options (~line 179)

- **Quote:** ""Remove all" (Recommended) — remove all optimus files (UNMODIFIED + LIKELY_GENERATED + MODIFIED). Safe when git-tracked"
- **Problem:** The "(Recommended)" label is static, so when MODIFIED files exist that are NOT git-tracked the default recommendation is irreversible deletion of user customizations with no recovery path.
- **Fix:** Make the recommendation conditional: recommend "Remove all" only when every MODIFIED file is git-tracked; otherwise recommend "Keep modified" and flag the untracked MODIFIED files in the option text.
- **Best practice:** BP20, BP16
- **Verifier:** ADJUSTED — Quote verbatim at line 179. Real: the option text is fixed low-freedom, the skill already computes per-file git tracking in Step 2, yet the recommendation never uses it — when MODIFIED files are untracked, the recommended default irreversibly deletes user customizations. Severity medium stands. The proposed change is sound but incomplete: reset's README.md line 35 hardcodes 'Remove all (Recommended)' too, so fixing only SKILL.md creates doc drift (D9).
  - **Revised severity:** medium
  - **Revised fix (implement this one):** Make the recommendation conditional (recommend 'Remove all' only when every MODIFIED file is git-tracked; otherwise recommend 'Keep modified' and name the untracked MODIFIED files in the option text), and update the README's confirmation-choices bullet to state the recommendation is conditional on git tracking.

#### F4. [low/ambiguity] skills/reset/SKILL.md — Step 2 generated-docs fingerprint table, .claude/CLAUDE.md row (~line 115) vs prose at line 127

- **Quote:** "`Conventions`, `Commands`, `Project Structure`, `Before Writing Code`, `Documentation`"
- **Problem:** The table gives CLAUDE.md a heading fingerprint (single-project template only), but line 127 restricts heading-matching to docs and the monorepo template has different headings (Architecture, Subproject Docs) — a model applying the table's headings misclassifies a pristine monorepo root CLAUDE.md as MODIFIED.
- **Fix:** Either drop the headings column for the CLAUDE.md row (comment-only check, as the prose implies) or add the monorepo heading set alongside the existing monorepo comment variant.
- **Best practice:** BP13, BP21
- **Verifier:** CONFIRMED — Quote verbatim at line 115. Verified against templates: single-project-claude.md has exactly these headings, but monorepo-claude.md has Architecture/Commands/Subproject Docs/Before Writing Code/Documentation. The prose (line 121: comment-only check for CLAUDE.md incl. monorepo variant; line 127: heading matching scoped to the four docs) conflicts with the table's heading cell for the CLAUDE.md row — a model following the table misclassifies a pristine monorepo root CLAUDE.md as MODIFIED. Fails safe and only under one of two readings, so low is right; dropping the heading cell (or adding the monorepo set) is the correct fix.

#### F5. [low/structure] skills/reset/SKILL.md — Step 5 item 2 (~line 215), referencing Step 4

- **Quote:** "Clean `settings.json` per Step 4 (always — regardless of user's choice, since surgical removal preserves user content)"
- **Problem:** Step 4 is numbered as a sequential workflow step between the confirmation question and execution, yet Step 5 re-invokes it as a sub-procedure — a sequential reader either runs it twice or must guess when it executes.
- **Fix:** Fold the settings.json procedure into Step 5 (e.g. "Step 5a") or annotate Step 4's heading with "(procedure — performed during Step 5, skipped on Abort)".
- **Best practice:** BP10, BP22
- **Verifier:** ADJUSTED — Quote verbatim at line 215 and the numbering wobble is real (Step 4 sits between confirmation and execution yet is re-invoked from Step 5). But the finding overstates the failure: either reading — run Step 4 in sequence then again at Step 5, or defer until Step 5 — produces identical results because the surgical removal is idempotent; no wrong behavior exists. Also, the 'fold into Step 5a' variant of the fix would break the existing cross-references to 'Step 4' at lines 16, 137, and 145.
  - **Revised severity:** low
  - **Revised fix (implement this one):** Keep only the annotation variant: mark Step 4's heading as a procedure executed during Step 5 (skipped on Abort), leaving the 'Step 4' cross-references in the Safety Rules and Step 2 intact.

#### F6. [low/other] skills/reset/SKILL.md — Step 4, permissions entries (~line 201)

- **Quote:** "Also remove any `mcp__*` entries — but only if a `.mcp.json` file exists in the relevant project root"
- **Problem:** The permissions skill only adds server-level `mcp__<server-name>` entries for servers declared in .mcp.json, but reset's blanket `mcp__*` removal also deletes user-added tool-level entries (e.g. `mcp__github__get_issue`) whenever .mcp.json exists.
- **Fix:** Narrow removal to entries of the exact form `mcp__<server-name>` where `<server-name>` is a server declared in the relevant `.mcp.json`, leaving all other `mcp__*` entries untouched.
- **Best practice:** BP21
- **Verifier:** CONFIRMED — Quote verbatim at line 201. Verified: permissions SKILL.md (lines 52, 58) adds only server-level `mcp__<server-name>` entries for servers declared in .mcp.json, so reset's blanket `mcp__*` removal sweeps user-added tool-level entries (e.g. `mcp__github__get_issue`) and entries for servers configured outside .mcp.json whenever any .mcp.json exists. Reset's own README (line 70) already describes the narrower behavior — 'MCP server allow entries (mcp__*) added by permissions → removed' — so the SKILL.md is out of line with its own docs. Proposed narrowing matches what permissions actually installs. Low severity is right (lost allow entries cause extra prompts, not data loss).

#### F7. [high/ambiguity] skills/reset/SKILL.md — Step 5 item 2 (line 215) interacting with Step 4 hook-entry removal (lines 194-198)
*Found by verifier (adversarial pass) — treat as confirmed*

- **Quote:** "always — regardless of user's choice, since surgical removal preserves user content"
- **Problem:** When the user picks 'Keep modified' (or 'Unmodified only') to preserve a customized hook — e.g. restrict-paths.sh carrying user-approved precious patterns that permissions itself wrote in — the unconditional settings.json cleanup still strips that hook's PreToolUse/PostToolUse entry, silently disabling the security guardrail the user explicitly chose to keep, contradicting the README's 'User-added hooks... → preserved' promise.
- **Fix:** In Step 4, remove a hook entry only if the referenced hook file was deleted (or does not exist); if a kept hook file would retain its entry, say so in the Step 7 report, and note the interaction in the Step 3 plan's settings.json line.
- **Best practice:** BP16, BP20

#### F8. [medium/other] skills/reset/SKILL.md — Step 2 generated-docs table, skill-writing-guidelines.md row (~line 117)
*Found by verifier (adversarial pass) — treat as confirmed*

- **Quote:** "*(no comment — check heading)* First line: `# Skill-writing guidelines for`"
- **Problem:** skill-writing-guidelines.md is actually a near-exact template like coding-guidelines.md (init substitutes only [PROJECT NAME] on line 1 — init SKILL.md line 288), so classifying it by heading heuristic means user edits within existing sections classify LIKELY_GENERATED and are deleted even under 'Keep modified', the option that promises to preserve user changes.
- **Fix:** Move skill-writing-guidelines.md from the heuristic table to the near-exact strategy (compare line 2 onward against $CLAUDE_PLUGIN_ROOT/skills/init/templates/docs/skill-writing-guidelines.md), and update the README classification-method table row to match.
- **Best practice:** BP21

### Already well-tuned (preserve; do not churn while fixing the above)

- Safety rules sit at the top, are marked absolute, and precisely scope the blast radius (tests, paths outside .claude/, settings.json surgical-only, mandatory confirmation) — textbook BP20/BP22.
- The fingerprint tables are accurate against every current template: all four CLAUDE.md variant comments, doc first lines, and all three architecture heading sets verified byte-for-byte.
- The settings.json surgical-removal procedure is exact and matches what init/permissions actually merge (prefix-matched hook entries, template-diffed allow/deny, empty-key pruning, `{}` file deletion) — appropriate low freedom for a fragile operation.
- Good progressive disclosure and reuse: 255-line single-file body that consumes init's multi-repo-detection reference and points at templates by path rather than duplicating their content.
- Classification taxonomy (UNMODIFIED / LIKELY_GENERATED / MODIFIED / COMPLEX) is used consistently across steps and in the README, with the plan grouped by category and per-file git recoverability.

---

## 11. unit-test-deep — 4/10

Files: `skills/unit-test-deep/SKILL.md` (155 lines) plus the skill's `agents/`, `references/`, `templates/`, `README.md`, and any shared references named in findings.

**Improvement need:** assessor 4 → verified **4** / 10. Rebuild recommended: no.

**Description assessment (511 chars):** 511 chars, accurate to actual behavior, front-loaded with a scannable lead ("Iterative test-coverage improvement loop") and a clear What+When structure consistent with the sibling deep skills. Two nits: it presents the refactor dispatch as unconditional ("dispatches ... per cycle") when the refactor phase is skipped whenever no untestable items are pending, and it omits the "Requires a test command in .claude/CLAUDE.md" prerequisite that both refactor-deep and code-review-deep state even though this skill hard-stops without one.

**Assessor score rationale:** The skill is structurally excellent and its CLI contract documentation is verifiably accurate, so most findings are one-line consistency fixes. The score sits at the top of the minor-polish band because of one load-bearing gap: the unconditional --allow-red baseline combined with unit-test-step's silent red-rollback means a codebase with pre-existing failing tests burns every cycle of the plugin's most expensive skill with zero retained work and no instructed warning — a targeted two-sentence fix, but in the safety mechanism the whole loop leans on.

**Verifier adjusted rationale:** The assessor's report is accurate: every checkable claim survived code-level verification. What survives is one genuinely load-bearing high (the unconditional --allow-red baseline plus silent per-cycle rollback can burn the plugin's most expensive loop to the cap with zero retained work — though the proposed fix had to be corrected because the CLI prints no failing tail on the allow-red path), five confirmed low one-line consistency/drift fixes, and one finding downgraded (the prerequisite-check conflict converges to a stop via the test-command gate regardless of which branch Claude takes). I add one missed medium in the shared loop template: the rollback case is indistinguishable from success in the step-4 contract, producing phantom cycle-history counts. The skill remains structurally excellent — exemplary progressive disclosure, verified CLI contract, strong safety/bisection design — so this sits at the top of the minor-polish band: mostly one-line edits plus one targeted failure-mode warning and one loop-template clarification. Score stays 4.

### Findings to implement

#### F1. [high/missing-guidance] skills/unit-test-deep/SKILL.md — 'Establish a baseline (fresh runs only)', line 118

- **Quote:** "`--allow-red` is passed unconditionally here: a coverage run legitimately starts with little or no passing test coverage"
- **Problem:** The skill normalizes a red baseline but gives no guidance for the pre-existing-failing-tests case, where every cycle's full-suite run stays red and `unit-test-step` silently rolls back all new tests (it prints only 'continue', appends no coverage history, so the plateau check never fires).
- **Fix:** After the baseline command, add: if the CLI prints `baseline-red-allowed` and the failure output shows failing tests (not merely 'no tests collected'), warn the user that each cycle will be rolled back until the failures are fixed and confirm (or recommend fixing them) before entering the loop.
- **Best practice:** BP23, BP11
- **Verifier:** ADJUSTED — Failure scenario fully confirmed in code: cmd_unit_test_step rolls back on red and prints only 'continue' (cli.py:1013-1023), coverage history is appended only on green (cli.py:1045), so the plateau check never fires and a pre-existing-failure repo burns every cycle to the cap with zero retained work — and SKILL.md:118 actively normalizes the red baseline, suppressing the CLI's own WARNING. Severity high stands. But the proposed change is not implementable as written: on the --allow-red path cmd_baseline does NOT print the failing tail (summary is printed only in the non-allow-red branch, cli.py:1295-1296), so the orchestrator has no 'failure output' to inspect for failing-tests vs no-tests-collected.
  - **Revised severity:** high
  - **Revised fix (implement this one):** After the baseline command, add: on `baseline-red-allowed`, if the project already has tests (per the Step 2 test-infrastructure check from /optimus:init) — or the baseline timed out — warn the user that every cycle's new tests will be silently rolled back until the suite is green, and confirm (or recommend fixing the failures) before entering the loop. Optionally also have baseline print the failing tail on the allow-red path (CLI + test update).

#### F2. [medium/ambiguity] skills/unit-test-deep/SKILL.md — 'Documentation prerequisites', line 48

- **Quote:** "apply the prerequisite check. If `.claude/CLAUDE.md` is missing, stop"
- **Problem:** The referenced prerequisite-check.md says the opposite for the same file ("CLAUDE.md missing → detect tech stack from manifest files ... so the skill can still run"), so a fresh Claude must guess whether to stop or apply the fallback, and the coding-guidelines.md-missing case is left implicit.
- **Fix:** Make the override explicit, e.g. "Run the existence check from prerequisite-check.md, but do NOT use its CLAUDE.md fallback — deep mode hard-stops without `.claude/CLAUDE.md`; the coding-guidelines fallback applies as written." (Same wording is shared by all three orchestrator skills — fix in all three.)
- **Best practice:** BP21, BP16
- **Verifier:** ADJUSTED — The conflict is real and verbatim (SKILL.md:48 vs prerequisite-check.md:14-16 'Use these fallbacks so the skill can still run'), shared by all three orchestrators. But the impact is capped: even if a fresh Claude wrongly applies the fallback, the immediately following 'Test command' section reads .claude/CLAUDE.md and hard-stops when no test command is documented — a missing file converges to a stop either way, only the message differs. Real ambiguity, low consequence.
  - **Revised severity:** low
  - **Revised fix (implement this one):** Keep the assessor's wording fix ('do NOT use its CLAUDE.md fallback — deep mode hard-stops; the coding-guidelines fallback applies as written') applied to all three orchestrator skills, but treat it as a low-priority clarity fix.

#### F3. [low/ambiguity] skills/unit-test-deep/SKILL.md — Step 5 bullet list, line 135

- **Quote:** "Termination check (`continue`, `convergence`, `cap`, `diminishing-returns`)"
- **Problem:** The enum reads as exhaustive but omits `parse-failure`, which orchestrator-loop-paired.md step 11, the CLI, and the README all include.
- **Fix:** Add `parse-failure` to the bullet so the SKILL.md summary matches the loop template's actual `check-termination` contract.
- **Best practice:** BP13
- **Verifier:** CONFIRMED — Verified: SKILL.md:135 omits `parse-failure` while orchestrator-loop-paired.md:190, cli.py:1399-1408, and the skill README:60 all include it. The bullet reads as an exhaustive contract summary. Not test-enforced (checked validate.sh and expected-outputs.yaml); adding the token is a safe one-word fix. Low is right — the loop template Claude actually executes is complete.

#### F4. [low/ambiguity] skills/unit-test-deep/SKILL.md — overview paragraph, line 9

- **Quote:** "Each cycle is two subagent dispatches: first `/optimus:unit-test` (writes tests, measures coverage, flags untestable code), then `/optimus:refactor`"
- **Problem:** The overview (and the frontmatter description) state the pairing unconditionally, while Step 3's warning and the loop template correctly make the refactor dispatch conditional on pending untestable items — an internal inconsistency in the same file.
- **Fix:** Change to "up to two subagent dispatches" (or add "when untestable items are pending") in the overview and description so all three statements agree.
- **Best practice:** BP13, BP4
- **Verifier:** CONFIRMED — Verified internal inconsistency: overview (SKILL.md:9) and frontmatter description state the pairing unconditionally; Step 3's warning ('only when the first phase flags untestable code') and paired-loop step 6 (PENDING==0 → skip) make it conditional. Note the closing Tip (line 155) repeats the unconditional phrasing — acceptable there as a worst-case cost statement, but the fix could touch it too. 'Up to two' is a safe edit.

#### F5. [low/doc-drift] references/coverage-harness-mode.md — 'Refactor Phase Execution', line 100

- **Quote:** "the orchestrator's prompt body includes `Phase: refactor` and `Focus: testability`"
- **Problem:** The actual refactor dispatch prompt in orchestrator-loop-paired.md step 6 contains no `Focus: testability` header line (focus arrives only via prose and the CLI-pinned `config.focus`), and a cli.py comment also references this nonexistent prompt line.
- **Fix:** Either add a `Focus: testability` line to the paired-loop dispatch prompt header, or correct coverage-harness-mode.md (and the `_make_coverage_progress` comment) to say focus is carried by `config.focus` in the progress file.
- **Best practice:** BP13, BP21
- **Verifier:** CONFIRMED — Verified all three artifacts: coverage-harness-mode.md:100 claims the prompt line; the paired-loop step 6 dispatch prompt contains no `Focus:` header (focus arrives via prose and CLI-pinned config.focus, cli.py:159-165); the cli.py:163 comment references the nonexistent line and itself calls it 'decorative'. harness-mode.md resolves focus solely from config.focus, so the doc-correction option (fix coverage-harness-mode.md + the comment) is the right one of the two offered — functionally harmless drift, low severity is correct.

#### F6. [low/weak-description] skills/unit-test-deep/SKILL.md — frontmatter description, line 2

- **Quote:** "Use to drive coverage up on a codebase that has untestable barriers"
- **Problem:** Unlike both sibling orchestrators, the description omits the "Requires a test command in .claude/CLAUDE.md" prerequisite even though Step 2 hard-stops without one (it also elides a verb: "until coverage plateaus or the cycle cap").
- **Fix:** Append "Requires a test command in .claude/CLAUDE.md." to match refactor-deep/code-review-deep, and fix the elision ("...or the cycle cap is reached").
- **Best practice:** BP4
- **Verifier:** CONFIRMED — Verified: refactor-deep and code-review-deep descriptions both end with 'Requires a test command in .claude/CLAUDE.md.' while unit-test-deep's omits it, and Step 2 ('If none is documented, stop') makes it a hard prerequisite. The elision ('...or the cycle cap') is a genuine mixed clause/noun parallelism slip unique to this description (siblings use noun/noun). Appending the sentence keeps the description well under 1024 chars. Low severity appropriate given disable-model-invocation (audience is human scanners).

#### F7. [low/doc-drift] skills/unit-test-deep/README.md — 'Termination Reasons' table, line 57

- **Quote:** "OR the refactor phase reported no testability findings."
- **Problem:** The README's `convergence` row omits the second refactor convergence trigger — findings exist but none are actionable (`no_actionable_fixes`) — which convergence.py and orchestrator-loop-paired.md step 8 both include.
- **Fix:** Amend the row to "...OR the refactor phase reported no testability findings or none actionable."
- **Best practice:** BP4 (accuracy of user docs); D9
- **Verifier:** CONFIRMED — Verified README↔behavior drift: convergence.py:30-31 returns converged on no_actionable_fixes ('found issues but none had actionable fixes') and paired-loop step 8's table says 'no testability findings or none actionable', but README:57's convergence row lists only the first trigger. One-line amendment, low severity, D9 fits.

#### F8. [medium/missing-guidance] references/orchestrator-loop-paired.md — step 4 table (~line 78) and step 10 (~line 181)
*Found by verifier (adversarial pass) — treat as confirmed*

- **Quote:** "`continue` | Unit-test phase complete — proceed to step 5."
- **Problem:** The CLI prints the identical `continue` after a red-suite rollback that discarded the whole phase, and step 10 tells the orchestrator to build record-cycle summaries from the subagent's (now-dropped) JSON — so a rolled-back cycle gets phantom 'N tests written' in cycle_history and status narration, in tension with the imported 'report only what the CLI confirmed' invariant.
- **Fix:** Amend the step-4 table to note `continue` also covers the red-rollback case (the CLI does not distinguish), and instruct step 10/status updates to mark unit-test counts as unverified-by-CLI — or, better, have unit-test-step emit a distinct `rolled-back` token (CLI + test update).
- **Best practice:** BP23, BP21, BP11

### Already well-tuned (preserve; do not churn while fixing the above)

- Progressive disclosure is exemplary: a 155-line SKILL.md delegates the entire loop body to a shared, ToC'd reference (orchestrator-loop-paired.md), staying within the repo's two-level chain policy while keeping conditional-branch detail out of the main file.
- Feedback-loop and safety design is best-in-class: snapshot before every dispatch, an explicitly justified re-snapshot before the refactor phase so rollback preserves the cycle's tests, parse-failure counting across phases and --resume, test-and-bisect, and per-phase checkpoint commits (BP11/BP20).
- Degrees of freedom are well calibrated: exact commands with stdout tables where the CLI contract is fragile (BP21), test-enforced verbatim plugin-root resolution where drift would break Windows runs, and prose freedom elsewhere.
- Every checkable CLI claim in SKILL.md is accurate against scripts/harness_common (hard cap 10 clamping, resume raising the cap and clearing diminishing-returns, archive/not-archived semantics, commit-message format).
- Cost transparency is handled well: the Step 3 confirmation, the --yes headless path with a claude -p example, and the closing Tip all set user expectations for the most expensive orchestrator.

---

## 12. refactor-deep — 4/10

Files: `skills/refactor-deep/SKILL.md` (157 lines) plus the skill's `agents/`, `references/`, `templates/`, `README.md`, and any shared references named in findings.

**Improvement need:** assessor 3 → verified **4** / 10. Rebuild recommended: no.

**Description assessment (516 chars):** At 516 chars it is scannable, leads with the differentiating phrase, and is accurate on mechanics (iteration cap, focus modes, test-command requirement, downstream pointer to /optimus:unit-test). But it spends ~80 chars stating the fresh-subagent fact twice, says "project-wide" although the default initial scope is the feature-branch diff, and omits the single most consequential differentiator vs /optimus:refactor — fixes are applied automatically without per-change approval — plus a negative pointer back to the sibling for single supervised passes.

**Assessor score rationale:** The orchestration core — the part that must not break — is accurate and well-guarded: every CLI claim in SKILL.md was verified against harness_common/cli.py and holds, the re-entry guard and green-baseline gate are correctly placed, and progressive disclosure to the shared loop reference is clean. The findings are docs-accuracy and discoverability defects (contradictory scope story, missing baseline-red recovery flag, description polish), all fixable with targeted line edits and none affecting loop correctness. That puts it at minor-polish level, not moderate.

**Verifier adjusted rationale:** Nothing was refuted: all six findings survive in substance (two adjusted — F1's harm mechanism cited a scope line the Step 3 confirmation doesn't contain and misplaced the full-project fallback in cli.py, and F5's replacement wording overstated a CLI guard that only fires on cap-terminated resumes). Verification additionally surfaced one high-severity hole the assessor missed: the --resume path skips the green-baseline gate on a false premise ('the baseline already ran and the calibrated timeout is persisted'), and the skill's own line-109 recovery guidance routes baseline-red users straight into that bypass — a load-bearing defect in the skill's central safety story, since it produces silently garbage runs where bisection reverts good work. That said, the orchestration core remains verified-accurate against cli.py, and every fix (including the missed one) is a localized wording edit in Step 4 plus mirrored edits in code-review-deep, not a structural change. Two mediums + one missed high + four lows of the targeted-edit kind puts this at 4 — top of 'minor polish', one notch above the assessor's 3.

### Findings to implement

#### F1. [medium/ambiguity] skills/refactor-deep/SKILL.md — Step 1 examples, lines 26-29 (README.md lines 23 and 32 mirror it)

- **Quote:** "`/optimus:refactor-deep` → full project, 8 iterations, balanced focus"
- **Problem:** The skill states two contradictory scope models — line 26 says non-path scope means "the full branch diff is still processed" while line 29 claims a bare invocation covers the "full project" — and the actual behavior (CLI init pre-populates scope_files.current from the feature-branch diff, cli.py:575-580, falling back to full-project discovery only when the diff is empty) is never stated in this skill, so the orchestrator will misdescribe scope in the Step 3 confirmation and users get a branch-footprint run when they expected the whole project.
- **Fix:** State the real rule once in Step 1: "with no path scope, iteration 1 covers the feature-branch diff when one exists, otherwise the full project; scope widens per iteration" — then align the example, the description's "project-wide", and both README statements to it.
- **Best practice:** BP21, BP13
- **Verifier:** ADJUSTED — The contradiction is real and verified: SKILL.md line 26 says the full branch diff is processed, line 29 and README line 23 say 'full project', and actual behavior (cli.py:575-580 pre-populates scope_files.current from the branch diff; base-skill Step 3 full-project discovery only when that is empty, per harness-mode.md §1 line 40) is stated nowhere in the skill. But two details are off: (a) the full-project fallback lives in harness-mode.md → base skill Step 3, not cli.py; (b) the claimed harm path is wrong — the Step 3 confirmation template contains no scope line at all, so nothing gets 'misdescribed' there; the harm is user-facing doc drift (example, description's 'project-wide', README). Medium severity stands (D1/D9 drift on the default invocation).
  - **Revised severity:** medium
  - **Revised fix (implement this one):** State the rule once in Step 1: 'with no path scope, iteration 1 covers the feature-branch diff when one exists, otherwise the full project; scope then widens only to files with active findings and newly modified files' (findings.update_scope), and align the line-29 example, the description's 'project-wide', and README lines 23/32 to it.

#### F2. [medium/missing-guidance] skills/refactor-deep/SKILL.md — Step 4 "Establish a green baseline", line 121

- **Quote:** "On `baseline-red`, stop and show the user the failing tests"
- **Problem:** The stop instruction gives no user-level recovery: the CLI's own failure message (cli.py:1297) says "pass --allow-red", an internal flag the skill does not parse — a user who re-runs `/optimus:refactor-deep --allow-red` gets it silently swallowed as scope text (Step 1 rule 7) and then hits "progress file already exists", and `--allow-red-baseline` appears nowhere user-discoverable (not in argument-hint, examples, or README).
- **Fix:** Extend the baseline-red handling to: "tell the user to fix the failing tests or re-run with `--allow-red-baseline` (note the CLI's message names the internal `--allow-red` flag)", and document `--allow-red-baseline` in the README.
- **Best practice:** BP23, BP21
- **Verifier:** CONFIRMED — All claims verified: cli.py:1297-1300 prints 'pass --allow-red' (a CLI-internal flag the skill never parses — Step 1 rule 6 only recognizes --allow-red-baseline); a user re-running with --allow-red gets it swallowed as scope text per Step 1 rule 7, then hits init's 'progress file already exists' error (cli.py:592-599); and --allow-red-baseline appears in no user-facing surface (README has zero allow-red mentions, argument-hint omits it, no example uses it). The proposed change is sound and breaks no repo mechanics.

#### F3. [low/weak-description] skills/refactor-deep/SKILL.md — frontmatter description, line 2

- **Quote:** "Each iteration runs in an isolated subagent so context does not accumulate."
- **Problem:** The description restates the fresh-subagent-per-iteration fact already given in its first clause, while omitting the key differentiator from the sibling /optimus:refactor (fixes auto-applied without per-change approval) and a negative trigger pointing back to it — the exact confusable pair, and refactor's description does point forward to refactor-deep.
- **Fix:** Replace the duplicate sentence with e.g. "Fixes are applied automatically without per-change approval; for a single supervised pass, use /optimus:refactor."
- **Best practice:** BP4, BP1
- **Verifier:** CONFIRMED — Quote is verbatim (line 2) and duplicates 'runs /optimus:refactor in a fresh subagent context per iteration' from the description's first clause. Verified that the sibling skills/refactor/SKILL.md description ends with a forward pointer ('For iterative refactor in a loop, use /optimus:refactor-deep') while refactor-deep has no reciprocal negative trigger, and the auto-apply-without-per-change-approval differentiator (SKILL.md lines 67 and 153) is absent from the description. Low severity is right — descriptions here serve human menu-scanning (repo context #1), and the swap costs no chars.

#### F4. [low/under-specification] skills/refactor-deep/SKILL.md — frontmatter argument-hint, line 4

- **Quote:** ""[testability|guidelines] [path] [--resume] [--yes] [--max-iterations N]""
- **Problem:** The hint omits two of the five flags Step 1 parses — `--no-commit` (documented in examples and README) and `--allow-red-baseline` (documented nowhere user-facing) — so users typing the slash command cannot discover them.
- **Fix:** Add `[--no-commit]` and `[--allow-red-baseline]` to the argument-hint (or at minimum add both to the README usage list).
- **Best practice:** BP4
- **Verifier:** CONFIRMED — Verified: Step 1 parses five flags (--resume, --no-commit, --yes, --max-iterations, --allow-red-baseline); the hint lists three. --no-commit is in the examples (line 34) and README (line 28) but not the hint; --allow-red-baseline is in nothing user-facing. validate.sh only enforces that argument-hint is quoted, so adding flags is safe. Low severity correct.

#### F5. [low/ambiguity] skills/refactor-deep/SKILL.md — Step 4 "On --resume", line 89

- **Quote:** "Pass `--max-iterations N` through when the user supplied a higher cap on `--resume`"
- **Problem:** The orchestrator cannot evaluate "higher" without reading the progress file (which the loop invariants discourage), and the CLI already clamps any value and guards cap-overrun itself (cli.py:696-728), so the conditional either forces a needless progress-file read or drops a user-supplied flag.
- **Fix:** Reword to "Pass `--max-iterations N` through whenever the user supplied it on `--resume` — the CLI clamps it and refuses a cap at or below the completed count."
- **Best practice:** BP21, BP2
- **Verifier:** ADJUSTED — The ambiguity is real: evaluating 'higher' requires reading the persisted cap, which the loop invariants ('slice-only progress reads') forbid, so a literal orchestrator either does a needless read or drops the flag. But the assessor's replacement wording overstates the CLI guard: the 'refuses a cap at or below the completed count' check (cli.py:713-728) fires only when the prior run terminated with reason 'cap'; on a diminishing-returns or interrupt resume, a lower N is silently accepted and lowers the cap (cli.py:696-700 sets any different value). Also note the identical phrase exists in skills/code-review-deep/SKILL.md line 90 — both consumers need the fix.
  - **Revised severity:** low
  - **Revised fix (implement this one):** Reword in both -deep skills to: 'Pass --max-iterations N through whenever the user supplied it on --resume — the CLI clamps it to the hard cap and, when the prior run ended at its cap, refuses a value at or below the completed count.'

#### F6. [low/redundancy] skills/refactor-deep/SKILL.md — Step 6: Final Report, lines 143-149 (vs references/orchestrator-loop-single.md "After the loop")

- **Quote:** "This prints the cumulative report and archives the run — except on a `diminishing-returns` soft-exit"
- **Problem:** Step 6 duplicates the shared loop reference's "After the loop" section — identical final-report command plus the same diminishing-returns/not-archived explanation — and both files are loaded in the orchestrator's context (Step 5 mandates reading the loop file); not test-enforced (no hits in validate.sh or expected-outputs.yaml).
- **Fix:** Trim Step 6 to the command only and defer the archival semantics to the loop reference's "After the loop" section (or vice versa for both -deep consumers).
- **Best practice:** BP1, BP7
- **Verifier:** CONFIRMED — Duplication verified: SKILL.md lines 143-149 repeat the final-report command plus the diminishing-returns/not-archived semantics that orchestrator-loop-single.md 'After the loop' (lines 154-162) states more fully, and both files are in context by Step 6 (Step 5 mandates reading the loop reference). Checked scripts/validate.sh (no final-report/archival/refactor-deep string checks) and test/expected-outputs.yaml (zero matches) — not test-enforced, so fair game per repo context #5. The change correctly keeps the concrete command in SKILL.md (the reference only has the <progress-path> placeholder) and trims only the semantics sentence. Low severity right — one sentence of BP1 trim.

#### F7. [high/missing-guidance] skills/refactor-deep/SKILL.md — Step 4 'Establish a green baseline (fresh runs only)', line 113 (interacting with lines 109 and 121)
*Found by verifier (adversarial pass) — treat as confirmed*

- **Quote:** "Skip on `--resume` — the baseline already ran and the calibrated timeout is persisted."
- **Problem:** This premise is false on the skill's own documented paths into --resume that never passed baseline (the baseline-red stop at line 121, or an interrupt between init and baseline): line 109 routes the 'progress file already exists' user to --resume, cmd_resume (cli.py:646-762) never re-checks the baseline, so the green-baseline safety gate is silently bypassed — the loop starts on a red tree and bisection blames and reverts the iteration's good fixes (the exact harm line 121 warns about), and even after the user fixes the tests the timeout stays at the uncalibrated 300s default so a slow suite spuriously times out during bisection.
- **Fix:** Qualify the skip: 'Skip the baseline on --resume only if the prior run completed at least one iteration; if it stopped at baseline-red or before baseline ran, re-run the baseline subcommand (green required, or --allow-red per the user) before entering the loop' — and mirror this in the line-109 progress-file-exists recovery guidance. Apply the same fix to code-review-deep.
- **Best practice:** BP23, BP11

### Already well-tuned (preserve; do not churn while fixing the above)

- Re-entry guard is the first instruction in Step 1 and the confirmation/cost warning is explicit — critical rules are top-placed (BP22) and the destructive loop is gated by user approval plus a green-baseline validate-before-execute gate (BP11, BP20).
- Plugin-root resolution (Step 2) handles the real Windows/env-var pitfall with a deterministic 3-step fallback and a clear literal-substitution rule that the loop reference reinforces (BP23).
- Instruction-vs-code fidelity is excellent: resume cap-raise and diminishing-returns clearing, init --force, baseline timeout calibration, and the archive exception all match cli.py exactly — rationales given (e.g. why to pass --test-command rather than let init re-parse) prevent real failure modes without over-constraining.
- Structure: 157-line body delegating per-iteration mechanics to a shared 163-line loop reference with a ToC, one level deep for the orchestrator (BP6, BP7, BP9).
- Argument parsing is example-backed with 7 concrete invocations including the headless/CI form (BP15, BP21), and focus-keyword rules are stated compactly and consistently with the base skill.
- The Tip section gives one clear default sequencing (testability first, then guidelines in a fresh conversation) instead of an option menu (BP17).

---

## 13. pr — 4/10

Files: `skills/pr/SKILL.md` (269 lines) plus the skill's `agents/`, `references/`, `templates/`, `README.md`, and any shared references named in findings.

**Improvement need:** assessor 3 → verified **4** / 10. Rebuild recommended: no.

**Description assessment (365 chars):** At 365 chars it is well-sized for a human scanning the slash menu: strong leading verb ("Creates or updates..."), states what (Conventional PR format, GitHub/GitLab), the differentiator (captures conversation intent), and when (branch ready for review, or updating an existing PR/MR). Accurate against actual behavior. Only blemish: it mixes "conversation" and "session" in the same sentence while every other surface (body, skill-handoff.md, README) consistently says "conversation".

**Assessor score rationale:** Core flows, failure gates, and the intent-handoff machinery are carefully engineered and largely test-enforced; nothing load-bearing is broken. Findings are polish-level: one medium ambiguity (\"without prompting\" could be read as skipping the Phase 3 confirmation before gh pr edit), stale tdd-consumer claims in pr-template.md and the README, and a handful of low-severity wording/consistency fixes. All are one-line edits — minor polish territory.

**Verifier adjusted rationale:** All seven findings survive: five confirmed as-is, two adjusted for incomplete fixes (README line 36 carries the same stale tdd-consumer claim; SKILL.md line 140 also says 'session'). None were misquotes, taste, or test-enforced conventions — I checked validate.sh (only the summary-heading handoff tokens and the mktemp pattern touch this skill) and expected-outputs.yaml (no pr strings). But the assessor's 3 slightly understates need: two gaps were missed. The substantive one is high severity — Step 4's push logic plain-pushes a diverged branch and fails non-fast-forward in exactly the after-rebase update scenario the skill itself centers, with no failure guidance and no gate before a force-push improvisation, a stark inconsistency with the skill's otherwise meticulous stop messages (BP23/BP20). Second, the multi-repo 'All' loop contradicts the unscoped 'stop' instructions in Steps 2–6 (medium). With one high, two mediums, and seven low/one-line fixes — all targeted, no structural work — the skill sits at the boundary of minor polish and moderate: 4. Rebuild is clearly unwarranted; the architecture, handoff contracts, and gates are sound and largely CI-enforced.

### Findings to implement

#### F1. [medium/ambiguity] skills/pr/SKILL.md — Step 6 Phase 2, "Friction floor" paragraph (line 223)

- **Quote:** "the regeneration must succeed **without prompting** the user"
- **Problem:** Read literally, this conflicts with the mandatory Phase 3 preview AskUserQuestion, so a fresh Claude could skip the confirmation gate before mutating the PR.
- **Fix:** Reword to scope the rule to intent prompts, e.g. "must succeed without any intent-related prompting — the Phase 3 preview/confirm still runs."
- **Best practice:** BP21, BP20
- **Verifier:** CONFIRMED — Quote verbatim at SKILL.md line 223. The bolded, unqualified rule sits in Phase 2 while Phase 3 immediately mandates an AskUserQuestion before `gh pr edit`. Sequential structure mitigates, but a rule stated as absolute ('must succeed without prompting') can plausibly override a later step for a literal reader, skipping the only confirm gate before mutating the PR. The scoping reword is cheap and breaks nothing. Medium is fair given the mutation risk (the user did opt in once at 'Ask what to update').

#### F2. [low/doc-drift] skills/pr/references/pr-template.md — intro (line 3)

- **Quote:** "Both `/optimus:pr` and `/optimus:tdd` use this template."
- **Problem:** Stale: tdd's SKILL.md no longer reads this template (it delegates PR creation entirely to /optimus:pr per skill-handoff.md); the actual second consumer is /optimus:code-review via the Intent-detection heuristic.
- **Fix:** Update the sentence to name `/optimus:pr` and `/optimus:code-review` (Intent heuristic) as the consumers.
- **Best practice:** BP12, BP13
- **Verifier:** CONFIRMED — Verbatim at pr-template.md line 3. Repo-wide grep confirms skills/tdd/SKILL.md never reads pr-template.md — TDD Step 9 pushes and delegates PR creation to /optimus:pr, and references/skill-handoff.md line 27 says inline PR creation from TDD is deliberately unsupported. The real second consumer is skills/code-review/SKILL.md:133 (canonical Intent-detection heuristic). Not test-enforced: validate.sh only asserts the summary-heading handoff tokens, and expected-outputs.yaml has no match. Genuine doc drift.

#### F3. [low/redundancy] skills/pr/SKILL.md — Step 5 "Detect default branch" (lines 80–81)

- **Quote:** "**GitHub:** `gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name'` … **GitLab:** use the default branch detected in Step 1"
- **Problem:** Step 1 already ran the default-branch-detection algorithm for the gate check, yet GitHub re-detects via the API with no rule for which value wins if they differ.
- **Fix:** Either reuse Step 1's result for both platforms, or state explicitly that the API value is authoritative for Step 5's diffs when it differs from Step 1's local detection.
- **Best practice:** BP17, BP13
- **Verifier:** CONFIRMED — Near-verbatim at lines 80–81. Step 1's Verify-git-state already ran the shared default-branch-detection algorithm as a gate, then Step 5 re-detects via the GitHub API with asymmetric platform handling and no precedence rule. Not enforced by validate.sh or expected-outputs.yaml. Low severity is right — operationally Step 5's value feeds the subsequent commands, so the divergence only bites when the gate decision was wrong. Of the two offered fixes, prefer 'API value is authoritative' — reusing Step 1's local chain for GitHub would lose accuracy when origin/HEAD is stale.

#### F4. [low/ambiguity] skills/pr/SKILL.md — Summary population rule, Problem bullet (line 140)

- **Quote:** "as specified in the state 1 rules above — quote/summarize the spec or JIRA task file if it was loaded"
- **Problem:** The pointer claims the spec/JIRA/initiating-brief guidance was "specified above", but the state-1 rules (line 125) contain none of it — the rule only exists here, so the cross-reference misleads.
- **Fix:** Drop "as specified in the state 1 rules above" or move the spec/JIRA/initiating-brief guidance up into the state-1 rule it claims to restate.
- **Best practice:** BP13, BP21
- **Verifier:** CONFIRMED — Verbatim at line 140. The state-1 rule at line 125 says only 'populate ... from the conversation; omit sub-fields with no clear answer' — it contains no spec/JIRA/initiating-brief guidance, so the cross-reference points at content that does not exist above. A fresh Claude wastes a lookup or doubts which rule governs. Dropping the phrase is safe (no path or token contract touched). Low severity accurate.

#### F5. [low/doc-drift] skills/pr/README.md — Skill Structure table (lines 208–209, also line 172)

- **Quote:** "Shared platform detection and CLI management reference (used by this skill, `/optimus:tdd`, and `/optimus:code-review`)"
- **Problem:** README credits /optimus:tdd as a consumer of both pr-template.md and platform-detection.md, but tdd's SKILL.md references neither and tdd's own README states TDD does not perform platform detection.
- **Fix:** Correct both table rows (pr-template.md: this skill + /optimus:code-review; platform-detection.md: this skill + /optimus:code-review) and fix line 172's "shared with /optimus:tdd".
- **Best practice:** BP12 (D9)
- **Verifier:** ADJUSTED — Verbatim at README line 209; lines 172 and 208 carry the same stale claim. tdd's SKILL.md references neither file and tdd's README line 252 explicitly says TDD does not perform platform detection. Real D9 drift, but the proposed change is incomplete: README line 36 ('Shared template — the Conventional PR template is reusable by other skills (e.g., `/optimus:tdd`)') repeats the same stale claim and must be fixed in the same pass; tdd's own README line 316 lists platform-detection.md too and should be corrected alongside.
  - **Revised severity:** low
  - **Revised fix (implement this one):** Correct README lines 208–210 and 172 to name /optimus:pr + /optimus:code-review as consumers, AND fix the Features bullet at line 36; flag tdd/README.md line 316's stale shared-file row for the same batch.

#### F6. [low/other] skills/pr/SKILL.md — Step 8 Final Summary template (line 260)

- **Quote:** "## All PRs/MRs Created"
- **Problem:** The combined-summary heading is fixed to "Created" even though a multi-repo run can include updated (or cancelled) PRs via the Update Flow, unlike Step 7's parameterized "[Created / Updated]" heading.
- **Fix:** Parameterize the heading (e.g. "## All PRs/MRs [Created / Updated]" or "Processed") and/or add a status column, matching Step 7's pattern.
- **Best practice:** BP14, BP13
- **Verifier:** CONFIRMED — Verbatim at line 260. The multi-repo filter (non-default branch + commits ahead) does not exclude repos with existing open PRs, so an 'All' run can route repos through the Update Flow, making the fixed 'Created' heading inaccurate while Step 7's heading is parameterized '[Created / Updated]'. The heading is not asserted in expected-outputs.yaml or validate.sh, so it is not deliberate enforced duplication. Low-severity template inaccuracy; parameterizing matches the existing Step 7 pattern.

#### F7. [low/weak-description] skills/pr/SKILL.md — frontmatter description (line 2)

- **Quote:** "Captures the implementation conversation's intent into the PR description when run in the same session."
- **Problem:** Mixes "conversation" and "session" in one sentence while the body, README, and skill-handoff.md consistently use "conversation" for the continuation-skill concept.
- **Fix:** Change "in the same session" to "in the same conversation".
- **Best practice:** BP13, BP4
- **Verifier:** ADJUSTED — Verbatim at line 2, and the fix ('same conversation') is right — skill-handoff.md and the README consistently say 'conversation'. But the finding's premise that the body is consistent is wrong: SKILL.md line 140 also says 'the start of the session'. The terminology mix is slightly broader than claimed, so the change must cover both spots.
  - **Revised severity:** low
  - **Revised fix (implement this one):** Change the description's 'in the same session' to 'in the same conversation' AND fix line 140's 'from the start of the session' to 'from the start of the conversation'.

#### F8. [high/missing-guidance] skills/pr/SKILL.md — Step 4 'Push branch if needed' (line 62)
*Found by verifier (adversarial pass) — treat as confirmed*

- **Quote:** "If the branch is on the remote but has unpushed commits (`git log origin/<branch>..HEAD`), push them: `git push origin <branch>`"
- **Problem:** After a local rebase — the exact scenario the skill's Update Flow champions (line 223: 'fix the description after a rebase') — origin/<branch>..HEAD lists every rebased commit, the plain push is rejected non-fast-forward, and the skill gives no failure-mode guidance, leaving Claude to improvise a force-push with no confirm gate while every other failure path has an explicit stop message.
- **Fix:** Add divergence detection (`git rev-list --count HEAD..origin/<branch>`): if the remote has commits not in local, do not plain-push — ask the user (AskUserQuestion) before `git push --force-with-lease`, or stop with that command as guidance.
- **Best practice:** BP23, BP20

#### F9. [medium/ambiguity] skills/pr/SKILL.md — Step 6 'Ask what to update', Cancel handling (line 200); same pattern in Steps 2–5 stop conditions
*Found by verifier (adversarial pass) — treat as confirmed*

- **Quote:** "If the user chooses **Cancel** → report the existing PR/MR URL and stop."
- **Problem:** In a multi-repo 'All' run, Step 1.8 says to complete Steps 2–7 per repo then continue, but every mid-flow abort in Steps 2–6 (platform unknown, CLI cancel, Update-Flow Cancel) says unscoped 'stop' — read literally, cancelling one repo's update aborts the remaining repos the user asked for.
- **Fix:** Add one scoping sentence to Step 1.8 (or Step 6): in a multi-repo run, per-repo 'stop' conditions skip to the next repo and record the outcome in the Step 8 summary; only Step 1 gates halt the whole run.
- **Best practice:** BP16, BP13

### Already well-tuned (preserve; do not churn while fixing the above)

- Every pre-flight gate has an exact stop message (no git repo, on default branch, undetectable default branch, CLI missing/unauthenticated, no commits) — BP21/BP23 done right without over-scripting recovery.
- The TDD/Workflow handoff contract is exemplary: case-sensitive literal headings, a compact per-source token table, graceful-degradation scoping, and both producer and consumer sides enforced by validate.sh.
- The Intent-fabrication guard ("Never infer Intent from commit messages or the diff alone") and the Update Flow's "never preserve diff-derivable facts" rule are sharp, rationale-backed safety constraints protecting the /optimus:code-review handoff.
- Progressive disclosure is clean: platform detection, default-branch detection, and the PR template live in shared references consumed by three skills; the 269-line body stays well under the cap.
- The Windows tempfile workaround carries its rationale inline and is backed by validate.sh's portable-mktemp check — low freedom applied exactly where the operation is fragile (BP2).

---

## 14. prompt — 4/10

Files: `skills/prompt/SKILL.md` (220 lines) plus the skill's `agents/`, `references/`, `templates/`, `README.md`, and any shared references named in findings.

**Improvement need:** assessor 4 → verified **4** / 10. Rebuild recommended: no.

**Description assessment (355 chars):** At 355 chars it is compact, third-person, and menu-scannable: leads with the action ("Crafts optimized, copy-ready prompts"), names concrete tool classes, states the multilingual behavior, and closes with an explicit when-clause ("Use when writing, fixing, improving, or adapting a prompt"). The middle sentence spends a few characters on internal mechanics ("selects the right template, runs a diagnostic checklist") rather than outcomes, but this is a minor stylistic point, not a defect. Accuracy vs. actual behavior is exact, including the Decompiler mode implied by "fixing... or adapting".

**Assessor score rationale:** The skill's architecture (hard rules up top, 9-step workflow, disciplined reference loading) is among the stronger patterns audited, and the description is well-tuned, so no structural work is needed. What remains is one real guidance conflict on a mainstream path (contradictory CoT instructions for current Claude/GPT/Gemini targets across Template E, diagnostic #26, and tool-routing) plus accumulated redundancy around the Claude Code routing paragraph, the five-fold marker rule, and the Step 9 handoff duplication — several targeted trims and one reconciliation, all localized edits. That puts it at the top of the minor-polish band rather than the moderate band.

**Verifier adjusted rationale:** The assessor's core diagnosis survives adversarial review: the CoT guidance conflict (Template E + diagnostic #26 vs tool-routing's Claude entry, plus the duplicated reasoning-native list vs Hard Rule 3's single-source designation) is a confirmed high on the skill's most mainstream path, and the Step 9 plan-mode bullet's duplication of skill-handoff.md is a confirmed medium made worse by the fact that the file is loaded at Step 9 anyway. The Variant A deictic mismatch is real (a broken convention application, which the rubric explicitly makes flaggable) though its fix must go through Variant C or an amendment to the shared handoff doc, since variant wording is verbatim-required. Two findings deflate on verification: the Step 4 paragraph restructure drops to low because Template M/N headers independently restate the PROMPT-not-plan rule at load time, and the five-fold marker rule drops to low because three of the five surfaces carry unique site-specific mechanics. The Step 6 technique-duplication finding is refuted outright — it misreads the conditional reference-loading design, and its proposed trim would under-specify supplementary techniques. I add one medium the assessor missed: Step 9's dynamic-workflow bullet re-litigates implementer routing after delivery and internally contradicts itself on migrations. Net: one high, three mediums, two lows on an otherwise exemplary architecture (top-placed hard rules, disciplined progressive disclosure, accurate description and README) — squarely minor-polish at 4, matching the assessor's score for slightly different composition of findings.

### Findings to implement

#### F1. [high/ambiguity] skills/prompt/references/templates.md — Template E header (~line 127); conflicts with references/tool-routing.md Claude section (~line 37) and references/diagnostic-patterns.md #26

- **Quote:** "ONLY for standard reasoning models (Claude, GPT, Gemini, Qwen 2.5, Llama)"
- **Problem:** For a Claude/GPT-5/Gemini-3 logic or debugging task the skill gets contradictory CoT guidance: Template E and diagnostic #26 say add explicit think-step-by-step scaffolding, while tool-routing's Claude entry says "Don't add 'think step by step'... current Claude calibrates reasoning depth automatically" — and Template E hardcodes its own no-CoT list (o3/o4-mini/R1/Qwen3) while Hard Rule 3 designates tool-routing.md as the single current list.
- **Fix:** Make tool-routing.md the single source of truth: have Template E and diagnostic #26 defer to the target tool's routing entry for whether explicit CoT is appropriate (removing the hardcoded model lists), and reconcile the near-identical category names 'Reasoning LLMs' vs 'Reasoning-Native LLMs' so a fresh instance can decide unambiguously.
- **Best practice:** BP13, BP12, BP17
- **Verifier:** CONFIRMED — The contradiction is real on the mainstream path: Step 4's table routes 'Logic, math, debugging' to Template E, whose scaffold prescribes an explicit <thinking> step-enumeration, and diagnostic #26 says add 'Think through both approaches step by step' — while tool-routing's Claude entry (line 37) says "Don't add 'think step by step'... current Claude calibrates reasoning depth automatically". Template E also hardcodes a no-CoT list (o3/o4-mini/R1/Qwen3) that duplicates the list Hard Rule 3 designates tool-routing.md to own. Minor scope quibble: the explicit conflict exists only for Claude targets (GPT-5.x/Gemini entries are merely silent on CoT), but Claude is the plugin's flagship target so high severity stands. The change is safe: no validate.sh/expected-outputs tokens touch these files, Step 3 already loads the routing section before Step 4 loads the template, and a templates.md→tool-routing.md pointer stays within the repo's allowed two-level reference depth.

#### F2. [medium/structure] skills/prompt/SKILL.md — Step 4, Claude Code routing paragraph (~line 112)

- **Quote:** "For Template M **or** N, your output is a PROMPT — NEVER produce the plan or the workflow script itself."
- **Problem:** This critical must-not-skip rule is buried mid-way through a single ~250-word paragraph that mixes six concerns (H/M/N routing, ambiguity handling, the /optimus:workflow scope note, the "Run a workflow to…" trigger phrasing, self-containment), most of which is restated again in tool-routing.md and templates.md Templates M/N.
- **Fix:** Convert the paragraph to a short bulleted decision list (execute → H, plan → M, fan-out → N, spec-implementation → /optimus:workflow) with the PROMPT-not-plan rule as its own emphasized bullet, and leave Template-N mechanics (trigger phrasing, scope rationale) only in templates.md where they already live.
- **Best practice:** BP22, BP16, BP1
- **Verifier:** ADJUSTED — The quote is verbatim (SKILL.md line 112) and the paragraph genuinely mixes ~six concerns as flowing prose where BP16 calls for an explicit decision list. But the 'buried critical rule' failure claim is overstated: Template M's header ('produces a PROMPT... NEVER produce the plan itself') and Template N's header ('NEVER author or output a .js workflow script') restate the rule prominently and are loaded whenever M or N is selected, so a fresh Claude has a safety net at exactly the moment it matters. This is a real readability/conciseness improvement, not a miss-risk fix.
  - **Revised severity:** low
  - **Revised fix (implement this one):** Keep the assessor's restructure (bulleted decision list with the PROMPT-not-plan rule as its own bullet; Template-N mechanics left in templates.md) — it is safe since validate.sh has no wiring tokens on this paragraph — but treat it as polish, not a critical-rule rescue.

#### F3. [medium/convention-conflict] skills/prompt/SKILL.md — Step 9 closing-tip variant mapping (~line 198)

- **Quote:** "an **approved plan-mode prompt that implemented code in this conversation** (→ `/optimus:commit`, then `/optimus:pr`)"
- **Problem:** The mapping forces Variant A, whose verbatim wording is "stay in this conversation when running /optimus:commit", but the tip is delivered in the prompt-crafting conversation right after bullet 1 told the user to paste the prompt "as the first message in a new Claude Code conversation" — the deictic "this conversation" contradicts that instruction, and no code has been implemented in this conversation at delivery time.
- **Fix:** For prompts destined for a different conversation, either emit Variant C or instruct the skill to phrase the tip against the future conversation ("stay in that plan-mode conversation when running /optimus:commit"), and reword the condition so it is decidable at delivery time (e.g., "a plan-mode prompt on the default approve-and-implement path").
- **Best practice:** BP13, BP21
- **Verifier:** ADJUSTED — The defect is real: Step 9 bullet 1 instructs pasting the plan-mode prompt 'as the first message in a new Claude Code conversation', and Template M confirms it targets a fresh conversation, yet the Variant A mapping forces the verbatim tip 'stay in this conversation when running /optimus:commit' delivered in the crafting conversation — wrong deixis, and the condition ('implemented code in this conversation') is never true at delivery time. Rubric context #7 explicitly permits flagging a broken convention application. However, the proposed change's second option ('phrase the tip against the future conversation') would violate skill-handoff.md's requirement that variants be emitted verbatim ('never paraphrase'), so only the first option is sound as-is.
  - **Revised severity:** medium
  - **Revised fix (implement this one):** Remap this Step 9 case to Variant C (decidable at delivery time and consistent with the new-conversation instruction), and reword the condition accordingly; if future-conversation phrasing is genuinely wanted, add it as a variant in references/skill-handoff.md itself — individual skills may not paraphrase the verbatim variants.

#### F4. [medium/redundancy] skills/prompt/SKILL.md — Output format (~line 34), Step 8 (~lines 167-183), Important (~line 210); templates.md Template L (~lines 330, 373)

- **Quote:** "This wrapper applies to every delivered prompt block, including multi-prompt and Prompt Decompiler (Template L) outputs."
- **Problem:** The BEGIN/END-marker wrapping rule is stated five times across SKILL.md and templates.md (none test-enforced — validate.sh and expected-outputs.yaml contain no marker tokens), bloating context and creating five surfaces that can diverge on details like fence placement.
- **Fix:** Keep one canonical, complete statement in Step 8 and reduce the other four occurrences to a one-line pointer ("wrap per Step 8 markers"), including collapsing Template L's two wrapping paragraphs into one pointer.
- **Best practice:** BP1, BP13
- **Verifier:** ADJUSTED — Verified not test-enforced (no marker tokens in validate.sh or expected-outputs.yaml; the prompt skill's only fixture check is files_not_modified), so the finding is legitimate — but 'stated five times' overstates the pure duplication. Line 34 is already a forward-pointer to Step 8; line 210 adds the multi-prompt each-block-individually rule; templates.md line 330 specifies which decompiler blocks are pasteable vs commentary; line 373 adds label placement for split prompts. Only ~2 surfaces are genuinely redundant restatement; the rest carry site-specific mechanics that a bare 'wrap per Step 8' pointer would lose. The wrapper is also the skill's core deliverable format, where some repetition is defensible low-freedom guidance (BP2).
  - **Revised severity:** low
  - **Revised fix (implement this one):** Consolidate the full mechanics in Step 8 and convert the other surfaces to pointer-plus-site-specifics (e.g., Template L keeps the which-blocks-to-wrap list but drops the re-explanation of fence placement); do not reduce lines 210/330/373 to bare pointers.

#### F5. [medium/redundancy] skills/prompt/SKILL.md — Step 9, plan-mode bullet (~line 189)

- **Quote:** "treat plan mode as review-only and **do not approve** — approval executes immediately and bypasses TDD's Red-Green-Refactor discipline"
- **Problem:** The bullet restates nearly the entire plan-mode deliverable decision (default approve-in-conversation, the /optimus:tdd carve-out, the "Refined plan" append, the fresh-conversation handoff) from references/skill-handoff.md, then also instructs reading that same file "for the deliverable-typed decision" it just duplicated.
- **Fix:** Compress the bullet to the routing outcome plus the pointer (e.g., "plan-mode prompt → default approve-and-implement; if it will feed /optimus:tdd, review-only — apply the Plan mode section of $CLAUDE_PLUGIN_ROOT/references/skill-handoff.md"), keeping only prompt-skill-specific details inline.
- **Best practice:** BP1, BP7
- **Verifier:** CONFIRMED — The Step 9 plan-mode bullet (line 189) restates nearly the whole Plan-mode section of references/skill-handoff.md (default approve-in-conversation, the tdd carve-out, the 'Refined plan' append, the fresh-conversation handoff) and then points to that same file. The duplication buys nothing: Step 9 already mandates reading skill-handoff.md for the closing-tip variant wording, so the file is loaded in every run regardless. Cross-file content duplication is fair game per the rubric (not test-enforced — validate.sh's skill-handoff wiring tokens apply to skills/handoff/SKILL.md, not prompt), and this repo has documented history of exactly this copy-drift failure mode. The proposed compression correctly retains the routing outcome and the do-not-approve carve-out inline.

#### F6. [medium/ambiguity] skills/prompt/SKILL.md — Step 9, dynamic-workflow bullet (~line 190)
*Found by verifier (adversarial pass) — treat as confirmed*

- **Quote:** "A bare Template-N prompt is best for one-off fan-out (audit, migration, cross-checked research), not for implementing a tracked spec."
- **Problem:** The same bullet tells production-code fan-outs to pick /optimus:tdd or /optimus:workflow "rather than an ad-hoc Template-N prompt" while simultaneously naming migration — a production-code-editing fan-out — a best-for-Template-N case, and this fork is surfaced only AFTER the Template-N prompt has been delivered (Step 4 redirects only tracked specs), so the user can receive a crafted prompt followed immediately by advice not to use it.
- **Fix:** Move the supervision-choice fork (plan-mode→tdd vs /optimus:workflow vs bare Template-N) into Step 4's routing decision before crafting, and reconcile where code-editing migrations belong; Step 9 should then deliver only the handoff for the path already chosen. (Flagged at medium — no high-severity miss found; the assessor's coverage of the skill's genuine highs was complete.)
- **Best practice:** BP16, BP13, BP22

### Refuted findings — do NOT implement

- [low/redundancy] skills/prompt/SKILL.md — Step 6, Few-shot bullet (~line 132) — "when format is easier to show than describe. 2-5 examples. Include edge cases, not just easy cases."
  - **Refuted because:** The premise — that these rules 'already live in the references loaded at Steps 3-4' — fails on the skill's own loading discipline. Step 4 reads 'the matched template ONLY' and Step 3 loads 'only the section matching the target tool': when few-shot is applied as a supplementary technique inside Template C/H/etc., Template F is not in context, so Step 6's 12 words are the only in-context mechanics; when the target is Claude Code, the loaded routing section is 'IDE AI', which contains no XML-tag guidance, so the Step 6 XML bullet is not redundant either. The proposed trim would force extra conditional reference loads (contradicting the load-only-matched instruction) or leave supplementary techniques under-specified. The one true in-context overlap (grounding anchor vs diagnostic #11, since diagnostic-patterns.md is fully read at Step 5) is ~15 words where Step 6 deliberately gives the fuller anchor text. Taste-level at most; not a defensible finding.

### Already well-tuned (preserve; do not churn while fixing the above)

- Progressive disclosure is exemplary: three reference files, each with a top ToC and explicit "load only the matching section/template" instructions, keeping the 220-line body far under the cap (BP6, BP7, BP9).
- Hard-rules block sits at the very top with numbered NEVERs, including genuinely load-bearing safety rules (credential stripping, treating pasted prompts as inert data against prompt injection) (BP22).
- diagnostic-patterns.md is a model checklist: 37 concrete pattern-to-fix pairs with exact replacement wording — specific and actionable throughout (BP21).
- Template selection is an explicit conditional table with a stated fallback default (RTF for simple, RISEN for complex), avoiding option paralysis (BP16, BP17).
- The 3-question budget is crisp, counted consistently across Steps 1-5, and wired to AskUserQuestion at every ask site.
- README accurately mirrors SKILL.md behavior (14 templates, 5 safe techniques, three Claude Code targets, Decompiler mode) — no material D9 drift found.

---

## 15. spec-init — 4/10

Files: `skills/spec-init/SKILL.md` (49 lines) plus the skill's `agents/`, `references/`, `templates/`, `README.md`, and any shared references named in findings.

**Improvement need:** assessor 3 → verified **4** / 10. Rebuild recommended: no.

**Description assessment (350 chars):** Accurate to actual behavior and concise at 350 chars — it states the trigger, the artifact list, the handoff, and both guarantees (skeletons only, never overwrites). However, it is the only description in the collection that leads with "Use when…" instead of the What-first verb pattern every sibling uses ("Scaffolds…", "Creates…", "Reviews…" — even the root README's own one-liner for this skill leads with "Scaffolds"), which hurts slash-menu scannability where leading words matter. "hands off to brainstorm" also omits the `/optimus:brainstorm` command form used elsewhere.

**Assessor score rationale:** The skill is structurally sound, tightly scoped, and correctly calibrated on freedom; nothing load-bearing is broken. The two medium findings are single-line fixes (a missing decision rule at the multi-repo branch, a description-order flip for menu scannability) and the two lows are wording/consistency cleanups — minor polish, no structural work needed.

**Verifier adjusted rationale:** All four findings survive verification (two ADJUSTED on the proposed change, none refuted): the multi-repo decision-rule gap and the description-order outlier are genuine mediums, and the two lows are real but behavior-safe consistency defects. The assessor missed the most consequential issue: the workspace-root scaffolding option Step 1 offers produces a cascade that brainstorm and tdd — which resolve docs/product/ per-repo — silently never load, voiding the skill's core 'reads the cascade as steering' promise in a supported configuration; worse, the assessor's own proposed fix for finding 1 would steer Claude toward that undiscoverable location. That miss, plus the fragile echo-from-headers remedy in finding 3, nudges the score from 3 to 4. Still minor-polish territory: every fix is a one-to-two-sentence localized edit; the 49-line body, boundary contract, never-overwrite guarantee, and template architecture are sound, and no change touches test-enforced text (verified against validate.sh and expected-outputs.yaml).

### Findings to implement

#### F1. [medium/under-specification] skills/spec-init/SKILL.md — Step 1 — Pre-flight (line 20)

- **Quote:** "scaffold at the appropriate level (workspace root vs. a subproject) rather than blindly in the current folder"
- **Problem:** multi-repo-detection.md explicitly delegates policy to the consuming skill ("Each consuming skill applies its own policy after detection"), but spec-init supplies no decision rule for choosing workspace root vs. subproject, forcing the model to guess where product steering docs belong.
- **Fix:** Add a one-line policy, e.g. "when 2+ repos are detected, ask the user which product the cascade describes: scaffold at the workspace root if the product spans the repos, else inside the chosen repo."
- **Best practice:** BP21, BP16
- **Verifier:** ADJUSTED — The gap is real and medium: multi-repo-detection.md line 3 delegates policy to consumers, and every other consuming skill states one (e.g., brainstorm/tdd/workflow: 'run inside the repo the user is targeting; if ambiguous, ask') while spec-init leaves 'appropriate level' undefined. But the proposed rule is hazardous: brainstorm (SKILL.md lines 36-40) and tdd (lines 34-35) load docs/product/* relative to the repo they run in, so directing Claude to 'scaffold at the workspace root if the product spans the repos' would place the cascade where the downstream consumers never discover it.
  - **Revised severity:** medium
  - **Revised fix (implement this one):** Add a policy that matches downstream discovery: when 2+ repos are detected, ask which repo the product lives in and scaffold inside that repo by default; if the user insists on the workspace root, warn that /optimus:brainstorm and /optimus:tdd resolve docs/product/ from the repo they run in and will not auto-load a workspace-root cascade.

#### F2. [medium/weak-description] skills/spec-init/SKILL.md — frontmatter (line 2)

- **Quote:** "Use when starting a new project or product and you want a docs-first plan before writing code — scaffolds an empty, product-neutral spec-driven-development cascade"
- **Problem:** The only description in the collection that leads with the trigger instead of the What-first structure all siblings use, so in a truncating slash menu the WHAT arrives ~97 chars in; "hands off to brainstorm" also drops the /optimus: command form.
- **Fix:** Flip to What-first, matching the root README's one-liner: "Scaffolds an empty, product-neutral SDD cascade (product vision, MVP PRD, target tech-stack) for a human to fill, then hands off to /optimus:brainstorm. Use when starting a new project…"
- **Best practice:** BP4, BP13
- **Verifier:** CONFIRMED — Verified against all 21 skill frontmatters: spec-init is the only description leading with the trigger; every sibling leads What-first ('Scaffolds', 'Creates', 'Reviews', 'Guides'…), and the root README's own one-liner for this skill leads with 'Scaffolds'. Rubric context #1 makes leading words in a truncating slash menu the judging criterion, and BP4's [What]+[When] structure applies. validate.sh only checks that a description field exists, so the flip is mechanically safe. The /optimus:brainstorm command-form point also holds (jira, workflow, unit-test descriptions all use slash forms).

#### F3. [low/convention-conflict] skills/spec-init/SKILL.md — Step 4 — Report and hand off (line 44)

- **Quote:** "higher docs set long-term direction; the active build spec governs what to build right now — when they conflict…the active build spec wins"
- **Problem:** Restates the canonical precedence rule inline even though sdd-mapping.md's contract says "Keep those rules defined only here so the skills never duplicate (or drift from) them" and sanctions restatement only in the scaffolded doc headers — a third, unchecked copy that can drift.
- **Fix:** Replace the italic restatement with "echo the 'Altitude & precedence' note from the scaffolded doc headers" (they are always present at Step 4), or amend sdd-mapping.md to explicitly sanction this SKILL.md copy.
- **Best practice:** BP13, BP1
- **Verifier:** ADJUSTED — The problem is real and not test-enforced: sdd-mapping.md line 10 says 'Keep those rules defined only here so the skills never duplicate (or drift from) them' and line 40 sanctions restatement only in the scaffolded doc headers; no precedence token appears in validate.sh or expected-outputs.yaml, so this third copy is unchecked. But the assessor's primary fix is fragile: its claim that the doc headers 'are always present at Step 4' is false in the all-files-exist skip path (Step 2 -> Step 4), where docs may be human-authored without the Altitude & precedence header and cascade-templates.md was never read. The offered alternative — amend sdd-mapping.md to sanction the SKILL.md copy — is the sound remedy.
  - **Revised severity:** low
  - **Revised fix (implement this one):** Keep the inline restatement and amend sdd-mapping.md's sanctioned-restatement list (line 40) to include spec-init's Step 4, so the copy is contract-sanctioned like the doc headers rather than removed via the fragile echo-from-headers approach.

#### F4. [low/ambiguity] skills/spec-init/SKILL.md — Step 4 — Report and hand off (line 45)

- **Quote:** "This is **not** a continuation skill (the human fills the docs out-of-band and `/optimus:brainstorm` gathers its own context)"
- **Problem:** Per skill-handoff.md the tip variant depends on whether the NEXT skill is a continuation skill, so the leading clause attaches the classification to the wrong subject (spec-init itself); the parenthetical is correct but the sentence muddles the convention's criterion for future editors.
- **Fix:** Reword to "the recommended next skill (/optimus:brainstorm) is not a continuation skill, so use the default — Variant C."
- **Best practice:** BP13
- **Verifier:** CONFIRMED — Quote verbatim at line 45. skill-handoff.md ties variant selection to the recommended NEXT skill ('Override the default tip when the next skill is one of these'; Variant C: 'When the closing block recommends only non-continuation skills'), so the lead clause attaches the classification to the wrong subject — a skill's own status never determines the tip variant. Behavior is safe because the exact Variant C text is inlined, which is why low is the right severity; the misstated criterion is still a real propagation risk since SKILL.md files serve as the reference pattern future skills copy. The assessor's reword is correct and breaks nothing.

#### F5. [high/missing-guidance] skills/spec-init/SKILL.md — Step 1 Pre-flight (line 20) and Step 4 handoff block (line 47)
*Found by verifier (adversarial pass) — treat as confirmed*

- **Quote:** "run `/optimus:brainstorm` to design the first build — it reads the cascade as steering and writes the engineering spec to `docs/specs/`"
- **Problem:** Step 1 explicitly offers workspace-root scaffolding, but both downstream consumers resolve the cascade per-repo — brainstorm loads `docs/product/*` from the repo it runs in ('process within the repo the user is targeting') and tdd likewise — so a workspace-root cascade is silently never read as steering, breaking the skill's core handoff promise in a supported branch with no warning.
- **Fix:** In Step 1's multi-repo branch, default to scaffolding inside the target repo and add one sentence of failure-mode guidance: if the workspace root is chosen, tell the user that /optimus:brainstorm and /optimus:tdd resolve docs/product/ from the repo they run in, so they must run those skills from the workspace root or move the cascade.
- **Best practice:** BP25, BP16, BP23

### Already well-tuned (preserve; do not churn while fixing the above)

- 49-line body with a crisp 4-step workflow; the hard scope boundary sits at the top under an emphatic header and is re-enforced as a concrete negative-scope list at the point of action in Step 3 (BP22, BP10, BP1).
- Degrees of freedom are well calibrated: low freedom exactly where fragile (verbatim template writes, never-overwrite existence check, strict do-not-write list) and high freedom everywhere else (BP2, BP14).
- Progressive disclosure done right: the 164-line templates reference has a ToC, is loaded only at Step 3, and its emitted skeletons are fully tool- and product-neutral per project policy (BP7, BP9).
- Clean composability: explicit non-goals fence off /optimus:init territory (.claude/) and /optimus:brainstorm territory (docs/specs/), preventing sibling-skill overlap (BP25).
- No doc drift: skill README and root README both match SKILL.md behavior, including the never-overwrite guarantee and the brainstorm handoff (D9 clean).

---

## 16. refactor — 4/10

Files: `skills/refactor/SKILL.md` (306 lines) plus the skill's `agents/`, `references/`, `templates/`, `README.md`, and any shared references named in findings.

**Improvement need:** assessor 4 → verified **4** / 10. Rebuild recommended: no.

**Description assessment (704 chars):** Accurate, third-person, leads with strong scannable words ("Refactors existing code for guideline compliance and testability using 4 parallel analysis agents"), and includes the right negative trigger pointing to /optimus:refactor-deep. However, at 704 chars it is tuned like a model-triggering description the plugin doesn't need (disable-model-invocation): the two-goal framing is stated three separate times and the focus parentheticals repeat the "Use after/before" sentence, so a slash-menu reader sees a truncated wall of redundant text.

**Assessor score rationale:** The core workflow, agent prompts, validation discipline, and shared-reference reuse are solid and production-ready; nothing load-bearing is broken in the default interactive path. The needed work is a handful of targeted consistency fixes concentrated in the harness-mode path (detection ordering, an incomplete step enumeration, a pr_description contradiction between two references) plus one agent-file lens omission that contradicts the README's advertised dual-lens routing, and a trimmable description. All are line-level edits — minor polish bordering on moderate, hence 4.

**Verifier adjusted rationale:** Five of six findings survive as reported (one medium doc-drift in Agent 1's lens list, one medium pr_description contradiction verified end to end through cli.py and code-review's section headings, three low consistency/polish items); the harness-detection-ordering finding is real but downgrades to low because the dispatch prompt explicitly forbids AskUserQuestion and the full SKILL.md is in context, leaving only a placement-consistency gap versus code-review. I added one missed medium: harness-mode.md's skill-step-execution paragraph is code-review-slanted for refactor beyond the flagged pr_description sentence. Nothing high-severity exists — the interactive core path, agent boundaries, validation discipline, and handoff are verified sound (finding cap 15 matches shared-agent-constraints.md, deep-mode numbers match constants, no test-enforced duplication misread as removable). Net picture matches the assessor's: a cluster of line-level harness-path consistency fixes plus a description trim — minor polish at the top of the 3-4 band, so 4 stands.

### Findings to implement

#### F1. [medium/missing-guidance] skills/refactor/agents/guideline-reviewer.md — Dynamic Prompt Construction (line 18)

- **Quote:** "read `.claude/CLAUDE.md`, `.claude/docs/coding-guidelines.md`, and any existing `.claude/docs/{architecture,testing,styling}.md`"
- **Problem:** Both doc lists (single project and monorepo) omit `skill-writing-guidelines.md` and the markdown-routing rule that constraint-doc-loading.md (loaded in Step 3) mandates and README.md lines 6/144 explicitly advertise, so in skill-authoring projects Agent 1 judges markdown instruction files by coding-guidelines.md — exactly what the shared reference forbids ('never judge a SKILL.md by coding-guidelines.md criteria').
- **Fix:** Add `.claude/docs/skill-writing-guidelines.md` (if exists) to both doc lists plus one routing sentence mirroring constraint-doc-loading.md's compact form; alternatively soften the README's claim that this skill routes markdown files to that lens.
- **Best practice:** BP13, BP21
- **Verifier:** CONFIRMED — Quote verbatim (guideline-reviewer.md:18). constraint-doc-loading.md (loaded in Step 3) lists skill-writing-guidelines.md and forbids judging SKILL.md by coding-guidelines criteria (line 36); skill README lines 6/144/161 advertise the routing; and the plugin-level agents/code-simplifier.md — read by refactor's Agent 4 — fully inlines the dual-lens routing, so the one agent whose job is guideline lenses is the only one missing it. Real doc-drift plus cross-agent inconsistency; the proposed change (add the doc plus the compact routing sentence) is safe and breaks no repo mechanics.

#### F2. [medium/structure] skills/refactor/SKILL.md — Step 2: Inline Harness Mode Detection (lines 68–70)

- **Quote:** "skip the Step 1 scope resolution entirely"
- **Problem:** The instruction to skip Step 1 arrives one step after Step 1, whose no-scope path invokes AskUserQuestion — a sequential reader resolves (or prompts for) scope before learning it is pre-resolved, and sibling code-review avoids this by placing harness detection (its Step 2) before its interactive scope step (Step 3); orchestrator-loop-single.md lists 'fell into interactive mode and hung on AskUserQuestion' as a known parse-failure cause.
- **Fix:** Move harness-mode detection above the current Step 1 (matching code-review's ordering relative to interactive scope), or add a one-line gate at the top of Step 1: 'If the invocation prompt contains HARNESS_MODE_INLINE, read Step 2 first.'
- **Best practice:** BP22, BP16
- **Verifier:** ADJUSTED — The facts hold: quote verbatim (SKILL.md:70), code-review's harness gate (Step 2) precedes its interactive scope step while refactor's AskUserQuestion scope step precedes the gate, and orchestrator-loop-single.md:137 lists the AskUserQuestion hang as a known parse-failure cause. But three mitigations cap practical risk: the whole SKILL.md is in context at invocation, the orchestrator dispatch prompt explicitly says 'Do not use AskUserQuestion. Do not loop.' and directs executing the harness protocol (orchestrator-loop-single.md:36-53), and Step 2 sits near the top. Also the 'move harness detection above Step 1' option would ripple through at least six internal step-number cross-references (Step 2's 'Step 1 scope resolution', Step 3's 'chosen scope (Step 1)', 'Steps 3, 4, 5, and 6', 'Step 7', the final summary's 'from Step 1', README's workflow list). Downgrade to low and take only the one-line gate variant of the change.
  - **Revised severity:** low
  - **Revised fix (implement this one):** Add a one-line gate at the top of Step 1 ('If the invocation prompt contains HARNESS_MODE_INLINE, read Step 2 first — scope is pre-resolved'); do not renumber steps.

#### F3. [medium/ambiguity] skills/refactor/agents/context-blocks.md — Usage Notes note (line 9)

- **Quote:** "The PR/MR Context Block does not apply to refactor — this skill does not operate on PRs/MRs."
- **Problem:** harness-mode.md (which Step 2 tells the iteration to follow) says a non-null `config.pr_description` must be injected 'per Step 5 "PR/MR context injection"' and applied via the 'Step 6 intent signal' adjustment — sections that exist only in code-review's SKILL.md — while the harness CLI (`_init_deep` in cli.py) populates pr_description for refactor-deep runs too, leaving a refactor iteration with a dangling instruction that this note contradicts.
- **Fix:** Add an explicit override in refactor's SKILL.md Step 2 or context-blocks.md ('under harness mode, ignore config.pr_description — the PR/MR block does not apply to refactor'), or scope harness-mode.md's pr_description paragraph to code-review only.
- **Best practice:** BP13, BP16, BP8
- **Verifier:** CONFIRMED — Quote verbatim (context-blocks.md:9). Verified end to end: cli.py's deep-init populates config.pr_description unconditionally for any deep skill (lines 581-583, shared by refactor-deep), and harness-mode.md:46 unconditionally instructs injecting it 'per Step 5 "PR/MR context injection"' and the 'Step 6 "PR/MR description as intent signal"' adjustment — subsection headings that exist only in code-review's SKILL.md (lines 177 and 234); refactor's Steps 5/6 are Validate/Present. The contradicting note is only read at iterations 2+, so iteration 1 sees the dangling instruction with no counter-signal. Medium severity and both proposed remedies are safe.

#### F4. [low/ambiguity] skills/refactor/SKILL.md — Step 2 (line 70) and Step 8 (line 270)

- **Quote:** "Proceed through Steps 3, 4, 5, and 6 — skip the Step 7 user confirmation"
- **Problem:** The harness flow demonstrably continues into Step 8 (its harness override paragraph and JSON emission live there), so the Steps 3–6 enumeration is incomplete, and conversely Step 8's interactive list header carries the harness-only annotation '(persistent — fix failed)' that can never occur in a single interactive run.
- **Fix:** Change the enumeration to 'Steps 3–6, then apply fixes per Step 8's harness paragraph', and move the persistent-skip clause out of the interactive numbered list into the harness-mode paragraph.
- **Best practice:** BP13, BP21
- **Verifier:** CONFIRMED — Both quotes verbatim (SKILL.md:70 and :271). The harness flow does continue into Step 8 — its harness override paragraph and the JSON emission live there, and harness-mode.md's own rule is 'proceed through all of the skill's remaining numbered steps' — so the 3-6 enumeration is inconsistent with the reference it delegates to. The '(persistent — fix failed)' annotation can only originate from the harness progress file (harness-mode.md section 5), never in a single interactive run, so the clause is dead text in the interactive list. Not test-enforced: test/expected-outputs.yaml contains no refactor entries. Low severity is right; note the persistent clause could equally just be deleted since harness-mode.md section 6 already carries the skip rule.

#### F5. [low/weak-description] skills/refactor/SKILL.md — frontmatter description (line 2)

- **Quote:** "Two goals — align code with project guidelines AND make untestable code testable so /optimus:unit-test can safely increase coverage."
- **Problem:** The two-goal framing appears three times (lead sentence, 'Two goals' sentence, 'Use after/before' sentence) and the focus parentheticals repeat the when-to-use triggers, inflating the description to 704 chars for an audience that scans a truncating slash menu.
- **Fix:** Cut to one goal statement + when-to-use + focus keywords + the refactor-deep negative trigger (~350–450 chars); the body's intro already restates the removed detail.
- **Best practice:** BP4, BP1
- **Verifier:** CONFIRMED — Description is exactly 704 chars (measured). The two-goal framing genuinely appears three times (lead sentence, 'Two goals' sentence, 'Use after/before' sentence) and the focus parentheticals '(after unit-test flags untestable code)'/'(after init establishes rules)' restate the same triggers. Rubric context #1 makes menu scannability and conciseness the explicit criterion under disable-model-invocation, so this is not taste. Trimming to ~350-450 chars while keeping the what, when, focus keywords, and the refactor-deep negative trigger loses nothing the body's intro doesn't restate. Low severity appropriate.

#### F6. [low/other] skills/refactor/SKILL.md — Step 8 harness paragraph (line 275)

- **Quote:** "(see `references/harness-mode.md` §7)"
- **Problem:** This is the file's only reference not prefixed with `$CLAUDE_PLUGIN_ROOT/`, so it nominally resolves to a nonexistent `references/` dir in the user's project and silently escapes validate.sh's CLAUDE_PLUGIN_ROOT path-existence check.
- **Fix:** Write it as `$CLAUDE_PLUGIN_ROOT/references/harness-mode.md` §7 like every other reference in the file.
- **Best practice:** BP13
- **Verifier:** CONFIRMED — Verbatim at SKILL.md:275 and verified as the file's only reference without the $CLAUDE_PLUGIN_ROOT prefix (all other harness-mode.md mentions across the base skills are prefixed). validate.sh's resolution check (lines 140-153) greps only for $CLAUDE_PLUGIN_ROOT-prefixed paths, so the bare path escapes it; additionally the orchestrator dispatch prompt only instructs subagents to substitute the absolute plugin root where $CLAUDE_PLUGIN_ROOT is literally written, so this path gets no substitution either. Practical harm is small since harness-mode.md was already read in Step 2, which is why low — not higher — is the right severity. The fix is trivial and passes validate.sh (the target file exists).

#### F7. [medium/ambiguity] references/harness-mode.md — 'Skill-step execution under harness mode' (lines 40, 44), consumed by refactor SKILL.md Step 2
*Found by verifier (adversarial pass) — treat as confirmed*

- **Quote:** "Step 3 (or its skill-equivalent) must use the "no local changes → branch-diff" path automatically, regardless of the working tree's actual state."
- **Problem:** Beyond the pr_description slice the assessor flagged, this whole paragraph (branch-diff path, 'large-diff warning') and line 40's fallback 'the skill's Step 3 file discovery via git' are written in code-review's vocabulary — refactor's Step 3 is doc loading plus a directory scan with no branch-diff path, so every refactor-deep iteration reads step instructions that map to nothing in its own SKILL.md.
- **Fix:** Split the skill-step-execution guidance into skill-scoped bullets (code-review: branch-diff path, large-diff warning; refactor: use scope_files.current, and when empty derive areas per Step 3's harness note), so each consumer only gets instructions that exist in its steps.
- **Best practice:** BP13, BP16

### Already well-tuned (preserve; do not churn while fixing the above)

- Focus/argument parsing is precisely specified exactly where naive parsing would misfire (standalone unquoted tokens, quoted-scope safe examples, both-keywords tiebreak) — well-calibrated low freedom on a fragile step (BP2, BP15, BP21).
- Interactive Step 8's failure recovery — revert all, re-apply one at a time with a test run after each, warn when no test command exists — is a textbook feedback loop with plan-validate-execute discipline (BP11, BP20, BP23).
- Progressive disclosure is genuinely good: a 306-line body delegating prerequisites, doc loading, verification, and harness protocol to shared references, staying within the sanctioned two-level depth (BP6, BP7).
- The four agent prompt files have crisp mutual-exclusion boundaries and shared false-positive/cap constraints, preventing overlap and padding across the fan-out (BP16, BP25).
- Step 5 validation is concrete and evidence-driven (±30-line context check, intent check, cross-agent consensus, git change-intent downgrade with graceful skip on git failure).
- The closing handoff applies skill-handoff.md Variant B/C selection correctly, and the deep-mode tip's 'default 8 passes, hard cap 20' matches constants.py exactly — no numeric drift.

---

## 17. commit — 4/10

Files: `skills/commit/SKILL.md` (139 lines) plus the skill's `agents/`, `references/`, `templates/`, `README.md`, and any shared references named in findings.

**Improvement need:** assessor 4 → verified **4** / 10. Rebuild recommended: no.

**Description assessment (298 chars):** Strong: leads with action verbs for menu scanning, states what (stage/commit/optional push, conventional message, confirm gate), key capabilities (protected-branch feature-branch offer, multi-repo), and when ("Use when ready to commit work in one step") in 298 chars, third person, and it accurately matches SKILL.md behavior. Only gap: no negative trigger pointing message-only users to the highly confusable sibling /optimus:commit-message (the sibling's description does differentiate itself with "read-only, never commits").

**Assessor score rationale:** Fundamentally sound and well-calibrated skill; the three medium findings (secrets-vs-Include-all conflict, untracked-handling ordered after message generation/splitting, convoluted closing-tip variant selection) are each 1–3 line targeted edits on edge or wrap-up paths, and the preview-confirm gate limits their practical harm. No structural problems, no body-size or reference-depth issues — minor polish, not moderate rework.

**Verifier adjusted rationale:** All seven findings survive adversarial verification (6 CONFIRMED, 1 ADJUSTED only to fix a lossy proposed change while keeping medium severity), and no high-severity misses were found. The strongest missed-candidate — the split + protected-branch interaction where per-commit branch creation could stack branches or hit checkout collisions — refutes itself on close reading: the per-commit loop includes step 4's branch re-check, so after commit #1 switches to the new feature branch, later commits correctly see an unprotected branch. Remaining unfound issues (no explicit single-repo nothing-to-commit stop, AskUserQuestion option limits for \"Let me choose\") are low severity and mitigated by the step 5 preview/confirm gate, which also bounds the practical harm of the three mediums (secrets-vs-Include-all conflict, message generated before untracked decisions, closing-tip variant indirection). Each surviving fix is a 1–3 line targeted edit on edge or wrap-up paths in an otherwise well-calibrated, well-structured skill with no body-size, reference-depth, or test-enforcement conflicts — squarely 'minor polish' per rubric anchors, so the assessor's 4 stands.

### Findings to implement

#### F1. [medium/ambiguity] skills/commit/SKILL.md §6 Stage and Commit (~line 97) vs §3 Handle Untracked Files (~line 30)

- **Quote:** "Never stage files that look like secrets."
- **Problem:** Step 6's absolute prohibition conflicts with step 3, where the user can pick "Include all — stage all untracked files" after being warned about secret-looking files, leaving a fresh Claude to guess whether explicit user consent overrides the "Never".
- **Fix:** Reconcile the two: in step 3, exclude secret-looking files from "Include all" and require individual confirmation for each of them; step 6 then adds "unless the user individually confirmed them in step 3".
- **Best practice:** BP21, BP13
- **Verifier:** CONFIRMED — Verbatim at SKILL.md line 97. Step 3 (line 30) offers "Include all — stage all untracked files" after only a warning, so a user who explicitly includes a flagged .env/.sqlite collides with step 6's absolute "Never" at execution time — a genuine BP13/BP21 conflict, not a redundant safety line. Neither string is enforced by scripts/validate.sh or test/expected-outputs.yaml, and the proposed reconciliation preserves the safety intent (per-file confirmation) rather than weakening it.

#### F2. [medium/structure] skills/commit/SKILL.md §2 (~line 20) and §3 ordering

- **Quote:** "If splitting, process each commit separately through steps 3–7."
- **Problem:** The commit message and split file-groups are finalized in step 2 before the untracked include/exclude decision in step 3 (gather-changes captures only untracked filenames, not contents), and the split path re-runs step 3's untracked questionnaire once per commit even though the split proposal already assigned files per commit.
- **Fix:** Move untracked-file handling before message generation (swap steps 2 and 3, instructing Claude to read included untracked files' contents for the analysis), and route split commits through steps 4–7 only.
- **Best practice:** BP10, BP16
- **Verifier:** CONFIRMED — Verbatim at line 20. gather-changes.md collects untracked files via `git status --short` only (names, no contents), and nothing instructs regenerating the message or split groups after step 3's include/exclude decision, so step 2's outputs genuinely precede the data they depend on. The per-commit re-run of step 3's questionnaire is redundant with the split proposal's per-commit file lists (conventional-commit-format.md: "For each proposed commit, specify: the commit message and the list of files to stage"). No validate.sh/expected-outputs.yaml token pins the current ordering. The proposed change correctly keeps step 4 in the per-commit loop, which is what makes the protected-branch split path self-heal after the first commit switches branches.

#### F3. [medium/ambiguity] skills/commit/SKILL.md §8 Report and Next Step (~lines 133–139)

- **Quote:** "When `/optimus:pr` is the recommended next step (either branch above), emit the closing tip"
- **Problem:** The closing-tip variant selection is split across two paragraphs and hinges on parsing "(either branch above)" — the feature-branch case (line 133) never says it "recommends" /optimus:pr, so a fresh Claude can plausibly emit no tip there, or the wrong Variant C (which tells the user to start a fresh conversation, stripping exactly the context the continuation skill /optimus:pr needs).
- **Fix:** Inline the variant choice in each branch: append "then emit Variant A with /optimus:pr" directly to the feature-branch sentence and to the "If a pull request is needed" bullet, deleting the trailing catch-all paragraph.
- **Best practice:** BP16, BP22
- **Verifier:** ADJUSTED — Verbatim at line 139 and the problem is real: "(either branch above)" has an ambiguous referent — the visually adjacent branching structure is the two bullets at lines 136–137, and line 137 already assigns "Variant C (default)", whose "(default)" label invites applying it to the feature-branch case, contradicting skill-handoff.md's continuation-skill rule for /optimus:pr ("Drift is the failure mode this section exists to prevent"). Medium severity stands. But the proposed change is lossy: "emit Variant A with /optimus:pr" drops the placeholder assignment `<non-continuation-examples>` = `/optimus:code-review` that Variant A's verbatim template requires.
  - **Revised severity:** medium
  - **Revised fix (implement this one):** Inline the variant choice in each branch as proposed, but retain the full substitution spec in each inline mention — e.g. append "then emit Variant A per $CLAUDE_PLUGIN_ROOT/references/skill-handoff.md with `<continuation-skill(s)>` = `/optimus:pr` and `<non-continuation-examples>` = `/optimus:code-review`" to both the feature-branch sentence and the "If a pull request is needed" bullet, then delete the trailing catch-all paragraph.

#### F4. [low/missing-guidance] skills/commit/SKILL.md §4 Branch and Push-Safety Check (~lines 49–51)

- **Quote:** "If the hook file does not exist at any checked location, assume the branch is safe for all operations."
- **Problem:** Only the file-missing case is covered — if the hook exists but no PROTECTED_BRANCHES array can be extracted (customized or drifted hook), the skill doesn't say whether to fail open or closed.
- **Fix:** Add one line: "If the file exists but no PROTECTED_BRANCHES array can be extracted, treat the branch as unprotected and note this in the step 5 preview."
- **Best practice:** BP23, BP21
- **Verifier:** CONFIRMED — Verbatim at line 51. Only the file-missing case is specified; extraction failure on a customized hook is plausible (the template itself says "Customize this list to match your project's protected branches"). The proposed fail-open-with-disclosure is safe because the hook itself still denies protected-branch git operations at PreToolUse (verified in .claude/hooks/restrict-paths.sh lines 276–290), so the skill's detection is UX-level, not the enforcement layer. Low severity is right.

#### F5. [low/ambiguity] skills/commit/SKILL.md §5 Preview and Confirm (~line 59) vs §2 (~line 22)

- **Quote:** "Present a summary for each repo (in multi-repo, use a heading per repo — e.g., `## repo-name`)"
- **Problem:** Step 5's combined "summary for each repo" phrasing conflicts with step 2's mandate to "process each repo with changes through steps 2–7 independently", so it's unclear whether the preview/AskUserQuestion confirmation happens once batched or per repo.
- **Fix:** State the model explicitly in step 5, e.g. "(in multi-repo, steps 2–7 run per repo, so each repo gets its own preview and confirmation; label it with a `## repo-name` heading)".
- **Best practice:** BP10, BP21
- **Verifier:** CONFIRMED — Verbatim at line 59. "Summary for each repo" with per-repo headings reads as one batched preview, while step 2 (line 22) mandates processing "each repo with changes through steps 2–7 independently" — implying per-repo confirmation. Step 8 explicitly says "combined summary across all repos", showing the author distinguishes batched vs per-repo elsewhere but step 5 does not, so a fresh Claude could legitimately do either. Real BP10/BP21 ambiguity; low severity appropriate.

#### F6. [low/weak-description] skills/commit/SKILL.md frontmatter (line 2)

- **Quote:** "Use when ready to commit work in one step."
- **Problem:** No negative trigger distinguishing this from the highly confusable sibling /optimus:commit-message, whose read-only preview role a menu-scanning user could want instead.
- **Fix:** Append "For a message-only suggestion without committing, use /optimus:commit-message." to the description (still well under length limits at ~370 chars).
- **Best practice:** BP4
- **Verifier:** CONFIRMED — Verbatim at end of the description (line 2). Rubric D1 explicitly names commit vs commit-message as a confusable sibling pair warranting negative triggers. Verified the sibling's description self-differentiates ("read-only, never commits") while commit's does not point back. The appended sentence keeps the description well under 1024 chars and scannable; breaks no frontmatter mechanics.

#### F7. [low/doc-drift] skills/commit/README.md §Skill Structure (~line 94)

- **Quote:** "Branch naming convention (shared with TDD)"
- **Problem:** Stale sharing note — branch-naming.md's own header says it is consumed by the branch, commit, tdd, and worktree skills, not just TDD; the table also omits the skill-handoff.md shared reference that step 8 depends on.
- **Fix:** Update the row to "(shared with branch, tdd, worktree)" and add a row for references/skill-handoff.md (closing-tip wording).
- **Best practice:** BP13; repo context #3 (README↔SKILL drift)
- **Verifier:** CONFIRMED — Verbatim at README.md line 94. branch-naming.md line 3 states it is "Consumed by `branch`, `commit`, `tdd`, and `worktree` skills", so the README row is stale. The Skill Structure table also lists the other shared references (conventional-commit-format, multi-repo-detection) but omits references/skill-handoff.md, which step 8 loads; the README does link skill-handoff.md in its prose intro, which supports keeping this at low severity as doc-drift (D9), not a functional gap. validate.sh does not check README structure tables, so the fix is safe.

### Already well-tuned (preserve; do not churn while fixing the above)

- Degrees-of-freedom calibration is excellent: exact low-freedom commands only where fragile (heredoc for multi-line commit messages, git add specificity, upstream-less push fallback), high-freedom prose for analysis steps (BP2).
- Clean progressive disclosure: 139-line body delegating to four small, focused shared references (gather-changes, conventional-commit-format, branch-naming, skill-handoff), staying within the repo's accepted two-level chain (BP6–BP8).
- Strong plan-validate-execute discipline for a repo-mutating skill: full preview (branch, complete message, file list) with AskUserQuestion confirmation before any mutation, plus explicit stop-on-failure rules for branch creation, commit, and push (BP20, BP23).
- Protected-branch conditional workflow is handled explicitly with concrete replacement options rather than vague guidance (BP16), and the feature-branch name derivation from the already-generated commit type avoids redundant inference.
- README is rich and accurate on the main flow, including the commit vs commit-message vs pr comparison tables and the continuation-skill conversation discipline matching references/skill-handoff.md.

---

## 18. worktree — 4/10

Files: `skills/worktree/SKILL.md` (102 lines) plus the skill's `agents/`, `references/`, `templates/`, `README.md`, and any shared references named in findings.

**Improvement need:** assessor 4 → verified **4** / 10. Rebuild recommended: no.

**Description assessment (299 chars):** Strong: 299 chars, third person, leads with WHAT ("Creates a git worktree for isolated parallel development"), states WHEN ("Use when you need to work on something else without disturbing current work"), and names the key capabilities (project setup, test baseline, multi-repo aware, parallel Claude Code sessions). Accurate against actual behavior and scans well in a slash menu. Only optional polish would be a negative trigger toward /optimus:branch ("just need a branch"), which the README covers but the description does not.

**Assessor score rationale:** Core workflow, description, structure, and reference architecture are sound and the README matches behavior, so no structural work is needed. The two medium findings are real but small edits: the shared reference carries caller policy that contradicts the skill's own stop rule (also affecting tdd), and the headline 'test baseline' feature has no failing-baseline branch. Remaining findings are low-severity wording/coverage gaps. A handful of targeted line edits across SKILL.md and worktree-setup.md fully addresses everything — minor polish, upper end.

**Verifier adjusted rationale:** Five of six findings survive as reported and one is adjusted only in framing (the SKILL.md failure line composes with, rather than contradicts, the reference's 'return to the caller' — the residual issue is partial restatement risking a skipped branch cleanup). Verified against validate.sh and test/expected-outputs.yaml: no worktree guard text, report template, or reference content is test-enforced, so all proposed changes are mechanically safe, including making the shared guard detection-only (tdd already defines its own policy). One real medium miss: the report claims the main workspace is 'unchanged' while the setup procedure modifies and stages .gitignore there, leaving an unannounced staged change. Net picture matches the assessor's: two (now three) medium policy/coverage gaps plus low wording nits, all fixable with a handful of line edits in SKILL.md and worktree-setup.md; description, structure, reference architecture, and README alignment are sound. Score stays 4 — upper end of minor polish.

### Findings to implement

#### F1. [medium/ambiguity] skills/worktree/references/worktree-setup.md — 'Worktree Detection Guard', lines 17-21

- **Quote:** "The caller should proceed with the standard branch workflow (no worktree)"
- **Problem:** The shared guard embeds caller policy (a canned 'Skipping worktree creation — working directly on the current branch' message plus continue-on-current-branch behavior) that directly contradicts SKILL.md Step 2's 'Then stop — do not create recursive worktrees', and neither consumer (worktree or tdd) actually uses it — both override with their own message and outcome.
- **Fix:** Strip caller policy from the guard: make it detection-only ('report whether pwd is inside a linked worktree; the calling skill defines the user message and next action'), or explicitly label the message/continuation as tdd-specific.
- **Best practice:** BP13, BP17
- **Verifier:** CONFIRMED — Quote verbatim (worktree-setup.md line 20). Both consumers override the guard's embedded policy: worktree SKILL.md Step 2 substitutes its own user message and an emphatic 'Then stop — do not create recursive worktrees', and tdd-worktree-orchestration.md line 9 says 'skip this subsection entirely and proceed to Decompose into behaviors' without relaying the guard's message. The canned 'proceed with the standard branch workflow' directly contradicts worktree's stop rule. Checked scripts/validate.sh wiring tokens and test/expected-outputs.yaml — no worktree guard text is test-enforced, so the detection-only change is safe for repo mechanics. Medium is right: SKILL.md's emphatic stop likely wins in practice, but the shared reference is loaded in the same context and states the opposite continuation.

#### F2. [medium/under-specification] skills/worktree/SKILL.md Step 5 template line 78 + references/worktree-setup.md §7 'Verify test baseline' (line 78)

- **Quote:** "Tests: passing / no test command detected"
- **Problem:** Neither file says what to do when the baseline test run FAILS — a common real event — and the report template cannot even express that outcome, so the model must guess whether to hide it, stop, or remove the worktree.
- **Fix:** Add a third outcome to the report line (e.g., 'failing (pre-existing — N failures)') and one sentence of policy in worktree-setup.md §7: a failing baseline is pre-existing, does not block worktree creation, and must be reported so it isn't later attributed to new work.
- **Best practice:** BP23, BP21
- **Verifier:** CONFIRMED — Quote verbatim (SKILL.md line 78); worktree-setup.md §7 says only 'confirm tests pass' or note 'no test command detected' — no branch for a failing baseline, and the two-outcome report line cannot express it. A pre-existing red suite is a common real event and this is the skill's headline 'test baseline' feature, so the model must guess between hiding, stopping, or aborting. Proposed change is small, sound, and unpinned by tests. Medium confirmed.

#### F3. [low/ambiguity] skills/worktree/SKILL.md — '1. Multi-repo Detection', line 16

- **Quote:** "Run the git commands below inside each child repo"
- **Problem:** 'Each child repo' implies running the workflow in all repos, but the next two bullets select a single target repo and the skill creates exactly one worktree — a fresh model could run detection/branch commands across every repo.
- **Fix:** Reword to 'Run the git commands below inside the target child repo (the workspace root has no .git/)'. (The same phrase is copy-pasted in branch/commit/code-review, where 'each' is sometimes correct — fix per-skill.)
- **Best practice:** BP21, BP13
- **Verifier:** CONFIRMED — Quote verbatim (SKILL.md line 16). Verified against siblings: in branch SKILL.md 'each' is correct (per-repo git status scan precedes target selection) and in commit/code-review the workflow genuinely spans all repos, but worktree has no per-repo scanning step — the next bullets select a single target repo and exactly one worktree is created, so 'each' is a copy-paste scope mismatch that could send a fresh model running branch commands across every repo. Low severity is right; the per-skill fix is correct.

#### F4. [low/ambiguity] skills/worktree/SKILL.md — '4. Create Worktree', line 68

- **Quote:** "If worktree creation fails, report the error with diagnostic information and stop."
- **Problem:** This restates failure handling that worktree-setup.md §8 already owns, with a divergent outcome ('stop' vs the reference's orphaned-branch cleanup + branch-workflow fallback suggestion + 'return to the caller'), so the model may skip the cleanup or follow the wrong policy.
- **Fix:** Replace the SKILL.md line with a pointer ('on failure, follow the reference's Failure handling; for this skill, "return to the caller" means stop after reporting'), or move the worktree-skill outcome into the reference's caller notes.
- **Best practice:** BP13, BP23
- **Verifier:** ADJUSTED — Quote verbatim (SKILL.md line 68), but the 'divergent outcome' framing mischaracterizes the reference: §8 explicitly ends with 'Return to the caller so it can decide how to proceed', so SKILL.md's 'stop' IS the anticipated caller policy, not a contradiction. The real, smaller issue is partial restatement — the SKILL.md line repeats 'report the error with diagnostic information' from §8 without the orphaned-branch cleanup or fallback suggestion, so a model may treat it as the complete failure policy and skip the cleanup.
  - **Revised severity:** low
  - **Revised fix (implement this one):** Replace the SKILL.md line with a pointer that composes rather than restates: 'On failure, follow the reference's Failure handling (§8) — cleanup and diagnostics — then stop.'

#### F5. [low/under-specification] skills/worktree/SKILL.md — '3. Gather Context and Branch Name', lines 44-47

- **Quote:** "**New feature** — "Implement a new capability""
- **Problem:** The AskUserQuestion fallback options capture only a category, not a description, so a user picking 'New feature' or 'Bug fix' leaves the slug undetermined and the model must invent a name or ask again without being told to.
- **Fix:** Either instruct a follow-up ('after a category answer, ask for a few words describing the task before generating the slug') or reframe the question so every answer path yields usable description text.
- **Best practice:** BP21, BP16
- **Verifier:** CONFIRMED — Quote verbatim (SKILL.md line 45). Two of the three AskUserQuestion options return only a category label, yet the next instruction is 'generate the slug from the description' — with description = 'Implement a new capability' the model either invents a name or produces a garbage slug like feat/implement-new-capability, and nothing tells it to follow up. Genuine BP16/BP21 gap; low severity appropriate since a strong model would ask naturally.

#### F6. [low/missing-guidance] skills/worktree/SKILL.md — '5. Report and Next Steps' template, lines 75-91

- **Quote:** "**Claude Code CLI**: `cd .worktrees/<worktree-dir> && claude`"
- **Problem:** In the multi-repo case (Step 1) the worktree lives at <repo>/.worktrees/<worktree-dir>, but the report template hardcodes repo-relative paths that are wrong from the workspace root where the user is sitting.
- **Fix:** Add one line after the template: 'In a multi-repo workspace, prefix all paths with the target repo directory (e.g., cd <repo>/.worktrees/<worktree-dir>)'.
- **Best practice:** BP14, BP21
- **Verifier:** CONFIRMED — Quote verbatim (SKILL.md line 87). Step 1 establishes that in a multi-repo workspace all git operations target a child repo, so the worktree lands at <repo>/.worktrees/<worktree-dir>, but every path in the Step 5 template (working directory, code command, cd, cleanup) is repo-relative and wrong from the workspace root where the user sits. The template is presented as a bare code block with no adapt note. One-line fix is safe and cheap. Low confirmed.

#### F7. [medium/doc-drift] skills/worktree/SKILL.md — Step 5 report template, line 77 (with references/worktree-setup.md §3, line 47)
*Found by verifier (adversarial pass) — treat as confirmed*

- **Quote:** "Main workspace: `<original-branch>` (unchanged)"
- **Problem:** Setup §3 appends `.worktrees/` to .gitignore AND stages it (`git add .gitignore`) in the main workspace, so 'unchanged'/'stays untouched' is false and a staged, uncommitted change silently rides into the user's next commit with no notice anywhere in the report.
- **Fix:** Add a conditional report line when §3 modified .gitignore — e.g. '.gitignore updated to ignore `.worktrees/` (staged, not committed)' — or stop staging in §3 (append only) and mention the edit; align the 'stays untouched' intro wording either way.
- **Best practice:** BP14, BP23

### Already well-tuned (preserve; do not churn while fixing the above)

- Description is a model for the plugin: 299 chars, what + when + key capabilities, accurate, and menu-scannable.
- Progressive disclosure is right-sized: a 102-line body delegating setup mechanics, branch naming, and multi-repo detection to single-level shared references — no chains beyond the allowed depth, no inline bloat.
- Degrees of freedom are well calibrated: exact commands only where fragile (git branch without checkout, show-ref collision probe, git worktree add), free-form guidance for project-setup detection.
- The recursive-worktree guard sits early (Step 2) with an emphatic 'Then stop' — correct placement for the one must-not-skip rule.
- README is thorough and consistent with SKILL.md (messages and example outputs match the templates; the When-NOT-to-Use tables cleanly disambiguate the confusable branch/tdd siblings) — no material drift found.

---

## 19. brainstorm — 3.5/10

Files: `skills/brainstorm/SKILL.md` (258 lines) plus the skill's `agents/`, `references/`, `templates/`, `README.md`, and any shared references named in findings.

**Improvement need:** assessor 3 → verified **3.5** / 10. Rebuild recommended: no.

**Description assessment (473 chars):** Strong: third person, leads with what ("Guides structured design brainstorming"), states when ("Use before implementation"), and names the concrete output and downstream consumers — accurate against actual behavior at 473 chars. The final sentence (Scenarios section consumed by /optimus:tdd) is body-level detail that lengthens the menu entry, but it is accurate and helps a human decide whether acceptance-criteria work belongs here; not worth a finding.

**Assessor score rationale:** The core flow (Steps 1–6 and the small/medium code handoffs) is accurate, well-gated, and correctly layered, and the description is strong. The real defects cluster on the secondary prose-deliverable branch of Step 7 — a convention conflict with skill-handoff.md plus an unresolvable actor ambiguity — with the remainder being small consistency and boundary fixes. Targeted edits to Step 7 suffice; nothing structural is broken.

**Verifier adjusted rationale:** All seven findings survived adversarial verification — every quote is verbatim, none is test-enforced duplication (validate.sh only pins the spec-format/scenario-style tokens, which no proposed change touches), and each proposed change is mechanically safe. The two mediums are real: the prose branch contradicts the canonical skill-handoff convention the skill itself cites as authoritative, and the /optimus:commit closing-tip instruction has an unresolvable actor/conversation ambiguity under Variant A's verbatim-wording rule. The five lows are genuine but minor consistency and boundary fixes. I add one missed medium (no existing-file check before the Step 5 spec write, risking silent loss of a Refined plan). No high-severity misses: description is accurate, the Hard Gate is top-placed, README and root docs are in sync, and the primary code-path handoffs are clean. Everything clusters on Step 7's secondary prose branch plus small consistency edits — targeted fixes, nothing structural — so the need sits at the upper end of 'minor polish': 3.5, a hair above the assessor's 3 to reflect that nothing was refuted and one additional medium exists.

### Findings to implement

#### F1. [medium/convention-conflict] skills/brainstorm/SKILL.md — Step 7, prose routing (~line 184) through Medium-to-large branch (~lines 192–256)

- **Quote:** "use the Medium-to-large branch below but follow the "Prose deliverable" note on the execution prompt"
- **Problem:** Prose deliverables are routed through the /optimus:tdd review-only carve-out (unmodified plan prompt ending "I will start a fresh conversation to run /optimus:tdd", plus the "Do not approve the plan" instruction justified by Red-Green-Refactor), even though the note says tdd "does not apply" and the cited shared convention (references/skill-handoff.md "Default — a prose deliverable... approve the plan to implement in the same conversation... no 'Refined plan' doc, no fresh conversation") prescribes the opposite for prose.
- **Fix:** Either route prose deliverables through skill-handoff's default flow (iterate in plan mode, approve, implement in the same conversation), or — if the three-conversation flow is intentional — instruct Claude to adapt the plan-mode prompt's closing line and the step-2 "Do not approve" rationale for prose and document the divergence.
- **Best practice:** BP16, BP21, BP13
- **Verifier:** CONFIRMED — Quote verbatim at SKILL.md line 184. skill-handoff.md line 71 explicitly assigns prose deliverables the approve-in-same-conversation default (no Refined plan, no fresh conversation) and line 78 limits the review-only carve-out to brainstorm's 'code paths', yet the prose route emits the unmodified plan prompt closing 'I will start a fresh conversation to run /optimus:tdd' (line 227) and the 'Do not approve' RGR rationale (line 236) while line 256 says tdd does not apply. Not enforced by validate.sh or expected-outputs.yaml, so not deliberate test-backed duplication. Real convention conflict plus internal contradiction on a secondary path — medium is right.

#### F2. [medium/ambiguity] skills/brainstorm/SKILL.md — Step 7, "Prose deliverable" note (~line 256)

- **Quote:** "After `<deliverable-path>` is produced, recommend `/optimus:commit` to commit the artifact and tell the user the closing tip"
- **Problem:** The deliverable is produced later by a different Claude in a fresh execution conversation, so the brainstorm Claude cannot act "after <deliverable-path> is produced" — and if it emits Variant A's verbatim "stay in this conversation when running /optimus:commit" in its own closing, the tip points at the wrong conversation.
- **Fix:** State explicitly that the emitted execution prompt must itself end with an instruction for the executing Claude to recommend /optimus:commit with the Variant A tip after producing the deliverable.
- **Best practice:** BP21
- **Verifier:** CONFIRMED — Quote verbatim at line 256. The deliverable is produced two conversations later by a different Claude, so the imperative is temporally impossible for the brainstorm Claude; and Variant A's paraphrase-forbidden wording 'stay in this conversation' (skill-handoff.md line 39) misleads if spoken in the brainstorm conversation. The proposed fix (embed the instruction in the emitted execution prompt) is mechanically sound — pasted prompts already reference /optimus: commands (the default execution prompt invokes /optimus:tdd), and the tool-agnostic rule covers artifacts written into user projects, not conversation prompts.

#### F3. [low/ambiguity] skills/brainstorm/SKILL.md — Step 4 section list (~lines 127–136)

- **Quote:** "Cover each section as applicable — omit sections that don't apply to the task:"
- **Problem:** The Step 4 list omits Context (and Open Questions), yet spec-format.md includes a Context section and Step 7's plan-mode prompt says "Synthesize from the spec's Context and Approach sections" — so Context is authored at write time without ever being presented for the user's design approval.
- **Fix:** Add Context (and optionally Open Questions) to the Step 4 section list so the reviewed design matches the template the spec is filled from.
- **Best practice:** BP13, BP14
- **Verifier:** CONFIRMED — Quote verbatim at line 127. The Step 4 list (lines 129–136) omits Context and Open Questions while spec-format.md includes both, Step 5 says to fill the template with 'the approved design content', and the Step 7 plan prompt (line 202) synthesizes from 'the spec's Context and Approach sections' — so Context is load-bearing content authored without appearing in the reviewed design. Real minor consistency gap under BP13/BP14; the change is harmless (no validate.sh token pins the Step 4 list). Low severity accurate.

#### F4. [low/missing-guidance] skills/brainstorm/SKILL.md — Step 7, non-implementation branches (~lines 181–182)

- **Quote:** "Recommend running `/optimus:refactor` to restructure the code."
- **Problem:** By Step 7 an approved spec has already been written, but the refactor and test-only handoffs never mention it and neither /optimus:refactor nor /optimus:unit-test reads docs/specs/, so the just-approved design is silently dropped at the handoff.
- **Fix:** Have the handoff text include the spec path and tell the user to feed its scope/decisions into the next skill's invocation (e.g., as the [scope] argument), or acknowledge explicitly that the spec serves only as a design record on these paths.
- **Best practice:** BP21, BP25
- **Verifier:** CONFIRMED — Quote verbatim at line 181. Verified by grep: neither skills/refactor/SKILL.md nor skills/unit-test/SKILL.md references docs/specs, and both gather context from scratch (guidelines docs, own analysis) — the just-approved spec is never surfaced in the handoff text, so the design is silently dropped. The [scope] example in the change works because refactor parses non-keyword text as free-form scope instructions. Low is fair (users are steered away from brainstorming pure refactors by the README, making this an edge path).

#### F5. [low/ambiguity] skills/brainstorm/SKILL.md — Step 7 branch headings (~lines 186, 190)

- **Quote:** "### Small (1–2 components, <5 behaviors implied)"
- **Problem:** A spec with 1–2 components but 5+ implied behaviors (and simple interfaces) matches neither branch condition, forcing a guess between materially different handoffs (direct /optimus:tdd vs. plan-mode prompt pair).
- **Fix:** Make the branches exhaustive — e.g., define Small and end Medium-to-large with "otherwise", or drop the behaviors clause from Small.
- **Best practice:** BP16
- **Verifier:** CONFIRMED — Quote verbatim at line 186. The two branch predicates genuinely leave a gap (2 components + 5+ behaviors + simple interfaces matches neither '1–2 components, <5 behaviors' nor '3+ components or complex interfaces'). Borderline pedantic — 'assess complexity from the Components table' plus the branch names give Claude latitude, and it would almost certainly route the gap case to Medium-to-large — but the numerals invite predicate-reading and the fix (end Medium-to-large with 'otherwise') is trivial and safe. Stands at low.

#### F6. [low/ambiguity] skills/brainstorm/SKILL.md — Step 7 substitution note (~line 231) vs. plan prompt (~line 207)

- **Quote:** "substitute `<spec-path>` with the actual path from Step 5 so each pasted block is self-contained"
- **Problem:** The same value is named `<file-path>` in Step 6, the Small branch, and the plan prompt's Starting Hints, but `<spec-path>` in the prompt closings and execution prompt — and the explicit substitution instruction names only `<spec-path>`, leaving `<file-path>` occurrences technically uncovered.
- **Fix:** Use one placeholder name for the spec path across Steps 6–7 and have the substitution note cover it.
- **Best practice:** BP13
- **Verifier:** CONFIRMED — Quote verbatim at line 231. Verified: <file-path> appears at lines 172 (Step 6), 188 (Small), 192 (workflow alternative), and 207 (plan prompt Starting Hints) while <spec-path> appears at 227, 236, 244–252 — two placeholder names for one value, with the explicit substitution instruction covering only one of them (and only the two prompt blocks, not the intervening user blockquote at line 236). Classic BP13 defect; unification breaks nothing test-enforced.

#### F7. [low/doc-drift] references/sdd-mapping.md — Phase mapping table (~line 65)

- **Quote:** "`/optimus:brainstorm` Step 4 writes `docs/specs/<slug>.md`"
- **Problem:** Brainstorm writes the spec in Step 5 ("Write the Spec"); Step 4 is the design conversation — the shared contract doc miscites the skill's step numbering.
- **Fix:** Update to Step 5, or drop the step number ("brainstorm writes docs/specs/<slug>.md") so future renumbering can't re-drift it.
- **Best practice:** BP13
- **Verifier:** CONFIRMED — Quote verbatim at references/sdd-mapping.md line 65. Brainstorm's Step 4 is 'Design' (conversation only); Step 5 'Write the Spec' writes the file — the shared contract doc, which brainstorm's Step 1 points to, miscites the step number. validate.sh has no token check on sdd-mapping, so the fix (drop or correct the step number) is safe. Low-impact documentation drift, correctly rated.

#### F8. [medium/missing-guidance] skills/brainstorm/SKILL.md — Step 5 'Write the file' (~lines 149–152)
*Found by verifier (adversarial pass) — treat as confirmed*

- **Quote:** "Create the `docs/specs/` directory if it doesn't exist"
- **Problem:** Step 5 writes docs/specs/YYYY-MM-DD-<topic-slug>.md with no check for a pre-existing file, so a same-day re-brainstorm of the same topic derives the identical path and silently overwrites the earlier spec — including any appended 'Refined plan' section that skill-handoff.md line 75 says append-not-overwrite exists to preserve.
- **Fix:** Before writing, check whether the target file already exists; if it does, ask the user (AskUserQuestion) whether to overwrite it or write to a suffixed filename, preserving any existing 'Refined plan' section on overwrite.
- **Best practice:** BP23, BP20

### Already well-tuned (preserve; do not churn while fixing the above)

- The Hard Gate (no implementation before an approved spec) sits at the top under an emphatic header — the skill's core safety rule is unmissable (BP22).
- Progressive disclosure is right-sized: a 258-line body defers the spec template and Given/When/Then discipline to two focused references loaded exactly when Steps 4–5 need them, and cross-skill contracts to shared references (BP6, BP7).
- JIRA context detection is a model conditional workflow: explicit key-match / most-recent-file / no-directory branches, concrete fallback messages, and a 7-day staleness note (BP16, BP23).
- Degrees of freedom are well calibrated: high freedom for exploration and design, low freedom only for genuinely fragile surfaces — the slug regex feeding tdd's auto-discovery, and verbatim handoff wording whose drift is a documented failure mode (BP2).
- Feedback loops are in place: user-approval gates before writing, plus a concrete self-review checklist (TODOs, contradictions, YAGNI, scenario discipline re-check) with a fix-then-ask rule (BP11).
- The Scenarios heading contract with /optimus:tdd and scenario-style's section anchors are enforced by scripts/validate.sh, so the load-bearing cross-file strings cannot silently drift.

---

## 20. code-review-deep — 3/10

Files: `skills/code-review-deep/SKILL.md` (156 lines) plus the skill's `agents/`, `references/`, `templates/`, `README.md`, and any shared references named in findings.

**Improvement need:** assessor 3 → verified **3** / 10. Rebuild recommended: no.

**Description assessment (433 chars):** 433 chars, leads with "Iterative auto-fix code review" — excellent menu scannability — and accurately covers what it does, the hard prerequisite (test command in .claude/CLAUDE.md), and when to use it, pairing with the sibling code-review description's cross-pointer. Its one flaw is internal redundancy: the fresh-subagent-per-iteration fact is stated twice, spending ~90 chars that push the when-to-use clause toward the truncation point.

**Assessor score rationale:** The skill is production-solid: the load-bearing machinery (argument parsing, plugin-root resolution, CLI contract, baseline gate, loop dispatch) is accurate against the code and largely test-pinned, and the structure is well layered. All findings are targeted polish — one genuine internal contradiction around --force recovery, a README gap on the baseline gate, small redundancies, and two minor wording/placeholder issues in a shared reference. Nothing structural is broken, so this sits at 'minor polish' (3), not 'moderate'.

**Verifier adjusted rationale:** All seven findings survived adversarial verification — six confirmed as filed, one adjusted only because its proposed fix would delete the Tip's unique second-opinion guidance (which itself contains a wrong-subcommand slip, `init` vs `resume`). I verified the load-bearing claims independently: cli.py's init/resume/baseline/final-report messages and archive semantics match SKILL.md exactly, the plugin-root section and loop wiring are contract-test-pinned, and none of the flagged text is enforced by validate.sh or expected-outputs.yaml, so every proposed change is mechanically safe. One additional medium doc-drift the assessor missed: the README's `cap` termination row promises resume-after-cap, which the archive behavior (and the skill's own Tip) contradicts. Nothing found is structural or high-severity — the surviving set is one internal contradiction (--force), two README drift items, and a handful of low redundancy/wording fixes, all one-or-two-sentence edits — so the assessor's score of 3 (minor polish) stands.

### Findings to implement

#### F1. [medium/ambiguity] skills/code-review-deep/SKILL.md — Step 4 'On fresh run', likely-errors bullet (~line 108) and closing note (line 112)

- **Quote:** "re-invoke this skill with `--force` to discard the prior progress and start fresh"
- **Problem:** Step 1's argument parsing has no `--force` flag (rule 6 sends it to scope text), yet this bullet tells the user to re-invoke the skill with `--force`, and line 112 then contradicts it with '(no separate user-visible orchestrator flag is needed)'.
- **Fix:** Either add `--force` to Step 1's parsed-flag list (forwarded to `cli.py init`) or reword the error guidance to match refactor-deep's phrasing ('re-invoke `init` with `--force`') and delete the contradictory parenthetical.
- **Best practice:** BP13, BP21, BP16
- **Verifier:** CONFIRMED — Quote verbatim at SKILL.md line 108. Step 1 parses exactly five flags and rule 6 routes everything else to scope text; argument-hint omits --force; line 112's parenthetical '(no separate user-visible orchestrator flag is needed)' directly conflicts with telling the user to re-invoke the skill with --force. Siblings refactor-deep:109 and unit-test-deep:106 use the non-contradictory phrasing 're-invoke `init` with `--force`'. No test or validate.sh check pins this wording (grep of expected-outputs.yaml and validate.sh for 'force' found nothing), so the proposed fix is safe. Medium is right: a genuine internal contradiction in a common recovery path (un-archived prior run).

#### F2. [low/doc-drift] skills/code-review-deep/README.md — Requirements / Usage (~lines 34-41)

- **Quote:** "- Test command in `.claude/CLAUDE.md`"
- **Problem:** The README never mentions the green-baseline gate or its `--allow-red-baseline` override (nor `--force`), so a user with a failing suite meets every listed requirement yet gets stopped by `baseline-red` with an undocumented escape flag.
- **Fix:** Add 'Green test suite at start (or `--allow-red-baseline`)' to Requirements and list `--allow-red-baseline` (and the progress-file `--force` recovery) in Usage.
- **Best practice:** BP4 (docs accuracy), D9
- **Verifier:** CONFIRMED — Quote verbatim at README.md line 40. The README's Requirements, Usage, and 'How It Differs' table never mention the green-baseline gate, --allow-red-baseline, or --force; SKILL.md Step 4 hard-stops on baseline-red (cli.py prints baseline-red and exits non-zero). A user with a red suite satisfies every listed requirement and is blocked by a gate with an escape flag documented only in SKILL.md — real D9 drift, low severity is correct.

#### F3. [low/redundancy] skills/code-review-deep/SKILL.md — '## Tip' (lines 152-156) vs Step 4 (line 90) and Step 6 (line 144)

- **Quote:** "after a `diminishing-returns` soft-exit (the CLI leaves that run un-archived)"
- **Problem:** The diminishing-returns/archive semantics and the resume cap-raise are each stated twice in SKILL.md (Step 6 + Tip; Step 4 + Tip) and a third time in orchestrator-loop-single.md 'After the loop' — a subtle rule stated three times invites drift; none of it is test-enforced.
- **Fix:** Shrink '## Tip' to a one-line pointer ('see Step 4/Step 6 for resume and archive semantics') or delete it, keeping each rule stated exactly once.
- **Best practice:** BP1
- **Verifier:** ADJUSTED — The duplication is real and not test-enforced (checked validate.sh, expected-outputs.yaml, test_skill_contract.py — only harness-mode.md's termination-reason list is pinned): the archive exception appears in Step 6, the Tip, and orchestrator-loop-single.md line 162; the cap-raise appears in Step 4 and the Tip. But the proposed change over-deletes: the Tip's second paragraph (fresh second-opinion pass after an archived clean finish, converges on first iteration on a clean tree) is unique content stated nowhere else — and it contains a factual slip: '(`init` would report no progress file)' names the wrong subcommand (cli.py cmd_resume prints 'ERROR: No progress file at ...'; init errors only when the file EXISTS).
  - **Revised severity:** low
  - **Revised fix (implement this one):** Trim the Tip's first paragraph to a pointer at Steps 4/6 (which already state the resume/archive semantics), keep the unique second paragraph about starting a fresh second-opinion run, and fix its wrong subcommand name (`init` → `resume`).

#### F4. [low/weak-description] skills/code-review-deep/SKILL.md — frontmatter description (line 2)

- **Quote:** "Each iteration runs in an isolated subagent so context does not accumulate."
- **Problem:** This sentence repeats 'runs ... in a fresh subagent context per iteration' from the description's first clause, wasting ~90 of 433 chars and pushing the 'Use when...' trigger clause toward menu truncation.
- **Fix:** Delete the sentence, folding 'so context does not accumulate' into the first clause if the rationale is worth keeping.
- **Best practice:** BP4, BP1
- **Verifier:** CONFIRMED — Quote verbatim in the frontmatter description (line 2). It restates 'runs ... in a fresh subagent context per iteration' from the first clause. The sentence is ~77 chars, not ~90, but the substance holds: under repo context #1 (descriptions judged for menu scannability/conciseness), the repetition spends space that pushes the 'Use when...' trigger clause toward truncation. Deleting it breaks nothing (no frontmatter mechanics involved). Low is right.

#### F5. [low/ambiguity] skills/code-review-deep/SKILL.md — Step 4 'On --resume' (line 90)

- **Quote:** "Pass `--max-iterations N` through when the user supplied a higher cap on `--resume`"
- **Problem:** The orchestrator cannot know whether N is 'higher' without reading the persisted config, and cli.py cmd_resume (lines 696-700) actually applies any supplied cap including a lower one — so a user deliberately resuming with a lower cap is silently ignored under a literal reading.
- **Fix:** Reword to 'Pass `--max-iterations N` through whenever the user supplied it on `--resume`' and let the CLI own the clamping.
- **Best practice:** BP21
- **Verifier:** CONFIRMED — Quote verbatim at SKILL.md line 90. Verified in cli.py cmd_resume (~lines 696-700): new_cap = max(min(args.max_iterations, MAX_ITERATIONS_HARD_CAP), 1) is applied whenever it differs from the persisted cap — including a LOWER value — with the CLI owning clamping and the cap-overrun guard. The orchestrator cannot know 'higher' without reading persisted config the skill never tells it to read. Rewording to 'whenever the user supplied it' matches actual CLI behavior and removes an unfulfillable comparison. Low severity correct.

#### F6. [low/under-specification] references/orchestrator-loop-single.md — 'Dispatch the base skill' template (line 40)

- **Quote:** "Phase: <skill>"
- **Problem:** `<skill>` is the only placeholder in the dispatch template never defined (the file defines `<base-skill>`), and harness-mode.md never reads a Phase line — only coverage-harness-mode.md does — so a fresh instance must guess what to substitute.
- **Fix:** Rename the placeholder to `Phase: <base-skill>` (or drop the line from the single-loop template since harness-mode.md ignores it).
- **Best practice:** BP13, BP21
- **Verifier:** CONFIRMED — Quote verbatim at orchestrator-loop-single.md line 40. The file's 'Where' clause (line 56) defines `<base-skill>` only; `<skill>` is never defined. Verified harness-mode.md contains no Phase-line consumption (only a prose mention of 'refactor phase'), cli.py's phase handling is coverage/paired-loop only, and test_skill_contract.py pins 'skills/<base-skill>/SKILL.md', HARNESS_MODE_INLINE, and 'Read the base SKILL.md' — not the Phase line — so either renaming to `<base-skill>` or dropping the line is safe. Low-impact (trivially inferable, nothing consumes it), so low is the right severity.

#### F7. [low/over-specification] references/orchestrator-loop-single.md — step 3 'Save the subagent return' (line 67)

- **Quote:** "renaming a prefix therefore requires synchronized updates to `_HARNESS_STATE_EXCLUDES` (authoritative) and this repo's `.gitignore` (the dev mirror)"
- **Problem:** This is maintainer-facing rename/sync documentation loaded into every deep run's context; at execution time the model only needs 'use these exact prefixes' (the sync itself is already pinned by test_git.py).
- **Fix:** Keep 'These exact filename prefixes are required' plus one clause on why (the commit un-stage step matches them), and move the rename/dev-mirror guidance to .claude/docs/architecture.md or a git.py comment.
- **Best practice:** BP1
- **Verifier:** CONFIRMED — Quote verbatim at orchestrator-loop-single.md line 67. This is maintainer-facing rename/sync documentation loaded into every deep run; at execution time the orchestrator needs only 'use these exact prefixes' plus why (commit_checkpoint's un-stage step matches them). The sync itself is pinned in code by test_git.py:122 (asserts '.claude/.deep-iteration-*' in excludes), and no contract test pins this prose, so moving the maintenance guidance to architecture.md or a git.py comment is safe. Legitimate BP1 over-specification, low.

#### F8. [medium/doc-drift] skills/code-review-deep/README.md — Termination Reasons table, `cap` row (~line 50)
*Found by verifier (adversarial pass) — treat as confirmed*

- **Quote:** "The iteration cap was reached. Resume with a higher cap if needed."
- **Problem:** The README promises resume-after-cap, but in the normal flow Step 6's `final-report --archive` archives every run except `diminishing-returns` (verified in cli.py cmd_final_report), so `--resume` after a cap exit errors 'No progress file' — the SKILL.md Tip even states the opposite ('convergence / cap ... archived ... --resume no longer finds it').
- **Fix:** Reword the `cap` row to match the Tip and CLI: 'Reached the iteration cap. The run is archived; re-run `/optimus:code-review-deep --max-iterations <higher>` for a fresh pass.'
- **Best practice:** D9, BP23

### Already well-tuned (preserve; do not churn while fixing the above)

- Degrees-of-freedom calibration is exemplary: exact commands only where fragile (plugin-root resolution, CLI invocations — both test-enforced byte-identical or contract-pinned in test_skill_contract.py), prose freedom elsewhere.
- Strong plan-validate-execute and feedback gates: clean-tree refusal, green-baseline gate with timeout calibration and a documented red-baseline stop rationale plus an explicit --allow-red-baseline escape hatch (BP11/BP20).
- Every CLI stdout token and error string quoted in SKILL.md (baseline-green/red, commit-skipped, not-archived, 'progress file already exists', 'Cannot determine HEAD commit') matches cli.py exactly — verified against the code.
- Progressive disclosure done right: a 156-line orchestrator body, per-iteration mechanics in a ToC'd shared reference, and the single-iteration protocol (harness-mode.md) loaded only in the subagent's fresh context.
- The loop-control invariants encode real observed failure modes concisely (snapshot-before-dispatch token check, slice-only progress reads, 'don't end a turn on a promise', report-only-what-the-CLI-confirmed).
- Closing handoff matches skill-handoff.md Variant A verbatim, correctly treating /optimus:commit and /optimus:pr as stay-in-conversation continuation skills.

---

## 21. branch — 3/10

Files: `skills/branch/SKILL.md` (115 lines) plus the skill's `agents/`, `references/`, `templates/`, `README.md`, and any shared references named in findings.

**Improvement need:** assessor 3 → verified **3** / 10. Rebuild recommended: no.

**Description assessment (272 chars):** Excellent for this plugin's human-menu audience: leads with what it does ("Creates and switches to a new, conventionally named branch"), names all three name-derivation sources, states the two safety guarantees (preserves local changes, never commits/pushes), and closes with a when-to-use clause. At 272 chars it is scannable and accurate against actual behavior; style matches sibling skills (worktree, commit).

**Assessor score rationale:** The skill is small, accurate, and well-structured with a strong description and correctly calibrated freedom; nothing load-bearing is broken and the only test-enforced contract (conventional \"feat/\" prefix in output) is satisfied. The real fixes are concentrated in the Step 5 handoff block — the /optimus:tdd recommendation contradicts the skill's own README and tdd's always-create-a-branch behavior, and the hardcoded Variant B misapplies the skill-handoff convention in the starting-fresh flow — plus three one-line clarifications. That is minor polish, not structural work.

**Verifier adjusted rationale:** All five findings survive adversarial verification with quotes verbatim and no conflicts with validate.sh or expected-outputs.yaml (branch's only test contract is 'feat/' in output; the 'Variant A' wiring token belongs to the handoff skill). The two mediums are genuine: the /optimus:tdd next-step bullet contradicts the skill's own README and tdd's unconditional branch creation (mis-targeting the eventual PR base), and the hardcoded Variant B breaks the skill-handoff variant-selection convention that every sibling skill applies conditionally. The three lows are real one-line clarifications. I add one missed medium: in a multi-repo workspace the 'one repo has changes → target it silently' rule overrides an explicit inline description naming a different repo, creating the branch (and carrying unrelated WIP) in the wrong repo — a decision-point conflict with Step 2's inline-description-first priority. No high-severity problems exist: the description is accurate, safety rules sit at top and bottom, and git checkout -b plus collision handling are correctly low-freedom. Six localized wording/routing fixes in Steps 1, 2, and 5 of an otherwise well-tuned 115-line skill keep this at 3 — minor polish, no rebuild.

### Findings to implement

#### F1. [medium/convention-conflict] skills/branch/SKILL.md, Step 5 Next Step (line 102) vs skills/branch/README.md "When NOT to Use" (line 100)

- **Quote:** "If the user seems to be starting new work → `/optimus:tdd` to build the feature test-first"
- **Problem:** tdd's SKILL.md says "Always create a new branch from the current branch", so following this recommendation after /optimus:branch stacks a second branch on the just-created one and makes tdd's later PR target the orphaned intermediate branch instead of main — exactly the flow the skill's own README warns against ("Starting TDD — use /optimus:tdd instead, which creates its own branch").
- **Fix:** Drop or caveat the tdd bullet, e.g. "note: /optimus:tdd creates its own branch from the current one — if the user's next step is TDD, they did not need this skill; warn that a second branch will be created", keeping SKILL.md consistent with the README.
- **Best practice:** BP25
- **Verifier:** CONFIRMED — Quote verbatim at SKILL.md line 102. tdd's SKILL.md line 108 says 'Always create a new branch from the current branch' with no skip option, and line 110 records the current branch as the later PR/MR target — so following this bullet right after /optimus:branch stacks a second branch and targets the PR at the just-created, unpushed local branch. branch's own README line 100 ('Starting TDD — use /optimus:tdd instead, which creates its own branch') warns against exactly this flow, so it is real SKILL↔README drift plus a composability mis-route, not a deliberate convention. Proposed caveat is minimal and breaks nothing (no validate.sh/test token involves this bullet).

#### F2. [medium/convention-conflict] skills/branch/SKILL.md, Step 5 Next Step (line 107)

- **Quote:** "use **Variant B** with `<continuation-skill(s)>` = `/optimus:commit`"
- **Problem:** skill-handoff.md selects the tip variant by what the closing block actually recommends (A = continuation only, C = non-continuation only, B = mixed), but branch hardcodes Variant B unconditionally — and in the "starting fresh" scenario the mandated "stay in this conversation for /optimus:commit so it captures implementation context" is wrong advice, since implementation will happen in the fresh /optimus:tdd conversation and commit belongs there.
- **Fix:** Make the variant conditional on the actual recommendation: Variant A when only /optimus:commit is recommended (in-progress case), Variant C when only tdd/worktree (starting-fresh case), Variant B only when a mix is presented.
- **Best practice:** BP16
- **Verifier:** CONFIRMED — Quote verbatim at line 107. skill-handoff.md keys the variant to what the closing block actually recommends (A = continuation only, B = mixed two-or-more, C = non-continuation only), and Step 5 picks ONE recommendation by context — so unconditional Variant B misapplies the convention, and in the starting-fresh flow (recommendation = tdd, no implementation happened in this conversation) the mandated 'stay in this conversation for /optimus:commit' clause is misleading. Sibling skills (refactor:305, how-to-run:221, prompt:198-200, commit:137-139) all select variants conditionally, proving the house pattern is conditional. validate.sh's 'Variant A' token check applies only to skills/handoff/SKILL.md, so the proposed conditional selection is safe.

#### F3. [low/under-specification] skills/branch/SKILL.md, Step 2 Gather Context, git diff analysis (lines 45-55)

- **Quote:** "If there are local changes, analyze them to infer intent:"
- **Problem:** All four prescribed analysis commands are `git diff` variants, which show nothing when the local changes are entirely untracked new files (a common in-progress case the skill explicitly supports), so a weaker model may hit the "changes too ambiguous" stop path despite having usable signal.
- **Fix:** Add one line: untracked files do not appear in `git diff` — use the paths from `git status --short` and read the new files if their names alone are ambiguous (mirroring gather-changes.md, which lists `git status --short` explicitly as the untracked-files source).
- **Best practice:** BP3, BP21, BP23
- **Verifier:** CONFIRMED — Quote verbatim at line 45. All four prescribed analysis commands (git diff --stat, --cached --stat, git diff, --cached) show nothing for purely-untracked changes, and the skill's own 'deeper analysis if file names alone are ambiguous' path is therefore a dead end for a supported first-class case (intro line 11 explicitly covers untracked files). Softening note: git status --short is already run first, so file paths ARE available to the model — but the content-analysis fallback (read the new files) is genuinely missing, and gather-changes.md confirms status --short is the repo's canonical untracked-files source. Low severity is right; the one-line fix is cheap and safe.

#### F4. [low/ambiguity] skills/branch/SKILL.md, Step 2, diff-analysis bullet (line 59)

- **Quote:** "these map directly to branch types in the shared reference"
- **Problem:** "the shared reference" has no antecedent at this point — the only reference read so far is multi-repo-detection.md; branch-naming.md is not introduced until Step 3, thirteen lines later.
- **Fix:** Name the file: "…map directly to branch types in `branch-naming.md` (read in Step 3)".
- **Best practice:** BP13
- **Verifier:** CONFIRMED — Quote verbatim at line 59. At that point the only reference introduced is multi-repo-detection.md; branch-naming.md is not named until Step 3 (line 72), so 'the shared reference' has no antecedent — a real forward-reference ambiguity, not taste. Naming the file inline doesn't affect validate.sh's cross-ref path check (which validates $CLAUDE_PLUGIN_ROOT paths, not bare filename mentions).

#### F5. [low/missing-guidance] skills/branch/SKILL.md, Step 4 Create Branch (lines 82-97)

- **Quote:** "Report (adapt based on whether local changes exist):"
- **Problem:** The report template has no slot for the target repo and the adapt instruction names only the local-changes axis, so in a multi-repo workspace (a first-class Step 1 path) the output may not say which repo received the branch.
- **Fix:** Add: "In a multi-repo workspace, name the target repo in the report, e.g. Created `<branch-name>` in `<repo>` from `<original-branch>`."
- **Best practice:** BP14, BP21
- **Verifier:** CONFIRMED — Quote verbatim at line 82. Step 1 makes multi-repo a first-class path and mandates targeting a single changed repo 'silently', yet the report template has no repo slot and the adapt instruction names only the local-changes axis — so in the silent-targeting case the user may never learn which repo received the branch. expected-outputs.yaml only asserts 'feat/' appears in branch output, so adding a repo mention breaks no test. Low severity is right.

#### F6. [medium/ambiguity] skills/branch/SKILL.md, Step 1 Multi-repo Detection (line 24) vs Step 2 priority order (line 37)
*Found by verifier (adversarial pass) — treat as confirmed*

- **Quote:** "If **one repo** has changes, target it silently"
- **Problem:** Repo targeting is decided purely by which repo has changes, while an explicit inline description — the top-priority naming source — plays no role in repo selection unless zero repos have changes, so an unrelated-WIP repo silently wins over the repo the user actually named.
- **Fix:** Add a clause to the one-repo case: 'unless the inline description or conversation clearly identifies a different repo as the target — then target that repo (its clean tree is the starting-fresh case) and leave the other repo's changes untouched.'
- **Best practice:** BP16, BP21

### Already well-tuned (preserve; do not churn while fixing the above)

- Lean 115-line body with a clear 5-step workflow; references are one level deep with targeted section pointers ("Type Detection Keywords", "Slug Rules") instead of whole-file re-reads — textbook progressive disclosure for a small skill.
- Degrees of freedom well calibrated: exact commands only where fragile (collision check via `git show-ref --verify --quiet`, `git checkout -b`, forbidden `git stash`/`git add`/`git reset` list), high freedom for intent inference from diffs/conversation.
- Explicit no-signal stop rule with a copyable user message ("do not create a branch with a generic or meaningless name") — a concrete guard against the skill's worst failure mode.
- Safety constraints (preserve working tree, never commit/push/modify) stated in the intro and reinforced in "Important" — critical rules are not buried.
- Multi-repo Step 1 handles all three cases (one/multiple/zero repos with changes) with explicit conditional routing and a specified AskUserQuestion, matching the shared house pattern.

---

## 22. commit-message — 3/10

Files: `skills/commit-message/SKILL.md` (36 lines) plus the skill's `agents/`, `references/`, `templates/`, `README.md`, and any shared references named in findings.

**Improvement need:** assessor 3 → verified **3** / 10. Rebuild recommended: no.

**Description assessment (198 chars):** Strong for this plugin's human-scanning audience: 198 chars, third person, leads with what it does, and explicitly differentiates from the sibling /optimus:commit ("read-only, never commits" / "without actually committing"). Accurate against actual behavior. Its one gap is omitting the skill's distinguishing continuation behavior — capturing the implementation conversation's "why" into the message body — which the root README advertises and skill-handoff.md formalizes.

**Assessor score rationale:** Fundamentally well-built and lean — good reuse, correct handoff mechanics, test-enforced safety. Needs minor polish only: two medium items (an incoherent /optimus:pr recommendation from an uncommitted state on the instruction surface, and a README 'How It Works' claim that contradicts the conversation-context-capture behavior) plus four low-severity refinements. Nothing structural; all fixes are one-to-three-sentence edits.

**Verifier adjusted rationale:** All six findings survive verification: both mediums CONFIRMED (the /optimus:pr recommendation from an uncommitted state is provably incoherent against pr's own Step 4/5 flow; the README 'entirely on diff output' sentence contradicts the mandated conversation-capture reference and the root README), two lows CONFIRMED, and two lows ADJUSTED (the shared-reference fix needs skill-neutral wording; the untracked-files finding's permission-ambiguity rationale was refuted but a milder missing-input gap remains). No high-severity misses found after targeted hunts: the skill README's 'Recommended sequence' matches skill-handoff.md's sanctioned code-review-conversation alternate (not drift), the closing tip applies Variant A correctly with verbatim placeholders, no contradictions or buried rules exist in the 36-line body, and the only unguarded failure modes (clean worktree, non-git directory) are low-severity with self-explanatory git errors. The assessor's score of 3 stands: minor polish — six one-to-three-sentence edits, nothing structural, on a lean, well-composed skill whose one fragile property (read-only) is test-enforced.

### Findings to implement

#### F1. [medium/under-specification] skills/commit-message/SKILL.md — closing recommendation, line 34

- **Quote:** "If the feature is ready → `/optimus:pr` to create a pull request"
- **Problem:** The skill's premise is that the analyzed changes are uncommitted, yet this branch recommends /optimus:pr directly with no commit precondition — pr never commits working-tree changes.
- **Fix:** Condition the pr path on the changes being committed, e.g. "If the analyzed changes are already committed and the feature is ready → /optimus:pr" or route through /optimus:commit first.
- **Best practice:** BP16, BP21
- **Verifier:** CONFIRMED — Quote verbatim at SKILL.md line 34. The skill's premise is uncommitted local changes, and skills/pr/SKILL.md proves the incoherence: Step 4 stops with 'No commits on this branch yet. Commit your changes first.' when the branch is empty, and Step 5 gathers content only from `git diff origin/<default>..HEAD` — so following this branch as written either dead-ends or opens a PR that silently excludes the very changes just analyzed. The one-clause conditioning fix is safe: the Variant A closing tip still lists both continuation skills, and skill-handoff.md's canonical chain (commit → pr) supports it. Medium is right — it is the skill's closing decision point on the instruction surface (BP16, BP3).

#### F2. [medium/doc-drift] skills/commit-message/README.md — 'How It Works', line 58

- **Quote:** "No files are read beyond what git provides — it operates entirely on diff output."
- **Problem:** conventional-commit-format.md's 'Capture implementation context' section instructs mining the conversation (prior messages, Edit/Write tool calls) for the commit body, and the root README advertises 'Benefits from running in the implementation conversation' — the skill README both omits and contradicts this behavior.
- **Fix:** Rewrite 'How It Works' (and add a Features bullet) to mention conversation-context capture when run in the implementation conversation, and drop or qualify the 'entirely on diff output' sentence.
- **Best practice:** BP4 (accuracy vs behavior); rubric context #3
- **Verifier:** CONFIRMED — Quote verbatim at README.md line 58. conventional-commit-format.md's 'Capture implementation context' section (lines 15–31) — which SKILL.md Step 2 mandates reading — instructs mining prior messages and Edit/Write tool calls for the commit body, and root README line 93 advertises 'Benefits from running in the implementation conversation' (line 123 names it a continuation skill). 'Operates entirely on diff output' contradicts that formalized behavior, and the README's Features and When-to-Run sections omit it entirely. Classic D9 drift; nothing in validate.sh or expected-outputs.yaml enforces the sentence.

#### F3. [low/redundancy] skills/commit-message/SKILL.md — 'Important', line 30

- **Quote:** "When changes are too broad for a single commit, recommend splitting"
- **Problem:** Within a 36-line file the split rule is stated three times with three different trigger phrasings — Step 3's 'naturally split into multiple commits', this bullet's 'too broad', and the reference's 'span multiple concerns'.
- **Fix:** Delete this Important bullet (Step 3 plus the reference's 'Splitting Into Multiple Commits' section already cover it) and align Step 3's phrasing with the reference's 'span multiple concerns'.
- **Best practice:** BP1, BP13
- **Verifier:** CONFIRMED — Quote verbatim at SKILL.md line 30. The split rule genuinely appears with three trigger phrasings in the 36-line file plus the reference: line 22 'naturally split into multiple commits', line 24 'span multiple concerns', line 30 'too broad', and the reference's 'Splitting Into Multiple Commits' section. Checked scripts/validate.sh (zero commit-message matches) and test/expected-outputs.yaml (only files_not_modified: true) — not test-enforced, and splitting is a quality judgment, not a safety constraint, so the redundancy is fair game. Deleting the Important bullet and aligning Step 3's phrasing breaks nothing (BP1, BP13).

#### F4. [low/missing-guidance] skills/commit/references/gather-changes.md — 'Multi-repo workspace detection', line 11

- **Quote:** "If no repos have changes at all, inform the user and stop."
- **Problem:** The clean-worktree case is handled explicitly only in the multi-repo branch; for a single repo with no staged, unstaged, or untracked changes, neither this shared procedure nor SKILL.md says what to do.
- **Fix:** Add one line to the 'Gather changes' section: if the commands show no local changes at all, inform the user there is nothing to suggest and stop (fixes both consuming skills).
- **Best practice:** BP21, BP23
- **Verifier:** ADJUSTED — Quote verbatim at gather-changes.md line 11, and the gap is real: the clean-worktree stop is spelled out only in the multi-repo branch; neither the 'Gather changes' section, SKILL.md, nor conventional-commit-format.md covers a single clean repo, and the asymmetry (explicit in one branch, absent in the other) is what makes it worth one line. Severity low stands. The proposed wording needs correction, though: gather-changes.md is shared with /optimus:commit, so 'nothing to suggest' is commit-message-flavored and would read wrong for the committing consumer.
  - **Revised severity:** low
  - **Revised fix (implement this one):** Add one skill-neutral line to gather-changes.md 'Gather changes': "If the commands show no staged, unstaged, or untracked changes, inform the user there are no local changes to work with and stop." — phrased so both consuming skills (commit-message, commit) can apply it.

#### F5. [low/under-specification] skills/commit-message/references/conventional-commit-format.md — 'Analyze Changes', line 7

- **Quote:** "Review the gathered git diff information"
- **Problem:** Untracked files appear only as names in `git status --short` — they have no diff — so a change set dominated by new files leaves Claude to guess whether reading their contents is permitted for analysis.
- **Fix:** Add a sentence: for untracked files, read their contents to classify type and scope (reading is allowed; only modification is forbidden).
- **Best practice:** BP21
- **Verifier:** ADJUSTED — Quote verbatim at conventional-commit-format.md line 7, but the stated problem is wrong: no permission ambiguity exists. Every read-only statement (description, SKILL.md lines 28–29) forbids only 'commit, stage, or modify' — reading is never discouraged, and no model would infer it is. What survives is a milder, real gap: gather-changes.md surfaces untracked files as names only (`git status --short`), so for a new-file-dominated change set the procedure literally provides no analyzable content, and a weaker model could classify type/scope from filenames alone (BP3, BP21). Notably /optimus:commit's Step 3 handles untracked files explicitly while commit-message's path never mentions them.
  - **Revised severity:** low
  - **Revised fix (implement this one):** In conventional-commit-format.md 'Analyze Changes', add: untracked files appear only as names in the gathered output — read their contents when needed to determine type and scope. Frame it as a missing analysis input, not a permissions clarification.

#### F6. [low/weak-description] skills/commit-message/SKILL.md — frontmatter description, line 2

- **Quote:** "Use when a commit message suggestion is needed without actually committing."
- **Problem:** The WHEN clause omits the skill's distinguishing continuation behavior — it is best run in the implementation conversation so the body can capture the 'why' (advertised in the root README and formalized in skill-handoff.md).
- **Fix:** Append a short clause such as 'Best run in the conversation where the changes were implemented, so the message body captures the why.'
- **Best practice:** BP4
- **Verifier:** CONFIRMED — Quote verbatim at SKILL.md line 2. The continuation behavior is the skill's key differentiator (root README line 93 advertises it; skill-handoff.md line 20 formalizes it), it changes WHEN a user should invoke the skill — exactly BP4's WHEN territory for the human menu audience — and the sibling /optimus:pr's description already models the pattern ('Captures the implementation conversation's intent... when run in the same session'). Adding one clause keeps the description under ~300 chars and scannable. Low is right; note /optimus:commit's description has the same omission, so the fix should ideally be applied to both siblings for consistency.

### Already well-tuned (preserve; do not churn while fixing the above)

- Exemplary progressive disclosure for a lightweight skill: a 36-line SKILL.md delegates gathering and format rules to two shared references, staying exactly at the allowed SKILL→A→B depth with zero procedure duplication against the sibling /optimus:commit
- Read-only safety constraint is stated in the description, the workflow, and the Important section, and is backed by a test gate (test/expected-outputs.yaml: files_not_modified: true) — appropriate emphasis for the one truly fragile property
- The closing handoff correctly applies skill-handoff.md Variant A: both recommended next skills (/optimus:commit, /optimus:pr) are continuation skills, and the placeholder substitutions match the shared doc verbatim
- The 'Capture implementation context' section in conventional-commit-format.md is well-calibrated: explicit inspect/omit lists plus a hard 'never fabricate context' fallback for fresh conversations
- Degrees of freedom are well matched: exact git commands where fragile (gather-changes.md), high-freedom judgment for type/scope/splitting decisions

---
