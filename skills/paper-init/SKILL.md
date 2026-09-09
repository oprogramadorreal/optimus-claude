---
description: >-
  Builds a self-contained paper-context bundle for implementing a research
  paper — sources, transcription, figures, references (blocking citations
  fetched), an implementation spec with the reported results, open questions,
  dataset provenance — under paper/, with datasets in a gitignored data/.
  Warns when reproduction outstrips local hardware. Downloads files and edits
  .gitignore and the root README. Stack-agnostic; writes no implementation
  code. Use when implementing a paper from a URL, PDF, DOI, or arXiv id.
disable-model-invocation: true
argument-hint: "<paper URL, PDF path, DOI, or arXiv id>"
---

# Paper Init

Build the local context bundle a later session needs to implement a research
paper: the paper itself, its figures and references, what it specifies, what
it leaves open, and its data. Context only — no implementation code, no stack
setup. Everything the implementer needs must end up on disk; nothing may
depend on this conversation's context.

## The bundle

One `paper/` directory at the project root holds everything paper-derived:

- `paper/README.md` — bundle index: what this is, the read-first order,
  current status. Under ~50 lines.
- `paper/source/` — pristine originals only: the PDF (supplementary
  material included) plus the best machine-readable form available (EPUB,
  HTML, XML, arXiv LaTeX source), exactly as acquired. Derived files (text
  dumps, extracted markup) never live here.
- `paper/source/metadata.json` — the provenance record (step 2).
- `paper/paper.md` — the faithful working transcription (step 3).
- `paper/tables.md` — overflow tables, only when the transcription takes its
  escape hatch (step 3).
- `paper/figures/` + `paper/figures/README.md` — every figure, one README
  line each (file, dimensions, caption) with known defects — duplicates,
  missing diagrams — at the top.
- `paper/references.md` — every reference, annotated: role (dataset,
  baseline, method), resolved link, and fetch priority.
- `paper/cited/` — pristine sources of the works the paper, or a fetched
  work in turn, defers load-bearing content to (step 3), when any were
  fetched. Nothing derived lives here.
- `paper/spec.md` — what the paper actually specifies (step 3), ending with
  the targets the implementation is later judged against.
- `paper/open-questions.md` — what the paper leaves open (step 3).
- `paper/dataset.md` — dataset provenance and re-acquisition, when the paper
  uses datasets (step 6).
- `paper/reference-code/` — vendored existing code, when it exists (step 4);
  gitignored, its provenance tracked in `metadata.json`.
- `data/` — the datasets themselves, gitignored, when any were acquired
  (step 6).

Keep generated workflow framing tool-agnostic: "a fresh session", "the
implementing agent", without `/optimus:*` commands. Preserve product/model
names that occur in the paper or its evidence; faithful transcription takes
precedence. The final chat message may name `/optimus:gauntlet`.

## 1. Resolve the paper

The invocation argument is a URL, a local PDF path, a DOI, or an arXiv id;
if none was given, ask for one. Resolve DOIs and arXiv ids to the source of
record. If the paper is inaccessible (paywall, dead link), say so plainly and
either stop or proceed from a file the user supplies.

When `git rev-parse --is-inside-work-tree` returns `true`, resolve its
`--show-toplevel` and proceed in that working tree, including linked worktrees.
A `.git` file alone does not distinguish them from submodules. Otherwise read
`$CLAUDE_PLUGIN_ROOT/skills/init/references/multi-repo-detection.md` and
apply it: the bundle goes inside the target repo, not above it. When it
detects a multi-repo workspace, ask which repo the paper work targets before
writing anything — bundle, `.gitignore`, and README block all land there;
when it finds no recognized structure, work in the current directory.

## 2. Acquire sources

