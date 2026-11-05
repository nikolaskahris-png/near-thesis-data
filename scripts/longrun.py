"""Issuance to 2031 under today's rule and under HSP-029, and the growth that NEAR kept from fees needs.

No price, volume or fee forecast. The model answers one question: how fast must what the wallets
keep (or all fees, counted in NEAR) grow to cover issuance on 1 January 2028, 2029 and 2031?

Rules, each with its source:
  A  today: issuance is at most 1/40 of total supply a year (nearcore `max_inflation_rate`,
     read on chain in data/control_map.json).
  B  HSP-029: cap(t) = 2.5% - 0.9% x min(t, 24) / 24, t in months from activation, applied
     every epoch; activation 90 days after ratification
     (https://gov.houseofstake.org/proposals/29, read 2026-11-03). Ratification is taken as the
     end of vote.dao's timelock (data/hsp029.json), the earliest it can be; a variant starts six
     months later, because the cut is binding only once validators run it.

Measured in the window and held constant (assumptions, named in every key):
  k            actual issuance / maximum issuance (validators below full uptime, gas burnt)
  epoch length window days / epoch starts in the window (data/burn.json)
  NEAR kept a day by the wallets, and all fees counted in NEAR a day, at the window's level

Steps one epoch at a time: S <- S x (1 + cap x k x epoch_days / 365.25).

build_numbers.py calls model() and stores every result as an `lr.` key in data/numbers.json, so
`build_numbers.py --verify` and `rebuild.py` check it with the rest. This file also prints the
table from the saved numbers.json:

    python scripts/longrun.py
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal, getcontext
from fractions import Fraction
from pathlib import Path

getcontext().prec = 40
D = Decimal
REPO = Path(__file__).resolve().parent.parent

YEAR_DAYS = D("365.25")              # as everywhere in this repository
MONTH_DAYS = YEAR_DAYS / 12
HSP029_START = D("0.025")            # cap at activation (proposal: 2.5%)
HSP029_END = D("0.016")              # cap after the ramp (proposal: 1.6%)
HSP029_RAMP_MONTHS = 24
HSP029_GRACE_DAYS = 90               # activation 90 days after ratification
LATE_DAYS = YEAR_DAYS / 2            # variant: activation six months later
TARGET_YEARS = (2028, 2029, 2031)    # coverage on 1 January of each
# Less NEAR issued under HSP-029 than at 2.5%, counted from activation, as the proposal states it
# (https://gov.houseofstake.org/proposals/29, read 2026-11-03). Only a cross-check.
PROPOSAL_NOT_ISSUED = {"2y": D(11_800_000), "6y": D(66_100_000)}
CROSS_CHECK_TOLERANCE = D("0.10")


def cap_b(days_since_activation):
    """HSP-029's cap at a time measured in days from activation (before activation: 2.5%)."""
    if days_since_activation <= 0:
        return HSP029_START
    months = min(days_since_activation / MONTH_DAYS, D(HSP029_RAMP_MONTHS))
    return HSP029_START - (HSP029_START - HSP029_END) * months / HSP029_RAMP_MONTHS


def days_between(a, b):
    return D(str((b - a).total_seconds())) / D(86400)


def run_path(s0, k, epoch_days, start, until, cap, marks):
    """Supply at each date in `marks` (and at `until`), stepping one epoch at a time.

    `cap(t)` gives the yearly cap at datetime t. Between two epoch starts the supply is held,
    as on chain; a mark that falls between them reads the supply of the last epoch start.
    Returns {mark: (supply, issuance per day at that mark)}.
    """
    out, s, t = {}, s0, start
    step = timedelta(seconds=float(epoch_days * 86400))
    pending = sorted(marks)
    while pending or t < until:
        while pending and pending[0] < t + step:
            m = pending.pop(0)
            out[m] = (s, s * cap(t) * k / YEAR_DAYS)
        if t >= until and not pending:
            break
        s = s * (1 + cap(t) * k * epoch_days / YEAR_DAYS)
        t = t + step
    return out


def growth(multiple, years):
    """Yearly growth rate that turns 1 into `multiple` in `years`."""
    return (multiple.ln() / years).exp() - 1


