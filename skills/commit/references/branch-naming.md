# Branch Naming Convention

Shared reference for generating feature branch names. Consumed by `branch`, `commit`, `tdd`, and `worktree` skills.

## Format

```
<type>/<slugified-description>
```

## Type

Use the conventional commit type that best describes the change:

| Type | Use when |
|------|----------|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `refactor` | Code restructuring without behavior change |
| `docs` | Documentation only |
| `style` | Formatting, whitespace (no logic change) |
| `test` | Adding or updating tests |
| `chore` | Build, CI, dependencies, tooling |
| `perf` | Performance improvement |

## Type Detection Keywords

When inferring `<type>` from a description or context:
- Keywords like "add", "implement", "create", "new" → `feat`
- Keywords like "fix", "bug", "broken", "error", "crash" → `fix`
- Keywords like "refactor", "restructure", "clean up", "simplify" → `refactor`
- Keywords like "test", "coverage", "spec" → `test`
- Keywords like "docs", "readme", "documentation", "comment" → `docs`
- Keywords like "style", "format", "lint", "whitespace" → `style`
- Keywords like "performance", "optimize", "speed", "cache" → `perf`
- Keywords like "build", "ci", "dependency", "upgrade", "config" → `chore`
- When ambiguous, default to `feat` for new files or `fix` for modifications

## Slug Rules

1. Start from the description (commit message subject, task description, etc.)
2. Convert to lowercase
3. Replace spaces with hyphens
4. Strip characters not in `[a-z0-9-]`
5. Collapse consecutive hyphens into one
6. Remove leading and trailing hyphens
7. Truncate to keep the total branch name (`<type>/` + slug) at max 50 characters

## Examples

- `feat/add-user-authentication`
- `fix/login-validation-error`
- `refactor/extract-payment-module`
- `test/add-cart-endpoint-coverage`
- `chore/upgrade-eslint-to-v9`
