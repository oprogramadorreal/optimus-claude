from .progress import generate_finding_id


def finding_key(item):
    """Extract the (file, line, category) key used to match findings and fixes."""
    return (item.get("file", ""), item.get("line"), item.get("category"))


def finding_matches(finding, fix):
    """Check if a finding matches a fix by file+line+category key."""
    return finding_key(finding) == finding_key(fix)


def mark_finding_status(progress, fix, status, detail):
    """Update a finding's status in the progress file."""
    # Try to find existing finding by file+line+category match
    for existing in progress["findings"]:
        if finding_matches(existing, fix):
            old_status = existing["status"]
            # Promote reverted -> attempt 2 -> persistent
            if status == "reverted — test failure" and old_status == "reverted — test failure":
                status = "reverted — attempt 2"
            elif status == "reverted — test failure" and old_status == "reverted — attempt 2":
                status = "persistent — fix failed"

            existing["status"] = status
            existing["iteration_last_attempted"] = progress["iteration"]["current"]
            existing.setdefault("status_history", []).append({
                "iteration": progress["iteration"]["current"],
                "status": status,
                "detail": detail,
            })
            return

    # Not found — add as new finding
    new_finding = {
        "id": generate_finding_id(progress),
        "file": fix.get("file", ""),
        "line": fix.get("line", 0),
        "end_line": fix.get("end_line", fix.get("line", 0)),
        "category": fix.get("category", ""),
        "guideline": fix.get("guideline", ""),
        "summary": fix.get("summary", ""),
        "fix_description": fix.get("fix_description", ""),
        "iteration_discovered": progress["iteration"]["current"],
        "iteration_last_attempted": progress["iteration"]["current"],
        "status": status,
        "status_history": [
            {
                "iteration": progress["iteration"]["current"],
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
    progress["findings"].append(new_finding)


def mark_all_fixed(progress, fixes):
    """Mark all fixes as fixed after tests passed."""
    for fix in fixes:
        mark_finding_status(progress, fix, "fixed", None)


def update_scope(progress, result):
    """
    Update scope_files for the next iteration.
    code-review: narrow to files with findings + newly modified files.
    refactor: keep the same scope (no narrowing).
    """
    if progress["skill"] == "refactor":
        return  # refactor keeps constant scope

    # code-review: narrow scope
    finding_files = set()
    for finding in progress["findings"]:
        if finding["status"] != "persistent — fix failed":
            finding_files.add(finding["file"])
    for fix in result.get("fixes_applied", []):
        finding_files.add(fix["file"])

    # Merge with existing scope
    current = set(progress["scope_files"]["current"])
    current.update(finding_files)
    progress["scope_files"]["current"] = sorted(current)
