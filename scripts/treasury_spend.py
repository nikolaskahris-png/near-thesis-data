"""What treasury.near receives and keeps, month by month in 2026, from balances and block headers.

treasury.near is the protocol treasury account. Two steps, run separately:

  Step A (default): prove the rule "the treasury receives exactly 1/10 of the NEAR minted at each
  epoch start". For every epoch start in data/burn.json (the locked window), the treasury's balance
  is read at the start block and at the block before it; the difference must be a tenth of what
  burn.py found minted there, up to integer rounding (minted - 10 * reward between 0 and 9 yocto).
  Anything else (another movement of the treasury in that block) is reported, not hidden.
  Also reads the balance at the window's two ends: the change minus the rewards is what came in or
  went out some other way.

  Step B (--months): the same for each month 1 Jan -> 1 Nov 2026 (first block at or after 00:00 UTC
  of the 1st). Per month: minted (all epoch starts found by search on epoch_id, as in burn.py),
  treasury_in = minted / 10, the balance change, and other_net = balance change - treasury_in
  (negative = net outflow; it is net of any other inflows in the month). Amounts and months only:
  nothing about recipients or purposes.

Block responses of step B are kept as slim files (the fields used, plus the sha256 of the full
response, so any block can be re-fetched and compared). Read-only: JSON-RPC "block" and
"view_account". No keys.

Usage:
    python scripts/treasury_spend.py              step A (about 200 calls)
    python scripts/treasury_spend.py --months     step B (about 3,000 calls; resumes if cut)
    python scripts/treasury_spend.py --verify     offline, from the saved files
"""
import argparse
import hashlib
import json
import sys
from datetime import date
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import burn  # noqa: E402
import daily  # noqa: E402
import lock_window as lw  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
OUT_NAME = "treasury_spend.json"
ACCOUNT = "treasury.near"
RULE_DIVISOR = 10
MAX_ROUNDING = RULE_DIVISOR - 1  # minted - 10 * reward, in yocto
RULE_TEXT = ("at each epoch start the treasury receives minted // 10 "
             "(minted - 10 * reward in 0..9 yocto)")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------- files

def acct_rel(data_root, height):
    p = data_root / "raw" / "treasury_spend" / "accounts" / f"{height}_{ACCOUNT}.json"
    return p, p.relative_to(data_root.parent).as_posix()


def fetch_account(chain, data_root, height, files):
    """Save (or reuse) the view_account response at a height; register it in `files`."""
    path, rel = acct_rel(data_root, height)
    if path.exists():
        raw = path.read_bytes()
    else:
        raw = daily.rpc_call(chain, {"request_type": "view_account", "block_id": height,
                                     "account_id": ACCOUNT})
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    files[rel] = sha256(raw)
    return raw


def amount_of(raw, height):
    res = json.loads(raw)["result"]
    if res["block_height"] != height:
        raise ValueError(f"balance read at block {res['block_height']}, not {height}")
    return int(res["amount"]), int(res["locked"])


def preload(chain, data_root):
    """Blocks already saved by earlier scripts are not fetched again."""
    for sub in ("burn", "blocks"):
        for p in (data_root / "raw" / sub).glob("block_*.json"):
            raw = p.read_bytes()
            h = json.loads(raw)["result"]["header"]
            chain.raw[h["height"]] = raw
            chain.headers[h["height"]] = h


def slim(raw):
    res = json.loads(raw)["result"]
    h = res["header"]
    return {"height": h["height"], "hash": h["hash"], "prev_height": h["prev_height"],
            "prev_hash": h["prev_hash"], "epoch_id": h["epoch_id"],
            "next_epoch_id": h["next_epoch_id"], "total_supply": h["total_supply"],
            "timestamp": h["timestamp"], "burnt_new": str(burn.burnt_new(res)),
            "raw_sha256": sha256(raw)}


# ---------------------------------------------------------------- computation (also --verify)

