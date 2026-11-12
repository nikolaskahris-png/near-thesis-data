"""Claim E: the chain is used, and that use pays holders almost nothing. Also the organizers' question.

The track's own prompt example (nearai/near-hackathon-prompt-examples, tracks/02-thesis.md) asks for daily
active accounts and transactions, and frames a hypothesis: is cross-chain volume through NEAR Intents a better
leading indicator of real network usage than the token price? This script answers both, from NearBlocks' public
daily statistics (no key), saved byte for byte:

  /v3/txn-stats              transactions, receipts and fees (NEAR) a day
  /v3/address-stats          active accounts and active contracts a day
  /v3/price-stats            NEAR's price a day
  /v3/intents/volume-stats   NEAR Intents' volume a day as NearBlocks indexes it on NEAR mainnet (USD)
  /v3/intents/account-stats  accounts that swapped through NEAR Intents a day

Each endpoint is fetched with limit=365 and limit=60 (the most recent days), and any missing day by date.

What is computed (offline, from the saved files):
  usage     12 months, 1 November 2025 to 31 October 2026: the first and last 30 days' means of transactions,
            active accounts and fees, and their change; fees in USD a year at each day's price.
  visible   NearBlocks' Intents volume against DefiLlama's (data/raw/rating/<FETCH>/volume.json), over the
            project's window (2 October to 1 November 2026) and the 30 days before 27 October.
  lead      weekly (Monday-Sunday, UTC) log-changes over the 52 weeks from 3 November 2025. For each predictor
            X in {Intents volume (DefiLlama), Intents volume (NearBlocks), NEAR price} and each usage series Y in
            {transactions, active accounts}: the correlation of X in week t with Y in week t+k, k = 0..4. The
            best |correlation| over k is tested against 10,000 circular shifts of X (fixed seed; shifts of at
            least 6 weeks), which keeps each series' own autocorrelation; p = share of shifts whose best
            |correlation| over the same lags is at least as large. Few weeks give low power: a high p means
            "not detected", not "no effect".

    python scripts/usage.py --fetch     fetch and save (network, read-only, no key)
    python scripts/usage.py             compute data/usage.json from the saved files
    python scripts/usage.py --verify    recompute and compare
"""
import argparse
import json
import math
import random
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fees as fz  # noqa: E402
import lock_window as lw  # noqa: E402

REPO = lw.REPO
OUT = "usage.json"
FETCH_OUT = "usage_fetch.json"
BASE = "https://api.nearblocks.io"
ENDPOINTS = {"txn": "/v3/txn-stats", "address": "/v3/address-stats", "price": "/v3/price-stats",
             "intents_volume": "/v3/intents/volume-stats", "intents_accounts": "/v3/intents/account-stats"}
YEAR = (date(2025, 11, 1), date(2026, 10, 31))
WINDOW = (date(2026, 10, 2), date(2026, 10, 31))
PRE_PRIVATE = (date(2026, 9, 27), date(2026, 10, 26))
AFTER_PRIVATE = (date(2026, 10, 27), date(2026, 11, 8))    # private_shift.py's after period
WEEK_85 = (date(2026, 11, 2), date(2026, 11, 8))            # Tideline's 85% week
WEEK0 = date(2025, 11, 3)            # a Monday
WEEKS = 52
LAGS = range(0, 5)
SHIFTS = 10000
MIN_SHIFT = 6
SEED = 20261113
LLAMA_VOLUME = "data/raw/rating/20261112T071359Z/volume.json"


# ---------------------------------------------------------------- fetch

