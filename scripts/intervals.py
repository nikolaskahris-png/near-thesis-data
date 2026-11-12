"""How sure are the two measured daily figures? A block bootstrap over the saved days. Offline, stdlib only.

Daily inflows are lumpy and neighbouring days are not independent, so the days are resampled in blocks of
consecutive days (moving blocks), 10,000 times, with a fixed seed: blocks of 7 days for the 30-day window (a week),
blocks of 3 for the before/after comparison, because the after period has only 13 days and blocks of 7 would leave
just 7 places to start one. The same intervals with blocks of 1, 3, 5 and 7 are saved too (block_sensitivity).
Everything comes from the daily rows in data/private_shift.json; nothing is fetched and nothing else is read.

A permutation test is added for the before/after change: the 38 days are shuffled 100,000 times (own seed) and
split 25/13; p is the share of splits whose change is at least as large, either way, as the one measured. It
assumes the days are exchangeable, which lumpy, autocorrelated inflows are not, so the bootstrap stays the main
result.

  window  2 to 31 October 2026 (the 30 days of the locked window): mean NEAR a day kept by the buybacks wallets,
          and by the buybacks wallets plus the front-end fund. build_numbers.py divides these by the new NEAR a
          day to give the coverage (10.8% and 16.5%) and its interval.
  shift   the change in NEAR a day kept by the three revenue wallets, 27 October to 8 November against
          2 to 26 October (the thesis's "-3%"), and the same for DefiLlama's revenue in NEAR ("-6%").
          The two periods are resampled separately, then compared.

The interval is the 2.5th to 97.5th percentile of the resamples (nearest rank). It says how much the figure could
move had the same weeks come out a little differently; it is not a forecast and it cannot see a change that
happened in the days we did not measure.

Usage:
    python scripts/intervals.py            write data/intervals.json
    python scripts/intervals.py --verify   recompute and compare with the saved file
"""
import argparse
import json
import math
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = "intervals.json"
BLOCK = 7          # the 30-day window
BLOCK_SHIFT = 3    # the before/after comparison
BLOCK_SIZES = (1, 3, 5, 7)
RESAMPLES = 10000
SEED = 20261112
LOW, HIGH = 0.025, 0.975
PERMUTATIONS = 100000
PERM_SEED = 20261113
WINDOW = ("2026-10-02", "2026-10-31")
BEFORE = ("2026-10-02", "2026-10-26")
AFTER = ("2026-10-27", "2026-11-08")


def rows_in(days, span):
    return [r for r in days if span[0] <= r["date"] <= span[1]]


def column(rows, key):
    return [float(r[key]) for r in rows]


def resample_mean(xs, rng, block=BLOCK):
    """Mean of one moving-block resample of xs, the same length as xs."""
    n = len(xs)
    out = []
    while len(out) < n:
        s = rng.randrange(0, n - block + 1)
        out.extend(xs[s:s + block])
    out = out[:n]
    return sum(out) / n


def percentile(sorted_xs, q):
    """Nearest rank, no interpolation."""
    k = min(len(sorted_xs) - 1, max(0, int(q * len(sorted_xs))))
    return sorted_xs[k]


def interval(values):
    s = sorted(values)
    return percentile(s, LOW), percentile(s, HIGH)


def mean_ci(xs, rng, block=BLOCK):
    res = [resample_mean(xs, rng, block) for _ in range(RESAMPLES)]
    lo, hi = interval(res)
    return {"mean": sum(xs) / len(xs), "low": lo, "high": hi, "days": len(xs)}


def change_ci(before, after, rng, block=BLOCK_SHIFT):
    res = []
    for _ in range(RESAMPLES):
        res.append(resample_mean(after, rng, block) / resample_mean(before, rng, block) - 1)
    lo, hi = interval(res)
    point = (sum(after) / len(after)) / (sum(before) / len(before)) - 1
    return {"change": point, "low": lo, "high": hi, "share_below_zero": sum(1 for x in res if x < 0) / len(res),
            "days_before": len(before), "days_after": len(after)}


