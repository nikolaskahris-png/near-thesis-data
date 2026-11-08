"""Who carried the HSP-029 vote: the veNEAR of every voter, from the voting contract's own events.

Every successful vote on vote.dao logs one event per change (voting-contract/src/votes.rs,
common/src/events.rs):
    EVENT_JSON:{"standard":"venear","event":"add_vote","data":[{"account_id",
                "proposal_id","vote","account_balance"}]}
and, when an account changes its vote, a "remove_vote" event first. A failed receipt's
state is rolled back, so its logs are ignored.

Method:
  1. NearBlocks receipts to vote.dao with method `vote` (direct votes and the contract's own
     chained call from take_snapshot_and_vote), newest first, back to the proposal's
     creation time. Receipts with method take_snapshot_and_vote give the signer of
     chained votes.
  2. Archival RPC `tx` for every transaction: the logs of each successful receipt
     executed by vote.dao.
  3. Replay add/remove events for proposal 29 in block order -> each account's final
     option and veNEAR.
  4. Check: per option, the sum of the voters' veNEAR and their count equal the contract's
     own totals (get_proposal) at the same block, to the yoctoNEAR. Otherwise nothing is
     published.

Privacy: account IDs can name private people. The NearBlocks pages and tx responses go
to data/private/hos/ (not committed); the public file lists voters by sha256 tag, option
and veNEAR, with the sha256 of every private file.

Usage:
    python scripts/hsp029_voters.py --trial DIR   now, at the latest final block (trial; vote open)
    python scripts/hsp029_voters.py               after hsp029.py: at its closing block
    python scripts/hsp029_voters.py --verify      offline check of data/hsp029_voters.json
"""
import argparse
import hashlib
import json
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hsp029  # noqa: E402
import privacy  # noqa: E402
import lock_window as lw  # noqa: E402
import stakers  # noqa: E402

CONTRACT = hsp029.CONTRACT
PROPOSAL_ID = hsp029.PROPOSAL_ID
OUT_NAME = "hsp029_voters.json"
NEARBLOCKS = f"https://api.nearblocks.io/v3/accounts/{CONTRACT}/receipts"
PAGE_WAIT = stakers.PAGE_WAIT
TOP = (1, 3, 8, 10)


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def tag(acct):
    return "sha256:" + sha256(acct.encode())[:16]


# ---------------------------------------------------------------- fetching

class Store:
    """Raw responses, saved byte for byte; private ones under data/private/."""

    def __init__(self, root, private_dir, public_dir):
        self.root, self.private_dir, self.public_dir = root, private_dir, public_dir
        self.files = {}

    def put(self, name, raw, private, request):
        path = (self.private_dir if private else self.public_dir) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        self.files[name] = {"path": path.resolve().relative_to(self.root).as_posix(),
                            "sha256": sha256(raw), "private": private, "request": request}
        return raw

    def saved(self, name, private):
        path = (self.private_dir if private else self.public_dir) / name
        return path.read_bytes() if path.exists() else None


def receipt_pages(store, method, stop_ns, get, wait):
    """Every NearBlocks page of receipts with this method, back to stop_ns."""
    cursor, n, out = None, 1, []
    while True:
        name = f"nearblocks_{method}/page_{n:03d}.json"
        raw = store.saved(name, True)
        q = {"method": method, "limit": 100}
        if cursor:
            q["next"] = cursor
        url = NEARBLOCKS + "?" + urllib.parse.urlencode(q)
        if raw is None:
            if n > 1:
                time.sleep(wait)
            raw = get(url)
            print(f"  NearBlocks {method} page {n}", flush=True)
        store.put(name, raw, True, {"url": url})
        doc = json.loads(raw)
        rows = stakers.receipts_in(doc)
        if not rows and n == 1 and method == "vote":
            raise SystemExit(f"No receipts in {name}: the NearBlocks format may have changed.")
        out += rows
        cursor = stakers.next_cursor(doc)
        oldest = min((int(r["block"]["block_timestamp"]) for r in rows), default=0)
        if not cursor or not rows or oldest < stop_ns:
            return out
        n += 1


def tx_status(chain, store, tx_hash, sender):
    name = f"tx/{tx_hash}.json"
    raw = store.saved(name, True)
    body = {"jsonrpc": "2.0", "id": "voters", "method": "tx",
            "params": {"tx_hash": tx_hash, "sender_account_id": sender}}
    if raw is None:
        raw = chain._post(body)
    doc = json.loads(raw)
    if "error" in doc or "result" not in doc:
        raise RuntimeError(f"tx {tx_hash} ({sender}): {json.dumps(doc.get('error'))[:300]}")
    # the request names the signer: only the method goes to the public file
    store.put(name, raw, True, {"rpc": chain.url, "method": "tx"})
    return raw


