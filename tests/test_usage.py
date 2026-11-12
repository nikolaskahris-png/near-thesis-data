"""Tests for scripts/usage.py: the committed result recomputes; the shift test and the lags behave."""
import random
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import usage as us  # noqa: E402


class Usage(unittest.TestCase):
    def test_committed_result_recomputes(self):
        res, problems = us.compute(REPO / "data")
        self.assertEqual(problems, [])
        self.assertEqual(us.dumps(res), (REPO / "data" / us.OUT).read_text(encoding="utf-8"))

    def test_lag_pairs_x_before_y(self):
        x, y = [1, 2, 3, 4, 5], [10, 20, 30, 40, 50]
        self.assertEqual(us.lagged(x, y, 2), ([1, 2, 3], [30, 40, 50]))

    def test_a_planted_lead_is_found(self):
        rng = random.Random(7)
        x = [rng.gauss(0, 1) for _ in range(52)]
        y = [0.0, 0.0] + [v + rng.gauss(0, 0.3) for v in x[:-2]]     # y follows x two weeks later
        k, c, _ = us.best_lag(x, y)
        self.assertEqual(k, 2)
        self.assertGreater(c, 0.8)
        self.assertLess(us.shift_test(x, y, random.Random(1)), 0.01)

    def test_noise_is_not_a_lead(self):
        rng = random.Random(3)
        x = [rng.gauss(0, 1) for _ in range(52)]
        y = [rng.gauss(0, 1) for _ in range(52)]
        self.assertGreater(us.shift_test(x, y, random.Random(1)), 0.05)


if __name__ == "__main__":
    unittest.main()