def fetch_all(data_root, fetch=fz.fetch, now=None):
    now = now or datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    raw_dir = data_root / "raw" / "usage" / stamp
    raw_dir.mkdir(parents=True, exist_ok=True)
    files = {}

    def get(name, query, tag):
        url = f"{BASE}{ENDPOINTS[name]}?{query}"
        raw = fetch(url)
        path = raw_dir / f"{name}_{tag}.json"
        path.write_bytes(raw)
        files.setdefault(name, []).append({"path": path.relative_to(data_root.parent).as_posix(),
                                           "sha256": lw.sha256(raw), "url": url})
        return json.loads(raw)["data"]

    for name in ENDPOINTS:
        rows = get(name, "limit=365", "365") + get(name, "limit=60", "60")
        have = {r["date"] for r in rows}
        d = YEAR[0]
        while d <= date(2026, 11, 8):
            if d.isoformat() not in have:
                get(name, f"limit=1&date={d.isoformat()}", d.isoformat())
            d += timedelta(days=1)
        print(f"{name}: saved {len(files[name])} responses")
    doc = {"fetched_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "source": BASE, "raw_files": files}
    (data_root / FETCH_OUT).write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8", newline="\n")
    return doc


# ---------------------------------------------------------------- inputs

def series(data_root):
    """{name: {date: row}} from the saved files, checked against their SHA-256."""
    doc = json.loads((data_root / FETCH_OUT).read_text(encoding="utf-8"))
    out, problems = {}, []
    for name, fl in doc["raw_files"].items():
        by = {}
        for f in fl:
            raw = (data_root.parent / f["path"]).read_bytes()
            if lw.sha256(raw) != f["sha256"]:
                problems.append(f"{f['path']}: changed")
                continue
            for r in json.loads(raw)["data"]:
                prev = by.get(r["date"])
                if prev is not None and prev != r:
                    # a day fetched twice can differ while NearBlocks still fills it: keep the later fetch
                    pass
                by[r["date"]] = r
        out[name] = by
    return out, problems, doc


def llama_volume(data_root):
    raw = json.loads((data_root.parent / LLAMA_VOLUME).read_text(encoding="utf-8"))
    return {datetime.fromtimestamp(int(t), timezone.utc).date().isoformat(): float(v)
            for t, v in raw["totalDataChart"]}


def days(a, b):
    d, out = a, []
    while d <= b:
        out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def mean(xs):
    return sum(xs) / len(xs)


# ---------------------------------------------------------------- statistics

def corr(x, y):
    n = len(x)
    mx, my = mean(x), mean(y)
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    if sx == 0 or sy == 0:
        return 0.0
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy)


def lagged(x, y, k):
    """x in week t against y in week t+k."""
    return (x[:len(x) - k], y[k:]) if k else (x, y)


def best_lag(x, y):
    cs = {k: corr(*lagged(x, y, k)) for k in LAGS}
    k = max(cs, key=lambda j: abs(cs[j]))
    return k, cs[k], cs


def shift_test(x, y, rng):
    _k, c, _ = best_lag(x, y)
    n, hits = len(x), 0
    for _ in range(SHIFTS):
        s = rng.randrange(MIN_SHIFT, n - MIN_SHIFT + 1)
        xs = x[s:] + x[:s]
        if abs(best_lag(xs, y)[1]) >= abs(c) - 1e-12:
            hits += 1
    return hits / SHIFTS


def weekly(byday, field, how="sum"):
    out = []
    for w in range(WEEKS + 1):
        d0 = WEEK0 + timedelta(weeks=w)
        vals = [byday[d.isoformat()][field] if field else byday[d.isoformat()]
                for d in (d0 + timedelta(days=i) for i in range(7))]
        vals = [float(v) for v in vals]
        out.append(sum(vals) if how == "sum" else mean(vals))
    return out


def dlog(xs):
    return [math.log(b / a) for a, b in zip(xs, xs[1:])]


# ---------------------------------------------------------------- compute