def model(s0, new_per_day, max_rate, epoch_days, start, ratified, kept, staking_yield, take_share,
          history):
    """Every result of the model, as {key: (value, kind, extra)}.

    s0            total_supply at the end block (NEAR)
    new_per_day   issuance per day measured in the window (NEAR)
    max_rate      maximum yearly issuance today (Fraction, 1/40)
    epoch_days    epoch length measured in the window (days)
    start         end of the window (datetime, UTC)
    ratified      end of vote.dao's timelock for HSP-029 (datetime, UTC)
    kept          {"buybacks": NEAR/day, "with_front_end": NEAR/day, "all_fees": NEAR/day}
    staking_yield today's staking yield before commission
    take_share    share of all fees the three wallets keep today
    history       {name: (April value, October value)} measured monthly
    """
    rate_a = D(max_rate.numerator) / D(max_rate.denominator)
    k = new_per_day * YEAR_DAYS / s0 / rate_a
    t0 = ratified + timedelta(days=HSP029_GRACE_DAYS)
    t0_late = t0 + timedelta(days=float(LATE_DAYS))
    targets = {y: datetime(y, 1, 1, tzinfo=timezone.utc) for y in TARGET_YEARS}
    span = {"2y": t0 + timedelta(days=float(2 * YEAR_DAYS)), "6y": t0 + timedelta(days=float(6 * YEAR_DAYS))}
    until = max(list(targets.values()) + list(span.values()))
    marks = list(targets.values()) + list(span.values()) + [t0]
    caps = {
        "A": lambda t: rate_a,
        "B": lambda t: cap_b(days_between(t0, t)),
        "B_late": lambda t: cap_b(days_between(t0_late, t)),
    }
    paths = {p: run_path(s0, k, epoch_days, start, until, cap, marks) for p, cap in caps.items()}

    r, assume = {}, ["k held at the window's level", "epoch length held at the window's level"]
    b_assume = assume + [f"HSP-029 active from {t0:%Y-%m-%d} (end of timelock + 90 days)"]
    late_assume = assume + [f"HSP-029 active from {t0_late:%Y-%m-%d} (six months late)"]
    path_assume = {"A": assume, "B": b_assume, "B_late": late_assume}
    r["lr.k"] = (k, "ratio", {"note": "issuance in the window / maximum issuance (1/40 of supply)"})
    r["lr.epoch_days"] = (epoch_days, "days", {"note": "window days / epoch starts in the window"})
    r["lr.activation_utc"] = (t0, "utc", {"note": "end of vote.dao's timelock + 90 days", "assumptions": b_assume})
    r["lr.activation_late_utc"] = (t0_late, "utc", {"note": "the same, six months later"})
    first = s0 * rate_a * k / YEAR_DAYS
    r["lr.first_epoch_issuance_per_day"] = (first, "near", {"note": "calibration: equals n1.new_near_per_day"})
    for p in ("A", "B"):
        for y, d in targets.items():
            r[f"lr.issuance_per_day.{p}.{y}"] = (paths[p][d][1], "near", {
                "note": f"NEAR issued per day on {d:%Y-%m-%d}", "assumptions": path_assume[p]})
        r[f"lr.supply.{p}.2031-01-01"] = (paths[p][targets[2031]][0], "near", {"assumptions": path_assume[p]})
    for n_, d in span.items():
        issued = {p: paths[p][d][0] - paths[p][t0][0] for p in ("A", "B")}
        less = issued["A"] - issued["B"]
        r[f"lr.not_issued_B.{n_}"] = (less, "million", {
            "note": f"NEAR not issued under HSP-029 in the {n_[0]} years from activation", "assumptions": b_assume})
        r[f"lr.hsp029_proposal.{n_}"] = (PROPOSAL_NOT_ISSUED[n_], "million", {
            "note": "the proposal's own figure, from activation (gov.houseofstake.org/proposals/29, read 2026-11-03)"})
        r[f"lr.not_issued_B_vs_proposal.{n_}"] = (less / PROPOSAL_NOT_ISSUED[n_] - 1, "signed_pct", {
            "note": "model / proposal - 1; the proposal starts from another block and supply"})
    for p in ("A", "B", "B_late"):
        for y, d in targets.items():
            years = days_between(start, d) / YEAR_DAYS
            for name, k0 in kept.items():
                m = paths[p][d][1] / k0
                extra = {"assumptions": path_assume[p] + [f"{name} per day starts at the window's level"],
                         "years": str(years)}
                r[f"lr.required_multiple.{name}.{p}.{y}"] = (m, "multiple", dict(extra, note=(
                    f"issuance per day on {d:%Y-%m-%d} / {name} per day in the window")))
                r[f"lr.required_growth.{name}.{p}.{y}"] = (growth(m, years), "growth", dict(extra, note=(
                    f"yearly growth that turns the window's {name} per day into the issuance per day "
                    f"of {d:%Y-%m-%d}")))
    for y, d in targets.items():
        # validators' yield scales with the cap when k, the treasury's share and the staked
        # share of supply are held: B / A = cap_B / cap_A
        ratio = cap_b(days_between(t0, d)) / rate_a
        r[f"lr.yield_gross.B.{y}"] = (staking_yield * ratio, "pct", {
            "note": f"today's staking yield x HSP-029's cap on {d:%Y-%m-%d} / 2.5%",
            "assumptions": b_assume + ["staked share of supply and treasury.near's share held"]})
    r["lr.take_rate_ceiling_multiple"] = (1 / take_share, "multiple", {
        "note": "1 / share of all fees the three wallets keep today: the most that keeping every fee can add, once"})
    for name, (a, b) in history.items():
        r[f"lr.history.2026-04_2026-10.{name}_multiple"] = (b / a, "multiple", {
            "note": f"October / April, measured monthly ({name})"})
    return r


