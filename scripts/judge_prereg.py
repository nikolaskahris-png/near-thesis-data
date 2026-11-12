"""Judge PREREG.md's prediction 2 offline, from the files the daily Action saves. Run by the Action every day.

Prediction 2 (PREREG.md, exact rules): balance of buybacks.multisignature.near = view_account.amount plus its
wNEAR inside intents.near; ratio = (balance at the end block - balance at the start block) / (total_supply in
the end block's header - total_supply in the start block's header); holds if ratio < 0.25.
  start block  the first block at or after 2026-11-01 00:00 UTC: the end block of data/daily/2026-11-01.json
  end block    the first block at or after 2026-11-16 00:00 UTC: the end block of data/daily/2026-11-16.json,
               which the daily Action writes at 00:15 UTC on 16 November
Both blocks, balances and supplies are read with daily.read_point from the saved raw responses, which also
checks that each block is the first of its day. Until the end day's file exists the result is "pending".

Predictions 1 and 3 need calls to stake.dao and NearBlocks at 2026-11-16 12:00 UTC; they are judged by hand.

    python scripts/judge_prereg.py            write data/prereg_judged.json
    python scripts/judge_prereg.py --verify   recompute and compare with the saved file

Offline and read-only: no network, no keys, nothing written on chain.
"""
import argparse
import json
import sys
from datetime import date
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import daily  # noqa: E402
import lock_window as lw  # noqa: E402

REPO = lw.REPO
OUT = "prereg_judged.json"
START_DAY, END_DAY = "2026-11-01", "2026-11-16"
THRESHOLD = Fraction(1, 4)
YOCTO = 10 ** 24


def point(data_root, day):
    doc = json.loads((data_root / "daily" / f"{day}.json").read_text(encoding="utf-8"))
    e = doc["end"]
    if e["date"] != day:
        return None, [f"{day}.json ends on {e['date']}"]
    p, problems = daily.read_point(data_root, date.fromisoformat(day), e["height"], e["previous_height"])
    bal = p[daily.BUYBACKS] + p[daily.BUYBACKS + "@intents"]
    return {"height": e["height"], "utc": p["utc"], "balance_yocto": str(bal),
            "total_supply_yocto": str(p["total_supply"])}, problems


def judge_p2(data_root, end_day=END_DAY):
    data_root = Path(data_root)
    if not (data_root / "daily" / f"{end_day}.json").exists():
        return {"status": "pending", "end_day": end_day}, []
    a, pa = point(data_root, START_DAY)
    b, pb = point(data_root, end_day)
    problems = pa + pb
    if problems:
        return None, problems
    d_bal = int(b["balance_yocto"]) - int(a["balance_yocto"])
    d_sup = int(b["total_supply_yocto"]) - int(a["total_supply_yocto"])
    if d_sup <= 0:
        return None, ["total supply did not grow between the two blocks"]
    r = Fraction(d_bal, d_sup)
    return {"status": "holds" if r < THRESHOLD else "fails", "ratio": f"{float(r):.6f}", "threshold": "0.25",
            "start": a, "end": b, "net_inflow_near": f"{d_bal / YOCTO:.3f}", "new_supply_near": f"{d_sup / YOCTO:.3f}"}, []


def compute(data_root):
    p2, problems = judge_p2(data_root)
    if problems:
        return None, problems
    return {"file": "PREREG.md", "prediction_2": p2,
            "predictions_1_and_3": "judged by hand: they need stake.dao and NearBlocks at 2026-11-16 12:00 UTC"}, []


def dumps(doc):
    return json.dumps(doc, indent=1) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--data", default=str(REPO / "data"))
    a = ap.parse_args()
    data_root = Path(a.data).resolve()
    res, problems = compute(data_root)
    if problems:
        print("FAILED:\n  " + "\n  ".join(problems))
        return 1
    path = data_root / OUT
    if a.verify:
        if not path.exists() or path.read_text(encoding="utf-8") != dumps(res):
            print(f"FAILED: {OUT} differs from the recomputation")
            return 1
    else:
        path.write_text(dumps(res), encoding="utf-8", newline="\n")
    p2 = res["prediction_2"]
    print("Prediction 2: " + (p2["status"] if p2["status"] == "pending" else
                              f"{p2['status']} (ratio {p2['ratio']}, threshold 0.25, blocks {p2['start']['height']}-{p2['end']['height']})"))
    print("OK" if a.verify else f"OK: saved data/{OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
