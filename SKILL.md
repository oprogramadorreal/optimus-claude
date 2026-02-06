---
name: bootstrap
description: Bootstrap effective documentation following LLM-optimized practices
disable-model-invocation: true
---

# Bootstrap Project Documentation

Create optimized CLAUDE.md and supporting docs using research-backed practices. Unlike `/init`, this generates structured documentation following the WHAT/WHY/HOW framework with progressive disclosure. Supports both single projects and monorepos.

## Before You Start

Read `.claude/skills/claude-code-bootstrap/references/claude-md-best-practices.md` and apply throughout:
- Keep every CLAUDE.md under 60 lines
- Use file:line references, not code snippets
- Only include universally-applicable instructions

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

**Extract**: Project name, tech stack, build system, available scripts.

**Analyze structure** (stay shallow):
- README.md for project purpose and features
- Top-level directories for architecture pattern
- Entry points (main.ts, index.ts, app.module.ts, etc.)

**Check for monorepo indicators:**

**Step A — Check for workspace config files** (confirms monorepo alone):

| Tool | Detection |
|------|-----------|
| npm/yarn/pnpm workspaces | `workspaces` field in root `package.json`, or `pnpm-workspace.yaml` |
| Lerna | `lerna.json` |
| Nx | `nx.json` |
| Turborepo | `turbo.json` |
| Rush | `rush.json` |
| Cargo workspace | `[workspace]` section in root `Cargo.toml` |
| Go workspace | `go.work` file |
| Gradle multi-project | `settings.gradle(.kts)` with `include` statements |
| Maven multi-module | `pom.xml` with `<modules>` section |
| Bazel | `WORKSPACE` or `WORKSPACE.bazel` file |

**Step B — Scan for independent manifests** (confirms monorepo if 2+ dirs found):

Scan top-level directories for manifest files (from the manifest table above). Skip:
- **Dot-directories**: `.git`, `.github`, `.vscode`, etc.
- **Dependencies**: `node_modules`, `vendor`, `.venv`, `venv`, `env`
- **Build output**: `dist`, `build`, `out`, `target`, `bin`, `obj`
- **Framework/cache**: `.next`, `.nuxt`, `__pycache__`, `.cache`, `.tox`
- **Non-project**: `examples`, `demos`, `test-fixtures`, `e2e`, `__tests__`, `.storybook`

**Step C — Check supporting signals** (cannot confirm alone):

- `README.md` describes multi-component architecture ("frontend and backend", "client and server", "microservices", etc.)
- `docker-compose.yml` / `compose.yml` defines multiple services with `build:` contexts pointing to different subdirectories

**Decision:**
- Workspace config found (Step A) → confirmed monorepo, enumerate from config
- 2+ dirs with manifests (Step B) → confirmed monorepo, enumerate from dirs
- Supporting signals (Step C) + 1 dir with manifest → likely monorepo, ask user to confirm
- Supporting signals only → insufficient evidence, ask user to identify subproject dirs
- No signals → single project

**If monorepo detected:** Inform user of detection signals and identified subprojects with tech stacks. Confirm before proceeding.

**Enumerate subprojects:**
- From workspace config (Step A): use its member list, plus any additional top-level dirs with manifests not covered by the config (mixed-tech monorepos).
- From manifest scan only (Step B): use all qualifying top-level dirs.
- If the root is listed as a workspace member (e.g., `"."` in workspaces, or root `[package]` in Cargo workspace), include it in the subproject table but do not create a separate CLAUDE.md for it — the root CLAUDE.md serves both roles. Otherwise, root manifest provides project-level context only.
- For each subproject, detect its individual tech stack using the manifest table above.

**Record** the workspace tool (if any) and the list of subproject paths for use in subsequent steps.

## Step 2: Create Directory Structure

```bash
mkdir -p .claude/docs
# If monorepo: also mkdir -p <subproject>/docs for each subproject that will receive docs (determined in Step 5)
```

## Step 3: Create CLAUDE.md

### Single project

Create `.claude/CLAUDE.md` with living document header:

```markdown
<!-- Keep this file and .claude/docs/ updated when project structure, conventions, or tooling changes -->

# Project Name
```

**Structure content using WHAT/WHY/HOW:**

| Section | Content |
|---------|---------|
| **WHAT** | Project name, purpose (1 line), tech stack summary |
| **WHY** | Essential commands: build, test, lint (from project manifest) |
| **HOW** | Documentation references with task-oriented descriptions |

**Documentation section format:**
```markdown
## Documentation
Read the relevant doc before making changes:
- `coding-guidelines.md` - For new features, refactoring, code structure
- `testing.md` - For writing or modifying tests
- `styling.md` - For UI components, CSS, visual changes
- `architecture.md` - For understanding project structure, data flow
```

Only list docs that were actually created. Keep total file under 60 lines.

### Monorepo

