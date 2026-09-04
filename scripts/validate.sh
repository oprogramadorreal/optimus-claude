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
  # Read the blob whole and slice in bash rather than piping to `head -1`. With
  # `set -o pipefail`, `head` exiting after one line leaves git writing into a
  # closed pipe, so any blob larger than the pipe buffer (~64K) made the
  # PIPELINE fail — `git cat-file` returned 128 — and `set -e` aborted the whole
  # run at THIS check, silently skipping every section below. It only surfaced
  # once test-hooks.sh and restrict-paths.sh grew past 64K.
  blob=$(git cat-file -p "HEAD:$f" 2>/dev/null || true)
  first_line=${blob%%$'\n'*}
  first_line=${first_line%$'\r'}
  if [[ "$first_line" == "#!/bin/bash"* ]]; then
    bad_shebangs+="  $f"$'\n'
  fi
done < <(git ls-files -- '*.sh' 'hooks/session-start')
check "All scripts use #!/usr/bin/env bash" test -z "$bad_shebangs"
if [ -n "$bad_shebangs" ]; then
  printf "       Non-portable shebangs:\n%s" "$bad_shebangs"
fi

# --- 3. Parsed skill metadata for both hosts ---
echo "[Skill metadata]"
if metadata_errors=$(python scripts/validate_skill_metadata.py 2>&1); then
  check "Skill YAML is valid and disables implicit invocation on both hosts" true
else
  check "Skill YAML is valid and disables implicit invocation on both hosts" false
  printf '       Requires Python and requirements-dev.txt. Issues:\n%s\n' "$metadata_errors"
fi

# --- 4. No ref in marketplace.json ---
echo "[Manifests]"
check "No ref field in marketplace.json" \
  bash -c '! grep -q "\"ref\"" .claude-plugin/marketplace.json'

# The Codex marketplace mirrors the Claude one. Codex reads
# .agents/plugins/marketplace.json first and installs the plugin from "./",
# then finds .claude-plugin/plugin.json as a legacy manifest — so the plugin
# name there has to be the one plugin.json declares, or Codex installs a
# plugin it cannot find skills for. Read without jq so the pin never SKIPs.
plugin_name=$(sed -n 's/^ *"name": *"\([^"]*\)".*/\1/p' .claude-plugin/plugin.json | head -1)
check "Codex marketplace installs plugin '$plugin_name' from ./" \
  bash -c "grep -q '\"name\": \"$plugin_name\"' .agents/plugins/marketplace.json && grep -q '\"path\": \"./\"' .agents/plugins/marketplace.json"

# --- 4b. Dogfooded hook matches the shipped template ---
# .claude/hooks/restrict-paths.sh is a copy of the template users install, and
# only the template is exercised by scripts/test-hooks.sh. Nothing else pins them
# together, and they have drifted before (commits that hardened the memory-store
# exemption and broadened the precious-file patterns landed in the template
# alone, leaving this repo running stale security logic). A template-only fix
# leaves this repo unprotected; a .claude/-only fix ships nothing to users.
# Guarded like every other optional tool below: a missing cmp must SKIP, not FAIL.
#
# format-python.sh is the same arrangement with the coverage inverted: the
# pytest suite drives the .claude/ copy and scripts/test-hooks.sh drives the
# template, so each is only as good as this pin. It is the one format-* hook
# with logic beyond parse-guard-invoke — it resolves black and isort out of a
# virtualenv — which is exactly where a template-only or .claude/-only fix hurts.
if command -v cmp &>/dev/null; then
  check "restrict-paths hook copies are in sync" \
    cmp -s .claude/hooks/restrict-paths.sh skills/permissions/templates/hooks/restrict-paths.sh
  check "format-python hook copies are in sync" \
    cmp -s .claude/hooks/format-python.sh skills/init/templates/hooks/format-python.sh
else
  echo "  SKIP  hook sync checks (cmp not installed)"
