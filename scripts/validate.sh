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
  # Strip CR for Windows compat; read first line directly to avoid broken pipe
  first_line=$(head -1 "$f" | tr -d '\r')
  if [[ "$first_line" != "---" ]]; then
    fm_errors+="  $f: missing frontmatter delimiter\n"
    continue
  fi
  # Extract frontmatter between --- delimiters (lines 2..closing ---)
  frontmatter=$(sed -n '2,/^---$/{ /^---$/d; p; }' "$f" | tr -d '\r')
  # Check description
  if ! grep -q '^description:' <<< "$frontmatter"; then
    fm_errors+="  $f: missing description field\n"
  fi
  # Check disable-model-invocation
  if ! grep -q 'disable-model-invocation: true' <<< "$frontmatter"; then
    fm_errors+="  $f: missing disable-model-invocation: true\n"
  fi
  # Check no name field (would shadow builtins)
  if grep -q '^name:' <<< "$frontmatter"; then
    fm_errors+="  $f: has 'name:' field (shadows builtin commands)\n"
  fi
  # Check argument-hint is quoted (bare brackets parse as a YAML list)
  if grep -q '^argument-hint:[[:space:]]*\[' <<< "$frontmatter"; then
    fm_errors+="  $f: argument-hint value must be quoted (bare brackets parse as a YAML list)\n"
  fi
  # Check rendered description length against the 1024-char platform cap
  # (handles both single-line and folded ">-" scalars)
  description=$(awk '
    /^description:[[:space:]]*>-?[[:space:]]*$/ { folded = 1; next }
    folded {
      if ($0 ~ /^[[:space:]]/) {
        line = $0; sub(/^[[:space:]]+/, "", line)
        text = (text == "" ? line : text " " line); next
      }
      folded = 0
    }
    /^description:[[:space:]]/ { text = $0; sub(/^description:[[:space:]]*/, "", text) }
    END { print text }
  ' <<< "$frontmatter")
  if [ "${#description}" -gt 1024 ]; then
    fm_errors+="  $f: description exceeds the 1024-char platform cap (${#description})\n"
  fi
done < <(find ./skills -name 'SKILL.md' -not -path './.git/*')
check "SKILL.md frontmatter valid" test -z "$fm_errors"
if [ -n "$fm_errors" ]; then
  # %b, not %s: fm_errors is accumulated with literal \n escapes (as in every
  # sibling check), which %s would print verbatim on one run-on line.
  printf "       Issues:\n%b" "$fm_errors"
fi

# --- 4. No ref in marketplace.json ---
echo "[Manifests]"
check "No ref field in marketplace.json" \
  bash -c '! grep -q "\"ref\"" .claude-plugin/marketplace.json'

# --- 4b. Dogfooded hook matches the shipped template ---
# .claude/hooks/restrict-paths.sh is a copy of the template users install, and
# only the template is exercised by scripts/test-hooks.sh. Nothing else pins them
# together, and they have drifted before (commits that hardened the memory-store
# exemption and broadened the precious-file patterns landed in the template
# alone, leaving this repo running stale security logic). A template-only fix
# leaves this repo unprotected; a .claude/-only fix ships nothing to users.
check "restrict-paths hook copies are in sync" \
  cmp -s .claude/hooks/restrict-paths.sh skills/permissions/templates/hooks/restrict-paths.sh

# --- 5. plugin.json validity ---
if command -v jq &>/dev/null; then
  check "plugin.json is valid JSON" jq empty .claude-plugin/plugin.json
  check "plugin.json has name" bash -c 'jq -e ".name" .claude-plugin/plugin.json >/dev/null'
  check "plugin.json has version" bash -c 'jq -e ".version" .claude-plugin/plugin.json >/dev/null'
  check "plugin.json has description" bash -c 'jq -e ".description" .claude-plugin/plugin.json >/dev/null'
else
  echo "  SKIP  plugin.json checks (jq not installed)"
fi

# --- 6. Version bump check (PR branches only) ---
echo "[Version bump]"
if ! git rev-parse --verify origin/master &>/dev/null; then
  echo "  SKIP  Version bump check (origin/master not available)"
elif ! command -v jq &>/dev/null; then
  echo "  SKIP  Version bump check (jq not installed)"
else
  head_commit=$(git rev-parse HEAD 2>/dev/null)
  master_commit=$(git rev-parse origin/master 2>/dev/null)
  if [ "$head_commit" = "$master_commit" ]; then
    echo "  SKIP  Version bump check (on master)"
  else
    master_ver=$(MSYS_NO_PATHCONV=1 git show origin/master:.claude-plugin/plugin.json 2>/dev/null | jq -r '.version' 2>/dev/null || echo "")
    current_ver=$(jq -r '.version' .claude-plugin/plugin.json 2>/dev/null || echo "")
    if [ -n "$master_ver" ] && [ -n "$current_ver" ]; then
      check "plugin.json version bumped (master: $master_ver, current: $current_ver)" \
        test "$current_ver" != "$master_ver"
      check "README.md version badge matches plugin.json ($current_ver)" \
        grep -qF "version-${current_ver}-blue" README.md
    else
      echo "  SKIP  Version bump check (could not extract versions)"
    fi
  fi
fi

# --- 7. Portable mktemp invocation in SKILL.md ---
# Forbid non-portable mktemp forms. The [^`]{0,200} cap stops matching at the
# closing backtick of an inline code span and bounds runaway matching across
# the line.
echo "[Portability]"
tmp_hits=$(grep -rnE 'mktemp[^`]{0,200}(/tmp/|TMPDIR:-/tmp|--tmpdir| -p | -t )' skills/*/SKILL.md 2>/dev/null || true)
check "Portable mktemp in skills (use mktemp ./<template> for Win+macOS portability)" test -z "$tmp_hits"
if [ -n "$tmp_hits" ]; then
  printf "       Non-portable mktemp (Windows- or BSD-incompatible):\n%s\n" "$tmp_hits"
fi

# --- 8. Cross-reference integrity ---
# Every $CLAUDE_PLUGIN_ROOT/... path in skill files must point to an existing file.
# grep -o emits one hit per occurrence, so a line carrying several references is
# checked in full. (A `sed 's|.*ROOT/\(...\).*|\1|'` here would match greedily and
# silently validate only the LAST reference on each such line.)
echo "[Cross-references]"
broken_refs=""
while IFS= read -r ref_hit; do
  # Each hit is "<file>:<lineno>:$CLAUDE_PLUGIN_ROOT/<path>". Paths appear inside
  # backticks, quotes, or bare — the match runs until whitespace/backtick/quote.
  src_file=${ref_hit%%:*}
  ref_path=$(printf '%s' "$ref_hit" | sed 's|^[^:]*:[0-9]*:||; s|^\$[{]\{0,1\}CLAUDE_PLUGIN_ROOT[}]\{0,1\}/||; s|\r$||')
  if [ -n "$ref_path" ] && [ ! -f "./$ref_path" ] && [ ! -d "./$ref_path" ]; then
    broken_refs+="  $src_file -> $ref_path\n"
  fi
done < <(grep -rnoE '\$\{?CLAUDE_PLUGIN_ROOT\}?/[^ `"'"'"']*' skills/ references/ 2>/dev/null || true)
check "All CLAUDE_PLUGIN_ROOT references resolve" test -z "$broken_refs"
if [ -n "$broken_refs" ]; then
  printf "       Broken references:\n%b" "$broken_refs"
fi

# --- 9. Orphan detection ---
# Every file in references/, templates/, and agents/ should be referenced by at least one skill file.
echo "[Orphan detection]"
orphan_files=""
# Build the set of all reference and template files
while IFS= read -r f; do
  # Skip README.md files in skill dirs (they're documentation, not referenced by SKILL.md via CLAUDE_PLUGIN_ROOT)
  basename_f=$(basename "$f")
  if [ "$basename_f" = "README.md" ]; then
    continue
  fi
  # Normalize: strip leading ./
  rel_path="${f#./}"
  # Check if this file is referenced in any skill .md file:
  # 1. By full relative path (e.g., skills/init/references/foo.md)
  # 2. By basename only (e.g., format-python.py in a table or prose)
  # 3. By parent directory reference (e.g., templates/hooks/ covers all files
  #    inside) — skill-level files only. For root references/ and agents/
  #    files this fallback is vacuous (the strings "references/" and "agents/"
  #    match trivially somewhere in skills/), so they must match by full path
  #    or basename.
  case "$rel_path" in
    references/*|agents/*)
      if ! grep -rq "$rel_path" skills/ 2>/dev/null && \
         ! grep -rq "$basename_f" skills/ 2>/dev/null; then
        orphan_files+="  $rel_path\n"
      fi
      ;;
    *)
      parent_dir=$(dirname "$rel_path")
      if ! grep -rq "$rel_path" skills/ 2>/dev/null && \
         ! grep -rq "$basename_f" skills/ 2>/dev/null && \
         ! grep -rq "$parent_dir/" skills/ 2>/dev/null; then
        orphan_files+="  $rel_path\n"
      fi
      ;;
  esac
done < <(( find ./skills -path '*/references/*' -o -path '*/templates/*' -o -path '*/agents/*'; find ./references ./agents -type f 2>/dev/null ) | grep -v '/__' | sort)
check "No orphaned reference/template/agent files" test -z "$orphan_files"
if [ -n "$orphan_files" ]; then
  printf "       Unreferenced files:\n%b" "$orphan_files"
fi

# --- 10. Template script syntax ---
echo "[Template syntax]"
syntax_errors=""

# Shell scripts
if command -v bash &>/dev/null; then
  while IFS= read -r f; do
    if ! bash -n "$f" 2>/dev/null; then
      syntax_errors+="  $f: bash syntax error\n"
    fi
  done < <(find ./skills -path '*/templates/*.sh' -o -path '*/templates/**/*.sh' 2>/dev/null | sort)
  # Also check hooks/session-start
  if [ -f "./hooks/session-start" ]; then
    if ! bash -n "./hooks/session-start" 2>/dev/null; then
      syntax_errors+="  hooks/session-start: bash syntax error\n"
    fi
  fi
fi

# Node.js scripts
if command -v node &>/dev/null; then
  while IFS= read -r f; do
    if ! node --check "$f" 2>/dev/null; then
      syntax_errors+="  $f: node syntax error\n"
    fi
  done < <(find ./skills -path '*/templates/*.js' -o -path '*/templates/**/*.js' 2>/dev/null | sort)
else
  echo "  SKIP  Node.js syntax checks (node not installed)"
fi

# Python scripts — detect working python command (python3 may be a broken Windows alias)
py_cmd=""
if python3 --version &>/dev/null; then
  py_cmd="python3"
elif python --version &>/dev/null; then
  py_cmd="python"
fi
if [ -n "$py_cmd" ]; then
  while IFS= read -r f; do
    if ! "$py_cmd" -c "import py_compile, sys; py_compile.compile(sys.argv[1], doraise=True)" "$f" 2>/dev/null; then
      syntax_errors+="  $f: python syntax error\n"
    fi
  done < <({ find ./skills -path '*/templates/*.py' -o -path '*/templates/**/*.py' 2>/dev/null; find ./scripts -name '*.py' 2>/dev/null; } | sort -u)
else
  echo "  SKIP  Python syntax checks (python not installed)"
fi

check "Template scripts parse without errors" test -z "$syntax_errors"
if [ -n "$syntax_errors" ]; then
  printf "       Syntax errors:\n%b" "$syntax_errors"
fi

# --- 11. JSON template validity ---
echo "[JSON templates]"
if command -v jq &>/dev/null; then
  json_errors=""
  while IFS= read -r f; do
    # Skip known files with intentional placeholders (e.g., <python-cmd>)
    if grep -q '<python-cmd>' "$f" 2>/dev/null; then
      continue
    fi
    if ! jq empty "$f" 2>/dev/null; then
      json_errors+="  $f: invalid JSON\n"
    fi
  done < <(find ./skills -path '*/templates/*.json' -o -path '*/templates/**/*.json' 2>/dev/null | sort)
  check "JSON templates are valid" test -z "$json_errors"
  if [ -n "$json_errors" ]; then
    printf "       Invalid JSON:\n%b" "$json_errors"
  fi
else
  echo "  SKIP  JSON template checks (jq not installed)"
fi

# --- 12. Skill directory completeness ---
echo "[Skill completeness]"
missing_files=""
for skill_dir in ./skills/*/; do
  skill_name=$(basename "$skill_dir")
  if [ ! -f "$skill_dir/SKILL.md" ]; then
    missing_files+="  skills/$skill_name/SKILL.md\n"
  fi
  if [ ! -f "$skill_dir/README.md" ]; then
    missing_files+="  skills/$skill_name/README.md\n"
  fi
done
check "Every skill has SKILL.md and README.md" test -z "$missing_files"
if [ -n "$missing_files" ]; then
  printf "       Missing files:\n%b" "$missing_files"
fi

# --- 13. README skill list vs actual skills/ directories ---
echo "[README consistency]"
readme_mismatch=""
# Get actual skill names from directories
actual_skills=""
for skill_dir in ./skills/*/; do
  actual_skills+="$(basename "$skill_dir") "
done
# Check each actual skill is mentioned in README.md
for skill in $actual_skills; do
  if ! grep -q "/optimus:$skill" README.md 2>/dev/null; then
    readme_mismatch+="  skills/$skill: not listed in README.md\n"
  fi
done
# CONTRIBUTING.md's project-structure tree has drifted before — assert
# every skill directory appears there too.
for skill in $actual_skills; do
  if ! grep -qE "(├──|└──) $skill/" CONTRIBUTING.md 2>/dev/null; then
    readme_mismatch+="  skills/$skill: not listed in CONTRIBUTING.md project structure\n"
  fi
done
check "README lists all skills" test -z "$readme_mismatch"
if [ -n "$readme_mismatch" ]; then
  printf "       Missing from README:\n%b" "$readme_mismatch"
fi

# --- 14. hooks.json validity ---
echo "[Plugin hooks]"
if command -v jq &>/dev/null; then
  check "hooks.json is valid JSON" jq empty hooks/hooks.json
  # Check that referenced command scripts exist
  hook_missing=""
  while IFS= read -r cmd; do
    # Extract script path from command string (strip quotes and $CLAUDE_PLUGIN_ROOT)
    script_path=$(printf '%s' "$cmd" | sed "s|.*'\${CLAUDE_PLUGIN_ROOT}/\([^']*\)'.*|\1|" | sed 's|"${CLAUDE_PLUGIN_ROOT}/||;s|"||g')
    if [ -n "$script_path" ] && [ ! -f "./$script_path" ]; then
      hook_missing+="  $script_path\n"
    fi
  done < <(jq -r '.. | .command? // empty' hooks/hooks.json 2>/dev/null)
  check "Hook command scripts exist" test -z "$hook_missing"
  if [ -n "$hook_missing" ]; then
    printf "       Missing hook scripts:\n%b" "$hook_missing"
  fi
else
  echo "  SKIP  hooks.json checks (jq not installed)"
fi

# --- 15. Plugin-level agents ---
echo "[Plugin agents]"
agent_issues=""
agent_count=0
# Glob the tree, not a hardcoded list: a new agent is validated automatically
# instead of shipping unvalidated when the list goes stale (skills get the
# same treatment in section 12 via ./skills/*/).
for agent_file in agents/*.md; do
  [ -e "$agent_file" ] || continue
  agent_count=$((agent_count + 1))
  # Check frontmatter has tools: field
  if ! grep -q '^tools:' "$agent_file" 2>/dev/null; then
    agent_issues+="  $agent_file: missing 'tools:' in frontmatter\n"
  fi
  if ! grep -q '^name:' "$agent_file" 2>/dev/null; then
    agent_issues+="  $agent_file: missing 'name:' in frontmatter\n"
  fi
done
if [ "$agent_count" -eq 0 ]; then
  agent_issues+="  agents/: no agent definitions found\n"
fi
# Check that old template agents directory does NOT exist
if [ -d "skills/init/templates/agents" ] && [ "$(ls -A skills/init/templates/agents 2>/dev/null)" ]; then
  agent_issues+="  skills/init/templates/agents/ still contains files (should be moved to agents/)\n"
fi
check "Plugin-level agents valid" test -z "$agent_issues"
if [ -n "$agent_issues" ]; then
  printf "       Issues:\n%b" "$agent_issues"
fi

# --- 16. Reference depth check (max 2 levels from SKILL.md) ---
echo "[Reference depth]"
deep_refs=""
# For each reference file that is loaded by a SKILL.md, check if it loads further
# references that themselves load more (3+ levels deep)
while IFS= read -r ref_file; do
  # This is a level-1 reference (loaded by SKILL.md). Check what it references.
  # Iterate over every reference rather than every line: with one path extracted
  # per line, a multi-ref line contributed only its last target, and a `continue`
  # on a non-file target (e.g. a directory) discarded the rest of that line too.
  while IFS= read -r l2_path; do
    if [ -z "$l2_path" ] || [ ! -f "./$l2_path" ]; then
      continue
    fi
    # This is a level-2 reference. Check if IT references more files (level-3 = too deep)
    # Exclude references to top-level agents/ and references/ — these are leaf files (role definitions, shared constraints)
    has_deep=$(grep '\$[{]\{0,1\}CLAUDE_PLUGIN_ROOT[}]\{0,1\}/' "./$l2_path" 2>/dev/null | grep -v '\$[{]\{0,1\}CLAUDE_PLUGIN_ROOT[}]\{0,1\}/agents/' | grep -v '\$[{]\{0,1\}CLAUDE_PLUGIN_ROOT[}]\{0,1\}/references/' || true)
    if [ -n "$has_deep" ]; then
      deep_refs+="  $ref_file -> $l2_path -> (further refs)\n"
    fi
  done < <(grep -oE '\$\{?CLAUDE_PLUGIN_ROOT\}?/[^ `"'"'"']*' "./$ref_file" 2>/dev/null | sed 's|^\$[{]\{0,1\}CLAUDE_PLUGIN_ROOT[}]\{0,1\}/||' || true)
done < <(find ./skills -path '*/references/*.md' -o -path '*/agents/*.md' | sort)
check "Reference depth <= 2 levels" test -z "$deep_refs"
if [ -n "$deep_refs" ]; then
  printf "       Deep reference chains (3+ levels):\n%b" "$deep_refs"
fi

# --- 17. Producer/consumer contracts ---
# Genuine two-sided contracts: a literal heading or token one file emits and
# another greps for. Drift on either side silently drops the handoff, so both
# sides are pinned. The contract is file-to-file, not skill-to-skill: an agent
# returning a heading its own SKILL.md keys off is the same failure mode as a
# cross-skill handoff, and is pinned here too. Missing files fail first-class —
# a rename or deletion must break the build, not skip the check.
echo "[Producer/consumer contracts]"
contract_errors=""

# require_tokens <file> <token>...: every token must appear literally in <file>.
# A missing file is itself a failure, never a silent skip.
require_tokens() {
  local file=$1 token
  shift
  if [ ! -f "$file" ]; then
    contract_errors+="  missing file: $file\n"
    return
  fi
  for token in "$@"; do
    if ! grep -qF -- "$token" "$file" 2>/dev/null; then
      contract_errors+="  $file missing contract token: $token\n"
    fi
  done
}

# require_pattern <file> <ere>...: every extended-regex pattern must match.
# For anchored headings ('^## Foo') where fixed-string search can't anchor.
require_pattern() {
  local file=$1 pattern
  shift
  if [ ! -f "$file" ]; then
    contract_errors+="  missing file: $file\n"
    return
  fi
  for pattern in "$@"; do
    if ! grep -qE "$pattern" "$file" 2>/dev/null; then
      contract_errors+="  $file missing contract pattern: $pattern\n"
    fi
  done
}

# require_min_count <identifier> <min> <file>: occurrence-count floor. Counts
# pin cross-step identifiers where a one-sided rename (or a dropped
# occurrence) silently disables a multi-step contract. `|| true` lets the
# count=0 case reach the comparison instead of aborting under set -e — count=0
# is exactly the failure mode this check exists to catch.
require_min_count() {
  local identifier=$1 expected=$2 file=$3 actual
  actual=$(grep -cF "$identifier" "$file" 2>/dev/null || true)
  [ -z "$actual" ] && actual=0
  if [ "$actual" -lt "$expected" ]; then
    contract_errors+="  $file cross-step identifier '$identifier' appears $actual times, expected >=$expected\n"
  fi
}

# Scenario contract: brainstorm's spec template emits these headings; tdd's
# scenario-driven shortcut greps specs for them.
require_tokens skills/brainstorm/SKILL.md '## Scenarios' '### Scenario:'
require_tokens skills/tdd/SKILL.md '## Scenarios' '### Scenario:'

# TDD-summary handoff: tdd emits the summary block; pr detects the
# '## TDD Summary' heading to populate Intent and the per-item Test plan.
require_tokens skills/tdd/SKILL.md '## TDD Summary' '### Behaviors Implemented' '### Coverage'
require_tokens skills/pr/SKILL.md '## TDD Summary' '### Behaviors Implemented' '### Coverage'

# Plan-mode handoff: the canonical '### Refined plan' heading defined in
# plan-mode-handoff.md is consumed by jira's refresh/codebase-analysis flows.
require_tokens skills/brainstorm/references/plan-mode-handoff.md '### Refined plan'
if ! grep -rqF -- '### Refined plan' skills/jira/ 2>/dev/null; then
  contract_errors+="  skills/jira/ has no file containing contract token: ### Refined plan\n"
fi

# Harness routing: /optimus:deep dispatches the base skills with
# HARNESS_MODE_INLINE and each base SKILL.md routes on it to its variant's
# reference (runtime contract with scripts/harness_common/cli.py; see
# test_skill_contract.py). The roster is derived from constants.py's variant
# frozensets, so a new deep target is covered here automatically instead of
# shipping unvalidated when a hardcoded list goes stale.
if [ -n "$py_cmd" ]; then
  deep_variant_skills=$(PYTHONPATH=./scripts "$py_cmd" -c "from harness_common.constants import DEEP_VARIANT_SKILLS; print(' '.join(sorted(DEEP_VARIANT_SKILLS)))")
  coverage_variant_skills=$(PYTHONPATH=./scripts "$py_cmd" -c "from harness_common.constants import COVERAGE_VARIANT_SKILLS; print(' '.join(sorted(COVERAGE_VARIANT_SKILLS)))")
  for hs in $deep_variant_skills; do
    require_tokens "skills/$hs/SKILL.md" 'HARNESS_MODE_INLINE' 'references/harness-mode.md'
  done
  for hs in $coverage_variant_skills; do
    require_tokens "skills/$hs/SKILL.md" 'HARNESS_MODE_INLINE' 'references/coverage-harness-mode.md'
  done
else
  echo "  SKIP  Harness-routing roster derivation (python not installed); frozen roster fallback"
  require_tokens skills/code-review/SKILL.md 'HARNESS_MODE_INLINE' 'references/harness-mode.md'
  require_tokens skills/refactor/SKILL.md 'HARNESS_MODE_INLINE' 'references/harness-mode.md'
  require_tokens skills/unit-test/SKILL.md 'HARNESS_MODE_INLINE' 'references/coverage-harness-mode.md'
fi
require_tokens skills/deep/SKILL.md 'HARNESS_MODE_INLINE'

# Agent-return contracts inside how-to-run: the detector and auditor agents emit
# these headings and SKILL.md waits on them by name. A rename on either side
# silently yields an empty handoff — Step 3 then renders every aspect unknown.
require_tokens skills/how-to-run/agents/project-environment-detector.md '## Context Detection Results'
require_tokens skills/how-to-run/SKILL.md 'Context Detection Results'
require_tokens skills/how-to-run/agents/how-to-run-auditor.md '## How-to-Run Audit Results'
require_tokens skills/how-to-run/SKILL.md 'How-to-Run Audit Results'

# Unsupported-stack wiring: the detector only flags the condition, SKILL.md runs
# the fallback. Dropping either side silently loses unknown-stack support.
require_tokens skills/how-to-run/agents/project-environment-detector.md '### Unsupported-Stack Fallback' '- **Triggered:**'
require_tokens skills/how-to-run/SKILL.md 'Triggered: yes' 'unsupported-stack-fallback.md'

# --- how-to-run load-bearing wiring ---
# Step/section navigation and agent return formats the how-to-run flow keys off
# by literal name. A one-sided rename anywhere below fails silently — routing is
# by literal string — with every other check green.
how_to_run_skill="skills/how-to-run/SKILL.md"
detector_file="skills/how-to-run/agents/project-environment-detector.md"
auditor_agent="skills/how-to-run/agents/how-to-run-auditor.md"
walkthrough_ref="skills/how-to-run/references/guided-walkthrough.md"
step6_file="skills/how-to-run/references/step6-verification-audits.md"
esd_file="skills/how-to-run/references/external-services-docker.md"
sections_file="skills/how-to-run/references/how-to-run-sections.md"

# Detector return-format contract: SKILL.md Steps 1/4 branch on these exact
# sub-headings and fields. A silent rename collapses service coverage, drops
# schema-bootstrap rendering, or loses workspace-aware command branching.
require_tokens "$detector_file" \
  '### Recommended Developer Tools' \
  '### External Services' \
  '### Environment Setup' \
  '### Schema Bootstrap' \
  '### Runtime Ports' \
  '### Components' \
  '- **Workspace kind:**' \
  '- **Setup scripts:**' \
  '- **Pre-commit hooks:**' \
  '- **direnv:**' \
  '- **Local TLS cert:**' \
  '- **Database migrations:**' \
  '| Key leaves |' \
  '| Secrets committed |'

# Walkthrough trigger keys: Step 3 routes on the literal 'Walk through it'
# option label and jumps to the '## Step 3a:' heading; Step 3a loads
# guided-walkthrough.md by path and exits on 'Stop the walkthrough' back to
# Step 6. A rename on one side only silently kills the walkthrough branch.
require_pattern "$how_to_run_skill" '^## Step 3a:' '^## Step 6:'
require_tokens "$how_to_run_skill" \
  'Walk through it' \
  'Regenerate' \
  '**Skip**' \
  'Stop the walkthrough' \
  'jump to Step 6' \
  'guided-walkthrough.md'
require_pattern "$walkthrough_ref" \
  '^## Pre-flight' \
  '^## Per-step loop' \
  '^## Advisory flags' \
  '^## Display sanitization' \
  '^## Completion summary'
require_tokens "$walkthrough_ref" \
  '"Done"' \
  '"Skip"' \
  '"Stop the walkthrough"' \
  'Remote code executor' \
  'Destructive command' \
  'SKILL.md Step 6' \
  '**Regenerate**' \
  'Audit:'
# Audit-verdict producer/consumer pair: the auditor emits these verdicts and
# the walkthrough renders them per step (with the 'Audit:' prefix above).
for verdict in 'Found but outdated' 'Partial' 'Missing'; do
  require_tokens "$walkthrough_ref" "$verdict"
  require_tokens "$auditor_agent" "$verdict"
done
# 'Documented but unverifiable' is consumed by SKILL.md's Step 3 per-item
# prompts, not the walkthrough — pin its own producer/consumer pair.
require_tokens "$auditor_agent" 'Documented but unverifiable'
require_tokens "$how_to_run_skill" 'Documented but unverifiable'

# §-style section-name navigation: SKILL.md and the references reach these
# sections exclusively by name (section 8 resolves file paths only, never
# §-names). A rename silently degrades the Docker-suggestion path, the
# workspace-aware command branching, and the Step 6 re-verification audits.
require_pattern "$esd_file" \
  '^## Service Classification Tables' \
  '^## Decision Heuristics' \
  '^## Web-Search Recipe' \
  '^## Verify Commands \(seeds\)' \
  '^## Pre-Conditions Block' \
  '^## Citation Format' \
  '^## Registry Allowlist' \
  '^### Docker-preferred' \
  '^### Local install only'
require_tokens "$esd_file" '**Step 6 audit:**' '## Canonical Image Catalogue (seeds)'
require_tokens "$sections_file" \
  '## External Services' \
  '## Workspace-Kind Command Branches' \
  '## Multi-Repo Workspace Template'
require_pattern "$step6_file" \
  '^## Record-time validation' \
  '^## Render-time sanitization' \
  '^## Step 6 audits'
# SKILL.md Steps 3/4 reach those sections by §-name only — pin the consumer side.
require_tokens "$how_to_run_skill" '§Record-time validation' '§Render-time sanitization'
# Audit-suite completeness: Step 6 applies "every Step 6 audit" in the audits
# file, so a silently dropped audit passes every other gate (the v3 rewrite
# dropped Template-shape this way while its render rules stayed mandated).
require_tokens "$step6_file" \
  'External Services re-verification' \
  'Pre-Conditions Block audit' \
  'Detector-token re-validation' \
  'Specific-Token Audit' \
  'Unverified-Count filter' \
  'Section ordering' \
  'Template-shape audit'

# Cross-step identifiers: Step 3/4 records rendered_line entries in the
# approved-unverifiable-items list and Step 6 exempts exactly those lines by
# full-line equality. A one-sided rename silently breaks the exemption (or
# exempts unintended lines). Threshold = current occurrence count.
require_min_count 'approved-unverifiable-items' 1 "$how_to_run_skill"
require_min_count 'rendered_line' 2 "$how_to_run_skill"
require_min_count 'approved-unverifiable-items' 2 "$step6_file"
require_min_count 'rendered_line' 2 "$step6_file"

# Handoff skill: load-bearing tokens. Renaming any silently breaks the
# emitted-doc shape, the save path, redaction, the unpushed-commit guard, the
# shared-reference loads, or the enhance/overwrite re-run routing.
require_tokens skills/handoff/SKILL.md \
  'docs/handoffs/' \
  '[REDACTED:' \
  '@{upstream}..HEAD' \
  'origin/HEAD..HEAD' \
  '## Goal' \
  '## Current state' \
  '## Next steps' \
  '## Relevant files & artifacts' \
  '### Inlined (not yet on remote)' \
  '## History' \
  '## Handoff document template' \
  '## Redaction patterns' \
  'multi-repo-detection.md' \
  'Enhance' \
  'Overwrite' \
  'Continue one' \
  'Create new'

# Brainstorm self-review reaches scenario-style.md by section name. A silent
# rename of either heading leaves the self-review pointer dangling.
require_pattern skills/brainstorm/references/scenario-style.md '^## Discipline' '^## Anti-patterns'

check "Producer/consumer contracts intact" test -z "$contract_errors"
if [ -n "$contract_errors" ]; then
  printf "       Contract issues:\n%b" "$contract_errors"
fi

# --- Summary ---
echo
echo "=== Results: $pass passed, $errors failed ==="
if [ "$errors" -gt 0 ]; then exit 1; else exit 0; fi
