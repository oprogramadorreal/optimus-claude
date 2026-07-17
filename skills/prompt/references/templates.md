# Prompt Templates Reference

14 prompt architectures. Load only the template matching the task — do not load the entire file. This file is the single source for the Claude Code plan-mode (Template M) and dynamic-workflow (Template N) behavioral rules.

## Table of Contents

| Template | Best For |
|----------|----------|
| [A — RTF](#template-a--rtf) | Simple one-shot tasks |
| [B — CO-STAR](#template-b--co-star) | Professional documents, business writing |
| [C — RISEN](#template-c--risen) | Complex multi-step projects |
| [D — CRISPE](#template-d--crispe) | Creative work, brand voice |
| [E — Chain of Thought](#template-e--chain-of-thought) | Logic, math, analysis, debugging |
| [F — Few-Shot](#template-f--few-shot) | Consistent structured output, pattern replication |
| [G — File-Scope](#template-g--file-scope) | Cursor, Windsurf, Copilot — code editing AI |
| [H — ReAct + Stop Conditions](#template-h--react--stop-conditions) | Claude Code, Devin — autonomous agents |
| [I — Visual Descriptor](#template-i--visual-descriptor) | Midjourney, DALL-E, Stable Diffusion, Sora |
| [J — Reference Image Editing](#template-j--reference-image-editing) | Editing an existing image with a reference |
| [K — ComfyUI](#template-k--comfyui) | ComfyUI node-based image workflows |
| [L — Prompt Decompiler](#template-l--prompt-decompiler) | Breaking down, adapting, or splitting existing prompts |
| [M — Exploration + Plan Architecture](#template-m--exploration--plan-architecture) | Claude Code plan mode — codebase exploration and planning |
| [N — Dynamic Workflow Orchestration](#template-n--dynamic-workflow-orchestration) | Claude Code dynamic workflows — fan-out / parallel subagent work |

## Template A — RTF

*Role, Task, Format — fast one-shot tasks where the request is clear and simple.*

```
Role: [One sentence defining who the AI is]
Task: [Precise verb + what to produce]
Format: [Exact output format and length]
```

## Template B — CO-STAR

*Professional documents, business writing, reports, marketing content.*

```
Context: [Background the AI needs to understand the situation]
Objective: [Exact goal — what success looks like]
Style: [Writing style: formal / conversational / technical / narrative]
Tone: [Emotional register: authoritative / empathetic / urgent / neutral]
Audience: [Who reads this — their knowledge level and expectations]
Response: [Format, length, and structure of the output]
```

## Template C — RISEN

*Complex multi-step projects requiring a clear sequence.*

```
Role: [Expert identity]
Instructions: [Overall task in plain terms]
Steps:
  1. [First action]
  2. [Second action]
  3. [Continue as needed]
End Goal: [What the final output must achieve]
Narrowing: [Constraints, scope limits, what to exclude]
```

## Template D — CRISPE

*Creative work, brand voice, iterative content.*

```
Capacity: [What capability or expertise the AI should have]
Role: [Specific persona to adopt]
Insight: [Key background insight that shapes the response]
Statement: [The core task or question]
Personality: [Tone and style — witty / authoritative / casual / sharp]
Experiment: [Request variants or alternatives to explore]
```

## Template E — Chain of Thought

*Logic-heavy tasks, math, debugging, multi-factor analysis. Gated by SKILL.md hard rule 3: check the target tool's tool-routing.md entry first — never for reasoning-native models or tools that calibrate reasoning automatically (use that entry's nudge wording instead). Not for simple or creative tasks.*

```
[Task statement]

Before answering, think through this carefully:
<thinking>
1. What is the actual problem being asked?
2. What constraints must the solution respect?
3. What are the possible approaches?
4. Which approach is best and why?
</thinking>

Give your final answer in <answer> tags only.
```

## Template F — Few-Shot

*When the output format is easier to show than describe. 2-5 examples; include edge cases, not just easy cases; XML tags — Claude parses XML reliably.*

```
[Task instruction]

Here are examples of the exact format needed:

<examples>
  <example>
    <input>[example input 1]</input>
    <output>[example output 1]</output>
  </example>
  <example>
    <input>[example input 2]</input>
    <output>[example output 2]</output>
  </example>
</examples>

Now apply this exact pattern to: [actual input]
```

## Template G — File-Scope

*Cursor, Windsurf, GitHub Copilot — any code editing AI. Prevents the most common failure: editing the wrong file or breaking existing logic.*

```
File: [exact/path/to/file.ext]
Function/Component: [exact name]

Current Behavior:
[What this code does right now]

Desired Change:
[What it should do after the edit]

Scope:
Only modify [function / component / section].
Do NOT touch: [list everything to leave unchanged]

Constraints:
- Language/framework: [specify version]
- Do not add dependencies not in [manifest file]
- Preserve existing [type signatures / API contracts / variable names]

Done When:
[Exact condition that confirms the change worked]
```

## Template H — ReAct + Stop Conditions

*Claude Code, Devin, autonomous agents. Runaway loops and scope explosion are the biggest credit killers — stop conditions are not optional.*

```
Objective:
[Single, unambiguous goal in one sentence]

Starting State:
[Current file structure / codebase state / environment]

Target State:
[What should exist when the agent is done]

Allowed Actions:
- [Specific action the agent may take]
- Install only packages listed in [manifest file]

Forbidden Actions:
- Do NOT modify files outside [directory/scope]
- Do NOT run the dev server or deploy
- Do NOT push to git
- Do NOT delete files without showing a diff first
- Do NOT make architecture decisions without human approval

Stop Conditions:
Pause and ask for human review when:
- A file would be permanently deleted
- A new external service or API needs to be integrated
- Two valid paths exist and the choice affects architecture
- An error cannot be resolved in 2 attempts
- The task requires changes outside the stated scope

Checkpoints:
After each major step, output: [what was completed]
At the end, output a full summary of every file changed.
```

## Template I — Visual Descriptor

*Midjourney, DALL-E, Stable Diffusion, Sora, Runway — image or video generation.*

```
Subject: [Main subject — specific, not vague]
Action/Pose: [What the subject is doing]
Setting: [Where the scene takes place]
Style: [photorealistic / cinematic / anime / oil painting / vector / etc.]
Mood: [dramatic / serene / eerie / joyful / etc.]
Lighting: [golden hour / studio / neon / overcast / candlelight / etc.]
Color Palette: [dominant colors or named palette]
Composition: [wide shot / close-up / aerial / Dutch angle / etc.]
Aspect Ratio: [16:9 / 1:1 / 9:16 / 4:3]
Negative Prompts: [blurry, watermark, extra fingers, distortion, low quality]
Style Reference: [artist / film / aesthetic reference if applicable]
```

**Tool-specific syntax:**
- **Midjourney**: comma-separated descriptors, `--ar`, `--style`, `--v 6` at end
- **Stable Diffusion**: `(word:1.3)` weight syntax, CFG 7-12, mandatory negative prompt
- **DALL-E 3**: prose works well; add "do not include any text in the image" unless text is needed
- **Sora / video**: add camera movement (slow dolly, static shot, crane up), duration, cut style
- **Seedance 2** (video): its prompt shape differs entirely — apply its Video AI entry in tool-routing.md instead of this field list

## Template J — Reference Image Editing

*When the user has an existing image to modify. Never describe the whole scene — only the change. Before writing the prompt, always tell the user: "Attach your reference image to [tool name] before sending this prompt."*

```
Reference image: [attached / URL]
What to keep exactly the same: [list everything that must not change]
What to change: [specific edit only — be precise]
How much to change: [subtle / moderate / significant]
Style consistency: maintain the exact style, lighting, and mood of the reference
Negative prompt: [what to avoid introducing]
```

**Tool-specific editing:**
- Midjourney: `--cref [image URL]` for character reference, `--sref` for style reference
- DALL-E 3: Edit endpoint, not Generate. User must have image editing enabled
- Stable Diffusion: img2img mode, denoising strength 0.3-0.6

## Template K — ComfyUI

*Node-based image workflows. Always output Positive and Negative as separate blocks. Ask first if not stated: "Which checkpoint model are you using? (SD 1.5, SDXL, Flux, or other)"*

```
POSITIVE PROMPT:
[subject], [style], [mood], [lighting], [composition], [quality boosters]

NEGATIVE PROMPT:
[what to exclude: blurry, low quality, watermark, extra limbs, bad anatomy, distorted]

CHECKPOINT: [model name]
SAMPLER: Euler a
CFG SCALE: 7
STEPS: 20-30
RESOLUTION: [width x height — divisible by 64]
```

**Model notes:** SD 1.5: under 75 tokens, use (word:weight). SDXL: longer prompts OK, natural language. Flux: natural language, less weight syntax, responsive to style.

## Template L — Prompt Decompiler

*When the user pastes an existing prompt to break down, adapt, simplify, or split.*

Detect the task: **Break down** (explain what each part does), **Adapt** (rewrite for a different tool, preserving intent — always ask: "What tool is the original from, and what tool are you adapting it for?"), **Simplify** (remove redundancy and tighten), or **Split** (divide a complex one-shot into a cleaner sequence).

Wrap each pasteable prompt block below — the `Recommended fix`, the `Adapted for [target tool]` block, and each split `[prompt block]` — in its own pair of the SKILL.md output-contract boundary markers. Labels, analysis, and commentary lines stay outside the markers.

**Break down format:**
```
Original prompt: [paste]

Structure analysis:
- Role/Identity: [what role is assigned and why]
- Task: [what action is being requested]
- Constraints: [what limits are set]
- Format: [what output shape is expected]
- Weaknesses: [what is missing or could cause wrong output]

Recommended fix: [rewritten version with gaps filled]
```

**Adapt format:**
```
Original ([source tool]): [original prompt]

Adapted for [target tool]:
[rewritten prompt using target tool syntax and best practices]

Key changes made:
- [change 1 and why]
- [change 2 and why]
```

**Split format:**
```
Original prompt: [paste]

This prompt is doing [N] things. Split into [N] sequential prompts:

Prompt 1 — [what it handles]:
[prompt block]

Prompt 2 — [what it handles]:
[prompt block]

Run these in order. Each output feeds the next.
```

## Template M — Exploration + Plan Architecture

*For Claude Code plan mode — produces a PROMPT the user pastes into a new plan-mode conversation. NEVER produce the plan itself.*

- Plan-mode Claude reads the project's CLAUDE.md and explores the codebase on its own — the prompt tells it WHAT to figure out, not pre-answers
- Verify and optimize user input: read referenced files to confirm findings, ask if something seems incorrect, synthesize into clear context — do not copy verbatim. Resolve entity names to paths, but do not explore code structure or internals beyond what the user provided — never pre-do plan-mode's exploration
- Preserve the user's explicit methodology instructions — if the user says to search the web, verify assumptions, ask questions, or use specific tools, carry those instructions into the prompt (typically in "What to Figure Out"). Do not silently drop them during synthesis
- NEVER include plan-mode-redundant guardrails ("YOU ARE IN PLAN MODE", "DO NOT EDIT CODE", "read-only", "do not execute") — plan mode enforces read-only automatically

```
## Goal
[The problem or change in one clear paragraph — include WHY if it shapes the approach.]

## Context
[Verified, optimized synthesis of the user's input: findings, constraints, prior
decisions, referenced documents — no exploration details beyond what the user provided.]

## Starting Hints (omit if the user named no locations)
[Files, directories, or patterns the user mentioned as relevant.]

## What to Figure Out
[Questions plan-mode Claude should answer through exploration. Frame as questions,
not pre-explored findings; include any research method the user requested.]
1. [Question about feasibility, approach, or architecture]
2. [Question about existing patterns to follow or reuse]
3. [Question about risks, trade-offs, or open decisions]

## Plan Deliverable
The plan should include:
- [Section the user needs — e.g., "Proposed approach with rationale"]
- [Section the user needs — e.g., "Files to create or modify, with what changes"]
- [Section the user needs — e.g., "Implementation sequence and dependencies"]
- [Section the user needs — e.g., "Risks and open questions"]

## Scope
- Focus on: [areas relevant to the goal]
- Out of scope: [areas to skip — saves tokens]
```

**When to use:** plan-mode codebase exploration ending in an implementation plan the prompt defines but does not pre-answer. **When NOT to use:** executing changes directly — Template H.

## Template N — Dynamic Workflow Orchestration

*For Claude Code dynamic workflows — produces a single NATURAL-LANGUAGE PROMPT the user pastes into an active Claude Code session to launch a workflow of REAL parallel subagents (exempt from hard rule 2 — the passes are real, not simulated). NEVER author a .js workflow script, and do NOT prescribe the workflow's phases or agent counts — describe the task, outcome, and constraints; Claude Code designs the orchestration and writes the script.*

- Express orchestration as **intent**, in natural language — open with "Run a workflow to…" (the scaffold below does). The prompt must clearly ask for a workflow of parallel agents, not a turn-by-turn task
- Describe the task, the quality bar (e.g. "cross-check findings before reporting"), and the required output. A pattern-type hint (fan-out / pipeline / adversarial-verification) is optional preference, never a prescribed phase plan with agent counts
- Scope is MANDATORY (cost + runaway risk): bound the target set and give an early-stop condition. The runtime auto-caps each run at 16 concurrent / 1,000 total agents — fixed limits, not knobs the prompt sets; the prompt's job is only to keep the target set from sprawling
- Permissions: workflow subagents run with edits auto-approved (acceptEdits) regardless of session mode. For analysis/audit work the prompt MUST say "read-only: do not edit, write, move, or delete any file; report findings only." (Opposite of Template M, which omits guardrails because plan mode enforces read-only)
- Do NOT put an approval or cost line in the prompt — Claude Code shows a launch-time approval with the planned phases on its own. Tell the *user* about the approval gate and token cost in the SKILL.md Step 7 handoff instead

```
Run a workflow to [TASK — what to do across what bounded target set: files / dirs / items].

Desired outcome: [what a good result looks like — the deliverable's purpose, not the steps].

You design the orchestration — decide the phases, how many agents, and how they divide and (where useful) cross-check the work. I'm giving you the task, the constraints, and the quality bar; you write the script and choose the shape.

Quality bar: [intent only — e.g. "be thorough: cover every item in scope"; "cross-check / verify findings before reporting and drop anything you can't confirm"; "approach this from several independent angles and reconcile them"]. Don't just run more agents — apply whatever verification makes the result trustworthy.

Scope:
- In scope: [explicit targets].  Out of scope: [skip].
- Mode: [READ-ONLY — do NOT edit, write, move, or delete any file; report findings only.  OR  agents may edit only within <path>; do NOT touch <forbidden>]. (Workflow agents auto-approve edits regardless of session mode — state this explicitly.)
- Stop early if [condition]; keep work bounded to the in-scope targets above. (The runtime auto-caps each run at 16 concurrent / 1,000 total agents — you don't set these.)

Output: [exact shape — e.g., one markdown report grouping findings by file with file:line evidence].
```

*Match the prompt's weight to the task: the block above is the full scaffold for a non-trivial fan-out; for a simple, clearly-bounded task one or two sentences naming the task, scope, read-only-vs-edit, and output shape are enough. Orchestration stays Claude Code's to design at any length.*

**When to use:** Claude Code fan-out / parallel work at scale — audit every X, review N files independently, research several angles, or draft a plan from several angles then weigh them. **When NOT to use:** a single linear task (Template H), read-only plan-mode exploration (Template M), any non-Claude-Code tool, or when the user wants the .js script itself.

*Setup: dynamic workflows may need enabling in `/config` on some plans.*
