# Paper preparation and reproduction evaluation

This protocol tests whether paper-init's durable context improves faithful implementation and independently reproduced results when followed by **unchanged gauntlet**. It supplements the [general evaluation plan](evaluation-plan.md); its existing cases and historical baselines retain their original meaning. The candidate instructions, fixtures, and local oracle are evaluation infrastructure. The [implementation review](paper-reproduction-review.md#validation-and-remaining-evidence) records exploratory fixture runs and their limitations. The controlled repeated comparison below and real-paper replication comparisons remain **unperformed**. Neither structural checks nor this protocol establishes model optimization.

## Question and conditions

The main hypothesis is that a claim-to-requirement-to-experiment-to-evidence contract reduces consequential omissions and unsupported assumptions for a fresh implementing session. Separately test whether hierarchy, optional numeric weighting, and refresh/version instructions justify their extra context and maintenance cost.

| Condition | Preparation instructions | Implementation and review |
|---|---|---|
| A: baseline | `paper-init` at `dfb47f850e9aa155fa8dfe7298da5a656e20df05` | The same pinned gauntlet and supporting references in all conditions |
| B: full candidate | The implemented paper-init revision, empirical reference, acceptance contract, reconciliation, and refresh rules | Identical runner, task, source access, resources, and user authorization |
| C: minimal contract | Baseline plus one compact claim/protocol/acceptance/evidence table and a handoff naming it; no new hierarchy, numeric scoring, or refresh machinery | Identical runner and settings |

Construct C in a separate experiment directory and save its complete diff and hashes before trials. It is an explicit competing design, not an automatic deletion of unrelated baseline safeguards. Leave acquisition, source transcription, uncertainty handling, dataset verification, scope decisions, and repository safeguards intact in every condition. Record B's actual commit after implementation; a dirty candidate requires the base commit, complete patch, and hashes of all loaded files. Never identify a condition only by its release version or cache directory name. Verify that gauntlet and its transitive supporting references have identical hashes across A/B/C.

Compare A/B/C as complete workflows first. If B helps, use separate one-factor comparisons for weighting, experiment-file splitting, or an additional instruction. Do not attribute a whole-candidate effect to one sentence. Optional weights are not required for every fixture: record whether each generated bundle uses them and evaluate their value only on cases with enough independent requirements for weighting to matter.

## Settings and trial preparation

Use **GPT-6 Astra (`gpt-6-astra`) in Codex** and **Claude Fable 5.1 (`claude-fable-5-1`) in Claude Code**, the targets named by the repository's general protocol. Pin actual host builds and model identifiers returned by the runtime; an unavailable target is an unperformed run, never a silent substitution. Confirm invocation and plugin enumeration through the supported host flow. CLI, desktop, and cloud are separate support observations.

Within each host/model, hold source bytes, task text, fixture starting commit, tools, sandbox, authentication/access, hardware, network policy, enabled agents, effort, and experiment limits constant. Use the same effort supported by that runtime, initially `high` as specified in the general plan. Do not equate equal effort labels with equal computation across models. Use isolated authenticated host configuration without copying personal credential files into fixtures, and fresh sessions without inherited memory or conversation.

Pre-register task-level preparation, implementation, and replay wall-time/compute limits and any service-spend cap. Allocate inexpensive fixture stage budgets within the global observation cap in [cases.json](../test/evaluations/cases.json); real-paper trials need their own declared budgets before condition assignment. Give identical stage budgets to each condition and also report total cost. A preparation-stage gain cannot hide an increase in total work. An external evaluator may interrupt at a budget limit and record `timed_out`; this is measurement censoring, not a new gauntlet stopping rule. Preserve partial work and retain every assigned trial in the denominator.

Randomize order using a recorded seed. Start with **five independent trials per task, model, and condition**. This is a pilot; expand to resolve variable outcomes or small differences. Judge artifacts blind to condition where practical and record when artifact formats reveal the condition. Score using the pre-registered task oracle, not the generated acceptance file alone. Preserve failed, blocked, interrupted, and timed-out attempts.

## Three separately observed stages