def check_rule(doc, data_root, rd, problems):
    """Step A. rd: raw files by relative path."""
    base = data_root.parent
    bdoc = json.loads((base / doc["burn_file"]).read_text(encoding="utf-8"))
    blocks, bproblems = burn.load_blocks(bdoc, data_root)
    if bproblems:
        problems += [f"burn.json: {x}" for x in bproblems]
        return None
    sup = lambda w: int(w["header"]["total_supply"])  # noqa: E731
    exact = off = max_dev = 0
    rewards = 0
    for k, ep in enumerate(bdoc["epochs"]):
        s, p = blocks[ep["start"]], blocks[ep["previous"]]
        minted = sup(s) - sup(p) + burn.burnt_new(s)
        try:
            a_s = amount_of(rd[acct_rel(data_root, ep["start"])[1]], ep["start"])
            a_p = amount_of(rd[acct_rel(data_root, ep["previous"])[1]], ep["previous"])
        except (KeyError, ValueError) as e:
            problems.append(f"epoch {k}: balance not available ({e})")
            continue
        if a_s[1] or a_p[1]:
            problems.append(f"epoch {k}: locked balance is not zero")
        reward = a_s[0] - a_p[0]
        dev = minted - RULE_DIVISOR * reward
        rewards += reward
        if dev == 0:
            exact += 1
        if not 0 <= dev <= MAX_ROUNDING:
            off += 1
            problems.append(f"epoch {k} (start {ep['start']}): treasury received {reward} yocto, "
                            f"minted {minted}: minted - 10 * received = {dev}")
        max_dev = max(max_dev, abs(dev))
    res = {"epochs": len(bdoc["epochs"]), "exact": exact, "outside_rule": off,
           "max_deviation_yocto": str(max_dev), "rewards_near": daily.near(rewards)}
    win = json.loads((base / bdoc["window_file"]).read_text(encoding="utf-8"))
    h0, h1 = win["boundaries"][0]["height"], win["boundaries"][-1]["height"]
    try:
        a0 = amount_of(rd[acct_rel(data_root, h0)[1]], h0)[0]
        a1 = amount_of(rd[acct_rel(data_root, h1)[1]], h1)[0]
    except (KeyError, ValueError) as e:
        problems.append(f"window balances not available ({e})")
        return res, None
    change = a1 - a0
    window = {"balance_change_near": daily.near(change), "rewards_near": daily.near(rewards),
              "other_net_near": daily.near(change - rewards)}
    cm = data_root / "control_map.json"
    if cm.exists():
        cmd = json.loads(cm.read_text(encoding="utf-8"))
        blk = cmd.get("block")
        if (blk.get("height") if isinstance(blk, dict) else blk) == h1:
            ref = cmd["links"]["protocol_treasury"]["balance_change_near"]
            window["equals_control_map"] = ref == window["balance_change_near"]
            if ref != window["balance_change_near"]:
                problems.append(f"window balance change {window['balance_change_near']} differs "
                                f"from the control map's {ref}")
    return res, window


