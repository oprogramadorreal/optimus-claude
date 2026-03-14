#!/usr/bin/env bash
# Structural validation for the optimus-claude plugin.
# Checks invariants that should hold on every commit.
# Run: bash scripts/validate.sh

set -euo pipefail

errors=0
pass=0

check() {
  local label="$1"
  shift
  if "$@" 2>/dev/null; then
    printf "  PASS  %s\n" "$label"
    ((pass++)) || true
  else
    printf "  FAIL  %s\n" "$label"
    ((errors++)) || true
  fi
}

echo "=== optimus-claude validation ==="
echo

# --- 1. No CRLF in script files (checks raw blobs via git cat-file) ---
echo "[Line endings]"
crlf_files=""
while IFS= read -r f; do
  if git cat-file -p "HEAD:$f" 2>/dev/null | grep -qP '\r$'; then
    crlf_files+="  $f"$'\n'
  fi
done < <(git ls-files -- '*.sh' 'hooks/session-start')
check "No CRLF in shell scripts" test -z "$crlf_files"
if [ -n "$crlf_files" ]; then
  printf "       Files with CRLF:\n%s" "$crlf_files"
fi

# --- 2. Shebang consistency ---
echo "[Shebangs]"
bad_shebangs=""
while IFS= read -r f; do
  first_line=$(git cat-file -p "HEAD:$f" 2>/dev/null | head -1 | tr -d '\r')
  if [[ "$first_line" == "#!/bin/bash"* ]]; then
    bad_shebangs+="  $f"$'\n'
  fi
done < <(git ls-files -- '*.sh' 'hooks/session-start')
check "All scripts use #!/usr/bin/env bash" test -z "$bad_shebangs"
if [ -n "$bad_shebangs" ]; then
  printf "       Non-portable shebangs:\n%s" "$bad_shebangs"
fi

# --- 3. SKILL.md frontmatter ---
echo "[SKILL.md frontmatter]"
fm_errors=""
while IFS= read -r f; do
  skill_name=$(basename "$(dirname "$f")")
  # Strip CR for Windows compat, then extract frontmatter between --- delimiters
  clean=$(tr -d '\r' < "$f")
  if ! echo "$clean" | head -1 | grep -q '^---'; then
    fm_errors+="  $f: missing frontmatter delimiter\n"
    continue
  fi
  frontmatter=$(echo "$clean" | sed -n '2,/^---$/{ /^---$/d; p; }')
  # Check description
  if ! echo "$frontmatter" | grep -q '^description:'; then
    fm_errors+="  $f: missing description field\n"
  fi
  # Check disable-model-invocation
  if ! echo "$frontmatter" | grep -q 'disable-model-invocation: true'; then
    fm_errors+="  $f: missing disable-model-invocation: true\n"
  fi
  # Check no name field (would shadow builtins)
  if echo "$frontmatter" | grep -q '^name:'; then
    fm_errors+="  $f: has 'name:' field (shadows builtin commands)\n"
  fi
done < <(find ./skills -name 'SKILL.md' -not -path './.git/*')
check "SKILL.md frontmatter valid" test -z "$fm_errors"
if [ -n "$fm_errors" ]; then
  printf "       Issues:\n%s" "$fm_errors"
fi

# --- 4. No ref in marketplace.json ---
echo "[Manifests]"
check "No ref field in marketplace.json" \
  bash -c '! grep -q "\"ref\"" .claude-plugin/marketplace.json'

# --- 5. plugin.json validity ---
if command -v jq &>/dev/null; then
  check "plugin.json is valid JSON" jq empty .claude-plugin/plugin.json
  check "plugin.json has name" bash -c 'jq -e ".name" .claude-plugin/plugin.json >/dev/null'
  check "plugin.json has version" bash -c 'jq -e ".version" .claude-plugin/plugin.json >/dev/null'
  check "plugin.json has description" bash -c 'jq -e ".description" .claude-plugin/plugin.json >/dev/null'
else
  echo "  SKIP  plugin.json checks (jq not installed)"
fi

# --- 6. No hardcoded /tmp in SKILL.md ---
echo "[Portability]"
tmp_hits=$(grep -rn 'mktemp /tmp/' skills/*/SKILL.md 2>/dev/null || true)
check "No hardcoded mktemp /tmp/ in skills" test -z "$tmp_hits"
if [ -n "$tmp_hits" ]; then
  printf "       Hardcoded /tmp:\n%s\n" "$tmp_hits"
fi

# --- Summary ---
echo
echo "=== Results: $pass passed, $errors failed ==="
exit "$errors"