def base_sensitivity(r, bases):
    """The 2031 hurdles again, from other base levels of what the wallets keep.

    `r` is model()'s result; `bases` is {name: {"buybacks": NEAR/day, "with_front_end": NEAR/day}}
    (a month, or an average of months). Same issuance on 1 January 2031 and same number of years as
    model(): only the starting level changes. Returns {key: (value, kind, extra)}.
    """
    out = {}
    for p in ("A", "B"):
        target = r[f"lr.issuance_per_day.{p}.2031"][0]
        for name in ("buybacks", "with_front_end"):
            years = D(r[f"lr.required_growth.{name}.{p}.2031"][2]["years"])
            grown = {}
            for base, level in bases.items():
                g = growth(target / level[name], years)
                grown[base] = g
                out[f"lr.required_growth.{name}.{p}.2031.base.{base}"] = (g, "growth", {
                    "note": f"as lr.required_growth.{name}.{p}.2031, starting from the {base} level "
                            f"({level[name]:.3f} NEAR a day) instead of the window's",
                    "years": str(years)})
            months = {b: g for b, g in grown.items() if "_" not in b}
            lo, hi = min(months, key=months.get), max(months, key=months.get)
            out[f"lr.required_growth.{name}.{p}.2031.base_min"] = (months[lo], "growth", {
                "note": f"lowest over the monthly bases: {lo}", "month": lo})
            out[f"lr.required_growth.{name}.{p}.2031.base_max"] = (months[hi], "growth", {
                "note": f"highest over the monthly bases: {hi}", "month": hi})
    return out


def check(r):
    """Problems with a model result: calibration, ramp, and the cross-check with the proposal."""
    problems = []
    for n_ in ("2y", "6y"):
        off = r[f"lr.not_issued_B_vs_proposal.{n_}"][0]
        if abs(off) > CROSS_CHECK_TOLERANCE:
            problems.append(f"HSP-029 {n_}: model differs from the proposal by {off:.1%}")
    return problems


def main():
    doc = json.loads((REPO / "data" / "numbers.json").read_text(encoding="utf-8"))
    n = doc["numbers"]
    keys = sorted(k for k in n if k.startswith(("lr.required_growth.", "lr.required_multiple.",
                                                  "lr.issuance_per_day.", "lr.not_issued")))
    if not keys:
        print("numbers.json has no lr. keys; run scripts/build_numbers.py first")
        return 1
    for k in keys:
        print(f"{k:58s} {n[k]['text']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
