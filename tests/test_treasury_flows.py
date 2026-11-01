"""Tests for scripts/treasury_flows.py on a simulated chain (no network).

Run: python -m unittest discover -s tests
"""
import base64
import json
import shutil
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lock_window as lw  # noqa: E402
import test_lock_window as tl  # noqa: E402
import treasury_flows as tf  # noqa: E402

Y = 10 ** 24
U = 10 ** 6
POOLS = sorted(tf.KNOWN_POOLS)
PRIVATE_NAME = "alice-person.near"  # must never appear in the public output


def b64(obj):
    return base64.b64encode(json.dumps(obj).encode()).decode()


def transfer(pid, to, amount, token="", status="Approved"):
    return {"id": pid, "submission_time": str(1_780_000_000 * lw.NS + pid), "status": status,
            "description": f"pay {to}",
            "kind": {"Transfer": {"token_id": token, "receiver_id": to, "amount": str(amount),
                                  "msg": None}}}


def call(pid, receiver, method, args=None, deposit=0, status="Approved"):
    return {"id": pid, "submission_time": str(1_780_000_000 * lw.NS + pid), "status": status,
            "description": "call",
            "kind": {"FunctionCall": {"receiver_id": receiver, "actions": [
                {"method_name": method, "args": b64(args or {}), "deposit": str(deposit),
                 "gas": "1"}]}}}


class PureTest(unittest.TestCase):
    def test_approved_between_uses_status_at_both_blocks(self):
        start = [{"id": 0, "status": "Approved"}, {"id": 1, "status": "InProgress"},
                 {"id": 2, "status": "Rejected"}]
        end = [{"id": 0, "status": "Approved"}, {"id": 1, "status": "Approved"},
               {"id": 2, "status": "Rejected"}, {"id": 3, "status": "Approved"},
               {"id": 4, "status": "Failed"}, {"id": 5, "status": "InProgress"}]
        self.assertEqual([p["id"] for p in tf.approved_between(start, end)], [1, 3])

    def test_flows_and_no_private_names(self):
        props = [
            transfer(1, tf.PAYMENTS, 100 * Y),
            transfer(2, PRIVATE_NAME, 5 * Y),
            transfer(3, "a" * 64, 2 * Y),
            transfer(4, tf.PAYMENTS, 250_000 * U, token=tf.USDC),
            call(5, "near-prime-public.poolv1.near", "unstake", {"amount": str(200 * Y)}),
            call(6, "nearai.pool.near", "deposit_and_stake", deposit=10 * Y),
            call(7, "near-prime-public.poolv1.near", "unstake_all"),
            call(8, "near-prime-public.poolv1.near", "withdraw_all"),
            call(9, tf.USDC, "ft_transfer", {"receiver_id": PRIVATE_NAME, "amount": str(7 * U)},
                 deposit=1),
            call(10, tf.WNEAR, "near_deposit", deposit=3 * Y),
        ]
        recs = [tf.record(p, POOLS) for p in props]
        f = tf.flows(recs)
        self.assertEqual(f["near_transferred_out"], 107 * Y)
        self.assertEqual(f["near_to_payments_account"], 100 * Y)
        self.assertEqual(f["near_to_others"], 7 * Y)
        self.assertEqual(f["near_out_recipients_other"], 2)
        self.assertEqual(f["usdc_transferred_out"], 250_007 * U)
        self.assertEqual(f["unstaked"], 200 * Y)
        self.assertEqual(f["unstake_all_calls"], 1)
        self.assertEqual(f["staked"], 10 * Y)
        self.assertEqual(f["withdraw_calls"], 1)
        self.assertEqual(f["deposits_to_non_pools"], 3 * Y + 1)
        text = json.dumps(recs)
        self.assertNotIn(PRIVATE_NAME, text)
        self.assertIn(tf.tag(PRIVATE_NAME), text)
        self.assertIn("near-prime-public.poolv1.near", text)  # infrastructure keeps its name

    def test_bridged_usdc_counts_and_equal_rows_are_kept(self):
        rows = [
            {"tx": "A", "height": 10, "ts": 1, "token": tf.WNEAR, "delta": -15 * Y,
             "receipt": "r1", "event": 0},
            {"tx": "A", "height": 10, "ts": 1, "token": tf.WNEAR, "delta": -15 * Y,
             "receipt": "r1", "event": 1},                       # same amount, other event
            {"tx": "A", "height": 10, "ts": 1, "token": tf.USDC_ETH, "delta": 60 * U,
             "receipt": "r2", "event": 0},
            {"tx": "A", "height": 10, "ts": 1, "token": tf.USDC_ETH, "delta": 60 * U,
             "receipt": "r2", "event": 0},                       # page overlap: drop
            {"tx": "B", "height": 11, "ts": 2, "token": tf.WNEAR, "delta": -1 * Y,
             "receipt": "r3", "event": 0},
            {"tx": "B", "height": 11, "ts": 2, "token": tf.USDT_NEAR, "delta": 2 * U,
             "receipt": "r3", "event": 1},
        ]
        sw = tf.swaps_from_rows(tf.unique_rows(rows))
        self.assertEqual([(s["tx"], s["wnear"], s["usdc"], s["usdt"]) for s in sw],
                         [("A", -30 * Y, 60 * U, 0), ("B", -1 * Y, 0, 2 * U)])

    def test_swaps_group_by_transaction(self):
        rows = [
            {"tx": "A", "height": 10, "ts": 1, "token": tf.WNEAR, "delta": -100 * Y},
            {"tx": "A", "height": 10, "ts": 1, "token": tf.USDC, "delta": 230 * U},
            {"tx": "B", "height": 11, "ts": 2, "token": tf.WNEAR, "delta": -5 * Y},  # payment
            {"tx": "C", "height": 12, "ts": 3, "token": tf.USDC, "delta": -9 * U},
            {"tx": "C", "height": 12, "ts": 3, "token": tf.WNEAR, "delta": 4 * Y},   # other way
        ]
        sw = tf.swaps_from_rows(rows)
        self.assertEqual([s["tx"] for s in sw], ["A"])
        self.assertEqual(sw[0]["usdc"], 230 * U)

    def test_mt_row_filters_other_accounts_and_fails_on_new_format(self):
        r = {"block": {"block_height": "5", "block_timestamp": "7"}, "token_id": "nep141:wrap.near",
             "delta_amount": "-3", "transaction_hash": "T", "affected_account_id": tf.PAYMENTS}
        self.assertEqual(tf.mt_row(r, tf.PAYMENTS)["token"], "wrap.near")
        self.assertIsNone(tf.mt_row(dict(r, affected_account_id="x.near"), tf.PAYMENTS))
        with self.assertRaises(SystemExit):
            tf.mt_row({"something": 1}, tf.PAYMENTS)


