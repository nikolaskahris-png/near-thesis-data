"""Measured base rates for the probabilities of PREREG-3.md.

The probabilities in PREREG-3.md are not guesses: each is how often the same event happened in the
history of the measure itself: the wallets from 1 April 2026 (buybacks.multisignature.near did not
exist on 1 March), DefiLlama from 1 March 2026 (the first full month after the fee switch of 23 February).

  P6 / P7  For every pair of 30-day windows whose starts are 38 days apart (as 2 October -> 9 November):
           how often the later window's buybacks kept, in USD a day, was at least half (P6) / at least
           all (P7) of the earlier one's. "Kept" is PREREG-3.md's measure without the treasury.near
           exclusion (no such transfer is known): the change in native NEAR of
           buybacks.multisignature.near and 1csfundsadmin.sputnik-dao.near, plus the wNEAR
           buybacks.multisignature.near holds inside intents.near, between the first blocks at or after
           00:00 UTC of the window's first day and of the day after its last, / 30, x the mean
           coingecko:near price at 12:00 UTC (coins.llama.fi) over the window's days.
  P8       For every 30-day window: how often all 30 days are counted by fees.py's rule and revenue is
           above zero each day, in DefiLlama's data as fetched now; and the same for the latest window
           that was at least 48 hours old in each earlier fetch saved in data/raw/defillama/ and
           data/raw/rating/.

Windows overlap: pairs one day apart share 29 of 30 days, so ~N pairs hold about N/30 independent ones.
History holds no change like the one PREREG-3.md describes for 9 November; the rates say what
happened, not what will.

Every response is saved byte for byte with its SHA-256 in data/raw/base_rates/; --verify recomputes
data/base_rates.json from them with no network.

Read-only: JSON-RPC "block" and "query", DefiLlama and coins.llama.fi. No keys, nothing written on chain.

Usage:
    python scripts/base_rates.py              # fetch (resumes where it stopped), compute, save
    python scripts/base_rates.py --verify     # offline: recompute from the saved responses
"""
import argparse
import base64
import json
import sys
from datetime import date, datetime, timedelta, timezone
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import daily  # noqa: E402
import fees  # noqa: E402
import lock_window as lw  # noqa: E402

REPO = lw.REPO
FIRST = date(2026, 3, 1)            # DefiLlama windows (P8)
FIRST_CHAIN = date(2026, 4, 1)      # buybacks.multisignature.near did not exist on 1 March
LAST = date(2026, 11, 8)            # last boundary read (00:00 UTC)
OFFSET = 38                         # days from the start of 2 Oct - 1 Nov to the start of 9 Nov - 9 Dec
WINDOW = 30
THRESHOLDS = (Fraction(1, 2), Fraction(1))
RAW = "raw/base_rates"
OUT = "base_rates.json"
BLOCKS_PER_DAY = 145_450            # first guess only; find_boundary walks to the exact block


def sha(b):
    return lw.sha256(b)


def days(a, b):
    return [a + timedelta(i) for i in range((b - a).days + 1)]


# ---------------------------------------------------------------- fetch
def fetch_chain(data_root):
    raw_root = data_root / RAW
    day_dir = raw_root / "days"
    day_dir.mkdir(parents=True, exist_ok=True)
    chain = lw.Chain()
    guess = None
    for d in days(FIRST_CHAIN, LAST):
        out = day_dir / f"{d.isoformat()}.json"
        if out.exists():
            guess = json.loads(out.read_text(encoding="utf-8"))["height"] + BLOCKS_PER_DAY
            continue
        target = lw.midnight_ns(d)
        if guess is None:
            final = chain.final_header()
            guess = int(final["height"] - (final["timestamp"] - target) / 594_000_000)
        hdr, prev = lw.find_boundary(chain, target, guess, step=400)
        assert hdr["timestamp"] >= target > prev["timestamp"] and hdr["prev_hash"] == prev["hash"]
        h = hdr["height"]
        files = {}

        def save(name, raw):
            p = raw_root / "blocks_accounts" / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(raw)
            files[p.relative_to(data_root).as_posix()] = sha(raw)

        save(f"block_{h}.json", chain.raw[h])
        save(f"block_{prev['height']}.json", chain.raw[prev["height"]])
        for acct in (daily.BUYBACKS, daily.ONECLICK):
            save(f"{h}_{acct}.json", daily.rpc_call(chain, {"request_type": "view_account", "block_id": h,
                                                             "account_id": acct}))
        args = base64.b64encode(json.dumps({"account_id": daily.BUYBACKS, "token_id": daily.WNEAR}).encode())
        save(f"{h}_{daily.BUYBACKS}_intents_wnear.json",
             daily.rpc_call(chain, {"request_type": "call_function", "block_id": h,
                                    "account_id": daily.INTENTS, "method_name": "mt_balance_of",
                                    "args_base64": args.decode()}))
        out.write_text(json.dumps({"date": d.isoformat(), "height": h, "previous_height": prev["height"],
                                   "raw_files": files}, indent=1) + "\n", encoding="utf-8", newline="\n")
        print(f"{d}  block {h}  ({chain.calls} calls, {chain.rate_limited} x 429)", flush=True)
        guess = h + BLOCKS_PER_DAY
        chain.raw.clear()
        chain.headers.clear()


