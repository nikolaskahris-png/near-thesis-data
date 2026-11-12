"""Tests for scripts/rating.py: the rating rules on made-up windows, the real 2026-11-01 window
against numbers.json, and the offline check (no network).

Run: python -m unittest discover -s tests
"""
import csv
import json
import shutil
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from fractions import Fraction
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import rating  # noqa: E402

TH = {"avoid_usd_per_day": "6270", "base_usd_per_day": "46692", "base_near_per_day": "9570",
      "growth_with_hsp029": "0.56", "growth_without_hsp029": "0.75"}
LATE = datetime(2030, 1, 1, tzinfo=timezone.utc)


def series(first, last, revenue=1000, price=4):
    s = {k: {} for k in rating.SERIES}
    d = first
    while d <= last:
        s["fees"][d], s["revenue"][d], s["volume"][d] = Fraction(3000), Fraction(revenue), Fraction(10 ** 6)
        s["price"][d] = Fraction(price)
        d += timedelta(days=1)
    return s


def hist(d, kept=250, fe=0, cov="0.108", new=88000):
    return {"date": d.isoformat(), "window_start": (d - timedelta(days=30)).isoformat(),
            "buybacks_per_day": str(kept), "fefunds_per_day": str(fe),
            "coverage_buybacks": cov, "new_supply_per_day": str(new)}


D1, D2 = date(2026, 11, 1), date(2026, 12, 1)
S = series(date(2026, 9, 1), date(2026, 12, 31))   # revenue 1000 USD at $4 = 250 NEAR a day


