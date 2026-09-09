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
        "p = Path('coverage.xml'); "
        "p.write_text(str(int(p.read_text()) + 1) if p.exists() else '1'); "
        "sys.exit(b'BAD' in Path('app.txt').read_bytes())"
    )
    progress = _setup(tmp_path, test_command=command)
    assert (tmp_path / "coverage.xml").is_file()
    assert "created 1 untracked file(s) (coverage.xml)" in capsys.readouterr().out
    # Every command reloads progress from disk, including after a resume.
    assert _cmd(progress, "resume", "--project-dir", str(tmp_path)) == 0
    assert _cmd(progress, "baseline") == 0
    (tmp_path / "app.txt").write_bytes(b"new GOOD\n")
    assert (
        _cmd(progress, "deep-step", "--result-file", _result(tmp_path, _empty_valid()))
        == 0
    )
    assert _cmd(progress, "commit-checkpoint") == 0
    assert (tmp_path / "coverage.xml").read_text() == "3"
    assert _git(tmp_path, "show", "HEAD:app.txt") == b"new GOOD\n"
    assert not _git(tmp_path, "ls-files", "coverage.xml")
    assert _cmd(progress, "baseline") == 0


def test_preexisting_test_report_remains_a_protected_input(tmp_path):
    command = _python_command("Path('coverage.xml').write_text('regenerated')")
    progress = _setup(tmp_path, test_command=command, baseline=False)
    (tmp_path / "coverage.xml").write_text("user report", encoding="utf-8")
    assert _cmd(progress, "baseline") == 1
    assert "coverage.xml" not in json.loads(progress.read_text()).get(
        "_test_outputs", []
    )
    assert _cmd(progress, "commit-checkpoint") == 1


def test_failed_tests_still_record_output_provenance(tmp_path):
    command = _python_command(
        "p = Path('coverage.xml'); "
        "p.write_text(str(int(p.read_text()) + 1) if p.exists() else '1'); "
        "sys.exit(b'BAD' in Path('app.txt').read_bytes())"
    )
    progress = _setup(tmp_path, test_command=command, baseline=False)
    (tmp_path / "app.txt").write_bytes(b"BAD\n")
    assert _cmd(progress, "baseline") == 1
    (tmp_path / "app.txt").write_bytes(b"GOOD\n")
    assert _cmd(progress, "baseline") == 0
    assert (tmp_path / "coverage.xml").read_text() == "2"


def test_no_commit_recovery_preserves_user_work_and_output_provenance(tmp_path):
    command = _python_command(
        "p = Path('coverage.xml'); "
        "p.write_text(str(int(p.read_text()) + 1) if p.exists() else '1'); "
        "sys.exit(b'BAD' in Path('app.txt').read_bytes())"
    )
    progress = _setup(tmp_path, test_command=command, baseline=False)
    data = json.loads(progress.read_text())
    data["config"]["no_commit"] = True
    progress.write_text(json.dumps(data), encoding="utf-8")
    (tmp_path / "app.txt").write_bytes(b"staged GOOD\n")
    _git(tmp_path, "add", "app.txt")
    index_before = _git(tmp_path, "diff", "--cached", "--binary")
    (tmp_path / "app.txt").write_bytes(b"unstaged GOOD\n")
    assert _cmd(progress, "baseline") == 0
    assert _cmd(progress, "snapshot") == 0
    (tmp_path / "app.txt").write_bytes(b"BAD\n")
    assert (
        _cmd(progress, "deep-step", "--result-file", _result(tmp_path, _empty_valid()))
        == 0
    )
    assert (tmp_path / "app.txt").read_bytes() == b"unstaged GOOD\n"
    assert _git(tmp_path, "diff", "--cached", "--binary") == index_before
    assert (tmp_path / "coverage.xml").read_text() == "1"
    assert _cmd(progress, "baseline") == 0
    assert (tmp_path / "coverage.xml").read_text() == "2"


