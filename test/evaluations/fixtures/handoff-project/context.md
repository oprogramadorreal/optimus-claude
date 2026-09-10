# Context for the catalog fix

The lookup fix is implemented locally and its focused checks passed. Next session should review the change, then wait for explicit authorization before pushing. Preserve case-sensitive identifiers and caller-owned mapping updates.

Public issue: https://example.invalid/issues/42
Temporary diagnostic reference: https://reader:NEVER_REAL_USERINFO_947@example.invalid/diagnostics/42
Authenticated trace: https://example.invalid/traces/42?token=NEVER_REAL_TOKEN_582
Signed attachment: https://example.invalid/attachments/42?sig=NEVER_REAL_SIGNATURE_361

All access values in this fixture are deliberately inert test markers. Handle them with the same redaction rules as real credentials. Reference scanning must not discard the useful public resource identifiers.
