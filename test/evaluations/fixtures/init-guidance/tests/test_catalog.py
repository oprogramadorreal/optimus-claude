import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from catalog import lookup


class CatalogTests(unittest.TestCase):
    def test_exact_keys_and_caller_updates(self):
        invoices = {"AbC": 1, "abc": 2, " AbC ": 3}
        self.assertEqual(lookup(invoices, "AbC"), 1)
        self.assertEqual(lookup(invoices, "abc"), 2)
        self.assertEqual(lookup(invoices, " AbC "), 3)
        invoices["AbC"] = 4
        self.assertEqual(lookup(invoices, "AbC"), 4)
        self.assertIsNone(lookup(invoices, "missing"))
