from pathlib import Path
from unittest.mock import patch

import pytest
from harness_common.fixes import (
    _is_path_within,
    _swap_content,
    apply_single_fix,
    bisect_fixes,
)


class TestIsPathWithin:
    def test_inside(self, tmp_path):
        child = tmp_path / "src" / "app.js"
        assert _is_path_within(child, tmp_path) is True

    def test_outside(self, tmp_path):
        outside = Path("/some/other/path")
        assert _is_path_within(outside, tmp_path) is False

    def test_same_path(self, tmp_path):
        assert _is_path_within(tmp_path, tmp_path) is True


class TestSwapContent:
    def test_basic_swap(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello world", encoding="utf-8")
        fix = {
            "file": "test.txt",
            "pre_edit_content": "hello",
            "post_edit_content": "goodbye",
        }
        result = _swap_content(
            fix, str(tmp_path), "pre_edit_content", "post_edit_content"
        )
        assert result is True
        assert f.read_text(encoding="utf-8") == "goodbye world"

    def test_file_not_found(self, tmp_path):
        fix = {"file": "missing.txt", "pre_edit_content": "x", "post_edit_content": "y"}
        assert (
            _swap_content(fix, str(tmp_path), "pre_edit_content", "post_edit_content")
            is False
        )

    def test_non_string_content_is_refused(self, tmp_path):
        # A non-string edit field (e.g. a JSON number that slipped past the
        # dispatch contract) must be refused, not crash the membership test /
        # str.replace.
        f = tmp_path / "test.txt"
        f.write_text("hello world", encoding="utf-8")
        fix = {"file": "test.txt", "pre_edit_content": 5, "post_edit_content": "x"}
        assert (
            _swap_content(fix, str(tmp_path), "pre_edit_content", "post_edit_content")
            is False
        )
        assert f.read_text(encoding="utf-8") == "hello world"

    def test_content_not_found(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello", encoding="utf-8")
        fix = {
            "file": "test.txt",
            "pre_edit_content": "missing",
            "post_edit_content": "y",
        }
        assert (
            _swap_content(fix, str(tmp_path), "pre_edit_content", "post_edit_content")
            is False
        )

    def test_ambiguous_match(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("aaa bbb aaa", encoding="utf-8")
        fix = {
            "file": "test.txt",
            "pre_edit_content": "aaa",
            "post_edit_content": "ccc",
        }
        assert (
            _swap_content(fix, str(tmp_path), "pre_edit_content", "post_edit_content")
            is False
        )

    def test_empty_source_field(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("content", encoding="utf-8")
        fix = {"file": "test.txt", "pre_edit_content": "", "post_edit_content": "new"}
        assert (
            _swap_content(fix, str(tmp_path), "pre_edit_content", "post_edit_content")
            is False
        )

    def test_path_traversal_blocked(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello", encoding="utf-8")
        fix = {
            "file": "../../../etc/passwd",
            "pre_edit_content": "hello",
            "post_edit_content": "hacked",
        }
        assert (
            _swap_content(fix, str(tmp_path), "pre_edit_content", "post_edit_content")
            is False
        )

    def test_git_directory_blocked(self, tmp_path):
        git_dir = tmp_path / ".git" / "config"
        git_dir.parent.mkdir()
        git_dir.write_text("content", encoding="utf-8")
        fix = {
            "file": ".git/config",
            "pre_edit_content": "content",
            "post_edit_content": "hacked",
        }
        assert (
            _swap_content(fix, str(tmp_path), "pre_edit_content", "post_edit_content")
            is False
        )

    def test_binary_file(self, tmp_path):
        f = tmp_path / "image.bin"
        f.write_bytes(b"\x80\x81\x82\xff\xfe")
        fix = {
            "file": "image.bin",
            "pre_edit_content": "x",
            "post_edit_content": "y",
        }
        assert (
            _swap_content(fix, str(tmp_path), "pre_edit_content", "post_edit_content")
            is False
        )

    def test_backslash_path_normalized(self, tmp_path):
        f = tmp_path / "src" / "app.js"
        f.parent.mkdir()
        f.write_text("old code", encoding="utf-8")
        fix = {
            "file": "src\\app.js",
            "pre_edit_content": "old code",
            "post_edit_content": "new code",
        }
        result = _swap_content(
            fix, str(tmp_path), "pre_edit_content", "post_edit_content"
        )
        assert result is True
        assert f.read_text(encoding="utf-8") == "new code"

    def test_deletion_fix(self, tmp_path):
        """Empty post_edit_content means deletion — should succeed."""
        f = tmp_path / "test.txt"
        f.write_text("keep this remove_me and this", encoding="utf-8")
        fix = {
            "file": "test.txt",
            "pre_edit_content": "remove_me ",
            "post_edit_content": "",
        }
        result = _swap_content(
            fix, str(tmp_path), "pre_edit_content", "post_edit_content"
        )
        assert result is True
        assert f.read_text(encoding="utf-8") == "keep this and this"


class TestApplySingleFix:
    def test_applies_pre_to_post(self, tmp_path):
        f = tmp_path / "src.js"
        f.write_text("obj.value", encoding="utf-8")
        fix = {
            "file": "src.js",
            "pre_edit_content": "obj.value",
            "post_edit_content": "obj?.value",
        }
        assert apply_single_fix(fix, str(tmp_path)) is True
        assert f.read_text(encoding="utf-8") == "obj?.value"


class TestBisectCleanResetIsDefault:
    """With a repeatable reset hook, bisection always rebuilds from the git
    snapshot — recorded content is never trusted as revert data. Regression
    for a field incident where truncated pre/post_edit_content records tore a
    coupled edit in half during the legacy revert-all phase."""

    def test_clean_reset_used_without_deletion_fixes(self, tmp_path):
        f = tmp_path / "a.py"
        resets = {"n": 0}

        def reset_to_clean():
            resets["n"] += 1
            f.write_text("PRE", encoding="utf-8")

        reset_to_clean()
        fix = {"file": "a.py", "pre_edit_content": "PRE", "post_edit_content": "POST"}
        apply_single_fix(fix, str(tmp_path))
        fixed, reverted, skipped = bisect_fixes(
            [fix],
            "test",
            str(tmp_path),
            run_tests_fn=lambda _c, _w: (True, "ok"),
            reset_to_clean=reset_to_clean,
        )
        assert (fixed, reverted, skipped) == (1, 0, 0)
        assert resets["n"] > 1  # rebuilt from clean → clean-reset strategy ran
        assert f.read_text(encoding="utf-8") == "POST"

    def test_truncated_record_cannot_tear_file(self, tmp_path):
        # The subagent really edited line2+line3, but the recorded pair was
        # truncated mid-edit when saved. A content-swap revert of the truncated
        # pair would produce a chimera file (neither pre nor post — the torn
        # state from the field incident). With the snapshot rebuild, the
        # truncated record can only fail its isolation test, and the tree ends
        # at a git-true state.
        f = tmp_path / "a.py"
        clean = "line1\nline2\nline3\n"

        def reset_to_clean():
            f.write_text(clean, encoding="utf-8")

        # Working tree as the subagent actually left it.
        f.write_text("line1\nEDITED2\nEDITED3\n", encoding="utf-8")
        truncated = {
            "file": "a.py",
            "pre_edit_content": "line1\nline2\n",
            "post_edit_content": "line1\nEDITED2\n",
        }
        fixed, reverted, skipped = bisect_fixes(
            [truncated],
            "test",
            str(tmp_path),
            run_tests_fn=lambda _c, _w: (False, "boom"),
            reset_to_clean=reset_to_clean,
        )
        assert (fixed, reverted, skipped) == (0, 1, 0)
        assert f.read_text(encoding="utf-8") == clean  # never torn

    def test_skipped_apply_is_loud(self, tmp_path, capsys):
        f = tmp_path / "a.py"

        def reset_to_clean():
            f.write_text("CLEAN", encoding="utf-8")

        reset_to_clean()
        # Record whose pre content doesn't exist in the clean file at all
        # (e.g. abbreviated with an ellipsis when saved).
        corrupt = {
            "file": "a.py",
            "pre_edit_content": "def foo(): ...",
            "post_edit_content": "def foo(): return 1",
        }
        details = {}

        def on_outcome(idx, _fix, outcome, detail):
            details[idx] = (outcome, detail)

        fixed, reverted, skipped = bisect_fixes(
            [corrupt],
            "test",
            str(tmp_path),
            run_tests_fn=lambda _c, _w: (True, "ok"),
            on_outcome=on_outcome,
            reset_to_clean=reset_to_clean,
        )
        assert (fixed, reverted, skipped) == (0, 0, 1)
        outcome, detail = details[0]
        assert outcome == "skipped"
        assert "verbatim" in detail
        assert "WARNING" in capsys.readouterr().out

    def test_no_retry_replay_when_nothing_kept(self, tmp_path):
        # All candidates rejected on the first pass and no keepers: a retry
        # would replay the identical first pass, so it must be skipped.
        a = tmp_path / "a.py"
        b = tmp_path / "b.py"

        def reset_to_clean():
            a.write_text("A_PRE", encoding="utf-8")
            b.write_text("B_PRE", encoding="utf-8")

        reset_to_clean()
        fixes = [
            {
                "file": "a.py",
                "pre_edit_content": "A_PRE",
                "post_edit_content": "A_POST",
            },
            {
                "file": "b.py",
                "pre_edit_content": "B_PRE",
                "post_edit_content": "B_POST",
            },
        ]
        for fix in fixes:
            apply_single_fix(fix, str(tmp_path))
        runs = []

        def failing_run_tests(_c, _w):
            runs.append(True)
            return False, "boom"

        fixed, reverted, skipped = bisect_fixes(
            fixes,
            "test",
            str(tmp_path),
            run_tests_fn=failing_run_tests,
            reset_to_clean=reset_to_clean,
        )
        assert (fixed, reverted, skipped) == (0, 2, 0)
        assert len(runs) == 2  # one per fix — no wasted replay

    def test_default_run_tests_fn(self, tmp_path):
        """When run_tests_fn is None, falls back to harness_common.runner.run_tests."""
        f = tmp_path / "a.txt"

        def reset_to_clean():
            f.write_text("old_a", encoding="utf-8")

        reset_to_clean()
        fix = {
            "file": "a.txt",
            "pre_edit_content": "old_a",
            "post_edit_content": "new_a",
        }
        apply_single_fix(fix, str(tmp_path))
        with patch(
            "harness_common.runner.run_tests", return_value=(True, "ok")
        ) as mock_rt:
            fixed, reverted, skipped = bisect_fixes(
                [fix], "test", str(tmp_path), reset_to_clean=reset_to_clean
            )
        assert (fixed, reverted, skipped) == (1, 0, 0)
        mock_rt.assert_called_once_with("test", str(tmp_path))

    def test_missing_reset_to_clean_raises(self, tmp_path):
        """Without a reset hook there is no trusted revert base — bisect_fixes
        must fail loudly rather than bisect against an unknown state."""
        fix = {
            "file": "a.txt",
            "pre_edit_content": "old",
            "post_edit_content": "new",
        }
        with pytest.raises(ValueError, match="reset_to_clean"):
            bisect_fixes(
                [fix],
                "test",
                str(tmp_path),
                run_tests_fn=lambda _c, _w: (True, "ok"),
                reset_to_clean=None,
            )


class TestBisectCleanReset:
    """bisect_fixes rebuilds from the reset_to_clean hook, which isolates
    deletion fixes that a content-swap revert could never un-apply."""

    def test_clean_reset_isolates_harmful_deletion(self, tmp_path):
        del_file = tmp_path / "del.py"
        good_file = tmp_path / "good.py"

        def reset_to_clean():
            del_file.write_text("DELETE_ME\n", encoding="utf-8")
            good_file.write_text("GOOD_PRE\n", encoding="utf-8")

        reset_to_clean()
        deletion = {
            "file": "del.py",
            "category": "dead-code",
            "line": 1,
            "pre_edit_content": "DELETE_ME\n",
            "post_edit_content": "",
        }
        good = {
            "file": "good.py",
            "category": "fix",
            "line": 1,
            "pre_edit_content": "GOOD_PRE",
            "post_edit_content": "GOOD_POST",
        }
        # Simulate the subagent applying both fixes before bisection.
        apply_single_fix(deletion, str(tmp_path))
        apply_single_fix(good, str(tmp_path))

        def fake_run_tests(_cmd, _cwd):
            # The deletion is harmful: tests fail whenever DELETE_ME is gone.
            ok = "DELETE_ME" in del_file.read_text(encoding="utf-8")
            return ok, "" if ok else "boom"

        outcomes = {}

        def on_outcome(_idx, fix, outcome, _detail):
            outcomes[fix["file"]] = outcome

        fixed, reverted, skipped = bisect_fixes(
            [deletion, good],
            "test",
            str(tmp_path),
            run_tests_fn=fake_run_tests,
            on_outcome=on_outcome,
            reset_to_clean=reset_to_clean,
        )

        # The harmful deletion is correctly reverted, and the good co-fix
        # survives instead of being lost to a full rollback.
        assert outcomes["del.py"] == "reverted"
        assert outcomes["good.py"] == "fixed"
        assert (fixed, reverted, skipped) == (1, 1, 0)
        assert "DELETE_ME" in del_file.read_text(encoding="utf-8")
        assert "GOOD_POST" in good_file.read_text(encoding="utf-8")

    def test_clean_reset_first_pass_apply_failure_skipped(self, tmp_path):
        # A fix that fails to apply on the clean-reset first pass is counted as
        # skipped. A deletion fix routes the set through clean-reset.
        deletion = {
            "file": "del.py",
            "category": "dead-code",
            "line": 1,
            "pre_edit_content": "DELETE_ME\n",
            "post_edit_content": "",
        }

        def reset_to_clean():
            (tmp_path / "del.py").write_text("DELETE_ME\n", encoding="utf-8")

        reset_to_clean()
        outcomes = {}

        def on_outcome(_idx, fix, outcome, _detail):
            outcomes[fix["file"]] = outcome

        with patch("harness_common.fixes.apply_single_fix", return_value=False):
            fixed, reverted, skipped = bisect_fixes(
                [deletion],
                "test",
                str(tmp_path),
                run_tests_fn=lambda _c, _w: (True, "ok"),
                on_outcome=on_outcome,
                reset_to_clean=reset_to_clean,
            )
        assert outcomes["del.py"] == "skipped"
        assert (fixed, reverted, skipped) == (0, 0, 1)

    def test_clean_reset_second_pass_recovers_order_dependent_fix(self, tmp_path):
        # In clean-reset mode, a fix that fails the first pass because of ordering
        # must still recover on the retry pass (run with all first-pass keepers
        # applied). Covers the clean-reset retry-recovery branch.
        a = tmp_path / "a.py"
        b = tmp_path / "b.py"
        d = tmp_path / "del.py"

        def reset_to_clean():
            a.write_text("A_PRE", encoding="utf-8")
            b.write_text("B_PRE", encoding="utf-8")
            d.write_text("DEL\n", encoding="utf-8")

        reset_to_clean()
        a_fix = {
            "file": "a.py",
            "category": "fix",
            "line": 1,
            "pre_edit_content": "A_PRE",
            "post_edit_content": "A_POST",
        }
        b_fix = {
            "file": "b.py",
            "category": "fix",
            "line": 1,
            "pre_edit_content": "B_PRE",
            "post_edit_content": "B_POST",
        }
        deletion = {
            "file": "del.py",
            "category": "dead-code",
            "line": 1,
            "pre_edit_content": "DEL\n",
            "post_edit_content": "",
        }
        # a is ordered before b, so a fails the first pass (b not yet applied)
        # and recovers on retry once b is a keeper.
        for fix in (a_fix, b_fix, deletion):
            apply_single_fix(fix, str(tmp_path))

        def fake_run_tests(_cmd, _cwd):
            a_post = a.read_text(encoding="utf-8") == "A_POST"
            b_post = b.read_text(encoding="utf-8") == "B_POST"
            ok = (not a_post) or (a_post and b_post)
            return ok, "" if ok else "a needs b"

        outcomes = {}
        details = {}

        def on_outcome(_idx, fix, outcome, detail):
            outcomes[fix["file"]] = outcome
            details[fix["file"]] = detail

        fixed, reverted, skipped = bisect_fixes(
            [a_fix, b_fix, deletion],
            "test",
            str(tmp_path),
            run_tests_fn=fake_run_tests,
            on_outcome=on_outcome,
            reset_to_clean=reset_to_clean,
        )
        assert outcomes == {"a.py": "fixed", "b.py": "fixed", "del.py": "fixed"}
        assert details["a.py"] == "Passed on retry (dependency resolved)"
        assert (fixed, reverted, skipped) == (3, 0, 0)

    def test_clean_reset_retry_apply_failure_skipped(self, tmp_path):
        # A fix rejected on the first pass that then cannot re-apply on the retry
        # pass (a keeper rewrote its anchor) is counted as skipped. Covers the
        # clean-reset retry-pass apply-failure branch.
        f = tmp_path / "f.py"
        d = tmp_path / "del.py"

        def reset_to_clean():
            f.write_text("MARKER\n", encoding="utf-8")
            d.write_text("DEL\n", encoding="utf-8")

        reset_to_clean()
        # x targets MARKER and breaks tests; keeper also rewrites MARKER, so on
        # x's retry the anchor is gone and the re-apply fails.
        x = {
            "file": "f.py",
            "category": "fix",
            "line": 1,
            "pre_edit_content": "MARKER\n",
            "post_edit_content": "X_DONE\n",
        }
        keeper = {
            "file": "f.py",
            "category": "fix",
            "line": 1,
            "pre_edit_content": "MARKER\n",
            "post_edit_content": "KEPT\n",
        }
        deletion = {
            "file": "del.py",
            "category": "dead-code",
            "line": 1,
            "pre_edit_content": "DEL\n",
            "post_edit_content": "",
        }

        def fake_run_tests(_cmd, _cwd):
            ok = "X_DONE" not in f.read_text(encoding="utf-8")
            return ok, "" if ok else "x broke it"

        outcomes = {}

        def on_outcome(idx, _fix, outcome, _detail):
            outcomes[idx] = outcome

        fixed, reverted, skipped = bisect_fixes(
            [x, keeper, deletion],
            "test",
            str(tmp_path),
            run_tests_fn=fake_run_tests,
            on_outcome=on_outcome,
            reset_to_clean=reset_to_clean,
        )
        assert outcomes[0] == "skipped"
        assert skipped == 1

    def test_clean_reset_raise_on_first_pass_does_not_crash(self, tmp_path):
        # reset_to_clean is restore_working_tree → git_restore_to, which raises
        # RuntimeError when its `git checkout` fails. The clean-reset bisect must
        # abort gracefully (undecided fixes reported skipped) rather than let the
        # exception propagate out and crash the deep-step / refactor-step.
        deletion = {
            "file": "del.py",
            "category": "dead-code",
            "line": 1,
            "pre_edit_content": "DELETE_ME\n",
            "post_edit_content": "",
        }

        def reset_to_clean():
            raise RuntimeError("git checkout HEAD -- . failed: index.lock")

        ran_tests = []

        def fake_run_tests(_cmd, _cwd):
            ran_tests.append(True)
            return True, "ok"

        outcomes = {}

        def on_outcome(idx, _fix, outcome, _detail):
            outcomes[idx] = outcome

        # Must not raise.
        fixed, reverted, skipped = bisect_fixes(
            [deletion],
            "test",
            str(tmp_path),
            run_tests_fn=fake_run_tests,
            on_outcome=on_outcome,
            reset_to_clean=reset_to_clean,
        )
        assert (fixed, reverted, skipped) == (0, 0, 1)
        assert outcomes[0] == "skipped"
        # Never tested a candidate on a base we failed to clean.
        assert ran_tests == []

    def test_clean_reset_raise_mid_bisect_preserves_decided_and_skips_rest(
        self, tmp_path
    ):
        # reset succeeds for the first candidate, then raises before the second.
        # The decided fix keeps its outcome; the undecided one is reported
        # skipped (via the emit loop's `.get` default) — no crash, no KeyError.
        a_file = tmp_path / "a.py"
        calls = {"n": 0}

        def reset_to_clean():
            calls["n"] += 1
            if calls["n"] == 2:
                raise RuntimeError("git checkout failed mid-bisect")
            a_file.write_text("A_PRE", encoding="utf-8")

        a_fix = {
            "file": "a.py",
            "category": "fix",
            "line": 1,
            "pre_edit_content": "A_PRE",
            "post_edit_content": "A_POST",
        }
        deletion = {
            "file": "del.py",
            "category": "dead-code",
            "line": 1,
            "pre_edit_content": "DEL\n",
            "post_edit_content": "",
        }

        outcomes = {}

        def on_outcome(idx, _fix, outcome, _detail):
            outcomes[idx] = outcome

        fixed, reverted, skipped = bisect_fixes(
            [a_fix, deletion],
            "test",
            str(tmp_path),
            run_tests_fn=lambda _c, _w: (True, "ok"),
            on_outcome=on_outcome,
            reset_to_clean=reset_to_clean,
        )
        assert outcomes[0] == "fixed"
        assert outcomes[1] == "skipped"
        assert (fixed, reverted, skipped) == (1, 0, 1)

    def test_clean_reset_raise_on_retry_pass_breaks_without_crash(self, tmp_path):
        # A fix rejected on the first pass enters the retry loop; if reset_to_clean
        # raises there, the retry aborts (break) without crashing. The fix keeps
        # its first-pass "reverted" outcome.
        bad_file = tmp_path / "bad.py"
        del_file = tmp_path / "del.py"
        calls = {"n": 0}

        def reset_to_clean():
            calls["n"] += 1
            if calls["n"] == 3:
                raise RuntimeError("git checkout failed on retry pass")
            bad_file.write_text("BAD_PRE", encoding="utf-8")
            del_file.write_text("DEL\n", encoding="utf-8")

        bad = {
            "file": "bad.py",
            "category": "fix",
            "line": 1,
            "pre_edit_content": "BAD_PRE",
            "post_edit_content": "BAD_POST",
        }
        deletion = {
            "file": "del.py",
            "category": "dead-code",
            "line": 1,
            "pre_edit_content": "DEL\n",
            "post_edit_content": "",
        }

        def fake_run_tests(_cmd, _cwd):
            ok = "BAD_POST" not in bad_file.read_text(encoding="utf-8")
            return ok, "" if ok else "bad broke it"

        outcomes = {}

        def on_outcome(idx, _fix, outcome, _detail):
            outcomes[idx] = outcome

        fixed, reverted, skipped = bisect_fixes(
            [bad, deletion],
            "test",
            str(tmp_path),
            run_tests_fn=fake_run_tests,
            on_outcome=on_outcome,
            reset_to_clean=reset_to_clean,
        )
        # bad stays reverted (its retry was aborted); deletion was fixed first pass.
        assert outcomes[0] == "reverted"
        assert outcomes[1] == "fixed"
        assert (fixed, reverted, skipped) == (1, 1, 0)
