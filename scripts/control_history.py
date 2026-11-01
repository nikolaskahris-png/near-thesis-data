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
  staking      the DAO's own stake, unstake and withdraw calls to staking pools
  transfer     DAO transfers: Transfer proposals and ft/mt transfer calls
  other        anything else (counted, named by receiver and method)

Key history (NearBlocks): every access key ever added to or deleted from the map's
accounts that act through keys (multisigs, stake.dao, the intents contracts, the NEAR AI
pool, vote.dao), counted up to the end block's time. Check: the keys NearBlocks shows as
active at that time are compared with the keys the chain returned at the end block
(control_map.py's view_access_key_list). An account where they differ is listed under
key_history_mismatches and gets no key numbers: NearBlocks keeps one record per public
key, so a key deleted and later added again shows as deleted (seen on intents.near).
NearBlocks is not pinned to a block, so --verify --archival skips these files.

Also included: the code changes of intents.near recorded by its controller
(ctl-intents.near get_deployment upgrade_times, executed times) and the farm rate
changes from data/farm_rate.json.

Dates: Sputnik stores only when a proposal was SUBMITTED, not when it passed. Proposal
dates below are submission dates; a proposal passes within the DAO's proposal_period.

Privacy: proposal texts, proposers and voters can name people. Those raw answers go
to data/private/control/ (not committed). Each page has a redacted copy in
data/raw/redacted/control/ (scripts/privacy.py) with, per proposal, only id, kind, status,
submission time, receiver (a known contract by name, anyone else as a sha256 tag) and
method names; the history is always computed from it, so --verify recomputes it offline.

Read-only: JSON-RPC "query". No keys, nothing written on chain.

Usage:
    python scripts/control_history.py --window data/window_2026-10-02_2026-11-01.json
    python scripts/control_history.py --verify
    python scripts/control_history.py --verify --archival
"""
import argparse
import json
import sys
import time
import urllib.parse
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import control_map as cm  # noqa: E402
import lock_window as lw  # noqa: E402
import privacy  # noqa: E402
import stakers  # noqa: E402

REPO = lw.REPO
OUT_NAME = "control_history.json"
PAGE = 100
KEY_ACCOUNTS = [cm.BUYBACKS, cm.TREASURY, cm.STAKE_DAO, cm.CTL, cm.INTENTS, cm.POOL, cm.VOTE]
NEARBLOCKS_KEYS = "https://api.nearblocks.io/v1/account/{}/keys"
KEY_PAGE = 100
LEVERS = ["fee", "code", "roles", "user_funds", "pause", "voting", "staking", "transfer", "other"]
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
              "set_owner", "propose_new_owner", "add_validator_catalog_manager",
              "remove_validator_catalog_manager"},
    "user_funds": {"ft_force_withdraw", "mt_force_transfer", "mt_force_withdraw",
                   "nft_force_withdraw", "force_lock_account", "force_unlock_account"},
    "pause": {"pa_pause_feature", "pa_unpause_feature", "pause", "unpause"},
    "staking": {"deposit_and_stake", "deposit", "stake", "stake_all", "unstake", "unstake_all",
                "withdraw", "withdraw_all"},
    "transfer": {"ft_transfer", "ft_transfer_call", "mt_transfer", "mt_transfer_call",
                 "near_withdraw", "storage_deposit"},
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


def collect_keys(store, get=stakers.http_get, wait=stakers.PAGE_WAIT):
    first = True
    for a in KEY_ACCOUNTS:
        page = 1
        while True:
            if not first:
                time.sleep(wait)
            first = False
            url = NEARBLOCKS_KEYS.format(a) + "?" + urllib.parse.urlencode(
                {"per_page": KEY_PAGE, "page": page})
            raw = get(url)
            store.put(f"history/keys/{a}/page_{page}", raw, False, {"nearblocks": url})
            if len(json.loads(raw).get("keys", [])) < KEY_PAGE:
                break
            page += 1


def key_history(root, files, end_ns):
    """Key changes per account up to end_ns, and the check against the chain at the end."""
    out = {}
    for a in KEY_ACCOUNTS:
        keys = []
        for key in sorted(k for k in files if k.startswith(f"history/keys/{a}/page_")):
            keys += json.loads((root / files[key]["path"]).read_bytes())["keys"]
        for k in keys:  # keys from genesis have no creation time on NearBlocks
            if k["created"]["block_timestamp"] is None:
                k["created"]["block_timestamp"] = 0
        added = sorted(k["created"]["block_timestamp"] for k in keys
                       if k["created"]["block_timestamp"] is not None
                       and int(k["created"]["block_timestamp"]) <= end_ns)
        removed = sorted(k["deleted"]["block_timestamp"] for k in keys
                         if k["deleted"]["block_timestamp"] is not None
                         and int(k["deleted"]["block_timestamp"]) <= end_ns)
        active = sorted(k["public_key"] for k in keys
                        if k["created"]["block_timestamp"] is not None
                        and int(k["created"]["block_timestamp"]) <= end_ns
                        and (k["deleted"]["block_timestamp"] is None
                             or int(k["deleted"]["block_timestamp"]) > end_ns))
        chain_file = root / "data" / "raw" / "control" / f"keys_{a}.json"
        chain = None
        if chain_file.exists():
            chain = sorted(k["public_key"] for k in json.loads(chain_file.read_bytes())["result"]["keys"])
        day = lambda t: lw.iso(int(t))[:10]
        out[a] = {
            "keys_ever": len(added),
            "full_access_ever": sum(1 for k in keys if k["permission_kind"] == "FULL_ACCESS"
                                    and k["created"]["block_timestamp"] is not None
                                    and int(k["created"]["block_timestamp"]) <= end_ns),
            "active_at_end": len(active),
            "added_dates": [list(x) for x in sorted(Counter(day(t) for t in added).items())],
            "removed_dates": [list(x) for x in sorted(Counter(day(t) for t in removed).items())],
            "last_change": max([day(t) for t in added + removed], default=None),
            "matches_chain_at_end_block": None if chain is None else chain == active,
        }
    return out


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


def trim(proposal):
    """A proposal reduced to what entries() reads; receivers outside KNOWN_CONTRACTS as tags."""
    k = kind_name(proposal["kind"])
    out = {"id": proposal["id"], "status": proposal["status"],
           "submission_time": proposal["submission_time"]}
    body = proposal["kind"].get(k) if isinstance(proposal["kind"], dict) else None
    if body is None:
        out["kind"] = proposal["kind"]
    elif k == "FunctionCall":
        out["kind"] = {k: {"receiver_id": privacy.redact(body["receiver_id"], KNOWN_CONTRACTS),
                           "actions": [{"method_name": a["method_name"]} for a in body["actions"]]}}
    elif k == "UpgradeRemote":
        out["kind"] = {k: {"receiver_id": privacy.redact(body["receiver_id"], KNOWN_CONTRACTS),
                           "method_name": body.get("method_name")}}
    else:
        out["kind"] = {k: {}}
    return out


def project(key, raw):
    if "/get_proposals_" not in key:
        raise ValueError(f"no redaction rule for {key}")
    return privacy.dumps({"redacted_value": [trim(p) for p in cm.decode(raw)]})


# ---------------------------------------------------------------- build

def build(root, files, window):
    def raw(key):
        return privacy.read(root, files[key])

    last_b = window["boundaries"][-1]
    items, statuses, removed = [], Counter(), {}
    keys = key_history(root, files, int(last_b["timestamp_ns"])) \
        if any(k.startswith("history/keys/") for k in files) else None
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
        "key_history": keys,
        "timeline": sorted((e for e in items if e["status"] == "Approved" and e["lever"] != "transfer"),
                           key=lambda e: (e["submitted"], e["dao"], e["id"])),
    }
    out["key_history_mismatches"] = None if keys is None else sorted(
        a for a, v in keys.items() if v["matches_chain_at_end_block"] is False)
    out["checks"] = {"public_output_names_allowlisted": not leaked(out)}
    return out


def leaked(out):
    names = cm.leaked_names(out)
    return [n for n in names if n not in KNOWN_CONTRACTS]


# ---------------------------------------------------------------- run / verify

def run(chain, data_dir, window_path, get=stakers.http_get, wait=stakers.PAGE_WAIT):
    window = json.loads(Path(window_path).read_text(encoding="utf-8"))
    store = cm.Store(data_dir)
    collect(chain, store, window["boundaries"][-1]["height"])
    collect_keys(store, get, wait)
    privacy.write_redacted(data_dir.parent, store.files, project)
    doc = {
        "measure": "control history: every proposal of the control map's DAOs, by lever",
        "window_file": Path(window_path).resolve().relative_to(data_dir.parent.resolve()).as_posix(),
        "source": {"rpc": chain.url},
        "privacy": "proposal texts, proposers and votes stay in data/private/control/ "
                   "(not committed); their requests and sha256 are below, with a redacted "
                   "copy under data/raw/redacted/control/ that the history is computed from",
        "raw_files": store.files,
    }
    doc.update(build(data_dir.parent, store.files, window))
    return doc


def verify(path, archival=False, chain=None):
    path = Path(path)
    doc = json.loads(path.read_text(encoding="utf-8"))
    root = path.resolve().parent.parent
    problems = []
    if archival:
        for key, f in doc["raw_files"].items():
            if "nearblocks" in f["request"]:
                continue  # an index service: pages change as new rows arrive
            p = root / f["path"]
            raw = cm.fetch(chain, f["request"])
            if lw.sha256(raw) != f["sha256"]:
                problems.append(f"archival answer differs: {key}")
            elif not p.exists():
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(raw)
    p2, absent = privacy.check_files(root, doc["raw_files"], project)
    problems += p2
    if problems:
        return problems, absent
    window = json.loads((root / doc["window_file"]).read_text(encoding="utf-8"))
    again = build(root, doc["raw_files"], window)
    for key, value in again.items():
        if doc.get(key) != value:
            problems.append(f"'{key}' does not recompute from the raw files")
    problems += [f"check failed: {k}" for k, ok in again["checks"].items() if not ok]
    return problems, absent


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
    for a, k in (doc.get("key_history") or {}).items():
        print(f"keys {a}: {k['keys_ever']} ever ({k['full_access_ever']} full), {k['active_at_end']} "
              f"at end, last change {k['last_change']}, chain match {k['matches_chain_at_end_block']}")
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
        print(privacy.status_line("the control history", missing))
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
