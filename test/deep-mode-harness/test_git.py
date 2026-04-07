import json
import subprocess
from unittest.mock import MagicMock, call, patch

from harness_common.git import _clean_working_tree
from impl.git import (  # noqa: F401 — re-exports from harness_common
    _base_from_symbolic_ref,
    _detect_base_branch,
    _verify_ref,
    git_commit_checkpoint,
    git_current_branch,
    git_diff_has_changes,
    git_discover_branch_files,
    git_fetch_open_pr_description,
    git_restore_snapshot,
    git_restore_to,
    git_rev_parse_head,
    git_stash_snapshot,
    restore_working_tree,
)
from impl.reporting import build_commit_body


class TestBuildCommitBody:
    def test_empty_findings(self):
        progress = {"findings": []}
        assert build_commit_body(progress, 1) == ""

    def test_no_matching_iteration(self):
        progress = {"findings": [{"iteration_last_attempted": 2, "status": "fixed"}]}
        assert build_commit_body(progress, 1) == ""

    def test_fixed_findings(self):
        progress = {
            "findings": [
                {
                    "iteration_last_attempted": 1,
                    "status": "fixed",
                    "file": "src/a.js",
                    "line": 10,
                    "category": "bug",
                    "summary": "Fix null check",
                },
            ]
        }
        body = build_commit_body(progress, 1)
        assert "Fixed:" in body
        assert "src/a.js:10" in body
        assert "[bug]" in body

    def test_reverted_findings(self):
        progress = {
            "findings": [
                {
                    "iteration_last_attempted": 1,
                    "status": "reverted — test failure",
                    "file": "src/b.js",
                    "line": 5,
                    "category": "style",
                    "summary": "Reformat",
                },
            ]
        }
        body = build_commit_body(progress, 1)
        assert "Reverted (test failure):" in body

    def test_max_entries_truncation(self):
        findings = []
        for i in range(15):
            findings.append(
                {
                    "iteration_last_attempted": 1,
                    "status": "fixed",
                    "file": f"src/file{i}.js",
                    "line": i,
                    "category": "bug",
                    "summary": f"Fix {i}",
                }
            )
        progress = {"findings": findings}
        body = build_commit_body(progress, 1, max_entries=5)
        assert "... and 10 more" in body

    def test_long_summary_truncated(self):
        progress = {
            "findings": [
                {
                    "iteration_last_attempted": 1,
                    "status": "fixed",
                    "file": "a.js",
                    "line": 1,
                    "category": "x",
                    "summary": "A" * 100,
                },
            ]
        }
        body = build_commit_body(progress, 1)
        assert "..." in body


class TestGitRevParseHead:
    @patch("harness_common.git.subprocess.run")
    def test_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="abc123\n")
        assert git_rev_parse_head("/tmp") == "abc123"

    @patch("harness_common.git.subprocess.run")
    def test_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        assert git_rev_parse_head("/tmp") is None


class TestCleanWorkingTree:
    @patch("harness_common.git.subprocess.run")
    def test_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        _clean_working_tree("/tmp/project")
        assert mock_run.call_count == 2

    @patch("harness_common.git.subprocess.run")
    def test_clean_failure_prints_warning(self, mock_run, capsys):
        # checkout succeeds, clean fails
        mock_run.side_effect = [
            MagicMock(returncode=0),
            MagicMock(returncode=1, stderr="permission denied"),
        ]
        _clean_working_tree("/tmp/project")
        assert "WARNING" in capsys.readouterr().out

    @patch("harness_common.git.subprocess.run")
    def test_checkout_failure_prints_warning(self, mock_run, capsys):
        # checkout fails, clean succeeds
        mock_run.side_effect = [
            MagicMock(returncode=1, stderr="error: checkout failed"),
            MagicMock(returncode=0),
        ]
        _clean_working_tree("/tmp/project")
        output = capsys.readouterr().out
        assert "WARNING" in output
        assert "git checkout" in output


