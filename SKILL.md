---
name: bootstrap
description: Bootstrap effective documentation following LLM-optimized practices
disable-model-invocation: true
---

# Bootstrap Project Documentation

Create optimized CLAUDE.md and supporting docs using research-backed practices. Unlike `/init`, this generates structured documentation following the WHAT/WHY/HOW framework with progressive disclosure. Supports both single projects and monorepos.

## Before You Start

Read `.claude/skills/claude-code-bootstrap/references/claude-md-best-practices.md`. Key constraints:
- Every CLAUDE.md <= 60 lines
- Use file:line references, not code snippets
- Only universally-applicable instructions

## Step 1: Detect Project Context

**Identify project type** from manifest files:

| Manifest | Type | Package Manager |
|----------|------|-----------------|
| package.json | Node.js | npm, yarn, pnpm, bun |
| Cargo.toml | Rust | cargo |
| pyproject.toml, setup.py, requirements.txt | Python | pip, poetry, uv |
| *.csproj, *.sln | C#/.NET | dotnet |
| pom.xml | Java | maven |
| build.gradle | Java | gradle |
| go.mod | Go | go |
| CMakeLists.txt, Makefile | C/C++ | cmake, make |
| Gemfile | Ruby | bundler |

Note: `.sln` files reference `.csproj` projects — they confirm .NET presence but aren't independent project manifests. Don't count a root `.sln` for root-as-project detection.

**Extract**: Project name, tech stack, build system, available scripts.

**Detect active package manager** (this determines command prefixes for CLAUDE.md and settings.json):

| Type | Check (in priority order) | Result |
|------|---------------------------|--------|
| Node.js | `pnpm-lock.yaml` exists | pnpm |
| Node.js | `yarn.lock` exists | yarn |
| Node.js | `bun.lockb` exists | bun |
| Node.js | default / `package-lock.json` | npm |
| Python | `uv.lock` exists OR `[tool.uv]` in pyproject.toml | uv (prefix commands with `uv run`) |
| Python | `poetry.lock` exists OR `[tool.poetry]` in pyproject.toml | poetry (prefix with `poetry run`) |
| Python | default | pip (bare commands: `pytest`, `ruff`, etc.) |

Use the detected package manager for all commands in CLAUDE.md and settings.json. For example, if the Node.js project uses pnpm, write `pnpm run build` not `npm run build`. If the Python project uses uv, write `uv run pytest` not just `pytest`.

**Analyze structure** (stay shallow — existing docs are audited separately in Step 1b):
- README.md for project purpose and features
- Top-level directories for architecture pattern
- Entry points (main.ts, index.ts, app.module.ts, etc.)

**Check for monorepo indicators:**

**Step A — Check for workspace config files** (confirms monorepo alone):
- npm/yarn/pnpm workspaces: `workspaces` in root `package.json`, or `pnpm-workspace.yaml`
- Lerna (`lerna.json`), Nx (`nx.json`), Turborepo (`turbo.json`), Rush (`rush.json`)
- Cargo workspace: `[workspace]` in root `Cargo.toml`; Go workspace: `go.work`
- Gradle: `settings.gradle(.kts)` with `include`; Maven: `pom.xml` with `<modules>`
- Bazel: `WORKSPACE` or `WORKSPACE.bazel`

**Step B — Scan for independent manifests** (confirms monorepo if 2+ projects found):

Scan top-level directories for manifest files (from the manifest table above). Skip:
- **Dot-directories**: `.git`, `.github`, `.vscode`, etc.
- **Dependencies**: `node_modules`, `vendor`, `.venv`, `venv`, `env`
- **Build output**: `dist`, `build`, `out`, `target`, `bin`, `obj`
- **Framework/cache**: `.next`, `.nuxt`, `__pycache__`, `.cache`, `.tox`
- **Non-project**: `examples`, `demos`, `test-fixtures`, `e2e`, `__tests__`, `.storybook`, `samples`, `experiments`, `scripts`, `tools`, `docs`

