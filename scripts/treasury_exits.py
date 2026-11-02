"""Where, exactly, did treasury.near's balance fall in the months where treasury_spend.py found
net outflows: the block, the amount and the cause (transaction or receipt hash) of each step.

Between two blocks, balance(h) - balance(start) - (protocol rewards paid at epoch starts <= h)
changes only when something else moves: an outflow lowers it. For a month with net outflows the
script bisects that quantity over the block heights, down to single steps (about 25 balance
reads per step), then asks the node for the cause of the change in that block
(EXPERIMENTAL_changes, account_changes).

--recipients then reads, for every step of at least 1 NEAR caused by a transaction, that
transaction's receipts (EXPERIMENTAL_tx_status) and records each transfer treasury.near sent:
receiver, deposit and whether it succeeded. Multisig and DAO contracts (*.multisignature.near,
*.sputnik-dao.near) are named; every other receiver is shown as a sha256 tag (see privacy.py).
The full answers stay in data/private/ (not in git); their redacted copies are public.

The steps found must add up to the month's other_net in data/treasury_spend.json to the yocto;
otherwise the run says so (a step hidden by an equal inflow in the same bisection interval
would show up as a difference).

Read-only: JSON-RPC "view_account", "block", "EXPERIMENTAL_changes", "EXPERIMENTAL_tx_status".
No keys.

Usage:
    python scripts/treasury_exits.py            needs data/treasury_spend.json (about 200 calls)
    python scripts/treasury_exits.py --recipients   adds the receivers (one call per large step)
    python scripts/treasury_exits.py --verify   offline, from the saved files
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
import treasury_spend as ts  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
OUT_NAME = "treasury_exits.json"
MIN_RECIPIENT_YOCTO = 10 ** 24  # steps of at least 1 NEAR get their receivers
# Receivers shown by name: multisig and DAO contracts. Everyone else gets a sha256 tag.
INSTITUTIONAL = re.compile(r"^[a-z0-9_-]+(?:\.[a-z0-9_-]+)*\.(?:multisignature|sputnik-dao)\.near$")


def tx_rel(tx_hash):
    return f"data/private/treasury_exits/tx/{tx_hash}.json"


def project_tx(key, raw):
    """Redacted copy of one EXPERIMENTAL_tx_status answer: the transfers treasury.near sent."""
    res = json.loads(raw)["result"]
    status = {o["id"]: o["outcome"]["status"] for o in res["receipts_outcome"]}
    transfers = []
    for r in res.get("receipts", []):
        action = r["receipt"].get("Action")
        if not action or r["predecessor_id"] != ts.ACCOUNT or r["receiver_id"] == ts.ACCOUNT:
            continue
        dep = 0
        for a in action["actions"]:
            if isinstance(a, dict):
                for kind in ("Transfer", "FunctionCall"):
                    if kind in a:
                        dep += int(a[kind].get("deposit", "0"))
        if dep:
            st = status.get(r["receipt_id"], {})
            transfers.append({"receipt_id": r["receipt_id"], "receiver_id": r["receiver_id"],
                              "deposit_yocto": str(dep),
                              "ok": "SuccessValue" in st or "SuccessReceiptId" in st})
    out = {"tx_hash": res["transaction"]["hash"], "signer_id": res["transaction"]["signer_id"],
           "transfers": transfers}
    public = {ts.ACCOUNT} | {t["receiver_id"] for t in transfers
                             if INSTITUTIONAL.match(t["receiver_id"])}
    return privacy.dumps(privacy.redact(out, public))


def recipients_of(doc, base):
    """From the redacted copies: (receivers per exit height, summary by receiver, problems)."""
    per, summary, problems = {}, {}, []
    for e in doc["exits"]:
        f = doc.get("tx_files", {}).get(e["cause"].get("tx_hash", ""))
        if not f:
            continue
        red = json.loads(privacy.read(base, f))
        rows = [{"account": t["receiver_id"], "amount_near": daily.near(int(t["deposit_yocto"])),
                 "ok": t["ok"]} for t in red["transfers"]]
        sent = sum(int(t["deposit_yocto"]) for t in red["transfers"])
        rest = int(e["amount_yocto"]) - sent
        if not 0 <= rest < MIN_RECIPIENT_YOCTO:
            problems.append(f"block {e['height']}: transfers {daily.near(sent)} do not explain "
                            f"the fall of {e['amount_near']} NEAR")
        per[e["height"]] = rows
        for t in red["transfers"]:
            if t["ok"]:
                s = summary.setdefault(t["receiver_id"], [0, 0])
                s[0] += int(t["deposit_yocto"])
                s[1] += 1
    out = [{"account": a, "amount_near": daily.near(v[0]), "transfers": v[1]}
           for a, v in sorted(summary.items(), key=lambda x: -x[1][0])]
    return per, out, problems


def add_recipients(chain, data_root):
    base = data_root.parent
    doc = json.loads((data_root / OUT_NAME).read_text(encoding="utf-8"))
    files = doc.setdefault("tx_files", {})
    for e in doc["exits"]:
        h = e["cause"].get("tx_hash")
        if not h or int(e["amount_yocto"]) < MIN_RECIPIENT_YOCTO:
            continue
        rel = tx_rel(h)
        path = base / rel
        if not path.exists():
            raw = chain._post({"jsonrpc": "2.0", "id": "exits", "method": "EXPERIMENTAL_tx_status",
                               "params": {"tx_hash": h, "sender_account_id": ts.ACCOUNT,
                                          "wait_until": "NONE"}})
            if "result" not in json.loads(raw):
                raise RuntimeError(f"tx {h}: {raw[:200]!r}")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        files[h] = {"path": rel, "sha256": sha256(path.read_bytes()), "private": True}
    privacy.write_redacted(base, files, project_tx)
    per, _, problems = recipients_of(doc, base)
    for e in doc["exits"]:
        if e["height"] in per:
            e["recipients"] = per[e["height"]]
    res, p = verify_exits(doc, data_root)
    doc["results"] = res
    (data_root / OUT_NAME).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8",
                                      newline="\n")
    return doc, problems + p


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def changes_rel(data_root, height):
    p = data_root / "raw" / "treasury_spend" / "changes" / f"{height}_{ts.ACCOUNT}.json"
    return p, p.relative_to(data_root.parent).as_posix()


def month_inputs(doc, data_root, rd):
    """For each month: (month entry, row, start heights with their treasury rewards)."""
    out, problems = [], []
    res, p = ts.compute(doc, data_root)
    problems += p
    for m, row in zip(doc["months"], res["months"]):
        got = ts.check_month(m, data_root, rd, [])
        out.append((m, row, got[4]))
    return out, problems


def find_steps(lo, hi, adj, existing_at, balance_adj):
    """Heights in (lo, hi] where adj changes, as (height, previous existing height, change).
    adj: {height: value} already known for lo and hi."""
    if adj[lo] == adj[hi]:
        return []
    mid = existing_at((lo + hi) // 2) if hi - lo > 1 else hi
    if mid >= hi:  # the upper half is all skipped heights: try the lower half
        mid = existing_at(lo + 1) if hi - lo > 1 else hi
    if mid >= hi:  # no block between lo and hi: one step
        return [(hi, lo, adj[hi] - adj[lo])]
    if mid not in adj:
        adj[mid] = balance_adj(mid)
    return find_steps(lo, mid, adj, existing_at, balance_adj) + \
        find_steps(mid, hi, adj, existing_at, balance_adj)


def verify_exits(doc, data_root):
    """Offline: every step recomputes from the saved balances; steps add up to other_net."""
    base = data_root.parent
    problems, rd = [], {}
    ts_doc = json.loads((data_root / ts.OUT_NAME).read_text(encoding="utf-8"))
    for rel, digest in {**ts_doc["raw_files"], **doc["raw_files"]}.items():
        p = base / rel
        if not p.exists():
            problems.append(f"missing {rel}")
        elif sha256(p.read_bytes()) != digest:
            problems.append(f"sha256 differs for {rel}")
        else:
            rd[rel] = p.read_bytes()
    if problems:
        return None, problems
    months, p = month_inputs(ts_doc, data_root, rd)
    problems += p
    results = {"months": [], "total_exits_near": None}
    total = 0
    for m, row, starts in months:
        key = m["start"]["date"]
        mine = [e for e in doc["exits"] if e["month"] == key]
        if row["other_net_near"] == "0.000" and not mine:
            continue
        reward_at = dict(starts)
        got = 0
        for e in mine:
            h, q = e["height"], e["previous"]
            ah, aq = (ts.amount_of(rd[ts.acct_rel(data_root, x)[1]], x)[0] for x in (h, q))
            amount = aq + reward_at.get(h, 0) - ah
            if str(amount) != e["amount_yocto"]:
                problems.append(f"{key}: block {h}: amount {amount} differs from {e['amount_yocto']}")
            if not m["start"]["height"] < h <= m["end"]["height"]:
                problems.append(f"{key}: block {h} is outside the month")
            c = json.loads(rd[changes_rel(data_root, h)[1]])
            hit = [x for x in c["result"]["changes"] if x["cause"] == e["cause"]]
            if not hit:
                problems.append(f"{key}: block {h}: cause not in the saved response")
            got += amount
        a0 = ts.amount_of(rd[ts.acct_rel(data_root, m["start"]["height"])[1]], m["start"]["height"])[0]
        a1 = ts.amount_of(rd[ts.acct_rel(data_root, m["end"]["height"])[1]], m["end"]["height"])[0]
        tin = sum(x for _, x in starts)
        other = a1 - a0 - tin
        if -got != other:
            problems.append(f"{key}: steps add up to {daily.near(-got)}, other_net is "
                            f"{daily.near(other)}")
        total += got
        results["months"].append({"month": key, "steps": len(mine), "exits_near": daily.near(got),
                                  "other_net_near": row["other_net_near"]})
    results["total_exits_near"] = daily.near(total)
    if doc.get("tx_files"):
        p, absent = privacy.check_files(base, doc["tx_files"], project_tx)
        problems += p
        if not p:
            per, summary, p = recipients_of(doc, base)
            problems += p
            for e in doc["exits"]:
                if per.get(e["height"]) != e.get("recipients"):
                    problems.append(f"block {e['height']}: receivers differ from the saved copies")
            results["recipients"] = summary
    return results, problems


def run(chain, data_root):
    ts_doc = json.loads((data_root / ts.OUT_NAME).read_text(encoding="utf-8"))
    ts.preload(chain, data_root)
    base = data_root.parent
    rd = {rel: (base / rel).read_bytes() for rel in ts_doc["raw_files"]}
    months, problems = month_inputs(ts_doc, data_root, rd)
    files, exits = {}, []
    for m, row, starts in months:
        if row["other_net_near"] == "0.000":
            continue
        a, b = m["start"]["height"], m["end"]["height"]
        sched = sorted(starts)

        def reward_upto(h, sched=sched):
            return sum(x for s, x in sched if s <= h)

        base_amount = ts.amount_of(rd[ts.acct_rel(data_root, a)[1]], a)[0]

        def balance_adj(h, a=a, sched=sched, base_amount=base_amount):
            raw = ts.fetch_account(chain, data_root, h, files)
            return ts.amount_of(raw, h)[0] - base_amount - sum(x for s, x in sched if s <= h)

        adj = {a: 0, b: balance_adj(b)}
        before = chain.calls
        steps = find_steps(a, b, adj, lambda h: burn.existing_at(chain, h)[0], balance_adj)
        for h, q, change in steps:
            ts.fetch_account(chain, data_root, q, files)
            ts.fetch_account(chain, data_root, h, files)
            path, rel = changes_rel(data_root, h)
            if not path.exists():
                raw = chain._post({"jsonrpc": "2.0", "id": "exits", "method": "EXPERIMENTAL_changes",
                                   "params": {"changes_type": "account_changes",
                                              "account_ids": [ts.ACCOUNT], "block_id": h}})
                if "error" in json.loads(raw):
                    raise RuntimeError(f"changes at {h}: {raw[:200]!r}")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
            raw = path.read_bytes()
            files[rel] = sha256(raw)
            changes = json.loads(raw)["result"]["changes"]
            cause = changes[0]["cause"] if changes else {}
            reward = dict(starts).get(h, 0)
            qa = ts.amount_of(ts.fetch_account(chain, data_root, q, files), q)[0]
            ha = ts.amount_of(ts.fetch_account(chain, data_root, h, files), h)[0]
            hdr = chain.block(h)
            exits.append({"month": m["start"]["date"], "height": h, "previous": q,
                          "utc": lw.iso(hdr["timestamp"])[:19] + "Z",
                          "amount_yocto": str(qa + reward - ha), "amount_near":
                          daily.near(qa + reward - ha), "cause": cause})
        print(f"{m['start']['date']}: {len(steps)} steps ({chain.calls - before} calls)", flush=True)
    doc = {"measure": "blocks, amounts and causes of treasury.near's balance falls",
           "source_file": "data/" + ts.OUT_NAME, "exits": exits,
           "raw_files": dict(sorted(files.items())), "results": {}}
    res, p = verify_exits(doc, data_root)
    problems += p
    doc["results"] = res
    (data_root / OUT_NAME).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8",
                                      newline="\n")
    return doc, problems


def show(doc):
    for e in doc["exits"]:
        c = e["cause"]
        h = c.get("tx_hash") or c.get("receipt_hash") or ""
        print(f"  {e['utc']}  block {e['height']:>11,}  {e['amount_near']:>12} NEAR  "
              f"{c.get('type', '')} {h}")
        for r in e.get("recipients", []):
            print(f"      -> {r['account']} {r['amount_near']} NEAR{'' if r['ok'] else ' (failed)'}")
    print(f"total {doc['results']['total_exits_near']} NEAR")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-dir", type=Path, default=REPO / "data")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--recipients", action="store_true")
    args = parser.parse_args()
    data_root = args.data_dir.resolve()
    if args.verify:
        doc = json.loads((data_root / OUT_NAME).read_text(encoding="utf-8"))
        res, problems = verify_exits(doc, data_root)
        if not problems and res != doc["results"]:
            problems.append("results do not recompute from the saved files")
        if problems:
            print("FAILED:\n  " + "\n  ".join(problems))
            return 1
        print(f"OK: {len(doc['exits'])} steps recompute from the saved balances and add up to "
              f"the monthly net outflows")
        if doc.get("tx_files"):
            _, absent = privacy.check_files(data_root.parent, doc["tx_files"], project_tx)
            print(privacy.status_line(f"receivers of {len(doc['tx_files'])} transactions", absent))
        return 0
    if args.recipients:
        chain = lw.Chain()
        doc, problems = add_recipients(chain, data_root)
        show(doc)
        for r in doc["results"].get("recipients", []):
            print(f"  -> {r['account']}: {r['amount_near']} NEAR in {r['transfers']} transfer(s)")
        print(f"{chain.calls} RPC calls")
        if problems:
            print("FAILED:\n  " + "\n  ".join(problems[:10]))
            return 1
        print("Offline check: OK")
        return 0
    chain = lw.Chain()
    doc, problems = run(chain, data_root)
    show(doc)
    print(f"{chain.calls} RPC calls")
    if problems:
        print("FAILED:\n  " + "\n  ".join(problems[:10]))
        return 1
    print("Offline check: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
