"""Final on-chain result of House of Stake proposal HSP-029 (vote.dao, proposal 29).

The result is computed with the voting contract's own rule
(github.com/houseofstake/house-of-stake-contracts, voting-contract/src/proposal.rs,
`compute_final_status`), not taken from a web page:

  quorum required = max(quorum_threshold_bps x snapshot total veNEAR / 10000, quorum_floor)
  quorum met      = veNEAR of all votes, every option counted >= quorum required
  approval met    = For x 10000 >= approval_threshold_bps x (For + Against)
                    (votes[0] = For, votes[1] = Against; any other option counts
                    toward quorum only)

Voting is closed at the first block whose header timestamp is at or after
voting_start_time_ns + voting_duration_ns (proposal.rs: `timestamp >= voting_end`).
The proposal is read at that block and at the block before it, so the file shows
that no vote was counted after the end. The contract's own `status` field is
recorded next to the computed result; in the classic flow a passed proposal sits
in a timelock first, and the stored status may only change when someone calls it.

Proof stored: raw archival responses (the two blocks, get_proposal at both,
get_config at the closing block, get_proposal at the latest final block), byte for
byte in data/raw/hos/, with sha256.

Read-only: JSON-RPC "block" and "call_function" calls. No API keys, nothing is
written on chain.

Usage:
    python scripts/hsp029.py --peek     one call now (current state); saves nothing
    python scripts/hsp029.py            after the vote has closed: lock, save, compute
    python scripts/hsp029.py --verify   offline check of data/hsp029.json

--verify needs no network: it recomputes everything from the raw responses.
"""
import argparse
import base64
import json
import sys
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lock_window as lw  # noqa: E402

CONTRACT = "vote.dao"
PROPOSAL_ID = 29
OUT_NAME = "hsp029.json"
YOCTO = 10 ** 24
NS = lw.NS
REPO = lw.REPO
FIXED_OPTIONS = ["For", "Against", "Abstain"]  # VoteOption index 0, 1, 2
REF_HEIGHT = 217453248  # fixed reference block, only for the first height guess
RULE_SOURCE = ("houseofstake/house-of-stake-contracts voting-contract/src/proposal.rs "
               "compute_final_status (commit 32611da, 2026-09-21)")
RULES = {
    "closing_block": "first block whose header timestamp is at or after "
                     "voting_start_time_ns + voting_duration_ns",
    "quorum_required": "max(quorum_threshold_bps x snapshot total_venear / 10000, quorum_floor)",
    "quorum_met": "total_votes.total_venear (all options) >= quorum_required",
    "approval_met": "For x 10000 >= approval_threshold_bps x (For + Against); "
                    "votes[0] = For, votes[1] = Against",
    "source": RULE_SOURCE,
}


# ---------- RPC ----------

def view(chain, method, args, height=None):
    """Raw response of a view call at a height (or at the latest final block)."""
    params = {"request_type": "call_function", "account_id": CONTRACT, "method_name": method,
              "args_base64": base64.b64encode(json.dumps(args).encode()).decode()}
    if height is None:
        params["finality"] = "final"
    else:
        params["block_id"] = height
    raw = chain._post({"jsonrpc": "2.0", "id": "hsp029", "method": "query", "params": params})
    doc = json.loads(raw)
    res = doc.get("result") or {}
    if "error" in doc or "result" not in res:
        err = doc.get("error") or res.get("error")
        raise RuntimeError(f"{method} at {height or 'final'}: {json.dumps(err)[:300]}")
    return raw


def decode(raw):
    return json.loads(bytes(json.loads(raw)["result"]["result"]).decode())


def at_height(raw):
    return json.loads(raw)["result"]["block_height"]


def header_of(raw):
    return json.loads(raw)["result"]["header"]


# ---------- the contract's rule ----------

def num(x):
    """U64 / NearToken / Bps come back as strings or plain numbers; None counts as 0."""
    return 0 if x is None else int(x)


def voting_end_ns(p):
    if p.get("voting_start_time_ns") is None:
        raise SystemExit("Proposal has no voting start time: voting has not started.")
    return num(p["voting_start_time_ns"]) + num(p["voting_duration_ns"])


