# Architecture

## Overview

[1-2 sentences: high-level architecture pattern — MVC, layered, hexagonal, microservices, etc.; for skill-authoring projects, also what kind (Claude Code plugin, prompt library, agent framework) and its primary purpose]

## Directory Map

| Directory | Purpose |
|-----------|---------|
| `[dir]/` | [description] |

<!-- Code sections: keep the next three sections only when the project has code components; delete them (and this comment) for pure skill-authoring projects -->

## Data Flow

[2-4 bullets or a short description: how requests/data move through the system — entry point → routing → business logic → data layer, or similar]

## Key Patterns

[2-4 bullets: important architectural patterns in use — dependency injection, repository pattern, event-driven, middleware chain, etc.]

## Dependencies Between Modules

[Brief description of module boundaries and which modules depend on which — helps prevent circular dependencies and maintain separation of concerns]

<!-- Skill Architecture: keep this section only when skill authoring was detected; delete it (and this comment) otherwise -->

## Skill Architecture

### Skill Organization

[2-4 bullets: how skills/agents/prompts are organized — naming conventions, directory structure, what files each skill directory contains]

### Agent Boundaries

[2-4 bullets: how agent definitions are scoped — shared vs skill-specific, context each agent receives, model assignments]

### Reference Hierarchy

[2-4 bullets: reference structure — maximum depth, shared vs local references, canonical ownership]

### Orchestration Patterns

[2-4 bullets: how skills coordinate multi-step workflows — agent delegation, user interaction points, checkpoint patterns]