Download into `paper/source/`, redundantly: the PDF whenever one exists (an
HTML-only paper's publisher full text is the primary source), any
supplementary material, plus the cleanest structured full text the
publisher offers — the transcription cross-checks formats against each
other. For arXiv papers, also pull the e-print source bundle
(`https://arxiv.org/e-print/<id>`) when offered: the LaTeX source makes math
transcription near-mechanical and ships figures at native resolution. Pull
figure rasters into `paper/figures/` from whichever source has the best
resolution (PDF-embedded usually beats web-served); keep native formats,
never re-encode, and write `paper/figures/README.md` as they land — one line
per figure (file, dimensions, caption from the paper text), known defects
(duplicates, missing diagrams) at the top. Installing transient fetch or
extraction tooling along the way (a PDF library, gdown, pandoc) is fine —
that is not the project stack — but install it isolated (pipx, a scratch
venv, `pip install --target` into a temp dir), never into the project's own
environment.

`metadata.json` records at minimum: `title`, `authors`, `venue`, `published`,
`doi`, `url`, `license`, `downloaded` (date), `code_available` (with the
paper's own availability sentence when it states one), `dataset_referenced`
(name, URL, whether the paper redistributes it — full provenance and
re-acquisition live in `paper/dataset.md`), and `local_files` — every file
in `source/` mapped to its role and exact acquisition record (URL or
command, and date; for a file the user supplied, the path it came from).
Add any further bibliographic fields the source offers. The test: a fresh
clone can re-acquire every publicly fetchable file from this record alone.

## 3. Working forms

- `paper/paper.md` — a complete transcription, not a summary: mirrored
  section headings, math in LaTeX, figures as local relative links with their
  captions, tables inline (escape hatch: a separate `tables.md` when tables
  are numerous or large, linked both ways). Open with a provenance header
  naming the source of record. Its length is the paper's own.
- `paper/spec.md` — only what the paper states, each fact tagged with its
  section ref: data, architecture, training procedure (including the compute
  the paper states — hardware, training time, scale), evaluation, baselines,
  reported results. Architecture/training/eval tables carry a "defined enough
  to implement?" column. Anything inferred, chosen, or assumed is labeled as
  ours or moves to `open-questions.md` — never present our choices as the
  paper's. End with a short "targets worth holding the implementation to"
  section — the quality bar the implementation is later judged against, so it
  must stand on its own: the externally meaningful results (numbers, and
  figures where the claim is qualitative), each with the metric, data,
  protocol, and spread the paper reports, plus the cheaper checks the paper
  states along the way (dataset counts, parameter counts, a loss reached)
  that let part of the implementation be judged before a full run exists. A
  target the bundle cannot yet measure — data not on disk, a scorer or
  protocol undefined — says what is missing. Keep the file under ~200 lines.
- `paper/references.md` — every reference the paper cites, annotated: role
  (dataset, baseline, method), resolved link, fetch priority. Step 4 appends
  the reference-code summary here when code exists.
- `paper/open-questions.md` — everything undefined, ordered by how much it
  blocks work: missing hyperparameters, ambiguous procedures, figure/table
  defects (ledgered in `figures/README.md` — point there, don't duplicate),
  credibility issues, and a suggested framing for the implementation, tech
  stack included (drawn from the paper and the project's existing stack if
  one exists). An open point with a defensible default says so and where it
  comes from (reference code, a cited work, common practice), so an
  unattended implementation run proceeds instead of stalling on it. Mark a
  finding `[verified]` only when checked against the local files during this
  run — never for inference — open the file with a one-line legend saying
  what the mark means, and settle now whatever those files can settle: no
  verifiable-now TODO leaks into the implementation phase. Keep it under
  ~150 lines.

When the paper defers load-bearing content to a citation — an inherited
architecture, a borrowed training procedure, a dataset defined there — the
bundle's contract covers that content too: fetch each such cited work's
sources now, as in step 2, into `paper/cited/<slug>/`, and record each in
a `cited_works` array in `metadata.json` (title, identifier, slug, license,
and the acquisition record — URL and date, or the path it came from for a
user-supplied file). Pull the specific facts the implementation needs from
it into `spec.md` or `open-questions.md`, tagged with provenance, and note
in `references.md` why it was fetched — a work the paper itself never cites
gets its own entry there. Apply the same test to each fetched work: when it
defers content the implementation still needs to a further work, fetch that
one too. Sources and targeted extraction only — no bundle per cited work.
Expect a handful of works, not a bibliography crawl: the test is dependence,
not relevance. An inaccessible cited work stays a visible gap — record what
is deferred to it in `open-questions.md` and report it in the final message
so the user can supply a copy.

If producing the bundle took mechanical extraction work a fresh session
could not trivially redo (pulling rasters out of a PDF, dumping text from an
EPUB), leave one small regenerator script that reproduces those derived
artifacts from `paper/source/` offline (placement follows project
conventions; when the project has none, `paper/`). Stamp only
script-produced files with a do-not-hand-edit header — the model-authored
files (`paper.md`, `spec.md`, and the rest) stay hand-editable, and a re-run
updates them in place. When you leave one, ensure `.gitattributes` pins the
script's outputs — `eol=lf` for generated text, `binary` for extracted
rasters — so regeneration stays diff-clean on any platform.

## 4. Reference code

Check the paper's own links and project page, then search for official or
third-party implementations. When code exists: vendor it into
`paper/reference-code/` (gitignored — step 7), record its provenance as a
`reference_code` object in `metadata.json` (upstream URL, exact commit or
tag, vendor date, license) — that tracked file is what lets a fresh clone
re-acquire the code; anything left inside `paper/reference-code/` itself is
gitignored away. Add a what-it-reveals summary to `references.md`
(hyperparameters, architecture details, training procedure). It is
reference material, never the implementation. When none exists, record
`code_available: false` in `metadata.json`.

## 5. Feasibility

When the paper's experiments plausibly demand substantial compute — model
training, large-scale simulation or rendering — assess feasibility before
step 6 acquires anything big. Most papers have nothing to gate (a survey, a
proof, a small-scale study); skip this step for them entirely.

- Draw the requirements from what `spec.md` recorded (step 3) and from the
  vendored reference code's own docs, which often state hardware. When
  neither states them, estimate from what the paper does record — model
  scale, dataset size, training steps — and label the figures as estimates.
- Detect the local GPU (model, VRAM) and RAM, and compare against what
  faithful reproduction needs. Detection tooling is not universal (no
  `nvidia-smi` on AMD or Apple Silicon machines): when it cannot answer,
  ask the user what the machine has — never read a failed detection as
  "no GPU".
- When the gap makes the reported targets unreachable in practice — not
  merely slower — ask once with `AskUserQuestion`: header "Hardware
  feasibility", the question naming the limiting factor and the concessions
  that would close the gap (reduced scale, a dataset subset, quantized or
  distilled variants, different hardware), options "Continue anyway" /
  "Reduce scope" / "Pause — line up other hardware first".
- Record the outcome where it binds. A reduced scope adjusts `spec.md`'s
  targets section — that is the bar the implementation is later judged
  against — gets a line in `open-questions.md`, may shrink what step 6
  downloads, and is recorded in `metadata.json` (the decision and the
  adjusted targets) so a refresh re-applies them rather than restoring the
  paper's reported targets. "Continue anyway" leaves the targets untouched
  and notes the hardware risk in `open-questions.md`. "Pause" stops the
  spend, not the bundle: step 6 writes re-acquisition steps into
  `dataset.md` instead of downloading, `open-questions.md` records the
  pause, and the remaining steps finish so the bundle commits complete and
  a re-run resumes it.
- Never write the hardware inventory itself into the bundle — it stays
  machine-agnostic; only the decision and its consequences go on disk.

No substantial compute, or no mismatch: no gate, and the final message says
at most one line about feasibility.

## 6. Datasets

Identify every dataset the paper uses. Freely downloadable ones go into
`data/` now; verify what arrived (file counts, sizes, integrity) against what
the source promises, and record the verified numbers. Write
`paper/dataset.md`: provenance, exact re-acquisition commands, the verified
counts, license and redistribution terms, and anything deliberately not
downloaded. Keep it under ~200 lines. If the paper uses no external datasets,
say so in one line of `paper/README.md`'s status and skip `dataset.md`,
`data/`, and the gitignore pair entirely.

Before a large download (GB-scale or hours of time), confirm with
`AskUserQuestion` — header "Dataset download", question stating size and
source, options "Download now" / "Skip — write re-acquisition steps only".
Small datasets download without asking. When a download is blocked (auth,
license acceptance, a manual form), do not ask — write the exact steps into
`dataset.md` and flag it in the final message.

## 7. Gitignore and routing

Each `.gitignore` rule below is independent — apply every one whose
condition holds, adding only what is missing:

- Datasets in use: `data/*` plus `!data/README.md`.
- Vendored reference code: `paper/reference-code/`.
- License: when `metadata.json`'s `license` does not permit redistribution
  (typical for a paywalled publisher PDF), also `paper/source/*` and
  `paper/figures/*` with `!paper/source/metadata.json` and
  `!paper/figures/README.md` exceptions — a fresh clone re-acquires those
  from the metadata record, which must therefore stay committed. When the
  license forbids redistribution or derivatives (an ND clause), flag in the
  final message that `paper.md` is a full-length derivative: committing it
  is the user's call when the repo is or will become public.
- Cited works: the same license test applies to each cited work on its
  own, whatever the main paper's license — one whose license forbids
  redistribution adds its own `paper/cited/<slug>/` directory, never the
  whole `paper/cited/` (other works may be committable). A fetched work is
  re-acquirable from the record; a user-supplied one exists only at the
  path it came from — say so in the final message.

A pre-existing `data/` line (directory form, common in ML repos) defeats the
`!data/README.md` exception — git cannot re-include a file under an excluded
directory. Narrow that line to `data/*` (same ignore coverage; exceptions
become possible), note the change in the final message, and verify with
`git check-ignore -q data/README.md`: it must exit non-zero, finding nothing
to ignore (under `-v`, a match on the `!` line is the exception working, not
the file being ignored).

When the paper uses datasets, also write `data/README.md`: what goes here,
the counts when known, license terms, and a pointer to `paper/dataset.md`.
Not a git repo? Skip the `.gitignore` part and note it in the final message.

Write `paper/README.md` (the bundle index). If a root `README.md` exists,
maintain one short routing block there pointing at the bundle(s), wrapped in
marker comments that identify it as managed:

```
<!-- paper-context:start -->
## Paper context
...
<!-- paper-context:end -->
```

On re-run, rewrite only what lies between the markers, never duplicate the
block; a `## Paper context` heading without markers is the user's own —
leave it alone and append a new marked block. If no root README exists,
skip — the bundle indexes itself.

## 8. Final message

Close with: what the bundle contains and where; cited works — which were
fetched and why, which the user supplied, and which remain gaps in
`open-questions.md` (or that none were needed); dataset status (downloaded
and verified, skipped, blocked — with the instructions pointer — or none);
hardware feasibility (one line when fine, the mismatch and the recorded
decision when not); any transient tooling installed; and the suggested tech
stack as recorded in `open-questions.md` — a suggestion only, nothing is
installed.

Then: commit the bundle first (e.g. with `/optimus:commit`, staying in this
conversation) so the implementation loop starts from a clean, tracked
baseline — the gitignored parts (`data/`, `paper/reference-code/`,
license-ignored sources) exist only in this checkout, so a worktree or fresh
clone re-acquires them from the records or copies them in. Then start a
fresh conversation with `/optimus:gauntlet`, printed as one paste-ready
line: the goal names the bundle root with its index as the read-first entry,
the bar its `spec.md` targets section.

## Re-running

Same paper — a resolved identifier (DOI, arXiv id) matches
`source/metadata.json`, or one source names the other's identifier (an arXiv
page listing the published DOI): refresh in place — update, don't duplicate,
and keep the original acquisition records (append the refresh; a preprint's
provenance is not overwritten by its published version's). A scope decision
recorded in `metadata.json` (step 5) is not paper content: re-apply it to
the regenerated `spec.md` targets rather than restoring the reported
results. Cited works already in `paper/cited/` are kept, not re-fetched;
when the revision drops a citation the bundle fetched, ask before removing
its directory. When the match is uncertain, ask before touching the
existing bundle. A different paper while
`paper/` already holds one: use `papers/<slug>/` (kebab-case slug from the
title) as the bundle root everywhere — datasets go in `papers/<slug>/data/`
with their own `data/README.md`, and the gitignore entries spell full paths
(`papers/<slug>/data/*` with its `!papers/<slug>/data/README.md` exception,
`papers/<slug>/reference-code/`, `papers/<slug>/cited/<work>/` only when
step 7's license rule fires for that work): a pattern
containing slashes anchors at the `.gitignore` location, so the bare step
6–7 paths cannot reach a nested bundle. Leave the existing bundle untouched
and add the new one to the routing block. If `papers/<slug>/` already holds
a different paper, disambiguate the slug (append the year or venue) — never
refresh a bundle that is not the same work. Never merge two papers into one
bundle; never move an existing `paper/` — that restructuring is the user's
call.

## Boundaries

- Never write under `docs/specs/` or `docs/product/` — `/optimus:tdd`
  auto-detects build specs there and `/optimus:brainstorm scaffold` owns the
  steering cascade. The transcription mirrors the paper's own headings
  verbatim, `Scenarios` included — spec auto-detection reads only those two
  directories, so no bundle heading can misfire it.
- Never write `.claude/.optimus-version` (owned by `/optimus:init`) and never
  edit `.claude/CLAUDE.md` (audited and reconciled by init under its preservation rules).
