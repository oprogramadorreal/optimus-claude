# Coding Guidelines

These guidelines inform architectural and design decisions when working on [PROJECT NAME].

## Core Principles

### Follow Existing Patterns
Match the codebase's architecture, naming, and style. When introducing a different approach, ensure it's a clear improvement and apply it consistently.

### Keep It Simple (KISS)
Default to the simplest design that meets current requirements. Introduce abstractions when they serve a concrete, immediate need — not a hypothetical future one.

### Prefer Clarity Over Cleverness
Choose clear, concise solutions with explicit control flow and simple data flow. Don't sacrifice readability for fewer lines or clever tricks.

## Naming and Structure

### Domain-Accurate Naming
Use names that reflect the domain. Prefer typed interfaces over primitives when it clarifies meaning.

### Small, Focused Functions (SRP)
Keep functions small with a single responsibility. Minimize parameters. Group related inputs into objects when it improves readability.

## Dependencies and Architecture

### Use Built-In Features First
Prefer framework and standard-library solutions over custom code or new dependencies.

### Pragmatic Abstractions
Apply SOLID principles and extract abstractions only when they improve clarity or are necessary to enable testing. Don't add indirection for its own sake. Ensure high cohesion, low coupling, and minimal side effects.

## Documentation

### Comment Intent, Not Code
Comment only non-obvious intent and tradeoffs. Don't narrate what the code already expresses.
