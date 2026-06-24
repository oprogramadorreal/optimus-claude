# Prompt Templates Reference

14 prompt architectures for different task types. Load only the template matching the task — do not load the entire file.

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
- **Seedance 2**: prose, not labeled fields (~60-100 words, Subject → Action → Environment → Camera → Style → Audio). ONE camera move; pacing words, not specs. DROP the Negative Prompts field — unsupported; fold exclusions into positive phrasing ("clean motion, correct hands"). Native synced audio; `@Image1`/`@Video1` reference tags

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

When delivering any decompiler output below, wrap each pasteable prompt block — the `Recommended fix`, the `Adapted for [target tool]` block, and each split `[prompt block]` — in the same plain-text boundary markers used in SKILL.md Step 8 (`----- BEGIN PROMPT -----` above the opening fence, `----- END PROMPT -----` below the closing fence, always OUTSIDE the fence). Do not wrap the Structure analysis, Key changes, or commentary lines — only the pasteable prompt text.

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

Wrap each `[prompt block]` above in its own `----- BEGIN PROMPT -----` / `----- END PROMPT -----` markers (placed outside its code fence) so each sequential prompt is individually selectable. Keep the `Prompt N — [what it handles]:` labels and the "Run these in order…" line outside the markers.

---

## Template M — Exploration + Plan Architecture

*For Claude Code plan mode — produces a PROMPT the user pastes into a new plan-mode conversation. NEVER produce the plan itself.*

- Plan-mode Claude reads the project's CLAUDE.md and explores the codebase on its own — the prompt tells it WHAT to figure out, not pre-answers
- Verify and optimize user input: read referenced files to confirm findings, ask if something seems incorrect, synthesize into clear context — do not copy verbatim. Resolve entity names to paths (validation), but do not explore code structure or internals beyond what the user provided
- If running inside the target project, use codebase access to validate user claims and improve prompt accuracy — but not to pre-do plan-mode's exploration
- Preserve the user's explicit methodology instructions — if the user says to search the web, verify assumptions, ask questions, or use specific tools, carry those instructions into the prompt (typically in "What to Figure Out" or as a standalone section). Do not silently drop them during synthesis
- NEVER include plan-mode-redundant guardrails ("YOU ARE IN PLAN MODE", "DO NOT EDIT CODE", "read-only", "do not execute") — plan mode enforces read-only automatically

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
[Questions that plan-mode Claude should answer through exploration —
codebase analysis, web research, or other methods the user specified.
Frame as questions, not as pre-explored findings.
If the user explicitly requested a research method (e.g., "search the web
to confirm"), include that instruction with the relevant question.]
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

---

## Template N — Dynamic Workflow Orchestration

*For Claude Code dynamic workflows — produces a single NATURAL-LANGUAGE PROMPT the user pastes into an active Claude Code session that asks it to spin up a workflow (real subagents running in parallel). Like Template M requests plan mode, this requests orchestration as INTENT. NEVER author or output a .js workflow script, and do NOT prescribe the workflow's phases or agent counts — describe the task, outcome, and constraints; Claude Code designs the orchestration and writes the script.*

- Not a banned multi-pass technique: Hard Rule #2 bans orchestration SIMULATED inside one inference pass. A workflow runs REAL independent subagents in REAL parallel inference; the orchestration lives in platform code, not one model turn. Output is still ONE prompt.
- Express orchestration as **intent**, in natural language — open with "Run a workflow to…" (the scaffold below does). Claude Code recognizes this as a workflow-launch intent; you do not need a single magic keyword (the older literal-`workflow` trigger has been superseded by natural-language launch recognition; the `ultracode` keyword is a separate opt-in for multi-agent orchestration, not the launch phrase). What matters is that the prompt clearly asks for a workflow of parallel agents, not a turn-by-turn task.
- Describe the task, the quality bar (e.g. "cross-check findings before reporting"), and the required output — then hand the orchestration to Claude Code: it decides the phases, agent counts, and verification mechanics and writes the script. A pattern-type hint (fan-out / pipeline / adversarial-verification) is optional preference in the prompt, never a prescribed phase plan with agent counts.
- Scope is MANDATORY (cost + runaway risk): bound the target set and give an early-stop condition. The runtime auto-caps each run at 16 concurrent / 1,000 total agents — fixed limits, not knobs the prompt sets; the prompt's job is only to keep the *target set* from sprawling. Note the run uses meaningfully more tokens than one conversation.
- Permissions: workflow subagents run with edits auto-approved (acceptEdits) regardless of session mode. For analysis/audit work the prompt MUST say "read-only: do not edit, write, move, or delete any file; report findings only." (Opposite of Template M, which omits guardrails because plan mode enforces read-only.)
- Do NOT put an approval or cost line in the prompt — Claude Code shows a launch-time approval prompt with the planned phases on its own (same reason Template M omits plan mode's enforced read-only: don't restate what the platform already does). Tell the *user* about the approval gate and token cost in the SKILL.md Step 9 handoff instead.

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

*Match the prompt's weight to the task. The block above is the full scaffold for a non-trivial or ambiguous fan-out; for a simple, clearly-bounded task a lean prompt is enough — one or two sentences naming the task, scope, read-only-vs-edit, and output shape. Never pad. Orchestration stays Claude Code's to design at any length.*

**When to use:** Claude Code fan-out / parallel work at scale — audit every X, review N files independently, research several angles, or draft a plan from several angles then weigh them.

**When NOT to use:** a single linear task (Template H), read-only plan-mode exploration (Template M), any non-Claude-Code tool, or when the user wants the .js script itself. Also: when the user wants to implement a tracked spec/task as a parallel build — the dedicated `/optimus:workflow` skill owns that entry point; Template N is for one-off, ad-hoc fan-out prompts.

*Setup: dynamic workflows may need enabling in `/config` on some plans.*
