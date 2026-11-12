"""Tests for scripts/judge_prereg.py: pending before 16 November, and the rule on days already saved."""
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import judge_prereg as jp  # noqa: E402


class JudgePrereg(unittest.TestCase):
    def test_pending_until_the_end_day_file_exists(self):
        if (REPO / "data" / "daily" / f"{jp.END_DAY}.json").exists():
            self.skipTest("the end day has been measured")
        res, problems = jp.judge_p2(REPO / "data")
        self.assertEqual(problems, [])
        self.assertEqual(res["status"], "pending")

    def test_the_rule_runs_on_a_saved_day(self):
        # the same code on a day already saved stands in for 16 November: it must read, check and decide
        res, problems = jp.judge_p2(REPO / "data", end_day="2026-11-10")
        self.assertEqual(problems, [])
        self.assertIn(res["status"], ("holds", "fails"))
        self.assertEqual(res["status"] == "holds", float(res["ratio"]) < 0.25)
        self.assertEqual(res["start"]["height"], 222491356)       # PREREG.md's baseline block

    def test_a_wrong_day_file_is_caught(self):
        # a 16 November file that ends on another day is refused before any balance is read
        with tempfile.TemporaryDirectory() as t:
            d = Path(t) / "data"
            (d / "daily").mkdir(parents=True)
            src = (REPO / "data" / "daily" / "2026-11-10.json").read_text(encoding="utf-8")
            (d / "daily" / "2026-11-16.json").write_text(src, encoding="utf-8")
            res, problems = jp.point(d, "2026-11-16")
            self.assertIsNone(res)
            self.assertIn("ends on 2026-11-10", problems[0])

    def test_committed_result_recomputes(self):
        res, problems = jp.compute(REPO / "data")
        self.assertEqual(problems, [])
        self.assertEqual(jp.dumps(res), (REPO / "data" / jp.OUT).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
