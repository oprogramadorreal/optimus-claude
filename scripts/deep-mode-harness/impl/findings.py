from .constants import FAILURE_STATUSES, PERSISTENT_STATUS, normalize_path


def generate_finding_id(progress):
    """Generate the next finding ID (f-001, f-002, ...)."""
    return f"f-{len(progress['findings']) + 1:03d}"


def finding_key(item):
    """Extract the (file, line, category) key used to match findings and fixes."""
    return (
        normalize_path(item.get("file", "")),
        item.get("line"),
        item.get("category"),
    )


def finding_matches(finding, fix):
    """Check if a finding matches a fix by file+line+category key."""
    return finding_key(finding) == finding_key(fix)


def _truncate_failure_hint(detail, max_len=200):
    """Extract a compact failure hint from a test output summary."""
    if not detail:
        return None
    hint = detail.strip()
    if len(hint) > max_len:
        hint = hint[:max_len] + "..."
    return hint


def _new_finding_from_fix(fix, progress, status, detail):
    """Build a new finding record from a fix dict."""
    iteration = progress["iteration"]["current"]
    line = fix.get("line", 0)
    return {
        "id": generate_finding_id(progress),
        "file": normalize_path(fix.get("file", "")),
        "line": line,
        "end_line": fix.get("end_line", line),
        "category": fix.get("category", ""),
        "guideline": fix.get("guideline", ""),
        "summary": fix.get("summary", ""),
        "fix_description": fix.get("fix_description", ""),
        "iteration_discovered": iteration,
        "iteration_last_attempted": iteration,
        "status": status,
        "status_history": [
            {
                "iteration": iteration,
                "status": status,
                "detail": detail,
            }
        ],
        "agent": fix.get("agent", ""),
        "confidence": fix.get("confidence", ""),
        "severity": fix.get("severity", ""),
        "pre_edit_content": fix.get("pre_edit_content", ""),
        "post_edit_content": fix.get("post_edit_content", ""),
    }


def _escalate_revert_status(new_status, old_status):
    """Escalate repeated test-failure reverts: failure → attempt 2 → persistent."""
    if old_status == PERSISTENT_STATUS:
        return PERSISTENT_STATUS
    if new_status == "reverted — test failure":
        if old_status == "reverted — test failure":
            return "reverted — attempt 2"
        if old_status == "reverted — attempt 2":
            return PERSISTENT_STATUS
    return new_status


def mark_finding_status(progress, fix, status, detail):
    """Update a finding's status in the progress file."""
    # Try to find existing finding by file+line+category match
    for existing in progress["findings"]:
        if finding_matches(existing, fix):
            effective_status = _escalate_revert_status(status, existing["status"])

            existing["status"] = effective_status
            existing["iteration_last_attempted"] = progress["iteration"]["current"]
            existing.setdefault("status_history", []).append(
                {
                    "iteration": progress["iteration"]["current"],
                    "status": effective_status,
                    "detail": detail,
                }
            )
            # Store compact failure context for the next iteration's prompt
            if effective_status in FAILURE_STATUSES:
                existing["last_failure_hint"] = _truncate_failure_hint(detail)
            elif effective_status == "fixed":
                existing.pop("last_failure_hint", None)
            return

    # Not found — add as new finding
    new_finding = _new_finding_from_fix(fix, progress, status, detail)
    progress["findings"].append(new_finding)


def mark_all_fixed(progress, fixes):
    """Mark all fixes as fixed after tests passed."""
    for fix in fixes:
        mark_finding_status(progress, fix, "fixed", None)


def update_scope(progress, result):
    """
    Widen scope_files.current to include all files with non-persistent active
    findings and all newly modified files from this iteration.

    This persists the structural-neighbor expansion that the agents performed
    in this iteration (per the scope expansion rule in each skill's
    shared-constraints.md) so the next iteration can continue reviewing those
    related files without re-discovering them from scratch.
    """
    finding_files = set()
    for finding in progress["findings"]:
        if finding["status"] != PERSISTENT_STATUS:
            finding_files.add(finding["file"])
    for fix in result.get("fixes_applied", []):
        fix_file = normalize_path(fix.get("file", ""))
        if fix_file:
            finding_files.add(fix_file)

    # Merge with existing scope
    current = set(progress["scope_files"]["current"])
    current.update(finding_files)
    progress["scope_files"]["current"] = sorted(current)
