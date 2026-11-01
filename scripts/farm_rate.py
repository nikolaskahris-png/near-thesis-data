"""Finding 6: the NEAR AI farm's reward rate, and every change to it, from stake.dao itself.

stake.dao (source: houseofstake/house-of-stake-contracts, staking-contract/) pays the
"NEAR AI Cloud Credits" farm in reward units: 24-decimal accounting units per second per
staked NEAR (`FarmPool.reward_rate`, types.rs; `farm_delta_reward_units`, stake.rs). The
contract has no USD conversion (staking-contract/README.md); credits are off-chain.

The rate changes only through `edit_price` (prices.rs), which the pool owner or a
catalog manager of that validator may call. This script:
  1. lists every `edit_price` receipt to stake.dao on NearBlocks (all time);
  2. reads each transaction's arguments and signer (NearBlocks);
  3. reads `get_farm_pool` on archival RPC one block before the receipt and 10 blocks
     after it (the call settles in a callback), `get_validator` (catalog managers) and
     the pool's `get_owner_id` at the receipt block;
  4. checks: the rate after equals the rate in the call's arguments, and the rate
     before differs from it.

Privacy: the signer's account and the catalog manager list go to data/private/farm/;
the public file keeps a sha256 tag and two booleans (signer is pool owner / catalog
manager).

Usage:
    python scripts/farm_rate.py            fetch, save, compute
    python scripts/farm_rate.py --verify   offline check of data/farm_rate.json
"""
import argparse
import base64
import hashlib
import json
import sys
import time
import urllib.parse
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lock_window as lw  # noqa: E402
import stakers  # noqa: E402

CONTRACT = "stake.dao"
VALIDATOR = "nearai.pool.near"
FARM_PRICE = "price_QzmSvxbZqdbV0XbG6VD6KkbB"
RECEIPTS = f"https://api.nearblocks.io/v3/accounts/{CONTRACT}/receipts"
TXN = "https://api.nearblocks.io/v1/txns/{}"
OUT_NAME = "farm_rate.json"
YOCTO = 10 ** 24
YEAR_S = 31_557_600  # 365.25 days
AFTER = 10           # blocks after the receipt: the change lands in a callback


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def tag(acct):
    return "sha256:" + sha256(acct.encode())[:16]


def units_per_near_year(rate):
    """reward_rate (24-decimal units / s / NEAR) -> whole units per staked NEAR per year."""
    return Fraction(int(rate) * YEAR_S, YOCTO)


def dec6(fr):
    scaled = round(Fraction(fr) * 10 ** 6)
    return f"{scaled // 10 ** 6}.{scaled % 10 ** 6:06d}"


# ---------------------------------------------------------------- fetch

class Store:
    def __init__(self, root):
        self.root = root
        self.files = {}

    def put(self, key, raw, private):
        sub = "private/farm" if private else "raw/farm"
        path = self.root / "data" / sub / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        self.files[key] = {"path": path.relative_to(self.root).as_posix(),
                           "sha256": sha256(raw), "private": private}
        return raw

    def saved(self, key, private):
        p = self.root / "data" / ("private/farm" if private else "raw/farm") / key
        return p.read_bytes() if p.exists() else None


def view_raw(chain, height, account, method, args):
    body = {"jsonrpc": "2.0", "id": "farm", "method": "query",
            "params": {"request_type": "call_function", "block_id": height,
                       "account_id": account, "method_name": method,
                       "args_base64": base64.b64encode(json.dumps(args).encode()).decode()}}
    raw = chain._post(body)
    doc = json.loads(raw)
    if "error" in doc or "result" not in doc.get("result", {}):
        raise RuntimeError(f"{method} on {account} at {height}: {raw[:300]!r}")
    return raw