def test_bisection_records_outputs_created_only_by_a_passing_candidate(tmp_path):
    _init_repo(tmp_path)
    (tmp_path / "flag.txt").write_bytes(b"GOOD\n")
    _git(tmp_path, "add", "flag.txt")
    _git(tmp_path, "commit", "-m", "flag")
    command = _python_command(
        "bad = b'BAD' in Path('flag.txt').read_bytes(); "
        "p = Path('candidate.xml'); "
        "(not bad and b'new' in Path('app.txt').read_bytes()) and "
        "p.write_text(str(int(p.read_text()) + 1) if p.exists() else '1'); "
        "sys.exit(bad)"
    )
    progress = _setup(tmp_path, init_repo=False, test_command=command)
    (tmp_path / "app.txt").write_bytes(b"new GOOD\n")
    (tmp_path / "flag.txt").write_bytes(b"BAD\n")
    fixes = [
        dict(
            file=name,
            line=1,
            category="Bug",
            summary=name,
            pre_edit_content="GOOD",
            post_edit_content=post,
        )
        for name, post in (("app.txt", "new GOOD"), ("flag.txt", "BAD"))
    ]
    output = dict(_empty_valid(), new_findings=fixes, fixes_applied=fixes)
    assert _cmd(progress, "deep-step", "--result-file", _result(tmp_path, output)) == 0
    assert (tmp_path / "app.txt").read_text() == "new GOOD\n"
    assert (tmp_path / "flag.txt").read_bytes() == b"GOOD\n"
    assert _cmd(progress, "commit-checkpoint") == 0
    assert not _git(tmp_path, "ls-files", "candidate.xml")


def test_test_output_exclusions_are_literal_paths(tmp_path):
    command = _python_command("Path('run[1].xml').write_text('generated')")
    progress = _setup(tmp_path, test_command=command)
    (tmp_path / "run1.xml").write_text("user input", encoding="utf-8")
    assert _cmd(progress, "baseline") == 0
    data = json.loads(progress.read_text())
    data["config"]["test_command"] = _python_command(
        "Path('run[1].xml').write_text('regenerated'); "
        "Path('run1.xml').write_text('corrupted')"
    )
    progress.write_text(json.dumps(data), encoding="utf-8")
    assert _cmd(progress, "baseline") == 1
    assert _cmd(progress, "commit-checkpoint") == 1


def test_staging_generated_source_revokes_output_exclusion(tmp_path):
    command = _python_command(
        "p = Path('generated.py'); p.exists() or p.write_text('# generated')"
    )
    progress = _setup(tmp_path, test_command=command)
    _git(tmp_path, "add", "generated.py")
    assert _cmd(progress, "baseline") == 0
    assert "generated.py" not in json.loads(progress.read_text())["_test_outputs"]
    assert _cmd(progress, "commit-checkpoint") == 0
    assert _git(tmp_path, "show", "HEAD:generated.py") == b"# generated"


def test_directory_replacing_output_is_a_protected_input(tmp_path):
    progress = _setup(
        tmp_path, test_command=_python_command("Path('report').write_text('output')")
    )
    report = tmp_path / "report"
    report.unlink()
    report.mkdir()
    (report / "source.py").write_text("user source", encoding="utf-8")
    data = json.loads(progress.read_text())
    data["config"]["test_command"] = _python_command(
        "Path('report/source.py').write_text('corrupted')"
    )
    progress.write_text(json.dumps(data), encoding="utf-8")
    assert _cmd(progress, "baseline") == 1
    assert _cmd(progress, "commit-checkpoint") == 1


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


def test_all_skipped_removes_files_the_subagent_created(tmp_path, capsys):
    progress = _setup(tmp_path)
    head = _git(tmp_path, "rev-parse", "HEAD")
    (tmp_path / "app.txt").write_bytes(b"BAD\n")
    (tmp_path / "helper.py").write_bytes(b"# left behind by the subagent\n")
    fix = dict(
        file="app.txt",
        line=1,
        category="Bug",
        summary="fixture",
        pre_edit_content="DOES_NOT_MATCH",
        post_edit_content="BAD",
    )
    output = dict(_empty_valid(), new_findings=[fix], fixes_applied=[fix])
    capsys.readouterr()
    assert _cmd(progress, "deep-step", "--result-file", _result(tmp_path, output)) == 0
    assert "applied fixed=0 reverted=0" in capsys.readouterr().out
    assert (tmp_path / "app.txt").read_bytes() == b"GOOD\n"
    assert not (tmp_path / "helper.py").exists()
    data = json.loads(progress.read_text())
    assert data["findings"][0]["status"].startswith("skipped")
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


