"""The rating's rules applied to four other protocols, from their docs and DefiLlama, not read on their chains.

Question: are the rules built so that everything comes out Hold? We apply the same three tests to Hyperliquid
(HYPE), Pump.fun (PUMP), Aave (AAVE) and Jupiter (JUP), and to NEAR, and print each test before the rating.

  Gate 1  Lock        the bought tokens sit where they cannot be sent out: a system address with no key, or burned.
                      A contract counts only once we have reviewed its code, as for NEAR (rating.py AUDITED_CODE);
                      we have reviewed none, so a contract that its owner calls irreversible does not pass.
  Gate 2  No drain    the bought stock did not fall more than 10% below its peak. That needs balances read on
                      their chains, which we did not read, so it is "not read" and cannot give Avoid.
  Gate 3  Coverage    tokens bought a year >= new tokens a year. Bought = DefiLlama's holders' revenue a year
                      / the mean price, both over the project's window (data/peers.json; PUMP from --fetch).
                      New tokens on two bases: what the protocol issues (what NEAR's coverage counts: minted),
                      and that plus insiders' scheduled unlocks. The growth leg (+75% a year) is not tested:
                      it needs a year of their history.

  Rating  Buy if gates 1 and 3 pass; Avoid if gate 2 fails; otherwise Hold. NEAR's own rules have two more
          tests (treasury.near sends nothing; two 30-day revenue floors) that only make sense for NEAR.

Every input that is not DefiLlama's or CoinGecko's comes from a saved page with its quote (quotes.py).

Usage:
    python scripts/peers_rating.py --fetch     fetch PUMP's DefiLlama flows and price for the window (network)
    python scripts/peers_rating.py             write data/peers_rating.json from the saved files
    python scripts/peers_rating.py --verify    recompute and compare with the saved file
"""
import argparse
import json
import math
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fees as fz  # noqa: E402
import lock_window as lw  # noqa: E402
import peers  # noqa: E402

REPO = lw.REPO
OUT = "peers_rating.json"
FETCH_OUT = "peers_rating_fetch.json"
YEAR = Decimal("365.25")
MONTHS = Decimal(12)

PUMP_SLUGS = ("pump", "pump.fun")       # DefiLlama: the parent first, then the launchpad alone
PUMP_GECKO = "pump-fun"

HYPE_RATE_AT_400M = Decimal("0.0237")   # hl_docs_staking: "approximately 2.37% per year" at 400M staked
HYPE_STAKED_REF = Decimal(400_000_000)
HYPE_STAKED_REPORTED = Decimal(440_000_000)   # cryptobriefing_hype_staked


def hype_rewards(staked):
    """The docs' rule: the rate is inversely proportional to the square root of total stake."""
    rate = HYPE_RATE_AT_400M * Decimal(math.sqrt(float(HYPE_STAKED_REF / staked)))
    return rate * staked


INPUTS = {
    "hyperliquid": {
        "label": "Hyperliquid (HYPE)", "token": "HYPE",
        "lock": True,
        "lock_note": "the assistance fund is a system address; its HYPE is burned (docs)",
        "sources": ["hl_docs_fees", "hl_docs_staking", "cryptobriefing_hype_staked", "tokenomist_hype"],
        "new_per_year": [
            ("protocol, docs' reference (400M staked)", hype_rewards(HYPE_STAKED_REF)),
            ("protocol, 440M staked as reported", hype_rewards(HYPE_STAKED_REPORTED)),
            ("protocol + team claims as announced", hype_rewards(HYPE_STAKED_REF) + Decimal(330_000) * MONTHS),
            ("protocol + team unlocks on schedule", hype_rewards(HYPE_STAKED_REF) + Decimal(9_916_666) * MONTHS),
        ],
    },
    "pump": {
        "label": "Pump.fun (PUMP)", "token": "PUMP",
        "lock": False,
        "lock_note": "a contract the press calls irreversible, for one year; we have not reviewed its code",
        "sources": ["indexvn_pump", "kucoin_pump_unlock"],
        "new_per_year": [
            ("protocol (fixed supply, no issuance)", Decimal(0)),
            ("protocol + insider unlocks on schedule", Decimal("6.875e9") * MONTHS),
        ],
    },
    "aave": {
        "label": "Aave (AAVE)", "token": "AAVE",
        "lock": False,
        "lock_note": "bought AAVE goes to the Ecosystem Reserve, which governance can spend",
        "sources": ["blofin_aave"],
        "new_per_year": [],          # not needed: gate 1 fails, and DefiLlama counts no holders' revenue
    },
    "jupiter": {
        "label": "Jupiter (JUP)", "token": "JUP",
        "lock": False,
        "lock_note": "bought JUP sits in the Litterbox Trust; the DAO votes on whether to burn it",
        "sources": ["jup_litterbox_burn", "tokenomist_jup"],
        "new_per_year": [
            ("protocol, no new team tokens or airdrop (schedule of 29 Oct 2026)", Decimal(0)),
        ],
    },
}


