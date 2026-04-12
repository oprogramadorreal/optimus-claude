from harness_common.digest import (
    build_coverage_coaching,
    build_coverage_digest,
    build_iteration_coaching,
    build_progress_digest,
)

# ---------------------------------------------------------------------------
# build_progress_digest
# ---------------------------------------------------------------------------


class TestBuildProgressDigest:
    def _make_progress(self, findings=None, scope_files=None, test_results=None):
        return {
            "findings": findings or [],
            "scope_files": scope_files or {"current": []},
            "test_results": test_results
            or {"last_full_run": None, "last_run_output_summary": ""},
        }

    def test_iteration_1_shows_scope_only(self):
        progress = self._make_progress(scope_files={"current": ["src/a.py"]})
        digest = build_progress_digest(progress, iteration=1)
        assert "Scope:" in digest
        assert "src/a.py" in digest
        # No progress line on iteration 1
        assert "Progress:" not in digest

    def test_iteration_2_shows_progress_counts(self):
        findings = [
            {"status": "fixed"},
            {"status": "reverted — test failure", "fix_description": "x"},
            {"status": "persistent — fix failed", "fix_description": "y"},
        ]
        progress = self._make_progress(findings=findings)
        digest = build_progress_digest(progress, iteration=2)
        assert "1 fixed" in digest
        assert "1 reverted" in digest
        assert "1 persistent" in digest

    def test_empty_scope_shows_discovery_note(self):
        progress = self._make_progress()
        digest = build_progress_digest(progress, iteration=1)
        assert "discover via git" in digest

    def test_scope_truncation(self):
        files = [f"src/file{i}.py" for i in range(15)]
        progress = self._make_progress(scope_files={"current": files})
        digest = build_progress_digest(progress, iteration=1)
        assert "15 files" in digest
        assert "+7 more" in digest

    def test_test_result_included(self):
        progress = self._make_progress(
            test_results={
                "last_full_run": "fail",
                "last_run_output_summary": "FAILED test_auth.py::test_login",
            }
        )
        digest = build_progress_digest(progress, iteration=2)
        assert "Last test run: fail" in digest
        assert "test_auth" in digest

    def test_failed_fixes_block_included_on_iteration_2(self):
        findings = [
            {
                "status": "reverted — test failure",
                "file": "src/app.py",
                "line": 10,
                "category": "bug",
                "fix_description": "Added null check",
                "last_failure_hint": "TypeError: None has no attr",
            }
        ]
        progress = self._make_progress(findings=findings)
        digest = build_progress_digest(progress, iteration=2)
        assert "Failed fix attempts:" in digest
        assert "src/app.py:10" in digest
        assert "Added null check" in digest
        assert "TypeError" in digest

    def test_no_failed_fixes_block_when_all_fixed(self):
        findings = [{"status": "fixed"}]
        progress = self._make_progress(findings=findings)
        digest = build_progress_digest(progress, iteration=2)
        assert "Failed fix attempts:" not in digest

    def test_failed_fixes_truncated_beyond_max(self):
        findings = [
            {
                "status": "reverted — test failure",
                "file": f"src/f{i}.py",
                "line": i,
                "category": "bug",
                "fix_description": f"Fix {i}",
            }
            for i in range(8)
        ]
        progress = self._make_progress(findings=findings)
        digest = build_progress_digest(progress, iteration=2)
        assert "... and 3 more" in digest


# ---------------------------------------------------------------------------
# build_iteration_coaching
# ---------------------------------------------------------------------------


class TestBuildIterationCoaching:
    def _make_progress(self, findings=None):
        return {"findings": findings or []}

    def test_iteration_1(self):
        coaching = build_iteration_coaching(self._make_progress(), iteration=1)
        assert "first pass" in coaching.lower()
        assert "high-severity" in coaching.lower()

    def test_iteration_2_with_reverts_prioritizes_revert_guidance(self):
        findings = [{"status": "reverted — test failure"}]
        coaching = build_iteration_coaching(self._make_progress(findings), iteration=2)
        assert "reverted" in coaching.lower()
        assert "different approach" in coaching.lower()

    def test_iteration_2_no_reverts(self):
        findings = [{"status": "fixed"}]
        coaching = build_iteration_coaching(self._make_progress(findings), iteration=2)
        assert "fixed so far" in coaching.lower()
        assert "new patterns" in coaching.lower()

    def test_iteration_5_diminishing(self):
        findings = [{"status": "fixed"}]
        coaching = build_iteration_coaching(self._make_progress(findings), iteration=5)
        assert "diminishing" in coaching.lower()
        assert "critical" in coaching.lower()


