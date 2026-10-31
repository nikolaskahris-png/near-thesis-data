"""Finding 1: coverage of new NEAR supply by the revenue wallets, month by month.

The same measurement as daily.py (number 1), between the first block at or after
00:00 UTC of the 1st of each month:

  coverage_buybacks = change in (buybacks.multisignature.near + 1csfundsadmin) / change in supply
  coverage_with_fe  = the same plus fefundsadmin.sputnik-dao.near

Independent of DefiLlama: only archival balances and block headers. Internal
moves from 1csfundsadmin to the buybacks wallet cancel out in the sum; payments
out to third parties are not added back (this measures NEAR that stayed out of
circulation). A month where the 1cs balance changed is flagged.

Every response is saved byte for byte under data/raw/ with its sha256 in
data/coverage_monthly.json; --verify recomputes every row without network.

Read-only: JSON-RPC "block", "view_account" and one view call. No keys.

Usage:
    python scripts/coverage.py --start 2026-04-01 --end 2026-11-01
    python scripts/coverage.py --verify
"""
import argparse
import csv
import json
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import daily  # noqa: E402
import lock_window as lw  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
COLUMNS = ["month", "window_start", "date", "block_start", "block_end",
           "new_supply_per_day", "buybacks_per_day", "fefunds_per_day",
           "coverage_buybacks", "coverage_with_fe", "flags"]


def month_starts(start, end):
    if start.day != 1 or end.day != 1:
        raise SystemExit("--start and --end must be the 1st of a month")
    d = start
    while d <= end:
        yield d
        d = date(d.year + d.month // 12, d.month % 12 + 1, 1)


def build(doc, data_root):
    rows, problems = [], []
    pts = doc["boundaries"]
    for a, b in zip(pts, pts[1:]):
        sub = {"date": b["date"], "start": a, "end": b, "raw_files": doc["raw_files"]}
        row, p = daily.build_row(sub, data_root)
        problems += p
        if row is None:
            return [], problems
        row["month"] = a["date"][:7]
        rows.append({k: row[k] for k in COLUMNS})
    return rows, sorted(set(problems))


def write(doc, data_root):
    out = data_root / "coverage_monthly.json"
    out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8", newline="\n")
    with (data_root / "coverage_monthly.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(doc["rows"])
    return out


def run(start, end, data_root, chain=None):
    chain = chain or lw.Chain()
    raw_root = data_root / "raw"
    points, files = [], {}
    for d in month_starts(start, end):
        before = chain.calls
        entry, f = daily.snapshot(chain, d, raw_root)
        points.append(entry)
        files.update(f)
        print(f"{d}  block {entry['height']:>11,}  ({chain.calls - before} calls)", flush=True)
    doc = {
        "measure": "finding 1: monthly coverage of new NEAR supply by the revenue wallets",
        "rule": lw.RULE,
        "source": {"rpc": lw.ARCHIVAL},
        "accounts": {"buybacks": [daily.BUYBACKS, daily.ONECLICK], "front_end_fund": daily.FEFUNDS},
        "boundaries": points,
        "raw_files": dict(sorted(files.items())),
    }
    doc["rows"], problems = build(doc, data_root)
    return write(doc, data_root), doc, problems, chain.calls


def verify(data_root):
    path = data_root / "coverage_monthly.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    rows, problems = build(doc, data_root)
    if not problems and rows != doc["rows"]:
        problems.append("rows recomputed from raw responses differ from the saved rows")
    return doc, problems


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--start", type=date.fromisoformat, help="first month start, YYYY-MM-01")
    parser.add_argument("--end", type=date.fromisoformat, help="last boundary, YYYY-MM-01")
    parser.add_argument("--data-dir", type=Path, default=REPO / "data")
    parser.add_argument("--verify", action="store_true", help="offline check of the saved file")
    args = parser.parse_args()
    data_root = args.data_dir.resolve()

    if args.verify:
        doc, problems = verify(data_root)
        if problems:
            print("\n".join(problems))
            print(f"FAILED: {len(problems)} problem(s)")
            return 1
        print(f"OK: {len(doc['rows'])} month(s) recomputed from raw responses, sha256 all match")
        return 0

    if not (args.start and args.end) or args.end <= args.start:
        parser.error("give --start and --end (end after start), or --verify")
    t0 = time.monotonic()
    out, doc, problems, calls = run(args.start, args.end, data_root)
    print(f"\n{'month':8} {'new/day':>12} {'buybacks/day':>13} {'fefunds/day':>12} "
          f"{'cov':>9} {'cov+fe':>9}  flags")
    for r in doc["rows"]:
        print(f"{r['month']:8} {r['new_supply_per_day']:>12} {r['buybacks_per_day']:>13} "
              f"{r['fefunds_per_day']:>12} {r['coverage_buybacks']:>9} {r['coverage_with_fe']:>9}"
              f"  {r['flags'] or '-'}")
    print(f"\n{calls} RPC calls, {time.monotonic() - t0:.0f} s. Saved {out}")
    if problems:
        print("\n".join(problems))
        print("FAILED")
        return 1
    _, problems = verify(data_root)
    if problems:
        print("\n".join(problems))
        print("FAILED offline check")
        return 1
    print("Offline check: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