def decide(lock, drained, coverage):
    """The rating's order: a drain gives Avoid; a lock and full coverage give Buy; anything else Hold."""
    if drained is True:
        return "Avoid"
    if lock and coverage is not None and coverage >= 1:
        return "Buy"
    return "Hold"


def coverage(bought, new):
    if bought is None or new is None:
        return None
    if new == 0:
        return None if bought == 0 else Decimal("Infinity")
    return bought / new


# ---------------------------------------------------------------- inputs from saved files

def bought_per_year(data_root):
    """{peer: (tokens bought a year, holders' revenue USD a year, mean price)} from peers.json and the PUMP fetch."""
    out = {}
    res = json.loads((data_root / "peers.json").read_text(encoding="utf-8"))["results"]
    for pid in ("hyperliquid", "aave", "jupiter"):
        r = res[pid]
        hr = Decimal(r["holders_revenue_usd_per_year"]) if r["holders_revenue_usd_per_year"] else Decimal(0)
        mp = Decimal(r["mean_price_usd"])
        out[pid] = (hr / mp, hr, mp)
    fpath = data_root / FETCH_OUT
    if fpath.exists():
        f = json.loads(fpath.read_text(encoding="utf-8"))
        hr = Decimal(f["holders_revenue_usd_per_year"]) if f["holders_revenue_usd_per_year"] else None
        mp = Decimal(f["mean_price_usd"]) if f["mean_price_usd"] else None
        out["pump"] = (None if hr is None or mp is None else hr / mp, hr, mp)
    else:
        out["pump"] = (None, None, None)
    return out


def near_row(data_root):
    n = json.loads((data_root / "numbers.json").read_text(encoding="utf-8"))["numbers"]
    bought = Decimal(n["n1.buybacks_near_per_day"]["value"]) * YEAR
    new = Decimal(n["n1.new_near_per_day"]["value"]) * YEAR
    return bought, new


def compute(data_root):
    data_root = Path(data_root)
    bought = bought_per_year(data_root)
    rows = {}
    for pid, inp in INPUTS.items():
        b, hr, mp = bought[pid]
        scen = []
        for name, new in inp["new_per_year"]:
            c = coverage(b, new)
            scen.append({"basis": name, "new_per_year": str(new), "coverage": None if c is None else str(c),
                         "gate3_coverage": None if c is None else bool(c >= 1),
                         "rating": decide(inp["lock"], None, c)})
        rows[pid] = {
            "label": inp["label"], "token": inp["token"],
            "gate1_lock": inp["lock"], "lock_note": inp["lock_note"],
            "gate2_no_drain": "not read on their chain",
            "bought_per_year": None if b is None else str(b),
            "holders_revenue_usd_per_year": None if hr is None else str(hr),
            "mean_price_usd": None if mp is None else str(mp),
            "bases": scen,
            "rating": decide(inp["lock"], None, None) if not scen else
                      ("Buy" if any(s["rating"] == "Buy" for s in scen) and all(s["rating"] == "Buy" for s in scen)
                       else "Buy on some bases" if any(s["rating"] == "Buy" for s in scen) else "Hold"),
            "sources": inp["sources"],
        }
    nb, nn = near_row(data_root)
    nc = nb / nn
    rows["near"] = {"label": "NEAR (NEAR Intents)", "token": "NEAR", "gate1_lock": False,
                    "lock_note": "the buybacks sit in multisigs that 2 of 4 signers can move",
                    "gate2_no_drain": "read on mainnet daily (rating.py)",
                    "bought_per_year": str(nb), "bases": [{"basis": "protocol", "new_per_year": str(nn),
                    "coverage": str(nc), "gate3_coverage": bool(nc >= 1), "rating": decide(False, False, nc)}],
                    "rating": decide(False, False, nc), "sources": ["data/numbers.json"]}
    return {"measure": __doc__.splitlines()[0], "window": "2026-10-02 to 2026-11-01 (peers.json)",
            "not_applied": ["growth leg (+75% a year): needs a year of their history",
                            "treasury.near and the two 30-day revenue floors: NEAR-specific",
                            "drain: their balances were not read on their chains"],
            "rows": rows}, []


def dumps(doc):
    def fix(x):
        if isinstance(x, dict):
            return {k: fix(v) for k, v in x.items()}
        if isinstance(x, list):
            return [fix(v) for v in x]
        if isinstance(x, str):
            try:
                d = Decimal(x)
            except Exception:
                return x
            if not d.is_finite():
                return x
            return format(d.quantize(Decimal("0.000001")), "f")
        return x
    return json.dumps(fix(doc), indent=1) + "\n"


