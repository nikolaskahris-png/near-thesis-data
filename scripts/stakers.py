"""Number 3: how widely NEAR AI staking is spread, measured on chain.

1. Account list: every account that ever called `stake` on stake.dao, from the
   NearBlocks receipts API (pages saved under data/raw/nearblocks/).
2. For each date, at the first block at or after 00:00 UTC: every account's
   position in the "NEAR AI Cloud Credits" farm (get_farm_position), the farm
   total (get_farm_pool) and the NEAR AI Agents locks (get_locks), all from the
   archival RPC and saved byte for byte under data/raw/stakedao/.
3. Completeness: the positions must add up exactly to total_farm_shares,
   otherwise the run fails. Who had entered by a block is decided by the
   position at that block (none = not yet), so the list may safely contain
   accounts that came later.

Read-only. No keys.

Usage:
    python scripts/stakers.py --dates 2026-11-01
    python scripts/stakers.py --dates 2026-08-01,2026-08-15,2026-09-01
    python scripts/stakers.py --verify
"""
import argparse
import base64
import hashlib
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lock_window as lw  # noqa: E402

CONTRACT = "stake.dao"
FARM_PRODUCT = "prod_33Kp14MGUJa2QA"
FARM_PRICE = "price_QzmSvxbZqdbV0XbG6VD6KkbB"
NEARBLOCKS = "https://api.nearblocks.io/v3/accounts/stake.dao/receipts"
PAGE_WAIT = 12  # seconds between NearBlocks calls without a key
LOCK_PAGE = 100
YOCTO = 10 ** 24
YEAR_S = 31_557_600  # 365.25 days
DAY_S = 86_400
REPO = Path(__file__).resolve().parent.parent


def sha256(data):
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------- account list

def http_get(url):
    headers = {"User-Agent": lw.USER_AGENT, "Accept": "application/json"}
    for attempt in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers),
                                        timeout=40) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < 5:
                time.sleep(30 * (attempt + 1))
                continue
            raise RuntimeError(f"HTTP {e.code} from {url}") from None
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if attempt < 5:
                time.sleep(10 * (attempt + 1))
                continue
            raise RuntimeError(f"cannot reach {url}: {e}") from None
    raise RuntimeError("unreachable")


def receipts_in(doc):
    """All dicts with a predecessor_account_id anywhere in a NearBlocks page."""
    found = []

    def walk(x):
        if isinstance(x, dict):
            if "predecessor_account_id" in x:
                found.append(x)
            else:
                for v in x.values():
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(doc)
    return found


def next_cursor(doc):
    meta = doc.get("meta") if isinstance(doc, dict) else None
    return (meta or {}).get("next_page") or None


def discover(data_root, tag, get=http_get, wait=PAGE_WAIT):
    """Fetch (or reuse) every page of stake receipts. Returns the account file path."""
    page_dir = data_root / "raw" / "nearblocks" / f"stake_receipts_{tag}"
    page_dir.mkdir(parents=True, exist_ok=True)
    cursor, n, pages = None, 1, {}
    while True:
        path = page_dir / f"page_{n:03d}.json"
        if not path.exists():
            q = {"method": "stake", "limit": 100}
            if cursor:
                q["next"] = cursor
            if n > 1:
                time.sleep(wait)
            path.write_bytes(get(NEARBLOCKS + "?" + urllib.parse.urlencode(q)))
            print(f"  NearBlocks page {n}", flush=True)
        raw = path.read_bytes()
        doc = json.loads(raw)
        if not receipts_in(doc) and n == 1:
            raise SystemExit(f"No receipts found in {path}: the API format may have changed.")
        pages[path.relative_to(data_root.parent).as_posix()] = sha256(raw)
        cursor = next_cursor(doc)
        if not cursor or not receipts_in(doc):
            break
        n += 1
    accounts = accounts_from_pages(data_root, pages)
    out = data_root / "stakers" / f"accounts_{tag}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"source": NEARBLOCKS + "?method=stake", "pages": pages,
                               "accounts": accounts}, indent=2) + "\n",
                   encoding="utf-8", newline="\n")
    return out


def accounts_from_pages(data_root, pages):
    accts = set()
    for rel in pages:
        for r in receipts_in(json.loads((data_root.parent / rel).read_bytes())):
            accts.add(r["predecessor_account_id"])
    return sorted(accts)


# ---------------------------------------------------------------- positions

