"""Number 2: how much of new NEAR supply all NEAR Intents fees could buy.

For a locked window (data/window_<start>_<end>.json from lock_window.py):

  max_coverage      = mean over counted days of (fees_d / price_d)  /  new NEAR per day
  equilibrium_price = mean fees per day (USD)  /  new NEAR per day

fees_d is DefiLlama "dailyFees" for NEAR Intents (protocol fee plus distribution
channel fees; solver spread and gas are not in it). price_d is the NEAR price at
12:00 UTC of day d from coins.llama.fi. So max_coverage is how many NEAR all fees
of each day would have bought at that day's price, against the new supply.
New supply comes only from the two locked boundary blocks (total_supply), over
every day of the window.

Incomplete DefiLlama days are not counted in the fee averages (they stay in the
supply): a day is incomplete if its fees are below 20% of the median day, or its
fees per dollar of volume are below half of the median day. Both medians are over
the days of the same window (or month).

Scenario HSP-029: new supply x 16/25 (maximum inflation 2.5% -> 1.6%; the proposal
itself scales staking yield the same way, 4.80% -> 3.07%). Labelled "scenario".

Also from the same four responses: volume, fees and revenue in bps of volume,
take rate (revenue / fees) per window and per calendar month from March 2026.

Every response is saved byte for byte under data/raw/defillama/<fetch time>/
with its sha256; --verify recomputes the whole result from them without network.

Read-only: four HTTPS GET calls. No keys.

Usage:
    python scripts/fees.py --window data/window_2026-10-02_2026-11-01.json
    python scripts/fees.py --verify data/fees_2026-10-02_2026-11-01.json
"""
import argparse
import hashlib
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lock_window as lw  # noqa: E402

PROTOCOL = "near-intents"
PRICE_ID = "coingecko:near"
LLAMA = "https://api.llama.fi"
SERIES_URLS = {
    "fees": f"{LLAMA}/summary/fees/{PROTOCOL}?dataType=dailyFees&excludeTotalDataChartBreakdown=true",
    "revenue": f"{LLAMA}/summary/fees/{PROTOCOL}?dataType=dailyRevenue&excludeTotalDataChartBreakdown=true",
    "volume": f"{LLAMA}/summary/dexs/{PROTOCOL}?excludeTotalDataChartBreakdown=true",
}
PRICE_URL = "https://coins.llama.fi/chart/{coin}?start={start}&span={span}&period=1d"
MONTHLY_FROM = date(2026, 3, 1)  # first full month after the fee switch of 23 Feb 2026
INCOMPLETE_FEES = Fraction(1, 5)
INCOMPLETE_BPS = Fraction(1, 2)
HSP029_FACTOR = Fraction(16, 25)
PRICE_TOLERANCE_S = 3 * 3600  # a price must be within 3 h of 12:00 UTC of its day
DAY = 86400
YOCTO = 10 ** 24
EPOCH = date(1970, 1, 1)
REPO = Path(__file__).resolve().parent.parent

RULES = {
    "max_coverage": "mean over counted days of (dailyFees_d / NEAR price_d) / new NEAR per day",
    "equilibrium_price": "mean dailyFees per counted day (USD) / new NEAR per day",
    "new_supply": "(total_supply at last boundary - total_supply at first boundary) / window days",
    "price": "coins.llama.fi coingecko:near at 12:00 UTC of each day",
    "incomplete_day": "fees < 20% of the median day, or fees/volume < 50% of the median day "
                      "(medians over the same window or month); not counted in fee averages",
    "hsp029_scenario": "new supply x 16/25 (maximum inflation 2.5% -> 1.6%), scenario only",
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def fetch(url, attempts=5, sleep=time.sleep):
    headers = {"User-Agent": lw.USER_AGENT, "Accept": "application/json"}
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers),
                                        timeout=60) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < attempts - 1:
                sleep(10 * 2 ** attempt)
                continue
            raise RuntimeError(f"HTTP {e.code} from {url}") from None
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if attempt < attempts - 1:
                sleep(10 * 2 ** attempt)
                continue
            raise RuntimeError(f"cannot reach {url}: {e}") from None
    raise RuntimeError("unreachable")


def price_url(first_day, last_day):
    start = int(datetime(first_day.year, first_day.month, first_day.day, 12,
                         tzinfo=timezone.utc).timestamp())
    return PRICE_URL.format(coin=PRICE_ID, start=start, span=(last_day - first_day).days + 1)


# ---------- parsing (exact: every JSON number becomes a Fraction) ----------