def fetch(chain, store, height, created_ns, get=stakers.http_get, wait=PAGE_WAIT):
    """Pages + tx responses for every vote receipt between creation and `height`."""
    votes = receipt_pages(store, "vote", created_ns, get, wait)
    chained = receipt_pages(store, "take_snapshot_and_vote", created_ns, get, wait)
    signer = {}
    for r in votes + chained:
        if r["predecessor_account_id"] != CONTRACT:
            signer.setdefault(r["transaction_hash"], r["predecessor_account_id"])
    txs = sorted({r["transaction_hash"] for r in votes
                  if created_ns <= int(r["block"]["block_timestamp"])
                  and int(r["block"]["block_height"]) <= height})
    missing = [t for t in txs if t not in signer]
    if missing:
        raise SystemExit(f"No signer found for {len(missing)} transaction(s), e.g. {missing[0]}")
    for i, t in enumerate(txs, 1):
        tx_status(chain, store, t, signer[t])
        if i % 20 == 0:
            print(f"  tx {i}/{len(txs)}", flush=True)
    heights = {}
    for r in votes:
        heights[r["receipt_id"]] = int(r["block"]["block_height"])
    return txs, heights


# ---------------------------------------------------------------- pure part

def events_of(tx_doc, proposal_id=PROPOSAL_ID):
    """Vote events of successful vote.dao receipts in one tx response, in log order."""
    out = []
    for ro in tx_doc["result"].get("receipts_outcome", []):
        oc = ro["outcome"]
        if oc.get("executor_id") != CONTRACT or "Failure" in (oc.get("status") or {}):
            continue
        for line in oc.get("logs", []):
            if not line.startswith("EVENT_JSON:"):
                continue
            ev = json.loads(line[len("EVENT_JSON:"):])
            if ev.get("standard") != "venear" or ev.get("event") not in ("add_vote",
                                                                          "remove_vote"):
                continue
            for d in ev.get("data", []):
                if int(d["proposal_id"]) == proposal_id:
                    out.append({"receipt": ro["id"], "event": ev["event"],
                                "account": d["account_id"], "vote": int(d["vote"]),
                                "venear": int(d["account_balance"])})
    return out


def replay(events):
    """events in chain order -> {account: (option, yocto veNEAR)}, plus problems."""
    state, problems = {}, []
    for e in events:
        cur = state.get(e["account"])
        if e["event"] == "remove_vote":
            if cur != (e["vote"], e["venear"]):
                problems.append(f"remove_vote does not match the current vote of a voter "
                                f"({e['receipt']})")
            state.pop(e["account"], None)
        else:
            if cur is not None:
                problems.append(f"add_vote without remove_vote for a voter ({e['receipt']})")
            state[e["account"]] = (e["vote"], e["venear"])
    return state, problems


def ordered_events(tx_docs, heights):
    """All events, ordered by the block of their receipt, then log order."""
    evs = []
    for i, doc in enumerate(tx_docs):
        for j, e in enumerate(events_of(doc)):
            # receipts that NearBlocks did not list (none expected) sort last within the tx
            evs.append((heights.get(e["receipt"], 0), i, j, e))
    return [e for *_, e in sorted(evs, key=lambda x: (x[0], x[1], x[2]))]


def concentration(voters, proposal):
    """Stats from the public voter list [{tag, option, venear}] and the proposal state."""
    opts = proposal.get("votes") or []
    problems = []
    for i, o in enumerate(opts):
        got = sum(int(v["venear_yocto"]) for v in voters if v["option"] == i)
        cnt = sum(1 for v in voters if v["option"] == i)
        if got != int(o["total_venear"]) or cnt != int(o["total_votes"]):
            problems.append(f"option {i}: voters add up to {hsp029.near_str(got)} veNEAR / {cnt} "
                            f"votes, contract says {hsp029.near_str(int(o['total_venear']))} / "
                            f"{o['total_votes']}")
    if any(v["option"] >= len(opts) for v in voters):
        problems.append("a voter has an option the proposal does not have")
    total = int(proposal["total_votes"]["total_venear"])
    ranked = sorted((int(v["venear_yocto"]) for v in voters), reverse=True)
    for_ranked = sorted((int(v["venear_yocto"]) for v in voters if v["option"] == 0),
                        reverse=True)
    snap_total = int(proposal["snapshot_and_state"]["total_venear"])
    required = max(snap_total * int(proposal["quorum_threshold_bps"]) // 10_000,
                   hsp029.num(proposal.get("quorum_floor")))  # same rule as hsp029.compute
    cum, to_quorum = 0, None
    for k, x in enumerate(ranked, 1):
        cum += x
        if cum >= required:
            to_quorum = k
            break
    stats = {"voters": len(voters), "total_venear": hsp029.near_str(total),
             "largest_venear": hsp029.near_str(ranked[0]) if ranked else "0.000",
             "median_venear": hsp029.near_str(int(stakers.median(ranked))),
             "for_voters": len(for_ranked),
             "fewest_voters_reaching_quorum": to_quorum}
    for k in TOP:
        stats[f"top{k}_share_of_votes_cast"] = hsp029.ratio(sum(ranked[:k]), total)
    stats["top8_share_of_for"] = hsp029.ratio(sum(for_ranked[:8]), sum(for_ranked))
    return stats, problems