# ---------------------------------------------------------------- simulated run

END_DATE = date(2026, 11, 1)
END_TS = lw.midnight_ns(END_DATE)
END_H = tl.expected_boundary(END_TS)
CREATED = 208_500_000          # stake.dao appears here (late July in the fake time line)
FIRST_STAKE = 209_169_270
Y2026_H = tl.expected_boundary(lw.midnight_ns(date(2026, 1, 1)))
MID = 214_000_000              # between the two starts and the end


def proposals_at(h):
    """Owner DAO proposals as they look at height h."""
    props = [transfer(0, tf.PAYMENTS, 50 * Y)]                         # before 2026: approved
    if h >= 200_000_000:
        props.append(transfer(1, PRIVATE_NAME, 9 * Y))                 # 2026, before stake.dao
    if h >= MID:
        props += [call(2, "near-prime-public.poolv1.near", "unstake", {"amount": str(100 * Y)}),
                  transfer(3, tf.PAYMENTS, 80 * Y),
                  transfer(4, tf.PAYMENTS, 1000 * U, token=tf.USDC),
                  transfer(5, PRIVATE_NAME, 1 * Y, status="InProgress" if h < END_H else "Approved")]
    return props


def holdings(h):
    """(liquid, prime staked, prime unstaked, nearai staked) of the owner at height h."""
    if h < 200_000_000:
        return 60 * Y, 1000 * Y, 0, 0
    if h < MID:
        return 51 * Y, 1000 * Y, 0, 10 * Y
    return 51 * Y + 100 * Y - 80 * Y - 1 * Y, 900 * Y + 2 * Y, 0, 10 * Y + 1 * Y  # +rewards


