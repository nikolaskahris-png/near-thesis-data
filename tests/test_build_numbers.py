"""Tests for scripts/build_numbers.py (no network, synthetic inputs).

Run: python -m unittest discover -s tests
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import build_numbers as bn  # noqa: E402

START, END = "2026-10-02", "2026-11-01"
B0, B1 = 218126921, 222491356


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding="utf-8")


def fake_repo(tmp, fees_end_block=B1, treasury_end=B1, stakers_block=B1):
    root = Path(tmp)
    data = root / "data"
    window = data / f"window_{START}_{END}.json"
    write(window, {"window": {"start": START, "end": END},
                   "boundaries": [{"height": B0, "total_supply_yocto": str(1_307_821_213 * 10 ** 24)},
                                  {"height": B1, "total_supply_yocto": str(1_310_472_976 * 10 ** 24)}]})
    cols = ("date,window_start,block_start,block_end,block_end_utc,total_supply_start,"
            "total_supply_end,new_supply_per_day,buybacks_start,buybacks_end,buybacks_per_day,"
            "fefunds_start,fefunds_end,fefunds_per_day,coverage_buybacks,coverage_with_fe,"
            "max_coverage_defillama,near_ai_stakers,near_ai_top_share,flags")
    (data / "history.csv").write_text(
        cols + f"\n{END},{START},{B0},{B1},x,1,2,88392.087,0,0,9569.750,0,0,4984.673,"
        "0.108265,0.164658,,,,\n", encoding="utf-8")
    write(data / "daily" / f"{END}.json", {"date": END, "stub": True})
    fw = {"block_start": B0, "block_end": fees_end_block, "new_near_per_day": "88392.087",
          "counted_days": 29, "excluded": {"2026-10-31": "fees_below_20pct_of_median"},
          "max_coverage": "0.455287", "equilibrium_price_usd": "2.2382",
          "hsp029_scenario_max_coverage": "0.711387",
          "hsp029_scenario_equilibrium_price_usd": "3.4972",
          "fees_usd_per_day": "197837.45", "revenue_usd_per_day": "71504.41",
          "volume_usd_per_day": "130592125.00", "fees_bps": "15.15", "take_rate": "0.361430",
          "mean_price_usd": "4.8977", "fees_near_per_day": "40243.8",
          "defillama_revenue_coverage": "0.166598"}
    write(data / f"fees_{START}_{END}.json",
          {"window_file": f"data/window_{START}_{END}.json", "fetched_utc": "x",
           "final": {"ready": False}, "result": {"window": fw, "monthly": [
               {"month": "2026-09", "full_month": True, "days": 30, "counted_days": 30,
                "excluded": {}, "fees_usd_per_day": "244210.00",
                "revenue_usd_per_day": "61317.10", "volume_usd_per_day": "160103145.90",
                "fees_bps": "15.25", "take_rate": "0.251101", "mean_price_usd": "3.2774",
                "revenue_near_per_day": "19129.4"},
               {"month": "2026-10", "full_month": True, "days": 31, "counted_days": 30,
                "excluded": {"2026-10-31": "fees_below_20pct_of_median"},
                "fees_usd_per_day": "198126.00", "revenue_usd_per_day": "71500.53",
                "volume_usd_per_day": "130406943.67", "fees_bps": "15.19",
                "take_rate": "0.360878", "mean_price_usd": "4.9049",
                "revenue_near_per_day": "14700.5"},
               {"month": "2026-11", "full_month": False}]}})
    write(data / "stakers" / f"{END}.json", {"stub": stakers_block})
    write(data / "coverage_monthly.json", {"rows": [
        {"month": "2026-09", "block_start": 1, "block_end": 2,
         "buybacks_per_day": "13478.332", "fefunds_per_day": "5327.698",
         "coverage_buybacks": "0.152552", "coverage_with_fe": "0.212852", "flags": ""},
        {"month": "2026-10", "block_start": 2, "block_end": B1,
         "buybacks_per_day": "9588.935", "fefunds_per_day": "4975.049",
         "coverage_buybacks": "0.108852", "coverage_with_fe": "0.165328", "flags": ""}]})
    w = {"start_block": 208930590, "end_block": treasury_end,
         "start_utc": "2026-07-28T17:25:00Z", "end_utc": "2026-11-01T00:00:00Z",
         "owner_flows": {"unstaked": "425334.490", "near_transferred_out": "423980.240",
                         "near_to_payments_account": "280337.660",
                         "usdc_transferred_out": "365000.00"},
         "owner_positions_start": {"owner_total_near": "1336984.004"},
         "owner_positions_end": {"owner_total_near": "935136.087"},
         "owner_total_near_change": "-401847.916",
         "payments_swaps_wnear_to_stablecoins": {"count": 7, "near_given": "139545.600",
                                                 "usd_received": "296652.40",
                                                 "mean_price_usd": "2.1258"}}
    write(data / "treasury_flows.json", {
        "meta": {"end_block": treasury_end},
        "windows": {"since_stake_dao": w, "year_2026": w},
        "stake_dao_first_stake_receipt": {"height": 209169270, "utc": "2026-07-30T09:49:40Z"}})
    return data, window


ROW = {"date": END, "window_start": START, "block_start": B0, "block_end": B1,
       "new_supply_per_day": "88392.087", "buybacks_per_day": "9569.750",
       "fefunds_per_day": "4984.673", "coverage_buybacks": "0.108265",
       "coverage_with_fe": "0.164658"}


def fake_row(day_doc, data_root):
    return dict(ROW), []


def fake_stats(path, data_root):
    block = json.loads(Path(path).read_text())["stub"]
    return ({"date": Path(path).stem, "block": block, "stakers_active": 112,
             "stakers_ever": 188, "stakers_left": 76, "left_share_of_ever": "0.404255",
             "largest_share": "0.732951", "largest_near": "1000000.000",
             "top10_share": "0.964371", "farm_total_near": "1364347.600",
             "outside_top10_accounts": 102, "outside_top10_near": "48610.600",
             "outside_top10_median_near": "60.000", "agents_locks": 86,
             "agents_locks_past_end": 75, "farm_or_active_lock_accounts": 145,
             "farm_or_any_lock_accounts": 181, "agents_lock_accounts": 83,
             "agents_locks_active": 43, "agents_locks_unlock_requested": 43,
             "agents_locks_active_within_term": 11, "agents_locks_near": "29739.000",
             "agents_locks_active_near": "14904.000",
             "agents_active_lock_near_vs_farm": "0.010924", "agents_locks_at_50_near": 58,
             "agents_lock_days_min": "30.00", "agents_lock_days_max": "31.00",
             "farm_reward_rate": "7605141075366948", "farm_units_per_near_year": "0.240000",
             "largest_units_per_day": "657.084189", "farm_units_per_day": "896.493000"}, [])


class FormatTest(unittest.TestCase):
    def test_formats(self):
        self.assertEqual(bn.f_pct("0.108265"), "10.8%")
        self.assertEqual(bn.f_pct("0.1645"), "16.5%")          # half up, not banker's
        self.assertEqual(bn.f_int("88392.087"), "88,392")
        self.assertEqual(bn.f_int("-401847.916"), "-401,848")
        self.assertEqual(bn.f_usd("2.2382", 2), "$2.24")
        self.assertEqual(bn.f_usd("197837.45"), "$197,837")


class BuildTest(unittest.TestCase):
    def test_builds_same_window_and_marks_provisional(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(bn.stakers, "compute", fake_stats), \
                    mock.patch.object(bn.daily, "build_row", fake_row):
            data, window = fake_repo(tmp)
            doc, problems = bn.build(data, window)
            self.assertEqual(problems, [])
            n = doc["numbers"]
            self.assertEqual(n["n1.coverage_buybacks"]["text"], "10.8%")
            self.assertEqual(n["n1.new_near_not_absorbed_per_day"]["text"], "78,822")
            self.assertEqual(n["n2.max_coverage"]["status"], "provisional")
            self.assertEqual(n["n3.largest_share"]["text"], "73.3%")
            self.assertEqual(n["f4.since_stake_dao.owner_near_change"]["text"], "-401,848")
            self.assertEqual(n["f8.computed_status"]["status"], "pending")
            # finding 9: 4,984.673 / (9,569.750 + 4,984.673)
            self.assertEqual(n["f9.front_end_share_of_wallets"]["text"], "34.2%")
            # investment view: multiples to 100% coverage, derived only
            self.assertEqual(n["iv.wallets_multiple_buybacks"]["text"], "×9.2")
            self.assertEqual(n["iv.wallets_multiple_with_front_end"]["text"], "×6.1")
            self.assertEqual(n["iv.fees_multiple"]["text"], "×2.2")
            self.assertEqual(n["iv.fees_multiple"]["status"], "provisional")
            # revenue at which today's revenue buys as many NEAR as are issued
            self.assertEqual(n["iv.revenue_equilibrium_price_usd"]["status"], "provisional")
            self.assertIn("iv.issuance_rate_per_year", n)
            self.assertNotIn("status", n["iv.wallets_multiple_buybacks"])
            # finding 7
            self.assertEqual(n["f7.locks_active"]["text"], "43")
            self.assertEqual(n["f7.locks_active_near"]["text"], "14,904")
            self.assertEqual(n["f7.active_lock_near_vs_farm"]["text"], "1.1%")
            self.assertEqual(n["f7.lock_days_max"]["text"], "31")
            # finding 2: monthly table, partial month left out, Sep -> Oct change
            self.assertEqual(n["f2.take_rate.2026-10"]["text"], "36.1%")
            self.assertEqual(n["f2.take_rate.2026-10"]["status"], "provisional")
            self.assertNotIn("f2.take_rate.2026-11", n)
            self.assertEqual(n["f2.wallets_kept_near_per_day.2026-09"]["text"], "18,806")
            self.assertEqual(n["f2.wallets_kept_share_of_revenue.2026-09"]["text"], "98%")
            self.assertEqual(n["f2.wallets_kept_share_of_revenue.2026-10"]["text"], "99%")
            self.assertEqual(n["f2.change.2026-09_2026-10.revenue_usd"]["text"], "+17%")
            self.assertEqual(n["f2.change.2026-09_2026-10.mean_price"]["text"], "+50%")
            self.assertEqual(n["f2.change.2026-09_2026-10.revenue_near"]["text"], "-23%")
            self.assertIn("f2.take_rate.2026-10", doc["provisional_or_pending"])
            # finding 6 at the end block; farm_rate.py not run yet -> pending
            self.assertEqual(n["f6.units_per_near_year"]["text"], "0.24")
            self.assertEqual(n["f6.largest_units_per_day"]["text"], "657.1")
            self.assertEqual(n["f6.rate_changes"]["status"], "pending")
            write(data / "farm_rate.json", {"edit_price_receipts_all_time": 1, "rate_changes": 1,
                                            "changes": [{
                "rate_changed": True, "receipt_block": 217788180, "tx_hash": "ENjb",
                "receipt_utc": "2026-09-29T14:21:09.243Z", "units_per_near_year_before": "0.120000",
                "units_per_near_year_after": "0.240000", "ratio_after_before": "2.000000",
                "signer_is_pool_owner": False, "signer_is_catalog_manager": True}]})
            n2 = bn.build(data, window)[0]["numbers"]
            self.assertEqual(n2["f6.change1.ratio"]["text"], "×2.0")
            self.assertEqual(n2["f6.change1.utc"]["text"], "2026-09-29 14:21 UTC")
            self.assertEqual(n2["f6.change1.signer_is_pool_owner"]["text"], "no")
            (data / "farm_rate.json").unlink()
            self.assertFalse(doc["complete"])
            self.assertIn("n2.max_coverage", doc["provisional_or_pending"])
            self.assertIn(f"data/daily/{END}.json", doc["sources"])
            self.assertNotIn("data/history.csv", doc["sources"])

            out = data / bn.OUT_NAME
            out.write_text(json.dumps(doc), encoding="utf-8")
            self.assertEqual(bn.verify(out, run_scripts=False), [])
            # a new day in history.csv (the daily Action) must not break the check
            (data / "history.csv").write_text((data / "history.csv").read_text() + "x\n")
            self.assertEqual(bn.verify(out, run_scripts=False), [])
            (data / "daily" / f"{END}.json").write_text("{}")
            self.assertTrue(any("source changed" in p for p in bn.verify(out, run_scripts=False)))

    def test_hsp029_and_voters_after_the_vote(self):
        hc = {"closing_block": {"height": 222600000, "timestamp_utc": "2026-11-02T16:48:08.5Z"},
              "reported_status_at_close": "Voting",
              "result": {"computed_status": "Succeeded",
                         "options": [{"index": 0, "label": "For", "venear": "3285084.854",
                                      "votes": 28}],
                         "turnout_of_snapshot": "0.622998",
                         "approval_share_for_of_for_plus_against": "1.000000",
                         "quorum_required_venear": "1846160.804",
                         "snapshot_total_venear": "5274745.155", "snapshot_accounts": 496}}
        stats = {"voters": 32, "for_voters": 28, "top1_share_of_votes_cast": "0.301000",
                 "top3_share_of_votes_cast": "0.700000", "top8_share_of_votes_cast": "0.920400",
                 "top10_share_of_votes_cast": "0.950000", "top8_share_of_for": "0.921000",
                 "largest_venear": "989000.000", "median_venear": "1200.500",
                 "fewest_voters_reaching_quorum": 3}
        for block, trial, ok in ((222600000, False, True), (222599999, False, False),
                                 (222600000, True, False)):
            with tempfile.TemporaryDirectory() as tmp, \
                    mock.patch.object(bn.stakers, "compute", fake_stats), \
                    mock.patch.object(bn.daily, "build_row", fake_row):
                data, window = fake_repo(tmp)
                write(data / "hsp029.json", hc)
                write(data / "hsp029_voters.json", {"block": block, "trial": trial,
                                                    "sums_match_contract": True, "stats": stats})
                doc, problems = bn.build(data, window)
                self.assertEqual(not problems, ok, (block, trial, problems))
                if ok:
                    n = doc["numbers"]
                    self.assertEqual(n["f8.top8_share_of_votes_cast"]["text"], "92.0%")
                    self.assertEqual(n["f8.fewest_voters_reaching_quorum"]["text"], "3")
                    self.assertEqual(n["f8.for_votes"]["text"], "28")
                    self.assertNotIn("f8.computed_status", doc["provisional_or_pending"])

    def test_refuses_inputs_from_another_window(self):
        for kwargs in ({"fees_end_block": B1 + 1}, {"treasury_end": B1 - 7},
                       {"stakers_block": 1}):
            with tempfile.TemporaryDirectory() as tmp, \
                    mock.patch.object(bn.stakers, "compute", fake_stats), \
                    mock.patch.object(bn.daily, "build_row", fake_row):
                data, window = fake_repo(tmp, **kwargs)
                _, problems = bn.build(data, window)
                self.assertTrue(problems, kwargs)


class MarkerTest(unittest.TestCase):
    numbers = {"n1.coverage_buybacks": {"text": "10.8%"}, "f8.computed_status": {"text": None}}

    def test_check_finds_wrong_unknown_and_unmeasured(self):
        good = "Coverage is <!--n:n1.coverage_buybacks-->10.8%<!--/n--> of new NEAR."
        self.assertEqual(bn.check_text(good, self.numbers), [])
        bad = ("<!--n:n1.coverage_buybacks-->11%<!--/n--> <!--n:n9.x-->1<!--/n--> "
               "<!--n:f8.computed_status-->Passed<!--/n-->")
        self.assertEqual(len(bn.check_text(bad, self.numbers)), 3)

    def test_required_numbers_must_be_marked(self):
        text = "Coverage is 10.8% of new NEAR."   # typed by hand, not marked
        problems = bn.check_text(text, self.numbers, ["n1.coverage_buybacks"])
        self.assertEqual(problems, ["required number 'n1.coverage_buybacks' is not marked in the text"])
        marked = "Coverage is <!--n:n1.coverage_buybacks-->10.8%<!--/n-->."
        self.assertEqual(bn.check_text(marked, self.numbers, ["n1.coverage_buybacks"]), [])

    def test_readme_marks_every_required_number(self):
        readme = (Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")
        marked = {m.group(1) for m in bn.MARK.finditer(readme)}
        self.assertEqual([k for k in bn.REQUIRED_IN_README if k not in marked], [])

    def test_render_rewrites_marked_text_only(self):
        text = "a <!--n:n1.coverage_buybacks-->old<!--/n--> b 11%"
        self.assertEqual(bn.render_text(text, self.numbers),
                         "a <!--n:n1.coverage_buybacks-->10.8%<!--/n--> b 11%")
        with self.assertRaises(SystemExit):
            bn.render_text("<!--n:f8.computed_status-->?<!--/n-->", self.numbers)


    def test_control_map(self):
        kn = lambda k, n, role: {"k": k, "n": n, "role": role}
        ms = {"confirmations": 2, "member_keys": 4, "full_access_keys": 0}
        links = {
            "intents_protocol_fee": {"value": {"fee_pips": 1, "fee_percent": "0.0001"},
                                     "fees_manager_grantees": {"public": [], "others": 0, "total": 0},
                                     "via": {"intents.sputnik-dao.near": kn(3, 5, "council")}},
            "intents_code": {"controller": {"add_release": {"intents.sputnik-dao.near": kn(3, 5, "council")},
                                            "updater_grantees": {"total": 1},
                                            "downgrader_grantees": {"total": 2}},
                             "code_changes": 20, "last_upgrade_utc": "2026-10-07T03:53:17.418572403Z",
                             "deployed_version": "0.4.5"},
            "buybacks_wallet": {"multisig": ms},
            "wallet_1cs": {"dao": kn(2, 4, "Approver"), "rules": kn(2, 4, "Admin")},
            "wallet_front_end": {"dao": kn(2, 5, "Approver"), "rules": kn(1, 5, "Admin")},
            "issuance": {"max_inflation_rate": "1/40", "protocol_upgrade_stake_threshold": "4/5",
                         "validators": 381, "validators_to_reach_threshold": 44,
                         "validators_to_block_upgrade": 5, "validators_to_reach_two_thirds": 27,
                         "validators_to_exceed_one_third": 9, "largest_validator_share": "0.056168"},
            "protocol_treasury": {"share_of_new_supply": "0.101432", "balance_change_near": "268972.864",
                                  "reported_protocol_reward_rate": "0/1", "multisig": ms},
            "hsp_voting": {"owner_dao": kn(3, 5, "Admin"), "reviewers": 5, "guardians": 5},
            "nearai_pool_rewards": {"reward_fee": "100/100", "owner_dao": kn(2, 3, "council"),
                                    "owner_rules": kn(2, 3, "council")},
            "farm_contract": {"full_access_keys": 2, "guardians": 5},
        }
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(bn.stakers, "compute", fake_stats), \
                mock.patch.object(bn.daily, "build_row", fake_row):
            data, window = fake_repo(tmp)
            self.assertEqual(bn.build(data, window)[0]["numbers"]["c.intents_fee_change"]["status"],
                             "pending")
            cm = {"block": {"height": B1, "timestamp_utc": "2026-11-01T00:00:00.17Z"},
                  "window_file": f"data/window_{START}_{END}.json",
                  "checks": {"a": True}, "links": links}
            write(data / "control_map.json", cm)
            doc, problems = bn.build(data, window)
            self.assertEqual(problems, [])
            n = doc["numbers"]
            self.assertEqual(n["c.front_end_rules"]["text"], "1 of 5")
            self.assertEqual(n["c.front_end_rules"]["role"], "Admin")
            self.assertEqual(n["c.intents_code_add_release"]["text"], "3 of 5")
            self.assertEqual(n["c.intents_code_updater_accounts"]["text"], "1")
            self.assertEqual(n["c.intents_fee_percent"]["text"], "0.0001%")
            self.assertEqual(n["c.issuance_validators_to_block_upgrade"]["text"], "5")
            self.assertEqual(n["c.issuance_largest_validator_share"]["text"], "5.6%")
            self.assertEqual(n["c.treasury_share_of_new_supply"]["text"], "10.1%")
            self.assertEqual(n["c.treasury_near_received"]["text"], "268,973")
            self.assertEqual(n["c.nearai_pool_reward_fee"]["text"], "100%")
            self.assertEqual(n["c.buybacks_confirmations"]["text"], "2 of 4")
            self.assertIn("data/control_map.json", doc["sources"])
            cm["block"]["height"] = B1 + 1
            cm["checks"]["a"] = False
            write(data / "control_map.json", cm)
            problems = bn.build(data, window)[1]
            self.assertTrue(any("control map block" in p for p in problems))
            self.assertIn("control_map.json: a check failed", problems)

    def test_control_history(self):
        lev = lambda n, first=None, last=None, bm=None: {
            "approved_actions": n, "first": first, "last": last, "by_year": {}, "by_method": bm or {}}
        hist = {"block": {"height": B1, "timestamp_utc": "2026-11-01T00:00:00.17Z"},
                "window_file": f"data/window_{START}_{END}.json", "checks": {"a": True},
                "per_dao": {"x.sputnik-dao.near": {"proposals": 110}, "y.sputnik-dao.near": {"proposals": 17}},
                "all_daos": {"fee": lev(6, "2024-11-07", "2025-10-02", {"intents.near.set_fee": 3}),
                             "user_funds": lev(12, "2025-01-14", "2026-06-10",
                                               {"intents.near.ft_force_withdraw": 9}),
                             "code": lev(0), "roles": lev(0), "pause": lev(0)},
                "intents_code_changes": {"count": 20, "downgrades": 1, "changes": []}}
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(bn.stakers, "compute", fake_stats), \
                mock.patch.object(bn.daily, "build_row", fake_row):
            data, window = fake_repo(tmp)
            self.assertEqual(bn.build(data, window)[0]["numbers"]["h.proposals_total"]["status"],
                             "pending")
            write(data / "control_history.json", hist)
            doc, problems = bn.build(data, window)
            self.assertEqual(problems, [])
            n = doc["numbers"]
            self.assertEqual(n["h.proposals_total"]["text"], "127")
            self.assertEqual(n["h.fee.approved_actions"]["text"], "6")
            self.assertEqual(n["h.fee.last"]["text"], "2025-10-02")
            self.assertEqual(n["h.set_fee"]["text"], "3")
            self.assertEqual(n["h.set_fee_collector"]["text"], "0")
            self.assertEqual(n["h.ft_force_withdraw"]["text"], "9")
            self.assertNotIn("h.code.first", n)
            self.assertEqual(n["h.intents_code_downgrades"]["text"], "1")
            hist["block"]["height"] = B1 + 1
            write(data / "control_history.json", hist)
            self.assertTrue(any("control history block" in p for p in bn.build(data, window)[1]))

    def test_offchain_credit_rate(self):
        import hashlib
        cfg = (b'{"contract_id":"stake.dao","farm_product_id":"%s","farm_price_id":"%s",'
               b'"credit_nano_usd_per_reward_unit":1000000000}'
               % (bn.stakers.FARM_PRODUCT.encode(), bn.stakers.FARM_PRICE.encode()))
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(bn.stakers, "compute", fake_stats), \
                mock.patch.object(bn.daily, "build_row", fake_row):
            data, window = fake_repo(tmp)
            (data / "offchain").mkdir()
            (data / "offchain" / "cfg_2026.json").write_bytes(cfg)
            meta = {"raw_file": "data/offchain/cfg_2026.json", "fetched_utc": "2026-11-01T20:58:37Z",
                    "sha256": hashlib.sha256(cfg).hexdigest()}
            write(data / "offchain" / "nearai_cloud_farm_config.json", meta)
            doc, problems = bn.build(data, window)
            self.assertEqual(problems, [])
            n = doc["numbers"]
            self.assertEqual(n["f6.usd_per_reward_unit"]["text"], "$1.00")
            self.assertEqual(n["f6.usd_per_reward_unit"]["status"], "off-chain")
            self.assertEqual(n["f6.usd_per_near_month"]["text"], "$0.02")
            self.assertEqual(n["f6.largest_usd_per_day"]["text"], "$657.1")
            self.assertNotIn("f6.usd_per_reward_unit", doc["provisional_or_pending"])
            meta["sha256"] = "0" * 64
            write(data / "offchain" / "nearai_cloud_farm_config.json", meta)
            self.assertIn("off-chain NEAR AI Cloud config: sha256 differs from its record",
                          bn.build(data, window)[1])

if __name__ == "__main__":
    unittest.main()
