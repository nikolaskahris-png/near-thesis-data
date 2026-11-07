"""Demand for NEAR Intents against its peers: 30 days of volume on DefiLlama, one source, one method.

    python scripts/demand.py            # fetch DefiLlama, save every response, compute data/demand.json
    python scripts/demand.py --verify   # offline: recompute data/demand.json from the saved responses

DefiLlama's volume dataset (the same adapters that give NEAR Intents' volume elsewhere in the repository)
has two lists a cross-chain swap can sit in: /overview/dexs with category "Bridge" (where NEAR Intents is)
and /overview/bridge-aggregators (LI.FI, 0x, Socket and others). Both report each protocol's volume over
the 30 days before the fetch (total30d). This script saves both lists and ranks NEAR Intents among every
protocol in them.

Not compared: DefiLlama's separate bridges dataset (Across, Relay, deBridge, Stargate), which counts
deposits rather than swaps and whose detail needs a paid key. Aggregators may route some orders through
NEAR Intents, so their volume can overlap with it; the ranking compares sizes, it does not add them up.
The 30 days are those before the fetch, not the project's window.

Read-only, public endpoints, no keys.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fees as fz  # noqa: E402
import lock_window as lw  # noqa: E402

REPO = lw.REPO
OUT_NAME = "demand.json"
OURS = "near-intents"
LISTS = {
    "bridge": ("https://api.llama.fi/overview/dexs?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true",
               "Bridge"),
    "bridge_aggregator": ("https://api.llama.fi/overview/bridge-aggregators?excludeTotalDataChart=true"
                          "&excludeTotalDataChartBreakdown=true", None),
}


def rows_of(raw, category):
    out = []
    for r in json.loads(raw, parse_float=Decimal)["protocols"]:
        if category and r.get("category") != category:
            continue
        v = r.get("total30d")
        if v is None:
            continue
        out.append({"slug": r.get("slug") or r.get("module"), "name": r.get("displayName") or r.get("name"),
                    "volume_30d_usd": Decimal(str(v))})
    return out


def compute(raws):
    rows = []
    for key, (_url, category) in LISTS.items():
        for r in rows_of(raws[key], category):
            rows.append(dict(r, list=key))
    rows = [r for r in rows if r["volume_30d_usd"] > 0]
    rows.sort(key=lambda r: (-r["volume_30d_usd"], r["slug"]))
    ours = next((r for r in rows if r["slug"] == OURS), None)
    others = [r for r in rows if r["slug"] != OURS]
    agg = [r for r in others if r["list"] == "bridge_aggregator"]
    return {
        "ours_30d_usd": None if ours is None else str(ours["volume_30d_usd"]),
        "ours_rank": None if ours is None else 1 + rows.index(ours),
        "protocols_ranked": len(rows),
        "largest_other": None if not others else {k: str(v) if isinstance(v, Decimal) else v
                                                  for k, v in others[0].items()},
        "largest_aggregator": None if not agg else {k: str(v) if isinstance(v, Decimal) else v
                                                    for k, v in agg[0].items()},
        "ours_over_largest_other": None if not (ours and others) else
        str(ours["volume_30d_usd"] / others[0]["volume_30d_usd"]),
        "ours_over_largest_aggregator": None if not (ours and agg) else
        str(ours["volume_30d_usd"] / agg[0]["volume_30d_usd"]),
        "top": [{k: str(v) if isinstance(v, Decimal) else v for k, v in r.items()} for r in rows[:8]],
    }


def run(data_dir, fetch=fz.fetch, now=None):
    now = now or datetime.now(timezone.utc)
    raw_dir = data_dir / "raw" / "demand" / now.strftime("%Y%m%dT%H%M%SZ")
    raw_dir.mkdir(parents=True, exist_ok=True)
    files, raws = {}, {}
    for key, (url, _c) in LISTS.items():
        raw = fetch(url)
        path = raw_dir / f"{key}.json"
        path.write_bytes(raw)
        files[key] = {"path": path.relative_to(data_dir.parent).as_posix(), "sha256": lw.sha256(raw), "url": url}
        raws[key] = raw
    res = compute(raws)
    if res["ours_30d_usd"] is None:
        raise RuntimeError(f"{OURS} not found in DefiLlama's 'Bridge' volume list")
    doc = {"measure": "NEAR Intents' 30-day volume ranked among DefiLlama's bridge and bridge-aggregator volume lists",
           "basis": "DefiLlama total30d at the fetch: the 30 days before it, not the project's window",
           "not_compared": "DefiLlama's bridges dataset (deposits, paid detail): Across, Relay, deBridge, Stargate",
           "fetched_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "raw_files": files, "results": res}
    (data_dir / OUT_NAME).write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8", newline="\n")
    return doc


def verify(path):
    path = Path(path)
    doc = json.loads(path.read_text(encoding="utf-8"))
    root = path.resolve().parent.parent
    problems, raws = [], {}
    for key, f in doc["raw_files"].items():
        p = root / f["path"]
        if not p.exists():
            problems.append(f"missing {f['path']}")
            continue
        raw = p.read_bytes()
        if lw.sha256(raw) != f["sha256"]:
            problems.append(f"sha256 differs: {f['path']}")
        raws[key] = raw
    if not problems and compute(raws) != doc["results"]:
        problems.append("results do not recompute from the saved responses")
    return problems, doc


def describe(doc):
    r = doc["results"]
    return (f"NEAR Intents ${Decimal(r['ours_30d_usd']) / 10 ** 9:.2f}B in 30 days, rank {r['ours_rank']} of "
            f"{r['protocols_ranked']}; largest other {r['largest_other']['name']} "
            f"${Decimal(r['largest_other']['volume_30d_usd']) / 10 ** 9:.2f}B; largest aggregator "
            f"{r['largest_aggregator']['name']} ${Decimal(r['largest_aggregator']['volume_30d_usd']) / 10 ** 9:.2f}B")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--verify", nargs="?", const=f"data/{OUT_NAME}", metavar="FILE")
    args = parser.parse_args()
    if args.verify:
        problems, doc = verify(REPO / args.verify)
        if problems:
            print("\n".join(problems))
            print("DEMAND VERIFY: FAIL")
            return 1
        print(f"OK: {describe(doc)}")
        return 0
    try:
        doc = run(REPO / "data")
    except RuntimeError as e:
        print(f"DEMAND: NOT FETCHED - {e}")
        return 2
    print(describe(doc))
    for r in doc["results"]["top"]:
        print(f"  {r['name']:<32} {r['list']:<18} ${Decimal(r['volume_30d_usd']):>16,.0f}")
    print(f"saved data/{OUT_NAME}; offline check: python scripts/demand.py --verify")
    return 0


if __name__ == "__main__":
    sys.exit(main())
