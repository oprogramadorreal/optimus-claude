# New Project Scaffolding

Procedure for scaffolding a new project from scratch in an empty directory. Referenced from init's detection step.

## Scope guard

This procedure creates a **minimal hello-world project** — the absolute baseline for the chosen stack. The user's project description is used only for naming and the README description line. Do NOT implement features, business logic, or architecture from the description. The result must be a buildable, runnable, minimal project with zero custom code beyond what the official scaffolding tool generates.

## Gather intent

Ask what the user wants to build (web app, backend/API, CLI tool, or something else), which stack, and the project name. Validate the name before use: it must match `^[a-zA-Z][a-zA-Z0-9._-]{0,99}$` (no spaces or shell metacharacters); if invalid, ask again with the chosen stack's naming convention (lowercase-hyphens for Node.js, underscores for Python/Rust, PascalCase for .NET).

## Scaffold commands

Use the official scaffolding CLI for each stack — do NOT hand-generate boilerplate; official tools produce correct, current project structures.

### Web app stacks

| Framework | Scaffold Command | Notes |
|-----------|-----------------|-------|
| React (Vite) | `npm create vite@latest <name> -- --template react-ts` | Adjust PM prefix per detection: `pnpm create`, `yarn create`, `bun create` |
| Next.js | `npx create-next-app@latest <name> --ts --app` | Uses App Router by default |
| Vue (Vite) | `npm create vite@latest <name> -- --template vue-ts` | Adjust PM prefix |
| Nuxt | `npx nuxi@latest init <name>` | |
| Svelte (SvelteKit) | `npx sv create <name>` | |
| Angular | `npx @angular/cli@latest new <name>` | |
| Flutter (web) | `flutter create --platforms web <name>` | |

### Backend / API stacks

| Framework | Scaffold Command | Notes |
|-----------|-----------------|-------|
| Node.js / Express | `mkdir <name> && cd <name> && npm init -y` | Then `npm install express` + minimal `index.js` with hello-world route and `start` script |
| Python / FastAPI | `uv init <name>` | Then `cd <name> && uv add fastapi` + minimal `main.py` with hello-world endpoint. Without uv: `mkdir <name> && cd <name> && python3 -m venv .venv`, install `fastapi uvicorn` with the venv's pip |
| Rust / Axum | `cargo init <name>` | Add `axum` and `tokio` to `Cargo.toml` + minimal hello-world server in `main.rs` |
| Go | `mkdir <name> && cd <name> && go mod init <name>` | Minimal `main.go` HTTP server. Bare module path as starter — ask if the user prefers a URL-like path; validate custom paths against `^[a-zA-Z0-9][a-zA-Z0-9._/-]*$` |
| C# / .NET Web API | `dotnet new webapi -o <name>` | Complete hello-world API |
| Java / Spring Boot | `mkdir -p <name> && curl --fail -sSL https://start.spring.io/starter.tgz -d type=maven-project -d language=java -d name=<name> -d artifactId=<name> -d baseDir= \| tar -xzf - -C <name>` | If curl/Spring Initializr unavailable, search the web for a current alternative |

### CLI tool stacks

| Language | Scaffold Command | Notes |
|----------|-----------------|-------|
| Node.js | `mkdir <name> && cd <name> && npm init -y` | Create `bin/<name>.js` with shebang + `bin` field in package.json |
| Python | `uv init <name>` | Create `<name>/__main__.py` with hello-world print. Without uv: manual venv setup |
| Rust | `cargo init <name>` | Complete hello-world CLI |
| Go | `mkdir <name> && cd <name> && go mod init <name>` | Minimal `main.go`; same module-path rule as above |

### Other stacks

| Type | Scaffold Command | Notes |
|------|-----------------|-------|
| Flutter (mobile) | `flutter create <name>` | Complete hello-world app |
| React Native | `npx react-native@latest init <name>` | |
| Dart (package) | `dart create -t package <name>` | |
| Node.js (library) | `mkdir <name> && cd <name> && npm init -y` | Create `src/index.ts` with placeholder export |
| Python (library) | `uv init --lib <name>` | Without uv: manual setup |
| Rust (library) | `cargo init --lib <name>` | |
| C/C++ (CMake) | `mkdir -p <name>/src && cd <name>` | Create `CMakeLists.txt` + `src/main.cpp` hello-world |

**Required CLI not installed** (cargo, flutter, dotnet, uv, ...): ask the user whether to install it (provide the standard install command for their platform) or fall back to manual setup — a minimal manifest, hello-world entry point, and `.gitignore`.

**Unsupported stack:** if the user's chosen stack isn't in the tables above, return an unsupported-stack signal to the caller with the stack name — init applies the shared fallback procedure.

## Post-scaffold

Scaffold commands create a `<name>/` subdirectory — `cd` into it so subsequent operations and init's re-detection run from the project root (skip when files landed directly in the CWD, e.g. manual setup).

1. **.gitignore** — if the scaffold tool generated one covering the stack's build artifacts and dependencies, keep it. Otherwise create one with the stack's standard entries (web-search if unsure). If one pre-existed, append missing entries without overwriting.
2. **README** — the project must have a README that tells a developer how to build and run it. Keep a scaffold-generated README with adequate instructions (updating name/description to match the user's input); otherwise create a minimal one: title, one-line description, and a Development section with install/dev/build/test commands that actually exist in the scaffolded project.
3. **Verify it works** — run the build or dev command and confirm success; diagnose and fix failures before proceeding. For dev servers, start with a 30-second timeout, confirm the ready signal (e.g., "listening on port"), then stop the process; if no signal appears, stop it and report.
4. **Git init** — run `git init` if `.git/` does not exist.

Then return control to init's detection step to re-detect the now-populated project from scratch.
