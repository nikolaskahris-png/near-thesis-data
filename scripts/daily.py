"""Daily snapshot of number 1: how much of new NEAR supply the revenue wallets absorb.

For a date D this measures, between the first block at or after 00:00 UTC of
D-30 and the first block at or after 00:00 UTC of D:

  coverage_buybacks = change in (buybacks.multisignature.near + 1csfundsadmin) / change in supply
  coverage_with_fe  = the same plus fefundsadmin.sputnik-dao.near

Each balance is NEAR on the account (view_account) plus, for buybacks and
fefundsadmin, wNEAR the account holds inside intents.near (mt_balance_of), so
NEAR moved into Intents still counts as held. Staked NEAR is not counted (flagged).

1csfundsadmin is the 1Click fund that collected fees until 23 Apr 2026 and later
moved ~510K NEAR to the buybacks wallet; summing the two cancels such internal
transfers without any hand-entered number. Payments out to third parties are
not added back: this measures NEAR that stayed out of circulation.

Always a 30-day window: total supply only grows at epoch ends (~3.4 per day),
so a single day reads ~78K or ~105K new NEAR depending on how many epochs it holds.

Every input is an archival RPC response saved byte for byte under data/raw/,
listed with its sha256 in data/daily/D.json. data/history.csv is rebuilt from
those files, and --verify recomputes everything from them without network.

Read-only: JSON-RPC "block", "view_account" and one view call. No keys.

Usage:
    python scripts/daily.py                    # today (UTC)
    python scripts/daily.py --date 2026-11-01  # a given date
    python scripts/daily.py --verify           # offline check of every saved day
"""
import argparse
import base64
import csv
import hashlib
import io
import json
import sys
from datetime import date, datetime, timedelta, timezone
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lock_window as lw  # noqa: E402

WINDOW_DAYS = 30
BUYBACKS = "buybacks.multisignature.near"
FEFUNDS = "fefundsadmin.sputnik-dao.near"
ONECLICK = "1csfundsadmin.sputnik-dao.near"  # 1Click fee fund until 23 Apr 2026
ACCOUNTS = (BUYBACKS, FEFUNDS, ONECLICK)
# Accounts declared to hold bought-back NEAR under a published rule (condition (b) of the rating), with
# the date of the declaration. NEAR moved there from the buybacks wallet after that date is still
# kept, not paid out: it counts in "buybacks", so meeting (b) does not look like an outflow. What a
# lock already holds on that date is its baseline and never counts as kept (judge #9, finding 1).
# Declaring is not enough for (b): sealed() reads from the chain whether anyone can still spend from it.
LOCKS = {}
# A lock is sealed at a block when the account has no contract (code_hash of an empty account) and no
# access keys: then no transaction can move its NEAR. That is (b), read from the chain (judge #9, finding 2).
EMPTY_CODE_HASH = "11111111111111111111111111111111"
INTENTS = "intents.near"
WNEAR = "nep141:wrap.near"
YOCTO = 10 ** 24
REPO = Path(__file__).resolve().parent.parent

COLUMNS = [
    "date", "window_start", "block_start", "block_end", "block_end_utc",
    "total_supply_start", "total_supply_end", "new_supply_per_day",
    "buybacks_start", "buybacks_end", "buybacks_per_day",
    "fefunds_start", "fefunds_end", "fefunds_per_day",
    "coverage_buybacks", "coverage_with_fe",
    "max_coverage_defillama", "near_ai_stakers", "near_ai_top_share",  # added 2-4 Nov
    "flags",
]


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def rpc_call(chain, params):
    raw = chain._post({"jsonrpc": "2.0", "id": "daily", "method": "query", "params": params})
    doc = json.loads(raw)
    if "error" in doc:
        raise RuntimeError(f"RPC error: {json.dumps(doc['error'])[:300]}")
    return raw


