# Formatter Hook Setup

Detailed instructions for installing auto-format hooks per tech stack. Referenced from Step 5 of the init skill.

## Hook Templates

All templates are in `$CLAUDE_PLUGIN_ROOT/skills/init/templates/hooks/`.

| Stack | Template | Formatter | Requires | Install when |
|-------|----------|-----------|----------|--------------|
| Python | `format-python.py` | black + isort | Python 3 | In project deps (requirements*.txt, pyproject.toml, Pipfile), or user approves |
| Node.js | `format-node.js` | prettier + organize-imports plugin | Node.js | In package.json devDependencies, or user approves |
| Rust | `format-rust.sh` | rustfmt | Bash | Always (rustfmt is built-in) |
| Go | `format-go.sh` | goimports → gofmt fallback | Bash | Always (hook detects goimports at runtime; offer `go install golang.org/x/tools/cmd/goimports@latest` if absent) |
| C#/.NET | `format-csharp.sh` | csharpier | Bash | In `.config/dotnet-tools.json`, or user approves (suggest `dotnet tool install csharpier`) |
| Java | `format-java.sh` | google-java-format | Bash | `google-java-format` is on PATH, or user approves (suggest installing from github.com/google/google-java-format) |
| C/C++ | `format-cpp.sh` | clang-format | Bash | `clang-format` is on PATH, or user approves (bundled with LLVM/Clang; available via system package manager) |

## Python Command Detection

Only when the Python formatter hook will be installed: Run `python3 --version`. If it fails, run `python --version` and verify the output shows Python 3.x. Use whichever succeeds as `<python-cmd>` in hook commands. If neither works, skip the Python hook and inform the user.

## Installation Steps

1. Copy applicable template(s) from `$CLAUDE_PLUGIN_ROOT/skills/init/templates/hooks/` to `.claude/hooks/`.
2. External formatters not in deps → ask user "Add [formatter] as dev dependency and install format hook?" If declined, skip.
3. If any hooks were installed, create `.claude/settings.json` using the template from `$CLAUDE_PLUGIN_ROOT/skills/init/templates/settings.json` as reference. Keep only entries for hooks actually installed. For Python, replace `<python-cmd>` with the detected command (`python3` or `python`). For Node.js use `node "..."`, for Bash-based hooks (Rust, Go, C#, Java, C/C++) use `bash "..."`. Monorepos: install all applicable hooks (each filters by file extension internally).

**If no hooks were installed**, do not create settings.json (unless it already exists with other content).

**Preserve existing content:** If an existing settings.json contains a `permissions` section or other custom configuration beyond `hooks`, preserve those sections. Merge hook changes into the existing file structure rather than overwriting.

## Node.js Plugin Setup

When the Node.js hook is installed: Ensure `prettier-plugin-organize-imports` is a devDependency (install with detected package manager if missing; skip config below if user declines). Then add it to the Prettier config's `plugins` array.

Check for config in this order: `.prettierrc`, `.prettierrc.json`, `.prettierrc.yaml`, `.prettierrc.yml`, `.prettierrc.toml`, `.prettierrc.mjs`, `.prettierrc.cjs`, `prettier.config.js`, `prettier.config.mjs`, `prettier.config.cjs`, `prettier.config.ts`, or `"prettier"` key in `package.json`.

If `prettier-plugin-tailwindcss` is present, insert organize-imports **before** it. If no config exists, create `.prettierrc` with `{ "plugins": ["prettier-plugin-organize-imports"] }`.