def near_str(yocto, places=3):
    q = Fraction(yocto, YOCTO)
    scaled = round(q * 10 ** places)
    sign = "-" if scaled < 0 else ""
    scaled = abs(scaled)
    return f"{sign}{scaled // 10 ** places}.{scaled % 10 ** places:0{places}d}"


def ratio(part, total, places=6):
    """part/total as a decimal string, exact rounding (no floats)."""
    if total == 0:
        return None
    scaled = round(Fraction(part, total) * 10 ** places)
    return f"{scaled // 10 ** places}.{scaled % 10 ** places:0{places}d}"


def compute(p):
    """Result of a proposal by the contract's rule. Pure: no network."""
    snap = p.get("snapshot_and_state")
    if not snap:
        return {"computed_status": "Defeated", "reason": "no snapshot"}
    snapshot_venear = num(snap["total_venear"])
    q_bps = num(p["quorum_threshold_bps"])
    a_bps = num(p["approval_threshold_bps"])
    floor = num(p.get("quorum_floor"))
    # Bps x NearToken in the contract: yocto * bps / 10000, integer division.
    bps_quorum = snapshot_venear * q_bps // 10_000
    required = max(bps_quorum, floor)
    options = p.get("votes") or []
    venear = [num(v.get("total_venear")) for v in options]
    counts = [num(v.get("total_votes")) for v in options]
    total = num((p.get("total_votes") or {}).get("total_venear"))
    total_count = num((p.get("total_votes") or {}).get("total_votes"))
    for_v = venear[0] if venear else 0
    against_v = venear[1] if len(venear) > 1 else 0
    den = for_v + against_v
    quorum_met = total >= required
    approval_met = den > 0 and for_v * 10_000 >= a_bps * den
    # Current contract: fixed options (common/src/voting.rs VoteOption); old ones listed them.
    labels = p.get("voting_options") or FIXED_OPTIONS
    tree = (snap.get("snapshot") or {})
    return {
        "computed_status": "Succeeded" if quorum_met and approval_met else "Defeated",
        "quorum_met": quorum_met,
        "approval_met": approval_met,
        "snapshot_block": tree.get("block_height"),
        "snapshot_accounts": tree.get("length"),
        "snapshot_total_venear": near_str(snapshot_venear),
        "quorum_threshold_bps": q_bps,
        "quorum_floor_venear": near_str(floor),
        "quorum_required_venear": near_str(required),
        "approval_threshold_bps": a_bps,
        "options": [{"index": i,
                     "label": labels[i] if i < len(labels) else None,
                     "venear": near_str(venear[i]),
                     "votes": counts[i]} for i in range(len(options))],
        "total_venear": near_str(total),
        "total_votes": total_count,
        "options_sum_equals_total": sum(venear) == total and sum(counts) == total_count,
        "turnout_of_snapshot": ratio(total, snapshot_venear),
        "turnout_of_quorum": ratio(total, required),
        "approval_share_for_of_for_plus_against": ratio(for_v, den),
        "for_share_of_all_votes": ratio(for_v, total),
        "has_actions": bool(p.get("actions")),
    }


def describe(p, end):
    out = {"proposal_id": p.get("id", PROPOSAL_ID), "title": p.get("title"),
           "link": p.get("link"),
           "voting_start_utc": lw.iso(num(p["voting_start_time_ns"])),
           "voting_end_utc": lw.iso(end), "voting_end_ns": str(end)}
    if p.get("timelock_duration_ns") is not None:
        out["timelock_end_utc"] = lw.iso(end + num(p["timelock_duration_ns"]))
    return out


# ---------- run ----------