def snapshot(chain, d, raw_root):
    """Boundary block of date d and every balance at it. Returns (entry, files)."""
    target = lw.midnight_ns(d)
    final = chain.final_header()
    if final["timestamp"] < target + lw.SAFETY_SECONDS * lw.NS:
        raise SystemExit(f"Too early: {d} 00:00 UTC is not final yet.")
    guess = int(final["height"] - (final["timestamp"] - target) / 594_000_000)
    hdr, prev = lw.find_boundary(chain, target, guess)
    assert hdr["timestamp"] >= target > prev["timestamp"] and hdr["prev_hash"] == prev["hash"]
    h = hdr["height"]
    files = {}

    def save(sub, name, raw):
        path = raw_root / sub / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        files[path.relative_to(raw_root.parent.parent).as_posix()] = sha256(raw)

    save("blocks", f"block_{h}.json", chain.raw[h])
    save("blocks", f"block_{prev['height']}.json", chain.raw[prev["height"]])
    for acct in ACCOUNTS + tuple(a for a, since in LOCKS.items() if d >= since):
        save("accounts", f"{h}_{acct}.json",
             rpc_call(chain, {"request_type": "view_account", "block_id": h, "account_id": acct}))
    for acct in (a for a, since in LOCKS.items() if d >= since):
        save("accounts", f"{h}_{acct}_keys.json",
             rpc_call(chain, {"request_type": "view_access_key_list", "block_id": h, "account_id": acct}))
    for acct in (BUYBACKS, FEFUNDS):
        args = base64.b64encode(json.dumps({"account_id": acct, "token_id": WNEAR}).encode()).decode()
        save("accounts", f"{h}_{acct}_intents_wnear.json",
             rpc_call(chain, {"request_type": "call_function", "block_id": h,
                              "account_id": INTENTS, "method_name": "mt_balance_of",
                              "args_base64": args}))
    return {"date": d.isoformat(), "height": h, "previous_height": prev["height"]}, files


def read_point(data_root, d, height, previous_height):
    """Values at one boundary, read only from the saved raw files."""
    raw_root = data_root / "raw"
    blk = json.loads((raw_root / "blocks" / f"block_{height}.json").read_bytes())["result"]["header"]
    prv = json.loads((raw_root / "blocks" / f"block_{previous_height}.json").read_bytes())
    prv = prv["result"]["header"]
    target = lw.midnight_ns(d)
    problems = []
    if not (blk["timestamp"] >= target > prv["timestamp"] and blk["prev_hash"] == prv["hash"]):
        problems.append(f"{d}: block {height} is not the first block of the day")
    point = {"height": height, "utc": lw.iso(blk["timestamp"])[:23] + "Z",
             "total_supply": int(blk["total_supply"])}
    for acct in ACCOUNTS:
        res = json.loads((raw_root / "accounts" / f"{height}_{acct}.json").read_bytes())["result"]
        if res["block_height"] != height:
            problems.append(f"{d}: {acct} read at block {res['block_height']}, not {height}")
        if int(res["locked"]) != 0:
            problems.append(f"{d}: {acct} has staked NEAR, not counted")
        point[acct] = int(res["amount"])
    for acct, since in LOCKS.items():
        point[acct] = None              # not read before the declaration
        if d >= since:
            res = json.loads((raw_root / "accounts" / f"{height}_{acct}.json").read_bytes())["result"]
            keys = json.loads((raw_root / "accounts" / f"{height}_{acct}_keys.json").read_bytes())["result"]
            if res["block_height"] != height or keys["block_height"] != height:
                problems.append(f"{d}: lock {acct} not read at block {height}")
            point[acct] = int(res["amount"])
            point[acct + "@sealed"] = res["code_hash"] == EMPTY_CODE_HASH and not keys["keys"]
    for acct in (BUYBACKS, FEFUNDS):
        res = json.loads((raw_root / "accounts" / f"{height}_{acct}_intents_wnear.json")
                         .read_bytes())["result"]
        wnear = int(json.loads(bytes(res["result"]).decode()))
        point[acct + "@intents"] = wnear
    return point, problems


