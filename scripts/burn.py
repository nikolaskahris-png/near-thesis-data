"""Gas burnt and gross issuance in the measurement window, exactly, from block headers.

NEAR's `total_supply` changes in two ways (nearcore 2.14.0, core/primitives/src/block.rs):

    total_supply(block) = total_supply(previous block) + minted - burnt of the block's new chunks

`minted` is nonzero only in the first block of an epoch; `burnt` is the sum of `balance_burnt`
over the chunks the block includes (height_included == height). So between two blocks of the
same epoch the supply only falls, by exactly the burnt amount, and across the window

    minted (gross issuance) = sum over epoch starts of (supply(start) - supply(previous) + burnt(start))
    burnt                   = minted - (supply(end) - supply(start of window))

No sampling: every epoch start in the window is found by search on `epoch_id` and read, about
three archival calls per epoch. Two blocks per epoch start are saved (the start and the block
before it), plus five blocks inside epochs where the rule above is checked to the yocto.

Uses the locked window (data/window_*.json). Read-only: JSON-RPC "block". No keys, and no call
that lists validators.

The result is net of the gas burnt, as the supply is: "burnt" here is what number 1 already
excludes from issuance. `hsp027_extra_burn_max_*` is an upper bound on what removing the 30%
gas rebate to contracts (HSP-027, protocol version 87) would add: balance_burnt is counted
after the rebate (nearcore runtime/runtime/src/lib.rs, tx_burnt_amount -= receiver_reward), so
the rebate is at most 3/7 of what is burnt today (equal only if all gas were function calls).

Usage:
    python scripts/burn.py
    python scripts/burn.py --verify [data/burn.json]     offline, from the saved blocks
"""
import argparse
import csv
import hashlib
import json
import sys
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import daily  # noqa: E402
import lock_window as lw  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
OUT_NAME = "burn.json"
EPOCH_LENGTH = 43_200  # blocks; only a first guess, every start is proved from epoch_id
IDENTITY_CHECKS = 5
MAX_INFLATION = Fraction(1, 40)
YEAR_DAYS = Fraction(36525, 100)
HSP027_BOUND = Fraction(3, 7)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------- search

def existing_at(chain, h, limit=200):
    """First existing block at height h or above, as (height, header)."""
    for x in range(h, h + limit):
        hdr = chain.block(x)
        if hdr is not None:
            return x, hdr
    raise RuntimeError(f"no block between heights {h} and {h + limit}")


