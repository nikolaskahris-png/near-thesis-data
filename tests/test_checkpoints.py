"""Buy's yearly checkpoints in numbers.json (lr.checkpoint.) are the floors scripts/rating.py applies on each 1 November."""
import json
import sys
import unittest
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import rating  # noqa: E402


class TestCheckpoints(unittest.TestCase):
    def setUp(self):
        self.n = json.loads((REPO / "data" / "numbers.json").read_text(encoding="utf-8"))["numbers"]

    def test_floors_are_rating_py_floors(self):
        th = {k: float(self.n[v]["value"]) for k, v in rating.THRESHOLD_KEYS.items()}
        for rule, gkey in (("A", "growth_without_hsp029"), ("B", "growth_with_hsp029")):
            for year in range(2027, 2031):
                d = date(year, 11, 1)
                factor = (1 + th[gkey]) ** ((d - rating.BASE_DATE).days / 365.25)   # as rating.py computes it
                self.assertAlmostEqual(float(self.n[f"lr.checkpoint.{rule}.{year}.near_per_day"]["value"]),
                                       th["base_near_per_day"] * factor, places=6)
                self.assertAlmostEqual(float(self.n[f"lr.checkpoint.{rule}.{year}.usd_per_day"]["value"]),
                                       th["base_usd_per_day"] * factor, places=6)

    def test_floors_rise_and_hsp029_lowers_them(self):
        for year in range(2027, 2031):
            a = float(self.n[f"lr.checkpoint.A.{year}.near_per_day"]["value"])
            b = float(self.n[f"lr.checkpoint.B.{year}.near_per_day"]["value"])
            self.assertLess(b, a)
            if year > 2027:
                self.assertGreater(a, float(self.n[f"lr.checkpoint.A.{year - 1}.near_per_day"]["value"]))


if __name__ == "__main__":
    unittest.main()