fi

# The hook carries a HOOK_VERSION that the SessionStart hook compares against a
# project's installed copy. A behavioural change that forgets to bump it ships
# silently to everyone who already ran /optimus:permissions.
#
# Pinned to the BANNER — the leading comment block — because that is where
# hooks/session-start stops reading: it scans for the marker with a bounded loop
# rather than sed (the file is 1800+ lines and the scan ran twice per session
# start) and gives up at the first line that is not a comment. A marker below
# that point reads as v0 on both sides and turns the freshness check into a
# silent no-op, which is exactly the failure this check exists to prevent.
# Expressed the same structural way here rather than as a second copy of a line
# count, so the two readers cannot drift apart.
check "restrict-paths template declares a HOOK_VERSION in its banner" \
  bash -c "sed -n '/^[^#]/q;p' skills/permissions/templates/hooks/restrict-paths.sh | grep -qE '^# HOOK_VERSION: [0-9]+'"

# --- 4c. Dogfooded coding-guidelines matches its shipped template ---
# .claude/docs/coding-guidelines.md is this repo's own copy of the file
# /optimus:init writes into user projects; line 1 differs by design (init
# substitutes the project name) and everything after it is verbatim. Nothing
# pinned them, so a rule added for users could silently miss this repo's own
# review passes. skill-writing-guidelines.md is deliberately NOT pinned: this
# repo's copy carries plugin-specific rules (no `name:` frontmatter, the
# two-level reference allowance, the closing-recommendation convention) that
# have no meaning in a user project.
if command -v diff &>/dev/null; then
  check "coding-guidelines.md matches its template below line 1" \
    bash -c "diff -q <(tail -n +2 .claude/docs/coding-guidelines.md) <(tail -n +2 skills/init/templates/docs/coding-guidelines.md) >/dev/null"
else
  echo "  SKIP  coding-guidelines sync check (diff not installed)"
fi

# --- 5. plugin.json validity ---
if command -v jq &>/dev/null; then
  check "plugin.json is valid JSON" jq empty .claude-plugin/plugin.json
  check "plugin.json has name" bash -c 'jq -e ".name" .claude-plugin/plugin.json >/dev/null'
  check "plugin.json has version" bash -c 'jq -e ".version" .claude-plugin/plugin.json >/dev/null'
  check "plugin.json has description" bash -c 'jq -e ".description" .claude-plugin/plugin.json >/dev/null'
  check "Codex marketplace.json is valid JSON" jq empty .agents/plugins/marketplace.json
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
  # Skip README.md files in skill dirs (they're documentation, not referenced by
  # SKILL.md via CLAUDE_PLUGIN_ROOT) and agents/openai.yaml (Codex reads it by
  # location; no skill file names it — section 12 checks its presence instead).
  basename_f=$(basename "$f")
  if [ "$basename_f" = "README.md" ] || [ "$basename_f" = "openai.yaml" ]; then
    continue
  fi
  # Normalize: strip leading ./
  rel_path="${f#./}"
  # Check if this file is referenced in any skill .md file:
  # 1. By full relative path (e.g., skills/init/references/foo.md)
  # 2. By basename only (e.g., format-python.sh in a table or prose)
  # 3. By parent directory reference (e.g., templates/hooks/ covers all files
  #    inside) — skill-level files only. For root references/ and agents/
  #    files this fallback is vacuous (the strings "references/" and "agents/"
  #    match trivially somewhere in skills/), so they must match by full path
  #    or basename.
  case "$rel_path" in
    references/*|agents/*)
      # Root references may be owned by another root reference rather than named
      # in a SKILL.md — the harness schemas are reached through harness-mode.md,
      # which is the single place that describes the output contract. So search
      # references/ too, excluding the candidate itself (a file trivially
      # contains its own basename).
      if ! grep -rq "$rel_path" skills/ 2>/dev/null && \
         ! grep -rq "$basename_f" skills/ 2>/dev/null && \
         ! grep -rq --exclude="$basename_f" "$rel_path" references/ 2>/dev/null && \
         ! grep -rq --exclude="$basename_f" "$basename_f" references/ 2>/dev/null; then
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
    if ! jq empty "$f" 2>/dev/null; then
      json_errors+="  $f: invalid JSON\n"
    fi
  done < <(find ./skills -path '*/templates/*.json' -o -path '*/templates/**/*.json' 2>/dev/null | sort)
  check "JSON templates are valid" test -z "$json_errors"
  if [ -n "$json_errors" ]; then
    printf "       Invalid JSON:\n%b" "$json_errors"
  fi

  # This repo's own settings.json must carry every deny rule the template ships.
  # Same dogfooding gap the restrict-paths and coding-guidelines pins close, and
  # it had already opened: the template narrowed `Bash(*git push --force*)` to a
  # pair that does not swallow `--force-with-lease`, this copy kept the greedy
  # glob, and the repo denied its own /optimus:pr flow. One-directional on
  # purpose — extra project-specific denies here are fine.
  check "settings.json carries every template deny rule" \
    bash -c "jq -e --slurpfile tpl skills/permissions/templates/settings.json '(\$tpl[0].permissions.deny - .permissions.deny) | length == 0' .claude/settings.json >/dev/null"
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
  # Section 3 parses the invocation policy; this section checks the layout.
  if [ ! -f "$skill_dir/agents/openai.yaml" ]; then
    missing_files+="  skills/$skill_name/agents/openai.yaml\n"
  fi
