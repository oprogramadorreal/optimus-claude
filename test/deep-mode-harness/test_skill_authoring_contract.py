"""Doc-contract tests locking the skill-authoring detection wording.

These tests guard the load-bearing markdown phrases that teach init to detect
a skill-authoring stack (Claude Code plugins, Codex skill repos, prompt
libraries, custom agent frameworks) and route review/refactor skills to use
`skill-writing-guidelines.md` as the quality lens for markdown instruction
files.

If any of these assertions fail, the dual-lens routing mechanism is broken and
projects that author markdown instructions will be reviewed against
coding-guidelines.md rules that don't apply to prose.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(rel):
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


class TestConstraintDocLoadingSkillAuthoring:
    def test_skill_authoring_lens_section_exists(self):
        text = _read("skills/init/references/constraint-doc-loading.md")
        assert "## Skill authoring lens" in text
        # The section must gate on skill-writing-guidelines.md presence
        assert ".claude/docs/skill-writing-guidelines.md" in text

    def test_skill_authoring_lens_routes_markdown_to_skill_writing_guidelines(self):
        text = _read("skills/init/references/constraint-doc-loading.md")
        # The conventional skill-authoring directory names must be listed
        for directory in (
            "skills/",
            "agents/",
            "prompts/",
            "commands/",
            "instructions/",
        ):
            assert (
                directory in text
            ), f"expected conventional dir {directory} in constraint-doc-loading.md"

    def test_skill_authoring_lens_preserves_default_for_code(self):
        text = _read("skills/init/references/constraint-doc-loading.md")
        # The default loading procedure must still cover non-skill-authoring projects:
        # the gating sentence must say the section does not apply when the file is absent.
        assert "this section does not apply" in text

    def test_single_project_section_lists_skill_writing_guidelines(self):
        text = _read("skills/init/references/constraint-doc-loading.md")
        # skill-writing-guidelines.md must appear inside the Single Project section,
        # not just anywhere in the file.
        single_project_section = text.split("## Single Project", 1)[1].split(
            "## Monorepo", 1
        )[0]
        assert "skill-writing-guidelines.md" in single_project_section

    def test_monorepo_section_lists_skill_writing_guidelines_as_shared(self):
        text = _read("skills/init/references/constraint-doc-loading.md")
        # In monorepos, skill-writing-guidelines.md must be listed as shared at root
        # alongside coding-guidelines.md — scope the check to the Monorepo section
        # so the co-occurrence is meaningful, not just two independent matches anywhere.
        monorepo_section = text.split("## Monorepo", 1)[1].split(
            "## Skill authoring lens", 1
        )[0]
        assert "skill-writing-guidelines.md" in monorepo_section
        assert "shared at root" in monorepo_section


class TestInitSkillAuthoringDetection:
    def test_init_step_1_checkpoint_includes_skill_authoring(self):
        text = _read("skills/init/SKILL.md")
        # Step 1 checkpoint must include skill-authoring detection
        assert "Skill authoring detected" in text

    def test_init_step_6_has_skill_writing_guidelines_row(self):
        text = _read("skills/init/SKILL.md")
        # The Step 6 conditional-install table must reference the new template.
        # Scope to Step 6 so an occurrence in Step 7's validation checklist or
        # elsewhere can't mask a missing Step 6 row.
        step_6 = text.split("## Step 6: Create Documentation Files", 1)[1]
        step_6 = step_6.split("## Step 6b", 1)[0]
        assert "templates/docs/skill-writing-guidelines.md" in step_6

    def test_init_detection_signal_documented(self):
        text = _read("skills/init/SKILL.md")
        # Detection signal must enumerate the structural check — instruction file names
        for marker in (
            "SKILL.md",
            "AGENT.md",
            "PROMPT.md",
            "COMMAND.md",
            "INSTRUCTION.md",
        ):
            assert (
                marker in text
            ), f"expected instruction file name {marker} in init SKILL.md detection"
        # Load-bearing invariants of the detection algorithm: the container must hold
        # ≥2 subdirectories, every subdirectory must contain an instruction file, and
        # the check must be case-insensitive. Without these, loosening the algorithm
        # to "any directory with a SKILL.md" would pass this test but cause false
        # positives on unrelated user projects.
        assert "2 subdirectories" in text, "detection must require ≥2 subdirectories"
        # Scope to Step 6 so the assertion locks the detection algorithm's
        # "every subdirectory" requirement — the word "every" appears elsewhere
        # in SKILL.md (Step 5, Step 7) and would mask a regression if checked
        # against the full file.
        step_6 = text.split("## Step 6: Create Documentation Files", 1)[1]
        step_6 = step_6.split("## Step 6b", 1)[0]
        assert "every" in step_6, "detection must require every subdirectory to match"
        assert "case-insensitive" in text, "detection must be case-insensitive"

    def test_init_install_semantics_is_merge_not_silent_overwrite(self):
        text = _read("skills/init/SKILL.md")
        # The install-semantics paragraph must guarantee both branches:
        # (a) new-file: write from template with [PROJECT NAME] substitution
        # (b) existing-file: review-and-propose, preserve user-added sections,
        #     never silently overwrite. Scope to the install-semantics paragraph
        #     so a weak match elsewhere in SKILL.md can't mask a regression.
        paragraph = text.split("`skill-writing-guidelines.md` install semantics:", 1)[1]
        paragraph = paragraph.split("**Placement rules:**", 1)[0]
        assert "review-and-propose" in paragraph
        assert "already exists" in paragraph
        assert "preserve user-added sections" in paragraph
        assert "Never silently overwrite" in paragraph
        assert "[PROJECT NAME]" in paragraph

    def test_init_monorepo_installs_skill_writing_guidelines_once_at_root(self):
        text = _read("skills/init/SKILL.md")
        # Monorepo placement rule: detection is repo-level, install once at root.
        # Scope to the Placement rules block so the assertion can't pass on a
        # stray phrase elsewhere. A regression that re-scoped the file
        # per-subproject would drop one of these markers.
        placement = text.split("**Placement rules:**", 1)[1]
        placement = placement.split("## Step 6b", 1)[0]
        assert "shared at root" in placement
        assert "once at root" in placement
        assert "at the repo level" in placement

    def test_init_step_7_verifies_skill_writing_guidelines(self):
        text = _read("skills/init/SKILL.md")
        # Step 7 content-check must verify skill-writing-guidelines.md has
        # [PROJECT NAME] replaced and user-added sections preserved. Without
        # this, init could skip post-generation verification of the file.
        step_7 = text.split("## Step 7: Verify and Report", 1)[1]
        assert "skill-writing-guidelines.md" in step_7
        assert "[PROJECT NAME]" in step_7
        assert "user-added sections" in step_7

    def test_init_step_4b_documents_both_html_comment_branches(self):
        text = _read("skills/init/SKILL.md")
        # Step 4b (subproject CLAUDE.md) must document both branches of the
        # HTML comment replacement: materialize when detected, remove when not.
        # The existing test_init_documents_both_branches_of_html_comment_replacement
        # checks the full file, so a removal of the Step 4b instruction could
        # be masked by the Step 4 match. Scope to Step 4b specifically.
        step_4b = text.split("## Step 4b:", 1)[1]
        step_4b = step_4b.split("## Step 5:", 1)[0]
        assert "skill-writing-guidelines.md" in step_4b
        assert (
            "remove the HTML comment entirely" in step_4b
        ), "Step 4b must document the remove-when-not-detected branch"


class TestSkillWritingGuidelinesTemplate:
    def test_template_file_exists(self):
        path = REPO_ROOT / "skills/init/templates/docs/skill-writing-guidelines.md"
        assert path.exists(), "skill-writing-guidelines.md template must exist"

    def test_template_has_project_name_placeholder(self):
        text = _read("skills/init/templates/docs/skill-writing-guidelines.md")
        assert (
            "[PROJECT NAME]" in text
        ), "template must use [PROJECT NAME] placeholder for init to fill in"

    def test_template_is_framework_agnostic(self):
        text = _read("skills/init/templates/docs/skill-writing-guidelines.md")
        # Must NOT contain Claude Code-specific content
        assert (
            "disable-model-invocation" not in text
        ), "template must be framework-agnostic — no Claude Code-specific rules"
        assert (
            "#22063" not in text
        ), "template must not reference Claude Code-specific GitHub issues"

    def test_template_covers_core_principles(self):
        text = _read("skills/init/templates/docs/skill-writing-guidelines.md")
        # The framework-agnostic principles that define the skill-writing lens
        for principle in ("KISS", "SRP", "Progressive Disclosure", "Writing Style"):
            assert principle in text, f"template must cover {principle}"


class TestProjectAnalyzerDetection:
    def test_project_analyzer_detects_skill_authoring(self):
        text = _read("skills/init/agents/project-analyzer.md")
        assert "Skill-authoring detection" in text or "skill-authoring" in text.lower()

    def test_project_analyzer_reports_skill_authoring_in_return_format(self):
        text = _read("skills/init/agents/project-analyzer.md")
        # Detection Results output must include the skill-authoring field
        assert "Skill authoring detected" in text

    def test_project_analyzer_detection_signal_matches_init_spec(self):
        # project-analyzer.md now owns the canonical detection algorithm — the
        # SKILL.md Step 1 checkpoint points to it. Lock the same load-bearing
        # invariants (≥2 subdirectories, every subdirectory, case-insensitive,
        # all five instruction file names) so the two specs cannot drift apart.
        text = _read("skills/init/agents/project-analyzer.md")
        for marker in (
            "SKILL.md",
            "AGENT.md",
            "PROMPT.md",
            "COMMAND.md",
            "INSTRUCTION.md",
        ):
            assert (
                marker in text
            ), f"expected instruction file name {marker} in project-analyzer.md"
        assert (
            "2 subdirectories" in text
        ), "project-analyzer must require ≥2 subdirectories"
        assert (
            "every" in text.lower()
        ), "project-analyzer must require every subdirectory to match"
        assert "case-insensitive" in text, "project-analyzer must be case-insensitive"


class TestDocumentationAuditorRecognizesSkillWriting:
    def test_auditor_knows_about_skill_writing_guidelines(self):
        text = _read("skills/init/agents/documentation-auditor.md")
        assert "skill-writing-guidelines.md" in text

    def test_auditor_handles_skill_writing_as_project_customizable(self):
        text = _read("skills/init/agents/documentation-auditor.md")
        # Must be audited as a project-customizable lens, with user-added sections preserved.
        assert "skill-writing-guidelines.md" in text
        assert "preserve user-added sections" in text

    def test_auditor_leaves_existing_skill_writing_guidelines_alone_without_stack(self):
        text = _read("skills/init/agents/documentation-auditor.md")
        # Asymmetric negative branch: if the project has no skill-authoring stack
        # but skill-writing-guidelines.md already exists, the auditor must NOT
        # flag it for removal — it may be an intentional user install. Losing
        # this clause would cause re-init on non-skill-authoring repos to
        # propose deleting user-installed guidelines.
        assert "leave it alone" in text
        assert "no skill-authoring stack" in text


class TestCLAUDEMdTemplatesHaveSkillAuthoringPlaceholder:
    """The dual-lens feature only works end-to-end if init can inject the
    skill-writing-guidelines pointer into the generated CLAUDE.md. That
    requires an HTML comment placeholder in every CLAUDE.md template that
    init will use as a substitution anchor. A template edit that drops the
    placeholder would silently break skill-authoring projects on re-init.
    """

    def test_single_project_template_has_skill_authoring_placeholder(self):
        text = _read("skills/init/templates/single-project-claude.md")
        assert "skill authoring was detected" in text.lower()
        assert "skill-writing-guidelines.md" in text
        # The anchor must be an HTML comment so init can detect and replace it
        assert "<!--" in text and "-->" in text

    def test_monorepo_template_has_skill_authoring_placeholder(self):
        text = _read("skills/init/templates/monorepo-claude.md")
        assert "skill authoring was detected" in text.lower()
        assert "skill-writing-guidelines.md" in text
        assert "<!--" in text and "-->" in text

    def test_subproject_template_has_skill_authoring_placeholder(self):
        text = _read("skills/init/templates/subproject-claude.md")
        assert "skill authoring was detected" in text.lower()
        assert "skill-writing-guidelines.md" in text
        assert "<!--" in text and "-->" in text

    def test_init_documents_both_branches_of_html_comment_replacement(self):
        text = _read("skills/init/SKILL.md")
        # Both branches must be spelled out: materialize when detected,
        # remove the HTML comment when not detected. If either branch is lost,
        # the template placeholder would leak into generated CLAUDE.md files
        # or the dual-lens pointer would never be injected.
        assert "replace the HTML comment placeholder" in text
        assert "remove the HTML comment entirely" in text


class TestPluginLevelCodeSimplifier:
    def test_code_simplifier_mentions_skill_writing_guidelines(self):
        # The plugin-level code-simplifier agent must be dual-lens aware.
        # It inlines the routing rules (rather than referencing constraint-doc-loading.md)
        # to keep itself a leaf in the reference graph — the validator enforces depth <= 2.
        text = _read("agents/code-simplifier.md")
        assert "skill-writing-guidelines.md" in text

    def test_code_simplifier_has_dual_lens_routing(self):
        text = _read("agents/code-simplifier.md")
        # Must have the dual-lens routing section heading, not just any mention
        # of "skill-authoring" (which would match a passing reference).
        assert "Dual-lens routing" in text

    def test_code_simplifier_forbids_cross_contamination(self):
        # The mutual-exclusion rule is the entire point of dual-lens routing.
        # A future cleanup pass could remove this sentence while leaving the
        # section headings in place, reintroducing the bug the routing prevents.
        text = _read("agents/code-simplifier.md")
        assert (
            "Never judge a SKILL.md by" in text or "never judge a SKILL.md by" in text
        )
        assert "`.py` file" in text and "skill-writing-guidelines.md" in text

    def test_constraint_doc_loading_forbids_cross_contamination(self):
        text = _read("skills/init/references/constraint-doc-loading.md")
        # Same mutual-exclusion guard in the canonical lens definition.
        assert "never judge a SKILL.md by" in text
        assert "never judge a `.py` file by" in text

    def test_dual_lens_directories_parity_across_all_sources(self):
        # The inlined routing in code-simplifier.md and the skip rule in
        # test-guardian.md must list the same conventional skill-authoring
        # directories as constraint-doc-loading.md. Without this parity check,
        # adding a new directory to one file but forgetting the others would
        # silently break routing for that directory.
        canonical = _read("skills/init/references/constraint-doc-loading.md")
        inlined = _read("agents/code-simplifier.md")
        guardian = _read("agents/test-guardian.md")

        dirs = {"skills/", "agents/", "prompts/", "commands/", "instructions/"}
        for d in dirs:
            assert d in canonical, f"{d} missing from constraint-doc-loading.md"
            assert d in inlined, f"{d} missing from code-simplifier.md"
            assert d in guardian, f"{d} missing from test-guardian.md"


class TestPluginLevelTestGuardian:
    def test_test_guardian_has_markdown_skip_rule(self):
        # The test-guardian must skip markdown instruction files in
        # skill-authoring projects. Without this rule, the agent would
        # flag instruction prose as untested code.
        text = _read("agents/test-guardian.md")
        assert "skill-writing-guidelines.md" in text
        assert "instruction prose" in text or "instruction files" in text

    def test_test_guardian_gates_skip_on_file_presence(self):
        # The skip rule must be gated on skill-writing-guidelines.md existence,
        # not unconditional — projects without skill authoring must not skip
        # their .md files. Scope to the skip-rule bullet so an unrelated
        # "exists" elsewhere in the file can't mask a regression.
        text = _read("agents/test-guardian.md")
        skip_rule = [
            line for line in text.splitlines() if "skill-writing-guidelines.md" in line
        ]
        assert skip_rule, "test-guardian must mention skill-writing-guidelines.md"
        assert any(
            "exists" in line.lower() for line in skip_rule
        ), "skip rule must be gated on file existence"


class TestVerifySkillAuthoringAwareness:
    def test_verify_environment_summary_includes_skill_writing_guidelines(self):
        text = _read("skills/verify/SKILL.md")
        assert "skill-writing-guidelines.md" in text


class TestResetSkillAuthoringAwareness:
    def test_reset_scan_list_includes_skill_writing_guidelines(self):
        text = _read("skills/reset/SKILL.md")
        assert ".claude/docs/skill-writing-guidelines.md" in text

    def test_reset_classifies_skill_writing_guidelines_as_heuristic(self):
        # skill-writing-guidelines.md uses review-and-propose semantics (like
        # testing.md), not verbatim-template semantics (like coding-guidelines.md).
        # It must appear in the "Generated docs (heuristic)" table, not the
        # "Near-exact template" section.
        text = _read("skills/reset/SKILL.md")
        heuristic_section = text.split("**Generated docs (heuristic", 1)[1].split(
            "For CLAUDE.md:", 1
        )[0]
        assert "skill-writing-guidelines.md" in heuristic_section

    def test_reset_heuristic_headings_match_template(self):
        # The fingerprint headings in reset must match the actual template
        # section headings — drift would cause misclassification.
        reset = _read("skills/reset/SKILL.md")
        template = _read("skills/init/templates/docs/skill-writing-guidelines.md")
        headings = [
            line.lstrip("# ").strip()
            for line in template.splitlines()
            if line.startswith("## ")
        ]
        for h in headings:
            assert h in reset, f"reset fingerprint missing heading: {h}"

    def test_reset_heuristic_check_instruction_includes_skill_writing(self):
        # The "For docs" instruction paragraph must include
        # skill-writing-guidelines.md so the heading check is applied to it.
        text = _read("skills/reset/SKILL.md")
        for_docs_lines = [
            line for line in text.splitlines() if line.startswith("For docs (")
        ]
        assert for_docs_lines, "reset must have a 'For docs (...)' instruction line"
        assert "skill-writing-guidelines.md" in for_docs_lines[0]


class TestMonorepoScopingRuleSkillWriting:
    def test_monorepo_scoping_rule_includes_skill_writing_guidelines(self):
        # The Monorepo Scoping Rule section must list skill-writing-guidelines.md
        # alongside coding-guidelines.md as a shared guideline. Without this,
        # monorepo subprojects would silently stop inheriting the skill-writing lens.
        text = _read("skills/init/references/constraint-doc-loading.md")
        scoping_section = text.split("## Monorepo Scoping Rule", 1)[1].split("##", 1)[0]
        assert "skill-writing-guidelines.md" in scoping_section


class TestStep4HTMLCommentBranches:
    def test_single_project_step4_documents_both_html_comment_branches(self):
        # Step 4 single-project flow must document both branches of the
        # HTML comment replacement: materialize when detected, remove when not.
        # Step 4b has its own scoped test; this covers the single-project flow.
        text = _read("skills/init/SKILL.md")
        single_section = text.split("### Single project", 1)[1].split(
            "### Monorepo", 1
        )[0]
        assert (
            "replace the HTML comment placeholder" in single_section
            or "replace the HTML comment" in single_section
        )
        assert "remove the HTML comment entirely" in single_section

    def test_monorepo_step4_references_skill_authoring_replacement(self):
        # Step 4 monorepo flow must reference the skill-authoring replacement rule.
        # Without this, the monorepo root CLAUDE.md would never get the dual-lens
        # pointer materialized.
        text = _read("skills/init/SKILL.md")
        monorepo_section = text.split("### Monorepo", 1)[1].split(
            "### Multi-repo workspace", 1
        )[0]
        assert "skill-authoring" in monorepo_section.lower()
        assert "HTML comment" in monorepo_section