class TestGitRestoreTo:
    @patch("harness_common.git._clean_working_tree")
    @patch("harness_common.git.subprocess.run")
    def test_success(self, mock_run, mock_clean):
        mock_run.return_value = MagicMock(returncode=0)
        git_restore_to("abc123", "/tmp")
        mock_clean.assert_called_once()

    @patch("harness_common.git.subprocess.run")
    def test_failure_raises(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="error: pathspec")
        import pytest

        with pytest.raises(RuntimeError, match="git checkout .* failed"):
            git_restore_to("abc123", "/tmp")


class TestGitCurrentBranch:
    @patch("harness_common.git.subprocess.run")
    def test_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="feature/foo\n")
        assert git_current_branch("/tmp") == "feature/foo"

    @patch("harness_common.git.subprocess.run")
    def test_failure_returns_empty(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        assert git_current_branch("/tmp") == ""


class TestGitDiffHasChanges:
    @patch("harness_common.git.subprocess.run")
    def test_unstaged_changes(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        assert git_diff_has_changes("/tmp") is True

    @patch("harness_common.git.subprocess.run")
    def test_staged_changes(self, mock_run):
        # diff --quiet passes, diff --cached --quiet fails
        mock_run.side_effect = [
            MagicMock(returncode=0),
            MagicMock(returncode=1),
        ]
        assert git_diff_has_changes("/tmp") is True

    @patch("harness_common.git.subprocess.run")
    def test_untracked_files(self, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=0),  # diff --quiet
            MagicMock(returncode=0),  # diff --cached --quiet
            MagicMock(returncode=0, stdout="new_file.txt\n"),  # ls-files
        ]
        assert git_diff_has_changes("/tmp") is True

    @patch("harness_common.git.subprocess.run")
    def test_no_changes(self, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=0),
            MagicMock(returncode=0),
            MagicMock(returncode=0, stdout=""),
        ]
        assert git_diff_has_changes("/tmp") is False


class TestRestoreWorkingTree:
    @patch("harness_common.git.git_restore_to")
    @patch("harness_common.git.git_restore_snapshot", return_value=True)
    def test_stash_path(self, mock_snapshot, mock_restore_to):
        restore_working_tree("stash123", "head123", "/tmp")
        mock_snapshot.assert_called_once_with("stash123", "/tmp", _run=None)
        mock_restore_to.assert_not_called()

    @patch("harness_common.git.git_restore_to")
    @patch("harness_common.git.git_restore_snapshot", return_value=False)
    def test_stash_fails_falls_back_to_head(self, mock_snapshot, mock_restore_to):
        restore_working_tree("stash123", "head123", "/tmp")
        mock_restore_to.assert_called_once_with("head123", "/tmp", _run=None)

    @patch("harness_common.git.git_restore_to")
    def test_no_stash_uses_head(self, mock_restore_to):
        restore_working_tree(None, "head123", "/tmp")
        mock_restore_to.assert_called_once_with("head123", "/tmp", _run=None)


class TestGitStashSnapshot:
    @patch("harness_common.git.subprocess.run")
    def test_success(self, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc123\n"),  # stash create
            MagicMock(returncode=0),  # stash store
        ]
        assert git_stash_snapshot("/tmp") == "abc123"

    @patch("harness_common.git.subprocess.run")
    def test_no_changes(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        assert git_stash_snapshot("/tmp") is None

    @patch("harness_common.git.subprocess.run")
    def test_store_failure_returns_none(self, mock_run, capsys):
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc123\n"),
            MagicMock(returncode=1, stderr="error storing"),
        ]
        assert git_stash_snapshot("/tmp") is None
        assert "WARNING" in capsys.readouterr().out


