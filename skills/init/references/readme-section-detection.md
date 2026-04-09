# README Section Detection

Algorithm for finding existing development setup instructions in project documentation. Referenced by init (Step 7) and how-to-run (Step 2).

## Heading Patterns

Match markdown headings (levels 1–3) against these patterns (case-insensitive):

```
Getting Started, Development, Setup, Installation, Running,
Quick Start, Local Development, How to Run, Prerequisites,
Running Locally, Dev Setup, Local Setup, Developer Guide,
Development Environment, Building, Build & Run
```

Regex: `(?i)^#{1,3}\s+(Getting Started|Development|Setup|Installation|Running|Quick Start|Local Development|How to Run|Prerequisites|Running Locally|Dev Setup|Local Setup|Developer Guide|Development Environment|Building|Build & Run)`

## Section Boundary Detection

Once a matching heading is found, the section extends from that heading to the next heading of the **same or higher level** (fewer `#` marks). Collect all content within that boundary for analysis.

## Classification Rules

For each aspect (Prerequisites, Installation, External Services, Environment Config, Running in Development, Building, Testing), classify as:

**Found & accurate** — the section documents this aspect AND the documented commands/versions/tools match the current project state (manifests, lock files, docker-compose, `.env.example`).

**Found but outdated** — the section documents this aspect BUT specific details contradict current project state. Examples: wrong package manager command (`npm install` but project uses pnpm), missing a required service that's in docker-compose, outdated runtime version constraint.

**Partial** — the section mentions this aspect but lacks actionable detail. Examples: "Install dependencies" without the actual command, "Set up the database" with no instructions.

**Missing** — no mention of this aspect found in any scanned document.

## Comparison Method

For each documented command or tool reference, cross-check against:
- Manifest scripts (package.json scripts, pyproject.toml scripts, Makefile targets)
- Lock files (which package manager is actually used)
- Docker-compose service definitions (which services exist, their ports, images)
- `.env.example` / `.env.sample` (which variables are required)
- Runtime constraint fields (`engines.node`, `python_requires`, `rust-version`, etc.)

A command is "outdated" only when a concrete contradiction exists — not when the documentation is simply less detailed than it could be.

## Fallback for Non-Standard READMEs

If no matching headings are found but the README exists, search paragraph text for keywords: `install`, `run`, `start`, `setup`, `docker`, `prerequisites`, `dependencies`. If found, report the location to the user as "possible dev instructions without a clear section heading" and include in the assessment.
