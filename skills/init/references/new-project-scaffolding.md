# New Project Scaffolding

Procedure for scaffolding a new project from scratch in an empty directory. Referenced from Step 1 of the init skill when an empty or near-empty directory is detected.

## Scope Guard

This procedure creates a **minimal hello-world project** — the absolute baseline for the chosen stack. The project description provided by the user is used ONLY for naming and the README description line. Do NOT implement features, business logic, or architecture based on the project description. The result must be a buildable, runnable, minimal project with zero custom code beyond what the official scaffolding tool generates.

## Section 1: Gather Project Intent

Use `AskUserQuestion` — header "New Project", question "What would you like to build?" with options:
- **Web app** — "Frontend or full-stack web application"
- **Backend / API** — "Server, REST API, or microservice"
- **CLI tool** — "Command-line application"
- **Other** — "Library, mobile app, or something else"

Based on the answer, ask a follow-up `AskUserQuestion` — header "Tech Stack", question "Which stack would you like to use?" with options appropriate to the category (see Scaffold Commands Table below for the full list of built-in options). Always include an "Other" option for unlisted stacks.

Then ask for the **project name** if not already clear from context. Validate it before use: it must match `^[a-zA-Z][a-zA-Z0-9._-]*$` (1–100 chars, no spaces or shell metacharacters). If invalid, ask again with guidance on valid naming for the chosen stack (lowercase with hyphens for Node.js; underscores for Python/Rust; PascalCase for .NET; etc.).

## Section 2: Scaffold Commands Table

Use the official scaffolding CLI for each stack. Do NOT manually generate boilerplate — official tools produce correct, up-to-date project structures with proper configs.

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
| Node.js / Express | `mkdir <name> && cd <name> && npm init -y` | After init: `npm install express` + create minimal `index.js` with hello-world route and `start` script in package.json |
| Python / FastAPI | `uv init <name>` | After init: `cd <name> && uv add fastapi` + create minimal `main.py` with hello-world endpoint. If uv not available: `mkdir <name> && cd <name> && python3 -m venv .venv && source .venv/bin/activate && pip install fastapi uvicorn` + create `main.py` |
| Rust / Axum | `cargo init <name>` | After init: add `axum` and `tokio` to `Cargo.toml` + replace `main.rs` with minimal hello-world server |
| Go | `mkdir <name> && cd <name> && go mod init <name>` | Create minimal `main.go` with hello-world HTTP server |
| C# / .NET Web API | `dotnet new webapi -o <name>` | Generates a complete hello-world API |
| Java / Spring Boot | `mkdir -p <name> && curl --fail -sSL https://start.spring.io/starter.tgz -d type=maven-project -d language=java -d name=<name> -d artifactId=<name> \| tar -xzf - -C <name>` | If curl/Spring Initializr unavailable, search web for current alternative |

### CLI tool stacks

| Language | Scaffold Command | Notes |
|----------|-----------------|-------|
| Node.js | `mkdir <name> && cd <name> && npm init -y` | Create `bin/<name>.js` with shebang + `bin` field in package.json |
| Python | `uv init <name>` | Create `<name>/__main__.py` with hello-world print. If uv not available: manual venv setup |
| Rust | `cargo init <name>` | Generates a complete hello-world CLI |
| Go | `mkdir <name> && cd <name> && go mod init <name>` | Create `main.go` with hello-world print |

### Other stacks

| Type | Scaffold Command | Notes |
|------|-----------------|-------|
| Flutter (mobile) | `flutter create <name>` | Generates a complete hello-world app |
| React Native | `npx @react-native-community/cli init <name>` | |
| Dart (package) | `dart create -t package <name>` | |
| Node.js (library) | `mkdir <name> && cd <name> && npm init -y` | Create `src/index.ts` with placeholder export |
| Python (library) | `uv init --lib <name>` | If uv not available: manual setup |
| Rust (library) | `cargo init --lib <name>` | |
| C/C++ (CMake) | `mkdir -p <name>/src && cd <name>` | Create `CMakeLists.txt` + `src/main.cpp` with hello-world |

### CLI not installed

If the required CLI tool (e.g., `cargo`, `flutter`, `dotnet`, `uv`) is not installed, inform the user and use `AskUserQuestion` — header "Missing Tool", question "[tool] is not installed. How would you like to proceed?":
- **Install it** — provide the standard installation command for the platform and proceed after installation
- **Manual setup** — create a minimal project manually: manifest file, entry point with hello-world code, and `.gitignore`

### Unsupported stacks

If the user selects "Other" and specifies a stack not in the tables above: return an **unsupported-stack signal** to the caller (SKILL.md) with the user's chosen stack name, so the caller can apply the unsupported-stack fallback procedure directly.

## Section 3: Post-Scaffold

### .gitignore

Most official scaffold tools generate a `.gitignore`. After scaffolding:
1. If `.gitignore` was generated by the scaffold tool — verify it covers the stack's build artifacts and dependencies. If adequate, keep as-is.
2. If no `.gitignore` exists — create one with standard entries for the detected stack (e.g., `node_modules/`, `dist/`, `.env` for Node.js; `__pycache__/`, `.venv/`, `*.pyc` for Python; `target/` for Rust; `bin/`, `obj/` for .NET; etc.). Use web search for the stack's standard `.gitignore` patterns if needed.
3. If `.gitignore` existed before scaffolding (pre-existing repo) — append any missing stack-specific entries without overwriting existing content.

### README

The project must have a `README.md` that tells a human developer how to build and run it.

1. If the scaffold tool generated a README with adequate build/run instructions (e.g., `create-next-app`, `create-react-app`) — keep it. Update the project name and description line to match the user's input if the scaffold README is generic.
2. If the scaffold tool generated a README without run instructions, or no README exists — create or update a minimal README:
   - `# <project-name>`
   - One-line description from the user's project description
   - `## Development` section with commands for: install dependencies, run in dev mode, build for production, and run tests — using the correct package manager prefix (per `tech-stack-detection.md` rules). Only include commands that are actually available in the scaffolded project.

### Verify project works

Run the build or dev command to confirm the scaffolded project compiles/starts successfully. If it fails, diagnose and fix before proceeding. The project must be in a buildable, runnable state. For dev servers, start the command, verify it begins serving (check for the expected output like "listening on port" or "ready"), then stop it.

### Git init

1. If `.git/` does not exist, run `git init`.

After git init, print: **"Scaffolding complete. Files are ready — use `/optimus:commit` when you want to make your first commit. Resuming project detection..."** and return control to init Step 1 at the "Project detection" subsection to re-detect the now-populated project from scratch.
