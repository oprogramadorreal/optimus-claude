# Paper-init implementation review

Reviewed 2026-09-11. The result strengthens paper-init's durable acceptance
bar while preserving all gauntlet files. This document distinguishes design
inspection, executed checks, and still-unproven performance hypotheses.

## Destination, sources, and context

Destination began clean at `dfb47f850e9aa155fa8dfe7298da5a656e20df05` on
`master`, in `E:/workspace/claude-code/optimus-claude`. Implementation uses
`feat/paper-reproduction-contract` in that same worktree. No source branch was
merged or cherry-picked. Both references remain intact.

`git worktree list --porcelain`, merge bases, logs, staged/unstaged diffs, and
status including untracked/ignored files established:

| Source | Actual path under `C:/Users/smscp/.herdr/worktrees/optimus-claude/` | Branch / HEAD | Work relative to baseline |
|---|---|---|---|
| Claude Code | `worktree-rapid-field-dd56` | `worktree/rapid-field-dd56` / `c2e6bbacd1797c74b2e7544af70c96316f7d9eed` | One task commit, 8 files; no staged, unstaged, or relevant untracked work |
| Codex | `worktree-lucky-valley-78bc` | `worktree/lucky-valley-78bc` / `ad2bcc6caf42ff7c9245790be805d54290cb7a20` | One task commit, 24 files; no staged, unstaged, or relevant untracked work |

Both share the destination's initial HEAD as their merge-base; there is no
starting-point difference or unrelated branch change to reconcile. Ignored
source content was test/Python cache output, not additional proposals. Sources
were inspected read-only with optional Git locks disabled; checks ran here or
in disposable fixtures. Git 2.36.1 rejected command-local ownership exceptions,
so reads used a temporary configuration with exactly these trusted paths, not
a change to the user's global configuration.

Herdr was available (`HERDR_ENV=1`). Installed CLI help, workspace/pane lists,
agent lists and `agent get` resolved Claude to `w9:p1` and Codex to `wC:p1`;
their reported working directories matched Git. Both were idle. Reads at 1000
and 5000 requested lines yielded partial terminal history, not complete exports.
The reported session IDs resolved to accessible native transcript files:

- Claude: `ad0c6172-4b24-4fc0-8d03-7834191198cc.jsonl` in its corresponding
  `.claude/projects/C--Users-smscp--herdr-worktrees-optimus-claude-worktree-rapid-field-dd56/`.
- Codex: `.codex/sessions/2026/09/11/rollout-2026-09-11T05-40-05-01a08f9f-bc97-7951-8a01-db5554f11d1d.jsonl`.

Exposed task/assistant messages, implementation diffs, and repository artifacts
were read. Claude's proposal source is in its reported temporary session
`scratchpad/proposal.md`; Codex's proposal is in its transcript and its evaluation
protocol is committed. Both sessions contain later explicit implementation
authorization. Their prior proposal-only instructions are historical context.
No agent was interrupted, prompted to implement, or given approval-dialog input;
the accessible transcripts made a factual handoff unnecessary. Unexposed internal
context was not available or assumed. Source test reports remain claims unless
independently rerun here.

## Independent preliminary assessment

Recorded before reading source diffs, conclusions, or transcripts; only HEADs,
changed-file names and pane titles had been seen. The original record is in
the local evidence directory's `preliminary.md`.

Baseline strengths: acquisition provenance, full transcription, figures,
blocking citations, reference code, section-linked spec, reported protocol and
spread, cheap checks, sourced defaults, hardware feasibility, scoped refresh,
and a fresh-session handoff. Gauntlet already has fresh independent critics,
fixed remits, inspectable bars, execution and anti-staging requirements,
integration review, tests, feature-branch milestones and user-controlled stops.

Provisional gaps: targets mix scientific facts with project scope; no explicit
claim-to-requirement-to-experiment-to-evidence chain; development, execution and
reproduction lack separate statuses; fresh-environment replay and protection of
evidence/criteria across refresh are underspecified. Proposed a compact acceptance
artifact, source-linked IDs and priorities, justified tolerances, preserved
decisions, and unchanged gauntlet. Main uncertainties were useful granularity,
weighting cost, stale evidence, and feasibility of controlled model trials.

Later evidence favored Codex's conditional artifact over an unconditional
targets tree and separate empty ledger. Independent review found its
"mandatory" default ambiguous; the final contract explicitly requires every
selected requirement, with diagnostics identified separately before evaluation.

## Decision matrix

All alternatives were assessed on fidelity, coverage, evidence, fresh-session
usability, instruction cost, host compatibility, maintenance risk and validation.
The preliminary proposal was subject to the same skepticism as both sources.

