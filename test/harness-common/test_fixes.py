from pathlib import Path
from unittest.mock import patch

from harness_common.fixes import (
    _is_path_within,
    _swap_content,
    apply_single_fix,
    bisect_fixes,
    revert_single_fix,
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


class TestRevertSingleFix:
    def test_reverts_post_to_pre(self, tmp_path):
        f = tmp_path / "src.js"
        f.write_text("obj?.value", encoding="utf-8")
        fix = {
            "file": "src.js",
            "pre_edit_content": "obj.value",
            "post_edit_content": "obj?.value",
        }
        assert revert_single_fix(fix, str(tmp_path)) is True
        assert f.read_text(encoding="utf-8") == "obj.value"


def _make_fix(tmp_path, filename, pre, post):
    """Helper: create a file with post content (applied state) and return fix dict."""
    f = tmp_path / filename
    f.write_text(post, encoding="utf-8")
    return {"file": filename, "pre_edit_content": pre, "post_edit_content": post}


class TestBisectFixes:
    def test_all_fixes_pass(self, tmp_path):
        """All fixes re-applied successfully and tests pass → all counted as fixed."""
        fixes = [
            _make_fix(tmp_path, "a.txt", "old_a", "new_a"),
            _make_fix(tmp_path, "b.txt", "old_b", "new_b"),
        ]
        run_tests = lambda cmd, cwd: (True, "ok")
        fixed, reverted, skipped = bisect_fixes(fixes, "test", str(tmp_path), run_tests)
        assert fixed == 2
        assert reverted == 0
        assert skipped == 0
        assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "new_a"
        assert (tmp_path / "b.txt").read_text(encoding="utf-8") == "new_b"

    def test_one_fix_breaks_tests(self, tmp_path):
        """Second fix causes test failure → it stays reverted."""
        fixes = [
            _make_fix(tmp_path, "a.txt", "old_a", "new_a"),
            _make_fix(tmp_path, "b.txt", "old_b", "new_b"),
        ]
        call_count = 0

        def run_tests(cmd, cwd):
            nonlocal call_count
            call_count += 1
            return (True, "ok") if call_count == 1 else (False, "fail")

        fixed, reverted, skipped = bisect_fixes(fixes, "test", str(tmp_path), run_tests)
        assert fixed == 1
        assert reverted == 1
        assert skipped == 0
        assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "new_a"
        assert (tmp_path / "b.txt").read_text(encoding="utf-8") == "old_b"

    def test_failed_revert_counted_as_fixed(self, tmp_path):
        """Fix that can't be reverted stays applied and counts as fixed."""
        fix = {
            "file": "missing.txt",
            "pre_edit_content": "old",
            "post_edit_content": "new",
        }
        run_tests = lambda cmd, cwd: (True, "ok")
        fixed, reverted, skipped = bisect_fixes([fix], "test", str(tmp_path), run_tests)
        assert fixed == 1
        assert reverted == 0
        assert skipped == 0

    def test_failed_apply_counted_as_skipped(self, tmp_path):
        """Fix that reverts but can't be re-applied counts as skipped."""
        f = tmp_path / "a.txt"
        f.write_text("new_a", encoding="utf-8")
        fix = {
            "file": "a.txt",
            "pre_edit_content": "old_a",
            "post_edit_content": "new_a",
        }
        # After revert, file has "old_a". Now make re-apply impossible by
        # writing ambiguous content before apply step runs.
        original_apply = (
            apply_single_fix.__wrapped__
            if hasattr(apply_single_fix, "__wrapped__")
            else None
        )

        def run_tests(cmd, cwd):
            return (True, "ok")

        # Patch apply_single_fix to return False (simulating apply failure)
        with patch("harness_common.fixes.apply_single_fix", return_value=False):
            fixed, reverted, skipped = bisect_fixes(
                [fix], "test", str(tmp_path), run_tests
            )
        assert fixed == 0
        assert reverted == 0
        assert skipped == 1

    def test_default_run_tests_fn(self, tmp_path):
        """When run_tests_fn is None, falls back to harness_common.runner.run_tests."""
        fixes = [_make_fix(tmp_path, "a.txt", "old_a", "new_a")]
        with patch(
            "harness_common.runner.run_tests", return_value=(True, "ok")
        ) as mock_rt:
            fixed, reverted, skipped = bisect_fixes(fixes, "test", str(tmp_path))
        assert fixed == 1
        mock_rt.assert_called_once_with("test", str(tmp_path))

    def test_mixed_scenario(self, tmp_path):
        """Mix of pass, fail, and unrevertable fixes."""
        fixes = [
            _make_fix(tmp_path, "a.txt", "old_a", "new_a"),  # will pass
            _make_fix(tmp_path, "b.txt", "old_b", "new_b"),  # will fail
            {
                "file": "gone.txt",
                "pre_edit_content": "x",
                "post_edit_content": "y",
            },  # unrevertable
        ]
        call_count = 0

        def run_tests(cmd, cwd):
            nonlocal call_count
            call_count += 1
            return (True, "ok") if call_count == 1 else (False, "fail")

        fixed, reverted, skipped = bisect_fixes(fixes, "test", str(tmp_path), run_tests)
        assert fixed == 2  # a.txt passed + gone.txt unrevertable
        assert reverted == 1  # b.txt failed
        assert skipped == 0

    def test_second_pass_recovers_order_dependent_fix(self, tmp_path):
        """Fix that fails in first pass due to ordering succeeds on retry."""
        fixes = [
            _make_fix(tmp_path, "a.txt", "old_a", "new_a"),  # depends on b
            _make_fix(tmp_path, "b.txt", "old_b", "new_b"),  # independent
        ]
        call_count = 0

        def run_tests(cmd, cwd):
            nonlocal call_count
            call_count += 1
            # First pass: a fails (call 1), b passes (call 2)
            # Second pass (retry a): a passes (call 3) because b is now applied
            if call_count == 1:
                return (False, "fail — missing import from b")
            return (True, "ok")

        fixed, reverted, skipped = bisect_fixes(fixes, "test", str(tmp_path), run_tests)
        assert call_count == 3  # first-pass(A fail, B pass) + second-pass(A pass)
        assert fixed == 2  # both recovered
        assert reverted == 0
        assert skipped == 0
        assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "new_a"
        assert (tmp_path / "b.txt").read_text(encoding="utf-8") == "new_b"

    def test_no_retry_when_all_reverted(self, tmp_path):
        """When no fixes passed first pass, skip second pass entirely."""
        fixes = [
            _make_fix(tmp_path, "a.txt", "old_a", "new_a"),
            _make_fix(tmp_path, "b.txt", "old_b", "new_b"),
        ]
        run_tests = lambda cmd, cwd: (False, "fail")
        fixed, reverted, skipped = bisect_fixes(fixes, "test", str(tmp_path), run_tests)
        assert fixed == 0
        assert reverted == 2
        assert skipped == 0
        assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "old_a"
        assert (tmp_path / "b.txt").read_text(encoding="utf-8") == "old_b"

    def test_on_outcome_callback_invoked_per_fix(self, tmp_path):
        """on_outcome receives (idx, fix, outcome, detail) for every processed fix."""
        fixes = [
            _make_fix(tmp_path, "a.txt", "old_a", "new_a"),  # will pass → "fixed"
            _make_fix(tmp_path, "b.txt", "old_b", "new_b"),  # will fail → "reverted"
            {
                "file": "gone.txt",  # unrevertable → "retained"
                "pre_edit_content": "x",
                "post_edit_content": "y",
            },
        ]
        call_count = 0

        def run_tests(cmd, cwd):
            nonlocal call_count
            call_count += 1
            return (True, "ok") if call_count == 1 else (False, "fail")

        outcomes = []

        def on_outcome(idx, fix, outcome, detail=None):
            outcomes.append((idx, fix["file"], outcome, detail))

        fixed, reverted, skipped = bisect_fixes(
            fixes,
            "test",
            str(tmp_path),
            run_tests,
            on_outcome=on_outcome,
        )
        # gone.txt is "retained" (counted as fixed), a.txt is "fixed", b.txt "reverted"
        assert fixed == 2
        assert reverted == 1
        assert skipped == 0
        # All three fixes should have produced exactly one outcome event
        assert len(outcomes) == 3
        outcomes_by_file = {
            file: (outcome, detail) for _, file, outcome, detail in outcomes
        }
        assert outcomes_by_file["a.txt"] == ("fixed", None)
        # b.txt is reverted with the failure summary as detail
        assert outcomes_by_file["b.txt"][0] == "reverted"
        assert outcomes_by_file["b.txt"][1] == "fail"
        assert outcomes_by_file["gone.txt"] == ("retained", None)

    def test_second_pass_apply_failure_counted_as_skipped(self, tmp_path):
        """If a reverted fix can't be re-applied on retry, it counts as skipped."""
        fixes = [
            _make_fix(tmp_path, "a.txt", "old_a", "new_a"),  # passes
            _make_fix(tmp_path, "b.txt", "old_b", "new_b"),  # fails first pass
        ]
        call_count = 0

        def run_tests(cmd, cwd):
            nonlocal call_count
            call_count += 1
            return (True, "ok") if call_count == 1 else (False, "fail")

        outcomes = []

        def on_outcome(idx, fix, outcome, detail=None):
            outcomes.append((fix["file"], outcome))

        # apply_single_fix call sequence:
        #   1) first-pass apply A → True
        #   2) first-pass apply B → True
        #   3) second-pass retry apply B → False  (drift simulated)
        with patch(
            "harness_common.fixes.apply_single_fix",
            side_effect=[True, True, False],
        ):
            fixed, reverted, skipped = bisect_fixes(
                fixes,
                "test",
                str(tmp_path),
                run_tests,
                on_outcome=on_outcome,
            )
        assert fixed == 1  # only A
        assert reverted == 0
        assert skipped == 1  # B's retry could not re-apply
        # B should have been marked "skipped" via the second-pass branch
        assert ("b.txt", "skipped") in outcomes
        assert ("a.txt", "fixed") in outcomes


class TestBisectCleanReset:
    """bisect_fixes with a reset_to_clean hook isolates deletion fixes that the
    legacy revert-all/re-apply strategy cannot un-apply."""

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

        # The harmful deletion is correctly reverted (not "retained"), and the
        # good co-fix survives instead of being lost to a full rollback.
        assert outcomes["del.py"] == "reverted"
        assert outcomes["good.py"] == "fixed"
        assert (fixed, reverted, skipped) == (1, 1, 0)
        assert "DELETE_ME" in del_file.read_text(encoding="utf-8")
        assert "GOOD_POST" in good_file.read_text(encoding="utf-8")

    def test_legacy_path_retains_deletion_without_reset(self, tmp_path):
        # Without a reset hook, a deletion that can't be reverted is counted as
        # "retained" — this is the behavior the clean-reset hook fixes.
        del_file = tmp_path / "del.py"
        del_file.write_text("DELETE_ME\n", encoding="utf-8")
        deletion = {
            "file": "del.py",
            "category": "dead-code",
            "line": 1,
            "pre_edit_content": "DELETE_ME\n",
            "post_edit_content": "",
        }
        apply_single_fix(deletion, str(tmp_path))

        outcomes = {}

        def on_outcome(_idx, fix, outcome, _detail):
            outcomes[fix["file"]] = outcome

        bisect_fixes(
            [deletion],
            "test",
            str(tmp_path),
            run_tests_fn=lambda _c, _w: (False, "boom"),
            on_outcome=on_outcome,
        )
        assert outcomes["del.py"] == "retained"

    def test_clean_reset_first_pass_apply_failure_skipped(self, tmp_path):
        # A fix that fails to apply on the clean-reset first pass is counted as
        # skipped (the clean-reset path has its own skip branch, separate from
        # the legacy bisect's). A deletion fix routes the set through clean-reset.
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