class TestGitRestoreSnapshot:
    @patch("harness_common.git.subprocess.run")
    @patch("harness_common.git._clean_working_tree")
    def test_success(self, mock_clean, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        assert git_restore_snapshot("abc123", "/tmp") is True
        mock_clean.assert_called_once()

    @patch("harness_common.git.subprocess.run")
    @patch("harness_common.git._clean_working_tree")
    def test_failure(self, mock_clean, mock_run, capsys):
        mock_run.return_value = MagicMock(returncode=1, stderr="conflict")
        assert git_restore_snapshot("abc123", "/tmp") is False
        assert "WARNING" in capsys.readouterr().out

    @patch("harness_common.git.subprocess.run")
    @patch("harness_common.git._clean_working_tree")
    def test_success_drops_matching_stash(self, mock_clean, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=0),  # stash apply
            MagicMock(
                returncode=0, stdout="stash@{0} abc123\nstash@{1} def456\n"
            ),  # stash list
            MagicMock(returncode=0),  # stash drop
        ]
        assert git_restore_snapshot("abc123", "/tmp") is True
        # Verify stash drop was called with the correct ref
        drop_call = mock_run.call_args_list[2]
        assert drop_call[0][0] == ["git", "stash", "drop", "stash@{0}"]


class TestVerifyRef:
    @patch("impl.git.subprocess.run")
    def test_timeout_returns_false(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(
            ["git", "rev-parse", "--verify", "origin/main"], 10
        )
        assert _verify_ref("/tmp", "origin/main") is False

    @patch("impl.git.subprocess.run")
    def test_file_not_found_returns_false(self, mock_run):
        mock_run.side_effect = FileNotFoundError("git binary missing")
        assert _verify_ref("/tmp", "origin/main") is False


class TestBaseFromSymbolicRef:
    @patch("impl.git.subprocess.run")
    def test_timeout_returns_none(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD"], 10
        )
        assert _base_from_symbolic_ref("/tmp") is None

    @patch("impl.git.subprocess.run")
    def test_file_not_found_returns_none(self, mock_run):
        mock_run.side_effect = FileNotFoundError("git binary missing")
        assert _base_from_symbolic_ref("/tmp") is None

    @patch("impl.git.subprocess.run")
    def test_malformed_ref_without_remotes_prefix_returns_none(self, mock_run):
        # symbolic-ref can return a non-standard value (e.g., the ref name was
        # somehow set to a local-only ref). The parser should refuse rather
        # than return a garbled "origin/" string.
        mock_run.return_value = MagicMock(returncode=0, stdout="refs/heads/main\n")
        assert _base_from_symbolic_ref("/tmp") is None


class TestDetectBaseBranch:
    @patch("impl.git.subprocess.run")
    def test_open_pr_returns_pr_base(self, mock_run):
        pr_json = json.dumps({"state": "OPEN", "baseRefName": "develop"})
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=pr_json),  # gh pr view
            MagicMock(returncode=0, stdout="abc123\n"),  # rev-parse verify
        ]
        assert _detect_base_branch("/tmp") == "origin/develop"
        # Verify the rev-parse call was actually issued
        verify_call = mock_run.call_args_list[1]
        assert verify_call[0][0] == ["git", "rev-parse", "--verify", "origin/develop"]

    @patch("impl.git.subprocess.run")
    def test_open_pr_unfetched_base_falls_through(self, mock_run):
        pr_json = json.dumps({"state": "OPEN", "baseRefName": "develop"})
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=pr_json),  # gh pr view
            MagicMock(returncode=1, stdout=""),  # rev-parse verify fails
            MagicMock(
                returncode=0, stdout="refs/remotes/origin/main\n"
            ),  # symbolic-ref
        ]
        assert _detect_base_branch("/tmp") == "origin/main"

    @patch("impl.git.subprocess.run")
    def test_closed_pr_falls_through_to_symbolic_ref(self, mock_run):
        pr_json = json.dumps({"state": "CLOSED", "baseRefName": "main"})
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=pr_json),  # gh pr view (closed)
            MagicMock(
                returncode=0, stdout="refs/remotes/origin/main\n"
            ),  # symbolic-ref
        ]
        assert _detect_base_branch("/tmp") == "origin/main"

    @patch("impl.git.subprocess.run")
    def test_gh_not_found_falls_through(self, mock_run):
        def side_effect(cmd, **kwargs):
            if cmd[0] == "gh":
                raise FileNotFoundError("gh not found")
            if "symbolic-ref" in cmd:
                return MagicMock(returncode=0, stdout="refs/remotes/origin/main\n")
            return MagicMock(returncode=1)

        mock_run.side_effect = side_effect
        assert _detect_base_branch("/tmp") == "origin/main"

    @patch("impl.git.subprocess.run")
    def test_symbolic_ref_strips_prefix(self, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=1),  # gh pr view fails
            MagicMock(
                returncode=0, stdout="refs/remotes/origin/develop\n"
            ),  # symbolic-ref
        ]
        assert _detect_base_branch("/tmp") == "origin/develop"

    @patch("impl.git.subprocess.run")
    def test_fallback_to_origin_main(self, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=1),  # gh fails
            MagicMock(returncode=1),  # symbolic-ref fails
            MagicMock(returncode=0, stdout="abc123\n"),  # origin/main exists
        ]
        assert _detect_base_branch("/tmp") == "origin/main"

    @patch("impl.git.subprocess.run")
    def test_fallback_to_origin_master(self, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=1),  # gh fails
            MagicMock(returncode=1),  # symbolic-ref fails
            MagicMock(returncode=1),  # origin/main doesn't exist
            MagicMock(returncode=0, stdout="abc123\n"),  # origin/master exists
        ]
        assert _detect_base_branch("/tmp") == "origin/master"

    @patch("impl.git.subprocess.run")
    def test_all_detection_fails_returns_none(self, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=1),  # gh fails
            MagicMock(returncode=1),  # symbolic-ref fails
            MagicMock(returncode=1),  # origin/main doesn't exist
            MagicMock(returncode=1),  # origin/master doesn't exist
        ]
        assert _detect_base_branch("/tmp") is None

    @patch("impl.git.subprocess.run")
    def test_gh_timeout_falls_through(self, mock_run):
        def side_effect(cmd, **kwargs):
            if cmd[0] == "gh":
                raise subprocess.TimeoutExpired(cmd, 10)
            if "symbolic-ref" in cmd:
                return MagicMock(returncode=0, stdout="refs/remotes/origin/main\n")
            return MagicMock(returncode=1)

        mock_run.side_effect = side_effect
        assert _detect_base_branch("/tmp") == "origin/main"