def fetch(chain, store, get=stakers.http_get, wait=stakers.PAGE_WAIT):
    cursor, n, receipts = None, 1, []
    while True:
        q = {"method": "edit_price", "limit": 100}
        if cursor:
            q["next"] = cursor
        key = f"nearblocks_edit_price/page_{n:03d}.json"
        raw = store.saved(key, True)
        if raw is None:
            if n > 1:
                time.sleep(wait)
            raw = get(RECEIPTS + "?" + urllib.parse.urlencode(q))
        store.put(key, raw, True)
        doc = json.loads(raw)
        rows = stakers.receipts_in(doc)
        receipts += rows
        cursor = stakers.next_cursor(doc)
        if not cursor or not rows:
            break
        n += 1
    for r in receipts:
        h = int(r["block"]["block_height"])
        tx = r["transaction_hash"]
        if store.saved(f"txn/{tx}.json", True) is None:
            time.sleep(wait)
            store.put(f"txn/{tx}.json", get(TXN.format(tx)), True)
        else:
            store.put(f"txn/{tx}.json", store.saved(f"txn/{tx}.json", True), True)
        for hh in (h - 1, h + AFTER):
            store.put(f"farm_pool_{hh}.json",
                      view_raw(chain, hh, CONTRACT, "get_farm_pool", {"price_id": FARM_PRICE}),
                      False)
        store.put(f"get_validator_{h}.json",
                  view_raw(chain, h, CONTRACT, "get_validator", {"validator_id": VALIDATOR}), True)
        store.put(f"get_owner_id_{h}.json",
                  view_raw(chain, h, VALIDATOR, "get_owner_id", {}), False)
        chain.block(h)
        store.put(f"block_{h}.json", chain.raw[h], False)


# ---------------------------------------------------------------- pure part

def decode(raw):
    return json.loads(bytes(json.loads(raw)["result"]["result"]).decode())


def build(root, files):
    """Everything from the saved files. Returns (doc part, problems)."""
    def load(key):
        return (root / files[key]["path"]).read_bytes()

    def have(key):
        return key in files and (root / files[key]["path"]).exists()

    problems = []
    pages = sorted(k for k in files if k.startswith("nearblocks_edit_price/"))
    private_present = all(have(k) for k in files if files[k]["private"])
    changes = []
    if not private_present:
        return None, problems
    receipts = []
    for k in pages:
        receipts += stakers.receipts_in(json.loads(load(k)))
    for r in sorted(receipts, key=lambda r: int(r["block"]["block_height"])):
        h = int(r["block"]["block_height"])
        tx = r["transaction_hash"]
        txn = json.loads(load(f"txn/{tx}.json"))["txns"][0]
        signer = txn["signer_account_id"]
        args = {}
        for a in txn.get("actions", []):
            if a.get("method") == "edit_price":
                args = json.loads(a.get("args") or "{}")
        before = decode(load(f"farm_pool_{h - 1}.json"))
        after = decode(load(f"farm_pool_{h + AFTER}.json"))
        managers = decode(load(f"get_validator_{h}.json")).get("catalog_manager_account_ids", [])
        owner = decode(load(f"get_owner_id_{h}.json"))
        hdr = json.loads(load(f"block_{h}.json"))["result"]["header"]
        new_rate = ((args.get("metadata") or {}).get("farm_reward_rate"))
        if args.get("price_id") != FARM_PRICE:
            continue  # an edit of another price: not the farm
        rb, ra = int(before["reward_rate"]), int(after["reward_rate"])
        if new_rate is not None and int(new_rate) != ra:
            problems.append(f"{tx}: rate after ({ra}) differs from the call ({new_rate})")
        changes.append({
            "tx_hash": tx, "receipt_block": h, "receipt_utc": lw.iso(hdr["timestamp"]),
            "receipt_succeeded": bool((r.get("outcome") or {}).get("status")),
            "signer_tag": tag(signer), "signer_is_pool_owner": signer == owner,
            "signer_is_catalog_manager": signer in managers,
            "catalog_managers": len(managers),
            "rate_before": str(rb), "rate_after": str(ra), "rate_changed": rb != ra,
            "ratio_after_before": dec6(Fraction(ra, rb)) if rb else None,
            "units_per_near_year_before": dec6(units_per_near_year(rb)),
            "units_per_near_year_after": dec6(units_per_near_year(ra)),
        })
    rate_changes = [c for c in changes if c["rate_changed"]]
    return {"edit_price_receipts_all_time": len(receipts),
            "farm_price_edits": len(changes),
            "rate_changes": len(rate_changes),
            "changes": changes}, problems


