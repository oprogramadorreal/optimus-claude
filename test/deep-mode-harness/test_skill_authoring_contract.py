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
        # The Step 6 conditional-install table must reference the new template
        assert "templates/docs/skill-writing-guidelines.md" in text

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
        assert "every" in text, "detection must require every subdirectory to match"
        assert "case-insensitive" in text, "detection must be case-insensitive"

    def test_init_install_semantics_is_merge_not_silent_overwrite(self):
        text = _read("skills/init/SKILL.md")
        # skill-writing-guidelines.md must use review-and-propose, NOT silent overwrite
        assert "review-and-propose" in text


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


class TestDocumentationAuditorRecognizesSkillWriting:
    def test_auditor_knows_about_skill_writing_guidelines(self):
        text = _read("skills/init/agents/documentation-auditor.md")
        assert "skill-writing-guidelines.md" in text

    def test_auditor_handles_skill_writing_as_project_customizable(self):
        text = _read("skills/init/agents/documentation-auditor.md")
        # Must be audited as a project-customizable lens, with user-added sections preserved.
        assert "skill-writing-guidelines.md" in text
        assert "preserve user-added sections" in text


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