def panic_message(doc):
    """The contract's own error (e.g. a panic), or None if the call ran normally."""
    if "error" in doc:
        cause = (doc["error"].get("cause") or {})
        if cause.get("name") == "CONTRACT_EXECUTION_ERROR":
            return json.dumps(cause.get("info") or doc["error"].get("data"))[:300]
        return None
    res = doc.get("result") or {}
    if "error" in res and "result" not in res:
        return str(res["error"])[:300]
    return None


def view(chain, height, method, args, allow_panic=False):
    body = {"jsonrpc": "2.0", "id": "stakers", "method": "query",
            "params": {"request_type": "call_function", "block_id": height,
                       "account_id": CONTRACT, "method_name": method,
                       "args_base64": base64.b64encode(json.dumps(args).encode()).decode()}}
    raw = chain._post(body)
    doc = json.loads(raw)
    if panic_message(doc) is not None:
        if allow_panic:
            return raw
        raise RuntimeError(f"{method} at {height}: contract error {panic_message(doc)}")
    if "error" in doc:
        raise RuntimeError(f"{method} at {height}: {json.dumps(doc['error'])[:300]}")
    return raw


def decode(raw):
    return json.loads(bytes(json.loads(raw)["result"]["result"]).decode())


def snapshot(chain, d, accounts_file, data_root):
    accounts = json.loads(accounts_file.read_text(encoding="utf-8"))["accounts"]
    target = lw.midnight_ns(d)
    final = chain.final_header()
    if final["timestamp"] < target + lw.SAFETY_SECONDS * lw.NS:
        raise SystemExit(f"Too early: {d} 00:00 UTC is not final yet.")
    guess = int(final["height"] - (final["timestamp"] - target) / 594_000_000)
    hdr, prev = lw.find_boundary(chain, target, guess)
    assert hdr["timestamp"] >= target > prev["timestamp"] and hdr["prev_hash"] == prev["hash"]
    h = hdr["height"]
    files = {}

    def save(rel, raw):
        path = data_root / "raw" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        files[path.relative_to(data_root.parent).as_posix()] = sha256(raw)

    def saved(rel):
        """Reuse a response already saved for this block (an interrupted run)."""
        path = data_root / "raw" / rel
        if path.exists():
            files[path.relative_to(data_root.parent).as_posix()] = sha256(path.read_bytes())
            return True
        return False

    save(f"blocks/block_{h}.json", chain.raw[h])
    save(f"blocks/block_{prev['height']}.json", chain.raw[prev["height"]])
    save(f"stakedao/{h}/farm_pool.json", view(chain, h, "get_farm_pool", {"price_id": FARM_PRICE}))
    for i, acct in enumerate(accounts, 1):
        rel = f"stakedao/{h}/position_{acct}.json"
        if not saved(rel):
            save(rel, view(chain, h, "get_farm_position",
                           {"account_id": acct, "product_id": FARM_PRODUCT}, allow_panic=True))
        if i % 50 == 0:
            print(f"  {d}: {i}/{len(accounts)} positions", flush=True)
    start = 0
    while True:
        raw = view(chain, h, "get_locks", {"from_index": start, "limit": LOCK_PAGE})
        save(f"stakedao/{h}/locks_{start:05d}.json", raw)
        if len(decode(raw)) < LOCK_PAGE:
            break
        start += LOCK_PAGE
    doc = {"date": d.isoformat(), "height": h, "previous_height": prev["height"],
           "accounts_file": accounts_file.relative_to(data_root.parent).as_posix(),
           "farm_product": FARM_PRODUCT, "farm_price": FARM_PRICE,
           "raw_files": dict(sorted(files.items()))}
    out = data_root / "stakers" / f"{d.isoformat()}.json"
    out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8", newline="\n")
    return out


# ---------------------------------------------------------------- numbers

def amount(pos):
    for key in ("staked_near_amount", "amount", "shares"):
        if key in pos:
            return int(pos[key])
    raise KeyError(f"no amount field in position: {sorted(pos)}")


def median(values):
    v = sorted(values)
    if not v:
        return Fraction(0)
    m = len(v) // 2
    return Fraction(v[m]) if len(v) % 2 else Fraction(v[m - 1] + v[m], 2)


def near(x, places=3):
    q = Fraction(x) / YOCTO
    return f"{float(q):.{places}f}"


def dec6(fr):
    scaled = round(Fraction(fr) * 10 ** 6)
    return f"{scaled // 10 ** 6}.{scaled % 10 ** 6:06d}"


def share(part, total):
    return f"{float(Fraction(part, total)):.6f}" if total else ""