def check_month(m, data_root, rd, problems):
    label = f"{m['start']['date']}..{m['end']['date']}"
    fa = json.loads(rd[m["blocks_file"]])
    blocks = {int(k): v for k, v in fa["blocks"].items()}
    a, pa = blocks.get(m["start"]["height"]), blocks.get(m["start"]["previous_height"])
    b, pb = blocks.get(m["end"]["height"]), blocks.get(m["end"]["previous_height"])
    if None in (a, pa, b, pb):
        problems.append(f"{label}: boundary blocks not saved")
        return None
    for blk, prv, d in ((a, pa, m["start"]["date"]), (b, pb, m["end"]["date"])):
        target = lw.midnight_ns(date.fromisoformat(d))
        if not (blk["timestamp"] >= target > prv["timestamp"] and blk["prev_hash"] == prv["hash"]):
            problems.append(f"{label}: {blk['height']} is not the first block of {d}")
    minted, prev_epoch, last_h, starts = 0, a["epoch_id"], a["height"], []
    for k, ep in enumerate(fa["epochs"]):
        s, p = blocks.get(ep["start"]), blocks.get(ep["previous"])
        if s is None or p is None:
            problems.append(f"{label}: epoch {k} blocks not saved")
            continue
        if not a["height"] < s["height"] <= b["height"] or s["height"] <= last_h:
            problems.append(f"{label}: epoch {k} start {s['height']} outside the month or out of order")
        if s["prev_height"] != p["height"] or s["prev_hash"] != p["hash"]:
            problems.append(f"{label}: epoch {k}: {s['height']} does not follow {p['height']}")
        if p["epoch_id"] != prev_epoch:
            problems.append(f"{label}: epoch {k}: the block before the start is not in the previous epoch")
        if p["next_epoch_id"] != s["epoch_id"] or p["epoch_id"] == s["epoch_id"]:
            problems.append(f"{label}: epoch {k}: {s['height']} is not the first block of its epoch")
        got = int(s["total_supply"]) - int(p["total_supply"]) + int(s["burnt_new"])
        if got <= 0:
            problems.append(f"{label}: epoch {k}: nothing minted at {s['height']}")
        minted += got
        starts.append((s["height"], got))
        prev_epoch, last_h = s["epoch_id"], s["height"]
    if prev_epoch != b["epoch_id"]:
        problems.append(f"{label}: the last epoch start is not in the month's final epoch")
    try:
        amt_a, lock_a = amount_of(rd[acct_rel(data_root, a["height"])[1]], a["height"])
        amt_b, lock_b = amount_of(rd[acct_rel(data_root, b["height"])[1]], b["height"])
    except (KeyError, ValueError) as e:
        problems.append(f"{label}: balance not available ({e})")
        return None
    change = amt_b - amt_a
    tin = Fraction(minted, RULE_DIVISOR)
    row = {"start": m["start"]["date"], "end": m["end"]["date"], "epochs": len(fa["epochs"]),
           "minted_near": daily.near(minted), "treasury_in_near": daily.near(tin),
           "balance_start_near": daily.near(amt_a), "balance_end_near": daily.near(amt_b),
           "balance_change_near": daily.near(change),
           "other_net_near": daily.near(change - tin),
           "kept_share": daily.ratio(change, tin), "locked_nonzero": bool(lock_a or lock_b)}
    return row, minted, change, tin, starts, b["height"]


def compute(doc, data_root):
    """Everything from the saved files. Returns (results, problems)."""
    base = data_root.parent
    problems, rd = [], {}
    for rel, digest in doc["raw_files"].items():
        p = base / rel
        if not p.exists():
            problems.append(f"missing {rel}")
        else:
            raw = p.read_bytes()
            if sha256(raw) != digest:
                problems.append(f"sha256 differs for {rel}")
            else:
                rd[rel] = raw
    if problems:
        return None, problems
    out = check_rule(doc, data_root, rd, problems)
    res = {"rule": None, "window": None, "months": [], "total": None}
    if out is None:
        return res, problems
    res["rule"], res["window"] = out
    bdoc = json.loads((base / doc["burn_file"]).read_text(encoding="utf-8"))
    win = json.loads((base / bdoc["window_file"]).read_text(encoding="utf-8"))
    w0, w1 = win["boundaries"][0]["height"], win["boundaries"][-1]["height"]
    tot_minted = tot_change = 0
    tot_in = Fraction(0)
    prev_end = None
    for m in doc.get("months", []):
        got = check_month(m, data_root, rd, problems)
        if got is None:
            continue
        row, minted, change, tin, starts, end_h = got
        if prev_end is not None and m["start"]["height"] != prev_end:
            problems.append(f"{row['start']}: does not start where the previous month ended")
        prev_end = m["end"]["height"]
        if end_h == w1:
            in_window = sum(x for h, x in starts if h > w0)
            if daily.near(in_window) != bdoc["results"]["minted_near"]:
                problems.append(f"{row['start']}: minted in the locked window {daily.near(in_window)} "
                                f"differs from burn.json's {bdoc['results']['minted_near']}")
        res["months"].append(row)
        tot_minted += minted
        tot_change += change
        tot_in += tin
    if res["months"]:
        res["total"] = {
            "from": res["months"][0]["start"], "to": res["months"][-1]["end"],
            "minted_near": daily.near(tot_minted), "treasury_in_near": daily.near(tot_in),
            "balance_change_near": daily.near(tot_change),
            "other_net_near": daily.near(tot_change - tot_in),
            "kept_share": daily.ratio(tot_change, tot_in)}
    return res, problems