1. **Preparation:** Copy only the case's model-visible fixture into a disposable repository. Invoke the selected paper-init with the exact case task. Supply any scope or access decisions through the same script of actual user answers in each condition. Record interventions instead of inventing an answer or treating elapsed time as authorization. Save the full resulting bundle, question/decision record, final handoff, source identities, diff, and host events. A blinded reviewer scores source-grounded coverage and whether preparation avoided implementation or stack setup.
2. **Fresh implementation:** Snapshot the prepared bundle and start a fresh session in an identical project. Supply only the saved bundle, its saved handoff, and normal project/host instructions; do not copy the preparation conversation or reviewer notes. Task facts and scope decisions must be recoverable from the bundle. Use the same pre-registered operating authorization for gauntlet in every condition. Reacquire gitignored data through the supplied instructions with the same access policy. Invoke the pinned gauntlet through its supported host path. Pin the actual accepted bundle revision and retain its referenced protocols for the run. Save builder/critic remits, evidence and verdicts, integration review, tests, commits, final state, and actual stopping reason.
3. **Independent replay:** Freeze the implementation submission, then have a separate evaluator reconstruct the declared environment, acquire permitted inputs, and run the documented entrypoint. Preserve dependency installation output, code/config/data identities, command, process exit status, logs, raw measurements, and regenerated aggregates. Compare against the independent source-based oracle and the selected-scope contract. Disclose any unavailable input or environment recreation step. A successful existing-session run alone does not satisfy independent reproduction.

Paper-init's `[verified]` preparation facts concern acquired files and extracted facts; they do not establish experimental success. Score development, execution, and reproduced results separately. In all stages, retain original reported targets independently of selected scope. A reduced-scope success can satisfy its explicit selected target while full reproduction remains unverified.

## Cases and evidence boundaries

The executable case definitions are in [cases.json](../test/evaluations/cases.json): `paper-deterministic`, `paper-stochastic-protocol`, `paper-blocked-data`, `paper-reduced-scope`, `paper-refresh`, `paper-fresh-clone`, and the three `gauntlet-*` controls. The synthetic [paper fixture](../test/evaluations/fixtures/paper-replication) supplies a small deterministic recurrence (E1), repeated stochastic estimator (E2), and proprietary extension (E3), with supporting methods and a clarification. It is fictional and deliberately cheap: use it to test omissions, handoff, and numerical replay without presenting it as research performance. E3's unavailable input is deliberate; the ordinary core cases select E1/E2 and exclude E3 explicitly. Core success is not full-paper reproduction. Keep [reviewer notes](../test/evaluations/paper-review.md), the scorer, and case/grader metadata outside the model-visible project. Visible source requirements and ordinary acceptance criteria remain available to the agent; evaluator answer keys are held separately to prevent leakage.

| Case family | Evaluation target | Evidence needed |
|---|---|---|
| Deterministic computation | Correct recurrence, baseline and ablation; computed output rather than copied targets | New replay outputs and independent numerical comparison |
| Repeated stochastic estimator | Specified data, repeats, seeds, aggregation, and interpretation of variability | Per-run measurements and recomputed summary; source/protocol review |
| Supplement, citation, and clarification | Load-bearing inherited methods and explicit correction survive the bundle | Source-backed requirements and linked resolved assumptions |
| Protocol trap | Wrong split, preprocessing, selection, metric units or aggregation cannot pass on score alone | Oracle checks plus code and data-path inspection |
| Blocked input / reduced scope | Preparation remains useful; blocked/full/reduced claims remain distinct | Actual access evidence, preserved original target, authorized scope, calibrated completion language |
| Refresh / fresh clone | Stable IDs and decisions persist; changed criteria are visible; dependencies are recoverable | Before/after bundle and metadata, preserved runtime artifacts, new-session acquisition record |
| Visual non-paper task | Existing visual bar and independent critics still operate | Rendered artifact, critic evidence and exact final verdict, integration evidence |
| Behavioral non-paper task | Real execution and public behavior remain the bar | Targeted execution and regression checks, no paper-specific required artifacts |
| Integration failure | Passing pieces do not authorize a broken whole | A seeded cross-piece failure detected in integration review |

Use [gauntlet controls](../test/evaluations/fixtures/gauntlet-controls) as a bounded starting point. Also exercise a plateau followed by user steering/resume, explicit user stop, a dirty tree with user-owned edits, fixed critic remits, and milestone commits. Review actual agent contexts to establish critic independence; merely counting agents does not prove it. Gauntlet must not acquire a new plateau exit or paper-specific default, and a result score must not waive tests or integration review.

The synthetic fixtures cannot establish generalization to long papers or accelerator workloads. Before making that claim, add pinned real-paper cases: a small CPU simulation, a modest stochastic ML experiment with baselines/ablations, a citation-dependent method, and a full/reduced accelerator comparison where compute is actually available. Pre-register each paper version, supplements, public clarifications, authorized reuse policy, selected claims, data revisions, and evidence-based tolerances. Use independently reviewed requirements and include material appendix experiments unless explicitly excluded. The representative PaperBench rubrics can inform coverage without becoming an unreviewed oracle for a different task.

## Local replay and structural checks

