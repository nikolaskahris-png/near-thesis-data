"""Did the buybacks keep coming once NEAR Intents moved to the private path? Offline, from saved files.

Another public repository on NEAR Intents, Tideline (github.com/ervhint/tideline-thesis), reads the
transfers of the Confidential Intents Treasury account from intents.near's logs and reports that "since
27 Oct 2026, a growing share of Intents swaps settles privately", and that over 2 to 8 November the
Treasury account carried 85% of the USD it counts on chain. We do not re-read those transactions. We
take its date as given, fixed before looking at our own series, and ask what the buybacks wallets kept
on mainnet before and after it:

  before   2 October to 26 October 2026 (the window's start to the day before Tideline's date)
  after    27 October to 8 November 2026 (Tideline's date to the last day of its 85% week)

For each day D:
  kept NEAR   change in native NEAR of buybacks.multisignature.near and 1csfundsadmin.sputnik-dao.near,
              plus the wNEAR buybacks.multisignature.near holds inside intents.near, between the first
              blocks at or after 00:00 UTC of D and of D+1. Boundaries and balances: the files
              base_rates.py saved (data/raw/base_rates/days/), and for days after its last boundary the
              end block that daily.py locked for that day (data/daily/, data/raw/accounts/).
  kept USD    kept NEAR x coingecko:near at 12:00 UTC of D (coins.llama.fi);
  revenue     DefiLlama's revenue for NEAR Intents on D, in USD, as context only: days near the end of a
              fetch can still be revised, and how DefiLlama counts private swaps is not known.
DefiLlama and prices come from one fetch saved by rating.py, pinned below (FETCH), so the result
does not move when new fetches are saved.

Judged against noise, not by a test: daily inflows are lumpy, so the after-mean is set against every
mean of the same number of consecutive days inside "before" (its lowest and highest). The Treasury
account's stablecoins at both ends come from confidential_treasury(.json, _daily.json).

    python scripts/private_shift.py            # compute and save data/private_shift.json
    python scripts/private_shift.py --verify   # recompute and compare
"""
import argparse
import json
import sys
from datetime import date, timedelta
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import base_rates as br  # noqa: E402
import daily  # noqa: E402
import fees  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
OUT = "private_shift.json"
FETCH = "raw/rating/20261109T063446Z"
BEFORE = (date(2026, 10, 2), date(2026, 10, 26))
AFTER = (date(2026, 10, 27), date(2026, 11, 8))
SOURCE = ("Tideline, github.com/ervhint/tideline-thesis, README and THESIS.md as of 9 Nov 2026: private settlement "
          "grows from 27 Oct 2026; the Confidential Intents Treasury carried 85% of the USD counted on chain, "
          "2-8 Nov 2026")


def days(a, b):
    return [a + timedelta(i) for i in range((b - a).days + 1)]


def balances(data_root):
    """date -> yocto NEAR held by the buybacks wallets at the first block of that date."""
    bal, problems = br.balances(data_root)
    files = {}
    for p in sorted((data_root / "daily").glob("*.json")):
        try:
            d = date.fromisoformat(p.stem)
        except ValueError:
            continue
        if d in bal or d > AFTER[1] + timedelta(1):   # later days do not change the result
            continue
        doc = json.loads(p.read_text(encoding="utf-8"))
        h, acc = doc["end"]["height"], data_root / "raw" / "accounts"
        total = 0
        for a in (daily.BUYBACKS, daily.ONECLICK):
            f = acc / f"{h}_{a}.json"
            res = json.loads(f.read_bytes())["result"]
            if res["block_height"] != h or int(res["locked"]):
                problems.append(f"{d}: {a} read at another block or has staked NEAR")
            total += int(res["amount"])
            files[f.relative_to(data_root.parent).as_posix()] = fees.sha256(f.read_bytes())
        f = acc / f"{h}_{daily.BUYBACKS}_intents_wnear.json"
        total += int(json.loads(bytes(json.loads(f.read_bytes())["result"]["result"]).decode()))
        files[f.relative_to(data_root.parent).as_posix()] = fees.sha256(f.read_bytes())
        bal[d] = total
    return bal, files, problems


def mean(xs):
    return sum(xs) / len(xs)


