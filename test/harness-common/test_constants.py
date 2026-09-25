import pytest
from harness_common.constants import normalize_path


class TestNormalizePath:
    def test_backslash_to_forward(self):
        assert normalize_path("C:\\Users\\test\\file.txt") == "C:/Users/test/file.txt"

    def test_forward_slash_unchanged(self):
        assert normalize_path("src/app.js") == "src/app.js"

    def test_empty_string(self):
        assert normalize_path("") == ""

    def test_mixed_slashes(self):
        assert normalize_path("src\\api/routes\\v1") == "src/api/routes/v1"

    @pytest.mark.parametrize("value", [None, 5])
    def test_non_string_is_no_path(self, value):
        assert normalize_path(value) == ""
