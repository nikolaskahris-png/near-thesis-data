"""Does the rating depend on the thresholds the author chose? The same rules with other thresholds, offline.

    python scripts/sensitivity.py            # write data/sensitivity.json
    python scripts/sensitivity.py --verify   # recompute and compare

The rules are rating.py's, called as they are (rating.evaluate), on the months backtest.py uses (April to
October 2026, from the same saved files), once for every combination of:

  Avoid test 1 floor     the wallets keep at least 50%, 75% (the rule) or 90% of DefiLlama's revenue
  Avoid test 2 floor     the buybacks keep at least 0.5x, 1x (the rule) or 1.5x April's dollars a day
  Buy growth (a)         +50%, the rule's own figure, or +100% a year
  rule (b)               as on chain (no lock), or assumed met in every month, with treasury.near quiet

The last line is a hypothesis, not a fact: it asks whether anything other than (b) stands between today
and Buy. (a) is judged only at a yearly check from the 1 November 2026 base, so in these months Buy can
only come from coverage of 100% or more.

It also reports where the rating flips (flips): with every other threshold at the rule's value, the lowest
Avoid floor, kept share or dollars, at which any month of the seven becomes Avoid, found by bisection.
"""
import argparse
import json
import sys
from fractions import Fraction
from itertools import product
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import backtest  # noqa: E402
import rating  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
OUT = "sensitivity.json"
KEPT = ("0.50", "0.75", "0.90")
USD = ("0.5", "1", "1.5")
GROWTH = ("0.50", None, "1.00")          # None: the rule's own figure from numbers.json
RULE_B = ("as on chain", "assumed met")


def compute(data_root):
    cov, raws, fetched, files, problems = backtest.inputs(data_root)
    if problems:
        return None, problems
    th0 = rating.thresholds(data_root / "numbers.json")
    hist = [{k: r[k] for k in ("date", "window_start", "buybacks_per_day", "fefunds_per_day",
                               "coverage_buybacks", "new_supply_per_day")} for r in cov["rows"]]
    months = {r["date"]: r["month"] for r in cov["rows"]}
    s = rating.parse(raws)
    stables = rating.treasury_stablecoins(data_root)
    saved = rating.KEPT_SHARE_MIN
    runs = []
    try:
        for kept, usd, growth, rule_b in product(KEPT, USD, GROWTH, RULE_B):
            rating.KEPT_SHARE_MIN = Fraction(kept)
            th = dict(th0)
            th["avoid_usd_per_day"] = str(Fraction(th0["avoid_usd_per_day"]) * Fraction(usd))
            if growth is not None:
                th["growth_without_hsp029"] = growth
            met = rule_b == "assumed met"
            sealed = {r["date"]: (["hypothetical-lock"] if met else []) for r in hist}
            quiet = {r["date"]: "yes" for r in hist} if met else {}
            rows = rating.evaluate(hist, s, th, fetched, sealed, quiet, earlier_of=backtest.previous_month,
                                   stables=stables)
            runs.append({"kept_share_floor": kept, "usd_floor_x_april": usd,
                         "growth_a": growth or th0["growth_without_hsp029"], "rule_b": rule_b,
                         "ratings": {months[r["date"]]: r["rating"] for r in rows},
                         "months_failing_a_test": [months[r["date"]] for r in rows
                                                   if "fail" in (r["test_kept_share"], r["test_usd"])]})
    finally:
        rating.KEPT_SHARE_MIN = saved
    # Where the rating flips: with every other threshold at the rule's value, the lowest Avoid floor at which any
    # month becomes Avoid, found by bisection (a higher floor can only fail more windows), to 0.0001.
    def avoid_months(kept, usd):
        rating.KEPT_SHARE_MIN = kept
        th = dict(th0)
        th["avoid_usd_per_day"] = str(Fraction(th0["avoid_usd_per_day"]) * usd)
        try:
            rows = rating.evaluate(hist, s, th, fetched, {r["date"]: [] for r in hist}, {},
                                   earlier_of=backtest.previous_month, stables=stables)
        finally:
            rating.KEPT_SHARE_MIN = saved
        return [months[r["date"]] for r in rows if r["rating"] == "Avoid"]

    def lowest(lo, hi, fires):
        if not fires(hi):
            return None, []
        while hi - lo > Fraction(1, 10000):
            mid = (lo + hi) / 2
            lo, hi = (lo, mid) if fires(mid) else (mid, hi)
        return hi, fires(hi)
    k_flip, k_months = lowest(Fraction(saved), Fraction(1), lambda x: avoid_months(x, Fraction(1)) or None)
    u_flip, u_months = lowest(Fraction(1), Fraction(10), lambda x: avoid_months(Fraction(saved), x) or None)
    flips = {"note": "with every other threshold at the rule's value; to 0.0001; null if no floor up to the bound flips it",
             "avoid_kept_share_floor_from": None if k_flip is None else f"{float(k_flip):.4f}",
             "avoid_kept_share_months": k_months or [],
             "avoid_usd_floor_x_april_from": None if u_flip is None else f"{float(u_flip):.4f}",
             "avoid_usd_months": u_months or []}
    counts = {k: sum(v == k for run in runs for v in run["ratings"].values()) for k in ("Hold", "Buy", "Avoid")}
    best = max(Fraction(r["coverage_counted"]) for r in rating.evaluate(
        hist, s, th0, fetched, {r["date"]: ["hypothetical-lock"] for r in hist}, {r["date"]: "yes" for r in hist},
        earlier_of=backtest.previous_month, stables=stables) if r["coverage_counted"])
    return {
        "measure": "the rating rules on April-October 2026 under other thresholds",
        "rules": __doc__.split("    python")[0].strip(),
        "inputs_sha256": files,
        "combinations": len(runs),
        "month_ratings": counts,
        "every_month_hold": counts["Hold"] == sum(counts.values()),
        "highest_coverage_counted": f"{float(best):.6f}",
        "flips": flips,
        "runs": runs,
    }, []


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
    print(f"{res['combinations']} combinations x 7 months: {res['month_ratings']}; "
          f"highest coverage counted {float(res['highest_coverage_counted']):.1%}")
    f = res["flips"]
    print(f"Avoid from a kept-share floor of {f['avoid_kept_share_floor_from']} ({', '.join(f['avoid_kept_share_months'])}) "
          f"or a dollar floor of {f['avoid_usd_floor_x_april_from']} x April ({', '.join(f['avoid_usd_months'])})")
    print("OK" if a.verify else f"OK: saved data/{OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
