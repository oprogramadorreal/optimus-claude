# Coding Guidelines

These guidelines inform architectural and design decisions when working on [PROJECT NAME].

## Core Principles

### Follow Existing Patterns
Match the codebase's architecture, naming, and style. Don't introduce new patterns unless necessary.

### Keep It Simple (KISS)
Default to the simplest change that works. Avoid speculative abstractions and keep diffs minimal.

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
Apply SOLID principles and extract abstractions only when they improve clarity. Don't add indirection for its own sake. Ensure high cohesion, low coupling, and minimal side effects.

## Documentation

### Comment Intent, Not Code
Comment only non-obvious intent and tradeoffs. Don't narrate what the code already expresses.
