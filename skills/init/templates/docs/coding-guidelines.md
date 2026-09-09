# Coding principles for [PROJECT NAME]

> Optimus baseline. Init refreshes recorded, unchanged template copies; customized copies remain subject to review. Keep project-specific rules here or in a routed project guide.

## Follow existing patterns

Write code that reads like the code around it — match the architecture, naming, and idiom already there. Prefer the framework and the standard library over a new dependency or a hand-rolled equivalent. A different approach has to be a clear improvement, and applied consistently rather than left as a second style in the same codebase.

## Scope discipline

Only change what the task requires. Don't improve adjacent code, add docstrings to untouched functions, or reformat files you are passing through. A bug fix does not need surrounding cleanup, and a one-shot operation rarely needs a helper. Remove code your change strands; leave code you merely walked past for its own change.

## Build what is required

Default to the simplest design that meets current requirements. No speculative abstractions, no configurability, no error handling beyond what correctness and security actually need, no half-finished implementations. When you control every call site, change them directly rather than adding a compatibility shim or a feature flag; for a published API with external consumers, follow the project's deprecation policy.

## Abstraction

Extract an abstraction when it removes real duplication, separates concerns that are already tangled, or makes something testable — not for symmetry, and not in anticipation of reuse. Deep nesting and long functions are evidence to weigh, not a trigger. When simplicity and decomposition pull against each other, the tiebreak is which version a reader understands faster. Aim for high cohesion, low coupling, and few side effects; evolve a pattern when the codebase has outgrown it, deliberately rather than speculatively.

## Validate at trust boundaries

Validate untrusted input — user input, external APIs, deserialization, and your own public API surface. Within a trust domain, rely on internal code and framework guarantees instead of guarding against states that cannot occur. Complexity that exists to satisfy a security or correctness requirement is not over-engineering.

## Names and comments

Names carry purpose and domain meaning, scaled to scope: short for short-lived locals, descriptive for module-level and public symbols. Avoid placeholders like `data`, `info`, or `temp` that send the reader elsewhere for context. Comment non-obvious intent and tradeoffs; don't narrate what the code already says.
