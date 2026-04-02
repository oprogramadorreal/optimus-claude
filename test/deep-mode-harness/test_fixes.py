from pathlib import Path
from unittest.mock import patch

from impl.fixes import (
    _is_path_within,
    _swap_content,
    _try_apply_fix,
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


class TestTryApplyFix:
    def _make_file_and_fix(self, tmp_path):
        f = tmp_path / "src" / "app.js"
        f.parent.mkdir(parents=True)
        f.write_text("const x = obj.value;", encoding="utf-8")
        fix = {
            "file": "src/app.js",
            "line": 1,
            "category": "bug",
            "pre_edit_content": "obj.value",
            "post_edit_content": "obj?.value",
        }
        return f, fix

    @patch("impl.fixes.run_tests")
    def test_fixed_when_tests_pass(self, mock_run_tests, tmp_path, sample_progress):
        mock_run_tests.return_value = (True, "All tests passed")
        f, fix = self._make_file_and_fix(tmp_path)
        outcome, _ = _try_apply_fix(fix, "npm test", str(tmp_path), sample_progress)
        assert outcome == "fixed"
        assert "obj?.value" in f.read_text(encoding="utf-8")
        assert sample_progress["findings"][0]["status"] == "fixed"

    @patch("impl.fixes.run_tests")
    def test_reverted_when_tests_fail(self, mock_run_tests, tmp_path, sample_progress):
        mock_run_tests.return_value = (False, "1 test failed")
        f, fix = self._make_file_and_fix(tmp_path)
        outcome, summary = _try_apply_fix(
            fix, "npm test", str(tmp_path), sample_progress
        )
        assert outcome == "reverted"
        assert summary == "1 test failed"
        # File should be reverted to original
        assert "obj.value" in f.read_text(encoding="utf-8")
        assert "obj?.value" not in f.read_text(encoding="utf-8")

    def test_skipped_when_apply_fails(self, tmp_path, sample_progress):
        fix = {
            "file": "nonexistent.js",
            "pre_edit_content": "x",
            "post_edit_content": "y",
        }
        outcome, _ = _try_apply_fix(fix, "npm test", str(tmp_path), sample_progress)
        assert outcome == "skipped"

    @patch("impl.fixes.run_tests")
    @patch("impl.fixes.revert_single_fix", return_value=False)
    def test_fixed_when_revert_fails(
        self, mock_revert, mock_run_tests, tmp_path, sample_progress
    ):
        mock_run_tests.return_value = (False, "test failed")
        f, fix = self._make_file_and_fix(tmp_path)
        outcome, _ = _try_apply_fix(fix, "npm test", str(tmp_path), sample_progress)
        assert outcome == "fixed"  # retained because revert failed
        assert sample_progress["findings"][0]["status"] == "fixed"


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
