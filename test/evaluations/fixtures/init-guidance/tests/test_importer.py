import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from importer.feed import invoice_id


class ImporterTests(unittest.TestCase):
    def test_feed_padding_only(self):
        self.assertEqual(invoice_id(" AbC "), "AbC")
        self.assertEqual(invoice_id("abc"), "abc")
