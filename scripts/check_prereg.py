"""Check that PREREG.md is the file anchored on NEAR mainnet, and when.

The anchor is one SocialDB write (`social.near` method `set`), signed by the project's
account. This script reads it back in four read-only calls and compares:

  1. social.near get  "samerice7976.near/thesis/prereg/1/**"   the stored record now
  2. tx               the anchoring transaction: signer, receiver, method, the exact
                      args it carried, and that every receipt succeeded
  3. block            the block that included the transaction (height, UTC time)
  4. block            the block where social.near executed it

Pass = sha256(PREREG.md) == the sha256 in the stored record == the sha256 in the
transaction's own args, the byte counts match, signer is the project's account,
and nothing in the transaction failed.

Proof stored: the four raw responses, byte for byte, in data/raw/prereg/, with sha256,
and the result in data/prereg.json.

Read-only: JSON-RPC "query" (call_function), "tx" and "block". No API keys, nothing
is written on chain.

Usage:
    python scripts/check_prereg.py --file      PREREG.md against the anchored sha256 (no network)
    python scripts/check_prereg.py             read the anchor (4 calls), save, check
    python scripts/check_prereg.py --verify    offline check of data/prereg.json
"""
import argparse
import base64
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lock_window as lw  # noqa: E402

REPO = lw.REPO
OUT_NAME = "prereg.json"
FILE_NAME = "PREREG.md"
SIGNER = "samerice7976.near"
CONTRACT = "social.near"
KEY = f"{SIGNER}/thesis/prereg/1"
TX_HASH = "8fZ8VTUyM1UjnybqPd1QCQi4c3y75dDRGR5TjkNGgnPL"
ANCHORED_SHA256 = "d3f48ed9172b1785b4dcf290b84e9a06c870b8b9b5481c6d40e51a4605b1d494"


# ---------- RPC ----------

def rpc(chain, method, params):
    raw = chain._post({"jsonrpc": "2.0", "id": "prereg", "method": method, "params": params})
    doc = json.loads(raw)
    if "error" in doc or "result" not in doc:
        raise RuntimeError(f"{method}: {json.dumps(doc.get('error'))[:300]}")
    return raw


def fetch(chain):
    """The four raw responses."""
    args = json.dumps({"keys": [f"{KEY}/**"]}).encode()
    raw_get = rpc(chain, "query", {"request_type": "call_function", "finality": "final",
                                   "account_id": CONTRACT, "method_name": "get",
                                   "args_base64": base64.b64encode(args).decode()})
    raw_tx = rpc(chain, "tx", {"tx_hash": TX_HASH, "sender_account_id": SIGNER,
                               "wait_until": "FINAL"})
    tx = json.loads(raw_tx)["result"]
    raw_tx_block = rpc(chain, "block", {"block_id": tx["transaction_outcome"]["block_hash"]})
    receipt = social_receipt(tx)
    raw_exec_block = rpc(chain, "block", {"block_id": receipt["block_hash"]})
    return {"social_get": raw_get, "tx": raw_tx, "tx_block": raw_tx_block,
            "execution_block": raw_exec_block}


# ---------- reading the responses ----------

def social_receipt(tx):
    """The receipt that social.near executed (the FunctionCall itself)."""
    for r in tx.get("receipts_outcome", []):
        if r["outcome"].get("executor_id") == CONTRACT:
            return r
    raise RuntimeError("no receipt executed by social.near in the transaction")


def stored_record(raw_get):
    doc = json.loads(raw_get)["result"]
    data = json.loads(bytes(doc["result"]).decode())
    node = data
    for part in KEY.split("/"):
        node = (node or {}).get(part)
    return node, doc["block_height"]


def sent_record(tx):
    """The record inside the transaction's own `set` args."""
    actions = tx["transaction"]["actions"]
    calls = [a["FunctionCall"] for a in actions if isinstance(a, dict) and "FunctionCall" in a]
    if len(calls) != 1 or calls[0]["method_name"] != "set":
        return None, calls
    args = json.loads(base64.b64decode(calls[0]["args"]))
    node = args.get("data")
    for part in KEY.split("/"):
        node = (node or {}).get(part)
    return node, calls[0]


def header(raw_block):
    h = json.loads(raw_block)["result"]["header"]
    return {"height": h["height"], "hash": h["hash"], "timestamp_utc": lw.iso(h["timestamp"])}


def file_check(root):
    data = (root / FILE_NAME).read_bytes()
    return {"sha256": lw.sha256(data), "bytes": len(data),
            "matches_anchored_sha256": lw.sha256(data) == ANCHORED_SHA256}


