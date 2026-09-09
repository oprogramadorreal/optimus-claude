# Catalog behavior

Catalog identifiers are case-sensitive public IDs. Both `AbC` and `abc` are valid distinct IDs; clients already store them. Do not normalize case or migrate stored keys. The caller owns the supplied mapping and may update it after construction. Lookup must observe those updates without mutating the mapping. Surrounding whitespace is transport noise and should be ignored during lookup. Unknown IDs return `None`.

This is a small standard-library Python module. Existing check: `python check.py`. No third-party dependencies or architecture changes are needed for this task.
