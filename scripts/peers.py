"""Peers on one basis: fees, revenue and holders' revenue against token value, NEAR and three peers.

    python scripts/peers.py            # fetch (DefiLlama + CoinGecko), save every response, compute
    python scripts/peers.py --verify   # offline: recompute data/peers.json from the saved responses

Same source and same days for every token, NEAR included:
  - flows: DefiLlama /summary/fees/<slug>, dataType dailyFees, dailyRevenue and dailyHoldersRevenue,
    the days of the project's window (2026-10-02 to 2026-11-01, 00:00 UTC, 30 days), mean per day x 365.25;
  - value: CoinGecko /coins/markets, market cap and fully diluted valuation in USD, at the time of the fetch.
Flows are the window's; values are the fetch's. NEAR here is DefiLlama's "NEAR Intents" against NEAR's market
cap, the same basis as the peers, not the on-chain wallet figures of the rest of the repository.
A series DefiLlama does not publish for a token is reported as missing, never as zero.

Read-only, public endpoints, no keys.
"""
import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fees as fz  # noqa: E402
import lock_window as lw  # noqa: E402

REPO = lw.REPO
OUT_NAME = "peers.json"
WINDOW = (date(2026, 10, 2), date(2026, 11, 1))      # [start, end): 30 days, the project's window
YEAR_DAYS = Decimal("365.25")
PEERS = {   # id: (DefiLlama fees slug, CoinGecko id, label)
    "near": ("near-intents", "near", "NEAR (NEAR Intents)"),
    "near_l1": ("near", "near", "NEAR (L1 gas)"),
    "hyperliquid": ("hyperliquid", "hyperliquid", "Hyperliquid (HYPE)"),
    "aave": ("aave", "aave", "Aave (AAVE)"),
    "jupiter": ("jupiter", "jupiter-exchange-solana", "Jupiter (JUP)"),
    "ethereum": ("ethereum", "ethereum", "Ethereum (ETH)"),
    "solana": ("solana", "solana", "Solana (SOL)"),
    "sui": ("sui", "sui", "Sui (SUI)"),
    "aptos": ("aptos", "aptos", "Aptos (APT)"),
}
# NEAR's whole fee capture: NEAR Intents plus the L1's gas, against the same market cap.
COMBINED = {"near_all": (("near", "near_l1"), "near", "NEAR (Intents + L1 gas)")}
SERIES = {"fees": "dailyFees", "revenue": "dailyRevenue", "holders_revenue": "dailyHoldersRevenue"}
LLAMA_URL = "https://api.llama.fi/summary/fees/{slug}?dataType={kind}&excludeTotalDataChartBreakdown=true"
GECKO_URL = ("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids={ids}"
             "&order=market_cap_desc&per_page=50&page=1&sparkline=false")


def urls():
    out = {f"{pid}_{name}": LLAMA_URL.format(slug=slug, kind=kind)
           for pid, (slug, _g, _l) in PEERS.items() for name, kind in SERIES.items()}
    out["coingecko_markets"] = GECKO_URL.format(ids=",".join(sorted({g for _s, g, _l in PEERS.values()})))
    return out


# ---------------------------------------------------------------- pure computation

def window_days():
    d, out = WINDOW[0], []
    while d < WINDOW[1]:
        out.append(d)
        d += timedelta(days=1)
    return out


