"""Flows of the account that owns nearai.pool.near (finding 4).

`nearai.pool.near` is the validator behind NEAR AI staking; its owner and reward
receiver is the DAO `jasnah-treasury.sputnik-dao.near` ("the owner" below). This
script measures, between two locked blocks, what the owner did with NEAR:

  - proposals of the owner's DAO that became Approved in the window (a Sputnik DAO
    acts only through proposals): NEAR and USDC transfers out, unstake, stake,
    withdraw, and any other function call;
  - the owner's NEAR positions at both blocks: liquid balance plus staked and
    unstaked balance in every staking pool its proposals have ever called;
  - swaps wNEAR -> USDC inside intents.near by the owner's payments account
    (`jasnah-payments.near`), from NearBlocks multi-token history.

Windows (end = last boundary of a locked window file, e.g. 2026-11-01 00:00 UTC):
  since_stake_dao: from the first block where stake.dao exists (the start of NEAR AI
                   staking by users) to the end block;
  year_2026:       from the first block at or after 2026-01-01 00:00 UTC to the end block.

"Approved in the window" = status Approved at the end block, and either missing or
not Approved at the start block. Exact, with no timestamps needed.

Privacy: proposal texts and counterparties can name private people. Those raw
responses go to data/private/ (not committed). The public file keeps their sha256,
the request that produced them, and records without names (recipients as sha256
prefixes; staking pools, token contracts and the owner's own accounts by name).
Anyone can re-fetch the same archival blocks (--archival) and compare the hashes.

Read-only: JSON-RPC "block", "query" and NearBlocks GET. No keys, nothing written on chain.

Usage:
    python scripts/treasury_flows.py --window data/window_2026-10-02_2026-11-01.json
    python scripts/treasury_flows.py --verify            offline
    python scripts/treasury_flows.py --verify --archival  re-fetch archival, compare sha256
"""
import argparse
import base64
import hashlib
import json
import re
import sys
import time
import urllib.parse
from datetime import date
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lock_window as lw  # noqa: E402
import stakers  # noqa: E402

TREASURY = "jasnah-treasury.sputnik-dao.near"
PAYMENTS = "jasnah-payments.near"
NEARAI_POOL = "nearai.pool.near"
KNOWN_POOLS = ["nearai.pool.near", "near-prime-public.poolv1.near"]
STAKE_DAO = "stake.dao"
INTENTS = "intents.near"
WNEAR = "wrap.near"
USDC = "17208628f84f5d6ad33f0da3bbbeb27ffcb398eac501a31bd6ad2011e36133a1"
USDC_ETH = "eth-0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48.omft.near"  # USDC bridged from Ethereum
USDT_NEAR = "usdt.tether-token.near"
USDT_ETH = "eth-0xdac17f958d2ee523a2206206994597c13d831ec7.omft.near"
# USD stablecoins inside intents.near, all with 6 decimals. Both USDC versions count as USDC.
STABLES = {USDC: "usdc", USDC_ETH: "usdc", USDT_NEAR: "usdt", USDT_ETH: "usdt"}
MT_TOKENS = [f"nep141:{t}" for t in (WNEAR, USDC, USDC_ETH, USDT_NEAR, USDT_ETH)]
MT_URL = "https://api.nearblocks.io/v3/accounts/{a}/mt-txns"
POOL_METHODS = {"deposit", "deposit_and_stake", "stake", "stake_all", "unstake", "unstake_all",
                "withdraw", "withdraw_all", "deposit_and_stake_all"}
YOCTO = 10 ** 24
USDC_UNIT = 10 ** 6
NS = lw.NS
REPO = lw.REPO
OUT_NAME = "treasury_flows.json"
PROPOSAL_PAGE = 100
YEAR_START = date(2026, 1, 1)
CREATION_LOW = 190_000_000  # stake.dao did not exist here (May 2026)
REF_HEIGHT = 217453248


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def units(x, unit, places=3):
    q = Fraction(int(x), unit)
    s = round(q * 10 ** places)
    sign = "-" if s < 0 else ""
    s = abs(s)
    return f"{sign}{s // 10 ** places}.{s % 10 ** places:0{places}d}"


