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
        self.assertEqual(len(man["files"]), 5)
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

    def test_paths_add_up_and_relay_is_signed_by_intents(self):
        doc = json.loads((REPO / "data" / bq.OUT).read_text(encoding="utf-8"))
        for per in ("october", "november"):
            p = doc["intents_call_paths"][per]
            self.assertEqual(sum(v["calls"] for v in p["by_path"].values()), doc["intents_callers"][per]["calls"])
            self.assertEqual(p["by_path"]["relay"]["calls"] + p["by_path"]["callback"]["calls"],
                             doc["intents_call_outcomes"][per]["by_kind"]["intents_itself"]["calls"])
            self.assertEqual(p["by_path"]["relay"]["methods"], ["execute_intents"])
            self.assertLess(abs(p["signed_calls"] / p["q1_txns_to_intents"] - 1), 0.001)
        keys = json.loads((REPO / "data/raw/control/keys_intents.near.json").read_text(encoding="utf-8"))["result"]["keys"]
        for k in keys:   # the relay path: intents.near can sign only execute_intents on itself
            fc = k["access_key"]["permission"]["FunctionCall"]
            self.assertEqual((fc["receiver_id"], fc["method_names"]), ("intents.near", ["execute_intents"]))

    def test_kinds(self):
        self.assertEqual(bq.kind("intents.near"), "intents_itself")
        self.assertEqual(bq.kind("escrow.ai.near"), "near_ai_escrow")
        self.assertEqual(bq.kind("sol.omft.near"), "token_contracts")
        self.assertEqual(bq.kind("wrap.near"), "token_contracts")
        self.assertEqual(bq.kind("17208628f84f5d6ad33f0da3bbbeb27ffcb398eac501a31bd6ad2011e36133a1"), "token_contracts")
        self.assertEqual(bq.kind("someone.near"), "everyone_else")

    def test_median(self):
        self.assertEqual(bq.median([3, 1, 2]), 2)
        self.assertEqual(bq.median([4, 1, 2, 3]), 2.5)


if __name__ == "__main__":
    unittest.main()
