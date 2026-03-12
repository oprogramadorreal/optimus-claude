# Branch Naming Convention

Shared reference for generating feature branch names. Consumed by `commit` and `tdd` skills.

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
