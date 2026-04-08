# Re-export shared fix functions for backward compatibility
from harness_common.fixes import (  # noqa: F401
    apply_single_fix,
)
from harness_common.fixes import bisect_fixes as _shared_bisect_fixes
from harness_common.fixes import (  # noqa: F401
    revert_single_fix,
)

from .constants import PREFIX
from .findings import mark_finding_status
from .runner import run_tests

# Map shared bisect outcome strings to deep-mode finding statuses + default
# detail messages for the static (non-test-failure) outcomes. The dynamic
# "reverted" detail is the per-fix test failure summary supplied by the
# shared bisector via the on_outcome callback.
_OUTCOME_TO_STATUS = {
    "fixed": "fixed",
    "reverted": "reverted — test failure",
    "retained": "retained — revert failed",
    "skipped": "skipped — apply failed",
}
_OUTCOME_DEFAULT_DETAIL = {
    "retained": "Could not mechanically revert during bisection — fix retained untested",
    "skipped": "Could not mechanically apply fix during bisection",
}


def _make_bisect_outcome_callback(progress):
    """Build the on_outcome callback that updates deep-mode finding statuses."""

    def _callback(idx, fix, outcome, detail=None):
        status = _OUTCOME_TO_STATUS.get(outcome)
        if status is None:
            return
        # For "fixed"/"reverted", the shared bisector supplies the dynamic
        # detail (retry note or test-failure summary). For "retained"/
        # "skipped" the shared bisector passes detail=None, so fall back
        # to the deep-mode default explanation.
        effective_detail = detail or _OUTCOME_DEFAULT_DETAIL.get(outcome)
        mark_finding_status(progress, fix, status, effective_detail)

    return _callback


def bisect_fixes(fixes, test_command, cwd, progress):
    """
    Incremental bisection: revert all fixes, then re-apply one by one,
    keeping passing fixes applied so subsequent fixes can depend on them.
    After the first pass, retry reverted fixes (they may depend on fixes
    that were applied later in the first pass).
    Returns (fixed_count, reverted_count, skipped_count).
    """
    print(f"{PREFIX} Bisecting {len(fixes)} fixes...")
    return _shared_bisect_fixes(
        fixes,
        test_command,
        cwd,
        run_tests_fn=run_tests,
        on_outcome=_make_bisect_outcome_callback(progress),
    )
