import json
import subprocess
from unittest.mock import MagicMock, patch

from harness_common.git import (
    _PR_BODY_TRUNCATE_LIMIT,
    _PR_TITLE_TRUNCATE_LIMIT,
    _base_from_default_branches,
    _base_from_open_pr,
    _base_from_symbolic_ref,
    _clean_working_tree,
    _detect_base_branch,
    _fetch_open_pr_data,
    _verify_ref,
    commit_checkpoint,
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
        mock_run.side_effect = [
            MagicMock(returncode=0),
            MagicMock(returncode=1, stderr="permission denied"),
        ]
        _clean_working_tree("/tmp/project")
        assert "WARNING" in capsys.readouterr().out

    @patch("harness_common.git.subprocess.run")
    def test_checkout_failure_prints_warning(self, mock_run, capsys):
        mock_run.side_effect = [
            MagicMock(returncode=1, stderr="error: checkout failed"),
            MagicMock(returncode=0),
        ]
        _clean_working_tree("/tmp/project")
        output = capsys.readouterr().out
        assert "WARNING" in output
        assert "git checkout" in output

    @patch("harness_common.git.subprocess.run")
    def test_clean_excludes_harness_state_files(self, mock_run):
        # Regression: orchestrator progress files / per-iteration temp files
        # must survive the restore-to-HEAD fallback path so the user can
        # --resume after a failed iteration.
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        _clean_working_tree("/tmp/project")
        clean_call = mock_run.call_args_list[1]
        clean_args = clean_call.args[0]
        # The clean command must carry -e patterns covering the progress file
        # families and per-iteration temp files.
        assert "-e" in clean_args
        # Each excluded pattern must appear as its own token (so a stale
        # `.json.done.json` typo cannot pass via substring match).
        excludes = [
            arg for arg, prev in zip(clean_args[1:], clean_args) if prev == "-e"
        ]
        assert ".claude/*-deep-progress.json" in excludes
        assert ".claude/*-deep-progress.json.bak" in excludes
        # The archived filename is `*-deep-progress.done.json` (Path.with_suffix
        # strips `.json` then appends `.done.json`); the pattern must match it.
        assert ".claude/*-deep-progress.done.json" in excludes
        assert ".claude/.deep-iteration-*" in excludes
        assert ".claude/.unit-test-deep-*" in excludes


class TestCommitCheckpoint:
    # commit_checkpoint takes a `_run` test seam, so we drive it directly
    # without monkey-patching subprocess.

    def _make_run(self, results):
        """Build a fake subprocess.run that returns results in order."""
        calls = []

        def fake_run(cmd, **_kw):
            calls.append(cmd)
            i = len(calls) - 1
            return results[min(i, len(results) - 1)]

        return fake_run, calls

    def test_commits_after_unstaging_progress_file(self, tmp_path):
        # Verifies the full dance: git add -A, then `git reset HEAD --`
        # against the progress file and its .bak sibling, then git commit.
        run, calls = self._make_run([MagicMock(returncode=0, stdout="", stderr="")] * 5)
        ok = commit_checkpoint("feat: x", tmp_path, ".claude/progress.json", _run=run)
        assert ok is True
        # 1 add + 2 reset HEAD (progress + bak) + 1 commit = 4 calls
        assert calls[0][:2] == ["git", "add"]
        reset_calls = [c for c in calls if c[:3] == ["git", "reset", "HEAD"]]
        assert len(reset_calls) == 2
        # The progress file and its .bak sibling are both un-staged.
        reset_targets = [c[-1] for c in reset_calls]
        assert ".claude/progress.json" in reset_targets
        assert ".claude/progress.json.bak" in reset_targets
        commit_calls = [c for c in calls if c[:2] == ["git", "commit"]]
        assert len(commit_calls) == 1
        assert "feat: x" in commit_calls[0]

    def test_nothing_to_commit_is_treated_as_success(self, tmp_path):
        # When the un-stage step removes every staged path, `git commit`
        # exits non-zero with "nothing to commit" in its output — this is
        # a no-op success, not a failure.
        run, _ = self._make_run(
            [
                MagicMock(returncode=0, stdout="", stderr=""),  # add
                MagicMock(returncode=0, stdout="", stderr=""),  # reset 1
                MagicMock(returncode=0, stdout="", stderr=""),  # reset 2
                MagicMock(
                    returncode=1,
                    stdout="nothing to commit, working tree clean",
                    stderr="",
                ),
            ]
        )
        ok = commit_checkpoint("feat: x", tmp_path, ".claude/progress.json", _run=run)
        assert ok is True

    def test_add_failure_returns_false(self, tmp_path, capsys):
        run, _ = self._make_run(
            [MagicMock(returncode=1, stdout="", stderr="permission denied")]
        )
        ok = commit_checkpoint("feat: x", tmp_path, ".claude/progress.json", _run=run)
        assert ok is False
        assert "git add -A failed" in capsys.readouterr().out

    def test_commit_failure_returns_false(self, tmp_path, capsys):
        # A genuine commit failure (e.g., pre-commit hook rejection) must
        # surface as False so the orchestrator can switch to --no-commit.
        run, _ = self._make_run(
            [
                MagicMock(returncode=0, stdout="", stderr=""),  # add
                MagicMock(returncode=0, stdout="", stderr=""),  # reset 1
                MagicMock(returncode=0, stdout="", stderr=""),  # reset 2
                MagicMock(returncode=1, stdout="", stderr="pre-commit hook failed"),
            ]
        )
        ok = commit_checkpoint("feat: x", tmp_path, ".claude/progress.json", _run=run)
        assert ok is False
        out = capsys.readouterr().out
        assert "checkpoint commit failed" in out


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
        mock_run.side_effect = [
            MagicMock(returncode=0),
            MagicMock(returncode=1),
        ]
        assert git_diff_has_changes("/tmp") is True

    @patch("harness_common.git.subprocess.run")
    def test_untracked_files(self, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=0),
            MagicMock(returncode=0),
            MagicMock(returncode=0, stdout="new_file.txt\n"),
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

    @patch("harness_common.git.git_restore_to")
    def test_no_stash_no_head_returns_false(self, mock_restore_to, capsys):
        # Regression for c53086d: when both inputs are None, restore_working_tree
        # warns and returns False rather than raising on the missing fallback.
        result = restore_working_tree(None, None, "/tmp")
        assert result is False
        mock_restore_to.assert_not_called()
        assert "no snapshot to restore from" in capsys.readouterr().out


class TestGitStashSnapshot:
    @patch("harness_common.git.subprocess.run")
    def test_success(self, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc123\n"),
            MagicMock(returncode=0),
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
            MagicMock(returncode=0),
            MagicMock(returncode=0, stdout="stash@{0} abc123\nstash@{1} def456\n"),
            MagicMock(returncode=0),
        ]
        assert git_restore_snapshot("abc123", "/tmp") is True
        drop_call = mock_run.call_args_list[2]
        assert drop_call[0][0] == ["git", "stash", "drop", "stash@{0}"]


class TestFetchOpenPrData:
    @patch("harness_common.git.subprocess.run")
    def test_decodes_non_latin1_body(self, mock_run):
        # Em-dash and accented chars would fail under Windows-default cp1252;
        # the encoding="utf-8" kwarg is what makes this work cross-platform.
        body = "Implements — feature: rotación de tokens"
        pr_json = json.dumps(
            {
                "title": "feat",
                "body": body,
                "baseRefName": "main",
                "state": "OPEN",
            }
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=pr_json)
        result = _fetch_open_pr_data("/tmp/project")
        assert result is not None
        assert result["body"] == body
        # Regression guard for commit 9e0553a — without these kwargs, Windows
        # would re-default to cp1252 and silently drop non-Latin-1 PR bodies.
        _args, kwargs = mock_run.call_args
        assert kwargs.get("encoding") == "utf-8"
        assert kwargs.get("errors") == "replace"

    @patch("harness_common.git.subprocess.run")
    def test_returns_none_when_pr_not_open(self, mock_run):
        pr_json = json.dumps(
            {
                "title": "feat",
                "body": "x",
                "baseRefName": "main",
                "state": "CLOSED",
            }
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=pr_json)
        assert _fetch_open_pr_data("/tmp/project") is None

    @patch("harness_common.git.subprocess.run")
    def test_returns_none_on_gh_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        assert _fetch_open_pr_data("/tmp/project") is None


class TestVerifyRef:
    @patch("harness_common.git.subprocess.run")
    def test_returns_true_on_zero_exit(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        assert _verify_ref("/tmp", "origin/main") is True

    @patch("harness_common.git.subprocess.run")
    def test_returns_false_on_non_zero_exit(self, mock_run):
        mock_run.return_value = MagicMock(returncode=128)
        assert _verify_ref("/tmp", "origin/nope") is False

    @patch("harness_common.git.subprocess.run")
    def test_returns_false_on_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="git", timeout=10)
        assert _verify_ref("/tmp", "origin/main") is False

    @patch("harness_common.git.subprocess.run")
    def test_returns_false_when_git_missing(self, mock_run):
        mock_run.side_effect = FileNotFoundError("git not on PATH")
        assert _verify_ref("/tmp", "origin/main") is False


class TestBaseFromOpenPr:
    @patch("harness_common.git._verify_ref", return_value=True)
    @patch("harness_common.git._fetch_open_pr_data")
    def test_returns_origin_prefixed_base(self, mock_fetch, _mock_verify):
        mock_fetch.return_value = {
            "title": "x",
            "body": "y",
            "baseRefName": "main",
            "state": "OPEN",
        }
        assert _base_from_open_pr("/tmp") == "origin/main"

    @patch("harness_common.git._fetch_open_pr_data", return_value=None)
    def test_returns_none_when_no_pr(self, _mock_fetch):
        assert _base_from_open_pr("/tmp") is None

    @patch("harness_common.git._verify_ref", return_value=False)
    @patch("harness_common.git._fetch_open_pr_data")
    def test_returns_none_when_local_ref_missing(self, mock_fetch, _mock_verify):
        # Open PR exists upstream, but the user has not fetched its base —
        # so the local `origin/<base>` ref doesn't resolve. Fall through.
        mock_fetch.return_value = {
            "title": "x",
            "body": "y",
            "baseRefName": "feature/upstream-base-not-fetched",
            "state": "OPEN",
        }
        assert _base_from_open_pr("/tmp") is None

    @patch("harness_common.git._fetch_open_pr_data")
    def test_returns_none_when_baseref_missing(self, mock_fetch):
        mock_fetch.return_value = {"title": "x", "body": "y", "state": "OPEN"}
        assert _base_from_open_pr("/tmp") is None


class TestBaseFromSymbolicRef:
    @patch("harness_common.git.subprocess.run")
    def test_strips_refs_remotes_prefix(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="refs/remotes/origin/main\n"
        )
        assert _base_from_symbolic_ref("/tmp") == "origin/main"

    @patch("harness_common.git.subprocess.run")
    def test_returns_none_when_unexpected_prefix(self, mock_run):
        # Should only honour refs/remotes/* output. Anything else is treated
        # as a malformed result and we fall through.
        mock_run.return_value = MagicMock(returncode=0, stdout="refs/heads/main\n")
        assert _base_from_symbolic_ref("/tmp") is None

    @patch("harness_common.git.subprocess.run")
    def test_returns_none_on_non_zero_exit(self, mock_run):
        mock_run.return_value = MagicMock(returncode=128, stdout="")
        assert _base_from_symbolic_ref("/tmp") is None

    @patch("harness_common.git.subprocess.run")
    def test_returns_none_on_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="git", timeout=10)
        assert _base_from_symbolic_ref("/tmp") is None


