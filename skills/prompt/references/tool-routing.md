# Tool Routing Reference

Prompt-specific guidance for each AI tool category. Load only the section matching the target tool — do not load the entire file.

## Table of Contents

| Category | Tools |
|----------|-------|
| [General-Purpose LLMs](#general-purpose-llms) | Claude, ChatGPT / GPT-5.x, Gemini 2.x / 3 Pro, MiniMax |
| [Reasoning-Native LLMs](#reasoning-native-llms) | o3 / o4-mini, DeepSeek-R1, Qwen3 thinking mode |
| [Open-Weight LLMs](#open-weight-llms) | Qwen 2.5, Llama, Mistral, Ollama |
| [IDE AI](#ide-ai) | Claude Code, Cursor / Windsurf, Cline, GitHub Copilot, Antigravity |
| [Agentic AI](#agentic-ai) | Devin / SWE-agent, Bolt / v0 / Lovable / Figma Make / Google Stitch |
| [Computer-Use Agents](#computer-use-agents) | Perplexity Comet, OpenAI Atlas, Claude in Chrome |
| [Research / Orchestration](#research--orchestration) | Perplexity, Manus, Perplexity Computer |
| [Image AI — Generation](#image-ai--generation) | Midjourney, DALL-E 3, Stable Diffusion, SeeDream |
| [Image AI — Editing](#image-ai--editing) | Reference image modification workflows |
| [Image AI — ComfyUI](#image-ai--comfyui) | Node-based workflows |
| [3D AI](#3d-ai) | Meshy, Tripo, Rodin, Unity AI, BlenderGPT |
| [Video AI](#video-ai) | Sora, Runway, Kling, LTX Video, Dream Machine, Seedance 2 |
| [Voice AI](#voice-ai) | ElevenLabs |
| [Workflow AI](#workflow-ai) | Zapier, Make, n8n |

## General-Purpose LLMs

Unlike [Reasoning-Native LLMs](#reasoning-native-llms), these accept explicit CoT scaffolding (Template E) for logic-heavy tasks — unless the tool's entry says reasoning is calibrated automatically (e.g., current Claude); the entry is authoritative for the CoT decision.

### Claude (claude.ai, Claude API, Claude 4.x / Fable 5)

- Be explicit and specific — Claude follows instructions literally, not by inference; always specify output format and length
- XML tags for complex multi-section prompts: `<context>`, `<task>`, `<constraints>`, `<output_format>`
- Claude Opus 4.x and Fable 5 over-engineer / over-tidy by default — add "Only make changes directly requested. Do not add features or refactor beyond what was asked."
- Don't instruct Fable 5 to echo or transcribe its reasoning as output text — that can trigger a refusal and fallback to Opus
- Provide context and reasoning WHY, not just WHAT — Claude generalizes better from explanations
- For complex or multi-step tasks, front-load everything in one turn — intent, constraints, acceptance criteria, relevant files; extra back-and-forth adds reasoning overhead and cost
- Don't add "think step by step" or a fixed thinking budget — current Claude calibrates reasoning depth automatically. To nudge: "Think carefully before responding" (more) or "Prioritize responding quickly" (less)

### ChatGPT / GPT-5.x

- Start with the smallest prompt that achieves the goal — add structure only when needed; handles dense, compact instruction well
- Be explicit about the output contract: format, length, what "done" looks like; state tool-use expectations if the model has tools
- Constrain verbosity when needed: "Respond in under 150 words. No preamble. No caveats."

### Gemini 2.x / Gemini 3 Pro

- Prone to hallucinated citations — always add "Cite only sources you are certain of. If uncertain, say [uncertain]."
- Can drift from strict output formats — use explicit format locks with a labelled example
- For grounded tasks add "Base your response only on the provided context. Do not extrapolate."
- Strong at long-context and multimodal — leverage the large context window for document-heavy prompts

### MiniMax (M3 / M2.7)

- OpenAI-compatible API — prompts that work with GPT transfer directly; for function calling, include OpenAI-style tool schemas
- Strong at instruction following, structured (JSON) output, and long-context synthesis; M2.7-highspeed is tuned for latency-sensitive tasks
- Temperature must be in the range [0, 1] — values above 1 fail
- May emit reasoning in `<think>` tags — add "Output only the final answer, no reasoning tags." if visible thinking is unwanted

## Reasoning-Native LLMs

These models reason internally across thousands of tokens. Adding CoT or "think step by step" instructions actively degrades their output.

### o3 / o4-mini

- SHORT clean instructions ONLY — state what you want and what done looks like, nothing more; system prompts under 200 words
- NEVER add CoT, "think step by step", or reasoning scaffolding
- Prefer zero-shot first — add few-shot only if strictly needed

### DeepSeek-R1

- Reasoning-native like o3 — do NOT add CoT; short clean instructions, goal and output format only
- Outputs reasoning in `<think>` tags by default — add "Output only the final answer, no reasoning." if needed

### Qwen3 (thinking mode)

- Thinking mode (/think or enable_thinking=True): treat exactly like o3 — short clean instructions, no CoT, no scaffolding
- Non-thinking mode: treat like Qwen 2.5 instruct — full structure, explicit format, role assignment

## Open-Weight LLMs

### Qwen 2.5 (instruct variants)

- Excellent instruction following, JSON output, structured data — works well with explicit format specs including JSON schemas
- Provide a clear system prompt defining the role; shorter focused prompts outperform long complex ones

### Llama / Mistral / open-weight LLMs

- Shorter prompts with simple flat structure — these models lose coherence with deeply nested instructions
- Be more explicit than with Claude or GPT — instruction following is weaker; always include a role in the system prompt

### Ollama (local model deployment)

- ALWAYS ask which model is running before writing — Llama3, Mistral, Qwen2.5, CodeLlama behave differently
- System prompt is the most impactful lever — include it in the output so the user can set it in their Modelfile
- Shorter simpler prompts outperform complex ones — local models lose coherence with deep nesting
- Temperature 0.1 for coding/deterministic tasks, 0.7-0.8 for creative tasks
- For coding: CodeLlama or Qwen2.5-Coder, not general Llama

## IDE AI

### Claude Code

- Agentic — runs tools, edits files, executes commands autonomously. Structure per Template H: starting state + target state + allowed/forbidden actions + stop conditions + checkpoints
- Stop conditions are MANDATORY — runaway loops are the biggest credit killer
- The [Claude entry's](#claude-claudeai-claude-api-claude-4x--fable-5) model steers apply (over-engineering guard, reasoning nudges); effort and thinking depth are harness-managed — do NOT hardcode an effort level or thinking budget
- Reasons more between tool calls and uses fewer of them by default — instruct tool use explicitly when needed: "Read all files in src/auth/ before starting"
- Spawns fewer subagents by default — request one explicitly when wanted: "Use a subagent to investigate X so it stays out of the main context"
- Always scope to specific files and directories — never a global instruction without a path anchor
- Human review triggers required: "Stop and ask before deleting any file, adding any dependency, or affecting the database schema"
- For complex tasks: split into sequential prompts. Output Prompt 1 and add "Run this first, then ask for Prompt 2" below it

### Claude Code (plan mode)

- Produces a self-contained prompt pasted as the first message of a fresh plan-mode conversation — no prior context available
- All behavioral rules live in templates.md Template M

### Claude Code (dynamic workflow)

- For fan-out / parallel work at scale: a natural-language prompt that launches a NATIVE dynamic workflow — real subagents in parallel, orchestration designed by Claude Code. Distinct from the [Workflow AI](#workflow-ai) section (Zapier / Make / n8n)
- Output is a PROMPT only, never a .js script; all behavioral rules live in templates.md Template N

### Cursor / Windsurf

- File path + function name + current behavior + desired change + do-not-touch list + language and version — never a global instruction without a file anchor
- "Done when:" is required — defines when the agent stops editing
- For complex tasks: split into sequential prompts rather than one large prompt

### Cline (formerly Claude Dev)

- Agentic VS Code extension — edits files, runs terminal commands, uses browser tools; powered by Claude, GPT, or others, so match the prompt style to the underlying model
- Starting state + target state + file scope + stop conditions + approval gates; specify which files to edit and which to leave untouched
- Add "Ask before running terminal commands" or "Ask before installing dependencies" to prevent unwanted actions
- Shows a task list before executing — for multi-step work, break into sequential prompts with clear checkpoints

### GitHub Copilot

- Write the exact function signature, docstring, or comment immediately before invoking
- Describe input types, return type, edge cases, and what the function must NOT do
- Copilot completes what it predicts, not what you intend — leave no ambiguity in the comment

### Antigravity (Google, powered by Gemini 3 Pro)

- Task-based prompting — describe outcomes, not steps; scope to one deliverable per session
- Prompt for an Artifact (task list, implementation plan) before execution so you can review it first
- Browser automation is built-in — include verification steps: "After building, verify UI at 375px and 1440px using the browser agent"
- Specify autonomy level: "Ask before running destructive terminal commands"

## Agentic AI

### Devin / SWE-agent

- Fully autonomous — can browse web, run terminal, write and test code; very explicit starting state + target state required
- Forbidden actions list is critical — these agents make decisions you did not intend without explicit constraints
- Scope the filesystem: "Only work within /src. Do not touch infrastructure, config, or CI files."

### Bolt / v0 / Lovable / Figma Make / Google Stitch

- Full-stack generators default to bloated boilerplate — always specify stack, version, what NOT to scaffold, clear component boundaries
- Add "Do not add authentication, dark mode, or features not explicitly listed" to prevent feature bloat
- Lovable responds well to design-forward descriptions — include visual/UX intent
- v0 is Vercel-native — specify if you need non-Next.js output; Bolt handles full-stack — be explicit about frontend vs backend vs database parts
- Figma Make references your Figma component names directly; Google Stitch is prompt-to-UI — describe the interface goal, add "match Material Design 3 guidelines" for Google-native styling

## Computer-Use Agents

Perplexity Comet, OpenAI Atlas, Claude in Chrome — these agents control a real browser (click, scroll, fill forms, complete transactions autonomously).

- Describe the outcome with explicit constraints, not navigation steps: "Find the cheapest flight from X to Y on Emirates or KLM, no Boeing 737 Max, one stop maximum" — the agent makes its own decisions without them
- Add permission boundaries: "Do not make any purchase. Research only."
- Add a stop condition for irreversible actions: "Ask me before submitting any form, completing any transaction, or sending any message"
- Comet is best for web research, comparison, and data extraction; Atlas is stronger for multi-step commerce and account management

## Research / Orchestration

### Perplexity / SearchGPT

- Specify mode: search vs analyze vs compare; add citation requirements
- Reframe hallucination-prone questions as grounded queries

### Manus / Perplexity Computer

- Multi-agent orchestrators — describe the end deliverable, not the steps; they decompose internally. Specify the output artifact type (report / spreadsheet / code / summary)
- Add "Flag any data point you are not confident about."
- For long multi-step tasks: add verification checkpoints — each chained step compounds hallucination risk

## Image AI — Generation

First detect: generation from scratch or editing an existing image? If editing → see [Image AI — Editing](#image-ai--editing).

### Midjourney

- Comma-separated descriptors, not prose. Subject first, then style, mood, lighting, composition
- Parameters at end: `--ar 16:9 --v 6 --style raw`; negative prompts via `--no [unwanted elements]`

### DALL-E 3

- Prose description works well; add "do not include text in the image unless specified."
- Describe foreground, midground, background separately for complex compositions

### Stable Diffusion

- `(word:weight)` syntax. CFG 7-12. Negative prompt is MANDATORY
- Steps 20-30 for drafts, 40-50 for finals

### SeeDream

- Strong at artistic and stylized generation — specify art style explicitly (anime, cinematic, painterly) before scene content
- Mood and atmosphere descriptors work well. Negative prompt recommended
- Images only — not to be confused with **Seedance 2**, ByteDance's *video* model (see [Video AI](#video-ai))

## Image AI — Editing

When the user mentions "change", "edit", "modify", "adjust" anything in an existing image, or uploads a reference.

- Always instruct the user to attach the reference image to the tool first
- Build the prompt around the delta ONLY — what changes, what stays the same
- Midjourney: `--cref [image URL]` for character reference or `--sref` for style reference
- DALL-E 3: use the Edit endpoint, not Generate. User must be in ChatGPT with image editing enabled
- Stable Diffusion: use img2img mode, not txt2img. Denoising strength 0.3-0.6 to preserve the original

## Image AI — ComfyUI

Node-based workflow — not a single prompt box.

- Ask which checkpoint model is loaded before writing (SD 1.5, SDXL, Flux)
- Always output two separate blocks: Positive Prompt and Negative Prompt. Never merge them
- SD 1.5: shorter prompts, under 75 tokens per block, use (word:weight) syntax. SDXL: handles longer prompts, more natural language. Flux: natural language, less weighted syntax, very responsive to style descriptions

## 3D AI

### Text to 3D (Meshy, Tripo, Rodin)

- Describe: style keyword (low-poly / realistic / stylized cartoon) + subject + key features + primary material + texture detail + technical spec
- Negative prompt supported: "no background, no base, no floating parts"
- Meshy: best for game assets. Tripo: fastest for clean topology. Rodin: highest quality for photorealistic
- Specify intended export: game engine (GLB/FBX), 3D printing (STL), web (GLB); for characters, specify A-pose or T-pose if the model will be rigged

### In-Engine AI (Unity AI, BlenderGPT)

- Unity AI (Unity 6.2+): use /ask for docs, /run for automating Editor tasks, /code for C# code. Be precise about Editor operations
- Unity AI Generators: text-to-sprite, text-to-texture, text-to-animation. Describe asset type, art style, technical constraints (resolution, color palette, animation loop or one-shot)
- BlenderGPT / Blender AI add-ons: these generate Python scripts for Blender. Be specific about geometry, material names, and scene context. Include "apply to selected object" or "apply to entire scene"

## Video AI

- **Sora**: describe as if directing a film shot. Camera movement is critical — static vs dolly vs crane changes output dramatically
- **Runway Gen-3**: responds to cinematic language — reference film styles for consistent aesthetic
- **Kling**: strong at realistic human motion — describe body movement explicitly, specify camera angle and shot type
- **LTX Video**: fast generation, prompt-sensitive — keep descriptions concise and visual. Specify resolution and motion intensity
- **Dream Machine (Luma)**: cinematic quality — reference lighting setups, lens types, and color grading styles
- **Seedance 2 (ByteDance video, ≠ SeeDream)**: prose director-style (Subject → Action → Environment → Camera → Lighting → Style → Audio, ~60-100 words). ONE primary camera move per shot; pacing words, not specs ("slow dolly" not "24fps"). NO negative prompts — phrase exclusions positively ("clean motion, correct hands"). Native synced audio (dialogue in quotes) and `@Image1`/`@Video1` reference tags distinguish it from Sora/Kling. Multi-shot in one prompt: chain with "camera cuts to…" (or "Shot 1: / Shot 2:") and re-name the subject each shot so identity holds. Image-to-video: describe only the motion/change plus "preserve composition and colors"

## Voice AI

### ElevenLabs

- Specify emotion, pacing, emphasis markers, and speech rate directly — prose descriptions do not translate
- Use SSML-like markers for emphasis: indicate which words to stress, where to pause

## Workflow AI

### Zapier / Make / n8n

- Trigger app + trigger event → action app + action + field mapping. Step by step.
- Auth requirements noted explicitly — "assumes [app] is already connected"
- For multi-step workflows: number each step and specify what data passes between steps
