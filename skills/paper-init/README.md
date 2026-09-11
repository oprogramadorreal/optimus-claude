# /optimus:paper-init

Builds a self-contained paper-context bundle for implementing a research paper — pristine sources,
a faithful transcription, figures, annotated references (works the paper defers load-bearing content
to are fetched too, and what those defer to in turn), an implementation spec with the reported
results, empirical acceptance criteria, open questions, and dataset provenance — under `paper/`, with datasets in a gitignored
`data/`. When the paper's experiments demand substantial compute, it compares the requirements
against the local hardware and warns before you invest in a reproduction the machine can't run.
Stack-agnostic: it writes no implementation code and sets up no project stack (transient
fetch or extraction tooling may be installed along the way — isolated, never into the project's
own environment; the final message names it). The
bundle prepares a later implementation run, typically `/optimus:gauntlet` judged against
`acceptance.md` and its linked protocols. `spec.md` preserves the paper's original targets;
acceptance records the selected scope and what evidence will establish it. Non-empirical papers
use the source-linked selected targets in `spec.md` without an empirical acceptance document.

## When to run

- You're starting a paper implementation — especially one with no official code.
- Before a `/optimus:gauntlet` run whose quality bar is a paper's reported results.
- Adding a second paper to a project that already implements one (lands in `papers/<slug>/`).
- Refreshing a bundle after the paper or dataset situation changes.

## When NOT to run

- You just want to run the paper's official code — clone it and go.
- You want a summary of a paper, not an implementation.
- The implementation itself — that's `/optimus:gauntlet` (or `/optimus:tdd` for smaller work).

## Usage

    /optimus:paper-init https://arxiv.org/abs/2402.13521
    /optimus:paper-init 2402.13521
    /optimus:paper-init 10.3389/frai.2026.1828627
    /optimus:paper-init ./downloads/paper.pdf
    /optimus:paper-init ./downloads/paper.pdf reproduce Table 2 only, CPU, no paid services

With no argument, it asks for one. It ends with a summary of the bundle, the cited works fetched,
the dataset status, hardware feasibility, and a suggested tech stack (a suggestion only — nothing
is installed), then points you at the next step: commit the bundle, then start the implementation
in a fresh conversation with the paste-ready `/optimus:gauntlet` line it prints.
Existing scope decisions and explicit reference-code or resource constraints carry through;
already authorized actions do not require another confirmation.

## What it produces

| Path | Contents |
|------|----------|
| `paper/README.md` | Bundle index: read order, selected scope, preparation/evidence status, blockers, bar revision and pinning instruction |
| `paper/source/` | Pristine originals (PDF, supplementary material, best machine-readable form) |
| `paper/source/metadata.json` | Provenance, source revisions and hashes, acquisition records, scope decision history, acceptance revision and defining documents |
| `paper/paper.md` | Complete working transcription — LaTeX math, local figure links, inline tables |
| `paper/tables.md` | Overflow tables, when numerous or large (linked both ways from `paper.md`) |
| `paper/figures/` + `paper/figures/README.md` | Best-resolution figure rasters, captioned, known defects flagged |
| `paper/references.md` | Every reference annotated with role, link, and fetch priority |
| `paper/cited/` | Pristine sources of the works the implementation depends on beyond the paper — cited works and, transitively, what those defer to — when any were fetched |
| `paper/spec.md` | Source-linked facts and original reported targets with stable IDs, metric, data, protocol, variability, cheaper checks, and gaps |
| `paper/acceptance.md` | Empirical scope inventory, requirements by development/execution/result, experiment protocols, justified criteria, and future evidence contract; bulky protocols use linked overflow only when needed |
| `paper/open-questions.md` | Stable question IDs, status, source-backed defaults, decisions and consequences; suggested framing/stack; `[verified]` means checked during preparation, not empirically reproduced |
| `paper/dataset.md` | Dataset versions/splits, preprocessing, provenance, exact re-acquisition commands, verified counts, license terms (when datasets are used) |
| `paper/reference-code/` | Existing implementations inspected during preparation (gitignored), with provenance and paper/code conflicts recorded; later reuse follows the user's scope and license |
| `data/` | Downloaded datasets (gitignored; `data/README.md` stays committed) |