class TestBaseFromDefaultBranches:
    @patch("harness_common.git._verify_ref")
    def test_prefers_main_when_both_exist(self, mock_verify):
        # When both `origin/main` and `origin/master` are present, main wins
        # — first match in the iteration order.
        mock_verify.side_effect = lambda _cwd, ref: ref in (
            "origin/main",
            "origin/master",
        )
        assert _base_from_default_branches("/tmp") == "origin/main"

    @patch("harness_common.git._verify_ref")
    def test_falls_back_to_master(self, mock_verify):
        mock_verify.side_effect = lambda _cwd, ref: ref == "origin/master"
        assert _base_from_default_branches("/tmp") == "origin/master"

    @patch("harness_common.git._verify_ref", return_value=False)
    def test_returns_none_when_neither_exists(self, _mock_verify):
        assert _base_from_default_branches("/tmp") is None


class TestDetectBaseBranch:
    @patch("harness_common.git._base_from_default_branches")
    @patch("harness_common.git._base_from_symbolic_ref")
    @patch("harness_common.git._base_from_open_pr")
    def test_open_pr_wins_first(self, mock_open_pr, mock_symbolic, mock_default):
        mock_open_pr.return_value = "origin/feature-base"
        assert _detect_base_branch("/tmp") == "origin/feature-base"
        mock_symbolic.assert_not_called()
        mock_default.assert_not_called()

    @patch("harness_common.git._base_from_default_branches")
    @patch("harness_common.git._base_from_symbolic_ref")
    @patch("harness_common.git._base_from_open_pr", return_value=None)
    def test_symbolic_ref_wins_second(self, _mock_open_pr, mock_symbolic, mock_default):
        mock_symbolic.return_value = "origin/develop"
        assert _detect_base_branch("/tmp") == "origin/develop"
        mock_default.assert_not_called()

    @patch("harness_common.git._base_from_default_branches")
    @patch("harness_common.git._base_from_symbolic_ref", return_value=None)
    @patch("harness_common.git._base_from_open_pr", return_value=None)
    def test_default_branches_third(self, _mock_open_pr, _mock_symbolic, mock_default):
        mock_default.return_value = "origin/master"
        assert _detect_base_branch("/tmp") == "origin/master"

    @patch("harness_common.git._base_from_default_branches", return_value=None)
    @patch("harness_common.git._base_from_symbolic_ref", return_value=None)
    @patch("harness_common.git._base_from_open_pr", return_value=None)
    def test_returns_none_when_all_fail(self, *_mocks):
        assert _detect_base_branch("/tmp") is None