def near(x):
    return units(x, YOCTO)


def usdc(x):
    return units(x, USDC_UNIT, 2)


def tag(acct):
    return "sha256:" + sha256(acct.encode())[:16]


# ---------------------------------------------------------------- RPC

def rpc_body(request):
    return {"jsonrpc": "2.0", "id": "treasury", "method": "query", "params": request}


def call_request(account, method, args, height):
    return {"request_type": "call_function", "block_id": height, "account_id": account,
            "method_name": method,
            "args_base64": base64.b64encode(json.dumps(args).encode()).decode()}


def account_request(account, height):
    return {"request_type": "view_account", "block_id": height, "account_id": account}


def keys_request(account, height):
    return {"request_type": "view_access_key_list", "block_id": height, "account_id": account}


def error_name(doc):
    err = doc.get("error")
    if err:
        return (err.get("cause") or {}).get("name") or err.get("name") or "ERROR"
    res = doc.get("result") or {}
    if "error" in res and "result" not in res and "amount" not in res and "keys" not in res:
        return "CONTRACT_ERROR"
    return None


def fetch(chain, request):
    """Raw bytes of one query. Raises on errors other than a missing account/contract."""
    raw = chain._post(rpc_body(request))
    name = error_name(json.loads(raw))
    if name in (None, "UNKNOWN_ACCOUNT", "CONTRACT_ERROR", "NO_CONTRACT_CODE",
                "CONTRACT_EXECUTION_ERROR"):
        return raw
    raise RuntimeError(f"{request.get('method_name') or request['request_type']} "
                       f"{request['account_id']} at {request['block_id']}: {name}")


def value_of(raw):
    """Decoded value of a saved query, or None when the account/contract was missing."""
    doc = json.loads(raw)
    if error_name(doc) is not None:
        return None
    res = doc["result"]
    if "result" in res:
        return json.loads(bytes(res["result"]).decode())
    return res


def exists_at(chain, account, height):
    """True/False, or None if this height has no block."""
    doc = json.loads(chain._post(rpc_body(account_request(account, height))))
    name = error_name(doc)
    if name == "UNKNOWN_BLOCK":
        return None
    if name == "UNKNOWN_ACCOUNT":
        return False
    if name is None:
        return True
    raise RuntimeError(f"view_account {account} at {height}: {name}")


def first_block_with_account(chain, account, lo, hi):
    """First existing block height at which `account` exists (lo: absent, hi: present)."""
    def probe(h):
        while True:
            e = exists_at(chain, account, h)
            if e is not None:
                return h, e
            h += 1
    assert probe(lo)[1] is False and probe(hi)[1] is True
    while hi - lo > 1:
        mid = (lo + hi) // 2
        h, e = probe(mid)
        if h >= hi:
            hi = mid  # every height from mid to hi-1 is skipped
            continue
        if e:
            hi = h
        else:
            lo = h
    return hi


# ---------------------------------------------------------------- store

class Store:
    """Saves raw responses; records path, sha256, privacy and the request."""

    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.files = {}

    def put(self, key, raw, private, request=None, kind="rpc"):
        sub = "private/treasury" if private else "raw/treasury"
        name = re.sub(r"[^A-Za-z0-9._-]+", "_", key) + ".json"
        path = self.data_dir / sub / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        self.files[key] = {"path": path.relative_to(self.data_dir.parent).as_posix(),
                           "sha256": sha256(raw), "private": private, "kind": kind,
                           "request": request}
        return raw