# ---------------------------------------------------------------- measuring

def new_doc():
    return {"measure": "what treasury.near receives and keeps, from balances and block headers",
            "account": ACCOUNT, "rule": RULE_TEXT, "burn_file": "data/" + burn.OUT_NAME,
            "raw_files": {}, "months": [], "results": {}}


def save(doc, data_root):
    doc["raw_files"] = dict(sorted(doc["raw_files"].items()))
    (data_root / OUT_NAME).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8",
                                      newline="\n")


def run_rule(chain, data_root):
    """Step A. Returns (doc, problems)."""
    bdoc = json.loads((data_root / burn.OUT_NAME).read_text(encoding="utf-8"))
    win = json.loads((data_root.parent / bdoc["window_file"]).read_text(encoding="utf-8"))
    heights = {win["boundaries"][0]["height"], win["boundaries"][-1]["height"]}
    for ep in bdoc["epochs"]:
        heights |= {ep["start"], ep["previous"]}
    doc = new_doc()
    for i, h in enumerate(sorted(heights), 1):
        fetch_account(chain, data_root, h, doc["raw_files"])
        if i % 50 == 0:
            print(f"  {i} of {len(heights)} balances", flush=True)
    res, problems = compute(doc, data_root)
    doc["results"] = res
    save(doc, data_root)
    return doc, problems


def boundary(chain, d, guess, step=2000):
    hdr, prev = lw.find_boundary(chain, lw.midnight_ns(d), guess, step)
    return {"date": d.isoformat(), "height": hdr["height"], "previous_height": prev["height"]}


def run_months(chain, data_root, spec, step=2000):
    """Step B. spec: [(date, height guess)] in order. Resumes: finished months are kept."""
    path = data_root / OUT_NAME
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc["results"]["rule"]["outside_rule"]:
        raise SystemExit("step A found epochs outside the 1/10 rule: stop and redesign")
    preload(chain, data_root)
    done = {(m["start"]["date"], m["end"]["date"]) for m in doc["months"]}
    points = {}
    for (d0, g0), (d1, g1) in zip(spec, spec[1:]):
        if (d0.isoformat(), d1.isoformat()) in done:
            continue
        before = chain.calls
        for d, g in ((d0, g0), (d1, g1)):
            if d not in points:
                points[d] = boundary(chain, d, g, step)
        a, b = points[d0], points[d1]
        cur = (a["height"], chain.block(a["height"]))
        end_epoch = chain.block(b["height"])["epoch_id"]
        epochs, guess = [], None
        while cur[1]["epoch_id"] != end_epoch:
            start = burn.find_next_start(chain, cur, guess)
            epochs.append({"start": start[0], "previous": start[1]["prev_height"]})
            cur, guess = start, start[0] + burn.EPOCH_LENGTH
        need = {a["height"], a["previous_height"], b["height"], b["previous_height"]}
        for e in epochs:
            need |= {e["start"], e["previous"]}
        blocks = {}
        for h in sorted(need):
            if h not in chain.raw:
                chain.block(h)
            blocks[str(h)] = slim(chain.raw[h])
        rel = f"data/raw/treasury_spend/blocks_{d0.isoformat()}_{d1.isoformat()}.json"
        text = json.dumps({"note": "slim copies of block responses: the fields used, and the "
                           "sha256 of the full response", "blocks": blocks, "epochs": epochs},
                          indent=1) + "\n"
        out = data_root.parent / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(text.encode("utf-8"))
        doc["raw_files"][rel] = sha256(text.encode("utf-8"))
        for h in (a["height"], b["height"]):
            fetch_account(chain, data_root, h, doc["raw_files"])
        doc["months"].append({"start": a, "end": b, "blocks_file": rel})
        res, problems = compute(doc, data_root)
        doc["results"] = res
        save(doc, data_root)
        row = res["months"][-1]
        print(f"{d0}  {len(epochs)} epochs  in {row['treasury_in_near']}  change "
              f"{row['balance_change_near']}  other {row['other_net_near']}  "
              f"({chain.calls - before} calls)", flush=True)
        if problems:
            return doc, problems
    return doc, compute(doc, data_root)[1]