class TestGitDiscoverBranchFiles:
    @patch("impl.git._detect_base_branch", return_value="origin/main")
    @patch("impl.git.subprocess.run")
    def test_returns_file_list_and_base(self, mock_run, mock_detect):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="src/app.js\nsrc/utils.js\n"
        )
        files, base = git_discover_branch_files("/tmp")
        assert files == ["src/app.js", "src/utils.js"]
        assert base == "origin/main"
        mock_run.assert_called_once_with(
            ["git", "diff", "--name-only", "origin/main...HEAD"],
            capture_output=True,
            text=True,
            cwd="/tmp",
            timeout=30,
        )

    @patch("impl.git._detect_base_branch", return_value=None)
    def test_no_base_branch_returns_empty(self, mock_detect, capsys):
        files, base = git_discover_branch_files("/tmp")
        assert files == []
        assert base is None
        assert "WARNING" in capsys.readouterr().out

    @patch("impl.git._detect_base_branch", return_value="origin/main")
    @patch("impl.git.subprocess.run")
    def test_diff_failure_returns_empty_with_base(self, mock_run, mock_detect, capsys):
        mock_run.return_value = MagicMock(returncode=1, stderr="fatal: bad revision")
        files, base = git_discover_branch_files("/tmp")
        assert files == []
        assert base == "origin/main"
        assert "WARNING" in capsys.readouterr().out

    @patch("impl.git._detect_base_branch", return_value="origin/main")
    @patch("impl.git.subprocess.run")
    def test_empty_diff_returns_empty_list(self, mock_run, mock_detect):
        mock_run.return_value = MagicMock(returncode=0, stdout="\n")
        files, base = git_discover_branch_files("/tmp")
        assert files == []
        assert base == "origin/main"

    @patch("impl.git._detect_base_branch", return_value="origin/main")
    @patch("impl.git.subprocess.run")
    def test_filters_blank_lines(self, mock_run, mock_detect):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="src/a.js\n\nsrc/b.js\n\n"
        )
        files, base = git_discover_branch_files("/tmp")
        assert files == ["src/a.js", "src/b.js"]

    @patch("impl.git._detect_base_branch", return_value="origin/main")
    @patch("impl.git.subprocess.run")
    def test_path_filter_passes_pathspec(self, mock_run, mock_detect):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="src/auth/login.py\nsrc/auth/session.py\n"
        )
        files, base = git_discover_branch_files("/tmp", path_filter="src/auth")
        assert files == ["src/auth/login.py", "src/auth/session.py"]
        mock_run.assert_called_once_with(
            ["git", "diff", "--name-only", "origin/main...HEAD", "--", "src/auth"],
            capture_output=True,
            text=True,
            cwd="/tmp",
            timeout=30,
        )

    @patch("impl.git._detect_base_branch", return_value="origin/main")
    @patch("impl.git.subprocess.run")
    def test_diff_subprocess_exception_returns_empty_with_base(
        self, mock_run, mock_detect, capsys
    ):
        # Cover the FileNotFoundError/TimeoutExpired branch in
        # git_discover_branch_files: base detection succeeds but the
        # subsequent `git diff --name-only` invocation itself raises.
        mock_run.side_effect = subprocess.TimeoutExpired(
            ["git", "diff", "--name-only", "origin/main...HEAD"], 30
        )
        files, base = git_discover_branch_files("/tmp")
        assert files == []
        assert base == "origin/main"
        assert "WARNING" in capsys.readouterr().out

    @patch("impl.git._detect_base_branch", return_value="origin/main")
    @patch("impl.git.subprocess.run")
    def test_no_path_filter_omits_pathspec(self, mock_run, mock_detect):
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        git_discover_branch_files("/tmp")
        cmd = mock_run.call_args[0][0]
        assert cmd == ["git", "diff", "--name-only", "origin/main...HEAD"]