def snapshot(chain, store, label, height, pools):
    """Every archival read for one block. Keys: '<label>/...'."""
    def q(key, request, private=False):
        store.put(f"{label}/{key}", fetch(chain, request), private, request)

    q("account/treasury", account_request(TREASURY, height))
    q("account/payments", account_request(PAYMENTS, height))
    for pool in pools:
        q(f"staked/{pool}", call_request(pool, "get_account_staked_balance",
                                         {"account_id": TREASURY}, height))
        q(f"unstaked/{pool}", call_request(pool, "get_account_unstaked_balance",
                                           {"account_id": TREASURY}, height))
    for who, acct in (("treasury", TREASURY), ("payments", PAYMENTS)):
        q(f"usdc/{who}", call_request(USDC, "ft_balance_of", {"account_id": acct}, height))
        q(f"intents/{who}", call_request(INTENTS, "mt_batch_balance_of",
                                         {"account_id": acct, "token_ids": MT_TOKENS}, height))
    i = 0
    while True:
        req = call_request(TREASURY, "get_proposals",
                           {"from_index": i, "limit": PROPOSAL_PAGE}, height)
        raw = store.put(f"{label}/proposals/{i:05d}", fetch(chain, req), True, req)
        page = value_of(raw) or []
        if len(page) < PROPOSAL_PAGE:
            break
        i += PROPOSAL_PAGE


def mt_pages(store, account, get=stakers.http_get, wait=stakers.PAGE_WAIT, reuse_dir=None):
    """All NearBlocks multi-token pages for an account (private: counterparties)."""
    cursor, n = None, 1
    while True:
        key = f"nearblocks/mt_{account}/page_{n:03d}"
        cached = reuse_dir / (re.sub(r"[^A-Za-z0-9._-]+", "_", key) + ".json") \
            if reuse_dir else None
        q = {"limit": 100}
        if cursor:
            q["next"] = cursor
        url = MT_URL.format(a=account) + "?" + urllib.parse.urlencode(q)
        if cached is not None and cached.exists():
            raw = cached.read_bytes()
        else:
            if n > 1:
                time.sleep(wait)
            raw = get(url)
            print(f"  NearBlocks mt-txns page {n}", flush=True)
        store.put(key, raw, True, {"url": url}, kind="nearblocks")
        doc = json.loads(raw)
        rows = mt_rows_raw(doc)
        cursor = stakers.next_cursor(doc)
        if not cursor or not rows:
            break
        n += 1


# ---------------------------------------------------------------- parsing

def mt_rows_raw(doc):
    if isinstance(doc, dict):
        for k in ("data", "txns", "mt_txns"):
            if isinstance(doc.get(k), list):
                return doc[k]
    return doc if isinstance(doc, list) else []


def mt_row(r, account):
    """Normalized multi-token row, or None if it is not a movement of `account`."""
    try:
        block = r.get("block") or {}
        height = int(block.get("block_height") or r["block_height"])
        ts = block.get("block_timestamp") or r.get("block_timestamp")
        token = str(r["token_id"]).removeprefix("nep141:")
        delta = int(r["delta_amount"])
        tx = r["transaction_hash"]
    except (KeyError, TypeError, ValueError) as e:
        raise SystemExit(f"Unexpected NearBlocks mt-txns row ({e}); keys: {sorted(r)}") from None
    affected = r.get("affected_account_id")
    if affected is not None and affected != account:
        return None
    return {"height": height, "ts": int(ts) if ts else None, "token": token,
            "delta": delta, "tx": tx, "receipt": r.get("receipt_id"),
            "event": r.get("event_index")}


def unique_rows(rows):
    """Drop rows seen twice (overlapping pages). Two equal movements in one
    transaction are different rows: they differ in receipt or event index."""
    seen, out = set(), []
    for r in rows:
        k = (r["tx"], r.get("receipt"), r.get("event"), r["token"], r["delta"])
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out


def swaps_from_rows(rows):
    """wNEAR -> stablecoin swaps: one transaction with wNEAR out and USDC or USDT in."""
    by_tx = {}
    for r in rows:
        t = by_tx.setdefault(r["tx"], {"tx": r["tx"], "height": r["height"], "ts": r["ts"],
                                        "wnear": 0, "usdc": 0, "usdt": 0, "other": 0})
        t["height"] = max(t["height"], r["height"])
        if r["token"] == WNEAR:
            t["wnear"] += r["delta"]
        elif r["token"] in STABLES:
            t[STABLES[r["token"]]] += r["delta"]
        else:
            t["other"] += 1
    return sorted((t for t in by_tx.values()
                   if t["wnear"] < 0 and (t["usdc"] > 0 or t["usdt"] > 0)),
                  key=lambda t: t["height"])


