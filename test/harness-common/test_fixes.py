from pathlib import Path

from harness_common.fixes import (
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