class TestGitFetchOpenPrDescription:
    @patch("impl.git.subprocess.run")
    def test_open_pr_returns_metadata(self, mock_run):
        pr_json = json.dumps(
            {
                "state": "OPEN",
                "title": "Fix auth bug",
                "body": "Fixes #42 by adding null check.",
                "baseRefName": "main",
            }
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=pr_json)
        info = git_fetch_open_pr_description("/tmp")
        assert info == {
            "title": "Fix auth bug",
            "body": "Fixes #42 by adding null check.",
            "base_ref": "origin/main",
        }

    @patch("impl.git.subprocess.run")
    def test_closed_pr_returns_none(self, mock_run):
        pr_json = json.dumps(
            {"state": "CLOSED", "title": "T", "body": "B", "baseRefName": "main"}
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=pr_json)
        assert git_fetch_open_pr_description("/tmp") is None

    @patch("impl.git.subprocess.run")
    def test_gh_not_found_returns_none(self, mock_run):
        mock_run.side_effect = FileNotFoundError("gh missing")
        assert git_fetch_open_pr_description("/tmp") is None

    @patch("impl.git.subprocess.run")
    def test_gh_timeout_returns_none(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired("gh", 10)
        assert git_fetch_open_pr_description("/tmp") is None

    @patch("impl.git.subprocess.run")
    def test_gh_nonzero_exit_returns_none(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        assert git_fetch_open_pr_description("/tmp") is None

    @patch("impl.git.subprocess.run")
    def test_malformed_json_returns_none(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="not json{")
        assert git_fetch_open_pr_description("/tmp") is None

    @patch("impl.git.subprocess.run")
    def test_oversized_body_is_truncated(self, mock_run):
        big = "x" * 5000
        pr_json = json.dumps(
            {"state": "OPEN", "title": "T", "body": big, "baseRefName": "main"}
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=pr_json)
        info = git_fetch_open_pr_description("/tmp")
        assert info is not None
        assert len(info["body"]) < 5000
        assert info["body"].endswith("[...truncated...]")

    @patch("impl.git.subprocess.run")
    def test_missing_base_ref_name_returns_none_base(self, mock_run):
        pr_json = json.dumps({"state": "OPEN", "title": "T", "body": "B"})
        mock_run.return_value = MagicMock(returncode=0, stdout=pr_json)
        info = git_fetch_open_pr_description("/tmp")
        assert info is not None
        assert info["base_ref"] is None

    @patch("impl.git.subprocess.run")
    def test_null_body_normalized_to_empty_string(self, mock_run):
        """gh can return body: null for a PR with no description."""
        pr_json = json.dumps(
            {"state": "OPEN", "title": "T", "body": None, "baseRefName": "main"}
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=pr_json)
        info = git_fetch_open_pr_description("/tmp")
        assert info is not None
        assert info["body"] == ""

    @patch("impl.git.subprocess.run")
    def test_oversized_title_is_truncated(self, mock_run):
        big_title = "T" * 600
        pr_json = json.dumps(
            {"state": "OPEN", "title": big_title, "body": "", "baseRefName": "main"}
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=pr_json)
        info = git_fetch_open_pr_description("/tmp")
        assert info is not None
        # Title is capped at _PR_TITLE_TRUNCATE_LIMIT (500)
        assert len(info["title"]) == 500
        assert info["title"] == "T" * 500


class TestGitCommitCheckpoint:
    @patch("harness_common.git.subprocess.run")
    def test_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        progress = {
            "skill": "code-review",
            "iteration_history": [{"iteration": 1, "fixed": 2, "reverted": 0}],
            "findings": [],
        }
        assert git_commit_checkpoint(progress, 1, "/tmp") is True
        # Should call: git add -A, git reset (x2), git commit
        assert mock_run.call_count == 4

    @patch("harness_common.git.subprocess.run")
    def test_add_failure(self, mock_run, capsys):
        mock_run.return_value = MagicMock(returncode=1, stderr="add failed")
        progress = {
            "skill": "code-review",
            "iteration_history": [],
            "findings": [],
        }
        assert git_commit_checkpoint(progress, 1, "/tmp") is False
        assert "WARNING" in capsys.readouterr().out

    @patch("harness_common.git.subprocess.run")
    def test_commit_failure(self, mock_run, capsys):
        # add succeeds, reset calls succeed, commit fails with real error
        mock_run.side_effect = [
            MagicMock(returncode=0),  # git add -A
            MagicMock(returncode=0),  # git reset (progress file)
            MagicMock(returncode=0),  # git reset (backup)
            MagicMock(returncode=1, stdout="", stderr="fatal: something broke"),
        ]
        progress = {
            "skill": "code-review",
            "iteration_history": [{"iteration": 1, "fixed": 1, "reverted": 0}],
            "findings": [],
        }
        assert git_commit_checkpoint(progress, 1, "/tmp") is False
        assert "WARNING" in capsys.readouterr().out

    @patch("harness_common.git.subprocess.run")
    def test_nothing_to_commit_returns_true(self, mock_run):
        # add succeeds, reset calls succeed, commit says nothing to commit
        mock_run.side_effect = [
            MagicMock(returncode=0),  # git add -A
            MagicMock(returncode=0),  # git reset (progress file)
            MagicMock(returncode=0),  # git reset (backup)
            MagicMock(
                returncode=1,
                stdout="On branch main\nnothing to commit, working tree clean\n",
                stderr="",
            ),
        ]
        progress = {
            "skill": "code-review",
            "iteration_history": [{"iteration": 1, "fixed": 0, "reverted": 0}],
            "findings": [],
        }
        assert git_commit_checkpoint(progress, 1, "/tmp") is True
