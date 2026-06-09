"""Tests for the orchestrator CLI (`scripts/harness_common/cli.py`)."""

import argparse
import json
import subprocess
from pathlib import Path

import pytest
from harness_common import cli, reporting
from harness_common.constants import (
    COMMIT_COMMITTED,
    COMMIT_FAILED,
    DEFAULT_TEST_TIMEOUT,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(*argv):
    """Invoke cli.main() and return its exit code."""
    return cli.main(list(argv))


def _make_repo(tmp_path, *, head="abc1234567890abc", test_command="npm test"):
    """Initialize a minimal repo-like scaffold with .claude/CLAUDE.md."""
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "CLAUDE.md").write_text(
        f"# Project\n\n```bash\n{test_command}\n```\n",
        encoding="utf-8",
    )
    return tmp_path


def _stub_git(
    monkeypatch, *, head="abc1234567890abc", branch_files=None, pr=None, dirty=False
):
    monkeypatch.setattr(cli, "git_rev_parse_head", lambda _cwd: head)
    monkeypatch.setattr(cli, "get_open_pr_data", lambda _cwd: None)
    monkeypatch.setattr(
        cli,
        "git_discover_branch_files",
        lambda _cwd, path_filter=None, pr_info=None: (
            branch_files or [],
            "origin/main",
        ),
    )
    monkeypatch.setattr(
        cli, "git_fetch_open_pr_description", lambda _cwd, pr_info=None: pr
    )
    monkeypatch.setattr(cli, "git_diff_has_changes", lambda _cwd: dirty)


