# Data ownership

`catalog.py` reads the caller's mapping directly; the caller may update it after
the lookup function is imported. Do not cache a snapshot of the mapping.

The importer normalizes transport padding before an ID reaches the catalog.
Keep that behavior at the feed boundary: it is not a general catalog rule.
