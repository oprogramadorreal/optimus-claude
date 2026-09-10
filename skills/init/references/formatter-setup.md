# Formatter Hook Setup

Instructions for installing auto-format hooks per tech stack. Referenced from Step 5 of the init skill.

## Prefer the project's existing workflow

Inspect formatter configuration, package scripts, local tool manifests, editor settings,
and CI before choosing a hook. The templates below run the project's own formatter on the
edited file: a hook is not a competing formatter when the project already uses the same
tool, and existing editor, pre-commit, or CI formatting does not make it redundant — those
run at other moments. Reuse the project's pinned version, ignore rules, and configuration.

Do not add a *different* formatter beside one the project already uses (Black beside Ruff
format, Prettier beside Biome): wrap the existing tool instead, or, when its command cannot
safely target one file, document it for use at task boundaries. Adding a new formatter
dependency needs the user's approval — present the exact dependency/configuration changes
and affected file scope first. Never reformat the repository as part of setup. Preserve
unrecorded/custom hooks under init's ownership rules.

## Hook Templates

All templates are in `$CLAUDE_PLUGIN_ROOT/skills/init/templates/hooks/`.

| Stack | Template | Formatter | Install when |
|-------|----------|-----------|--------------|
| Python | `format-python.sh` | black + isort | In project deps (requirements*.txt, pyproject.toml, Pipfile), or user approves |
| Node.js | `format-node.cjs` | prettier | In package.json devDependencies, or user approves |
| Rust | `format-rust.sh` | rustfmt | Installed toolchain has rustfmt and nearest project rustfmt config declares its edition; otherwise retain Cargo workflow |
| Go | `format-go.sh` | gofmt | Always (built-in) |
| C#/.NET | `format-csharp.sh` | csharpier | `csharpier` entry exists in `.config/dotnet-tools.json` (do NOT check `dotnet csharpier --version` or PATH — a global-only install is not sufficient), or user approves |
| Java | `format-java.sh` | google-java-format | On PATH, or user approves (JAR from github.com/google/google-java-format releases, placed on PATH) |
| C/C++ | `format-cpp.sh` | clang-format | On PATH, or user approves (bundled with LLVM/Clang; available via system package manager) |
| Dart/Flutter | `format-dart.sh` | dart format | Always (built-in with the Dart/Flutter SDK) |
| (other) | — | Search web for "[language] most popular formatter" | On PATH, or user approves installation |

**Unsupported stacks:** Apply the fallback procedure from `unsupported-stack-fallback.md` (loaded by the parent skill) to find the standard formatter via web search. If none is found, inform the user: **"Could not determine a formatter for [detected stack] — skipping formatter hook."** Do not create a hook. If the user approves the proposed formatter, create a custom shell hook (`.claude/hooks/format-<language>.sh`) following the full pattern of the existing shell hooks (`format-rust.sh`, `format-go.sh`): shebang, JSON stdin parsing into `$file_path`, file-extension guard for the language's source extensions, then formatter invocation with `"$file_path"`.

> **No import organizers:** Tools that remove unused imports (e.g., `prettier-plugin-organize-imports`, `goimports`) are intentionally excluded from PostToolUse hooks. They remove imports that appear unused mid-edit, causing a destructive loop when Claude adds an import before writing the code that uses it.

## Installation Steps

1. Establish ownership and migration choices before copying applicable templates to `.claude/hooks/`.
   - **Legacy migration:** `format-python.py` (Optimus <= 3.5.0) is replaced by `format-python.sh`; `format-node.js` is replaced by `format-node.cjs` for ESM compatibility. Show the old file and exact `PostToolUse` entries. Remove an unchanged recorded legacy file/entry as part of the approved migration; modified/unrecorded versions need an explicit reviewed choice. Never delete solely by filename or leave both registrations active. If the old hook is kept, skip the competing new hook and report the incomplete migration.
2. External formatters not in deps → ask the user "Add [formatter] as dev dependency and install format hook?" If declined, skip that stack's hook entirely. If approved, install with the detected package manager's standard dev-dependency command. Non-obvious flows:
   - **C#/.NET (csharpier):** install as a local tool so all developers get it via `dotnet tool restore` — if `.config/dotnet-tools.json` is missing run `dotnet new tool-manifest`, then `dotnet tool install csharpier`, then `dotnet tool restore`. "In deps" always means the tool-manifest entry, never PATH.
     Preserve existing pinned versions. The hook resolves the local tool from the edited package and uses pre-1.0 syntax for 0.x or the `format` subcommand for 1.x and later; it does not upgrade tools.
   - **Unsupported stacks:** use the installation command identified via web search — present the exact command for user approval before executing.
3. **Confirm reachability before claiming hooks work.** Python resolves black/isort in `.venv`, `venv`, or `env` above the edited file, then PATH. For an external Poetry/pipenv/conda environment, prefer the existing project command at task boundaries; do not move its environment merely to fit this hook. Rust requires an explicit `edition` in the nearest `rustfmt.toml` or `.rustfmt.toml`, runs from the edited package to honor its toolchain, and retains that config's style options. Verify edition and `style_edition` against Cargo/the pinned toolchain during setup; mixed-edition workspaces need package-specific config or the existing `cargo fmt` command. Do not invent an edition or change configuration without approval. Rustfmt can follow out-of-line modules; retain the task-boundary workflow if that scope is inappropriate per edit. Missing/unsupported setup skips the hook with a useful command alternative.
4. If hooks were installed, merge `.claude/settings.json` using `$CLAUDE_PLUGIN_ROOT/skills/init/templates/settings.json`. Add a separate matcher group per new hook; preserve existing groups, permissions, and other sections. Node hooks run via `node "..."`; shell hooks via `bash "..."`. Keep new entries only for hooks actually installed, record only those additions, and do not create settings.json when no hooks were installed.
