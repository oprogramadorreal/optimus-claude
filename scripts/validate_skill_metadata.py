"""Validate the metadata each host uses to discover and invoke skills."""

import sys
from pathlib import Path

import yaml


def validate_skill(skill_dir):
    errors = []
    skill_path = skill_dir / "SKILL.md"
    try:
        lines = skill_path.read_text(encoding="utf-8").splitlines()
        if not lines or lines[0] != "---":
            raise ValueError("missing opening frontmatter delimiter")
        try:
            end = lines.index("---", 1)
        except ValueError:
            raise ValueError("missing closing frontmatter delimiter") from None
        metadata = yaml.safe_load("\n".join(lines[1:end]))
        if not isinstance(metadata, dict):
            raise ValueError("frontmatter must be a YAML mapping")
        description = metadata.get("description")
        if not isinstance(description, str) or not description.strip():
            errors.append(f"{skill_path}: description must be a non-empty string")
        elif len(description) > 1024:
            errors.append(f"{skill_path}: description exceeds 1024 characters")
        if metadata.get("disable-model-invocation") is not True:
            errors.append(f"{skill_path}: disable-model-invocation must be true")
        if "name" in metadata:
            errors.append(f"{skill_path}: name would override the plugin namespace")
        if "argument-hint" in metadata and not isinstance(
            metadata["argument-hint"], str
        ):
            errors.append(f"{skill_path}: argument-hint must be a string")
    except (OSError, ValueError, yaml.YAMLError) as exc:
        errors.append(f"{skill_path}: {exc}")

    policy_path = skill_dir / "agents" / "openai.yaml"
    try:
        metadata = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
        policy = metadata.get("policy") if isinstance(metadata, dict) else None
        if (
            not isinstance(policy, dict)
            or policy.get("allow_implicit_invocation") is not False
        ):
            errors.append(
                f"{policy_path}: policy.allow_implicit_invocation must be false"
            )
    except (OSError, yaml.YAMLError) as exc:
        errors.append(f"{policy_path}: {exc}")
    return errors


def main():
    errors = [
        error
        for skill_dir in sorted(Path("skills").iterdir())
        if skill_dir.is_dir()
        for error in validate_skill(skill_dir)
    ]
    for error in errors:
        print(error)
    return bool(errors)


if __name__ == "__main__":
    sys.exit(main())
