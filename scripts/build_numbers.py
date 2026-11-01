"""Collect every number of the thesis into data/numbers.json, from the scripts' own outputs.

Nothing here touches the network or re-measures anything. Each number keeps:
  value   the exact figure as its source file states it
  text    the form used in README and dashboard (English formatting)
  source  the file it comes from, with that file's sha256
The build fails when the inputs do not describe the same window: numbers 1, 2 and 3
and the treasury flows must end at the last boundary of the same locked window file.

README and dashboard never contain a typed number. They mark each one:
    <!--n:n1.coverage_buybacks-->10.8%<!--/n-->
`--check FILE` fails if a marked text differs from numbers.json; `--render FILE`
rewrites the marked texts from numbers.json.

Usage:
    python scripts/build_numbers.py --window data/window_2026-10-02_2026-11-01.json
    python scripts/build_numbers.py --verify            every script's offline check + rebuild
    python scripts/build_numbers.py --check README.md
    python scripts/build_numbers.py --render README.md
"""
import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lock_window as lw  # noqa: E402
import stakers  # noqa: E402

REPO = lw.REPO
OUT_NAME = "numbers.json"
MARK = re.compile(r"<!--n:([A-Za-z0-9_.\-]+)-->(.*?)<!--/n-->", re.S)


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ---------------------------------------------------------------- formatting

def dec(x):
    return Decimal(str(x))


def rnd(x, places):
    q = Decimal(1).scaleb(-places)
    return dec(x).quantize(q, rounding=ROUND_HALF_UP)


def f_int(x):
    return f"{rnd(x, 0):,.0f}"


def f_num(x, places):
    return f"{rnd(x, places):,.{places}f}"


def f_pct(share, places=1):
    return f"{rnd(dec(share) * 100, places):.{places}f}%"


def f_usd(x, places=0):
    return f"${rnd(x, places):,.{places}f}"


# ---------------------------------------------------------------- collection

class Numbers:
    def __init__(self, root):
        self.root = root
        self.items = {}
        self.sources = {}

    def source(self, path):
        rel = Path(path).resolve().relative_to(self.root).as_posix()
        self.sources[rel] = sha256_file(path)
        return rel

    def add(self, key, value, text, src, **extra):
        if key in self.items:
            raise ValueError(f"duplicate key {key}")
        item = {"value": None if value is None else str(value), "text": text, "source": src}
        item.update(extra)
        self.items[key] = item


def history_row(data_dir, date):
    with open(data_dir / "history.csv", newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r["date"] == date]
    if not rows:
        raise SystemExit(f"history.csv has no row for {date}: run daily.py for that date.")
    return rows[-1]