def _read_progress(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _git_init(tmp_path):
    """Create a real git repo with one commit, for tests that exercise the
    actual git layer instead of stubbing it."""

    def g(*args):
        subprocess.run(
            ["git", *args],
            cwd=str(tmp_path),
            capture_output=True,
            text=True,
            check=True,
        )

    g("init")
    g("config", "user.email", "t@t.test")
    g("config", "user.name", "t")
    (tmp_path / "seed.txt").write_text("seed\n", encoding="utf-8")
    g("add", "seed.txt")
    g("commit", "-m", "base")


# ---------------------------------------------------------------------------
# _progress_path_for_skill (default-path resolution)
# ---------------------------------------------------------------------------


class TestProgressPathForSkill:
    def test_explicit_progress_file_wins(self):
        args = argparse.Namespace(progress_file="out/p.json", skill="code-review")
        assert cli._progress_path_for_skill(args) == Path("out/p.json")

    def test_falls_back_to_skill_default(self):
        # The orchestrator skills always pass --progress-file, but the CLI must
        # still resolve the per-skill default when it is omitted (manual use).
        args = argparse.Namespace(progress_file=None, skill="refactor")
        assert cli._progress_path_for_skill(args) == Path(
            cli.DEFAULT_PROGRESS_FILES["refactor"]
        )

    def test_unknown_skill_without_progress_file_exits(self):
        args = argparse.Namespace(progress_file=None, skill="bogus")
        with pytest.raises(SystemExit):
            cli._progress_path_for_skill(args)


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


class TestInit:
    def test_deep_code_review(self, tmp_path, monkeypatch):
        repo = _make_repo(tmp_path)
        _stub_git(monkeypatch)
        progress_path = repo / "progress.json"
        exit_code = _run(
            "init",
            "--skill",
            "code-review",
            "--progress-file",
            str(progress_path),
            "--project-dir",
            str(repo),
        )
        assert exit_code == 0
        data = _read_progress(progress_path)
        assert data["skill"] == "code-review"
        assert data["iteration"]["current"] == 1
        assert data["config"]["max_iterations"] == 8
        assert data["config"]["test_command"] == "npm test"
        assert data["config"]["focus"] == ""

    def test_deep_refactor_with_focus(self, tmp_path, monkeypatch):
        repo = _make_repo(tmp_path)
        _stub_git(monkeypatch)
        progress_path = repo / "progress.json"
        exit_code = _run(
            "init",
            "--skill",
            "refactor",
            "--focus",
            "testability",
            "--progress-file",
            str(progress_path),
            "--project-dir",
            str(repo),
        )
        assert exit_code == 0
        data = _read_progress(progress_path)
        assert data["config"]["focus"] == "testability"

    def test_deep_focus_rejected_on_code_review(self, tmp_path, monkeypatch, capsys):
        repo = _make_repo(tmp_path)
        _stub_git(monkeypatch)
        progress_path = repo / "progress.json"
        exit_code = _run(
            "init",
            "--skill",
            "code-review",
            "--focus",
            "testability",
            "--progress-file",
            str(progress_path),
            "--project-dir",
            str(repo),
        )
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "focus" in captured.err.lower()

    def test_unknown_skill_errors(self, tmp_path, monkeypatch, capsys):
        # --skill has no argparse `choices` constraint, so an unsupported value
        # reaches cmd_init's membership check; it must fail cleanly and write no
        # progress file. Regression for the unknown-skill guard.
        repo = _make_repo(tmp_path)
        _stub_git(monkeypatch)
        progress_path = repo / "progress.json"
        exit_code = _run(
            "init",
            "--skill",
            "bad-skill",
            "--progress-file",
            str(progress_path),
            "--project-dir",
            str(repo),
        )
        assert exit_code == 1
        assert "Unknown skill" in capsys.readouterr().err
        assert not progress_path.exists()

    def test_deep_invalid_focus(self, tmp_path, monkeypatch, capsys):
        repo = _make_repo(tmp_path)
        _stub_git(monkeypatch)
        progress_path = repo / "progress.json"
        exit_code = _run(
            "init",
            "--skill",
            "refactor",
            "--focus",
            "speedup",
            "--progress-file",
            str(progress_path),
            "--project-dir",
            str(repo),
        )
        assert exit_code == 1

    def test_no_test_command(self, tmp_path, monkeypatch, capsys):
        repo = tmp_path
        (repo / ".claude").mkdir()
        (repo / ".claude" / "CLAUDE.md").write_text(
            "# no test command", encoding="utf-8"
        )
        _stub_git(monkeypatch)
        progress_path = repo / "progress.json"
        exit_code = _run(
            "init",
            "--skill",
            "code-review",
            "--progress-file",
            str(progress_path),
            "--project-dir",
            str(repo),
        )
        assert exit_code == 1
        assert "No test command" in capsys.readouterr().err

    def test_coverage_init(self, tmp_path, monkeypatch):
        repo = _make_repo(tmp_path)
        _stub_git(monkeypatch)
        progress_path = repo / "progress.json"
        exit_code = _run(
            "init",
            "--skill",
            "unit-test",
            "--progress-file",
            str(progress_path),
            "--project-dir",
            str(repo),
        )
        assert exit_code == 0
        data = _read_progress(progress_path)
        assert data["harness"] == "test-coverage"
        assert data["cycle"]["current"] == 1
        assert data["config"]["max_cycles"] == 5
        # The refactor phase resolves its finding-cap focus from config.focus
        # (references/harness-mode.md step 1); the coverage variant always runs
        # its refactor phase for testability, so init must pin it.
        assert data["config"]["focus"] == "testability"

    def test_max_iterations_clamp_high(self, tmp_path, monkeypatch):
        repo = _make_repo(tmp_path)
        _stub_git(monkeypatch)
        progress_path = repo / "progress.json"
        _run(
            "init",
            "--skill",
            "code-review",
            "--max-iterations",
            "99",
            "--progress-file",
            str(progress_path),
            "--project-dir",
            str(repo),
        )
        data = _read_progress(progress_path)
        assert data["config"]["max_iterations"] == 20  # hard cap

    def test_max_cycles_clamp_low(self, tmp_path, monkeypatch):
        repo = _make_repo(tmp_path)
        _stub_git(monkeypatch)
        progress_path = repo / "progress.json"
        _run(
            "init",
            "--skill",
            "unit-test",
            "--max-cycles",
            "0",
            "--progress-file",
            str(progress_path),
            "--project-dir",
            str(repo),
        )
        data = _read_progress(progress_path)
        assert data["config"]["max_cycles"] == 1

    def test_deep_branch_scope_population(self, tmp_path, monkeypatch):
        repo = _make_repo(tmp_path)
        _stub_git(monkeypatch, branch_files=["src/a.py", "src/b.py"])
        progress_path = repo / "progress.json"
        _run(
            "init",
            "--skill",
            "code-review",
            "--progress-file",
            str(progress_path),
            "--project-dir",
            str(repo),
        )
        data = _read_progress(progress_path)
        assert data["scope_files"]["current"] == ["src/a.py", "src/b.py"]
        assert data["config"]["scope"]["base_ref"] == "origin/main"

    def test_deep_pr_description_capture(self, tmp_path, monkeypatch):
        repo = _make_repo(tmp_path)
        _stub_git(
            monkeypatch,
            pr={"title": "Test PR", "body": "Body", "base_ref": "origin/main"},
        )
        progress_path = repo / "progress.json"
        _run(
            "init",
            "--skill",
            "code-review",
            "--progress-file",
            str(progress_path),
            "--project-dir",
            str(repo),
        )
        data = _read_progress(progress_path)
        assert data["config"]["pr_description"]["title"] == "Test PR"

    def test_deep_natural_language_scope(self, tmp_path, monkeypatch):
        # Regression for c53086d: non-existent scope is treated as prose, not
        # a git pathspec, so config.scope.mode stays "branch-diff" and the
        # natural-language text is preserved in scope_text.
        repo = _make_repo(tmp_path)
        _stub_git(monkeypatch)
        progress_path = repo / "progress.json"
        _run(
            "init",
            "--skill",
            "code-review",
            "--scope",
            "focus on src/auth",
            "--progress-file",
            str(progress_path),
            "--project-dir",
            str(repo),
        )
        data = _read_progress(progress_path)
        assert data["config"]["scope"]["mode"] == "branch-diff"
        assert data["config"]["scope"]["paths"] == []
        assert data["config"]["scope"]["scope_text"] == "focus on src/auth"

    def test_deep_path_scope_existing(self, tmp_path, monkeypatch):
        # Complement to test_deep_natural_language_scope: when --scope points
        # at an existing directory, it is treated as a git pathspec.
        repo = _make_repo(tmp_path)
        (repo / "src").mkdir()
        _stub_git(monkeypatch)
        progress_path = repo / "progress.json"
        _run(
            "init",
            "--skill",
            "code-review",
            "--scope",
            "src",
            "--progress-file",
            str(progress_path),
            "--project-dir",
            str(repo),
        )
        data = _read_progress(progress_path)
        assert data["config"]["scope"]["mode"] == "directory"
        assert data["config"]["scope"]["paths"] == ["src"]
        assert data["config"]["scope"]["scope_text"] is None

    def test_deep_absolute_path_outside_project_falls_back_to_branch_diff(
        self, tmp_path, monkeypatch
    ):
        # Regression for 310c928: an absolute path scope (e.g. "/etc",
        # "C:\\Windows") must not be treated as a git pathspec. Path semantics
        # let `project_root / "/etc"` collapse to `/etc`, and without the
        # containment check the loop would silently `git diff -- /etc` (empty)
        # and run with no scope.
        repo = _make_repo(tmp_path)
        _stub_git(monkeypatch)
        progress_path = repo / "progress.json"
        outside = str(tmp_path.anchor or "/") + "definitely-not-in-this-repo"
        _run(
            "init",
            "--skill",
            "code-review",
            "--scope",
            outside,
            "--progress-file",
            str(progress_path),
            "--project-dir",
            str(repo),
        )
        data = _read_progress(progress_path)
        assert data["config"]["scope"]["mode"] == "branch-diff"
        assert data["config"]["scope"]["paths"] == []
        assert data["config"]["scope"]["scope_text"] == outside

    def test_init_aborts_when_head_undeterminable(self, tmp_path, monkeypatch, capsys):
        # cmd_init must exit 1 without writing a progress file when HEAD cannot
        # be resolved — the git-side twin of the tested "no test command" abort.
        repo = _make_repo(tmp_path)
        _stub_git(monkeypatch)
        monkeypatch.setattr(cli, "git_rev_parse_head", lambda _cwd: None)
        progress_path = repo / "progress.json"
        exit_code = _run(
            "init",
            "--skill",
            "code-review",
            "--progress-file",
            str(progress_path),
            "--project-dir",
            str(repo),
        )
        assert exit_code == 1
        assert "Cannot determine HEAD" in capsys.readouterr().err
        assert not progress_path.exists()

    def test_refuses_dirty_tree_on_fresh_run(self, tmp_path, monkeypatch, capsys):
        # A fresh (non --no-commit) run must refuse a dirty tree so the user's
        # uncommitted work isn't folded into the iteration-1 checkpoint commit.
        repo = _make_repo(tmp_path)
        _stub_git(monkeypatch, dirty=True)
        progress_path = repo / "progress.json"
        exit_code = _run(
            "init",
            "--skill",
            "code-review",
            "--progress-file",
            str(progress_path),
            "--project-dir",
            str(repo),
        )
        assert exit_code == 1
        assert "uncommitted changes" in capsys.readouterr().err
        assert not progress_path.exists()

    def test_dirty_tree_allowed_with_no_commit(self, tmp_path, monkeypatch):
        repo = _make_repo(tmp_path)
        _stub_git(monkeypatch, dirty=True)
        progress_path = repo / "progress.json"
        exit_code = _run(
            "init",
            "--skill",
            "code-review",
            "--no-commit",
            "--progress-file",
            str(progress_path),
            "--project-dir",
            str(repo),
        )
        assert exit_code == 0
        assert _read_progress(progress_path)["config"]["no_commit"] is True

    def test_fetches_pr_data_once_and_threads_it(self, tmp_path, monkeypatch):
        # CL1: init fetches open-PR data once via get_open_pr_data and threads it
        # into both branch discovery and the description builder, rather than
        # each re-shelling out to `gh pr view`.
        repo = _make_repo(tmp_path)
        sentinel = {"state": "OPEN", "baseRefName": "main", "title": "T", "body": "B"}
        calls = {"fetch": 0}
        received = {}

        def _fake_get(_cwd):
            calls["fetch"] += 1
            return sentinel

        def _fake_discover(_cwd, path_filter=None, pr_info=None):
            received["discover"] = pr_info
            return [], "origin/main"

        def _fake_desc(_cwd, pr_info=None):
            received["desc"] = pr_info
            return None

        monkeypatch.setattr(cli, "git_rev_parse_head", lambda _cwd: "abc1234")
        monkeypatch.setattr(cli, "git_diff_has_changes", lambda _cwd: False)
        monkeypatch.setattr(cli, "get_open_pr_data", _fake_get)
        monkeypatch.setattr(cli, "git_discover_branch_files", _fake_discover)
        monkeypatch.setattr(cli, "git_fetch_open_pr_description", _fake_desc)
        progress_path = repo / "progress.json"
        exit_code = _run(
            "init",
            "--skill",
            "code-review",
            "--progress-file",
            str(progress_path),
            "--project-dir",
            str(repo),
        )
        assert exit_code == 0
        assert calls["fetch"] == 1
        assert received["discover"] is sentinel
        assert received["desc"] is sentinel

    def test_refuses_to_overwrite_existing_progress(
        self, tmp_path, monkeypatch, capsys
    ):
        # Regression: a second `init` without --force must NOT silently wipe
        # the prior run's findings. The orchestrator must explicitly choose
        # between --resume (continue) and --force (discard).
        repo = _make_repo(tmp_path)
        _stub_git(monkeypatch)
        progress_path = repo / "progress.json"
        _run(
            "init",
            "--skill",
            "code-review",
            "--progress-file",
            str(progress_path),
            "--project-dir",
            str(repo),
        )
        # Mark the existing progress so we can confirm it survived.
        data = _read_progress(progress_path)
        data["findings"] = [{"sentinel": "prior-run"}]
        progress_path.write_text(json.dumps(data), encoding="utf-8")

        exit_code = _run(
            "init",
            "--skill",
            "code-review",
            "--progress-file",
            str(progress_path),
            "--project-dir",
            str(repo),
        )
        assert exit_code == 1
        err = capsys.readouterr().err
        assert "already exists" in err
        assert "--resume" in err
        assert "--force" in err
        # Prior progress untouched.
        assert _read_progress(progress_path)["findings"] == [{"sentinel": "prior-run"}]

    def test_force_overwrites_existing_progress(self, tmp_path, monkeypatch):
        repo = _make_repo(tmp_path)
        _stub_git(monkeypatch)
        progress_path = repo / "progress.json"
        _run(
            "init",
            "--skill",
            "code-review",
            "--progress-file",
            str(progress_path),
            "--project-dir",
            str(repo),
        )
        data = _read_progress(progress_path)
        data["findings"] = [{"sentinel": "prior-run"}]
        progress_path.write_text(json.dumps(data), encoding="utf-8")

        exit_code = _run(
            "init",
            "--skill",
            "code-review",
            "--progress-file",
            str(progress_path),
            "--project-dir",
            str(repo),
            "--force",
        )
        assert exit_code == 0
        # New progress replaces the old (empty findings, fresh iteration).
        new_data = _read_progress(progress_path)
        assert new_data["findings"] == []
        assert new_data["iteration"]["current"] == 1


# ---------------------------------------------------------------------------
# resume
# ---------------------------------------------------------------------------


class TestResume:
    def test_success(self, tmp_path, capsys):
        progress_path = tmp_path / "progress.json"
        progress_path.write_text(
            json.dumps(
                {"skill": "code-review", "config": {"project_root": str(tmp_path)}}
            ),
            encoding="utf-8",
        )
        exit_code = _run(
            "resume",
            "--progress-file",
            str(progress_path),
            "--project-dir",
            str(tmp_path),
        )
        assert exit_code == 0
        assert capsys.readouterr().out.strip() == "code-review"

    def test_missing_file(self, tmp_path, capsys):
        exit_code = _run(
            "resume",
            "--progress-file",
            str(tmp_path / "no_such.json"),
        )
        assert exit_code == 1
        assert "No progress file" in capsys.readouterr().err

    def test_project_root_mismatch(self, tmp_path, capsys):
        progress_path = tmp_path / "progress.json"
        progress_path.write_text(
            json.dumps({"skill": "code-review", "config": {"project_root": "/other"}}),
            encoding="utf-8",
        )
        exit_code = _run(
            "resume",
            "--progress-file",
            str(progress_path),
            "--project-dir",
            str(tmp_path),
        )
        assert exit_code == 1

    def test_restores_from_backup(self, tmp_path, capsys):
        progress_path = tmp_path / "progress.json"
        backup = tmp_path / "progress.json.bak"
        backup.write_text(
            json.dumps(
                {"skill": "refactor", "config": {"project_root": str(tmp_path)}}
            ),
            encoding="utf-8",
        )
        exit_code = _run(
            "resume",
            "--progress-file",
            str(progress_path),
            "--project-dir",
            str(tmp_path),
        )
        assert exit_code == 0
        assert progress_path.exists()
        # The restored file must carry the backup's content, not an empty stub.
        assert _read_progress(progress_path)["skill"] == "refactor"

    def test_corrupt_progress_file_fails_cleanly(self, tmp_path, capsys):
        # cmd_resume must surface a readable error (not a raw traceback) when
        # the progress file is unreadable JSON.
        progress_path = tmp_path / "progress.json"
        progress_path.write_text("{not valid json", encoding="utf-8")
        exit_code = _run(
            "resume",
            "--progress-file",
            str(progress_path),
            "--project-dir",
            str(tmp_path),
        )
        assert exit_code == 1
        assert "Cannot read progress file" in capsys.readouterr().err

    def test_missing_required_field_fails(self, tmp_path, capsys):
        # A progress file missing required `skill` or `config` is malformed —
        # resume must reject it instead of proceeding with undefined state.
        progress_path = tmp_path / "progress.json"
        progress_path.write_text(
            json.dumps({"skill": "code-review"}),  # no config
            encoding="utf-8",
        )
        exit_code = _run(
            "resume",
            "--progress-file",
            str(progress_path),
            "--project-dir",
            str(tmp_path),
        )
        assert exit_code == 1
        err = capsys.readouterr().err
        assert "missing" in err.lower() or "invalid" in err.lower()

    def test_clears_diminishing_returns_termination(self, tmp_path):
        # A diminishing-returns soft-exit leaves the file resumable. Resuming
        # must clear the stored termination so check-termination re-evaluates
        # instead of immediately re-emitting it (otherwise --resume quits at once).
        progress_path = tmp_path / "progress.json"
        progress_path.write_text(
            json.dumps(
                {
                    "skill": "code-review",
                    "config": {"project_root": str(tmp_path), "max_iterations": 8},
                    "termination": {
                        "reason": "diminishing-returns",
                        "message": "plateaued",
                    },
                }
            ),
            encoding="utf-8",
        )
        exit_code = _run(
            "resume",
            "--progress-file",
            str(progress_path),
            "--project-dir",
            str(tmp_path),
        )
        assert exit_code == 0
        assert _read_progress(progress_path)["termination"]["reason"] is None

    def test_advances_iteration_on_resume_after_termination(self, tmp_path):
        # A terminated run exits before step 8 (`advance`), so iteration.current
        # still points at the just-completed iteration. Resuming must bump it so
        # the loop continues at the next iteration instead of re-dispatching the
        # same number. Regression for the resume-counter off-by-one.
        progress_path = tmp_path / "progress.json"
        progress_path.write_text(
            json.dumps(
                {
                    "skill": "code-review",
                    "config": {"project_root": str(tmp_path), "max_iterations": 12},
                    "iteration": {"current": 8, "completed": 7},
                    "termination": {"reason": "cap", "message": "Reached cap (8)"},
                }
            ),
            encoding="utf-8",
        )
        exit_code = _run(
            "resume",
            "--progress-file",
            str(progress_path),
            "--project-dir",
            str(tmp_path),
            "--max-iterations",
            "12",
        )
        assert exit_code == 0
        assert _read_progress(progress_path)["iteration"]["current"] == 9

    def test_does_not_advance_iteration_on_mid_iteration_resume(self, tmp_path):
        # A mid-iteration Ctrl-C leaves no termination reason; the interrupted
        # iteration must be re-run, so the counter must stay put.
        progress_path = tmp_path / "progress.json"
        progress_path.write_text(
            json.dumps(
                {
                    "skill": "code-review",
                    "config": {"project_root": str(tmp_path), "max_iterations": 12},
                    "iteration": {"current": 8, "completed": 7},
                    "termination": {"reason": None, "message": None},
                }
            ),
            encoding="utf-8",
        )
        exit_code = _run(
            "resume",
            "--progress-file",
            str(progress_path),
            "--project-dir",
            str(tmp_path),
        )
        assert exit_code == 0
        assert _read_progress(progress_path)["iteration"]["current"] == 8

    def test_raises_iteration_cap(self, tmp_path):
        # The documented "--resume --max-iterations <new-cap>" must raise the
        # persisted cap so the loop can continue past the prior limit.
        progress_path = tmp_path / "progress.json"
        progress_path.write_text(
            json.dumps(
                {
                    "skill": "code-review",
                    "config": {"project_root": str(tmp_path), "max_iterations": 8},
                }
            ),
            encoding="utf-8",
        )
        exit_code = _run(
            "resume",
            "--progress-file",
            str(progress_path),
            "--project-dir",
            str(tmp_path),
            "--max-iterations",
            "15",
        )
        assert exit_code == 0
        assert _read_progress(progress_path)["config"]["max_iterations"] == 15

    def test_resume_cap_clamped_to_hard_cap(self, tmp_path):
        progress_path = tmp_path / "progress.json"
        progress_path.write_text(
            json.dumps(
                {
                    "skill": "code-review",
                    "config": {"project_root": str(tmp_path), "max_iterations": 8},
                }
            ),
            encoding="utf-8",
        )
        _run(
            "resume",
            "--progress-file",
            str(progress_path),
            "--project-dir",
            str(tmp_path),
            "--max-iterations",
            "999",
        )
        assert _read_progress(progress_path)["config"]["max_iterations"] == 20

    def test_raises_cycle_cap(self, tmp_path):
        # Coverage-variant twin of test_raises_iteration_cap (unit-test-deep).
        progress_path = tmp_path / "progress.json"
        progress_path.write_text(
            json.dumps(
                {
                    "skill": "unit-test",
                    "config": {"project_root": str(tmp_path), "max_cycles": 5},
                }
            ),
            encoding="utf-8",
        )
        exit_code = _run(
            "resume",
            "--progress-file",
            str(progress_path),
            "--project-dir",
            str(tmp_path),
            "--max-cycles",
            "8",
        )
        assert exit_code == 0
        assert _read_progress(progress_path)["config"]["max_cycles"] == 8


# ---------------------------------------------------------------------------
# parse
# ---------------------------------------------------------------------------


class TestParse:
    def test_extracts_json_block(self, tmp_path, capsys):
        raw = tmp_path / "raw.txt"
        raw.write_text(
            "Some preamble text.\n\n"
            "```json:harness-output\n"
            '{"iteration": 1, "new_findings": []}\n'
            "```\n",
            encoding="utf-8",
        )
        exit_code = _run("parse", "--input-file", str(raw))
        assert exit_code == 0
        parsed = json.loads(capsys.readouterr().out)
        assert parsed["iteration"] == 1

    def test_missing_block(self, tmp_path, capsys):
        raw = tmp_path / "raw.txt"
        raw.write_text("Just some text, no JSON block.", encoding="utf-8")
        exit_code = _run("parse", "--input-file", str(raw))
        assert exit_code == 1

    def test_output_file(self, tmp_path):
        raw = tmp_path / "raw.txt"
        raw.write_text(
            "```json:harness-output\n" '{"iteration": 1}\n' "```\n",
            encoding="utf-8",
        )
        out = tmp_path / "out.json"
        _run("parse", "--input-file", str(raw), "--output-file", str(out))
        assert json.loads(out.read_text(encoding="utf-8"))["iteration"] == 1

    def test_missing_input_file_emits_error(self, tmp_path, capsys):
        # Regression for 9e0553a: read_text wrapped in try/except OSError so
        # parse-failure recovery sees a clean stderr + exit 1 instead of a raw
        # traceback.
        exit_code = _run("parse", "--input-file", str(tmp_path / "no_such.txt"))
        assert exit_code == 1
        assert "Cannot read" in capsys.readouterr().err

    def test_corrupt_progress_file_does_not_crash(self, tmp_path, capsys):
        # When --progress-file points at a corrupt file, cmd_parse must skip the
        # failure-count update (read_progress raises → progress=None) instead of
        # crashing, and must not rewrite the unreadable file. Regression for the
        # try/except (ValueError, OSError) guard in cmd_parse.
        raw = tmp_path / "raw.txt"
        raw.write_text("No JSON block here.", encoding="utf-8")
        progress_path = tmp_path / "progress.json"
        progress_path.write_text("{ not valid json", encoding="utf-8")
        exit_code = _run(
            "parse",
            "--input-file",
            str(raw),
            "--progress-file",
            str(progress_path),
        )
        assert exit_code == 1
        assert "No json:harness-output block" in capsys.readouterr().err
        # The corrupt file is left untouched (no counter write).
        assert progress_path.read_text(encoding="utf-8") == "{ not valid json"

    def test_output_file_write_failure_is_handled(self, tmp_path, capsys):
        # A failure writing --output-file must surface a clean error and exit 1,
        # not a raw traceback. Regression for the try/except around the write.
        raw = tmp_path / "raw.txt"
        raw.write_text(
            '```json:harness-output\n{"iteration": 1}\n```\n', encoding="utf-8"
        )
        bad_output = tmp_path / "no_such_dir" / "out.json"  # parent dir is missing
        exit_code = _run(
            "parse",
            "--input-file",
            str(raw),
            "--output-file",
            str(bad_output),
        )
        assert exit_code == 1
        assert "Cannot write" in capsys.readouterr().err

    def test_parse_failure_rolls_back_partial_edits(self, tmp_path, monkeypatch):
        # A parse failure must roll the working tree back to this iteration's
        # snapshot so the failed dispatch leaves no partial edits behind.
        raw = tmp_path / "raw.txt"
        raw.write_text("No JSON block here.", encoding="utf-8")
        progress_path = tmp_path / "progress.json"
        progress_path.write_text(
            json.dumps(
                {
                    "skill": "code-review",
                    "config": {"project_root": str(tmp_path)},
                    "iteration": {"current": 3},
                    "parse_failure_count": 0,
                    "_snapshot": {
                        "iteration_token": 3,
                        "pre_head": "deadbeef",
                        "pre_stash": None,
                    },
                }
            ),
            encoding="utf-8",
        )
        calls = []
        monkeypatch.setattr(
            cli,
            "restore_working_tree",
            lambda stash, head, _root: calls.append((stash, head)),
        )
        exit_code = _run(
            "parse",
            "--input-file",
            str(raw),
            "--progress-file",
            str(progress_path),
        )
        assert exit_code == 1
        assert calls == [(None, "deadbeef")]
        assert _read_progress(progress_path)["parse_failure_count"] == 1

    def test_parse_failure_rollback_exception_is_swallowed(self, tmp_path, monkeypatch):
        # If restore_working_tree itself raises mid-rollback (e.g. git missing),
        # the best-effort except (RuntimeError, OSError) must swallow it: the
        # failure count is still recorded and the command exits 1 cleanly rather
        # than surfacing a traceback.
        raw = tmp_path / "raw.txt"
        raw.write_text("No JSON block here.", encoding="utf-8")
        progress_path = tmp_path / "progress.json"
        progress_path.write_text(
            json.dumps(
                {
                    "skill": "code-review",
                    "config": {"project_root": str(tmp_path)},
                    "iteration": {"current": 3},
                    "parse_failure_count": 0,
                    "_snapshot": {
                        "iteration_token": 3,
                        "pre_head": "deadbeef",
                        "pre_stash": None,
                    },
                }
            ),
            encoding="utf-8",
        )

        def _boom(_stash, _head, _root):
            raise RuntimeError("git binary missing")

        monkeypatch.setattr(cli, "restore_working_tree", _boom)
        exit_code = _run(
            "parse",
            "--input-file",
            str(raw),
            "--progress-file",
            str(progress_path),
        )
        assert exit_code == 1
        assert _read_progress(progress_path)["parse_failure_count"] == 1

    def test_parse_failure_no_rollback_when_snapshot_stale(self, tmp_path, monkeypatch):
        # A snapshot token from a prior iteration must NOT trigger a restore —
        # restoring to a stale state would revert to the wrong commit.
        raw = tmp_path / "raw.txt"
        raw.write_text("No JSON block here.", encoding="utf-8")
        progress_path = tmp_path / "progress.json"
        progress_path.write_text(
            json.dumps(
                {
                    "skill": "code-review",
                    "config": {"project_root": str(tmp_path)},
                    "iteration": {"current": 5},
                    "parse_failure_count": 0,
                    "_snapshot": {"iteration_token": 2, "pre_head": "old"},
                }
            ),
            encoding="utf-8",
        )
        called = []
        monkeypatch.setattr(cli, "restore_working_tree", lambda *a: called.append(a))
        exit_code = _run(
            "parse",
            "--input-file",
            str(raw),
            "--progress-file",
            str(progress_path),
        )
        assert exit_code == 1
        assert called == []  # stale snapshot → no restore
        assert _read_progress(progress_path)["parse_failure_count"] == 1

    def test_progress_file_increments_failure_counter(self, tmp_path):
        # When --progress-file is supplied and the parse fails, the CLI must
        # bump parse_failure_count so cross-iteration "two failures →
        # terminate" can be detected after --resume.
        raw = tmp_path / "raw.txt"
        raw.write_text("No JSON here.", encoding="utf-8")
        progress_path = tmp_path / "progress.json"
        progress_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "skill": "code-review",
                    "parse_failure_count": 0,
                }
            ),
            encoding="utf-8",
        )
        _run(
            "parse",
            "--input-file",
            str(raw),
            "--progress-file",
            str(progress_path),
        )
        assert _read_progress(progress_path)["parse_failure_count"] == 1
        # Second failure increments to 2.
        _run(
            "parse",
            "--input-file",
            str(raw),
            "--progress-file",
            str(progress_path),
        )
        assert _read_progress(progress_path)["parse_failure_count"] == 2

    def test_progress_file_resets_counter_on_success(self, tmp_path):
        # An isolated single failure must not poison a later good iteration:
        # a successful parse resets parse_failure_count to 0.
        raw_good = tmp_path / "good.txt"
        raw_good.write_text(
            "```json:harness-output\n" '{"iteration": 1}\n' "```\n",
            encoding="utf-8",
        )
        progress_path = tmp_path / "progress.json"
        progress_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "skill": "code-review",
                    "parse_failure_count": 1,
                }
            ),
            encoding="utf-8",
        )
        _run(
            "parse",
            "--input-file",
            str(raw_good),
            "--progress-file",
            str(progress_path),
        )
        assert _read_progress(progress_path)["parse_failure_count"] == 0

    def test_progress_file_missing_is_tolerated(self, tmp_path):
        # If --progress-file is supplied but doesn't exist yet, parse still
        # works — the orchestrator's init step will create it later.
        raw = tmp_path / "raw.txt"
        raw.write_text(
            "```json:harness-output\n" '{"iteration": 1}\n' "```\n",
            encoding="utf-8",
        )
        exit_code = _run(
            "parse",
            "--input-file",
            str(raw),
            "--progress-file",
            str(tmp_path / "no_such.json"),
        )
        assert exit_code == 0

    def test_failure_counter_survives_resume(self, tmp_path, capsys):
        # End-to-end regression for PR #140's claim: parse_failure_count must
        # survive a --resume between two failed iterations. Sequence:
        #   1. parse fails → counter = 1
        #   2. resume (re-reads progress from disk) — counter must persist
        #   3. parse fails → counter = 2
        #   4. check-termination → must surface "parse-failure"
        raw = tmp_path / "raw.txt"
        raw.write_text("No JSON block here.", encoding="utf-8")
        progress_path = tmp_path / "progress.json"
        progress_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "skill": "code-review",
                    "config": {"project_root": str(tmp_path)},
                    "parse_failure_count": 0,
                    "termination": {"reason": None, "message": None},
                }
            ),
            encoding="utf-8",
        )

        _run(
            "parse",
            "--input-file",
            str(raw),
            "--progress-file",
            str(progress_path),
        )
        assert _read_progress(progress_path)["parse_failure_count"] == 1

        # Simulate a --resume between failures (the orchestrator was
        # cancelled and re-launched). Counter must persist across this call.
        exit_code = _run(
            "resume",
            "--progress-file",
            str(progress_path),
            "--project-dir",
            str(tmp_path),
        )
        assert exit_code == 0
        assert _read_progress(progress_path)["parse_failure_count"] == 1
        capsys.readouterr()  # drain "code-review" line printed by resume

        _run(
            "parse",
            "--input-file",
            str(raw),
            "--progress-file",
            str(progress_path),
        )
        assert _read_progress(progress_path)["parse_failure_count"] == 2

        exit_code = _run("check-termination", "--progress-file", str(progress_path))
        assert exit_code == 0
        assert capsys.readouterr().out.strip() == "parse-failure"


