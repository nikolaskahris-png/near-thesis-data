"""Tests for scripts/backtest.py: the rating rules on April-October 2026, offline.

Run: python -m unittest discover -s tests
"""
import json
import shutil
import sys
import tempfile
import unittest
from datetime import date, timedelta
from fractions import Fraction
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import backtest  # noqa: E402
import rating  # noqa: E402
from test_rating import LATE, TH, series  # noqa: E402


class BacktestTest(unittest.TestCase):
    def test_saved_files_recompute(self):
        self.assertEqual(backtest.verify(REPO / "data"), [])

    def test_seven_months_and_their_ratings(self):
        (doc, rows), problems = backtest.compute(REPO / "data")
        self.assertEqual(problems, [])
        self.assertEqual([r["month"] for r in rows], [f"2026-{m:02d}" for m in range(4, 11)])
        s = doc["summary"]
        self.assertEqual(s["ratings"]["Hold"] + s["ratings"]["Buy"] + s["ratings"]["Avoid"], 7)
        self.assertEqual(s["rule_b_months"], 0)          # no lock declared: Buy cannot fire
        self.assertEqual(s["ratings"]["Buy"], 0)

    def test_previous_month(self):
        self.assertEqual(backtest.previous_month(date(2026, 5, 1)), date(2026, 4, 1))
        self.assertEqual(backtest.previous_month(date(2026, 1, 1)), date(2025, 12, 1))

    def test_avoid_compares_with_the_previous_month(self):
        # two calendar months that both fail test 2 (USD kept at or under the threshold): Avoid
        s = series(date(2026, 4, 1), date(2026, 6, 30), price=1)
        h = [{"date": d1.isoformat(), "window_start": d0.isoformat(), "buybacks_per_day": "100",
              "fefunds_per_day": "0", "coverage_buybacks": "0.001", "new_supply_per_day": "88000"}
             for d0, d1 in ((date(2026, 4, 1), date(2026, 5, 1)), (date(2026, 5, 1), date(2026, 6, 1)))]
        rows = rating.evaluate(h, s, TH, LATE, {}, {}, earlier_of=backtest.previous_month)
        self.assertEqual([r["rating"] for r in rows], ["Hold", "Avoid"])
        # the default (30 days earlier: 2 May) finds no earlier window for June
        rows = rating.evaluate(h, s, TH, LATE, {}, {})
        self.assertEqual(rows[1]["earlier_window"], "not in history")


if __name__ == "__main__":
    unittest.main()