class FakeTreasuryChain(tl.FakeChain):
    def _post(self, body):
        if body["method"] != "query":
            return super()._post(body)
        self.calls += 1
        p = body["params"]
        h = p["block_id"]

        def ok(value=None, **extra):
            res = {"block_height": h, "block_hash": f"H{h}"}
            if value is not None:
                res.update({"result": list(json.dumps(value).encode()), "logs": []})
            res.update(extra)
            return json.dumps({"jsonrpc": "2.0", "id": "treasury", "result": res}).encode()

        def err(name):
            return json.dumps({"jsonrpc": "2.0", "id": "treasury",
                               "error": {"name": "HANDLER_ERROR", "cause": {"name": name}}}).encode()

        if tl.skipped(h) or h > self.final_height:
            return err("UNKNOWN_BLOCK")
        acct = p["account_id"]
        if p["request_type"] == "view_account":
            if acct == tf.STAKE_DAO and h < CREATED:
                return err("UNKNOWN_ACCOUNT")
            amount = holdings(h)[0] if acct == tf.TREASURY else 2 * Y
            return ok(amount=str(amount), locked="0", code_hash="x", storage_usage=1)
        if p["request_type"] == "view_access_key_list":
            return ok(keys=[])
        args = json.loads(base64.b64decode(p["args_base64"]))
        m = p["method_name"]
        liquid, prime_s, prime_u, ai_s = holdings(h)
        if m == "get_proposals":
            props = proposals_at(h)
            return ok(props[args["from_index"]:args["from_index"] + args["limit"]])
        if m == "get_account_staked_balance":
            if acct == "nearai.pool.near" and h < 200_000_000:
                return err("UNKNOWN_ACCOUNT")  # pool did not exist yet
            return ok(str(prime_s if acct.startswith("near-prime") else ai_s))
        if m == "get_account_unstaked_balance":
            if acct == "nearai.pool.near" and h < 200_000_000:
                return err("UNKNOWN_ACCOUNT")
            return ok(str(prime_u if acct.startswith("near-prime") else 0))
        if m == "ft_balance_of":
            return ok(str(5 * U))
        if m == "mt_batch_balance_of":
            return ok(["0", str(3 * U), "0", "0", "0"])
        raise AssertionError(m)


def fake_nearblocks(url):
    rows = [  # one swap after stake.dao started, one in early 2026, one payment
        {"block": {"block_height": str(MID + 5), "block_timestamp": str(tl.ts(MID + 5))},
         "token_id": "nep141:wrap.near", "delta_amount": str(-90 * Y), "transaction_hash": "S2",
         "affected_account_id": tf.PAYMENTS},
        {"block": {"block_height": str(MID + 5), "block_timestamp": str(tl.ts(MID + 5))},
         "token_id": f"nep141:{tf.USDC}", "delta_amount": str(210 * U), "transaction_hash": "S2",
         "affected_account_id": tf.PAYMENTS, "involved_account_id": "solver.near"},
        {"block": {"block_height": "201000000", "block_timestamp": str(tl.ts(201_000_000))},
         "token_id": "nep141:wrap.near", "delta_amount": str(-50 * Y), "transaction_hash": "S1",
         "affected_account_id": tf.PAYMENTS},
        {"block": {"block_height": "201000000", "block_timestamp": str(tl.ts(201_000_000))},
         "token_id": f"nep141:{tf.USDC}", "delta_amount": str(90 * U), "transaction_hash": "S1",
         "affected_account_id": tf.PAYMENTS},
        {"block": {"block_height": str(MID + 9), "block_timestamp": "1"},
         "token_id": "nep141:wrap.near", "delta_amount": str(-3 * Y), "transaction_hash": "P1",
         "affected_account_id": tf.PAYMENTS, "involved_account_id": PRIVATE_NAME},
    ]
    if "next=" in url:
        return json.dumps({"data": [], "meta": {}}).encode()
    return json.dumps({"data": rows, "meta": {"next_page": "c2"}}).encode()