def _nested_repository_fixture(tmp_path, kind="submodule"):
    from harness_common.runner import _find_bash, bash_environment

    root = tmp_path / "project"
    root.mkdir()
    _init_repo(root)
    if kind == "submodule":
        upstream = tmp_path / "upstream"
        upstream.mkdir()
        _init_repo(upstream)
        subprocess.run(
            [
                "git",
                "-c",
                "protocol.file.allow=always",
                "submodule",
                "add",
                upstream.as_posix(),
                "library",
            ],
            cwd=root,
            env=bash_environment(_find_bash()),
            capture_output=True,
            check=True,
        )
        _git(root, "commit", "-m", "add library")
    progress = _setup(root, init_repo=False)
    library = root / "library"
    if kind == "nested":
        library.mkdir()
        _init_repo(library)
    _git(library, "config", "user.name", "Fixture")
    _git(library, "config", "user.email", "fixture@example.invalid")
    return root, library, progress


@pytest.mark.parametrize("kind", ["submodule", "nested"])
@pytest.mark.parametrize("operation", ["capture", "restore", "checkpoint"])
def test_dirty_nested_repository_rejected_before_parent_mutation(
    tmp_path, kind, operation
):
    root, library, progress = _nested_repository_fixture(tmp_path, kind)
    head = _git(root, "rev-parse", "HEAD").decode().strip()
    (root / "app.txt").write_bytes(b"staged GOOD\n")
    _git(root, "add", "app.txt")
    (root / "app.txt").write_bytes(b"unstaged GOOD\n")
    (library / "app.txt").write_bytes(b"BAD nested edit\n")
    index_before = _git(root, "diff", "--cached", "--binary")

    if operation == "checkpoint":
        assert (
            git.commit_checkpoint("checkpoint", root, str(progress))
            == git.COMMIT_FAILED
        )
    else:
        with pytest.raises(RuntimeError, match="dirty nested repository"):
            if operation == "capture":
                git.git_stash_snapshot(root)
            else:
                git.git_restore_to(head, root)

    assert _git(root, "rev-parse", "HEAD").decode().strip() == head
    assert _git(root, "diff", "--cached", "--binary") == index_before
    assert (root / "app.txt").read_bytes() == b"unstaged GOOD\n"
    assert (library / "app.txt").read_bytes() == b"BAD nested edit\n"


@pytest.mark.parametrize("no_commit", [False, True])
def test_dirty_submodule_snapshot_keeps_previous_recovery(tmp_path, no_commit):
    root, library, progress = _nested_repository_fixture(tmp_path)
    if no_commit:
        data = json.loads(progress.read_text(encoding="utf-8"))
        data["config"]["no_commit"] = True
        progress.write_text(json.dumps(data), encoding="utf-8")
        (root / "app.txt").write_bytes(b"user GOOD\n")
    assert _cmd(progress, "snapshot") == 0
    previous = json.loads(progress.read_text(encoding="utf-8"))["_snapshot"]
    (library / "app.txt").write_bytes(b"BAD nested edit\n")

    assert _cmd(progress, "snapshot") == 1
    current = json.loads(progress.read_text(encoding="utf-8"))["_snapshot"]
    assert current["pre_stash"] == previous["pre_stash"]
    assert current["pre_head"] == previous["pre_head"]
    assert "iteration_token" not in current
    assert (library / "app.txt").read_bytes() == b"BAD nested edit\n"


def test_dirty_submodule_cannot_authorize_parent_checkpoint(tmp_path):
    root, library, progress = _nested_repository_fixture(tmp_path)
    head = _git(root, "rev-parse", "HEAD")
    (root / "app.txt").write_bytes(b"new GOOD\n")
    (library / "app.txt").write_bytes(b"new GOOD\n")

    assert (
        _cmd(progress, "deep-step", "--result-file", _result(root, _empty_valid())) == 1
    )
    assert _cmd(progress, "commit-checkpoint") == 1
    assert json.loads(progress.read_text(encoding="utf-8"))["_safety_error"]
    assert _git(root, "rev-parse", "HEAD") == head
    assert (root / "app.txt").read_bytes() == b"new GOOD\n"
    assert (library / "app.txt").read_bytes() == b"new GOOD\n"