The maintained local replay oracle has this interface, run from the plugin checkout after an implementation exists:

```text
python test/evaluations/paper_score.py "<submitted-project>" reproduce.py --evidence "<new-output-directory>"
python test/evaluations/paper_score.py "<submitted-project>" reproduce.py --evidence "<new-output-directory>" --scope deterministic
```

These commands are specific to the synthetic fixture, whose submitted relative Python entrypoint must support the documented `--config` and `--output` arguments. Substitute its actual filename. The default scope is `core` (E1/E2); `deterministic` selects E1. Choose the scope from the original case task before evaluating, never to hide a failed claim. The scorer supplies fresh canonical and parameter-perturbed configurations and new JSON output paths in copied submissions, invokes the calling Python interpreter with `-E -s`, and compares observed numerical outputs with its independent calculation. Its `--timeout` is a per-subprocess limit (30 seconds by default), separate from model-stage budgets. It preserves the copies, configs, output, logs, and `report.json` in the required new evidence directory outside the submission. Inspect that report and the process status: development requires human review, and `ready_for_review` does not mean replicated. Do not impose this filename, JSON schema, Python dependency, or CLI shape on ordinary paper-init output.

The scorer's fresh output paths and omission of `runs/`, caches, and local environments avoid accepting an old run directory as fresh execution evidence. It still uses the calling Python/runtime environment; **it is not a hermetic environment recreation or a security sandbox**. Execute submissions under the evaluation host's normal sandbox in a disposable workspace. A trusted evaluator must separately reconstruct the declared environment for full replay evidence. The scorer does not establish scientific fidelity, source provenance, meaningful development tests, critic independence, or semantic completion honesty. Those require the reviewer procedure and recorded artifacts.

Run focused oracle tests during development:

```text
python -m pytest test/test_paper_evaluation.py
```

Then run the repository's standard gates from [CONTRIBUTING.md](../CONTRIBUTING.md). Structural checks should cover valid fixture metadata, links and IDs, route preservation, acceptance-reference contracts, scorer failure propagation, and intentionally wrong/stale submissions. Avoid matching ordinary skill prose. A parsed table or a passing static test cannot demonstrate that a model reads sources, executes experiments, or preserves scope.

Seed adverse submissions for reviewer calibration: unexecuted but plausible code, staged metrics, stale artifacts, missing baseline/ablation conditions, wrong seeds or aggregation, a better score from an incorrect protocol, and a reduced-scale run mislabeled as full reproduction. Evaluate the scorer against cases within its stated contract and use human review for the remainder. Do not silently broaden its numeric pass into an end-to-end pass.

## Scoring and adoption

Before viewing candidate outputs, an independent reviewer prepares a claim and protocol checklist from the original sources. Mark each requirement's source, importance, selected-scope disposition, and evidence type. Two reviewers independently score a representative subset and all disputed completion claims; adjudicate disagreements with cited evidence. Report agreement and false-pass/false-fail examples. If using a model judge, pin its model/prompt and compare it with those human labels; its verdict is an observation rather than ground truth.

| Measure | Scoring rule |
|---|---|
| Preparation coverage | Source-supported selected claims with complete method/protocol/acceptance/evidence links divided by the independently identified selected claims; list omissions |
| Unsupported assumptions | Count consequential unsupported assertions, invented clarifications, and unlabeled defaults; preserve their consequences |
| Fidelity | Review methods, baseline fairness, data and preprocessing, evaluation, randomness, and selection against source requirements |
| Development / execution / results | Report separate verified fractions and unresolved/blocked counts; never substitute code coverage for results |
| Scope honesty | Count false full-reproduction claims, silent exclusions, weakened tolerances, and invalid transfer from reduced scale |
| Refresh / handoff | Record lost decisions, changed IDs without mapping, mutable active bars, unrecoverable inputs, and reliance on prior conversation |
| Gauntlet invariants | Record independent critics, fixed remit, evidence inspection, real execution, integration review, green tests, repository preservation, and actual stopping reason |
| Cost | Report stage and total latency, tokens and service/compute costs only where exposed, plus intervention count and reviewer time |

Optional numeric summaries use fixed reviewer-owned importance weights, not candidate-chosen weights. Report original-scope and selected-scope denominators and development/execution/result scores separately. Unknown or unverified requirements remain visible and do not earn verified credit. Mandatory requirements cannot be discharged by a high weighted average. Paper reproduction means meeting the justified target and fidelity requirements; scientific outperformance is unnecessary and cannot excuse protocol violations.

Preserve the general plan's metadata and add these fields per trial; `null` means unavailable, and an empty record is not a result:

