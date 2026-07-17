# Formatter Hook Setup

Instructions for installing auto-format hooks per tech stack. Referenced from Step 5 of the init skill.

## Hook Templates

All templates are in `$CLAUDE_PLUGIN_ROOT/skills/init/templates/hooks/`.

| Stack | Template | Formatter | Install when |
|-------|----------|-----------|--------------|
| Python | `format-python.py` | black + isort | In project deps (requirements*.txt, pyproject.toml, Pipfile), or user approves |
| Node.js | `format-node.js` | prettier | In package.json devDependencies, or user approves |
| Rust | `format-rust.sh` | rustfmt | Always (built-in) |
| Go | `format-go.sh` | gofmt | Always (built-in) |
| C#/.NET | `format-csharp.sh` | csharpier | `csharpier` entry exists in `.config/dotnet-tools.json` (do NOT check `dotnet csharpier --version` or PATH — a global-only install is not sufficient), or user approves |
| Java | `format-java.sh` | google-java-format | On PATH, or user approves (JAR from github.com/google/google-java-format releases, placed on PATH) |
| C/C++ | `format-cpp.sh` | clang-format | On PATH, or user approves (bundled with LLVM/Clang; available via system package manager) |
| Dart/Flutter | `format-dart.sh` | dart format | Always (built-in with the Dart/Flutter SDK) |
| (other) | — | Search web for "[language] most popular formatter" | On PATH, or user approves installation |

**Unsupported stacks:** Apply the fallback procedure from `unsupported-stack-fallback.md` (loaded by the parent skill) to find the standard formatter via web search. If none is found, inform the user: **"Could not determine a formatter for [detected stack] — skipping formatter hook."** Do not create a hook. If the user approves the proposed formatter, create a custom shell hook (`.claude/hooks/format-<language>.sh`) following the full pattern of the existing shell hooks (`format-rust.sh`, `format-go.sh`): shebang, JSON stdin parsing into `$file_path`, file-extension guard for the language's source extensions, then formatter invocation with `"$file_path"`.

> **No import organizers:** Tools that remove unused imports (e.g., `prettier-plugin-organize-imports`, `goimports`) are intentionally excluded from PostToolUse hooks. They remove imports that appear unused mid-edit, causing a destructive loop when Claude adds an import before writing the code that uses it.

## Python Command Detection

Only when the Python hook will be installed: run `python3 --version`; if it fails, run `python --version` and verify Python 3.x. Use whichever succeeds as `<python-cmd>`. If neither works, skip the Python hook and inform the user.

## Installation Steps

1. Copy the applicable template(s) to `.claude/hooks/` (custom hooks per the unsupported-stacks rule above).
2. External formatters not in deps → ask the user "Add [formatter] as dev dependency and install format hook?" If declined, skip that stack's hook entirely. If approved, install with the detected package manager's standard dev-dependency command. Non-obvious flows:
   - **C#/.NET (csharpier):** install as a local tool so all developers get it via `dotnet tool restore` — if `.config/dotnet-tools.json` is missing run `dotnet new tool-manifest`, then `dotnet tool install csharpier`, then `dotnet tool restore`. "In deps" always means the tool-manifest entry, never PATH.
   - **Unsupported stacks:** use the installation command identified via web search — present the exact command for user approval before executing.
3. If any hooks were installed, create or update `.claude/settings.json` using `$CLAUDE_PLUGIN_ROOT/skills/init/templates/settings.json` as reference, keeping only entries for hooks actually installed. Python: replace `<python-cmd>` with the detected command. Node.js hooks run via `node "..."`; all shell hooks (Rust, Go, C#, Java, C/C++, Dart/Flutter, custom) via `bash "..."`. Monorepos: install all applicable hooks — each self-filters by file extension. settings.json follows the merge semantics in the skill's File semantics block (merge, never overwrite; don't create it when no hooks were installed unless it already exists).
