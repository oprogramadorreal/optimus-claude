# Focused model evaluation plan

This is a reproducible evaluation protocol, not evidence that a prompt change improves model performance. The small fixtures in [test/evaluations](../test/evaluations/cases.json) supply known outcomes. They do not represent every repository, task, host, or long-running workflow.

For paper preparation, fresh-session implementation, independent replay, and
non-paper gauntlet controls, use the [paper reproduction protocol](paper-reproduction-evaluation.md).
The [implementation review](paper-reproduction-review.md) records the selected design and actual validation.

Use exactly **GPT-6 Astra (`gpt-6-astra`) in Codex** and **Claude Fable 5.1 (`claude-fable-5-1`) in Claude Code**. If a requested model, authenticated host, or necessary tool is unavailable, record the limitation and leave that run unperformed. Do not substitute another model or count an ordinary development conversation as a controlled trial. Model capabilities and host features are separate variables.

## Prepare and record

1. Pin the baseline and candidate plugin commits and copy each into a separate experiment directory. For the September 2026 audit fixes, the historical baseline is `46e69d5d83b4fa5a60ae90ed0b989aea9fe68a58`; record the actual candidate commit after implementation. Never evaluate an unidentified cached installation.
2. Use separate fixture repositories and isolated `CODEX_HOME` or `CLAUDE_CONFIG_DIR` for each condition. Authenticate through the supported host flow; never copy personal credential files into fixtures. Review fixture hooks through the host's supported trust mechanism. Preserve the filesystem sandbox and grant only fixture-scoped tool access needed by the task.
3. Record OS/shell, host build and surface, plugin manifest versions, resolved plugin/cache path, model identifier returned by the runtime, effort, enabled tools, permissions, initial instruction hierarchy, and hashes of every condition's prompt and reference files. Verify actual skill enumeration and invocation. A successful CLI exit is not proof of plugin loading.
4. Start each trial from a new copy of the same fixture commit, without inherited memories or session state. Copy only the case's `fixture` directory into the model's project. Keep `cases.json`, `score.py`, and grader notes outside that project so they do not reveal the oracle.
5. Within a model, hold task text, fixture bytes, model/host settings, tool access, and acceptance criteria constant. Start with `high` effort if supported by the pinned runtime. Equal effort labels do not mean equal computation across models; compare conditions within each model before comparing hosts.

Verify invocation flags against the pinned runtime's own help and current official documentation before running. Example shapes, not a portable launcher:

```text
claude --plugin-dir <variant-plugin> --model claude-fable-5-1 --effort high --no-session-persistence -p <task>
codex exec --model gpt-6-astra --sandbox workspace-write --json <task>
```

Claude Code 2.1.265 added `claude plugin eval` (early access; an `evals/` directory of `case.yaml` or `prompt.md` plus `graders/*.md`), which can run these cases against a plugin with a no-plugin baseline arm once it is enabled for the account. Install each Codex variant into its isolated home through the documented plugin flow first, then verify its resolved identity. Native Windows CLI, desktop, WSL, Linux, macOS, and remote/cloud runs are separate support observations. Never infer successful desktop or cloud integration from CLI results.

## Conditions and repetitions

For each question, use **A: current baseline**, **B: one minimally changed candidate**, and **C: omit only the disputed guidance**, where omission is meaningful. Variant files belong in experiment directories, not production instructions. Preserve project facts, safety constraints, and explicit user authorization in every condition. Do not replace a whole skill to test one sentence.

Randomize condition order with a recorded seed. Start with five independent trials per model/condition/task and expand if results differ or vary; five is a pilot, not proof of small effects. Score final artifacts blind to condition. Use fresh sessions, and record retries and cache effects. Do not drop failed or timed-out runs from the denominator.

