"""Smoke-oracle regressions. These use local fixtures/stubs, never paid models."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from harness_common.runner import _find_bash, bash_environment
from skill_test_support import expectation, snapshot, validate

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def project(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    subprocess.run(["git", "init", "-q", str(project)], check=True)
    subprocess.run(
        ["git", "-C", str(project), "config", "user.email", "test@example.invalid"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(project), "config", "user.name", "Test"], check=True
    )
    (project / "index.js").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(project), "add", "index.js"], check=True)
    subprocess.run(["git", "-C", str(project), "commit", "-qm", "base"], check=True)
    return project


def result_file(tmp_path, **overrides):
    path = tmp_path / "result.json"
    path.write_text(
        json.dumps(
            {
                "type": "result",
                "subtype": "success",
                "is_error": False,
                "result": "Completed",
                **overrides,
            }
        ),
        encoding="utf-8",
    )
    return path


def test_readonly_detects_change_to_already_dirty_file(project, tmp_path):
    path = project / "index.js"
    path.write_text("user change\n", encoding="utf-8")
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps(snapshot(project)), encoding="utf-8")
    path.write_text("lost user change\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Read-only"):
        validate({"files_not_modified": True}, project, result_file(tmp_path), baseline)


@pytest.mark.parametrize("spec", [{}, {"files_exist": []}, {"typo": True}])
def test_empty_or_unknown_expectations_fail(tmp_path, spec):
    path = tmp_path / "expected.yaml"
    path.write_text(json.dumps({"init": {"empty-project": spec}}), encoding="utf-8")
    with pytest.raises(ValueError):
        expectation(path, "init", "empty-project")
    with pytest.raises(ValueError):
        expectation(path, "prompt", "empty-project")


@pytest.mark.parametrize(
    "result",
    [
        {"is_error": True, "subtype": "error_max_turns"},
        {"result": ""},
        {"type": "system"},
    ],
)
def test_unsuccessful_or_empty_result_fails(project, tmp_path, result):
    with pytest.raises(ValueError):
        validate(
            {"output_nonempty": True}, project, result_file(tmp_path, **result), None
        )


def test_branch_oracle_checks_git_not_response(project, tmp_path):
    output = result_file(tmp_path, result="Created feat/example")
    with pytest.raises(ValueError, match="branch prefix"):
        validate({"branch_prefix": "feat/"}, project, output, None)
    subprocess.run(
        ["git", "-C", str(project), "checkout", "-qb", "feat/example"], check=True
    )
    validate({"branch_prefix": "feat/"}, project, output, None)


@pytest.mark.parametrize(
    "mode, skill, expected_status",
    [
        ("success", "commit-suggest", 0),
        ("exit-one", "commit-suggest", 1),
        ("mutate", "commit-suggest", 1),
        ("branch-lie", "commit-branch", 1),
        ("branch-create", "commit-branch", 0),
    ],
)
def test_bash_runner_selects_checkout_and_rejects_false_success(
    project, tmp_path, mode, skill, expected_status
):
    checkout = tmp_path / "plugin checkout with spaces"
    (checkout / "scripts").mkdir(parents=True)
    for name in ("test-skills.sh", "skill_test_support.py"):
        shutil.copyfile(ROOT / "scripts" / name, checkout / "scripts" / name)
    fixture = checkout / "test" / "fixtures" / "node-project"
    shutil.copytree(project, fixture)
    shutil.copyfile(
        ROOT / "test" / "expected-outputs.yaml",
        checkout / "test" / "expected-outputs.yaml",
    )
    subprocess.run(["git", "init", "-q", str(checkout)], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(checkout),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "--allow-empty",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    stub_dir = tmp_path / "stubs"
    stub_dir.mkdir()
    stub = stub_dir / "claude"
    stub.write_text(
        "#!/usr/bin/env bash\n"
        'if [ "$1" = "--version" ]; then echo "stub-claude (not a model)"; exit 0; fi\n'
        'printf "%s\\n" "$@" > "$ARGV_LOG"\n'
        'if [ "$STUB_MODE" = "mutate" ]; then echo overwritten > index.js; fi\n'
        'if [ "$STUB_MODE" = "branch-create" ]; then git checkout -qb feat/example; fi\n'
        'echo \'{"type":"result","subtype":"success","is_error":false,"result":"feat/example"}\'\n'
        '[ "$STUB_MODE" != "exit-one" ]\n',
        encoding="utf-8",
        newline="\n",
    )
    stub.chmod(0o755)
    import sys

    bash = _find_bash()
    env = bash_environment(bash)
    env["PATH"] = str(stub_dir) + os.pathsep + env.get("PATH", "")
    env.update(
        PYTHON=sys.executable.replace("\\", "/"),
        ARGV_LOG=str(tmp_path / "argv.log"),
        STUB_MODE=mode,
    )
    result = subprocess.run(
        [
            bash,
            str(checkout / "scripts" / "test-skills.sh"),
            "--skill",
            skill,
            "--fixture",
            "node",
            "--model",
            "requested-model-id",
        ],
        cwd=checkout,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    assert result.returncode == expected_status, result.stdout + result.stderr
    args = (tmp_path / "argv.log").read_text(encoding="utf-8").splitlines()
    assert "--plugin-dir" in args
    selected = args[args.index("--plugin-dir") + 1].replace("\\", "/")
    # Git Bash records MSYS paths; this comparison preserves path-with-spaces
    # evidence without assuming drive-letter spelling.
    assert selected.endswith("/plugin checkout with spaces")
    assert args[args.index("--model") + 1] == "requested-model-id"
    assert (fixture / "index.js").read_text(encoding="utf-8") == "base\n"


def test_worktree_runs_preserve_previous_failed_worktree(tmp_path):
    import sys

    checkout = tmp_path / "checkout"
    (checkout / "scripts").mkdir(parents=True)
    for name in ("test-skills.sh", "skill_test_support.py"):
        shutil.copyfile(ROOT / "scripts" / name, checkout / "scripts" / name)
    fixture = checkout / "test" / "fixtures" / "node-project"
    fixture.mkdir(parents=True)
    (fixture / "index.js").write_text("base\n", encoding="utf-8")
    shutil.copyfile(
        ROOT / "test" / "expected-outputs.yaml",
        checkout / "test" / "expected-outputs.yaml",
    )
    (checkout / ".gitignore").write_text(".worktrees/\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(checkout)], check=True)
    subprocess.run(["git", "-C", str(checkout), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(checkout),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    stub_dir = tmp_path / "stubs"
    stub_dir.mkdir()
    stub = stub_dir / "claude"
    stub.write_text(
        '#!/usr/bin/env bash\nif [ "$1" = "--version" ]; then echo stub-claude; exit 0; fi\nexit 99\n',
        encoding="utf-8",
        newline="\n",
    )
    stub.chmod(0o755)
    bash = _find_bash()
    env = bash_environment(bash)
    env["PATH"] = str(stub_dir) + os.pathsep + env.get("PATH", "")
    env["PYTHON"] = sys.executable.replace("\\", "/")
    command = [
        bash,
        str(checkout / "scripts" / "test-skills.sh"),
        "--worktree",
        "--model",
        "stub",
        "--skill",
        "commit-suggest",
        "--fixture",
    ]
    failed = subprocess.run(
        [*command, "missing"],
        cwd=checkout,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    assert failed.returncode == 1, failed.stdout + failed.stderr
    previous = list((checkout / ".worktrees").glob("skill-tests.*"))
    assert len(previous) == 1
    sentinel = previous[0] / "preserve-me.txt"
    sentinel.write_text("failed-run evidence", encoding="utf-8")
    succeeded = subprocess.run(
        [*command, "node", "--dry-run"],
        cwd=checkout,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    assert succeeded.returncode == 0, succeeded.stdout + succeeded.stderr
    assert "Uncommitted source edits are excluded" in succeeded.stdout
    assert sentinel.read_text(encoding="utf-8") == "failed-run evidence"
    assert list((checkout / ".worktrees").glob("skill-tests.*")) == previous
