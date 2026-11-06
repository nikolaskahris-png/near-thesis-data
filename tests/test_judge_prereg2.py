"""Tests for scripts/judge_prereg2.py on a simulated chain (no network).

Run: python -m unittest discover -s tests
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import judge_prereg2 as jp  # noqa: E402
import lock_window as lw  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
T0 = jp.ns_of("2026-11-04T00:00:00Z")
STEP = 600_000_000          # 0.6 s a block
SWITCH = 150_000            # first height of the epoch where version 87 starts
SWITCH88 = 330_000


def exists(h):
    return h % 7 != 3        # some heights are skipped, as on mainnet


def ts(h):
    return T0 + h * STEP


def version(h):
    return 86 if h < SWITCH else 87 if h < SWITCH88 else 88


class FakeChain(lw.Chain):
    def __init__(self):
        super().__init__(sleep=lambda s: None, log=lambda line: None)

    def _post(self, body):
        m, p = body["method"], body["params"]
        h = p.get("block_id")
        if h is None or (isinstance(h, int) and not exists(h)):
            return json.dumps({"error": {"name": "HANDLER_ERROR", "cause": {"name": "UNKNOWN_BLOCK"}}}).encode()
        if m == "block":
            prev = h - 1
            while not exists(prev):
                prev -= 1
            return json.dumps({"result": {"header": {
                "height": h, "hash": f"H{h}", "prev_hash": f"H{prev}", "timestamp": ts(h),
                "timestamp_nanosec": str(ts(h)), "total_supply": "1"}}}).encode()
        if m == "EXPERIMENTAL_protocol_config":
            return json.dumps({"result": {"protocol_version": version(h), "epoch_length": 43200}}).encode()
        raise AssertionError(m)


def watch_csv(rows):
    head = ("date,utc,final_height,protocol_version,target_version,blocks_sampled,producers_seen,"
            "block_producers,seen_share,signaling_share,threshold\n")
    lines = [f"d{i},{lw.iso(ts(h))},{h},{version(h)},87,300,70,100,0.9,0.9,4/5" for i, h in enumerate(rows)]
    return head + "\n".join(lines) + "\n"


class JudgeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "data").mkdir()
        shutil.copy(REPO / "PREREG-2.md", self.tmp / "PREREG-2.md")
        # daily records: one before the switch, two after (heights about a day apart at 0.6 s)
        (self.tmp / "data" / "upgrade_watch.csv").write_text(watch_csv([1, 144_000, 288_001]), encoding="utf-8")
        self.after = jp.ns_of("2026-11-06T00:00:00Z") + 3600 * lw.NS

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_prediction_4_holds_and_scores(self):
        doc = jp.judge(FakeChain(), "4", self.tmp / "data", now_ns=self.after)
        r = doc["predictions"]["4"]["result"]
        target = jp.ns_of("2026-11-06T00:00:00Z")
        self.assertTrue(r["holds"])
        self.assertEqual(r["protocol_version"], 87)
        self.assertEqual(r["brier"], "0.0225")
        self.assertGreaterEqual(int(r["judging_block"]["timestamp_ns"]), target)
        self.assertLess(int(r["previous_block"]["timestamp_ns"]), target)
        self.assertTrue(all(r["checks"].values()))
        self.assertEqual(doc["brier_mean"], {"judged": 1, "mean": "0.0225"})

    def test_first_block_with_version_found_by_bisection(self):
        doc = jp.judge(FakeChain(), "4", self.tmp / "data", now_ns=self.after)
        f = doc["first_block_with_version"]["87"]["result"]
        first = SWITCH if exists(SWITCH) else SWITCH + 1
        self.assertEqual(f["first_block"]["height"], first)
        self.assertEqual(f["version_at_block_before"], 86)
        self.assertTrue(all(f["checks"].values()))
        days = (jp.Decimal(ts(first) - jp.ns_of(jp.HSP027_PASSED)) / jp.Decimal(86400 * lw.NS))
        self.assertEqual(f["days_from_hsp027_passed"], str(days.quantize(jp.Decimal("0.01"))))

    def test_verify_offline_and_detects_tampering(self):
        jp.judge(FakeChain(), "4", self.tmp / "data", now_ns=self.after)
        out = self.tmp / "data" / jp.OUT_NAME
        problems, _ = jp.verify(out)
        self.assertEqual(problems, [])
        doc = json.loads(out.read_text(encoding="utf-8"))
        cfg = self.tmp / doc["predictions"]["4"]["raw_files"]["protocol_config"]["path"]
        cfg.write_bytes(cfg.read_bytes().replace(b"87", b"86"))
        problems, _ = jp.verify(out)
        self.assertTrue(any("sha256 differs" in p for p in problems))

    def test_verify_catches_a_changed_result(self):
        jp.judge(FakeChain(), "4", self.tmp / "data", now_ns=self.after)
        out = self.tmp / "data" / jp.OUT_NAME
        doc = json.loads(out.read_text(encoding="utf-8"))
        doc["predictions"]["4"]["result"]["brier"] = "0"
        out.write_text(json.dumps(doc), encoding="utf-8")
        problems, _ = jp.verify(out)
        self.assertIn("prediction 4: result does not recompute", problems)

    def test_refuses_before_the_judging_time_is_final(self):
        with self.assertRaises(RuntimeError):
            jp.judge(FakeChain(), "4", self.tmp / "data", now_ns=jp.ns_of("2026-11-06T00:05:00Z"))

    def test_a_failed_prediction_scores_the_probability_squared(self):
        self.assertEqual(jp.brier("0.85", 0), "0.7225")
        self.assertEqual(jp.brier("0.75", 1), "0.0625")

    def test_second_prediction_merges(self):
        jp.judge(FakeChain(), "4", self.tmp / "data", now_ns=self.after)
        (self.tmp / "data" / "upgrade_watch.csv").write_text(
            watch_csv([1, 144_000, 288_001, 320_000]), encoding="utf-8")
        doc = jp.judge(FakeChain(), "5", self.tmp / "data", now_ns=jp.ns_of("2026-11-08T01:00:00Z"))
        self.assertEqual(sorted(doc["predictions"]), ["4", "5"])
        self.assertEqual(doc["brier_mean"]["judged"], 2)
        self.assertEqual(jp.verify(self.tmp / "data" / jp.OUT_NAME)[0], [])

    def test_prereg_table_matches_the_terms(self):
        checks = jp.prereg_file_checks((REPO / "PREREG-2.md").read_bytes())
        self.assertTrue(all(checks.values()), checks)


if __name__ == "__main__":
    unittest.main()
