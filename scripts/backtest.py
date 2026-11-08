"""The rating rules on the seven months before the window: April to October 2026, offline.

    python scripts/backtest.py            # write data/backtest.json and data/backtest.csv
    python scripts/backtest.py --verify   # offline: both recompute from the saved files

The rules are rating.py's, called as they are (rating.evaluate), on one window per calendar month:
  NEAR side   data/coverage_monthly.json: what the three wallets kept a day, read from the chain at the
              first block of each month (the same files as finding 1);
  DefiLlama   the saved responses that data/fees_*.json lists (fees, revenue, volume, price), counted
              day by day exactly as in fees.py;
  thresholds  data/numbers.json, as in rating.py.
Differences from rating.py, all stated in the output: windows are calendar months, not 30 days ending
each day, and Avoid compares each month with the month before; treasury.near "quiet" was not read for
past months (counts as not quiet, as in rating.py); (b) is read from daily.LOCKS, and no lock has been
declared, so (b) is "no" in every month.

The (a) pace check is a sensitivity, not a rule: (a) is judged only at a yearly check from the
2026-11-01 base. Here the same required growth is applied from the April window to the October window,
in USD and in NEAR, to show whether demand growth alone would have met it.
"""
import argparse
import csv
import io
import json
import sys
from datetime import date, datetime, timezone
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import daily  # noqa: E402
import fees  # noqa: E402
import rating  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
FEES_FILE = "fees_2026-10-02_2026-11-01.json"
OUT_JSON, OUT_CSV = "backtest.json", "backtest.csv"
COLUMNS = ["month"] + rating.COLUMNS


def previous_month(d):
    return date(d.year - (d.month == 1), d.month - 1 or 12, 1)


def inputs(data_root):
    cov_path = data_root / "coverage_monthly.json"
    fees_path = data_root / FEES_FILE
    cov = json.loads(cov_path.read_text(encoding="utf-8"))
    fdoc = json.loads(fees_path.read_text(encoding="utf-8"))
    base = data_root.parent
    files = {fees.rel(cov_path, base): fees.sha256(cov_path.read_bytes()),
             fees.rel(fees_path, base): fees.sha256(fees_path.read_bytes())}
    raws, problems = {}, []
    for name in rating.SERIES:
        info = fdoc["raw"][name]
        raw = (base / info["path"]).read_bytes()
        if fees.sha256(raw) != info["sha256"]:
            problems.append(f"sha256 differs for {info['path']}")
        raws[name] = raw
        files[info["path"]] = info["sha256"]
    fetched = datetime.strptime(fdoc["fetched_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return cov, raws, fetched, files, problems


def compute(data_root):
    cov, raws, fetched, files, problems = inputs(data_root)
    if problems:
        return None, problems
    th = rating.thresholds(data_root / "numbers.json")
    months = {r["date"]: r["month"] for r in cov["rows"]}
    hist = [{k: r[k] for k in ("date", "window_start", "buybacks_per_day", "fefunds_per_day",
                               "coverage_buybacks", "new_supply_per_day")} for r in cov["rows"]]
    sealed = {r["date"]: [] for r in hist} if not daily.LOCKS else None
    if sealed is None:
        return None, ["daily.LOCKS is not empty: read (b) for past months before running the backtest"]
    rows = rating.evaluate(hist, rating.parse(raws), th, fetched, sealed, {}, earlier_of=previous_month)
    for r in rows:
        r["month"] = months[r["date"]]
    first, last = rows[0], rows[-1]
    days = (date.fromisoformat(last["date"]) - date.fromisoformat(first["date"])).days
    g = Fraction(th["growth_without_hsp029"])
    need = Fraction((1 + float(g)) ** (days / 365.25))
    usd = Fraction(last["buybacks_kept_usd_per_day"]) / Fraction(first["buybacks_kept_usd_per_day"])
    near = (Fraction(next(h["buybacks_per_day"] for h in hist if h["date"] == last["date"]))
            / Fraction(next(h["buybacks_per_day"] for h in hist if h["date"] == first["date"])))
    judged = [r for r in rows if r["status"] != "incomplete"]
    low = min(judged, key=lambda r: Fraction(r["kept_share"]))
    high = max(judged, key=lambda r: Fraction(r["coverage_counted"]))
    summary = {
        "months": len(rows), "first_month": first["month"], "last_month": last["month"],
        "ratings": {k: sum(r["rating"] == k for r in rows) for k in ("Hold", "Buy", "Avoid")},
        "months_failing_an_avoid_test": [r["month"] for r in rows if "fail" in (r["test_kept_share"], r["test_usd"])],
        "lowest_kept_share": low["kept_share"], "lowest_kept_share_month": low["month"],
        "highest_coverage_counted": high["coverage_counted"], "highest_coverage_counted_month": high["month"],
        "rule_b_months": sum(r["rule_b"] == "yes" for r in rows),
        "a_pace": {"from_month": first["month"], "to_month": last["month"], "days": days,
                   "required_growth_a_year": th["growth_without_hsp029"],
                   "required_multiple": fees.fmt(need, 6),
                   "usd_multiple": fees.fmt(usd, 6), "near_multiple": fees.fmt(near, 6),
                   "met_in_usd_and_near": usd >= need and near >= need},
    }
    doc = {"measure": "the rating rules (rating.evaluate) on each calendar month April-October 2026",
           "differences_from_rating_py": [
               "one window per calendar month; Avoid compares with the previous month",
               "treasury.near quiet not read for past months (counts as not quiet, as in rating.py)",
               "(b) from daily.LOCKS: no lock declared, so (b) is no in every month",
               "Avoid test 2's threshold is April's level (numbers.json f2), so April fails it by construction",
               "a_pace is a sensitivity: the (a) growth applied from the first to the last month; "
               "(a) itself is judged only at a yearly check from the 2026-11-01 base"],
           "inputs_sha256": files, "thresholds": th, "summary": summary}
    return (doc, rows), []


def text(rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\n")
    w.writeheader()
    w.writerows([{c: r[c] for c in COLUMNS} for r in rows])
    return buf.getvalue()


def dumps(doc):
    return json.dumps(doc, indent=1, default=str) + "\n"


def verify(data_root):
    res, problems = compute(data_root)
    if problems:
        return problems
    doc, rows = res
    for name, want in ((OUT_JSON, dumps(doc)), (OUT_CSV, text(rows))):
        p = data_root / name
        if not p.exists():
            problems.append(f"{name} is missing")
        elif p.read_bytes().decode("utf-8") != want:
            problems.append(f"{name} differs from the rows recomputed from the saved files")
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--data", default=str(REPO / "data"))
    a = ap.parse_args()
    data_root = Path(a.data).resolve()
    if a.verify:
        problems = verify(data_root)
        print("\n".join(problems) if problems else
              "OK: backtest.csv recomputes from coverage_monthly.json and the saved DefiLlama responses")
        return 1 if problems else 0
    res, problems = compute(data_root)
    if problems:
        print("\n".join(problems))
        return 1
    doc, rows = res
    (data_root / OUT_JSON).write_text(dumps(doc), encoding="utf-8", newline="\n")
    (data_root / OUT_CSV).write_text(text(rows), encoding="utf-8", newline="")
    for r in rows:
        print(f"{r['month']}  {r['rating']:5}  kept share {r['kept_share']}  buybacks ${r['buybacks_kept_usd_per_day']}/day"
              f"  coverage counted {r['coverage_counted']}  tests {r['test_kept_share']}/{r['test_usd']}")
    print(json.dumps(doc["summary"], indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