def build(data_dir, window_file):
    root = data_dir.resolve().parent
    window_file = Path(window_file)
    win = json.loads(window_file.read_text(encoding="utf-8"))
    first_b, last_b = win["boundaries"][0], win["boundaries"][-1]
    start_date, end_date = win["window"]["start"], win["window"]["end"]
    n = Numbers(root)
    wsrc = n.source(window_file)
    problems = []

    def same(label, got, want):
        if str(got) != str(want):
            problems.append(f"{label}: {got} != {want}")

    common = {"window": f"{start_date} 00:00 UTC to {end_date} 00:00 UTC",
              "blocks": f"{first_b['height']}-{last_b['height']}"}

    # ---- number 1: coverage by the revenue wallets (daily.py, same window)
    row = history_row(data_dir, end_date)
    hsrc = n.source(data_dir / "history.csv")
    same("number 1 window start", row["window_start"], start_date)
    same("number 1 start block", row["block_start"], first_b["height"])
    same("number 1 end block", row["block_end"], last_b["height"])
    n.add("n1.new_near_per_day", row["new_supply_per_day"], f_int(row["new_supply_per_day"]),
          hsrc, unit="NEAR/day", **common)
    n.add("n1.buybacks_near_per_day", row["buybacks_per_day"], f_int(row["buybacks_per_day"]),
          hsrc, unit="NEAR/day", note="buybacks.multisignature.near + 1csfundsadmin", **common)
    n.add("n1.front_end_near_per_day", row["fefunds_per_day"], f_int(row["fefunds_per_day"]),
          hsrc, unit="NEAR/day", note="fefundsadmin.sputnik-dao.near", **common)
    n.add("n1.coverage_buybacks", row["coverage_buybacks"], f_pct(row["coverage_buybacks"]),
          hsrc, unit="share", **common)
    n.add("n1.coverage_with_front_end", row["coverage_with_fe"], f_pct(row["coverage_with_fe"]),
          hsrc, unit="share", **common)
    uncovered = dec(row["new_supply_per_day"]) - dec(row["buybacks_per_day"])
    n.add("n1.new_near_not_absorbed_per_day", uncovered, f_int(uncovered), hsrc,
          unit="NEAR/day", note="new NEAR minus NEAR kept by the buybacks wallet; total "
          "supply still grows by n1.new_near_per_day", **common)

    # ---- finding 9: front-end share of what the revenue wallets keep (same window, wallets)
    kept = dec(row["buybacks_per_day"]) + dec(row["fefunds_per_day"])
    n.add("f9.front_end_share_of_wallets", dec(row["fefunds_per_day"]) / kept,
          f_pct(dec(row["fefunds_per_day"]) / kept), hsrc, unit="share",
          note="fefundsadmin.sputnik-dao.near / (buybacks.multisignature.near + 1csfundsadmin "
          "+ fefundsadmin), net NEAR kept per day, measured on the wallets", **common)

    # ---- number 2: maximum coverage by all fees (fees.py)
    fees_path = data_dir / f"fees_{start_date}_{end_date}.json"
    fees = json.loads(fees_path.read_text(encoding="utf-8"))
    fsrc = n.source(fees_path)
    fw = fees["result"]["window"]
    same("number 2 window file", Path(fees["window_file"]).as_posix(),
         window_file.resolve().relative_to(root).as_posix())
    same("number 2 start block", fw["block_start"], first_b["height"])
    same("number 2 end block", fw["block_end"], last_b["height"])
    same("number 2 new NEAR/day vs number 1", fw["new_near_per_day"], row["new_supply_per_day"])
    status = "final" if fees["final"]["ready"] else "provisional"
    fc = dict(common, status=status, fetched_utc=fees["fetched_utc"],
              counted_days=fw["counted_days"], excluded_days=sorted(fw["excluded"]))
    for key, field, fmt, unit in (
            ("n2.max_coverage", "max_coverage", f_pct, "share"),
            ("n2.equilibrium_price_usd", "equilibrium_price_usd", lambda v: f_usd(v, 2), "USD"),
            ("n2.hsp029_max_coverage", "hsp029_scenario_max_coverage", f_pct, "share"),
            ("n2.hsp029_equilibrium_price_usd", "hsp029_scenario_equilibrium_price_usd",
             lambda v: f_usd(v, 2), "USD"),
            ("n2.fees_usd_per_day", "fees_usd_per_day", f_usd, "USD/day"),
            ("n2.revenue_usd_per_day", "revenue_usd_per_day", f_usd, "USD/day"),
            ("n2.volume_usd_per_day", "volume_usd_per_day", f_usd, "USD/day"),
            ("n2.fees_bps", "fees_bps", lambda v: f_num(v, 1), "bps of volume"),
            ("n2.take_rate", "take_rate", f_pct, "revenue / fees"),
            ("n2.mean_price_usd", "mean_price_usd", lambda v: f_usd(v, 2), "USD"),
            ("n2.fees_near_per_day", "fees_near_per_day", f_int, "NEAR/day"),
            ("n2.defillama_revenue_coverage", "defillama_revenue_coverage", f_pct, "share")):
        n.add(key, fw[field], fmt(fw[field]), fsrc, unit=unit, **fc)

    # ---- number 3: NEAR AI stakers at the end block (stakers.py)
    snap = data_dir / "stakers" / f"{end_date}.json"
    stats, p = stakers.compute(snap, data_dir.resolve())
    problems += [f"stakers: {x}" for x in p]
    ssrc = n.source(snap)
    if stats:
        same("number 3 block", stats["block"], last_b["height"])
        sc = {"block": last_b["height"], "as_of": f"{end_date} 00:00 UTC"}
        for key, field, fmt, unit in (
                ("n3.stakers_active", "stakers_active", f_int, "accounts"),
                ("n3.stakers_ever", "stakers_ever", f_int, "accounts"),
                ("n3.stakers_left", "stakers_left", f_int, "accounts"),
                ("n3.left_share_of_ever", "left_share_of_ever", f_pct, "share"),
                ("n3.largest_share", "largest_share", f_pct, "share of farm"),
                ("n3.largest_near", "largest_near", f_int, "NEAR"),
                ("n3.top10_share", "top10_share", f_pct, "share of farm"),
                ("n3.farm_total_near", "farm_total_near", f_int, "NEAR"),
                ("n3.outside_top10_accounts", "outside_top10_accounts", f_int, "accounts"),
                ("n3.outside_top10_near", "outside_top10_near", f_int, "NEAR"),
                ("n3.outside_top10_median_near", "outside_top10_median_near", f_int, "NEAR"),
                ("n3.agents_locks", "agents_locks", f_int, "locks"),
                ("n3.agents_locks_past_end", "agents_locks_past_end", f_int, "locks"),
                ("n3.farm_or_active_lock_accounts", "farm_or_active_lock_accounts", f_int,
                 "accounts"),
                ("n3.farm_or_any_lock_accounts", "farm_or_any_lock_accounts", f_int, "accounts")):
            n.add(key, stats[field], fmt(stats[field]), ssrc, unit=unit, **sc)

        # ---- finding 7: NEAR AI Agents subscriptions (locks), same snapshot
        for key, field, fmt, unit in (
                ("f7.locks", "agents_locks", f_int, "locks"),
                ("f7.lock_accounts", "agents_lock_accounts", f_int, "accounts"),
                ("f7.locks_active", "agents_locks_active", f_int, "locks"),
                ("f7.locks_unlock_requested", "agents_locks_unlock_requested", f_int, "locks"),
                ("f7.locks_active_within_term", "agents_locks_active_within_term", f_int,
                 "locks"),
                ("f7.locks_past_end", "agents_locks_past_end", f_int, "locks"),
                ("f7.locks_near", "agents_locks_near", f_int, "NEAR"),
                ("f7.locks_active_near", "agents_locks_active_near", f_int, "NEAR"),
                ("f7.active_lock_near_vs_farm", "agents_active_lock_near_vs_farm", f_pct,
                 "Active-lock NEAR / farm NEAR"),
                ("f7.locks_at_50_near", "agents_locks_at_50_near", f_int, "locks"),
                ("f7.lock_days_min", "agents_lock_days_min", lambda v: f_num(v, 0), "days"),
                ("f7.lock_days_max", "agents_lock_days_max", lambda v: f_num(v, 0), "days")):
            n.add(key, stats[field], fmt(stats[field]), ssrc, unit=unit, **sc)

        # ---- finding 6: farm reward rate at the end block (stakers.py saves get_farm_pool)
        for key, field, fmt, unit in (
                ("f6.reward_rate", "farm_reward_rate", str, "24-decimal units / s / NEAR"),
                ("f6.units_per_near_year", "farm_units_per_near_year",
                 lambda v: f_num(v, 2), "reward units per staked NEAR per year (365.25 d)"),
                ("f6.largest_units_per_day", "largest_units_per_day", lambda v: f_num(v, 1),
                 "reward units per day"),
                ("f6.farm_units_per_day", "farm_units_per_day", f_int, "reward units per day")):
            n.add(key, stats[field], fmt(stats[field]), ssrc, unit=unit,
                  note="reward units are not USD: the contract has no USD conversion", **sc)

    # ---- finding 6: every change of the farm rate (farm_rate.py)
    fr_path = data_dir / "farm_rate.json"
    if fr_path.exists():
        frd = json.loads(fr_path.read_text(encoding="utf-8"))
        frsrc = n.source(fr_path)
        n.add("f6.edit_price_receipts_all_time", frd["edit_price_receipts_all_time"],
              f_int(frd["edit_price_receipts_all_time"]), frsrc, unit="receipts")
        n.add("f6.rate_changes", frd["rate_changes"], f_int(frd["rate_changes"]), frsrc,
              unit="changes")
        for i, c in enumerate(x for x in frd["changes"] if x["rate_changed"]):
            cc = {"block": c["receipt_block"], "tx_hash": c["tx_hash"]}
            for key, val, txt in (
                    ("utc", c["receipt_utc"], c["receipt_utc"][:16].replace("T", " ") + " UTC"),
                    ("units_per_near_year_before", c["units_per_near_year_before"],
                     f_num(c["units_per_near_year_before"], 2)),
                    ("units_per_near_year_after", c["units_per_near_year_after"],
                     f_num(c["units_per_near_year_after"], 2)),
                    ("ratio", c["ratio_after_before"], "×" + f_num(c["ratio_after_before"], 1)),
                    ("signer_is_pool_owner", c["signer_is_pool_owner"],
                     "yes" if c["signer_is_pool_owner"] else "no"),
                    ("signer_is_catalog_manager", c["signer_is_catalog_manager"],
                     "yes" if c["signer_is_catalog_manager"] else "no")):
                n.add(f"f6.change{i + 1}.{key}", val, txt, frsrc, **cc)
    else:
        n.add("f6.rate_changes", None, None, None, status="pending",
              note="farm_rate.py has not run")

    # ---- finding 5: concentration over time (every saved stakers snapshot)
    for path in sorted((data_dir / "stakers").glob("20*.json")):
        st, p = stakers.compute(path, data_dir.resolve())
        problems += [f"stakers {path.name}: {x}" for x in p]
        if not st:
            continue
        src = n.source(path)
        d = st["date"]
        n.add(f"f5.largest_share.{d}", st["largest_share"], f_pct(st["largest_share"]), src,
              unit="share of farm", block=st["block"])
        n.add(f"f5.stakers_active.{d}", st["stakers_active"], f_int(st["stakers_active"]), src,
              unit="accounts", block=st["block"])
        if st.get("farm_units_per_near_year"):
            n.add(f"f6.units_per_near_year.{d}", st["farm_units_per_near_year"],
                  f_num(st["farm_units_per_near_year"], 2), src,
                  unit="reward units per staked NEAR per year", block=st["block"])

    # ---- finding 1: monthly coverage by the wallets (coverage.py)
    cov_path = data_dir / "coverage_monthly.json"
    cov = json.loads(cov_path.read_text(encoding="utf-8"))
    csrc = n.source(cov_path)
    for r in cov["rows"]:
        m = r["month"]
        extra = {"unit": "share", "blocks": f"{r['block_start']}-{r['block_end']}",
                 "flags": r.get("flags", "")}
        n.add(f"f1.coverage_buybacks.{m}", r["coverage_buybacks"], f_pct(r["coverage_buybacks"]),
              csrc, **extra)
        n.add(f"f1.coverage_with_front_end.{m}", r["coverage_with_fe"],
              f_pct(r["coverage_with_fe"]), csrc, **extra)

    # ---- finding 2: monthly fees, take rate, price and NEAR bought (fees.py + coverage.py)
    kept_by_month = {r["month"]: dec(r["buybacks_per_day"]) + dec(r["fefunds_per_day"])
                     for r in cov["rows"]}
    fmon = {}
    for m in fees["result"].get("monthly", []):
        if not m.get("full_month"):
            continue
        k = m["month"]
        fmon[k] = m
        mc = {"status": status, "fetched_utc": fees["fetched_utc"],
              "month": k, "counted_days": m["counted_days"], "days": m["days"],
              "excluded_days": sorted(m["excluded"])}
        for key, field, fmt, unit in (
                ("fees_usd_per_day", "fees_usd_per_day", f_usd, "USD/day"),
                ("revenue_usd_per_day", "revenue_usd_per_day", f_usd, "USD/day"),
                ("volume_usd_per_day", "volume_usd_per_day", f_usd, "USD/day"),
                ("fees_bps", "fees_bps", lambda v: f_num(v, 1), "bps of volume"),
                ("take_rate", "take_rate", f_pct, "revenue / fees"),
                ("mean_price_usd", "mean_price_usd", lambda v: f_usd(v, 2), "USD"),
                ("revenue_near_per_day", "revenue_near_per_day", f_int, "NEAR/day")):
            n.add(f"f2.{key}.{k}", m[field], fmt(m[field]), fsrc, unit=unit, **mc)
        if k in kept_by_month and dec(m["revenue_near_per_day"]) > 0:
            kept_share = kept_by_month[k] / dec(m["revenue_near_per_day"])
            n.add(f"f2.wallets_kept_near_per_day.{k}", kept_by_month[k],
                  f_int(kept_by_month[k]), csrc, unit="NEAR/day",
                  note="buybacks + 1cs + fefundsadmin, net change on the wallets", month=k)
            n.add(f"f2.wallets_kept_share_of_revenue.{k}", kept_share, f_pct(kept_share, 0),
                  fsrc, unit="wallets NEAR / DefiLlama revenue NEAR", also=csrc,
                  note="wallets counted on every day of the month; DefiLlama revenue on "
                  "its counted days", **mc)
    months = sorted(fmon)
    if len(months) >= 2:
        a, b = months[-2], months[-1]
        pair = f"{a}_{b}"
        pc = {"status": status, "fetched_utc": fees["fetched_utc"], "from": a, "to": b}
        for key, field in (("revenue_usd", "revenue_usd_per_day"),
                           ("mean_price", "mean_price_usd"),
                           ("revenue_near", "revenue_near_per_day"),
                           ("volume_usd", "volume_usd_per_day")):
            ch = dec(fmon[b][field]) / dec(fmon[a][field]) - 1
            txt = ("+" if ch > 0 else "") + f_pct(ch, 0)
            n.add(f"f2.change.{pair}.{key}", ch, txt, fsrc, unit="relative change", **pc)

    # ---- finding 4: flows of the owner of nearai.pool.near (treasury_flows.py)
    tf_path = data_dir / "treasury_flows.json"
    tfd = json.loads(tf_path.read_text(encoding="utf-8"))
    tsrc = n.source(tf_path)
    same("treasury end block", tfd["meta"]["end_block"], last_b["height"])
    for wname, short in (("since_stake_dao", "since_stake_dao"), ("year_2026", "y2026")):
        w = tfd["windows"][wname]
        f, s = w["owner_flows"], w["payments_swaps_wnear_to_stablecoins"]
        tc = {"blocks": f"{w['start_block']}-{w['end_block']}",
              "window": f"{w['start_utc'][:16]} UTC to {w['end_utc'][:16]} UTC"}
        for key, val, fmt, unit in (
                ("unstaked_near", f["unstaked"], f_int, "NEAR"),
                ("near_sent_out", f["near_transferred_out"], f_int, "NEAR"),
                ("near_to_payments_account", f["near_to_payments_account"], f_int, "NEAR"),
                ("usdc_sent_out", f["usdc_transferred_out"], f_usd, "USDC"),
                ("owner_near_start", w["owner_positions_start"]["owner_total_near"], f_int, "NEAR"),
                ("owner_near_end", w["owner_positions_end"]["owner_total_near"], f_int, "NEAR"),
                ("owner_near_change", w["owner_total_near_change"], f_int, "NEAR"),
                ("swaps", s["count"], f_int, "swaps"),
                ("swaps_near_given", s["near_given"], f_int, "NEAR"),
                ("swaps_usd_received", s["usd_received"], f_usd, "USDC+USDT"),
                ("swaps_mean_price_usd", s["mean_price_usd"], lambda v: f_usd(v, 2), "USD")):
            n.add(f"f4.{short}.{key}", val, fmt(val) if val is not None else None, tsrc,
                  unit=unit, **tc)
    n.add("f4.stake_dao_start_utc", tfd["windows"]["since_stake_dao"]["start_utc"],
          tfd["windows"]["since_stake_dao"]["start_utc"][:10], tsrc,
          note="first block where the stake.dao account exists")
    fs = tfd["stake_dao_first_stake_receipt"]
    n.add("f4.first_stake_utc", fs["utc"], fs["utc"][:10], tsrc, block=fs["height"])

    # ---- finding 8: HSP-029 (hsp029.py), once the vote has closed
    hsp_path = data_dir / "hsp029.json"
    if hsp_path.exists():
        h = json.loads(hsp_path.read_text(encoding="utf-8"))
        hsrc2 = n.source(hsp_path)
        r = h["result"]
        hc = {"block": h["closing_block"]["height"],
              "as_of": h["closing_block"]["timestamp_utc"][:19] + "Z"}
        n.add("f8.computed_status", r["computed_status"], r["computed_status"], hsrc2, **hc)
        n.add("f8.contract_status_at_close", h["reported_status_at_close"],
              h["reported_status_at_close"], hsrc2, **hc)
        for o in r["options"]:
            lab = (o["label"] or str(o["index"])).lower()
            n.add(f"f8.{lab}_venear", o["venear"], f_int(o["venear"]), hsrc2, unit="veNEAR", **hc)
            n.add(f"f8.{lab}_votes", o["votes"], f_int(o["votes"]), hsrc2, unit="votes", **hc)
        for key, field, fmt in (
                ("turnout_of_snapshot", "turnout_of_snapshot", f_pct),
                ("approval_share", "approval_share_for_of_for_plus_against", f_pct),
                ("quorum_required_venear", "quorum_required_venear", f_int),
                ("snapshot_total_venear", "snapshot_total_venear", f_int),
                ("snapshot_accounts", "snapshot_accounts", f_int)):
            n.add(f"f8.{key}", r[field], fmt(r[field]), hsrc2, **hc)
        # who carried the vote (hsp029_voters.py), same closing block
        vpath = data_dir / "hsp029_voters.json"
        if vpath.exists():
            v = json.loads(vpath.read_text(encoding="utf-8"))
            vsrc = n.source(vpath)
            same("HSP-029 voters block", v["block"], h["closing_block"]["height"])
            if not v.get("sums_match_contract") or v.get("trial"):
                problems.append("hsp029_voters.json: trial file or sums do not match the contract")
            st = v["stats"]
            for key, fmt in (("voters", f_int), ("for_voters", f_int),
                             ("top1_share_of_votes_cast", f_pct),
                             ("top3_share_of_votes_cast", f_pct),
                             ("top8_share_of_votes_cast", f_pct),
                             ("top10_share_of_votes_cast", f_pct),
                             ("top8_share_of_for", f_pct),
                             ("largest_venear", f_int), ("median_venear", f_int),
                             ("fewest_voters_reaching_quorum", f_int)):
                val = st[key]
                n.add(f"f8.{key}", val, None if val is None else fmt(val), vsrc, **hc)
        else:
            n.add("f8.top8_share_of_votes_cast", None, None, None, status="pending",
                  note="hsp029_voters.py runs after hsp029.py")
    else:
        n.add("f8.computed_status", None, None, None, status="pending",
              note="hsp029.py runs after the vote closes (2026-11-02 16:48:08 UTC)")

    provisional = sorted(k for k, v in n.items.items() if v.get("status") in ("provisional",
                                                                                  "pending"))
    doc = {
        "about": "Every number used in the README and the dashboard. Built by "
                 "scripts/build_numbers.py from the files listed in 'sources'; check with "
                 "python scripts/build_numbers.py --verify",
        "window_file": wsrc,
        "window": {"start": start_date, "end": end_date,
                   "start_block": first_b["height"], "end_block": last_b["height"]},
        "complete": not provisional,
        "provisional_or_pending": provisional,
        "sources": dict(sorted(n.sources.items())),
        "numbers": dict(sorted(n.items.items())),
    }
    return doc, problems


