"""Tests for scripts/daily.py on a simulated chain (no network).

Run: python -m unittest discover -s tests
"""
import base64
import csv
import json
import sys
import tempfile
import unittest
from datetime import date
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import daily  # noqa: E402
import lock_window as lw  # noqa: E402
from test_lock_window import FakeChain, final_height_at, H0  # noqa: E402

Y = 10 ** 24


def balance(acct, h):
    # Supply grows 1 NEAR per block in the fake header (10**33 + h yocto... scaled below);
    # buybacks gain 0.1 NEAR per block, fefunds 0.05, 1cs is constant.
    n = h - H0
    return {daily.BUYBACKS: 2_000_000 * Y + n * Y // 10,
            daily.FEFUNDS: 1_900_000 * Y + n * Y // 20,
            daily.ONECLICK: 5 * Y}[acct]


class FakeChainWithState(FakeChain):
    def _post(self, body):
        if body["method"] == "block":
            raw = json.loads(super()._post(body))
            if "result" in raw:  # supply: 1 NEAR per block
                h = raw["result"]["header"]["height"]
                raw["result"]["header"]["total_supply"] = str(1_300_000_000 * Y + (h - H0) * Y)
            return json.dumps(raw).encode()
        self.calls += 1
        p = body["params"]
        h = p["block_id"]
        if p["request_type"] == "view_account":
            res = {"amount": str(balance(p["account_id"], h)), "locked": "0",
                   "block_height": h, "block_hash": f"H{h}"}
        else:
            args = json.loads(base64.b64decode(p["args_base64"]))
            assert p["method_name"] == "mt_balance_of" and args["token_id"] == daily.WNEAR
            res = {"result": list(b'"0"'), "logs": [], "block_height": h}
        return json.dumps({"jsonrpc": "2.0", "id": "daily", "result": res}).encode()


class DailyTest(unittest.TestCase):
    def test_row_matches_hand_computation_and_verifies(self):
        d = date(2026, 11, 1)
        chain = FakeChainWithState(final_height_at(lw.midnight_ns(d) + 3600 * lw.NS))
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"
            doc, rows, problems, _ = daily.run(d, data, chain)
            self.assertEqual(problems, [])
            row = rows[0]
            blocks = doc["end"]["height"] - doc["start"]["height"]
            self.assertEqual(row["window_start"], "2026-10-02")
            # buybacks gain 0.1 per block, supply 1 per block -> exactly 0.1
            self.assertEqual(row["coverage_buybacks"], "0.100000")
            self.assertEqual(row["coverage_with_fe"], "0.150000")
            self.assertEqual(row["new_supply_per_day"], daily.near(blocks * Y // 30))
            self.assertEqual(row["flags"], "")
            # 1cs is constant in the fake chain, so it adds to the level but not the change
            self.assertEqual(row["buybacks_start"], daily.near(balance(daily.BUYBACKS, doc["start"]["height"]) + 5 * Y))

            # history.csv is rebuilt identically by --verify
            before = (data / "history.csv").read_text(encoding="utf-8")
            rows2, problems2 = daily.write_history(data)
            self.assertEqual(problems2, [])
            self.assertEqual((data / "history.csv").read_text(encoding="utf-8"), before)
            self.assertEqual(list(csv.DictReader(before.splitlines()))[0]["coverage_buybacks"],
                             "0.100000")

            # A changed raw balance is caught.
            f = data / "raw" / "accounts" / f"{doc['end']['height']}_{daily.BUYBACKS}.json"
            f.write_bytes(f.read_bytes().replace(b'"amount": "', b'"amount": "9'))
            _, problems3 = daily.write_history(data)
            self.assertTrue(any("sha256" in p for p in problems3))

    def test_near_formatting(self):
        self.assertEqual(daily.near(1_234_567_890 * 10 ** 15), "1.235")
        self.assertEqual(daily.near(-5 * 10 ** 23), "-0.500")
        self.assertEqual(daily.near(999_999_9 * 10 ** 17), "1.000")


if __name__ == "__main__":
    unittest.main()