done
check "Every skill has SKILL.md, README.md, and agents/openai.yaml" test -z "$missing_files"
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
    # Check every plugin-relative path the command names, whatever wraps it.
    # SessionStart names its script twice: once for the direct `bash` launch
    # and once inside the git-alias fallback Codex's cmd.exe host needs when
    # bash.exe is not on PATH.
    while IFS= read -r script_path; do
      if [ -n "$script_path" ] && [ ! -f "./$script_path" ]; then
        hook_missing+="  $script_path\n"
      fi
    done < <(printf '%s' "$cmd" | grep -oE '\$\{CLAUDE_PLUGIN_ROOT\}/[^"[:space:]\\]+' | sed 's|^${CLAUDE_PLUGIN_ROOT}/||' | sort -u)
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
# Two assertions, and both are needed. The named list is the only thing that
# checks these files EXIST: replacing it with a bare glob left `agent_count`
# at 1 when one of the two was deleted, so validation stayed green while the
# plugin shipped without its user-invocable optimus:test-guardian subagent and
# skills/init/README.md's relative link 404'd. Nothing else pins them — check 8
# only validates $CLAUDE_PLUGIN_ROOT paths, and check 9 only flags files that
# are already there.
for agent_file in agents/code-simplifier.md agents/test-guardian.md; do
  [ -f "$agent_file" ] || agent_issues+="  $agent_file: missing (required plugin agent)\n"