def category(acct, pools):
    if acct == PAYMENTS:
        return "owner payments account"
    if acct == TREASURY:
        return "owner itself"
    if acct in pools:
        return "staking pool"
    if acct in (WNEAR, USDC):
        return "token contract"
    if acct == INTENTS:
        return "intents.near"
    if re.fullmatch(r"[0-9a-f]{64}", acct):
        return "implicit account"
    return "named account"


def public_name(acct, pools):
    """Infrastructure and the owner's own accounts by name; anyone else as a hash."""
    cat = category(acct, pools)
    return acct if cat in ("owner payments account", "owner itself", "staking pool",
                           "token contract", "intents.near") else tag(acct)


def decode_args(b64):
    try:
        return json.loads(base64.b64decode(b64 or "").decode() or "{}")
    except (ValueError, UnicodeDecodeError):
        return None


def pools_from(proposals):
    found = set(KNOWN_POOLS)
    for p in proposals:
        fc = (p.get("kind") or {}).get("FunctionCall") if isinstance(p.get("kind"), dict) else None
        if fc and any(a.get("method_name") in POOL_METHODS for a in fc.get("actions", [])):
            found.add(fc["receiver_id"])
    return sorted(found)


def record(p, pools):
    """A proposal as a public record (no names of anyone outside infrastructure)."""
    kind = p.get("kind")
    rec = {"id": p["id"], "submission_time_utc": lw.iso(int(p["submission_time"]))
           if p.get("submission_time") else None}
    if isinstance(kind, dict) and "Transfer" in kind:
        t = kind["Transfer"]
        token = t.get("token_id") or ""
        rec.update({"kind": "Transfer",
                    "token": "NEAR" if token in ("", "near") else
                             "USDC" if token == USDC else "wNEAR" if token == WNEAR else tag(token),
                    "amount_raw": str(t["amount"]),
                    "recipient": public_name(t["receiver_id"], pools),
                    "recipient_category": category(t["receiver_id"], pools)})
    elif isinstance(kind, dict) and "FunctionCall" in kind:
        fc = kind["FunctionCall"]
        calls = []
        for a in fc.get("actions", []):
            args = decode_args(a.get("args"))
            c = {"method": a.get("method_name"), "deposit_raw": str(a.get("deposit") or "0")}
            if isinstance(args, dict) and "amount" in args:
                c["amount_raw"] = str(args["amount"])
            if isinstance(args, dict) and "receiver_id" in args:
                c["to"] = public_name(args["receiver_id"], pools)
                c["to_category"] = category(args["receiver_id"], pools)
            calls.append(c)
        rec.update({"kind": "FunctionCall", "receiver": public_name(fc["receiver_id"], pools),
                    "receiver_category": category(fc["receiver_id"], pools), "calls": calls})
    else:
        rec["kind"] = kind if isinstance(kind, str) else next(iter(kind or {"Other": 0}))
    return rec


def approved_between(start_props, end_props):
    start = {p["id"]: p.get("status") for p in start_props}
    return [p for p in end_props
            if p.get("status") == "Approved" and start.get(p["id"]) != "Approved"]