Use template from `.claude/skills/claude-code-bootstrap/templates/monorepo-claude.md` instead. Fill in:
- Subproject table with all detected subprojects (path, purpose, tech stack)
- Root-level / workspace-wide commands only (not subproject-specific commands)
- References to each subproject's CLAUDE.md
- If a workspace tool was detected (Step A), include "managed by [tool]" in the description line
- If no workspace tool was detected (Step B only), use "Monorepo with [N] packages" or "Multi-project repository with [N] components" without referencing a workspace tool

If more than 6 subprojects, group by category (apps, libs, services) in the root CLAUDE.md and move the full subproject table to `.claude/docs/architecture.md`. Keep descriptions concise (abbreviate stacks, e.g., "TS/React" not "TypeScript, React, Vite, Tailwind") to stay under 60 lines.

## Step 3b: Create Subproject CLAUDE.md Files (monorepo only)

For each detected subproject (except root-as-member — the root CLAUDE.md already covers it), create `<subproject>/CLAUDE.md` using template from `.claude/skills/claude-code-bootstrap/templates/subproject-claude.md`:
- Scope WHAT/WHY/HOW to that subproject's tech stack and purpose
- Include only commands specific to this subproject (run from its directory)
- Reference its local `docs/` folder for detailed documentation
- Mention parent monorepo name in the opening line
- Keep under 60 lines

## Step 4: Create settings.json

Use template from `.claude/skills/claude-code-bootstrap/templates/settings.json`. Customize allow list based on detected project type:

| Type | Commands to Allow |
|------|-------------------|
| Node.js | `npm run`, `npx`, `yarn`, `pnpm` |
| Rust | `cargo build`, `cargo test`, `cargo run`, `cargo clippy` |
| Python | `pytest`, `pip`, `poetry`, `uv`, `ruff`, `mypy` |
| C#/.NET | `dotnet build`, `dotnet test`, `dotnet run`, `dotnet restore` |
| Java/Maven | `mvn compile`, `mvn test`, `mvn package` |
| Java/Gradle | `gradle build`, `gradle test`, `gradlew` |
| Go | `go build`, `go test`, `go run`, `go vet`, `golangci-lint` |
| C/C++ | `cmake`, `make`, `ctest`, `ninja` |
| Ruby | `bundle`, `rake`, `rspec` |

**If monorepo:** Union the permission sets for all tech stacks detected across subprojects into a single root `.claude/settings.json`.

## Step 5: Create Documentation Files

**Always create in `.claude/docs/`:**
- `coding-guidelines.md` - Use template from `.claude/skills/claude-code-bootstrap/templates/docs/coding-guidelines.md` (replace [PROJECT NAME]). This is shared across the entire repo.

**Create if applicable:**

| File | Create When |
|------|-------------|
| `testing.md` | Test framework detected (Jest, Karma, pytest, cargo test, go test, etc.) |
| `styling.md` | Frontend project (Angular, React, Vue, or has CSS/SCSS files) |
| `architecture.md` | Project has meaningful structure worth documenting |

**Single project:** Place these files in `.claude/docs/`.

**Monorepo:** Place `testing.md`, `styling.md`, and `architecture.md` in each **subproject's** `docs/` folder, scoped to that subproject's tech stack. Each subproject can also have its own `coding-guidelines.md` if its conventions differ significantly from the shared root guidelines. Only create files applicable to each subproject (e.g., skip `styling.md` for backend-only subprojects).

## Step 6: Handle Existing Files

| Scenario | Action |
|----------|--------|
| Root `CLAUDE.md` exists | Read for context, create improved `.claude/CLAUDE.md`, suggest removing root file |
| `.claude/CLAUDE.md` exists (single project) | Read for context, update/improve as needed |
| `.claude/CLAUDE.md` exists (single-project style) in a monorepo | Read existing content for context and useful details to preserve. Replace with monorepo orchestrator version. Inform user the file was refactored for monorepo structure |
| `.claude/CLAUDE.md` exists (already monorepo style) | Read for context, update/improve as needed |
| `.claude/docs/` files exist (testing.md, styling.md, etc.) in a monorepo | Read for context. Move relevant content to each subproject's `docs/` folder, scoped appropriately. Remove the root copies that are now subproject-specific. Keep only `coding-guidelines.md` at root |
| No manifest detected | Create generic docs with placeholders, inform user manual customization is recommended |
| Subproject `CLAUDE.md` exists | Read for context, create improved version, inform user |

## Step 7: Verify

List all created files. If monorepo, include subproject files:
```bash
find .claude -type f \( -name "*.md" -o -name "*.json" \)
```

If monorepo, also list subproject documentation using the actual detected subproject paths from Step 1 (not hardcoded directory names):
```bash
# Replace with actual detected subproject paths, e.g.:
find api/ web/ shared/ -name "CLAUDE.md" -o -path "*/docs/*.md" 2>/dev/null
```