# ---------------------------------------------------------------------------
# deep-step
# ---------------------------------------------------------------------------


def _seed_deep_progress(tmp_path, *, iteration=1, scope_files=None):
    progress = {
        "schema_version": 1,
        "skill": "code-review",
        "started_at": "2025-01-01T00:00:00Z",
        "config": {
            "max_iterations": 8,
            "test_command": "npm test",
            "scope": {"mode": "local-changes", "paths": [], "base_ref": None},
            "project_root": str(tmp_path),
            "base_commit": "abc1234",
            "focus": "",
            "pr_description": None,
        },
        "iteration": {"current": iteration, "completed": iteration - 1},
        "findings": [],
        "scope_files": {"current": scope_files or []},
        "test_results": {"last_full_run": None, "last_run_output_summary": None},
        "iteration_history": [],
        "termination": {"reason": None, "message": None},
        "_snapshot": {
            "pre_head": "abc1234",
            "pre_stash": None,
            "iteration_token": iteration,
        },
    }
    path = tmp_path / "progress.json"
    path.write_text(json.dumps(progress, indent=2), encoding="utf-8")
    return path


def _one_fix_result():
    """A deep-step result JSON with a single actionable fix (triggers a test run)."""
    fix = {
        "file": "a.py",
        "line": 1,
        "category": "x",
        "summary": "s",
        "pre_edit_content": "a",
        "post_edit_content": "b",
    }
    return {
        "iteration": 1,
        "new_findings": [fix],
        "fixes_applied": [fix],
        "no_new_findings": False,
        "no_actionable_fixes": False,
    }


