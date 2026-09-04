"""Regressions for invalid metadata silently dropping invocation restrictions."""

from pathlib import Path

import pytest
from validate_skill_metadata import validate_skill

FRONTMATTER = "description: Reviews changes\ndisable-model-invocation: true\n"
POLICY = "policy:\n  allow_implicit_invocation: false\n"


def write_skill(tmp_path, frontmatter=FRONTMATTER, policy=POLICY):
    (tmp_path / "SKILL.md").write_text(
        f"---\n{frontmatter}---\n# Skill\n", encoding="utf-8"
    )
    (tmp_path / "agents").mkdir()
    (tmp_path / "agents" / "openai.yaml").write_text(policy, encoding="utf-8")
    return tmp_path


@pytest.mark.parametrize(
    "frontmatter",
    [
        FRONTMATTER,
        'description: "Read-only: reviews changes"\ndisable-model-invocation: true\n',
        "description: >-\n  Read-only: reviews changes\n  across files.\ndisable-model-invocation: true\n",
    ],
)
def test_valid_descriptions(tmp_path, frontmatter):
    assert validate_skill(write_skill(tmp_path, frontmatter)) == []


@pytest.mark.parametrize(
    "frontmatter",
    [
        "description: Read-only: reviews changes\ndisable-model-invocation: true\n",
        'description: Reviews changes\ndisable-model-invocation: "true"\n',
        "description: Reviews changes\ndisable-model-invocation: false\n",
        "description: Reviews changes\n",
        "description: [reviews, changes]\ndisable-model-invocation: true\n",
        "description: " + "x" * 1025 + "\ndisable-model-invocation: true\n",
        FRONTMATTER + "argument-hint: [path]\n",
        FRONTMATTER + "name: review\n",
        "- description: Reviews changes\n",
    ],
)
def test_invalid_frontmatter_is_rejected(tmp_path, frontmatter):
    errors = validate_skill(write_skill(tmp_path, frontmatter))
    assert errors
    assert all("SKILL.md:" in error for error in errors)


@pytest.mark.parametrize(
    "policy",
    [
        "interface:\n  allow_implicit_invocation: false\n",
        'policy:\n  allow_implicit_invocation: "false"\n',
        "policy:\n  allow_implicit_invocation: true\n",
        "policy:\n  allow_implicit_invocation: 0\n",
        "policy: {}\n",
        "policy: [false]\n",
        "policy: [\n",
        "- policy: false\n",
    ],
)
def test_missing_or_invalid_invocation_policy_is_rejected(tmp_path, policy):
    errors = validate_skill(write_skill(tmp_path, policy=policy))
    assert len(errors) == 1
    assert "openai.yaml:" in errors[0]


def test_unterminated_frontmatter_is_rejected(tmp_path):
    write_skill(tmp_path)
    (tmp_path / "SKILL.md").write_text("---\n" + FRONTMATTER, encoding="utf-8")
    assert "missing closing frontmatter delimiter" in validate_skill(tmp_path)[0]


def test_missing_sidecar_is_rejected(tmp_path):
    write_skill(tmp_path)
    (tmp_path / "agents" / "openai.yaml").unlink()
    assert "openai.yaml:" in validate_skill(tmp_path)[0]


def test_shipped_skill_metadata():
    skills = Path(__file__).resolve().parent.parent / "skills"
    errors = [
        error
        for skill in skills.iterdir()
        if skill.is_dir()
        for error in validate_skill(skill)
    ]
    assert errors == []
