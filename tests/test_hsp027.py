"""Tests for scripts/hsp027.py on a simulated response (no network).

Run: python -m unittest discover -s tests
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import hsp027  # noqa: E402
import hsp029  # noqa: E402
import lock_window as lw  # noqa: E402

NS = lw.NS
START = 1782172800 * NS                  # 2026-06-23T00:00:00Z
DURATION = 10 * 86400 * NS               # ends 2026-07-03T00:00:00Z


def response(p, height=200_000_000):
    value = list(json.dumps(p).encode())
    return json.dumps({"jsonrpc": "2.0", "id": "hsp029",
                       "result": {"result": value, "logs": [], "block_height": height,
                                  "block_hash": "x"}}).encode()


class Run(unittest.TestCase):
    def setUp(self):
        self.p = {"id": 27, "title": "HSP-027 test", "link": None, "proposer_id": "someone.near",
                  "description": "free text", "voting_start_time_ns": str(START),
                  "voting_duration_ns": str(DURATION), "status": "Approved"}
        self.orig = hsp029.view
        hsp029.view = lambda chain, method, args, height=None: response(self.p)

    def tearDown(self):
        hsp029.view = self.orig

    def test_end_date_and_redaction(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"
            data.mkdir()
            doc = hsp027.run(type("C", (), {"url": "test"})(), data)
            self.assertEqual(doc["voting_end_date_utc"], "2026-07-03")
            self.assertEqual(doc["proposal"]["voting_end_utc"][:19], "2026-07-03T00:00:00")
            red = (Path(tmp) / doc["raw_files"]["proposal_latest"]["redacted"]["path"]).read_text()
            self.assertNotIn("someone.near", red)
            self.assertNotIn("free text", red)
            out = data / "hsp027.json"
            out.write_text(json.dumps(doc), encoding="utf-8")
            self.assertEqual(hsp027.verify(out), [])
            doc["voting_end_date_utc"] = "2026-07-04"
            out.write_text(json.dumps(doc), encoding="utf-8")
            self.assertTrue(hsp027.verify(out))


if __name__ == "__main__":
    unittest.main()