class TestDeepStep:
    def test_convergence(self, tmp_path, capsys):
        ppath = _seed_deep_progress(tmp_path)
        result = tmp_path / "result.json"
        result.write_text(
            json.dumps(
                {
                    "iteration": 1,
                    "new_findings": [],
                    "fixes_applied": [],
                    "no_new_findings": True,
                    "no_actionable_fixes": False,
                }
            ),
            encoding="utf-8",
        )
        exit_code = _run(
            "deep-step",
            "--progress-file",
            str(ppath),
            "--result-file",
            str(result),
        )
        assert exit_code == 0
        assert capsys.readouterr().out.strip() == "converged"
        data = _read_progress(ppath)
        assert data["termination"]["reason"] == "convergence"
        # No tests ran on this path — test_passed must be None, not True.
        assert data["iteration_history"][-1]["test_passed"] is None

    def test_no_actionable(self, tmp_path, capsys):
        ppath = _seed_deep_progress(tmp_path)
        result = tmp_path / "result.json"
        result.write_text(
            json.dumps(
                {
                    "iteration": 1,
                    "new_findings": [
                        {
                            "file": "a.py",
                            "line": 1,
                            "category": "x",
                            "summary": "s",
                            "pre_edit_content": "",
                            "post_edit_content": "",
                        }
                    ],
                    "fixes_applied": [],
                    "no_new_findings": False,
                    "no_actionable_fixes": True,
                }
            ),
            encoding="utf-8",
        )
        exit_code = _run(
            "deep-step",
            "--progress-file",
            str(ppath),
            "--result-file",
            str(result),
        )
        assert exit_code == 0
        assert capsys.readouterr().out.strip() == "no-actionable"
        data = _read_progress(ppath)
        assert data["termination"]["reason"] == "no-actionable"
        assert data["iteration_history"][-1]["test_passed"] is None

    def test_applied_all_pass(self, tmp_path, capsys, monkeypatch):
        ppath = _seed_deep_progress(tmp_path)
        # Stub the test runner to always pass
        monkeypatch.setattr(cli, "run_tests", lambda *a, **kw: (True, "ok"))
        result = tmp_path / "result.json"
        result.write_text(
            json.dumps(
                {
                    "iteration": 1,
                    "new_findings": [
                        {
                            "file": "a.py",
                            "line": 1,
                            "category": "x",
                            "summary": "s",
                            "pre_edit_content": "a",
                            "post_edit_content": "b",
                        }
                    ],
                    "fixes_applied": [
                        {
                            "file": "a.py",
                            "line": 1,
                            "category": "x",
                            "summary": "s",
                            "pre_edit_content": "a",
                            "post_edit_content": "b",
                        }
                    ],
                    "no_new_findings": False,
                    "no_actionable_fixes": False,
                }
            ),
            encoding="utf-8",
        )
        exit_code = _run(
            "deep-step",
            "--progress-file",
            str(ppath),
            "--result-file",
            str(result),
        )
        assert exit_code == 0
        out = capsys.readouterr().out
        assert out.strip().startswith("applied")
        data = _read_progress(ppath)
        assert data["iteration_history"][-1]["fixed"] == 1

    def test_no_commit_mode_rolls_back_to_stash_on_combined_regression(
        self, tmp_path, monkeypatch
    ):
        # No-commit mode (the snapshot carries a stash, not just a HEAD): when a
        # fix survives bisection but the combined set still fails the suite, the
        # iteration must roll the working tree back to the pre-iteration STASH.
        # Exercises _clean_reset_hook's no-commit return-None branch (clean-reset
        # bisect is disabled there because the stash is single-use) and the
        # stash-restore reconciliation that the commit-mode tests never reach.
        ppath = _seed_deep_progress(tmp_path)
        data = _read_progress(ppath)
        data["config"]["no_commit"] = True
        data["_snapshot"]["pre_stash"] = "stash_sha"
        ppath.write_text(json.dumps(data, indent=2), encoding="utf-8")

        # Suite fails on the initial run and again after bisection retains a fix.
        monkeypatch.setattr(cli, "run_tests", lambda *a, **kw: (False, "boom"))
        captured = {}

        def fake_bisect(*_a, reset_to_clean=None, **_kw):
            captured["reset_to_clean"] = reset_to_clean
            return (1, 0, [])  # one fix retained, none reverted individually

        monkeypatch.setattr(cli, "bisect_fixes", fake_bisect)
        restore_calls = []
        monkeypatch.setattr(
            cli,
            "restore_working_tree",
            lambda stash, head, _cwd, **_kw: restore_calls.append((stash, head)),
        )
        result = tmp_path / "result.json"
        result.write_text(json.dumps(_one_fix_result()), encoding="utf-8")

        exit_code = _run(
            "deep-step", "--progress-file", str(ppath), "--result-file", str(result)
        )
        assert exit_code == 0
        # Clean-reset bisect is disabled in no-commit mode (one-shot stash).
        assert captured["reset_to_clean"] is None
        # Rolled back to the stash + HEAD, not a bare HEAD checkout.
        assert restore_calls == [("stash_sha", "abc1234")]
        # The full restore zeroes the net fix tally and ends the iteration.
        history = _read_progress(ppath)["iteration_history"][-1]
        assert history["fixed"] == 0
        assert history["reverted"] == 1
        assert _read_progress(ppath)["termination"]["reason"] == "all-reverted"

    def test_configured_timeout_is_threaded_to_run_tests(self, tmp_path, monkeypatch):
        # config.test_timeout (set by `baseline`) must reach run_tests.
        ppath = _seed_deep_progress(tmp_path)
        data = _read_progress(ppath)
        data["config"]["test_timeout"] = 777
        ppath.write_text(json.dumps(data, indent=2), encoding="utf-8")
        captured = {}

        def fake_run_tests(tc, cwd, timeout=None, **kw):
            captured["timeout"] = timeout
            return (True, "ok")

        monkeypatch.setattr(cli, "run_tests", fake_run_tests)
        result = tmp_path / "result.json"
        result.write_text(json.dumps(_one_fix_result()), encoding="utf-8")
        _run("deep-step", "--progress-file", str(ppath), "--result-file", str(result))
        assert captured["timeout"] == 777

    def test_absent_timeout_falls_back_to_default(self, tmp_path, monkeypatch):
        # _seed_deep_progress writes no test_timeout, mirroring an old/resumed
        # progress file — run_tests must still get DEFAULT_TEST_TIMEOUT.
        ppath = _seed_deep_progress(tmp_path)
        captured = {}

        def fake_run_tests(tc, cwd, timeout=None, **kw):
            captured["timeout"] = timeout
            return (True, "ok")

        monkeypatch.setattr(cli, "run_tests", fake_run_tests)
        result = tmp_path / "result.json"
        result.write_text(json.dumps(_one_fix_result()), encoding="utf-8")
        _run("deep-step", "--progress-file", str(ppath), "--result-file", str(result))
        assert captured["timeout"] == DEFAULT_TEST_TIMEOUT

    def test_malformed_empty_fixes_does_not_crash(self, tmp_path, capsys):
        # Regression: if a subagent reports new_findings but neither
        # no_actionable_fixes=true nor any fixes_applied entries with valid
        # edit pairs, the deep-step used to crash on int(None) at the
        # "applied …" print line. Must instead print "test_passed=-".
        ppath = _seed_deep_progress(tmp_path)
        result = tmp_path / "result.json"
        result.write_text(
            json.dumps(
                {
                    "iteration": 1,
                    "new_findings": [
                        {
                            "file": "a.py",
                            "line": 1,
                            "category": "x",
                            "summary": "s",
                            "pre_edit_content": "",
                            "post_edit_content": "",
                        }
                    ],
                    "fixes_applied": [],
                    "no_new_findings": False,
                    "no_actionable_fixes": False,
                }
            ),
            encoding="utf-8",
        )
        exit_code = _run(
            "deep-step",
            "--progress-file",
            str(ppath),
            "--result-file",
            str(result),
        )
        assert exit_code == 0
        out = capsys.readouterr().out.strip()
        assert out.startswith("applied")
        assert "test_passed=-" in out

    def test_bisect_skipped_status_propagates_to_progress(
        self, tmp_path, capsys, monkeypatch
    ):
        # A bisect "skipped" outcome (apply failed — pre_edit_content didn't
        # match the file) must mark the finding "skipped — apply failed" and
        # NOT increment the fixed counter. Without a regression test the
        # special-case in _make_bisect_callback could drift unnoticed.
        ppath = _seed_deep_progress(tmp_path)
        monkeypatch.setattr(cli, "run_tests", lambda *a, **kw: (False, "FAIL"))

        def _stub_bisect(
            fixes, _tc, _cwd, run_tests_fn=None, on_outcome=None, reset_to_clean=None
        ):
            for idx, fix in enumerate(fixes):
                on_outcome(idx, fix, "skipped", "apply failed")
            return 0, 0, len(fixes)

        monkeypatch.setattr(cli, "bisect_fixes", _stub_bisect)
        result = tmp_path / "result.json"
        result.write_text(
            json.dumps(
                {
                    "iteration": 1,
                    "new_findings": [
                        {
                            "file": "a.py",
                            "line": 1,
                            "category": "x",
                            "summary": "s",
                            "pre_edit_content": "a",
                            "post_edit_content": "b",
                        }
                    ],
                    "fixes_applied": [
                        {
                            "file": "a.py",
                            "line": 1,
                            "category": "x",
                            "summary": "s",
                            "pre_edit_content": "a",
                            "post_edit_content": "b",
                        }
                    ],
                    "no_new_findings": False,
                    "no_actionable_fixes": False,
                }
            ),
            encoding="utf-8",
        )
        exit_code = _run(
            "deep-step",
            "--progress-file",
            str(ppath),
            "--result-file",
            str(result),
        )
        assert exit_code == 0
        out = capsys.readouterr().out.strip()
        assert "fixed=0" in out
        data = _read_progress(ppath)
        assert data["findings"][0]["status"] == "skipped — apply failed"

    def test_promote_actionable_fixes_recovers_from_false_flag(
        self, tmp_path, capsys, monkeypatch
    ):
        # When the subagent sets no_actionable_fixes=true but new_findings
        # carry valid pre/post edit pairs, _promote_actionable_fixes lifts
        # them into fixes_applied and clears the flag so deep-step proceeds
        # to the bisect/apply path instead of terminating "no-actionable".
        ppath = _seed_deep_progress(tmp_path)
        monkeypatch.setattr(cli, "run_tests", lambda *a, **kw: (True, "ok"))
        result = tmp_path / "result.json"
        result.write_text(
            json.dumps(
                {
                    "iteration": 1,
                    "new_findings": [
                        {
                            "file": "a.py",
                            "line": 1,
                            "category": "x",
                            "summary": "s",
                            "pre_edit_content": "a",
                            "post_edit_content": "b",
                        }
                    ],
                    "fixes_applied": [],
                    "no_new_findings": False,
                    "no_actionable_fixes": True,
                }
            ),
            encoding="utf-8",
        )
        exit_code = _run(
            "deep-step",
            "--progress-file",
            str(ppath),
            "--result-file",
            str(result),
        )
        assert exit_code == 0
        assert capsys.readouterr().out.strip().startswith("applied")
        data = _read_progress(ppath)
        # Promoted finding counts as 1 applied; no early "no-actionable" exit.
        assert data["iteration_history"][-1]["fixed"] == 1
        assert data["termination"]["reason"] is None

    def test_promote_skips_when_edit_pair_invalid(self, tmp_path, capsys):
        # _promote_actionable_fixes must NOT promote a finding whose
        # pre_edit_content equals post_edit_content (no edit) or whose
        # post_edit_content is None. Original "no-actionable" termination
        # must stand.
        ppath = _seed_deep_progress(tmp_path)
        result = tmp_path / "result.json"
        result.write_text(
            json.dumps(
                {
                    "iteration": 1,
                    "new_findings": [
                        {
                            "file": "a.py",
                            "line": 1,
                            "category": "x",
                            "summary": "s",
                            "pre_edit_content": "a",
                            "post_edit_content": "a",
                        },
                        {
                            "file": "b.py",
                            "line": 1,
                            "category": "x",
                            "summary": "s",
                            "pre_edit_content": "a",
                            "post_edit_content": None,
                        },
                    ],
                    "fixes_applied": [],
                    "no_new_findings": False,
                    "no_actionable_fixes": True,
                }
            ),
            encoding="utf-8",
        )
        exit_code = _run(
            "deep-step",
            "--progress-file",
            str(ppath),
            "--result-file",
            str(result),
        )
        assert exit_code == 0
        assert capsys.readouterr().out.strip() == "no-actionable"

    def test_interaction_bug_combined_regression(self, tmp_path, capsys, monkeypatch):
        # Bisect succeeds (one fix kept), but the full re-run after bisect
        # fails — the working tree is restored and the previously-fixed
        # finding is demoted to "reverted — test failure" with the
        # "Interaction bug — combined fixes failed" detail.
        ppath = _seed_deep_progress(tmp_path)
        (tmp_path / "a.py").write_text("a", encoding="utf-8")
        # First run fails, bisect retains one, second full-run also fails.
        call_count = {"n": 0}

        def _stub_tests(*_a, **_kw):
            call_count["n"] += 1
            # n=1 initial fail, n=2 post-bisect fail
            return False, f"FAIL #{call_count['n']}"

        monkeypatch.setattr(cli, "run_tests", _stub_tests)

        def _stub_bisect(
            fixes, _tc, _cwd, run_tests_fn=None, on_outcome=None, reset_to_clean=None
        ):
            for idx, fix in enumerate(fixes):
                on_outcome(idx, fix, "fixed", "OK")
            return len(fixes), 0, 0

        monkeypatch.setattr(cli, "bisect_fixes", _stub_bisect)
        monkeypatch.setattr(cli, "restore_working_tree", lambda *a, **kw: None)
        result = tmp_path / "result.json"
        result.write_text(
            json.dumps(
                {
                    "iteration": 1,
                    "new_findings": [
                        {
                            "file": "a.py",
                            "line": 1,
                            "category": "x",
                            "summary": "s",
                            "pre_edit_content": "a",
                            "post_edit_content": "b",
                        }
                    ],
                    "fixes_applied": [
                        {
                            "file": "a.py",
                            "line": 1,
                            "category": "x",
                            "summary": "s",
                            "pre_edit_content": "a",
                            "post_edit_content": "b",
                        }
                    ],
                    "no_new_findings": False,
                    "no_actionable_fixes": False,
                }
            ),
            encoding="utf-8",
        )
        exit_code = _run(
            "deep-step",
            "--progress-file",
            str(ppath),
            "--result-file",
            str(result),
        )
        assert exit_code == 0
        data = _read_progress(ppath)
        # Finding was promoted from "fixed" to "reverted — test failure"
        # with the interaction-bug detail.
        assert len(data["findings"]) == 1
        f = data["findings"][0]
        assert f["status"] == "reverted — test failure"
        latest_detail = f["status_history"][-1]["detail"] or ""
        assert "Interaction bug" in latest_detail
        # fixed dropped to 0, reverted bumped to 1.
        assert data["iteration_history"][-1]["fixed"] == 0
        assert data["iteration_history"][-1]["reverted"] == 1

    def test_all_reverted(self, tmp_path, capsys, monkeypatch):
        # When bisection reverts every fix, deep-step prints "all-reverted"
        # and records termination.reason accordingly.
        ppath = _seed_deep_progress(tmp_path)
        (tmp_path / "a.py").write_text("a", encoding="utf-8")
        monkeypatch.setattr(cli, "run_tests", lambda *a, **kw: (False, "FAIL"))

        def _stub_bisect(
            fixes, _tc, _cwd, run_tests_fn=None, on_outcome=None, reset_to_clean=None
        ):
            for idx, fix in enumerate(fixes):
                on_outcome(idx, fix, "reverted", "FAIL")
            return 0, len(fixes), 0

        monkeypatch.setattr(cli, "bisect_fixes", _stub_bisect)
        result = tmp_path / "result.json"
        result.write_text(
            json.dumps(
                {
                    "iteration": 1,
                    "new_findings": [
                        {
                            "file": "a.py",
                            "line": 1,
                            "category": "x",
                            "summary": "s",
                            "pre_edit_content": "a",
                            "post_edit_content": "b",
                        }
                    ],
                    "fixes_applied": [
                        {
                            "file": "a.py",
                            "line": 1,
                            "category": "x",
                            "summary": "s",
                            "pre_edit_content": "a",
                            "post_edit_content": "b",
                        }
                    ],
                    "no_new_findings": False,
                    "no_actionable_fixes": False,
                }
            ),
            encoding="utf-8",
        )
        exit_code = _run(
            "deep-step",
            "--progress-file",
            str(ppath),
            "--result-file",
            str(result),
        )
        assert exit_code == 0
        assert capsys.readouterr().out.strip() == "all-reverted"
        data = _read_progress(ppath)
        assert data["termination"]["reason"] == "all-reverted"

    def test_interaction_bug_demotes_retained_fix(self, tmp_path, capsys, monkeypatch):
        # Symmetric to test_interaction_bug_combined_regression but for the
        # "retained" bisect outcome (revert failed -> fix stayed applied
        # untested). When the post-bisect full re-run fails, the working-tree
        # restore removes the retained fix, so _mark_combined_regression must
        # demote it from "retained -- revert failed" to "reverted -- test
        # failure" via its retained branch.
        ppath = _seed_deep_progress(tmp_path)
        (tmp_path / "a.py").write_text("a", encoding="utf-8")
        monkeypatch.setattr(cli, "run_tests", lambda *a, **kw: (False, "FAIL"))

        def _stub_bisect(
            fixes, _tc, _cwd, run_tests_fn=None, on_outcome=None, reset_to_clean=None
        ):
            for idx, fix in enumerate(fixes):
                on_outcome(idx, fix, "retained", "revert failed")
            # retained counts toward fixed_count in the real bisect_fixes.
            return len(fixes), 0, 0

        monkeypatch.setattr(cli, "bisect_fixes", _stub_bisect)
        monkeypatch.setattr(cli, "restore_working_tree", lambda *a, **kw: None)
        result = tmp_path / "result.json"
        result.write_text(
            json.dumps(
                {
                    "iteration": 1,
                    "new_findings": [
                        {
                            "file": "a.py",
                            "line": 1,
                            "category": "x",
                            "summary": "s",
                            "pre_edit_content": "a",
                            "post_edit_content": "b",
                        }
                    ],
                    "fixes_applied": [
                        {
                            "file": "a.py",
                            "line": 1,
                            "category": "x",
                            "summary": "s",
                            "pre_edit_content": "a",
                            "post_edit_content": "b",
                        }
                    ],
                    "no_new_findings": False,
                    "no_actionable_fixes": False,
                }
            ),
            encoding="utf-8",
        )
        exit_code = _run(
            "deep-step",
            "--progress-file",
            str(ppath),
            "--result-file",
            str(result),
        )
        assert exit_code == 0
        data = _read_progress(ppath)
        finding = data["findings"][0]
        assert finding["status"] == "reverted — test failure"
        latest_detail = finding["status_history"][-1]["detail"] or ""
        assert "retained fix" in latest_detail
        assert data["iteration_history"][-1]["fixed"] == 0
        assert data["iteration_history"][-1]["reverted"] == 1


# ---------------------------------------------------------------------------
# unit-test-step
# ---------------------------------------------------------------------------


def _seed_coverage_progress(tmp_path, *, cycle=1):
    progress = {
        "schema_version": 1,
        "harness": "test-coverage",
        "skill": "unit-test",
        "started_at": "2025-01-01T00:00:00Z",
        "config": {
            "max_cycles": 5,
            "test_command": "pytest",
            "scope": "",
            "project_root": str(tmp_path),
            "base_commit": "abc1234",
        },
        "cycle": {"current": cycle, "completed": cycle - 1},
        "phase": "unit-test",
        "coverage": {"baseline": None, "current": None, "tool": None, "history": []},
        "tests_created": [],
        "untestable_code": [],
        "refactor_findings": [],
        "bugs_discovered": [],
        "cycle_history": [],
        "test_results": {"last_full_run": None, "last_run_output_summary": None},
        "termination": {"reason": None, "message": None},
        "_snapshot": {
            "pre_head": "abc1234",
            "pre_stash": None,
            "iteration_token": cycle,
        },
    }
    path = tmp_path / "progress.json"
    path.write_text(json.dumps(progress, indent=2), encoding="utf-8")
    return path


class TestUnitTestStep:
    def test_convergence(self, tmp_path, capsys, monkeypatch):
        ppath = _seed_coverage_progress(tmp_path)
        monkeypatch.setattr(cli, "run_tests", lambda *a, **kw: (True, "ok"))
        result = tmp_path / "result.json"
        result.write_text(
            json.dumps(
                {
                    "iteration": 1,
                    "phase": "unit-test",
                    "coverage": {
                        "before": 50,
                        "after": 50,
                        "delta": 0,
                        "tool": "pytest-cov",
                    },
                    "tests_written": [],
                    "untestable_code": [],
                    "bugs_discovered": [],
                    "no_new_tests": True,
                    "no_untestable_code": True,
                    "no_coverage_gained": True,
                }
            ),
            encoding="utf-8",
        )
        exit_code = _run(
            "unit-test-step",
            "--progress-file",
            str(ppath),
            "--result-file",
            str(result),
        )
        assert exit_code == 0
        assert capsys.readouterr().out.strip() == "converged"
        data = _read_progress(ppath)
        assert data["termination"]["reason"] == "convergence"
        assert data["cycle_history"] == [{"cycle": 1, "unit_test": {"converged": True}}]
        assert data["cycle"]["completed"] == 1

    def test_continue_with_pending_untestable(self, tmp_path, capsys, monkeypatch):
        ppath = _seed_coverage_progress(tmp_path)
        monkeypatch.setattr(cli, "run_tests", lambda *a, **kw: (True, "ok"))
        result = tmp_path / "result.json"
        result.write_text(
            json.dumps(
                {
                    "iteration": 1,
                    "phase": "unit-test",
                    "coverage": {
                        "before": 50,
                        "after": 60,
                        "delta": 10,
                        "tool": "pytest-cov",
                    },
                    "tests_written": [
                        {
                            "file": "t.py",
                            "target_file": "s.py",
                            "target_description": "f()",
                            "test_count": 3,
                            "status": "pass",
                            "failure_reason": None,
                        }
                    ],
                    "untestable_code": [
                        {
                            "file": "u.py",
                            "line": 1,
                            "end_line": 2,
                            "function": "g",
                            "barrier": "x",
                            "barrier_description": "y",
                            "suggested_refactoring": "z",
                        }
                    ],
                    "bugs_discovered": [],
                    "no_new_tests": False,
                    "no_untestable_code": False,
                    "no_coverage_gained": False,
                }
            ),
            encoding="utf-8",
        )
        exit_code = _run(
            "unit-test-step",
            "--progress-file",
            str(ppath),
            "--result-file",
            str(result),
        )
        assert exit_code == 0
        assert capsys.readouterr().out.strip() == "continue"
        data = _read_progress(ppath)
        assert len(data["tests_created"]) == 1
        assert len(data["untestable_code"]) == 1
        assert data["untestable_code"][0]["status"] == "pending"


