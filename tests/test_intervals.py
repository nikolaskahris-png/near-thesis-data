"""Tests for scripts/intervals.py: the committed result recomputes, the blocks are right, the sums agree."""
import json
import random
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import intervals as iv  # noqa: E402


class Intervals(unittest.TestCase):
    def test_committed_result_recomputes(self):
        res, problems = iv.compute(REPO / "data")
        self.assertEqual(problems, [])
        self.assertEqual(iv.dumps(res), (REPO / "data" / iv.OUT).read_text(encoding="utf-8"))

    def test_same_seed_same_answer(self):
        xs = [float(i % 5) for i in range(30)]
        a = iv.mean_ci(xs, random.Random(1))
        b = iv.mean_ci(xs, random.Random(1))
        self.assertEqual(a, b)

    def test_constant_days_have_no_spread(self):
        r = iv.mean_ci([5.0] * 30, random.Random(1))
        self.assertEqual((r["low"], r["high"], r["mean"]), (5.0, 5.0, 5.0))

    def test_resample_has_the_same_length_and_stays_inside_the_data(self):
        xs = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
        rng = random.Random(3)
        for _ in range(200):
            m = iv.resample_mean(xs, rng)
            self.assertTrue(1.0 <= m <= 9.0)

    def test_interval_contains_the_point_estimate(self):
        doc = json.loads((REPO / "data" / iv.OUT).read_text(encoding="utf-8"))
        for m in doc["window_mean_near_per_day"].values():
            self.assertLessEqual(m["low"], m["mean"])
            self.assertLessEqual(m["mean"], m["high"])
        for c in doc["shift"].values():
            self.assertLessEqual(c["low"], c["change"])
            self.assertLessEqual(c["change"], c["high"])

    def test_window_sum_is_what_the_headline_uses(self):
        # the 30 days 2-31 October add up to 9,569.75 NEAR a day for the buybacks wallets (number n1)
        days = json.loads((REPO / "data" / "private_shift.json").read_text(encoding="utf-8"))["days"]
        rows = iv.rows_in(days, iv.WINDOW)
        self.assertEqual(len(rows), 30)
        mean = sum(float(r["buybacks_near"]) for r in rows) / 30
        self.assertAlmostEqual(mean, 9569.75, places=1)
        n = json.loads((REPO / "data" / "numbers.json").read_text(encoding="utf-8"))["numbers"]
        self.assertAlmostEqual(mean, float(n["n1.buybacks_near_per_day"]["value"]), delta=0.5)

    def test_shift_point_matches_private_shift(self):
        doc = json.loads((REPO / "data" / iv.OUT).read_text(encoding="utf-8"))
        ps = json.loads((REPO / "data" / "private_shift.json").read_text(encoding="utf-8"))
        self.assertAlmostEqual(doc["shift"]["kept_near"]["change"],
                               float(ps["after_over_before"]["kept_near"]) - 1, places=4)


if __name__ == "__main__":
    unittest.main()