def build(root, raw_files):
    """Everything computed from the raw files and PREREG.md. Used by run() and --verify."""
    def load(key):
        return (root / raw_files[key]["path"]).read_bytes()

    tx = json.loads(load("tx"))["result"]
    stored, read_at = stored_record(load("social_get"))
    sent, call = sent_record(tx)
    f = file_check(root)
    failures = [r["id"] for r in tx.get("receipts_outcome", [])
                if "Failure" in (r["outcome"].get("status") or {})]
    receipt = social_receipt(tx)
    checks = {
        "file_sha256_is_anchored_sha256": f["matches_anchored_sha256"],
        "stored_record_found": isinstance(stored, dict),
        "stored_sha256_equals_file": isinstance(stored, dict) and stored.get("sha256") == f["sha256"],
        "stored_bytes_equal_file": isinstance(stored, dict) and stored.get("bytes") == str(f["bytes"]),
        "tx_args_record_equals_stored": sent is not None and sent == stored,
        "tx_signer_is_project_account": tx["transaction"]["signer_id"] == SIGNER,
        "tx_receiver_is_social_near": tx["transaction"]["receiver_id"] == CONTRACT,
        "tx_status_success": "SuccessValue" in (tx.get("status") or {}),
        "no_receipt_failed": not failures,
        "execution_block_after_tx_block":
            header(load("execution_block"))["height"] >= header(load("tx_block"))["height"],
    }
    return {
        "file": {"name": FILE_NAME, **f},
        "stored_record": stored,
        "stored_record_read_at_block": read_at,
        "transaction": {
            "hash": tx["transaction"]["hash"],
            "signer_id": tx["transaction"]["signer_id"],
            "receiver_id": tx["transaction"]["receiver_id"],
            "method": call.get("method_name") if isinstance(call, dict) else None,
            "deposit_yocto": call.get("deposit") if isinstance(call, dict) else None,
            "included_in_block": header(load("tx_block")),
            "executed_in_block": header(load("execution_block")),
            "social_receipt_id": receipt["id"],
        },
        "checks": checks,
    }


# ---------- run / verify ----------

def run(chain, data_dir):
    raws = fetch(chain)
    raw_dir = data_dir / "raw" / "prereg"
    raw_dir.mkdir(parents=True, exist_ok=True)
    fetched = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    names = {"social_get": f"social_get_{fetched}.json", "tx": f"tx_{TX_HASH}.json",
             "tx_block": "tx_block.json", "execution_block": "execution_block.json"}
    raw_files = {}
    for key, raw in raws.items():
        path = raw_dir / names[key]
        path.write_bytes(raw)
        raw_files[key] = {"path": path.relative_to(data_dir.parent).as_posix(),
                          "sha256": lw.sha256(raw)}
    doc = {
        "measure": "pre-registration anchor: PREREG.md against its SocialDB record",
        "key": KEY,
        "anchored_sha256": ANCHORED_SHA256,
        "source": {"rpc": chain.url, "methods": ["query call_function get", "tx", "block"]},
        "fetched_utc": fetched,
        "raw_files": raw_files,
    }
    doc.update(build(data_dir.parent, raw_files))
    return doc


def verify(path):
    """Offline check. Returns a list of problems (empty = OK)."""
    path = Path(path)
    doc = json.loads(path.read_text(encoding="utf-8"))
    root = path.resolve().parent.parent  # data/prereg.json -> repo root
    problems = []
    for key, f in doc["raw_files"].items():
        p = root / f["path"]
        if not p.exists():
            problems.append(f"missing raw file {f['path']}")
        elif lw.sha256(p.read_bytes()) != f["sha256"]:
            problems.append(f"sha256 mismatch: {f['path']}")
    if problems:
        return problems
    again = build(root, doc["raw_files"])
    for key, value in again.items():
        if doc.get(key) != value:
            problems.append(f"'{key}' does not recompute from the raw files")
    problems += [f"check failed: {k}" for k, ok in again["checks"].items() if not ok]
    return problems


def show(doc):
    t = doc["transaction"]
    print(f"{FILE_NAME}: {doc['file']['bytes']} bytes, sha256 {doc['file']['sha256']}")
    print(f"SocialDB {doc['key']} (read at block {doc['stored_record_read_at_block']:,}): "
          f"sha256 {(doc['stored_record'] or {}).get('sha256')}")
    print(f"tx {t['hash']}: {t['signer_id']} -> {t['receiver_id']}.{t['method']}, "
          f"included in block {t['included_in_block']['height']:,} "
          f"({t['included_in_block']['timestamp_utc'][:19]}Z), "
          f"executed in block {t['executed_in_block']['height']:,} "
          f"({t['executed_in_block']['timestamp_utc'][:19]}Z)")
    bad = [k for k, ok in doc["checks"].items() if not ok]
    print("Checks: all OK" if not bad else f"Checks FAILED: {', '.join(bad)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--file", action="store_true",
                        help="only compare PREREG.md with the anchored sha256 (no network)")
    parser.add_argument("--verify", nargs="?", const=str(REPO / "data" / OUT_NAME), metavar="FILE",
                        help="offline check (default data/prereg.json)")
    parser.add_argument("--data-dir", type=Path, default=REPO / "data")
    args = parser.parse_args()
    if args.file:
        f = file_check(args.data_dir.parent)
        print(f"{FILE_NAME} sha256 {f['sha256']}\nanchored   sha256 {ANCHORED_SHA256}")
        if not f["matches_anchored_sha256"]:
            print("FAILED: PREREG.md is not the anchored file")
            sys.exit(1)
        print("OK: PREREG.md is the anchored file")
        return
    if args.verify:
        problems = verify(args.verify)
        if problems:
            print("FAILED:\n  " + "\n  ".join(problems))
            sys.exit(1)
        print("OK: raw sha256 match, PREREG.md = stored record = transaction args, tx succeeded")
        return
    chain = lw.Chain(pause=0.5)
    doc = run(chain, args.data_dir)
    out = args.data_dir / OUT_NAME
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    show(doc)
    print(f"Saved {out.relative_to(args.data_dir.parent).as_posix()} ({chain.calls} calls)")
    problems = verify(out)
    if problems:
        print("VERIFY FAILED:\n  " + "\n  ".join(problems))
        sys.exit(1)


if __name__ == "__main__":
    main()
