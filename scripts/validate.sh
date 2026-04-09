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

# --- 7. Cross-reference integrity ---
# Every $CLAUDE_PLUGIN_ROOT/... path in skill files must point to an existing file.
echo "[Cross-references]"
broken_refs=""
while IFS= read -r ref_line; do
  # Extract the path after $CLAUDE_PLUGIN_ROOT/ or ${CLAUDE_PLUGIN_ROOT}/
  # Paths appear inside backticks, quotes, or bare — extract until whitespace/backtick/quote
  ref_path=$(printf '%s' "$ref_line" | sed -n 's|.*\$[{]\{0,1\}CLAUDE_PLUGIN_ROOT[}]\{0,1\}/\([^ `"'"'"']*\).*|\1|p' | head -1)
  if [ -n "$ref_path" ] && [ ! -f "./$ref_path" ] && [ ! -d "./$ref_path" ]; then
    # Get source file for context
    src_file=$(printf '%s' "$ref_line" | cut -d: -f1)
    broken_refs+="  $src_file -> $ref_path\n"
  fi
done < <(grep -rn '\$[{]\{0,1\}CLAUDE_PLUGIN_ROOT[}]\{0,1\}/' skills/ references/ 2>/dev/null || true)
check "All CLAUDE_PLUGIN_ROOT references resolve" test -z "$broken_refs"
if [ -n "$broken_refs" ]; then
  printf "       Broken references:\n%b" "$broken_refs"
fi

# --- 8. Orphan detection ---
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
  # 3. By parent directory reference (e.g., templates/hooks/ covers all files inside)
  parent_dir=$(dirname "$rel_path")
  if ! grep -rq "$rel_path" skills/ 2>/dev/null && \
     ! grep -rq "$basename_f" skills/ 2>/dev/null && \
     ! grep -rq "$parent_dir/" skills/ 2>/dev/null; then
    orphan_files+="  $rel_path\n"
  fi
done < <(( find ./skills -path '*/references/*' -o -path '*/templates/*' -o -path '*/agents/*'; find ./references ./agents -type f 2>/dev/null ) | grep -v '/__' | sort)
check "No orphaned reference/template/agent files" test -z "$orphan_files"
if [ -n "$orphan_files" ]; then
  printf "       Unreferenced files:\n%b" "$orphan_files"
fi

# --- 9. Template script syntax ---
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

# --- 10. JSON template validity ---
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

# --- 11. Skill directory completeness ---
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

# --- 12. README skill list vs actual skills/ directories ---
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
check "README lists all skills" test -z "$readme_mismatch"
if [ -n "$readme_mismatch" ]; then
  printf "       Missing from README:\n%b" "$readme_mismatch"
fi

# --- 13. hooks.json validity ---
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

# --- 14. Plugin-level agents ---
echo "[Plugin agents]"
agent_issues=""
for agent_file in agents/code-simplifier.md agents/test-guardian.md; do
  if [ ! -f "$agent_file" ]; then
    agent_issues+="  $agent_file: missing\n"
  else
    # Check frontmatter has tools: field
    if ! grep -q '^tools:' "$agent_file" 2>/dev/null; then
      agent_issues+="  $agent_file: missing 'tools:' in frontmatter\n"
    fi
    if ! grep -q '^name:' "$agent_file" 2>/dev/null; then
      agent_issues+="  $agent_file: missing 'name:' in frontmatter\n"
    fi
  fi
done
# Check that old template agents directory does NOT exist
if [ -d "skills/init/templates/agents" ] && [ "$(ls -A skills/init/templates/agents 2>/dev/null)" ]; then
  agent_issues+="  skills/init/templates/agents/ still contains files (should be moved to agents/)\n"
fi
check "Plugin-level agents valid" test -z "$agent_issues"
if [ -n "$agent_issues" ]; then
  printf "       Issues:\n%b" "$agent_issues"
fi

# --- 15. Reference depth check (max 2 levels from SKILL.md) ---
echo "[Reference depth]"
deep_refs=""
# For each reference file that is loaded by a SKILL.md, check if it loads further
# references that themselves load more (3+ levels deep)
while IFS= read -r ref_file; do
  # This is a level-1 reference (loaded by SKILL.md). Check what it references.
  while IFS= read -r l2_line; do
    l2_path=$(printf '%s' "$l2_line" | sed -n 's|.*\$[{]\{0,1\}CLAUDE_PLUGIN_ROOT[}]\{0,1\}/\([^ `"'"'"']*\).*|\1|p' | head -1)
    if [ -z "$l2_path" ] || [ ! -f "./$l2_path" ]; then
      continue
    fi
    # This is a level-2 reference. Check if IT references more files (level-3 = too deep)
    # Exclude references to top-level agents/ and references/ — these are leaf files (role definitions, shared constraints)
    has_deep=$(grep '\$[{]\{0,1\}CLAUDE_PLUGIN_ROOT[}]\{0,1\}/' "./$l2_path" 2>/dev/null | grep -v '\$[{]\{0,1\}CLAUDE_PLUGIN_ROOT[}]\{0,1\}/agents/' | grep -v '\$[{]\{0,1\}CLAUDE_PLUGIN_ROOT[}]\{0,1\}/references/' || true)
    if [ -n "$has_deep" ]; then
      deep_refs+="  $ref_file -> $l2_path -> (further refs)\n"
    fi
  done < <(grep '\$[{]\{0,1\}CLAUDE_PLUGIN_ROOT[}]\{0,1\}/' "./$ref_file" 2>/dev/null || true)
