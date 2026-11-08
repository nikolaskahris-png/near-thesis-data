"""Demand for NEAR Intents against its peers: 30 days of volume on DefiLlama, one source, one method.

    python scripts/demand.py            # fetch DefiLlama, save every response, compute data/demand.json
    python scripts/demand.py --verify   # offline: recompute data/demand.json from the saved responses

DefiLlama's volume dataset (the same adapters that give NEAR Intents' volume elsewhere in the repository)
has two lists a cross-chain swap can sit in: /overview/dexs with category "Bridge" (where NEAR Intents is)
and /overview/bridge-aggregators (LI.FI, 0x, Socket and others). Both report each protocol's volume over
the 30 days before the fetch (total30d). This script saves both lists and ranks NEAR Intents among every
protocol in them, and also against every protocol with volume in /overview/dexs, whatever its category,
both as DefiLlama lists them (each version of a protocol separately) and with versions added up under
their parent protocol. /overview/dexs is DefiLlama's DEX-volume overview; NEAR Intents sits in it as a
"Bridge".

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
    # The same 30 days against every protocol in the volume list, whatever its category (DEXs, launchpads,
    # prediction markets...): where NEAR Intents stands without choosing the peer group.
    full = [r for r in json.loads(raws["bridge"], parse_float=Decimal)["protocols"]
            if r.get("total30d") is not None and Decimal(str(r["total30d"])) > 0]
    full.sort(key=lambda r: (-Decimal(str(r["total30d"])), r.get("slug") or r.get("module") or ""))
    pos = next((i for i, r in enumerate(full) if (r.get("slug") or r.get("module")) == OURS), None)
    # The same list with every protocol's versions added up under its parent (Uniswap V3 + V4 + ... as one),
    # since DefiLlama lists versions separately; a protocol with no parent stands alone.
    groups = {}
    for r in full:
        g = r.get("parentProtocol") or f"id#{r.get('defillamaId') or r.get('id') or r.get('slug')}"
        groups[g] = groups.get(g, Decimal(0)) + Decimal(str(r["total30d"]))
    ours_group = None if pos is None else (full[pos].get("parentProtocol")
                                           or f"id#{full[pos].get('defillamaId') or full[pos].get('id') or OURS}")
    ranked = sorted(groups.items(), key=lambda kv: (-kv[1], kv[0]))
    gpos = None if ours_group is None else [k for k, _ in ranked].index(ours_group)
    return {
        "parent_rank": None if gpos is None else gpos + 1,
        "parent_groups_with_volume": len(ranked),
        "ours_group": ours_group,
        "ours_group_30d_usd": None if gpos is None else str(ranked[gpos][1]),
        "all_rank": None if pos is None else pos + 1,
        "all_protocols_with_volume": len(full),
        "all_categories_above": [] if pos is None else sorted({r.get("category") or "none" for r in full[:pos]}),
        "ours_30d_usd": None if ours is None else str(ours["volume_30d_usd"]),
        "ours_rank": None if ours is None else 1 + rows.index(ours),
        "protocols_ranked": len(rows),
        "bridges_with_volume": sum(1 for r in rows if r["list"] == "bridge"),
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
            f"{r['largest_aggregator']['name']} ${Decimal(r['largest_aggregator']['volume_30d_usd']) / 10 ** 9:.2f}B; "
            f"rank {r['all_rank']} of {r['all_protocols_with_volume']} in the whole volume list")


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
