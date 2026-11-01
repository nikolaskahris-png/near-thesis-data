"""Control history: when each lever of the control map was actually used.

The control map (control_map.py) says who CAN change each link. This script lists
what the same accounts DID: every proposal ever made in the five Sputnik DAOs of the
map, read from the DAOs themselves at the locked end block, sorted by lever.

  fee          set_fee, set_fee_collector on intents.near
  code         releases, upgrades and code staging on ctl-intents.near or intents.near,
               UpgradeSelf / UpgradeRemote proposals
  roles        role grants and revocations on any contract, DAO members and policy
  user_funds   ft_force_withdraw, mt_force_transfer, nft_force_withdraw,
               force_lock_account, force_unlock_account on intents.near
  pause        pa_pause_feature, pa_unpause_feature
  voting       set_* calls on vote.dao (who reviews, councils, guards the vote)
  transfer     DAO transfers (NEAR or tokens out of the DAO)
  other        anything else (counted, named by receiver and method)

Also included: the code changes of intents.near recorded by its controller
(ctl-intents.near get_deployment upgrade_times, executed times) and the farm rate
changes from data/farm_rate.json.

Dates: Sputnik stores only when a proposal was SUBMITTED, not when it passed. Proposal
dates below are submission dates; a proposal passes within the DAO's proposal_period.

Privacy: proposal texts, proposers and voters can name people. Those raw answers go
to data/private/control/ (not committed); the public file keeps their sha256 and, per
proposal, only id, kind, status, submission date, receiver (if a contract in
PUBLIC_ACCOUNTS or a known contract) and method.

Read-only: JSON-RPC "query". No keys, nothing written on chain.

Usage:
    python scripts/control_history.py --window data/window_2026-10-02_2026-11-01.json
    python scripts/control_history.py --verify
    python scripts/control_history.py --verify --archival
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import control_map as cm  # noqa: E402
import lock_window as lw  # noqa: E402

REPO = lw.REPO
OUT_NAME = "control_history.json"
PAGE = 100
LEVERS = ["fee", "code", "roles", "user_funds", "pause", "voting", "transfer", "other"]
# Contracts that may be named as receivers in the public file, besides cm.PUBLIC_ACCOUNTS.
KNOWN_CONTRACTS = cm.PUBLIC_ACCOUNTS | {"omft.near", "rec.hos", "registrar", "venear.dao",
                                        "venear.stagingdao.near", "outlayer-admin.near"}
METHODS = {
    "fee": {"set_fee", "set_fee_collector"},
    "code": {"add_release_info", "add_release_blob", "set_latest_release", "remove_release",
             "upgrade", "unrestricted_upgrade", "downgrade", "up_stage_code", "up_deploy_code",
             "add_deployment_info", "update_deployment_info", "deploy"},
    "roles": {"acl_grant_role", "acl_revoke_role", "acl_add_super_admin", "acl_revoke_super_admin",
              "acl_add_admin", "acl_revoke_admin", "add_full_access_key", "attach_full_access_key",
              "set_owner", "propose_new_owner"},
    "user_funds": {"ft_force_withdraw", "mt_force_transfer", "mt_force_withdraw",
                   "nft_force_withdraw", "force_lock_account", "force_unlock_account"},
    "pause": {"pa_pause_feature", "pa_unpause_feature", "pause", "unpause"},
}
POLICY_KINDS = {"ChangePolicy", "AddMemberToRole", "RemoveMemberFromRole",
                "ChangePolicyAddOrUpdateRole", "ChangePolicyRemoveRole",
                "ChangePolicyUpdateDefaultVotePolicy", "ChangePolicyUpdateParameters"}


# ---------------------------------------------------------------- fetching

def collect(chain, store, height):
    def q(key, request, private):
        raw = cm.fetch(chain, request)
        store.put(key, raw, private, request)
        return raw

    for d in cm.DAOS:
        last = cm.decode(q(f"history/{d}/get_last_proposal_id",
                           cm.request_view(d, "get_last_proposal_id", {}, height), False))
        for start in range(0, last, PAGE):
            q(f"history/{d}/get_proposals_{start}",
              cm.request_view(d, "get_proposals", {"from_index": start, "limit": PAGE}, height),
              True)
    q(f"history/{cm.CTL}/get_deployment",
      cm.request_view(cm.CTL, "get_deployment", {"account_id": cm.INTENTS}, height), False)


# ---------------------------------------------------------------- classify

def kind_name(kind):
    return kind if isinstance(kind, str) else next(iter(kind))


def lever_of(dao, kind, receiver=None, method=None):
    k = kind_name(kind)
    if k in POLICY_KINDS:
        return "roles"
    if k in ("UpgradeSelf", "UpgradeRemote"):
        return "code"
    if k == "Transfer":
        return "transfer"
    if k == "FunctionCall":
        if receiver == cm.VOTE and method and method.startswith("set_"):
            return "voting"
        for lever, names in METHODS.items():
            if method in names:
                return lever
    return "other"


def public_receiver(r):
    return r if r in KNOWN_CONTRACTS else "(account)"


def date_of(ns):
    return lw.iso(int(ns))[:10]


def entries(dao, proposal):
    """One public entry per action (a FunctionCall proposal can hold several)."""
    k = kind_name(proposal["kind"])
    base = {"dao": dao, "id": proposal["id"], "kind": k, "status": proposal["status"],
            "submitted": date_of(proposal["submission_time"])}
    body = proposal["kind"].get(k) if isinstance(proposal["kind"], dict) else None
    if k == "FunctionCall":
        return [{**base, "receiver": public_receiver(body["receiver_id"]),
                 "method": a["method_name"],
                 "lever": lever_of(dao, k, body["receiver_id"], a["method_name"])}
                for a in body["actions"]]
    if k == "UpgradeRemote":
        return [{**base, "receiver": public_receiver(body["receiver_id"]),
                 "method": body.get("method_name"), "lever": "code"}]
    return [{**base, "lever": lever_of(dao, k)}]


def summarise(items):
    out = {}
    for lever in LEVERS:
        approved = [e for e in items if e["lever"] == lever and e["status"] == "Approved"]
        dates = sorted(e["submitted"] for e in approved)
        out[lever] = {
            "approved_actions": len(approved),
            "first": dates[0] if dates else None,
            "last": dates[-1] if dates else None,
            "by_year": dict(sorted(Counter(d[:4] for d in dates).items())),
            "by_method": dict(sorted(Counter(
                f"{e.get('receiver', '')}.{e['method']}" if e.get("method") else e["kind"]
                for e in approved).items())),
        }
    return out


# ---------------------------------------------------------------- build

def build(root, files, window):
    def raw(key):
        return (root / files[key]["path"]).read_bytes()

    last_b = window["boundaries"][-1]
    items, statuses, removed = [], Counter(), {}
    for d in cm.DAOS:
        last = cm.decode(raw(f"history/{d}/get_last_proposal_id"))
        seen = []
        for start in range(0, last, PAGE):
            for p in cm.decode(raw(f"history/{d}/get_proposals_{start}")):
                seen.append(p["id"])
                statuses[(d, p["status"])] += 1
                items += entries(d, p)
        if not set(seen) <= set(range(last)) or len(seen) != len(set(seen)):
            raise ValueError(f"{d}: proposal ids outside 0..{last - 1} or repeated")
        removed[d] = last - len(seen)  # Sputnik drops removed proposals from get_proposals
    dep = cm.decode(raw(f"history/{cm.CTL}/get_deployment"))
    code_changes = [{"utc": lw.iso(int(t)), "version": v}
                    for t, v in sorted(dep.get("upgrade_times", {}).items(), key=lambda kv: int(kv[0]))]
    downgrades = sum(1 for a, b in zip(code_changes, code_changes[1:])
                     if tuple(map(int, b["version"].split("."))) < tuple(map(int, a["version"].split("."))))
    per_dao = {d: {"proposals": sum(c for (dd, _), c in statuses.items() if dd == d),
                   "by_status": dict(sorted((s, c) for (dd, s), c in statuses.items() if dd == d)),
                   "removed_proposals": removed[d],
                   "levers": summarise([e for e in items if e["dao"] == d])} for d in cm.DAOS}
    farm = None
    fr = root / "data" / "farm_rate.json"
    if fr.exists():
        frd = json.loads(fr.read_text(encoding="utf-8"))
        farm = [{"utc": c["receipt_utc"], "before": c["units_per_near_year_before"],
                 "after": c["units_per_near_year_after"]}
                for c in frd["changes"] if c["rate_changed"]]
    out = {
        "block": {"height": last_b["height"], "timestamp_utc": last_b["timestamp_utc"]},
        "dates_note": "proposal dates are submission dates (Sputnik does not store approval time); "
                      "intents.near code changes are execution times from ctl-intents.near",
        "per_dao": per_dao,
        "all_daos": summarise(items),
        "intents_code_changes": {"count": len(code_changes), "downgrades": downgrades,
                                 "changes": code_changes},
        "farm_rate_changes": farm,
        "timeline": sorted((e for e in items if e["status"] == "Approved" and e["lever"] != "transfer"),
                           key=lambda e: (e["submitted"], e["dao"], e["id"])),
    }
    out["checks"] = {"public_output_names_allowlisted": not leaked(out)}
    return out


def leaked(out):
    names = cm.leaked_names(out)
    return [n for n in names if n not in KNOWN_CONTRACTS]


# ---------------------------------------------------------------- run / verify

def run(chain, data_dir, window_path):
    window = json.loads(Path(window_path).read_text(encoding="utf-8"))
    store = cm.Store(data_dir)
    collect(chain, store, window["boundaries"][-1]["height"])
    doc = {
        "measure": "control history: every proposal of the control map's DAOs, by lever",
        "window_file": Path(window_path).resolve().relative_to(data_dir.parent.resolve()).as_posix(),
        "source": {"rpc": chain.url},
        "privacy": "proposal texts, proposers and votes stay in data/private/control/ "
                   "(not committed); their requests and sha256 are below",
        "raw_files": store.files,
    }
    doc.update(build(data_dir.parent, store.files, window))
    return doc


def verify(path, archival=False, chain=None):
    path = Path(path)
    doc = json.loads(path.read_text(encoding="utf-8"))
    root = path.resolve().parent.parent
    problems, missing = [], 0
    for key, f in doc["raw_files"].items():
        p = root / f["path"]
        if archival:
            raw = cm.fetch(chain, f["request"])
            if lw.sha256(raw) != f["sha256"]:
                problems.append(f"archival answer differs: {key}")
            elif not p.exists():
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(raw)
        if not p.exists():
            if f["private"]:
                missing += 1
            else:
                problems.append(f"missing raw file {f['path']}")
        elif lw.sha256(p.read_bytes()) != f["sha256"]:
            problems.append(f"sha256 mismatch: {f['path']}")
    if problems or missing:
        return problems, missing
    window = json.loads((root / doc["window_file"]).read_text(encoding="utf-8"))
    again = build(root, doc["raw_files"], window)
    for key, value in again.items():
        if doc.get(key) != value:
            problems.append(f"'{key}' does not recompute from the raw files")
    problems += [f"check failed: {k}" for k, ok in again["checks"].items() if not ok]
    return problems, 0


def show(doc):
    print(f"Block {doc['block']['height']:,}")
    for d, s in doc["per_dao"].items():
        used = ", ".join(f"{lv} {v['approved_actions']}" for lv, v in s["levers"].items()
                         if v["approved_actions"])
        print(f"{d}: {s['proposals']} proposals · approved actions: {used}")
    a = doc["all_daos"]
    for lv in LEVERS:
        v = a[lv]
        if v["approved_actions"]:
            print(f"  {lv:<11} {v['approved_actions']:>4}  {v['first']} .. {v['last']}  {v['by_year']}")
    c = doc["intents_code_changes"]
    print(f"intents.near code changes: {c['count']} ({c['downgrades']} downgrades), last "
          f"{c['changes'][-1]['utc'][:10] if c['changes'] else None}")
    bad = [k for k, ok in doc["checks"].items() if not ok]
    print("Checks: all OK" if not bad else f"Checks FAILED: {', '.join(bad)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--window")
    parser.add_argument("--verify", nargs="?", const=str(REPO / "data" / OUT_NAME), metavar="FILE")
    parser.add_argument("--archival", action="store_true")
    parser.add_argument("--data-dir", type=Path, default=REPO / "data")
    args = parser.parse_args()
    if args.verify:
        problems, missing = verify(args.verify, args.archival, lw.Chain() if args.archival else None)
        if problems:
            print("FAILED:\n  " + "\n  ".join(problems))
            sys.exit(1)
        if missing:
            print(f"OK for public files; {missing} private raw file(s) absent, so the history is "
                  f"not recomputed here (run --verify --archival to re-fetch and compare sha256)")
            return
        print("OK: raw sha256 match and the control history recomputes exactly")
        return
    if not args.window:
        parser.error("--window is required")
    chain = lw.Chain()
    doc = run(chain, args.data_dir, args.window)
    out = args.data_dir / OUT_NAME
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
                   newline="\n")
    show(doc)
    print(f"Saved {out.relative_to(args.data_dir.parent).as_posix()} ({chain.calls} calls, "
          f"{chain.rate_limited} rate limited)")
    problems, _ = verify(out)
    if problems:
        print("VERIFY FAILED:\n  " + "\n  ".join(problems))
        sys.exit(1)


if __name__ == "__main__":
    main()