# ---------------------------------------------------------------- verify

SCRIPT_CHECKS = [
    ("lock_window.py", lambda doc: ["--verify", doc["window_file"]]),
    ("daily.py", lambda doc: ["--verify"]),
    ("fees.py", lambda doc: ["--verify",
                             f"data/fees_{doc['window']['start']}_{doc['window']['end']}.json"]),
    ("coverage.py", lambda doc: ["--verify"]),
    ("stakers.py", lambda doc: ["--verify"]),
    ("treasury_flows.py", lambda doc: ["--verify"]),
    ("hsp029.py", lambda doc: ["--verify"]),
    ("hsp029_voters.py", lambda doc: ["--verify"]),
    ("farm_rate.py", lambda doc: ["--verify"]),
]


def verify(path, run_scripts=True, runner=subprocess.run):
    path = Path(path)
    doc = json.loads(path.read_text(encoding="utf-8"))
    root = path.resolve().parent.parent
    problems = []
    for rel, digest in doc["sources"].items():
        p = root / rel
        if not p.exists():
            problems.append(f"missing source {rel}")
        elif sha256_file(p) != digest:
            problems.append(f"source changed since the build: {rel}")
    if run_scripts:
        for script, args in SCRIPT_CHECKS:
            out_file = {"hsp029.py": "hsp029.json", "hsp029_voters.py": "hsp029_voters.json",
                        "farm_rate.py": "farm_rate.json"}
            if script in out_file and not (root / "data" / out_file[script]).exists():
                continue
            res = runner([sys.executable, str(root / "scripts" / script)] + args(doc),
                         cwd=root, capture_output=True, text=True)
            line = (res.stdout.strip().splitlines() or [""])[-1]
            print(f"  {script:<18} {'OK' if res.returncode == 0 else 'FAILED'}  {line[:110]}")
            if res.returncode != 0:
                problems.append(f"{script} --verify failed")
    if not problems:
        again, p = build(root / "data", root / doc["window_file"])
        problems += p
        if again != doc:
            changed = [k for k in again["numbers"] if again["numbers"][k] != doc["numbers"].get(k)]
            problems.append(f"numbers.json does not rebuild the same ({len(changed)} differ: "
                            f"{', '.join(changed[:5])})")
    return problems


