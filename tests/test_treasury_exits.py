"""Tests for scripts/treasury_exits.py on a simulated chain (no network).

Run: python -m unittest discover -s tests
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import burn  # noqa: E402
import daily  # noqa: E402
import test_burn as tb  # noqa: E402
import test_treasury_spend as tts  # noqa: E402
import treasury_exits as te  # noqa: E402
import treasury_spend as ts  # noqa: E402

Y = tb.Y


class FakeExitChain(tts.FakeTreasuryChain):
    def _post(self, body):
        if body["method"] == "EXPERIMENTAL_changes":
            self.calls += 1
            h = body["params"]["block_id"]
            return json.dumps({"jsonrpc": "2.0", "id": "exits", "result": {
                "block_hash": f"H{h}", "changes": [
                    {"cause": {"type": "receipt_processing", "receipt_hash": f"R{h}"},
                     "type": "account_update", "change": {"account_id": ts.ACCOUNT}}]}}).encode()
        return super()._post(body)


class TreasuryExitsTest(unittest.TestCase):
    def prepare(self, extra):
        burn.EPOCH_LENGTH = 100
        ts.ANCHOR_BACK = 150
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.data, _, _ = tb.make_data(tmp.name)
        burn.run(FakeExitChain(extra=extra), self.data / "window_t.json", self.data)
        ts.run_rule(FakeExitChain(extra=extra), self.data)
        ts.run_months(FakeExitChain(extra=extra), self.data, tts.MONTH_SPEC, step=50)
        return FakeExitChain(extra=extra)

    def test_finds_every_step_with_block_amount_and_cause(self):
        chain = self.prepare({1500: -2 * Y, 1600: -Y, 1696: -Y // 2})
        doc, problems = te.run(chain, self.data)
        self.assertEqual(problems, [])
        got = [(e["height"], e["amount_yocto"], e["cause"]["receipt_hash"]) for e in doc["exits"]]
        self.assertEqual(got, [(1500, str(2 * Y), "R1500"), (1600, str(Y), "R1600"),
                               (1696, str(Y // 2), "R1696")])
        self.assertEqual(doc["results"]["total_exits_near"], daily.near(Y * 7 // 2))
        self.assertLess(chain.calls, 400)

    def test_verify_offline_and_tampering(self):
        chain = self.prepare({1500: -2 * Y})
        doc, _ = te.run(chain, self.data)
        res, p = te.verify_exits(doc, self.data)
        self.assertEqual(p, [])
        self.assertEqual(res, doc["results"])
        f = self.data / "raw" / "treasury_spend" / "accounts" / "1500_treasury.near.json"
        f.write_bytes(f.read_bytes().replace(b'"locked"', b'"locked" '))
        _, p = te.verify_exits(doc, self.data)
        self.assertTrue(any("sha256" in x for x in p))

    def test_a_missing_step_is_caught_by_the_monthly_total(self):
        chain = self.prepare({1500: -2 * Y, 1600: -Y})
        doc, _ = te.run(chain, self.data)
        doc["exits"] = [e for e in doc["exits"] if e["height"] != 1600]
        _, p = te.verify_exits(doc, self.data)
        self.assertTrue(any("add up" in x for x in p), p)


if __name__ == "__main__":
    unittest.main()