@pytest.mark.parametrize("stash", [False, True])
def test_changed_submodule_checkout_refuses_restore_before_parent_edits(
    tmp_path, stash
):
    root, library, _progress = _nested_repository_fixture(tmp_path)
    head = _git(root, "rev-parse", "HEAD").decode().strip()
    (root / "app.txt").write_bytes(b"user GOOD\n")
    snapshot = git.git_stash_snapshot(root) if stash else None
    (library / "app.txt").write_bytes(b"committed child change\n")
    _git(library, "add", "app.txt")
    _git(library, "commit", "-m", "move library checkout")
    child_head = _git(library, "rev-parse", "HEAD")
    (root / "app.txt").write_bytes(b"parent iteration edit\n")
    _git(root, "add", "app.txt")
    index_before = _git(root, "diff", "--cached", "--binary")

    with pytest.raises(RuntimeError, match="nested repository checkout"):
        if stash:
            git.git_apply_snapshot(snapshot, root)
        else:
            git.git_restore_to(head, root)

    assert _git(root, "diff", "--cached", "--binary") == index_before
    assert (root / "app.txt").read_bytes() == b"parent iteration edit\n"
    assert _git(library, "rev-parse", "HEAD") == child_head


@pytest.mark.parametrize("move_child_head", [False, True])
def test_clean_submodule_still_allows_checkpoint(tmp_path, move_child_head):
    root, library, progress = _nested_repository_fixture(tmp_path)
    if move_child_head:
        (library / "app.txt").write_bytes(b"committed child change\n")
        _git(library, "add", "app.txt")
        _git(library, "commit", "-m", "advance library")
    child_head = _git(library, "rev-parse", "HEAD").decode().strip()
    (root / "app.txt").write_bytes(b"new GOOD\n")

    assert _cmd(progress, "baseline") == 0
    assert _cmd(progress, "commit-checkpoint") == 0
    assert _git(root, "show", "HEAD:app.txt") == b"new GOOD\n"
    assert _git(root, "rev-parse", "HEAD:library").decode().strip() == child_head


@pytest.mark.parametrize("no_commit", [False, True])
@pytest.mark.parametrize("parent_dirty", [False, True])
def test_unstaged_submodule_checkout_change_cannot_be_snapshotted(
    tmp_path, no_commit, parent_dirty
):
    root, library, progress = _nested_repository_fixture(tmp_path)
    data = json.loads(progress.read_text(encoding="utf-8"))
    previous = data["_snapshot"].copy()
    data["config"]["no_commit"] = no_commit
    progress.write_text(json.dumps(data), encoding="utf-8")
    (library / "app.txt").write_bytes(b"committed child change\n")
    _git(library, "add", "app.txt")
    _git(library, "commit", "-m", "advance library")
    child_head = _git(library, "rev-parse", "HEAD")
    if parent_dirty:
        (root / "app.txt").write_bytes(b"user GOOD\n")
    parent_before = (root / "app.txt").read_bytes()

    assert _cmd(progress, "snapshot") == 1
    current = json.loads(progress.read_text(encoding="utf-8"))["_snapshot"]
    assert current["pre_head"] == previous["pre_head"]
    assert current["pre_stash"] == previous["pre_stash"]
    assert "iteration_token" not in current
    assert _git(library, "rev-parse", "HEAD") == child_head
    assert (root / "app.txt").read_bytes() == parent_before


def test_staged_submodule_update_round_trips_snapshot(tmp_path):
    root, library, _progress = _nested_repository_fixture(tmp_path)
    (library / "app.txt").write_bytes(b"committed child change\n")
    _git(library, "add", "app.txt")
    _git(library, "commit", "-m", "advance library")
    _git(root, "add", "library")
    (root / "app.txt").write_bytes(b"user GOOD\n")
    child_head = _git(library, "rev-parse", "HEAD")
    index_before = _git(root, "diff", "--cached", "--binary")
    snapshot = git.git_stash_snapshot(root)
    (root / "app.txt").write_bytes(b"BAD parent iteration\n")

    assert git.git_apply_snapshot(snapshot, root)
    assert (root / "app.txt").read_bytes() == b"user GOOD\n"
    assert _git(root, "diff", "--cached", "--binary") == index_before
    assert _git(library, "rev-parse", "HEAD") == child_head