def run(chain, root, get=stakers.http_get, wait=stakers.PAGE_WAIT):
    store = Store(root)
    fetch(chain, store, get=get, wait=wait)
    part, problems = build(root, store.files)
    if problems:
        raise SystemExit("Checks failed:\n  " + "\n  ".join(problems))
    doc = {"measure": "finding 6: NEAR AI farm reward rate and its changes",
           "contract": CONTRACT, "farm_price_id": FARM_PRICE, "validator": VALIDATOR,
           "rules": {"units_per_near_year": "reward_rate x 31,557,600 / 1e24 "
                                            "(24-decimal units per second per staked NEAR)",
                     "rate_before": "get_farm_pool one block before the edit_price receipt",
                     "rate_after": f"get_farm_pool {AFTER} blocks after it"},
           "privacy": "signer and catalog manager accounts stay in data/private/farm/",
           "raw_files": dict(sorted(store.files.items()))}
    doc.update(part)
    out = root / "data" / OUT_NAME
    out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8", newline="\n")
    return doc


def verify(path):
    path = Path(path)
    doc = json.loads(path.read_text(encoding="utf-8"))
    root = path.resolve().parent.parent
    problems, missing = [], 0
    for key, f in doc["raw_files"].items():
        p = root / f["path"]
        if not p.exists():
            if f["private"]:
                missing += 1
            else:
                problems.append(f"missing public file {f['path']}")
        elif sha256(p.read_bytes()) != f["sha256"]:
            problems.append(f"sha256 mismatch: {f['path']}")
    if problems:
        return problems, missing
    # public part: every rate before/after recomputes from the public farm_pool files
    for c in doc["changes"]:
        for side, hh in (("before", c["receipt_block"] - 1), ("after", c["receipt_block"] + AFTER)):
            raw = (root / doc["raw_files"][f"farm_pool_{hh}.json"]["path"]).read_bytes()
            rate = decode(raw)["reward_rate"]
            if rate != c[f"rate_{side}"] or dec6(units_per_near_year(rate)) != \
                    c[f"units_per_near_year_{side}"]:
                problems.append(f"{c['tx_hash']}: rate {side} does not recompute")
    if not missing:
        part, p = build(root, doc["raw_files"])
        problems += p
        if part is not None and any(doc.get(k) != v for k, v in part.items()):
            problems.append("result does not recompute from the private files")
    return problems, missing


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--verify", nargs="?", const=str(lw.REPO / "data" / OUT_NAME),
                        metavar="FILE")
    args = parser.parse_args()
    if args.verify:
        problems, missing = verify(args.verify)
        if problems:
            print("FAILED:\n  " + "\n  ".join(problems))
            sys.exit(1)
        print("OK: sha256 match and every rate recomputes"
              + (f"; {missing} private file(s) absent, signer checks not recomputed"
                 if missing else ""))
        return
    chain = lw.Chain()
    doc = run(chain, lw.REPO)
    print(f"edit_price receipts (all time): {doc['edit_price_receipts_all_time']}, farm price "
          f"edits: {doc['farm_price_edits']}, rate changes: {doc['rate_changes']}")
    for c in doc["changes"]:
        print(f"  {c['receipt_utc'][:19]}Z block {c['receipt_block']:,} tx {c['tx_hash']}: "
              f"{c['units_per_near_year_before']} -> {c['units_per_near_year_after']} units/NEAR/yr"
              f" (x{c['ratio_after_before']}); signer is pool owner: {c['signer_is_pool_owner']},"
              f" catalog manager: {c['signer_is_catalog_manager']}")
    print(f"Saved data/{OUT_NAME} ({chain.calls} RPC calls)")


if __name__ == "__main__":
    main()
