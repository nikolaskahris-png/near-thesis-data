"""When House of Stake proposal HSP-027 (vote.dao, proposal 27) passed: its voting end, read from the chain.

One read-only call: vote.dao get_proposal {"proposal_id": 27} at the latest final block. The vote
closes at voting_start_time_ns + voting_duration_ns, computed exactly as hsp029.py does for HSP-029
(the voting contract's proposal.rs: `timestamp >= voting_end`). Both fields are fixed once voting
starts, so a read after the vote gives the same end as a read at its closing block.

The response names people's accounts and carries the proposer's text, so the original stays in
data/private/hos/hsp027/ (not committed) and a redacted copy (privacy.py, as hsp029.py) is saved in
data/raw/redacted/hos/hsp027/. data/hsp027.json lists both with sha256.

Usage:
    python scripts/hsp027.py            one call, save, compute
    python scripts/hsp027.py --verify   offline check of data/hsp027.json
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hsp029  # noqa: E402
import lock_window as lw  # noqa: E402
import privacy  # noqa: E402

PROPOSAL_ID = 27
OUT_NAME = "hsp027.json"
REPO = lw.REPO
RULE = "voting end = voting_start_time_ns + voting_duration_ns (as hsp029.py; proposal.rs)"


def build(root, raw_files):
    """Everything computed from the saved response."""
    raw = privacy.read(root, raw_files["proposal_latest"])
    p = hsp029.decode(raw)
    end = hsp029.voting_end_ns(p)
    out = hsp029.describe(p, end)
    out["proposal_id"] = p.get("id", PROPOSAL_ID)
    return {"proposal": out, "voting_end_date_utc": out["voting_end_utc"][:10],
            "reported_status": p.get("status"), "read_at_block": hsp029.at_height(raw)}


def run(chain, data_dir):
    raw = hsp029.view(chain, "get_proposal", {"proposal_id": PROPOSAL_ID})
    if hsp029.decode(raw) is None:
        raise SystemExit(f"Proposal {PROPOSAL_ID} not found on {hsp029.CONTRACT}.")
    fetched = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    priv = data_dir / "private" / "hos" / "hsp027"
    priv.mkdir(parents=True, exist_ok=True)
    path = priv / f"get_proposal_{PROPOSAL_ID}_final_{fetched}.json"
    path.write_bytes(raw)
    raw_files = {"proposal_latest": {"path": path.relative_to(data_dir.parent).as_posix(),
                                     "sha256": lw.sha256(raw), "private": True}}
    privacy.write_redacted(data_dir.parent, raw_files, hsp029.project)
    doc = {"measure": "the date HSP-027 passed: its voting end, read from vote.dao",
           "contract": hsp029.CONTRACT, "source": {"rpc": chain.url, "methods": ["get_proposal"]},
           "rule": RULE, "fetched_utc": fetched, "raw_files": raw_files}
    doc.update(build(data_dir.parent, raw_files))
    return doc


def verify(path):
    path = Path(path)
    doc = json.loads(path.read_text(encoding="utf-8"))
    root = path.resolve().parent.parent
    problems, absent = privacy.check_files(root, doc["raw_files"], hsp029.project)
    verify.absent = absent
    if problems:
        return problems
    for key, value in build(root, doc["raw_files"]).items():
        if doc.get(key) != value:
            problems.append(f"'{key}' does not recompute from the saved response")
    return problems


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--verify", nargs="?", const=str(REPO / "data" / OUT_NAME), metavar="FILE")
    p.add_argument("--data-dir", type=Path, default=REPO / "data")
    a = p.parse_args()
    if a.verify:
        problems = verify(a.verify)
        if problems:
            print("FAILED:\n  " + "\n  ".join(problems))
            sys.exit(1)
        print("OK: sha256 match, voting end recomputes" + (
            f" (PUBLIC_REDACTED: {verify.absent} private original not in git; redacted copy checked)"
            if getattr(verify, "absent", 0) else ""))
        return
    chain = lw.Chain(url=lw.RPC)
    doc = run(chain, a.data_dir)
    out = a.data_dir / OUT_NAME
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    pr = doc["proposal"]
    print(f"HSP-027 ({pr.get('title')}): voting {pr['voting_start_utc'][:19]}Z -> {pr['voting_end_utc'][:19]}Z"
          f" · status {doc['reported_status']} · block {doc['read_at_block']:,}")
    print(f"Saved {out.relative_to(a.data_dir.parent).as_posix()} ({chain.calls} call)")
    problems = verify(out)
    print("VERIFY: OK" if not problems else "VERIFY FAILED:\n  " + "\n  ".join(problems))


if __name__ == "__main__":
    main()