def flows(records):
    """Totals of a list of approved proposal records."""
    out = {"approved_proposals": len(records),
           "near_transferred_out": 0, "near_to_payments_account": 0,
           "near_to_others": 0, "near_out_recipients_other": set(),
           "usdc_transferred_out": 0, "wnear_transferred_out": 0,
           "unstaked": 0, "unstake_all_calls": 0, "staked": 0,
           "withdraw_calls": 0, "deposits_to_non_pools": 0, "other_calls": {}}
    for r in records:
        if r["kind"] == "Transfer":
            amt = int(r["amount_raw"])
            if r["token"] == "NEAR":
                out["near_transferred_out"] += amt
                if r["recipient_category"] == "owner payments account":
                    out["near_to_payments_account"] += amt
                else:
                    out["near_to_others"] += amt
                    out["near_out_recipients_other"].add(r["recipient"])
            elif r["token"] == "USDC":
                out["usdc_transferred_out"] += amt
            elif r["token"] == "wNEAR":
                out["wnear_transferred_out"] += amt
        elif r["kind"] == "FunctionCall":
            pool = r["receiver_category"] == "staking pool"
            for c in r["calls"]:
                m, dep = c["method"], int(c["deposit_raw"])
                if pool and m == "unstake":
                    out["unstaked"] += int(c.get("amount_raw") or 0)
                elif pool and m == "unstake_all":
                    out["unstake_all_calls"] += 1
                elif pool and m in ("deposit_and_stake", "deposit"):
                    out["staked"] += dep
                elif pool and m == "stake":
                    out["staked"] += int(c.get("amount_raw") or 0)
                elif pool and m in ("withdraw", "withdraw_all"):
                    out["withdraw_calls"] += 1
                else:
                    if not pool:
                        out["deposits_to_non_pools"] += dep
                    if r["receiver"] == USDC and m == "ft_transfer":
                        out["usdc_transferred_out"] += int(c.get("amount_raw") or 0)
                    key = f"{r['receiver_category']}:{m}"
                    out["other_calls"][key] = out["other_calls"].get(key, 0) + 1
    out["near_out_recipients_other"] = len(out["near_out_recipients_other"])
    return out


def positions(files_value, label, pools):
    """NEAR/USDC holdings of the owner and its payments account at one block."""
    def v(key):
        return files_value(f"{label}/{key}")

    acct_t, acct_p = v("account/treasury"), v("account/payments")
    pos = {"owner_liquid": int(acct_t["amount"]) if acct_t else 0,
           "payments_liquid": int(acct_p["amount"]) if acct_p else 0,
           "pools": {}}
    staked_total = 0
    for pool in pools:
        s, u = v(f"staked/{pool}"), v(f"unstaked/{pool}")
        s, u = int(s or 0), int(u or 0)
        pos["pools"][pool] = {"staked": s, "unstaked": u}
        staked_total += s + u
    pos["owner_in_pools"] = staked_total
    pos["owner_total_near"] = pos["owner_liquid"] + staked_total
    for who in ("treasury", "payments"):
        pos[f"{who}_usdc"] = int(v(f"usdc/{who}") or 0)
        mt = [int(x) for x in (v(f"intents/{who}") or ["0"] * len(MT_TOKENS))]
        pos[f"{who}_intents_wnear"] = mt[0]
        pos[f"{who}_intents_usdc"] = mt[1] + mt[2]
        pos[f"{who}_intents_usdt"] = mt[3] + mt[4]
    return pos


def fmt_positions(pos):
    out = {}
    for k, val in pos.items():
        if k == "pools":
            out[k] = {p: {a: near(b) for a, b in d.items()} for p, d in val.items()}
        elif "usdc" in k or "usdt" in k:  # both 6 decimals
            out[k] = usdc(val)
        else:
            out[k] = near(val)
    return out


# ---------------------------------------------------------------- build

