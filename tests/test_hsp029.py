"""Tests for scripts/hsp029.py on a simulated chain (no network).

Run: python -m unittest discover -s tests
"""
import base64
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hsp029 as h  # noqa: E402
import lock_window as lw  # noqa: E402
import test_lock_window as tl  # noqa: E402

Y = 10 ** 24
NS = lw.NS
START = 1793638088 * NS - 13 * 86400 * NS  # voting start, 13 days before the end
DURATION = 13 * 86400 * NS
END = START + DURATION                      # 2026-11-02T16:48:08Z


def proposal(for_y, against_y, other_y=0, counts=(26, 1, 2), floor=0, status="Voting",
             snapshot=5_274_745 * Y, q_bps=3500, a_bps=6667):
    votes = [for_y, against_y, other_y]
    return {
        "id": 29, "title": "HSP-029 test", "link": None,
        "voting_options": ["For", "Against", "Abstain"],
        "voting_start_time_ns": str(START), "voting_duration_ns": str(DURATION),
        "timelock_duration_ns": str(14 * 86400 * NS),
        "snapshot_and_state": {"snapshot": {"root": "x", "length": 496, "block_height": 220563095},
                               "timestamp_ns": "1", "total_venear": str(snapshot)},
        "votes": [{"total_venear": str(v), "total_votes": c} for v, c in zip(votes, counts)],
        "total_votes": {"total_venear": str(sum(votes)), "total_votes": sum(counts)},
        "status": status, "quorum_threshold_bps": q_bps, "quorum_floor": str(floor),
        "approval_threshold_bps": a_bps, "actions": None,
    }


class ComputeTest(unittest.TestCase):
    def test_passes_with_numbers_like_27_october(self):
        r = h.compute(proposal(3_180_353 * Y, 155 * Y // 10, 942 * Y // 10))
        self.assertEqual(r["computed_status"], "Succeeded")
        self.assertEqual(r["quorum_required_venear"], "1846160.750")  # 35% of 5,274,745
        self.assertTrue(r["options_sum_equals_total"])
        self.assertEqual(r["options"][0]["label"], "For")
        p = proposal(1, 0)
        del p["voting_options"]  # current contract: fixed options, none listed
        self.assertEqual([o["label"] for o in h.compute(p)["options"]], ["For", "Against", "Abstain"])

    def test_approval_threshold_is_exact_and_two_thirds_is_not_enough(self):
        big = 2_000_000 * Y  # well above quorum
        # 6667 bps exactly: met (>=)
        self.assertTrue(h.compute(proposal(6667 * big // 10000, 3333 * big // 10000))["approval_met"])
        # 2/3 = 6666.67 bps < 6667: not met
        r = h.compute(proposal(2 * big, 1 * big))
        self.assertFalse(r["approval_met"])
        self.assertEqual(r["computed_status"], "Defeated")

    def test_third_option_counts_for_quorum_not_for_approval(self):
        # For + Against alone are below quorum; Abstain lifts turnout above it.
        r = h.compute(proposal(100_000 * Y, 0, 1_800_000 * Y))
        self.assertTrue(r["quorum_met"])
        self.assertTrue(r["approval_met"])
        self.assertEqual(r["approval_share_for_of_for_plus_against"], "1.000000")
        r = h.compute(proposal(100_000 * Y, 0, 0))
        self.assertFalse(r["quorum_met"])

    def test_quorum_floor_wins_when_higher(self):
        r = h.compute(proposal(1_900_000 * Y, 0, floor=2_000_000 * Y))
        self.assertEqual(r["quorum_required_venear"], "2000000.000")
        self.assertFalse(r["quorum_met"])

    def test_no_snapshot_is_defeated(self):
        p = proposal(1, 0)
        p["snapshot_and_state"] = None
        self.assertEqual(h.compute(p)["computed_status"], "Defeated")


class FakeHosChain(tl.FakeChain):
    """Blocks from the lock_window fake chain, plus vote.dao views.

    One last vote lands in the last block before the end; nothing changes after it.
    """

    def __init__(self, final_height):
        super().__init__(final_height)
        h = tl.expected_boundary(END)
        self.close_height = h
        self.last_vote_height = tl.prev_existing(h)

    def state(self, height):
        late = 5 * Y if height >= self.last_vote_height else 0
        status = "Voting" if tl.ts(height) < END else "Timelock"
        return proposal(3_180_353 * Y + late, 155 * Y // 10, 942 * Y // 10,
                        counts=(27 if late else 26, 1, 2), status=status)

    def _post(self, body):
        if body["method"] != "query":
            return super()._post(body)
        self.calls += 1
        params = body["params"]
        height = self.final_height if params.get("finality") == "final" else params["block_id"]
        args = json.loads(base64.b64decode(params["args_base64"]))
        if params["method_name"] == "get_proposal":
            value = self.state(height) if args["proposal_id"] == 29 else None
        else:
            value = {"quorum_threshold_bps": 3500, "approval_threshold_bps": 6667}
        res = {"result": list(json.dumps(value).encode()), "logs": [], "block_height": height,
               "block_hash": f"H{height}"}
        return json.dumps({"jsonrpc": "2.0", "id": "hsp029", "result": res}).encode()


class RunTest(unittest.TestCase):
    def test_locks_closing_block_and_verifies(self):
        chain = FakeHosChain(tl.final_height_at(END + 3 * 3600 * NS))
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"
            doc = h.run(chain, data)
            self.assertEqual(doc["closing_block"]["height"], chain.close_height)
            self.assertTrue(all(doc["checks"].values()), doc["checks"])
            # The vote in the last block before the end is counted.
            self.assertEqual(doc["result"]["options"][0]["votes"], 27)
            self.assertEqual(doc["result"]["computed_status"], "Succeeded")
            self.assertEqual(doc["reported_status_at_close"], "Timelock")
            self.assertEqual(doc["proposal"]["voting_end_utc"][:19], "2026-11-02T16:48:08")
            out = data / h.OUT_NAME
            out.write_text(json.dumps(doc), encoding="utf-8")
            self.assertEqual(h.verify(out), [])

            # Change one byte of one raw file: verify must catch it.
            raw = data.parent / doc["raw_files"]["proposal_at_close"]["path"]
            raw.write_bytes(raw.read_bytes().replace(b'"hsp029"', b'"hsp028"'))
            self.assertTrue(any("sha256" in p for p in h.verify(out)))

    def test_refuses_before_vote_closed(self):
        chain = FakeHosChain(tl.final_height_at(END + 60 * NS))
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit):
                h.run(chain, Path(tmp) / "data")


if __name__ == "__main__":
    unittest.main()
