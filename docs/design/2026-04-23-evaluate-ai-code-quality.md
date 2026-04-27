# Design: Incorporate Uncle Bob's AI code-quality criteria into optimus-claude

**Date:** 2026-04-23
**Status:** Approved
**Goal:** Extend optimus-claude with mutation testing (top priority) and three advisory static-analysis signals (cyclomatic complexity, module size, dependency structure) via a two-tier integration — the existing harness pattern for convergence-loop tools, plus a new shared `deterministic-tool-consumption.md` reference that governs all advisory tool adapters.

**Source:** JIRA OPTS-8 — `docs/jira/OPTS-8.md`

## Context

optimus-claude validates AI-generated code quality today through test coverage: `/optimus:init` installs coverage tooling per stack, `/optimus:unit-test` consumes the coverage score as a convergence signal. This pipeline validates *that* tests exist — not whether they are *effective*. Mutation testing (OPTS-8's top priority) closes that gap by producing a score that iterates in the same loop.

Three further Uncle-Bob criteria — cyclomatic complexity, module size, and dependency structure — are today judged only by LLM heuristics inside `skills/refactor/agents/testability-analyzer.md`. These judgements are subjective and non-reproducible. Deterministic static-analysis tools can feed those agents with measurable inputs.

The most consequential precondition the codebase reveals: **there is no existing pattern for a skill or agent to invoke a deterministic external tool and consume structured output.** Every agent today is LLM-driven. Coverage is special-cased inside the harness. The single shared reference for deterministic-tool consumption is the foundation every subsequent tool will inherit — getting its contract right matters more than any individual tool choice.

Scope boundary: OPTS-8 is the design record only. All source-modifying work is deferred to per-section follow-up JIRA tickets.

## Approach

Two tiers, distinguished by whether the tool drives an iterative loop or produces a one-shot snapshot.

1. **Shared foundation (lands first).** A new `references/deterministic-tool-consumption.md` defines a single contract every deterministic tool adapter implements: detection, invocation, JSON output schema, absence handling, graceful degradation, and reset path. It is the canonical way any deterministic tool plugs into the plugin, whether the consumer is the harness or an agent.

2. **Convergence tier — mutation testing.** Extends the existing `coverage-harness-mode.md` pattern. Mutation-score plateau becomes a convergence signal alongside coverage plateau. **Packaging decision:** an opt-in `deep harness mutation` mode inside `/optimus:unit-test`, *not* a separate `/optimus:mutation-test` skill. Rationale: mutation testing is in service of better test writing — the same mental context users already reach for when running `/optimus:unit-test`. A separate skill would fragment that surface without adding capability. **Scope decision (clarified 2026-04-27):** the MVP lives in **harness mode only**. Interactive deep mode (`/optimus:unit-test deep`, no `harness`) already has a coverage-plateau termination condition that mutation-plateau would peer with — but adding mutation invocation inside Claude's in-conversation loop is a meaningfully different implementation (Claude itself invokes the tool, parses the envelope, drives termination) and is deferred to Ticket #8. Normal mode (single-pass) has no loop and is intentionally out of scope.

3. **Advisory tier — CC, module size, dependency structure.** One-shot snapshots feeding `skills/refactor/agents/testability-analyzer.md` (and optionally `skills/code-review/agents/test-guardian.md`). No harness involvement — these tools do not produce a metric the loop should chase. Findings enter the agent's existing markdown output as fields on each barrier. "Findings inform the agent; they do not drive it" (mitigates JIRA Risk #5 — metric-driven churn).

4. **CI decision.** No new `/optimus:ci` skill under OPTS-8. The same detection logic lives inside the existing skills; a sample GitHub Actions workflow fragment lives in the root `README.md` under a new "CI integration" section. A dedicated CI skill is revisited only if concrete user demand surfaces. Maintenance cost vs marginal benefit does not justify the addition today.

5. **Graceful degradation (AC #11).** The shared reference mandates every integration supply:
   - Detection logic that never fails loudly when a tool is absent.
   - Behavior when absent: informational warning, never a fatal error.
   - An `/optimus:reset` inverse path for anything `init` installs.

## Components

| Component | Responsibility | New / Modified |
|-----------|----------------|----------------|
| `references/deterministic-tool-consumption.md` | Canonical contract: detection → invoke → parse → absence handling → reset | New |
| `skills/refactor/agents/dependency-analyzer.md` | Consume dependency-tool output; emit findings following the shared reference | New |
| `references/coverage-harness-mode.md` | Add mutation-score plateau as a convergence signal | Modified |
| `skills/unit-test/SKILL.md` | Add opt-in `deep harness mutation` step; delegate tool invocation through the shared reference | Modified |
| `scripts/test-coverage-harness/impl/progress.py` | Extend progress schema with a `mutation` peer key to `coverage` | Modified |
| `scripts/test-coverage-harness/impl/convergence.py` | Add mutation-plateau check alongside coverage-plateau | Modified |
| `scripts/test-coverage-harness/main.py` | Invoke the mutation tool when flagged; coverage-only path remains the default | Modified |
| `skills/init/references/test-infra-provisioning.md` | Per-stack mutation-tool install (opt-in) | Modified |
| `skills/init/references/test-framework-recommendations.md` | Add Mutation / CC / Module-size / Deps columns to the stack matrix | Modified |
| `skills/reset/` (existing reset skill) | Inverse uninstall paths for any new tools `init` installs | Modified |
| `skills/refactor/agents/testability-analyzer.md` | Consume CC + module-size findings via the shared reference | Modified |
| `skills/code-review/agents/test-guardian.md` | Opt-in surfacing of CC / cycle / module-size findings from deterministic tools | Modified |
| `README.md` | Add a "CI integration" section with a sample workflow fragment | Modified |

## Interfaces

### Shared adapter contract

Every deterministic tool wrapper emits a JSON envelope that both the harness and advisory agents can consume:

```json
{
  "tool": "mutmut",
  "version": "3.1.0",
  "stack": "python",
  "scope": "diff" | "full",
  "findings": [ /* tool-specific array */ ],
  "summary": { "primary_metric": 0.78 },
  "absent": false
}
```

- Agents read `findings[]` and render them into their existing markdown output format.
- Harness convergence reads `summary.primary_metric` deltas across cycles. `primary_metric` is only meaningful for convergence-tier tools; advisory-tier envelopes may set it to `null`.
- `absent: true` replaces a failed invocation — the consumer treats it as informational and continues. Never fatal.
- Adapters are thin per-stack shell wrappers invoked by the skill; the shared reference specifies the envelope shape, not the implementation language of the wrapper.

### Convergence signal — mutation

Plateau detected when **two consecutive cycles** report `|Δ mutation-score| ≤ 1pp`. The threshold is loosened from coverage's ≤ 0.5pp to account for mutation testing's inherent variance on small codebases. Documented in `references/coverage-harness-mode.md`.

### Per-stack tool matrix

Added as new columns in `skills/init/references/test-framework-recommendations.md`:

| Stack | Mutation | CC | Module size | Dependency structure |
|-------|----------|----|-------------|----------------------|
| Python | `mutmut` | `radon cc` | `radon raw` | `pydeps` + `import-linter` |
| Node+Vite / Node other | `stryker` | ESLint complexity rule | `jscpd` | `dependency-cruiser` / `madge` |
| Go | `gremlins` | `gocyclo` | `gocognit` / built-in | `go-callvis` / `godepgraph` |
| Rust | `cargo-mutants` | *(no mature OSS — gap)* | `tokei` | `cargo-deps` |

Gaps (Rust CC today) are flagged in this doc and spawn named follow-up tickets — they are not pretended away.

## Edge Cases and Risks

| Risk | Mitigation |
|------|------------|
| `init` blast radius — mutation tools extend writes into `pyproject.toml` / `package.json` / `Cargo.toml` (JIRA Risk #1) | All installs opt-in via the existing `init` test-infra prompt. Shared reference mandates the `/optimus:reset` inverse path for every tool. |
| Mutation runs too slow to use inside the unit-test loop (Risk #2) | `deep harness mutation` defaults to diff-scoped runs. Full-run is explicit opt-in. Expected runtime per stack documented in `coverage-harness-mode.md`. |
| Stack matrix explosion — four tools × many stacks (Risk #3) | Shared reference enforces "absent tool = informational, never fatal". Adding a stack without a mature tool is a documented gap, not a regression. |
| Harness JSON contract churn as metrics multiply (Risk #4) | Only the convergence tier (mutation) touches `harness_common` schema. Advisory tier uses the shared reference independently — harness schema blast radius stays contained to one new key. |
| Metric-driven refactor churn — "refactor anything with CC > 10" (Risk #5) | Advisory findings enter `testability-analyzer` as *inputs* on existing barriers, never as the ranking driver. Numbers appear as fields, not verdicts. Agent still chooses what to recommend. |
| Precedent risk — first deterministic-tool consumer sets the pattern (Risk #6) | Shared reference is designed, approved, and landed *before* any tool-specific ticket. Each per-criterion ticket explicitly cites and follows it. |
| Coverage-harness regression when mutation mode is added | Mutation is strictly opt-in via an additional flag. Coverage-only path stays the default and is covered by existing harness tests. New tests are added for the mutation path. |
| AC #6 violation — accidentally introducing a paid dependency | Matrix above contains only free / open-source tools. Shared reference forbids paid tools in its acceptance criteria. |

## Out of Scope

- Any source-modifying implementation under OPTS-8 itself — each design section spawns its own follow-up JIRA ticket (see below).
- A separate `/optimus:mutation-test` skill (decision: fold into `/optimus:unit-test`).
- A separate `/optimus:ci` skill (decision: README sample workflow is sufficient).
- Rust cyclomatic-complexity tooling (documented gap; named follow-up).
- Paid tools (AC #6) — nothing in the matrix requires a license.
- Adopting an external CRAP tool (e.g., Cobertura's Java-only implementation). The CRAP metric itself is in scope as a derived advisory field inside `testability-analyzer` (see Refined plan finding #3 and Ticket #4 AC #6); a per-stack CRAP tool dependency is not.
- Dependency-graph visualisations beyond the analyzer agent's text findings.
- Retrofitting existing LLM-driven agents (e.g., bug-detector, security-reviewer) to consume deterministic tool output — out of scope until a need arises.

## Open Questions

- Should advisory findings surface during `/optimus:code-review` by default, or only behind an opt-in flag? *Lean opt-in* — avoids review noise and preserves the current review cadence. Confirm during the `test-guardian` ticket.
- Do Go and Rust mutation tools (`gremlins`, `cargo-mutants`) ship in the first wave, or only after the Python + JS/TS MVP has proven stable? *Lean defer* to a second wave to keep the first implementation ticket scoped.
- Exact on-disk layout of the diff-scope cache used by mutation reruns — a harness-internals decision, not an architectural one. Deferred to the mutation-testing implementation ticket.

## Follow-up JIRA tickets to spawn (AC #7)

Each bullet becomes one ticket; OPTS-8 itself remains the design record.

1. Build `references/deterministic-tool-consumption.md` with contract tests. **Prerequisite for every other ticket below.**
2. Extend `/optimus:unit-test` with the `deep harness mutation` mode: harness schema additions, convergence updates, adapter wiring via the shared reference. **Harness mode only — interactive deep is Ticket #8.**
3. Add mutation-tool install paths to `skills/init/references/test-infra-provisioning.md` per stack, plus the `/optimus:reset` inverse.
4. Extend `skills/refactor/agents/testability-analyzer.md` to consume CC and module-size findings via the shared reference.
5. New `skills/refactor/agents/dependency-analyzer.md` agent consuming dependency-structure tools via the shared reference.
6. Optional — opt-in CC / cycle / module-size surfacing in `skills/code-review/agents/test-guardian.md`.
7. Add a "CI integration" section plus a sample GitHub Actions workflow fragment to `README.md`.
8. Extend interactive deep mode (`/optimus:unit-test deep mutation`, no `harness`) with mutation-plateau as a peer to coverage-plateau termination. Reuses Ticket #2's adapters; touches only the interactive deep-mode loop.

## Refined plan — per-ticket briefs (added 2026-04-23, CRAP addendum 2026-04-27)

Validation against the current codebase surfaced two findings that changed the shape of these briefs:

1. **Tool matrix substitutions.** `jscpd` is a copy-paste detector, not a module-size tool — ticket #3 substitutes ESLint `max-lines` (preferred — in-band with the CC pick) or `cloc`. `cargo-deps` is unmaintained and Graphviz-only — ticket #3 substitutes built-in `cargo tree --format json`. Original matrix preserved above.
2. **Reset scope widening.** [skills/reset/SKILL.md](../../skills/reset/SKILL.md) restricts itself to `.claude/` by explicit rule. Ticket #3 widens that contract so mutation-tool entries in manifest files can be surgically removed, and names the widening as a ticket-specific risk with a conditional-removal guardrail.
3. **CRAP metric (added 2026-04-27, prompted by JIRA description refresh).** The reporter asked whether CRAP (Change Risk Anti-Patterns — `CC² × (1 − coverage)³ + CC`, originated in Java/Cobertura) belongs here. **Decision: yes, but as a derived advisory field — no new tool, no new ticket.** Once ticket #4 lands, `testability-analyzer` already has both inputs (CC envelope from ticket #4, coverage envelope from the existing harness). The agent computes CRAP per function in-band and surfaces it as an additional optional field on existing barriers, alongside `CC:` and `Module size:`. Rationale for not spinning a separate ticket: (a) no widely-maintained cross-stack OSS CRAP tool exists today — every option is Java-only or Cobertura-bound, which would violate AC #6 by stack and contradict the "no paid / Java-only" constraint; (b) the formula is trivial to derive in-agent and avoids matrix explosion; (c) treating CRAP as advisory inherits Risk #5 mitigation automatically — never a ranking driver. The rule "findings are still ordered by testability impact, not metric value" already applies. AC #4 of ticket #4 explicitly covers this — no change to ticket structure required beyond the AC addition below.
4. **Mutation-mode scope (added 2026-04-27, prompted by SKILL.md re-read).** Ticket #2's `mutation` keyword is bound to **harness mode only** (`/optimus:unit-test deep harness mutation`). [skills/unit-test/SKILL.md](../../skills/unit-test/SKILL.md) has three execution modes — normal (single pass), interactive deep (in-conversation loop, lines 241–280), and harness deep (external Python script). The interactive deep loop already terminates on coverage plateau (line 258), so a mutation-plateau peer is the natural fit there too — **but** invoking mutation tools inside Claude's in-conversation loop is a different implementation surface (Claude parses the ticket-#1 envelope and drives termination itself, rather than the harness orchestrator doing it), with different context-window pressure (mutation runs are slow → context accumulation across iterations bites harder than the harness's fresh-context-per-phase model). **Decision:** keep ticket #2 harness-only as MVP; spawn **Ticket #8** to extend interactive-deep mode with mutation-plateau as a follow-up. Normal mode stays out — it has no convergence loop, so a one-shot mutation report there has marginal value over running mutmut/stryker directly.

Ticket #1 gates #2, #3, #4, #5, #6, #8. Ticket #7 is independent.

---

### Ticket 1 — Shared deterministic-tool-consumption reference

**Goal.** Land a single canonical reference that every deterministic tool adapter (convergence or advisory) inherits — detection, invocation, JSON envelope shape, absence handling, reset path.

**Prerequisites.** None.

**Files to create.**
- `references/deterministic-tool-consumption.md` — new canonical contract.

**Files to modify.** None. Ticket #1 only creates the reference.

**Acceptance criteria.**
1. Reference defines the JSON envelope exactly as in the "Shared adapter contract" section above (`tool`, `version`, `stack`, `scope`, `findings[]`, `summary.primary_metric`, `absent`). `primary_metric: null` is valid for advisory-tier tools.
2. Reference defines detection logic that **never fails loudly when a tool is absent** (AC #11) — specifies the `absent: true` path and requires consumers to treat it as informational, not fatal.
3. Reference defines the reset-path contract: every adapter that `init` installs MUST have a documented inverse in `skills/reset/`.
4. Reference forbids paid-tool dependencies (AC #6) in its acceptance criteria section.
5. Reference includes at least one worked example (pseudocode or adapter stub) so future tickets have a concrete template.
6. Any contract tests live under `test/` at a path consistent with existing test layout — plain pytest, no new test framework.

**Risks.** Risk #6 (precedent) — this reference is the pattern every subsequent tool inherits; wrong contract here compounds. Mitigated by landing it alone before any tool-specific ticket.

---

### Ticket 2 — `/optimus:unit-test` deep-harness-mutation mode

**Goal.** Add an opt-in `deep harness mutation` mode that runs a mutation tool inside the existing coverage-harness loop and converges on mutation-score plateau alongside coverage plateau.

**Scope.** Harness mode only. Interactive deep mode (`/optimus:unit-test deep`, without `harness`) and normal mode are explicitly out of scope; interactive deep is covered by Ticket #8.

**Prerequisites.** Ticket #1.

**Files to create.**
- New tests in [test/test-coverage-harness/test_convergence.py](../../test/test-coverage-harness/test_convergence.py) — mutation-plateau cases.
- New tests in [test/test-coverage-harness/test_progress.py](../../test/test-coverage-harness/test_progress.py) — `mutation` key in the initial progress schema.
- New tests guarding the coverage-only regression path when the mutation flag is absent.

**Files to modify.**
- [scripts/test-coverage-harness/impl/progress.py](../../scripts/test-coverage-harness/impl/progress.py) — add a `mutation` peer key to `coverage` in `make_initial_progress` (line 40–45), shape `{baseline, current, tool, history: []}`.
- [scripts/test-coverage-harness/impl/convergence.py](../../scripts/test-coverage-harness/impl/convergence.py) — add `check_mutation_plateau(mutation_history, min_consecutive=2)` mirroring `check_coverage_plateau` but with `|Δ| ≤ 1pp` rather than zero-delta (per the design's convergence-signal section).
- [scripts/test-coverage-harness/main.py](../../scripts/test-coverage-harness/main.py) — gate mutation invocation on a flag from the skill; coverage-only remains the default.
- [skills/unit-test/SKILL.md](../../skills/unit-test/SKILL.md) — extend Step 1 arg parsing (lines 14–27) to accept a trailing `mutation` keyword after `deep harness`. Extend harness-mode detection (lines 29–41) to forward the flag.
- [references/coverage-harness-mode.md](../../references/coverage-harness-mode.md) — add mutation-score plateau as a peer convergence signal; document diff-scope default, full-run explicit opt-in, expected per-stack runtime order of magnitude.

**Acceptance criteria.**
1. Progress schema gains a `mutation` key with identical shape to `coverage`. Existing `coverage` key shape is unchanged.
2. `check_mutation_plateau` returns `(True, reason)` when two consecutive history entries report `|delta| ≤ 1pp`, else `(False, None)`. Unit-tested.
3. With the mutation flag **absent**, every existing `test/test-coverage-harness/` test still passes unchanged — the coverage-only path is provably not regressed.
4. With the mutation flag **present**, the harness invokes the stack's mutation adapter via the ticket-#1 envelope and records results into `progress.mutation.history`.
5. `deep harness mutation` defaults to **diff-scoped** runs. Full-run reached only via an additional explicit keyword.
6. If the mutation tool is **absent**, the harness emits an informational warning and continues in coverage-only mode (never fatal — inherited from ticket #1).
7. The `mutation` keyword is accepted **only** after `deep harness`. Invocations like `/optimus:unit-test mutation` or `/optimus:unit-test deep mutation` (without `harness`) are rejected with a clear message pointing at Ticket #8 as the deferred path.

**Risks.** Risk #2 (mutation too slow) — mitigated by diff-scope default. Risk #4 (schema churn) — contained to one new peer key. "Coverage-harness regression" — AC #3 is the direct guard.

---

### Ticket 3 — `init` mutation-tool install paths + `/optimus:reset` inverse

**Goal.** Add per-stack mutation-tool installation to `skills/init/` as opt-in, and extend `skills/reset/SKILL.md` so the installs have a working inverse.

**Prerequisites.** Ticket #1.

**Files to modify.**
- [skills/init/references/test-infra-provisioning.md](../../skills/init/references/test-infra-provisioning.md) — new opt-in section for mutation-tool install, parallel to the coverage-tool install step; gated on explicit user approval.
- [skills/init/references/test-framework-recommendations.md](../../skills/init/references/test-framework-recommendations.md) — add the Mutation / CC / Module-size / Dependency-structure columns from the matrix, **with substitutions applied**: `jscpd` → ESLint `max-lines` (preferred, in-band with the CC pick) or `cloc` for the Node module-size column; `cargo-deps` → `cargo tree --format json` for the Rust dependency column. Rust CC remains labelled as a gap.
- [skills/reset/SKILL.md](../../skills/reset/SKILL.md) — widen the "NEVER touch files outside `.claude/`" rule to permit surgical removal of *only* the specific dev-dep entries `init` wrote to `pyproject.toml` / `package.json` / `Cargo.toml`. The safety bar stays: categorized diff + user confirmation before any manifest edit.

**Acceptance criteria.**
1. Mutation-tool install is **opt-in** — a user who declines is left with a coverage-only project indistinguishable from today's `init` output.
2. Per-stack matrix names one tool per non-gap cell; Rust CC is explicitly labelled "gap — no mature OSS", not faked.
3. Every tool listed cites a free/open-source license (AC #6).
4. `skills/reset/SKILL.md` cleanly undoes each mutation install: removes the dev-dep entry from the manifest and leaves no orphaned config. Verified by a reset → init → reset round-trip.
5. When reset runs on a project `init` did **not** install mutation tooling into, manifests are **not touched** — the widening is strictly conditional on prior install evidence.
6. Mutation tools absent at install time (network failure, user declines mid-flow) leave the project in a clean coverage-only state.

**Risks.** Risk #1 (init blast radius) — mitigated by opt-in + manifest-level reset. Risk #3 (stack matrix explosion) — mitigated by documenting Rust CC as a gap. **Ticket-specific:** widening reset's file-scope rule is a contract change on a historically tight skill. AC #5's conditional-removal rule is the guardrail.

---

### Ticket 4 — Extend `testability-analyzer` with CC + module-size findings

**Goal.** Feed deterministic CC and module-size output into the existing agent as fields on existing barriers — never as the ranking driver.

**Prerequisites.** Ticket #1.

**Files to modify.**
- [skills/refactor/agents/testability-analyzer.md](../../skills/refactor/agents/testability-analyzer.md) — extend the output format (lines 40–57) with three new optional fields per finding: `CC:` (integer, from radon/ESLint/gocyclo), `Module size:` (LOC, from radon raw / `max-lines` / tokei), and `CRAP:` (rounded number — derived in-agent as `CC² × (1 − coverage)³ + CC` when both CC and coverage envelopes are present for the same function/file). Append a rule: findings are still ordered by testability impact, not metric value.

**Acceptance criteria.**
1. When the deterministic tool is **present**, findings include the new fields with concrete integer values.
2. When the deterministic tool is **absent** (ticket #1 `absent: true`), findings omit the fields entirely — existing output format unchanged, no error, no placeholder.
3. Agent's High/Medium confidence bar, max-15 findings limit, and read-only constraints (from [references/shared-agent-constraints.md](../../references/shared-agent-constraints.md)) remain intact.
4. A finding is **never created solely because** CC, module-size, or CRAP crossed a threshold. Existing structural-barrier focus (lines 22–33) remains the sole trigger.
5. Example output in the agent markdown updated to show both the with-metrics and without-metrics shapes.
6. **CRAP derivation:** the agent computes `CRAP = CC² × (1 − coverage)³ + CC` only when **both** the CC envelope (this ticket) and the coverage envelope (existing harness output) are present and resolvable to the same function/file. If either input is missing for a given finding, the `CRAP:` field is omitted — never zero, never a placeholder. No external tool dependency for CRAP; no Java-only path; no addition to the per-stack matrix.

**Risks.** Risk #5 (metric-driven churn) — AC #4 is the direct mitigation; CRAP is treated identically to raw CC, never as a ranking driver. Risk #6 (precedent) — resolved by ticket #1 landing first.

---

### Ticket 5 — New `dependency-analyzer` agent under `skills/refactor/agents/`

**Goal.** Add a new refactor-family agent that consumes dependency-structure tool output and emits findings following the ticket-#1 contract.

**Prerequisites.** Ticket #1.

**Files to create.**
- `skills/refactor/agents/dependency-analyzer.md` — structure mirrors [skills/refactor/agents/testability-analyzer.md](../../skills/refactor/agents/testability-analyzer.md) (frontmatter with `name`, `description`, `model`, `tools`; reads `.claude/CLAUDE.md`, coding guidelines, `shared-constraints.md`).

**Files to modify.**
- [skills/refactor/SKILL.md](../../skills/refactor/SKILL.md) — register the new agent in whatever discovery mechanism the skill uses for its four sibling agents today (exact hook confirmed during implementation).
- [skills/refactor/README.md](../../skills/refactor/README.md) — add a one-line row for the new agent in the agents-list section.

**Acceptance criteria.**
1. Agent emits findings in the same File/Category/Confidence/Issue/Current/Suggested format as the existing four refactor-family agents (consistent with `shared-agent-constraints.md` — max 15 findings, High/Medium only, read-only tools).
2. Agent consumes dependency-tool output via the ticket-#1 envelope (`findings[]`, `summary`). Does not shell out directly.
3. Findings flag **import cycles** and **boundary violations** (e.g. `import-linter` contract failures, `dependency-cruiser` forbidden-rule violations). Does not flag any non-violation — graph shape alone is never a finding.
4. Absence handling inherited from ticket #1: missing tool → zero findings with an informational note, never an error.
5. Agent is discoverable/invocable by the refactor skill the same way its four siblings are — verified by running the skill end-to-end in a test project with `pydeps` + `import-linter` installed.

**Risks.** Risk #5 (metric-driven churn) — AC #3 (violations only, never raw graph shape). Risk #6 (precedent) — resolved by ticket #1.

---

### Ticket 6 — Optional opt-in advisory surfacing in `test-guardian`

**Goal.** Allow the skill-scoped test-guardian to optionally surface CC / cycle / module-size findings during `/optimus:code-review`, behind an explicit flag. Default off — review output stays noise-free.

**Prerequisites.** Tickets #1, #4, #5.

**Files to modify.**
- [skills/code-review/agents/test-guardian.md](../../skills/code-review/agents/test-guardian.md) — add an **Optional Static Analysis** output block, rendered only when the review flag is set and ticket-#1 envelopes are present. No existing structured slot — this ticket defines it.
- [skills/code-review/SKILL.md](../../skills/code-review/SKILL.md) — add the opt-in flag (name decided inside the ticket). Default: off.

**Acceptance criteria.**
1. With the opt-in flag **off** (default), review output is byte-identical to today's output on the same diff.
2. With the flag **on** and deterministic envelopes available, review output includes the new block — CC, cycle, module-size — formatted consistently with the agent's existing File/Category/Confidence sections.
3. With the flag **on** but no envelopes available, the block is omitted silently (no "N/A" placeholder).
4. The plugin-level [agents/test-guardian.md](../../agents/test-guardian.md) (the comprehensive base definition) is **not** modified — only the skill-scoped specialization.
5. The "lean opt-in" rationale (from the design's Open Questions) is documented inside the skill-scoped agent markdown so future maintainers understand the default.

**Risks.** Risk #5 (metric-driven churn) — mitigated by the opt-in default. None of the new surfaced values gate PR approval.

---

### Ticket 7 — README CI-integration section

**Goal.** Add a "CI integration" section to the root `README.md` with a sample GitHub Actions workflow fragment that runs the coverage-harness and (opt-in) the mutation mode.

**Prerequisites.** None. Can land after ticket #2 ships the mutation mode; the fragment handles the coverage-only case too.

**Files to modify.**
- [README.md](../../README.md) — new "CI integration" section; sample GitHub Actions fragment calling the harness CLI.

**Acceptance criteria.**
1. Sample workflow runs successfully against the current harness CLI (verified by dropping it into `.github/workflows/` in a throwaway fork and watching it go green).
2. Sample includes **both** a coverage-only invocation and a mutation-enabled invocation, clearly labelled.
3. Section explicitly states that no `/optimus:ci` skill exists today and links to the relevant skill docs for per-project customization.
4. Section fits under the existing README structure without duplicating content elsewhere.

**Risks.** None from the design Risks table. Ticket-specific: example-workflow rot — mitigated by keeping the fragment short and pointing at skill docs for authoritative detail.

---

### Ticket 8 — Extend interactive deep mode with mutation-plateau (added 2026-04-27)

**Goal.** Allow `/optimus:unit-test deep mutation` (no `harness`) to drive Claude's in-conversation iteration loop with a mutation-score plateau as a peer to the existing coverage-plateau termination condition.

**Scope.** Interactive deep mode only. Harness mode is already covered by Ticket #2; normal mode (single-pass) remains out of scope by design — no convergence loop to plug into.

**Prerequisites.** Ticket #1 (envelope contract). Ticket #2 (per-stack mutation adapters and the `coverage-harness-mode.md` mutation-plateau definition — Ticket #8 reuses the same `|Δ| ≤ 1pp` threshold and adapter wrappers).

**Files to modify.**
- [skills/unit-test/SKILL.md](../../skills/unit-test/SKILL.md):
  - Step 1 arg parsing (lines 14–27): accept `mutation` after `deep` (without `harness`). Currently rejected — Ticket #2 AC #7 enforces that.
  - Step 1 deep-mode state init (lines 96–103): add `accumulated-mutation-history = []` peer to `accumulated-coverage-delta`.
  - Step 4 deep-mode loop (lines 241–280): add a new termination condition between current #3 (coverage plateau) and #4 (cap reached): "**Mutation plateau** — mutation tool is available AND `|iteration-mutation-delta| ≤ 1pp` for two consecutive iterations → stop." Use the same shape as the coverage-plateau check.
  - Step 4 per-iteration: invoke the stack's mutation adapter via the Ticket-#1 envelope, parse `summary.primary_metric`, append to `accumulated-mutation-history`. Only when mutation flag is present.
  - Iteration report (lines 264–272): add a `Mutation: [score / not measured]` line peer to `Cumulative coverage`.
  - Cumulative report (lines 282–306): add `Mutation score delta` to the Summary block.

**Acceptance criteria.**
1. With `mutation` keyword **absent**, the deep-mode loop is byte-identical to today's behavior — Ticket #2's regression-guard discipline applies here too.
2. With `mutation` keyword **present** and the mutation tool available, the loop terminates on mutation plateau using the same `|Δ| ≤ 1pp` threshold defined in `coverage-harness-mode.md`. Two consecutive iterations within tolerance trigger termination.
3. With `mutation` keyword **present** but the mutation tool absent, the loop emits an informational warning and continues with the existing coverage-plateau / convergence / cap conditions only — never fatal (inherited from Ticket #1).
4. Mutation invocation is **diff-scoped by default** (matching Ticket #2). Full-run requires an additional explicit keyword.
5. Iteration report renders the per-iteration mutation score; cumulative report renders the cumulative delta.
6. Context-window pressure: if mutation invocation output exceeds a per-iteration budget (defined inside the ticket), the score is recorded but the raw envelope is dropped from in-conversation context to avoid quality degradation across iterations. Documented in the ticket.

**Risks.**
- **Risk #2 (mutation too slow)** — bites harder here than in Ticket #2 because interactive deep accumulates context across iterations. AC #4 (diff-scope default) is the primary mitigation; AC #6 (envelope drop) is the secondary.
- **Coverage-harness regression** is not in scope — Ticket #8 doesn't touch the harness — but the **interactive deep regression** (today's coverage-only deep-mode behavior must remain unchanged when `mutation` is absent) is its analog. AC #1 is the direct guard.
- **Ticket-specific:** the deep-mode loop is the most heavily instructed part of `unit-test/SKILL.md`. Adding a fifth termination condition + new state + new report fields touches lines 241–306 — review carefully against the comment at line 243 ("keep structure in sync with code-review/SKILL.md Step 9 and refactor/SKILL.md Step 8") to ensure the cross-skill structural parity is preserved.