def compute(data_root):
    bal, files, problems = balances(data_root)
    fetch = data_root / FETCH
    price = fees.price_series((fetch / "price.json").read_bytes())
    revenue = fees.daily_series((fetch / "revenue.json").read_bytes(), "revenue")
    for name in ("price.json", "revenue.json"):
        files[(fetch / name).relative_to(data_root.parent).as_posix()] = fees.sha256((fetch / name).read_bytes())
    rows = []
    for d in days(BEFORE[0], AFTER[1]):
        n = d + timedelta(1)
        if d not in bal or n not in bal or d not in price:
            problems.append(f"{d}: no balance at both ends or no price")
            continue
        k = Fraction(bal[n] - bal[d], fees.YOCTO)
        rows.append({"date": d.isoformat(), "kept_near": k, "kept_usd": k * price[d],
                     "revenue_usd": revenue.get(d)})
    if problems:
        return None, problems
    by = {r["date"]: r for r in rows}

    def period(a, b):
        rs = [by[d.isoformat()] for d in days(a, b)]
        rev = [r["revenue_usd"] for r in rs if r["revenue_usd"] is not None]
        return {"first": a.isoformat(), "last": b.isoformat(), "days": len(rs),
                "kept_near_per_day": mean([r["kept_near"] for r in rs]),
                "kept_usd_per_day": mean([r["kept_usd"] for r in rs]),
                "revenue_usd_per_day": mean(rev) if len(rev) == len(rs) else None,
                "days_with_no_inflow": sum(r["kept_near"] <= 0 for r in rs)}

    before, after = period(*BEFORE), period(*AFTER)
    n = after["days"]
    runs = [mean([by[d.isoformat()]["kept_near"] for d in days(s, s + timedelta(n - 1))])
            for s in days(BEFORE[0], BEFORE[1] - timedelta(n - 1))]
    st = {}
    for name in ("confidential_treasury.json", "confidential_treasury_daily.json"):   # the daily file grows:
        p = data_root / name                                                        # only the values used count
        if p.exists():
            st.update({r["date"]: Fraction(r["by_group_usd"]["stablecoins"])
                       for r in json.loads(p.read_text(encoding="utf-8"))["series"]})
    ends = {k: st.get(v) for k, v in (("before_start", BEFORE[0].isoformat()), ("after_start", AFTER[0].isoformat()),
                                       ("after_end", (AFTER[1] + timedelta(1)).isoformat()))}
    f = lambda x, p=6: None if x is None else fees.fmt(x, p)  # noqa: E731
    out = {
        "measure": "what the buybacks wallets kept a day on mainnet, before and after the date from which "
                   "another repository reports private settlement growing",
        "rules": __doc__.split("    python")[0].strip(),
        "external_source": SOURCE,
        "periods": {name: {k: (f(v) if isinstance(v, Fraction) else v) for k, v in p.items()}
                    for name, p in (("before", before), ("after", after))},
        "after_over_before": {k: f(after[k] / before[k]) for k in ("kept_near_per_day", "kept_usd_per_day")},
        "before_runs_of_after_length": {"days": n, "count": len(runs), "lowest_kept_near_per_day": f(min(runs)),
                                        "highest_kept_near_per_day": f(max(runs)),
                                        "after_inside": min(runs) <= after["kept_near_per_day"] <= max(runs)},
        "treasury_stablecoins_usd": {k: f(v, 0) for k, v in ends.items()},
        "days": [{k: (f(v) if isinstance(v, Fraction) else v) for k, v in r.items()} for r in rows],
        "files_sha256": dict(sorted(files.items())),
    }
    return out, []


def dumps(doc):
    return json.dumps(doc, indent=1) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--data", default=str(REPO / "data"))
    a = ap.parse_args()
    data_root = Path(a.data).resolve()
    res, problems = compute(data_root)
    if problems:
        print("FAILED:\n  " + "\n  ".join(problems[:20]))
        return 1
    path = data_root / OUT
    if a.verify:
        if not path.exists() or path.read_text(encoding="utf-8") != dumps(res):
            print(f"FAILED: {OUT} differs from the recomputation")
            return 1
    else:
        path.write_text(dumps(res), encoding="utf-8", newline="\n")
    b, f_ = res["periods"]["before"], res["periods"]["after"]
    print(f"before {b['first']}..{b['last']}: {float(b['kept_near_per_day']):,.0f} NEAR/day, "
          f"${float(b['kept_usd_per_day']):,.0f}/day")
    print(f"after  {f_['first']}..{f_['last']}: {float(f_['kept_near_per_day']):,.0f} NEAR/day, "
          f"${float(f_['kept_usd_per_day']):,.0f}/day")
    r = res["before_runs_of_after_length"]
    print(f"after/before NEAR {float(res['after_over_before']['kept_near_per_day']):.3f}; "
          f"{r['count']} runs of {r['days']} days before: {float(r['lowest_kept_near_per_day']):,.0f}.."
          f"{float(r['highest_kept_near_per_day']):,.0f}; after inside: {r['after_inside']}")
    print("OK" if a.verify else f"OK: saved data/{OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
