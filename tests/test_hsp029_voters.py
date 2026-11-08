"""Tests for scripts/hsp029_voters.py on simulated NearBlocks pages and tx responses.

Run: python -m unittest discover -s tests
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import hsp029_voters as hv  # noqa: E402

Y = 10 ** 24
CREATED = 1_792_000_000 * 10 ** 9
H = 222_900_000


def ev(event, acct, vote, venear, pid=29):
    return "EVENT_JSON:" + json.dumps({"standard": "venear", "version": "1.0.0", "event": event,
                                       "data": [{"account_id": acct, "proposal_id": pid,
                                                 "vote": vote,
                                                 "account_balance": str(venear)}]})


def outcome(rid, logs, ok=True, executor="vote.dao"):
    st = {"SuccessValue": ""} if ok else {"Failure": {"ActionError": {}}}
    return {"id": rid, "outcome": {"executor_id": executor, "logs": logs, "status": st}}


# tx hash -> (signer, receipt outcomes)
TXS = {
    "tx_a": ("a.near", [outcome("r_a", [ev("add_vote", "a.near", 0, 1000 * Y)])]),
    # b first votes Against, then changes to For
    "tx_b1": ("b.near", [outcome("r_b1", [ev("add_vote", "b.near", 1, 500 * Y)])]),
    "tx_b2": ("b.near", [outcome("r_b2", [ev("remove_vote", "b.near", 1, 500 * Y),
                                           ev("add_vote", "b.near", 0, 500 * Y)])]),
    # c: take_snapshot_and_vote -> snapshot callback -> chained vote (predecessor vote.dao)
    "tx_c": ("c.near", [outcome("r_c0", []), outcome("r_c1", []),
                        outcome("r_c2", [ev("add_vote", "c.near", 2, 200 * Y)])]),
    # d: receipt failed (deposit too small) -> rolled back, logs ignored
    "tx_d": ("d.near", [outcome("r_d", [ev("add_vote", "d.near", 0, 9999 * Y)], ok=False)]),
    # e: vote on another proposal
    "tx_e": ("e.near", [outcome("r_e", [ev("add_vote", "e.near", 0, 7 * Y, pid=28)])]),
}


def receipt(rid, tx, pred, height, ts, method):
    return {"actions": [{"action": "FUNCTION_CALL", "method": method}],
            "block": {"block_height": str(height), "block_timestamp": str(ts)},
            "predecessor_account_id": pred, "receipt_id": rid, "receiver_account_id": "vote.dao",
            "transaction_hash": tx}


VOTE_ROWS = [  # newest first, as NearBlocks returns them
    receipt("r_late", "tx_late", "z.near", H + 5, CREATED + 99, "vote"),  # after the block
    receipt("r_e", "tx_e", "e.near", H - 1, CREATED + 60, "vote"),
    receipt("r_d", "tx_d", "d.near", H - 2, CREATED + 50, "vote"),
    receipt("r_c2", "tx_c", "vote.dao", H - 3, CREATED + 40, "vote"),
    receipt("r_b2", "tx_b2", "b.near", H - 4, CREATED + 30, "vote"),
    receipt("r_b1", "tx_b1", "b.near", H - 5, CREATED + 20, "vote"),
    receipt("r_a", "tx_a", "a.near", H - 6, CREATED + 10, "vote"),
    receipt("r_old", "tx_old", "o.near", H - 900, CREATED - 10, "vote"),  # before creation
]
CHAIN_ROWS = [receipt("r_c0", "tx_c", "c.near", H - 4, CREATED + 39, "take_snapshot_and_vote")]


def page(rows, nxt=None):
    return json.dumps({"data": rows, "meta": {"next_page": nxt} if nxt else {}}).encode()


def fake_get(url):
    if "take_snapshot_and_vote" in url:
        return page(CHAIN_ROWS)
    if "next=p2" in url:
        return page(VOTE_ROWS[4:])
    return page(VOTE_ROWS[:4], "p2")


class FakeChain:
    url = "fake://archival"

    def __init__(self):
        self.calls = 0
        self.asked = []

    def _post(self, body):
        self.calls += 1
        p = body["params"]
        self.asked.append((p["tx_hash"], p["sender_account_id"]))
        signer, ros = TXS[p["tx_hash"]]
        assert p["sender_account_id"] == signer
        return json.dumps({"jsonrpc": "2.0", "id": "x",
                           "result": {"receipts_outcome": ros}}).encode()


def proposal_raw(for_y, against_y, abstain_y, counts):
    votes = [for_y, against_y, abstain_y]
    p = {"id": 29, "creation_time_ns": str(CREATED),
         "snapshot_and_state": {"total_venear": str(4000 * Y), "snapshot": {}},
         "quorum_threshold_bps": 3500, "quorum_floor": str(1000 * Y),
         "approval_threshold_bps": 6667,
         "votes": [{"total_venear": str(v), "total_votes": c} for v, c in zip(votes, counts)],
         "total_votes": {"total_venear": str(sum(votes)), "total_votes": sum(counts)}}
    return json.dumps({"result": {"result": list(json.dumps(p).encode()),
                                  "block_height": H}}).encode()


GOOD = proposal_raw(1500 * Y, 0, 200 * Y, (2, 0, 1))


class VotersTest(unittest.TestCase):
    def run_it(self, raw=GOOD, trial=False):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        chain = FakeChain()
        doc = hv.run(chain, tmp, H, raw, trial=trial, get=fake_get, wait=0)
        return tmp, chain, doc

    def test_replays_changes_ignores_failures_and_other_proposals(self):
        root, chain, doc = self.run_it()
        self.assertTrue(doc["sums_match_contract"])
        self.assertEqual(doc["private_check"], "recomputed")
        by_tag = {v["tag"]: (v["option"], v["venear"]) for v in doc["voters"]}
        self.assertEqual(by_tag, {hv.tag("a.near"): (0, "1000.000"),
                                  hv.tag("b.near"): (0, "500.000"),   # changed to For
                                  hv.tag("c.near"): (2, "200.000")})  # chained vote
        # chained vote: tx looked up with the real signer; tx before creation / after H skipped
        self.assertIn(("tx_c", "c.near"), chain.asked)
        self.assertNotIn("tx_old", [t for t, _ in chain.asked])
        self.assertNotIn("tx_late", [t for t, _ in chain.asked])
        s = doc["stats"]
        self.assertEqual(s["voters"], 3)
        self.assertEqual(s["top1_share_of_votes_cast"], "0.588235")   # 1000 / 1700
        self.assertEqual(s["top8_share_of_votes_cast"], "1.000000")
        self.assertEqual(s["top8_share_of_for"], "1.000000")
        self.assertEqual(s["fewest_voters_reaching_quorum"], 2)       # quorum 35% of 4000 = 1400 <= 1000 + 500
        # account IDs never in the public file
        public = (root / "data" / hv.OUT_NAME).read_text()
        for name in ("a.near", "b.near", "c.near"):
            self.assertNotIn(name, public)
        self.assertTrue(all(f["private"] for f in doc["raw_files"].values()))   # the proposal too
        self.assertIn("redacted", doc["raw_files"]["proposal"])

    def test_verify_offline_and_tampering(self):
        root, _, doc = self.run_it()
        path = root / "data" / hv.OUT_NAME
        problems, d = hv.verify(path)
        self.assertEqual(problems, [])
        self.assertEqual(d["private_check"], "recomputed")
        self.assertNotIn("PUBLIC_REDACTED", hv.verify_line(d["private_absent"]))
        # clean clone: private folder absent -> still OK from the public list
        shutil.rmtree(root / "data" / "private")
        problems, d = hv.verify(path)
        self.assertEqual(problems, [])
        self.assertIn("absent", d["private_check"])
        self.assertIn("PUBLIC_REDACTED", hv.verify_line(d["private_absent"]))
        self.assertIn(f"{d['private_absent']} private original(s)", hv.verify_line(d["private_absent"]))
        # tampered public voter list -> sums no longer match the contract
        doc2 = json.loads(path.read_text())
        doc2["voters"][0]["venear_yocto"] = str(int(doc2["voters"][0]["venear_yocto"]) - 1)
        path.write_text(json.dumps(doc2))
        problems, _ = hv.verify(path)
        self.assertTrue(problems)

    def test_refuses_when_voters_do_not_add_up(self):
        bad = proposal_raw(1500 * Y + 1, 0, 200 * Y, (2, 0, 1))
        with self.assertRaises(SystemExit):
            self.run_it(raw=bad)

    def test_trial_keeps_everything_in_its_folder(self):
        root, _, doc = self.run_it(trial=True)
        self.assertTrue((root / "hsp029_voters_trial.json").exists())
        self.assertTrue(all(not f["path"].startswith("..") for f in doc["raw_files"].values()))
        self.assertEqual(hv.verify(root / "hsp029_voters_trial.json")[0], [])

    def test_remove_without_matching_vote_is_reported(self):
        _, p = hv.replay([{"receipt": "x", "event": "remove_vote", "account": "q", "vote": 0,
                           "venear": 1}])
        self.assertTrue(p)


if __name__ == "__main__":
    unittest.main()
