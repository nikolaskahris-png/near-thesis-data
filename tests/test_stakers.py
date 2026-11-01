"""Tests for scripts/stakers.py on a simulated chain and API (no network).

Run: python -m unittest discover -s tests
"""
import base64
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lock_window as lw  # noqa: E402
import stakers  # noqa: E402
from test_lock_window import FakeChain, final_height_at  # noqa: E402

Y = 10 ** 24
# account -> NEAR staked (None = never entered, 0 = left)
STATE = {"big.near": 1_000_000, "a.near": 100_000, "b.near": 50_000, "c.near": 50,
         "d.near": 20, "e.near": 0, "late.near": None}
for i in range(10):
    STATE[f"s{i}.near"] = 100 + i
LOCKS = [{"account_id": "a.near", "status": "Active", "amount_near": str(50 * Y),
          "start_ns": str(1), "end_ns": str(1 + 30 * 86400 * 10 ** 9)},
         {"account_id": "x.near", "status": "UnlockRequested", "amount_near": str(500 * Y),
          "end_ns": str(10 ** 30)},
         {"account_id": "y.near", "status": "Active", "amount_near": str(2000 * Y),
          "start_ns": str(10 ** 30 - 31 * 86400 * 10 ** 9), "end_ns": str(10 ** 30)}]


class FakeStakeDao(FakeChain):
    def __init__(self, final_height, state, extra_total=0):
        super().__init__(final_height)
        self.state = state
        self.extra_total = extra_total

    def _post(self, body):
        if body["method"] == "block":
            return super()._post(body)
        self.calls += 1
        p = body["params"]
        args = json.loads(base64.b64decode(p["args_base64"]))
        m = p["method_name"]
        if m == "get_farm_pool":
            total = sum(v for v in self.state.values() if v) * Y + self.extra_total
            res = {"total_farm_shares": str(total), "reward_rate": "7605141075366948"}
        elif m == "get_farm_position" and args["account_id"] == "panic.near":
            return json.dumps({"jsonrpc": "2.0", "id": "stakers", "error": {
                "name": "HANDLER_ERROR", "cause": {"name": "CONTRACT_EXECUTION_ERROR",
                                                   "info": {"vm_error": "Smart contract panicked: no position"}},
                "data": "panicked"}}).encode()
        elif m == "get_farm_position":
            v = self.state.get(args["account_id"])
            res = None if v is None else {"staked_near_amount": str(v * Y),
                                          "status": "Active" if v else "Closed"}
        elif m == "get_locks":
            res = LOCKS[args["from_index"]:args["from_index"] + args["limit"]]
        out = {"result": list(json.dumps(res).encode()), "logs": [], "block_height": p["block_id"]}
        return json.dumps({"jsonrpc": "2.0", "id": "stakers", "result": out}).encode()


def fake_pages(accounts):
    half = len(accounts) // 2
    pages = [
        {"data": [{"predecessor_account_id": a} for a in accounts[:half]],
         "meta": {"next_page": "CURSOR2"}},
        {"data": [{"predecessor_account_id": a} for a in accounts[half:]], "meta": {}},
    ]
    calls = []

    def get(url):
        calls.append(url)
        return json.dumps(pages[1 if "CURSOR2" in url else 0]).encode()
    return get, calls


