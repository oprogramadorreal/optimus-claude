# Tech Stack Detection

Shared detection tables for identifying project type and package manager from manifest files. Referenced by init (Step 1) and how-to-run (Step 1).

## Manifest → Project Type

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
| pubspec.yaml | Dart/Flutter | pub |
| (other manifest file) | Detect language from file contents | Search web for "[language] package manager" |

If a manifest file is found that doesn't match any row above, first detect the programming language by reading the manifest and nearby source files, then read and apply `$CLAUDE_PLUGIN_ROOT/skills/init/references/unsupported-stack-fallback.md` with the detected language.

### .NET note

`.sln` files reference `.csproj` projects — they confirm .NET presence but aren't independent project manifests. Don't count a root `.sln` for root-as-project detection. When a single root `.sln` references all `.csproj` files found during detection, treat the entire solution as one project (see .NET solution consolidation in `$CLAUDE_PLUGIN_ROOT/skills/init/references/project-detection.md`). List all solution projects and their roles in documentation.

### Dart/Flutter note

For Dart/Flutter projects, when `build_runner` is in `dev_dependencies`, document both `build_runner build` and `build_runner watch` commands and note that generated files (`.g.dart`, `.freezed.dart`) must not be edited manually.

## Package Manager Detection

Determines command prefixes for all generated commands.

| Type | Check (in priority order) | Result |
|------|---------------------------|--------|
| Node.js | `pnpm-lock.yaml` exists | pnpm |
| Node.js | `yarn.lock` exists | yarn |
| Node.js | `bun.lockb` or `bun.lock` exists | bun |
| Node.js | default / `package-lock.json` | npm |
| Python | `uv.lock` exists OR `[tool.uv]` in pyproject.toml | uv (prefix commands with `uv run`) |
| Python | `poetry.lock` exists OR `[tool.poetry]` in pyproject.toml | poetry (prefix with `poetry run`) |
| Python | default | pip (bare commands: `pytest`, `ruff`, etc.) |
| Dart/Flutter | `pubspec.yaml` has Flutter SDK dependency (`dependencies.flutter.sdk: flutter`) | flutter (prefix commands with `flutter`) |
| Dart/Flutter | `pubspec.yaml` without Flutter SDK dependency (pure Dart package) | dart (prefix commands with `dart`) |

If a lock file doesn't match any row above and the package manager was not already determined by manifest detection, read and apply `$CLAUDE_PLUGIN_ROOT/skills/init/references/unsupported-stack-fallback.md` to identify the package manager via web search.

## Runtime Version Constraint Fields

These manifest fields specify runtime version constraints — used by how-to-run for Prerequisites sections:

| Manifest | Field | Example |
|----------|-------|---------|
| package.json | `engines.node` | `">=18"` |
| pyproject.toml | `project.requires-python` / `python_requires` | `">=3.11"` |
| Cargo.toml | `rust-version` | `"1.75"` |
| pubspec.yaml | `environment.sdk` | `">=3.0.0 <4.0.0"` |

## Command Prefix Rules

Use the detected package manager for all generated commands. Examples:
- Node.js with pnpm → `pnpm run build` not `npm run build`
- Python with uv → `uv run pytest` not just `pytest`
- Dart with Flutter → `flutter pub get` not `dart pub get`, `flutter test` not `dart test`