# ---------------------------------------------------------------- fetch (network, run by the author)

def fetch(data_root, fetch=fz.fetch, now=None):
    now = now or datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    raw_dir = data_root / "raw" / "peers_rating" / stamp
    raw_dir.mkdir(parents=True, exist_ok=True)
    files, flows, used = {}, {}, None
    for slug in PUMP_SLUGS:
        got = {}
        for name, kind in peers.SERIES.items():
            url = peers.LLAMA_URL.format(slug=slug, kind=kind)
            try:
                raw = fetch(url)
            except RuntimeError as e:
                if "refused" in str(e) or "cannot reach" in str(e):
                    raise
                got[name] = (None, None, url)
                continue
            got[name] = (raw, lw.sha256(raw), url)
        if got.get("holders_revenue", (None,))[0] is not None:
            used = slug
            break
    if used is None:
        raise SystemExit("no DefiLlama holders' revenue for PUMP under " + ", ".join(PUMP_SLUGS))
    for name, (raw, digest, url) in got.items():
        if raw is None:
            continue
        path = raw_dir / f"pump_{name}.json"
        path.write_bytes(raw)
        files[f"pump_{name}"] = {"path": path.relative_to(data_root.parent).as_posix(), "sha256": digest, "url": url}
        flows[name] = peers.flow(raw)
    purl = peers.price_url(PUMP_GECKO)
    praw = fetch(purl)
    path = raw_dir / "price_pump.json"
    path.write_bytes(praw)
    files["price_pump"] = {"path": path.relative_to(data_root.parent).as_posix(), "sha256": lw.sha256(praw), "url": purl}
    doc = {"fetched_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "defillama_slug": used, "coingecko_id": PUMP_GECKO,
           "raw_files": files}
    doc.update(derive(data_root, files))
    (data_root / FETCH_OUT).write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8", newline="\n")
    return doc


def derive(data_root, files):
    """PUMP's means over the window, recomputed from the saved raw files."""
    root = data_root.parent
    out = {}
    for name in peers.SERIES:
        f = files.get(f"pump_{name}")
        mean, n = peers.flow((root / f["path"]).read_bytes()) if f else (None, 0)
        out[f"{name}_usd_per_year"] = None if mean is None else str(mean * peers.YEAR_DAYS)
        out[f"{name}_days"] = n
    mp, n = peers.mean_price((root / files["price_pump"]["path"]).read_bytes(), PUMP_GECKO)
    out["mean_price_usd"] = None if mp is None else str(mp)
    out["price_days"] = n
    return out


def verify_fetch(data_root):
    path = data_root / FETCH_OUT
    if not path.exists():
        return ["data/peers_rating_fetch.json is missing: run --fetch"]
    doc = json.loads(path.read_text(encoding="utf-8"))
    problems = []
    for name, f in doc["raw_files"].items():
        p = data_root.parent / f["path"]
        if not p.exists() or lw.sha256(p.read_bytes()) != f["sha256"]:
            problems.append(f"{name}: raw file missing or changed")
    if not problems:
        again = derive(data_root, doc["raw_files"])
        for k, v in again.items():
            if doc.get(k) != v:
                problems.append(f"{k}: {doc.get(k)} saved, {v} recomputed")
    return problems


def show(doc):
    for pid, r in doc["rows"].items():
        b = r["bought_per_year"]
        print(f"{r['label']}: bought {float(b):,.0f} {r['token']}/yr" if b else f"{r['label']}: bought n/a")
        print(f"  Gate 1 lock: {'PASS' if r['gate1_lock'] else 'FAIL'} ({r['lock_note']})")
        print(f"  Gate 2 no drain: {r['gate2_no_drain']}")
        for s in r["bases"]:
            c = s["coverage"]
            ctext = "n/a" if c is None else ("no new tokens" if c == "Infinity" else f"{float(c):.0%}")
            print(f"  Gate 3 coverage, {s['basis']}: {ctext} -> {s['rating']}")
        print(f"  Rating: {r['rating']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--data", default=str(REPO / "data"))
    a = ap.parse_args()
    data_root = Path(a.data).resolve()
    if a.fetch:
        d = fetch(data_root)
        print(f"PUMP: slug {d['defillama_slug']}, holders' revenue ${float(d['holders_revenue_usd_per_year'] or 0):,.0f}/yr, "
              f"mean price ${float(d['mean_price_usd'] or 0):.6f}, days {d['holders_revenue_days']}/{d['price_days']}")
    problems = verify_fetch(data_root) if (data_root / FETCH_OUT).exists() else []
    res, p2 = compute(data_root)
    problems += p2
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
    show(res)
    print("OK" if a.verify else f"OK: saved data/{OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