def near(yocto, places=3):
    q = Fraction(yocto, YOCTO)
    sign = "-" if q < 0 else ""
    q = abs(q)
    whole = int(q)
    frac = round((q - whole) * 10 ** places)
    if frac == 10 ** places:
        whole, frac = whole + 1, 0
    return f"{sign}{whole}.{frac:0{places}d}"


def ratio(num, den, places=6):
    return f"{float(Fraction(num, den)):.{places}f}"


def build_row(day_doc, data_root):
    """Recompute one history row from a day file and its raw responses."""
    base = data_root.parent
    problems = []
    for rel, digest in day_doc["raw_files"].items():
        if sha256((base / rel).read_bytes()) != digest:
            problems.append(f"{day_doc['date']}: sha256 differs for {rel}")
    if problems:
        return None, problems
    s, e = day_doc["start"], day_doc["end"]
    a, p1 = read_point(data_root, date.fromisoformat(s["date"]), s["height"], s["previous_height"])
    b, p2 = read_point(data_root, date.fromisoformat(e["date"]), e["height"], e["previous_height"])
    problems += p1 + p2
    days = (date.fromisoformat(e["date"]) - date.fromisoformat(s["date"])).days
    d_supply = b["total_supply"] - a["total_supply"]
    # A declared lock counts by its change only. If the window starts before the declaration, the lock's
    # balance on the declaration date stands in for its start: NEAR it held then is a baseline, not kept.
    for acct, since in LOCKS.items():
        if a[acct] is None and b[acct] is not None:
            day = data_root / "daily" / f"{since.isoformat()}.json"
            if not day.exists():
                problems.append(f"{e['date']}: lock {acct} declared {since}, but data/daily/{since}.json is missing")
                a[acct] = b[acct]
            else:
                end = json.loads(day.read_text(encoding="utf-8"))["end"]
                at_since, p3 = read_point(data_root, since, end["height"], end["previous_height"])
                problems += p3
                a[acct] = at_since[acct]

    def buy(p):  # NEAR on the accounts plus wNEAR they hold inside intents.near, plus declared locks
        return p[BUYBACKS] + p[BUYBACKS + "@intents"] + p[ONECLICK] + sum(p[a] or 0 for a in LOCKS)

    def fe(p):
        return p[FEFUNDS] + p[FEFUNDS + "@intents"]

    d_buy = buy(b) - buy(a)
    d_fe = fe(b) - fe(a)
    flags = []
    if d_buy < 0:
        flags.append("buybacks_balance_fell")
    if d_fe < 0:
        flags.append("fefunds_balance_fell")
    if b[ONECLICK] != a[ONECLICK]:
        flags.append("1cs_balance_changed")  # still counted; flag shows an internal move
    for acct in (BUYBACKS, FEFUNDS):
        if a[acct + "@intents"] or b[acct + "@intents"]:
            flags.append(f"{acct.split('.')[0]}_holds_wnear_in_intents")
    row = {
        "date": e["date"], "window_start": s["date"],
        "block_start": a["height"], "block_end": b["height"], "block_end_utc": b["utc"],
        "total_supply_start": near(a["total_supply"]), "total_supply_end": near(b["total_supply"]),
        "new_supply_per_day": near(d_supply // days),
        "buybacks_start": near(buy(a)), "buybacks_end": near(buy(b)),
        "buybacks_per_day": near(d_buy // days if d_buy >= 0 else -((-d_buy) // days)),
        "fefunds_start": near(fe(a)), "fefunds_end": near(fe(b)),
        "fefunds_per_day": near(d_fe // days if d_fe >= 0 else -((-d_fe) // days)),
        "coverage_buybacks": ratio(d_buy, d_supply),
        "coverage_with_fe": ratio(d_buy + d_fe, d_supply),
        "max_coverage_defillama": "", "near_ai_stakers": "", "near_ai_top_share": "",
        "flags": ";".join(flags),
    }
    return row, problems


def sealed(data_root):
    """{date: [lock accounts sealed at that day's end block]} from the day files: condition (b) per window,
    read from the chain, and never before the block where it became true."""
    out = {}
    for path in sorted((data_root / "daily").glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        e = doc["end"]
        d = date.fromisoformat(e["date"])
        if not any(d >= since for since in LOCKS.values()):
            out[doc["date"]] = []
            continue
        point, _ = read_point(data_root, d, e["height"], e["previous_height"])
        out[doc["date"]] = sorted(a for a in LOCKS if point.get(a + "@sealed"))
    return out


def history_rows(data_root):
    rows, problems = [], []
    for path in sorted((data_root / "daily").glob("*.json")):
        row, p = build_row(json.loads(path.read_text(encoding="utf-8")), data_root)
        problems += p
        if row:
            rows.append(row)
    return rows, problems


def history_text(rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def write_history(data_root):
    rows, problems = history_rows(data_root)
    (data_root / "history.csv").write_text(history_text(rows), encoding="utf-8", newline="")
    return rows, problems


def verify_history(data_root):
    """Recompute every row from the day files and raw responses, and compare with the committed
    history.csv byte for byte. Nothing is written: a row edited by hand is a failure."""
    rows, problems = history_rows(data_root)
    path = data_root / "history.csv"
    if not path.exists():
        return rows, problems + ["history.csv is missing"]
    saved = path.read_bytes().decode("utf-8")
    again = history_text(rows)
    if saved != again:
        old, new = saved.splitlines(), again.splitlines()
        diff = [f"{i + 1}" for i in range(max(len(old), len(new)))
                if (old[i] if i < len(old) else None) != (new[i] if i < len(new) else None)]
        problems.append(f"history.csv differs from the rows recomputed from data/daily/ "
                        f"(line(s) {', '.join(diff[:5])}{'…' if len(diff) > 5 else ''})")
    return rows, problems


def run(d, data_root, chain=None):
    chain = chain or lw.Chain()
    raw_root = data_root / "raw"
    start, f1 = snapshot(chain, d - timedelta(days=WINDOW_DAYS), raw_root)
    end, f2 = snapshot(chain, d, raw_root)
    day_doc = {
        "date": d.isoformat(),
        "window_days": WINDOW_DAYS,
        "rule": lw.RULE,
        "source": {"rpc": lw.ARCHIVAL},
        "start": start, "end": end,
        "raw_files": dict(sorted({**f1, **f2}.items())),
    }
    (data_root / "daily").mkdir(parents=True, exist_ok=True)
    path = data_root / "daily" / f"{d.isoformat()}.json"
    path.write_text(json.dumps(day_doc, indent=2) + "\n", encoding="utf-8", newline="\n")
    rows, problems = write_history(data_root)
    return day_doc, rows, problems, chain.calls


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--date", type=date.fromisoformat,
                        help="YYYY-MM-DD (default: today in UTC)")
    parser.add_argument("--data-dir", type=Path, default=REPO / "data")
    parser.add_argument("--verify", action="store_true", help="offline check of every saved day")
    args = parser.parse_args()
    data_root = args.data_dir.resolve()

    if args.verify:
        rows, problems = verify_history(data_root)
        if problems:
            print("\n".join(problems))
            print(f"FAILED: {len(problems)} problem(s)")
            return 1
        print(f"OK: {len(rows)} day(s) recomputed from raw responses, sha256 all match, history.csv identical")
        return 0

    d = args.date or datetime.now(timezone.utc).date()
    _doc, rows, problems, calls = run(d, data_root)
    row = next(r for r in rows if r["date"] == d.isoformat())
    print(f"{d}: blocks {row['block_start']} -> {row['block_end']}, {calls} RPC calls")
    print(f"  new supply/day {row['new_supply_per_day']}  buybacks/day {row['buybacks_per_day']}"
          f"  fefunds/day {row['fefunds_per_day']}")
    print(f"  coverage buybacks {row['coverage_buybacks']}  with fefunds {row['coverage_with_fe']}"
          f"  flags: {row['flags'] or '-'}")
    if problems:
        print("\n".join(problems))
        print("FAILED")
        return 1
    print("Offline check: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
