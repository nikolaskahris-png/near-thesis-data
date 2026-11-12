"""Tests for scripts/peers_rating.py: the decision order, the HYPE issuance rule, NEAR rated as rating.py rates it."""
import csv
import sys
import unittest
from decimal import Decimal
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import peers_rating as pr  # noqa: E402


class PeersRating(unittest.TestCase):
    def test_decision_order(self):
        self.assertEqual(pr.decide(True, True, Decimal(5)), "Avoid")      # a drain beats everything
        self.assertEqual(pr.decide(True, None, Decimal(1)), "Buy")
        self.assertEqual(pr.decide(True, None, Decimal("0.99")), "Hold")
        self.assertEqual(pr.decide(False, None, Decimal(5)), "Hold")     # no lock, no Buy
        self.assertEqual(pr.decide(True, None, None), "Hold")            # coverage unknown

    def test_hype_rewards_follow_the_docs(self):
        self.assertEqual(pr.hype_rewards(Decimal(400_000_000)), Decimal("9480000.0000"))
        # inversely proportional to the square root of stake: rewards grow with its square root
        r440 = pr.hype_rewards(Decimal(440_000_000))
        self.assertAlmostEqual(float(r440), 9_480_000 * (440 / 400) ** 0.5, delta=1)

    def test_no_new_tokens_is_not_a_division_error(self):
        self.assertEqual(pr.coverage(Decimal(5), Decimal(0)), Decimal("Infinity"))
        self.assertIsNone(pr.coverage(Decimal(0), Decimal(0)))
        self.assertIsNone(pr.coverage(None, Decimal(1)))

    def test_near_gets_what_rating_py_gives(self):
        res, problems = pr.compute(REPO / "data")
        self.assertEqual(problems, [])
        with open(REPO / "data" / "rating.csv", encoding="utf-8") as f:
            last = list(csv.DictReader(f))[-1]
        self.assertEqual(res["rows"]["near"]["rating"], "Hold")
        self.assertIn(last["rating"], ("Hold",))

    def test_only_a_lock_can_open_buy(self):
        res, _ = pr.compute(REPO / "data")
        for pid, r in res["rows"].items():
            if not r["gate1_lock"]:
                self.assertEqual(r["rating"], "Hold", pid)

    def test_committed_result_recomputes(self):
        res, problems = pr.compute(REPO / "data")
        self.assertEqual(problems, [])
        self.assertEqual(pr.dumps(res), (REPO / "data" / pr.OUT).read_text(encoding="utf-8"))

    def test_every_source_is_a_quoted_page(self):
        import quotes
        for inp in pr.INPUTS.values():
            for sid in inp["sources"]:
                self.assertIn(sid, quotes.SOURCES)


if __name__ == "__main__":
    unittest.main()
