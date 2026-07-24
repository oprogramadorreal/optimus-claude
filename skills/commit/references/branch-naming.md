# Branch Naming Convention

Shared reference for generating feature branch names. Consumed by the commit, tdd, and worktree skills.

## Format

```
<type>/<slugified-description>
```

`<type>` is the conventional commit type that best describes the change: `feat`, `fix`, `refactor`, `docs`, `style`, `test`, `chore`, or `perf`.

## Type Detection Keywords

When inferring `<type>` from a description or context:

- "add", "implement", "create", "new" → `feat`
- "fix", "bug", "broken", "error", "crash" → `fix`
- "refactor", "restructure", "clean up", "simplify" → `refactor`
- "test", "coverage", "spec" → `test`
- "docs", "readme", "documentation" → `docs`
- "style", "format", "lint", "whitespace" → `style`
- "performance", "optimize", "speed", "cache" → `perf`
- "build", "ci", "dependency", "upgrade", "config" → `chore`
- When ambiguous, default to `feat` for new files or `fix` for modifications

## Slug Rules

Lowercase the description, replace spaces with hyphens, strip characters outside `[a-z0-9-]`, collapse consecutive hyphens, and trim leading/trailing hyphens. Truncate so the total branch name (`<type>/` + slug) stays at max 50 characters.

## Collision Handling

Default policy when the derived name already exists (`git show-ref --verify --quiet refs/heads/<branch-name>` succeeds): append `-2` to the slug; if taken, try `-3` through `-9`. If all collide, inform the user and stop.

## Examples

- `feat/add-user-authentication`
- `fix/login-validation-error`
- `chore/upgrade-eslint-to-v9`
