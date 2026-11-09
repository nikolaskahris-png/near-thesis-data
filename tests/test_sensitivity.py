"""Tests for scripts/sensitivity.py: the committed grid recomputes, and the rule's own thresholds are in it."""
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import rating  # noqa: E402
import sensitivity  # noqa: E402


class Sensitivity(unittest.TestCase):
    def test_committed_grid_recomputes(self):
        res, problems = sensitivity.compute(REPO / "data")
        self.assertEqual(problems, [])
        self.assertEqual(sensitivity.dumps(res), (REPO / "data" / sensitivity.OUT).read_text(encoding="utf-8"))

    def test_the_rule_itself_is_one_combination_and_matches_the_backtest(self):
        doc = json.loads((REPO / "data" / sensitivity.OUT).read_text(encoding="utf-8"))
        bt = {}
        with open(REPO / "data" / "backtest.csv", encoding="utf-8") as f:
            import csv
            bt = {r["month"]: r["rating"] for r in csv.DictReader(f)}
        rule = [r for r in doc["runs"] if r["kept_share_floor"] == "0.75" and r["usd_floor_x_april"] == "1"
                and r["rule_b"] == "as on chain" and r["growth_a"] == rating.thresholds(REPO / "data" / "numbers.json")["growth_without_hsp029"]]
        self.assertEqual(len(rule), 1)
        self.assertEqual(rule[0]["ratings"], bt)

    def test_threshold_is_restored(self):
        sensitivity.compute(REPO / "data")
        self.assertEqual(rating.KEPT_SHARE_MIN, rating.Fraction(3, 4))


if __name__ == "__main__":
    unittest.main()