def build(root, files, meta):
    """Everything computed from the saved files. Used by run() and --verify."""
    def raw(key):
        return (root / files[key]["path"]).read_bytes()

    missing = set()

    def val(key):
        v = value_of(raw(key))
        if v is None:
            missing.add(key)  # account or contract absent at that block, or a contract error
        return v

    def header(h):
        return lw_header(raw(f"block/{h}"))

    def proposals(label):
        props = []
        for key in sorted(k for k in files if k.startswith(f"{label}/proposals/")):
            props += val(key) or []
        return props

    end_props = proposals("end")
    pools = meta["pools"]
    assert pools == pools_from(end_props), "pool list does not match the proposals"

    rows = []
    for key in sorted(k for k in files if k.startswith(f"nearblocks/mt_{PAYMENTS}/")):
        for r in mt_rows_raw(json.loads(raw(key))):
            n = mt_row(r, PAYMENTS)
            if n is not None:
                rows.append(n)
    all_swaps = swaps_from_rows(unique_rows(rows))

    end_h = meta["end_block"]
    windows = {}
    for name, label in (("since_stake_dao", "stake_dao_start"), ("year_2026", "y2026_start")):
        start_h = meta[f"{label}_block"]
        recs = [record(p, pools) for p in approved_between(proposals(label), end_props)]
        f = flows(recs)
        p0, p1 = positions(val, label, pools), positions(val, "end", pools)
        change = p1["owner_total_near"] - p0["owner_total_near"]
        sw = [s for s in all_swaps if start_h < s["height"] <= end_h]
        given = -sum(s["wnear"] for s in sw)
        got_usdc = sum(max(s["usdc"], 0) for s in sw)
        got_usdt = sum(max(s["usdt"], 0) for s in sw)
        got = got_usdc + got_usdt
        windows[name] = {
            "start_block": start_h, "start_utc": lw.iso(header(start_h)["timestamp"]),
            "end_block": end_h, "end_utc": lw.iso(header(end_h)["timestamp"]),
            "approved_proposal_ids": [r["id"] for r in recs],
            "owner_flows": {k: (near(v) if k in ("near_transferred_out", "near_to_payments_account",
                                                  "near_to_others", "unstaked", "staked",
                                                  "deposits_to_non_pools", "wnear_transferred_out")
                                else usdc(v) if k == "usdc_transferred_out" else v)
                            for k, v in f.items()},
            "owner_positions_start": fmt_positions(p0),
            "owner_positions_end": fmt_positions(p1),
            "owner_total_near_change": near(change),
            # Holdings change + NEAR sent out = what came in (staking rewards, transfers in).
            "implied_inflows_near": near(change + f["near_transferred_out"]
                                         + f["deposits_to_non_pools"]),
            "payments_swaps_wnear_to_stablecoins": {
                "count": len(sw), "near_given": near(given), "usdc_received": usdc(got_usdc),
                "usdt_received": usdc(got_usdt), "usd_received": usdc(got),
                "mean_price_usd": (f"{float(Fraction(got, USDC_UNIT) / Fraction(given, YOCTO)):.4f}"
                                   if given else None),
                "last_utc": lw.iso(sw[-1]["ts"]) if sw and sw[-1]["ts"] else None,
            },
        }
    swaps_public = [{"tx": s["tx"], "height": s["height"],
                     "utc": lw.iso(s["ts"]) if s["ts"] else None,
                     "near_given": near(-s["wnear"]), "usdc_received": usdc(max(s["usdc"], 0)),
                     "usdt_received": usdc(max(s["usdt"], 0))}
                    for s in all_swaps]
    recs_public = [record(p, pools) for p in approved_between(proposals("y2026_start"), end_props)]
    keys = val("end/access_keys")
    first_stake = first_stake_receipt(root, meta["stake_receipt_pages"])
    return {
        "windows": windows,
        "approved_proposals_2026": recs_public,
        "payments_swaps_all": swaps_public,
        "owner_access_keys_at_end": len((keys or {}).get("keys", [])),
        "stake_dao_first_stake_receipt": first_stake,
        "pools": pools,
        "missing_values": sorted(missing),
    }


def lw_header(raw):
    return json.loads(raw)["result"]["header"]


def first_stake_receipt(root, pages):
    best = None
    for rel in pages:
        for r in stakers.receipts_in(json.loads((root / rel).read_bytes())):
            b = r.get("block") or {}
            h = int(b.get("block_height"))
            ok = (r.get("outcome") or {}).get("status")
            cand = (h, int(b.get("block_timestamp")), bool(ok))
            if best is None or h < best[0]:
                best = cand
    if best is None:
        return None
    return {"height": best[0], "utc": lw.iso(best[1]), "succeeded": best[2]}


# ---------------------------------------------------------------- run

