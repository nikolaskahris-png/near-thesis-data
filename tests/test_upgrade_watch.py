"""Tests for scripts/upgrade_watch.py on a simulated chain (no network).

Run: python -m unittest discover -s tests
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import upgrade_watch as uw  # noqa: E402

TOP = 1000
# producers a, b, c, d with stakes 50, 30, 15, 5; e is chunk-only (no blocks expected)
VALS = [("a.poolv1.near", 50, 10), ("b.poolv1.near", 30, 6), ("c.poolv1.near", 15, 3),
        ("d.poolv1.near", 5, 1), ("e.poolv1.near", 40, 0)]


def author(h):
    return ["a.poolv1.near", "b.poolv1.near", "c.poolv1.near"][h % 3]  # d never seen


def version(h, upgraded):
    return 87 if author(h) in upgraded else 86


class FakeChain:
    url = "fake://archival"

    def __init__(self, upgraded=("a.poolv1.near",)):
        self.upgraded, self.calls = set(upgraded), 0

    def block(self, h):
        return {"author": author(h), "header": {
            "height": h, "hash": f"H{h}", "prev_hash": f"H{h - 1}", "epoch_id": "E",
            "timestamp": 1793750400 * 10 ** 9, "latest_protocol_version": version(h, self.upgraded)}}

    def _post(self, body):
        self.calls += 1
        m, p = body["method"], body["params"]
        if m == "block":
            r = self.block(TOP if p.get("finality") else int(p["block_id"][1:]))
        elif m == "EXPERIMENTAL_protocol_config":
            r = {"protocol_version": 86, "protocol_upgrade_stake_threshold": [4, 5]}
        elif m == "validators":
            assert p == {"epoch_id": "E"}
            r = {"current_validators": [{"account_id": a, "stake": str(s * 10 ** 24),
                                         "num_expected_blocks": n} for a, s, n in VALS]}
        return json.dumps({"jsonrpc": "2.0", "id": "watch", "result": r}).encode()


class UpgradeWatchTest(unittest.TestCase):
    def run_once(self, data, upgraded=("a.poolv1.near",)):
        doc = uw.collect(FakeChain(upgraded), sample=30)
        doc["result"] = uw.compute(doc)
        uw.save(data, doc)
        return doc

    def test_shares_and_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            doc = self.run_once(data)
            r = doc["result"]
            self.assertEqual((r["blocks_sampled"], r["producers_seen"], r["block_producers"]), (30, 3, 4))
            self.assertEqual(r["signaling_share"], "0.500000")   # a: 50 of 100
            self.assertEqual(r["seen_share"], "0.950000")        # a+b+c, d unseen, e chunk-only
            self.assertTrue(all(r["checks"].values()))
            text = (data / "upgrade_watch" / "2026-11-04.json").read_text()
            self.assertNotIn("poolv1.near", text)                # no producer names stored
            self.assertEqual(uw.verify(data), ([], 1))
            self.run_once(data, upgraded=("a.poolv1.near", "b.poolv1.near"))  # same day: replaced
            rows = (data / "upgrade_watch.csv").read_text().splitlines()
            self.assertEqual(len(rows), 2)
            self.assertIn("0.800000", rows[1])
            self.assertEqual(uw.verify(data), ([], 1))

    def test_tampered_day_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            self.run_once(data)
            p = data / "upgrade_watch" / "2026-11-04.json"
            d = json.loads(p.read_text())
            d["producers"][0]["version"] = 99
            p.write_text(json.dumps(d))
            problems, _ = uw.verify(data)
            self.assertIn("2026-11-04.json: check failed: producer_versions_match_their_latest_block",
                          problems)


if __name__ == "__main__":
    unittest.main()
