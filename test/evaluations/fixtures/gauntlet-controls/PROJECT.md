# General-purpose gauntlet controls

The task selects a control. This is not a paper-replication project. No new
dependencies are needed. `python check.py` is the project check. Preserve the
notes in `user-notes.txt`; the evaluator may stage or edit them before a run.

For behavior and integration work: route identifiers with surrounding whitespace
as their trimmed, case-sensitive equivalents through the public `route` function.
`None` and unknown identifiers return `None`. Preserve the caller-owned mapping,
including observation of later caller updates. The public route composes
`normalize` and `Catalog.lookup`; passing isolated component checks is insufficient.

For visual work: make `index.html` match `reference.html` when viewed at both
360px and 1200px width. Preserve labels and keyboard-accessible links. Inspect the
actual rendering and provide reviewer-accessible visual evidence.

Gauntlet's independent critics, fixed remit, real execution, integration review,
test gate, stopping behavior and repository safeguards remain in force. Do not
create research-paper context artifacts for these controls.