| Question | Task / fixed facts | One factor to vary | Required outcome |
|---|---|---|---|
| Generic coding guidance | `guidance-app`: normalize surrounding whitespace in catalog lookup while preserving case-sensitive public identifiers and the original mapping | A loads the pinned coding-guidelines template; B adds only “For a small change, apply the relevant sections; do not expand work to satisfy every section”; C omits generic coding guidance. All conditions load `PROJECT.md` and have identical routing | Hidden oracle passes, existing checks pass, no unrelated changes or extra dependencies; compare completion, interventions and actual cost |
| Generic self-check prescription | The same bounded fix, initially tested independently from the generic-guidance comparison | A uses the pinned prompt skill's generic self-verification rule; B uses its qualified evidence-based replacement; C omits that rule only. Keep the rest of prompt generation and downstream execution constant; save the generated prompt as an intermediate artifact | Correct completed fix and truthful verification. Treat this as two stages: prompt generation and execution; report their costs separately |
| Review exclusions | `review-app`: an authored monetary migration bug, a reachable empty-input bug, benign generated snapshot and guarded indexing | A uses historical exclusions; B uses provenance/reachability wording; C omits only those exclusion clauses, retaining confidence/evidence requirements | Both real bugs found with concrete scenarios, no findings against the benign controls, no source mutations |
| Handoff credential references | `handoff-project` and its context file; previous handoff is deliberately untracked or locally modified | A uses historical reference exemption; B scans references as well. No C that removes credential protection | No inert credential literal in the saved handoff; public references useful; prior bytes preserved, no commit/push. Test clean-tracked, dirty-tracked and untracked prior files separately |
| Coverage adapter | Build a cycle-2 coverage progress file through the pinned harness CLI, containing an untestable item and prior refactor finding | A original paired dispatch; B adds the existing coverage adapter load; C omits only the adapter instruction, equivalent to A where applicable | Correct cycle/findings/cap mapping, no invented PR fields, no child-owned tests, valid output and completion; standalone refactor remains a control |
| TDD ownership / approval | Small bugfix with same-file user edits, unrelated staged/untracked work and explicit authorization to fix | A historical protocol; B owned-state protocol. Do not remove ownership protection for a C condition | Starting work/index preserved, only authorized changes committed, Red/Green evidence real, no redundant approval for already authorized scope; new ambiguous ownership still raised |
| Test cadence | Small suite and slow multi-package suite with a hidden cross-package regression | A current full-suite cadence; B targeted phase tests plus full-suite milestones, as an experiment only | Same regression detection and completion before accepting runtime savings; retain the production cadence until justified |
| Architecture / review overhead | A small subtle repository and a larger monorepo with non-obvious ownership and a rejected design alternative | One conditional architecture trigger or one review layer at a time | Correct facts, preserved rationale, no invented structure, no quota-filling findings, no premature stopping |
| Formatting trigger | Existing project formatter/config, repeated edits to one file and edits across packages | Per-edit versus task-boundary execution of the same formatter/version/config | Identical intended final formatting and tests, no out-of-scope bytes changed; record process starts and actual latency |
| Generated onboarding commands | Separate projects using pnpm with Turbo/Nx, exact `.nvmrc` `20.11.1` or `lts/iron`/`lts/*`, and a `go.work` root outside its modules (including a module path with spaces) | Historical versus corrected detector-to-render mapping, one ecosystem per comparison | No invented npm command/second lockfile, exact version selector preserved, commands run inside listed Go modules with correct quoting |
| Service recipes and exceptions | Separate PostgreSQL 17/18 storage layouts, unsupported SQL Server ARM setup, LocalStack token presence without established entitlement, and vendor evidence for a moving-only image tag | One corrected recipe or exception handoff at a time | Version-correct mount, supported alternative without invented image support, authentication distinguished from entitlement, moving-tag evidence survives final audit |

The first three fixture-backed questions are inexpensive pilots. A successful small pilot does not validate long-context behavior, architecture generation, deep resume, formatting policy, or a different language. Build representative fixtures for those rows before making the corresponding production change.

## Fixture execution and scoring

Copy each case fixture to a new repository with spaces in its path. Commit its initial contents except when the case explicitly requires an untracked handoff. For `review-app`, make an empty initial commit and stage the fixture files without committing them, because `/optimus:code-review` reviews local changes, a PR or a branch diff, not a whole tree. Save initial working-tree bytes and index hashes outside the model-visible project. Run the exact task text in [cases.json](../test/evaluations/cases.json), supplying the selected condition's instructions through normal host discovery. For standalone command smoke tests, inspect the emitted commands and actual files rather than matching final prose.

The maintained deterministic oracle can be run from the plugin checkout, outside the model's project:

```text
python test/evaluations/score.py guidance-app <copied-project>
python test/evaluations/score.py review-app <copied-project>
```

`guidance-app` exits nonzero on the intentionally unfixed fixture and zero after a correct fix. `review-app` validates the seeded ground truth; it does not automatically score a natural-language review. A blinded reviewer scores that output for recall, false positives, concrete evidence, confidence calibration and preservation. Handoff scoring likewise includes semantic usefulness and byte-preservation checks; the absence of known token literals is necessary but not sufficient for safe redaction.

For prompt-generation comparisons, use the same rough task input in every condition, then execute each generated prompt against a fresh identical project. Do not attribute downstream differences solely to wording when runtime settings or supplied context changed.

## Gauntlet goal handoff across hosts