class TestGitDiscoverBranchFiles:
    @patch("harness_common.git.subprocess.run")
    @patch("harness_common.git._detect_base_branch", return_value="origin/main")
    def test_returns_files_and_base(self, _mock_base, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="src/a.py\nsrc/b.py\n")
        files, base = git_discover_branch_files("/tmp")
        assert files == ["src/a.py", "src/b.py"]
        assert base == "origin/main"
        # Diff uses three-dot to compare branch vs merge-base.
        args = mock_run.call_args.args[0]
        assert args[:3] == ["git", "diff", "--name-only"]
        assert "origin/main...HEAD" in args

    @patch("harness_common.git.subprocess.run")
    @patch("harness_common.git._detect_base_branch", return_value="origin/main")
    def test_path_filter_injects_pathspec(self, _mock_base, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="src/auth/login.py\n")
        files, base = git_discover_branch_files("/tmp", path_filter="src/auth")
        assert files == ["src/auth/login.py"]
        assert base == "origin/main"
        args = mock_run.call_args.args[0]
        # The `--` separator comes after the diff spec so git treats the
        # next token as a pathspec, never as a ref.
        assert "--" in args
        sep_idx = args.index("--")
        assert args[sep_idx + 1] == "src/auth"

    @patch("harness_common.git.subprocess.run")
    @patch("harness_common.git._detect_base_branch", return_value=None)
    def test_returns_empty_and_none_when_no_base_detected(self, _mock_base, mock_run):
        assert git_discover_branch_files("/tmp") == ([], None)
        # We must NOT have run git diff when no base could be detected.
        mock_run.assert_not_called()

    @patch("harness_common.git.subprocess.run")
    @patch("harness_common.git._detect_base_branch", return_value="origin/main")
    def test_empty_diff_returns_empty_list(self, _mock_base, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="\n")
        files, base = git_discover_branch_files("/tmp")
        assert files == []
        assert base == "origin/main"

    @patch("harness_common.git.subprocess.run")
    @patch("harness_common.git._detect_base_branch", return_value="origin/main")
    def test_diff_failure_returns_empty(self, _mock_base, mock_run):
        mock_run.return_value = MagicMock(returncode=128, stdout="")
        files, base = git_discover_branch_files("/tmp")
        assert files == []
        # Base is preserved so the caller can still report which base we tried.
        assert base == "origin/main"

    @patch("harness_common.git.subprocess.run")
    @patch("harness_common.git._detect_base_branch", return_value="origin/main")
    def test_timeout_returns_empty(self, _mock_base, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="git", timeout=30)
        files, base = git_discover_branch_files("/tmp")
        assert files == []
        assert base == "origin/main"


