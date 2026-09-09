# /optimus:paper-init

Builds a self-contained paper-context bundle for implementing a research paper — pristine sources,
a faithful transcription, figures, annotated references (works the paper defers load-bearing content
to are fetched too, and what those defer to in turn), an implementation spec with the reported
results, open questions, and dataset provenance — under `paper/`, with datasets in a gitignored
`data/`. When the paper's experiments demand substantial compute, it compares the requirements
against the local hardware and warns before you invest in a reproduction the machine can't run.
Stack-agnostic: it writes no implementation code and sets up no project stack (transient
fetch or extraction tooling may be installed along the way — isolated, never into the project's
own environment; the final message names it). The
bundle is the launchpad for a later implementation run, typically `/optimus:gauntlet` judged
against `spec.md`'s targets — the paper's reported results, unless the feasibility gate reduced them.

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

With no argument, it asks for one. It ends with a summary of the bundle, the cited works fetched,
the dataset status, hardware feasibility, and a suggested tech stack (a suggestion only — nothing
is installed), then points you at the next step: commit the bundle, then start the implementation
in a fresh conversation with the paste-ready `/optimus:gauntlet` line it prints.

## What it produces

| Path | Contents |
|------|----------|
| `paper/README.md` | Bundle index: what this is, read-first order, status |
| `paper/source/` | Pristine originals (PDF, supplementary material, best machine-readable form) |
| `paper/source/metadata.json` | Provenance: bibliographic facts, license, code/dataset availability, exact re-acquisition record per file |
| `paper/paper.md` | Complete working transcription — LaTeX math, local figure links, inline tables |
| `paper/tables.md` | Overflow tables, when numerous or large (linked both ways from `paper.md`) |
| `paper/figures/` + `paper/figures/README.md` | Best-resolution figure rasters, captioned, known defects flagged |
| `paper/references.md` | Every reference annotated with role, link, and fetch priority |
| `paper/cited/` | Pristine sources of the works the implementation depends on beyond the paper — cited works and, transitively, what those defer to — when any were fetched |
| `paper/spec.md` | What the paper specifies, §-referenced — ending in the targets the implementation is held to: metric, data, protocol, and spread per target, the cheaper checks stated along the way, and what can't be measured locally yet |
| `paper/open-questions.md` | What's undefined, blocking-first — each point with its best default and source when one exists — plus a suggested framing and tech stack; `[verified]` marks file-checked findings |
| `paper/dataset.md` | Dataset provenance, exact re-acquisition commands, verified counts, license terms (when the paper uses datasets) |
| `paper/reference-code/` | Vendored existing implementations (gitignored), when they exist — reference, never the implementation |
| `data/` | Downloaded datasets (gitignored; `data/README.md` stays committed) |

It also ensures `.gitignore` ignores `data/*` (with a `!data/README.md` exception — a pre-existing
`data/` line is narrowed to `data/*` when one would defeat it) and `paper/reference-code/`, plus
`paper/source/*` (the metadata record stays committed) and figure rasters when the paper's license
doesn't permit redistribution — the same test applies to each cited work individually
(`paper/cited/<slug>/`) — and maintains a marker-delimited routing block in the root README when
one exists.
Its workflow framing is tool-agnostic — no file mentions this plugin or `/optimus:` commands; product and model names that the paper itself uses are transcribed faithfully.

## How it works

1. **Resolves the paper** from your argument (URL, PDF path, DOI, or arXiv id).
2. **Acquires sources** redundantly into `paper/source/` and records exactly how each file was
   obtained, so a fresh clone can re-acquire everything.
3. **Writes the working forms** — transcription, figures, annotated references, spec, open
   questions — verifying against the local files whatever can be settled now, and fetching each
   cited work the implementation can't proceed without, and in turn what those works defer to
   (sources and targeted extraction only, never a per-citation bundle).
4. **Checks for existing code** (the paper's own links and project page, then a code search) and
   vendors it as reference material when found.
5. **Assesses feasibility** when the paper's experiments demand substantial compute: compares the
   requirements against the local hardware and, on a genuine mismatch, asks once how to proceed —
   continue anyway, reduce scope, or line up other hardware — before any large dataset downloads.
6. **Gets the datasets**: freely downloadable ones are fetched and verified; large downloads
   (GB-scale) ask first; blocked downloads (auth, license forms) get exact manual instructions
   in `paper/dataset.md` instead. A paper with no datasets skips this entirely.
7. **Sets up gitignore and routing** so data stays local and the bundle stays discoverable.
8. **Reports** the bundle, cited works fetched, dataset status, hardware feasibility, and a
   suggested stack — then the next step, as a paste-ready `/optimus:gauntlet` line.

It commits nothing; the final message tells you to commit the bundle before starting the
implementation run, so the loop starts from a clean, tracked baseline.

## Notes

- Needs network access; paywalled papers stop with a plain explanation (or use a PDF you supply).
- In a multi-repo workspace, it asks which repo the paper work targets and builds inside it,
  never above it.
- Re-running on the same paper refreshes in place; it never moves or merges an existing bundle.
- The gitignored parts of the bundle (datasets, vendored reference code, license-ignored sources)
  live only in the checkout that ran the skill — a worktree or fresh clone re-acquires them from
  the recorded provenance, or you copy them in.
- Never touches `docs/specs/`, `docs/product/`, `.claude/CLAUDE.md`, or `.claude/.optimus-version`.
