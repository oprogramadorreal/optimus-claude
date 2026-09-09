"""Composed real-Git regressions: dispatch failures must never reach a commit."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from harness_common import cli, git, reporting


def _git(root, *args):
    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True, check=True
    ).stdout


def _init_repo(root):
    _git(root, "init")
    _git(root, "config", "user.name", "Fixture")
    _git(root, "config", "user.email", "fixture@example.invalid")
    _git(root, "config", "core.autocrlf", "false")
    (root / "app.txt").write_bytes(b"GOOD\n")
    _git(root, "add", "app.txt")
    _git(root, "commit", "-m", "base")


def _python_command(body):
    python = Path(sys.executable).as_posix()
    return f'"{python}" -c "from pathlib import Path; import sys; {body}"'


def _setup(root, *, init_repo=True, test_command=None, baseline=True):
    if init_repo:
        _init_repo(root)
    progress = root / ".claude" / "code-review-deep-progress.json"
    command = test_command or _python_command(
        "sys.exit(b'BAD' in Path('app.txt').read_bytes())"
    )
    assert (
        cli.main(
            [
                "init",
                "--skill",
                "code-review",
                "--project-dir",
                str(root),
                "--test-command",
                command,
                "--progress-file",
                str(progress),
            ]
        )
        == 0
    )
    if baseline:
        assert _cmd(progress, "baseline") == 0
        assert _cmd(progress, "snapshot") == 0
    return progress


def _cmd(progress, command, *args):
    return cli.main([command, "--progress-file", str(progress), *args])


def _result(root, value):
    path = root / ".claude" / ".deep-iteration-result.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return str(path)


def _empty_valid():
    return dict(
        iteration=1,
        new_findings=[],
        fixes_applied=[],
        fixes_skipped_persistent=[],
        no_new_findings=False,
        no_actionable_fixes=False,
    )


def test_empty_object_cannot_commit_unreported_edit(tmp_path):
    progress = _setup(tmp_path)
    head = _git(tmp_path, "rev-parse", "HEAD")
    (tmp_path / "app.txt").write_bytes(b"BAD\n")
    assert _cmd(progress, "deep-step", "--result-file", _result(tmp_path, {})) == 1
    assert _cmd(progress, "commit-checkpoint") == 1
    assert _git(tmp_path, "rev-parse", "HEAD") == head
    assert (tmp_path / "app.txt").read_bytes() == b"BAD\n"
    assert _cmd(progress, "snapshot") == 1
    (tmp_path / "app.txt").write_bytes(b"recovered GOOD\n")
    assert _cmd(progress, "baseline") == 0
    assert _cmd(progress, "snapshot") == 0


def test_valid_no_fix_output_still_tests_and_restores_stray_edits(tmp_path):
    progress = _setup(tmp_path)
    head = _git(tmp_path, "rev-parse", "HEAD")
    (tmp_path / "app.txt").write_bytes(b"BAD\n")
    assert (
        _cmd(progress, "deep-step", "--result-file", _result(tmp_path, _empty_valid()))
        == 0
    )
    assert (tmp_path / "app.txt").read_bytes() == b"GOOD\n"
    assert _cmd(progress, "commit-checkpoint") == 0
    assert _git(tmp_path, "rev-parse", "HEAD") == head


@pytest.mark.parametrize("reported_fix", [False, True])
def test_failed_restore_blocks_checkpoint_and_fresh_snapshot(tmp_path, reported_fix):
    progress = _setup(tmp_path)
    head = _git(tmp_path, "rev-parse", "HEAD")
    (tmp_path / "app.txt").write_bytes(b"BAD\n")
    output = _empty_valid()
    if reported_fix:
        fix = dict(
            file="app.txt",
            line=1,
            category="Bug",
            summary="fixture",
            pre_edit_content="GOOD",
            post_edit_content="BAD",
        )
        output.update(new_findings=[fix], fixes_applied=[fix])
    result = _result(tmp_path, output)
    lock = tmp_path / ".git" / "index.lock"
    lock.write_bytes(b"fixture lock")
    try:
        assert _cmd(progress, "deep-step", "--result-file", result) == 1
    finally:
        lock.unlink()
    assert _cmd(progress, "commit-checkpoint") == 1
    assert _cmd(progress, "snapshot") == 1
    assert _git(tmp_path, "rev-parse", "HEAD") == head
    assert (tmp_path / "app.txt").read_bytes() == b"BAD\n"


def test_checkpoint_requires_same_green_bytes_without_repeating_tests(
    tmp_path, monkeypatch
):
    progress = _setup(tmp_path)
    (tmp_path / "app.txt").write_bytes(b"new GOOD\n")
    assert _cmd(progress, "commit-checkpoint") == 1
    assert _cmd(progress, "baseline") == 0
    (tmp_path / "untracked.txt").write_bytes(b"new work")
    assert _cmd(progress, "commit-checkpoint") == 1
    assert _cmd(progress, "baseline") == 0
    monkeypatch.setattr(
        cli,
        "run_tests",
        lambda *a, **kw: pytest.fail("Checkpoint repeated already-green tests"),
    )
    assert _cmd(progress, "commit-checkpoint") == 0
    assert _git(tmp_path, "show", "HEAD:untracked.txt") == b"new work"
    assert not _git(tmp_path, "ls-tree", "-r", "--name-only", "HEAD", ".claude")


@pytest.mark.parametrize("stage_new_file", [False, True])
def test_snapshot_restores_original_index_and_working_bytes(tmp_path, stage_new_file):
    progress = _setup(tmp_path)
    app = tmp_path / "app.txt"
    app.write_bytes(b"staged GOOD\n")
    _git(tmp_path, "add", "app.txt")
    app.write_bytes(b"unstaged GOOD\n")
    if stage_new_file:
        (tmp_path / "new.txt").write_bytes(b"new staged\n")
        _git(tmp_path, "add", "new.txt")
        (tmp_path / "new.txt").write_bytes(b"new staged plus unstaged\n")
    (tmp_path / "notes.txt").write_bytes(b"user notes\n")
    before_index = _git(tmp_path, "diff", "--cached", "--binary")
    before_files = {
        name: path.read_bytes()
        for name in ("app.txt", "new.txt", "notes.txt")
        if (path := tmp_path / name).exists()
    }
    data = json.loads(progress.read_text(encoding="utf-8"))
    data["config"]["no_commit"] = True
    progress.write_text(json.dumps(data), encoding="utf-8")
    assert _cmd(progress, "snapshot") == 0
    snapshot = json.loads(progress.read_text(encoding="utf-8"))["_snapshot"][
        "pre_stash"
    ]
    app.write_bytes(b"BAD iteration\n")
    (tmp_path / "notes.txt").write_bytes(b"changed by iteration\n")
    (tmp_path / "iteration-only.txt").write_bytes(b"new staged iteration output\n")
    _git(tmp_path, "add", "iteration-only.txt")
    assert git.git_restore_snapshot(snapshot, tmp_path)
    assert not (tmp_path / "iteration-only.txt").exists()
    assert _git(tmp_path, "diff", "--cached", "--binary") == before_index
    for name, content in before_files.items():
        assert (tmp_path / name).read_bytes() == content


def test_full_restore_removes_iteration_only_staged_additions(tmp_path):
    _setup(tmp_path)
    head = _git(tmp_path, "rev-parse", "HEAD").decode().strip()
    (tmp_path / "iteration-only.txt").write_bytes(b"new staged output\n")
    _git(tmp_path, "add", "iteration-only.txt")
    git.git_restore_to(head, tmp_path)
    assert not (tmp_path / "iteration-only.txt").exists()
    assert not _git(tmp_path, "diff", "--cached", "--binary")
    assert _git(tmp_path, "rev-parse", "HEAD").decode().strip() == head


def test_artifacts_created_by_tests_do_not_fail_validation(tmp_path, capsys):
    command = _python_command(
        "Path('coverage.xml').write_text('run'); "
        "sys.exit(b'BAD' in Path('app.txt').read_bytes())"
    )
    progress = _setup(tmp_path, test_command=command)
    assert (tmp_path / "coverage.xml").is_file()
    assert "created 1 untracked file(s) (coverage.xml)" in capsys.readouterr().out
    assert _cmd(progress, "commit-checkpoint") == 0


def test_source_edited_during_tests_fails_validation(tmp_path, capsys):
    command = _python_command("Path('app.txt').write_bytes(b'GOOD edited')")
    progress = _setup(tmp_path, test_command=command, baseline=False)
    assert _cmd(progress, "baseline") == 1
    assert "changed during tests" in capsys.readouterr().out


def test_uninitialized_submodule_does_not_block_baseline(tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    _init_repo(library)
    upstream = tmp_path / "upstream"
    upstream.mkdir()
    _init_repo(upstream)
    _git(
        upstream,
        "-c",
        "protocol.file.allow=always",
        "submodule",
        "add",
        library.as_posix(),
        "library",
    )
    _git(upstream, "commit", "-m", "add submodule")
    clone = tmp_path / "clone"
    subprocess.run(
        ["git", "clone", "-q", upstream.as_posix(), clone.as_posix()], check=True
    )
    assert not (clone / "library" / ".git").exists()
    _git(clone, "config", "user.name", "Fixture")
    _git(clone, "config", "user.email", "fixture@example.invalid")
    _setup(clone, init_repo=False)


def test_all_reverted_removes_files_the_subagent_created(tmp_path, capsys):
    progress = _setup(tmp_path)
    head = _git(tmp_path, "rev-parse", "HEAD")
    (tmp_path / "app.txt").write_bytes(b"BAD\n")
    (tmp_path / "helper.py").write_bytes(b"# left behind by the subagent\n")
    fix = dict(
        file="app.txt",
        line=1,
        category="Bug",
        summary="fixture",
        pre_edit_content="GOOD",
        post_edit_content="BAD",
    )
    output = dict(_empty_valid(), new_findings=[fix], fixes_applied=[fix])
    capsys.readouterr()
    assert _cmd(progress, "deep-step", "--result-file", _result(tmp_path, output)) == 0
    assert "all-reverted" in capsys.readouterr().out
    assert (tmp_path / "app.txt").read_bytes() == b"GOOD\n"
    assert not (tmp_path / "helper.py").exists()
    assert _cmd(progress, "commit-checkpoint") == 0
    assert _git(tmp_path, "rev-parse", "HEAD") == head


def test_resume_after_safety_error_points_to_baseline(tmp_path, capsys):
    progress = _setup(tmp_path)
    (tmp_path / "app.txt").write_bytes(b"BAD\n")
    assert _cmd(progress, "deep-step", "--result-file", _result(tmp_path, {})) == 1
    assert json.loads(progress.read_text(encoding="utf-8"))["_safety_error"]
    capsys.readouterr()
    assert _cmd(progress, "resume", "--project-dir", str(tmp_path)) == 0
    assert "run baseline" in capsys.readouterr().err
    assert _cmd(progress, "snapshot") == 1
    (tmp_path / "app.txt").write_bytes(b"GOOD\n")
    assert _cmd(progress, "baseline") == 0
    assert _cmd(progress, "snapshot") == 0


@pytest.mark.parametrize("mode", ["no_commit", "commit_disabled"])
def test_uncommitted_report_never_suggests_destructive_rollback(mode, capsys):
    progress = {"config": {"base_commit": "abc123"}}
    (progress["config"] if mode == "no_commit" else progress)[mode] = True
    reporting._print_rollback_footer(progress, True)
    output = capsys.readouterr().out
    assert "uncommitted" in output
    assert "reset --hard" not in output
    assert "rebase" not in output