def setup_repo(tmp):
    data = Path(tmp) / "data"
    pages = data / "raw" / "nearblocks" / "stake_receipts_2026-11-01"
    pages.mkdir(parents=True)
    (pages / "page_001.json").write_text(json.dumps({"data": [
        {"predecessor_account_id": "x.near", "outcome": {"status": False},
         "block": {"block_height": str(FIRST_STAKE), "block_timestamp": str(tl.ts(FIRST_STAKE))}},
        {"predecessor_account_id": "y.near", "outcome": {"status": True},
         "block": {"block_height": str(FIRST_STAKE + 50),
                   "block_timestamp": str(tl.ts(FIRST_STAKE + 50))}}]}))
    window = data / "window.json"
    window.write_text(json.dumps({"boundaries": [{"height": END_H}]}))
    return data, window


class RunTest(unittest.TestCase):
    def test_run_verify_and_privacy(self):
        chain = FakeTreasuryChain(tl.final_height_at(END_TS + 3600 * lw.NS))
        with tempfile.TemporaryDirectory() as tmp:
            data, window = setup_repo(tmp)
            doc = tf.run(chain, data, window, get=fake_nearblocks, wait=0)
            out = data / tf.OUT_NAME
            out.write_text(json.dumps(doc), encoding="utf-8")

            w = doc["windows"]["since_stake_dao"]
            self.assertEqual(w["start_block"], CREATED)
            self.assertEqual(w["approved_proposal_ids"], [2, 3, 4, 5])
            f = w["owner_flows"]
            self.assertEqual(f["unstaked"], "100.000")
            self.assertEqual(f["near_transferred_out"], "81.000")
            self.assertEqual(f["near_to_payments_account"], "80.000")
            self.assertEqual(f["usdc_transferred_out"], "1000.00")
            # Holdings 1061 -> 983 (-78); 81 out => 3 NEAR came in (rewards).
            self.assertEqual(w["owner_total_near_change"], "-78.000")
            self.assertEqual(w["implied_inflows_near"], "3.000")
            s = w["payments_swaps_wnear_to_stablecoins"]
            self.assertEqual((s["count"], s["near_given"], s["usdc_received"]),
                             (1, "90.000", "210.00"))
            y = doc["windows"]["year_2026"]
            self.assertEqual(y["start_block"], Y2026_H)
            self.assertEqual(y["approved_proposal_ids"], [1, 2, 3, 4, 5])
            self.assertEqual(y["payments_swaps_wnear_to_stablecoins"]["count"], 2)
            self.assertEqual(doc["stake_dao_first_stake_receipt"]["height"], FIRST_STAKE)
            self.assertFalse(doc["stake_dao_first_stake_receipt"]["succeeded"])
            self.assertEqual(doc["owner_access_keys_at_end"], 0)
            self.assertIn("y2026_start/staked/nearai.pool.near", doc["missing_values"])
            self.assertEqual(w["owner_positions_end"]["payments_intents_usdc"], "3.00")
            self.assertEqual(w["owner_positions_end"]["payments_intents_usdt"], "0.00")

            # Nothing private in any public file.
            public = [out] + [data.parent / f["path"] for f in doc["raw_files"].values()
                              if not f["private"]]
            for p in public:
                self.assertNotIn(PRIVATE_NAME, p.read_text(encoding="utf-8"), p)
            self.assertTrue(any(f["private"] for f in doc["raw_files"].values()))

            self.assertEqual(tf.verify(out), ([], 0))
            self.assertEqual(tf.verify(out, archival=True, chain=chain)[0], [])

            # Without the private folder: public files still check, nothing recomputed.
            shutil.rmtree(data / "private")
            problems, missing = tf.verify(out)
            self.assertEqual(problems, [])
            self.assertGreater(missing, 0)

            # A changed public byte is caught.
            raw = next(data.parent / f["path"] for f in doc["raw_files"].values()
                       if not f["private"] and f["kind"] == "rpc")
            raw.write_bytes(raw.read_bytes().replace(b'"treasury"', b'"treasurx"'))
            self.assertTrue(any("sha256" in p for p in tf.verify(out)[0]))


if __name__ == "__main__":
    unittest.main()