def fetch_llama(data_root):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    d = data_root / RAW / "llama" / stamp
    d.mkdir(parents=True, exist_ok=True)
    urls = dict(fees.SERIES_URLS)
    urls["price"] = fees.price_url(FIRST, LAST - timedelta(1))
    files = {}
    for k, url in urls.items():
        raw = fees.fetch(url)
        (d / f"{k}.json").write_bytes(raw)
        files[k] = {"path": (d / f"{k}.json").relative_to(data_root).as_posix(), "sha256": sha(raw), "url": url}
    (d / "fetch.json").write_text(json.dumps({"fetched_utc": stamp, "files": files}, indent=1) + "\n",
                                  encoding="utf-8", newline="\n")
    print(f"DefiLlama and coins.llama.fi saved in {d.relative_to(data_root)}")


# ---------------------------------------------------------------- compute (offline)
def balances(data_root):
    """date -> yocto NEAR of the buybacks wallets at the first block of that date, read from saved files."""
    out, problems = {}, []
    for p in sorted((data_root / RAW / "days").glob("*.json")):
        doc = json.loads(p.read_text(encoding="utf-8"))
        for rel, digest in doc["raw_files"].items():
            if sha((data_root / rel).read_bytes()) != digest:
                problems.append(f"sha256 differs: {rel}")
        d, h = date.fromisoformat(doc["date"]), doc["height"]
        ba = data_root / RAW / "blocks_accounts"
        blk = json.loads((ba / f"block_{h}.json").read_bytes())["result"]["header"]
        prv = json.loads((ba / f"block_{doc['previous_height']}.json").read_bytes())["result"]["header"]
        t = lw.midnight_ns(d)
        if not (blk["timestamp"] >= t > prv["timestamp"] and blk["prev_hash"] == prv["hash"]):
            problems.append(f"{d}: block {h} is not the first block of the day")
        total = 0
        for acct in (daily.BUYBACKS, daily.ONECLICK):
            res = json.loads((ba / f"{h}_{acct}.json").read_bytes())["result"]
            if res["block_height"] != h:
                problems.append(f"{d}: {acct} read at another block")
            if int(res["locked"]):
                problems.append(f"{d}: {acct} has staked NEAR, not counted")
            total += int(res["amount"])
        res = json.loads((ba / f"{h}_{daily.BUYBACKS}_intents_wnear.json").read_bytes())["result"]
        total += int(json.loads(bytes(res["result"]).decode()))
        out[d] = total
    return out, problems


def latest_llama(data_root):
    root = data_root / RAW / "llama"
    stamps = sorted(p.name for p in root.iterdir()) if root.exists() else []
    if not stamps:
        raise SystemExit("no DefiLlama fetch saved: run without --verify first")
    doc = json.loads((root / stamps[-1] / "fetch.json").read_text(encoding="utf-8"))
    raws, problems = {}, []
    for k, f in doc["files"].items():
        b = (data_root / f["path"]).read_bytes()
        if sha(b) != f["sha256"]:
            problems.append(f"sha256 differs: {f['path']}")
        raws[k] = b
    return doc["fetched_utc"], raws, problems


def complete_windows(s, last_day):
    """(windows, complete) over 30-day windows from FIRST whose last day <= last_day."""
    n = full = 0
    bad_days = set()
    d0 = FIRST
    while d0 + timedelta(WINDOW - 1) <= last_day:
        ds = [d0 + timedelta(i) for i in range(WINDOW)]
        flags, _ = fees.judge(ds, s)
        bad = [d for d in ds if flags[d] or s["revenue"].get(d, 0) <= 0]
        bad_days.update(bad)
        n += 1
        full += not bad
        d0 += timedelta(1)
    return n, full, sorted(bad_days)


def f6(x):
    return f"{float(x):.6f}"


