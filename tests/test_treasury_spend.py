"""Tests for scripts/treasury_spend.py on a simulated chain (no network).

Run: python -m unittest discover -s tests
"""
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import burn  # noqa: E402
import daily  # noqa: E402
import lock_window as lw  # noqa: E402
import test_burn as tb  # noqa: E402
import treasury_spend as ts  # noqa: E402

Y = tb.Y
T_BASE = lw.midnight_ns(date(2026, 1, 1))
SECONDS_PER_BLOCK = 288  # 300 blocks a day: block 1100 is 1 Jan 00:00, 1400 is 2 Jan, 1700 is 3 Jan
TREASURY0 = 100 * Y
SPEND_AT, SPEND = 1500, 2 * Y  # an outflow in the middle of the second "month"
MONTH_SPEC = [(date(2026, 1, 1), 1090), (date(2026, 1, 2), 1390), (date(2026, 1, 3), 1690)]


def treasury_at(h, extra):
    bal = TREASURY0
    for s, m in zip(tb.STARTS_REAL, tb.MINTED):
        if m and s <= h:
            bal += m // 10
    for at, amt in extra.items():
        if at <= h:
            bal += amt
    return bal


class FakeTreasuryChain(tb.FakeBurnChain):
    def __init__(self, extra=None, **kw):
        super().__init__(**kw)
        self.extra = {SPEND_AT: -SPEND} if extra is None else extra

    def _post(self, body):
        if body["method"] == "query":
            self.calls += 1
            p = body["params"]
            h = p["block_id"]
            if h not in tb.SUPPLY:
                return json.dumps({"error": {"cause": {"name": "UNKNOWN_BLOCK"}}}).encode()
            return json.dumps({"jsonrpc": "2.0", "id": "daily", "result": {
                "amount": str(treasury_at(h, self.extra)), "locked": "0", "block_height": h,
                "block_hash": f"H{h}"}}).encode()
        raw = super()._post(body)
        doc = json.loads(raw)
        if "result" in doc:
            h = doc["result"]["header"]["height"]
            doc["result"]["header"]["timestamp"] = T_BASE + (h - 1100) * SECONDS_PER_BLOCK * lw.NS
            raw = json.dumps(doc).encode()
        return raw


class TreasurySpendTest(unittest.TestCase):
    def setUp(self):
        burn.EPOCH_LENGTH = 100
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.data, self.w0, self.w1 = tb.make_data(tmp.name)
        _, problems = burn.run(FakeTreasuryChain(), self.data / "window_t.json", self.data)
        self.assertEqual(problems, [])

    def rule(self, **kw):
        return ts.run_rule(FakeTreasuryChain(**kw), self.data)

    def test_rule_holds_on_every_epoch_start(self):
        doc, problems = self.rule()
        self.assertEqual(problems, [])
        r = doc["results"]["rule"]
        self.assertEqual((r["epochs"], r["exact"], r["outside_rule"]), (5, 5, 0))
        self.assertEqual(r["max_deviation_yocto"], "0")
        self.assertEqual(r["rewards_near"], daily.near((9 + 7 + 8 + 6 + 5) * Y // 10))
        w = doc["results"]["window"]
        self.assertEqual(w["other_net_near"], daily.near(-SPEND))  # the outflow at 1500 is in the window

    def test_other_movement_in_an_epoch_start_block_is_shown(self):
        start = tb.STARTS_REAL[3]  # 1290: the treasury also receives 1 NEAR in that block
        doc, problems = self.rule(extra={start: Y})
        self.assertTrue(any(f"start {start}" in x for x in problems), problems)
        self.assertEqual(doc["results"]["rule"]["outside_rule"], 1)

    def test_months_net_of_inflows_and_outflows(self):
        doc, problems = self.rule()
        self.assertEqual(problems, [])
        doc, problems = ts.run_months(FakeTreasuryChain(), self.data, MONTH_SPEC, step=50)
        self.assertEqual(problems, [])
        m1, m2 = doc["results"]["months"]
        self.assertEqual(m1["epochs"], 2)  # starts 1106 and 1290
        self.assertEqual(m1["minted_near"], daily.near(15 * Y))
        self.assertEqual(m1["treasury_in_near"], daily.near(Y * 3 // 2))
        self.assertEqual(m1["other_net_near"], "0.000")
        self.assertEqual(m1["kept_share"], "1.000000")
        self.assertEqual(m2["epochs"], 2)  # starts 1403 and 1695
        self.assertEqual(m2["minted_near"], daily.near(11 * Y))
        self.assertEqual(m2["other_net_near"], daily.near(-SPEND))
        self.assertEqual(m2["balance_change_near"], daily.near(11 * Y // 10 - SPEND))
        total = doc["results"]["total"]
        self.assertEqual(total["other_net_near"], daily.near(-SPEND))
        self.assertEqual(m2["end"], "2026-01-03")

    def test_verify_offline_and_tampering(self):
        self.rule()
        doc, _ = ts.run_months(FakeTreasuryChain(), self.data, MONTH_SPEC, step=50)
        again, p = ts.compute(doc, self.data)
        self.assertEqual(p, [])
        self.assertEqual(again, doc["results"])
        f = next((self.data / "raw" / "treasury_spend").glob("blocks_*.json"))
        f.write_bytes(f.read_bytes().replace(b'"epochs"', b'"epochs" '))
        _, p = ts.compute(doc, self.data)
        self.assertTrue(any("sha256" in x for x in p))

    def test_a_forgotten_epoch_in_a_month_is_caught(self):
        self.rule()
        doc, _ = ts.run_months(FakeTreasuryChain(), self.data, MONTH_SPEC, step=50)
        rel = doc["months"][0]["blocks_file"]
        path = self.data.parent / rel
        content = json.loads(path.read_text(encoding="utf-8"))
        content["epochs"].pop(0)
        text = json.dumps(content, indent=1) + "\n"
        path.write_bytes(text.encode("utf-8"))
        doc["raw_files"][rel] = ts.sha256(text.encode("utf-8"))
        _, p = ts.compute(doc, self.data)
        self.assertTrue(any("previous epoch" in x for x in p), p)

    def test_months_resume_without_redoing_finished_ones(self):
        self.rule()
        ts.run_months(FakeTreasuryChain(), self.data, MONTH_SPEC[:2], step=50)
        chain = FakeTreasuryChain()
        doc, problems = ts.run_months(chain, self.data, MONTH_SPEC, step=50)
        self.assertEqual(problems, [])
        self.assertEqual(len(doc["results"]["months"]), 2)

    def test_months_refuse_to_run_when_the_rule_failed(self):
        self.rule(extra={tb.STARTS_REAL[3]: Y})
        with self.assertRaises(SystemExit):
            ts.run_months(FakeTreasuryChain(), self.data, MONTH_SPEC, step=50)


if __name__ == "__main__":
    unittest.main()