| Decision | Baseline | Claude | Codex | Independent proposal / final choice and tradeoff |
|---|---|---|---|---|
| Bar artifact | Short targets section in spec | Always adds targets tree and empty decisions file | Conditional empirical acceptance, protocols by reference | **Adapt Codex**: one empirical bar; keep factual spec and existing decision history. Less duplication; more reading than baseline. |
| Scope | Reduced targets replace active spec targets | Original value beside reduced leaves, but unverifiable leaves automatically excluded | Original values preserved; blocked work selected until authorized exclusion | **Retain Codex** and provisional separation. Missing inputs cannot silently shrink success. |
| Coverage | Baselines and metrics present, matrix implicit | Adds seed/preprocessing/ablation detail | Source-linked experiment matrix, controls, selection, units, uncertainty | **Adapt Codex**, compact shared protocols. Guards concrete omissions at added context cost. |
| Progress structure | Cheap checks present | Small hierarchy, H/M/L and tier/scope mix | Hierarchy, stage/outcome/scope separation; optional weights | **Combine** compact hierarchy with Codex distinctions. Counts normally suffice; no mandatory scoring engine. |
| Tolerances | Reported spread, no comparison policy | Spread/interval suggested as tolerance; deviation can excuse overshoot | Predefined justified comparison; SD not automatically a tolerance | **Retain Codex**. Reject post-result waiver; uncertainty remains visible. PaperBench does not supply a universal margin. |
| Evidence | Targets indicate missing measurements | Entrypoint, logs, results report | Fresh environment, raw measurements, input identities, independent recomputation | **Adapt Codex**. Stronger evidence than file existence; compute/access costs remain. |
| Smoke runs | Paper-stated cheap checks | Every leaf must have a smoke path under an hour | Cheap checks cannot discharge full claims | **Omit Claude's universal limit**; useful smoke path with declared purpose/cost. |
| Decisions | Open questions plus metadata scope | Separate ledger never regenerated | Stable questions and durable decision history | **Adapt Codex**, preserve any existing separate ledger too. Avoid another mandatory file. |
| Refresh | Reapply scope, retain acquisition records | Stable IDs and ledger preservation | Prior bars/protocols/evidence preserved, commit/snapshot plus hash map | **Adapt** immutable pins; omit duplicate bar hashes. Retire IDs; revalidate affected evidence. |
| Reference reuse | Vendors reference, wording ambiguous about reuse | Same ambiguity | Permits inspection, retains ambiguous phrase | **Clarify independently**: preparation only vendors/inspects; later licensed reuse follows user scope. No benchmark code ban. |
| Exact source bytes | Calls sources pristine; Git conversion unspecified | Same | Adds exact hashes, conversion unspecified | **Adapt after observation**: narrow `-text` attributes for acquired originals. A fresh fixture clone changed LF to CRLF; the implementation recovered committed bytes. |
| Gauntlet | Established general loop | Skill unchanged, README bullet | Entire skill directory unchanged | **Retain baseline** byte-for-byte. Put reproduction interpretation in supplied bar. |
| Evaluation | General tests; no paper cases | Proposed trials, structural reports | Runnable synthetic oracle/tests and controlled protocol; no completed model trials | **Adopt infrastructure**, independently execute and label limits. More tests do not prove a better skill. |

Consequential source evidence is in Claude's `templates/targets.md` (comparison,
excluded scopes, smoke requirement), and Codex's
`references/empirical-reproduction.md` (scope, tolerances, evidence, refresh).
The final [skill](../skills/paper-init/SKILL.md) and
[empirical reference](../skills/paper-init/references/empirical-reproduction.md)
are the executable instructions, not this review.

## Primary-source rationale