def public_list(state):
    rows = [{"tag": tag(a), "option": o, "venear": hsp029.near_str(v), "venear_yocto": str(v)}
            for a, (o, v) in state.items()]
    return sorted(rows, key=lambda r: (-int(r["venear_yocto"]), r["tag"]))


def build(root, doc):
    """Everything computed from the files listed in doc. Used by run() and --verify."""
    files = doc["raw_files"]
    proposal = hsp029.decode(privacy.read(root, files["proposal"]))   # redacted copy when private
    out = {}
    voters = doc["voters"]
    stats, problems = concentration(voters, proposal)
    out["stats"], out["sums_match_contract"] = stats, not problems
    out["problems"] = problems
    txs = [k for k in files if k.startswith("tx/")]
    present = [k for k in txs if (root / files[k]["path"]).exists()]
    if txs and len(present) == len(txs):
        tx_docs = [json.loads((root / files[k]["path"]).read_bytes()) for k in sorted(txs)]
        heights = {}
        for k in sorted(f for f in files if f.startswith("nearblocks_vote/")):
            for r in stakers.receipts_in(json.loads((root / files[k]["path"]).read_bytes())):
                heights[r["receipt_id"]] = int(r["block"]["block_height"])
        state, p = replay(ordered_events(tx_docs, heights))
        out["private_check"] = "recomputed" if public_list(state) == voters and not p \
            else "differs"
        out["problems"] = problems + p
    else:
        out["private_check"] = f"{len(txs) - len(present)} private file(s) absent"
    out["private_absent"] = len(txs) - len(present)
    return out


# ---------------------------------------------------------------- run / verify

def layout(root, trial):
    """(private dir, public dir, output file). Trial: everything inside the trial folder."""
    if trial:
        return root / "private", root / "raw", root / "hsp029_voters_trial.json"
    return (root / "data" / "private" / "hos", root / "data" / "raw" / "hos",
            root / "data" / OUT_NAME)


def run(chain, root, height, proposal_raw, trial, get=stakers.http_get, wait=PAGE_WAIT):
    """root = repo root (final) or the trial folder (trial)."""
    private_dir, public_dir, out_path = layout(root, trial)
    store = Store(root, private_dir, public_dir)
    pname = f"get_proposal_{PROPOSAL_ID}_at_{height}.json"
    store.put(pname, proposal_raw, not trial, {"method": "get_proposal", "block_id": height})
    proposal = hsp029.decode(proposal_raw)
    created = int(proposal["creation_time_ns"])
    txs, heights = fetch(chain, store, height, created, get=get, wait=wait)
    tx_docs = [json.loads(store.saved(f"tx/{t}.json", True)) for t in txs]
    state, problems = replay(ordered_events(tx_docs, heights))
    if problems:
        raise SystemExit("Events do not replay cleanly:\n  " + "\n  ".join(problems))
    files = {"proposal": store.files[pname]}
    if not trial:   # the proposal names accounts and carries its text: private, read from a redacted copy
        privacy.write_redacted(root, {"proposal": files["proposal"]}, hsp029.project)
    files.update({k: v for k, v in sorted(store.files.items()) if k != pname})
    doc = {
        "measure": "finding 8: veNEAR of every HSP-029 voter, from vote.dao events",
        "trial": trial,
        "block": height,
        "fetched_utc": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "method": __doc__.split("Method:")[1].split("Privacy:")[0].strip(),
        "privacy": "account IDs stay in data/private/ (not committed); public voters are "
                   "sha256 tags",
        "raw_files": files,
        "voters": public_list(state),
    }
    doc.update(build(root, doc))
    if not doc["sums_match_contract"]:
        bad = out_path.with_suffix(".failed.json")
        bad.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8", newline="\n")
        raise SystemExit("Voters do not add up to the contract's totals (nothing published; "
                         f"see {bad.name}):\n  " + "\n  ".join(doc["problems"]))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
                        newline="\n")
    return doc


