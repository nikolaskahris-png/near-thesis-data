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
                   "boundaries": [{"height": B0}, {"height": B1}]})
    cols = ("date,window_start,block_start,block_end,block_end_utc,total_supply_start,"
            "total_supply_end,new_supply_per_day,buybacks_start,buybacks_end,buybacks_per_day,"
            "fefunds_start,fefunds_end,fefunds_per_day,coverage_buybacks,coverage_with_fe,"
            "max_coverage_defillama,near_ai_stakers,near_ai_top_share,flags")
    (data / "history.csv").write_text(
        cols + f"\n{END},{START},{B0},{B1},x,1,2,88392.087,0,0,9569.750,0,0,4984.673,"
        "0.108265,0.164658,,,,\n", encoding="utf-8")
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
           "final": {"ready": False}, "result": {"window": fw}})
    write(data / "stakers" / f"{END}.json", {"stub": stakers_block})
    write(data / "coverage_monthly.json", {"rows": [
        {"month": "2026-10", "block_start": 1, "block_end": B1,
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


def fake_stats(path, data_root):
    block = json.loads(Path(path).read_text())["stub"]
    return ({"date": Path(path).stem, "block": block, "stakers_active": 112,
             "stakers_ever": 188, "stakers_left": 76, "left_share_of_ever": "0.404255",
             "largest_share": "0.732951", "largest_near": "1000000.000",
             "top10_share": "0.964371", "farm_total_near": "1364347.600",
             "outside_top10_accounts": 102, "outside_top10_near": "48610.600",
             "outside_top10_median_near": "60.000", "agents_locks": 86,
             "agents_locks_past_end": 75, "farm_or_active_lock_accounts": 145,
             "farm_or_any_lock_accounts": 181}, [])


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
                mock.patch.object(bn.stakers, "compute", fake_stats):
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
            self.assertFalse(doc["complete"])
            self.assertIn("n2.max_coverage", doc["provisional_or_pending"])
            self.assertIn("history.csv", " ".join(doc["sources"]))

            out = data / bn.OUT_NAME
            out.write_text(json.dumps(doc), encoding="utf-8")
            self.assertEqual(bn.verify(out, run_scripts=False), [])
            (data / "history.csv").write_text((data / "history.csv").read_text() + "\n")
            self.assertTrue(any("source changed" in p for p in bn.verify(out, run_scripts=False)))

    def test_refuses_inputs_from_another_window(self):
        for kwargs in ({"fees_end_block": B1 + 1}, {"treasury_end": B1 - 7},
                       {"stakers_block": 1}):
            with tempfile.TemporaryDirectory() as tmp, \
                    mock.patch.object(bn.stakers, "compute", fake_stats):
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

    def test_render_rewrites_marked_text_only(self):
        text = "a <!--n:n1.coverage_buybacks-->old<!--/n--> b 11%"
        self.assertEqual(bn.render_text(text, self.numbers),
                         "a <!--n:n1.coverage_buybacks-->10.8%<!--/n--> b 11%")
        with self.assertRaises(SystemExit):
            bn.render_text("<!--n:f8.computed_status-->?<!--/n-->", self.numbers)


if __name__ == "__main__":
    unittest.main()