done
# The glob then validates the CONTENT of every agent, named or not, so a new one
# is checked automatically instead of shipping unvalidated when the list above
# goes stale (skills get the same treatment in section 12 via ./skills/*/).
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
# A pin belongs here only when a rename on one side breaks a handoff that the
# reading model cannot recover by meaning. That is true in exactly two cases:
#   (a) a program parses the string — HARNESS_MODE_INLINE and the harness
#       reference paths are dispatched on by scripts/harness_common/cli.py;
#   (b) the string crosses a conversation boundary through an artifact on disk
#       or an agent return block — one skill writes '## Scenarios' into a spec
#       file that another skill greps weeks later; an agent names the block its
#       dispatcher picks out of a long return.
# Everything else is a model reading prose, and Claude resolves a renamed
# heading by meaning. Pinning the wording of a skill's own instructions makes CI
# the thing that blocks simplifying it — the anti-pattern this plugin's own
# skill-writing guidelines forbid. Regressions in intra-skill routing belong in
# test/, asserted as behaviour, not asserted as wording here.
# Missing files fail first-class — a rename or deletion must break the build.
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
  # `|| true`: an import-time failure in constants.py must surface as a contract
  # FAIL below, not abort the whole run via set -e with no summary printed.
  deep_variant_skills=$(PYTHONPATH=./scripts "$py_cmd" -c "from harness_common.constants import DEEP_VARIANT_SKILLS; print(' '.join(sorted(DEEP_VARIANT_SKILLS)))" 2>/dev/null) || true
  coverage_variant_skills=$(PYTHONPATH=./scripts "$py_cmd" -c "from harness_common.constants import COVERAGE_VARIANT_SKILLS; print(' '.join(sorted(COVERAGE_VARIANT_SKILLS)))" 2>/dev/null) || true
  if [ -z "$deep_variant_skills" ] || [ -z "$coverage_variant_skills" ]; then
    contract_errors+="  harness roster derivation failed: scripts/harness_common/constants.py did not yield DEEP_VARIANT_SKILLS/COVERAGE_VARIANT_SKILLS\n"
  fi
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

# The rest of that same return block. Pinning only the outer '## Context
# Detection Results' heading above pins the envelope and none of the contents:
# SKILL.md Steps 1 and 4 branch on these exact sub-headings and fields, so a
# one-sided rename yields a block that arrives intact and reads as "nothing
# detected" — service coverage collapses, schema bootstrap stops rendering, and
# workspace-aware command branching is lost, with every other check green. Same
# criterion (b) as the envelope; the boundary does not stop at the first heading.
require_tokens skills/how-to-run/agents/project-environment-detector.md \
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

# Audit verdicts: values the auditor agent returns and two consumers match on by
# name — SKILL.md Step 3's per-item prompts and the walkthrough's per-step
# rendering. An agent-return value is criterion (b) exactly as an agent-return
# heading is.
for verdict in 'Found but outdated' 'Partial' 'Missing' 'Documented but unverifiable'; do
  require_tokens skills/how-to-run/agents/how-to-run-auditor.md "$verdict"
done
require_tokens skills/how-to-run/SKILL.md 'Documented but unverifiable'
require_tokens skills/how-to-run/references/guided-walkthrough.md \
  'Found but outdated' 'Partial' 'Missing'

# NOT pinned here: `rendered_line` and `approved-unverifiable-items`, the
# identifiers how-to-run's Step 3/4 store and its own Step 6 exempts by full-line
# equality. They meet neither criterion above — no program parses them (nothing
# under scripts/ mentions either name) and the list is explicitly IN-MEMORY, so
# it never crosses a conversation boundary. They are one skill's internal
# routing, read by the same model in the same conversation, which is exactly
# what the preamble says belongs in test/ as behaviour rather than here as
# wording. Pinned, renaming a variable inside how-to-run turned CI red with no
# behavioural regression.

# Handoff: the paradigm criterion-(b) case — this skill writes a document to
# disk that a LATER conversation (or /optimus:handoff itself, on a re-run) reads
# back by these literal names. The save path and the redaction marker are read
# by the same code path. Prose that never leaves the skill is deliberately not
# pinned here.
require_tokens skills/handoff/SKILL.md \
  'docs/handoffs/' \
  '[REDACTED:' \
  '## Goal' \
  '## Current state' \
  '## Next steps' \
  '## Relevant files & artifacts' \
  '### Inlined (not yet on remote)' \
  '## History'

check "Producer/consumer contracts intact" test -z "$contract_errors"
if [ -n "$contract_errors" ]; then
  printf "       Contract issues:\n%b" "$contract_errors"
fi

# --- Summary ---
echo
echo "=== Results: $pass passed, $errors failed ==="
if [ "$errors" -gt 0 ]; then exit 1; else exit 0; fi
