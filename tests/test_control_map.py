"""Tests for scripts/control_map.py on simulated RPC answers (no network).

The simulated answers have the shapes read on mainnet at block 222,491,356 (1 Nov 2026);
member names are replaced by placeholders.

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
import control_map as cm  # noqa: E402

Y = 10 ** 24
END, START = 222491356, 218126921
HEX = "8e69c33b572dad1f2da6f744c834705e651d3784af2471b58949f2fefd5b55d3"


def people(n, tag):
    return [f"{tag}{i}.near" for i in range(n)]


def vp(t):
    return {"quorum": "0", "threshold": t, "weight_kind": "RoleWeight"}


ALL_KINDS = ["transfer", "call", "upgrade_self", "upgrade_remote", "policy", "config",
             "add_member_to_role", "remove_member_from_role", "set_vote_token", "vote"]
POLICIES = {
    cm.INTENTS_DAO: {"roles": [
        {"name": "council", "kind": {"Group": people(5, "c")}, "permissions": ["*:*"],
         "vote_policy": {k: vp("3") for k in ALL_KINDS if k != "policy"}},
        {"name": "all", "kind": "Everyone", "permissions": ["call:AddProposal"], "vote_policy": {}}],
        "default_vote_policy": vp([1, 2])},
    cm.FE_DAO: {"roles": [
        {"name": "Requestor", "kind": {"Group": people(5, "r")},
         "permissions": ["call:AddProposal", "transfer:AddProposal"], "vote_policy": {}},
        {"name": "Admin", "kind": {"Group": people(5, "a")},
         "permissions": ["policy:*", "add_member_to_role:*", "config:*", "upgrade_self:*"],
         "vote_policy": {k: vp("1") for k in ["policy", "add_member_to_role", "config", "upgrade_self"]}},
        {"name": "Approver", "kind": {"Group": people(5, "p")},
         "permissions": ["transfer:VoteApprove", "call:VoteApprove"],
         "vote_policy": {k: vp("2") for k in ALL_KINDS}}],
        "default_vote_policy": vp([1, 2])},
    cm.CS_DAO: {"roles": [
        {"name": "Admin", "kind": {"Group": people(4, "a")}, "permissions": ["policy:*"],
         "vote_policy": {"policy": vp("2")}},
        {"name": "Approver", "kind": {"Group": people(4, "p")},
         "permissions": ["transfer:VoteApprove", "call:VoteApprove"],
         "vote_policy": {"transfer": vp("2"), "call": vp("2")}}],
        "default_vote_policy": vp([1, 2])},
    cm.HOS_ROOT: {"roles": [{"name": "Admin", "kind": {"Group": people(5, "h")},
                             "permissions": ["*:*"], "vote_policy": {}}],
                  "default_vote_policy": vp("3")},
    cm.POOL_OWNER: {"roles": [
        {"name": "all", "kind": "Everyone", "permissions": [], "vote_policy": {}},
        {"name": "council", "kind": {"Group": people(3, "j")},
         "permissions": ["policy:VoteApprove", "transfer:VoteApprove", "call:VoteApprove",
                         "add_member_to_role:VoteApprove"],
         "vote_policy": {k: vp([49, 100]) for k in ALL_KINDS}}],
        "default_vote_policy": vp([1, 2])},
}
GRANTEES = {
    cm.INTENTS: {"DAO": [cm.INTENTS_DAO], "FeesManager": [], "Upgrader": [cm.CTL],
                 "PauseManager": [HEX, "pm.bridge.near"]},
    cm.CTL: {"DAO": [cm.INTENTS_DAO], "Updater": [HEX], "Downgrader": [HEX, "x" * 64],
             "Releaser": [], "Deployer": []},
}
KEYS = {
    cm.BUYBACKS: [("fc", cm.BUYBACKS)] * 4,
    cm.TREASURY: [("fc", cm.TREASURY)] * 4,
    cm.INTENTS: [("fc", cm.INTENTS)] * 9,
    cm.STAKE_DAO: [("full", None)] * 2,
}


def view_answer(value):
    return {"result": list(json.dumps(value).encode()), "logs": [], "block_height": END}


def stakes():
    # 10 validators: 20, 15, 12, 10, 9, 8, 8, 7, 6, 5 (total 100)
    return [20, 15, 12, 10, 9, 8, 8, 7, 6, 5]


class FakeChain:
    url = "fake://archival"

    def __init__(self, policies=POLICIES, versions=("0.4.5", "0.3.3")):
        self.policies, self.versions, self.calls = policies, versions, 0

    def _post(self, body):
        self.calls += 1
        m, p = body["method"], body["params"]
        if m == "EXPERIMENTAL_protocol_config":
            r = {"protocol_version": 86, "max_inflation_rate": [1, 40], "protocol_reward_rate": [0, 1],
                 "protocol_upgrade_stake_threshold": [4, 5], "protocol_treasury_account": "treasury.near"}
        elif m == "validators":
            assert p == {"epoch_id": "EPOCH"}
            r = {"epoch_start_height": END - 40000,
                 "current_validators": [{"account_id": f"v{i}.poolv1.near", "stake": str(s * Y)}
                                        for i, s in enumerate(stakes())]}
        elif p["request_type"] == "view_account":
            amount = {cm.TREASURY: (1_257_331 if p["block_id"] == START else 1_526_304) * Y}
            r = {"amount": str(amount.get(p["account_id"], Y)), "locked": "0",
                 "code_hash": "4zSoHkLjJWZm34Psd4Eq2WUXHELt6LxtKmUXpsZWAECp", "block_height": p["block_id"]}
        elif p["request_type"] == "view_access_key_list":
            keys = []
            for kind, recv in KEYS.get(p["account_id"], []):
                perm = "FullAccess" if kind == "full" else {"FunctionCall": {
                    "receiver_id": recv, "method_names": ["confirm"], "allowance": None}}
                keys.append({"public_key": "ed25519:x", "access_key": {"nonce": 1, "permission": perm}})
            r = {"keys": keys, "block_height": p["block_id"]}
        else:
            acc, meth = p["account_id"], p["method_name"]
            args = json.loads(base64.b64decode(p["args_base64"]))
            assert p["block_id"] == END
            v = {
                "contract_source_metadata": {"version": self.versions[0 if acc == cm.INTENTS else 1]},
                "acl_role_variants": list(GRANTEES.get(acc, {})),
                "acl_get_super_admins": [cm.INTENTS_DAO, acc],
                "acl_get_grantees": GRANTEES.get(acc, {}).get(args.get("role"), []),
                "fee": 1,
                "get_deployment": {"version": "0.4.5", "hash": "a1",
                                   "upgrade_times": {"1730896107734667690": "0.1.1",
                                                     "1791402797418572403": "0.4.5"}},
                "get_releases": [{"hash": "a", "version": "0.4.4"}, {"hash": "b", "version": "0.4.5"}],
                "get_policy": self.policies.get(acc),
                "get_num_confirmations": 2,
                "get_config": {"owner_account_id": cm.HOS_ROOT if acc == cm.VOTE else cm.STAKE_DAO,
                               "reviewer_ids": people(5, "rv"), "council_ids": people(5, "cl"),
                               "guardians": people(5, "g"), "max_active_proposals": 3},
                "get_reward_fee_fraction": {"numerator": 100, "denominator": 100},
                "get_owner_id": cm.POOL_OWNER,
            }[meth]
            r = view_answer(v)
        return json.dumps({"jsonrpc": "2.0", "id": "control", "result": r}).encode()


class ControlMapTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        data = self.root / "data"
        (data / "raw" / "blocks").mkdir(parents=True)
        (data / "raw" / "blocks" / f"block_{END}.json").write_text(
            json.dumps({"result": {"header": {"height": END, "epoch_id": "EPOCH"}}}))
        b = lambda h, s, t: {"height": h, "total_supply_yocto": str(s * Y), "timestamp_utc": t}
        self.window = data / "window_test.json"
        self.window.write_text(json.dumps({"boundaries": [
            b(START, 1_307_821_213, "2026-10-02T00:00:00.370847409Z"),
            b(END, 1_310_472_976, "2026-11-01T00:00:00.175647275Z")]}))

    def tearDown(self):
        self.tmp.cleanup()

    def save(self, chain=None):
        doc = cm.run(chain or FakeChain(), self.root / "data", self.window)
        out = self.root / "data" / cm.OUT_NAME
        out.write_text(json.dumps(doc), encoding="utf-8")
        return doc, out

    def test_thresholds_follow_sputnik_rule(self):
        doc, _ = self.save()
        kn = lambda x: (x["k"], x["n"], x["role"])
        d = doc["daos"]
        self.assertEqual(kn(d[cm.INTENTS_DAO]["kinds"]["call"]), (3, 5, "council"))
        self.assertEqual(kn(d[cm.INTENTS_DAO]["rules"]), (3, 5, "council"))  # default [1,2] -> 5//2+1
        self.assertEqual(kn(d[cm.FE_DAO]["kinds"]["transfer"]), (2, 5, "Approver"))
        self.assertEqual(kn(d[cm.FE_DAO]["rules"]), (1, 5, "Admin"))
        self.assertEqual(kn(d[cm.CS_DAO]["rules"]), (2, 4, "Admin"))
        self.assertEqual(kn(d[cm.HOS_ROOT]["rules"]), (3, 5, "Admin"))
        self.assertEqual(kn(d[cm.POOL_OWNER]["kinds"]["transfer"]), (2, 3, "council"))  # 49*3//100+1
        self.assertIsNone(d[cm.CS_DAO]["kinds"]["upgrade_self"])

    def test_links(self):
        doc, out = self.save()
        L = doc["links"]
        self.assertEqual(L["intents_protocol_fee"]["value"], {"fee_pips": 1, "fee_percent": "0.0001"})
        self.assertEqual(L["intents_protocol_fee"]["fees_manager_grantees"]["total"], 0)
        self.assertEqual(L["intents_code"]["upgrader_grantees"]["public"], [cm.CTL])
        self.assertEqual(L["intents_code"]["controller"]["updater_grantees"],
                         {"public": [], "others": 1, "total": 1})
        self.assertEqual(L["intents_code"]["code_changes"], 2)
        self.assertEqual(L["buybacks_wallet"]["multisig"],
                         {"confirmations": 2, "member_keys": 4, "full_access_keys": 0})
        i = L["issuance"]
        # 20+15+12+10+9+8+8 = 82 >= 80 -> 7; 20 not > 20, 20+15 > 20 -> 2; 67 >= 66.7 -> 6? 20+15+12+10+9=66 < 66.67, +8 -> 6
        self.assertEqual((i["validators_to_reach_threshold"], i["validators_to_block_upgrade"],
                          i["validators_to_reach_two_thirds"], i["validators_to_exceed_one_third"]),
                         (7, 2, 6, 2))
        self.assertEqual(i["largest_validator_share"], "0.200000")
        t = L["protocol_treasury"]
        self.assertEqual(t["balance_change_near"], "268973.000")
        self.assertEqual(t["share_of_new_supply"], "0.101432")
        self.assertEqual(t["reported_protocol_reward_rate"], "0/1")
        self.assertEqual(L["farm_contract"]["full_access_keys"], 2)
        self.assertEqual(L["hsp_voting"]["guardians"], 5)
        self.assertTrue(all(doc["checks"].values()), doc["checks"])
        self.assertEqual(cm.verify(out), ([], 0))

    def test_no_private_names_in_public_output(self):
        doc, _ = self.save()
        text = json.dumps({k: v for k, v in doc.items() if k != "raw_files"})
        for name in ["c0.near", "a0.near", "g0.near", "rv0.near", "v0.poolv1.near", HEX, "pm.bridge.near"]:
            self.assertNotIn(name, text)
        self.assertEqual(cm.leaked_names(doc["links"]), [])
        self.assertEqual(cm.leaked_names({"x": ["someone.near"]}), ["someone.near"])

    def test_private_answers_are_stored_apart(self):
        doc, out = self.save()
        private = {k for k, f in doc["raw_files"].items() if f["private"]}
        self.assertIn(f"{cm.INTENTS_DAO}/get_policy", private)
        self.assertIn("validators", private)
        self.assertIn(f"{cm.CTL}/grantees/Updater", private)
        self.assertNotIn(f"{cm.INTENTS}/fee", private)
        for k in private:
            self.assertTrue(doc["raw_files"][k]["path"].startswith("data/private/control/"))
        for k in private:  # a judge without data/private/: public files still check
            (self.root / doc["raw_files"][k]["path"]).unlink()
        self.assertEqual(cm.verify(out), ([], len(private)))

    def test_version_mismatch_is_flagged(self):
        doc, _ = self.save(FakeChain(versions=("0.4.6", "0.3.3")))
        self.assertFalse(doc["checks"]["intents_source_version_matches_rules"])

    def test_tampered_raw_file(self):
        doc, out = self.save()
        p = self.root / doc["raw_files"][f"{cm.INTENTS}/fee"]["path"]
        p.write_bytes(p.read_bytes() + b" ")
        problems, _ = cm.verify(out)
        self.assertIn(f"sha256 mismatch: {doc['raw_files'][f'{cm.INTENTS}/fee']['path']}", problems)

    def test_offline_recompute_from_redacted_copies(self):
        doc, out = self.save()
        redacted = [self.root / f["redacted"]["path"] for f in doc["raw_files"].values()
                    if f["private"]]
        self.assertTrue(redacted)
        for p in redacted:
            text = p.read_text(encoding="utf-8")
            for name in ["c0.near", "a0.near", "g0.near", "rv0.near", "v0.poolv1.near", HEX,
                         "pm.bridge.near"]:
                self.assertNotIn(name, text, p.name)
        shutil.rmtree(self.root / "data" / "private")
        self.assertEqual(cm.verify(out), ([], len(redacted)))
        d = json.loads(out.read_text(encoding="utf-8"))
        d["links"]["issuance"]["validators"] += 1   # a wrong number is caught without private files
        out.write_text(json.dumps(d), encoding="utf-8")
        self.assertTrue(any("does not recompute" in p for p in cm.verify(out)[0]))

    def test_redacted_copy_must_match_original(self):
        doc, out = self.save()
        f = doc["raw_files"]["validators"]
        p = self.root / f["redacted"]["path"]
        d = json.loads(p.read_bytes())
        d["result"]["current_validators"] = d["result"]["current_validators"][1:]
        p.write_bytes(json.dumps(d).encode())
        doc["raw_files"]["validators"]["redacted"]["sha256"] = cm.lw.sha256(p.read_bytes())
        out.write_text(json.dumps(doc), encoding="utf-8")
        self.assertIn("redacted copy does not match its original: validators", cm.verify(out)[0])


if __name__ == "__main__":
    unittest.main()