def compute(data_root):
    data_root = Path(data_root)
    if not (data_root / FETCH_OUT).exists():
        return None, ["data/usage_fetch.json is missing: run --fetch"]
    s, problems, fdoc = series(data_root)
    llama = llama_volume(data_root)
    need = days(YEAR[0], max(WEEK0 + timedelta(weeks=WEEKS + 1) - timedelta(days=1), WEEK_85[1]))
    for name in ("txn", "address", "price", "intents_volume"):
        miss = [d for d in need if d not in s.get(name, {})]
        if miss:
            problems.append(f"{name}: {len(miss)} days missing, first {miss[0]}")
    miss = [d for d in need if d not in llama]
    if miss:
        problems.append(f"DefiLlama volume: {len(miss)} days missing, first {miss[0]}")
    if problems:
        return None, problems
    tx, ad, pr, iv = s["txn"], s["address"], s["price"], s["intents_volume"]
    price = {d: float(r["near_price"]) for d, r in pr.items() if r.get("near_price") is not None}

    first, last = days(YEAR[0], YEAR[0] + timedelta(days=29)), days(YEAR[1] - timedelta(days=29), YEAR[1])
    usage = {}
    for key, src, field in (("txns", tx, "txns"), ("meta_txns", tx, "meta_txns"),
                            ("active_accounts", ad, "active_accounts"), ("meta_accounts", ad, "meta_accounts"),
                            ("active_contracts", ad, "active_contracts"), ("fee_near", tx, "txn_fee")):
        a = mean([float(src[d][field]) for d in first])
        b = mean([float(src[d][field]) for d in last])
        usage[key] = {"first_30d_mean": a, "last_30d_mean": b, "change": b / a - 1}
    for key, tot, meta in (("txns_not_meta", "txns", "meta_txns"), ("accounts_not_meta", "active_accounts", "meta_accounts")):
        a = usage[tot]["first_30d_mean"] - usage[meta]["first_30d_mean"]
        b = usage[tot]["last_30d_mean"] - usage[meta]["last_30d_mean"]
        usage[key] = {"first_30d_mean": a, "last_30d_mean": b, "change": b / a - 1}
    months = {}
    for d in days(*YEAR):
        months.setdefault(d[:7], []).append(float(tx[d]["txns"]))
    usage["txns_by_month"] = {m: mean(v) for m, v in sorted(months.items())}
    fee_usd_year = sum(float(tx[d]["txn_fee"]) * price[d] for d in days(*YEAR))
    usage["fee_usd_year"] = fee_usd_year
    usage["fee_usd_per_txn_last_30d"] = mean([float(tx[d]["txn_fee"]) * price[d] / float(tx[d]["txns"]) for d in last])

    visible = {}
    for key, (a, b) in (("window", WINDOW), ("before_private", PRE_PRIVATE), ("after_private", AFTER_PRIVATE),
                        ("week_85", WEEK_85)):
        nb = sum(float(iv[d]["daily"]) for d in days(a, b))
        dl = sum(llama[d] for d in days(a, b))
        visible[key] = {"first": a.isoformat(), "last": b.isoformat(), "nearblocks_usd": nb, "defillama_usd": dl,
                        "nearblocks_share": nb / dl}

    usage_y = {"txns": weekly(tx, "txns"), "active_accounts": weekly(ad, "active_accounts", "mean")}
    preds = {"intents_volume_defillama": weekly(llama, None), "intents_volume_nearblocks": weekly(iv, "daily"),
             "near_price": weekly(price, None, "mean")}
    rng = random.Random(SEED)
    lead = {}
    for pn, pv in preds.items():
        x = dlog(pv)
        for yn, yv in usage_y.items():
            y = dlog(yv)
            k, c, cs = best_lag(x, y)
            lead[f"{pn}->{yn}"] = {"best_lag_weeks": k, "corr": c, "p_shift": shift_test(x, y, rng),
                                   "corr_by_lag": {str(j): v for j, v in cs.items()}}
    return {"measure": __doc__.splitlines()[0], "fetched_utc": fdoc["fetched_utc"],
            "year": [YEAR[0].isoformat(), YEAR[1].isoformat()], "weeks": [WEEK0.isoformat(), WEEKS],
            "method": f"weekly log-changes, lags {list(LAGS)} weeks, {SHIFTS} circular shifts (min {MIN_SHIFT}), seed {SEED}",
            "usage": usage, "visible_intents_volume": visible, "lead": lead}, []


def rnd(x):
    if isinstance(x, float):
        return round(x, 6)
    if isinstance(x, dict):
        return {k: rnd(v) for k, v in x.items()}
    if isinstance(x, list):
        return [rnd(v) for v in x]
    return x


def dumps(doc):
    return json.dumps(rnd(doc), indent=1) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--data", default=str(REPO / "data"))
    a = ap.parse_args()
    data_root = Path(a.data).resolve()
    if a.fetch:
        fetch_all(data_root)
    res, problems = compute(data_root)
    if problems:
        print("FAILED:\n  " + "\n  ".join(problems))
        return 1
    path = data_root / OUT
    if a.verify:
        if not path.exists() or path.read_text(encoding="utf-8") != dumps(res):
            print(f"FAILED: {OUT} differs from the recomputation")
            return 1
    else:
        path.write_text(dumps(res), encoding="utf-8", newline="\n")
    u = res["usage"]
    for k in ("txns", "active_accounts", "fee_near"):
        print(f"{k}: {u[k]['first_30d_mean']:,.0f} -> {u[k]['last_30d_mean']:,.0f} a day ({u[k]['change']:+.0%})")
    print(f"fees a year: ${u['fee_usd_year']:,.0f}")
    for k, v in res["visible_intents_volume"].items():
        print(f"Intents volume NearBlocks/DefiLlama, {k}: {v['nearblocks_share']:.1%}")
    for k, v in res["lead"].items():
        print(f"{k}: best lag {v['best_lag_weeks']} w, corr {v['corr']:+.2f}, p {v['p_shift']:.3f}")
    print("OK" if a.verify else f"OK: saved data/{OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
