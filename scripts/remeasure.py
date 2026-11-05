"""Re-measure numbers 1 and 3 from the chain and compare them with the saved files.

This is the network counterpart of `build_numbers.py --verify`. It runs the same
code as the scripts that made the saved files, writes into a new temporary folder
(nothing under data/ changes), and compares:

  Number 1  daily.py for the window's end date. The day's row (blocks, supply,
            balances, coverage) must equal the saved row in data/history.csv.
            It also reports whether every archival response is byte-identical
            to the saved one (data/daily/<date>.json lists their sha256).
  Number 3  stakers.py for the same date. Every statistic must equal the one
            recomputed from the saved snapshot. The list of accounts that ever
            called `stake` is fetched again from NearBlocks today, so it can hold
            accounts that first staked after the date; at that block they have no
            position, and no statistic counts them.

Needs network: archival RPC (FastNEAR) and the NearBlocks API. No keys, read-only.
Takes a few minutes: about 200 position reads with a 0.5 s pause, and a 12 s pause
between NearBlocks pages. Exit code 0 only if both numbers match.

Usage:
    python scripts/remeasure.py                    # both numbers, 2026-11-01
    python scripts/remeasure.py --only 1           # number 1 only (under a minute)
    python scripts/remeasure.py --keep             # keep the temporary folder
"""
import argparse
import csv
import json
import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import daily  # noqa: E402
import lock_window as lw  # noqa: E402
import stakers  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
DATE = date(2026, 11, 1)  # end of the locked window 2 Oct -> 1 Nov 2026
# Says where the private originals were found; differs by design between runs.
NOT_COMPARED = {"private_check"}


def differences(saved, new, skip=()):
    """Keys whose values differ, as (key, saved, new), in key order."""
    keys = sorted((set(saved) | set(new)) - set(skip))
    return [(k, saved.get(k), new.get(k)) for k in keys if saved.get(k) != new.get(k)]


def temp_data_dir(parent):
    """The scripts write paths relative to the folder above data/, so the copy must be
    named data/ for those paths to read the same as in the repository."""
    d = Path(parent) / "data"
    d.mkdir()
    return d


def saved_row(d, data_root):
    with (data_root / "history.csv").open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["date"] == d.isoformat():
                return row
    raise SystemExit(f"No saved row for {d} in data/history.csv")


def number1(d, tmp, chain, data_root):
    doc, rows, problems, _calls = daily.run(d, tmp, chain)
    new = next(r for r in rows if r["date"] == d.isoformat())
    # Compared as history.csv writes them: text.
    diff = differences(saved_row(d, data_root), {k: str(v) for k, v in new.items()})
    saved_doc = json.loads((data_root / "daily" / f"{d.isoformat()}.json").read_text("utf-8"))
    same_raw = saved_doc["raw_files"] == doc["raw_files"]
    print(f"Number 1, {d}: blocks {new['block_start']} -> {new['block_end']}, "
          f"coverage {new['coverage_buybacks']} (with front-end fund {new['coverage_with_fe']})")
    print(f"  archival responses byte-identical to the saved ones: {'yes' if same_raw else 'no'}"
          f" ({len(doc['raw_files'])} files)")
    return report(diff + [("problem", "", p) for p in problems])


def number3(d, tmp, chain, data_root, get=stakers.http_get, wait=stakers.PAGE_WAIT):
    accounts = stakers.discover(tmp, d.isoformat(), get=get, wait=wait)
    snap = stakers.snapshot(chain, d, accounts, tmp)
    new, problems = stakers.compute(snap, tmp)
    saved, saved_problems = stakers.compute(data_root / "stakers" / f"{d.isoformat()}.json",
                                            data_root)
    if saved_problems:
        return report([("saved snapshot", "", p) for p in saved_problems])
    if new is None:
        return report([("problem", "", p) for p in problems])
    listed = len(json.loads(accounts.read_text("utf-8"))["accounts"])
    print(f"Number 3, {d}: block {new['block']}, active {new['stakers_active']}, "
          f"ever {new['stakers_ever']}, largest {new['largest_share']}, "
          f"top10 {new['top10_share']}, median outside top10 {new['outside_top10_median_near']}")
    print(f"  accounts listed by NearBlocks today: {listed}; "
          f"{len(new) - len(NOT_COMPARED)} statistics compared")
    return report(differences(saved, new, NOT_COMPARED) + [("problem", "", p) for p in problems])


def report(diff):
    if not diff:
        print("  SAME as the saved files")
        return True
    for key, old, new in diff:
        print(f"  DIFFERENT {key}: saved {old!r}, now {new!r}")
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", choices=["1", "3"])
    parser.add_argument("--keep", action="store_true", help="keep the temporary folder")
    parser.add_argument("--data-dir", type=Path, default=REPO / "data", help=argparse.SUPPRESS)
    args = parser.parse_args()
    data_root = args.data_dir.resolve()
    parent = Path(tempfile.mkdtemp(prefix="remeasure_"))
    tmp = temp_data_dir(parent)
    print(f"Temporary folder: {tmp}", flush=True)
    chain = lw.Chain()
    ok = True
    try:
        if args.only in (None, "1"):
            ok &= number1(DATE, tmp, chain, data_root)
        if args.only in (None, "3"):
            ok &= number3(DATE, tmp, chain, data_root)
    finally:
        if not args.keep:
            shutil.rmtree(parent, ignore_errors=True)
    print(f"{chain.calls} RPC calls")
    print("REMEASURE: SAME" if ok else "REMEASURE: DIFFERENT")
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RuntimeError as e:
        # network problems (refused, unresolved, too many failed attempts): one clear line
        print(f"REMEASURE: NOT RUN - {e}", file=sys.stderr)
        sys.exit(2)
