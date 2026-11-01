"""Watch the validators' vote for the next NEAR protocol version.

A governance vote (HSP-027, HSP-029) changes nothing on chain by itself: it takes a
nearcore release, and the new protocol version starts only when block producers holding
protocol_upgrade_stake_threshold (4/5) of the stake run it. HSP-027 (remove the developer
gas rebate) is protocol version 87 in nearcore 2.14.0; its mainnet vote opens on
2026-11-04 00:00 UTC (core/primitives/src/version.rs, tag 2.14.0).

Each block header carries latest_protocol_version, the version its producer runs. This
script walks back SAMPLE blocks from the latest final block, keeps each producer's most
recent value, and weights it by the producer's stake in the current epoch:

  signaling_share = stake of sampled producers at >= TARGET / stake of all block producers
  seen_share      = stake of sampled producers / stake of all block producers

It also records the protocol version in force (EXPERIMENTAL_protocol_config).

Saved per run: data/upgrade_watch/<UTC date>.json with every sampled block (height, hash,
prev_hash, version) and every producer as sha256(account)[:16] with its stake and version,
so the shares recompute offline (--verify) and the blocks can be re-read from any archival
node. No producer names are stored. One row per date in data/upgrade_watch.csv.

Read-only: JSON-RPC "block", "validators", "EXPERIMENTAL_protocol_config". No keys.

Usage:
    python scripts/upgrade_watch.py              # now
    python scripts/upgrade_watch.py --verify     # offline check of every saved day
"""
import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lock_window as lw  # noqa: E402

REPO = lw.REPO
TARGET = 87
SAMPLE = 300
COLUMNS = ["date", "utc", "final_height", "protocol_version", "target_version",
           "blocks_sampled", "producers_seen", "block_producers", "seen_share",
           "signaling_share", "threshold"]


def rpc(chain, method, params):
    doc = json.loads(chain._post({"jsonrpc": "2.0", "id": "watch", "method": method,
                                  "params": params}))
    if "error" in doc or "result" not in doc:
        raise RuntimeError(f"{method}: {json.dumps(doc.get('error'))[:300]}")
    return doc["result"]


def anon(account):
    return hashlib.sha256(account.encode()).hexdigest()[:16]


def share(part, total, places=6):
    scaled = round(Fraction(part, total) * 10 ** places) if total else 0
    return f"{scaled // 10 ** places}.{scaled % 10 ** places:0{places}d}"


def collect(chain, sample=SAMPLE):
    top = rpc(chain, "block", {"finality": "final"})
    height = top["header"]["height"]
    pc = rpc(chain, "EXPERIMENTAL_protocol_config", {"block_id": height})
    vals = rpc(chain, "validators", {"epoch_id": top["header"]["epoch_id"]})
    blocks, b = [], top
    while len(blocks) < sample:
        h = b["header"]
        blocks.append({"height": h["height"], "hash": h["hash"], "prev_hash": h["prev_hash"],
                       "epoch_id": h["epoch_id"], "author": b["author"],
                       "version": h["latest_protocol_version"]})
        b = rpc(chain, "block", {"block_id": h["prev_hash"]})
    latest = {}
    for blk in blocks:  # newest first: keep each producer's most recent block
        latest.setdefault(blk["author"], blk["version"])
    producers = [{"id": anon(v["account_id"]), "stake": v["stake"],
                  "version": latest.get(v["account_id"])}
                 for v in vals["current_validators"] if int(v.get("num_expected_blocks", 0)) > 0]
    for blk in blocks:
        blk["author"] = anon(blk["author"])
    return {
        "utc": lw.iso(top["header"]["timestamp"]),
        "final_height": height,
        "protocol_version": pc["protocol_version"],
        "threshold": f"{pc['protocol_upgrade_stake_threshold'][0]}/{pc['protocol_upgrade_stake_threshold'][1]}",
        "epoch_id": top["header"]["epoch_id"],
        "blocks": blocks,
        "producers": sorted(producers, key=lambda p: p["id"]),
    }


