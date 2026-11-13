"""Rule (b) on a real chain: a NEAR testnet account with no contract and no access key, read by daily.lock_sealed.

The Buy rule needs a lock the chain shows cannot send NEAR out (daily.lock_sealed). No such lock exists on
mainnet, so the gate had only been tested on made-up responses. Here it reads a real account on NEAR testnet,
created from the testnet faucet and then stripped of its only key by hand (the author signed the DeleteKey; no
key is used by this script). Read-only: two JSON-RPC queries at one final block, saved byte for byte.

    python scripts/testnet_lock.py --fetch    read the account and its keys now (network), save, compute
    python scripts/testnet_lock.py            recompute data/testnet_lock.json from the saved responses
    python scripts/testnet_lock.py --verify   recompute and compare (offline)
"""
import argparse
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import daily  # noqa: E402
import lock_window as lw  # noqa: E402

REPO = lw.REPO
ACCOUNT = "near-thesis-lock-1311.testnet"
RPC = "https://rpc.testnet.near.org"
DELETE_KEY_TX = "9wRFixnLRDPixPTvc94HfCxn7Lqqqok3sxeLS5CBXkaZ"   # the author's DeleteKey of its only key, 13 Nov 2026
RAW = Path("data/raw/testnet_lock")
OUT = Path("data/testnet_lock.json")


def rpc(params):
    body = json.dumps({"jsonrpc": "2.0", "id": "near-thesis-data", "method": "query", "params": params}).encode()
    req = urllib.request.Request(RPC, data=body, headers={"Content-Type": "application/json",
                                                         "User-Agent": "near-thesis-data"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
    doc = json.loads(raw)
    if "error" in doc:
        raise RuntimeError(json.dumps(doc["error"])[:300])
    return raw, doc["result"]


def fetch():
    raw_acc, acc = rpc({"request_type": "view_account", "finality": "final", "account_id": ACCOUNT})
    h = acc["block_height"]
    raw_keys, keys = rpc({"request_type": "view_access_key_list", "block_id": h, "account_id": ACCOUNT})
    (REPO / RAW).mkdir(parents=True, exist_ok=True)
    (REPO / RAW / f"{h}_account.json").write_bytes(raw_acc)
    (REPO / RAW / f"{h}_keys.json").write_bytes(raw_keys)
    return h


def compute():
    files = sorted((REPO / RAW).glob("*_account.json"))
    if not files:
        return None, ["no saved testnet response: run --fetch"]
    acc_path = files[-1]
    h = int(acc_path.name.split("_")[0])
    keys_path = REPO / RAW / f"{h}_keys.json"
    raw_acc, raw_keys = acc_path.read_bytes(), keys_path.read_bytes()
    acc, keys = json.loads(raw_acc)["result"], json.loads(raw_keys)["result"]
    problems = []
    if acc["block_height"] != h or keys["block_height"] != h:
        problems.append("account and keys not read at the same block")
    sealed = daily.lock_sealed(acc, keys["keys"], account=ACCOUNT)
    return {"measure": __doc__.splitlines()[0], "network": "testnet", "rpc": RPC, "account": ACCOUNT, "delete_key_tx": DELETE_KEY_TX,
            "block_height": h, "block_hash": acc["block_hash"], "code_hash": acc["code_hash"],
            "global_contract": acc.get("global_contract_account_id") or acc.get("global_contract_hash"),
            "access_keys": len(keys["keys"]), "amount_yocto": acc["amount"], "sealed": sealed,
            "files": {str(RAW / acc_path.name).replace("\\", "/"): lw.sha256(raw_acc),
                      str(RAW / keys_path.name).replace("\\", "/"): lw.sha256(raw_keys)}}, problems


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    if a.fetch:
        print(f"read {ACCOUNT} at block {fetch()}")
    res, problems = compute()
    if problems or res is None:
        print("\n".join(problems))
        sys.exit(1)
    text = json.dumps(res, indent=1) + "\n"
    if a.verify:
        ok = (REPO / OUT).exists() and (REPO / OUT).read_text(encoding="utf-8") == text
        print("testnet_lock: OK" if ok else "testnet_lock: DIFFERS")
        sys.exit(0 if ok else 1)
    (REPO / OUT).write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {OUT}: {ACCOUNT} at block {res['block_height']}: {res['access_keys']} keys, "
          f"code {res['code_hash']}, sealed = {res['sealed']}")


if __name__ == "__main__":
    main()
