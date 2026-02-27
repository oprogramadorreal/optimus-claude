# Coding Guidelines

These guidelines inform architectural and design decisions when working on [PROJECT NAME].

## Core Principles

### Follow Existing Patterns
Match the codebase's architecture, naming, and style. Don't introduce new patterns unless necessary.

### Keep It Simple (KISS)
Default to the simplest change that works. Avoid speculative abstractions and keep diffs minimal.

### Prefer Clarity
Choose clear, concise solutions. Reduce duplication but don't sacrifice readability for fewer lines.

### Readability Over Cleverness
Use explicit control flow and simple data flow. Prioritize correctness over clever tricks.

## Naming and Structure

### Domain-Accurate Naming
Use names that reflect the domain. Prefer typed interfaces over primitives when it clarifies meaning.

### Small, Focused Functions (SRP)
Keep functions small with a single responsibility. Minimize parameters. Group related inputs into objects when it improves readability.

## Dependencies and Architecture

### Minimize Dependencies
Prefer existing dependencies and built-in features. Avoid adding new packages unnecessarily.

### Pragmatic SOLID
Apply SOLID principles when they improve clarity and maintainability. Don't add indirection just to "be SOLID."

### Extract Abstractions Sparingly
Only create abstractions for clarity. Ensure high cohesion, low coupling, and minimal side effects.

## Documentation

### Comment Intent, Not Code
Comment only non-obvious intent and tradeoffs. Don't narrate what the code already expresses.
