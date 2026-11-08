"""Where the 30,171,200 NEAR that left treasury.near in April and May 2026 went next.

treasury_exits.py found the transfers out of treasury.near and their receivers. This script follows
the NEAR one step at a time from those receivers, on the chain: for each account on the path it
bisects the account's balance (view_account amount) between two blocks down to single blocks where
it changed by at least 1,000 NEAR, asks the node for the cause of each change (EXPERIMENTAL_changes,
account_changes), and reads the cause: for a transaction, the transfers the account sent
(EXPERIMENTAL_tx_status); for a receipt, who sent it (EXPERIMENTAL_receipt). It also reads every
account's balance on 1 August, 2 October and 1 November 2026.

Each step must be explained by its cause to within 1 NEAR (gas). Two hops start a few blocks after
the NEAR arrived, so an arrival and a departure in the same interval cannot hide each other; the
script checks that the balance at that start holds what arrived.

It stops where an account has many flows and the NEAR mix with others: tracing further would
attribute to treasury.near what is not its. Nothing here says who holds an account or why it moved:
only blocks, amounts and transactions.

Privacy: the accounts followed are listed in data/private/treasury_trace/hops.json (not in git).
Multisig and DAO contracts are named; every other account is a sha256 tag (privacy.py). Balance
answers carry no account name and are public; changes, transactions and receipts are private, with
redacted copies in data/raw/redacted/treasury_trace/ that the computation reads.

Read-only: JSON-RPC "view_account", "block", "EXPERIMENTAL_changes", "EXPERIMENTAL_tx_status",
"EXPERIMENTAL_receipt". No keys.

Usage:
    python scripts/treasury_trace.py            fetch (needs data/private/treasury_trace/hops.json)
    python scripts/treasury_trace.py --verify   offline, from the saved and redacted files
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import burn  # noqa: E402
import daily  # noqa: E402
import lock_window as lw  # noqa: E402
import privacy  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
OUT_NAME = "treasury_trace.json"
HOPS = "data/private/treasury_trace/hops.json"
MIN_STEP = 1_000 * 10 ** 24          # changes of at least 1,000 NEAR are followed
GAS_TOLERANCE = 10 ** 24            # a step and its cause may differ by gas, under 1 NEAR
INSTITUTIONAL = re.compile(r"^[a-z0-9_-]+(?:\.[a-z0-9_-]+)*\.(?:multisignature|sputnik-dao)\.near$")
PUBLIC = {"treasury.near", "system"}


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def show(acct):
    """How an account appears in public files."""
    if acct in PUBLIC or INSTITUTIONAL.match(acct) or acct.endswith(".poolv1.near"):
        return acct
    return privacy.tag(acct)


def public_names(obj):
    names = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            names |= public_names(k) | public_names(v)
    elif isinstance(obj, list):
        for v in obj:
            names |= public_names(v)
    elif isinstance(obj, str) and show(obj) == obj:
        names.add(obj)
    return names


def project(key, raw):
    """Redacted copy: only the fields the computation reads, accounts shown as show() does."""
    res = json.loads(raw)["result"]
    kind = key.split(":")[0]
    if kind == "changes":
        out = {"block_hash": res["block_hash"], "causes": [c["cause"] for c in res["changes"]]}
    elif kind == "tx":
        status = {o["id"]: list(o["outcome"]["status"])[0] for o in res["receipts_outcome"]}
        sender = res["transaction"]["signer_id"]
        sent = []
        for r in res.get("receipts", []):
            act = r["receipt"].get("Action")
            if not act or r["predecessor_id"] != sender or r["receiver_id"] == sender:
                continue
            dep = sum(int((a.get("Transfer") or a.get("FunctionCall") or {}).get("deposit", "0"))
                      for a in act["actions"] if isinstance(a, dict))
            sent.append({"to": r["receiver_id"], "deposit_yocto": str(dep),
                         "ok": status.get(r["receipt_id"]) in ("SuccessValue", "SuccessReceiptId")})
        out = {"tx_hash": res["transaction"]["hash"], "signer": sender, "sent": sent}
    else:  # receipt
        act = res["receipt"].get("Action") or {}
        dep = sum(int((a.get("Transfer") or a.get("FunctionCall") or {}).get("deposit", "0"))
                  for a in act.get("actions", []) if isinstance(a, dict))
        out = {"receipt_id": res["receipt_id"], "from": res["predecessor_id"], "to": res["receiver_id"],
               "deposit_yocto": str(dep)}
    return privacy.dumps(privacy.redact(out, public_names(out)))


# ---------------------------------------------------------------- fetch
class Fetch:
    def __init__(self, chain, base):
        self.chain, self.base = chain, base
        self.raw_files, self.private = {}, {}

    def balance(self, acct, h):
        """(existing height >= h, amount) of acct; the answer saved under its tag."""
        h, _ = burn.existing_at(self.chain, h)
        rel = f"data/raw/treasury_trace/accounts/{h}_{show(acct).replace(':', '_')}.json"
        p = self.base / rel
        if not p.exists():
            raw = daily.rpc_call(self.chain, {"request_type": "view_account", "block_id": h, "account_id": acct})
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(raw)
        raw = p.read_bytes()
        self.raw_files[rel] = sha256(raw)
        return h, int(json.loads(raw)["result"]["amount"])

    def private_call(self, key, rel, method, params):
        p = self.base / rel
        if not p.exists():
            raw = self.chain._post({"jsonrpc": "2.0", "id": "trace", "method": method, "params": params})
            if "result" not in json.loads(raw):
                raise RuntimeError(f"{method}: {raw[:200]!r}")
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(raw)
        self.private[key] = {"path": rel, "sha256": sha256(p.read_bytes()), "private": True}
        return json.loads(p.read_bytes())["result"]

    def steps(self, acct, lo, hi, alo, ahi, out):
        if abs(ahi - alo) < MIN_STEP:
            return
        if hi - lo <= 1:
            out.append((hi, lo))
            return
        mid, am = self.balance(acct, (lo + hi) // 2)
        if mid >= hi:
            out.append((hi, lo))
            return
        self.steps(acct, lo, mid, alo, am, out)
        self.steps(acct, mid, hi, am, ahi, out)


def fetch(chain, base):
    spec = json.loads((base / HOPS).read_text(encoding="utf-8"))
    f = Fetch(chain, base)
    hops = []
    for hop in spec["hops"]:
        a = hop["account"]
        lo, alo = f.balance(a, hop["lo"])
        hi, ahi = f.balance(a, hop["hi"])
        found = []
        f.steps(a, lo, hi, alo, ahi, found)
        steps = []
        for h, q in found:
            t = show(a).replace(":", "_")
            ch = f.private_call(f"changes:{h}:{t}", f"data/private/treasury_trace/changes/{h}_{t}.json",
                                "EXPERIMENTAL_changes", {"changes_type": "account_changes",
                                                         "account_ids": [a], "block_id": h})
            causes = [c["cause"] for c in ch["changes"]]
            keys = [f"changes:{h}:{t}"]
            tx = next((c["tx_hash"] for c in causes if c.get("tx_hash")), None)
            if tx:
                f.private_call(f"tx:{tx}", f"data/private/treasury_trace/tx/{tx}.json", "EXPERIMENTAL_tx_status",
                               {"tx_hash": tx, "sender_account_id": a, "wait_until": "NONE"})
                keys.append(f"tx:{tx}")
            else:
                for c in causes:
                    if c.get("type") == "receipt_processing":
                        r = c["receipt_hash"]
                        f.private_call(f"receipt:{r}", f"data/private/treasury_trace/receipts/{r}.json",
                                       "EXPERIMENTAL_receipt", {"receipt_id": r})
                        keys.append(f"receipt:{r}")
            steps.append({"height": h, "previous": q, "causes": keys})
        hops.append({"path": hop["path"], "account": show(a), "lo": lo, "hi": hi, "steps": steps})
    balances = {}
    for a in [h["account"] for h in spec["hops"]] + spec["balances_only"]:
        balances[show(a)] = {d: f.balance(a, h)[0] for d, h in spec["dates"].items()}
    privacy.write_redacted(base, f.private, project)
    doc = {"measure": "where the NEAR that left treasury.near in April and May 2026 went next",
           "rules": __doc__.split("Privacy:")[0].strip(), "min_step_near": "1000",
           "hops": hops, "balances_at": balances,
           "raw_files": dict(sorted(f.raw_files.items())), "private_files": dict(sorted(f.private.items()))}
    return doc


# ---------------------------------------------------------------- compute (offline)
def compute(doc, base):
    problems = []
    for rel, d in doc["raw_files"].items():
        p = base / rel
        if not p.exists() or sha256(p.read_bytes()) != d:
            problems.append(f"missing or changed: {rel}")
    p, absent = privacy.check_files(base, doc["private_files"], project)
    problems += p
    if problems:
        return None, problems, absent

    def amount(acct, h):
        rel = f"data/raw/treasury_trace/accounts/{h}_{acct.replace(':', '_')}.json"
        res = json.loads((base / rel).read_bytes())["result"]
        if res["block_height"] != h:
            problems.append(f"{rel}: read at {res['block_height']}")
        return int(res["amount"])

    def red(key):
        return json.loads(privacy.read(base, doc["private_files"][key]))

    rows = []
    for hop in doc["hops"]:
        a = hop["account"]
        total = amount(a, hop["hi"]) - amount(a, hop["lo"])
        followed = 0
        for s in hop["steps"]:
            change = amount(a, s["height"]) - amount(a, s["previous"])
            followed += change
            row = {"path": hop["path"], "account": a, "height": s["height"], "change_near": daily.near(change)}
            for key in s["causes"][1:]:
                r = red(key)
                if key.startswith("tx:"):
                    ok = [x for x in r["sent"] if x["ok"]]
                    sent = sum(int(x["deposit_yocto"]) for x in ok)
                    if abs(-change - sent) >= GAS_TOLERANCE:
                        problems.append(f"{a} block {s['height']}: change {daily.near(change)} not explained "
                                        f"by transfers of {daily.near(sent)}")
                    row.update(tx=r["tx_hash"], to=[{"account": x["to"], "near": daily.near(int(x["deposit_yocto"]))}
                                                    for x in ok])
                else:
                    row.setdefault("from", []).append({"account": r["from"],
                                                       "near": daily.near(int(r["deposit_yocto"]))})
            if "from" in row:
                got = sum(int(red(k)["deposit_yocto"]) for k in s["causes"][1:] if k.startswith("receipt:"))
                if abs(change - got) >= GAS_TOLERANCE:
                    problems.append(f"{a} block {s['height']}: change {daily.near(change)} not explained "
                                    f"by receipts of {daily.near(got)}")
            if len(s["causes"]) == 1:
                problems.append(f"{a} block {s['height']}: no transaction or receipt found for the change")
            rows.append(row)
        rest = total - followed
        if abs(rest) >= MIN_STEP:
            problems.append(f"{a}: changes under 1,000 NEAR add up to {daily.near(rest)}")
        hop_row = {"path": hop["path"], "account": a, "lo": hop["lo"], "hi": hop["hi"],
                   "balance_lo_near": daily.near(amount(a, hop["lo"])), "balance_hi_near": daily.near(amount(a, hop["hi"])),
                   "not_followed_near": daily.near(rest)}
        rows.append(hop_row)
    # A hop that starts after the NEAR arrived must hold them at its start (no arrival hidden by a departure)
    for hop in doc["hops"]:
        sent_here = [(r["height"], x["near"]) for r in rows if "to" in r for x in r["to"]
                     if x["account"] == hop["account"]]
        for h, near in sent_here:
            if h <= hop["lo"] and amount(hop["account"], hop["lo"]) + GAS_TOLERANCE < int(round(float(near) * 10 ** 6)) * 10 ** 18:
                problems.append(f"{hop['account']}: at its start {hop['lo']} it holds less than the "
                                f"{near} NEAR sent to it at {h}")
    bal = {a: {d: daily.near(amount(a, h)) for d, h in v.items()} for a, v in doc["balances_at"].items()}
    return {"steps_and_hops": rows, "balances": bal}, problems, absent


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    base = REPO
    path = base / "data" / OUT_NAME
    if a.verify:
        doc = json.loads(path.read_text(encoding="utf-8"))
        res, problems, absent = compute(doc, base)
        if not problems and res != doc.get("results"):
            problems.append(f"{OUT_NAME}: results differ from the recomputation")
    else:
        if not (base / HOPS).exists():
            raise SystemExit(f"{HOPS} is missing: it lists the accounts to follow (private)")
        doc = fetch(lw.Chain(), base)
        res, problems, absent = compute(doc, base)
        doc["results"] = res
        path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    if res:
        for r in res["steps_and_hops"]:
            if "change_near" in r:
                where = r.get("to") or r.get("from")
                print(f"path {r['path']}  {r['account'][:24]:24}  block {r['height']}  {r['change_near']:>16}  "
                      f"{json.dumps(where)[:120]}")
        for acct, v in res["balances"].items():
            print(f"  {acct[:24]:24}  " + "  ".join(f"{d} {x}" for d, x in v.items()))
    if problems:
        print("FAILED:\n  " + "\n  ".join(problems[:20]))
        sys.exit(1)
    print(privacy.status_line("treasury_trace.json", absent) if a.verify else f"OK: saved data/{OUT_NAME}")


if __name__ == "__main__":
    main()