def permutation_p(before, after, rng, n=PERMUTATIONS):
    """Two-sided: the share of random 25/13 splits of the same days whose |log(after/before)| >= the measured one."""
    allx = before + after
    k = len(after)
    total = sum(allx)
    obs = abs(math.log((sum(after) / k) / (sum(before) / len(before))))
    hits = 0
    for _ in range(n):
        a = sum(rng.sample(allx, k))
        if abs(math.log((a / k) / ((total - a) / (len(allx) - k)))) >= obs - 1e-12:
            hits += 1
    return {"p_two_sided": hits / n, "permutations": n, "seed": PERM_SEED}


def compute(data_root):
    path = Path(data_root) / "private_shift.json"
    if not path.exists():
        return None, ["data/private_shift.json is missing"]
    days = json.loads(path.read_text(encoding="utf-8"))["days"]
    problems = []
    win, bef, aft = rows_in(days, WINDOW), rows_in(days, BEFORE), rows_in(days, AFTER)
    for name, rows, n in (("window", win, 30), ("before", bef, 25), ("after", aft, 13)):
        if len(rows) != n:
            problems.append(f"{name}: {len(rows)} days, expected {n}")
    if problems:
        return None, problems
    rng = random.Random(SEED)   # one stream, drawn in a fixed order
    res = {
        "method": f"moving-block bootstrap, blocks of {BLOCK} consecutive days for the window and {BLOCK_SHIFT} for the "
                  f"before/after change, {RESAMPLES} resamples, seed {SEED}, "
                  f"interval = {LOW:.1%} to {HIGH:.1%} percentile (nearest rank), stdlib only, from the days in "
                  "data/private_shift.json",
        "windows": {"window": list(WINDOW), "before": list(BEFORE), "after": list(AFTER)},
        "window_mean_near_per_day": {
            "buybacks": mean_ci(column(win, "buybacks_near"), rng),
            "buybacks_and_front_end": mean_ci(column(win, "kept_near"), rng),
        },
        "shift": {
            "kept_near": change_ci(column(bef, "kept_near"), column(aft, "kept_near"), rng),
            "revenue_near": change_ci(column(bef, "revenue_near"), column(aft, "revenue_near"), rng),
        },
        "block_sensitivity": [],
    }
    prng = random.Random(PERM_SEED)
    res["permutation"] = {k: permutation_p(column(bef, k), column(aft, k), prng) for k in ("kept_near", "revenue_near")}
    for blk in BLOCK_SIZES:
        cb = mean_ci(column(win, "buybacks_near"), rng, blk)
        ck = change_ci(column(bef, "kept_near"), column(aft, "kept_near"), rng, blk)
        res["block_sensitivity"].append({"block_days": blk, "buybacks_low": cb["low"], "buybacks_high": cb["high"],
                                         "kept_near_change_low": ck["low"], "kept_near_change_high": ck["high"],
                                         "kept_near_share_below_zero": ck["share_below_zero"]})
    return res, []


def round_floats(x):
    if isinstance(x, float):
        return round(x, 6)
    if isinstance(x, dict):
        return {k: round_floats(v) for k, v in x.items()}
    if isinstance(x, list):
        return [round_floats(v) for v in x]
    return x


def dumps(doc):
    return json.dumps(round_floats(doc), indent=1) + "\n"


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
    w = res["window_mean_near_per_day"]
    s = res["shift"]
    print(f"buybacks {w['buybacks']['mean']:.0f} NEAR/day [{w['buybacks']['low']:.0f}, {w['buybacks']['high']:.0f}]; "
          f"with front end {w['buybacks_and_front_end']['mean']:.0f} [{w['buybacks_and_front_end']['low']:.0f}, "
          f"{w['buybacks_and_front_end']['high']:.0f}]")
    for k in ("kept_near", "revenue_near"):
        print(f"{k} change {s[k]['change']:+.1%} [{s[k]['low']:+.1%}, {s[k]['high']:+.1%}], "
              f"{s[k]['share_below_zero']:.0%} of resamples below zero")
    print("OK" if a.verify else f"OK: saved data/{OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
