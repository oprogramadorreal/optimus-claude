import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from harness_common.constants import (
    COMMIT_COMMITTED,
    COMMIT_FAILED,
    COMMIT_NOTHING,
)
from harness_common.git import (
    _HARNESS_STATE_EXCLUDES,
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
    get_open_pr_data,
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

_REPO_ROOT = Path(__file__).resolve().parents[2]


def test_gitignore_mirrors_harness_state_excludes():
    """This repo's .gitignore must mirror the harness temp-file prefixes.

    commit_checkpoint's authoritative protection is the un-stage step (it does
    NOT depend on .gitignore — `/optimus:init` does not provision it in user
    repos). But keeping this repo's own .gitignore in sync is a dev convenience
    so harness runs here don't leave the patterns showing as untracked; pin it
    so a rename on one side without `_HARNESS_STATE_EXCLUDES` can't drift.
    """
    gitignore = (_REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    for pattern in _HARNESS_STATE_EXCLUDES:
        if pattern.startswith(".claude/."):
            assert pattern in gitignore, f"{pattern} missing from .gitignore"


@patch("harness_common.git._fetch_open_pr_data")
def test_get_open_pr_data_delegates(mock_fetch):
    mock_fetch.return_value = {"state": "OPEN"}
    assert get_open_pr_data("/tmp/project") == {"state": "OPEN"}
    mock_fetch.assert_called_once_with("/tmp/project")


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
    # without monkey-patching subprocess. The seam is keyed by git subcommand
    # (rather than positional) so the order/number of `git reset` un-stage calls
    # can change without re-tuning a brittle results list.

    def _make_run(self, *, add_rc=0, staged_rc=1, commit_result=None):
        """Build a fake subprocess.run keyed by git subcommand.

        ``staged_rc`` is the returncode of ``git diff --cached --quiet``
        (1 = something is staged, 0 = nothing staged). ``commit_result``, when
        given, is the MagicMock returned for ``git commit``; otherwise a clean
        success is synthesized.
        """
        calls = []

        def fake_run(cmd, **_kw):
            calls.append(cmd)
            if cmd[:2] == ["git", "add"]:
                return MagicMock(returncode=add_rc, stdout="", stderr="")
            if cmd[:4] == ["git", "diff", "--cached", "--quiet"]:
                return MagicMock(returncode=staged_rc, stdout="", stderr="")
            if cmd[:2] == ["git", "commit"]:
                return commit_result or MagicMock(returncode=0, stdout="", stderr="")
            # `git reset HEAD -- <pattern>` and anything else succeed quietly.
            return MagicMock(returncode=0, stdout="", stderr="")

        return fake_run, calls

    def test_commits_after_unstaging_progress_file(self, tmp_path):
        # Verifies the full dance: git add -A, then `git reset HEAD --` against
        # the progress file, its .bak sibling, and every harness scratch / state
        # pattern, then (something still staged) git commit. Un-staging the
        # scratch patterns is authoritative — it must not depend on .gitignore.
        run, calls = self._make_run(staged_rc=1)  # something staged → commit runs
        status = commit_checkpoint(
            "feat: x", tmp_path, ".claude/progress.json", _run=run
        )
        assert status == COMMIT_COMMITTED
        assert calls[0][:2] == ["git", "add"]
        reset_calls = [c for c in calls if c[:3] == ["git", "reset", "HEAD"]]
        reset_targets = [c[-1] for c in reset_calls]
        # The progress file and its .bak sibling are un-staged...
        assert ".claude/progress.json" in reset_targets
        assert ".claude/progress.json.bak" in reset_targets
        # ...along with every harness scratch / state pattern, so a checkpoint
        # commit never captures them regardless of the user .gitignore.
        for pattern in _HARNESS_STATE_EXCLUDES:
            assert pattern in reset_targets
        commit_calls = [c for c in calls if c[:2] == ["git", "commit"]]
        assert len(commit_calls) == 1
        assert "feat: x" in commit_calls[0]

    def test_nothing_staged_after_unstage_skips_commit(self, tmp_path):
        # The deterministic guard: after un-staging, `git diff --cached --quiet`
        # returns 0 (nothing staged), so the function reports a no-op success
        # WITHOUT attempting `git commit` — regardless of git's prose. This is
        # the no-fix-iteration path that previously misfired as commit-failed.
        run, calls = self._make_run(staged_rc=0)
        status = commit_checkpoint(
            "feat: x", tmp_path, ".claude/progress.json", _run=run
        )
        assert status == COMMIT_NOTHING
        assert not [c for c in calls if c[:2] == ["git", "commit"]]

    def test_nothing_added_phrasing_is_treated_as_nothing(self, tmp_path):
        # Defense-in-depth: if something is staged at check time but the commit
        # still reports nothing (e.g. a hook un-staged it in between), both the
        # legacy "nothing to commit" and the untracked-files "nothing added to
        # commit" phrasings map to a no-op success — never commit-failed.
        commit = MagicMock(
            returncode=1,
            stdout="nothing added to commit but untracked files present",
            stderr="",
        )
        run, _ = self._make_run(staged_rc=1, commit_result=commit)
        status = commit_checkpoint(
            "feat: x", tmp_path, ".claude/progress.json", _run=run
        )
        assert status == COMMIT_NOTHING

    def test_add_failure_returns_failed(self, tmp_path, capsys):
        run, _ = self._make_run(add_rc=1)
        status = commit_checkpoint(
            "feat: x", tmp_path, ".claude/progress.json", _run=run
        )
        assert status == COMMIT_FAILED
        assert "git add -A failed" in capsys.readouterr().out

    def test_commit_failure_returns_failed(self, tmp_path, capsys):
        # A genuine commit failure (e.g., pre-commit hook rejection) must
        # surface as COMMIT_FAILED so the orchestrator can switch to --no-commit.
        commit = MagicMock(returncode=1, stdout="", stderr="pre-commit hook failed")
        run, _ = self._make_run(staged_rc=1, commit_result=commit)
        status = commit_checkpoint(
            "feat: x", tmp_path, ".claude/progress.json", _run=run
        )
        assert status == COMMIT_FAILED
        assert "checkpoint commit failed" in capsys.readouterr().out


def _git(cwd, *args):
    """Run a git command in ``cwd``, raising on failure."""
    subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True, text=True, check=True
    )


def _head(cwd):
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(cwd), capture_output=True, text=True
    ).stdout.strip()


