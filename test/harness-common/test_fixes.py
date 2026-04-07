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
        """on_outcome receives (idx, fix, outcome) for every processed fix."""
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

        def on_outcome(idx, fix, outcome):
            outcomes.append((idx, fix["file"], outcome))

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
        outcomes_by_file = {file: outcome for _, file, outcome in outcomes}
        assert outcomes_by_file["a.txt"] == "fixed"
        assert outcomes_by_file["b.txt"] == "reverted"
        assert outcomes_by_file["gone.txt"] == "retained"

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

        def on_outcome(idx, fix, outcome):
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