**Depth-2 check for container directories:** For any scanned top-level directory that has no manifest and is not in the skip list, check its immediate subdirectories for manifest files (applying the same skip rules). This catches nested subprojects inside container directories (e.g., `app/API/` and `app/client/` inside `app/`). Count each qualifying subdirectory as a separate project using its full relative path (e.g., `app/API`, `app/client`).

**Root-as-project check** (only when the total number of qualifying projects found in Step B — including depth-2 results — equals exactly 1):
The root itself may be an independent project. Count it as an additional project if the root has a manifest file AND at least one of:
- A **framework-specific config** at root (`angular.json`, `next.config.*`, `nuxt.config.*`, `vue.config.*`, `svelte.config.*`, `astro.config.*`, `webpack.config.*`, `vite.config.*`, `tsconfig.app.json`)
- A **root source directory** (`src/`, `app/`, or `lib/`) containing source files, where the subdirectory project also has its own source files — indicating two separate codebases
- A **different test framework** at root vs the subdirectory (e.g., root has `karma.conf.js` while subdirectory has `jest.config.js`)

**Step C — Check supporting signals** (cannot confirm alone):

- `README.md` describes multi-component architecture (mentions separate apps, services, or components: "frontend and backend", "client and server", "API server", "microservices", etc.)
- `docker-compose.yml` / `compose.yml` defines multiple services with `build:` contexts pointing to different subdirectories
- Root manifest scripts use `concurrently`, `npm-run-all`, or `run-p`/`run-s` to launch multiple processes
- Proxy configuration exists (`proxy.conf.json`, `proxy.conf.js`, `setupProxy.js`) indicating a frontend proxying to a local backend

**Decision:**
- Workspace config found (Step A) → confirmed monorepo, enumerate from config
- 2+ projects with manifests (Step B) → confirmed monorepo, enumerate from projects
- Supporting signals (Step C) + 1 dir with manifest → likely monorepo, ask user to confirm
- Supporting signals only → insufficient evidence, ask user to identify subproject dirs
- No signals → single project

**If monorepo detected:** Inform user of detection signals and identified subprojects with tech stacks. Confirm before proceeding.

**Enumerate subprojects:**
- Step A detected: use workspace member list + any additional top-level dirs with manifests not in the config.
- Step B only: use all qualifying directories (including nested ones found via depth-2 check). If the root-as-project check qualified the root, include it too.
- Root-as-project or root-as-workspace-member (e.g., `"."` in workspaces): include in subproject table but do NOT create a separate CLAUDE.md — root CLAUDE.md covers it. Its docs go in `.claude/docs/`.
- For each subproject, detect its tech stack using the manifest table.

### Step 1 Checkpoint

Before proceeding, confirm you have all of the following. If any are missing, re-examine the project:

- **Project name** (from manifest or README)
- **Tech stack(s)** (languages, frameworks, from manifest dependencies)
- **Package manager** (detected from lock files / config — e.g., npm, pnpm, yarn, uv, poetry, pip)
- **Build/test/lint commands** (from manifest scripts, prefixed with the detected package manager)
- **Monorepo status**: single project, confirmed monorepo, or ambiguous (awaiting user input)
- If monorepo: **subproject list** with each subproject's path, purpose, and tech stack
- If monorepo: **workspace tool** (if any)
- **Existing files inventory** (existence check only — content is read in Step 1b): which of `.claude/CLAUDE.md`, `.claude/settings.json`, `.claude/docs/*`, root `CLAUDE.md`, subproject `CLAUDE.md` files already exist

Print this as a **Detection Summary** to the user before proceeding. This gives the user a chance to correct any misdetection before files are generated. If the user provides corrections, update the detection results accordingly before proceeding.

### Step 1b: Documentation Audit (only when existing docs found)

**Skip this step entirely if no existing documentation files were found in the inventory.** Proceed directly to Step 2.

If existing docs were found, analyze them to identify what needs updating:

