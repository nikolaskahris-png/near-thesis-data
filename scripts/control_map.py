"""Control map: who can change each link from the fee a user pays to the NEAR a holder keeps.

Every link is read at one locked block (the last boundary of a window file) from a NEAR
archival RPC, and each answer is reduced to "k of n": how many signatures (DAO votes,
multisig confirmations or keys) are enough to change that link.

Rules used, from the contracts' own code:
  Sputnik DAO v2 (sputnikdao2 policy.rs): a proposal of kind L passes when, in any role
    whose permissions include L:VoteApprove (or L:*, *:VoteApprove, *:*), approvals reach
    max(quorum, threshold); threshold Weight(w) = min(w, n), Ratio(a, b) = min(a*n//b + 1, n),
    n = members of the role; a role without a policy for L uses the default policy.
    "rules" = the smallest k among kinds that change the DAO's own policy or members
    (policy, policy_add_or_update_role, policy_update_default_vote_policy,
    add_member_to_role): whoever can do that can grant itself every other permission.
  NEAR multisig (buybacks, treasury.near): k = get_num_confirmations, n = access keys that
    can only call the multisig itself; any full-access key is reported (it would be 1 of 1).
  intents.near (near/intents 0.4.5, contracts/defuse/src/contract): set_fee and
    set_fee_collector need role DAO or FeesManager; upgrade needs role DAO or Upgrader.
  ctl-intents.near (aurora-controller-factory 0.3.3, contract/src/lib.rs): add_release_info
    and unrestricted_upgrade need role DAO; upgrade (to an added release with a higher
    version) needs DAO or Updater; downgrade (to the release's own downgrade hash) needs
    DAO or Downgrader.
  Protocol: an upgrade activates when validators holding protocol_upgrade_stake_threshold
    of the epoch's stake run it; counts below use the validators of the locked block's epoch.

Privacy: answers that list accounts of people (DAO members, role grantees, guardians,
reviewers, validators) go to data/private/control/ (not committed). Each has a redacted
copy in data/raw/redacted/control/ (scripts/privacy.py): only the fields used below, with
accounts outside PUBLIC_ACCOUNTS as sha256 tags. The map is always computed from the
public files and the redacted copies, so --verify recomputes it offline.

Read-only: JSON-RPC "query", "EXPERIMENTAL_protocol_config" and "validators".
No keys, nothing written on chain.

Usage:
    python scripts/control_map.py --window data/window_2026-10-02_2026-11-01.json
    python scripts/control_map.py --verify             offline
    python scripts/control_map.py --verify --archival  re-fetch every answer, compare sha256
"""
import argparse
import base64
import json
import re
import sys
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lock_window as lw  # noqa: E402
import privacy  # noqa: E402

REPO = lw.REPO
OUT_NAME = "control_map.json"
YOCTO = 10 ** 24

INTENTS = "intents.near"
CTL = "ctl-intents.near"
INTENTS_DAO = "intents.sputnik-dao.near"
BUYBACKS = "buybacks.multisignature.near"
TREASURY = "treasury.near"
CS_DAO = "1csfundsadmin.sputnik-dao.near"
FE_DAO = "fefundsadmin.sputnik-dao.near"
VOTE = "vote.dao"
HOS_ROOT = "hos-root.sputnik-dao.near"
POOL = "nearai.pool.near"
POOL_OWNER = "jasnah-treasury.sputnik-dao.near"
STAKE_DAO = "stake.dao"
DAOS = [INTENTS_DAO, CS_DAO, FE_DAO, HOS_ROOT, POOL_OWNER]
MULTISIGS = [BUYBACKS, TREASURY]
ACCOUNTS = [INTENTS, CTL, INTENTS_DAO, BUYBACKS, TREASURY, CS_DAO, FE_DAO, VOTE, HOS_ROOT,
            POOL, POOL_OWNER, STAKE_DAO]
# Contracts and organisations' accounts that may be named in the public file.
PUBLIC_ACCOUNTS = set(ACCOUNTS) | {"wrap.near", "venear.dao", "hos-deposits.sputnik-dao.near"}

EXPECTED_SOURCE = {INTENTS: "0.4.5", CTL: "0.3.3"}  # versions whose code the rules above read
RULE_KINDS = ["policy", "policy_add_or_update_role", "policy_update_default_vote_policy",
              "add_member_to_role"]
