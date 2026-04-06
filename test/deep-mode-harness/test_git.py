import json
import subprocess
from unittest.mock import MagicMock, call, patch

from impl.git import (
    _clean_working_tree,
    _detect_base_branch,
    git_commit_checkpoint,
    git_current_branch,
    git_diff_has_changes,
    git_discover_branch_files,
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
    @patch("impl.git.subprocess.run")
    def test_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="abc123\n")
        assert git_rev_parse_head("/tmp") == "abc123"

    @patch("impl.git.subprocess.run")
    def test_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        assert git_rev_parse_head("/tmp") is None


class TestCleanWorkingTree:
    @patch("impl.git.subprocess.run")
    def test_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        _clean_working_tree("/tmp/project")
        assert mock_run.call_count == 2

    @patch("impl.git.subprocess.run")
    def test_clean_failure_prints_warning(self, mock_run, capsys):
        # checkout succeeds, clean fails
        mock_run.side_effect = [
            MagicMock(returncode=0),
            MagicMock(returncode=1, stderr="permission denied"),
        ]
        _clean_working_tree("/tmp/project")
        assert "WARNING" in capsys.readouterr().out

    @patch("impl.git.subprocess.run")
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
    @patch("impl.git._clean_working_tree")
    @patch("impl.git.subprocess.run")
    def test_success(self, mock_run, mock_clean):
        mock_run.return_value = MagicMock(returncode=0)
        git_restore_to("abc123", "/tmp")
        mock_clean.assert_called_once()

    @patch("impl.git.subprocess.run")
    def test_failure_raises(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="error: pathspec")
        import pytest

        with pytest.raises(RuntimeError, match="git checkout .* failed"):
            git_restore_to("abc123", "/tmp")


class TestGitCurrentBranch:
    @patch("impl.git.subprocess.run")
    def test_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="feature/foo\n")
        assert git_current_branch("/tmp") == "feature/foo"

    @patch("impl.git.subprocess.run")
    def test_failure_returns_empty(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        assert git_current_branch("/tmp") == ""


class TestGitDiffHasChanges:
    @patch("impl.git.subprocess.run")
    def test_unstaged_changes(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        assert git_diff_has_changes("/tmp") is True

    @patch("impl.git.subprocess.run")
    def test_staged_changes(self, mock_run):
        # diff --quiet passes, diff --cached --quiet fails
        mock_run.side_effect = [
            MagicMock(returncode=0),
            MagicMock(returncode=1),
        ]
        assert git_diff_has_changes("/tmp") is True

    @patch("impl.git.subprocess.run")
    def test_untracked_files(self, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=0),  # diff --quiet
            MagicMock(returncode=0),  # diff --cached --quiet
            MagicMock(returncode=0, stdout="new_file.txt\n"),  # ls-files
        ]
        assert git_diff_has_changes("/tmp") is True

    @patch("impl.git.subprocess.run")
    def test_no_changes(self, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=0),
            MagicMock(returncode=0),
            MagicMock(returncode=0, stdout=""),
        ]
        assert git_diff_has_changes("/tmp") is False


class TestRestoreWorkingTree:
    @patch("impl.git.git_restore_to")
    @patch("impl.git.git_restore_snapshot", return_value=True)
    def test_stash_path(self, mock_snapshot, mock_restore_to):
        restore_working_tree("stash123", "head123", "/tmp")
        mock_snapshot.assert_called_once_with("stash123", "/tmp")
        mock_restore_to.assert_not_called()

    @patch("impl.git.git_restore_to")
    @patch("impl.git.git_restore_snapshot", return_value=False)
    def test_stash_fails_falls_back_to_head(self, mock_snapshot, mock_restore_to):
        restore_working_tree("stash123", "head123", "/tmp")
        mock_restore_to.assert_called_once_with("head123", "/tmp")

    @patch("impl.git.git_restore_to")
    def test_no_stash_uses_head(self, mock_restore_to):
        restore_working_tree(None, "head123", "/tmp")
        mock_restore_to.assert_called_once_with("head123", "/tmp")


class TestGitStashSnapshot:
    @patch("impl.git.subprocess.run")
    def test_success(self, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc123\n"),  # stash create
            MagicMock(returncode=0),  # stash store
        ]
        assert git_stash_snapshot("/tmp") == "abc123"

    @patch("impl.git.subprocess.run")
    def test_no_changes(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        assert git_stash_snapshot("/tmp") is None

    @patch("impl.git.subprocess.run")
    def test_store_failure_returns_none(self, mock_run, capsys):
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc123\n"),
            MagicMock(returncode=1, stderr="error storing"),
        ]
        assert git_stash_snapshot("/tmp") is None
        assert "WARNING" in capsys.readouterr().out


class TestGitRestoreSnapshot:
    @patch("impl.git.subprocess.run")
    @patch("impl.git._clean_working_tree")
    def test_success(self, mock_clean, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        assert git_restore_snapshot("abc123", "/tmp") is True
        mock_clean.assert_called_once()

    @patch("impl.git.subprocess.run")
    @patch("impl.git._clean_working_tree")
    def test_failure(self, mock_clean, mock_run, capsys):
        mock_run.return_value = MagicMock(returncode=1, stderr="conflict")
        assert git_restore_snapshot("abc123", "/tmp") is False
        assert "WARNING" in capsys.readouterr().out

    @patch("impl.git.subprocess.run")
    @patch("impl.git._clean_working_tree")
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


class TestDetectBaseBranch:
    @patch("impl.git.subprocess.run")
    def test_open_pr_returns_pr_base(self, mock_run):
        pr_json = json.dumps({"state": "OPEN", "baseRefName": "develop"})
        mock_run.return_value = MagicMock(returncode=0, stdout=pr_json)
        assert _detect_base_branch("/tmp") == "origin/develop"

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


class TestGitCommitCheckpoint:
    @patch("impl.git.subprocess.run")
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

    @patch("impl.git.subprocess.run")
    def test_add_failure(self, mock_run, capsys):
        mock_run.return_value = MagicMock(returncode=1, stderr="add failed")
        progress = {
            "skill": "code-review",
            "iteration_history": [],
            "findings": [],
        }
        assert git_commit_checkpoint(progress, 1, "/tmp") is False
        assert "WARNING" in capsys.readouterr().out

    @patch("impl.git.subprocess.run")
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

    @patch("impl.git.subprocess.run")
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
