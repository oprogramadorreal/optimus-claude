# Body-File Temp File Pattern

Used by `pr`, `tdd`, and `code-review` to materialize a body/description on disk for `gh pr create --body-file` / `gh pr comment --body-file` / `glab api -F body=@…`.

## Canonical pattern

Substitute `<stem>` (e.g., `pr-body`, `review-summary`) per call site. Run as a single chained bash invocation so the `trap` is in scope for every step:

```bash
TMPFILE=$(mktemp ./.<stem>-XXXXXX.md) && trap 'rm -f "$TMPFILE"' EXIT INT TERM \
  && printf '%s' "<body>" > "$TMPFILE" \
  && <gh-or-glab-command-using "$TMPFILE">
```

The explicit `rm -f` is unnecessary — the `EXIT` trap fires on normal exit too.

## Why this exact shape

1. **Path in CWD** — Windows-native `gh.exe` / `glab.exe` cannot resolve Git Bash's `/tmp` mount; using a `/tmp` path silently submits an empty body / comment. A `./…` relative path is identical for the POSIX shell and the Windows binary.
2. **Dot-prefixed filename** — orphan files left after an interruption are excluded from a `git add *.md` glob (bash dotglob is off by default), reducing the chance that a draft PR body or unredacted review summary gets accidentally staged.
3. **`trap … EXIT INT TERM`** — guarantees cleanup even if the `gh`/`glab` step is Ctrl-C'd or errors out. Without it, the temp file persists in the working tree.
4. **`--tmpdir` is not used** — it's a GNU coreutils extension that BSD `mktemp` on macOS rejects.

## Validator contract

`scripts/validate.sh` section 7 forbids non-portable mktemp invocations in `skills/*/SKILL.md` (`/tmp/`, `${TMPDIR:-/tmp}`, `--tmpdir`, `-p`, `-t`). Section 17 pins the consumer references to this file so a silent revert is caught.