def run(chain, data_dir, window_file, get=stakers.http_get, wait=stakers.PAGE_WAIT):
    win = json.loads(Path(window_file).read_text(encoding="utf-8"))
    end_b = win["boundaries"][-1]
    end_h = end_b["height"]
    store = Store(data_dir)

    pages = sorted((data_dir / "raw" / "nearblocks").glob("stake_receipts_*/page_*.json"))
    if not pages:
        raise SystemExit("No stake.dao receipt pages found: run stakers.py first.")
    latest = max(p.parent for p in pages)
    stake_pages = [p.relative_to(data_dir.parent).as_posix()
                   for p in sorted(latest.glob("page_*.json"))]

    # 1. NearBlocks first (slow, reusable if the run stops later).
    mt_pages(store, PAYMENTS, get=get, wait=wait, reuse_dir=data_dir / "private" / "treasury")

    # 2. Window starts.
    first = first_stake_receipt(data_dir.parent, stake_pages)
    created = first_block_with_account(chain, STAKE_DAO, CREATION_LOW, first["height"])
    final = chain.final_header()
    ref = chain.block(REF_HEIGHT)
    nspb = (final["timestamp"] - ref["timestamp"]) / (final["height"] - ref["height"])
    y_target = lw.midnight_ns(YEAR_START)
    y_hdr, y_prev = lw.find_boundary(chain, y_target,
                                     int(ref["height"] - (ref["timestamp"] - y_target) / nspb))
    for h in (created, y_hdr["height"], y_prev["height"], end_h):
        if chain.block(h) is None:
            raise RuntimeError(f"no block at {h}")
        store.put(f"block/{h}", chain.raw[h], False,
                  {"method": "block", "block_id": h}, kind="block")

    # 3. Proposals at the end block decide which pools to read.
    end_req = call_request(TREASURY, "get_proposals", {"from_index": 0, "limit": 10_000}, end_h)
    probe = value_of(fetch(chain, end_req)) or []
    pools = pools_from(probe)
    for label, h in (("stake_dao_start", created), ("y2026_start", y_hdr["height"]),
                     ("end", end_h)):
        snapshot(chain, store, label, h, pools)
    store.put("end/access_keys", fetch(chain, keys_request(TREASURY, end_h)), False,
              keys_request(TREASURY, end_h))

    meta = {"end_block": end_h, "stake_dao_start_block": created,
            "y2026_start_block": y_hdr["height"], "pools": pools,
            "stake_receipt_pages": stake_pages}
    doc = {
        "measure": "finding 4: NEAR flows of the owner of nearai.pool.near",
        "accounts": {"owner": TREASURY, "payments": PAYMENTS, "pool": NEARAI_POOL},
        "rules": {
            "approved_in_window": "status Approved at the end block, and missing or not "
                                  "Approved at the start block",
            "since_stake_dao_start": "first block where the stake.dao account exists",
            "year_2026_start": "first block whose header timestamp is at or after "
                               "2026-01-01 00:00:00 UTC",
            "end": f"last boundary of {Path(window_file).as_posix()}",
            "swap": "one transaction in which the payments account's wNEAR inside intents.near "
                    "goes down and its USDC (native or bridged from Ethereum) or USDT goes up "
                    "(NearBlocks mt-txns; rows deduplicated by receipt and event index)",
            "privacy": "proposal texts and counterparties stay in data/private/ (not committed); "
                       "recipients outside infrastructure appear as sha256 prefixes",
        },
        "source": {"rpc": chain.url, "nearblocks": MT_URL.format(a=PAYMENTS)},
        "window_file": Path(window_file).as_posix(),
        "meta": meta,
        "raw_files": store.files,
    }
    doc.update(build(data_dir.parent, store.files, meta))
    return doc


# ---------------------------------------------------------------- verify

