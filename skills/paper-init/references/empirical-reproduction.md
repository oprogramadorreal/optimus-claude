# Preparing empirical acceptance criteria

Read for papers with empirical claims. Write preparation artifacts only;
the implementing session chooses the stack, writes entrypoints, and runs
experiments. Apply the actual bundle root to every path, including nested
`papers/<slug>/` bundles.

## Contents

- [Scope and requirements](#scope-and-requirements)
- [Experiment protocols](#experiment-protocols)
- [Acceptance and progress](#acceptance-and-progress)
- [Execution evidence](#execution-evidence)
- [Fresh-session handoff](#fresh-session-handoff)

## Scope and requirements

Write one `acceptance.md`, under ~200 lines with linked overflow only when
needed. Include the source/acceptance revision, selected scope and resource
constraints, requirements, experiment protocols, evidence instructions, and
links to open decisions. This is a visible project bar, not a hidden rubric.
Keep paper facts canonical in `spec.md`; link its target IDs and precise
paper, supplement, citation, or clarification locations.

Inventory the empirical claims, tables/figures, baselines, and ablations,
including material appendix experiments. Group equivalent rows without losing
conditions. Default to the paper's empirical scope unless the user selected
less. Record exclusions and their reasons; unavailable or infeasible work
stays selected and blocked until a scope decision authorizes exclusion.
Keep the original targets beside any reduced-scope criteria. A published
baseline value is a reference comparison, not evidence that we reran it.

Group independently assessable requirements under claims or experiments,
using stable IDs, scientific importance (relative to siblings, not difficulty),
and dependencies. This assessment structure does not prescribe builder tasks.
Each requirement links its source, experiment, pass rule, and expected evidence
or explicit gap. Every selected requirement is required for completion;
optional diagnostics must be identified as such before evaluation.

Separate what the evidence establishes; do not require three repetitive rows
for every fact when one compact row can name the relevant checks:

| Stage | What must be checked | Evidence |
|---|---|---|
| Development | Method and protocol implemented faithfully | Code/config locations and focused method checks |
| Execution | Required path ran with the specified inputs | Observed exit status, complete logs, run manifest and outputs |
| Result | Run supports the selected claim under the agreed protocol | Raw measurements and independently recomputed comparison |

For example: `R1 — Table 2 / spec T1; high importance; E1 method, baseline
and ablation across the stated seed set; result depends on data/protocol
checks; compare using the sourced rule; evidence: E1 manifest, per-seed CSV
and recomputed table`. Fill from the paper, not this illustrative text.

## Experiment protocols

For each selected experiment, give a compact protocol plus its configuration
matrix. Share common procedures by reference. A baseline or ablation needs
its own conditions and evidence, not just a name in a list. Cover these when
applicable; mark unstated details and link affected open-question IDs:

| Area | Implementation-critical facts |
|---|---|
| Method | Equations/objective, architecture, initialization, optimizer/schedule, duration, stopping, checkpoint and hyperparameter selection |
| Data | Revision/identity, split and counts, preprocessing order, filtering, normalization, augmentation, leakage controls; link `dataset.md` |
| Controls | Baselines and ablations; rerun versus published comparison; tuning budgets and any protocol differences |
| Evaluation | Metric definition, units/direction, evaluator version, aggregation, inference/sampling settings, plotted quantities |
| Randomness | Seeds, repeats, pairing across methods, mean versus best run, SD/SEM/CI and what the interval describes |
| Comparison | Original target ID, project pass rule and justification, required method/data checks, unresolved criteria |
| Resources | Stated versus estimated compute, repeat/control costs, time, storage, access/services, supplied budget and reduced alternatives |
| Evidence | Future command/config interface, logs, raw measurements, derived outputs, and independent verification procedure |

Link sources instead of duplicating the transcription. Public errata and
author clarifications can resolve methods; a project assumption must remain
labeled as ours. Preserve conflicts and the rationale for resolving them in
`open-questions.md`. Routine defaults may unblock implementation within the
selected claim, but cannot authorize a different experiment or extra spend.

## Acceptance and progress

Define comparison rules before results are observed. Numerical equality is
appropriate only when the computation and precision justify it; otherwise
give a sourced or explicitly justified project tolerance. Reported SD is not
automatically a tolerance, overlapping error bars do not prove equivalence,
and no universal percentage applies. Preserve stochastic repeats, selection
rules, and the meaning of reported variability. For qualitative claims, name
observable properties, comparison conditions, and required figures.

An unresolved criterion stays an open decision. Settle it within the user's
scope before the first critic remit; do not choose a threshold after failure.
A better number from the wrong method, split, preprocessing, or selection
rule is a fidelity gap. An out-of-band result needs investigation; recording
a deviation does not waive the fixed rule.

Report stage, outcome, and scope separately, e.g. `result / unverified /
full scope` or `execution / passed / reduced scope`. Keep missing, blocked,
failed, and unverified requirements visible. Code inspection and smoke runs
can establish partial progress; they cannot stand in for reproduced results.

Counts by stage and importance normally suffice. If numeric partial progress
is useful for a large hierarchy, choose positive sibling weights before
implementation and justify their scientific importance as our judgment. A
leaf's effective weight is the product of normalized weights along its path;
only verified passes earn it. Report selected and original scope denominators
and stage breakdowns, retaining excluded/blocked work in original coverage.
Never use a weighted average to waive a selected requirement or declare a pass.

Put this interpretation in the generated bar, in tool-agnostic language:

> Passing this fixed bar means faithful reproduction of the explicitly
> selected scope under its method, protocol, result, and evidence criteria.
> Scientific outperformance is unnecessary. Every selected requirement must
> pass; weighted progress and labeled exclusions cannot hide a selected gap.
> Name the scope and unverified original claims in the result explanation.
> Changed scope or thresholds require a separately identified evaluation;
> they cannot narrow an existing critic's remit. The implementing loop's
> independent review, real execution, integration, repository checks, and
> stopping rules still apply. Blocked work does not create a new stop rule.

Gauntlet can then retain its exact `beats the bar` verdict without changing
its general behavior.

## Execution evidence

Require a documented platform-appropriate entrypoint and configuration that
reacquire allowed inputs, execute the selected experiments, and regenerate
metrics/figures. Plan this interface; do not implement it during preparation.
Separate training and evaluation where useful, declaring which the claim
requires. Offer a cheap smoke path where meaningful, with its limited purpose
and estimated cost; do not promise an arbitrary runtime or full-claim coverage.

Independent verification uses a fresh checkout and isolated environment with
declared dependencies and pinned versions where available. No hidden packages,
caches, undeclared files, or precomputed answers substituted for required work.
Declare permitted datasets, pretrained models, checkpoints, and services with
their role and acquisition record. Checkpoint-only evaluation does not verify
retraining. Do not prescribe Bash, Docker, or particular hardware universally.

Each run records code revision, config/data identities, environment, seeds,
full command, observed exit status, timing/resources, complete logs and raw
per-run measurements. An independent verifier inspects inputs and recomputes
aggregates/plots and the comparison. A self-reported success, plausible file,
timestamp, or log excerpt alone is insufficient. Preparation's `[verified]`
source checks do not establish execution. Preserve failed attempts and selection
history as well as successes. Map requirement IDs to actual evidence locations.

Keep small manifests and summaries durable. Large outputs may live outside Git
with stable locations, checksums, retrieval/access instructions, and availability
status. Missing evidence stays a gap. If clean replay cannot run, report exactly
what was inspected and what remains unverified.

## Fresh-session handoff

Put in the bundle index: review coverage against the sources and resolve
acceptance choices within the user's scope, then pin the actual committed bar
and all defining protocols/decisions before the first critic remit. A model's
draft is not an authoritative scientific rubric. Use an immutable snapshot
when Git does not retain the exact bytes. The pin names the source/acceptance
revision and its defining files; never invent a future commit hash.

Critic remits use snapshot paths or revision-specific retrieval commands,
not paths whose content a refresh can replace. Routine method decisions may
be resolved under that fixed bar and added to the decision history; changed
criteria need a separately identified evaluation. Later implementation commits
do not change the bar. A refresh preserves previous criteria and evidence,
identifies affected requirements, and requires revalidation before old results
can support changed claims. Apply the skill's preservation and license rules.