class StakersTest(unittest.TestCase):
    def run_snapshot(self, listed, extra_total=0):
        d = date(2026, 11, 1)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        data = Path(tmp.name) / "data"
        get, calls = fake_pages(listed)
        acc = stakers.discover(data, "t", get=get, wait=0)
        self.assertEqual(len(calls), 2)
        chain = FakeStakeDao(final_height_at(lw.midnight_ns(d) + 3600 * lw.NS), STATE, extra_total)
        snap = stakers.snapshot(chain, d, acc, data)
        return data, snap

    def test_numbers(self):
        data, snap = self.run_snapshot(sorted(STATE))
        st, problems = stakers.compute(snap, data)
        self.assertEqual(problems, [])
        self.assertEqual(st["stakers_active"], 15)
        self.assertEqual(st["stakers_ever"], 16)   # late.near never entered
        self.assertEqual(st["stakers_left"], 1)    # e.near
        self.assertEqual(st["largest_account"], stakers.tag("big.near"))
        self.assertEqual(st["private_check"], "recomputed")
        total = 1_000_000 + 100_000 + 50_000 + 50 + 20 + sum(100 + i for i in range(10))
        self.assertEqual(st["largest_share"], f"{1_000_000 / total:.6f}")
        self.assertEqual(st["outside_top10_accounts"], 5)
        # outside top 10: 101, 100, 50, 20 ... sorted desc: 1M,100K,50K,109..103 | 102,101,100,50,20
        self.assertEqual(st["outside_top10_median_near"], "100.000")
        self.assertEqual(st["accounts_under_100_near"], 2)
        self.assertEqual(st["agents_locks"], 3)
        self.assertEqual(st["agents_lock_accounts"], 3)
        self.assertEqual(st["agents_locks_past_end"], 1)          # a.near ended long ago
        self.assertEqual(st["farm_or_active_lock_accounts"], 16)  # a.near is in both, + y.near
        self.assertEqual(st["farm_or_any_lock_accounts"], 17)     # + x.near
        self.assertEqual(st["agents_locks_active"], 2)
        self.assertEqual(st["agents_locks_unlock_requested"], 1)
        self.assertEqual(st["agents_locks_active_within_term"], 1)  # y.near only
        self.assertEqual(st["agents_locks_near"], "2550.000")
        self.assertEqual(st["agents_locks_active_near"], "2050.000")
        self.assertEqual(st["agents_active_lock_near_vs_farm"], f"{2050 / total:.6f}")
        self.assertEqual(st["agents_locks_at_50_near"], 1)
        self.assertEqual(st["farm_units_per_near_year"], "0.240000")
        self.assertEqual(st["largest_units_per_day"], "657.084189")  # 1,000,000 NEAR
        self.assertEqual((st["agents_lock_days_min"], st["agents_lock_days_max"]),
                         ("30.00", "31.00"))           # x.near has no start: not counted
        results, problems = stakers.verify_all(data)
        self.assertEqual(problems, [])
        self.assertEqual(results[0]["stakers_active"], 15)

    def test_contract_error_counts_as_no_position(self):
        data, snap = self.run_snapshot(sorted(list(STATE) + ["panic.near"]))
        st, problems = stakers.compute(snap, data)
        self.assertEqual(problems, [])
        self.assertEqual(st["stakers_active"], 15)
        self.assertEqual(st["accounts_without_position_contract_error"], 1)
        self.assertIn("panicked", st["contract_error_example"])

    def test_missing_account_fails(self):
        listed = sorted(a for a in STATE if a != "b.near")
        data, snap = self.run_snapshot(listed)
        _, problems = stakers.compute(snap, data)
        self.assertTrue(any("incomplete" in p for p in problems))

    def test_tampered_page_fails_verify(self):
        data, _ = self.run_snapshot(sorted(STATE))
        page = next((data / "private" / "nearblocks").rglob("page_001.json"))
        page.write_bytes(page.read_bytes().replace(b"a.near", b"z.near"))
        _, problems = stakers.verify_all(data)
        self.assertTrue(problems)

    def test_public_files_name_no_account(self):
        data, snap = self.run_snapshot(sorted(STATE))
        public = [p for p in data.rglob("*.json") if "private" not in p.parts]
        for p in public:
            text = p.read_text(encoding="utf-8")
            for acct in list(STATE) + ["x.near", "y.near"]:
                self.assertNotIn(f'"{acct}"', text, f"{acct} in {p.name}")
        self.assertIn(stakers.tag("big.near"), snap.read_text(encoding="utf-8"))

    def test_without_private_files_same_numbers(self):
        import shutil
        data, snap = self.run_snapshot(sorted(STATE))
        full, _ = stakers.compute(snap, data)
        shutil.rmtree(data / "private")
        st, problems = stakers.compute(snap, data)
        self.assertEqual(problems, [])
        self.assertTrue(st.pop("private_check").endswith("private file(s) absent"))
        full.pop("private_check")
        self.assertEqual(st, full)
        results, problems = stakers.verify_all(data)
        self.assertEqual(problems, [])

    def test_edited_public_list_fails(self):
        data, snap = self.run_snapshot(sorted(STATE))
        doc = json.loads(snap.read_text(encoding="utf-8"))
        e = next(e for e in doc["positions"] if e["kind"] == "position")
        e["amount_yocto"] = str(int(e["amount_yocto"]) + 1)
        snap.write_text(json.dumps(doc), encoding="utf-8")
        _, problems = stakers.compute(snap, data)
        self.assertTrue(any("differ from the private files" in p for p in problems))


if __name__ == "__main__":
    unittest.main()
