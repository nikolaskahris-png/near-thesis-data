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

            # --verify compares and writes nothing: a row edited by hand is caught.
            (data / "history.csv").write_text(before.replace("0.100000", "0.250000", 1), encoding="utf-8", newline="")
            _, problems4 = daily.verify_history(data)
            self.assertTrue(any("history.csv differs" in p for p in problems4))
            self.assertIn("0.250000", (data / "history.csv").read_text(encoding="utf-8"))
            (data / "history.csv").write_text(before, encoding="utf-8", newline="")
            self.assertEqual(daily.verify_history(data)[1], [])

            # A changed raw balance is caught.
            f = data / "raw" / "accounts" / f"{doc['end']['height']}_{daily.BUYBACKS}.json"
            f.write_bytes(f.read_bytes().replace(b'"amount": "', b'"amount": "9'))
            _, problems3 = daily.write_history(data)
            self.assertTrue(any("sha256" in p for p in problems3))

    def test_wnear_inside_intents_counts_as_held(self):
        d = date(2026, 11, 1)

        class WithWnear(FakeChainWithState):
            def _post(self, body):
                p = body.get("params", {})
                if p.get("request_type") == "call_function" and p["block_id"] == self.end_h:
                    args = json.loads(base64.b64decode(p["args_base64"]))
                    if args["account_id"] == daily.BUYBACKS:
                        self.calls += 1
                        res = {"result": list(b'"3000000000000000000000000"'), "logs": [],
                               "block_height": p["block_id"]}
                        return json.dumps({"jsonrpc": "2.0", "id": "daily", "result": res}).encode()
                return super()._post(body)

        plain = FakeChainWithState(final_height_at(lw.midnight_ns(d) + 3600 * lw.NS))
        with tempfile.TemporaryDirectory() as tmp:
            doc, rows, _, _ = daily.run(d, Path(tmp) / "data", plain)
        chain = WithWnear(final_height_at(lw.midnight_ns(d) + 3600 * lw.NS))
        chain.end_h = doc["end"]["height"]
        with tempfile.TemporaryDirectory() as tmp:
            _, rows2, problems, _ = daily.run(d, Path(tmp) / "data", chain)
        self.assertEqual(problems, [])
        blocks = doc["end"]["height"] - doc["start"]["height"]
        self.assertEqual(rows2[0]["coverage_buybacks"],
                         daily.ratio(blocks * Y // 10 + 3 * Y, blocks * Y))
        self.assertIn("buybacks_holds_wnear_in_intents", rows2[0]["flags"])
        self.assertEqual(rows[0]["coverage_buybacks"], "0.100000")

    def test_near_formatting(self):
        self.assertEqual(daily.near(1_234_567_890 * 10 ** 15), "1.235")
        self.assertEqual(daily.near(-5 * 10 ** 23), "-0.500")
        self.assertEqual(daily.near(999_999_9 * 10 ** 17), "1.000")


class LockTest(unittest.TestCase):
    """Condition (b): NEAR moved to a declared lock after the declaration stays kept; what the lock held
    when declared is a baseline, never kept (judge #9, finding 1); sealed() reads (b) from the chain
    (no contract, no keys), per window (judge #9, finding 2)."""

    LOCK = "lock.test"
    MOVED = 500_000 * Y
    HELD = 1_000_000 * Y     # what the lock already holds when it is declared

    def chain(self, d, end_h=None, moved=0, keys=(), code_hash=daily.EMPTY_CODE_HASH):
        lock, held = self.LOCK, self.HELD

        class Lock(FakeChainWithState):
            def _post(self, body):
                p = body.get("params", {})
                if body["method"] == "query" and p.get("account_id") in (lock, daily.BUYBACKS) \
                        and p.get("request_type") in ("view_account", "view_access_key_list"):
                    h, acct = p["block_id"], p["account_id"]
                    at_end = end_h is not None and h == end_h
                    self.calls += 1
                    if p["request_type"] == "view_access_key_list":
                        res = {"keys": [{"public_key": k, "access_key": {"nonce": 0, "permission": "FullAccess"}}
                                        for k in keys], "block_height": h, "block_hash": f"H{h}"}
                    else:
                        amount = (held + (moved if at_end else 0)) if acct == lock else \
                            balance(acct, h) - (moved if at_end else 0)
                        res = {"amount": str(amount), "locked": "0", "code_hash": code_hash,
                               "block_height": h, "block_hash": f"H{h}"}
                    return json.dumps({"jsonrpc": "2.0", "id": "daily", "result": res}).encode()
                return super()._post(body)
        return Lock(final_height_at(lw.midnight_ns(d) + 3600 * lw.NS))

    def with_lock(self, since, fn):
        old = dict(daily.LOCKS)
        daily.LOCKS.clear()
        daily.LOCKS.update({self.LOCK: since})
        try:
            return fn()
        finally:
            daily.LOCKS.clear()
            daily.LOCKS.update(old)

    def base(self, d):
        with tempfile.TemporaryDirectory() as tmp:
            doc, rows, _, _ = daily.run(d, Path(tmp) / "data", FakeChainWithState(
                final_height_at(lw.midnight_ns(d) + 3600 * lw.NS)))
            return rows[0]["coverage_buybacks"], doc["end"]["height"]

    def test_move_after_the_declaration_keeps_coverage(self):
        d = date(2026, 11, 1)
        base, end_h = self.base(d)

        def go():
            with tempfile.TemporaryDirectory() as tmp:
                data = Path(tmp) / "data"
                _, rows, problems, _ = daily.run(d, data, self.chain(d, end_h, moved=self.MOVED))
                self.assertEqual(problems, [])
                self.assertEqual(rows[0]["coverage_buybacks"], base)
                self.assertNotIn("buybacks_balance_fell", rows[0]["flags"])
                self.assertEqual(daily.verify_history(data)[1], [])
                self.assertEqual(daily.sealed(data), {"2026-11-01": [self.LOCK]})
        self.with_lock(date(2026, 10, 2), go)          # declared on the window's first day

    def test_what_a_lock_holds_when_declared_is_not_kept(self):
        d = date(2026, 11, 1)
        base, _ = self.base(d)

        def go():
            with tempfile.TemporaryDirectory() as tmp:
                data = Path(tmp) / "data"
                # declared on the window's last day, already holding 1,000,000 NEAR: no phantom inflow
                _, rows, problems, _ = daily.run(d, data, self.chain(d))
                self.assertEqual(problems, [])
                self.assertEqual(rows[0]["coverage_buybacks"], base)
        self.with_lock(d, go)

    def test_a_lock_with_a_key_or_a_contract_is_not_sealed(self):
        d = date(2026, 11, 1)
        for kw in ({"keys": ["ed25519:K"]}, {"code_hash": "E8jZ1giWcVrps8PcV75ATauu6gFRkcwjNtKp7NKmipZG"}):
            def go():
                with tempfile.TemporaryDirectory() as tmp:
                    data = Path(tmp) / "data"
                    daily.run(d, data, self.chain(d, **kw))
                    self.assertEqual(daily.sealed(data), {"2026-11-01": []})
            self.with_lock(date(2026, 10, 2), go)

    def test_no_lock_declared_means_no_rule_b(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"
            d = date(2026, 11, 1)
            daily.run(d, data, FakeChainWithState(final_height_at(lw.midnight_ns(d) + 3600 * lw.NS)))
            self.assertEqual(daily.sealed(data), {"2026-11-01": []})


if __name__ == "__main__":
    unittest.main()