class Rules(unittest.TestCase):
    def run_rows(self, rows, s=S, locks=(), fetched=LATE, th=TH, sealed=None, quiet=None):
        if sealed is None:      # by default a lock given here is sealed in every window
            sealed = {r["date"]: list(locks) for r in rows}
        if quiet is None:       # by default treasury.near sent nothing in any window
            quiet = {r["date"]: "yes" for r in rows}
        return {r["date"]: r for r in rating.evaluate(rows, s, th, fetched, sealed, quiet)}

    def stock_rows(self, first, last, start, per_day, moves):
        """Daily rows from first to last; the stock grows per_day and moves {date: NEAR} change it."""
        rows, stock, d = [], Fraction(start), first
        while d <= last:
            stock += per_day + moves.get(d, 0)
            rows.append(dict(hist(d), buybacks_end=f"{int(stock)}.000"))
            d += timedelta(days=1)
        return rows

    def test_drain_of_the_whole_stock_is_avoid_at_once_and_stays(self):
        # judge #21, finding 1: 10,000 NEAR a day, all of it moved out in one transfer on 20 Nov
        rows = self.stock_rows(D1, date(2027, 2, 1), 2_145_248, 10_000, {date(2026, 11, 20): -2_300_000})
        out = self.run_rows(rows, th={**TH, "avoid_usd_per_day": "900"})
        before = [r for d, r in out.items() if d < "2026-11-20"]
        after = [r for d, r in out.items() if d >= "2026-11-20"]
        self.assertEqual({r["rating"] for r in before}, {"Hold"})
        self.assertEqual({r["rating"] for r in after}, {"Avoid"})        # 74 days, none Hold
        self.assertEqual(after[0]["test_stock"], "fail")
        self.assertIn("drain test", after[0]["note"])

    def test_a_fall_of_ten_percent_or_less_is_not_a_drain(self):
        rows = self.stock_rows(D1, date(2026, 11, 30), 1_000_000, 0, {date(2026, 11, 10): -100_000})
        out = self.run_rows(rows, th={**TH, "avoid_usd_per_day": "900"})
        self.assertEqual(out["2026-11-10"]["test_stock"], "pass")          # exactly 10% below: not more
        self.assertEqual({r["rating"] for r in out.values()}, {"Hold"})

    def test_avoid_ends_when_the_stock_is_back_within_ten_percent(self):
        rows = self.stock_rows(D1, date(2026, 11, 30), 1_000_000, 0,
                               {date(2026, 11, 10): -200_000, date(2026, 11, 15): 150_000})
        out = self.run_rows(rows, th={**TH, "avoid_usd_per_day": "900"})
        self.assertEqual([out[f"2026-11-{d:02d}"]["rating"] for d in (9, 10, 14, 15)], ["Hold", "Avoid", "Avoid", "Hold"])
        self.assertEqual(out["2026-11-15"]["stock_peak_near"], "1000000.000")

    def test_a_drain_overrides_buy(self):
        rows = self.stock_rows(D1, date(2026, 11, 5), 1_000_000, 0, {date(2026, 11, 3): -500_000})
        s = series(date(2026, 9, 1), date(2026, 12, 31), revenue=400000)
        s["fees"] = dict.fromkeys(s["fees"], Fraction(400000))     # coverage counted: 90,000 of 88,000 issued
        out = self.run_rows([dict(r, buybacks_per_day="90000") for r in rows], locks=("lock.near",),
                            th={**TH, "avoid_usd_per_day": "900"}, s=s)
        self.assertEqual((out["2026-11-02"]["rating"], out["2026-11-03"]["rating"]), ("Buy", "Avoid"))

    def test_rows_without_a_stock_are_not_judged(self):
        r = self.run_rows([hist(D1)])["2026-11-01"]
        self.assertEqual((r["test_stock"], r["stock_near"]), ("not judged", ""))

    def test_healthy_window_is_hold(self):
        # kept 250 of 250 NEAR of revenue; 250 NEAR x $4 = $1,000 a day, above a $900 floor
        r = self.run_rows([hist(D1)], th={**TH, "avoid_usd_per_day": "900"})["2026-11-01"]
        self.assertEqual((r["kept_share"], r["test_kept_share"], r["test_usd"], r["rating"]),
                         ("1.000000", "pass", "pass", "Hold"))
        self.assertEqual(r["earlier_window"], "not in history")

    def test_one_failing_window_is_still_hold(self):
        r = self.run_rows([hist(D1, kept=100)], th={**TH, "avoid_usd_per_day": "100"})["2026-11-01"]
        self.assertEqual((r["test_kept_share"], r["rating"]), ("fail", "Hold"))
        self.assertIn("earlier window", r["note"])

    def test_two_failing_windows_in_a_row_is_avoid(self):
        rows = self.run_rows([hist(D1, kept=100), hist(D2, kept=100)], th={**TH, "avoid_usd_per_day": "100"})
        self.assertEqual(rows["2026-12-01"]["earlier_window"], "fail")
        self.assertEqual(rows["2026-12-01"]["rating"], "Avoid")

    def test_usd_floor_alone_fails_a_window(self):
        rows = self.run_rows([hist(D1), hist(D2)])          # $1,000 a day <= $6,270
        self.assertEqual((rows["2026-12-01"]["test_kept_share"], rows["2026-12-01"]["test_usd"]), ("pass", "fail"))
        self.assertEqual(rows["2026-12-01"]["rating"], "Avoid")

    def test_buy_needs_rule_b(self):
        # 250 NEAR kept a day, all of DefiLlama's revenue (250) and under its fees (750), 245 issued
        th = {**TH, "avoid_usd_per_day": "100"}
        self.assertEqual(self.run_rows([hist(D1, cov="1.02", new=245)], th=th)["2026-11-01"]["rating"], "Hold")
        r = self.run_rows([hist(D1, cov="1.02", new=245)], th=th, locks=["lock.near"])["2026-11-01"]
        self.assertEqual((r["rule_b"], r["covers_issuance"], r["rating"]), ("yes", "yes", "Buy"))

    def test_rule_b_counts_only_from_the_window_where_the_chain_shows_it(self):
        # Judge #9, finding 2: (b) is read per window from the chain, so it never flips past rows
        th = {**TH, "avoid_usd_per_day": "100"}
        rows = self.run_rows([hist(D1, cov="1.02", new=245), hist(D2, cov="1.02", new=245)], th=th,
                             sealed={"2026-11-01": [], "2026-12-01": ["lock.near"]})
        self.assertEqual((rows["2026-11-01"]["rule_b"], rows["2026-11-01"]["rating"]), ("no", "Hold"))
        self.assertEqual((rows["2026-12-01"]["rule_b"], rows["2026-12-01"]["rating"]), ("yes", "Buy"))

    def test_inflows_that_are_not_fees_cannot_make_buy(self):
        # Judge #9, finding 1: a transfer of 2.4M NEAR from another wallet lifts the balance change above
        # issuance (coverage 1.14), but coverage counted is capped by DefiLlama's revenue: 250 / 88,000
        th = {**TH, "avoid_usd_per_day": "100"}
        r = self.run_rows([hist(D1, kept=100000, cov="1.14")], th=th, locks=["lock.near"])["2026-11-01"]
        self.assertEqual((r["coverage_counted"], r["covers_issuance"], r["rating"]), ("0.002841", "no", "Hold"))
        # and by the fees: revenue above fees (not seen so far) still cannot lift it past them
        s = series(date(2026, 9, 1), date(2026, 12, 31), revenue=10 ** 6)
        r = self.run_rows([hist(D1, kept=100000, cov="1.14")], s=s, th=th, locks=["lock.near"])["2026-11-01"]
        self.assertEqual((r["coverage_counted"], r["rating"]), ("0.008523", "Hold"))

    def test_treasury_transfer_cannot_make_buy(self):
        # Research 7/11, risk A: DefiLlama counts a transfer from treasury.near as revenue, so only the fee
        # cap would limit it. A window where treasury.near's request nonce moved, or that was not read,
        # cannot reach Buy, by coverage or by (a).
        th = {**TH, "avoid_usd_per_day": "100"}
        for q in ("no", "not read"):
            r = self.run_rows([hist(D1, cov="1.02", new=245)], th=th, locks=["lock.near"],
                              quiet={"2026-11-01": q})["2026-11-01"]
            self.assertEqual((r["treasury_quiet"], r["covers_issuance"], r["rating"]), (q, "yes", "Hold"))
        y1 = date(2027, 11, 1)
        s = series(date(2027, 9, 1), date(2027, 11, 30), revenue=100000, price=5)
        r = self.run_rows([hist(y1, kept=17000, cov="0.2")], s=s, locks=["lock.near"],
                          quiet={"2027-11-01": "no"})["2027-11-01"]
        self.assertEqual((r["yearly_a"], r["rating"]), ("fail", "Hold"))

    def test_zero_revenue_leaves_test_2_alone(self):
        # Research 7/11, risk B: if the fees leave DefiLlama's view, test 1 is not judged; the on-chain
        # dollar test decides. Here it passes, so no window fails.
        s = series(date(2026, 9, 1), date(2026, 12, 31), revenue=0)
        rows = self.run_rows([hist(D1), hist(D2)], s=s, th={**TH, "avoid_usd_per_day": "100"})
        r = rows["2026-12-01"]
        self.assertEqual((r["test_kept_share"], r["test_usd"], r["earlier_window"], r["rating"]),
                         ("not judged", "pass", "pass", "Hold"))
        # and if the dollars fall to the floor in both windows, Avoid fires on test 2 alone
        rows = self.run_rows([hist(D1), hist(D2)], s=s)
        self.assertEqual((rows["2026-12-01"]["test_usd"], rows["2026-12-01"]["rating"]), ("fail", "Avoid"))

    def test_private_path_growth_leaves_test_2_unjudged(self):
        # Judge #13, finding 7: the buybacks' dollars fall to the floor while DefiLlama's fees fall too and
        # the Confidential Intents Treasury account grows: capture may have moved to FAR, so no fail.
        s = series(date(2026, 9, 1), date(2026, 12, 31))
        for d in s["fees"]:
            if d >= date(2026, 11, 1):
                s["fees"][d] = Fraction(1000)          # fees fall in the second window
        grow = {"2026-10-02": Fraction(10), "2026-11-01": Fraction(20), "2026-12-01": Fraction(30)}
        flat = {"2026-10-02": Fraction(10), "2026-11-01": Fraction(10), "2026-12-01": Fraction(10)}
        def run(stables):
            return {r["date"]: r for r in rating.evaluate([hist(D1), hist(D2)], s, TH, LATE,
                                                            {}, {}, stables=stables)}
        r = run(grow)
        # D1 has no earlier window to compare fees with, and the account grew: not judged either
        self.assertEqual((r["2026-11-01"]["test_usd"], r["2026-12-01"]["test_usd"], r["2026-12-01"]["rating"]),
                         ("not judged", "not judged", "Hold"))
        self.assertIn("private path", r["2026-12-01"]["note"])
        r = run(flat)                                   # the account did not grow: capture stopped
        self.assertEqual((r["2026-12-01"]["test_usd"], r["2026-12-01"]["rating"]), ("fail", "Avoid"))
        r = run({})                                     # not read: evidence is needed, so still a fail
        self.assertEqual((r["2026-12-01"]["test_usd"], r["2026-12-01"]["rating"]), ("fail", "Avoid"))

    def test_steady_fees_keep_test_2_a_fail_whatever_far_holds(self):
        grow = {"2026-10-02": Fraction(10), "2026-11-01": Fraction(20), "2026-12-01": Fraction(30)}
        rows = {r["date"]: r for r in rating.evaluate([hist(D1), hist(D2)], S, TH, LATE, {}, {}, stables=grow)}
        self.assertEqual((rows["2026-12-01"]["test_usd"], rows["2026-12-01"]["rating"]), ("fail", "Hold"))
        self.assertEqual(rows["2026-11-01"]["test_usd"], "not judged")   # no earlier window: fees not comparable

    def test_missing_defillama_day_leaves_test_2_alone(self):
        s = series(date(2026, 9, 1), date(2026, 12, 31))
        for d in (date(2026, 10, 15), date(2026, 11, 15)):
            del s["revenue"][d]
        rows = self.run_rows([hist(D1), hist(D2)], s=s)      # $1,000 a day <= $6,270 in both
        r = rows["2026-12-01"]
        self.assertEqual((r["status"], r["test_kept_share"], r["test_usd"], r["rating"]),
                         ("incomplete", "not judged", "fail", "Avoid"))

    def test_incomplete_window_does_not_judge_coverage(self):
        s = series(date(2026, 9, 1), date(2026, 12, 31))
        del s["fees"][date(2026, 10, 15)]
        r = self.run_rows([hist(D1, cov="1.02", new=245)], s=s, locks=["lock.near"])["2026-11-01"]
        self.assertEqual((r["covers_issuance"], r["rating"]), ("not judged", "Hold"))

    def test_avoid_overrides_buy(self):
        rows = self.run_rows([hist(D1, kept=100, cov="1.02", new=98), hist(D2, kept=100, cov="1.02", new=98)],
                             th={**TH, "avoid_usd_per_day": "100"}, locks=["lock.near"])
        self.assertEqual(rows["2026-12-01"]["rating"], "Avoid")
        self.assertIn("Avoid overrides", rows["2026-12-01"]["note"])

    def test_missing_day_is_incomplete_and_not_judged(self):
        s = series(date(2026, 9, 1), date(2026, 12, 31))
        del s["price"][date(2026, 10, 15)]
        rows = self.run_rows([hist(D1, kept=100), hist(D2, kept=100)], s=s, th={**TH, "avoid_usd_per_day": "100"})
        self.assertEqual((rows["2026-11-01"]["status"], rows["2026-11-01"]["rating"]), ("incomplete", "Hold"))
        self.assertEqual((rows["2026-12-01"]["earlier_window"], rows["2026-12-01"]["rating"]), ("not judged", "Hold"))

    def test_price_fall_with_steady_dollars_reaches_buy(self):
        # Judge #8: at a lower price the same dollars buy more NEAR; coverage >= 100% and the dollar test
        # passes, so with (b) the rating is Buy. Here $1,000 a day at $0.25 = 4,000 NEAR, all of issuance.
        s = series(date(2026, 9, 1), date(2026, 12, 31), revenue=1000, price=Fraction(1, 4))
        r = self.run_rows([hist(D1, kept=4000, cov="1.0", new=4000)], s=s, locks=["lock.near"],
                          th={**TH, "avoid_usd_per_day": "900"})["2026-11-01"]
        self.assertEqual((r["test_usd"], r["test_kept_share"], r["rating"]), ("pass", "pass", "Buy"))

    def test_recent_window_is_provisional(self):
        r = self.run_rows([hist(D1)], fetched=datetime(2026, 11, 2, 0, 15, tzinfo=timezone.utc))["2026-11-01"]
        self.assertEqual(r["status"], "provisional")

    def test_yearly_check_a(self):
        y1 = date(2027, 11, 1)
        s = series(date(2027, 9, 1), date(2027, 11, 30), revenue=100000, price=5)
        # without HSP-029 the hurdle is +75% a year: 9,570 -> 16,748 NEAR and 46,692 -> 81,711 USD a day;
        # 17,000 NEAR at $5 passes both, 16,000 NEAR fails the NEAR leg
        r = self.run_rows([hist(y1, kept=17000, cov="0.2")], s=s, locks=["lock.near"])["2027-11-01"]
        self.assertEqual((r["yearly_a"], r["rating"]), ("pass", "Buy"))
        # a pass holds until the next yearly check, not just on its own day
        rows = self.run_rows([hist(y1, kept=17000, cov="0.2"), hist(y1 + timedelta(days=1), kept=17000, cov="0.2")],
                             s=s, locks=["lock.near"])
        self.assertEqual((rows["2027-11-02"]["yearly_a"], rows["2027-11-02"]["rating"]), ("pass since 2027-11-01", "Buy"))
        r = self.run_rows([hist(y1, kept=16000, cov="0.2")], s=s, locks=["lock.near"])["2027-11-01"]
        self.assertEqual((r["yearly_a"], r["rating"]), ("fail", "Hold"))
        self.assertEqual(self.run_rows([hist(D1)])["2026-11-01"]["yearly_a"], "")


