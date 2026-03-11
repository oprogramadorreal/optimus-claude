# Mock Project Scaffolds

Minimal consumer project templates used by the Mock Project Agent (Step 5) to verify libraries, plugins, APIs, and reusable components from the outside-in. Mock projects exercise the public API surface to confirm it works as documented.

## When to Create a Mock Project

Create a mock project when the feature being verified is **consumed by external code**. Detection heuristics:

1. The diff modifies files under `lib/`, `packages/`, `src/lib/`, or similar library paths
2. The project's manifest has publishable fields (`main`, `exports`, `bin`, `types` in package.json; `[lib]` in Cargo.toml; etc.)
3. The diff changes public API surface — exported functions, REST endpoints, CLI commands, gRPC services
4. The diff adds or changes a plugin interface, middleware, or hook system
5. Commit messages mention "API", "SDK", "client", "endpoint", "contract", "plugin"

If none of these apply, skip mock project creation — use verification tests within the existing project instead.

## Scaffold Directory

Mock projects are created inside the sandbox worktree at `_mock/`:
```
.worktrees/verify-<branch-slug>/_mock/
```

This directory is automatically cleaned up when the sandbox is removed.

## Per-Stack Scaffolds

### Node.js / TypeScript

```bash
mkdir _mock && cd _mock
npm init -y
npm install ../ --install-links
```

Create `index.js` (or `index.ts` if the parent project uses TypeScript) importing and exercising the changed public APIs.

If TypeScript: copy or reference the parent's `tsconfig.json` base and add `ts-node` or `tsx` for execution.

### Python

```bash
mkdir _mock && cd _mock
python -m venv .venv
source .venv/bin/activate  # or .venv/Scripts/activate on Windows
pip install -e ../
```

Create `main.py` importing and exercising the changed public APIs.

### Rust

```bash
cargo new _mock
```

Add path dependency to `_mock/Cargo.toml`:
```toml
[dependencies]
<package-name> = { path = ".." }
```

Create `_mock/src/main.rs` using the changed public APIs.

### Go

```bash
mkdir _mock && cd _mock
go mod init mock
go mod edit -replace <module-path>=../
go mod tidy
```

Create `_mock/main.go` importing and exercising the changed public APIs.

### C# / .NET

```bash
dotnet new console -o _mock
dotnet add _mock reference ../src/<project>.csproj
```

Create `_mock/Program.cs` using the changed public APIs.

### Java (Maven)

```bash
mkdir -p _mock/src/main/java
```

Create `_mock/pom.xml` with a `<dependency>` pointing to the parent project's coordinates and `<systemPath>` for local JAR, or use a multi-module parent POM approach.

Create `_mock/src/main/java/Main.java` exercising the changed public APIs.

### Java (Gradle)

Create `_mock/build.gradle` with:
```groovy
dependencies {
    implementation files('../build/libs/<project>.jar')
}
```

Or use `includeBuild('..')` for composite builds.

### C / C++ (CMake)

```bash
mkdir _mock && cd _mock
```

Create `_mock/CMakeLists.txt`:
```cmake
cmake_minimum_required(VERSION 3.10)
project(mock_consumer)
add_subdirectory(.. parent_lib)
add_executable(mock_consumer main.c)
target_link_libraries(mock_consumer <library-target>)
```

Create `_mock/main.c` (or `main.cpp`) exercising the changed public APIs.

### Dart / Flutter

**For Dart packages:**

```bash
dart create -t console _mock
```

Add path dependency to `_mock/pubspec.yaml`:
```yaml
dependencies:
  <package-name>:
    path: ../
```

Create `_mock/bin/_mock.dart` importing and exercising the changed public APIs.

**For Flutter packages/plugins:**

```bash
flutter create --template=app _mock
```

Add path dependency to `_mock/pubspec.yaml` under `dependencies:` and create a test or main file exercising the widget/plugin APIs.

### Other Stacks

If the project's stack doesn't match any scaffold above, search the web for how to create a minimal consumer project for the detected language and package manager. Proposed commands must invoke a single well-known CLI tool with simple arguments (no shell operators, pipes, redirects, variable expansion, subshells, chained commands, or interpreter invocations; bare command name with no path separators; single line of printable ASCII). Present exact commands to the user for approval before executing. Follow the same principles as other stacks (see Mock Project Principles below). Specifically:
1. Create `_mock/` directory
2. Initialize a minimal project using the stack's standard tooling
3. Add a local/path dependency pointing to `../`
4. Create a main/entry file exercising the changed public APIs

## Mock Project Principles

- **Minimal** — under 50 lines of consumer code per behavior being verified
- **Focused** — exercises only the changed public APIs, not the entire library
- **Disposable** — lives only inside the sandbox, never committed
- **Runnable** — must produce a clear pass/fail result (exit code 0 = pass, non-zero = fail)
- **Self-contained** — must build and run with only the sandbox worktree as context
