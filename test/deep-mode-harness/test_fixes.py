from pathlib import Path

from impl.fixes import (
    _is_path_within,
    _swap_content,
    apply_single_fix,
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