def test_no_fix_iteration_with_untracked_progress_is_nothing_to_commit(tmp_path):
    """Real-repo regression for the masked commit-checkpoint bug.

    In a user project whose .gitignore does NOT carry the harness patterns, a
    no-fix iteration leaves the progress file untracked. ``git add -A`` stages
    it, the un-stage drops it, and ``git commit`` would print "nothing added to
    commit but untracked files present". commit_checkpoint must report a no-op
    success (COMMIT_NOTHING) and leave HEAD untouched — never a commit failure
    that would durably disable checkpoints. A mocked test masked this; only a
    real git repo exercises the actual git phrasing.
    """
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "t@t.test")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "file.txt").write_text("hello\n", encoding="utf-8")
    _git(tmp_path, "add", "file.txt")
    _git(tmp_path, "commit", "-m", "base")
    head_before = _head(tmp_path)

    # Simulate a no-fix iteration: the only tree change is the untracked,
    # NON-gitignored progress file (this scratch repo has no .gitignore).
    progress = tmp_path / ".claude" / "code-review-deep-progress.json"
    progress.parent.mkdir()
    progress.write_text("{}", encoding="utf-8")

    status = commit_checkpoint(
        "chore: checkpoint", tmp_path, ".claude/code-review-deep-progress.json"
    )
    assert status == COMMIT_NOTHING
    assert _head(tmp_path) == head_before  # no checkpoint commit was created


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

    @patch("harness_common.git.subprocess.run")
    @patch("harness_common.git._clean_working_tree")
    def test_failure_prints_recovery_hint_and_keeps_stash(
        self, mock_clean, mock_run, capsys
    ):
        # On a failed `stash apply`, the snapshot must NOT be dropped and the
        # user must be told how to recover it manually (regression for the
        # restore-recovery hardening in commit fac1fec).
        mock_run.return_value = MagicMock(returncode=1, stderr="conflict")
        assert git_restore_snapshot("abc123", "/tmp") is False
        assert "git stash apply abc123" in capsys.readouterr().out
        # The failure path returns before listing/dropping, so the only
        # subprocess call was the `stash apply` itself — the stash survives.
        assert mock_run.call_count == 1
        assert mock_run.call_args.args[0] == ["git", "stash", "apply", "abc123"]


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

    @patch("harness_common.git.subprocess.run")
    def test_returns_none_when_gh_missing(self, mock_run):
        # gh not installed: subprocess.run raises FileNotFoundError, which the
        # except clause absorbs into None (graceful degradation — PR context is
        # simply not injected). Mirrors _verify_ref's covered failure branch.
        mock_run.side_effect = FileNotFoundError("gh not found")
        assert _fetch_open_pr_data("/tmp/project") is None

    @patch("harness_common.git.subprocess.run")
    def test_returns_none_on_malformed_json(self, mock_run):
        # gh exited 0 but emitted non-JSON (truncated / interleaved output):
        # json.loads raises ValueError, also absorbed into None.
        mock_run.return_value = MagicMock(returncode=0, stdout="not json{")
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

    @patch("harness_common.git._verify_ref", return_value=True)
    @patch("harness_common.git._fetch_open_pr_data")
    def test_provided_pr_info_skips_refetch(self, mock_fetch, _mock_verify):
        # CL1: threading pr_info (dict or None) must not trigger a re-fetch —
        # None means "fetched, no open PR", not "not provided".
        pr = {"baseRefName": "main", "state": "OPEN"}
        assert _base_from_open_pr("/tmp", pr) == "origin/main"
        assert _base_from_open_pr("/tmp", None) is None
        mock_fetch.assert_not_called()


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

    @patch("harness_common.git.subprocess.run")
    @patch("harness_common.git._detect_base_branch", return_value="origin/main")
    def test_diff_uses_utf8_encoding(self, _mock_base, mock_run):
        # Non-ASCII filenames would fail under Windows-default cp1252; the
        # encoding="utf-8" kwarg keeps branch-file discovery cross-platform
        # (regression for commit fac1fec, mirrors TestFetchOpenPrData).
        mock_run.return_value = MagicMock(returncode=0, stdout="src/café.py\n")
        files, _base = git_discover_branch_files("/tmp")
        assert files == ["src/café.py"]
        _args, kwargs = mock_run.call_args
        assert kwargs.get("encoding") == "utf-8"
        assert kwargs.get("errors") == "replace"


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
    def test_provided_none_skips_refetch(self, mock_fetch):
        # CL1: threading pr_info=None (no open PR) must not re-fetch.
        assert git_fetch_open_pr_description("/tmp", None) is None
        mock_fetch.assert_not_called()

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