class RealWindow(unittest.TestCase):
    """The committed 2026-11-01 row must reproduce the README's figures from numbers.json."""

    def test_2026_11_01_matches_numbers_json(self):
        with open(REPO / "data" / "rating.csv", encoding="utf-8", newline="") as f:
            row = next(r for r in csv.DictReader(f) if r["date"] == "2026-11-01")
        n = json.loads((REPO / "data" / "numbers.json").read_text(encoding="utf-8"))
        n = n.get("numbers", n)
        self.assertEqual(row["status"], "final")
        self.assertEqual(row["max_coverage_defillama"], n["n2.max_coverage"]["value"])
        self.assertLess(abs(Fraction(row["buybacks_kept_usd_per_day"])
                            - Fraction(n["iv.buybacks_kept_usd_per_day"]["value"])), 1)
        self.assertEqual(f"${float(Fraction(row['mean_price_usd'])):.2f}", n["n2.mean_price_usd"]["text"])
        self.assertEqual(row["rating"], "Hold")

    def test_committed_rating_verifies(self):
        self.assertEqual(rating.verify(REPO / "data"), [])


class Verify(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.data = self.tmp / "data"
        (self.data / "raw" / "x").mkdir(parents=True)
        shutil.copy(REPO / "data" / "history.csv", self.data / "history.csv")
        shutil.copy(REPO / "data" / "numbers.json", self.data / "numbers.json")
        shutil.copy(REPO / "data" / rating.CT_FILE, self.data / rating.CT_FILE)
        doc = json.loads((REPO / "data" / "rating.json").read_text(encoding="utf-8"))
        for name in rating.SERIES:
            shutil.copy(REPO / doc["raw"][name]["path"], self.data / "raw" / "x" / f"{name}.json")
        rating.build(self.data, self.data / "raw" / "x", doc["fetched_utc"], {})

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_clean_copy_verifies(self):
        self.assertEqual(rating.verify(self.data), [])

    def test_edited_treasury_file_fails(self):
        p = self.data / rating.CT_FILE
        p.write_bytes(p.read_bytes() + b" ")
        self.assertTrue(any("private_path" in x for x in rating.verify(self.data)))

    def test_daily_treasury_file_extends_the_series(self):
        doc = {"series": [{"date": "2026-11-09", "by_group_usd": {"stablecoins": "1"}}]}
        (self.data / rating.CT_DAILY).write_text(json.dumps(doc), encoding="utf-8")
        self.assertTrue(any("private_path" in x for x in rating.verify(self.data)))   # a new file must be recorded
        st = rating.treasury_stablecoins(self.data)
        self.assertEqual((st["2026-11-09"], "2026-11-08" in st), (Fraction(1), True))

    def test_edited_csv_fails(self):
        p = self.data / "rating.csv"
        p.write_text(p.read_text(encoding="utf-8").replace(",Hold,", ",Buy,", 1), encoding="utf-8", newline="")
        self.assertTrue(rating.verify(self.data))

    def test_offline_rebuild_after_a_new_history_row(self):
        h = self.data / "history.csv"
        lines = h.read_text(encoding="utf-8").splitlines()
        last = lines[-1].split(",")
        d = date.fromisoformat(last[0]) + timedelta(days=1)
        last[0], last[1] = d.isoformat(), (d - timedelta(days=30)).isoformat()
        h.write_text("\n".join(lines + [",".join(last)]) + "\n", encoding="utf-8", newline="")
        self.assertTrue(rating.verify(self.data))            # the new row is not in rating.csv yet
        doc = json.loads((self.data / "rating.json").read_text(encoding="utf-8"))
        rating.build(self.data, (self.tmp / doc["raw"]["fees"]["path"]).parent, doc["fetched_utc"], {})
        self.assertEqual(rating.verify(self.data), [])
        with open(self.data / "rating.csv", encoding="utf-8", newline="") as f:
            self.assertEqual(list(csv.DictReader(f))[-1]["status"], "incomplete")

    def test_edited_raw_fails(self):
        p = self.data / "raw" / "x" / "revenue.json"
        p.write_bytes(p.read_bytes() + b" ")
        self.assertTrue(any("sha256" in x for x in rating.verify(self.data)))


if __name__ == "__main__":
    unittest.main()
