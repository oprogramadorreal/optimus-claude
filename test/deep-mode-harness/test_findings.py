from impl.findings import (
    finding_matches,
    mark_all_fixed,
    mark_finding_status,
    update_scope,
)


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
        mark_finding_status(sample_progress, sample_fix, "reverted — test failure", "fail 1")
        mark_finding_status(sample_progress, sample_fix, "reverted — test failure", "fail 2")
        assert sample_progress["findings"][0]["status"] == "reverted — attempt 2"

    def test_promotion_attempt2_to_persistent(self, sample_progress, sample_fix):
        mark_finding_status(sample_progress, sample_fix, "reverted — test failure", "fail 1")
        mark_finding_status(sample_progress, sample_fix, "reverted — test failure", "fail 2")
        mark_finding_status(sample_progress, sample_fix, "reverted — test failure", "fail 3")
        assert sample_progress["findings"][0]["status"] == "persistent — fix failed"

    def test_sequential_ids(self, sample_progress):
        fix1 = {"file": "a.js", "line": 1, "category": "bug"}
        fix2 = {"file": "b.js", "line": 2, "category": "style"}
        mark_finding_status(sample_progress, fix1, "fixed", None)
        mark_finding_status(sample_progress, fix2, "fixed", None)
        assert sample_progress["findings"][0]["id"] == "f-001"
        assert sample_progress["findings"][1]["id"] == "f-002"


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
    def test_refactor_no_change(self, sample_progress):
        sample_progress["skill"] = "refactor"
        sample_progress["scope_files"]["current"] = ["src/"]
        update_scope(sample_progress, {"fixes_applied": [{"file": "src/a.js"}]})
        assert sample_progress["scope_files"]["current"] == ["src/"]

    def test_code_review_narrows(self, sample_progress):
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
