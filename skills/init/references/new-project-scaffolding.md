# New Project Scaffolding

Procedure for scaffolding a new project from scratch in an empty directory. Referenced from Step 1 of the init skill.

## Scope Guard

This procedure creates a **minimal hello-world project** — the absolute baseline for the chosen stack. The user's project description is used ONLY for naming and the README description line. Do NOT implement features, business logic, or architecture based on it. The result must be a buildable, runnable, minimal project with zero custom code beyond what the official scaffolding tool generates.

## Gather Project Intent

Use `AskUserQuestion` — header "New Project", question "What would you like to build?": **Web app** (frontend or full-stack) / **Backend / API** / **CLI tool** / **Other** (library, mobile app, or something else). Follow up with header "Tech Stack", question "Which stack would you like to use?" — options from the matching table below, always including an "Other" option.

Ask for the **project name** if not clear from context. It must match `^[a-zA-Z][a-zA-Z0-9._-]{0,99}$` (no spaces or shell metacharacters). If invalid, ask again with guidance on valid naming for the chosen stack (lowercase-hyphens for Node.js; underscores for Python/Rust; PascalCase for .NET; etc.).

## Scaffold Commands

Use the official scaffolding CLI — do NOT hand-generate boilerplate the official tool produces. Adjust the package-manager prefix per detection (`pnpm create`, `yarn create`, `bun create`).

### Web app

| Framework | Scaffold Command |
|-----------|-----------------|
| React (Vite) | `npm create vite@latest <name> -- --template react-ts` |
| Next.js | `npx create-next-app@latest <name> --ts --app` |
| Vue (Vite) | `npm create vite@latest <name> -- --template vue-ts` |
| Nuxt | `npx nuxi@latest init <name>` |
| Svelte (SvelteKit) | `npx sv create <name>` |
| Angular | `npx @angular/cli@latest new <name>` |
| Flutter (web) | `flutter create --platforms web <name>` |

### Backend / API

| Framework | Scaffold Command |
|-----------|-----------------|
| Node.js / Express | `mkdir <name> && cd <name> && npm init -y`, then `npm install express` + minimal `index.js` hello-world route + `start` script |
| Python / FastAPI | `uv init <name>`, then `cd <name> && uv add fastapi` + minimal `main.py` endpoint. No uv → manual venv (`python3 -m venv .venv`), `pip install fastapi uvicorn` |
| Rust / Axum | `cargo init <name>`, then add `axum` + `tokio` to `Cargo.toml` + minimal hello-world server in `main.rs` |
| Go | `mkdir <name> && cd <name> && go mod init <name>` + minimal `main.go` HTTP server. Bare-name module path is the starter — offer a URL-like path (e.g., `github.com/user/<name>`); validate custom paths against `^[a-zA-Z0-9][a-zA-Z0-9._/-]*$` before use |
| C# / .NET Web API | `dotnet new webapi -o <name>` |
| Java / Spring Boot | `mkdir -p <name> && curl --fail -sSL https://start.spring.io/starter.tgz -d type=maven-project -d language=java -d name=<name> -d artifactId=<name> -d baseDir= \| tar -xzf - -C <name>` (if unavailable, search web for the current alternative) |

### CLI tool

| Language | Scaffold Command |
|----------|-----------------|
| Node.js | `mkdir <name> && cd <name> && npm init -y` + `bin/<name>.js` with shebang + `bin` field |
| Python | `uv init <name>` + `<name>/__main__.py` hello-world (no uv → manual venv) |
| Rust | `cargo init <name>` |
| Go | `mkdir <name> && cd <name> && go mod init <name>` + hello-world `main.go` (same module-path rule as Backend) |

### Other

| Type | Scaffold Command |
|------|-----------------|
| Flutter (mobile) | `flutter create <name>` |
| React Native | `npx react-native@latest init <name>` |
| Dart (package) | `dart create -t package <name>` |
| Node.js (library) | `mkdir <name> && cd <name> && npm init -y` + `src/index.ts` placeholder export |
| Python (library) | `uv init --lib <name>` (no uv → manual setup) |
| Rust (library) | `cargo init --lib <name>` |
| C/C++ (CMake) | `mkdir -p <name>/src && cd <name>` + `CMakeLists.txt` + hello-world `src/main.cpp` |

**CLI not installed:** if the required tool (e.g., `cargo`, `flutter`, `dotnet`, `uv`) is missing, use `AskUserQuestion` — header "Missing Tool", question "[tool] is not installed. How would you like to proceed?": **Install it** (provide the standard install command for the platform, proceed after) / **Manual setup** (minimal manifest + hello-world entry point + `.gitignore`).

**Unsupported stacks:** if the user selects "Other" with a stack not in the tables, return an **unsupported-stack signal** to the caller (SKILL.md) with the chosen stack name — the caller applies the fallback procedure.

## Post-Scaffold

Scaffold commands create a `<name>/` subdirectory — `cd <name>` before these steps so everything (including init re-detection) runs from the project root. Skip the `cd` only if files landed directly in the CWD (rare — manual setup).

- **.gitignore:** verify the scaffold-generated one covers build artifacts and dependencies; create a standard one for the stack if missing; if one pre-existed, append missing stack entries without overwriting.
- **README.md:** must tell a developer how to build and run. Keep an adequate scaffold-generated README (updating name/description to the user's input); otherwise create a minimal one — title, one-line description, `## Development` section with install/dev/build/test commands that actually exist in the scaffolded project.
- **Verify the project works:** run the build or dev command and confirm success; diagnose and fix failures before proceeding. For dev servers: start with a 30-second timeout, verify a ready signal ("listening on port", "ready"), then stop it; no signal within the timeout → stop the process and report for diagnosis.
- **Git init:** run `git init` if `.git/` does not exist.

Then print **"Scaffolding complete. Resuming project detection..."** and return control to init Step 1's project detection to re-detect the now-populated project from scratch.