It also ensures `.gitignore` ignores `data/*` (with a `!data/README.md` exception — a pre-existing
`data/` line is narrowed to `data/*` when one would defeat it) and `paper/reference-code/`, plus
`paper/source/*` (the metadata record stays committed) and figure rasters when the paper's license
doesn't permit redistribution — the same test applies to each cited work individually
(`paper/cited/<slug>/`) — and maintains a marker-delimited routing block in the root README when
one exists.
Acquired originals with exact-byte hashes get narrow `.gitattributes` rules to
preserve their bytes across checkouts; metadata and working forms remain editable.
Its workflow framing is tool-agnostic — no file mentions this plugin or `/optimus:` commands; product and model names that the paper itself uses are transcribed faithfully.

## How it works

1. **Resolves the paper** from your argument (URL, PDF path, DOI, or arXiv id).
2. **Acquires sources** redundantly into `paper/source/`, including relevant public author
   clarifications and errata, and records versions, hashes, and acquisition provenance.
3. **Writes the working forms** — transcription, figures, annotated references, spec, open
   questions, and empirical acceptance — verifying against the local files what can be settled now, and fetching each
   cited work the implementation can't proceed without, and in turn what those works defer to
   (sources and targeted extraction only, never a per-citation bundle).
4. **Checks for existing code** (the paper's own links and project page, then a code search) and
   vendors it as reference material when allowed; paper/code conflicts remain explicit.
5. **Assesses feasibility** when the paper's experiments demand substantial compute: compares the
   experiment matrix and resource budget against local feasibility and, on a mismatch, asks once how to proceed —
   continue anyway, reduce scope, or line up other hardware — before any large dataset downloads.
6. **Gets the datasets**: freely downloadable ones are fetched and verified; large downloads
   (GB-scale) need authorization; blocked downloads (auth, license forms) get exact manual instructions
   in `paper/dataset.md` instead. A paper with no datasets skips this entirely.
7. **Sets up gitignore and routing** so data stays local and the bundle stays discoverable.
8. **Reconciles and hands off**: checks claim coverage and source/evidence links after code and
   dataset inspection, settles answerable gaps, records the bar revision, and reports preparation
   status with the paste-ready `/optimus:gauntlet` line.

It commits nothing; the final message tells you to commit the bundle before starting the
implementation run, so the loop starts from a clean, tracked baseline.

## What counts as reproduction

The empirical contract connects claims to method/data requirements, baselines, ablations,
evaluation and selection protocols, seeds/repeats, reported variability, and independently
verifiable evidence. It separates code development, successful execution, and reproduced
results. Optional importance weights describe partial progress; selected failures cannot be
averaged into a pass. Tolerances need justification, and unknown criteria remain explicit gaps.

A fresh implementing session pins the actual committed bar (or an immutable snapshot), then
creates the stack, entrypoint, run manifests, logs, raw metrics, and derived results. Independent
verification uses a fresh checkout and isolated environment with declared inputs. Preparation
creates those instructions, not a reproduction script or experimental evidence.

Gauntlet's `beats the bar` means satisfying the selected reproduction criteria; the implementation
need not scientifically outperform the paper. Reduced-scope success must be labeled as such.
Gauntlet retains its independent critics, fixed remit, execution, integration checks, stopping
rules, and repository safeguards unchanged.

Unavailable requirements remain selected and blocked until you authorize a scope change.
Recording a deviation cannot excuse an out-of-band result, and reported standard deviation
does not automatically define the acceptance tolerance.

On refresh, original paper targets and scope decisions stay separate. Prior bars and source
versions remain recoverable, changed requirements identify evidence needing revalidation, and
existing runs keep their original bar. Older bundles with reduced spec targets migrate those
decisions to acceptance without discarding their rationale or claiming full reproduction.

## Notes

- Needs network access; paywalled papers stop with a plain explanation (or use a PDF you supply).
- In a multi-repo workspace, it asks which repo the paper work targets and builds inside it,
  never above it.
- Re-running on the same paper refreshes in place; it never moves or merges an existing bundle.
- The gitignored parts of the bundle (datasets, vendored reference code, license-ignored sources)
  live only in the checkout that ran the skill — a worktree or fresh clone re-acquires them from
  the recorded provenance, or you copy them in.
- Never touches `docs/specs/`, `docs/product/`, `.claude/CLAUDE.md`, or `.claude/.optimus-version`.

The [evaluation protocol](../../docs/paper-reproduction-evaluation.md) describes controlled
baseline/candidate comparisons, fixture replay checks, and non-paper gauntlet controls. These
instructions are not yet supported by controlled model-performance results.
