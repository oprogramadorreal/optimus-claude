"""Tests for the orchestrator CLI (`scripts/harness_common/cli.py`)."""

import json

import pytest
from harness_common import cli, reporting

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


def _stub_git(monkeypatch, *, head="abc1234567890abc", branch_files=None, pr=None):
    monkeypatch.setattr(cli, "git_rev_parse_head", lambda _cwd: head)
    monkeypatch.setattr(
        cli,
        "git_discover_branch_files",
        lambda _cwd, path_filter=None: (branch_files or [], "origin/main"),
    )
    monkeypatch.setattr(cli, "git_fetch_open_pr_description", lambda _cwd: pr)


def _read_progress(path):
    return json.loads(path.read_text(encoding="utf-8"))


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
        "_snapshot": {"pre_head": "abc1234", "pre_stash": None},
    }
    path = tmp_path / "progress.json"
    path.write_text(json.dumps(progress, indent=2), encoding="utf-8")
    return path


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

        def _stub_bisect(fixes, _tc, _cwd, on_outcome=None):
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

        def _stub_bisect(fixes, _tc, _cwd, on_outcome=None):
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

        def _stub_bisect(fixes, _tc, _cwd, on_outcome=None):
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
        "_snapshot": {"pre_head": "abc1234", "pre_stash": None},
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

        def _stub_bisect(fixes, _tc, _cwd, on_outcome=None):
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

        def _stub_bisect(fixes, _tc, _cwd, on_outcome=None):
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

        def _stub_bisect(fixes, _tc, _cwd, on_outcome=None):
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
            return True

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
            return True

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
            return True

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
        # The orchestrator depends on the "commit-failed" marker to switch
        # remaining iterations to --no-commit mode. Regression for an
        # untested exit path.
        ppath = _seed_deep_progress(tmp_path)
        monkeypatch.setattr(cli, "git_diff_has_changes", lambda _cwd: True)
        monkeypatch.setattr(cli, "git_commit_checkpoint", lambda *_a, **_kw: False)
        exit_code = _run("commit-checkpoint", "--progress-file", str(ppath))
        assert exit_code == 1
        assert capsys.readouterr().out.strip() == "commit-failed"


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