class TestGitFetchOpenPrDescription:
    @patch("harness_common.git._fetch_open_pr_data")
    def test_returns_truncated_payload(self, mock_fetch):
        mock_fetch.return_value = {
            "title": "feat: x",
            "body": "Implements x",
            "baseRefName": "develop",
            "state": "OPEN",
        }
        out = git_fetch_open_pr_description("/tmp")
        assert out == {
            "title": "feat: x",
            "body": "Implements x",
            "base_ref": "origin/develop",
        }

    @patch("harness_common.git._fetch_open_pr_data", return_value=None)
    def test_returns_none_when_no_pr(self, _mock_fetch):
        assert git_fetch_open_pr_description("/tmp") is None

    @patch("harness_common.git._fetch_open_pr_data")
    def test_title_truncated_at_limit(self, mock_fetch):
        long_title = "x" * (_PR_TITLE_TRUNCATE_LIMIT + 50)
        mock_fetch.return_value = {
            "title": long_title,
            "body": "",
            "baseRefName": "main",
            "state": "OPEN",
        }
        out = git_fetch_open_pr_description("/tmp")
        assert len(out["title"]) == _PR_TITLE_TRUNCATE_LIMIT

    @patch("harness_common.git._fetch_open_pr_data")
    def test_title_at_exactly_limit_not_truncated(self, mock_fetch):
        title = "x" * _PR_TITLE_TRUNCATE_LIMIT
        mock_fetch.return_value = {
            "title": title,
            "body": "",
            "baseRefName": "main",
            "state": "OPEN",
        }
        out = git_fetch_open_pr_description("/tmp")
        assert out["title"] == title

    @patch("harness_common.git._fetch_open_pr_data")
    def test_body_truncated_at_limit_with_marker(self, mock_fetch):
        body = "y" * (_PR_BODY_TRUNCATE_LIMIT + 100)
        mock_fetch.return_value = {
            "title": "x",
            "body": body,
            "baseRefName": "main",
            "state": "OPEN",
        }
        out = git_fetch_open_pr_description("/tmp")
        # Original body is sliced to the limit, then a marker is appended.
        assert out["body"].startswith("y" * _PR_BODY_TRUNCATE_LIMIT)
        assert out["body"].endswith("[...truncated...]")

    @patch("harness_common.git._fetch_open_pr_data")
    def test_body_at_exactly_limit_not_truncated(self, mock_fetch):
        body = "y" * _PR_BODY_TRUNCATE_LIMIT
        mock_fetch.return_value = {
            "title": "x",
            "body": body,
            "baseRefName": "main",
            "state": "OPEN",
        }
        out = git_fetch_open_pr_description("/tmp")
        assert out["body"] == body
        assert "[...truncated...]" not in out["body"]

    @patch("harness_common.git._fetch_open_pr_data")
    def test_base_ref_none_when_baseref_absent(self, mock_fetch):
        mock_fetch.return_value = {
            "title": "x",
            "body": "y",
            "baseRefName": None,
            "state": "OPEN",
        }
        out = git_fetch_open_pr_description("/tmp")
        assert out["base_ref"] is None

    @patch("harness_common.git._fetch_open_pr_data")
    def test_missing_title_and_body_default_to_empty(self, mock_fetch):
        mock_fetch.return_value = {"baseRefName": "main", "state": "OPEN"}
        out = git_fetch_open_pr_description("/tmp")
        assert out["title"] == ""
        assert out["body"] == ""
        assert out["base_ref"] == "origin/main"
