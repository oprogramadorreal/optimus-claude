# Re-running on an existing bundle

Same paper — a resolved identifier (DOI, arXiv id) matches
`source/metadata.json`, or one source names the other's identifier (an arXiv
page listing the published DOI): refresh in place — update, don't duplicate,
and keep the original acquisition records (append the refresh; a preprint's
provenance is not overwritten by its published version's). When the match is
uncertain, ask before touching the existing bundle. Preserve target
and question IDs, decision rationale, and history. A scope decision in
`metadata.json` binds the selected scope. For empirical papers, apply it in
`acceptance.md`; `spec.md` keeps the original reported results. For older
empirical bundles that reduced the spec's targets, migrate those decisions
into acceptance and recover the paper's
originals from sources. Surface conflicts when a new source revision makes
an earlier decision inapplicable; never silently drop or reinterpret it.
Retire removed requirement IDs with a reason instead of reusing or renumbering
them. Read existing decision ledgers, including `decisions.md` if present;
preserve them and do not reopen settled questions without new evidence.

Before replacing context used by an active or past evaluation, preserve its
bar and linked protocols in a revision snapshot. Consult existing evaluation
records when available. Record changed requirements and which evidence needs revalidation;
never overwrite run artifacts, logs, or critic verdicts, or silently replace
an active run's fixed bar. A new acceptance revision is a proposed bar for a
new evaluation, not permission to relax failed criteria. Preserve necessary
source versions and acquisition records too. Snapshots inherit the source
license and ignore rules: never expose ignored sources or reference code by
copying them into a tracked archive. Git history stands in for a snapshot
only when it actually retains the prior bytes.

Cited works already in `paper/cited/` are kept, not re-fetched unless the
required source version changes or a missing file must be re-acquired;
when the revision drops a citation the bundle fetched, ask before removing
its directory. A different paper while
`paper/` already holds one: use `papers/<slug>/` (kebab-case slug from the
title) as the bundle root everywhere — datasets go in `papers/<slug>/data/`
with their own `data/README.md`, and every `.gitignore` and `.gitattributes`
entry (license-rule entries and `!` exceptions included) and the
`git check-ignore` check use nested paths (`paper/` becomes `papers/<slug>/`,
`data/` becomes `papers/<slug>/data/`): a pattern containing slashes anchors
at its file's location, so bare paths cannot reach a nested bundle. Leave
the existing bundle untouched and add the new one to the routing block. If
`papers/<slug>/` already holds a different paper, disambiguate the slug
(append the year or venue) — never
refresh a bundle that is not the same work. Never merge two papers into one
bundle; never move an existing `paper/` — that restructuring is the user's
call.
