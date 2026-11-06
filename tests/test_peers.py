"""Tests for scripts/peers.py on simulated DefiLlama and CoinGecko answers (no network).

Run: python -m unittest discover -s tests
"""
import json
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import fees as fz  # noqa: E402
import peers  # noqa: E402

DAYS = peers.window_days()


def chart(per_day, extra_days=3, skip=()):
    first = DAYS[0] - timedelta(days=extra_days)
    out, d = [], first
    while d <= DAYS[-1] + timedelta(days=extra_days):
        if d not in skip:
            out.append([(d - fz.EPOCH).days * fz.DAY, per_day if d in DAYS else 999999])
        d += timedelta(days=1)
    return json.dumps({"name": "x", "totalDataChart": out}).encode()


MARKETS = json.dumps([
    {"id": "ethereum", "current_price": 3000, "market_cap": 360000000000, "fully_diluted_valuation": 360000000000,
     "last_updated": "2026-11-06T12:00:00Z"},
    {"id": "near", "current_price": 4.9, "market_cap": 6000000000, "fully_diluted_valuation": 6400000000,
     "last_updated": "2026-11-06T12:00:00Z"},
    {"id": "hyperliquid", "current_price": 40, "market_cap": 13000000000, "fully_diluted_valuation": 40000000000,
     "last_updated": "2026-11-06T12:00:00Z"},
    {"id": "aave", "current_price": 200, "market_cap": 3000000000, "fully_diluted_valuation": 3200000000,
     "last_updated": "2026-11-06T12:00:00Z"},
    {"id": "jupiter-exchange-solana", "current_price": 0.5, "market_cap": 1500000000,
     "fully_diluted_valuation": 5000000000, "last_updated": "2026-11-06T12:00:00Z"},
]).encode()


FETCH_PRICE = {"ethereum": 3000, "near": 4.9, "hyperliquid": 40, "aave": 200, "jupiter-exchange-solana": 0.5}


def prices(gid, skip=()):
    """Daily 12:00 UTC prices: twice the fetch price on the window's days, 7 outside them."""
    base = Decimal(str(FETCH_PRICE.get(gid, 1))) * 2
    out, d = [], DAYS[0] - timedelta(days=2)
    while d <= DAYS[-1] + timedelta(days=2):
        if d not in skip:
            out.append({"timestamp": (d - fz.EPOCH).days * fz.DAY + fz.DAY // 2,
                        "price": float(base) if d in DAYS else 7})
        d += timedelta(days=1)
    return json.dumps({"coins": {f"coingecko:{gid}": {"symbol": "X", "prices": out}}}).encode()


def fake_fetch(url):
    if "coins.llama.fi" in url:
        return prices(url.split("coingecko:")[1].split("?")[0])
    if "coingecko" in url:
        return MARKETS
    if "near-intents" in url and "HoldersRevenue" in url:
        raise RuntimeError(f"HTTP 404 from {url}")
    per_day = {"dailyFees": 1000, "dailyRevenue": 400, "dailyHoldersRevenue": 300}[url.split("dataType=")[1].split("&")[0]]
    return chart(per_day)


class PeersTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "data").mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_fake(self):
        return peers.run(self.tmp / "data", fetch=fake_fetch, now=datetime(2026, 11, 6, 12, tzinfo=timezone.utc))

    def test_only_the_window_days_count_and_ratios(self):
        r = self.run_fake()["results"]["aave"]
        self.assertEqual(r["days"], {"fees": 30, "revenue": 30, "holders_revenue": 30, "price": 30})
        self.assertEqual(Decimal(r["revenue_usd_per_year"]), Decimal(400) * Decimal("365.25"))
        # value at the window's mean price: the fetch's supply (3e9 / $200) x the mean price ($400)
        self.assertEqual(Decimal(r["mean_price_usd"]), Decimal(400))
        self.assertEqual(Decimal(r["market_cap_usd"]), Decimal(6000000000))
        self.assertEqual(Decimal(r["mcap_to_revenue"]), Decimal(6000000000) / (Decimal(400) * Decimal("365.25")))
        self.assertEqual(Decimal(r["mcap_at_fetch_to_revenue"]), Decimal(3000000000) / (Decimal(400) * Decimal("365.25")))
        self.assertTrue(r["complete"])

    def test_a_series_not_published_is_missing_not_zero(self):
        doc = self.run_fake()
        near = doc["results"]["near"]
        self.assertIsNone(near["holders_revenue_usd_per_year"])
        self.assertIsNone(near["holders_yield_on_mcap"])
        self.assertIn("near_holders_revenue", doc["not_published"])

    def test_verify_offline_and_tamper(self):
        self.run_fake()
        out = self.tmp / "data" / peers.OUT_NAME
        self.assertEqual(peers.verify(out)[0], [])
        doc = json.loads(out.read_text(encoding="utf-8"))
        p = self.tmp / doc["raw_files"]["aave_revenue"]["path"]
        p.write_bytes(p.read_bytes().replace(b"400", b"401"))
        self.assertTrue(any("sha256 differs" in x for x in peers.verify(out)[0]))

    def test_near_all_adds_intents_and_gas_against_one_market_cap(self):
        r = self.run_fake()["results"]
        self.assertEqual(Decimal(r["near_all"]["fees_usd_per_year"]),
                         Decimal(r["near"]["fees_usd_per_year"]) + Decimal(r["near_l1"]["fees_usd_per_year"]))
        self.assertEqual(r["near_all"]["market_cap_usd"], r["near"]["market_cap_usd"])
        self.assertIsNone(r["near_all"]["holders_revenue_usd_per_year"])  # Intents' holders series is missing here

    def test_a_token_with_no_market_entry_has_no_ratios(self):
        r = self.run_fake()["results"]["sui"]
        self.assertIsNone(r["market_cap_usd"])
        self.assertIsNone(r["mcap_to_revenue"])
        self.assertFalse(r["partial"])

    def test_price_days_outside_the_window_do_not_count(self):
        mean, n = peers.mean_price(prices("aave", skip={DAYS[5]}), "aave")
        self.assertEqual((mean, n), (Decimal(400), 29))

    def test_missing_days_mark_incomplete(self):
        mean, n = peers.flow(chart(1000, skip={DAYS[3]}))
        self.assertEqual((mean, n), (Decimal(1000), 29))

    def test_refused_network_stops(self):
        def refuse(url):
            raise RuntimeError(f"the network refused the connection to {url} (Forbidden)")
        with self.assertRaises(RuntimeError):
            peers.run(self.tmp / "data", fetch=refuse)


if __name__ == "__main__":
    unittest.main()
