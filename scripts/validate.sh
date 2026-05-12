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

# --- 7. No hardcoded /tmp in SKILL.md ---
echo "[Portability]"
tmp_hits=$(grep -rn 'mktemp /tmp/' skills/*/SKILL.md 2>/dev/null || true)
check "No hardcoded mktemp /tmp/ in skills" test -z "$tmp_hits"
if [ -n "$tmp_hits" ]; then
  printf "       Hardcoded /tmp:\n%s\n" "$tmp_hits"
fi

# --- 8. Cross-reference integrity ---
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

# --- 16. Reference depth check (max 2 levels from SKILL.md) ---
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

# --- 17. Load-bearing wiring assertions ---
# Textual section references and cross-skill reference-file wiring that the
# generic cross-reference check (check 8) does not cover. A failure here means
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
# Trigger-key contract (continued): the 'Triggered:' key must literally appear
# inside the detector's Unsupported-Stack Fallback return-format section. SKILL.md
# greps for "Unsupported-Stack Fallback → Triggered: yes" — if a future edit renames
# Triggered: to Fired: or similar, the heading check above would still pass while
# the fallback silently never fires. Scope the search to the section body.
if [ -f skills/how-to-run/agents/project-environment-detector.md ]; then
  usf_body=$(awk '/^### Unsupported-Stack Fallback/{f=1;next}/^### /{f=0}f' skills/how-to-run/agents/project-environment-detector.md 2>/dev/null)
  if ! printf '%s' "$usf_body" | grep -qF 'Triggered:' 2>/dev/null; then
    wiring_errors+="  skills/how-to-run/agents/project-environment-detector.md Unsupported-Stack Fallback section missing 'Triggered:' key\n"
  fi
fi

# The 'Additional Detection Hints' heading in how-to-run-sections.md is referenced
# by name from SKILL.md, README.md, and the detector agent. A rename would
# silently break all three without the generic cross-ref check catching it.
if ! grep -q '^## Additional Detection Hints' "$sections_file" 2>/dev/null; then
  wiring_errors+="  $sections_file missing '## Additional Detection Hints' heading\n"
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
  for token in 'CMakeLists.txt' 'meson.build' 'BUILD.bazel' 'WORKSPACE' '*.sln' '*.vcxproj' '*.xcodeproj' '*.xcworkspace' 'build.gradle' 'settings.gradle' 'AndroidManifest.xml' 'compileSdkVersion' '*.uproject' 'ProjectSettings/ProjectVersion.txt' 'project.godot' 'platformio.ini' '*.ino' 'Package.swift' 'Podfile' 'Makefile'; do
    if ! printf '%s' "$bsd_body" | grep -qF "$token" 2>/dev/null; then
      wiring_errors+="  Build System Detection table body missing row for: $token\n"
    fi
  done
fi

# Load-bearing headings in external-services-docker.md: SKILL.md Step 4 and
# Step 6 reach these sections by name, and the Decision Heuristics link the
# snippet-template H3s by anchor. A silent rename breaks the entire
# Docker-suggestion path.
esd_file="skills/how-to-run/references/external-services-docker.md"
if [ -f "$esd_file" ]; then
  for heading in \
    '^## Service Classification Tables' \
    '^## Decision Heuristics' \
    '^## Web-Search Recipe' \
    '^## Verify Commands \(seeds\)' \
    '^## Pre-Conditions Block' \
    '^### Trigger' \
    '^### Block format' \
    '^### Substitution' \
    '^### Step 6 audit' \
    '^## Citation Format' \
    '^## Registry Allowlist' \
    '^### Docker-preferred' \
    '^### Local install only'; do
    if ! grep -qE "$heading" "$esd_file" 2>/dev/null; then
      wiring_errors+="  $esd_file missing heading matching: $heading\n"
    fi
  done
  for esd_token in \
    '### Shared-cloud primary (Docker optional)' \
    '### Shared-cloud, no Docker alternative' \
    '### Known Vendor Emulators' \
    '## Vendor-Service → Emulator Index' \
    '**PowerShell caveat (Windows host).**' \
    '**GUI-client connect note.**' \
    'SQLCMDPASSWORD' \
    'MYSQL_PWD' \
    '--authenticationDatabase admin' \
    'MONGO_INITDB_ROOT_USERNAME' \
    'Stale-tag re-validation' \
    '^[A-Za-z_][A-Za-z0-9_.:-]{0,127}$' \
    '**Pre-condition — update before running Setup or starting the backend.**' \
    '^([0-9]{4}-)?(latest|stable|edge|nightly|canary|main|current|rolling)$' \
    'pg_isready -U postgres' \
    'redis-cli ping' \
    '/opt/mssql-tools18/bin/sqlcmd' \
    'mongosh' \
    'mysqladmin -u root ping' \
    'SSMS' \
    'pgAdmin' \
    '- Connection details for' \
    'the block subsumes it'; do
    if ! grep -qF -- "$esd_token" "$esd_file" 2>/dev/null; then
      wiring_errors+="  $esd_file missing wiring token: $esd_token\n"
    fi
  done
fi

# Return-format heading contracts: SKILL.md consumes the detector's
# "## Context Detection Results" and the auditor's "## How-to-Run Audit Results"
# headings by name. A rename silently drops all findings from the context summary.
if ! grep -q '^## Context Detection Results' skills/how-to-run/agents/project-environment-detector.md 2>/dev/null; then
  wiring_errors+="  skills/how-to-run/agents/project-environment-detector.md missing '## Context Detection Results' return-format heading\n"
fi
if ! grep -q '^## How-to-Run Audit Results' skills/how-to-run/agents/how-to-run-auditor.md 2>/dev/null; then
  wiring_errors+="  skills/how-to-run/agents/how-to-run-auditor.md missing '## How-to-Run Audit Results' return-format heading\n"
fi

# Detector return-format sub-headings and column contracts added by the
# framework-config detection feature. SKILL.md Step 1 / Step 4 branch on
# these exact strings; a silent rename would collapse service coverage,
# drop schema-bootstrap rendering, or hide the (candidate) marker.
detector_file="skills/how-to-run/agents/project-environment-detector.md"
if [ -f "$detector_file" ]; then
  for detector_heading in \
    '### Recommended Developer Tools' \
    '### External Services' \
    '### Environment Setup' \
    '### Schema Bootstrap' \
    '### Runtime Ports' \
    '### Components'; do
    if ! grep -qF "$detector_heading" "$detector_file" 2>/dev/null; then
      wiring_errors+="  $detector_file missing sub-heading: $detector_heading\n"
    fi
  done
  for detector_token in \
    '| Confidence |' \
    '| Format |' \
    '| Invocation hint |' \
    '| Endpoint semantics |' \
    '| Bootstrap mechanism |' \
    '`local-windows-auth`' \
    '`local-named-instance`' \
    '`local-socket`' \
    '`local-default`' \
    '`remote`' \
    '`ambiguous`' \
    '`docker-compose`' \
    '`raw-sql`' \
    '`seed-script`' \
    '`fixture-load`' \
    '`confirmed`' \
    '`candidate`' \
    'Format: dotenv' \
    '#### Task 5c' \
    '#### Task 5d' \
    'No bound runtime ports detected.' \
    'No runnable components detected.' \
    '| Requires (services) | Requires (components) |' \
    'Integrated Security=(True|Yes|SSPI)' \
    'Trusted_Connection=(Yes|True|1)' \
    'mongodb://%2Ftmp%2F' \
    'mongodb+unix://' \
    '\(local\)\\[A-Za-z0-9_-]+'; do
    if ! grep -qF "$detector_token" "$detector_file" 2>/dev/null; then
      wiring_errors+="  $detector_file missing return-format token: $detector_token\n"
    fi
  done
fi

# Component-layout wiring in how-to-run-sections.md. Silent rename of
# any token below would collapse the rendered layout to a
# single-component or H4-per-component shape and lose worker/scheduler
# documentation.
if [ -f "$sections_file" ]; then
  for sections_token in \
    '**Boot order:**' \
    '**Component count → layout.**' \
    'Compact multi-component layout' \
    '**Flat layout (1-2 components).**' \
    'Components table (Task 5d)' \
    'Runtime Ports table (Task 5c)' \
    '## Workspace-Kind Command Branches' \
    '`npm-workspaces`' \
    '`pnpm-workspaces`' \
    '`yarn-workspaces`' \
    '`lerna`' \
    '`nx`' \
    '`turbo`' \
    '`cargo-workspace`' \
    '`go-workspace`' \
    '`gradle-multi-module`' \
    '`maven-multi-module`' \
    '#### Quick start (Dev Container)' \
    '**One-shot setup (preferred):**' \
    '**Manual setup:**' \
    '**All-candidate compression.**' \
    '**Per-service "Update `<key>` in `<config file>`" consolidation.**' \
    '## Source Dependencies / Clone All' \
    '## Running Everything' \
    '## Schema Bootstrap' \
    '### Pick-one rule' \
    '### Connection-mode-aware invocation' \
    '## Section Depends-On Graph' \
    '## Diagnostic Ladders' \
    '## Environment Setup' \
    '**Alternative bootstrap script:**' \
    'PGPASSWORD' \
    'alembic upgrade head' \
    'npx prisma migrate deploy' \
    'dotnet ef database update' \
    'bundle exec rails db:migrate' \
    'mix ecto.migrate' \
    'flyway migrate' \
    'liquibase update' \
    'npx knex migrate:latest' \
    'npx sequelize db:migrate' \
    'npm run typeorm migration:run' \
    'AutoMigrate function — there is no separate migrate command' \
    '### Container running but host can'"'"'t connect' \
    'Default skeleton — multi-configuration build systems' \
    'Single-configuration skeleton — Cargo / Go / single-output build systems' \
    '| 3-5 |' \
    '| 6+ |' \
    '| Subproject | Path | Dev command | URL / port |'; do
    if ! grep -qF -- "$sections_token" "$sections_file" 2>/dev/null; then
      wiring_errors+="  $sections_file missing component-layout wiring token: $sections_token\n"
    fi
  done
fi

# Dev Workflow Signals fields (setup scripts, pre-commit, direnv, mkcert).
# Detector emits these signal rows; main skill templates branch on them to
# render one-shot setup / quick start / prereq notes. A silent field rename
# would drop the entire branch.
if [ -f "$detector_file" ]; then
  for dws_token in \
    '- **Setup scripts:**' \
    '- **Pre-commit hooks:**' \
    '- **direnv:**' \
    '- **Local TLS cert:**' \
    '- **Database migrations:**'; do
    if ! grep -qF -- "$dws_token" "$detector_file" 2>/dev/null; then
      wiring_errors+="  $detector_file missing Dev Workflow Signals field: $dws_token\n"
    fi
  done
fi

# Env-Setup key-leafs / secrets-committed wiring: leaf-property + secrets
# columns in the detector's Environment Setup table, Verify: guidance in
# how-to-run-sections.md, and the committed-secrets Caution block.
if [ -f "$detector_file" ]; then
  for env_setup_token in \
    '| Key leaves |' \
    '| Secrets committed |'; do
    if ! grep -qF -- "$env_setup_token" "$detector_file" 2>/dev/null; then
      wiring_errors+="  $detector_file missing Env-Setup key-leaves/secrets column: $env_setup_token\n"
    fi
  done
fi
if [ -f "$sections_file" ]; then
  for env_setup_token in \
    'Keys you will edit:' \
    '**Optional `Verify:` line.**' \
    'appears to contain live credentials'; do
    if ! grep -qF -- "$env_setup_token" "$sections_file" 2>/dev/null; then
      wiring_errors+="  $sections_file missing Env-Setup key-leaves/secrets token: $env_setup_token\n"
    fi
  done
fi

# Specific-Token Audit + Unverified-Count filter wiring in SKILL.md.
# Step 6 relies on these tokens to run the audit passes that catch
# hallucinated ports/paths/counts (port 5000 vs actual 51914, unverified
# "15 .csproj projects" prose, etc.). Step 4 Content Principles must cite
# the same rules so the two steps stay in sync.
how_to_run_skill="skills/how-to-run/SKILL.md"
if [ -f "$how_to_run_skill" ]; then
  for token in \
    'Specific-Token Audit' \
    'Unverified-Count filter' \
    'Never assert an unobserved path' \
    'Never guess runtime ports' \
    'grounded-tokens' \
    'Runtime Ports table' \
    'Section ordering audit' \
    'Pre-Conditions Block audit' \
    'Reconcile rendered commands against project script runners' \
    '**Verify bullets:**' \
    '**Diagnostic ladders:**' \
    'Stale-tag re-validation'; do
    if ! grep -qF "$token" "$how_to_run_skill" 2>/dev/null; then
      wiring_errors+="  $how_to_run_skill missing token-audit wiring token: $token\n"
    fi
  done
fi

# Workspace-kind wiring in detector.md. Detector must emit the Workspace kind
# field that SKILL.md Step 1 Checkpoint and Step 4 branch on. Silent rename
# loses the per-kind command branching.
wk_token='- **Workspace kind:**'
if [ -f "$detector_file" ] && ! grep -qF -- "$wk_token" "$detector_file" 2>/dev/null; then
  wiring_errors+="  $detector_file missing Workspace kind field: $wk_token\n"
fi

# Version-manager file wiring in detector.md. These are the authoritative
# runtime pins when the manifest is silent. Silent removal of any filename
# would drop support for that language's pyenv/nvm/asdf flow.
if [ -f "$detector_file" ]; then
  for vm_token in \
    '.python-version' \
    '.ruby-version' \
    '.nvmrc' \
    '.node-version' \
    '.java-version' \
    'rust-toolchain.toml' \
    '.tool-versions' \
    'recommended pin'; do
    if ! grep -qF -- "$vm_token" "$detector_file" 2>/dev/null; then
      wiring_errors+="  $detector_file missing version-manager token: $vm_token\n"
    fi
  done
fi
# Template-shape audit + Content Principle anchors in SKILL.md.
# A silent rename of any of these would let the corresponding
# layout/audit regression slip through unnoticed.
if [ -f "$how_to_run_skill" ]; then
  for shape_token in \
    'Template-shape audit' \
    'Render once, not twice.' \
    'all-candidate compression' \
    'Compact multi-component layout' \
    '`Verify:` permitted only' \
    'OS-version line in Prerequisites' \
    'Build Debug+Release pair' \
    'Running-in-Development layout vs Components-table row count' \
    'Detector-internal fields' \
    'Workspace-aware commands.' \
    'count is 7 or more' \
    '## Contents'; do
    if ! grep -qF -- "$shape_token" "$how_to_run_skill" 2>/dev/null; then
      wiring_errors+="  $how_to_run_skill missing template-shape wiring token: $shape_token\n"
    fi
  done
fi

# Unit-test deep-mode wiring: the Deep mode loop in skills/unit-test/SKILL.md
# depends on exact-string status values, stop messages, and state variable names.
# A silent rename (e.g., "bug-found" -> "bug_found") would leave the termination
# conditions unmatched, the cumulative report mis-classified, or the analyzer's
# iteration-context block lying — with no other check catching it.
unit_test_skill="skills/unit-test/SKILL.md"
for token in \
  'accumulated-items' \
  'accumulated-untestable' \
  'accumulated-bugs' \
  'iteration-count' \
  'total-added' \
  'total-reverted' \
  'accumulated-coverage-delta' \
  '`pass`' \
  '`reverted — test failure`' \
  '`bug-found`' \
  '`abandoned`' \
  'Deep mode complete — converged on iteration' \
  'Deep mode stopped — all tests added in iteration' \
  'Deep mode stopped — coverage plateau on iteration' \
  'Deep mode reached the iteration cap'; do
  if ! grep -qF "$token" "$unit_test_skill" 2>/dev/null; then
    wiring_errors+="  $unit_test_skill missing deep-mode wiring token: $token\n"
  fi
done

# Brainstorm/TDD scenario contract: TDD's Step 3 scenario-driven shortcut greps
# for the literal '## Scenarios' and '### Scenario:' strings in design docs that
# brainstorm produces from the design-doc-format template. A silent rename of
# either heading on either side would cause TDD's shortcut to never fire — the
# user would silently fall back to the generic decomposition path with no error.
brainstorm_template="skills/brainstorm/references/design-doc-format.md"
tdd_skill="skills/tdd/SKILL.md"
if [ -f "$brainstorm_template" ]; then
  for scenario_token in '## Scenarios' '### Scenario:'; do
    if ! grep -qF -- "$scenario_token" "$brainstorm_template" 2>/dev/null; then
      wiring_errors+="  $brainstorm_template missing scenario contract token: $scenario_token\n"
    fi
  done
fi
if [ -f "$tdd_skill" ]; then
  for scenario_token in '## Scenarios' '### Scenario:'; do
    if ! grep -qF -- "$scenario_token" "$tdd_skill" 2>/dev/null; then
      wiring_errors+="  $tdd_skill missing scenario contract token: $scenario_token\n"
    fi
  done
fi

# Brainstorm self-review reaches scenario-style.md by section name. Silent
# rename of either heading would leave the self-review pointer dangling.
scenario_style="skills/brainstorm/references/scenario-style.md"
if [ -f "$scenario_style" ]; then
  for scenario_style_heading in '^## Discipline' '^## Anti-patterns'; do
    if ! grep -qE "$scenario_style_heading" "$scenario_style" 2>/dev/null; then
      wiring_errors+="  $scenario_style missing heading matching: $scenario_style_heading\n"
    fi
  done
fi

# Trigger-key contract for the walkthrough branch added by the guided
# walkthrough feature. SKILL.md Step 3 routes on the literal "Walk through it"
# AskUserQuestion option string and jumps to the "## Step 3a" heading; Step 3a
# loads guided-walkthrough.md by path. The walkthrough's own "Stop the
# walkthrough" exit string is referenced from SKILL.md Step 3a. If any of these
# strings drifts, the entire branch silently dies — the generic cross-ref
# check (check 8) only validates path resolution, not these textual contracts.
walkthrough_ref="skills/how-to-run/references/guided-walkthrough.md"
auditor_agent="skills/how-to-run/agents/how-to-run-auditor.md"
# Audit verdict list — producer/consumer contract between Step 2 auditor
# agent (producer) and the walkthrough's per-step Audit: prefix (consumer).
# Applied to each side independently below.
audit_verdicts=('Found & accurate' 'Found but outdated' 'Partial' 'Documented but unverifiable' 'Missing')
# Assert file presence as first-class checks (not `if [ -f ]` guards) so a
# rename or deletion fails the build instead of silently skipping the
# downstream wiring loops.
check "how-to-run SKILL.md present" test -f "$how_to_run_skill"
check "how-to-run guided-walkthrough.md present" test -f "$walkthrough_ref"
check "how-to-run auditor agent present" test -f "$auditor_agent"
# Heading anchor uses regex; literal triggers use fixed-string match so a
# typo like 'guided-walkthroughxmd' (where . matches any char in regex mode)
# cannot satisfy the wiring contract.
if ! grep -qE '^## Step 3a:' "$how_to_run_skill" 2>/dev/null; then
  wiring_errors+="  $how_to_run_skill missing walkthrough heading: ^## Step 3a:\n"
fi
# Step 6 is the jump target for Step 3 Skip and Step 3a completion; ensure
# the heading exists. The textual 'jump to Step 6' references are validated
# below in the control-flow phrases loop.
if ! grep -qE '^## Step 6\b' "$how_to_run_skill" 2>/dev/null; then
  wiring_errors+="  $how_to_run_skill missing jump target: ^## Step 6\n"
fi
# Step 3 option labels — silent rename without matching update in the
# per-answer routing block would silently send the user down the wrong
# branch. '**Skip**' uses bold form because bare 'Skip' would also match
# 'skipped' / 'Skip the prompt' in unrelated prose elsewhere in SKILL.md.
for option_label in 'Walk through it' 'Regenerate' '**Skip**'; do
  if ! grep -qF "$option_label" "$how_to_run_skill" 2>/dev/null; then
    wiring_errors+="  $how_to_run_skill missing Step 3 option label: $option_label\n"
  fi
done
# Control-flow phrases — exit strings and cross-step jump targets. A silent
# rename here dangles the SKILL→walkthrough→SKILL handoff.
for control_phrase in 'Stop the walkthrough' 'jump to Step 3a' 'jump to Step 6'; do
  if ! grep -qF "$control_phrase" "$how_to_run_skill" 2>/dev/null; then
    wiring_errors+="  $how_to_run_skill missing control-flow phrase: $control_phrase\n"
  fi
done
# Discoverability strings — the AskUserQuestion header that the user sees,
# the reference file path SKILL.md loads, and the frontmatter phrase that
# surfaces this option in skill descriptions.
for discoverability_string in 'guided-walkthrough.md' 'guided in-chat walkthrough' 'How to Run Documentation'; do
  if ! grep -qF "$discoverability_string" "$how_to_run_skill" 2>/dev/null; then
    wiring_errors+="  $how_to_run_skill missing discoverability string: $discoverability_string\n"
  fi
done
for heading in '^## Pre-flight' '^## Per-step loop' '^## Advisory flags' '^## Display sanitization' '^## Heavy-staleness handling' '^## Completion summary' '^## What this walkthrough never modifies'; do
  if ! grep -qE "$heading" "$walkthrough_ref" 2>/dev/null; then
    wiring_errors+="  $walkthrough_ref missing heading matching: $heading\n"
  fi
done
# Option labels — the per-step loop renders these via AskUserQuestion.
# Silent rename desyncs the rendered options from the SKILL.md routing
# contract (Step 3a jumps back to Step 6 on "Stop the walkthrough").
for option_label in '"Done"' '"Skip"' '"Stop the walkthrough"'; do
  if ! grep -qF "$option_label" "$walkthrough_ref" 2>/dev/null; then
    wiring_errors+="  $walkthrough_ref missing option label: $option_label\n"
  fi
done
# Advisory prepends in the walkthrough — silent rename drops the warning
# surface the user sees before each per-step prompt.
for advisory_string in 'Remote code executor' 'Destructive command'; do
  if ! grep -qF "$advisory_string" "$walkthrough_ref" 2>/dev/null; then
    wiring_errors+="  $walkthrough_ref missing advisory string: $advisory_string\n"
  fi
done
# Control-flow / exit strings — 'SKILL.md Step 6' is the post-walkthrough
# jump target, '**Regenerate**' is the recovery recommendation. Silent
# rename dangles the SKILL→walkthrough→SKILL handoff or the recovery
# cross-reference. ('Stop the walkthrough' is covered by the option_label
# loop above — the quoted form there is a strict superset of the bare form.)
for control_phrase in 'SKILL.md Step 6' '**Regenerate**'; do
  if ! grep -qF "$control_phrase" "$walkthrough_ref" 2>/dev/null; then
    wiring_errors+="  $walkthrough_ref missing control-flow phrase: $control_phrase\n"
  fi
done
# Per-step audit-verdict prefix — the literal label ('Audit:') that ties
# the rendered verdict to its auditor source. A silent rename to 'Verdict:'
# or 'Status:' would still pass the verdict-string check below but would
# disconnect the rendered prefix from the audit surface.
if ! grep -qF 'Audit:' "$walkthrough_ref" 2>/dev/null; then
  wiring_errors+="  $walkthrough_ref missing audit-verdict prefix: Audit:\n"
fi
for verdict in "${audit_verdicts[@]}"; do
  if ! grep -qF "$verdict" "$walkthrough_ref" 2>/dev/null; then
    wiring_errors+="  $walkthrough_ref missing audit verdict: $verdict\n"
  fi
  if ! grep -qF "$verdict" "$auditor_agent" 2>/dev/null; then
    wiring_errors+="  $auditor_agent missing audit verdict: $verdict\n"
  fi
done
# Cross-file return-format header — auditor agent emits this section header
# and SKILL.md Steps 2/3 consume it by name. A silent rename in either file
# would break the Step 2 → Step 3 handoff that feeds the walkthrough's audit
# verdict surfaces.
if ! grep -qF 'How-to-Run Audit Results' "$auditor_agent" 2>/dev/null; then
  wiring_errors+="  $auditor_agent missing return-format header: How-to-Run Audit Results\n"
fi
if ! grep -qF 'How-to-Run Audit Results' "$how_to_run_skill" 2>/dev/null; then
  wiring_errors+="  $how_to_run_skill missing return-format consumer: How-to-Run Audit Results\n"
fi
# Cross-step identifiers within SKILL.md — these list/field names are
# referenced from multiple Steps (3 record, 4 populate, 6 exempt); a silent
# rename in only one location would silently disable the cross-step contract
# (e.g., Step 6 would reject legitimately approved unverifiable items).
# Threshold = current occurrence count; one location renamed = check fails.
# `|| true` lets the count=0 case reach the threshold comparison instead
# of aborting the script under `set -euo pipefail` — count=0 is exactly
# the failure mode this check is designed to catch.
check_cross_step_identifier() {
  local identifier=$1 expected=$2 file=$3
  local actual
  actual=$(grep -cF "$identifier" "$file" 2>/dev/null || true)
  [ -z "$actual" ] && actual=0
  if [ "$actual" -lt "$expected" ]; then
    wiring_errors+="  $file cross-step identifier '$identifier' appears $actual times, expected >=$expected\n"
  fi
}
check_cross_step_identifier 'approved-unverifiable-items' 4 "$how_to_run_skill"
check_cross_step_identifier 'rendered_line' 3 "$how_to_run_skill"
# Stale-info report identifiers — Step 4/5 prose references the Step 6
# "Outdated info" report by name; a silent rename of either side breaks
# the path from principle to report. Each side is checked independently
# so the failure message identifies which surface drifted.
if ! grep -qF 'Outdated info found in other files' "$how_to_run_skill" 2>/dev/null; then
  wiring_errors+="  $how_to_run_skill missing Step 6 stale-info report heading: Outdated info found in other files\n"
fi
if ! grep -qF 'Outdated info elsewhere' "$how_to_run_skill" 2>/dev/null; then
  wiring_errors+="  $how_to_run_skill missing Step 4/5 cross-reference to stale-info report: Outdated info elsewhere\n"
fi

check "Load-bearing wiring intact" test -z "$wiring_errors"
if [ -n "$wiring_errors" ]; then
  printf "       Wiring issues:\n%b" "$wiring_errors"
fi

# --- Summary ---
echo
echo "=== Results: $pass passed, $errors failed ==="
if [ "$errors" -gt 0 ]; then exit 1; else exit 0; fi
