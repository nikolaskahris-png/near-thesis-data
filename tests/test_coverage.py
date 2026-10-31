"""Tests for scripts/coverage.py on a simulated chain (no network).

Run: python -m unittest discover -s tests
"""
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import coverage  # noqa: E402
import daily  # noqa: E402
import lock_window as lw  # noqa: E402
from test_daily import FakeChainWithState  # noqa: E402
from test_lock_window import final_height_at  # noqa: E402


class CoverageTest(unittest.TestCase):
    def test_monthly_rows_match_hand_computation_and_verify(self):
        end = date(2026, 11, 1)
        chain = FakeChainWithState(final_height_at(lw.midnight_ns(end) + 3600 * lw.NS))
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"
            _out, doc, problems, _ = coverage.run(date(2026, 8, 1), end, data, chain)
            self.assertEqual(problems, [])
            self.assertEqual([r["month"] for r in doc["rows"]],
                             ["2026-08", "2026-09", "2026-10"])
            for r in doc["rows"]:  # 0.1 and 0.05 NEAR per block against 1 NEAR of supply
                self.assertEqual(r["coverage_buybacks"], "0.100000")
                self.assertEqual(r["coverage_with_fe"], "0.150000")
                self.assertEqual(r["flags"], "")
            self.assertEqual(doc["rows"][1]["window_start"], "2026-09-01")
            self.assertEqual(doc["rows"][1]["date"], "2026-10-01")
            _, p2 = coverage.verify(data)
            self.assertEqual(p2, [])
            b = doc["boundaries"][2]["height"]
            f = data / "raw" / "accounts" / f"{b}_{daily.FEFUNDS}.json"
            f.write_bytes(f.read_bytes().replace(b'"amount": "', b'"amount": "7'))
            _, p3 = coverage.verify(data)
            self.assertTrue(any("sha256" in p for p in p3))

    def test_month_starts(self):
        self.assertEqual(list(coverage.month_starts(date(2026, 11, 1), date(2027, 2, 1)))[-2:],
                         [date(2027, 1, 1), date(2027, 2, 1)])
        with self.assertRaises(SystemExit):
            list(coverage.month_starts(date(2026, 4, 2), date(2026, 6, 1)))


if __name__ == "__main__":
    unittest.main()