# ---------------------------------------------------------------------------
# refactor-step
# ---------------------------------------------------------------------------


def _seed_coverage_progress_with_untestable(tmp_path, *, files):
    """Seed a coverage progress with one pending untestable item per file."""
    ppath = _seed_coverage_progress(tmp_path)
    data = _read_progress(ppath)
    for path in files:
        data["untestable_code"].append(
            {
                "file": path,
                "line": 1,
                "end_line": 2,
                "function": "g",
                "barrier": "x",
                "barrier_description": "y",
                "suggested_refactoring": "z",
                "status": "pending",
            }
        )
    ppath.write_text(json.dumps(data), encoding="utf-8")
    return ppath


class TestRefactorStep:
    def test_convergence(self, tmp_path, capsys):
        ppath = _seed_coverage_progress(tmp_path)
        result = tmp_path / "result.json"
        result.write_text(
            json.dumps(
                {
                    "cycle": 1,
                    "phase": "refactor",
                    "new_findings": [],
                    "fixes_applied": [],
                    "no_new_findings": True,
                    "no_actionable_fixes": False,
                }
            ),
            encoding="utf-8",
        )
        exit_code = _run(
            "refactor-step",
            "--progress-file",
            str(ppath),
            "--result-file",
            str(result),
        )
        assert exit_code == 0
        assert capsys.readouterr().out.strip() == "converged"
        data = _read_progress(ppath)
        assert data["termination"]["reason"] == "convergence"
        assert data["cycle_history"] == [
            {"cycle": 1, "refactor": {"converged": True, "fixed": 0, "reverted": 0}}
        ]
        assert data["cycle"]["completed"] == 1

    def test_empty_fixes_prints_test_passed_dash(self, tmp_path, capsys):
        # Regression for 310c928 / parity with TestDeepStep:
        # test_malformed_empty_fixes_does_not_crash: when fixes_applied is
        # empty but no_actionable_fixes is False (subagent reported new
        # findings but no actionable edit pairs), refactor-step must print
        # test_passed=- rather than test_passed=1.
        ppath = _seed_coverage_progress_with_untestable(tmp_path, files=["u.py"])
        result = tmp_path / "result.json"
        result.write_text(
            json.dumps(
                {
                    "cycle": 1,
                    "phase": "refactor",
                    "new_findings": [
                        {
                            "file": "u.py",
                            "line": 1,
                            "category": "refactor",
                            "summary": "s",
                            "pre_edit_content": "",
                            "post_edit_content": "",
                        }
                    ],
                    "fixes_applied": [],
                    "no_new_findings": False,
                    "no_actionable_fixes": False,
                }
            ),
            encoding="utf-8",
        )
        exit_code = _run(
            "refactor-step",
            "--progress-file",
            str(ppath),
            "--result-file",
            str(result),
        )
        assert exit_code == 0
        out = capsys.readouterr().out.strip()
        assert out.startswith("applied")
        assert "test_passed=-" in out

    def test_applied_all_pass_marks_attempted(self, tmp_path, capsys, monkeypatch):
        ppath = _seed_coverage_progress_with_untestable(tmp_path, files=["u.py"])
        (tmp_path / "u.py").write_text("a", encoding="utf-8")
        monkeypatch.setattr(cli, "run_tests", lambda *a, **kw: (True, "ok"))
        result = tmp_path / "result.json"
        result.write_text(
            json.dumps(
                {
                    "cycle": 1,
                    "phase": "refactor",
                    "new_findings": [
                        {
                            "file": "u.py",
                            "line": 1,
                            "category": "refactor",
                            "summary": "extract",
                            "pre_edit_content": "a",
                            "post_edit_content": "b",
                        }
                    ],
                    "fixes_applied": [
                        {
                            "file": "u.py",
                            "line": 1,
                            "category": "refactor",
                            "summary": "extract",
                            "pre_edit_content": "a",
                            "post_edit_content": "b",
                        }
                    ],
                    "no_new_findings": False,
                    "no_actionable_fixes": False,
                }
            ),
            encoding="utf-8",
        )
        exit_code = _run(
            "refactor-step",
            "--progress-file",
            str(ppath),
            "--result-file",
            str(result),
        )
        assert exit_code == 0
        out = capsys.readouterr().out.strip()
        assert out.startswith("applied")
        assert "fixed=1" in out and "reverted=0" in out and "test_passed=1" in out
        data = _read_progress(ppath)
        assert len(data["refactor_findings"]) == 1
        assert data["refactor_findings"][0]["status"] == "fixed"
        assert data["untestable_code"][0]["status"] == "attempted"
        assert data["untestable_code"][0]["refactor_attempt_cycle"] == 1

    def test_bare_fix_absent_from_new_findings_marks_attempted(
        self, tmp_path, capsys, monkeypatch
    ):
        # A fix present in fixes_applied but absent from new_findings must still
        # be registered as a refactor_finding (mirrors deep-step), so its
        # untestable item is marked "attempted" instead of stranded pending.
        ppath = _seed_coverage_progress_with_untestable(tmp_path, files=["u.py"])
        (tmp_path / "u.py").write_text("a", encoding="utf-8")
        monkeypatch.setattr(cli, "run_tests", lambda *a, **kw: (True, "ok"))
        result = tmp_path / "result.json"
        result.write_text(
            json.dumps(
                {
                    "cycle": 1,
                    "phase": "refactor",
                    "new_findings": [],  # subagent did not echo the fix as a finding
                    "fixes_applied": [
                        {
                            "file": "u.py",
                            "line": 1,
                            "category": "refactor",
                            "summary": "extract",
                            "pre_edit_content": "a",
                            "post_edit_content": "b",
                        }
                    ],
                    "no_new_findings": False,
                    "no_actionable_fixes": False,
                }
            ),
            encoding="utf-8",
        )
        exit_code = _run(
            "refactor-step",
            "--progress-file",
            str(ppath),
            "--result-file",
            str(result),
        )
        assert exit_code == 0
        data = _read_progress(ppath)
        assert any(
            f["file"] == "u.py" and f["status"] == "fixed"
            for f in data["refactor_findings"]
        )
        assert data["untestable_code"][0]["status"] == "attempted"
        assert data["untestable_code"][0]["refactor_attempt_cycle"] == 1

    def test_attempted_marking_is_separator_agnostic(
        self, tmp_path, capsys, monkeypatch
    ):
        # The untestable item is stored with forward slashes, but the refactor
        # subagent may cite the fixed file with OS-native backslashes. The
        # touched-file match must normalize both sides, else the item never
        # converges and is re-dispatched every cycle.
        ppath = _seed_coverage_progress_with_untestable(tmp_path, files=["pkg/u.py"])
        (tmp_path / "pkg").mkdir()
        (tmp_path / "pkg" / "u.py").write_text("a", encoding="utf-8")
        monkeypatch.setattr(cli, "run_tests", lambda *a, **kw: (True, "ok"))
        result = tmp_path / "result.json"
        result.write_text(
            json.dumps(
                {
                    "cycle": 1,
                    "phase": "refactor",
                    "new_findings": [
                        {
                            "file": "pkg\\u.py",
                            "line": 1,
                            "category": "refactor",
                            "summary": "s",
                            "pre_edit_content": "a",
                            "post_edit_content": "b",
                        }
                    ],
                    "fixes_applied": [
                        {
                            "file": "pkg\\u.py",
                            "line": 1,
                            "category": "refactor",
                            "summary": "s",
                            "pre_edit_content": "a",
                            "post_edit_content": "b",
                        }
                    ],
                    "no_new_findings": False,
                    "no_actionable_fixes": False,
                }
            ),
            encoding="utf-8",
        )
        exit_code = _run(
            "refactor-step",
            "--progress-file",
            str(ppath),
            "--result-file",
            str(result),
        )
        assert exit_code == 0
        data = _read_progress(ppath)
        assert data["untestable_code"][0]["status"] == "attempted"
        assert data["untestable_code"][0]["refactor_attempt_cycle"] == 1

    def test_bisect_skipped_status_propagates_to_refactor_findings(
        self, tmp_path, capsys, monkeypatch
    ):
        # Mirror of TestDeepStep.test_bisect_skipped_status_propagates_to_progress
        # for the refactor phase: a "skipped" bisect outcome must mark the
        # refactor_findings entry "skipped — apply failed" and NOT increment
        # fixed_count (which would otherwise inflate iteration_history).
        ppath = _seed_coverage_progress_with_untestable(tmp_path, files=["u.py"])
        (tmp_path / "u.py").write_text("a", encoding="utf-8")
        monkeypatch.setattr(cli, "run_tests", lambda *a, **kw: (False, "FAIL"))

        def _stub_bisect(
            fixes, _tc, _cwd, run_tests_fn=None, on_outcome=None, reset_to_clean=None
        ):
            for idx, fix in enumerate(fixes):
                on_outcome(idx, fix, "skipped", "apply failed")
            return 0, 0, len(fixes)

        monkeypatch.setattr(cli, "bisect_fixes", _stub_bisect)
        result = tmp_path / "result.json"
        result.write_text(
            json.dumps(
                {
                    "cycle": 1,
                    "phase": "refactor",
                    "new_findings": [
                        {
                            "file": "u.py",
                            "line": 1,
                            "category": "refactor",
                            "summary": "s",
                            "pre_edit_content": "a",
                            "post_edit_content": "b",
                        }
                    ],
                    "fixes_applied": [
                        {
                            "file": "u.py",
                            "line": 1,
                            "category": "refactor",
                            "summary": "s",
                            "pre_edit_content": "a",
                            "post_edit_content": "b",
                        }
                    ],
                    "no_new_findings": False,
                    "no_actionable_fixes": False,
                }
            ),
            encoding="utf-8",
        )
        exit_code = _run(
            "refactor-step",
            "--progress-file",
            str(ppath),
            "--result-file",
            str(result),
        )
        assert exit_code == 0
        out = capsys.readouterr().out.strip()
        assert "fixed=0" in out
        data = _read_progress(ppath)
        assert data["refactor_findings"][0]["status"] == "skipped — apply failed"

    def test_bisect_reverts_failed_fix(self, tmp_path, capsys, monkeypatch):
        ppath = _seed_coverage_progress_with_untestable(tmp_path, files=["u.py"])
        (tmp_path / "u.py").write_text("a", encoding="utf-8")
        monkeypatch.setattr(cli, "run_tests", lambda *a, **kw: (False, "FAIL"))

        def _stub_bisect(
            fixes, _tc, _cwd, run_tests_fn=None, on_outcome=None, reset_to_clean=None
        ):
            for idx, fix in enumerate(fixes):
                on_outcome(idx, fix, "reverted", "FAIL")
            return 0, len(fixes), 0

        monkeypatch.setattr(cli, "bisect_fixes", _stub_bisect)
        result = tmp_path / "result.json"
        result.write_text(
            json.dumps(
                {
                    "cycle": 1,
                    "phase": "refactor",
                    "new_findings": [
                        {
                            "file": "u.py",
                            "line": 1,
                            "category": "refactor",
                            "summary": "s",
                            "pre_edit_content": "a",
                            "post_edit_content": "b",
                        }
                    ],
                    "fixes_applied": [
                        {
                            "file": "u.py",
                            "line": 1,
                            "category": "refactor",
                            "summary": "s",
                            "pre_edit_content": "a",
                            "post_edit_content": "b",
                        }
                    ],
                    "no_new_findings": False,
                    "no_actionable_fixes": False,
                }
            ),
            encoding="utf-8",
        )
        exit_code = _run(
            "refactor-step",
            "--progress-file",
            str(ppath),
            "--result-file",
            str(result),
        )
        assert exit_code == 0
        out = capsys.readouterr().out.strip()
        assert "fixed=0" in out and "reverted=1" in out
        data = _read_progress(ppath)
        assert data["refactor_findings"][0]["status"] == "reverted — test failure"
        # No fixed status means no untestable_code item gets "attempted"
        assert data["untestable_code"][0]["status"] == "pending"

    def test_interaction_bug_after_bisect(self, tmp_path, capsys, monkeypatch):
        # Mirror of TestDeepStep.test_interaction_bug_combined_regression but
        # for the refactor phase: bisect retains one fix, the full re-run
        # then fails, the working tree is restored, and the previously-fixed
        # refactor_findings entry is demoted to "reverted — test failure".
        ppath = _seed_coverage_progress_with_untestable(tmp_path, files=["u.py"])
        (tmp_path / "u.py").write_text("a", encoding="utf-8")
        call_count = {"n": 0}

        def _stub_tests(*_a, **_kw):
            call_count["n"] += 1
            return False, f"FAIL #{call_count['n']}"

        monkeypatch.setattr(cli, "run_tests", _stub_tests)

        def _stub_bisect(
            fixes, _tc, _cwd, run_tests_fn=None, on_outcome=None, reset_to_clean=None
        ):
            for idx, fix in enumerate(fixes):
                on_outcome(idx, fix, "fixed", "OK")
            return len(fixes), 0, 0

        monkeypatch.setattr(cli, "bisect_fixes", _stub_bisect)
        monkeypatch.setattr(cli, "restore_working_tree", lambda *a, **kw: None)
        result = tmp_path / "result.json"
        result.write_text(
            json.dumps(
                {
                    "cycle": 1,
                    "phase": "refactor",
                    "new_findings": [
                        {
                            "file": "u.py",
                            "line": 1,
                            "category": "refactor",
                            "summary": "s",
                            "pre_edit_content": "a",
                            "post_edit_content": "b",
                        }
                    ],
                    "fixes_applied": [
                        {
                            "file": "u.py",
                            "line": 1,
                            "category": "refactor",
                            "summary": "s",
                            "pre_edit_content": "a",
                            "post_edit_content": "b",
                        }
                    ],
                    "no_new_findings": False,
                    "no_actionable_fixes": False,
                }
            ),
            encoding="utf-8",
        )
        exit_code = _run(
            "refactor-step",
            "--progress-file",
            str(ppath),
            "--result-file",
            str(result),
        )
        assert exit_code == 0
        out = capsys.readouterr().out.strip()
        # After the restore, the previously-fixed finding is demoted.
        assert "fixed=0" in out
        assert "reverted=1" in out
        data = _read_progress(ppath)
        assert data["refactor_findings"][0]["status"] == "reverted — test failure"
        # untestable_code stays pending (no surviving fixed status).
        assert data["untestable_code"][0]["status"] == "pending"


