# CLAUDE.md Best Practices Reference

This document contains best practices for writing effective CLAUDE.md files, extracted from industry knowledge and the HumanLayer engineering blog.

## Core Principles

### The Stateless Foundation

LLMs have frozen weights at inference time and learn nothing from sessions. CLAUDE.md is the **only** file automatically included in every agent conversation, making it critical for context continuity. Every line in this file affects every workflow phase.

### High-Leverage Point

CLAUDE.md is one of the highest leverage points in your Claude Code setup. Craft it deliberately rather than auto-generating. Consider every line carefully.

## Content Structure: WHAT/WHY/HOW Framework

Structure your CLAUDE.md around three dimensions:

### WHAT - Technical Overview
- Technology stack and frameworks
- Project structure and codebase map
- **Especially important in monorepos**: clarify apps, shared packages, and their purposes so the agent knows where to locate things

### WHY - Purpose and Reasoning
- Project purpose and function of different components
- Reasoning behind architectural decisions
- Why certain patterns or conventions exist

### HOW - Operational Guidance
- Package manager and build system
- Test execution commands
- Typecheck and lint procedures
- Compilation and build steps
- Verification methods

## Instruction Management

### Quantity Constraints
- Research indicates frontier LLMs can follow **~150-200 instructions** with reasonable consistency
- Claude Code's system prompt already contains ~50 instructions, leaving limited capacity
- Smaller models degrade exponentially as instructions increase
- Larger models show linear decay with instruction count

### Universal Applicability Rule
- Include **only** instructions broadly applicable to all tasks
- Avoid task-specific commands
- Avoid database schema structures or unrelated guidance
- Non-universally-applicable content **distracts** the model and reduces quality

### Length Guidelines
- Keep files under **300 lines** maximum
- Ideal target: **under 60 lines** (HumanLayer maintains theirs at this size)
- Less is more - every line must earn its place

## Progressive Disclosure Pattern

### Separate Task-Specific Documentation
Create individual markdown files for detailed topics:
- `building_the_project.md`
- `running_tests.md`
- `code_conventions.md`
- `service_architecture.md`
- `database_schema.md`
- `service_communication_patterns.md`

### Reference Strategy
- Reference these files from CLAUDE.md with brief descriptions
- Let Claude decide which documents to consult based on the task
- Use `file:line` pointers instead of embedded code snippets
- Embedded code becomes outdated quickly
- Point to authoritative sources rather than duplicating content

## What NOT to Include

### Code Style Guidelines
**"Never send an LLM to do a linter's job."**
- Formatters are cheaper, faster, and more reliable
- Use deterministic tools (ESLint, Prettier, Biome, etc.)
- Style instructions consume context and degrade instruction-following quality
- Let tooling handle formatting enforcement

### Auto-Generated Content
- Avoid `/init` commands or auto-generated templates for CLAUDE.md
- The file requires deliberate crafting, not boilerplate
- Generic content dilutes the effectiveness

### Irrelevant Instructions
- Claude ignores content marked as non-relevant
- Built-in system reminders tell Claude to only use "highly relevant" context
- Overloading with non-universal instructions causes Claude to ignore instructions entirely

## Alternative Approaches for Style & Formatting

Instead of putting style rules in CLAUDE.md:

### Stop Hooks
Configure Claude Code to run formatters/linters automatically and present errors for Claude to fix.

### Slash Commands
Create custom commands that reference code guidelines alongside version control changes.

### In-Context Learning
- Provide code examples through repository searches
- Agents learn patterns naturally from existing code
- No explicit rules needed for consistent style

## Claude's Attention Behavior

### Periphery Placement Effect
Instructions at the **beginning** (system message/CLAUDE.md) and **end** (recent messages) receive more attention than middle content.

### Ignoring Mechanism
Claude Code injects a system reminder stating context "may or may not be relevant" and should only be used if "highly relevant to your task." Including too much non-universal content triggers this filtering.

## Monorepo Pattern

For monorepos with multiple subprojects, use a hierarchical CLAUDE.md approach:

### Root CLAUDE.md as Orchestrator
- Maps the overall repo architecture (subproject table with paths, purposes, tech stacks)
- Contains only root-level / workspace-wide commands
- References each subproject's CLAUDE.md
- Links to shared docs (coding guidelines apply to all subprojects)
- Still under 60 lines

### Subproject CLAUDE.md for Scoped Guidance
- Placed directly in the subproject directory (e.g., `packages/frontend/CLAUDE.md`)
- Claude Code auto-discovers these when working with files in that directory
- Same WHAT/WHY/HOW structure, scoped to one subproject
- References local `docs/` folder for subproject-specific testing, styling, architecture
- Mentions parent monorepo name for context
- Under 60 lines each

### Documentation Placement
- **Shared docs** (coding guidelines): Root `.claude/docs/` only — not duplicated per subproject
- **Subproject-specific docs** (testing, styling, architecture): In each subproject's `docs/` folder
- Each subproject's docs are scoped to its tech stack (e.g., frontend gets styling.md, backend does not)

### Why This Works
- Root CLAUDE.md stays lean by delegating subproject details to subproject files
- Claude only loads subproject context when working in that directory (on-demand)
- All levels are additive — root provides shared context, subproject provides specifics
- More specific instructions naturally take precedence on conflict

## Quality Checklist

When writing or reviewing your CLAUDE.md:

- [ ] Under 60 lines (ideal) or 300 lines (maximum)
- [ ] Contains only universally-applicable instructions
- [ ] Uses WHAT/WHY/HOW structure
- [ ] References separate docs for details (progressive disclosure)
- [ ] Uses file:line references instead of code snippets
- [ ] No code style rules (use linters instead)
- [ ] No task-specific or rarely-needed information
- [ ] Every line earns its place
- [ ] Monorepo: root CLAUDE.md is an orchestrator, not a dump of all subproject details
- [ ] Monorepo: each subproject has its own scoped CLAUDE.md under 60 lines

## Summary

Craft a focused onboarding document that addresses:
1. Project architecture (WHAT)
2. Purpose and reasoning (WHY)
3. Workflows and commands (HOW)

Delegate specific instructions to separate documents via progressive disclosure. Use tooling for style enforcement. Deliberately minimize and prioritize content for maximum instruction-following consistency.

**Remember: Less is more.**