def verify(path, archival=False, chain=None):
    path = Path(path)
    doc = json.loads(path.read_text(encoding="utf-8"))
    root = path.resolve().parent.parent
    problems, missing_private = [], 0
    for key, f in doc["raw_files"].items():
        p = root / f["path"]
        if not p.exists():
            if f["private"]:
                missing_private += 1
                continue
            problems.append(f"missing raw file {f['path']}")
        elif sha256(p.read_bytes()) != f["sha256"]:
            problems.append(f"sha256 mismatch: {f['path']}")
    if archival:
        chain = chain or lw.Chain()
        for key, f in doc["raw_files"].items():
            if f["kind"] == "nearblocks":
                continue  # an index service: pages change as new rows arrive
            if f["kind"] == "block":
                chain.block(f["request"]["block_id"])
                raw = chain.raw[f["request"]["block_id"]]
            else:
                raw = fetch(chain, f["request"])
            if sha256(raw) != f["sha256"]:
                problems.append(f"archival re-fetch differs: {key}")
    if problems:
        return problems, missing_private
    if missing_private:
        return problems, missing_private  # cannot recompute without them
    again = build(root, doc["raw_files"], doc["meta"])
    for key, value in again.items():
        if doc.get(key) != value:
            problems.append(f"'{key}' does not recompute from the raw files")
    return problems, 0


# ---------------------------------------------------------------- main

def show(doc):
    for name, w in doc["windows"].items():
        f, s = w["owner_flows"], w["payments_swaps_wnear_to_stablecoins"]
        print(f"\n{name}: block {w['start_block']:,} ({w['start_utc'][:16]}) -> "
              f"{w['end_block']:,} ({w['end_utc'][:16]})")
        print(f"  approved proposals {f['approved_proposals']} · unstaked {f['unstaked']} NEAR "
              f"(+{f['unstake_all_calls']} unstake_all) · staked {f['staked']}")
        print(f"  NEAR out {f['near_transferred_out']} (payments account "
              f"{f['near_to_payments_account']}, others {f['near_to_others']} to "
              f"{f['near_out_recipients_other']} accounts) · USDC out {f['usdc_transferred_out']}")
        print(f"  owner NEAR {w['owner_positions_start']['owner_total_near']} -> "
              f"{w['owner_positions_end']['owner_total_near']} (change "
              f"{w['owner_total_near_change']}, implied inflows {w['implied_inflows_near']})")
        print(f"  payments swaps wNEAR->USD: {s['count']} · {s['near_given']} NEAR -> "
              f"{s['usdc_received']} USDC + {s['usdt_received']} USDT · mean "
              f"${s['mean_price_usd']} · last {s['last_utc']}")
    print(f"\nowner access keys at end: {doc['owner_access_keys_at_end']} · first stake receipt "
          f"{doc['stake_dao_first_stake_receipt']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--window", help="locked window file; its last boundary is the end block")
    parser.add_argument("--data-dir", type=Path, default=REPO / "data")
    parser.add_argument("--verify", nargs="?", const=str(REPO / "data" / OUT_NAME), metavar="FILE")
    parser.add_argument("--archival", action="store_true", help="with --verify: re-fetch and compare")
    args = parser.parse_args()
    if args.verify:
        problems, missing = verify(args.verify, archival=args.archival)
        if problems:
            print("FAILED:\n  " + "\n  ".join(problems))
            sys.exit(1)
        if missing:
            print(f"OK for public files; {missing} private raw file(s) absent, so the result "
                  f"was not recomputed{' (archival hashes match)' if args.archival else ''}.")
        else:
            print("OK: sha256 match and every number recomputes from the raw files"
                  + (" · archival re-fetch matches" if args.archival else ""))
        return
    if not args.window:
        parser.error("--window is required")
    chain = lw.Chain()
    doc = run(chain, args.data_dir, args.window)
    out = args.data_dir / OUT_NAME
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
                   newline="\n")
    show(doc)
    print(f"\nSaved {out.relative_to(args.data_dir.parent).as_posix()} "
          f"({chain.calls} archival calls, {chain.rate_limited} rate limited)")
    problems, _ = verify(out)
    if problems:
        print("VERIFY FAILED:\n  " + "\n  ".join(problems))
        sys.exit(1)


if __name__ == "__main__":
    main()