REPORT_KINDS = ["transfer", "call", "upgrade_self", "upgrade_remote"] + RULE_KINDS
SOURCES = {
    "sputnik": "near-daos/sputnik-dao-contract sputnikdao2/src/policy.rs (proposal_status, "
               "WeightOrRatio::to_weight, can_execute_action)",
    "intents": "near/intents 0.4.5 contracts/defuse/src/contract/fees.rs (set_fee: DAO, "
               "FeesManager), upgrade.rs (upgrade: DAO, Upgrader)",
    "ctl": "aurora-is-near/aurora-controller-factory 0.3.3 contract/src/lib.rs "
           "(add_release_info, unrestricted_upgrade: DAO; upgrade: DAO, Updater; "
           "downgrade: DAO, Downgrader)",
}


# ---------------------------------------------------------------- fetching

def b64(args):
    return base64.b64encode(json.dumps(args).encode()).decode()


def request_view(account, method, args, height):
    return {"method": "query", "params": {
        "request_type": "call_function", "block_id": height, "account_id": account,
        "method_name": method, "args_base64": b64(args)}}


def request_account(account, height, keys=False):
    return {"method": "query", "params": {
        "request_type": "view_access_key_list" if keys else "view_account",
        "block_id": height, "account_id": account}}


def fetch(chain, request):
    raw = chain._post({"jsonrpc": "2.0", "id": "control", **request})
    doc = json.loads(raw)
    res = doc.get("result")
    if "error" in doc or res is None or (isinstance(res, dict) and "error" in res):
        err = doc.get("error") or res.get("error")
        raise RuntimeError(f"{json.dumps(request)[:160]}: {json.dumps(err)[:300]}")
    return raw


