"""Oracles for the headless skill smoke runner (no model calls here)."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import yaml

SECTIONS = {
    "files_exist",
    "files_not_exist",
    "files_contain",
    "files_not_modified",
    "output_contains",
    "output_nonempty",
    "branch_prefix",
}


def expectation(path, skill, fixture):
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    spec = data.get(skill, {}).get(fixture) if isinstance(data, dict) else None
    if not isinstance(spec, dict) or not spec or not any(spec.values()):
        raise ValueError(f"Missing or empty expectations for {skill}:{fixture}")
    unknown = set(spec) - SECTIONS
    if unknown:
        raise ValueError(f"Unknown expectations: {', '.join(sorted(unknown))}")
    return spec


def git_output(root, *args):
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        check=True,
    ).stdout.decode("utf-8", errors="replace")


def snapshot(root):
    """Compare bytes and Git state, including edits to already-dirty files."""
    root = Path(root)
    files = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if ".git" in relative.parts:
            continue
        if path.is_symlink():
            files[relative.as_posix()] = {"link": str(path.readlink())}
        elif path.is_file():
            files[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "files": files,
        "head": git_output(root, "rev-parse", "HEAD"),
        "branch": git_output(root, "symbolic-ref", "--short", "HEAD"),
        "staged": git_output(root, "diff", "--cached", "--binary"),
        "status": git_output(root, "status", "--porcelain=v1", "-z"),
    }


def validate(spec, root, output_path, baseline):
    root = Path(root)
    result = json.loads(Path(output_path).read_text(encoding="utf-8"))
    if not isinstance(result, dict) or result.get("type") != "result":
        raise ValueError("Claude did not return a result envelope")
    if result.get("is_error") is not False or result.get("subtype") != "success":
        raise ValueError(
            f"Claude run did not complete successfully: {result.get('subtype')}"
        )
    output = result.get("result", "")
    if not isinstance(output, str) or not output.strip():
        raise ValueError("Claude returned an empty final response")
    failures = []
    for name in spec.get("files_exist", []):
        if not (root / name).is_file():
            failures.append(f"Missing file: {name}")
    for name in spec.get("files_not_exist", []):
        if (root / name).exists():
            failures.append(f"Unexpected file: {name}")
    for name, needles in spec.get("files_contain", {}).items():
        path = root / name
        content = path.read_text(encoding="utf-8") if path.is_file() else ""
        for needle in needles:
            if needle not in content:
                failures.append(f"{name} is missing {needle!r}")
    for needle in spec.get("output_contains", []):
        if needle.lower() not in output.lower():
            failures.append(f"Response is missing {needle!r}")
    if spec.get("files_not_modified") and snapshot(root) != json.loads(
        Path(baseline).read_text(encoding="utf-8")
    ):
        failures.append("Read-only skill changed file contents or Git state")
    if "branch_prefix" in spec:
        branch = git_output(root, "symbolic-ref", "--short", "HEAD").strip()
        if not branch.startswith(spec["branch_prefix"]):
            failures.append(
                f"Expected branch prefix {spec['branch_prefix']!r}, got {branch!r}"
            )
    if failures:
        raise ValueError("; ".join(failures))
    metrics = {
        key: result[key]
        for key in (
            "duration_ms",
            "duration_api_ms",
            "num_turns",
            "usage",
            "modelUsage",
            "total_cost_usd",
        )
        if key in result
    }
    if metrics:
        print("Host result metrics: " + json.dumps(metrics, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("snapshot", "expectation", "validate"))
    parser.add_argument("--root")
    parser.add_argument("--expected")
    parser.add_argument("--skill")
    parser.add_argument("--fixture")
    parser.add_argument("--output")
    parser.add_argument("--baseline")
    args = parser.parse_args()
    try:
        if args.action == "snapshot":
            print(json.dumps(snapshot(args.root), ensure_ascii=True))
        else:
            spec = expectation(args.expected, args.skill, args.fixture)
            if args.action == "validate":
                validate(spec, args.root, args.output, args.baseline)
    except (ValueError, OSError, subprocess.CalledProcessError, yaml.YAMLError) as exc:
        parser.exit(1, f"Skill smoke check failed: {exc}\n")


if __name__ == "__main__":
    main()
