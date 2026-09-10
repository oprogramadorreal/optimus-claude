# Project Structure Detection Logic

Detection algorithm for identifying monorepo and multi-repo workspace structures.

## Step 0 — Multi-repo workspace check (runs before Steps A/B/C)

If `git rev-parse --is-inside-work-tree` returns `true`, resolve `git rev-parse --show-toplevel` and run Step A at that root — normal checkouts and linked worktrees both take this common path.

Otherwise apply the **Multi-Repo Workspace Detection** algorithm from `multi-repo-detection.md`, which your prompt's reference list points you at for exactly this case. On a confirmed workspace, run Steps A/B/C inside each enumerated repo to classify it as single project or monorepo. (Canonical source: `multi-repo-detection.md`, shared with every other skill that needs it — there is no second copy to keep in sync.)

**Manifest validity (applies to all steps):** A lock file without its corresponding manifest (e.g., `package-lock.json` without `package.json`) does not count as a valid manifest.

## Step A — Check for Workspace Config Files (confirms monorepo alone)

- npm/yarn/pnpm workspaces: `workspaces` in root `package.json`, or `pnpm-workspace.yaml`
- Lerna (`lerna.json`), Nx (`nx.json`), Turborepo (`turbo.json`), Rush (`rush.json`)
- Cargo workspace: `[workspace]` in root `Cargo.toml`; Go workspace: `go.work`
- Melos: `melos.yaml` at root (Dart/Flutter monorepo management tool)
- Dart pub workspaces: root `pubspec.yaml` containing a `workspace:` field (Dart 3.6+ / Flutter 3.27+)
- Gradle: `settings.gradle(.kts)` with `include`; Maven: `pom.xml` with `<modules>`
- Bazel: `WORKSPACE` or `WORKSPACE.bazel`

## Step B — Scan for Independent Manifests (confirms monorepo if 2+ projects found)

Scan top-level directories for manifest files (manifest table in `tech-stack-detection.md`). Skip:
- **Dot-directories**: `.git`, `.github`, `.vscode`, etc.
- **Dependencies**: `node_modules`, `vendor`, `.venv`, `venv`, `env`
- **Build output**: `dist`, `build`, `out`, `target`, `bin`, `obj`
- **Framework/cache**: `.next`, `.nuxt`, `__pycache__`, `.cache`, `.tox`
- **Non-project**: `examples`, `demos`, `test-fixtures`, `e2e`, `__tests__`, `.storybook`, `samples`, `experiments`, `scripts`, `tools`, `docs`
- **Git submodules**: skip a directory when `git -C "<directory>" rev-parse --show-superproject-working-tree` identifies its superproject, or the parent's `.gitmodules` registers it. Do not exclude linked worktrees merely because their `.git` is a file.

**Depth-2 check for container directories:** For any scanned top-level directory that has no manifest and is not in the skip list, check its immediate subdirectories for manifest files (same skip rules). This catches nested subprojects inside container directories (e.g., `app/API/` and `app/client/` inside `app/`). Count each qualifying subdirectory as a separate project using its full relative path.

**Root-as-project check** (only when the total number of qualifying projects found in Step B — including depth-2 results — equals exactly 1):
The root itself may be an independent project. Count it as an additional project if the root has a manifest file AND at least one of:
- A **framework-specific config** at root (`angular.json`, `next.config.*`, `nuxt.config.*`, `vue.config.*`, `svelte.config.*`, `astro.config.*`, `webpack.config.*`, `vite.config.*`, `tsconfig.app.json`)
- A **root source directory** (`src/`, `app/`, or `lib/`) containing source files, where the subdirectory project also has its own source files — indicating two separate codebases
- A **different test framework** at root vs the subdirectory (e.g., root has `karma.conf.js` while subdirectory has `jest.config.js`)

**.NET solution consolidation** (post-scan refinement — runs before decision matrix):
If a single `.sln` file exists at the root, parse its `Project(...)` entries to get referenced `.csproj` paths. If every `.csproj` found by Step B is referenced by that `.sln`, collapse all those directories into one project for the decision matrix count. Non-`.csproj` manifests (e.g., `package.json` in a frontend directory) still count separately — so a repo with one `.sln` plus a `frontend/package.json` yields 2 projects and still qualifies as a monorepo. Skip consolidation when: no `.sln` exists, multiple `.sln` files exist at root, or any `.csproj` is not referenced by the `.sln`.

## Step C — Check Supporting Signals (cannot confirm alone)

- `README.md` describes multi-component architecture ("frontend and backend", "client and server", "API server", "microservices", etc.)
- `docker-compose.yml` / `compose.yml` defines multiple services with `build:` contexts pointing to different subdirectories
- Root manifest scripts use `concurrently`, `npm-run-all`, or `run-p`/`run-s` to launch multiple processes
- Proxy configuration exists (`proxy.conf.json`, `proxy.conf.js`, `setupProxy.js`) indicating a frontend proxying to a local backend

## Decision Matrix

- Multi-repo workspace (Step 0) → confirmed multi-repo, enumerate repos
- Workspace config found (Step A) → confirmed monorepo, enumerate from config
- 2+ projects with manifests (Step B) → confirmed monorepo, enumerate from projects
- Supporting signals (Step C) + 1 dir with manifest → likely monorepo, ask user to confirm
- Supporting signals only → insufficient evidence, ask user to identify subproject dirs
- No signals → single project

## Subproject Enumeration

**If monorepo detected:** Inform user of detection signals and identified subprojects with tech stacks. Confirm before proceeding.

- Step A detected: use workspace member list + any additional top-level dirs with manifests not in the config.
- Step B only: use all qualifying directories (including nested ones found via depth-2 check). If the root-as-project check qualified the root, include it too.
- Root-as-project or root-as-workspace-member (e.g., `"."` in workspaces): include in subproject table but do NOT create a separate CLAUDE.md — root CLAUDE.md covers it. Its docs go in `.claude/docs/`.
- For each subproject, detect its tech stack using the manifest table.
