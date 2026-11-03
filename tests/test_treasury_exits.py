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
import privacy  # noqa: E402
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


IMPLICIT = "ab" * 32


def tx_answer(tx_hash, transfers):
    """A minimal EXPERIMENTAL_tx_status answer: treasury.near confirms, the contract pays out."""
    receipts = [{"predecessor_id": ts.ACCOUNT, "receiver_id": ts.ACCOUNT, "receipt_id": "R0",
                 "receipt": {"Action": {"actions": [{"FunctionCall": {"method_name": "confirm",
                                                                      "deposit": "0"}}]}}}]
    outcomes = [{"id": "R0", "outcome": {"status": {"SuccessValue": ""}}}]
    for i, (to, dep, ok) in enumerate(transfers, 1):
        receipts.append({"predecessor_id": ts.ACCOUNT, "receiver_id": to, "receipt_id": f"R{i}",
                         "receipt": {"Action": {"actions": [{"Transfer": {"deposit": str(dep)}}]}}})
        outcomes.append({"id": f"R{i}", "outcome": {"status": {"SuccessValue": ""} if ok else
                                                    {"Failure": {}}}})
    receipts.append({"predecessor_id": "system", "receiver_id": ts.ACCOUNT, "receipt_id": "RF",
                     "receipt": {"Action": {"actions": [{"Transfer": {"deposit": "5"}}]}}})
    return json.dumps({"jsonrpc": "2.0", "id": "exits", "result": {
        "transaction": {"hash": tx_hash, "signer_id": ts.ACCOUNT},
        "receipts": receipts, "receipts_outcome": outcomes}}).encode()


class RecipientsTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        gas = 3 * 10 ** 22
        answers = {"T1": [("ecotreasury4.multisignature.near", 49 * 10 ** 29, True)],
                   "T2": [(IMPLICIT, 5 * 10 ** 30, True)],
                   "T3": [("someone.near", 3 * Y, False)],
                   "T4": [("foundation.near", Y, True)]}
        self.doc = {"exits": [], "tx_files": {}}
        for n, (h, tr) in enumerate(answers.items()):
            rel = te.tx_rel(h)
            (self.base / rel).parent.mkdir(parents=True, exist_ok=True)
            raw = tx_answer(h, tr)
            (self.base / rel).write_bytes(raw)
            self.doc["tx_files"][h] = {"path": rel, "sha256": te.sha256(raw), "private": True}
            self.doc["exits"].append({"height": 100 + n, "cause": {"tx_hash": h},
                                      "amount_yocto": str(sum(d for _, d, _ in tr) + gas),
                                      "amount_near": "x"})
        privacy.write_redacted(self.base, self.doc["tx_files"], te.project_tx)

    def test_names_multisig_tags_others_and_explains_each_fall(self):
        per, summary, problems = te.recipients_of(self.doc, self.base)
        self.assertEqual(problems, [])
        self.assertEqual(per[100][0]["account"], "ecotreasury4.multisignature.near")
        self.assertEqual(per[101][0]["account"], privacy.tag(IMPLICIT))
        self.assertEqual(per[102][0]["account"], privacy.tag("someone.near"))
        self.assertEqual(per[103][0]["account"], "foundation.near")
        self.assertFalse(per[102][0]["ok"])
        self.assertEqual([s["account"] for s in summary],
                         [privacy.tag(IMPLICIT), "ecotreasury4.multisignature.near", "foundation.near"])
        public = b"".join((self.base / f["redacted"]["path"]).read_bytes()
                          for f in self.doc["tx_files"].values())
        self.assertNotIn(IMPLICIT.encode(), public)
        self.assertNotIn(b"someone.near", public)

    def test_a_fall_the_transfers_do_not_explain_is_caught(self):
        self.doc["exits"][0]["amount_yocto"] = str(int(self.doc["exits"][0]["amount_yocto"]) + 2 * Y)
        _, _, problems = te.recipients_of(self.doc, self.base)
        self.assertTrue(any("do not explain" in x for x in problems), problems)

    def test_redacted_copies_recompute_without_the_originals(self):
        for f in self.doc["tx_files"].values():
            (self.base / f["path"]).unlink()
        p, absent = privacy.check_files(self.base, self.doc["tx_files"], te.project_tx)
        self.assertEqual((p, absent), ([], 4))
        per, _, problems = te.recipients_of(self.doc, self.base)
        self.assertEqual(problems, [])
        self.assertEqual(len(per), 4)


if __name__ == "__main__":
    unittest.main()
