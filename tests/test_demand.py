"""Tests for scripts/demand.py on simulated DefiLlama answers (no network)."""
import json
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import demand  # noqa: E402

DEXS = json.dumps({"protocols": [
    {"slug": "near-intents", "name": "NEAR Intents", "category": "Bridge", "total30d": 4000},
    {"slug": "unit", "name": "Unit", "category": "Bridge", "total30d": 2000},
    {"slug": "dead", "name": "Dead", "category": "Bridge", "total30d": 0},
    {"slug": "uni", "name": "Uni", "category": "Dexs", "total30d": 10 ** 9},
]}).encode()
AGG = json.dumps({"protocols": [
    {"slug": "lifi", "name": "LI.FI", "category": "Bridge Aggregator", "total30d": 1500},
    {"slug": "zrx", "name": "0x", "category": "Bridge Aggregator", "total30d": 1100},
    {"slug": "none", "name": "None", "category": "Bridge Aggregator", "total30d": None},
]}).encode()


def fake_fetch(url):
    return AGG if "bridge-aggregators" in url else DEXS


class DemandTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "data").mkdir()
        self.doc = demand.run(self.tmp / "data", fetch=fake_fetch, now=datetime(2026, 11, 7, tzinfo=timezone.utc))

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_rank_among_both_lists_without_dexs_or_zero_volume(self):
        r = self.doc["results"]
        self.assertEqual((r["ours_rank"], r["protocols_ranked"]), (1, 4))
        self.assertEqual(r["largest_other"]["slug"], "unit")
        self.assertEqual(r["largest_aggregator"]["slug"], "lifi")
        self.assertEqual(Decimal(r["ours_over_largest_aggregator"]), Decimal(4000) / Decimal(1500))

    def test_verify_offline_and_tamper(self):
        out = self.tmp / "data" / demand.OUT_NAME
        self.assertEqual(demand.verify(out)[0], [])
        p = self.tmp / self.doc["raw_files"]["bridge_aggregator"]["path"]
        p.write_bytes(p.read_bytes().replace(b"1500", b"9500"))
        self.assertTrue(any("sha256" in x for x in demand.verify(out)[0]))

    def test_missing_ours_stops(self):
        with self.assertRaises(RuntimeError):
            demand.run(self.tmp / "data", fetch=lambda u: AGG)


if __name__ == "__main__":
    unittest.main()
