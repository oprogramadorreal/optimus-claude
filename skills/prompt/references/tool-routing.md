# Tool Routing Reference

Prompt-specific guidance for each AI tool category. Load only the section matching the target tool — do not load the entire file.

## Table of Contents

| Category | Tools |
|----------|-------|
| [Reasoning LLMs](#reasoning-llms) | Claude, ChatGPT / GPT-5.x, Gemini 2.x / 3 Pro |
| [Reasoning-Native LLMs](#reasoning-native-llms) | o3 / o4-mini, DeepSeek-R1, Qwen3 thinking mode |
| [Open-Weight LLMs](#open-weight-llms) | Qwen 2.5, Llama, Mistral, Ollama |
| [IDE AI](#ide-ai) | Claude Code, Cursor / Windsurf, GitHub Copilot, Antigravity |
| [Agentic AI](#agentic-ai) | Devin / SWE-agent, Bolt / v0 / Lovable / Figma Make / Google Stitch |
| [Computer-Use Agents](#computer-use-agents) | Perplexity Comet, OpenAI Atlas, Claude in Chrome |
| [Research / Orchestration](#research--orchestration) | Perplexity, Manus, Perplexity Computer |
| [Image AI — Generation](#image-ai--generation) | Midjourney, DALL-E 3, Stable Diffusion, SeeDream |
| [Image AI — Editing](#image-ai--editing) | Reference image modification workflows |
| [Image AI — ComfyUI](#image-ai--comfyui) | Node-based workflows |
| [3D AI](#3d-ai) | Meshy, Tripo, Rodin, Unity AI, BlenderGPT |
| [Video AI](#video-ai) | Sora, Runway, Kling, LTX Video, Dream Machine |
| [Voice AI](#voice-ai) | ElevenLabs |
| [Workflow AI](#workflow-ai) | Zapier, Make, n8n |

---

## Reasoning LLMs

### Claude (claude.ai, Claude API, Claude 4.x)

- Be explicit and specific — Claude follows instructions literally, not by inference
- XML tags for complex multi-section prompts: `<context>`, `<task>`, `<constraints>`, `<output_format>`
- Claude Opus 4.x over-engineers by default — add "Only make changes directly requested. Do not add features or refactor beyond what was asked."
- Provide context and reasoning WHY, not just WHAT — Claude generalizes better from explanations
- Always specify output format and length explicitly

### ChatGPT / GPT-5.x

- Start with the smallest prompt that achieves the goal — add structure only when needed
- Be explicit about the output contract: format, length, what "done" looks like
- State tool-use expectations explicitly if the model has access to tools
- Compact structured outputs — GPT-5.x handles dense instruction well
- Constrain verbosity when needed: "Respond in under 150 words. No preamble. No caveats."
- Strong at long-context synthesis and tone adherence

### Gemini 2.x / Gemini 3 Pro

- Strong at long-context and multimodal — leverage its large context window for document-heavy prompts
- Prone to hallucinated citations — always add "Cite only sources you are certain of. If uncertain, say [uncertain]."
- Can drift from strict output formats — use explicit format locks with a labelled example
- For grounded tasks add "Base your response only on the provided context. Do not extrapolate."

---

## Reasoning-Native LLMs

These models reason internally across thousands of tokens. Adding CoT or "think step by step" instructions actively degrades their output.

### o3 / o4-mini

- SHORT clean instructions ONLY
- NEVER add CoT, "think step by step", or reasoning scaffolding
- Prefer zero-shot first — add few-shot only if strictly needed
- State what you want and what done looks like. Nothing more.
- Keep system prompts under 200 words

### DeepSeek-R1

- Reasoning-native like o3 — do NOT add CoT instructions
- Short clean instructions only — state the goal and desired output format
- Outputs reasoning in `<think>` tags by default — add "Output only the final answer, no reasoning." if needed

### Qwen3 (thinking mode)

- Two modes: thinking mode (/think or enable_thinking=True) and non-thinking mode
- Thinking mode: treat exactly like o3 — short clean instructions, no CoT, no scaffolding
- Non-thinking mode: treat like Qwen 2.5 instruct — full structure, explicit format, role assignment

---

## Open-Weight LLMs

### Qwen 2.5 (instruct variants)

- Excellent instruction following, JSON output, structured data
- Provide a clear system prompt defining the role — responds well to role context
- Works well with explicit output format specs including JSON schemas
- Shorter focused prompts outperform long complex ones — scope tightly

### Llama / Mistral / open-weight LLMs

- Shorter prompts work better — these models lose coherence with deeply nested instructions
- Simple flat structure — avoid heavy nesting or multi-level hierarchies
- Be more explicit than with Claude or GPT — instruction following is weaker
- Always include a role in the system prompt

### Ollama (local model deployment)

- ALWAYS ask which model is running before writing — Llama3, Mistral, Qwen2.5, CodeLlama behave differently
- System prompt is the most impactful lever — include it in the output so user can set it in their Modelfile
- Shorter simpler prompts outperform complex ones — local models lose coherence with deep nesting
- Temperature 0.1 for coding/deterministic tasks, 0.7-0.8 for creative tasks
- For coding: CodeLlama or Qwen2.5-Coder, not general Llama

---

## IDE AI

### Claude Code

- Agentic — runs tools, edits files, executes commands autonomously
- Starting state + target state + allowed actions + forbidden actions + stop conditions + checkpoints
- Stop conditions are MANDATORY — runaway loops are the biggest credit killer
- Claude Opus 4.x over-engineers — add "Only make changes directly requested. Do not add extra files, abstractions, or features."
- Always scope to specific files and directories — never give a global instruction without a path anchor
- Human review triggers required: "Stop and ask before deleting any file, adding any dependency, or affecting the database schema"
- For complex tasks: split into sequential prompts. Output Prompt 1 and add "Run this first, then ask for Prompt 2" below it

### Claude Code (plan mode)

- Plan-mode Claude reads the project's CLAUDE.md for codebase orientation — do NOT replicate that information in the prompt
- "What to Figure Out" is the highest-value section — frame as questions, not pre-explored findings
- Scope boundaries help avoid wasted exploration — include when the user specified relevant areas
- The prompt must be self-contained — it will be pasted as the first message in a fresh conversation with no prior context
- See Template M in templates.md for full behavioral rules (input verification, codebase access policy, redundant-instruction exclusions)

### Cursor / Windsurf

- File path + function name + current behavior + desired change + do-not-touch list + language and version
- Never give a global instruction without a file anchor
- "Done when:" is required — defines when the agent stops editing
- For complex tasks: split into sequential prompts rather than one large prompt

### GitHub Copilot

- Write the exact function signature, docstring, or comment immediately before invoking
- Describe input types, return type, edge cases, and what the function must NOT do
- Copilot completes what it predicts, not what you intend — leave no ambiguity in the comment

### Antigravity (Google, powered by Gemini 3 Pro)

- Task-based prompting — describe outcomes, not steps
- Prompt for an Artifact (task list, implementation plan) before execution so you can review it first
- Browser automation is built-in — include verification steps: "After building, verify UI at 375px and 1440px using the browser agent"
- Specify autonomy level: "Ask before running destructive terminal commands"
- Do NOT mix unrelated tasks — scope to one deliverable per session

---

## Agentic AI

### Devin / SWE-agent

- Fully autonomous — can browse web, run terminal, write and test code
- Very explicit starting state + target state required
- Forbidden actions list is critical — these agents make decisions you did not intend without explicit constraints
- Scope the filesystem: "Only work within /src. Do not touch infrastructure, config, or CI files."

### Bolt / v0 / Lovable / Figma Make / Google Stitch

- Full-stack generators default to bloated boilerplate — scope it down explicitly
- Always specify: stack, version, what NOT to scaffold, clear component boundaries
- Lovable responds well to design-forward descriptions — include visual/UX intent
- v0 is Vercel-native — specify if you need non-Next.js output
- Bolt handles full-stack — be explicit about which parts are frontend vs backend vs database
- Figma Make is design-to-code native — reference your Figma component names directly
- Google Stitch is prompt-to-UI focused — describe the interface goal not the implementation. Add "match Material Design 3 guidelines" for Google-native styling
- Add "Do not add authentication, dark mode, or features not explicitly listed" to prevent feature bloat

---

## Computer-Use Agents

Perplexity Comet, OpenAI Atlas, Claude in Chrome — these agents control a real browser (click, scroll, fill forms, complete transactions autonomously).

- Describe the outcome, not the navigation steps: "Find the cheapest flight from X to Y on Emirates or KLM, no Boeing 737 Max, one stop maximum"
- Specify constraints explicitly — the agent will make its own decisions without them
- Add permission boundaries: "Do not make any purchase. Research only."
- Add a stop condition for irreversible actions: "Ask me before submitting any form, completing any transaction, or sending any message"
- Comet works best with web research, comparison, and data extraction tasks
- Atlas is stronger for multi-step commerce and account management tasks

---

## Research / Orchestration

### Perplexity / SearchGPT

- Specify mode: search vs analyze vs compare
- Add citation requirements
- Reframe hallucination-prone questions as grounded queries

### Manus / Perplexity Computer

- Multi-agent orchestrators — describe the end deliverable, not the steps. They decompose internally.
- Specify the output artifact type (report / spreadsheet / code / summary)
- Add "Flag any data point you are not confident about."
- For long multi-step tasks: add verification checkpoints since each chained step compounds hallucination risk

---

## Image AI — Generation

First detect: generation from scratch or editing an existing image? If editing → see [Image AI — Editing](#image-ai--editing).

### Midjourney

- Comma-separated descriptors, not prose. Subject first, then style, mood, lighting, composition
- Parameters at end: `--ar 16:9 --v 6 --style raw`
- Negative prompts via `--no [unwanted elements]`

### DALL-E 3

- Prose description works well
- Add "do not include text in the image unless specified."
- Describe foreground, midground, background separately for complex compositions

### Stable Diffusion

- `(word:weight)` syntax. CFG 7-12
- Negative prompt is MANDATORY
- Steps 20-30 for drafts, 40-50 for finals

### SeeDream

- Strong at artistic and stylized generation
- Specify art style explicitly (anime, cinematic, painterly) before scene content
- Mood and atmosphere descriptors work well. Negative prompt recommended

---

## Image AI — Editing

When user mentions "change", "edit", "modify", "adjust" anything in an existing image, or uploads a reference.

- Always instruct the user to attach the reference image to the tool first
- Build the prompt around the delta ONLY — what changes, what stays the same
- Midjourney: `--cref [image URL]` for character reference or `--sref` for style reference
- DALL-E 3: use the Edit endpoint, not Generate. User must be in ChatGPT with image editing enabled
- Stable Diffusion: use img2img mode, not txt2img. Denoising strength 0.3-0.6 to preserve the original

---

## Image AI — ComfyUI

Node-based workflow — not a single prompt box.

- Ask which checkpoint model is loaded before writing (SD 1.5, SDXL, Flux)
- Always output two separate blocks: Positive Prompt and Negative Prompt. Never merge them
- SD 1.5: shorter prompts, under 75 tokens per block, use (word:weight) syntax
- SDXL: handles longer prompts, more natural language alongside weighted syntax
- Flux: natural language works well, less reliance on weighted syntax, very responsive to style descriptions

---

## 3D AI

### Text to 3D (Meshy, Tripo, Rodin)

- Describe: style keyword (low-poly / realistic / stylized cartoon) + subject + key features + primary material + texture detail + technical spec
- Negative prompt supported: "no background, no base, no floating parts"
- Meshy: best for game assets. Tripo: fastest for clean topology. Rodin: highest quality for photorealistic
- Specify intended export: game engine (GLB/FBX), 3D printing (STL), web (GLB)
- For characters: specify A-pose or T-pose if the model will be rigged

### In-Engine AI (Unity AI, BlenderGPT)

- Unity AI (Unity 6.2+): use /ask for docs, /run for automating Editor tasks, /code for C# code. Be precise about Editor operations
- Unity AI Generators: text-to-sprite, text-to-texture, text-to-animation. Describe asset type, art style, technical constraints (resolution, color palette, animation loop or one-shot)
- BlenderGPT / Blender AI add-ons: these generate Python scripts for Blender. Be specific about geometry, material names, and scene context. Include "apply to selected object" or "apply to entire scene"

---

## Video AI

- **Sora**: describe as if directing a film shot. Camera movement is critical — static vs dolly vs crane changes output dramatically
- **Runway Gen-3**: responds to cinematic language — reference film styles for consistent aesthetic
- **Kling**: strong at realistic human motion — describe body movement explicitly, specify camera angle and shot type
- **LTX Video**: fast generation, prompt-sensitive — keep descriptions concise and visual. Specify resolution and motion intensity
- **Dream Machine (Luma)**: cinematic quality — reference lighting setups, lens types, and color grading styles

---

## Voice AI

### ElevenLabs

- Specify emotion, pacing, emphasis markers, and speech rate directly
- Use SSML-like markers for emphasis: indicate which words to stress, where to pause
- Prose descriptions do not translate — specify parameters directly

---

## Workflow AI

### Zapier / Make / n8n

- Trigger app + trigger event → action app + action + field mapping. Step by step.
- Auth requirements noted explicitly — "assumes [app] is already connected"
- For multi-step workflows: number each step and specify what data passes between steps