# ---------------------------------------------------------------------------
# record-cycle
# ---------------------------------------------------------------------------


class TestRecordCycle:
    def test_unit_test_only(self, tmp_path):
        ppath = _seed_coverage_progress(tmp_path)
        ut = json.dumps({"fixed": 2, "reverted": 0})
        exit_code = _run(
            "record-cycle",
            "--progress-file",
            str(ppath),
            "--unit-test-summary",
            ut,
        )
        assert exit_code == 0
        data = _read_progress(ppath)
        assert data["cycle_history"] == [
            {"cycle": 1, "unit_test": {"fixed": 2, "reverted": 0}}
        ]
        assert data["cycle"]["completed"] == 1
        assert data["cycle"]["current"] == 2

    def test_unit_test_and_refactor(self, tmp_path):
        ppath = _seed_coverage_progress(tmp_path)
        exit_code = _run(
            "record-cycle",
            "--progress-file",
            str(ppath),
            "--unit-test-summary",
            json.dumps({"fixed": 1}),
            "--refactor-summary",
            json.dumps({"fixed": 1, "reverted": 0}),
        )
        assert exit_code == 0
        data = _read_progress(ppath)
        assert data["cycle_history"] == [
            {
                "cycle": 1,
                "unit_test": {"fixed": 1},
                "refactor": {"fixed": 1, "reverted": 0},
            }
        ]
        assert data["cycle"]["current"] == 2

    def test_invalid_json_exits_one(self, tmp_path, capsys):
        ppath = _seed_coverage_progress(tmp_path)
        exit_code = _run(
            "record-cycle",
            "--progress-file",
            str(ppath),
            "--unit-test-summary",
            "{not valid json",
        )
        assert exit_code == 1
        assert "Invalid cycle summary JSON" in capsys.readouterr().err
        # Progress file untouched on parse failure
        data = _read_progress(ppath)
        assert data["cycle_history"] == []
        assert data["cycle"]["current"] == 1


# ---------------------------------------------------------------------------
# check-termination
# ---------------------------------------------------------------------------


class TestCheckTermination:
    def test_continue_deep(self, tmp_path, capsys):
        ppath = _seed_deep_progress(tmp_path)
        exit_code = _run("check-termination", "--progress-file", str(ppath))
        assert exit_code == 0
        assert capsys.readouterr().out.strip() == "continue"

    def test_cap_deep(self, tmp_path, capsys):
        ppath = _seed_deep_progress(tmp_path, iteration=8)
        exit_code = _run("check-termination", "--progress-file", str(ppath))
        assert exit_code == 0
        assert capsys.readouterr().out.strip() == "cap"
        data = _read_progress(ppath)
        assert data["termination"]["reason"] == "cap"

    def test_existing_termination_returned(self, tmp_path, capsys):
        ppath = _seed_deep_progress(tmp_path)
        data = _read_progress(ppath)
        data["termination"] = {"reason": "convergence", "message": "done"}
        ppath.write_text(json.dumps(data, indent=2), encoding="utf-8")
        exit_code = _run("check-termination", "--progress-file", str(ppath))
        assert exit_code == 0
        assert capsys.readouterr().out.strip() == "convergence"

    def test_diminishing_returns_deep(self, tmp_path, capsys):
        ppath = _seed_deep_progress(tmp_path, iteration=5)
        data = _read_progress(ppath)
        # Two consecutive iterations with ≤1 new finding and 0 reverted
        data["iteration_history"] = [
            {
                "iteration": 4,
                "new_findings": 1,
                "fixed": 0,
                "reverted": 0,
                "persistent": 0,
                "test_passed": True,
            },
            {
                "iteration": 5,
                "new_findings": 0,
                "fixed": 0,
                "reverted": 0,
                "persistent": 0,
                "test_passed": True,
            },
        ]
        ppath.write_text(json.dumps(data, indent=2), encoding="utf-8")
        exit_code = _run("check-termination", "--progress-file", str(ppath))
        assert exit_code == 0
        assert capsys.readouterr().out.strip() == "diminishing-returns"

    def test_parse_failure_threshold_deep(self, tmp_path, capsys):
        # Two consecutive failed parses → check-termination surfaces
        # parse-failure (records the reason, no need for mark-termination).
        ppath = _seed_deep_progress(tmp_path)
        data = _read_progress(ppath)
        data["parse_failure_count"] = 2
        ppath.write_text(json.dumps(data, indent=2), encoding="utf-8")
        exit_code = _run("check-termination", "--progress-file", str(ppath))
        assert exit_code == 0
        assert capsys.readouterr().out.strip() == "parse-failure"
        assert _read_progress(ppath)["termination"]["reason"] == "parse-failure"

    def test_parse_failure_below_threshold_continues(self, tmp_path, capsys):
        # A single parse failure (counter == 1) must not terminate; the loop
        # gets one more chance before parse-failure kicks in.
        ppath = _seed_deep_progress(tmp_path)
        data = _read_progress(ppath)
        data["parse_failure_count"] = 1
        ppath.write_text(json.dumps(data, indent=2), encoding="utf-8")
        exit_code = _run("check-termination", "--progress-file", str(ppath))
        assert exit_code == 0
        assert capsys.readouterr().out.strip() == "continue"
        assert _read_progress(ppath)["termination"]["reason"] is None

    def test_parse_failure_threshold_coverage(self, tmp_path, capsys):
        # Same threshold rule applies to the coverage variant — a unit-test
        # parse failure followed by a refactor parse failure counts as two.
        ppath = _seed_coverage_progress(tmp_path)
        data = _read_progress(ppath)
        data["parse_failure_count"] = 2
        ppath.write_text(json.dumps(data, indent=2), encoding="utf-8")
        exit_code = _run("check-termination", "--progress-file", str(ppath))
        assert exit_code == 0
        assert capsys.readouterr().out.strip() == "parse-failure"

    def test_cap_coverage(self, tmp_path, capsys):
        # record-cycle pre-increments cycle.current after the last cycle
        # completes, so cap fires when current > max_cycles (cycle 6 means
        # cycle 5 just finished with max_cycles=5).
        ppath = _seed_coverage_progress(tmp_path, cycle=6)
        exit_code = _run("check-termination", "--progress-file", str(ppath))
        assert exit_code == 0
        assert capsys.readouterr().out.strip() == "cap"

    def test_no_cap_coverage_on_final_cycle(self, tmp_path, capsys):
        # Boundary: when current == max_cycles, the final cycle is still
        # allowed to run (record-cycle will then bump to max_cycles+1 and
        # the next check-termination caps).
        ppath = _seed_coverage_progress(tmp_path, cycle=5)
        exit_code = _run("check-termination", "--progress-file", str(ppath))
        assert exit_code == 0
        assert capsys.readouterr().out.strip() == "continue"

    def test_diminishing_returns_coverage(self, tmp_path, capsys, monkeypatch):
        # Drive check_coverage_plateau via the coverage variant: two
        # consecutive zero-delta history entries should trigger
        # diminishing-returns and record the termination reason.
        ppath = _seed_coverage_progress(tmp_path, cycle=2)
        data = _read_progress(ppath)
        data["coverage"]["history"] = [
            {"cycle": 1, "before": 60, "after": 60, "delta": 0},
            {"cycle": 2, "before": 60, "after": 60, "delta": 0},
        ]
        ppath.write_text(json.dumps(data, indent=2), encoding="utf-8")
        monkeypatch.setattr(
            cli,
            "check_coverage_plateau",
            lambda _hist: (True, "plateau detected"),
        )
        exit_code = _run("check-termination", "--progress-file", str(ppath))
        assert exit_code == 0
        assert capsys.readouterr().out.strip() == "diminishing-returns"
        data = _read_progress(ppath)
        assert data["termination"]["reason"] == "diminishing-returns"


# ---------------------------------------------------------------------------
# advance
# ---------------------------------------------------------------------------


class TestAdvance:
    def test_deep(self, tmp_path):
        ppath = _seed_deep_progress(tmp_path, iteration=3)
        _run("advance", "--progress-file", str(ppath))
        data = _read_progress(ppath)
        assert data["iteration"]["current"] == 4


# ---------------------------------------------------------------------------
# pending-refactor-count
# ---------------------------------------------------------------------------


class TestPendingRefactorCount:
    def test_count(self, tmp_path, capsys):
        ppath = _seed_coverage_progress(tmp_path)
        data = _read_progress(ppath)
        data["untestable_code"] = [
            {"status": "pending"},
            {"status": "pending"},
            {"status": "attempted"},
        ]
        ppath.write_text(json.dumps(data, indent=2), encoding="utf-8")
        _run("pending-refactor-count", "--progress-file", str(ppath))
        assert capsys.readouterr().out.strip() == "2"


# ---------------------------------------------------------------------------
# mark-termination
# ---------------------------------------------------------------------------


class TestMarkTermination:
    def test_records_parse_failure(self, tmp_path):
        # The CLI subcommand the orchestrator uses to record a parse-failure
        # termination without touching the progress file directly.
        ppath = _seed_deep_progress(tmp_path)
        exit_code = _run(
            "mark-termination",
            "--progress-file",
            str(ppath),
            "--reason",
            "parse-failure",
            "--message",
            "two consecutive iterations produced no JSON",
        )
        assert exit_code == 0
        data = _read_progress(ppath)
        assert data["termination"]["reason"] == "parse-failure"
        assert "two consecutive" in data["termination"]["message"]

    def test_rejects_unknown_reason(self, tmp_path):
        ppath = _seed_deep_progress(tmp_path)
        with pytest.raises(SystemExit):
            _run(
                "mark-termination",
                "--progress-file",
                str(ppath),
                "--reason",
                "made-up-reason",
            )


# ---------------------------------------------------------------------------
# commit-checkpoint
# ---------------------------------------------------------------------------


class TestCommitCheckpoint:
    def test_nothing_to_commit(self, tmp_path, capsys, monkeypatch):
        ppath = _seed_deep_progress(tmp_path)
        monkeypatch.setattr(cli, "git_diff_has_changes", lambda _cwd: False)
        exit_code = _run("commit-checkpoint", "--progress-file", str(ppath))
        assert exit_code == 0
        assert capsys.readouterr().out.strip() == "nothing-to-commit"

    def test_commit_success_deep(self, tmp_path, capsys, monkeypatch):
        ppath = _seed_deep_progress(tmp_path)
        monkeypatch.setattr(cli, "git_diff_has_changes", lambda _cwd: True)
        captured = {}

        def fake_commit(message, cwd, pf, **kw):
            captured["message"] = message
            return COMMIT_COMMITTED

        monkeypatch.setattr(cli, "git_commit_checkpoint", fake_commit)
        exit_code = _run("commit-checkpoint", "--progress-file", str(ppath))
        assert exit_code == 0
        assert capsys.readouterr().out.strip() == "committed"
        assert "deep-orchestrator" in captured["message"]

    def test_commit_success_coverage_unit_test(self, tmp_path, capsys, monkeypatch):
        # Coverage variant with phase=unit-test: title prefix is "test"
        # (per PHASE_COMMIT_TYPE) and the body lists the cycle's tests_created.
        ppath = _seed_coverage_progress(tmp_path)
        data = _read_progress(ppath)
        data["tests_created"] = [
            {
                "cycle": 1,
                "file": "t.py",
                "target_file": "s.py",
                "target_description": "f",
                "test_count": 3,
                "status": "pass",
                "failure_reason": None,
            },
        ]
        ppath.write_text(json.dumps(data, indent=2), encoding="utf-8")
        monkeypatch.setattr(cli, "git_diff_has_changes", lambda _cwd: True)
        captured = {}

        def fake_commit(message, cwd, pf, **kw):
            captured["message"] = message
            return COMMIT_COMMITTED

        monkeypatch.setattr(cli, "git_commit_checkpoint", fake_commit)
        exit_code = _run(
            "commit-checkpoint",
            "--progress-file",
            str(ppath),
            "--phase",
            "unit-test",
        )
        assert exit_code == 0
        assert capsys.readouterr().out.strip() == "committed"
        assert captured["message"].startswith("test(coverage-orchestrator)")
        assert "1 tests written" in captured["message"]
        assert "Tests written:" in captured["message"]

    def test_commit_success_coverage_refactor(self, tmp_path, capsys, monkeypatch):
        # Coverage variant with phase=refactor: title prefix is "refactor"
        # and the body lists the cycle's fixed refactor_findings.
        ppath = _seed_coverage_progress(tmp_path)
        data = _read_progress(ppath)
        data["refactor_findings"] = [
            {
                "cycle": 1,
                "file": "u.py",
                "line": 1,
                "category": "refactor",
                "summary": "extract",
                "status": "fixed",
            },
        ]
        ppath.write_text(json.dumps(data, indent=2), encoding="utf-8")
        monkeypatch.setattr(cli, "git_diff_has_changes", lambda _cwd: True)
        captured = {}

        def fake_commit(message, cwd, pf, **kw):
            captured["message"] = message
            return COMMIT_COMMITTED

        monkeypatch.setattr(cli, "git_commit_checkpoint", fake_commit)
        exit_code = _run(
            "commit-checkpoint",
            "--progress-file",
            str(ppath),
            "--phase",
            "refactor",
        )
        assert exit_code == 0
        assert capsys.readouterr().out.strip() == "committed"
        assert captured["message"].startswith("refactor(coverage-orchestrator)")
        assert "1 fixed" in captured["message"]
        assert "Testability fixes applied:" in captured["message"]

    def test_commit_failed_exit_code_and_marker(self, tmp_path, capsys, monkeypatch):
        # On commit-failed the CLI durably sets commit_disabled, so later
        # snapshots auto-stash and later checkpoints self-skip — the orchestrator
        # no longer has to switch modes by hand.
        ppath = _seed_deep_progress(tmp_path)
        monkeypatch.setattr(cli, "git_diff_has_changes", lambda _cwd: True)
        monkeypatch.setattr(
            cli, "git_commit_checkpoint", lambda *_a, **_kw: COMMIT_FAILED
        )
        exit_code = _run("commit-checkpoint", "--progress-file", str(ppath))
        assert exit_code == 1
        assert capsys.readouterr().out.strip() == "commit-failed"
        assert _read_progress(ppath)["commit_disabled"] is True

    def test_no_fix_iteration_keeps_commits_enabled(self, tmp_path, capsys):
        # End-to-end regression with a REAL git repo (no monkeypatching of the
        # git layer): a no-fix iteration whose only tree change is the untracked
        # progress file must report nothing-to-commit and leave commit_disabled
        # False — the field bug that durably killed checkpoint recoverability.
        _git_init(tmp_path)
        ppath = _seed_deep_progress(tmp_path)
        # _seed_deep_progress points project_root at tmp_path; the progress file
        # itself is the only untracked change, mirroring a converged iteration.
        exit_code = _run("commit-checkpoint", "--progress-file", str(ppath))
        assert exit_code == 0
        assert capsys.readouterr().out.strip() == "nothing-to-commit"
        # The field bug flipped this to True; the fix must leave it unset/falsy.
        assert not _read_progress(ppath).get("commit_disabled")