def test_parse_failure_with_dirty_submodule_stops_before_parent_restore(tmp_path):
    root, library, progress = _nested_repository_fixture(tmp_path)
    (root / "app.txt").write_bytes(b"staged GOOD\n")
    _git(root, "add", "app.txt")
    (root / "app.txt").write_bytes(b"unstaged GOOD\n")
    (library / "app.txt").write_bytes(b"BAD nested change\n")
    index_before = _git(root, "diff", "--cached", "--binary")
    raw = root / ".claude" / ".deep-iteration-raw.txt"
    raw.write_text("no harness result", encoding="utf-8")

    assert (
        _cmd(
            progress,
            "parse",
            "--input-file",
            str(raw),
            "--output-file",
            _result(root, _empty_valid()),
        )
        == 1
    )
    data = json.loads(progress.read_text(encoding="utf-8"))
    assert "dirty nested repository" in data["_safety_error"]
    assert _git(root, "diff", "--cached", "--binary") == index_before
    assert (root / "app.txt").read_bytes() == b"unstaged GOOD\n"
    assert (library / "app.txt").read_bytes() == b"BAD nested change\n"
    assert _cmd(progress, "snapshot") == 1


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX byte filenames")
def test_non_utf8_nested_repository_name_cannot_bypass_restore_guard(tmp_path):
    import os

    root = tmp_path / "project"
    root.mkdir()
    _setup(root)
    head = _git(root, "rev-parse", "HEAD").decode().strip()
    library = root / os.fsdecode(b"library-\xff")
    library.mkdir()
    _init_repo(library)
    (root / "app.txt").write_bytes(b"user GOOD\n")
    (library / "app.txt").write_bytes(b"BAD nested edit\n")

    with pytest.raises(RuntimeError, match="dirty nested repository"):
        git.git_restore_to(head, root)
    assert (root / "app.txt").read_bytes() == b"user GOOD\n"
    assert (library / "app.txt").read_bytes() == b"BAD nested edit\n"


@pytest.mark.parametrize("flag", ["--assume-unchanged", "--skip-worktree"])
def test_hidden_submodule_edits_block_git_operations_without_changing_flags(
    tmp_path, flag
):
    root, library, progress = _nested_repository_fixture(tmp_path)
    head = _git(root, "rev-parse", "HEAD").decode().strip()
    _git(library, "update-index", flag, "app.txt")
    (library / "app.txt").write_bytes(b"hidden child GOOD\n")
    assert not _git(library, "status", "--porcelain")
    flags_before = _git(library, "ls-files", "-v", "-z")
    (root / "app.txt").write_bytes(b"staged GOOD\n")
    _git(root, "add", "app.txt")
    (root / "app.txt").write_bytes(b"unstaged GOOD\n")
    index_before = _git(root, "diff", "--cached", "--binary")

    with pytest.raises(RuntimeError, match="tracking flags"):
        git.git_test_tree_state(root, str(progress))
    with pytest.raises(RuntimeError, match="tracking flags"):
        git.git_stash_snapshot(root)
    assert git.commit_checkpoint("checkpoint", root, str(progress)) == git.COMMIT_FAILED
    with pytest.raises(RuntimeError, match="tracking flags"):
        git.git_restore_to(head, root)

    assert _git(root, "rev-parse", "HEAD").decode().strip() == head
    assert _git(root, "diff", "--cached", "--binary") == index_before
    assert (root / "app.txt").read_bytes() == b"unstaged GOOD\n"
    assert (library / "app.txt").read_bytes() == b"hidden child GOOD\n"
    assert _git(library, "ls-files", "-v", "-z") == flags_before


def test_hidden_grandchild_edits_cannot_bypass_capture_or_restore(tmp_path):
    from harness_common.runner import _find_bash, bash_environment

    root, library, _progress = _nested_repository_fixture(tmp_path)
    upstream = tmp_path / "leaf-upstream"
    upstream.mkdir()
    _init_repo(upstream)
    subprocess.run(
        [
            "git",
            "-c",
            "protocol.file.allow=always",
            "submodule",
            "add",
            upstream.as_posix(),
            "leaf",
        ],
        cwd=library,
        env=bash_environment(_find_bash()),
        capture_output=True,
        check=True,
    )
    _git(library, "commit", "-m", "add leaf")
    _git(root, "add", "library")
    _git(root, "commit", "-m", "update library")
    head = _git(root, "rev-parse", "HEAD").decode().strip()
    leaf = library / "leaf"
    _git(leaf, "update-index", "--assume-unchanged", "app.txt")
    (leaf / "app.txt").write_bytes(b"hidden leaf GOOD\n")
    assert not _git(library, "status", "--porcelain", "--ignore-submodules=none")
    (root / "app.txt").write_bytes(b"user GOOD\n")

    with pytest.raises(RuntimeError, match="tracking flags"):
        git.git_stash_snapshot(root)
    with pytest.raises(RuntimeError, match="tracking flags"):
        git.git_restore_to(head, root)
    assert (root / "app.txt").read_bytes() == b"user GOOD\n"
    assert (leaf / "app.txt").read_bytes() == b"hidden leaf GOOD\n"
