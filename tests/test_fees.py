"""Tests for scripts/fees.py on fake DefiLlama responses (no network).

Run: python -m unittest discover -s tests
"""
import json
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import fees  # noqa: E402

Y = 10 ** 24
START, END = date(2026, 10, 2), date(2026, 11, 1)
SERIES_FROM = date(2026, 2, 23)
LOW_FEES = date(2026, 10, 22)     # fees 5 on normal volume -> below 20% of median
LOW_BPS = date(2026, 10, 30)      # normal fees on 5x volume -> below half the median bps
HIGH_PRICE = date(2026, 10, 10)   # price 4 instead of 2


def ts(d, hour=0):
    return int(datetime(d.year, d.month, d.day, hour, tzinfo=timezone.utc).timestamp())


def day_values(d):
    fee, vol, price = 100, 1_000_000, 2
    if d == LOW_FEES:
        fee = 5
    if d == LOW_BPS:
        vol = 5_000_000
    if d == HIGH_PRICE:
        price = 4
    return fee, 30 * fee / 100, vol, price


def fake_raws(drop=None, fee_override=None):
    days = [SERIES_FROM + timedelta(days=i) for i in range((END - SERIES_FROM).days)]
    chart = {"fees": [], "revenue": [], "volume": []}
    prices = []
    for d in days:
        fee, rev, vol, price = day_values(d)
        if fee_override and d in fee_override:
            fee = fee_override[d]
        if d != drop:
            chart["fees"].append([ts(d), fee])
        chart["revenue"].append([ts(d), rev])
        chart["volume"].append([ts(d), vol])
        if d >= fees.MONTHLY_FROM:
            prices.append({"timestamp": ts(d, 12), "price": float(price)})
    raws = {k: json.dumps({"name": "NEAR Intents", "totalDataChart": v}).encode()
            for k, v in chart.items()}
    raws["price"] = json.dumps({"coins": {fees.PRICE_ID: {"symbol": "NEAR", "confidence": 0.99,
                                                          "prices": prices}}}).encode()
    return raws


def fake_window():
    # supply grows exactly 100 NEAR per day over the 30 days
    return {"window": {"start": START.isoformat(), "end": END.isoformat(), "days": 30,
                       "boundaries": 31, "rule": "test"},
            "boundaries": [{"date": START.isoformat(), "height": 1000,
                            "total_supply_yocto": str(1_300_000_000 * Y)},
                           {"date": END.isoformat(), "height": 2000,
                            "total_supply_yocto": str(1_300_000_000 * Y + 3000 * Y)}]}


def fetcher(raws):
    def f(url):
        if "coins.llama.fi" in url:
            return raws["price"]
        if "dataType=dailyFees" in url:
            return raws["fees"]
        if "dataType=dailyRevenue" in url:
            return raws["revenue"]
        return raws["volume"]
    return f


class FeesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name) / "data"
        self.data.mkdir()
        self.window = self.data / f"window_{START}_{END}.json"
        self.window.write_text(json.dumps(fake_window()), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def run_once(self, raws, now=datetime(2026, 11, 2, 9, tzinfo=timezone.utc)):
        return fees.run(self.window, self.data, fetch=fetcher(raws), check_window=False, now=now)

    def test_number_2_matches_hand_computation(self):
        out, doc = self.run_once(fake_raws())
        w = doc["result"]["window"]
        self.assertEqual(w["counted_days"], 28)
        self.assertEqual(set(w["excluded"]), {LOW_FEES.isoformat(), LOW_BPS.isoformat()})
        self.assertEqual(w["excluded"][LOW_FEES.isoformat()], "fees_below_20pct_of_median")
        self.assertEqual(w["excluded"][LOW_BPS.isoformat()], "fees_per_volume_below_half_of_median")
        self.assertEqual(w["new_near_per_day"], "100.000")
        # 27 days buy 50 NEAR, one day (price 4) buys 25; supply 100 per day
        cover = Fraction(27 * 50 + 25, 28) / 100
        self.assertEqual(w["max_coverage"], fees.fmt(cover, 6))
        self.assertEqual(w["equilibrium_price_usd"], "1.0000")
        self.assertEqual(w["fees_bps"], "1.00")
        self.assertEqual(w["take_rate"], "0.300000")
        self.assertEqual(w["hsp029_scenario_max_coverage"], fees.fmt(cover * 25 / 16, 6))
        self.assertEqual(w["hsp029_scenario_equilibrium_price_usd"], "1.5625")
        self.assertEqual(w["fees_weighted_price_usd"], fees.fmt(Fraction(2800, 27 * 50 + 25), 4))
        # monthly table: March .. October, October full
        months = doc["result"]["monthly"]
        self.assertEqual([m["month"] for m in months][0], "2026-03")
        self.assertEqual(months[-1]["month"], "2026-10")
        self.assertTrue(months[-1]["full_month"])
        self.assertEqual(months[-1]["days"], 31)
        self.assertEqual(fees.verify(out, check_window=False), [])

    def test_tampered_raw_is_caught(self):
        out, doc = self.run_once(fake_raws())
        p = self.data.parent / doc["raw"]["fees"]["path"]
        p.write_bytes(p.read_bytes().replace(b"100]", b"101]", 1))
        problems = fees.verify(out, check_window=False)
        self.assertTrue(any("sha256" in x for x in problems))

    def test_missing_window_day_stops(self):
        with self.assertRaises(SystemExit):
            self.run_once(fake_raws(drop=date(2026, 10, 15)))

    def test_revision_between_fetches_is_listed(self):
        self.run_once(fake_raws(), now=datetime(2026, 11, 1, 9, tzinfo=timezone.utc))
        _, doc = self.run_once(fake_raws(fee_override={LOW_BPS: 500}))
        revs = doc["revisions_vs_previous_fetch"]
        self.assertEqual([r["date"] for r in revs], [LOW_BPS.isoformat()])
        self.assertEqual(revs[0]["fees_usd"], ["100.00", "500.00"])

    def test_price_far_from_noon_is_rejected(self):
        raw = json.dumps({"coins": {fees.PRICE_ID: {"prices": [
            {"timestamp": ts(START, 3), "price": 2.0}]}}}).encode()
        with self.assertRaises(ValueError):
            fees.price_series(raw)

    def test_fmt(self):
        self.assertEqual(fees.fmt(Fraction(1, 3), 4), "0.3333")
        self.assertEqual(fees.fmt(Fraction(-5, 2), 0), "-2")
        self.assertEqual(fees.fmt(Fraction(2675, 1000), 2), "2.68")


if __name__ == "__main__":
    unittest.main()