# ---------------------------------------------------------------------------
# baseline
# ---------------------------------------------------------------------------


class TestBaseline:
    def test_green_floor_keeps_default_timeout(self, tmp_path, capsys, monkeypatch):
        ppath = _seed_deep_progress(tmp_path)
        monkeypatch.setattr(cli, "run_tests", lambda *a, **kw: (True, "ok"))
        # Fast suite → calibrated timeout never drops below the default floor.
        times = iter([1000.0, 1005.0])
        monkeypatch.setattr(cli.time, "monotonic", lambda: next(times))
        exit_code = _run("baseline", "--progress-file", str(ppath))
        assert exit_code == 0
        out = capsys.readouterr().out
        assert out.strip().splitlines()[-1] == (
            f"baseline-green timeout={DEFAULT_TEST_TIMEOUT}"
        )
        assert _read_progress(ppath)["config"]["test_timeout"] == DEFAULT_TEST_TIMEOUT

    def test_green_calibrates_above_floor_for_slow_suite(
        self, tmp_path, capsys, monkeypatch
    ):
        ppath = _seed_deep_progress(tmp_path)
        monkeypatch.setattr(cli, "run_tests", lambda *a, **kw: (True, "ok"))
        times = iter([0.0, 240.0])  # 240s baseline run
        monkeypatch.setattr(cli.time, "monotonic", lambda: next(times))
        exit_code = _run("baseline", "--progress-file", str(ppath))
        assert exit_code == 0
        out = capsys.readouterr().out
        # max(300, ceil(240 * 3)) == 720
        assert _read_progress(ppath)["config"]["test_timeout"] == 720
        assert "slow" in out.lower()
        assert out.strip().splitlines()[-1] == "baseline-green timeout=720"

    def test_red_refuses_to_start(self, tmp_path, capsys, monkeypatch):
        ppath = _seed_deep_progress(tmp_path)
        monkeypatch.setattr(cli, "run_tests", lambda *a, **kw: (False, "assert boom"))
        exit_code = _run("baseline", "--progress-file", str(ppath))
        assert exit_code == 1
        out = capsys.readouterr().out
        assert "assert boom" in out
        assert out.strip().splitlines()[-1] == "baseline-red"
        # A red run's duration is untrustworthy — no calibration written.
        assert "test_timeout" not in _read_progress(ppath)["config"]

    def test_red_allowed_proceeds_without_calibration(
        self, tmp_path, capsys, monkeypatch
    ):
        ppath = _seed_deep_progress(tmp_path)
        monkeypatch.setattr(cli, "run_tests", lambda *a, **kw: (False, "assert boom"))
        exit_code = _run("baseline", "--progress-file", str(ppath), "--allow-red")
        assert exit_code == 0
        out = capsys.readouterr().out
        assert out.strip().splitlines()[-1] == "baseline-red-allowed"
        assert "test_timeout" not in _read_progress(ppath)["config"]


# ---------------------------------------------------------------------------
# final-report
# ---------------------------------------------------------------------------


