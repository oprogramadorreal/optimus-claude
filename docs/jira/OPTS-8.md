---
source: jira
issue: OPTS-8
date: 2026-04-23
enriched-date: 2026-04-23
description-refresh-date: 2026-04-27
---

## Task: OPTS-8 — How to evaluate AI-generated code quality

### Goal
Evaluate how to incorporate Uncle Bob's AI code-quality criteria (mutation testing, cyclomatic complexity, module size, dependency structure) into the optimus-claude plugin, since test coverage is already covered.

### Acceptance Criteria
1. Produce an analysis of how the optimus-claude plugin currently works and where each of the four remaining criteria (mutation testing, cyclomatic complexity, module size, dependency structure) could be incorporated.
2. For **mutation testing** specifically, evaluate whether `init` should install a mutation-testing tool per stack (e.g., `mutmut` for Python) and whether `unit-test` should use it to guide test writing — mirroring the current coverage approach.
3. For **cyclomatic complexity**, evaluate alternatives: (a) a new `optimus:ci` skill to configure static-analysis tooling in CI, (b) having `code-review` perform the analysis directly, or (c) a combination — and describe how `code-review` / `refactor` would consume feedback from those tools to act on the code. Within this criterion, also evaluate whether the **CRAP metric** (Change Risk Anti-Patterns — `CC² × (1 − coverage)³ + CC`) makes sense for optimus-claude, given that it composes CC with the coverage signal the harness already produces.
4. Propose an approach for **module size** and **dependency structure** analysis.
5. Include a **risk analysis** of the proposed changes to avoid breaking current behavior.
6. Ensure proposals do not require a paid dependency (no hard dependency on commercial tools like SonarQube Server).
7. Deliver a recommendation prioritizing mutation testing (identified as the most important by the reporter) and deterministic static-analysis tools that feed back into existing skills.
8. Decide whether mutation testing lives inside `/optimus:unit-test` (reuses the coverage-harness pattern), inside a new `/optimus:mutation-test` skill, or both — and document the rationale. (from codebase analysis)
9. Establish a reusable "deterministic tool → agent feedback" reference in `references/` so CC, module-size, and dependency tools share one integration pattern. No such pattern exists today. (from codebase analysis)
10. Evaluate plugging CC/module-size findings into `skills/refactor/agents/testability-analyzer.md` before building a new skill, since that agent already enumerates structural barriers and measured hotspots map onto its output format. (from codebase analysis)
11. Document graceful degradation for each proposed tool — the skill must still work when the tool is absent, mirroring how `unit-test` handles missing coverage tooling. (from codebase analysis)

### Context
- Type: Story
- Status: Backlog
- Priority: Medium
- Assignee: Marco Souza
- Reference link in description: https://kodare.net/2016/12/01/mutmut-a-python-mutation-testing-system.html

### Key Decisions (from description)
- **Test coverage is already handled** — `init` installs coverage tools, `unit-test` uses them. No new work needed here.
- **Mutation testing is the top priority** — because it validates whether AI-generated tests are actually effective, not just present.
- **No paid tools** — static-analysis proposals must use free/open-source tools.
- **Safety first** — any proposal must include a risk analysis showing current behavior won't break.
- **CRAP metric** (added to description on 2026-04-27) — evaluate whether CRAP makes sense alongside raw CC. Decision recorded in design doc: derive in-agent from CC + coverage; no new tool, no new ticket — folds into ticket #4.

### Refined Description
Deliver a design document (not code) that answers, for each non-coverage Uncle-Bob criterion, **where** it plugs into optimus-claude's existing architecture, **how** graceful degradation works when the underlying tool is absent, **what** the uninstall path looks like via `/optimus:reset`, and **what** the per-criterion risk profile is.

The codebase analysis reveals a precondition the JIRA description didn't state: **there is no existing pattern for a skill/agent to invoke a deterministic tool and consume its output**. Every agent today is LLM-driven. The single most consequential decision in this study is therefore not "which tool for which criterion" — it is **the design of the shared `references/deterministic-tool-consumption.md` pattern that every subsequent tool will inherit**. Land that first, then retrofit each criterion onto it.

Scope boundary: this story ends when the design is approved and next-step JIRA tickets exist for implementation. No source-modifying work for mutation testing, CC, module size, or dependency analysis should happen under OPTS-8 itself.

### Suggested Approach
Work in this sequence. Earlier items are prerequisites for later ones — do not parallelize.

1. **Design the shared tool-consumption reference** (`references/deterministic-tool-consumption.md`). Decide: tool detection, JSON-vs-text parsing contract, error/absence handling, fit into the `harness_common` schema. This is the foundation; a bad design here compounds across every future tool.
2. **Design the mutation-testing integration** on top of that reference. Decide: new `/optimus:mutation-test` skill vs. extension inside `/optimus:unit-test`; scoping (diff-based vs. full-run) to keep feedback loops usable; convergence signal for the coverage-harness (mutation-score plateau).
3. **Design CC + module-size integration** as a feed into `skills/refactor/agents/testability-analyzer.md` rather than a new skill. Define the deterministic input (`radon` / ESLint complexity), ranking heuristics (avoid metric-driven churn), and the optional review-time flag in `skills/code-review/`.
4. **Design dependency-structure integration** as a new `dependency-analyzer` agent under `skills/refactor/` consuming `pydeps`/`import-linter` or `dependency-cruiser`/`madge`. Define which findings are informational and which block refactor proposals.
5. **Decide on `optimus:ci`**. Evaluate whether a dedicated CI-config skill is worth the maintenance cost vs. shipping detection inside existing skills plus sample workflow files in the README.
6. **Risk sign-off**. Re-read the Risks section below against each proposal. If any risk is unmitigated, the proposal is not ready to ship.
7. **Spawn implementation tickets** in JIRA, one per design section, so OPTS-8 itself remains the design record.

