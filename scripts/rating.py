"""The rating (Hold / Buy / Avoid) for every 30-day window in data/history.csv, from its rules.

The rules are the README's "The rating in full". For each history row (the 30 days before D):

  wallets kept share  = NEAR the three wallets kept a day (buybacks + 1Click fund + front-end fund,
                        history.csv) / DefiLlama's revenue for NEAR Intents, in NEAR a day
  buybacks kept, USD  = NEAR the buybacks wallets kept a day x the window's mean NEAR price
  coverage            = coverage_buybacks from history.csv (NEAR kept / NEAR issued)
  coverage counted    = the Buy path's coverage: NEAR the buybacks wallets kept a day, but at most
                        DefiLlama's revenue and at most its fees for the window, both in NEAR a day,
                        / NEAR issued. A balance can also grow by transfers that are not fees (the
                        front-end fund, treasury.near, any donor); capped this way, they cannot make
                        Buy: coverage counted reaches 100% only if the fees themselves cover issuance.
  (b)                 = on the window's end block, a lock declared in daily.LOCKS has no contract and
                        no access keys, so no one can spend from it (daily.sealed); read per window, so
                        it is never true before the block where it became true.

  A window fails if kept share < 75%, or buybacks kept in USD <= April's level (numbers.json
  f2.buybacks_kept_usd_per_day.2026-04). Avoid if this window and the one ending 30 days
  earlier both fail. Buy if (b) holds and either coverage counted
  >= 100% or (a) held at the latest yearly check (the 1 November window): buybacks kept had grown at
  the required pace from the 2026-11-01 window, in USD and in NEAR. A pass holds until the next
  yearly check. Avoid overrides Buy. Otherwise Hold, also when a rule cannot be judged.

DefiLlama days are counted exactly as in fees.py (the same flags, the same mean price), so the
2026-11-01 row reproduces numbers.json. A row is "incomplete" if a day lacks a series, and
"provisional" until 48 h after the window's last day (DefiLlama revises recent days).
Every run re-fetches the whole series, so provisional rows settle by themselves.

Read-only, no keys. Raw responses are saved byte for byte with their sha256 in data/rating.json;
--verify recomputes data/rating.csv from them and history.csv with no network.

Usage:
    python scripts/rating.py                          # fetch DefiLlama, write rating.json + rating.csv
    python scripts/rating.py --from data/raw/defillama/20261104T150225Z   # use saved responses
    python scripts/rating.py --offline                # rebuild from the responses rating.json lists (new rows: incomplete)
    python scripts/rating.py --verify                 # offline check
    python scripts/rating.py --show                   # print the latest rows
"""
import argparse
import csv
import io
import json
import sys
from datetime import date, datetime, timedelta, timezone
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import daily  # noqa: E402
import fees  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
BASE_DATE = date(2026, 11, 1)          # the window the rating was set on
KEPT_SHARE_MIN = Fraction(3, 4)        # Avoid test 1: the wallets keep at least 75% of revenue
HSP029_IN_FORCE = False                # set True once validators run a release with HSP-029 (upgrade_watch.py)
SERIES = ("fees", "revenue", "volume", "price")
THRESHOLD_KEYS = {
    "avoid_usd_per_day": "f2.buybacks_kept_usd_per_day.2026-04",
    "base_usd_per_day": "iv.buybacks_kept_usd_per_day",
    "base_near_per_day": "n1.buybacks_near_per_day",
    "growth_with_hsp029": "lr.required_growth.buybacks.B.2031",
    "growth_without_hsp029": "lr.required_growth.buybacks.A.2031",
}
COLUMNS = [
    "date", "window_start", "status", "counted_days",
    "revenue_near_per_day", "wallets_kept_near_per_day", "kept_share",
    "mean_price_usd", "buybacks_kept_usd_per_day", "max_coverage_defillama", "coverage_buybacks",
    "coverage_counted",
    "test_kept_share", "test_usd", "earlier_window", "rule_b", "covers_issuance", "yearly_a",
    "rating", "note",
]


def thresholds(numbers_path):
    n = json.loads(Path(numbers_path).read_text(encoding="utf-8"))
    items = n.get("numbers", n)
    return {name: str(items[key]["value"]) for name, key in THRESHOLD_KEYS.items()}


def parse(raws):
    s = {name: fees.daily_series(raws[name], name) for name in ("fees", "revenue", "volume")}
    s["price"] = fees.price_series(raws["price"])
    return s


def pct(x):
    return fees.fmt(x, 6)


