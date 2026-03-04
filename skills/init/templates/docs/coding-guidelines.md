# Coding principles for [PROJECT NAME]

## Follow Existing Patterns
Match the codebase's architecture, naming, and style. Prefer framework and standard-library solutions over custom code or new dependencies. When introducing a different approach, ensure it's a clear improvement and document the rationale. Apply new patterns consistently — don't leave the codebase in a mixed state.

## Keep It Simple (KISS)
Default to the simplest design that meets current requirements. Prefer clear, explicit solutions over compact or clever tricks. Avoid speculative abstractions — extract helpers and layers only when they improve clarity or reduce duplication. Remove dead code — unused functions, unreachable branches, and commented-out blocks add noise without value.

## Single Responsibility (SRP) / Manage Complexity
Keep functions, classes, and modules focused on a single responsibility. When a unit handles multiple concerns, mixes abstraction levels, or has deeply nested control flow — decompose it. Deep nesting and long methods signal missing abstractions, not a need for more simplicity. Group related parameters into objects when it improves readability.

## Domain-Accurate Naming
Use names that reflect the domain. Prefer typed interfaces over primitives when it clarifies meaning. Comment only non-obvious intent and tradeoffs — don't narrate what the code already expresses.

## Pragmatic Abstractions
Apply SOLID principles and extract abstractions when they improve clarity, reduce duplication, or enable testing. Don't add indirection for its own sake. Ensure high cohesion, low coupling, and minimal side effects. Evolve patterns when the codebase outgrows them — but migrate deliberately, not speculatively.
