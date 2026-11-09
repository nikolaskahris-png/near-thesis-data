"""Tests for the daily part of scripts/confidential_treasury.py (no network)."""
import json
import shutil
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import confidential_treasury as ct  # noqa: E402


class DailyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "daily").mkdir()
        for d, h in (("2026-11-08", 100), ("2026-11-09", 200), ("2026-11-10", 300)):
            (self.tmp / "daily" / f"{d}.json").write_text(json.dumps({"end": {"date": d, "height": h}}))
        (self.tmp / "daily" / "notes.json").write_text("{}")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_only_days_after_last(self):
        self.assertEqual(ct.daily_dates(self.tmp), [date(2026, 11, 9), date(2026, 11, 10)])

    def test_height_is_the_daily_lock(self):
        self.assertEqual(ct.daily_height(self.tmp, date(2026, 11, 9)), 200)

    def test_fixed_file_stops_at_last(self):
        self.assertEqual(max(ct.dates()), ct.LAST)
        doc = json.loads((REPO / "data" / ct.OUT).read_text(encoding="utf-8"))
        self.assertEqual(doc["series"][-1]["date"], ct.LAST.isoformat())

    def test_the_daily_height_matches_base_rates_on_a_shared_day(self):
        # the two first-block-of-the-day files agree where both exist
        d = ct.LAST
        self.assertEqual(ct.daily_height(REPO / "data", d), ct.height_of(REPO / "data", d))


if __name__ == "__main__":
    unittest.main()