class Store:
    """Saves each raw answer, public or private, and remembers its request and sha256."""

    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.files = {}

    def put(self, key, raw, private, request):
        sub = "private/control" if private else "raw/control"
        path = self.data_dir / sub / (re.sub(r"[^A-Za-z0-9_.-]", "_", key) + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        self.files[key] = {"path": path.relative_to(self.data_dir.parent).as_posix(),
                           "sha256": lw.sha256(raw), "private": private, "request": request}


def decode(raw):
    doc = json.loads(raw)
    if "redacted_value" in doc:
        return doc["redacted_value"]
    return json.loads(bytes(doc["result"]["result"]).decode())


def project(key, raw):
    """Redacted copy of a private answer: the fields build() reads, people as tags."""
    pub = PUBLIC_ACCOUNTS
    if key == "validators":
        res = json.loads(raw)["result"]
        return privacy.dumps({"result": {
            "current_validators": [{"stake": v["stake"]} for v in res["current_validators"]],
            "epoch_start_height": res.get("epoch_start_height")}})
    v = decode(raw)
    if key.endswith("/get_policy"):
        v = {"roles": [{"name": r["name"], "kind": privacy.redact(r["kind"], pub),
                        "permissions": r["permissions"], "vote_policy": r.get("vote_policy", {})}
                       for r in v["roles"]],
             "default_vote_policy": v["default_vote_policy"]}
    elif key == f"{VOTE}/get_config":
        v = {k: privacy.redact(v[k], pub) for k in ("owner_account_id", "reviewer_ids",
                                                    "council_ids", "guardians",
                                                    "max_active_proposals") if k in v}
    elif key == f"{STAKE_DAO}/get_config":
        v = {k: privacy.redact(v[k], pub) for k in ("owner_account_id", "guardians") if k in v}
    elif "/grantees/" in key:
        v = privacy.redact(v, pub)
    else:
        raise ValueError(f"no redaction rule for {key}")
    return privacy.dumps({"redacted_value": v})


def collect(chain, store, height, start_height, epoch_id):
    def q(key, request, private=False):
        raw = fetch(chain, request)
        store.put(key, raw, private, request)
        return raw

    for a in ACCOUNTS:
        q(f"account/{a}", request_account(a, height))
        q(f"keys/{a}", request_account(a, height, keys=True))
    q(f"account_start/{TREASURY}", request_account(TREASURY, start_height))
    for c in (INTENTS, CTL):
        q(f"{c}/contract_source_metadata", request_view(c, "contract_source_metadata", {}, height))
        roles = decode(q(f"{c}/acl_role_variants", request_view(c, "acl_role_variants", {}, height)))
        q(f"{c}/acl_get_super_admins",
          request_view(c, "acl_get_super_admins", {"skip": 0, "limit": 100}, height))
        for r in roles:
            q(f"{c}/grantees/{r}",
              request_view(c, "acl_get_grantees", {"role": r, "skip": 0, "limit": 100}, height),
              private=True)
    q(f"{INTENTS}/fee", request_view(INTENTS, "fee", {}, height))
    q(f"{CTL}/get_deployment", request_view(CTL, "get_deployment", {"account_id": INTENTS}, height))
    q(f"{CTL}/get_releases", request_view(CTL, "get_releases", {}, height))
    for d in DAOS:
        q(f"{d}/get_policy", request_view(d, "get_policy", {}, height), private=True)
    for m in MULTISIGS:
        q(f"{m}/get_num_confirmations", request_view(m, "get_num_confirmations", {}, height))
    q(f"{VOTE}/get_config", request_view(VOTE, "get_config", {}, height), private=True)
    q(f"{STAKE_DAO}/get_config", request_view(STAKE_DAO, "get_config", {}, height), private=True)
    q(f"{POOL}/get_reward_fee_fraction", request_view(POOL, "get_reward_fee_fraction", {}, height))
    q(f"{POOL}/get_owner_id", request_view(POOL, "get_owner_id", {}, height))
    q("protocol_config", {"method": "EXPERIMENTAL_protocol_config", "params": {"block_id": height}})
    q("validators", {"method": "validators", "params": {"epoch_id": epoch_id}}, private=True)


# ---------------------------------------------------------------- rules

def permits(perms, kind, action="VoteApprove"):
    return any(p in perms for p in (f"{kind}:{action}", f"{kind}:*", f"*:{action}", "*:*"))


def threshold_weight(threshold, n):
    if isinstance(threshold, list):
        a, b = threshold
        return min(a * n // b + 1, n)
    return min(int(threshold), n)


def k_of_n(policy, kind):
    """Fewest approvals that pass a proposal of `kind`: (k, n, role) or None."""
    best = None
    for role in policy["roles"]:
        group = role["kind"].get("Group") if isinstance(role["kind"], dict) else None
        if group is None or not permits(role["permissions"], kind):
            continue
        vp = role.get("vote_policy", {}).get(kind, policy["default_vote_policy"])
        if vp.get("weight_kind", "RoleWeight") != "RoleWeight":
            raise ValueError(f"role {role['name']}: weight_kind {vp['weight_kind']} not handled")
        n = len(group)
        k = max(int(vp.get("quorum", "0")), threshold_weight(vp["threshold"], n))
        if best is None or (k, n) < (best["k"], best["n"]):
            best = {"k": k, "n": n, "role": role["name"]}
    return best


def dao_summary(policy):
    kinds = {k: k_of_n(policy, k) for k in REPORT_KINDS}
    rules = [v for k, v in kinds.items() if k in RULE_KINDS and v]
    return {
        "kinds": kinds,
        "rules": min(rules, key=lambda v: (v["k"], v["n"])) if rules else None,
        "roles": [{"name": r["name"],
                   "members": len(r["kind"]["Group"]) if isinstance(r["kind"], dict)
                   and "Group" in r["kind"] else r["kind"],
                   "permissions": sorted(r["permissions"])} for r in policy["roles"]],
    }


def key_summary(keys_doc, account):
    full, own, other = 0, 0, 0
    for k in keys_doc["keys"]:
        perm = k["access_key"]["permission"]
        if perm == "FullAccess":
            full += 1
        elif perm["FunctionCall"]["receiver_id"] == account:
            own += 1
        else:
            other += 1
    return {"full_access": full, "function_call_on_itself": own, "function_call_other": other}


def named(accounts):
    """Public form of an account list: names of known contracts, a count for the rest."""
    return {"public": sorted(a for a in accounts if a in PUBLIC_ACCOUNTS),
            "others": sum(1 for a in accounts if a not in PUBLIC_ACCOUNTS),
            "total": len(accounts)}


def stake_needed(stakes, num, den, strict):
    """Fewest validators (largest first) whose stake reaches num/den (or exceeds it)."""
    total = sum(stakes)
    acc = 0
    for i, s in enumerate(sorted(stakes, reverse=True), 1):
        acc += s
        if (acc * den > num * total) if strict else (acc * den >= num * total):
            return i
    return None


def frac(x):
    return f"{x[0]}/{x[1]}"


def ratio(part, total, places=6):
    scaled = round(Fraction(part, total) * 10 ** places)
    sign = "-" if scaled < 0 else ""
    scaled = abs(scaled)
    return f"{sign}{scaled // 10 ** places}.{scaled % 10 ** places:0{places}d}"


# ---------------------------------------------------------------- build

def build(root, files, window):
    """Everything computed from the raw files. Used by run() and by --verify."""
    def raw(key):
        return privacy.read(root, files[key])

    def view(key):
        return decode(raw(key))

    def result(key):
        return json.loads(raw(key))["result"]

    first_b, last_b = window["boundaries"][0], window["boundaries"][-1]
    accounts = {a: {"code_hash": result(f"account/{a}")["code_hash"],
                    **key_summary(result(f"keys/{a}"), a)} for a in ACCOUNTS}

    def acl(c):
        roles = view(f"{c}/acl_role_variants")
        return {"super_admins": named(view(f"{c}/acl_get_super_admins")),
                "grantees": {r: named(view(f"{c}/grantees/{r}")) for r in roles}}

    intents_acl, ctl_acl = acl(INTENTS), acl(CTL)
    versions = {c: view(f"{c}/contract_source_metadata").get("version") for c in (INTENTS, CTL)}
    deployment = view(f"{CTL}/get_deployment")
    upgrades = sorted(deployment.get("upgrade_times", {}).items(), key=lambda kv: int(kv[0]))
    releases = view(f"{CTL}/get_releases")
    fee_pips = view(f"{INTENTS}/fee")
    daos = {d: dao_summary(view(f"{d}/get_policy")) for d in DAOS}
    multisigs = {m: {"confirmations": view(f"{m}/get_num_confirmations"),
                     "member_keys": accounts[m]["function_call_on_itself"],
                     "full_access_keys": accounts[m]["full_access"]} for m in MULTISIGS}
    vote_cfg = view(f"{VOTE}/get_config")
    stake_cfg = view(f"{STAKE_DAO}/get_config")
    pool_fee = view(f"{POOL}/get_reward_fee_fraction")
    pc = result("protocol_config")
    vals = result("validators")
    stakes = [int(v["stake"]) for v in vals["current_validators"]]
    t_start = int(result(f"account_start/{TREASURY}")["amount"])
    t_end = int(result(f"account/{TREASURY}")["amount"])
    supply_growth = int(last_b["total_supply_yocto"]) - int(first_b["total_supply_yocto"])

    links = {
        "intents_protocol_fee": {
            "value": {"fee_pips": fee_pips, "fee_percent": str(Decimal(fee_pips) / Decimal(10 ** 4))},
            "changed_by": "role DAO or FeesManager on intents.near",
            "dao_grantees": intents_acl["grantees"].get("DAO"),
            "fees_manager_grantees": intents_acl["grantees"].get("FeesManager"),
            "via": {INTENTS_DAO: daos[INTENTS_DAO]["kinds"]["call"]},
        },
        "intents_code": {
            "changed_by": "role DAO or Upgrader on intents.near",
            "upgrader_grantees": intents_acl["grantees"].get("Upgrader"),
            "controller": {
                "add_release": {INTENTS_DAO: daos[INTENTS_DAO]["kinds"]["call"]},
                "updater_grantees": ctl_acl["grantees"].get("Updater"),
                "downgrader_grantees": ctl_acl["grantees"].get("Downgrader"),
                "releaser_grantees": ctl_acl["grantees"].get("Releaser"),
                "dao_grantees": ctl_acl["grantees"].get("DAO"),
                "full_access_keys": accounts[CTL]["full_access"],
            },
            "deployed_version": deployment.get("version"),
            "code_changes": len(upgrades),
            "last_upgrade_utc": lw.iso(int(upgrades[-1][0])) if upgrades else None,
            "releases": len(releases),
        },
        "user_fee_1click": {"changed_by": "off-chain (1Click terms)", "on_chain": False},
        "buybacks_wallet": {"multisig": multisigs[BUYBACKS]},
        "wallet_1cs": {"dao": daos[CS_DAO]["kinds"]["transfer"], "rules": daos[CS_DAO]["rules"]},
        "wallet_front_end": {"dao": daos[FE_DAO]["kinds"]["transfer"], "rules": daos[FE_DAO]["rules"]},
        "issuance": {
            "max_inflation_rate": frac(pc["max_inflation_rate"]),
            "protocol_upgrade_stake_threshold": frac(pc["protocol_upgrade_stake_threshold"]),
            "protocol_version": pc["protocol_version"],
            "validators": len(stakes),
            "validators_to_reach_threshold": stake_needed(stakes, *pc["protocol_upgrade_stake_threshold"], False),
            "validators_to_block_upgrade": stake_needed(
                stakes, pc["protocol_upgrade_stake_threshold"][1] - pc["protocol_upgrade_stake_threshold"][0],
                pc["protocol_upgrade_stake_threshold"][1], True),
            "validators_to_reach_two_thirds": stake_needed(stakes, 2, 3, False),
            "validators_to_exceed_one_third": stake_needed(stakes, 1, 3, True),
            "largest_validator_share": ratio(max(stakes), sum(stakes)),
            "epoch_start_height": vals.get("epoch_start_height"),
        },
        "protocol_treasury": {
            "account": pc.get("protocol_treasury_account"),
            "reported_protocol_reward_rate": frac(pc["protocol_reward_rate"]),
            "balance_change_near": ratio(t_end - t_start, YOCTO, 3),
            "share_of_new_supply": ratio(t_end - t_start, supply_growth),
            "multisig": multisigs[TREASURY],
            "note": "measured from balances; the RPC field protocol_reward_rate is reported, not used",
        },
        "hsp_voting": {
            "owner": vote_cfg.get("owner_account_id"),
            "owner_dao": daos[HOS_ROOT]["rules"],
            "reviewers": len(vote_cfg.get("reviewer_ids") or []),
            "council": len(vote_cfg.get("council_ids") or []),
            "guardians": len(vote_cfg.get("guardians") or []),
            "max_active_proposals": vote_cfg.get("max_active_proposals"),
            "full_access_keys": accounts[VOTE]["full_access"],
        },
        "nearai_pool_rewards": {
            "reward_fee": f"{pool_fee['numerator']}/{pool_fee['denominator']}",
            "owner": view(f"{POOL}/get_owner_id"),
            "owner_dao": daos[POOL_OWNER]["kinds"]["transfer"],
            "owner_rules": daos[POOL_OWNER]["rules"],
            "full_access_keys": accounts[POOL]["full_access"],
        },
        "farm_contract": {
            "owner": stake_cfg.get("owner_account_id"),
            "full_access_keys": accounts[STAKE_DAO]["full_access"],
            "guardians": len(stake_cfg.get("guardians") or []),
            "credits_rate": "see data/farm_rate.json (edit_price by one catalog manager)",
        },
    }
    checks = {
        "intents_source_version_matches_rules": versions[INTENTS] == EXPECTED_SOURCE[INTENTS],
        "controller_source_version_matches_rules": versions[CTL] == EXPECTED_SOURCE[CTL],
        "deployed_intents_version_equals_metadata": deployment.get("version") == versions[INTENTS],
        "validators_epoch_contains_end_block":
            vals.get("epoch_start_height", 10 ** 12) <= last_b["height"],
        "public_output_names_allowlisted": True,  # set below
    }
    out = {"block": {"height": last_b["height"], "timestamp_utc": last_b["timestamp_utc"]},
           "rules_source": SOURCES, "source_versions": versions,
           "accounts": accounts, "daos": daos, "links": links, "checks": checks}
    checks["public_output_names_allowlisted"] = not leaked_names(out)
    return out


ACCOUNT_RE = re.compile(r"^(?:[a-z0-9][a-z0-9_-]*\.)*[a-z0-9_-]+\.(?:near|dao|tg)$|^[0-9a-f]{64}$")


def leaked_names(obj):
    """Account-like strings in the public output that are not in PUBLIC_ACCOUNTS."""
    found = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            found += leaked_names(k) + leaked_names(v)
    elif isinstance(obj, list):
        for v in obj:
            found += leaked_names(v)
    elif isinstance(obj, str) and ACCOUNT_RE.match(obj) and obj not in PUBLIC_ACCOUNTS:
        found.append(obj)
    return found


# ---------------------------------------------------------------- run / verify

def run(chain, data_dir, window_path):
    window = json.loads(Path(window_path).read_text(encoding="utf-8"))
    start, end = window["boundaries"][0], window["boundaries"][-1]
    block_file = data_dir / "raw" / "blocks" / f"block_{end['height']}.json"
    header = json.loads(block_file.read_bytes())["result"]["header"]
    store = Store(data_dir)
    collect(chain, store, end["height"], start["height"], header["epoch_id"])
    privacy.write_redacted(data_dir.parent, store.files, project)
    doc = {
        "measure": "control map: who can change each link of the value path, as k of n",
        "window_file": Path(window_path).resolve().relative_to(data_dir.parent.resolve()).as_posix(),
        "source": {"rpc": chain.url},
        "privacy": "answers that list people's accounts stay in data/private/control/ "
                   "(not committed); their requests and sha256 are below, with a redacted "
                   "copy under data/raw/redacted/control/ that the map is computed from",
        "raw_files": store.files,
    }
    doc.update(build(data_dir.parent, store.files, window))
    return doc


def verify(path, archival=False, chain=None):
    """Offline check (or re-fetch with archival=True). Returns (problems, private absent)."""
    path = Path(path)
    doc = json.loads(path.read_text(encoding="utf-8"))
    root = path.resolve().parent.parent
    problems = []
    if archival:
        for key, f in doc["raw_files"].items():
            p = root / f["path"]
            raw = fetch(chain, f["request"])
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
    L = doc["links"]

    def kn(x):
        return f"{x['k']} of {x['n']} ({x['role']})" if x else "nobody"

    print(f"Block {doc['block']['height']:,} ({doc['block']['timestamp_utc'][:19]}Z)")
    f = L["intents_protocol_fee"]
    print(f"intents.near fee: {f['value']['fee_pips']} pip ({f['value']['fee_percent']}%) · "
          f"FeesManager {f['fees_manager_grantees']['total']} · DAO call {kn(f['via'][INTENTS_DAO])}")
    c = L["intents_code"]
    print(f"intents.near code {c['deployed_version']}: {c['code_changes']} code changes, last {c['last_upgrade_utc'][:10]} · "
          f"Updater {c['controller']['updater_grantees']['total']} · Downgrader "
          f"{c['controller']['downgrader_grantees']['total']} · releases by DAO")
    m = L["buybacks_wallet"]["multisig"]
    print(f"buybacks: {m['confirmations']} of {m['member_keys']} keys, full keys {m['full_access_keys']}")
    for name, key in (("1cs", "wallet_1cs"), ("front end", "wallet_front_end")):
        print(f"{name}: transfer {kn(L[key]['dao'])} · rules {kn(L[key]['rules'])}")
    i = L["issuance"]
    print(f"issuance {i['max_inflation_rate']}: upgrade needs {i['validators_to_reach_threshold']} of "
          f"{i['validators']} validators, {i['validators_to_block_upgrade']} can block; largest "
          f"{i['largest_validator_share']}")
    t = L["protocol_treasury"]
    print(f"treasury.near: +{t['balance_change_near']} NEAR = {t['share_of_new_supply']} of new supply "
          f"(RPC protocol_reward_rate {t['reported_protocol_reward_rate']})")
    h = L["hsp_voting"]
    print(f"vote.dao owner DAO rules {kn(h['owner_dao'])} · reviewers {h['reviewers']} · guardians {h['guardians']}")
    p = L["nearai_pool_rewards"]
    print(f"nearai.pool.near fee {p['reward_fee']} · owner transfer {kn(p['owner_dao'])}")
    s = L["farm_contract"]
    print(f"stake.dao owner {s['owner']}: {s['full_access_keys']} full keys, {s['guardians']} guardians")
    bad = [k for k, ok in doc["checks"].items() if not ok]
    print("Checks: all OK" if not bad else f"Checks FAILED: {', '.join(bad)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--window", help="locked window file (end block = last boundary)")
    parser.add_argument("--verify", nargs="?", const=str(REPO / "data" / OUT_NAME), metavar="FILE")
    parser.add_argument("--archival", action="store_true", help="with --verify: re-fetch answers")
    parser.add_argument("--data-dir", type=Path, default=REPO / "data")
    args = parser.parse_args()
    if args.verify:
        problems, missing = verify(args.verify, args.archival, lw.Chain() if args.archival else None)
        if problems:
            print("FAILED:\n  " + "\n  ".join(problems))
            sys.exit(1)
        print(privacy.status_line("the control map", missing))
        return
    if not args.window:
        parser.error("--window is required")
    chain = lw.Chain()
    doc = run(chain, args.data_dir, args.window)
    out = args.data_dir / OUT_NAME
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    show(doc)
    print(f"Saved {out.relative_to(args.data_dir.parent).as_posix()} ({chain.calls} calls, "
          f"{chain.rate_limited} rate limited)")
    problems, _ = verify(out)
    if problems:
        print("VERIFY FAILED:\n  " + "\n  ".join(problems))
        sys.exit(1)


if __name__ == "__main__":
    main()
