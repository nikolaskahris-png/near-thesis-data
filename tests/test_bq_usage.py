"""Tests for scripts/bq_usage.py: the saved BigQuery results are intact, add up, and recompute."""
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import bq_usage as bq  # noqa: E402


class BqUsage(unittest.TestCase):
    def test_committed_result_recomputes(self):
        res, problems = bq.compute(REPO / "data")
        self.assertEqual(problems, [])
        self.assertEqual(bq.us.dumps(res), (REPO / "data" / bq.OUT).read_text(encoding="utf-8"))

    def test_every_saved_file_matches_its_sha256(self):
        _, problems, man = bq.load(REPO / "data")
        self.assertEqual(problems, [])
        self.assertEqual(len(man["files"]), 3)
        for meta in man["files"].values():
            self.assertTrue((REPO / meta["query"]).exists())

    def test_a_changed_byte_is_caught(self):
        res = json.loads((REPO / "data" / bq.MANIFEST).read_text(encoding="utf-8"))
        rel = "data/bq/q1_transactions.csv"
        raw = (REPO / rel).read_bytes()
        self.assertNotEqual(bq.lw.sha256(raw.replace(b"4294270", b"4294271", 1)), res["files"][rel]["sha256"])

    def test_callers_add_up_to_the_daily_calls(self):
        doc = json.loads((REPO / "data" / bq.OUT).read_text(encoding="utf-8"))
        for per in ("october", "november"):
            self.assertAlmostEqual(sum(doc["intents_callers"][per]["share"].values()), 1.0, places=5)

    def test_kinds(self):
        self.assertEqual(bq.kind("intents.near"), "intents_itself")
        self.assertEqual(bq.kind("escrow.ai.near"), "near_ai_escrow")
        self.assertEqual(bq.kind("sol.omft.near"), "token_contracts")
        self.assertEqual(bq.kind("wrap.near"), "token_contracts")
        self.assertEqual(bq.kind("someone.near"), "everyone_else")

    def test_median(self):
        self.assertEqual(bq.median([3, 1, 2]), 2)
        self.assertEqual(bq.median([4, 1, 2, 3]), 2.5)


if __name__ == "__main__":
    unittest.main()
