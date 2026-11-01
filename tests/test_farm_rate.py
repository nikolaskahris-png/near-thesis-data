"""Tests for scripts/farm_rate.py on simulated NearBlocks and archival answers (no network).

Run: python -m unittest discover -s tests
"""
import base64
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import farm_rate as fr  # noqa: E402

OLD, NEW = 3802570537683474, 7605141075366948
H = 217788180
MANAGER, OWNER = "manager.near", "owner-dao.sputnik-dao.near"


def page(rows):
    return json.dumps({"data": rows, "meta": {}}).encode()


def receipt(h, tx):
    return {"actions": [{"action": "FUNCTION_CALL", "method": "edit_price"}],
            "block": {"block_height": str(h), "block_timestamp": "1"},
            "outcome": {"status": True}, "predecessor_account_id": MANAGER,
            "receipt_id": "r" + tx, "receiver_account_id": "stake.dao", "transaction_hash": tx}


def txn(tx, signer, price, rate):
    args = {"metadata": {"max_amount": None, "farm_reward_rate": str(rate)}, "price_id": price}
    return json.dumps({"txns": [{"transaction_hash": tx, "signer_account_id": signer,
                                 "actions": [{"action": "FUNCTION_CALL", "method": "edit_price",
                                              "args": json.dumps(args)}]}]}).encode()


class FakeGet:
    def __init__(self, called_rate=NEW, signer=MANAGER):
        self.called_rate, self.signer = called_rate, signer

    def __call__(self, url):
        if "receipts" in url:
            return page([receipt(H, "tx1"), receipt(H + 500, "tx2")])
        if url.endswith("tx1"):
            return txn("tx1", self.signer, fr.FARM_PRICE, self.called_rate)
        return txn("tx2", self.signer, "price_other", 5)  # another price: ignored


class FakeChain:
    url = "fake://archival"

    def __init__(self):
        self.calls, self.raw = 0, {}

    def _post(self, body):
        self.calls += 1
        p = body["params"]
        h, m = p["block_id"], p["method_name"]
        if m == "get_farm_pool":
            res = {"price_id": fr.FARM_PRICE, "reward_rate": str(OLD if h < H + 3 else NEW),
                   "total_farm_shares": "1"}
        elif m == "get_validator":
            res = {"validator_id": fr.VALIDATOR, "catalog_manager_account_ids": [MANAGER]}
        else:
            res = OWNER
        return json.dumps({"result": {"result": list(json.dumps(res).encode()),
                                      "block_height": h}}).encode()

    def block(self, h):
        self.raw[h] = json.dumps({"result": {"header": {"height": h,
                                                        "timestamp": 1790691669243413391}}}).encode()
        return {}


class FarmRateTest(unittest.TestCase):
    def run_it(self, get=None):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        doc = fr.run(FakeChain(), root, get=get or FakeGet(), wait=0)
        return root, doc

    def test_units_per_year_are_exact(self):
        self.assertEqual(fr.units_per_near_year(OLD), fr.Fraction(3802570537683474 * 31557600,
                                                                 10 ** 24))
        self.assertEqual(fr.dec6(fr.units_per_near_year(OLD)), "0.120000")
        self.assertEqual(fr.dec6(fr.units_per_near_year(NEW)), "0.240000")

    def test_change_found_signer_checked_private_kept_out(self):
        root, doc = self.run_it()
        self.assertEqual(doc["edit_price_receipts_all_time"], 2)
        self.assertEqual(doc["farm_price_edits"], 1)       # the other price is not the farm
        self.assertEqual(doc["rate_changes"], 1)
        c = doc["changes"][0]
        self.assertEqual((c["units_per_near_year_before"], c["units_per_near_year_after"]),
                         ("0.120000", "0.240000"))
        self.assertEqual(c["ratio_after_before"], "2.000000")
        self.assertTrue(c["signer_is_catalog_manager"])
        self.assertFalse(c["signer_is_pool_owner"])
        public = (root / "data" / fr.OUT_NAME).read_text()
        self.assertNotIn(MANAGER, public)
        for f in doc["raw_files"].values():
            if not f["private"]:
                self.assertNotIn(MANAGER, (root / f["path"]).read_text())

    def test_verify_offline_with_and_without_private_files(self):
        root, _ = self.run_it()
        path = root / "data" / fr.OUT_NAME
        self.assertEqual(fr.verify(path), ([], 0))
        shutil.rmtree(root / "data" / "private")
        problems, missing = fr.verify(path)
        self.assertEqual(problems, [])
        self.assertGreater(missing, 0)
        d = json.loads(path.read_text())
        d["changes"][0]["rate_after"] = str(OLD)
        path.write_text(json.dumps(d))
        self.assertTrue(fr.verify(path)[0])

    def test_refuses_when_rate_after_is_not_the_called_rate(self):
        with self.assertRaises(SystemExit):
            self.run_it(get=FakeGet(called_rate=NEW + 1))


if __name__ == "__main__":
    unittest.main()