def real_spec(data_root):
    """1st of each month from 1 Jan to 1 Nov 2026, with a height guess for each."""
    flows = json.loads((data_root / "treasury_flows.json").read_text(encoding="utf-8"))
    cov = json.loads((data_root / "coverage_monthly.json").read_text(encoding="utf-8"))
    known = {date(2026, 1, 1): flows["meta"]["y2026_start_block"]}
    known.update({date.fromisoformat(b["date"]): b["height"] for b in cov["boundaries"]})
    spec = []
    for month in range(1, 12):
        d = date(2026, month, 1)
        if d not in known:  # between two known points: by days
            lo = max(x for x in known if x < d)
            hi = min(x for x in known if x > d)
            g = known[lo] + (known[hi] - known[lo]) * (d - lo).days // (hi - lo).days
        else:
            g = known[d]
        spec.append((d, g))
    return spec


def show(res):
    r, w = res["rule"], res["window"]
    print(f"rule: {r['exact']} of {r['epochs']} epoch starts exact, {r['outside_rule']} outside "
          f"(max deviation {r['max_deviation_yocto']} yocto); rewards {r['rewards_near']} NEAR")
    if w:
        print(f"window: balance change {w['balance_change_near']}, rewards {w['rewards_near']}, "
              f"other net {w['other_net_near']}")
    for m in res["months"]:
        print(f"  {m['start']}: in {m['treasury_in_near']:>12}  change {m['balance_change_near']:>13}"
              f"  other net {m['other_net_near']:>13}  kept {m['kept_share']}")
    if res["total"]:
        t = res["total"]
        print(f"total {t['from']} -> {t['to']}: in {t['treasury_in_near']}, change "
              f"{t['balance_change_near']}, other net {t['other_net_near']}, kept {t['kept_share']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-dir", type=Path, default=REPO / "data")
    parser.add_argument("--months", action="store_true", help="step B")
    parser.add_argument("--verify", nargs="?", const="", metavar="FILE")
    args = parser.parse_args()
    data_root = args.data_dir.resolve()
    if args.verify is not None:
        path = Path(args.verify) if args.verify else data_root / OUT_NAME
        doc = json.loads(path.read_text(encoding="utf-8"))
        res, problems = compute(doc, data_root)
        if not problems and res != doc["results"]:
            problems.append("results do not recompute from the saved files")
        if problems:
            print("FAILED:\n  " + "\n  ".join(problems))
            return 1
        print(f"OK: {res['rule']['epochs']} epoch starts and {len(res['months'])} months recompute "
              f"from the saved files")
        return 0
    chain = lw.Chain()
    if args.months:
        doc, problems = run_months(chain, data_root, real_spec(data_root))
    else:
        doc, problems = run_rule(chain, data_root)
    show(doc["results"])
    print(f"{chain.calls} RPC calls")
    if problems:
        print("FAILED:\n  " + "\n  ".join(problems))
        return 1
    print("Offline check: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