class TestFinalReport:
    def test_deep_report_prints(self, tmp_path, capsys, monkeypatch):
        ppath = _seed_deep_progress(tmp_path)
        monkeypatch.setattr(reporting, "git_current_branch", lambda _cwd: "feat/x")
        exit_code = _run("final-report", "--progress-file", str(ppath))
        assert exit_code == 0
        out = capsys.readouterr().out
        assert "Deep-orchestrator cumulative report" in out

    def test_archive_removes_iteration_temps(self, tmp_path, monkeypatch):
        monkeypatch.setattr(reporting, "git_current_branch", lambda _cwd: "feat/x")
        ppath = _seed_deep_progress(tmp_path)
        # Per-iteration scratch the loop leaves in the progress dir...
        temps = [
            tmp_path / ".deep-iteration-raw.txt",
            tmp_path / ".deep-iteration-result.json",
            tmp_path / ".unit-test-deep-ut-raw.txt",
        ]
        for temp in temps:
            temp.write_text("x", encoding="utf-8")
        # ...plus a sibling that must survive (not a scratch temp).
        keep = tmp_path / "keep.txt"
        keep.write_text("keep", encoding="utf-8")
        exit_code = _run("final-report", "--progress-file", str(ppath), "--archive")
        assert exit_code == 0
        for temp in temps:
            assert not temp.exists()
        assert keep.exists()
        assert (tmp_path / "progress.done.json").exists()

    def test_archive_survives_unremovable_scratch_temp(self, tmp_path, monkeypatch):
        # A scratch temp that can't be unlinked (locked / permission denied)
        # must not fail the archive: the progress file is already renamed to
        # .done.json by then, so the best-effort cleanup swallows the OSError
        # and still returns 0. A directory matching the glob stands in for the
        # unremovable temp — Path.unlink() raises OSError on a directory.
        monkeypatch.setattr(reporting, "git_current_branch", lambda _cwd: "feat/x")
        ppath = _seed_deep_progress(tmp_path)
        (tmp_path / ".deep-iteration-locked").mkdir()
        removable = tmp_path / ".deep-iteration-raw.txt"
        removable.write_text("x", encoding="utf-8")
        exit_code = _run("final-report", "--progress-file", str(ppath), "--archive")
        assert exit_code == 0
        assert (tmp_path / "progress.done.json").exists()
        # The OSError on the directory was swallowed; the loop still cleaned the
        # removable temp, and the unremovable entry survived.
        assert not removable.exists()
        assert (tmp_path / ".deep-iteration-locked").exists()

    def test_deep_report_separator_is_ascii(self, tmp_path, capsys, monkeypatch):
        # The "Stopped:" separator must be ASCII so the report can't mojibake on
        # a legacy Windows console (cp437/cp1252).
        monkeypatch.setattr(reporting, "git_current_branch", lambda _cwd: "feat/x")
        ppath = _seed_deep_progress(tmp_path)
        data = _read_progress(ppath)
        data["termination"] = {"reason": "convergence", "message": "Zero new findings"}
        ppath.write_text(json.dumps(data, indent=2), encoding="utf-8")
        _run("final-report", "--progress-file", str(ppath))
        out = capsys.readouterr().out
        out.encode("ascii")  # raises if a non-ASCII separator slipped back in
        assert "convergence - Zero new findings" in out

    def test_coverage_delta_separator_is_ascii(self, tmp_path, capsys, monkeypatch):
        # The coverage delta arrow must be ASCII for the same reason.
        monkeypatch.setattr(reporting, "git_current_branch", lambda _cwd: "feat/x")
        ppath = _seed_coverage_progress(tmp_path)
        data = _read_progress(ppath)
        data["coverage"]["baseline"] = 50
        data["coverage"]["current"] = 80
        ppath.write_text(json.dumps(data, indent=2), encoding="utf-8")
        _run("final-report", "--progress-file", str(ppath))
        out = capsys.readouterr().out
        out.encode("ascii")
        assert "50% -> 80%" in out

    def test_coverage_report_prints(self, tmp_path, capsys, monkeypatch):
        ppath = _seed_coverage_progress(tmp_path)
        monkeypatch.setattr(reporting, "git_current_branch", lambda _cwd: "feat/x")
        exit_code = _run("final-report", "--progress-file", str(ppath))
        assert exit_code == 0
        out = capsys.readouterr().out
        assert "Coverage orchestrator report" in out

    def test_archive_moves_file(self, tmp_path, monkeypatch):
        ppath = _seed_deep_progress(tmp_path)
        monkeypatch.setattr(reporting, "git_current_branch", lambda _cwd: "")
        _run("final-report", "--progress-file", str(ppath), "--archive")
        assert not ppath.exists()
        assert (tmp_path / "progress.done.json").exists()

    def test_archive_removes_backup(self, tmp_path, monkeypatch):
        ppath = _seed_deep_progress(tmp_path)
        monkeypatch.setattr(reporting, "git_current_branch", lambda _cwd: "")
        backup = tmp_path / (ppath.name + cli.BACKUP_SUFFIX)
        backup.write_text("{}", encoding="utf-8")
        _run("final-report", "--progress-file", str(ppath), "--archive")
        assert not backup.exists()
        assert (tmp_path / "progress.done.json").exists()

    def test_archive_oserror_returns_1(self, tmp_path, capsys, monkeypatch):
        ppath = _seed_deep_progress(tmp_path)
        monkeypatch.setattr(reporting, "git_current_branch", lambda _cwd: "")

        def _raise_oserror(*_args, **_kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(cli.os, "replace", _raise_oserror)
        exit_code = _run("final-report", "--progress-file", str(ppath), "--archive")
        assert exit_code == 1
        assert "archive failed" in capsys.readouterr().err
        # The progress file must survive a failed archive (atomicity contract).
        assert ppath.exists()

    def test_diminishing_returns_not_archived(self, tmp_path, capsys, monkeypatch):
        # A diminishing-returns soft-exit is resumable — final-report --archive
        # must leave the active progress file in place (and skip the .done.json
        # rename) so the advertised --resume can continue the run.
        ppath = _seed_deep_progress(tmp_path)
        data = _read_progress(ppath)
        data["termination"] = {"reason": "diminishing-returns", "message": "plateau"}
        ppath.write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.setattr(reporting, "git_current_branch", lambda _cwd: "")
        exit_code = _run("final-report", "--progress-file", str(ppath), "--archive")
        assert exit_code == 0
        out = capsys.readouterr().out
        assert "not-archived" in out
        assert ppath.exists()
        assert not (tmp_path / "progress.done.json").exists()


# ---------------------------------------------------------------------------
# snapshot
# ---------------------------------------------------------------------------


class TestSnapshot:
    def test_captures_head(self, tmp_path, capsys, monkeypatch):
        ppath = _seed_deep_progress(tmp_path)
        monkeypatch.setattr(cli, "git_rev_parse_head", lambda _cwd: "head_sha")
        monkeypatch.setattr(cli, "git_stash_snapshot", lambda _cwd: None)
        exit_code = _run("snapshot", "--progress-file", str(ppath))
        assert exit_code == 0
        assert capsys.readouterr().out.strip() == "head_sha"
        data = _read_progress(ppath)
        assert data["_snapshot"]["pre_head"] == "head_sha"
        assert data["_snapshot"]["pre_stash"] is None

    def test_includes_stash(self, tmp_path, monkeypatch):
        ppath = _seed_deep_progress(tmp_path)
        monkeypatch.setattr(cli, "git_rev_parse_head", lambda _cwd: "head_sha")
        monkeypatch.setattr(cli, "git_stash_snapshot", lambda _cwd: "stash_sha")
        _run("snapshot", "--progress-file", str(ppath), "--include-stash")
        data = _read_progress(ppath)
        assert data["_snapshot"]["pre_stash"] == "stash_sha"

    def test_head_unavailable_returns_error(self, tmp_path, capsys, monkeypatch):
        ppath = _seed_deep_progress(tmp_path)
        monkeypatch.setattr(cli, "git_rev_parse_head", lambda _cwd: None)
        exit_code = _run("snapshot", "--progress-file", str(ppath))
        assert exit_code == 1
        assert "Cannot determine HEAD" in capsys.readouterr().err

    def test_auto_stashes_in_no_commit_mode(self, tmp_path, monkeypatch):
        # No --include-stash flag: auto-stash is driven by persisted
        # config.no_commit so the orchestrator never has to remember it.
        ppath = _seed_deep_progress(tmp_path)
        data = _read_progress(ppath)
        data["config"]["no_commit"] = True
        ppath.write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.setattr(cli, "git_rev_parse_head", lambda _cwd: "head_sha")
        monkeypatch.setattr(cli, "git_stash_snapshot", lambda _cwd: "stash_sha")
        _run("snapshot", "--progress-file", str(ppath))
        assert _read_progress(ppath)["_snapshot"]["pre_stash"] == "stash_sha"

    def test_auto_stashes_after_commit_disabled(self, tmp_path, monkeypatch):
        ppath = _seed_deep_progress(tmp_path)
        data = _read_progress(ppath)
        data["commit_disabled"] = True
        ppath.write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.setattr(cli, "git_rev_parse_head", lambda _cwd: "head_sha")
        monkeypatch.setattr(cli, "git_stash_snapshot", lambda _cwd: "stash_sha")
        _run("snapshot", "--progress-file", str(ppath))
        assert _read_progress(ppath)["_snapshot"]["pre_stash"] == "stash_sha"

    def test_stamps_iteration_token(self, tmp_path, monkeypatch):
        ppath = _seed_deep_progress(tmp_path, iteration=3)
        monkeypatch.setattr(cli, "git_rev_parse_head", lambda _cwd: "head_sha")
        monkeypatch.setattr(cli, "git_stash_snapshot", lambda _cwd: None)
        _run("snapshot", "--progress-file", str(ppath))
        assert _read_progress(ppath)["_snapshot"]["iteration_token"] == 3

    def test_stamps_cycle_token_in_coverage_variant(self, tmp_path, monkeypatch):
        # Coverage-variant snapshots must stamp the cycle number via
        # _current_unit's coverage branch (progress["cycle"]["current"]), not an
        # iteration field. Regression for the untested coverage snapshot path.
        ppath = _seed_coverage_progress(tmp_path, cycle=4)
        data = _read_progress(ppath)
        data["_snapshot"]["iteration_token"] = 999  # stale — must be overwritten
        ppath.write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.setattr(cli, "git_rev_parse_head", lambda _cwd: "head_sha")
        monkeypatch.setattr(cli, "git_stash_snapshot", lambda _cwd: None)
        _run("snapshot", "--progress-file", str(ppath))
        assert _read_progress(ppath)["_snapshot"]["iteration_token"] == 4


# ---------------------------------------------------------------------------
# --no-commit persistence + commit-checkpoint self-skip
# ---------------------------------------------------------------------------


class TestNoCommitMode:
    def test_init_persists_no_commit(self, tmp_path, monkeypatch):
        repo = _make_repo(tmp_path)
        _stub_git(monkeypatch)
        ppath = repo / "progress.json"
        _run(
            "init",
            "--skill",
            "code-review",
            "--no-commit",
            "--progress-file",
            str(ppath),
            "--project-dir",
            str(repo),
        )
        data = _read_progress(ppath)
        assert data["config"]["no_commit"] is True
        assert data["commit_disabled"] is False

    def test_init_commit_mode_is_default(self, tmp_path, monkeypatch):
        repo = _make_repo(tmp_path)
        _stub_git(monkeypatch)
        ppath = repo / "progress.json"
        _run(
            "init",
            "--skill",
            "code-review",
            "--progress-file",
            str(ppath),
            "--project-dir",
            str(repo),
        )
        assert _read_progress(ppath)["config"]["no_commit"] is False

    def test_commit_checkpoint_self_skips_when_no_commit(
        self, tmp_path, capsys, monkeypatch
    ):
        ppath = _seed_deep_progress(tmp_path)
        data = _read_progress(ppath)
        data["config"]["no_commit"] = True
        ppath.write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.setattr(
            cli,
            "git_commit_checkpoint",
            lambda *_a, **_kw: pytest.fail("must not commit in no-commit mode"),
        )
        exit_code = _run("commit-checkpoint", "--progress-file", str(ppath))
        assert exit_code == 0
        assert capsys.readouterr().out.strip() == "commit-skipped"

    def test_commit_checkpoint_self_skips_after_commit_disabled(
        self, tmp_path, capsys, monkeypatch
    ):
        # A checkpoint after a prior commit-failed (commit_disabled=True)
        # self-skips even though the run was not started --no-commit.
        ppath = _seed_deep_progress(tmp_path)
        data = _read_progress(ppath)
        data["commit_disabled"] = True
        ppath.write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.setattr(
            cli,
            "git_commit_checkpoint",
            lambda *_a, **_kw: pytest.fail("must not commit after commit_disabled"),
        )
        exit_code = _run("commit-checkpoint", "--progress-file", str(ppath))
        assert exit_code == 0
        assert capsys.readouterr().out.strip() == "commit-skipped"


# ---------------------------------------------------------------------------
# snapshot-freshness guard (skipped-snapshot detection)
# ---------------------------------------------------------------------------


class TestSnapshotFreshnessGuard:
    def test_deep_step_errors_on_stale_token(self, tmp_path, capsys):
        ppath = _seed_deep_progress(tmp_path, iteration=3)
        data = _read_progress(ppath)
        data["_snapshot"]["iteration_token"] = 2  # snapshot skipped this iteration
        ppath.write_text(json.dumps(data), encoding="utf-8")
        result = tmp_path / "result.json"
        result.write_text(
            json.dumps(
                {
                    "iteration": 3,
                    "new_findings": [],
                    "fixes_applied": [],
                    "no_new_findings": False,
                    "no_actionable_fixes": True,
                }
            ),
            encoding="utf-8",
        )
        exit_code = _run(
            "deep-step", "--progress-file", str(ppath), "--result-file", str(result)
        )
        assert exit_code == 1
        assert "stale" in capsys.readouterr().err

    def test_unit_test_step_errors_on_stale_token(self, tmp_path, capsys):
        ppath = _seed_coverage_progress(tmp_path, cycle=2)
        data = _read_progress(ppath)
        data["_snapshot"]["iteration_token"] = 1
        ppath.write_text(json.dumps(data), encoding="utf-8")
        result = tmp_path / "result.json"
        result.write_text(
            json.dumps(
                {
                    "coverage": {},
                    "tests_written": [],
                    "untestable_code": [],
                    "bugs_discovered": [],
                }
            ),
            encoding="utf-8",
        )
        exit_code = _run(
            "unit-test-step",
            "--progress-file",
            str(ppath),
            "--result-file",
            str(result),
        )
        assert exit_code == 1
        assert "stale" in capsys.readouterr().err

    def test_refactor_step_errors_on_stale_token(self, tmp_path, capsys):
        ppath = _seed_coverage_progress(tmp_path, cycle=2)
        data = _read_progress(ppath)
        data["_snapshot"]["iteration_token"] = 1
        ppath.write_text(json.dumps(data), encoding="utf-8")
        result = tmp_path / "result.json"
        result.write_text(
            json.dumps({"new_findings": [], "fixes_applied": []}), encoding="utf-8"
        )
        exit_code = _run(
            "refactor-step",
            "--progress-file",
            str(ppath),
            "--result-file",
            str(result),
        )
        assert exit_code == 1
        assert "stale" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# unit-test-step state-merge substructure
# ---------------------------------------------------------------------------


class TestUnitTestStepStateMerge:
    def test_records_coverage_scope_dedup_and_bugs(self, tmp_path, monkeypatch):
        ppath = _seed_coverage_progress(tmp_path, cycle=1)
        monkeypatch.setattr(cli, "run_tests", lambda *a, **kw: (True, "ok"))
        dup = {"file": "u.py", "line": 10, "function": "f"}
        result = tmp_path / "result.json"
        result.write_text(
            json.dumps(
                {
                    "coverage": {
                        "before": 50,
                        "after": 60,
                        "delta": 10,
                        "tool": "pytest-cov",
                    },
                    "tests_written": [{"file": "t.py", "target_file": "s.py"}],
                    "untestable_code": [
                        {**dup, "barrier": "global state"},
                        {**dup, "barrier": "duplicate - same key"},
                    ],
                    "bugs_discovered": [{"file": "b.py", "summary": "off-by-one"}],
                    "no_new_tests": False,
                    "no_untestable_code": False,
                    "no_coverage_gained": False,
                }
            ),
            encoding="utf-8",
        )
        exit_code = _run(
            "unit-test-step",
            "--progress-file",
            str(ppath),
            "--result-file",
            str(result),
        )
        assert exit_code == 0
        data = _read_progress(ppath)
        assert data["coverage"]["baseline"] == 50
        assert data["coverage"]["current"] == 60
        assert data["coverage"]["tool"] == "pytest-cov"
        assert len(data["coverage"]["history"]) == 1
        assert data["coverage"]["history"][0]["delta"] == 10
        # dedup by (file, line, function) keeps a single entry
        assert len(data["untestable_code"]) == 1
        # refactor-phase scope refreshed from pending untestable files
        assert data["scope_files"]["current"] == ["u.py"]
        # bugs tagged with the discovering cycle
        assert data["bugs_discovered"][0]["cycle_discovered"] == 1

    def test_untestable_file_path_normalized_on_storage(self, tmp_path, monkeypatch):
        # A unit-test subagent that reports an untestable file with OS-native
        # backslashes must be stored with forward slashes, so the dedup key here
        # and the refactor phase's touched-file match are separator-agnostic.
        ppath = _seed_coverage_progress(tmp_path)
        monkeypatch.setattr(cli, "run_tests", lambda *a, **kw: (True, "ok"))
        result = tmp_path / "result.json"
        result.write_text(
            json.dumps(
                {
                    "untestable_code": [
                        {
                            "file": "src\\pkg\\mod.py",
                            "line": 5,
                            "function": "f",
                            "barrier": "global state",
                        }
                    ],
                    "no_new_tests": False,
                    "no_untestable_code": False,
                    "no_coverage_gained": False,
                }
            ),
            encoding="utf-8",
        )
        exit_code = _run(
            "unit-test-step",
            "--progress-file",
            str(ppath),
            "--result-file",
            str(result),
        )
        assert exit_code == 0
        data = _read_progress(ppath)
        assert data["untestable_code"][0]["file"] == "src/pkg/mod.py"
        assert data["scope_files"]["current"] == ["src/pkg/mod.py"]


# ---------------------------------------------------------------------------
# _promote_actionable_fixes dedup branch
# ---------------------------------------------------------------------------


class TestPromoteActionableDedup:
    def test_does_not_re_promote_already_applied_finding(
        self, tmp_path, capsys, monkeypatch
    ):
        # no_actionable_fixes=True with new_findings = [already-applied, fresh].
        # The dedup branch must skip re-promoting the already-applied one so the
        # fixed count reflects 2 distinct fixes, not 3.
        ppath = _seed_deep_progress(tmp_path)
        monkeypatch.setattr(cli, "run_tests", lambda *a, **kw: (True, "ok"))
        applied = {
            "file": "a.py",
            "line": 1,
            "category": "x",
            "summary": "s",
            "pre_edit_content": "a",
            "post_edit_content": "b",
        }
        fresh = {
            "file": "c.py",
            "line": 9,
            "category": "x",
            "summary": "t",
            "pre_edit_content": "c",
            "post_edit_content": "d",
        }
        result = tmp_path / "result.json"
        result.write_text(
            json.dumps(
                {
                    "iteration": 1,
                    "new_findings": [applied, fresh],
                    "fixes_applied": [applied],
                    "no_new_findings": False,
                    "no_actionable_fixes": True,
                }
            ),
            encoding="utf-8",
        )
        exit_code = _run(
            "deep-step", "--progress-file", str(ppath), "--result-file", str(result)
        )
        assert exit_code == 0
        assert capsys.readouterr().out.strip().startswith("applied")
        data = _read_progress(ppath)
        assert data["iteration_history"][-1]["fixed"] == 2
        assert len(data["findings"]) == 2


# ---------------------------------------------------------------------------
# final-report body content
# ---------------------------------------------------------------------------


class TestFinalReportBody:
    def test_deep_report_renders_findings_and_footer(
        self, tmp_path, capsys, monkeypatch
    ):
        ppath = _seed_deep_progress(tmp_path)
        data = _read_progress(ppath)
        data["iteration"]["completed"] = 1
        data["findings"] = [
            {
                "file": "a.py",
                "line": 1,
                "category": "bug",
                "summary": "fixed one",
                "status": "fixed",
            },
            {
                "file": "b.py",
                "line": 2,
                "category": "bug",
                "summary": "stuck",
                "status": "persistent — fix failed",
            },
        ]
        ppath.write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.setattr(reporting, "git_current_branch", lambda _cwd: "feat/x")
        exit_code = _run("final-report", "--progress-file", str(ppath))
        assert exit_code == 0
        out = capsys.readouterr().out
        # per-finding table rows render file:line + status
        assert "a.py:1" in out
        assert "b.py:2" in out
        assert "persistent — fix failed" in out
        # rollback footer prints (a fix exists) with the push line on a feature branch
        assert "git reset --hard" in out
        assert "git push -u origin feat/x" in out

    def test_rollback_footer_suppresses_push_on_master(
        self, tmp_path, capsys, monkeypatch
    ):
        ppath = _seed_deep_progress(tmp_path)
        data = _read_progress(ppath)
        data["findings"] = [
            {
                "file": "a.py",
                "line": 1,
                "category": "bug",
                "summary": "fixed one",
                "status": "fixed",
            },
        ]
        ppath.write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.setattr(reporting, "git_current_branch", lambda _cwd: "master")
        _run("final-report", "--progress-file", str(ppath))
        out = capsys.readouterr().out
        assert "git reset --hard" in out  # footer still prints
        assert "git push -u origin" not in out  # but not the branch-push line

    def test_coverage_report_renders_body_and_history(
        self, tmp_path, capsys, monkeypatch
    ):
        # The populated coverage-report body (coverage delta, summary counts,
        # per-cycle history table) must render — symmetric with the deep-report
        # body test above. Guards reporting.print_coverage_report lines that an
        # empty-progress header test otherwise left uncovered.
        ppath = _seed_coverage_progress(tmp_path, cycle=3)
        data = _read_progress(ppath)
        data["coverage"] = {
            "baseline": 40,
            "current": 75,
            "tool": "pytest-cov",
            "history": [
                {"cycle": 1, "before": 40, "after": 60, "delta": 20},
                {"cycle": 2, "before": 60, "after": 75, "delta": 15},
            ],
        }
        data["tests_created"] = [
            {"file": "test_a.py", "target_file": "a.py", "test_count": 5, "cycle": 1},
            {"file": "test_b.py", "target_file": "b.py", "test_count": 3, "cycle": 2},
        ]
        data["refactor_findings"] = [
            {
                "file": "a.py",
                "line": 1,
                "category": "Testability",
                "summary": "extract helper",
                "status": "fixed",
                "cycle": 1,
            },
        ]
        data["untestable_code"] = [{"file": "c.py", "reason": "global state"}]
        data["bugs_discovered"] = [{"file": "b.py", "summary": "off-by-one"}]
        ppath.write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.setattr(reporting, "git_current_branch", lambda _cwd: "feat/x")
        exit_code = _run("final-report", "--progress-file", str(ppath))
        assert exit_code == 0
        out = capsys.readouterr().out
        assert "40% -> 75%" in out
        assert "8 tests in 2 files" in out
        assert "Testability fixes: 1" in out
        assert "Still untestable: 1" in out
        assert "Bugs discovered:" in out
        # per-cycle history table renders both cycles' deltas
        assert "Before" in out and "Delta" in out
        assert "20" in out
        assert "15" in out

    def test_coverage_report_handles_measured_baseline_without_current(
        self, tmp_path, capsys, monkeypatch
    ):
        # baseline measured but no later 'after' recorded must not print "None%".
        ppath = _seed_coverage_progress(tmp_path, cycle=1)
        data = _read_progress(ppath)
        data["coverage"] = {
            "baseline": 73,
            "current": None,
            "tool": None,
            "history": [],
        }
        ppath.write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.setattr(reporting, "git_current_branch", lambda _cwd: "feat/x")
        exit_code = _run("final-report", "--progress-file", str(ppath))
        assert exit_code == 0
        out = capsys.readouterr().out
        assert "None%" not in out
        assert "73%" in out


# ---------------------------------------------------------------------------
# diminishing-returns soft-exit branches
# ---------------------------------------------------------------------------


class TestSoftExitBranches:
    def test_no_soft_exit_before_min_iteration(self, tmp_path, capsys):
        ppath = _seed_deep_progress(tmp_path, iteration=3)
        data = _read_progress(ppath)
        data["iteration_history"] = [
            {
                "iteration": 2,
                "new_findings": 0,
                "fixed": 0,
                "reverted": 0,
                "persistent": 0,
                "test_passed": True,
            },
            {
                "iteration": 3,
                "new_findings": 0,
                "fixed": 0,
                "reverted": 0,
                "persistent": 0,
                "test_passed": True,
            },
        ]
        ppath.write_text(json.dumps(data), encoding="utf-8")
        _run("check-termination", "--progress-file", str(ppath))
        assert capsys.readouterr().out.strip() == "continue"

    def test_high_yield_resets_window(self, tmp_path, capsys):
        ppath = _seed_deep_progress(tmp_path, iteration=5)
        data = _read_progress(ppath)
        data["iteration_history"] = [
            {
                "iteration": 4,
                "new_findings": 3,
                "fixed": 3,
                "reverted": 0,
                "persistent": 0,
                "test_passed": True,
            },
            {
                "iteration": 5,
                "new_findings": 0,
                "fixed": 0,
                "reverted": 0,
                "persistent": 0,
                "test_passed": True,
            },
        ]
        ppath.write_text(json.dumps(data), encoding="utf-8")
        _run("check-termination", "--progress-file", str(ppath))
        assert capsys.readouterr().out.strip() == "continue"

    def test_reverted_fix_resets_window(self, tmp_path, capsys):
        ppath = _seed_deep_progress(tmp_path, iteration=5)
        data = _read_progress(ppath)
        data["iteration_history"] = [
            {
                "iteration": 4,
                "new_findings": 1,
                "fixed": 0,
                "reverted": 1,
                "persistent": 0,
                "test_passed": False,
            },
            {
                "iteration": 5,
                "new_findings": 1,
                "fixed": 1,
                "reverted": 0,
                "persistent": 0,
                "test_passed": True,
            },
        ]
        ppath.write_text(json.dumps(data), encoding="utf-8")
        _run("check-termination", "--progress-file", str(ppath))
        assert capsys.readouterr().out.strip() == "continue"