def window_values(row, s, fetched):
    """The DefiLlama side of one history row, or (status, None) if it cannot be judged."""
    start, end = date.fromisoformat(row["window_start"]), date.fromisoformat(row["date"])
    days = [start + timedelta(days=i) for i in range((end - start).days)]
    missing = [d for d in days if any(d not in s[k] for k in SERIES)]
    if missing:
        return "incomplete", {"note": f"no DefiLlama data for {len(missing)} day(s), from {missing[0]}"}
    agg, _ = fees.aggregate(days, s)
    hours = (fetched - datetime(end.year, end.month, end.day, tzinfo=timezone.utc)).total_seconds() / 3600
    status = "final" if hours >= fees.FINAL_AFTER_H else "provisional"
    return status, agg


def evaluate(history, s, th, fetched, sealed):
    """sealed: {date: [lock accounts sealed at that window's end block]}, from daily.sealed()."""
    by_date = {r["date"]: r for r in history}
    out, fails = [], {}
    a_since = None          # date of the yearly check whose (a) passed; holds until the next check
    for r in history:
        d = date.fromisoformat(r["date"])
        status, agg = window_values(r, s, fetched)
        kept_bb = Fraction(r["buybacks_per_day"])
        kept_all = kept_bb + Fraction(r["fefunds_per_day"])
        rule_b = bool(sealed.get(r["date"]))
        cov = None          # coverage counted: judged only when DefiLlama's days are all there
        row = {c: "" for c in COLUMNS}
        row.update(date=r["date"], window_start=r["window_start"], status=status,
                   wallets_kept_near_per_day=fees.fmt(kept_all, 3), coverage_buybacks=r["coverage_buybacks"],
                   rule_b="yes" if rule_b else "no", covers_issuance="not judged")
        notes = []
        fail = None
        if status == "incomplete":
            notes.append(agg["note"])
        else:
            rev = agg["revenue_near_per_day"]
            share = kept_all / rev if rev > 0 else None
            usd = kept_bb * agg["mean_price_usd"]
            new = Fraction(r["new_supply_per_day"])
            cov = min(kept_bb, rev, agg["fees_near_per_day"]) / new
            t_share = "fail" if share is None or share < KEPT_SHARE_MIN else "pass"
            t_usd = "fail" if usd <= Fraction(th["avoid_usd_per_day"]) else "pass"
            fail = "fail" in (t_share, t_usd)
            row.update(counted_days=agg["counted_days"], revenue_near_per_day=fees.fmt(rev, 3),
                       kept_share="" if share is None else pct(share),
                       mean_price_usd=fees.fmt(agg["mean_price_usd"], 6),
                       buybacks_kept_usd_per_day=fees.fmt(usd, 2),
                       max_coverage_defillama=pct(agg["fees_near_per_day"] / new),
                       coverage_counted=pct(cov), covers_issuance="yes" if cov >= 1 else "no",
                       test_kept_share=t_share, test_usd=t_usd)
            if share is None:
                notes.append("DefiLlama revenue is zero")
            if agg["excluded"]:
                notes.append(f"{len(agg['excluded'])} day(s) excluded as in fees.py")
        fails[r["date"]] = fail
        earlier = (d - timedelta(days=daily.WINDOW_DAYS)).isoformat()
        if earlier not in by_date:
            row["earlier_window"] = "not in history"
        else:
            e = fails.get(earlier)
            row["earlier_window"] = {True: "fail", False: "pass", None: "not judged"}[e]
        # (a): only at a yearly check, on the 1 November window, against the 2026-11-01 base
        if d.month == BASE_DATE.month and d.day == BASE_DATE.day and d > BASE_DATE and status != "incomplete":
            g = Fraction(th["growth_with_hsp029" if HSP029_IN_FORCE else "growth_without_hsp029"])
            factor = Fraction((1 + float(g)) ** ((d - BASE_DATE).days / 365.25))
            ok = (kept_bb * agg["mean_price_usd"] >= Fraction(th["base_usd_per_day"]) * factor
                  and kept_bb >= Fraction(th["base_near_per_day"]) * factor)
            row["yearly_a"] = "pass" if ok else "fail"
            a_since = d if ok else None
        elif a_since is not None:
            row["yearly_a"] = f"pass since {a_since.isoformat()}"
        avoid = fail is True and row["earlier_window"] == "fail"
        buy = rule_b and ((cov is not None and cov >= 1) or row["yearly_a"].startswith("pass"))
        row["rating"] = "Avoid" if avoid else "Buy" if buy else "Hold"
        if fail and not avoid:
            notes.append("this window fails an Avoid test; Avoid needs the earlier window to fail too")
        if avoid and buy:
            notes.append("Buy conditions met, Avoid overrides")
        if status == "provisional":
            notes.append("DefiLlama may still revise these days")
        row["note"] = "; ".join(notes)
        out.append(row)
    return out


