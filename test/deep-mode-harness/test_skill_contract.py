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


class TestHarnessModeReferenceContract:
    def test_scope_files_override_is_conditional(self):
        text = _read("references/harness-mode.md")
        # Pre-fix hard override must not reappear
        assert "File list for agents = `scope_files.current`" not in text
        # Replacement conditional must be present
        assert "If `scope_files.current` is non-empty" in text
        # Step 3/4/5 override subsection exists
        assert "Steps 3, 4, 5 execution under harness mode" in text