def compute(snap_file, data_root):
    """All number-3 statistics from one saved snapshot. Returns (stats, problems)."""
    snap = json.loads(Path(snap_file).read_text(encoding="utf-8"))
    base = data_root.parent
    problems = []
    for rel, digest in snap["raw_files"].items():
        if sha256((base / rel).read_bytes()) != digest:
            problems.append(f"{snap['date']}: sha256 differs for {rel}")
    if problems:
        return None, problems
    h = snap["height"]
    blk = json.loads((data_root / "raw" / "blocks" / f"block_{h}.json").read_bytes())
    prv = json.loads((data_root / "raw" / "blocks" / f"block_{snap['previous_height']}.json")
                     .read_bytes())
    blk, prv = blk["result"]["header"], prv["result"]["header"]
    target = lw.midnight_ns(date.fromisoformat(snap["date"]))
    if not (blk["timestamp"] >= target > prv["timestamp"] and blk["prev_hash"] == prv["hash"]):
        problems.append(f"{snap['date']}: block {h} is not the first block of the day")

    accounts = json.loads((base / snap["accounts_file"]).read_text(encoding="utf-8"))["accounts"]
    pool = decode((data_root / "raw" / "stakedao" / str(h) / "farm_pool.json").read_bytes())
    total = int(pool["total_farm_shares"])
    active, ever, closed = {}, 0, 0
    panics = {}
    for acct in accounts:
        raw = (data_root / "raw" / "stakedao" / str(h) / f"position_{acct}.json").read_bytes()
        msg = panic_message(json.loads(raw))
        if msg is not None:  # contract refused: no position; the sum check below confirms it
            panics[acct] = msg
            continue
        pos = decode(raw)
        if pos is None:
            continue
        ever += 1
        amt = amount(pos)
        if pos.get("status", "Active") == "Active" and amt > 0:
            active[acct] = amt
        else:
            closed += 1
    s = sum(active.values())
    if s != total:
        problems.append(f"{snap['date']}: positions add up to {s}, farm total is {total} "
                        f"(difference {total - s}): account list incomplete")

    locks = []
    for path in sorted((data_root / "raw" / "stakedao" / str(h)).glob("locks_*.json")):
        locks += decode(path.read_bytes())
    lock_status = {}
    lock_accounts, active_lock_accounts, past_end = set(), set(), 0
    lock_near, active_lock_near, active_in_term, at_50 = 0, 0, 0, 0
    lock_days = []
    for lk in locks:
        st = str(lk.get("status", "unknown"))
        amt = int(lk.get("amount_near", 0))
        lock_status[st] = lock_status.get(st, 0) + 1
        lock_near += amt
        at_50 += amt == 50 * YOCTO
        ended = bool(int(lk.get("end_ns", 0))) and int(lk["end_ns"]) < blk["timestamp"]
        if amt > 0:
            lock_accounts.add(lk["account_id"])
            if st == "Active":
                active_lock_accounts.add(lk["account_id"])
        if st == "Active":
            active_lock_near += amt
            active_in_term += not ended
        past_end += ended
        if int(lk.get("start_ns", 0)) and int(lk.get("end_ns", 0)):
            lock_days.append(Fraction(int(lk["end_ns"]) - int(lk["start_ns"]), 86400 * 10 ** 9))

    ranked = sorted(active.values(), reverse=True)
    rest = ranked[10:]
    stats = {
        "date": snap["date"], "block": h, "block_utc": lw.iso(blk["timestamp"])[:23] + "Z",
        "farm_total_near": near(total), "positions_sum_near": near(s),
        "stakers_active": len(active), "stakers_ever": ever, "stakers_left": closed,
        "left_share_of_ever": share(closed, ever),
        "largest_near": near(ranked[0]) if ranked else "0",
        "largest_share": share(ranked[0] if ranked else 0, total),
        "largest_account": max(active, key=active.get) if active else "",
        "top3_share": share(sum(ranked[:3]), total), "top10_share": share(sum(ranked[:10]), total),
        "outside_top10_accounts": len(rest), "outside_top10_near": near(sum(rest)),
        "outside_top10_median_near": near(median(rest)),
        "median_all_near": near(median(ranked)),
        "mean_all_near": near(Fraction(s, len(ranked))) if ranked else "0",
        "accounts_under_100_near": sum(1 for v in ranked if v < 100 * YOCTO),
        "accounts_100k_or_more": sum(1 for v in ranked if v >= 100_000 * YOCTO),
        "agents_locks": len(locks), "agents_locks_by_status": lock_status,
        "agents_lock_accounts": len(lock_accounts),
        "agents_locks_past_end": past_end,
        "agents_locks_active": lock_status.get("Active", 0),
        "agents_locks_unlock_requested": lock_status.get("UnlockRequested", 0),
        "agents_locks_active_within_term": active_in_term,
        "agents_locks_near": near(lock_near),
        "agents_locks_active_near": near(active_lock_near),
        "agents_active_lock_near_vs_farm": share(active_lock_near, total),
        "agents_locks_at_50_near": at_50,
        "agents_lock_days_min": f"{float(min(lock_days)):.2f}" if lock_days else "",
        "agents_lock_days_max": f"{float(max(lock_days)):.2f}" if lock_days else "",
        # Separate line only; prediction 3 counts the farm alone (stakers_active).
        "farm_or_active_lock_accounts": len(set(active) | active_lock_accounts),
        "farm_or_any_lock_accounts": len(set(active) | lock_accounts),
        # finding 6: reward units (24 decimals) per second per staked NEAR (stake.dao types.rs)
        "farm_reward_rate": str(pool.get("reward_rate", "")),
        "farm_units_per_near_year": dec6(Fraction(int(pool["reward_rate"]) * YEAR_S, YOCTO))
        if pool.get("reward_rate") else "",
        "largest_units_per_day": dec6(Fraction(ranked[0] * int(pool["reward_rate"]) * DAY_S,
                                               YOCTO * YOCTO))
        if ranked and pool.get("reward_rate") else "",
        "farm_units_per_day": dec6(Fraction(total * int(pool["reward_rate"]) * DAY_S,
                                            YOCTO * YOCTO)) if pool.get("reward_rate") else "",
        "accounts_without_position_contract_error": len(panics),
        "contract_error_example": next(iter(panics.values()), ""),
    }
    return stats, problems