def run(chain, data_dir, proposal_id=PROPOSAL_ID):
    final = chain.final_header()
    raw_latest = view(chain, "get_proposal", {"proposal_id": proposal_id})
    latest = decode(raw_latest)
    if latest is None:
        raise SystemExit(f"Proposal {proposal_id} not found on {CONTRACT}.")
    end = voting_end_ns(latest)
    if final["timestamp"] < end + lw.SAFETY_SECONDS * NS:
        raise SystemExit(f"Too early: voting ends {lw.iso(end)[:19]}Z. Run again after "
                         f"{lw.iso(end + lw.SAFETY_SECONDS * NS)[:16]} UTC.")

    ref = chain.block(REF_HEIGHT)
    ns_per_block = (final["timestamp"] - ref["timestamp"]) / (final["height"] - ref["height"])
    guess = int(final["height"] - (final["timestamp"] - end) / ns_per_block)
    hdr, prev = lw.find_boundary(chain, end, guess)
    assert hdr["timestamp"] >= end > prev["timestamp"]
    assert hdr["prev_hash"] == prev["hash"]

    raw_close = view(chain, "get_proposal", {"proposal_id": proposal_id}, hdr["height"])
    raw_prev = view(chain, "get_proposal", {"proposal_id": proposal_id}, prev["height"])
    raw_cfg = view(chain, "get_config", {}, hdr["height"])

    raw_dir = data_dir / "raw" / "hos"
    raw_dir.mkdir(parents=True, exist_ok=True)
    fetched = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    files = {
        "closing_block": (f"block_{hdr['height']}.json", chain.raw[hdr["height"]]),
        "previous_block": (f"block_{prev['height']}.json", chain.raw[prev["height"]]),
        "proposal_at_close": (f"get_proposal_{proposal_id}_at_{hdr['height']}.json", raw_close),
        "proposal_before_close": (f"get_proposal_{proposal_id}_at_{prev['height']}.json", raw_prev),
        "config_at_close": (f"get_config_at_{hdr['height']}.json", raw_cfg),
        "proposal_latest": (f"get_proposal_{proposal_id}_final_{fetched}.json", raw_latest),
    }
    raw_files = {}
    for key, (name, raw) in files.items():
        path = raw_dir / name
        path.write_bytes(raw)
        raw_files[key] = {"path": path.relative_to(data_dir.parent).as_posix(),
                          "sha256": lw.sha256(raw)}
    doc = {
        "measure": "finding 8: final on-chain result of HSP-029",
        "contract": CONTRACT,
        "source": {"rpc": chain.url, "methods": ["block", "get_proposal", "get_config"]},
        "rules": RULES,
        "fetched_utc": fetched,
        "raw_files": raw_files,
    }
    doc.update(build(data_dir.parent, raw_files))
    return doc


def build(root, raw_files):
    """Everything computed from the raw files. Used by run() and by --verify."""
    def load(key):
        return (root / raw_files[key]["path"]).read_bytes()

    hdr = header_of(load("closing_block"))
    prev = header_of(load("previous_block"))
    p_close = decode(load("proposal_at_close"))
    p_prev = decode(load("proposal_before_close"))
    p_latest = decode(load("proposal_latest"))
    end = voting_end_ns(p_close)
    checks = {
        "closing_timestamp_at_or_after_end": hdr["timestamp"] >= end,
        "previous_timestamp_before_end": prev["timestamp"] < end,
        "closing_prev_hash_is_previous_block": hdr["prev_hash"] == prev["hash"],
        "proposal_read_at_closing_block": at_height(load("proposal_at_close")) == hdr["height"],
        "proposal_read_at_previous_block": at_height(load("proposal_before_close")) == prev["height"],
        "no_vote_counted_in_closing_block":
            p_close.get("votes") == p_prev.get("votes")
            and p_close.get("total_votes") == p_prev.get("total_votes"),
        "latest_votes_equal_close":
            p_latest.get("votes") == p_close.get("votes")
            and p_latest.get("total_votes") == p_close.get("total_votes"),
    }
    return {
        "proposal": describe(p_close, end),
        "closing_block": {"height": hdr["height"], "hash": hdr["hash"],
                          "timestamp_utc": lw.iso(hdr["timestamp"])},
        "previous_block": {"height": prev["height"], "hash": prev["hash"],
                           "timestamp_utc": lw.iso(prev["timestamp"])},
        "checks": checks,
        "result": compute(p_close),
        "reported_status_at_close": p_close.get("status"),
        "reported_status_latest": p_latest.get("status"),
        "latest_block": at_height(load("proposal_latest")),
    }