def load(raw):
    return json.loads(raw, parse_float=Fraction)


def daily_series(raw, name):
    out = {}
    for ts, value in load(raw)["totalDataChart"]:
        if ts % DAY:
            raise ValueError(f"{name}: timestamp {ts} is not 00:00 UTC")
        d = EPOCH + timedelta(days=ts // DAY)
        if d in out:
            raise ValueError(f"{name}: two values for {d}")
        out[d] = Fraction(value)
    return out


def price_series(raw):
    out = {}
    for p in load(raw)["coins"][PRICE_ID]["prices"]:
        ts = p["timestamp"]
        d = EPOCH + timedelta(days=ts // DAY)
        if abs(ts - (ts // DAY * DAY + DAY // 2)) > PRICE_TOLERANCE_S:
            raise ValueError(f"price: timestamp {ts} is not near 12:00 UTC")
        if d in out:
            raise ValueError(f"price: two values for {d}")
        out[d] = Fraction(p["price"])
    return out


# ---------- formatting ----------

def fmt(x, places):
    q = round(Fraction(x) * 10 ** places)  # exact, half to even
    sign = "-" if q < 0 else ""
    q = abs(q)
    whole, frac = divmod(q, 10 ** places)
    return f"{sign}{whole}.{frac:0{places}d}" if places else f"{sign}{whole}"


# ---------- the measurement ----------

def judge(days, s):
    """Flags per day; a day with any flag is not counted in fee averages."""
    ok = [d for d in days if d in s["fees"] and d in s["volume"]
          and s["fees"][d] > 0 and s["volume"][d] > 0]
    med_fees = statistics.median([s["fees"][d] for d in ok]) if ok else 0
    med_bps = statistics.median([s["fees"][d] / s["volume"][d] for d in ok]) if ok else 0
    flags = {}
    for d in days:
        f = [f"no_{k}" for k in ("fees", "revenue", "volume", "price") if d not in s[k]]
        if not f:
            if s["volume"][d] <= 0:
                f.append("no_volume")
            elif s["fees"][d] < INCOMPLETE_FEES * med_fees:
                f.append("fees_below_20pct_of_median")
            elif s["fees"][d] / s["volume"][d] < INCOMPLETE_BPS * med_bps:
                f.append("fees_per_volume_below_half_of_median")
        flags[d] = f
    return flags


def aggregate(days, s):
    flags = judge(days, s)
    counted = [d for d in days if not flags[d]]
    n = len(counted)
    if n == 0:
        raise ValueError(f"no complete day in {days[0]}..{days[-1]}")
    fees = sum(s["fees"][d] for d in counted)
    rev = sum(s["revenue"][d] for d in counted)
    vol = sum(s["volume"][d] for d in counted)
    fees_near = sum(s["fees"][d] / s["price"][d] for d in counted)
    rev_near = sum(s["revenue"][d] / s["price"][d] for d in counted)
    agg = {
        "first_day": days[0].isoformat(), "last_day": days[-1].isoformat(),
        "days": len(days), "counted_days": n,
        "excluded": {d.isoformat(): ";".join(flags[d]) for d in days if flags[d]},
        "volume_usd_per_day": vol / n,
        "fees_usd_per_day": fees / n,
        "revenue_usd_per_day": rev / n,
        "fees_bps": fees / vol * 10000,
        "revenue_bps": rev / vol * 10000,
        "take_rate": rev / fees,
        "mean_price_usd": sum(s["price"][d] for d in counted) / n,
        "fees_weighted_price_usd": fees / fees_near,
        "fees_near_per_day": fees_near / n,
        "revenue_near_per_day": rev_near / n,
    }
    return agg, flags


def months(first, last):
    d = first
    while d <= last:
        nxt = date(d.year + d.month // 12, d.month % 12 + 1, 1)
        yield [d + timedelta(days=i) for i in range((min(nxt, last + timedelta(days=1)) - d).days)]
        d = nxt


def compute(window, raws):
    """The whole result from the window document and the four raw responses."""
    s = {k: daily_series(raws[k], k) for k in SERIES_URLS}
    s["price"] = price_series(raws["price"])
    start = date.fromisoformat(window["window"]["start"])
    end = date.fromisoformat(window["window"]["end"])
    n_days = (end - start).days
    days = [start + timedelta(days=i) for i in range(n_days)]
    missing = [d.isoformat() for d in days if d not in s["fees"]]
    if missing:
        raise SystemExit(f"DefiLlama has no fees yet for {', '.join(missing)}; run again later.")
    first, last = window["boundaries"][0], window["boundaries"][-1]
    d_supply = int(last["total_supply_yocto"]) - int(first["total_supply_yocto"])
    issuance = Fraction(d_supply, YOCTO * n_days)

    agg, flags = aggregate(days, s)
    scen = issuance * HSP029_FACTOR
    win = dict(agg)
    win.update({
        "block_start": first["height"], "block_end": last["height"],
        "new_near_per_day": issuance,
        "max_coverage": agg["fees_near_per_day"] / issuance,
        "equilibrium_price_usd": agg["fees_usd_per_day"] / issuance,
        "defillama_revenue_coverage": agg["revenue_near_per_day"] / issuance,
        "hsp029_scenario_new_near_per_day": scen,
        "hsp029_scenario_max_coverage": agg["fees_near_per_day"] / scen,
        "hsp029_scenario_equilibrium_price_usd": agg["fees_usd_per_day"] / scen,
    })

    day_rows = []
    for d in days:
        row = {"date": d.isoformat()}
        for k in ("fees", "revenue", "volume"):
            row[f"{k}_usd"] = fmt(s[k][d], 2) if d in s[k] else ""
        row["price_usd"] = fmt(s["price"][d], 6) if d in s["price"] else ""
        ok = d in s["price"] and d in s["volume"] and s["volume"][d] > 0
        row["fees_bps"] = fmt(s["fees"][d] / s["volume"][d] * 10000, 2) if ok else ""
        row["fees_near"] = fmt(s["fees"][d] / s["price"][d], 1) if ok else ""
        row["flags"] = ";".join(flags[d])
        day_rows.append(row)

    monthly = []
    last_day = end - timedelta(days=1)
    for mdays in months(MONTHLY_FROM, last_day):
        m, _ = aggregate(mdays, s)
        m["month"] = mdays[0].strftime("%Y-%m")
        m["full_month"] = len(mdays) == (date(mdays[0].year + mdays[0].month // 12,
                                              mdays[0].month % 12 + 1, 1) - mdays[0]).days
        monthly.append(m)

    return {"window": render(win), "days": day_rows, "monthly": [render(m) for m in monthly]}


PLACES = {"take_rate": 6, "max_coverage": 6, "defillama_revenue_coverage": 6,
          "hsp029_scenario_max_coverage": 6, "fees_bps": 2, "revenue_bps": 2,
          "mean_price_usd": 4, "fees_weighted_price_usd": 4, "equilibrium_price_usd": 4,
          "hsp029_scenario_equilibrium_price_usd": 4, "new_near_per_day": 3,
          "hsp029_scenario_new_near_per_day": 3, "fees_near_per_day": 1,
          "revenue_near_per_day": 1}


def render(d):
    out = {}
    for k, v in d.items():
        if isinstance(v, Fraction):
            v = fmt(v, PLACES.get(k, 2))
        out[k] = v
    return out


# ---------- run / verify ----------

def rel(path, base):
    try:
        return Path(path).resolve().relative_to(base).as_posix()
    except ValueError:
        return Path(path).resolve().as_posix()


def run(window_path, data_root, fetch=fetch, check_window=True, now=None):
    window_path = Path(window_path).resolve()
    if check_window:
        problems = lw.verify(window_path)
        if problems:
            raise SystemExit("window file fails its offline check:\n" + "\n".join(problems))
    window = json.loads(window_path.read_text(encoding="utf-8"))
    start = date.fromisoformat(window["window"]["start"])
    end = date.fromisoformat(window["window"]["end"])
    now = now or datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    urls = dict(SERIES_URLS)
    urls["price"] = price_url(min(MONTHLY_FROM, start), end - timedelta(days=1))
    raw_dir = data_root / "raw" / "defillama" / stamp
    raw_dir.mkdir(parents=True, exist_ok=True)
    raws, raw_files = {}, {}
    for name, url in urls.items():
        raws[name] = fetch(url)
        path = raw_dir / f"{name}.json"
        path.write_bytes(raws[name])
        raw_files[name] = {"path": rel(path, data_root.parent), "sha256": sha256(raws[name]),
                           "url": url}
    result = compute(window, raws)
    out = data_root / f"fees_{start}_{end}.json"
    revisions = []
    if out.exists():
        prev = json.loads(out.read_text(encoding="utf-8"))
        old = {r["date"]: r for r in prev["result"]["days"]}
        for r in result["days"]:
            o = old.get(r["date"])
            if o and (o["fees_usd"], o["price_usd"]) != (r["fees_usd"], r["price_usd"]):
                revisions.append({"date": r["date"], "previous_fetch": prev["fetched_utc"],
                                  "fees_usd": [o["fees_usd"], r["fees_usd"]],
                                  "price_usd": [o["price_usd"], r["price_usd"]]})
    doc = {
        "measure": "number 2: share of new NEAR supply that all NEAR Intents fees could buy",
        "window_file": rel(window_path, data_root.parent),
        "window": {"start": start.isoformat(), "end": end.isoformat(), "days": (end - start).days},
        "rules": RULES,
        "fetched_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hours_after_window_end": round((now - datetime(end.year, end.month, end.day,
                                                        tzinfo=timezone.utc)).total_seconds() / 3600, 1),
        "raw": raw_files,
        "result": result,
        "revisions_vs_previous_fetch": revisions,
    }
    out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8", newline="\n")
    return out, doc


def verify(path, check_window=True):
    """Offline: sha256 of every raw file, then the whole result recomputed."""
    path = Path(path).resolve()
    doc = json.loads(path.read_text(encoding="utf-8"))
    base = path.parent.parent
    problems = []
    window_path = Path(doc["window_file"])
    window_path = window_path if window_path.is_absolute() else base / window_path
    if check_window:
        problems += [f"window: {p}" for p in lw.verify(window_path)]
    raws = {}
    for name, info in doc["raw"].items():
        raw = (base / info["path"]).read_bytes()
        if sha256(raw) != info["sha256"]:
            problems.append(f"sha256 differs for {info['path']}")
        raws[name] = raw
    if problems:
        return problems
    window = json.loads(window_path.read_text(encoding="utf-8"))
    if compute(window, raws) != doc["result"]:
        problems.append("result recomputed from raw responses differs from the saved result")
    return problems


def report(doc):
    w = doc["result"]["window"]
    print(f"Window {w['first_day']} .. {w['last_day']}: {w['counted_days']} of {w['days']} days counted"
          f"  (fetched {doc['fetched_utc']}, {doc['hours_after_window_end']} h after window end)")
    for d, why in w["excluded"].items():
        print(f"  excluded {d}: {why}")
    print(f"  volume/day ${w['volume_usd_per_day']}  fees/day ${w['fees_usd_per_day']}"
          f"  fees {w['fees_bps']} bps  take rate {w['take_rate']}")
    print(f"  new NEAR/day {w['new_near_per_day']}  fees could buy {w['fees_near_per_day']} NEAR/day")
    print(f"  NUMBER 2 max coverage {w['max_coverage']}  equilibrium price ${w['equilibrium_price_usd']}")
    print(f"  scenario HSP-029: max coverage {w['hsp029_scenario_max_coverage']}"
          f"  equilibrium price ${w['hsp029_scenario_equilibrium_price_usd']}")
    print("  last 7 days (date, fees, volume, bps, flags):")
    for r in doc["result"]["days"][-7:]:
        print(f"    {r['date']}  {r['fees_usd']:>12}  {r['volume_usd']:>15}  {r['fees_bps']:>6}  {r['flags']}")
    print("  months (fees bps, take rate, NEAR/day from revenue, counted days):")
    for m in doc["result"]["monthly"]:
        print(f"    {m['month']}  {m['fees_bps']:>6}  {m['take_rate']}  {m['revenue_near_per_day']:>9}"
              f"  {m['counted_days']}/{m['days']}{'' if m['full_month'] else ' (partial)'}")
    for r in doc["revisions_vs_previous_fetch"]:
        print(f"  REVISED {r['date']}: fees {r['fees_usd'][0]} -> {r['fees_usd'][1]}"
              f", price {r['price_usd'][0]} -> {r['price_usd'][1]}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--window", type=Path, help="locked window file from lock_window.py")
    parser.add_argument("--data-dir", type=Path, default=REPO / "data")
    parser.add_argument("--verify", metavar="FILE", help="check a fees file offline")
    args = parser.parse_args()
    if args.verify:
        problems = verify(args.verify)
        if problems:
            print("\n".join(problems))
            print(f"FAILED: {len(problems)} problem(s)")
            return 1
        print("OK: raw sha256 match and the result recomputes exactly")
        return 0
    if not args.window:
        parser.error("give --window FILE or --verify FILE")
    out, doc = run(args.window, args.data_dir.resolve())
    report(doc)
    print(f"Saved {out}")
    problems = verify(out)
    if problems:
        print("\n".join(problems))
        print("FAILED offline check")
        return 1
    print("Offline check: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