def verify(path):
    path = Path(path)
    doc = json.loads(path.read_text(encoding="utf-8"))
    root = path.resolve().parent if doc.get("trial") else path.resolve().parent.parent
    problems = []
    for key, f in doc["raw_files"].items():
        p = root / f["path"]
        r = f.get("redacted")
        if r and (not (root / r["path"]).exists() or sha256((root / r["path"]).read_bytes()) != r["sha256"]):
            problems.append(f"redacted copy missing or changed: {r['path']}")
        if not p.exists():
            if not f["private"]:
                problems.append(f"missing public file {f['path']}")
        elif sha256(p.read_bytes()) != f["sha256"]:
            problems.append(f"sha256 mismatch: {f['path']}")
        elif r and hsp029.project(key, p.read_bytes()) != (root / r["path"]).read_bytes():
            problems.append(f"redacted copy does not match its original: {key}")
    if problems:
        return problems, doc
    again = build(root, doc)
    for key in ("stats", "sums_match_contract"):
        if again[key] != doc[key]:
            problems.append(f"'{key}' does not recompute")
    problems += again["problems"]
    if again["private_check"] == "differs":
        problems.append("private raw files do not give the same voter list")
    return problems, dict(doc, private_check=again["private_check"],
                          private_absent=again["private_absent"])


def verify_line(absent):
    """The --verify verdict. Same PUBLIC_REDACTED wording as the other scripts."""
    if absent:
        return (f"OK: the voters add up to the contract's totals and every statistic recomputes "
                f"offline from the public voter list (PUBLIC_REDACTED); {absent} private original(s) "
                f"not in git for privacy, so their match with the public list was not checked here")
    return ("OK: the voters add up to the contract's totals and every statistic recomputes "
            "offline, and the private originals give the same voter list")


def show(doc):
    s = doc["stats"]
    print(f"Block {doc['block']:,}{' (TRIAL)' if doc['trial'] else ''}: {s['voters']} voters, "
          f"{s['total_venear']} veNEAR cast, sums match the contract: {doc['sums_match_contract']}")
    print(f"  largest {s['largest_venear']} · top1 {s['top1_share_of_votes_cast']} · top3 "
          f"{s['top3_share_of_votes_cast']} · top8 {s['top8_share_of_votes_cast']} · top10 "
          f"{s['top10_share_of_votes_cast']} · top8 of For {s['top8_share_of_for']}")
    print(f"  fewest voters reaching quorum: {s['fewest_voters_reaching_quorum']} · median "
          f"{s['median_venear']} veNEAR")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--trial", metavar="DIR", type=Path,
                        help="measure now at the latest final block; files go to DIR")
    parser.add_argument("--verify", nargs="?", const=str(lw.REPO / "data" / OUT_NAME),
                        metavar="FILE")
    args = parser.parse_args()
    if args.verify:
        if not Path(args.verify).exists():
            print(f"SKIPPED: {Path(args.verify).name} does not exist yet; it is made after "
                  f"hsp029.py, once the vote has closed (2026-11-02 16:48:08 UTC)")
            return
        problems, doc = verify(args.verify)
        if problems:
            print("FAILED:\n  " + "\n  ".join(problems))
            sys.exit(1)
        print(verify_line(doc["private_absent"]))
        return
    chain = lw.Chain()
    if args.trial:
        final = chain.final_header()
        height = final["height"]
        raw = hsp029.view(chain, "get_proposal", {"proposal_id": PROPOSAL_ID}, height)
        root = args.trial.resolve()
        root.mkdir(parents=True, exist_ok=True)
    else:
        hpath = lw.REPO / "data" / hsp029.OUT_NAME
        if not hpath.exists():
            raise SystemExit("Run hsp029.py first (after the vote closes).")
        h = json.loads(hpath.read_text(encoding="utf-8"))
        height = h["closing_block"]["height"]
        raw = (lw.REPO / h["raw_files"]["proposal_at_close"]["path"]).read_bytes()
        root = lw.REPO
    doc = run(chain, root, height, raw, trial=bool(args.trial))
    show(doc)
    print(f"Saved {layout(root, bool(args.trial))[2]} ({chain.calls} RPC calls)")


if __name__ == "__main__":
    main()
