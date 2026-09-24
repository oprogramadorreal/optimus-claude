# Architecture

<!-- Delete any section with nothing project-specific to say rather than filling it with generalities; every bullet count below is a ceiling, not a target. -->

## Overview

[1-2 sentences: the architecture pattern — MVC, layered, hexagonal, microservices, etc.; for skill-authoring projects, also what kind (Claude Code plugin, prompt library, agent framework) and its primary purpose]

## Directory Map

[Only directories whose purpose is not obvious from the name, or whose contents are generated or owned by another system. Skip the rest — a listing already shows them. Delete this section if nothing qualifies.]

| Directory | Purpose |
|-----------|---------|
| `[dir]/` | [description] |

<!-- Code sections: keep the next three sections only when the project has code components; delete them (and this comment) for pure skill-authoring projects -->

## Data Flow

[How requests or data actually move through this system — entry point → routing → business logic → data layer, or whatever shape it really has. At most 4 bullets.]

## Key Patterns

[At most 4 bullets: architectural patterns actually in use here, and why. Skip patterns a reader would infer from the framework.]

## Dependencies Between Modules

[Module boundaries and which modules depend on which — enough to keep a change from introducing a cycle or crossing a layer.]

<!-- Skill Architecture: keep this section only when skill authoring was detected; delete it (and this comment) otherwise -->

## Skill Architecture

[How instruction files are organized here, only where it is not evident from the directory layout: naming and structure conventions, where agent prompts live and what context they receive, reference depth and canonical ownership, and how multi-step flows coordinate — delegation, user checkpoints, handoffs between skills. At most 6 bullets total; drop any of those topics this project has nothing specific to say about.]