PaperBench supports separate code/execution/result evidence, fresh reproduction,
importance-weighted partial progress, and explicit author clarifications. Its
Code-Dev/full-replication correlation for o1 was only `r=0.48`; automated judges
were imperfect. Rubric generation took expert iteration, and prompting changes
helped some tested models while hurting another. These historical findings
motivate our evidence distinctions; they do not validate this prompt or today's
models. [PaperBench §§2–5 and Appendices A, C, F–I](https://arxiv.org/pdf/2504.01848)

The official repository redirects to `openai/frontier-evals`. Inspected at
`51052cede8cc608f95bb00346635e03759013e5a`: [task representation](https://github.com/openai/frontier-evals/blob/51052cede8cc608f95bb00346635e03759013e5a/project/paperbench/paperbench/rubric/tasks.py),
[scoring](https://github.com/openai/frontier-evals/blob/51052cede8cc608f95bb00346635e03759013e5a/project/paperbench/paperbench/judge/graded_task_node.py),
[reproducer](https://github.com/openai/frontier-evals/blob/51052cede8cc608f95bb00346635e03759013e5a/project/paperbench/paperbench/reproduce.py), and
[judge](https://github.com/openai/frontier-evals/blob/51052cede8cc608f95bb00346635e03759013e5a/project/paperbench/paperbench/judge/simple.py).
These substantiate evidence categories and sibling weighting, but timestamps
and an entrypoint alone cannot establish honest computation. Input identities
and independent recomputation are engineering adaptations.

[Stochastic Interpolants](https://github.com/openai/frontier-evals/blob/51052cede8cc608f95bb00346635e03759013e5a/project/paperbench/data/papers/stochastic-interpolants/rubric.json)
uses approximate FID targets. [Robust CLIP's rubric](https://github.com/openai/frontier-evals/blob/51052cede8cc608f95bb00346635e03759013e5a/project/paperbench/data/papers/robust-clip/rubric.json)
and [author addendum](https://github.com/openai/frontier-evals/blob/51052cede8cc608f95bb00346635e03759013e5a/project/paperbench/data/papers/robust-clip/addendum.md)
even disagree about particular images; neighboring attack criteria differ as
well. Preserve conflicts rather than treating a rubric as infallible. Hidden
rubrics, from-scratch bans, fixed hardware/OS/filenames, and blanket appendix
exclusions are not ordinary paper-init defaults.

Official OpenAI guidance checked **2026-09-11**; requested pages resolved
directly. [Build skills](https://learn.chatgpt.com/docs/build-skills) supports
focused scope, explicit outputs and progressive disclosure. [Latest-model
guidance](https://developers.openai.com/api/docs/guides/latest-model) identifies
**GPT-6 Astra (`gpt-6-astra`)** and addresses instruction conflicts, unnecessary
clarification, delegation and verification overhead. The [catalog](https://developers.openai.com/api/docs/models)
also lists **GPT-5.6 Sol (`gpt-5.6-sol`, alias `gpt-5.6`)**, Terra and Luna.
Keep shared prompts and established host metadata; public `name` guidance does
not justify changing this repository's tested omission convention. Astra advice
is not evidence of equivalent Claude behavior or measured optimization.

## Original and final workflow

Original: acquire sources → transcribe/specify → check code/resources/data →
handoff spec targets → gauntlet compares real output to that bar.

Final: same acquisition and preparation, plus source-linked empirical acceptance
and explicit scope → reconcile after code/data findings → fresh session reviews
and pins criteria/protocols → unchanged gauntlet judges execution and verifiable
evidence against those criteria. Refresh retains prior criteria and evidence,
requiring revalidation for changed claims. No experimental code or stack setup
is produced during paper-init.

## Validation and remaining evidence

Local raw evidence lives under `evals/paper-synthesis/` (ignored evaluation
output, not shipped project artifacts). `evidence/` holds source research,
exposed transcript extracts, the preliminary assessment, check logs, instruction
size measurements, and the parent evaluator's `behavior-review.md`. Fixture
directories retain actual generated bundles, instructions, tasks, code and runs.
The [evaluation protocol](paper-reproduction-evaluation.md) specifies the stronger
controlled comparison still needed; these runs are exploratory, not that pilot.

| Validation actually performed | Outcome and evidence |
|---|---|
| Repository structural validation | `bash scripts/validate.sh`: 22 passed, zero failed; four jq-dependent groups skipped. Python JSON/manifest/version/deny-rule/hook-path checks passed separately (`evidence/structural.log`, `artifact-checks.json`). |
| Hook suite | `bash scripts/test-hooks.sh`: 410 passed, zero failed (`evidence/hooks.log`). |
| Full Python suite in isolated checkout | 715 passed, seven skipped, 261.59 seconds (`evidence/isolated-pytest.log`). Includes 19 real scorer tests; also independently ran those 19 in the destination. |
| Native Codex loader | CLI 0.154.0 enumerated all 21 skills with expected metadata/source hashes (`evidence/loader.json`); enumeration is not skill execution. |
| Baseline/candidate preparation | One fresh hosted-agent session each, identical fictional E1/E2 task and sources. Both retained the core protocol and E3 exclusion. Candidate added explicit acceptance/evidence/pinning instructions (`trials/A`, `trials/B`). |
| Fresh-session implementation | Candidate bundle committed and cloned in a disposable repo; new session implemented E1/E2 from the bundle/handoff. Data recovery exposed and documented Git line-ending conversion (`implementation/outcome.md`). |
| Independent replay and source review | Parent inspected runtime against paper/supplement and ran the external oracle: canonical and changed-input probes exited 0; development 1/1, execution 4/4, result 3/3 checks (`replay/report.json`). |
| Exact-byte Git mechanism | Fresh clone with `core.autocrlf=true` retained acquired original bytes under narrow `-text`; metadata remained normal text (`source-bytes/report.json`). |
| Refresh with actual prior evidence | Proposed A2 added sampled-record provenance without changing A1, code or run artifacts. Parent compared before/after bytes; prior IDs already existed, so the handoff calls for independent revalidation rather than manufactured fields or an automatic rerun (`refresh/outcome.md`, `parent-preservation.json`). |
| Blocked-data preparation | Full E1/E2/E3 remained selected; unavailable private data and unspecified E3 tolerance stayed explicit blockers. No substitute, silent exclusion or result claim (`adverse/paper-blocked-data/outcome.md`). |
| Reduced-scope preparation | Required E1 plus all three seed-3 diagnostic conditions; original E2 repeats/mean/SD preserved, singleton SD undefined/null, original E2/E3 unverified (`adverse/paper-reduced-scope/outcome.md`). |
| Non-paper gauntlet | One builder round, independent piece and separate integration critics passed public behavior/composition; original mixed staged/unstaged notes preserved (`gauntlet/outcome.md`). |

The first full pytest attempt stalled in the existing real-formatter integration
area and was stopped after over ten minutes, preserving its log. The successful
isolated run used the same tests and interpreter without a project `.venv` and
with formatter executables removed from PATH: three formatter tests therefore
skipped. The other skips concern POSIX filenames, a Windows-invalid quote in a
filename, Bash 3.2, and unavailable `pwsh`. No test was changed to make it pass.

The preparation pair used fresh hosted conversations with identical supplied
inputs/access and inherited runtime, not independently pinned native model/effort
telemetry. B's saved snapshot predates the source-byte rule, explicit non-empirical
selected-target fallback and metadata-location clarification; its empirical
reference is identical. Only B underwent implementation, so no comparative
implementation advantage was measured. The implementation trial did not execute
full gauntlet. Replay used fresh project copies and Python `-E -s` with reviewed
standard-library code, not a new VM or newly installed dependency environment.

Matched native Codex attempts requested `gpt-6-astra`, `high`, equal 600-second
limits, and identical tools/access. Both were blocked by policy on the first
required filesystem read before preparing a bundle (`native/A`, `native/B`).
Their process exit zero means an agent turn ended, not successful execution.
No native Claude behavioral trial completed. These are blocked observations,
not evidence of either prompt failing its scientific task.

The non-paper control allowed expanding `check.py`; it is not the registered
untouched-check variant. Critics independently tested the missing behaviors.
One passing round does not test retries, plateau/resume, explicit user stop or
browser rendering. All production gauntlet files remain unchanged, but that
alone cannot prove every interaction with a new supplied bar.

The refresh trial used actual retained run evidence with sampled IDs already
present, rather than the protocol's missing-ID canary variant. The new evidence
requirement stayed unverified pending independent linkage review; no historical
result was upgraded. This tests one preservation/revalidation path, not all
uncommitted, licensed-source, stale-link or active-critic refresh combinations.
The blocked and reduced preparations ran sequentially in one separate hosted
session with separate fixtures; they are adverse-case executions, not independent
repeated trials. Both preserved initial input bytes and prepared context only.
Their supplied snapshot differs from final solely in the clarification that
source originals intended for tracking includes newly acquired untracked files.
The non-empirical selected-target fallback was inspected but not model-tested.

Instruction cost remains material: baseline paper-init has 19,926 characters;
Claude's skill plus template 24,950; Codex's skill plus empirical reference
40,677; final skill plus conditional reference about 37,500. These count only
those files, not complete sessions or tokens. In the single preparation pair,
derived bundle output was 23,638 bytes for A and 33,070 for B, excluding acquired
originals. More explicit context may prevent omissions, but repeated trials must
show whether that benefit justifies reading and maintenance cost. Automatic
acceptance generation still requires source review; weights remain subjective.

Further evaluation should compare baseline, final and a minimal contract under
the protocol's repeated, pinned host/model conditions; include real papers with
ambiguous criteria, significant training, unavailable resources and source reuse.
Measure false reproduction claims, independent result fidelity, handoff omissions,
total cost, refresh mistakes, and general gauntlet stopping/visual controls. No
PaperBench score, model optimization or broad behavioral superiority is claimed.