def compute(doc, target=TARGET):
    blocks, producers = doc["blocks"], doc["producers"]
    total = sum(int(p["stake"]) for p in producers)
    seen = [p for p in producers if p["version"] is not None]
    signaling = sum(int(p["stake"]) for p in seen if p["version"] >= target)
    chain_ok = all(a["prev_hash"] == b["hash"] and a["height"] > b["height"]
                   for a, b in zip(blocks, blocks[1:]))
    latest = {}
    for blk in blocks:  # newest first
        latest.setdefault(blk["author"], blk["version"])
    versions_ok = all(p["version"] == latest.get(p["id"]) for p in producers)
    return {
        "target_version": target,
        "blocks_sampled": len(blocks),
        "producers_seen": len(seen),
        "block_producers": len(producers),
        "seen_share": share(sum(int(p["stake"]) for p in seen), total),
        "signaling_share": share(signaling, total),
        "checks": {"sampled_blocks_form_one_chain": chain_ok,
                   "producer_versions_match_their_latest_block": versions_ok,
                   "authors_are_block_producers":
                       {b["author"] for b in blocks} <= {p["id"] for p in producers}},
    }


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        for r in sorted(rows, key=lambda r: r["date"]):
            w.writerow(r)


def row_of(day, doc):
    r = {"date": day, "utc": doc["utc"], "final_height": doc["final_height"],
         "protocol_version": doc["protocol_version"], "threshold": doc["threshold"]}
    r.update({k: v for k, v in doc["result"].items() if k in COLUMNS})
    return r


def save(data_dir, doc):
    day = doc["utc"][:10]
    out_dir = data_dir / "upgrade_watch"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{day}.json"
    path.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8", newline="\n")
    rows = {}
    csv_path = data_dir / "upgrade_watch.csv"
    if csv_path.exists():
        with open(csv_path, newline="", encoding="utf-8") as f:
            rows = {r["date"]: r for r in csv.DictReader(f)}
    rows[day] = row_of(day, doc)
    write_csv(csv_path, rows.values())
    return path


def verify(data_dir):
    problems = []
    rows = {}
    for path in sorted((data_dir / "upgrade_watch").glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        again = compute(doc, doc["result"]["target_version"])
        if again != doc["result"]:
            problems.append(f"{path.name}: result does not recompute")
        problems += [f"{path.name}: check failed: {k}" for k, ok in again["checks"].items() if not ok]
        rows[path.stem] = {k: str(v) for k, v in row_of(path.stem, doc).items()}
    csv_path = data_dir / "upgrade_watch.csv"
    if rows:
        with open(csv_path, newline="", encoding="utf-8") as f:
            saved = {r["date"]: r for r in csv.DictReader(f)}
        if saved != rows:
            problems.append("upgrade_watch.csv does not match the day files")
    return problems, len(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--target", type=int, default=TARGET)
    parser.add_argument("--sample", type=int, default=SAMPLE)
    parser.add_argument("--data-dir", type=Path, default=REPO / "data")
    args = parser.parse_args()
    if args.verify:
        problems, n = verify(args.data_dir)
        if problems:
            print("FAILED:\n  " + "\n  ".join(problems))
            sys.exit(1)
        print(f"OK: {n} day(s) recompute from the saved samples")
        return
    chain = lw.Chain(pause=0.3)
    doc = collect(chain, args.sample)
    doc["result"] = compute(doc, args.target)
    path = save(args.data_dir, doc)
    r = doc["result"]
    print(f"{doc['utc'][:19]}Z block {doc['final_height']:,}: protocol {doc['protocol_version']}, "
          f"{r['signaling_share']} of block-producer stake signals >= {args.target} "
          f"(seen {r['producers_seen']}/{r['block_producers']} producers, {r['seen_share']} of stake; "
          f"needs {doc['threshold']})")
    print(f"Saved {path.relative_to(args.data_dir.parent).as_posix()} ({chain.calls} calls)")
    bad = [k for k, ok in r["checks"].items() if not ok]
    if bad:
        print("Checks FAILED: " + ", ".join(bad))
        sys.exit(1)


if __name__ == "__main__":
    main()