### Codebase Impact
Grouped by concern. This is a study; entries describe *candidate* plug-in points, not required edits.

**Mutation testing** (user-identified top priority)
- `skills/init/SKILL.md` + `skills/init/references/test-infra-provisioning.md` — add mutation-tool installation per stack (mutmut for Python, stryker for JS/TS) alongside coverage. Tied to AC #2.
- `skills/unit-test/SKILL.md` — add a mutation-run step, OR spawn a dedicated `/optimus:mutation-test` skill. Tied to AC #2, #8.
- `references/coverage-harness-mode.md` — extend (or mirror) with a mutation-score plateau as a convergence signal. Tied to AC #2.

**Cyclomatic complexity & module size**
- `skills/refactor/agents/testability-analyzer.md` — feed deterministic findings from `radon` (Python) or ESLint's complexity rule (JS/TS); agent currently uses LLM-only heuristics. Tied to AC #3, #4, #10.
- `skills/code-review/agents/test-guardian.md` — optional: opt-in surfacing of CC / cycle / module-size findings during review (default off). Tied to AC #3.
- **CRAP metric (derived, no new tool)** — once CC and coverage envelopes are both present (post ticket #4), `testability-analyzer` can compute `CRAP = CC² × (1 − coverage)³ + CC` per function inside the agent and surface it as an additional advisory field. No new dependency; no Java-only tool; no change to the per-stack matrix. Tied to AC #3.

**Dependency structure**
- `skills/refactor/` — new `dependency-analyzer` agent consuming `pydeps`/`import-linter` (Python) or `dependency-cruiser`/`madge` (JS/TS). Tied to AC #4.
- `skills/code-review/` — optional: surface new cycles / boundary violations introduced by a PR. Tied to AC #4.

**Shared infrastructure (biggest gap)**
- `references/` — new `deterministic-tool-consumption.md`. No such pattern exists today; every agent is LLM-driven. Tied to AC #1, #9.

**CI route**
- `.github/workflows/` + potential new `skills/optimus-ci/` — evaluate whether a CI-config skill is worth building, or whether baking detection into existing skills plus sample workflow files covers the need. Tied to AC #3.

### Risks
- **`init` blast radius** — adding mutation-tool installation extends writes into user's `pyproject.toml` / `package.json` dev deps. Needs the same opt-in pattern and `/optimus:reset` coverage already used for coverage tooling.
- **Mutation runs are slow** — mutmut/stryker can take minutes-to-hours. Naive reuse of the coverage-harness loop would make `/optimus:unit-test` unusably slow. Must support diff-scoped / opt-in mode.
- **Stack matrix explosion** — coverage today covers roughly four frameworks. Mutation + CC + dependency tools per stack multiplies the matrix. Detection must stay stack-agnostic with graceful fallback (AC #11).
- **Harness JSON contracts** — `harness_common`, deep-mode, and coverage-harness share tight schemas. New metrics (mutation score, CC, cycles, module size) each require schema additions and can break existing convergence logic for `unit-test` and `refactor`.
- **Metric-driven churn** — CC thresholds are heuristics. Telling agents "refactor anything over CC > 10" can produce low-value refactors. Metric findings should inform agents, not drive them.
- **Precedent risk** — the first deterministic-tool-consuming agent sets the pattern every subsequent tool inherits. Argues for landing the shared reference (AC #9) before any tool-specific agent.

### Implementation Tickets

The full design lives in [docs/design/2026-04-23-evaluate-ai-code-quality.md](../design/2026-04-23-evaluate-ai-code-quality.md). OPTS-8 is the design record; per-section work is tracked in these follow-up tickets (all in Backlog as of 2026-04-27):

| Ticket | Title | Prerequisites |
|--------|-------|---------------|
| OPTS-10 | Create `references/deterministic-tool-consumption.md` shared contract | None — gates all others |
| OPTS-11 | Add deep-harness mutation mode to `/optimus:unit-test` (harness mode only) | OPTS-10 |
| OPTS-12 | Per-stack mutation-tool install in `/optimus:init` + `/optimus:reset` inverse | OPTS-10 |
| OPTS-13 | Extend `testability-analyzer` with CC, module-size, and CRAP findings | OPTS-10 |
| OPTS-14 | New `dependency-analyzer` agent in `skills/refactor/` | OPTS-10 |
| OPTS-15 | Optional opt-in advisory surfacing in code-review's `test-guardian` | OPTS-10, OPTS-13, OPTS-14 |
| OPTS-16 | README "CI integration" section with sample workflow | None (independent) |
| OPTS-18 | Extend interactive deep mode (`/optimus:unit-test deep mutation`) with mutation-plateau termination | OPTS-10, OPTS-11 |

OPTS-10 is the single hard prerequisite — every other ticket inherits its envelope contract. OPTS-16 is the only ticket that can land independently. OPTS-18 is the deferred interactive-deep companion to OPTS-11; both share the per-stack adapters and the mutation-plateau threshold definition. (OPTS-17 was unrelated; JIRA allocated OPTS-18 as the next available key.) No source-modifying work happens under OPTS-8 itself.

### Scope Assessment
**Complex** — research/design study touching `init` (installers), `unit-test` or a new skill, `refactor` (new agents + tool plumbing), `code-review` (optional findings), `references/` (new shared pattern), and a possible `optimus:ci`. The JIRA issue has 7 stated criteria, which hints at medium, but the code reveals a missing shared integration pattern plus six affected areas — this lifts the effort into the complex bucket. Output should be a design/plan artifact with follow-up JIRA tickets, not a single implementation PR.
