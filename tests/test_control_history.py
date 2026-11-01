"""Tests for scripts/control_history.py on simulated DAO answers (no network).

Run: python -m unittest discover -s tests
"""
import base64
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import control_history as ch  # noqa: E402
import control_map as cm  # noqa: E402

END = 222491356
NS = 10 ** 9
T2025 = 1740096000 * NS  # 2025-02-21
T2026 = 1791331200 * NS  # 2026-10-07


def fc(pid, receiver, methods, t, status="Approved"):
    return {"id": pid, "proposer": "person.near", "description": "text naming person.near",
            "kind": {"FunctionCall": {"receiver_id": receiver,
                                      "actions": [{"method_name": m, "args": "", "deposit": "1",
                                                   "gas": "1"} for m in methods]}},
            "status": status, "vote_counts": {}, "votes": {"voter.near": "Approve"},
            "submission_time": str(t)}


def other(pid, kind, t, status="Approved"):
    return {"id": pid, "proposer": "person.near", "description": "x", "kind": kind,
            "status": status, "vote_counts": {}, "votes": {}, "submission_time": str(t)}


PROPOSALS = {
    cm.INTENTS_DAO: [
        fc(0, cm.INTENTS, ["set_fee"], T2025),
        fc(1, cm.CTL, ["add_release_info", "upgrade"], T2025),
        fc(2, cm.INTENTS, ["ft_force_withdraw"], T2026),
        fc(3, cm.INTENTS, ["acl_grant_role"], T2026),
        fc(4, cm.INTENTS, ["set_fee"], T2026, status="Rejected"),
        fc(5, "someone.near", ["do_thing"], T2026),
        # id 6 removed: missing from get_proposals
        other(7, {"ChangePolicy": {"policy": {"roles": [{"kind": {"Group": ["m.near"]}}]}}}, T2026),
        other(8, "Vote", T2026),
    ],
    cm.HOS_ROOT: [fc(0, cm.VOTE, ["set_guardians"], T2026),
                  other(1, {"UpgradeRemote": {"receiver_id": "registrar", "method_name": "upgrade",
                                              "hash": "h"}}, T2026)],
    cm.POOL_OWNER: [other(0, {"Transfer": {"token_id": "", "receiver_id": "payee.near",
                                           "amount": "1"}}, T2026)],
    cm.CS_DAO: [],
    cm.FE_DAO: [other(0, {"AddMemberToRole": {"member_id": "new.near", "role": "Admin"}}, T2026)],
}
LAST = {cm.INTENTS_DAO: 9}


class FakeChain:
    url = "fake://archival"

    def __init__(self):
        self.calls = 0

    def _post(self, body):
        self.calls += 1
        p = body["params"]
        assert p["block_id"] == END
        acc, meth = p["account_id"], p["method_name"]
        args = json.loads(base64.b64decode(p["args_base64"]))
        if meth == "get_last_proposal_id":
            v = LAST.get(acc, len(PROPOSALS[acc]))
        elif meth == "get_proposals":
            v = [x for x in PROPOSALS[acc]
                 if args["from_index"] <= x["id"] < args["from_index"] + args["limit"]]
        elif meth == "get_deployment":
            v = {"version": "0.4.5", "upgrade_times": {
                str(T2025): "0.2.7", str(T2025 + NS): "0.2.5", str(T2026): "0.4.5"}}
        else:
            raise AssertionError(meth)
        return json.dumps({"jsonrpc": "2.0", "id": "control", "result": {
            "result": list(json.dumps(v).encode()), "logs": [], "block_height": END}}).encode()


class ControlHistoryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        data = self.root / "data"
        data.mkdir()
        self.window = data / "window_test.json"
        self.window.write_text(json.dumps({"boundaries": [
            {"height": 1}, {"height": END, "timestamp_utc": "2026-11-01T00:00:00.17Z"}]}))

    def tearDown(self):
        self.tmp.cleanup()

    def save(self):
        doc = ch.run(FakeChain(), self.root / "data", self.window)
        out = self.root / "data" / ch.OUT_NAME
        out.write_text(json.dumps(doc), encoding="utf-8")
        return doc, out

    def test_levers(self):
        doc, out = self.save()
        a = doc["all_daos"]
        self.assertEqual(a["fee"]["approved_actions"], 1)  # the rejected set_fee is not counted
        self.assertEqual(a["fee"]["first"], "2025-02-21")
        self.assertEqual(a["code"]["approved_actions"], 3)  # add_release_info, upgrade, UpgradeRemote
        self.assertEqual(a["user_funds"]["by_method"], {"intents.near.ft_force_withdraw": 1})
        self.assertEqual(a["roles"]["approved_actions"], 3)  # acl_grant_role, ChangePolicy, AddMember
        self.assertEqual(a["voting"]["by_method"], {"vote.dao.set_guardians": 1})
        self.assertEqual(a["transfer"]["approved_actions"], 1)
        self.assertEqual(a["other"]["by_method"], {"(account).do_thing": 1, "Vote": 1})
        self.assertEqual(a["code"]["by_year"], {"2025": 2, "2026": 1})
        i = doc["per_dao"][cm.INTENTS_DAO]
        self.assertEqual(i["proposals"], 8)
        self.assertEqual(i["removed_proposals"], 1)
        c = doc["intents_code_changes"]
        self.assertEqual((c["count"], c["downgrades"]), (3, 1))
        self.assertTrue(all(e["lever"] != "transfer" for e in doc["timeline"]))
        self.assertTrue(all(doc["checks"].values()))
        self.assertEqual(ch.verify(out), ([], 0))

    def test_no_people_in_public_output(self):
        doc, _ = self.save()
        text = json.dumps({k: v for k, v in doc.items() if k != "raw_files"})
        for name in ["person.near", "voter.near", "someone.near", "payee.near", "new.near",
                     "m.near", "text naming"]:
            self.assertNotIn(name, text)

    def test_private_pages_and_missing_private(self):
        doc, out = self.save()
        private = [k for k, f in doc["raw_files"].items() if f["private"]]
        self.assertTrue(all("get_proposals" in k for k in private))
        for k in private:
            (self.root / doc["raw_files"][k]["path"]).unlink()
        self.assertEqual(ch.verify(out), ([], len(private)))

    def test_tampered(self):
        doc, out = self.save()
        key = f"history/{cm.CTL}/get_deployment"
        p = self.root / doc["raw_files"][key]["path"]
        p.write_bytes(p.read_bytes() + b" ")
        self.assertIn(f"sha256 mismatch: {doc['raw_files'][key]['path']}", ch.verify(out)[0])


if __name__ == "__main__":
    unittest.main()
