# Coding principles for [PROJECT NAME]

## Follow Existing Patterns
Match the codebase's architecture, naming, and style. Prefer framework and standard-library solutions over custom code or new dependencies. When introducing a different approach, ensure it's a clear improvement and document the rationale. Apply new patterns consistently — don't leave the codebase in a mixed state.

## Keep It Simple (KISS)
Default to the simplest design that meets current requirements (YAGNI). Prefer clear, explicit solutions over compact or clever tricks. Avoid speculative abstractions and half-finished implementations — extract helpers and layers only when they improve clarity or reduce duplication. Don't add features, error handling, or configurability beyond what was requested or required for correctness/security. Validate at trust boundaries — untrusted input such as user input, external APIs, and deserialization, including your own public API surface — and within a single trust domain, trust internal code and framework guarantees rather than guarding against scenarios that cannot happen. When you control all call sites, change the code directly instead of adding feature flags or backwards-compatibility shims; for published APIs or libraries with external consumers, follow the project's deprecation policy. A bug fix doesn't need surrounding cleanup and a one-shot operation rarely needs a helper. Only modify what the task requires — don't "improve" adjacent code, add docstrings to untouched functions, or reformat files you're passing through. Remove dead code — unused functions, unreachable branches, and commented-out blocks add noise without value. Comment only non-obvious intent and tradeoffs — don't narrate what the code already expresses.

## Single Responsibility (SRP) / Manage Complexity
Keep functions, classes, and modules focused on a single responsibility. When a unit handles multiple concerns, mixes abstraction levels, or has deeply nested control flow — decompose it. Deep nesting and long methods signal missing abstractions, not a need for more simplicity. Group related parameters into objects and prefer typed interfaces over primitives when it clarifies meaning.

## Intention-Revealing Names
Choose names that convey purpose and domain meaning — a reader should understand what a variable holds, what a function does, or what a class represents without tracing through the implementation. Avoid abbreviations, single-letter names outside tiny scopes, and generic placeholders like `data`, `info`, or `temp` that force the reader to look elsewhere for context. Scale name length to scope: short names for short-lived locals, descriptive names for module-level and public symbols.

## Pragmatic Abstractions
Apply SOLID principles and extract abstractions when they improve clarity, reduce duplication (DRY), or enable testing. Don't add indirection for its own sake. Ensure high cohesion, low coupling, and minimal side effects. Evolve patterns when the codebase outgrows them — but migrate deliberately, not speculatively.