def text(rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def load_history(data_root):
    with open(data_root / "history.csv", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def compute(doc, data_root):
    base = data_root.parent
    problems, raws = [], {}
    for name in SERIES:
        info = doc["raw"][name]
        raw = (base / info["path"]).read_bytes()
        if fees.sha256(raw) != info["sha256"]:
            problems.append(f"sha256 differs for {info['path']}")
        raws[name] = raw
    th_now = thresholds(data_root / "numbers.json")
    if th_now != doc["thresholds"]:
        problems.append("thresholds in rating.json differ from numbers.json")
    if doc["locks"] != sorted(daily.LOCKS):
        problems.append("locks in rating.json differ from LOCKS in daily.py")
    if problems:
        return None, problems
    fetched = datetime.strptime(doc["fetched_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    rows = evaluate(load_history(data_root), parse(raws), doc["thresholds"], fetched, daily.sealed(data_root))
    return rows, problems


def build(data_root, raw_dir, fetched_utc, urls):
    base = data_root.parent
    doc = {
        "measure": "the rating (Hold / Buy / Avoid) for every window in history.csv, from README's rules",
        "rules": {"kept_share_min": "0.75", "avoid": "this window and the one ending 30 days earlier fail",
                  "buy": "rule (b) read from the chain (a declared lock with no contract and no keys), and "
                         "coverage counted (kept, at most DefiLlama's revenue and fees) >= 100% or (a) at a yearly check",
                  "precedence": "Avoid overrides Buy", "hsp029_in_force": HSP029_IN_FORCE},
        "fetched_utc": fetched_utc,
        "locks": sorted(daily.LOCKS),
        "thresholds": thresholds(data_root / "numbers.json"),
        "raw": {name: {"path": fees.rel(raw_dir / f"{name}.json", base),
                       "sha256": fees.sha256((raw_dir / f"{name}.json").read_bytes()),
                       "url": urls.get(name, "")} for name in SERIES},
    }
    rows, problems = compute(doc, data_root)
    if problems:
        raise SystemExit("\n".join(problems))
    (data_root / "rating.json").write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8", newline="\n")
    (data_root / "rating.csv").write_text(text(rows), encoding="utf-8", newline="")
    return rows


def fetch_all(data_root, fetch=fees.fetch, now=None):
    now = now or datetime.now(timezone.utc)
    history = load_history(data_root)
    first = min(date.fromisoformat(r["window_start"]) for r in history)
    last = max(date.fromisoformat(r["date"]) for r in history) - timedelta(days=1)
    urls = dict(fees.SERIES_URLS)
    urls["price"] = fees.price_url(first, last)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    raw_dir = data_root / "raw" / "rating" / stamp
    raw_dir.mkdir(parents=True, exist_ok=True)
    for name in SERIES:
        (raw_dir / f"{name}.json").write_bytes(fetch(urls[name]))
    return build(data_root, raw_dir, now.strftime("%Y-%m-%dT%H:%M:%SZ"), urls)


def verify(data_root):
    path = data_root / "rating.json"
    if not path.exists():
        return ["rating.json is missing"]
    rows, problems = compute(json.loads(path.read_text(encoding="utf-8")), data_root)
    if problems:
        return problems
    saved = (data_root / "rating.csv").read_bytes().decode("utf-8")
    if saved != text(rows):
        problems.append("rating.csv differs from the rows recomputed from history.csv and the saved responses")
    return problems


def show(data_root, n=5):
    with open(data_root / "rating.csv", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows[-n:]:
        print(f"{r['date']}  {r['rating']:5}  {r['status']:11}  coverage {r['coverage_buybacks']}  "
              f"kept share {r['kept_share'] or '-'}  buybacks ${r['buybacks_kept_usd_per_day'] or '-'}/day  "
              f"earlier {r['earlier_window']}  {r['note']}")


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--from", dest="raw_from", help="a saved folder with fees/revenue/volume/price.json")
    p.add_argument("--offline", action="store_true")
    p.add_argument("--verify", action="store_true")
    p.add_argument("--show", action="store_true")
    p.add_argument("--data", default=str(REPO / "data"))
    a = p.parse_args()
    data_root = Path(a.data).resolve()
    if a.verify:
        problems = verify(data_root)
        print("\n".join(problems) if problems else "OK: rating.csv recomputes from history.csv and the saved responses")
        return 1 if problems else 0
    if a.show:
        show(data_root)
        return 0
    if a.offline:
        doc = json.loads((data_root / "rating.json").read_text(encoding="utf-8"))
        raw_dir = (data_root.parent / doc["raw"]["fees"]["path"]).parent
        build(data_root, raw_dir, doc["fetched_utc"], {k: v["url"] for k, v in doc["raw"].items()})
    elif a.raw_from:
        raw_dir = Path(a.raw_from).resolve()
        stamp = raw_dir.name
        fetched = datetime.strptime(stamp, "%Y%m%dT%H%M%SZ").strftime("%Y-%m-%dT%H:%M:%SZ")
        build(data_root, raw_dir, fetched, {})
    else:
        try:
            fetch_all(data_root)
        except RuntimeError as e:
            print(f"RATING: NOT RUN - {e}")
            return 2
    show(data_root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
