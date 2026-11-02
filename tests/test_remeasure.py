"""Tests for scripts/remeasure.py on simulated chains (no network).

Run: python -m unittest discover -s tests
"""
import contextlib
import csv
import io
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import daily  # noqa: E402
import lock_window as lw  # noqa: E402
import remeasure  # noqa: E402
import stakers  # noqa: E402
from test_daily import FakeChainWithState  # noqa: E402
from test_lock_window import final_height_at  # noqa: E402
from test_stakers import STATE, FakeStakeDao, fake_pages  # noqa: E402

D = date(2026, 11, 1)
REPO = Path(__file__).resolve().parent.parent


def quiet(fn, *args, **kw):
    with contextlib.redirect_stdout(io.StringIO()) as out:
        return fn(*args, **kw), out.getvalue()


class RemeasureTest(unittest.TestCase):
    def dirs(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        saved = Path(tmp.name) / "saved" / "data"
        (Path(tmp.name) / "new").mkdir()
        return saved, remeasure.temp_data_dir(Path(tmp.name) / "new")

    def test_differences(self):
        self.assertEqual(remeasure.differences({"a": 1, "b": 2}, {"a": 1, "b": 3}), [("b", 2, 3)])
        self.assertEqual(remeasure.differences({"a": 1, "p": "x"}, {"a": 1, "p": "y"}, {"p"}), [])
        self.assertEqual(remeasure.differences({"a": 1}, {}), [("a", 1, None)])

    def test_temp_folder_is_named_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(remeasure.temp_data_dir(tmp).name, "data")

    def test_number1_same_then_different(self):
        saved, new = self.dirs()
        chain = lambda: FakeChainWithState(final_height_at(lw.midnight_ns(D) + 3600 * lw.NS))
        daily.run(D, saved, chain())
        ok, out = quiet(remeasure.number1, D, new, chain(), saved)
        self.assertTrue(ok, out)
        self.assertIn("byte-identical to the saved ones: yes", out)

        # A saved row that the chain does not give back is reported.
        path = saved / "history.csv"
        rows = list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))
        rows[0]["coverage_buybacks"] = "0.200000"
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        _, new2 = self.dirs()
        ok, out = quiet(remeasure.number1, D, new2, chain(), saved)
        self.assertFalse(ok)
        self.assertIn("DIFFERENT coverage_buybacks: saved '0.200000', now '0.100000'", out)

    def test_number3_ignores_accounts_that_staked_later(self):
        saved, new = self.dirs()
        chain = lambda state: FakeStakeDao(final_height_at(lw.midnight_ns(D) + 3600 * lw.NS), state)
        get, _ = fake_pages(sorted(STATE))
        quiet(stakers.discover, saved, "2026-11-01", get=get, wait=0)
        acc = saved / "stakers" / "accounts_2026-11-01.json"
        quiet(stakers.snapshot, chain(STATE), D, acc, saved)

        # Today NearBlocks also lists an account that first staked after the date:
        # it has no position at that block.
        get2, _ = fake_pages(sorted(list(STATE) + ["after.near"]))
        ok, out = quiet(remeasure.number3, D, new, chain(STATE), saved, get=get2, wait=0)
        self.assertTrue(ok, out)

        # A position that differs at the block is reported.
        changed = dict(STATE, **{"d.near": 21})
        _, new2 = self.dirs()
        ok, out = quiet(remeasure.number3, D, new2, chain(changed), saved, get=get2, wait=0)
        self.assertFalse(ok)
        self.assertIn("DIFFERENT farm_total_near", out)

    def test_agent_files_are_identical(self):
        claude, agents = REPO / "CLAUDE.md", REPO / "AGENTS.md"
        if claude.exists() or agents.exists():
            self.assertEqual(claude.read_bytes(), agents.read_bytes(),
                             "CLAUDE.md and AGENTS.md must stay identical")


if __name__ == "__main__":
    unittest.main()
