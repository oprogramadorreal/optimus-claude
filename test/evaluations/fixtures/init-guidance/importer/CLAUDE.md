# Partner feed importer

This directory belongs to invoice-ledger.

Run `python -m unittest discover -s ../tests -p test_importer.py` here.

The partner pads IDs with spaces in transit. Strip this padding only at the
import boundary; preserve case and do not broaden the rule to catalog lookup.
See `../.claude/docs/testing.md` when changing tests.
