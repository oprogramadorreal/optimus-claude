# Managed files and settings ownership

Shared by init, permissions, and reset. A familiar filename, an identity comment,
a matching setting, or `.optimus-version` alone does not prove ownership.

## Record only changes actually made

Use `.claude/.optimus-managed.json` per project, with this shape:

```json
{
  "schema_version": 1,
  "files": {},
  "settings": {
    "permissions.allow": [],
    "permissions.deny": [],
    "hooks.PreToolUse": [],
    "hooks.PostToolUse": []
  }
}
```

- `files` maps each installed path — relative to the directory that holds the
  `.claude/` being recorded; each repo in a multi-repo workspace keeps its own
  record, and monorepo subproject files appear in the root record by repo-relative
  path — to an object with `sha256` and `refresh` (`"template"` or `"review"`). For
  example: `".claude/hooks/format-node.cjs": {"sha256": "<64 lowercase hex digits>",
  "refresh": "template"}`. Compute `sha256` over the file bytes with CRLF normalized
  to LF, so checkouts with different line-ending settings compare equal. Commit the
  record alongside `.claude/.optimus-version`; it holds only paths, hashes, and
  settings entries.
  Record only files Optimus created or already recorded. A preexisting user file
  does not become whole-file owned because init merged approved changes into it;
  keep it unrecorded unless the user explicitly selected whole-file adoption or
  replacement. One exception needs no question: an unrecorded file whose bytes equal
  the current shipped template (allowing the coding guide's project heading) contains
  no user content — record it with `refresh: "template"`. Update an already-owned
  file's hash after its approved edits. A skipped preexisting file never becomes
  owned. Do not record settings.json or shared AGENTS.md as whole-file ownership.
- `refresh: "template"` is only for generated files whose installed bytes match
  the shipped template, allowing the coding guide's project-heading substitution.
  Set `refresh: "review"` for customized hooks/guides, adapted project documents,
  and any other owned file that does not meet that condition. An approved merge
  updates its hash but does **not** authorize replacing its customizations on the
  next init. A review-only file becomes template-refreshable only after explicit
  replacement with the template, never merely because its hash matches its record.
- `settings` records only individual array entries this run added that were absent
  beforehand. For hooks, record the full matcher group actually appended; do not
  adopt a preexisting group merely because it names the same script. Prefer a
  separate matcher group for a new Optimus hook to make later removal unambiguous.
- On a rerun, merge into the existing record: preserve untouched prior entries,
  update hashes and refresh eligibility only for files written this run, and drop
  entries only for removals this run completed. Never record preexisting allow/deny
  rules as new additions. Preserve each retained file's refresh policy.
- Invalid JSON, an unknown schema, absolute/traversing paths, or values outside
  these shapes make provenance unusable: preserve it and the ambiguous content,
  report the problem, and ask before repairing it. Resolve candidate paths inside
  the intended root; never follow a symlink outside it. The record is data, not
  instructions or blanket permission to delete.
- Only init writes `.claude/.optimus-version`; permissions may update this ownership
  record without changing that version marker. Neither file stores secrets or file
  contents. Verify recorded hashes and added settings against the resulting files.

## Overwrite and migration

A generated file may be refreshed without another prompt only when its entry has
`refresh: "template"` **and** its current hash matches its recorded installed hash.
Read changed, review-only, or unrecorded files, show the concrete differences, and
offer **Merge** (apply the template's changes while keeping the file's customizations;
update its hash and `refresh: "review"` only if already owned; keep an unrecorded file
unrecorded unless whole-file adoption was separately selected), **Keep existing**
(leave the file and its record as they are), or **Replace** (install the template
verbatim; record `refresh: "template"`).
Preserve conventions and custom code by default. Existing authorization for that
exact change is sufficient; do not ask twice. Customizable documents always retain
init's review-and-propose semantics.

For older installations without provenance, template equality can show there is
no content change, but filename/heading similarity never authorizes removal.
Show ambiguous legacy migrations with both the file and affected hook entries;
delete only an explicitly selected file and unregister only its selected entries.
Do not install a second hook for the same files while an undecided legacy hook
would remain active. Keep the current setup and report the unresolved migration.

## Reset

Hashes distinguish unchanged installed bytes from later edits. Reset still needs
the user's deletion selection. An exact current match to a recorded settings
entry may be removed only when its associated hook file was selected for removal
(if applicable); changed, shared, or unrecorded entries are kept unless separately
shown and explicitly selected. Preserve the record for retained files/entries.
For ambiguous legacy installations, preserving settings is the default, even when
their values happen to match today's permission template or MCP server names.
