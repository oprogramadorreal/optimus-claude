"""Execute shipped worktree and TDD Git examples in disposable repositories.

These check command semantics and preservation, not whether a model obeys the
surrounding ownership protocol. Model-level rollback/redaction checks belong in
the audit evaluation plan.
"""

import os
import re
import subprocess
import textwrap
from pathlib import Path

import pytest
from harness_common.runner import _find_bash, bash_environment

ROOT = Path(__file__).resolve().parents[1]
BASH = _find_bash()


@pytest.fixture
def git_project(tmp_path):
    project = tmp_path / "project with spaces"
    project.mkdir()
    environment = bash_environment(BASH)
    for name in list(environment):
        if name.startswith("GIT_"):
            del environment[name]
    environment.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")

    def git(*arguments, check=True):
        return subprocess.run(
            ["git", *arguments],
            cwd=project,
            env=environment,
            capture_output=True,
            check=check,
        )

    git("init")
    git("config", "user.name", "Isolated Skill Test")
    git("config", "user.email", "skill-test@example.invalid")
    git("config", "core.autocrlf", "false")
    git("config", "commit.gpgsign", "false")
    git("commit", "--allow-empty", "-m", "baseline")
    return project, environment, git


def _run_snippet(project, environment, snippet):
    return subprocess.run(
        [BASH, "-c", snippet],
        cwd=project,
        env=environment,
        capture_output=True,
        timeout=30,
    )


def _ignore_snippet():
    source = (ROOT / "skills/worktree/references/worktree-setup.md").read_text(
        encoding="utf-8"
    )
    blocks = re.findall(r"```bash\n(.*?)```", source, re.DOTALL)
    return textwrap.dedent(next(block for block in blocks if "check-ignore" in block))


@pytest.mark.parametrize(
    "initial",
    [
        b"# add .worktrees here later\n",
        b"*.log",  # Missing final newline must not swallow the new rule.
        b".worktrees/\n!.worktrees/\n",
        b".worktrees/\r\n",
    ],
)
def test_worktree_ignore_uses_git_and_preserves_existing_bytes(git_project, initial):
    project, environment, git = git_project
    ignore = project / ".gitignore"
    ignore.write_bytes(initial)
    before = git("check-ignore", "-q", "--", ".worktrees/child", check=False)
    result = _run_snippet(project, environment, _ignore_snippet())
    assert result.returncode == 0, result.stderr
    assert git("check-ignore", "-q", "--", ".worktrees/child").returncode == 0
    expected = initial if before.returncode == 0 else initial + b"\n.worktrees/\n"
    assert ignore.read_bytes() == expected
    assert git("diff", "--cached", "--name-only").stdout == b""
    # A second setup must not append another copy.
    assert _run_snippet(project, environment, _ignore_snippet()).returncode == 0
    assert ignore.read_bytes() == expected


def test_worktree_setup_preserves_staged_and_unstaged_ignore_edits(git_project):
    project, environment, git = git_project
    ignore = project / ".gitignore"
    ignore.write_bytes(b"baseline\n")
    git("add", ".gitignore")
    git("commit", "-m", "ignore baseline")
    ignore.write_bytes(b"baseline\nuser-staged\n")
    git("add", ".gitignore")
    staged = git("show", ":.gitignore").stdout
    ignore.write_bytes(b"baseline\nuser-staged\nuser-unstaged")
    original = ignore.read_bytes()
    result = _run_snippet(project, environment, _ignore_snippet())
    assert result.returncode == 0, result.stderr
    assert git("show", ":.gitignore").stdout == staged
    assert ignore.read_bytes() == original + b"\n.worktrees/\n"


def test_existing_external_ignore_does_not_create_project_config(git_project, tmp_path):
    project, environment, git = git_project
    excludes = tmp_path / "external ignore"
    excludes.write_bytes(b".worktrees/\n")
    git("config", "core.excludesFile", str(excludes))
    result = _run_snippet(project, environment, _ignore_snippet())
    assert result.returncode == 0, result.stderr
    assert not (project / ".gitignore").exists()


def test_ignore_query_failure_does_not_append_rule(git_project):
    project, environment, _ = git_project
    ignore = project / ".gitignore"
    ignore.write_bytes(b"user-rule\n")
    # A repository config failure is not the ordinary check-ignore exit 1.
    (project / ".git/config").write_bytes(b"[malformed\n")
    result = _run_snippet(project, environment, _ignore_snippet())
    assert result.returncode != 0
    assert ignore.read_bytes() == b"user-rule\n"


def test_tdd_exact_path_commit_preserves_unrelated_index_and_worktree(git_project):
    project, environment, git = git_project
    other = project / "user file.txt"
    other.write_bytes(b"baseline\n")
    git("add", "user file.txt")
    git("commit", "-m", "user baseline")
    other.write_bytes(b"staged user edit\n")
    git("add", "user file.txt")
    index_before = git("show", ":user file.txt").stdout
    other.write_bytes(b"unstaged user edit\n")
    (project / "untracked user.txt").write_bytes(b"private draft\n")
    (project / "cycle file.txt").write_bytes(b"owned cycle\n")

    source = (ROOT / "skills/tdd/SKILL.md").read_text(encoding="utf-8")
    add = re.search(r"`(git add -- <owned-files>)`", source).group(1)
    commit = re.search(r"`(git commit --only .*? -- <owned-files>)`", source).group(1)
    for command in [add, commit]:
        command = command.replace("<owned-files>", '"cycle file.txt"')
        command = command.replace("<message>", "feat: cycle")
        result = _run_snippet(project, environment, command)
        assert result.returncode == 0, result.stderr

    assert (
        git("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").stdout
        == b"cycle file.txt\n"
    )
    assert git("show", ":user file.txt").stdout == index_before
    assert other.read_bytes() == b"unstaged user edit\n"
    assert (project / "untracked user.txt").read_bytes() == b"private draft\n"
    assert git("diff", "--cached", "--name-only").stdout == b"user file.txt\n"


def test_paired_refactor_dispatch_names_existing_field_adapter():
    loop = (ROOT / "references/orchestrator-loop-paired.md").read_text(encoding="utf-8")
    dispatch = loop.split("    Phase: refactor\n", 1)[1].split("```", 1)[0]
    adapter = ROOT / "references/coverage-harness-mode.md"
    assert "references/coverage-harness-mode.md" in dispatch
    assert "Refactor Phase Execution" in dispatch
    assert "## Refactor Phase Execution" in adapter.read_text(encoding="utf-8")
