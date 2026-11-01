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



class RateLimitTest(unittest.TestCase):
    def test_429_slows_down_and_retries(self):
        import io
        import urllib.error
        from unittest import mock
        answers = [429, 429, 200]
        waits = []

        def fake_urlopen(req, timeout):
            code = answers.pop(0)
            if code != 200:
                raise urllib.error.HTTPError(req.full_url, code, "Too Many", {}, io.BytesIO())
            return mock.MagicMock(__enter__=lambda s: io.BytesIO(b'{"ok":1}'),
                                  __exit__=lambda *a: False)

        chain = lw.Chain(url="https://x", sleep=waits.append)
        with mock.patch("urllib.request.urlopen", fake_urlopen):
            self.assertEqual(chain._post({}), b'{"ok":1}')
        self.assertEqual(chain.calls, 3)
        self.assertEqual(chain.pause, 2.0)           # 0.5 -> 1.0 -> 2.0
        self.assertEqual(waits, [0.5, 5, 1.0, 10, 2.0])

    def test_json_rpc_error_with_422_status_is_returned(self):
        import io
        import urllib.error
        from unittest import mock
        body = json.dumps({"jsonrpc": "2.0", "id": "lock", "error": {
            "name": "HANDLER_ERROR", "cause": {"name": "UNKNOWN_BLOCK", "info": {}}}}).encode()

        def fake_urlopen(req, timeout):
            raise urllib.error.HTTPError(req.full_url, 422, "Unprocessable", {}, io.BytesIO(body))

        chain = lw.Chain(url="https://x", sleep=lambda s: None)
        with mock.patch("urllib.request.urlopen", fake_urlopen):
            self.assertIsNone(chain.block(178_000_000))   # skipped height, not a crash
            self.assertIn(178_000_000, chain.skipped)

        def not_json(req, timeout):
            raise urllib.error.HTTPError(req.full_url, 422, "Unprocessable", {},
                                         io.BytesIO(b"<html>bad</html>"))
        with mock.patch("urllib.request.urlopen", not_json):
            with self.assertRaises(RuntimeError):
                chain.block(178_000_001)

    def test_pace_recovers_after_answers_without_429(self):
        import io
        from unittest import mock

        def ok(req, timeout):
            return mock.MagicMock(__enter__=lambda s: io.BytesIO(b'{"ok":1}'),
                                  __exit__=lambda *a: False)

        chain = lw.Chain(url="https://x", sleep=lambda s: None, recover_after=20)
        chain.pause = 3.0  # as after several 429s
        with mock.patch("urllib.request.urlopen", ok):
            for _ in range(19):
                chain._post({})
            self.assertEqual(chain.pause, 3.0)       # not yet
            chain._post({})
            self.assertEqual(chain.pause, 1.5)       # 20 good answers: halve
            for _ in range(40):
                chain._post({})
            self.assertEqual(chain.pause, 0.5)       # back to the start, never below
            for _ in range(40):
                chain._post({})
            self.assertEqual(chain.pause, 0.5)


if __name__ == "__main__":
    unittest.main()
