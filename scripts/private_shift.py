"""Did capture stop once NEAR Intents moved to the private path? Offline, from saved files.

Another public repository on NEAR Intents, Tideline (github.com/ervhint/tideline-thesis, THESIS.md at commit
90a78e6, saved in data/raw/sources/), reads the transfers of the Confidential Intents Treasury account from
intents.near's logs and reports that "Since 27 Oct 2026 swaps settle on intents.far, which public indexers
cannot see", and that over 2 to 8 November the Treasury account "carried 85% of the USD counted on chain".
We do not re-read those transactions. We take its date as given and compare:

  before   2 October to 26 October 2026 (the window's start to the day before Tideline's date)
  after    27 October to 8 November 2026 (Tideline's date to the last day of its 85% week)

The result depends on the date, so the same comparison is also made with the change on 20, 24 and
30 October and 2 November (cut_dates).

For each day D, like for like with DefiLlama, whose revenue counts NEAR flowing into the same three wallets:
  kept NEAR     change in NEAR held by the three revenue wallets between the first blocks at or after
                00:00 UTC of D and of D+1: buybacks.multisignature.near and 1csfundsadmin.sputnik-dao.near
                (the buybacks wallets) and fefundsadmin.sputnik-dao.near (the front-end fund), native NEAR
                plus the wNEAR buybacks and fefundsadmin hold inside intents.near. Boundaries and balances:
                base_rates.py's files (data/raw/base_rates/days/), the end blocks daily.py locked
                (data/daily/, data/raw/accounts/), and the front-end fund at the boundaries neither had
                read, saved by --fetch with daily.py's calls and file names (data/raw/accounts/).
  revenue NEAR  DefiLlama's revenue for NEAR Intents on D in USD / coingecko:near at 12:00 UTC of D.
  kept USD      kept NEAR x the same price.
Days near the end of a DefiLlama fetch can still be revised. DefiLlama and prices come from one fetch saved
by rating.py, pinned below (FETCH), so the result does not move when new fetches are saved.

Judged against noise, not by a test: daily inflows are lumpy, so each after-mean is set against every mean
of the same number of consecutive days inside "before" (its lowest and highest). The Treasury account's
stablecoins at both ends come from confidential_treasury(.json, _daily.json).

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
CUT_DATES = (date(2026, 10, 20), date(2026, 10, 24), date(2026, 10, 27), date(2026, 10, 30), date(2026, 11, 2))
SOURCE = ("Tideline, github.com/ervhint/tideline-thesis, THESIS.md at commit 90a78e6a358315331dbb0c68548edcb736244a3e "
          "(saved: data/raw/sources/tideline_thesis.md): \"Since 27 Oct 2026 swaps settle on intents.far, which public "
          "indexers cannot see\"; the Confidential Intents Treasury \"carried 85% of the USD counted on chain\", "
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


def boundary_heights(data_root):
    """date -> height of the first block at or after 00:00 UTC, from base_rates.py's and daily.py's saved files."""
    out = {}
    for p in sorted((data_root / "raw" / "base_rates" / "days").glob("*.json")):
        doc = json.loads(p.read_text(encoding="utf-8"))
        out[date.fromisoformat(doc["date"])] = doc["height"]
    for p in sorted((data_root / "daily").glob("*.json")):
        try:
            date.fromisoformat(p.stem)
        except ValueError:
            continue
        doc = json.loads(p.read_text(encoding="utf-8"))
        for end in ("start", "end"):
            d, h = date.fromisoformat(doc[end]["date"]), doc[end]["height"]
            if out.setdefault(d, h) != h:
                raise SystemExit(f"{d}: two different boundary blocks saved ({out[d]}, {h})")
    return out


def fefunds_files(data_root, h):
    acc = data_root / "raw" / "accounts"
    return acc / f"{h}_{daily.FEFUNDS}.json", acc / f"{h}_{daily.FEFUNDS}_intents_wnear.json"


def fetch_fefunds(data_root):
    """Read the front-end fund at every day boundary of BEFORE and AFTER that no script has saved yet.
    Same calls and file names as daily.py: view_account, and the wNEAR it holds inside intents.near."""
    import base64
    import lock_window as lw
    heights = boundary_heights(data_root)
    chain, n = None, 0
    for d in days(BEFORE[0], AFTER[1] + timedelta(1)):
        if d not in heights:
            raise SystemExit(f"{d}: no boundary block saved; run base_rates.py or daily.py first")
        h = heights[d]
        acct_f, wnear_f = fefunds_files(data_root, h)
        if acct_f.exists() and wnear_f.exists():
            continue
        chain = chain or lw.Chain()
        acct_f.parent.mkdir(parents=True, exist_ok=True)
        acct_f.write_bytes(daily.rpc_call(chain, {"request_type": "view_account", "block_id": h,
                                                  "account_id": daily.FEFUNDS}))
        args = base64.b64encode(json.dumps({"account_id": daily.FEFUNDS, "token_id": daily.WNEAR}).encode()).decode()
        wnear_f.write_bytes(daily.rpc_call(chain, {"request_type": "call_function", "block_id": h,
                                                   "account_id": daily.INTENTS, "method_name": "mt_balance_of",
                                                   "args_base64": args}))
        n += 1
        print(f"{d}  block {h}  front-end fund saved", flush=True)
    print(f"front-end fund: {n} boundaries fetched, the rest were already saved")


def fefunds_balances(data_root, files, problems):
    """date -> yocto NEAR of the front-end fund (native NEAR plus wNEAR inside intents.near)."""
    out = {}
    heights = boundary_heights(data_root)
    for d in days(BEFORE[0], AFTER[1] + timedelta(1)):
        h = heights.get(d)
        acct_f, wnear_f = fefunds_files(data_root, h) if h else (None, None)
        if not h or not acct_f.exists() or not wnear_f.exists():
            problems.append(f"{d}: front-end fund not saved (python scripts/private_shift.py --fetch)")
            continue
        res = json.loads(acct_f.read_bytes())["result"]
        if res["block_height"] != h or int(res["locked"]):
            problems.append(f"{d}: front-end fund read at another block or has staked NEAR")
        w = json.loads(wnear_f.read_bytes())["result"]
        out[d] = int(res["amount"]) + int(json.loads(bytes(w["result"]).decode()))
        for f in (acct_f, wnear_f):
            files[f.relative_to(data_root.parent).as_posix()] = fees.sha256(f.read_bytes())
    return out


def mean(xs):
    return sum(xs) / len(xs)


def compute(data_root):
    bal, files, problems = balances(data_root)
    fe = fefunds_balances(data_root, files, problems)
    fetch = data_root / FETCH
    price = fees.price_series((fetch / "price.json").read_bytes())
    revenue = fees.daily_series((fetch / "revenue.json").read_bytes(), "revenue")
    for name in ("price.json", "revenue.json"):
        files[(fetch / name).relative_to(data_root.parent).as_posix()] = fees.sha256((fetch / name).read_bytes())
    rows = []
    for d in days(BEFORE[0], AFTER[1]):
        n = d + timedelta(1)
        if d not in bal or n not in bal or d not in fe or n not in fe or d not in price or revenue.get(d) is None:
            problems.append(f"{d}: no balance at both ends, no price or no revenue")
            continue
        b = Fraction(bal[n] - bal[d], fees.YOCTO)
        f = Fraction(fe[n] - fe[d], fees.YOCTO)
        rows.append({"date": d.isoformat(), "kept_near": b + f, "buybacks_near": b, "front_end_near": f,
                     "kept_usd": (b + f) * price[d], "revenue_usd": revenue[d], "revenue_near": revenue[d] / price[d]})
    if problems:
        return None, problems
    by = {r["date"]: r for r in rows}
    keys = ("kept_near", "buybacks_near", "front_end_near", "kept_usd", "revenue_usd", "revenue_near")

    def period(a, b):
        rs = [by[d.isoformat()] for d in days(a, b)]
        out = {"first": a.isoformat(), "last": b.isoformat(), "days": len(rs)}
        out.update({f"{k}_per_day": mean([r[k] for r in rs]) for k in keys})
        out["kept_share_of_revenue"] = out["kept_near_per_day"] / out["revenue_near_per_day"]
        out["days_with_no_inflow"] = sum(r["kept_near"] <= 0 for r in rs)
        return out

    before, after = period(*BEFORE), period(*AFTER)
    n = after["days"]
    starts = days(BEFORE[0], BEFORE[1] - timedelta(n - 1))
    runs = {k: [mean([by[d.isoformat()][k] for d in days(s, s + timedelta(n - 1))]) for s in starts]
            for k in ("kept_near", "revenue_near")}
    cuts = []
    for c in CUT_DATES:   # the same comparison with the change on other days: the result's dependence on the date
        b, a = period(BEFORE[0], c - timedelta(1)), period(c, AFTER[1])
        cuts.append({"cut": c.isoformat(), **{f"{k}_after_over_before": a[f"{k}_per_day"] / b[f"{k}_per_day"]
                                              for k in ("kept_near", "buybacks_near", "revenue_near", "revenue_usd")}})
    st = {}
    for name in ("confidential_treasury.json", "confidential_treasury_daily.json"):   # the daily file grows:
        p = data_root / name                                                        # only the values used count
        if p.exists():
            st.update({r["date"]: Fraction(r["by_group_usd"]["stablecoins"])
                       for r in json.loads(p.read_text(encoding="utf-8"))["series"]})
    ends = {k: st.get(v) for k, v in (("before_start", BEFORE[0].isoformat()), ("after_start", AFTER[0].isoformat()),
                                       ("after_end", (AFTER[1] + timedelta(1)).isoformat()))}
    f = lambda x, p=6: None if x is None else fees.fmt(x, p)  # noqa: E731
    conv = lambda d: {k: (f(v) if isinstance(v, Fraction) else v) for k, v in d.items()}  # noqa: E731
    out = {
        "measure": "what the three revenue wallets kept a day on mainnet, in NEAR, before and after the date from which "
                   "another repository reports private settlement growing, beside DefiLlama's revenue in NEAR",
        "rules": __doc__.split("    python")[0].strip(),
        "external_source": SOURCE,
        "periods": {"before": conv(before), "after": conv(after)},
        "after_over_before": {k: f(after[f"{k}_per_day"] / before[f"{k}_per_day"]) for k in keys},
        "before_runs_of_after_length": {"days": n, "count": len(starts),
                                        **{f"{x}_{k}_per_day": f(fn(runs[k])) for k in runs
                                           for x, fn in (("lowest", min), ("highest", max))},
                                        "after_inside": all(min(runs[k]) <= after[f"{k}_per_day"] <= max(runs[k])
                                                            for k in runs)},
        "cut_dates": [conv(c) for c in cuts],
        "treasury_stablecoins_usd": {k: f(v, 0) for k, v in ends.items()},
        "days": [conv(r) for r in rows],
        "files_sha256": dict(sorted(files.items())),
    }
    return out, []


def dumps(doc):
    return json.dumps(doc, indent=1) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--fetch", action="store_true", help="read the front-end fund at the boundaries not yet saved "
                                                         "(network, read-only), then compute")
    ap.add_argument("--data", default=str(REPO / "data"))
    a = ap.parse_args()
    data_root = Path(a.data).resolve()
    if a.fetch:
        fetch_fefunds(data_root)
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
    for x in (b, f_):
        print(f"{x['first']}..{x['last']}: wallets kept {float(x['kept_near_per_day']):,.0f} NEAR/day, "
              f"DefiLlama revenue {float(x['revenue_near_per_day']):,.0f} NEAR/day")
    r, ab = res["before_runs_of_after_length"], res["after_over_before"]
    print(f"after/before: wallets {float(ab['kept_near']):.3f}, revenue {float(ab['revenue_near']):.3f} (NEAR); "
          f"{r['count']} runs of {r['days']} days before: {float(r['lowest_kept_near_per_day']):,.0f}.."
          f"{float(r['highest_kept_near_per_day']):,.0f}; after inside: {r['after_inside']}")
    print("OK" if a.verify else f"OK: saved data/{OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