def find_next_start(chain, lo, guess=None):
    """lo = (height, header) of a block in epoch e. Returns (height, header) of the first block
    of the next epoch: the block whose epoch_id differs and whose previous block is still in e."""
    e = lo[1]["epoch_id"]
    probe = existing_at(chain, guess if guess is not None else lo[0] + 1)
    if probe[1]["epoch_id"] == e:
        lo, step = probe, 1
        while True:
            probe = existing_at(chain, lo[0] + step)
            if probe[1]["epoch_id"] != e:
                hi = probe
                break
            lo, step = probe, step * 2
    else:
        hi, step = probe, 1
        while True:
            h = hi[0] - step
            if h <= lo[0]:
                break
            probe = existing_at(chain, h)
            step *= 2
            if probe[0] >= hi[0]:
                continue
            if probe[1]["epoch_id"] == e:
                lo = probe
                break
            hi = probe
    while True:
        prev_h = hi[1]["prev_height"]
        prev = chain.block(prev_h)
        if prev["epoch_id"] == e:
            return hi
        hi = (prev_h, prev)
        if hi[0] <= lo[0]:
            raise RuntimeError("epoch search left its bracket")
        probe = existing_at(chain, (lo[0] + hi[0]) // 2)
        if probe[0] < hi[0]:
            if probe[1]["epoch_id"] == e:
                lo = probe
            else:
                hi = probe


def burnt_new(block_result):
    """Sum of balance_burnt over the chunks this block includes (yocto)."""
    h = block_result["header"]["height"]
    return sum(int(c["balance_burnt"]) for c in block_result["chunks"] if c["height_included"] == h)


# ---------------------------------------------------------------- computation (also --verify)

def load_blocks(doc, data_root):
    base = data_root.parent
    blocks, problems = {}, []
    for rel, digest in doc["raw_files"].items():
        p = base / rel
        if not p.exists():
            problems.append(f"missing {rel}")
            continue
        raw = p.read_bytes()
        if sha256(raw) != digest:
            problems.append(f"sha256 differs for {rel}")
            continue
        blocks[json.loads(raw)["result"]["header"]["height"]] = json.loads(raw)["result"]
    return blocks, problems


def history_value(data_root, date_str):
    p = data_root / "history.csv"
    if not p.exists():
        return None
    with p.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["date"] == date_str:
                return row["new_supply_per_day"]
    return None


def compute(doc, data_root):
    """Everything from the saved blocks. Returns (results, problems)."""
    blocks, problems = load_blocks(doc, data_root)
    if problems:
        return None, problems
    win = json.loads((data_root.parent / doc["window_file"]).read_text(encoding="utf-8"))
    b0, b1 = win["boundaries"][0], win["boundaries"][-1]
    days = win["window"]["days"]
    try:
        w0, w1 = blocks[b0["height"]], blocks[b1["height"]]
    except KeyError as e:
        return None, [f"window boundary block {e} not saved"]
    for b, w in ((b0, w0), (b1, w1)):
        if w["header"]["hash"] != b["hash"]:
            problems.append(f"block {b['height']} is not the locked boundary (hash differs)")
    sup = lambda w: int(w["header"]["total_supply"])  # noqa: E731

    minted, prev_epoch = 0, w0["header"]["epoch_id"]
    last_h = b0["height"]
    for k, ep in enumerate(doc["epochs"]):
        try:
            s, p = blocks[ep["start"]]["header"], blocks[ep["previous"]]["header"]
        except KeyError as e:
            problems.append(f"epoch {k}: block {e} not saved")
            continue
        s_res, p_res = blocks[ep["start"]], blocks[ep["previous"]]
        if not b0["height"] < s["height"] <= b1["height"] or s["height"] <= last_h:
            problems.append(f"epoch {k}: start {s['height']} outside the window or out of order")
        if s["prev_height"] != p["height"]:
            problems.append(f"epoch {k}: {s['height']} does not follow {p['height']}")
        if p["epoch_id"] != prev_epoch:
            problems.append(f"epoch {k}: the block before the start is not in the previous epoch")
        if p["next_epoch_id"] != s["epoch_id"] or p["epoch_id"] == s["epoch_id"]:
            problems.append(f"epoch {k}: {s['height']} is not the first block of its epoch")
        m = sup(s_res) - sup(p_res) + burnt_new(s_res)
        if m <= 0:
            problems.append(f"epoch {k}: nothing minted at {s['height']}")
        minted += m
        prev_epoch, last_h = s["epoch_id"], s["height"]
    if prev_epoch != w1["header"]["epoch_id"]:
        problems.append("the last epoch start is not in the window's final epoch")

    for c in doc["identity"]:
        try:
            r, q = blocks[c["height"]], blocks[c["previous"]]
        except KeyError as e:
            problems.append(f"identity check: block {e} not saved")
            continue
        if r["header"]["epoch_id"] != q["header"]["epoch_id"] or r["header"]["prev_height"] != q["header"]["height"]:
            problems.append(f"identity check at {c['height']}: not two blocks of one epoch")
        elif sup(q) - sup(r) != burnt_new(r):
            problems.append(f"identity check at {c['height']}: supply fell by {sup(q) - sup(r)}, "
                            f"chunks burnt {burnt_new(r)}")
    if len(doc["identity"]) < IDENTITY_CHECKS:
        problems.append("fewer identity checks than required")

    delta = sup(w1) - sup(w0)
    burnt = minted - delta
    if burnt < 0:
        problems.append("negative burn")
    max_mint = Fraction(sup(w0)) * MAX_INFLATION / YEAR_DAYS
    res = {
        "epochs": len(doc["epochs"]), "days": days,
        "minted_near": daily.near(minted), "burnt_near": daily.near(burnt),
        "net_near": daily.near(delta),
        "minted_near_per_day": daily.near(minted // days),
        "burnt_near_per_day": daily.near(burnt // days),
        "net_near_per_day": daily.near(delta // days),
        "burnt_share_of_minted": daily.ratio(burnt, minted),
        "max_mint_near_per_day": daily.near(max_mint),
        "minted_share_of_max": daily.ratio(Fraction(minted, days), max_mint),
        "hsp027_extra_burn_max_near_per_day": daily.near(Fraction(burnt, days) * HSP027_BOUND),
        "hsp027_extra_max_share_of_minted": daily.ratio(burnt * HSP027_BOUND, minted),
    }
    hist = history_value(data_root, b1["date"])
    if hist is None:
        problems.append(f"no row for {b1['date']} in history.csv to compare the net issuance with")
    elif hist != res["net_near_per_day"]:
        problems.append(f"net issuance per day {res['net_near_per_day']} differs from "
                        f"number 1's {hist}")
    res["net_equals_number_1"] = hist == res["net_near_per_day"]
    cm = data_root / "control_map.json"
    res["treasury_share_of_minted"] = ""
    if cm.exists():
        cmd = json.loads(cm.read_text(encoding="utf-8"))
        blk = cmd.get("block")
        if (blk.get("height") if isinstance(blk, dict) else blk) == b1["height"]:
            t = Decimal(cmd["links"]["protocol_treasury"]["balance_change_near"])
            res["treasury_share_of_minted"] = f"{float(t / Decimal(minted) * 10 ** 24):.6f}"
    return res, problems


# ---------------------------------------------------------------- measuring

def pick_identity_blocks(chain, w0_h, w1_h):
    """IDENTITY_CHECKS blocks at equal spacing inside the window, each with the block before it
    in the same epoch (a block that starts an epoch is moved on by one)."""
    out = []
    for i in range(1, IDENTITY_CHECKS + 1):
        h = existing_at(chain, w0_h + (w1_h - w0_h) * i // (IDENTITY_CHECKS + 1))[0]
        while True:
            hdr = chain.block(h)
            prev = chain.block(hdr["prev_height"])
            if prev["epoch_id"] == hdr["epoch_id"]:
                out.append({"height": h, "previous": hdr["prev_height"]})
                break
            h = existing_at(chain, h + 1)[0]
    return out


def run(chain, window_path, data_root):
    window_path = Path(window_path)
    win = json.loads(window_path.read_text(encoding="utf-8"))
    b0, b1 = win["boundaries"][0], win["boundaries"][-1]
    cur = (b0["height"], chain.block(b0["height"]))
    last = (b1["height"], chain.block(b1["height"]))
    epochs, guess = [], None
    while cur[1]["epoch_id"] != last[1]["epoch_id"]:
        start = find_next_start(chain, cur, guess)
        epochs.append({"start": start[0], "previous": start[1]["prev_height"]})
        if len(epochs) % 10 == 0:
            print(f"  {len(epochs)} epoch starts, height {start[0]}", flush=True)
        cur, guess = start, start[0] + EPOCH_LENGTH
    identity = pick_identity_blocks(chain, b0["height"], b1["height"])
    need = {b0["height"], b1["height"]}
    for e in epochs:
        need |= {e["start"], e["previous"]}
    for c in identity:
        need |= {c["height"], c["previous"]}
    raw_dir = data_root / "raw" / "burn"
    raw_dir.mkdir(parents=True, exist_ok=True)
    files = {}
    for h in sorted(need):
        path = raw_dir / f"block_{h}.json"
        path.write_bytes(chain.raw[h])
        files[path.relative_to(data_root.parent).as_posix()] = sha256(chain.raw[h])
    doc = {
        "measure": "gross issuance and gas burnt in the locked window, from epoch starts",
        "window_file": window_path.resolve().relative_to(data_root.parent).as_posix(),
        "rule": "total_supply(block) = total_supply(previous) + minted - burnt of the new chunks",
        "epoch_length_guess": EPOCH_LENGTH,
        "epochs": epochs, "identity": identity, "raw_files": dict(sorted(files.items())),
    }
    res, problems = compute(doc, data_root)
    doc["results"] = res
    (data_root / OUT_NAME).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8",
                                      newline="\n")
    return doc, problems


def show(res):
    print(f"{res['epochs']} epoch starts in {res['days']} days: minted {res['minted_near_per_day']} "
          f"NEAR a day, burnt {res['burnt_near_per_day']} ({res['burnt_share_of_minted']} of minted), "
          f"net {res['net_near_per_day']} (equals number 1: {res['net_equals_number_1']})")
    print(f"  reference cap {res['max_mint_near_per_day']} a day; minted is {res['minted_share_of_max']} "
          f"of it · HSP-027 would add at most {res['hsp027_extra_burn_max_near_per_day']} a day "
          f"({res['hsp027_extra_max_share_of_minted']} of minted)")
    if res["treasury_share_of_minted"]:
        print(f"  treasury.near: {res['treasury_share_of_minted']} of minted")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--window", type=Path,
                        default=REPO / "data" / "window_2026-10-02_2026-11-01.json")
    parser.add_argument("--data-dir", type=Path, default=REPO / "data")
    parser.add_argument("--verify", nargs="?", const=str(REPO / "data" / OUT_NAME), metavar="FILE")
    args = parser.parse_args()
    data_root = args.data_dir.resolve()
    if args.verify:
        doc = json.loads(Path(args.verify).read_text(encoding="utf-8"))
        res, problems = compute(doc, data_root)
        if not problems and res != doc["results"]:
            problems.append("results do not recompute from the saved blocks")
        if problems:
            print("FAILED:\n  " + "\n  ".join(problems))
            return 1
        print(f"OK: {res['epochs']} epoch starts and {len(doc['identity'])} identity checks recompute "
              f"from the saved blocks; net issuance equals number 1")
        return 0
    chain = lw.Chain()
    doc, problems = run(chain, args.window, data_root)
    show(doc["results"])
    print(f"{chain.calls} RPC calls")
    if problems:
        print("FAILED:\n  " + "\n  ".join(problems))
        return 1
    print("Offline check: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