done < <(find ./skills -path '*/references/*.md' -o -path '*/agents/*.md' | sort)
check "Reference depth <= 2 levels" test -z "$deep_refs"
if [ -n "$deep_refs" ]; then
  printf "       Deep reference chains (3+ levels):\n%b" "$deep_refs"
fi

# --- 16. Load-bearing wiring assertions ---
# Textual section references and cross-skill reference-file wiring that the
# generic cross-reference check (check 7) does not cover. A failure here means
# a silent regression in how a skill reaches a capability it depends on.
echo "[Load-bearing wiring]"
wiring_errors=""

sections_file="skills/how-to-run/references/how-to-run-sections.md"

# how-to-run must wire to the unsupported-stack fallback procedure from the main
# SKILL context — the detector agent is read-only and cannot run it. Dropping
# this reference silently loses unknown-stack support.
if ! grep -q 'unsupported-stack-fallback.md' skills/how-to-run/SKILL.md 2>/dev/null; then
  wiring_errors+="  skills/how-to-run/SKILL.md no longer references unsupported-stack-fallback.md\n"
fi

# Trigger-key contract: SKILL.md checks the literal string
# "Unsupported-Stack Fallback → Triggered: yes" to decide whether to run the
# 5-step fallback, and the detector agent emits that key under a matching
# heading in its return format. If either side drifts, the fallback silently
# never fires.
if ! grep -q 'Unsupported-Stack Fallback → Triggered: yes' skills/how-to-run/SKILL.md 2>/dev/null; then
  wiring_errors+="  skills/how-to-run/SKILL.md no longer checks 'Unsupported-Stack Fallback → Triggered: yes' trigger key\n"
fi
if ! grep -q '^### Unsupported-Stack Fallback' skills/how-to-run/agents/project-environment-detector.md 2>/dev/null; then
  wiring_errors+="  skills/how-to-run/agents/project-environment-detector.md missing '### Unsupported-Stack Fallback' return-format heading\n"
fi

# The 'Extended Stacks Covered' heading in how-to-run-sections.md is referenced
# by name from SKILL.md, README.md, and the detector agent. A rename would
# silently break all three without the generic cross-ref check catching it.
if ! grep -q '^## Extended Stacks Covered' "$sections_file" 2>/dev/null; then
  wiring_errors+="  $sections_file missing '## Extended Stacks Covered' heading\n"
fi
# The 'Build System Detection' heading is load-bearing for Task 0a of the
# detector agent, which delegates its entire build-file enumeration to the table.
if ! grep -q '^## Build System Detection' "$sections_file" 2>/dev/null; then
  wiring_errors+="  $sections_file missing '## Build System Detection' heading\n"
fi

# Build System Detection table rows that the detector agent depends on. Before
# the consolidation the agent had these signals inlined in its own Task 0a list.
# Now Task 0a delegates entirely to this table, so a silent row deletion during
# a table cleanup would drop a detection signal the agent used to guarantee.
# Scope the grep to the "## Build System Detection" section body so incidental
# mentions elsewhere in the file (Signal → Section Mapping, Toolchain & SDKs)
# cannot satisfy the check. Each token must appear in the table body.
if [ -f "$sections_file" ]; then
  bsd_body=$(awk '/^## Build System Detection/{f=1;next}/^## /{f=0}f' "$sections_file" 2>/dev/null)
  for token in 'CMakeLists.txt' 'meson.build' 'BUILD.bazel' 'WORKSPACE' '\*.sln' '\*.vcxproj' '\*.xcodeproj' '\*.xcworkspace' 'build.gradle' 'settings.gradle' 'AndroidManifest.xml' 'compileSdkVersion' '\*.uproject' 'ProjectVersion.txt' 'project.godot' 'platformio.ini' '\*.ino' 'Package.swift' 'Podfile' 'Makefile'; do
    if ! printf '%s' "$bsd_body" | grep -q "$token" 2>/dev/null; then
      wiring_errors+="  Build System Detection table body missing row for: $token\n"
    fi
  done
fi

check "Load-bearing wiring intact" test -z "$wiring_errors"
if [ -n "$wiring_errors" ]; then
  printf "       Wiring issues:\n%b" "$wiring_errors"
fi

# --- Summary ---
echo
echo "=== Results: $pass passed, $errors failed ==="
if [ "$errors" -gt 0 ]; then exit 1; else exit 0; fi
