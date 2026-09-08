"""Regressions for invalid metadata silently dropping invocation restrictions."""

import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from harness_common.runner import _find_bash
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


@pytest.mark.parametrize("python_available", [True, False])
def test_validation_selects_working_python3(tmp_path, python_available):
    repo = Path(__file__).resolve().parent.parent
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    shutil.copy(repo / "scripts" / "validate_skill_metadata.py", scripts)
    skill = tmp_path / "skills" / "review"
    skill.mkdir(parents=True)
    write_skill(skill)

    launchers = tmp_path / "bin"
    launchers.mkdir()
    selected = tmp_path / "selected-python"
    executable = shlex.quote(Path(sys.executable).as_posix())
    for command in ("python", "python3"):
        launcher = launchers / command
        launcher.write_text(
            "#!/usr/bin/env bash\n"
            + (
                "exit 127\n"
                if command == "python" and not python_available
                else f'{executable} "$@" || exit $?\n'
                'if [[ "$1" == scripts/validate_skill_metadata.py ]]; then\n'
                f'  printf "%s\\n" {command} > "$SELECTED_PYTHON"\n'
                "fi\n"
            ),
            encoding="utf-8",
            newline="\n",
        )
        launcher.chmod(0o755)

    bash = Path(_find_bash())
    env = {**os.environ, "SELECTED_PYTHON": str(selected)}
    env["PATH"] = os.pathsep.join(
        [
            str(launchers),
            str(bash.parent),
            str(bash.parent.parent / "usr/bin"),
            env["PATH"],
        ]
    )
    # Execute the real entrypoint. Later manifest checks fail in this intentionally
    # small fixture; the marker is written only after real metadata validation passes.
    result = subprocess.run(
        [str(bash), str(repo / "scripts" / "validate.sh")],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    assert selected.is_file(), result.stdout + result.stderr
    assert selected.read_text().strip() == ("python" if python_available else "python3")
