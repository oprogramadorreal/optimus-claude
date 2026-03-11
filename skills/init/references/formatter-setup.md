# Formatter Hook Setup

Detailed instructions for installing auto-format hooks per tech stack. Referenced from Step 5 of the init skill.

## Hook Templates

All templates are in `$CLAUDE_PLUGIN_ROOT/skills/init/templates/hooks/`.

| Stack | Template | Formatter | Requires | Install when |
|-------|----------|-----------|----------|--------------|
| Python | `format-python.py` | black + isort | Python 3 | In project deps (requirements*.txt, pyproject.toml, Pipfile), or user approves |
| Node.js | `format-node.js` | prettier | Node.js | In package.json devDependencies, or user approves |
| Rust | `format-rust.sh` | rustfmt | Bash | Always (rustfmt is built-in) |
| Go | `format-go.sh` | gofmt | Bash | Always (gofmt is built-in) |
| C#/.NET | `format-csharp.sh` | csharpier | Bash | In `.config/dotnet-tools.json`, or user approves (suggest `dotnet tool install csharpier`) |
| Java | `format-java.sh` | google-java-format | Bash | `google-java-format` is on PATH, or user approves (suggest installing from github.com/google/google-java-format) |
| C/C++ | `format-cpp.sh` | clang-format | Bash | `clang-format` is on PATH, or user approves (bundled with LLVM/Clang; available via system package manager) |
| Dart/Flutter | `format-dart.sh` | dart format | Bash | Always (dart format is built-in with the Dart/Flutter SDK) |
| (other) | — | Search web for "[language] most popular formatter" | Bash | Formatter is on PATH, or user approves installation |

**Unsupported stacks:** Use web search to find the standard formatter for the detected language. If no formatter is found (or web search is unavailable), inform the user: **"Could not determine a formatter for [detected stack] — skipping formatter hook."** Do not create a hook. If found, the command must invoke a single well-known CLI tool with simple arguments (no shell operators, pipes, redirects, variable expansion, subshells, chained commands, or interpreter invocations; bare command name with no path separators; single line of printable ASCII). Present findings and exact commands to the user for approval before executing. If approved, create a custom shell hook (`.claude/hooks/format-<language>.sh`) following the pattern of existing shell-based hooks (`format-rust.sh`, `format-go.sh`). The hook body must contain only the formatter invocation with its file-path argument (always double-quote `"$1"` to prevent word splitting on filenames with spaces).

> **No import organizers:** Tools that remove unused imports (e.g., `prettier-plugin-organize-imports`, `goimports`) are intentionally excluded from PostToolUse hooks. They remove imports that appear unused mid-edit, causing a destructive loop when Claude adds an import before writing the code that uses it.

## Python Command Detection

Only when the Python formatter hook will be installed: Run `python3 --version`. If it fails, run `python --version` and verify the output shows Python 3.x. Use whichever succeeds as `<python-cmd>` in hook commands. If neither works, skip the Python hook and inform the user.

## Installation Steps

1. Copy applicable template(s) from `$CLAUDE_PLUGIN_ROOT/skills/init/templates/hooks/` to `.claude/hooks/`. For unsupported stacks, create a custom `format-<language>.sh` in `.claude/hooks/` following existing shell hook patterns (e.g., `format-rust.sh`, `format-go.sh`).
2. External formatters not in deps → ask user "Add [formatter] as dev dependency and install format hook?" If declined, skip that stack's hook entirely. If approved, install the formatter using the stack-specific commands in "Formatter Installation Commands" below (for unsupported stacks, use the installation command identified via web search — present the exact command to the user for approval before executing), then proceed to copy/create the hook.
3. If any hooks were installed, create `.claude/settings.json` using the template from `$CLAUDE_PLUGIN_ROOT/skills/init/templates/settings.json` as reference. Keep only entries for hooks actually installed. For Python, replace `<python-cmd>` with the detected command (`python3` or `python`). For Node.js use `node "..."`, for Bash-based hooks (Rust, Go, C#, Java, C/C++, Dart/Flutter, and custom unsupported-stack hooks) use `bash "..."`. Monorepos: install all applicable hooks (each filters by file extension internally).

**If no hooks were installed**, do not create settings.json (unless it already exists with other content).

**Preserve existing content:** If an existing settings.json contains a `permissions` section or other custom configuration beyond `hooks`, preserve those sections. Merge hook changes into the existing file structure rather than overwriting.

## Formatter Installation Commands

When the user approves a formatter that is not already in the project, install it before copying the hook template. Use the package manager detected during project analysis.

**Python (black + isort):**
- pip: `pip install black isort` (or add to the appropriate requirements file and install)
- poetry: `poetry add --group dev black isort`
- uv: `uv add --dev black isort`

**Node.js (prettier):**
- npm: `npm install --save-dev prettier`
- yarn: `yarn add --dev prettier`
- pnpm: `pnpm add --save-dev prettier`
- bun: `bun add --dev prettier`

**C#/.NET (csharpier):**
- If `.config/dotnet-tools.json` does not exist: `dotnet new tool-manifest`
- Then: `dotnet tool install csharpier`
- Then: `dotnet tool restore`

**Java (google-java-format):**
- Download the latest JAR from github.com/google/google-java-format releases and place it on PATH

**C/C++ (clang-format):**
- Linux: install via system package manager (e.g., `apt install clang-format`)
- macOS: `brew install clang-format`
- Windows: install via LLVM installer or `choco install llvm`

