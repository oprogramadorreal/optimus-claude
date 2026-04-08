from impl.findings import (
    _escalate_revert_status,
    _truncate_failure_hint,
    finding_matches,
    mark_all_fixed,
    mark_finding_status,
    update_scope,
)


class TestTruncateFailureHint:
    def test_none_detail(self):
        assert _truncate_failure_hint(None) is None

    def test_empty_string(self):
        assert _truncate_failure_hint("") is None

    def test_short_string(self):
        assert _truncate_failure_hint("short error") == "short error"

    def test_whitespace_stripped(self):
        assert _truncate_failure_hint("  error  ") == "error"

    def test_long_string_truncated(self):
        long_detail = "x" * 250
        result = _truncate_failure_hint(long_detail)
        assert len(result) == 203  # 200 + "..."
        assert result.endswith("...")

    def test_custom_max_len(self):
        result = _truncate_failure_hint("abcdefghij", max_len=5)
        assert result == "abcde..."


class TestFindingMatches:
    def test_exact_match(self):
        finding = {"file": "src/a.js", "line": 10, "category": "bug"}
        fix = {"file": "src/a.js", "line": 10, "category": "bug"}
        assert finding_matches(finding, fix) is True

    def test_different_file(self):
        finding = {"file": "src/a.js", "line": 10, "category": "bug"}
        fix = {"file": "src/b.js", "line": 10, "category": "bug"}
        assert finding_matches(finding, fix) is False

    def test_different_line(self):
        finding = {"file": "src/a.js", "line": 10, "category": "bug"}
        fix = {"file": "src/a.js", "line": 20, "category": "bug"}
        assert finding_matches(finding, fix) is False

    def test_different_category(self):
        finding = {"file": "src/a.js", "line": 10, "category": "bug"}
        fix = {"file": "src/a.js", "line": 10, "category": "style"}
        assert finding_matches(finding, fix) is False

    def test_missing_keys_in_fix(self):
        finding = {"file": "src/a.js", "line": 10, "category": "bug"}
        fix = {"file": "src/a.js"}
        assert finding_matches(finding, fix) is False


class TestMarkFindingStatus:
    def test_new_finding(self, sample_progress, sample_fix):
        mark_finding_status(sample_progress, sample_fix, "fixed", "test passed")
        assert len(sample_progress["findings"]) == 1
        f = sample_progress["findings"][0]
        assert f["id"] == "f-001"
        assert f["status"] == "fixed"
        assert f["file"] == "src/app.js"

    def test_update_existing(self, sample_progress, sample_fix):
        mark_finding_status(sample_progress, sample_fix, "applied-pending-test", None)
        mark_finding_status(sample_progress, sample_fix, "fixed", "passed")
        assert len(sample_progress["findings"]) == 1
        assert sample_progress["findings"][0]["status"] == "fixed"
        assert len(sample_progress["findings"][0]["status_history"]) == 2

    def test_promotion_reverted_to_attempt2(self, sample_progress, sample_fix):
        mark_finding_status(
            sample_progress, sample_fix, "reverted — test failure", "fail 1"
        )
        mark_finding_status(
            sample_progress, sample_fix, "reverted — test failure", "fail 2"
        )
        assert sample_progress["findings"][0]["status"] == "reverted — attempt 2"

    def test_promotion_attempt2_to_persistent(self, sample_progress, sample_fix):
        mark_finding_status(
            sample_progress, sample_fix, "reverted — test failure", "fail 1"
        )
        mark_finding_status(
            sample_progress, sample_fix, "reverted — test failure", "fail 2"
        )
        mark_finding_status(
            sample_progress, sample_fix, "reverted — test failure", "fail 3"
        )
        assert sample_progress["findings"][0]["status"] == "persistent — fix failed"

    def test_sequential_ids(self, sample_progress):
        fix1 = {"file": "a.js", "line": 1, "category": "bug"}
        fix2 = {"file": "b.js", "line": 2, "category": "style"}
        mark_finding_status(sample_progress, fix1, "fixed", None)
        mark_finding_status(sample_progress, fix2, "fixed", None)
        assert sample_progress["findings"][0]["id"] == "f-001"
        assert sample_progress["findings"][1]["id"] == "f-002"


class TestEscalateRevertStatus:
    def test_persistent_status_stays_persistent(self):
        """Once a finding reaches persistent status, it stays persistent."""
        assert (
            _escalate_revert_status(
                "reverted — test failure", "persistent — fix failed"
            )
            == "persistent — fix failed"
        )

    def test_persistent_status_stays_for_any_new_status(self):
        assert (
            _escalate_revert_status("fixed", "persistent — fix failed")
            == "persistent — fix failed"
        )


class TestMarkAllFixed:
    def test_marks_all(self, sample_progress):
        fixes = [
            {"file": "a.js", "line": 1, "category": "bug"},
            {"file": "b.js", "line": 2, "category": "style"},
        ]
        mark_all_fixed(sample_progress, fixes)
        assert all(f["status"] == "fixed" for f in sample_progress["findings"])
        assert len(sample_progress["findings"]) == 2


class TestUpdateScope:
    def test_refactor_widens_like_code_review(self, sample_progress):
        """Refactor widens scope just like code-review so structural-neighbor
        expansion discovered by agents persists into the next iteration."""
        sample_progress["skill"] = "refactor"
        sample_progress["scope_files"]["current"] = ["src/a.js"]
        sample_progress["findings"] = [
            {"file": "src/a.js", "status": "fixed"},
            {"file": "src/sibling.js", "status": "discovered"},
        ]
        update_scope(sample_progress, {"fixes_applied": [{"file": "src/neighbor.js"}]})
        scope = sample_progress["scope_files"]["current"]
        assert "src/a.js" in scope
        assert "src/sibling.js" in scope
        assert "src/neighbor.js" in scope

    def test_excludes_persistent_findings_from_scope(self, sample_progress):
        sample_progress["findings"] = [
            {"file": "src/a.js", "status": "fixed"},
            {"file": "src/b.js", "status": "persistent — fix failed"},
        ]
        result = {"fixes_applied": [{"file": "src/c.js"}]}
        update_scope(sample_progress, result)
        scope = sample_progress["scope_files"]["current"]
        assert "src/a.js" in scope
        assert "src/c.js" in scope
        # persistent findings are excluded
        assert "src/b.js" not in scope