def compute(data_root):
    bal, problems = balances(data_root)
    fetched, raws, p2 = latest_llama(data_root)
    problems += p2
    price = fees.price_series(raws["price"])

    def kept_usd(d0):
        d1 = d0 + timedelta(WINDOW)
        if d0 not in bal or d1 not in bal:
            return None
        ps = [price[d] for d in days(d0, d1 - timedelta(1)) if d in price]
        if len(ps) < 25:
            return None
        return Fraction(bal[d1] - bal[d0], WINDOW * fees.YOCTO) * (sum(ps) / len(ps))

    pairs = []
    d0 = FIRST_CHAIN
    while d0 + timedelta(OFFSET + WINDOW) <= LAST:
        a, b = kept_usd(d0), kept_usd(d0 + timedelta(OFFSET))
        if a is not None and b is not None:
            pairs.append((d0, a, b))
        d0 += timedelta(1)
    base = [p for p in pairs if p[1] > 0]
    rates = {}
    for t in THRESHOLDS:
        k = sum(1 for _, a, b in base if b >= t * a)
        rates[str(t)] = {"held": k, "pairs": len(base), "rate": f6(Fraction(k, len(base))) if base else None}
    by_month = {}
    for d, a, b in base:
        m = by_month.setdefault(d.strftime("%Y-%m"), {"pairs": 0, "half": 0, "all": 0})
        m["pairs"] += 1
        m["half"] += b >= a / 2
        m["all"] += b >= a
    ref = kept_usd(date(2026, 10, 2))

    s = {k: fees.daily_series(raws[k], k) for k in ("fees", "revenue", "volume")}
    s["price"] = price
    ft = datetime.strptime(fetched, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    last_ok = (ft - timedelta(hours=48)).date() - timedelta(1)
    n, full, bad = complete_windows(s, min(last_ok, max(price)))

    vintages = []
    for sub in ("raw/defillama", "raw/rating"):
        root = data_root / sub
        for v in sorted(p for p in root.iterdir() if p.is_dir()) if root.exists() else []:
            try:
                sv = {k: fees.daily_series((v / f"{k}.json").read_bytes(), k) for k in ("fees", "revenue", "volume")}
            except FileNotFoundError:
                continue
            sv["price"] = price
            vt = datetime.strptime(v.name, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            lo = (vt - timedelta(hours=48)).date() - timedelta(1)
            ds = [lo - timedelta(WINDOW - 1 - i) for i in range(WINDOW)]
            if not all(d in price for d in ds):
                continue
            flags, _ = fees.judge(ds, sv)
            badv = [str(d) for d in ds if flags[d] or sv["revenue"].get(d, 0) <= 0]
            vintages.append({"fetch": f"{sub}/{v.name}", "window": [str(ds[0]), str(ds[-1])],
                             "complete": not badv, "bad_days": badv})

    return {
        "measure": "base rates for PREREG-3.md predictions 6-8",
        "rules": __doc__.split("Usage:")[0].strip(),
        "first_day": str(FIRST), "last_boundary": str(LAST), "offset_days": OFFSET,
        "boundaries_read": len(bal),
        "check_2026_10_02_window_usd_per_day": f6(ref) if ref is not None else None,
        "p6_p7": {"thresholds": rates, "by_baseline_month": by_month,
                  "pairs_with_baseline_not_above_zero": len(pairs) - len(base),
                  "independent_pairs_about": round(len(base) / WINDOW, 1)},
        "p8": {"defillama_fetched_utc": fetched, "windows": n, "complete": full,
               "rate": f6(Fraction(full, n)) if n else None, "bad_days": [str(d) for d in bad],
               "at_48h_in_earlier_fetches": vintages},
    }, problems


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    data_root = REPO / "data"
    if not a.verify:
        fetch_chain(data_root)
        fetch_llama(data_root)
    doc, problems = compute(data_root)
    path = data_root / OUT
    text = json.dumps(doc, indent=1, ensure_ascii=False) + "\n"
    if a.verify:
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            problems.append(f"{OUT} differs from the recomputation")
    else:
        path.write_text(text, encoding="utf-8", newline="\n")
    r = doc["p6_p7"]["thresholds"]
    print(f"P6 (>= half):  {r['1/2']['held']}/{r['1/2']['pairs']} = {r['1/2']['rate']}")
    print(f"P7 (>= all):   {r['1']['held']}/{r['1']['pairs']} = {r['1']['rate']}")
    print(f"P8 (complete): {doc['p8']['complete']}/{doc['p8']['windows']} = {doc['p8']['rate']}; "
          f"at 48 h: {sum(v['complete'] for v in doc['p8']['at_48h_in_earlier_fetches'])}/"
          f"{len(doc['p8']['at_48h_in_earlier_fetches'])}")
    print(f"check: 2 Oct window ${doc['check_2026_10_02_window_usd_per_day']} a day (PREREG-3: $46,691.40)")
    if problems:
        print("FAILED:\n  " + "\n  ".join(problems[:20]))
        sys.exit(1)
    print("OK" if a.verify else f"OK: saved data/{OUT}")


if __name__ == "__main__":
    main()
