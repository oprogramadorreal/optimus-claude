# Skill-writing guidelines for [PROJECT NAME]

This file governs the quality of **markdown instruction files** authored for an AI agent — skills, agents, prompts, commands, or instructions. Code files (Python, TypeScript, etc.) follow `coding-guidelines.md` instead. When reviewing, refactoring, or evaluating any file, route to the lens that matches the file's type: prose instruction files use the rules below; code files use `coding-guidelines.md`.

## Foundation

The core quality principles apply to instruction authoring just as they apply to code — but the concrete rules differ.

- **Follow Existing Patterns** — match the project's existing instruction structure, frontmatter conventions, directory layout, and reference patterns. Prefer established approaches over novel ones. When introducing a new pattern, apply it consistently — don't leave the project in a mixed state.
- **KISS** — default to the simplest instructions that meet current requirements. Don't add steps or branches for hypothetical scenarios. Remove dead steps — unused branches, commented-out instructions, and redundant clarifications add noise without value. Safety procedures (validation rules, command allowlists, user-approval gates) and explicit behavioral constraints are requirements — their detail is justified, not a simplicity violation.
- **SRP** — each instruction file focused on one concern, each step on one action. When a step handles multiple concerns or mixes abstraction levels, decompose it.

  > **Exception — orchestration files:** An instruction file may span multiple concerns when it serves as a one-time setup orchestrator whose value depends on executing all steps atomically. Keep orchestration files well-structured internally — each step should still follow SRP.

- **Intention-Revealing Names** — file names, directory names, and reference doc names should convey purpose without tracing through content. Avoid generic names like `helper.md`, `utils.md`, or `doc2.md`.
- **Pragmatic Abstractions** — extract shared references when 2+ instruction files reuse a procedure. Don't add indirection for its own sake. Don't extract for hypothetical future reuse.

## Writing Style

- The AI agent is already very smart — only add context it doesn't already have. Challenge each instruction: "Does the agent really need this?" Omit explanations of concepts the agent already knows; include behavioral rules, safety constraints, and domain procedures it can't infer.
- Imperative step-by-step instructions, not conversational prose.
- Keep instruction file bodies short — move detailed reference material to separate files. If a file grows past a few hundred lines, split it.
- No time-sensitive information. Consistent terminology throughout — pick one term per concept and use it everywhere (e.g., always "field" not a mix of "field", "box", "element").

## Degrees of Freedom

Match the level of specificity to the task's fragility:

- **High freedom** (text-based guidance) — when multiple approaches are valid and decisions depend on context. Example: code review criteria, documentation structure.
- **Medium freedom** (pseudocode or parameterized templates) — when a preferred pattern exists but some variation is acceptable. Example: report generation with configurable sections.
- **Low freedom** (exact scripts, no deviation) — when operations are fragile, consistency is critical, or a specific sequence must be followed. Example: database migrations, validation commands.

Default to high freedom unless the task is fragile. Provide a sensible default with an escape hatch rather than listing many options.

## Description Quality (frontmatter)

- When the agent framework uses frontmatter `description` fields, they must describe both WHAT the instruction does AND WHEN to use it — descriptions are how the agent selects the right instruction from many available ones.
- Write descriptions in third person — they are injected into the system prompt. Good: "Generates commit messages by analyzing diffs." Avoid: "I can help you generate commit messages."
- Include specific keywords users would naturally say.
- Be concrete and specific, not vague. Bad: "Helps with documents." Good: "Extracts text and tables from PDF files, fills forms, merges documents. Use when working with PDF files or when the user mentions PDFs, forms, or document extraction."
- Prefer gerund form for instruction names when possible: `processing-pdfs`, `analyzing-code`. Avoid vague names: `helper`, `utils`, `tools`.

## Progressive Disclosure

- Load only metadata (description) at startup.
- Load the full instruction file only when it is invoked.
- Load reference files only as needed within the instruction's execution.
- Reference depth should not exceed two levels from the main instruction file (INSTRUCTION→A→B maximum). If you need A→B→C→D, restructure by flattening the chain — make the main instruction reference the deeper files directly. Only inline content when the extracted file is small, single-use, and tightly coupled to its parent; otherwise inlining violates SRP by mixing concerns in one file. Circular references between files are never allowed.
- For reference files longer than 100 lines, include a table of contents at the top so the agent can see the full scope even when previewing with partial reads.

## Directory Layout

- Group related instruction files in conventional directories (`skills/`, `agents/`, `prompts/`, `commands/`, `instructions/`) — whichever your framework uses.
- Split detailed reference material into separate files under `references/` or similar.
- When using prompt templates for sub-agents, put each agent's prompt in its own file — don't inline agent prompts in the main instruction file.

## Shared References

- When a procedure is used by 2+ instructions, extract to a reference file owned by one canonical instruction. Others read the reference and apply their own policy — avoiding logic duplication while keeping each instruction self-contained.

## Workflows and Feedback Loops

For complex multi-step instructions:

- Break operations into clear sequential steps. For particularly complex workflows, provide a checklist the agent can copy and track progress against.
- Implement feedback loops for quality-critical tasks: run validator → fix errors → repeat. Make validation a gate — "only proceed when validation passes."
- Use conditional workflows to guide the agent through decision points: "Creating new? → follow creation workflow. Editing existing? → follow editing workflow."

## Common Patterns

- **Template pattern** — provide output format templates. Use strict templates ("ALWAYS use this exact structure") when consistency is critical; use flexible templates ("sensible default, adapt as needed") when context should drive the structure.
- **Examples pattern** — provide input/output pairs (like few-shot prompting) when output quality depends on matching a specific style or format. Examples communicate style and detail level more clearly than descriptions alone.
- **Conditional workflow** — branch instructions based on detected state or user intent. Push large branches into separate reference files rather than inlining them all in the main instruction.

## Evaluation and Iteration

- Build evaluations before writing extensive documentation — identify what the agent gets wrong without the instruction, then write minimal instructions to address those gaps.
- Test instructions iteratively: write minimal instructions → test with real tasks → observe behavior → refine.
- Watch how the agent navigates the instruction in practice: does it miss references? Over-rely on certain sections? Ignore bundled files? Iterate based on these observations.

## Anti-patterns

- **Over-explaining** — don't explain what PDFs are or how libraries work. The agent knows. Add only what it can't infer: project-specific rules, domain procedures, safety constraints.
- **Too many options** — don't list five libraries for the same task. Provide one sensible default with an escape hatch for edge cases.
- **Windows-style paths** — always use forward slashes (`reference/guide.md`), never backslashes. Forward slashes work cross-platform.
- **Inconsistent terminology** — pick one term per concept. Don't mix "field"/"box"/"element" or "extract"/"pull"/"get" for the same operation.

## Documentation

- Every instruction should have a user-facing description or README explaining what it does and when to use it.
- After any instruction change, verify the user-facing description and any referring indexes still reflect current behavior.
