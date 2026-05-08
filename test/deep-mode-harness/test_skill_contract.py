"""Doc-contract tests locking the harness-mode wording in skill and reference files.

These tests guard the load-bearing markdown phrases that control how skills
behave under HARNESS_MODE_ACTIVE. The pre-fix wording (e.g. "proceed directly
to Step 5") silently disabled file discovery and constraint-doc loading — we
assert both that the new wording is present and that the pre-fix sentinel
phrases do not come back.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(rel):
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


class TestCodeReviewHarnessContract:
    def test_harness_section_runs_steps_3_and_4(self):
        text = _read("skills/code-review/SKILL.md")
        assert "HARNESS_MODE_ACTIVE" in text
        # Load-bearing phrase from PR #93
        assert "Step 3, Step 4, and Step 5" in text
        # Regression sentinel: the pre-fix wording must not reappear
        assert "proceed directly to Step 5" not in text

    def test_step_5_file_list_supports_both_sources(self):
        text = _read("skills/code-review/SKILL.md")
        # Step 5 must reference the harness pre-populated file list source
        assert "scope_files.current" in text


class TestCodeReviewAutoRouteContract:
    def test_force_branch_diff_recorded_for_step_3(self):
        text = _read("skills/code-review/SKILL.md")
        # Step 1 must record the --branch flag as force-branch-diff state for Step 3
        assert "Recorded as `force-branch-diff`" in text

    def test_force_branch_diff_consumed_in_step_3(self):
        text = _read("skills/code-review/SKILL.md")
        # Step 3 bullet must consume the same state name Step 1 records — drift between
        # producer and consumer would silently disable the --branch override
        assert "`force-branch-diff` is set" in text

    def test_gitlab_mr_substitution_documented(self):
        text = _read("skills/code-review/SKILL.md")
        # Auto-route notices must document the MR !N substitution for GitLab projects;
        # silent removal would emit GitHub-formatted "PR #N" notices on GitLab repos
        assert 'substitute "MR !N" for "PR #N"' in text

    def test_step_3_captures_current_branch(self):
        text = _read("skills/code-review/SKILL.md")
        # Auto-route compares HEAD to origin/<current-branch>; Step 3 must capture it
        assert "<current-branch>" in text
        assert "git rev-parse --abbrev-ref HEAD" in text

    def test_auto_route_uses_rev_list_pushed_check(self):
        text = _read("skills/code-review/SKILL.md")
        # Load-bearing: HEAD-pushed gate must use git rev-list against origin/<current-branch>
        # AND require BOTH exit 0 AND no output. `git rev-list A..B` exits 0 even when it
        # prints commit SHAs, so dropping "with no output" silently lets auto-route fire
        # for branches with unpushed local commits.
        assert "git rev-list origin/<current-branch>..HEAD" in text
        assert "exits 0 with no output" in text
        assert "returns lines or exits non-zero" in text

    def test_auto_route_user_notification_phrases(self):
        text = _read("skills/code-review/SKILL.md")
        # Two user-facing notices that signal the chosen route
        assert "using the PR description as author intent context" in text
        assert "PR #N exists but HEAD is not fully pushed" in text

    def test_auto_route_user_recovery_hints(self):
        text = _read("skills/code-review/SKILL.md")
        # Each notice must include an escape-hatch hint to switch routes
        assert "Pass `--branch`" in text
        assert "Pass `--pr N`" in text

    def test_auto_route_does_not_prompt_user(self):
        text = _read("skills/code-review/SKILL.md")
        # Pre-fix behavior was an interactive prompt; new behavior must not regress.
        # Two complementary guarantees: the outer auto-route must not prompt for the
        # mode choice, and the inner jump to PR mode must not re-prompt at the
        # explicit-PR block (which has its own user-prompt paths for unknown platforms).
        assert "do NOT prompt the user to choose" in text
        assert "without re-prompting" in text

    def test_branch_flag_documented_in_examples(self):
        text = _read("skills/code-review/SKILL.md")
        # User-discoverable invocations must remain in the Examples list
        assert "/optimus:code-review --branch" in text
        assert "/optimus:code-review deep --branch" in text

    def test_force_branch_diff_takes_precedence_over_pr_route(self):
        text = _read("skills/code-review/SKILL.md")
        # --branch override must fire BEFORE the PR auto-route bullet so the user's
        # explicit flag wins; reordering would silently let an open PR override
        # `force-branch-diff`
        force_branch_idx = text.index("`force-branch-diff` is set")
        pr_route_idx = text.index("HEAD is fully pushed")
        assert force_branch_idx < pr_route_idx

    def test_auto_route_reuses_step_2_identifier(self):
        text = _read("skills/code-review/SKILL.md")
        # Auto-route must reuse the PR/MR identifier already fetched in sub-step 2
        # to avoid a redundant gh/glab round-trip and keep pr-description flowing
        assert "Reuse the PR/MR identifier captured in sub-step 2 above" in text

    def test_auto_route_state_filter_locked(self):
        text = _read("skills/code-review/SKILL.md")
        # Auto-route must only fire on truly open PRs/MRs — a drive-by drop of
        # the state filter would let closed/merged PRs pull stale pr-description
        # into agent context. Both platform literals are load-bearing.
        assert '`state` equals `"OPEN"`' in text  # GitHub
        assert '`state` equals `"opened"`' in text  # GitLab

    def test_auto_route_target_branch_field_names_locked(self):
        text = _read("skills/code-review/SKILL.md")
        # Target-branch extraction depends on the literal JSON field names; a
        # prose-cleanup that renames either to a non-existent field would silently
        # fall back to default-branch detection, mis-comparing PRs that target a
        # non-default branch (e.g., stacked PRs, release branches).
        assert "baseRefName" in text  # GitHub
        assert "target_branch" in text  # GitLab

    def test_no_open_pr_branch_route_locked(self):
        text = _read("skills/code-review/SKILL.md")
        # The 4-branch decision tree's default fall-through; silently dropping it
        # would leave the most common case (fresh feature branch with no PR yet)
        # unrouted.
        assert "No open PR/MR found (or CLI unavailable)" in text

    def test_pre_fix_interactive_prompt_wording_removed(self):
        text = _read("skills/code-review/SKILL.md")
        # Regression sentinel for the dual offer-to-review prompt this PR replaced;
        # if it returned alongside the new "do NOT prompt the user to choose" rule,
        # the two would silently contradict each other at runtime.
        assert "also offer to review it directly" not in text
        assert "If an open PR/MR was found in step 2" not in text

    def test_user_notice_lead_in_phrases_locked(self):
        text = _read("skills/code-review/SKILL.md")
        # The two route notices share a "Reviewing X —" lead-in that signals the
        # chosen route to the user; locking the lead-ins (not just the trailing
        # rationale) prevents silent rewrites that lose the parallelism.
        assert "Reviewing PR #N" in text
        assert "Reviewing the branch diff" in text

    def test_unpushed_state_prose_locked(self):
        text = _read("skills/code-review/SKILL.md")
        # Bullet 3 has equivalent technical predicate (rev-list output) and
        # user-facing prose for the unpushed condition. Drift between them would
        # obscure why the bullet fires.
        assert "pushed state cannot be determined" in text

    def test_auto_route_nested_under_no_local_changes(self):
        text = _read("skills/code-review/SKILL.md")
        # Auto-route bullets are structurally nested inside "If no local changes";
        # a future restructure that lifts them outside that branch would silently
        # let them fire when local changes exist.
        no_local_idx = text.index("If no local changes")
        force_branch_idx = text.index("`force-branch-diff` is set")
        nothing_idx = text.index("If nothing at all")
        assert no_local_idx < force_branch_idx < nothing_idx

    def test_current_branch_capture_phrasing_locked(self):
        text = _read("skills/code-review/SKILL.md")
        # The load-bearing relationship is "capture current branch AS <current-branch>";
        # locking the verbatim phrase prevents drive-bys that leave both tokens
        # but break the binding.
        assert "capture the current branch as `<current-branch>`" in text

    def test_pr_mode_jump_target_locked(self):
        text = _read("skills/code-review/SKILL.md")
        # Auto-route hands off to the "PR mode (explicit request)" section. If
        # that heading is renamed without updating the cross-reference, the
        # auto-PR bullet's pointer would dangle silently.
        assert "### PR mode (explicit request)" in text
        assert "jump to the **PR mode (explicit request)** block below" in text

    def test_readmes_document_auto_route_behavior(self):
        skill_readme = _read("skills/code-review/README.md")
        root_readme = _read("README.md")
        # User-facing READMEs make claims about auto-route behavior that must
        # match the SKILL contract; without locks, SKILL.md and READMEs can
        # drift apart silently. The root README qualifier is load-bearing —
        # without it the claim could drift to "auto-routes whenever an open
        # PR exists", which would contradict the HEAD-pushed gate.
        assert "auto-routes to an open PR/MR when HEAD is fully pushed" in skill_readme
        assert "/optimus:code-review --branch" in skill_readme
        assert "Auto-routes to PR mode" in root_readme
        assert "clean branch with a fully-pushed open PR/MR" in root_readme

    def test_outer_commits_found_gate_locked(self):
        text = _read("skills/code-review/SKILL.md")
        # The 4-branch auto-route only fires when "If commits found → route"
        # gates it. A reword that drops the conditional would let the bullets
        # fire on a freshly checked-out branch with zero commits ahead.
        assert "If commits found → route to the appropriate review mode" in text

    def test_commits_detection_command_locked(self):
        text = _read("skills/code-review/SKILL.md")
        # Sub-step 3 populates the "If commits found" predicate via this exact
        # command. Drift to a triple-dot range or a missing `origin/` prefix
        # would silently change which branches auto-route fires for.
        assert "git log --oneline origin/<base-branch>..HEAD" in text

    def test_base_branch_binding_phrasing_locked(self):
        text = _read("skills/code-review/SKILL.md")
        # Symmetric counterpart to test_current_branch_capture_phrasing_locked.
        # Without this binding, `<base-branch>` would be referenced (line 112,
        # the git log command) without ever being defined.
        assert "Use the detected branch as `<base-branch>`" in text

    def test_branch_flag_precedence_exceptions_locked(self):
        text = _read("skills/code-review/SKILL.md")
        # `--branch` is documented as having no effect under two conditions:
        # local changes present, or explicit `--pr N`. Without this clause,
        # the Step 3 bullet ordering alone could be misread as `--branch`
        # overriding explicit PR requests.
        assert "Has no effect when local changes are present" in text

    def test_pr_identifier_field_capture_locked(self):
        text = _read("skills/code-review/SKILL.md")
        # `test_auto_route_reuses_step_2_identifier` requires sub-step 2 to
        # produce a PR/MR identifier for sub-step 4 to reuse. The fields
        # producing that identifier are `number` (GitHub `--json` flag list)
        # and `iid` (GitLab JSON field). A drive-by edit dropping `number`
        # from the GitHub flag list would silently break the identifier reuse
        # — sub-step 2 would no longer fetch the `N` that sub-step 4 needs.
        assert (
            "number,state,baseRefName" in text
        )  # GitHub --json flags include the identifier
        assert "only use `number` and `baseRefName`" in text  # GitHub prose
        assert "only use `iid` and `target_branch`" in text  # GitLab prose

    def test_unknown_platform_dispatch_locked(self):
        text = _read("skills/code-review/SKILL.md")
        # The platform dispatch in sub-step 2 has three branches: GitHub,
        # GitLab, and unknown. The unknown branch is the one that exercises
        # both CLIs in self-hosted or atypical-remote setups; without it the
        # auto-route would have no defined behavior on unknown-platform repos.
        assert "If platform unknown: try both" in text
        assert "first result where an open PR/MR is confirmed" in text

    def test_branch_mode_jump_target_locked(self):
        text = _read("skills/code-review/SKILL.md")
        # Symmetric to `test_pr_mode_jump_target_locked`: three of the four
        # auto-route bullets delegate to the Branch/ref mode block via the
        # handoff sentence on line 112. If that block heading is renamed or
        # the `<ref>` binding is removed, the three branch-diff routes would
        # dangle silently.
        assert "### Branch/ref mode" in text
        assert (
            "jumps to the **Branch/ref mode** block using `origin/<base-branch>` as `<ref>`"
            in text
        )

    def test_default_branch_fallback_locked(self):
        text = _read("skills/code-review/SKILL.md")
        # The "no-PR" arm of sub-step 2 binds `<base-branch>` via default-branch
        # detection. Without it, sub-step 3's `git log --oneline origin/<base-branch>..HEAD`
        # has no value to compare against on a fresh feature branch with no PR yet —
        # the most common auto-route case. Both the trigger phrase and the literal
        # reference path are load-bearing.
        assert "If no open PR/MR found or CLI unavailable" in text
        assert "skills/pr/references/default-branch-detection.md" in text

    def test_pr_description_capture_binding_locked(self):
        text = _read("skills/code-review/SKILL.md")
        # Cross-step binding: sub-step 2 stores `pr-description` from the PR/MR
        # title and body; Steps 5 and 6 consume it for author-intent injection.
        # A rename here without coordinated edits to Steps 5-6 would silently
        # disable PR description injection — auto-route's main user promise.
        # Note GitHub uses `body`; GitLab uses `description`.
        assert "Store the `title` and `body` fields as `pr-description`" in text
        assert "Store the `title` and `description` fields as `pr-description`" in text
        # Confirm Steps 5 and 6 reference the same binding name.
        assert "If a `pr-description` was captured in Step" in text


class TestCodeReviewIntentSourcesContract:
    """Locks the user-intent-text / branch-intent-text / User Intent Block
    cross-step bindings introduced for intent-mismatch detection. A rename
    or section reorder without coordinated edits would silently disable the
    feature — the existing Python harness tests do not cover the
    markdown-only cross-step bindings these assertions guard."""

    def test_user_intent_capture_step1_locked(self):
        text = _read("skills/code-review/SKILL.md")
        # Cross-step binding: Step 1 captures the slash-command remainder as
        # `user-intent-text`; Step 5's User-intent injection consumes it. A
        # rename would silently disable the user-supplied free-text path.
        assert "store the rest as `user-intent-text`" in text

    def test_branch_intent_capture_step3_locked(self):
        text = _read("skills/code-review/SKILL.md")
        # Step 3's branch-diff path captures `branch-intent-text` from a
        # bounded git log. Drift in the command (lost `-10` cap, missing
        # `--no-merges`, or rename of the binding) would break the no-PR
        # intent source — and the 10-commit cap (R2 mitigation) could
        # regress unnoticed without this assertion.
        assert (
            'git log --no-merges -10 --format="%h %s%n%b" <ref>..HEAD' in text
        )
        assert "`branch-intent-text`" in text

    def test_user_intent_injection_step5_locked(self):
        text = _read("skills/code-review/SKILL.md")
        # Step 5's User-intent injection trigger and mutual-exclusion gate.
        # A reorder would silently double-inject or never inject.
        assert "If no PR/MR Context Block was injected AND" in text
        assert "prepend the User Intent Block" in text

    def test_pr_plus_freetext_notice_locked(self):
        text = _read("skills/code-review/SKILL.md")
        # Surfaces the silent input drop when `--pr` / `#N` is combined with
        # free-text intent and PR mode wins mutual exclusion. Removal would
        # restore the silent UX defect.
        assert "Free-text intent was supplied alongside" in text

    def test_intent_mismatch_guard_in_bug_detector_locked(self):
        text = _read("skills/code-review/agents/bug-detector.md")
        # The "skip if no intent source" guard is the load-bearing bound on
        # false positives — its removal would let bug-detector speculate
        # from pre-scan commit subjects, producing low-quality findings.
        assert "skip this category entirely — do not speculate" in text

    def test_intent_mismatch_specificity_guard_locked(self):
        text = _read("skills/code-review/agents/bug-detector.md")
        # The specificity guard suppresses speculative matching on vague
        # intent ("cleanup", "improve X"). Removal would reopen the
        # false-positive surface for aspirational free-text.
        assert "too vague to anchor a specific finding" in text

    def test_step1_excludes_scope_only_remainders(self):
        text = _read("skills/code-review/SKILL.md")
        # Step 1 must classify path-like and scope-keyword remainders as
        # scope-only (so they do not become `user-intent-text`). Removing
        # this filter would let `/optimus:code-review src/auth` or
        # `/optimus:code-review "focus on src/auth"` flow as intent and
        # produce speculative intent-mismatch findings against scope text —
        # the bug-detector specificity guard alone is heuristic.
        assert "Scope-only remainders" in text
        assert "`focus on`, `scope to`, `review`, `only`" in text
        assert "leave `user-intent-text` empty" in text

    def test_harness_branch_intent_skip_notice_locked(self):
        text = _read("references/harness-mode.md")
        # Under harness mode, branch-intent capture is in-session and silent
        # on shallow clones. The `[branch-intent] skipped — <reason>` notice
        # makes the drop observable in the harness log without changing the
        # JSON schema. Removal would restore the silent failure mode.
        assert "[branch-intent] skipped" in text
        assert "before** the JSON block" in text


class TestRefactorHarnessContract:
    def test_refactor_harness_section_does_not_skip_scope_resolution(self):
        text = _read("skills/refactor/SKILL.md")
        assert "HARNESS_MODE_ACTIVE" in text
        # Pre-fix wording must not reappear
        assert "proceed directly to Step 3" not in text
        # New wording acknowledges scope resolution + Step 3 + Step 4
        assert "Step 1's scope resolution" in text

    def test_map_analysis_areas_has_harness_override(self):
        text = _read("skills/refactor/SKILL.md")
        assert "Harness mode:" in text
        assert "parent directories" in text


class TestUnitTestHarnessContract:
    def test_harness_section_runs_steps_2_through_4(self):
        text = _read("skills/unit-test/SKILL.md")
        assert "HARNESS_MODE_ACTIVE" in text
        # Load-bearing phrase: harness mode runs the full multi-step pipeline once
        assert "run Steps 2–4 exactly once" in text
        # Regression sentinel: pre-fix wording from the PR #93 family must not appear
        assert "proceed directly to Step 5" not in text

    def test_harness_output_step_emits_structured_json(self):
        text = _read("skills/unit-test/SKILL.md")
        # Step 6 emits the JSON block instead of the Step 5 summary
        assert "json:harness-output" in text

    def test_iteration_cap_contract_locked(self):
        text = _read("skills/unit-test/SKILL.md")
        # Default/hard-cap and clamp warnings are user-visible contract;
        # silent drift (e.g. default 8 to match refactor) would break README
        # consistency and validate.sh wiring.
        assert "default 5, hard cap 10" in text
        assert "Iteration cap clamped to 10 (maximum)." in text
        assert "Iteration cap clamped to 1 (minimum)." in text

    def test_deep_mode_test_command_fallback_wording(self):
        text = _read("skills/unit-test/SKILL.md")
        # Safety-net contract: when no test command is available, deep mode
        # must fall back to normal mode rather than run unguarded auto-approve.
        assert "Deep mode requires a test command for safe auto-approve" in text
        assert "Falling back to normal mode" in text

    def test_step_5_interactive_deep_mode_skip_contract(self):
        text = _read("skills/unit-test/SKILL.md")
        # Interactive deep mode replaces the single-pass Step 5 summary with
        # the cumulative report; a silent drop would double-render the summary.
        assert "Interactive deep mode:" in text
        assert "the cumulative report rendered by the deep mode loop" in text

    def test_coverage_plateau_threshold_locked(self):
        # 0.5pp is the sole numeric knob for the plateau stop condition.
        # README advertises "0.5 percentage points"; drift between the two
        # would be silent — neither validate.sh nor any other test locks it.
        skill = _read("skills/unit-test/SKILL.md")
        readme = _read("skills/unit-test/README.md")
        assert "0.5pp" in skill
        assert "0.5 percentage points" in readme

    def test_accumulated_items_entry_schema_fields(self):
        # Convergence matching filters on `target` in `accumulated-items`;
        # a silent rename of any field (file/target/iteration/status) would
        # break the exact-match check with no loud failure.
        text = _read("skills/unit-test/SKILL.md")
        assert "**file**" in text
        assert "**target**" in text
        assert "**iteration**" in text
        assert "**status**" in text


class TestHarnessModeReferenceContract:
    def test_scope_files_override_is_conditional(self):
        text = _read("references/harness-mode.md")
        # Pre-fix hard override must not reappear
        assert "File list for agents = `scope_files.current`" not in text
        # Replacement conditional must be present
        assert "If `scope_files.current` is non-empty" in text
        # Step 3/4/5 override subsection exists
        assert "Steps 3, 4, 5 execution under harness mode" in text
