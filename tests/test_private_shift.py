"""Tests for scripts/private_shift.py: the committed result recomputes, and the periods are fixed."""
import json
import sys
import unittest
from datetime import date
from fractions import Fraction
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import private_shift as ps  # noqa: E402


class PrivateShift(unittest.TestCase):
    def test_periods_fixed_from_the_external_date(self):
        self.assertEqual(ps.BEFORE, (date(2026, 10, 2), date(2026, 10, 26)))
        self.assertEqual(ps.AFTER, (date(2026, 10, 27), date(2026, 11, 8)))

    def test_committed_result_recomputes(self):
        res, problems = ps.compute(REPO / "data")
        self.assertEqual(problems, [])
        self.assertEqual(ps.dumps(res), (REPO / "data" / ps.OUT).read_text(encoding="utf-8"))

    def test_means_are_the_days(self):
        doc = json.loads((REPO / "data" / ps.OUT).read_text(encoding="utf-8"))
        for name, (a, b) in (("before", ps.BEFORE), ("after", ps.AFTER)):
            rows = [r for r in doc["days"] if a.isoformat() <= r["date"] <= b.isoformat()]
            m = sum(Fraction(r["kept_near"]) for r in rows) / len(rows)
            self.assertAlmostEqual(float(m), float(doc["periods"][name]["kept_near_per_day"]), places=4)
            self.assertEqual(len(rows), doc["periods"][name]["days"])

    def test_three_wallets_are_the_sum(self):
        doc = json.loads((REPO / "data" / ps.OUT).read_text(encoding="utf-8"))
        for r in doc["days"]:
            self.assertLessEqual(abs(Fraction(r["kept_near"]) - Fraction(r["buybacks_near"]) - Fraction(r["front_end_near"])),
                                 Fraction(2, 10 ** 6))   # each is rounded to 6 places

    def test_tideline_date_is_one_of_the_cuts_and_equals_the_main_result(self):
        doc = json.loads((REPO / "data" / ps.OUT).read_text(encoding="utf-8"))
        cut = {c["cut"]: c for c in doc["cut_dates"]}[ps.AFTER[0].isoformat()]
        self.assertEqual(cut["kept_near_after_over_before"], doc["after_over_before"]["kept_near"])
        self.assertEqual(cut["revenue_near_after_over_before"], doc["after_over_before"]["revenue_near"])


if __name__ == "__main__":
    unittest.main()
