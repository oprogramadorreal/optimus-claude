# Prompt Templates Reference

13 prompt architectures for different task types. Load only the template matching the task — do not load the entire file.

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

---

## Template A — RTF

*Role, Task, Format. Use for fast one-shot tasks where the request is clear and simple.*

```
Role: [One sentence defining who the AI is]
Task: [Precise verb + what to produce]
Format: [Exact output format and length]
```

**Example:**
```
Role: You are a senior technical writer.
Task: Write a one-paragraph description of what a REST API is.
Format: Plain prose, 3 sentences maximum, no jargon, suitable for a non-technical audience.
```

---

## Template B — CO-STAR

*Context, Objective, Style, Tone, Audience, Response. Use for professional documents, business writing, reports, and marketing content.*

```
Context: [Background the AI needs to understand the situation]
Objective: [Exact goal — what success looks like]
Style: [Writing style: formal / conversational / technical / narrative]
Tone: [Emotional register: authoritative / empathetic / urgent / neutral]
Audience: [Who reads this — their knowledge level and expectations]
Response: [Format, length, and structure of the output]
```

**Example:**
```
Context: Founder pitching a B2B SaaS tool that automates expense reporting for mid-size companies.
Objective: Write a cold email that gets a reply from a CFO.
Style: Direct and conversational, not salesy.
Tone: Confident but not pushy.
Audience: CFO at a 200-person company, busy, skeptical of vendor emails.
Response: 5 sentences max. Subject line included. No bullet points.
```

---

## Template C — RISEN

*Role, Instructions, Steps, End Goal, Narrowing. Use for complex multi-step projects requiring a clear sequence.*

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

**Example:**
```
Role: Product manager with 10 years of experience in mobile apps.
Instructions: Write a product requirements document for a habit tracking feature.
Steps:
  1. Define the problem statement in one paragraph
  2. List user stories: "As a [user], I want [goal] so that [reason]"
  3. Define acceptance criteria for each story
  4. List out-of-scope items explicitly
End Goal: A PRD that an engineering team can begin sprint planning from immediately.
Narrowing: No technical implementation details. No wireframes. Under 600 words.
```

---

## Template D — CRISPE

*Capacity, Role, Insight, Statement, Personality, Experiment. Use for creative work, brand voice, and iterative content.*

```
Capacity: [What capability or expertise the AI should have]
Role: [Specific persona to adopt]
Insight: [Key background insight that shapes the response]
Statement: [The core task or question]
Personality: [Tone and style — witty / authoritative / casual / sharp]
Experiment: [Request variants or alternatives to explore]
```

**Example:**
```
Capacity: Expert copywriter specializing in SaaS product launches.
Role: Brand voice for a productivity tool aimed at developers.
Insight: Developers hate marketing speak and respond to honesty and specificity.
Statement: Write the hero headline and sub-headline for the landing page.
Personality: Sharp, dry, confident — no adjectives, no exclamation marks.
Experiment: Give 3 variants ranging from minimal to bold.
```

---

## Template E — Chain of Thought

*For logic-heavy tasks, math, debugging, and multi-factor analysis. ONLY for standard reasoning models (Claude, GPT, Gemini, Qwen 2.5, Llama). NEVER for o3, o4-mini, DeepSeek-R1, or Qwen3 thinking mode.*

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

**When to use:** debugging with non-obvious cause, comparing technical approaches, math/calculation, analysis where a wrong first impression is likely.

**When NOT to use:** o3/o4-mini/R1/Qwen3-thinking (they think internally — CoT hurts), simple tasks, creative tasks.

---

## Template F — Few-Shot

*When the output format is easier to show than describe. Examples outperform instructions for format-sensitive tasks.*

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

**Rules:** 2-5 examples. Include edge cases, not just easy cases. Use XML tags — Claude parses XML reliably.

---

## Template G — File-Scope

*For Cursor, Windsurf, GitHub Copilot — any code editing AI. Prevents the most common failure: editing the wrong file or breaking existing logic.*

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

---

## Template H — ReAct + Stop Conditions

*For Claude Code, Devin, autonomous agents. Runaway loops and scope explosion are the biggest credit killers — stop conditions are not optional.*

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

---

## Template I — Visual Descriptor

*For Midjourney, DALL-E, Stable Diffusion, Sora, Runway — image or video generation.*

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
- **Midjourney**: Comma-separated descriptors, `--ar`, `--style`, `--v 6` at end
- **Stable Diffusion**: `(word:1.3)` weight syntax, CFG 7-12, mandatory negative prompt
- **DALL-E 3**: Prose works well, add "do not include any text in the image" unless text is needed
- **Sora / video**: Add camera movement (slow dolly, static shot, crane up), duration, cut style

---

## Template J — Reference Image Editing

*When the user has an existing image to modify. Never describe the whole scene — only the change.*

Before writing the prompt, always tell the user: "Attach your reference image to [tool name] before sending this prompt."

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

---

## Template K — ComfyUI

*Node-based image workflows. Always output Positive and Negative as separate blocks.*

Ask first if not stated: "Which checkpoint model are you using? (SD 1.5, SDXL, Flux, or other)"

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

---

## Template L — Prompt Decompiler

*When the user pastes an existing prompt to break down, adapt, simplify, or split.*

Detect which task is needed:
- **Break down** — explain what each part does
- **Adapt** — rewrite for a different tool while preserving intent
- **Simplify** — remove redundancy and tighten
- **Split** — divide a complex one-shot into a cleaner sequence

For Adapt tasks, always ask: "What tool is the original from, and what tool are you adapting it for?"

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

---

## Template M — Exploration + Plan Architecture

*Your output is a PROMPT the user will paste as the first message in a new Claude Code plan-mode conversation — NEVER produce the plan itself.*

*Plan-mode Claude reads the project's CLAUDE.md and explores the codebase on its own. The prompt tells it WHAT to figure out — it does not pre-answer those questions.*

*Verify and optimize the user's input before including it in "Context." Read referenced files to confirm findings, ask the user if something seems incorrect, and synthesize the information into clear, actionable context. Do not copy user input verbatim — craft it. But do not add codebase exploration details beyond what the user provided.*

*Do not include plan-mode-redundant instructions (e.g., "do not execute changes," "this is read-only") — plan mode enforces these automatically.*

*You may or may not be running inside the target project. If you are (i.e., the current codebase is where the plan-mode prompt will be executed), use that access to improve the prompt: verify user claims against actual files, check that referenced paths exist, validate findings, and ask smarter clarifying questions. But use codebase access to improve the prompt's accuracy — not to pre-do plan-mode's exploration work.*

```
## Goal
[What needs to be achieved — the problem or change, in one clear paragraph.
Include WHY it matters if that shapes the approach.]

## Context
[Verified, optimized synthesis of the user's input: findings, constraints, prior
decisions, referenced documents. Verify correctness where possible, ask if
something seems off, and integrate seamlessly — but do not add codebase
exploration details beyond what the user provided.]

## Starting Hints (optional — omit if the user did not mention specific locations)
[Specific files, directories, or patterns the user mentioned as relevant.]

## What to Figure Out
[Questions that plan-mode Claude should answer through its own codebase
exploration. Frame as questions, not as pre-explored findings.]
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

**When to use:** The user wants Claude Code in plan mode to explore a codebase and produce an implementation plan. The prompt provides problem context and defines what the plan should contain — it does NOT pre-explore the codebase or pre-answer analytical questions.

**When NOT to use:** The user wants Claude Code to execute changes directly — use Template H instead.