def verify(path):
    """Offline check. Returns a list of problems (empty = OK)."""
    path = Path(path)
    doc = json.loads(path.read_text(encoding="utf-8"))
    root = path.resolve().parent.parent  # data/hsp029.json -> repo root
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
    failed = [k for k, ok in again["checks"].items()
              if not ok and k != "latest_votes_equal_close"]
    problems += [f"check failed: {k}" for k in failed]
    return problems


# ---------- output ----------

def show(doc):
    p, r = doc["proposal"], doc["result"]
    print(f"Proposal {p['proposal_id']}: {p.get('title')}")
    print(f"Voting end {p['voting_end_utc'][:19]}Z · closing block {doc['closing_block']['height']:,}"
          f" ({doc['closing_block']['timestamp_utc'][:23]})")
    print(f"Snapshot block {r.get('snapshot_block')}, {r.get('snapshot_accounts')} accounts, "
          f"{r.get('snapshot_total_venear')} veNEAR")
    for o in r.get("options", []):
        print(f"  [{o['index']}] {o['label']}: {o['venear']} veNEAR, {o['votes']} votes")
    print(f"Total {r.get('total_venear')} veNEAR ({r.get('total_votes')} votes) · quorum required "
          f"{r.get('quorum_required_venear')} → met: {r.get('quorum_met')}")
    print(f"Approval For/(For+Against) {r.get('approval_share_for_of_for_plus_against')} "
          f"(needs {r.get('approval_threshold_bps')} bps) → met: {r.get('approval_met')}")
    print(f"Computed: {r['computed_status']} · contract status at close: "
          f"{doc['reported_status_at_close']} · latest: {doc['reported_status_latest']}")
    bad = [k for k, ok in doc["checks"].items() if not ok]
    print("Checks: all OK" if not bad else f"Checks FAILED: {', '.join(bad)}")


def peek(chain, proposal_id=PROPOSAL_ID):
    raw = view(chain, "get_proposal", {"proposal_id": proposal_id})
    p = decode(raw)
    if p is None:
        raise SystemExit(f"Proposal {proposal_id} not found on {CONTRACT}.")
    print(f"block {at_height(raw):,} · fields: {', '.join(sorted(p))}")
    print(f"title: {p.get('title')} · status: {p.get('status')} · options: {p.get('voting_options')}")
    if p.get("voting_start_time_ns") is not None:
        print(f"voting ends {lw.iso(voting_end_ns(p))[:19]}Z")
    r = compute(p)
    print(json.dumps(r, indent=1))
    print("(current state only; nothing saved)")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--peek", action="store_true", help="one call now, nothing saved")
    parser.add_argument("--verify", nargs="?", const=str(REPO / "data" / OUT_NAME), metavar="FILE",
                        help="offline check (default data/hsp029.json)")
    parser.add_argument("--proposal", type=int, default=PROPOSAL_ID)
    parser.add_argument("--data-dir", type=Path, default=REPO / "data")
    args = parser.parse_args()
    if args.verify:
        if not Path(args.verify).exists():
            print(f"SKIPPED: {Path(args.verify).name} does not exist yet; it is made after the "
                  f"vote closes (2026-11-02 16:48:08 UTC)")
            return
        problems = verify(args.verify)
        if problems:
            print("FAILED:\n  " + "\n  ".join(problems))
            sys.exit(1)
        print("OK: raw sha256 match, closing block checks pass, result recomputes exactly")
        return
    if args.peek:
        peek(lw.Chain(url=lw.RPC), args.proposal)
        return
    chain = lw.Chain()
    doc = run(chain, args.data_dir, args.proposal)
    out = args.data_dir / OUT_NAME
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
                   newline="\n")
    show(doc)
    print(f"Saved {out.relative_to(args.data_dir.parent).as_posix()} ({chain.calls} calls)")
    problems = verify(out)
    if problems:
        print("VERIFY FAILED:\n  " + "\n  ".join(problems))
        sys.exit(1)


if __name__ == "__main__":
    main()