# ---------------------------------------------------------------- README markers

def check_text(text, numbers):
    problems = []
    for m in MARK.finditer(text):
        key, shown = m.group(1), m.group(2)
        item = numbers.get(key)
        if item is None:
            problems.append(f"unknown number '{key}'")
        elif item["text"] is None:
            problems.append(f"'{key}' is not measured yet")
        elif shown != item["text"]:
            problems.append(f"'{key}' shows '{shown}', numbers.json says '{item['text']}'")
    return problems


def render_text(text, numbers):
    def sub(m):
        item = numbers.get(m.group(1))
        if item is None or item["text"] is None:
            raise SystemExit(f"cannot render '{m.group(1)}': not in numbers.json or not measured")
        return f"<!--n:{m.group(1)}-->{item['text']}<!--/n-->"
    return MARK.sub(sub, text)


# ---------------------------------------------------------------- main

def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--window", help="locked window file all numbers are measured in")
    parser.add_argument("--data-dir", type=Path, default=REPO / "data")
    parser.add_argument("--verify", nargs="?", const=str(REPO / "data" / OUT_NAME), metavar="FILE")
    parser.add_argument("--check", metavar="TEXT_FILE")
    parser.add_argument("--render", metavar="TEXT_FILE")
    args = parser.parse_args()
    out = args.data_dir / OUT_NAME
    if args.verify:
        problems = verify(args.verify)
        if problems:
            print("FAILED:\n  " + "\n  ".join(problems))
            sys.exit(1)
        doc = json.loads(Path(args.verify).read_text(encoding="utf-8"))
        print(f"OK: every script's check passes and numbers.json rebuilds the same "
              f"({len(doc['numbers'])} numbers; provisional or pending: "
              f"{len(doc['provisional_or_pending'])})")
        return
    if args.check or args.render:
        numbers = json.loads(out.read_text(encoding="utf-8"))["numbers"]
        target = Path(args.check or args.render)
        text = target.read_text(encoding="utf-8")
        if args.render:
            target.write_text(render_text(text, numbers), encoding="utf-8", newline="\n")
            text = target.read_text(encoding="utf-8")
        problems = check_text(text, numbers)
        if problems:
            print("FAILED:\n  " + "\n  ".join(problems))
            sys.exit(1)
        print(f"OK: {len(MARK.findall(text))} marked numbers in {target.name} match numbers.json")
        return
    if not args.window:
        parser.error("--window is required")
    doc, problems = build(args.data_dir, args.window)
    if problems:
        print("FAILED: the inputs do not describe the same window\n  " + "\n  ".join(problems))
        sys.exit(1)
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
                   newline="\n")
    nums = doc["numbers"]
    for key in ("n1.coverage_buybacks", "n1.coverage_with_front_end", "n2.max_coverage",
                "n2.equilibrium_price_usd", "n3.stakers_active", "n3.largest_share",
                "f4.since_stake_dao.owner_near_change", "f4.since_stake_dao.swaps_near_given",
                "f8.computed_status"):
        print(f"  {key:<40} {nums[key]['text']}  {nums[key].get('status', '')}")
    print(f"Saved {out.relative_to(args.data_dir.parent).as_posix()}: {len(nums)} numbers, "
          f"{len(doc['sources'])} sources; provisional or pending: "
          f"{', '.join(doc['provisional_or_pending'][:3])}"
          f"{' …' if len(doc['provisional_or_pending']) > 3 else ''}")


if __name__ == "__main__":
    main()