def flow(raw):
    """Mean per day over the window's days, from a DefiLlama summary response; None if not published."""
    if raw is None:
        return None, 0
    doc = json.loads(raw, parse_float=Decimal)
    chart = doc.get("totalDataChart") if isinstance(doc, dict) else None
    if not chart:
        return None, 0
    by_day = {fz.EPOCH + timedelta(days=int(ts) // fz.DAY): Decimal(str(v)) for ts, v in chart}
    days = [by_day[d] for d in window_days() if d in by_day]
    if not days:
        return None, 0
    return sum(days) / len(days), len(days)


def markets(raw):
    rows = json.loads(raw, parse_float=Decimal)
    return {r["id"]: {"market_cap": Decimal(str(r["market_cap"])) if r.get("market_cap") else None,
                      "fdv": Decimal(str(r["fully_diluted_valuation"])) if r.get("fully_diluted_valuation") else None,
                      "price": Decimal(str(r["current_price"])) if r.get("current_price") else None,
                      "last_updated": r.get("last_updated")}
            for r in rows}


def ratio(a, b):
    return None if a is None or b in (None, 0) else a / b


def row(label, slug, gid, per_year, days, m):
    mcap, fdv = m.get("market_cap"), m.get("fdv")
    vals = {
        "fees_usd_per_year": per_year["fees"],
        "revenue_usd_per_year": per_year["revenue"],
        "holders_revenue_usd_per_year": per_year["holders_revenue"],
        "market_cap_usd": mcap, "fdv_usd": fdv, "price_usd": m.get("price"),
        "mcap_to_revenue": ratio(mcap, per_year["revenue"]),
        "fdv_to_revenue": ratio(fdv, per_year["revenue"]),
        "mcap_to_fees": ratio(mcap, per_year["fees"]),
        "holders_yield_on_mcap": ratio(per_year["holders_revenue"], mcap),
    }
    r = {"label": label, "defillama_slug": slug, "coingecko_id": gid, "days": days}
    r.update({k: None if v is None else str(v) for k, v in vals.items()})
    r["value_as_of"] = m.get("last_updated")
    full = len(window_days())
    r["complete"] = all(days[k] == full for k in ("fees", "revenue"))
    r["partial"] = any(0 < n < full for n in days.values())     # some window days missing: a data problem
    return r


def compute(raws):
    """raws: {name: bytes or None}. Returns the results per token, every value a decimal string or None."""
    mk = markets(raws["coingecko_markets"])
    out, flows = {}, {}
    for pid, (slug, gid, label) in PEERS.items():
        per_year, days = {}, {}
        for name in SERIES:
            mean, n = flow(raws.get(f"{pid}_{name}"))
            days[name] = n
            per_year[name] = None if mean is None else mean * YEAR_DAYS
        flows[pid] = (per_year, days)
        out[pid] = row(label, slug, gid, per_year, days, mk.get(gid, {}))
    for cid, (parts, gid, label) in COMBINED.items():
        per_year = {name: (None if any(flows[p][0][name] is None for p in parts)
                           else sum(flows[p][0][name] for p in parts)) for name in SERIES}
        days = {name: min(flows[p][1][name] for p in parts) for name in SERIES}
        out[cid] = row(label, "+".join(PEERS[p][0] for p in parts), gid, per_year, days, mk.get(gid, {}))
    return out


# ---------------------------------------------------------------- fetch / verify

def run(data_dir, fetch=fz.fetch, now=None):
    now = now or datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    raw_dir = data_dir / "raw" / "peers" / stamp
    raw_dir.mkdir(parents=True, exist_ok=True)
    files, raws, missing = {}, {}, {}
    for name, url in urls().items():
        try:
            raw = fetch(url)
        except RuntimeError as e:
            if name == "coingecko_markets" or "refused" in str(e) or "cannot reach" in str(e):
                raise
            missing[name] = str(e)       # e.g. a series DefiLlama does not publish for this token
            raws[name] = None
            continue
        path = raw_dir / f"{name}.json"
        path.write_bytes(raw)
        files[name] = {"path": path.relative_to(data_dir.parent).as_posix(), "sha256": lw.sha256(raw),
                       "url": url}
        raws[name] = raw
    doc = {"measure": "peers on one basis: DefiLlama flows over the window, CoinGecko values at the fetch",
           "window": {"start": WINDOW[0].isoformat(), "end": WINDOW[1].isoformat(), "days": len(window_days())},
           "fetched_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "raw_files": files, "not_published": missing,
           "results": compute(raws)}
    (data_dir / OUT_NAME).write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8", newline="\n")
    return doc


def verify(path):
    path = Path(path)
    doc = json.loads(path.read_text(encoding="utf-8"))
    root = path.resolve().parent.parent
    problems, raws = [], {}
    for name, f in doc["raw_files"].items():
        p = root / f["path"]
        if not p.exists():
            problems.append(f"missing {f['path']}")
            continue
        raw = p.read_bytes()
        if lw.sha256(raw) != f["sha256"]:
            problems.append(f"sha256 differs: {f['path']}")
        raws[name] = raw
    for name in doc["not_published"]:
        raws[name] = None
    if problems:
        return problems, doc
    if compute(raws) != doc["results"]:
        problems.append("results do not recompute from the saved responses")
    return problems, doc


def describe(doc):
    def x(v):
        return "—" if v is None else f"{Decimal(v):,.0f}×"
    return "; ".join(f"{r['label']}: mcap/revenue {x(r['mcap_to_revenue'])}" for r in doc["results"].values())


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--verify", nargs="?", const=f"data/{OUT_NAME}", metavar="FILE")
    args = parser.parse_args()
    if args.verify:
        problems, doc = verify(REPO / args.verify)
        if problems:
            print("\n".join(problems))
            print("PEERS VERIFY: FAIL")
            return 1
        print(f"OK: {describe(doc)}")
        return 0
    try:
        doc = run(REPO / "data")
    except RuntimeError as e:
        print(f"PEERS: NOT FETCHED - {e}")
        return 2
    print(describe(doc))
    for pid, r in doc["results"].items():
        print(f"  {pid}: days {r['days']}, complete {r['complete']}, value as of {r['value_as_of']}")
    if doc["not_published"]:
        print("  not published: " + ", ".join(doc["not_published"]))
    print(f"saved data/{OUT_NAME}; offline check: python scripts/peers.py --verify")
    return 0


if __name__ == "__main__":
    sys.exit(main())