def verify_all(data_root):
    results, problems = [], []
    for acc in sorted((data_root / "stakers").glob("accounts_*.json")):
        doc = json.loads(acc.read_text(encoding="utf-8"))
        for rel, digest in doc["pages"].items():
            if sha256((data_root.parent / rel).read_bytes()) != digest:
                problems.append(f"{acc.name}: sha256 differs for {rel}")
        if accounts_from_pages(data_root, doc["pages"]) != doc["accounts"]:
            problems.append(f"{acc.name}: account list differs from the saved pages")
    for snap in sorted((data_root / "stakers").glob("20*.json")):
        stats, p = compute(snap, data_root)
        problems += p
        if stats:
            results.append(stats)
    return results, problems


def show(stats):
    print(f"{stats['date']} block {stats['block']}: active {stats['stakers_active']}, "
          f"ever {stats['stakers_ever']}, left {stats['stakers_left']} "
          f"({stats['left_share_of_ever']}), largest {stats['largest_share']}, "
          f"top10 {stats['top10_share']}, outside top10 {stats['outside_top10_accounts']} "
          f"accounts / {stats['outside_top10_near']} NEAR / median "
          f"{stats['outside_top10_median_near']}, locks {stats['agents_locks']} "
          f"{stats['agents_locks_by_status']}, contract errors "
          f"{stats['accounts_without_position_contract_error']}")
    if stats["contract_error_example"]:
        print(f"  example contract error: {stats['contract_error_example']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dates", help="comma-separated YYYY-MM-DD")
    parser.add_argument("--accounts-tag", help="reuse/make account list with this tag "
                        "(default: the last date)")
    parser.add_argument("--data-dir", type=Path, default=REPO / "data")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    data_root = args.data_dir.resolve()

    if args.verify:
        results, problems = verify_all(data_root)
        for st in results:
            show(st)
        if problems:
            print("\n".join(problems))
            print(f"FAILED: {len(problems)} problem(s)")
            return 1
        print(f"OK: {len(results)} snapshot(s) recomputed from raw responses")
        return 0

    if not args.dates:
        parser.error("give --dates or --verify")
    dates = sorted(date.fromisoformat(x.strip()) for x in args.dates.split(","))
    tag = args.accounts_tag or dates[-1].isoformat()
    print(f"Account list ({tag})", flush=True)
    accounts_file = discover(data_root, tag)
    n = len(json.loads(accounts_file.read_text(encoding="utf-8"))["accounts"])
    print(f"  {n} accounts ever called stake", flush=True)
    chain = lw.Chain()
    failed = False
    for d in dates:
        snap = snapshot(chain, d, accounts_file, data_root)
        stats, problems = compute(snap, data_root)
        show(stats)
        if problems:
            print("\n".join(problems))
            failed = True
    print(f"{chain.calls} RPC calls")
    print("FAILED" if failed else "Offline check: OK")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