# ---------------------------------------------------------------------------
# build_coverage_digest
# ---------------------------------------------------------------------------


class TestBuildCoverageDigest:
    def _make_progress(
        self,
        baseline=None,
        current=None,
        tests_created=None,
        untestable=None,
        test_results=None,
    ):
        return {
            "coverage": {
                "baseline": baseline,
                "current": current,
                "history": [],
            },
            "tests_created": tests_created or [],
            "untestable_code": untestable or [],
            "test_results": test_results
            or {"last_full_run": None, "last_run_output_summary": ""},
        }

    def test_baseline_and_current_coverage(self):
        progress = self._make_progress(baseline=45.0, current=62.0)
        digest = build_coverage_digest(progress, cycle=2, phase="unit-test")
        assert "baseline 45.0%" in digest
        assert "current 62.0%" in digest

    def test_tests_created_count(self):
        tests = [{"file": "test_a.py"}, {"file": "test_b.py"}]
        progress = self._make_progress(tests_created=tests)
        digest = build_coverage_digest(progress, cycle=2, phase="unit-test")
        assert "Tests created so far: 2" in digest

    def test_pending_untestable_shown(self):
        untestable = [
            {"file": "src/legacy.py", "status": "pending"},
            {"file": "src/old.py", "status": "attempted"},
        ]
        progress = self._make_progress(untestable=untestable)
        digest = build_coverage_digest(progress, cycle=1, phase="unit-test")
        assert "Untestable code items pending: 1" in digest

    def test_refactor_phase_shows_untestable_files(self):
        untestable = [
            {"file": "src/legacy.py", "status": "pending"},
            {"file": "src/legacy.py", "function": "bar", "status": "pending"},
            {"file": "src/old.py", "status": "pending"},
        ]
        progress = self._make_progress(untestable=untestable)
        digest = build_coverage_digest(progress, cycle=1, phase="refactor")
        assert "Untestable files to address:" in digest
        assert "src/legacy.py" in digest
        assert "src/old.py" in digest

    def test_no_coverage_data(self):
        progress = self._make_progress()
        digest = build_coverage_digest(progress, cycle=1, phase="unit-test")
        # Should not crash, just produce minimal output
        assert "baseline" not in digest


# ---------------------------------------------------------------------------
# build_coverage_coaching
# ---------------------------------------------------------------------------


class TestBuildCoverageCoaching:
    def _make_progress(self, untestable=None, history=None):
        return {
            "untestable_code": untestable or [],
            "coverage": {"history": history or []},
        }

    def test_first_cycle_unit_test(self):
        coaching = build_coverage_coaching(
            self._make_progress(), cycle=1, phase="unit-test"
        )
        assert "first cycle" in coaching.lower()
        assert "coverage gaps" in coaching.lower()

    def test_refactor_phase(self):
        untestable = [
            {"file": "src/a.py", "status": "pending"},
            {"file": "src/b.py", "status": "pending"},
        ]
        coaching = build_coverage_coaching(
            self._make_progress(untestable=untestable), cycle=2, phase="refactor"
        )
        assert "2 untestable" in coaching.lower()
        assert "testable" in coaching.lower()

    def test_unit_test_stalled_coverage(self):
        history = [
            {"cycle": 1, "delta": 5.0},
            {"cycle": 2, "delta": 0},
        ]
        coaching = build_coverage_coaching(
            self._make_progress(history=history), cycle=3, phase="unit-test"
        )
        assert "stalled" in coaching.lower()

    def test_unit_test_cycle_2_normal(self):
        history = [{"cycle": 1, "delta": 5.0}]
        coaching = build_coverage_coaching(
            self._make_progress(history=history), cycle=2, phase="unit-test"
        )
        assert "continue writing" in coaching.lower()