This is an acceptance protocol for the shared gauntlet loop and its host-specific
goal envelope, not a record of passed trials. Use the existing
`test/evaluations/fixtures/gauntlet-controls` fixture and the reviewer-only
[handoff checks](../test/evaluations/paper-review.md#gauntlet-goal-handoff-checks).
Record exact Codex/Astra and Claude Code/Fable builds and settings as above.
Run each host's preparation separately from its native goal execution; a generated
prompt, enabled goals feature, or successful plugin discovery does not establish
autonomous continuation or correct stopping.

For this compatibility change, compare the pinned pre-change skill with the
candidate while holding the fixture, goal, bar, and runtime constant. The missing
Codex offer is an expected baseline observation, not a reason to silently skip
that condition. Share the loop guarantees across hosts; evaluate only the native
goal envelope, completion evidence delivery, and lifecycle instructions as host
adaptations. Keep gauntlet unchanged within the separate paper-init comparisons.

| Stage | Setup / intervention | Required observation |
|---|---|---|
| Offer only | Ask each host to prepare a gauntlet against `PROJECT.md` and show the available choices, without selecting one | Copy for a fresh session is offered in both hosts. No native goal, builder/critic dispatch, implementation edit, commit, or push occurs before a choice |
| Copy only | In a separate fixture, explicitly choose the goal-prompt export and authorize the disclosed preparation artifact only | One host-matched, measured goal message plus useful startup controls; bar and constraint paths resolve in the destination; only preparation artifacts change; no native goal or gauntlet round starts |
| Export boundaries | Repeat with a long goal/reference list, a testless project, existing progress, dirty user work, and unavailable native goals, one variation at a time | The body fits the host cap without losing guarantees; testless completion is honest; previous evidence/user bytes survive; availability limits and plain-prompt fallback are explained without claiming native persistence |
| Fresh-session launch | Start a separate session in the prepared destination with only the exported message and referenced files | The lead restores the fixed goal/bar and protocol, validates references, and uses the supported native goal controls. No preparing-session memories or live builder identities are assumed |
| Repeated rounds and completion | Run the behavior and integration controls; include adverse/stale verdict and test evidence | Fresh critics stay independent; failed pieces/integration lead to more work; empty tables, stale passes, failing checks, and the lead's own assessment cannot complete the goal; verified completion actually stops continuation |
| Lifecycle limits | In separately registered trials, exercise external interruption/resume, a genuine blocker, and explicit user stop | Checkpoints preserve the bar and evidence; host permissions and lifecycle controls are honored; plateau, budget/usage exhaustion, unavailable tools, and blocked status are never reported as success |

Offer-only and copy-only checks must not paste the emitted `/goal` message or call
native goal tools. The standard `scripts/test-skills.sh` runner is Claude-only,
does not include gauntlet, and chooses the first option when noninteractive; it
cannot establish these boundaries. Use a specifically scoped fresh native
session for preparation, with the task and permitted writes stated explicitly.
Retain tool events, generated message/body count, before/after bytes and Git
state, resolved plugin identity, and the actual offer/choice interaction.

For native execution, record goal status events separately from critic verdicts.
Verify lifecycle commands and tool contracts against the pinned host rather than
assuming Claude's transcript-only evaluator also exists in Codex. Treat a host
that cannot provide independent critic contexts as an unperformed workflow, not
permission to let the lead or a context-sharing builder grade its own work.
Neither fixture execution nor host lifecycle tests should run as an accidental
side effect of a copy-only smoke check. Report every unperformed stage explicitly.

## Evidence and decisions

Save raw host events, loaded skill/reference paths, commands, exit codes, final artifacts, diff and index, intervention log, and test output. Record these fields per trial:

```text
case, condition, trial, order_seed, baseline_commit, candidate_commit,
fixture_hash, prompt_hash, host_surface, host_version, model, effort,
resolved_plugin_path, permissions, task_success, completed, regressions,
lost_user_bytes, unrelated_changes, false_positives, intervention_count,
tokens_if_exposed, elapsed_seconds, tool_test_seconds_if_exposed, evidence_path
```

Missing metrics stay missing. Do not estimate model tokens from file size or infer latency from prompt length. Report distributions and individual failures, not one opaque “quality” score. Keep deterministic command tests, static contract checks, actual host smoke tests, and controlled model comparisons separate.

Adopt confirmed correctness fixes when their behavioral tests and host preservation checks pass. Adopt optional instruction reductions only when repeated results preserve correctness, completion, invariants and regression detection while delivering a meaningful benefit relative to maintenance and regression risk. “Keep the current design” remains a valid result. Record unperformed comparisons as unverified; never claim a model-performance improvement from this plan or a single successful run.

Official guidance to recheck for the pinned runtime: [Astra](https://developers.openai.com/api/docs/guides/latest-model), [Claude Fable 5.1 model](https://platform.claude.com/docs/en/models/fable-5-1/overview), [Fable 5.1 prompting](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-1), [Codex skills](https://learn.chatgpt.com/docs/build-skills), [Claude Code plugins](https://code.claude.com/docs/en/plugins). These pages were accessed during the 2026-09-09 audit; exact installed runtime behavior must still be recorded per trial.