```text
paper_source_revision, source_hashes, addendum_hashes, reference_reuse_policy,
condition_patch_hash, loaded_reference_hashes, gauntlet_hashes,
oracle_revision, oracle_hash, scope_decision, original_scope_ids, selected_scope_ids,
bundle_revision, acceptance_revision, handoff_hash, submission_revision,
stage_budgets, actual_stage_times, runtime_environment, data_config_identities,
development_observations, execution_observations, result_observations,
unverified_ids, blocked_ids, excluded_ids, false_completion_claims,
reviewer_labels, disagreements, adjudication, replay_command, replay_exit_status,
replay_report_path, raw_evidence_paths, interruptions, actual_stopping_reason
```

Publish per-trial outcomes and distributions by task and model/host, including negative results. Adopt the full contract on evidence of repeated gains in source-grounded coverage and independent reproduction without increased unsupported assumptions, false success, user-work loss, or weakened gauntlet invariants, and with acceptable total cost. Prefer C or retain baseline behavior where richer instructions add cost without useful evidence. Small or mixed pilot effects require more trials; structural correctness fixes and behavioral-performance claims are distinct decisions.

## Rationale and deliberately unadopted benchmark rules

PaperBench separates development, execution, and result requirements, uses weighted hierarchies, and reproduces submissions before judging. Its Code-Dev proxy correlated only weakly with full replication for o1 (`r = 0.48`). JudgeEval's o3-mini-high F1 was `0.83` overall, with different reliability by requirement type. These findings motivate distinct outcomes and reviewer calibration; they do not predict this plugin's performance on current models. [PaperBench, sections 2.2-2.6, 4 and Appendix G](https://arxiv.org/html/2504.01848v3)

The official [requirement representation](https://github.com/openai/frontier-evals/blob/51052cede8cc608f95bb00346635e03759013e5a/project/paperbench/paperbench/rubric/tasks.py), [reproducer](https://github.com/openai/frontier-evals/blob/51052cede8cc608f95bb00346635e03759013e5a/project/paperbench/paperbench/reproduce.py), and [judge](https://github.com/openai/frontier-evals/blob/51052cede8cc608f95bb00346635e03759013e5a/project/paperbench/paperbench/judge/simple.py) make the evidence distinction concrete. [Stochastic Interpolants](https://github.com/openai/frontier-evals/blob/51052cede8cc608f95bb00346635e03759013e5a/project/paperbench/data/papers/stochastic-interpolants/rubric.json) and [Robust CLIP](https://github.com/openai/frontier-evals/blob/51052cede8cc608f95bb00346635e03759013e5a/project/paperbench/data/papers/robust-clip/rubric.json) are representative coverage examples. Author addenda clarify methods and scope; see [Stochastic Interpolants](https://github.com/openai/frontier-evals/blob/51052cede8cc608f95bb00346635e03759013e5a/project/paperbench/data/papers/stochastic-interpolants/addendum.md) and [All-in-one](https://github.com/openai/frontier-evals/blob/51052cede8cc608f95bb00346635e03759013e5a/project/paperbench/data/papers/all-in-one/addendum.md). Preserve source conflicts: the [Robust CLIP addendum](https://github.com/openai/frontier-evals/blob/51052cede8cc608f95bb00346635e03759013e5a/project/paperbench/data/papers/robust-clip/addendum.md) and rubric disagree about a stock-image requirement, as documented in the [review](paper-reproduction-review.md#primary-source-rationale).

Ordinary paper-init usage keeps acceptance criteria visible and allows reference implementations with provenance and the user's reuse policy. Hidden benchmark rubrics, from-scratch restrictions, fixed A10 hardware, Bash entrypoints, and time limits are not production defaults. A run using different access or grading rules is PaperBench-inspired, not a benchmark-comparable PaperBench score. These distinctions follow the benchmark's stated task boundaries. [PaperBench, section 2.1 and Appendix A](https://arxiv.org/html/2504.01848v3)

Official OpenAI guidance was checked on **2026-09-11**. [Build skills](https://learn.chatgpt.com/docs/build-skills) supports focused scope, explicit outputs, concise descriptions, and progressive disclosure. The candidate therefore keeps the main skill focused on preparation and puts empirical details in a conditional reference. [Latest-model guidance](https://developers.openai.com/api/docs/guides/latest-model) targets **GPT-6 Astra** and discusses instruction conflicts, unnecessary clarification, delegation, and verification overhead. These are hypotheses to measure under pinned settings, not reasons to weaken necessary checks or import API-specific configuration into Claude Code. Preserve supported host invocation and metadata conventions; current documentation does not establish that this candidate is optimized for any model.
