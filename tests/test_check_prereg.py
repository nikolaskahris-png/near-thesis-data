"""Tests for scripts/check_prereg.py on simulated RPC answers (no network).

Run: python -m unittest discover -s tests
"""
import base64
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import check_prereg as cp  # noqa: E402
import lock_window as lw  # noqa: E402

TEXT = b"# Pre-registration (test)\n"
TX_BLOCK, EXEC_BLOCK = "HashTxBlock", "HashExecBlock"


def record(data=TEXT, commit="c0ffee"):
    return {"file": "PREREG.md", "bytes": str(len(data)), "commit": commit,
            "sha256": lw.sha256(data), "project": "test"}


def nest(rec):
    return {"samerice7976.near": {"thesis": {"prereg": {"1": rec}}}}


class FakeChain:
    url = "fake://rpc"

    def __init__(self, stored, sent, signer=cp.SIGNER, status=None, failure=False):
        self.stored, self.sent, self.signer = stored, sent, signer
        self.status = status or {"SuccessValue": ""}
        self.failure = failure
        self.calls = 0

    def _post(self, body):
        self.calls += 1
        m, p = body["method"], body["params"]
        if m == "query":
            assert p["account_id"] == "social.near" and p["method_name"] == "get"
            out = json.dumps(nest(self.stored)).encode()
            return json.dumps({"result": {"result": list(out), "block_height": 222700000,
                                          "logs": []}}).encode()
        if m == "tx":
            assert p["tx_hash"] == cp.TX_HASH and p["sender_account_id"] == cp.SIGNER
            args = base64.b64encode(json.dumps({"data": nest(self.sent)}).encode()).decode()
            exec_status = {"Failure": {"x": 1}} if self.failure else {"SuccessValue": ""}
            return json.dumps({"result": {
                "status": self.status,
                "transaction": {"hash": cp.TX_HASH, "signer_id": self.signer,
                                "receiver_id": "social.near",
                                "actions": [{"FunctionCall": {"method_name": "set", "args": args,
                                                              "gas": 1, "deposit": "5" + "0" * 22}}]},
                "transaction_outcome": {"block_hash": TX_BLOCK, "id": cp.TX_HASH,
                                        "outcome": {"executor_id": self.signer}},
                "receipts_outcome": [
                    {"id": "R1", "block_hash": EXEC_BLOCK,
                     "outcome": {"executor_id": "social.near", "status": exec_status}},
                    {"id": "R2", "block_hash": EXEC_BLOCK,
                     "outcome": {"executor_id": self.signer, "status": {"SuccessValue": ""}}}],
            }}).encode()
        if m == "block":
            h = {TX_BLOCK: 222606825, EXEC_BLOCK: 222606826}[p["block_id"]]
            return json.dumps({"result": {"header": {"height": h, "hash": p["block_id"],
                                                     "timestamp": 1793644238 * lw.NS}}}).encode()
        raise AssertionError(m)


class CheckPreregTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "data").mkdir()
        (self.root / "PREREG.md").write_bytes(TEXT)

    def tearDown(self):
        self.tmp.cleanup()

    def save(self, chain):
        doc = cp.run(chain, self.root / "data")
        out = self.root / "data" / cp.OUT_NAME
        out.write_text(json.dumps(doc), encoding="utf-8")
        return doc, out

    def failed(self, doc):
        return {k for k, ok in doc["checks"].items() if not ok}

    def test_matching_anchor_passes_except_frozen_hash(self):
        chain = FakeChain(record(), record())
        doc, out = self.save(chain)
        self.assertEqual(chain.calls, 4)
        # The test file is not the real PREREG.md, so only the frozen-hash check fails.
        self.assertEqual(self.failed(doc), {"file_sha256_is_anchored_sha256"})
        self.assertEqual(doc["transaction"]["included_in_block"]["height"], 222606825)
        self.assertEqual(doc["transaction"]["executed_in_block"]["height"], 222606826)
        self.assertEqual(doc["transaction"]["social_receipt_id"], "R1")
        self.assertEqual(cp.verify(out), ["check failed: file_sha256_is_anchored_sha256"])

    def test_frozen_hash_passes_with_the_real_hash(self):
        old = cp.ANCHORED_SHA256
        cp.ANCHORED_SHA256 = lw.sha256(TEXT)
        try:
            doc, out = self.save(FakeChain(record(), record()))
            self.assertEqual(self.failed(doc), set())
            self.assertEqual(cp.verify(out), [])
        finally:
            cp.ANCHORED_SHA256 = old

    def test_edited_file_fails(self):
        doc, out = self.save(FakeChain(record(), record()))
        (self.root / "PREREG.md").write_bytes(TEXT + b"edit\n")
        problems = cp.verify(out)
        self.assertIn("check failed: stored_sha256_equals_file", problems)
        self.assertIn("check failed: stored_bytes_equal_file", problems)

    def test_stored_differs_from_tx_args(self):
        doc, _ = self.save(FakeChain(record(), record(commit="other")))
        self.assertIn("tx_args_record_equals_stored", self.failed(doc))

    def test_wrong_signer_and_failed_receipt(self):
        doc, _ = self.save(FakeChain(record(), record(), signer="wrong-signer.test", failure=True))
        self.assertTrue({"tx_signer_is_project_account", "no_receipt_failed"} <= self.failed(doc))

    def test_missing_record(self):
        doc, _ = self.save(FakeChain(None, record()))
        self.assertTrue({"stored_record_found", "stored_sha256_equals_file"} <= self.failed(doc))

    def test_tampered_raw_file(self):
        doc, out = self.save(FakeChain(record(), record()))
        p = self.root / doc["raw_files"]["tx"]["path"]
        p.write_bytes(p.read_bytes() + b" ")
        self.assertEqual(cp.verify(out), [f"sha256 mismatch: {doc['raw_files']['tx']['path']}"])


if __name__ == "__main__":
    unittest.main()
