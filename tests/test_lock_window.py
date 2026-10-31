"""Tests for scripts/lock_window.py on a simulated chain (no network).

Run: python -m unittest discover -s tests
"""
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import lock_window as lw  # noqa: E402

NS = lw.NS
H0 = 217453248
T0 = lw.midnight_ns(date(2026, 9, 27)) + (7 * 3600 + 4 * 60) * NS  # 27 Sep 07:04 UTC


def skipped(h):
    # Some heights have no block, including runs of two, as on NEAR.
    return h % 997 == 0 or h % 4999 in (0, 1)


def ts(h):
    # ~0.59 s per block with jitter, still strictly increasing with height.
    return T0 + (h - H0) * 590_000_000 + (h * 7919 % 100) * 1_000_000


def prev_existing(h):
    h -= 1
    while skipped(h):
        h -= 1
    return h


class FakeChain(lw.Chain):
    def __init__(self, final_height):
        super().__init__(url="fake", pause=0)
        self.final_height = final_height

    def _post(self, body):
        self.calls += 1
        params = body["params"]
        h = self.final_height if params.get("finality") == "final" else params["block_id"]
        if skipped(h) or h > self.final_height:
            return json.dumps({"jsonrpc": "2.0", "id": "lock",
                               "error": {"name": "HANDLER_ERROR",
                                         "cause": {"name": "UNKNOWN_BLOCK", "info": {}}}}).encode()
        t = ts(h)
        header = {"height": h, "hash": f"H{h}", "prev_hash": f"H{prev_existing(h)}",
                  "timestamp": t, "timestamp_nanosec": str(t),
                  "total_supply": str(10 ** 33 + h)}
        return json.dumps({"jsonrpc": "2.0", "id": "lock",
                           "result": {"header": header, "chunks": []}}).encode()


def expected_boundary(target):
    h = H0 + (target - T0) // 590_000_000 - 50
    while skipped(h) or ts(h) < target:
        h += 1
    return h


def final_height_at(ns):
    return H0 + (ns - T0) // 590_000_000


class LockWindowTest(unittest.TestCase):
    def test_finds_every_boundary_and_verifies(self):
        start, end = date(2026, 10, 2), date(2026, 11, 1)
        chain = FakeChain(final_height_at(lw.midnight_ns(date(2026, 11, 1)) + 3600 * NS))
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"
            doc = lw.lock(chain, start, end, data)
            self.assertEqual(len(doc["boundaries"]), 31)
            self.assertEqual(doc["window"]["days"], 30)
            for b in doc["boundaries"]:
                target = lw.midnight_ns(date.fromisoformat(b["date"]))
                self.assertEqual(b["height"], expected_boundary(target), b["date"])
                self.assertEqual(b["previous"]["height"], prev_existing(b["height"]))
            out = data / "window.json"
            out.write_text(json.dumps(doc), encoding="utf-8")
            self.assertEqual(lw.verify(out), [])

            # Change one byte in one raw file: verify must catch it.
            raw = next((data / "raw" / "blocks").iterdir())
            raw.write_bytes(raw.read_bytes().replace(b'"lock"', b'"lokk"'))
            self.assertTrue(any("sha256" in p for p in lw.verify(out)))

    def test_boundary_right_after_skipped_heights(self):
        # Target falls inside a run of skipped heights: answer is the next real block.
        h = 4999 * 43600  # skipped, and so is h + 1
        self.assertTrue(skipped(h) and skipped(h + 1) and not skipped(h + 2))
        chain = FakeChain(h + 10_000_000)
        hdr, prev = lw.find_boundary(chain, ts(h - 1) + 1, guess=h - 5000)
        self.assertEqual(hdr["height"], h + 2)
        self.assertEqual(prev["height"], h - 1)

    def test_refuses_before_last_boundary_is_final(self):
        chain = FakeChain(final_height_at(lw.midnight_ns(date(2026, 11, 1)) + 60 * NS))
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit):
                lw.lock(chain, date(2026, 10, 2), date(2026, 11, 1), Path(tmp) / "data")

    def test_guess_far_off_in_both_directions(self):
        target = lw.midnight_ns(date(2026, 10, 15))
        for off in (-300_000, -7, 0, 9, 250_000):
            chain = FakeChain(final_height_at(target) + 1_000_000)
            hdr, _ = lw.find_boundary(chain, target, expected_boundary(target) + off)
            self.assertEqual(hdr["height"], expected_boundary(target), off)


if __name__ == "__main__":
    unittest.main()
