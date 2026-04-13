from harness_common.digest import (
    build_coverage_coaching,
    build_coverage_digest,
    build_iteration_coaching,
    build_progress_digest,
)


class TestBuildProgressDigest:
    def test_first_iteration_no_findings(self):
        progress = {"findings": [], "config": {"max_iterations": 5}}
        result = build_progress_digest(progress, 1)
        assert "First iteration" in result

    def test_shows_finding_counts(self):
        progress = {
            "findings": [
                {"status": "fixed", "file": "a.py", "line": 1},
                {"status": "reverted — test failure", "file": "b.py", "line": 2},
                {"status": "persistent — fix failed", "file": "c.py", "line": 3},
                {"status": "discovered", "file": "d.py", "line": 4},
            ],
            "config": {"max_iterations": 5},
            "scope_files": {"current": ["a.py", "b.py"]},
            "test_results": {"last_full_run": "pass"},
        }
        result = build_progress_digest(progress, 2)
        assert "1 fixed" in result
        assert "1 reverted" in result
        assert "1 persistent" in result
        assert "1 pending" in result
        assert "PASS" in result

    def test_scope_truncation(self):
        progress = {
            "findings": [{"status": "fixed"}],
            "config": {"max_iterations": 5},
            "scope_files": {"current": [f"file{i}.py" for i in range(8)]},
        }
        result = build_progress_digest(progress, 2)
        assert "+3 more" in result

    def test_failed_fixes_shown_from_iteration_2(self):
        progress = {
            "findings": [
                {
                    "status": "reverted — test failure",
                    "file": "x.py",
                    "line": 10,
                    "last_failure_hint": "NameError: foo undefined",
                },
            ],
            "config": {"max_iterations": 5},
        }
        result = build_progress_digest(progress, 2)
        assert "Prior failed fixes" in result
        assert "NameError" in result

    def test_no_failed_fixes_on_iteration_1(self):
        progress = {
            "findings": [
                {"status": "reverted — test failure", "file": "x.py", "line": 10},
            ],
            "config": {"max_iterations": 5},
        }
        result = build_progress_digest(progress, 1)
        assert "Prior failed fixes" not in result


class TestBuildIterationCoaching:
    def test_iteration_1(self):
        result = build_iteration_coaching({}, 1)
        assert "high-severity" in result

    def test_iteration_2_with_reverts(self):
        progress = {"findings": [{"status": "reverted — test failure"}]}
        result = build_iteration_coaching(progress, 2)
        assert "NEW patterns" in result
        assert "fundamentally different" in result

    def test_iteration_3_no_reverts(self):
        progress = {"findings": [{"status": "fixed"}]}
        result = build_iteration_coaching(progress, 3)
        assert "NEW patterns" in result
        assert "fundamentally different" not in result

    def test_iteration_4_diminishing(self):
        result = build_iteration_coaching({}, 4)
        assert "diminishing" in result
        assert "CRITICAL" in result


class TestBuildCoverageDigest:
    def test_basic_coverage_info(self):
        progress = {
            "config": {"max_cycles": 5},
            "coverage": {"baseline": 45, "current": 55},
            "tests_created": [{"file": "test_a.py"}],
            "untestable_code": [],
        }
        result = build_coverage_digest(progress, 2, "unit-test")
        assert "Cycle 2" in result
        assert "baseline 45%" in result
        assert "current 55%" in result
        assert "Tests written so far: 1" in result

    def test_pending_untestable(self):
        progress = {
            "config": {"max_cycles": 5},
            "coverage": {},
            "untestable_code": [
                {"file": "a.py", "line": 10, "function": "foo", "status": "pending"},
                {"file": "b.py", "line": 20, "function": "bar", "status": "attempted"},
            ],
        }
        result = build_coverage_digest(progress, 1, "refactor")
        assert "pending: 1" in result

    def test_no_baseline(self):
        progress = {"config": {"max_cycles": 3}, "coverage": {}}
        result = build_coverage_digest(progress, 1, "unit-test")
        assert "baseline" not in result


class TestBuildCoverageCoaching:
    def test_unit_test_cycle_1(self):
        result = build_coverage_coaching({}, 1, "unit-test")
        assert "impactful" in result

    def test_unit_test_cycle_2(self):
        result = build_coverage_coaching({}, 2, "unit-test")
        assert "not yet covered" in result

    def test_refactor_cycle_1(self):
        result = build_coverage_coaching({}, 1, "refactor")
        assert "testability" in result

    def test_refactor_cycle_2(self):
        result = build_coverage_coaching({}, 2, "refactor")
        assert "remaining untestable" in result