1. **Read all existing doc files** from the inventory (CLAUDE.md, settings.json, all `.claude/docs/*.md`, and for monorepos each subproject's CLAUDE.md and `docs/*.md`).

2. **Compare documented state vs detected state:**

| Dimension | Check |
|-----------|-------|
| **Commands** | Do build/test/lint commands in CLAUDE.md and settings.json `allow` list match current manifest scripts? |
| **Tech stack** | Does the documented stack match current dependencies in manifest files? |
| **Structure** | Do folder names, entry points, and architecture references in docs match the actual filesystem? |
| **Doc coverage** | Are there detected project aspects (test framework, UI deps, complex architecture) with no corresponding doc? Are there docs for aspects no longer present? |
| **Monorepo** | Do subproject tables match current workspace members? Any added/removed subprojects? |

3. **Present an Audit Report** to the user, organized as:
   - **Outdated** — items in docs that no longer match the project (with specific before/after)
   - **Missing** — project aspects that should have docs but don't
   - **Accurate** — items that are still correct (brief summary, no action needed)

4. **Ask the user** how to proceed:
   - **Update all** — apply all recommended changes
   - **Selective** — present findings as a numbered list; user picks which numbers to apply. Unapproved findings are left as-is (existing content preserved).
   - **Fresh start** — ignore existing docs and regenerate from scratch (proceeds to Step 2 as if no docs existed)

Remember the user's choice and approved findings. Steps 2–6 will reference them to make targeted updates rather than full overwrites.

## Step 2: Handle Existing Files

**Audit-aware rule (applies to Steps 2–6):** If user chose "Fresh start", treat all files as Missing. Otherwise: if Step 1b marked a file as Accurate, skip it. If Outdated, apply only user-approved changes — preserve everything else. If Missing or no audit was run, create normally. For "Selective" updates, only act on approved findings.

**Before creating any file**, check if it already exists. If so, read it first. Inform the user what was preserved vs changed.

**Relocate when scope changes:** If docs need to move (e.g., root `.claude/docs/testing.md` → subproject-scoped in a monorepo), move content to the new location and remove the old file. Keep only `coding-guidelines.md` at root.

If root `CLAUDE.md` exists (not in `.claude/`), suggest removing it after `.claude/CLAUDE.md` is created.

## Step 3: Create Directory Structure

```bash
mkdir -p .claude/docs .claude/hooks
# Monorepo: also mkdir -p <subproject>/docs for each subproject from Step 1
```

## Step 4: Create CLAUDE.md

### Single project

Use template from `.claude/skills/claude-code-bootstrap/templates/single-project-claude.md`. Fill in all placeholders:
- Replace `[PROJECT NAME]` with the actual project name
- Replace `[One-line description]` with purpose from README or manifest
- Replace `[TECH STACK]` with detected languages and frameworks
- Replace command placeholders with real commands using the detected package manager
- Replace directory placeholders with actual project directories
- In the Documentation section, list only docs that were actually created using `.claude/docs/` prefix

The template follows WHAT/WHY/HOW structure. Keep total file under 60 lines. If no manifest was detected, use generic placeholders and inform user that manual customization is recommended.

### Monorepo

Use template from `.claude/skills/claude-code-bootstrap/templates/monorepo-claude.md` instead. Fill in:
- Subproject table with all detected subprojects (path, purpose, tech stack)
- Root-level / workspace-wide commands only (not subproject-specific commands)
- References to each subproject's CLAUDE.md
- If a workspace tool was detected (Step A), include "managed by [tool]" in the description line
- If no workspace tool was detected (Step B only), use "Monorepo with [N] packages" or "Multi-project repository with [N] components" without referencing a workspace tool

If root-as-project: also list root-scoped docs from `.claude/docs/` (testing.md, styling.md, architecture.md as applicable) in the Documentation section, alongside the shared `coding-guidelines.md`.

If more than 6 subprojects, group by category (apps, libs, services) in the root CLAUDE.md and move the full subproject table to `.claude/docs/architecture.md`. Keep descriptions concise (abbreviate stacks, e.g., "TS/React" not "TypeScript, React, Vite, Tailwind") to stay under 60 lines.

## Step 4b: Create Subproject CLAUDE.md Files (monorepo only)

For each detected subproject (except root-as-project/root-as-member — the root CLAUDE.md already covers it), create `<subproject>/CLAUDE.md` using template from `.claude/skills/claude-code-bootstrap/templates/subproject-claude.md`:
- Scope WHAT/WHY/HOW to that subproject's tech stack and purpose
- Include only commands specific to this subproject (run from its directory)
- Reference its local `docs/` folder for detailed documentation
- Mention parent monorepo name in the opening line
- Keep under 60 lines

## Step 5: Create settings.json

Use template from `.claude/skills/claude-code-bootstrap/templates/settings.json` (which provides the deny list). **Replace the empty allow list entirely** with commands appropriate for the detected project type — only include commands for the tech stacks actually present in this project:

| Type | Commands to Allow |
|------|-------------------|
| Node.js (npm) | `npm run`, `npx`, `npm ls` |
| Node.js (pnpm) | `pnpm run`, `pnpm -r`, `pnpm install`, `pnpm dev`, `pnpm build`, `pnpm test`, `pnpm lint`, `npx` |
| Node.js (yarn) | `yarn run`, `yarn`, `npx` |
| Node.js (bun) | `bun run`, `bunx` |
| Rust | `cargo build`, `cargo test`, `cargo run`, `cargo clippy` |
| Python (uv) | `uv run`, `uv sync`, `uv pip`, `ruff`, `mypy` |
| Python (poetry) | `poetry run`, `poetry install`, `ruff`, `mypy` |
| Python (pip) | `pytest`, `pip install`, `pip list`, `ruff`, `mypy`, `python -m pytest`, `python -m mypy` |
| C#/.NET | `dotnet build`, `dotnet test`, `dotnet run`, `dotnet restore`, `dotnet tool restore` |
| Java/Maven | `mvn compile`, `mvn test`, `mvn package` |
| Java/Gradle | `gradle build`, `gradle test`, `gradlew` |
| Go | `go build`, `go test`, `go run`, `go vet`, `golangci-lint` |
| C/C++ | `cmake`, `make`, `ctest`, `ninja` |
| Ruby | `bundle`, `rake`, `rspec` |

**If monorepo:** Union the permission sets for all tech stacks detected across subprojects into a single root `.claude/settings.json`.

**Preserve custom sections:** If an existing settings.json contains a `hooks` section or other custom configuration beyond `permissions`, preserve those sections when updating. Merge permission changes into the existing file structure rather than overwriting from the template.

## Step 5b: Install Formatter Hooks

Add auto-format hooks so files stay consistently formatted after every Edit/Write. Use templates from `.claude/skills/claude-code-bootstrap/templates/hooks/`.

**Audit-aware rule applies** (see Step 2). Additionally, skip a hook if `.claude/hooks/` already contains a file named `format-<stack>.*` (e.g., `format-python.py`, `format-python.sh`).

| Stack | Template | Formatter | Requires | Install when |
|-------|----------|-----------|----------|--------------|
| Python | `format-python.py` | black + isort | Python 3 | In project deps (requirements*.txt, pyproject.toml, Pipfile), or user approves |
| Node.js | `format-node.js` | prettier | Node.js | In package.json devDependencies, or user approves |
| Rust | `format-rust.sh` | rustfmt | Bash | Always (rustfmt is built-in) |
| Go | `format-go.sh` | gofmt | Bash | Always (gofmt is built-in) |
| C#/.NET | `format-csharp.sh` | csharpier | Bash | In `.config/dotnet-tools.json`, or user approves (suggest `dotnet tool install csharpier`) |

**Detect Python command** (only when the Python formatter hook will be installed): Run `python3 --version`. If it fails, run `python --version` and verify the output shows Python 3.x. Use whichever succeeds as `<python-cmd>` in hook commands below. If neither works, skip the Python hook and inform the user.

1. Copy applicable template(s) from `.claude/skills/claude-code-bootstrap/templates/hooks/` to `.claude/hooks/`.
2. External formatters not in deps → ask user "Add [formatter] as dev dependency and install format hook?" If declined, skip.
3. Add a `hooks.PostToolUse` entry to `.claude/settings.json` (merge with existing). All hooks share one matcher entry — add each hook command to the `hooks` array:

```json
"hooks": {
  "PostToolUse": [
    {
      "matcher": "Edit|Write",
      "hooks": [
        { "type": "command", "command": "<python-cmd> \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/format-python.py", "timeout": 30 },
        { "type": "command", "command": "node \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/format-node.js", "timeout": 30 },
        { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/format-csharp.sh", "timeout": 30 }
      ]
    }
  ]
}
```

Include only the hooks that were actually installed. For Python use `<python-cmd> "..."` (the detected command — `python3` or `python`), for Node.js use `node "..."`, for Bash-based hooks (Rust, Go, C#) use `bash "..."`. Monorepos: install all applicable hooks (each filters by file extension internally).

## Step 6: Create Documentation Files

**Always create in `.claude/docs/`:**
- `coding-guidelines.md` - Use template from `.claude/skills/claude-code-bootstrap/templates/docs/coding-guidelines.md` (replace [PROJECT NAME]). Shared across the entire repo.

**Create based on these detection rules:**

| File | Create when ANY of these are true |
|------|-----------------------------------|
| `testing.md` | Manifest lists a test dependency (jest, vitest, mocha, karma, pytest, unittest, rspec, etc.) OR a `test`/`test:*` script exists in manifest OR a `tests/`, `test/`, `spec/`, `__tests__/` directory exists |
| `styling.md` | Manifest lists a UI framework (react, vue, angular, svelte, solid) OR lists CSS tooling (tailwindcss, styled-components, sass, less, postcss) OR `.css`/`.scss`/`.less` files exist in `src/` |
| `architecture.md` | Project has 3+ top-level source directories (excluding config, tests, docs, build output) OR uses recognized pattern directories (controllers/, services/, repositories/, handlers/, models/) |

**Placement rules:**
- **Single project:** All files go in `.claude/docs/`.
- **Monorepo:** `testing.md`, `styling.md`, and `architecture.md` go in each subproject's `docs/` folder, scoped to that subproject's stack. Apply the detection rules above **per subproject** (e.g., skip `styling.md` for a subproject with no UI deps). For root-as-project, its scoped docs go in `.claude/docs/` alongside the shared `coding-guidelines.md`. Each subproject can also get its own `coding-guidelines.md` only if its conventions differ significantly from root.

## Step 7: Verify and Report

Run through this checklist. **Fix any failures before reporting to the user.**

**File existence** — verify every expected file was created. List all files in `.claude/` matching `*.md`, `*.json`, or `hooks/*`, and for monorepos also check each subproject path from Step 1 for `CLAUDE.md` and `docs/*.md`.

**Content checks** — verify each file has real content, not placeholders:
- `.claude/CLAUDE.md`: Actual project name, real commands, Documentation section. Line count <= 60.
- `.claude/settings.json`: `allow` list matches detected tech stacks only (no unrelated commands). If file had custom sections (hooks, etc.), verify they're preserved.
- `.claude/docs/coding-guidelines.md`: `[PROJECT NAME]` replaced with actual name.
- Each `testing.md`, `styling.md`, `architecture.md`: References the project's actual frameworks, tooling, and directory names.
- Monorepo: each subproject's `CLAUDE.md` exists, mentions subproject name, and is <= 60 lines.
- `.claude/hooks/*`: Each hook matches its template; settings.json `hooks.PostToolUse` references every installed hook file and vice versa.

**Cross-reference checks:**
- Every doc listed in a CLAUDE.md Documentation section actually exists as a file.
- Monorepo: every subproject in root CLAUDE.md's Architecture table has a corresponding `CLAUDE.md` file.

**If any check fails:** Fix the issue, then re-verify. Do not proceed to the summary until all checks pass.

**Summary:** Report to the user: files created, detected tech stack, and decisions made (monorepo detection rationale, which optional docs were created and why, which were skipped and why).
