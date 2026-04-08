from pathlib import Path
from unittest.mock import patch

from harness_common.fixes import _is_path_within, _swap_content
from impl.fixes import (
    _make_bisect_outcome_callback,
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
        f.write_text("aaa aaa", encoding="utf-8")
        fix = {
            "file": "test.txt",
            "pre_edit_content": "aaa",
            "post_edit_content": "bbb",
        }
        assert (
            _swap_content(fix, str(tmp_path), "pre_edit_content", "post_edit_content")
            is False
        )

    def test_empty_find_key(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello", encoding="utf-8")
        fix = {"file": "test.txt", "pre_edit_content": "", "post_edit_content": "y"}
        assert (
            _swap_content(fix, str(tmp_path), "pre_edit_content", "post_edit_content")
            is False
        )

    def test_blocks_git_path(self, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        f = git_dir / "config"
        f.write_text("original", encoding="utf-8")
        fix = {
            "file": ".git/config",
            "pre_edit_content": "original",
            "post_edit_content": "hacked",
        }
        assert (
            _swap_content(fix, str(tmp_path), "pre_edit_content", "post_edit_content")
            is False
        )

    def test_deletion_fix(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("keep this\ndelete this\nkeep too", encoding="utf-8")
        fix = {
            "file": "test.txt",
            "pre_edit_content": "delete this\n",
            "post_edit_content": "",
        }
        result = _swap_content(
            fix, str(tmp_path), "pre_edit_content", "post_edit_content"
        )
        assert result is True
        assert f.read_text(encoding="utf-8") == "keep this\nkeep too"


class TestApplyRevertRoundTrip:
    def test_apply_and_revert(self, tmp_path):
        f = tmp_path / "src" / "app.js"
        f.parent.mkdir(parents=True)
        original = "const x = obj.value;"
        f.write_text(original, encoding="utf-8")
        fix = {
            "file": "src/app.js",
            "pre_edit_content": "obj.value",
            "post_edit_content": "obj?.value",
        }
        assert apply_single_fix(fix, str(tmp_path)) is True
        assert "obj?.value" in f.read_text(encoding="utf-8")

        assert revert_single_fix(fix, str(tmp_path)) is True
        assert f.read_text(encoding="utf-8") == original


class TestSwapContentEdgeCases:
    def test_unicode_decode_error(self, tmp_path):
        """Binary file triggers UnicodeDecodeError and returns False."""
        f = tmp_path / "binary.bin"
        f.write_bytes(b"\xff\xfe\x00\x01\x80\x81")
        fix = {
            "file": "binary.bin",
            "pre_edit_content": "x",
            "post_edit_content": "y",
        }
        assert (
            _swap_content(fix, str(tmp_path), "pre_edit_content", "post_edit_content")
            is False
        )

    def test_backslash_path_normalization(self, tmp_path):
        """Windows-style backslashes in fix['file'] are normalized."""
        sub = tmp_path / "src"
        sub.mkdir()
        f = sub / "app.js"
        f.write_text("hello", encoding="utf-8")
        fix = {
            "file": "src\\app.js",
            "pre_edit_content": "hello",
            "post_edit_content": "goodbye",
        }
        result = _swap_content(
            fix, str(tmp_path), "pre_edit_content", "post_edit_content"
        )
        assert result is True
        assert f.read_text(encoding="utf-8") == "goodbye"

    def test_path_traversal_blocked(self, tmp_path):
        """Path traversal outside cwd is blocked."""
        fix = {
            "file": "../etc/passwd",
            "pre_edit_content": "x",
            "post_edit_content": "y",
        }
        assert (
            _swap_content(fix, str(tmp_path), "pre_edit_content", "post_edit_content")
            is False
        )


class TestBisectFixes:
    def _setup_files(self, tmp_path, filenames):
        """Create source files with unique content for each fix."""
        fixes = []
        for i, name in enumerate(filenames):
            f = tmp_path / name
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(f"original_{i}", encoding="utf-8")
            fixes.append(
                {
                    "file": name,
                    "line": 1,
                    "category": "bug",
                    "summary": f"Fix {name}",
                    "pre_edit_content": f"original_{i}",
                    "post_edit_content": f"fixed_{i}",
                }
            )
        return fixes

    @patch("impl.fixes.run_tests")
    def test_all_fixes_pass(self, mock_run_tests, tmp_path, sample_progress):
        mock_run_tests.return_value = (True, "pass")
        fixes = self._setup_files(tmp_path, ["a.js", "b.js"])
        # Apply fixes first (bisect reverts then re-applies)
        for fix in fixes:
            apply_single_fix(fix, str(tmp_path))
        fixed, reverted, skipped = bisect_fixes(
            fixes, "npm test", str(tmp_path), sample_progress
        )
        assert fixed == 2
        assert reverted == 0
        assert skipped == 0

    @patch("impl.fixes.run_tests")
    def test_one_fix_fails(self, mock_run_tests, tmp_path, sample_progress):
        # First fix passes, second fails, retry also fails
        mock_run_tests.side_effect = [(True, "pass"), (False, "fail"), (False, "fail")]
        fixes = self._setup_files(tmp_path, ["a.js", "b.js"])
        for fix in fixes:
            apply_single_fix(fix, str(tmp_path))
        fixed, reverted, skipped = bisect_fixes(
            fixes, "npm test", str(tmp_path), sample_progress
        )
        assert fixed == 1
        assert reverted == 1
        assert skipped == 0

    @patch("impl.fixes.run_tests")
    def test_retry_pass_on_second_attempt(
        self, mock_run_tests, tmp_path, sample_progress
    ):
        # First pass: fix 0 passes, fix 1 fails
        # Second pass (retry): fix 1 passes
        mock_run_tests.side_effect = [
            (True, "pass"),
            (False, "fail"),
            (True, "pass on retry"),
        ]
        fixes = self._setup_files(tmp_path, ["a.js", "b.js"])
        for fix in fixes:
            apply_single_fix(fix, str(tmp_path))
        fixed, reverted, skipped = bisect_fixes(
            fixes, "npm test", str(tmp_path), sample_progress
        )
        assert fixed == 2
        assert reverted == 0

    @patch("impl.fixes.run_tests")
    def test_no_retry_when_nothing_fixed(
        self, mock_run_tests, tmp_path, sample_progress
    ):
        # All fixes fail — no retry (retry only happens when fixed_count > 0)
        mock_run_tests.side_effect = [(False, "fail"), (False, "fail")]
        fixes = self._setup_files(tmp_path, ["a.js", "b.js"])
        for fix in fixes:
            apply_single_fix(fix, str(tmp_path))
        fixed, reverted, skipped = bisect_fixes(
            fixes, "npm test", str(tmp_path), sample_progress
        )
        assert fixed == 0
        assert reverted == 2

    @patch("impl.fixes.run_tests")
    def test_revert_failure_marks_retained(
        self, mock_run_tests, tmp_path, sample_progress
    ):
        """When mechanical revert fails, fix is marked 'retained — revert failed'."""
        fixes = self._setup_files(tmp_path, ["a.js"])
        apply_single_fix(fixes[0], str(tmp_path))
        # Tamper with file so revert can't find the post_edit_content
        f = tmp_path / "a.js"
        f.write_text("completely different content", encoding="utf-8")

        fixed, reverted, skipped = bisect_fixes(
            fixes, "npm test", str(tmp_path), sample_progress
        )
        assert fixed == 1  # counted as applied (couldn't revert)
        assert reverted == 0
        # Finding should be marked retained
        status = sample_progress["findings"][0]["status"]
        assert "retained" in status

    @patch("impl.fixes.run_tests")
    @patch("harness_common.fixes.revert_single_fix", return_value=True)
    @patch("harness_common.fixes.apply_single_fix")
    def test_skip_in_first_pass(
        self, mock_apply, mock_revert, mock_run_tests, tmp_path, sample_progress
    ):
        """Fix that can't be re-applied during bisection is marked skipped."""
        fixes = self._setup_files(tmp_path, ["a.js", "b.js"])
        # First fix apply fails (skip), second succeeds
        mock_apply.side_effect = [False, True]
        mock_run_tests.return_value = (True, "pass")
        fixed, reverted, skipped = bisect_fixes(
            fixes, "npm test", str(tmp_path), sample_progress
        )
        assert skipped == 1
        assert fixed == 1
        assert reverted == 0

    def test_unknown_outcome_is_ignored(self, sample_progress):
        """Callback ignores outcome strings outside the known set, leaving
        the finding untouched — a defensive guard against future shared
        bisector outcomes that deep-mode hasn't mapped yet."""
        sample_progress["findings"] = [
            {"file": "a.js", "line": 1, "category": "bug", "status": "pending"}
        ]
        fix = {"file": "a.js", "line": 1, "category": "bug"}
        callback = _make_bisect_outcome_callback(sample_progress)

        callback(0, fix, "some-future-outcome", detail="ignored")

        assert sample_progress["findings"][0]["status"] == "pending"

    @patch("impl.fixes.run_tests")
    @patch("harness_common.fixes.revert_single_fix", return_value=True)
    @patch("harness_common.fixes.apply_single_fix")
    def test_retry_skip_path(
        self, mock_apply, mock_revert, mock_run_tests, tmp_path, sample_progress
    ):
        """Fix that fails first pass and can't re-apply on retry is marked skipped."""
        fixes = self._setup_files(tmp_path, ["a.js", "b.js"])
        # First pass: fix 0 applies+passes, fix 1 applies+fails test
        # Retry: fix 1 apply returns False (skipped)
        mock_apply.side_effect = [True, True, False]
        mock_run_tests.side_effect = [
            (True, "pass"),  # fix 0 first pass
            (False, "fail"),  # fix 1 first pass
        ]
        fixed, reverted, skipped = bisect_fixes(
            fixes, "npm test", str(tmp_path), sample_progress
        )
        assert fixed == 1
        assert skipped == 1
        assert reverted == 0
