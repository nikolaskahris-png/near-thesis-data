"""Collect every number of the thesis into data/numbers.json, from the scripts' own outputs.

Nothing here touches the network or re-measures anything. Each number keeps:
  value   the exact figure as its source file states it
  text    the form used in the README (English formatting)
  source  the file it comes from, with that file's sha256
The build fails when the inputs do not describe the same window: numbers 1, 2 and 3
and the treasury flows must end at the last boundary of the same locked window file.

The README never contains a typed measured number. It marks each one:
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
import hashlib
import json
import re
import subprocess
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import daily  # noqa: E402
import lock_window as lw  # noqa: E402
import longrun  # noqa: E402
import stakers  # noqa: E402

REPO = lw.REPO
OUT_NAME = "numbers.json"
MARK = re.compile(r"<!--n:([A-Za-z0-9_.\-]+)-->(.*?)<!--/n-->", re.S)


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ---------------------------------------------------------------- formatting

def dec(x):
    return Decimal(str(x))


HSP029_SCALE = Decimal(16) / Decimal(25)   # HSP-029: issuance 2.5% -> 1.6% of the maximum
HORIZON_DAYS = 1522   # 1 November 2026 (window end) to 1 January 2031, the thesis horizon


def rnd(x, places):
    q = Decimal(1).scaleb(-places)
    return dec(x).quantize(q, rounding=ROUND_HALF_UP)


def f_int(x):
    return f"{rnd(x, 0):,.0f}"


def f_num(x, places):
    return f"{rnd(x, places):,.{places}f}"


def f_pct(share, places=1):
    return f"{rnd(dec(share) * 100, places):.{places}f}%"


def ordinal(k):
    return f"{k}{'th' if 10 <= k % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(k % 10, 'th')}"


def day_month(iso):
    months = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
              "November", "December")
    return f"{int(iso[8:10])} {months[int(iso[5:7]) - 1]}"


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


def day_row(data_dir, date):
    """Number 1 for one date, recomputed from its own day file (data/daily/D.json).

    The day file never changes once written; history.csv grows every day, so it is not
    used as a source here (its sha256 would change with each new row).
    Returns (path of the day file, row, problems)."""
    path = data_dir / "daily" / f"{date}.json"
    if not path.exists():
        raise SystemExit(f"No day file for {date}: run daily.py --date {date}.")
    row, problems = daily.build_row(json.loads(path.read_text(encoding="utf-8")),
                                    data_dir.resolve())
    return path, row, problems


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
    dpath, row, dp = day_row(data_dir, end_date)
    problems += [f"daily {end_date}: {x}" for x in dp]
    if not row:
        return None, problems
    hsrc = n.source(dpath)
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
    # NEAR held at the end block by the wallets that k-of-n signers can move (balances,
    # liquid + wNEAR on intents.near, as daily.py reads them).
    eb = {"block": last_b["height"], "as_of": row["block_end_utc"]}
    held_b, held_fe = dec(row["buybacks_end"]), dec(row["fefunds_end"])
    n.add("n1.buybacks_held_near", held_b, f_int(held_b), hsrc, unit="NEAR",
          note="buybacks.multisignature.near + 1csfundsadmin.sputnik-dao.near at the end block", **eb)
    n.add("n1.front_end_held_near", held_fe, f_int(held_fe), hsrc, unit="NEAR",
          note="fefundsadmin.sputnik-dao.near at the end block", **eb)
    n.add("n1.wallets_held_near", held_b + held_fe, f_int(held_b + held_fe), hsrc, unit="NEAR",
          note="n1.buybacks_held_near + n1.front_end_held_near", **eb)
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
    # Sensitivity to the NEAR Intents exploit of 2026-10-01 (Omni deposits and withdrawals; the
    # intents.near DAO paused features and installed new code from 1 to 7 October): the same
    # ceiling without 2 to 7 October, from the same day rows and the same excluded days.
    calm = [d for d in fees["result"].get("days", [])
            if d["date"] not in fw["excluded"] and not "2026-10-02" <= d["date"] <= "2026-10-07"]
    if 0 < len(calm) < fw["counted_days"]:
        c = (sum(dec(d["fees_usd"]) / dec(d["price_usd"]) for d in calm) / len(calm)
             / dec(fw["new_near_per_day"]))
        n.add("n2.max_coverage_without_2026-10-02_to_07", c, f_pct(c), fsrc, unit="share",
              note="n2.max_coverage over the counted days outside 2026-10-02..07, the days after "
                   "the NEAR Intents exploit of 2026-10-01", **fc)

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

    # ---- gas burnt and gross issuance in the same window (burn.py)
    bpath = data_dir / "burn.json"
    if bpath.exists():
        bd = json.loads(bpath.read_text(encoding="utf-8"))
        same("burn.json window", bd["window_file"], wsrc)
        br = bd["results"]
        same("burn net issuance = number 1", br["net_near_per_day"], row["new_supply_per_day"])
        bsrc = n.source(bpath)
        for key, txt, unit in (
                ("epochs", f_int(br["epochs"]), "epoch starts"),
                ("minted_near_per_day", f_int(br["minted_near_per_day"]), "NEAR/day"),
                ("burnt_near_per_day", f_int(br["burnt_near_per_day"]), "NEAR/day"),
                ("burnt_share_of_minted", f_pct(br["burnt_share_of_minted"], 1), "share"),
                ("max_mint_near_per_day", f_int(br["max_mint_near_per_day"]), "NEAR/day"),
                ("minted_share_of_max", f_pct(br["minted_share_of_max"], 2), "share"),
                ("hsp027_extra_burn_max_near_per_day", f_int(br["hsp027_extra_burn_max_near_per_day"]),
                 "NEAR/day"),
                ("hsp027_extra_max_share_of_minted", f_pct(br["hsp027_extra_max_share_of_minted"], 2),
                 "share")):
            n.add(f"b.{key}", br[key], txt, bsrc, unit=unit, **common)
        if br.get("treasury_share_of_minted"):
            n.add("b.treasury_share_of_minted", br["treasury_share_of_minted"],
                  f_pct(br["treasury_share_of_minted"], 1), bsrc, unit="share", **common)

    # ---- finding 13: treasury.near in 2026 (treasury_spend.py) and its exits (treasury_exits.py)
    tpath = data_dir / "treasury_spend.json"
    if tpath.exists():
        td = json.loads(tpath.read_text(encoding="utf-8"))
        tsrc = n.source(tpath)
        tr = td["results"]
        rule, tw, tot = tr["rule"], tr["window"], tr["total"]
        same("treasury_spend rule in window = control map", tw["equals_control_map"], True)
        same("treasury_spend rule exact", rule["exact"], rule["epochs"])
        n.add("ts.rule_epochs", rule["epochs"], f_int(rule["epochs"]), tsrc, unit="epochs", **common,
              note="epochs in the window where treasury.near's reward equals "
                   "floor(floor(supply * dt / (40 * 365 days)) / 10), to the yocto")
        n.add("ts.rule_exact", rule["exact"], f_int(rule["exact"]), tsrc, unit="epochs", **common)
        n.add("ts.share_of_minted", rule["treasury_share_of_minted"],
              f_pct(rule["treasury_share_of_minted"], 2), tsrc, unit="share", **common,
              note="above 10% because validators below full uptime receive less than the maximum")
        for key in ("mean", "min", "max"):
            v = rule[f"unminted_share_of_max_{key}"]
            n.add(f"ts.unminted_share_of_max_{key}", v, f_pct(v, 2), tsrc, unit="share", **common)
        n.add("ts.window_other_net_near", tw["other_net_near"], f_num(tw["other_net_near"], 3), tsrc,
              unit="NEAR", **common, note="balance change minus protocol rewards in the window")
        months = td["months"]
        yc = {"window": f"{tot['from']} 00:00 UTC to {tot['to']} 00:00 UTC",
              "blocks": f"{months[0]['start']['height']}-{months[-1]['end']['height']}"}
        n.add("ts.year_treasury_in_near", tot["treasury_in_near"], f_int(tot["treasury_in_near"]),
              tsrc, unit="NEAR", **yc)
        out = -dec(tot["other_net_near"])
        n.add("ts.year_out_near", out, f_int(out), tsrc, unit="NEAR", **yc,
              note="minus other_net: what left treasury.near besides protocol rewards")
        rows = tr["months"]
        n.add("ts.balance_start_near", rows[0]["balance_start_near"],
              f_int(rows[0]["balance_start_near"]), tsrc, unit="NEAR", **yc)
        n.add("ts.balance_end_near", rows[-1]["balance_end_near"],
              f_int(rows[-1]["balance_end_near"]), tsrc, unit="NEAR", **yc)
        out_months = [r for r in rows if dec(r["other_net_near"]) != 0]
        n.add("ts.months_with_outflows", len(out_months), f_int(len(out_months)), tsrc,
              unit="months", **yc)
        for r in out_months:
            v = -dec(r["other_net_near"])
            n.add(f"ts.out_near.{r['start'][:7]}", v, f_int(v), tsrc, unit="NEAR",
                  window=f"{r['start']} 00:00 UTC to {r['end']} 00:00 UTC", blocks=yc["blocks"])
        epath = data_dir / "treasury_exits.json"
        if epath.exists():
            ed = json.loads(epath.read_text(encoding="utf-8"))
            esrc = n.source(epath)
            er = ed["results"]
            same("treasury_exits total = treasury_spend other_net", er["total_exits_near"],
                 f"{out:.3f}")
            n.add("te.steps", len(ed["exits"]), f_int(len(ed["exits"])), esrc,
                  unit="balance steps", **yc)
            big = [e for e in ed["exits"] if "recipients" in e]
            n.add("te.transactions_read", len(big), f_int(len(big)), esrc,
                  unit="transactions of 1 NEAR or more", **yc)
            for i, r in enumerate(er.get("recipients", []), 1):
                acct = r["account"]
                short = acct.split(".")[0] if not acct.startswith("sha256:") else \
                    "sha256_" + acct[len("sha256:"):][:8]
                n.add(f"te.to.{short}.amount", r["amount_near"], f_int(r["amount_near"]), esrc,
                      unit="NEAR", account=acct, transfers=r["transfers"], **yc)
                n.add(f"te.to.{short}.transfers", r["transfers"], f_int(r["transfers"]), esrc,
                      unit="transfers", account=acct, **yc)

    # ---- finding 6: reward units -> US dollars of credits (NEAR AI Cloud, off-chain snapshot)
    oc_meta = data_dir / "offchain" / "nearai_cloud_farm_config.json"
    if oc_meta.exists() and "f6.units_per_near_year" in n.items:
        om = json.loads(oc_meta.read_text(encoding="utf-8"))
        n.source(oc_meta)
        rawp = root / om["raw_file"]
        rsrc = n.source(rawp)
        if sha256_file(rawp) != om["sha256"]:
            problems.append("off-chain NEAR AI Cloud config: sha256 differs from its record")
        cfg = json.loads(rawp.read_bytes())
        same("off-chain config contract", cfg["contract_id"], "stake.dao")
        same("off-chain config farm product", cfg["farm_product_id"], stakers.FARM_PRODUCT)
        same("off-chain config farm price", cfg["farm_price_id"], stakers.FARM_PRICE)
        usd = dec(cfg["credit_nano_usd_per_reward_unit"]) / dec(10 ** 9)
        oc = {"status": "off-chain", "as_of": om["fetched_utc"],
              "note": "NEAR AI Cloud setting read in a signed-in session; not on chain, can change "
                      "without an on-chain trace (data/offchain/nearai_cloud_farm_config.json)"}
        n.add("f6.usd_per_reward_unit", usd, f_usd(usd, 2), rsrc, unit="USD per reward unit", **oc)
        per_month = dec(n.items["f6.units_per_near_year"]["value"]) * usd / 12
        n.add("f6.usd_per_near_month", per_month, f_usd(per_month, 2), rsrc,
              unit="USD of credits per staked NEAR per month", **oc)
        largest = dec(n.items["f6.largest_units_per_day"]["value"]) * usd
        n.add("f6.largest_usd_per_day", largest, f_usd(largest, 1), rsrc,
              unit="USD of credits per day, largest farm position", **oc)

    # ---- finding 5: concentration over time (every saved stakers snapshot)
    largest_by_date = []
    for path in sorted((data_dir / "stakers").glob("20*.json")):
        st, p = stakers.compute(path, data_dir.resolve())
        problems += [f"stakers {path.name}: {x}" for x in p]
        if not st:
            continue
        src = n.source(path)
        d = st["date"]
        n.add(f"f5.largest_share.{d}", st["largest_share"], f_pct(st["largest_share"]), src,
              unit="share of farm", block=st["block"])
        if "largest_near" in st and "largest_account" in st:
            n.add(f"f5.largest_near.{d}", st["largest_near"], f_int(st["largest_near"]), src,
                  unit="NEAR", block=st["block"])
            largest_by_date.append((d, st["largest_account"], src))
        n.add(f"f5.stakers_active.{d}", st["stakers_active"], f_int(st["stakers_active"]), src,
              unit="accounts", block=st["block"])
        if st.get("farm_units_per_near_year"):
            n.add(f"f6.units_per_near_year.{d}", st["farm_units_per_near_year"],
                  f_num(st["farm_units_per_near_year"], 2), src,
                  unit="reward units per staked NEAR per year", block=st["block"])

    if largest_by_date:
        end_tag = largest_by_date[-1][1]
        since = largest_by_date[-1][0]
        for d, t, _ in reversed(largest_by_date):
            if t != end_tag:
                break
            since = d
        n.add("f5.largest_same_account_since", since, since, largest_by_date[-1][2],
              note="first snapshot date from which the largest farm account is the same tag as "
                   "at the end block")
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
        n.add(f"f1.buybacks_kept_near_per_day.{m}", r["buybacks_per_day"], f_int(r["buybacks_per_day"]),
              csrc, unit="NEAR/day", blocks=extra["blocks"], flags=extra["flags"],
              note="buybacks wallet + 1Click fund, net change in the calendar month / days")
    # the latest month against the one before: the series is not monotone (judge #9, finding 3)
    if len(cov["rows"]) >= 2:
        r0, r1 = cov["rows"][-2], cov["rows"][-1]
        ch = dec(r1["buybacks_per_day"]) / dec(r0["buybacks_per_day"]) - 1
        n.add(f"f1.change.{r0['month']}_{r1['month']}.buybacks_kept_near", ch,
              ("+" if ch > 0 else "") + f_pct(ch, 0), csrc, unit="relative change",
              derived_from=[f"f1.buybacks_kept_near_per_day.{r0['month']}",
                            f"f1.buybacks_kept_near_per_day.{r1['month']}"])

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
                ("revenue_near_per_day", "revenue_near_per_day", f_int, "NEAR/day"),
                ("fees_near_per_day", "fees_near_per_day", f_int, "NEAR/day")):
            if field not in m:
                continue
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
    # H2: what the wallets kept of DefiLlama's revenue over every month with both,
    # as totals (per-day x calendar days), so long months weigh more than short ones.
    # Same rule as the monthly share: wallets on every day, DefiLlama's mean over its
    # counted days; days DefiLlama left out are listed in excluded_days.
    both = sorted(k for k in fmon if k in kept_by_month)
    if both:
        kept_tot = sum(kept_by_month[k] * fmon[k]["days"] for k in both)
        rev_tot = sum(dec(fmon[k]["revenue_near_per_day"]) * fmon[k]["days"] for k in both)
        span = f"{both[0]}_{both[-1]}"
        sc = {"status": status, "fetched_utc": fees["fetched_utc"], "months": both,
              "days": sum(fmon[k]["days"] for k in both),
              "excluded_days": sorted(d for k in both for d in fmon[k]["excluded"])}
        lowest = min(both, key=lambda k: kept_by_month[k] / dec(fmon[k]["revenue_near_per_day"]))
        n.add(f"f2.wallets_kept_near.{span}", kept_tot, f_int(kept_tot), csrc, unit="NEAR",
              note="buybacks + 1cs + fefundsadmin, net balance change, sum of months", **sc)
        n.add(f"f2.revenue_near.{span}", rev_tot, f_int(rev_tot), fsrc, unit="NEAR",
              note="DefiLlama revenue in NEAR (daily revenue / daily price), mean over counted "
                   "days x days in month, sum of months", **sc)
        n.add(f"f2.wallets_kept_share_of_revenue.{span}", kept_tot / rev_tot,
              f_pct(kept_tot / rev_tot), fsrc, unit="wallets NEAR / DefiLlama revenue NEAR",
              also=csrc, lowest_month=lowest, **sc)
        n.add(f"f2.revenue_not_kept_near.{span}", rev_tot - kept_tot, f_int(rev_tot - kept_tot),
              fsrc, unit="NEAR", also=csrc,
              note="revenue minus what the wallets kept: payments out (e.g. to third parties), "
                   "timing at month edges and DefiLlama attribution together; not split", **sc)
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

    # ---- control map: who can change each link, as k of n (control_map.py), end block
    cm_path = data_dir / "control_map.json"
    if cm_path.exists():
        cm = json.loads(cm_path.read_text(encoding="utf-8"))
        csrc = n.source(cm_path)
        same("control map block", cm["block"]["height"], last_b["height"])
        same("control map window file", cm["window_file"], wsrc)
        if not all(cm["checks"].values()):
            problems.append("control_map.json: a check failed")
        L = cm["links"]
        cc = {"block": cm["block"]["height"], "as_of": cm["block"]["timestamp_utc"][:19] + "Z"}

        def kn(x):
            return None if x is None else f"{x['k']} of {x['n']}"

        def add_kn(key, x, **extra):
            n.add(key, kn(x), kn(x), csrc, role=None if x is None else x["role"], **cc, **extra)

        def add_int(key, v, unit):
            n.add(key, v, f_int(v), csrc, unit=unit, **cc)

        fee, code = L["intents_protocol_fee"], L["intents_code"]
        ctl = code["controller"]
        n.add("c.intents_fee_pips", fee["value"]["fee_pips"], f"{fee['value']['fee_pips']} pip",
              csrc, unit="pips (1,000,000 = 100%)", **cc)
        n.add("c.intents_fee_percent", fee["value"]["fee_percent"],
              fee["value"]["fee_percent"] + "%", csrc, unit="percent", **cc)
        add_kn("c.intents_fee_change", next(iter(fee["via"].values())),
               note="role DAO on intents.near = intents.sputnik-dao.near, call proposal")
        add_int("c.intents_fees_manager_accounts", fee["fees_manager_grantees"]["total"], "accounts")
        add_kn("c.intents_code_add_release", next(iter(ctl["add_release"].values())),
               note="add_release_info on ctl-intents.near needs role DAO")
        add_int("c.intents_code_updater_accounts", ctl["updater_grantees"]["total"], "accounts")
        add_int("c.intents_code_downgrader_accounts", ctl["downgrader_grantees"]["total"],
                "accounts")
        add_int("c.intents_code_changes", code["code_changes"], "upgrades and downgrades")
        n.add("c.intents_code_last_change_utc", code["last_upgrade_utc"],
              code["last_upgrade_utc"][:10], csrc, **cc)
        n.add("c.intents_code_version", code["deployed_version"], code["deployed_version"],
              csrc, **cc)
        m = L["buybacks_wallet"]["multisig"]
        n.add("c.buybacks_confirmations", f"{m['confirmations']} of {m['member_keys']}",
              f"{m['confirmations']} of {m['member_keys']}", csrc, unit="multisig keys", **cc)
        add_int("c.buybacks_full_access_keys", m["full_access_keys"], "keys")
        add_kn("c.wallet_1cs_transfer", L["wallet_1cs"]["dao"])
        add_kn("c.wallet_1cs_rules", L["wallet_1cs"]["rules"])
        add_kn("c.front_end_transfer", L["wallet_front_end"]["dao"])
        add_kn("c.front_end_rules", L["wallet_front_end"]["rules"])
        i = L["issuance"]
        for key, val in (("max_inflation_rate", i["max_inflation_rate"]),
                         ("upgrade_stake_threshold", i["protocol_upgrade_stake_threshold"])):
            n.add(f"c.issuance_{key}", val, val, csrc, **cc)
        for key, field in (("validators", "validators"),
                           ("validators_to_pass_upgrade", "validators_to_reach_threshold"),
                           ("validators_to_block_upgrade", "validators_to_block_upgrade"),
                           ("validators_to_reach_two_thirds", "validators_to_reach_two_thirds"),
                           ("validators_to_exceed_one_third", "validators_to_exceed_one_third")):
            add_int(f"c.issuance_{key}", i[field], "validators")
        n.add("c.issuance_largest_validator_share", i["largest_validator_share"],
              f_pct(i["largest_validator_share"]), csrc, unit="share of stake", **cc)
        if "total_stake_near" in i:
            n.add("c.issuance_total_stake_near", i["total_stake_near"], f_int(i["total_stake_near"]),
                  csrc, unit="NEAR", note="stake of the current validators of the end block's "
                  "epoch", **cc)
            n.add("c.issuance_staked_share", i["staked_share_of_supply"],
                  f_pct(i["staked_share_of_supply"]), csrc, unit="share of total supply",
                  note="c.issuance_total_stake_near / total_supply at the end block", **cc)
        t = L["protocol_treasury"]
        tw = {"window": common["window"], "blocks": common["blocks"]}
        n.add("c.treasury_share_of_new_supply", t["share_of_new_supply"],
              f_pct(t["share_of_new_supply"]), csrc, unit="share", **tw,
              note="treasury.near balance change / total_supply change; RPC protocol_reward_rate "
                   "reports " + t["reported_protocol_reward_rate"] + " and is not used")
        n.add("c.treasury_near_received", t["balance_change_near"], f_int(t["balance_change_near"]),
              csrc, unit="NEAR", **tw)
        tm = t["multisig"]
        n.add("c.treasury_confirmations", f"{tm['confirmations']} of {tm['member_keys']}",
              f"{tm['confirmations']} of {tm['member_keys']}", csrc, unit="multisig keys", **cc)
        h = L["hsp_voting"]
        add_kn("c.hsp_owner_rules", h["owner_dao"])
        add_int("c.hsp_reviewers", h["reviewers"], "accounts")
        add_int("c.hsp_guardians", h["guardians"], "accounts")
        pl = L["nearai_pool_rewards"]
        num, den = (int(x) for x in pl["reward_fee"].split("/"))
        n.add("c.nearai_pool_reward_fee", pl["reward_fee"], f_pct(dec(num) / dec(den), 0), csrc,
              unit="share of rewards kept by the pool owner", **cc)
        add_kn("c.nearai_pool_owner_transfer", pl["owner_dao"])
        add_kn("c.nearai_pool_owner_rules", pl["owner_rules"])
        fc = L["farm_contract"]
        add_int("c.farm_contract_full_access_keys", fc["full_access_keys"], "keys")
        add_int("c.farm_contract_guardians", fc["guardians"], "accounts")
        # Members of the five DAOs that run the links, from the redacted get_policy copies
        # (accounts as sha256 tags, the same tag for the same account): distinct accounts,
        # and how many sit in more than one DAO. Counts only; no list is published.
        pol = {k.split("/")[0]: f for k, f in cm.get("raw_files", {}).items()
               if k.endswith("/get_policy") and "redacted" in f}
        if pol:
            seen = {}
            for dao, f in sorted(pol.items()):
                rp = root / f["redacted"]["path"]
                if not rp.exists() or sha256_file(rp) != f["redacted"]["sha256"]:
                    problems.append(f"control map: redacted policy of {dao} missing or changed")
                    continue
                n.source(rp)
                roles = json.loads(rp.read_text(encoding="utf-8"))["redacted_value"]["roles"]
                for r in roles:
                    kind = r["kind"]
                    if isinstance(kind, dict) and "Group" in kind:
                        for acct in kind["Group"]:
                            seen.setdefault(acct, set()).add(dao)
            add_int("c.dao_count", len(pol), "DAOs")
            add_int("c.dao_member_accounts", len(seen), "accounts")
            add_int("c.dao_members_in_two_or_more", sum(1 for d in seen.values() if len(d) > 1),
                    "accounts")
    else:
        n.add("c.intents_fee_change", None, None, None, status="pending",
              note="control_map.py has not run")

    # ---- control history: how often each lever was used (control_history.py), end block
    ch_path = data_dir / "control_history.json"
    if ch_path.exists():
        chd = json.loads(ch_path.read_text(encoding="utf-8"))
        hsrc3 = n.source(ch_path)
        same("control history block", chd["block"]["height"], last_b["height"])
        same("control history window file", chd["window_file"], wsrc)
        if not all(chd["checks"].values()):
            problems.append("control_history.json: a check failed")
        hc3 = {"block": chd["block"]["height"], "as_of": chd["block"]["timestamp_utc"][:19] + "Z",
               "note": "approved actions in the control map's DAOs; dates are submission dates"}
        n.add("h.proposals_total", sum(d["proposals"] for d in chd["per_dao"].values()),
              f_int(sum(d["proposals"] for d in chd["per_dao"].values())), hsrc3,
              unit="proposals", **hc3)
        for lever, v in chd["all_daos"].items():
            n.add(f"h.{lever}.approved_actions", v["approved_actions"], f_int(v["approved_actions"]),
                  hsrc3, unit="actions", **hc3)
            if v["approved_actions"]:
                n.add(f"h.{lever}.first", v["first"], v["first"], hsrc3, **hc3)
                n.add(f"h.{lever}.last", v["last"], v["last"], hsrc3, **hc3)
        a = chd["all_daos"]
        for key, lever, method in (
                ("set_fee", "fee", "intents.near.set_fee"),
                ("set_fee_collector", "fee", "intents.near.set_fee_collector"),
                ("add_release_info", "code", "ctl-intents.near.add_release_info"),
                ("intents_acl_grant_role", "roles", "intents.near.acl_grant_role"),
                ("catalog_manager_added", "roles", "stake.dao.add_validator_catalog_manager"),
                ("ft_force_withdraw", "user_funds", "intents.near.ft_force_withdraw"),
                ("mt_force_transfer", "user_funds", "intents.near.mt_force_transfer"),
                ("pause_feature", "pause", "intents.near.pa_pause_feature"),
                ("unpause_feature", "pause", "intents.near.pa_unpause_feature")):
            val = a[lever]["by_method"].get(method, 0)
            n.add(f"h.{key}", val, f_int(val), hsrc3, unit="actions", **hc3)
        cc3 = chd["intents_code_changes"]
        n.add("h.intents_code_changes", cc3["count"], f_int(cc3["count"]), hsrc3,
              unit="executed upgrades and downgrades", **hc3)
        n.add("h.intents_code_downgrades", cc3["downgrades"], f_int(cc3["downgrades"]), hsrc3,
              unit="downgrades", **hc3)
        short = {"buybacks.multisignature.near": "buybacks", "treasury.near": "treasury",
                 "stake.dao": "stake_dao", "ctl-intents.near": "ctl_intents",
                 "intents.near": "intents", "nearai.pool.near": "nearai_pool", "vote.dao": "vote_dao"}
        for acc, kh in (chd.get("key_history") or {}).items():
            k = f"h.keys.{short.get(acc, acc)}"
            if kh["matches_chain_at_end_block"] is not True:
                n.add(f"{k}.ever", None, None, hsrc3, status="not-measured", **hc3,
                      reason="NearBlocks key list does not match the chain at the end block")
                continue
            kc = {**hc3, "note": "access keys from NearBlocks up to the end block's time; active "
                                 "keys checked against the chain at the end block"}
            n.add(f"{k}.ever", kh["keys_ever"], f_int(kh["keys_ever"]), hsrc3, unit="keys", **kc)
            n.add(f"{k}.full_access_ever", kh["full_access_ever"], f_int(kh["full_access_ever"]),
                  hsrc3, unit="keys", **kc)
            n.add(f"{k}.active_at_end", kh["active_at_end"], f_int(kh["active_at_end"]), hsrc3,
                  unit="keys", **kc)
            if kh["last_change"]:
                n.add(f"{k}.last_change", kh["last_change"], kh["last_change"], hsrc3, **kc)
    else:
        n.add("h.proposals_total", None, None, None, status="pending",
              note="control_history.py has not run")

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
        tl = (h.get("proposal") or {}).get("timelock_end_utc")
        if tl:
            n.add("f8.timelock_end_utc", tl, tl[:10] + " " + tl[11:16] + " UTC", hsrc2,
                  note="voting end + vote.dao's timelock_duration_ns, from get_proposal", **hc)
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

    # ---- investment view: how far today's figures are from full coverage (derived only)
    def derive(key, value, of, note):
        base = n.items[of[0]]
        extra = {k: base[k] for k in ("window", "blocks", "status") if k in base}
        if any(n.items[k].get("status") == "provisional" for k in of):
            extra["status"] = "provisional"
        n.add(key, value, "×" + f_num(value, 1), base["source"], unit="multiple",
              derived_from=list(of), note=note, **extra)

    cov_b = dec(n.items["n1.coverage_buybacks"]["value"])
    cov_fe = dec(n.items["n1.coverage_with_front_end"]["value"])
    max_cov = dec(n.items["n2.max_coverage"]["value"])
    hsp_cov = dec(n.items["n2.hsp029_max_coverage"]["value"])
    derive("iv.wallets_multiple_buybacks", 1 / cov_b, ["n1.coverage_buybacks"],
           "1 / n1.coverage_buybacks: growth the buybacks wallets' NEAR per day needs for 100% "
           "coverage at today's issuance")
    derive("iv.wallets_multiple_with_front_end", 1 / cov_fe, ["n1.coverage_with_front_end"],
           "1 / n1.coverage_with_front_end")
    derive("iv.fees_multiple", 1 / max_cov, ["n2.max_coverage"],
           "1 / n2.max_coverage: growth all fees (in NEAR) need for 100% coverage if NEAR "
           "kept every fee")
    derive("iv.hsp029_fees_multiple", 1 / hsp_cov, ["n2.hsp029_max_coverage"],
           "1 / n2.hsp029_max_coverage")
    # Lever model inputs (dashboard): what share of all fees the wallets keep, and the price
    # at which DefiLlama's fees were converted to NEAR (fees in USD / fees in NEAR). With
    # them, coverage = fees_usd x growth x kept / price / (issuance x factor) reproduces
    # n2.max_coverage, n2.hsp029_max_coverage and the equilibrium prices exactly.
    prov = {"status": n.items["n2.max_coverage"]["status"], "window": n.items["n2.max_coverage"].get("window"),
            "blocks": n.items["n2.max_coverage"].get("blocks")}
    for key, cov, of in (("iv.wallets_share_of_fees_buybacks", cov_b, "n1.coverage_buybacks"),
                         ("iv.wallets_share_of_fees_with_front_end", cov_fe, "n1.coverage_with_front_end")):
        n.add(key, cov / max_cov, f_pct(cov / max_cov), n.items[of]["source"], unit="share of all fees",
              derived_from=[of, "n2.max_coverage"], note=f"{of} / n2.max_coverage", **prov)
    fusd = dec(n.items["n2.fees_usd_per_day"]["value"])
    fnear = dec(n.items["n2.fees_near_per_day"]["value"])
    n.add("iv.fees_conversion_price_usd", fusd / fnear, f_usd(fusd / fnear, 2),
          n.items["n2.fees_usd_per_day"]["source"], unit="USD per NEAR",
          derived_from=["n2.fees_usd_per_day", "n2.fees_near_per_day"],
          note="n2.fees_usd_per_day / n2.fees_near_per_day: each day's fees at that day's price", **prov)
    new_day = dec(n.items["n1.new_near_per_day"]["value"])
    supply_end = dec(last_b["total_supply_yocto"]) / dec(10 ** 24)
    year_rate = new_day * dec("365.25") / supply_end
    n.add("iv.issuance_rate_per_year", year_rate, f"{rnd(year_rate * 100, 2)}%",
          n.items["n1.new_near_per_day"]["source"], unit="share of total supply per year",
          note="n1.new_near_per_day x 365.25 / total_supply at the end block", **common)
    n.add("iv.buybacks_offset_points_per_year", cov_b * year_rate,
          f"{rnd(cov_b * year_rate * 100, 2)}", n.items["n1.coverage_buybacks"]["source"],
          unit="percentage points of supply per year",
          note="n1.coverage_buybacks x iv.issuance_rate_per_year", **common)
    rev = dec(n.items["n2.revenue_usd_per_day"]["value"])
    n.add("iv.revenue_equilibrium_price_usd", rev / new_day, f_usd(rev / new_day, 2),
          n.items["n2.revenue_usd_per_day"]["source"], unit="USD",
          note="n2.revenue_usd_per_day / n1.new_near_per_day: the price at which DefiLlama "
               "revenue buys as many NEAR as are issued",
          status=n.items["n2.revenue_usd_per_day"]["status"],
          window=common["window"], blocks=common["blocks"])
    # Valuation in the same window: the market value of all NEAR in total_supply at the
    # window's mean price, against what fees, revenue and the wallets bring in a year.
    # total_supply, not circulating supply: circulating supply needs an off-chain source.
    price = dec(n.items["n2.mean_price_usd"]["value"])
    value = supply_end * price
    vsrc = n.items["n2.mean_price_usd"]["source"]
    n.add("iv.supply_value_usd", value, f"${rnd(value / 10 ** 9, 2)}B", vsrc, unit="USD",
          derived_from=["n2.mean_price_usd"],
          note="total_supply at the end block x n2.mean_price_usd (mean of the window's daily "
               "prices); all NEAR, not circulating supply", **prov)
    kept_day = (dec(n.items["n1.buybacks_near_per_day"]["value"])
                + dec(n.items["n1.front_end_near_per_day"]["value"]))
    yearly = (
        ("iv.issuance_usd_per_year", new_day * price, ["n1.new_near_per_day", "n2.mean_price_usd"],
         "n1.new_near_per_day x n2.mean_price_usd x 365.25: what a year of issuance is worth"),
        ("iv.fees_usd_per_year", fusd, ["n2.fees_usd_per_day"], "n2.fees_usd_per_day x 365.25"),
        ("iv.revenue_usd_per_year", rev, ["n2.revenue_usd_per_day"],
         "n2.revenue_usd_per_day x 365.25"),
        ("iv.wallets_kept_usd_per_year", kept_day * price,
         ["n1.buybacks_near_per_day", "n1.front_end_near_per_day", "n2.mean_price_usd"],
         "(n1.buybacks_near_per_day + n1.front_end_near_per_day) x n2.mean_price_usd x 365.25: "
         "what the three wallets kept, in dollars"),
    )
    for key, per_day, of, note in yearly:
        per_year = per_day * dec("365.25")
        n.add(key, per_year, f"${rnd(per_year / 10 ** 6, 1)}M", vsrc, unit="USD per year",
              derived_from=of, note=note, **prov)
        if key != "iv.issuance_usd_per_year":
            mkey = "iv.value_to_" + key[3:].replace("_usd_per_year", "")
            n.add(mkey, value / per_year, f"{rnd(value / per_year, 0):,.0f}×", vsrc, unit="multiple",
                  derived_from=["iv.supply_value_usd", key],
                  note=f"iv.supply_value_usd / {key}", **prov)
    # Buyback yield: what the wallets keep a year in dollars / the value of all NEAR. Coverage is
    # exactly this yield / the issuance rate, so it falls when the price rises and revenue does not.
    rate = n.items["iv.issuance_rate_per_year"]["value"]
    for name, near_day, cov_key in (
            ("buybacks", dec(n.items["n1.buybacks_near_per_day"]["value"]), "n1.coverage_buybacks"),
            ("with_front_end", kept_day, "n1.coverage_with_front_end")):
        usd_day = near_day * price
        y = usd_day * dec("365.25") / value
        if name == "buybacks":
            n.add("iv.buybacks_kept_usd_per_day", usd_day, f_usd(usd_day), vsrc, unit="USD/day",
                  derived_from=["n1.buybacks_near_per_day", "n2.mean_price_usd"],
                  note="n1.buybacks_near_per_day x n2.mean_price_usd", **prov)
            new_near = dec(n.items["n1.new_near_per_day"]["value"])
            n.add("iv.buybacks_equilibrium_price_usd", usd_day / new_near, f_usd(usd_day / new_near, 2), vsrc,
                  unit="USD", derived_from=["iv.buybacks_kept_usd_per_day", "n1.new_near_per_day"],
                  note="the NEAR price at which the dollars the buybacks wallets keep a day buy as many NEAR "
                       "as are issued: the Buy-on-price threshold of the rating", **prov)
        n.add(f"iv.buyback_yield_{name}", y, f_pct(y, 2), vsrc, unit="share of value per year",
              derived_from=[cov_key, "n2.mean_price_usd", "iv.supply_value_usd"],
              note="what the wallets keep a year, in dollars / iv.supply_value_usd", **prov)
        n.add(f"iv.net_dilution_{name}", dec(rate) - y, f_pct(dec(rate) - y, 2), vsrc,
              unit="share of supply per year", derived_from=["iv.issuance_rate_per_year", f"iv.buyback_yield_{name}"],
              note="iv.issuance_rate_per_year - buyback yield: about how fast NEAR outside the wallets grows, while the wallets keep what they buy; total supply grows by the full issuance rate", **prov)
        cov_v = dec(n.items[cov_key]["value"])
        if abs(y / dec(rate) - cov_v) > dec("0.0000006"):
            problems.append(f"buyback yield / issuance rate != {cov_key}: {y / dec(rate)} vs {cov_v}")
    # The buybacks wallets' keep in dollars, month by month (balances x the month's mean price)
    for row_m in json.loads((data_dir / "coverage_monthly.json").read_text(encoding="utf-8"))["rows"]:
        mk = f"f2.mean_price_usd.{row_m['month']}"
        if mk in n.items:
            usd = dec(row_m["buybacks_per_day"]) * dec(n.items[mk]["value"])
            n.add(f"f2.buybacks_kept_usd_per_day.{row_m['month']}", usd, f_usd(usd), n.items[mk]["source"],
                  unit="USD/day", derived_from=[f"f1.coverage_buybacks.{row_m['month']}", mk],
                  note="buybacks wallets' NEAR kept a day in the calendar month x the month's mean price",
                  status=n.items[mk].get("status"))
    if "c.issuance_total_stake_near" in n.items:
        stake = dec(n.items["c.issuance_total_stake_near"]["value"])
        farm = dec(n.items["n3.farm_total_near"]["value"])
        n.add("iv.farm_share_of_stake", farm / stake, f_pct(farm / stake, 2),
              n.items["n3.farm_total_near"]["source"], unit="share of stake",
              note="n3.farm_total_near / c.issuance_total_stake_near (same end block)")
    if "c.issuance_total_stake_near" in n.items and "b.minted_near_per_day" in n.items:
        # Validators are paid from gross minting (before gas is burnt), less treasury.near's
        # reward; net issuance would understate what they receive by the gas burnt.
        to_treasury = new_day * dec(n.items["c.treasury_share_of_new_supply"]["value"])
        to_val = dec(n.items["b.minted_near_per_day"]["value"]) - to_treasury
        y = to_val * dec("365.25") / stake
        n.add("iv.staking_yield_gross", y, f_pct(y), n.items["c.issuance_total_stake_near"]["source"],
              unit="share of stake per year",
              derived_from=["b.minted_near_per_day", "n1.new_near_per_day",
                            "c.treasury_share_of_new_supply", "c.issuance_total_stake_near"],
              note="(gross NEAR minted per day - NEAR per day kept by treasury.near) x 365.25 / "
                   "stake of the current validators; before validator commissions and downtime")
        # NEAR price at which a farm staker's credits are worth as much as a validator's
        # NEAR rewards (before commission): credits per NEAR a year / staking yield.
        if "f6.usd_per_reward_unit" in n.items:
            usd = dec(n.items["f6.usd_per_reward_unit"]["value"])
            oc = {k: n.items["f6.usd_per_reward_unit"][k] for k in ("status", "as_of")}
            units = dec(n.items["f6.units_per_near_year"]["value"])
            n.add("iv.farm_breakeven_price_usd", units * usd / y, f_usd(units * usd / y, 2),
                  n.items["f6.usd_per_reward_unit"]["source"], unit="USD per NEAR",
                  derived_from=["f6.units_per_near_year", "f6.usd_per_reward_unit",
                                "iv.staking_yield_gross"],
                  note="below this NEAR price the farm's credits pay more than staking with a "
                       "validator (before commission); above it, less", **oc)
            if "f6.change1.units_per_near_year_before" in n.items:
                ub = dec(n.items["f6.change1.units_per_near_year_before"]["value"])
                n.add("iv.farm_breakeven_price_before_usd", ub * usd / y, f_usd(ub * usd / y, 2),
                      n.items["f6.usd_per_reward_unit"]["source"], unit="USD per NEAR",
                      derived_from=["f6.change1.units_per_near_year_before",
                                    "f6.usd_per_reward_unit", "iv.staking_yield_gross"],
                      note="the same break-even with the rate before its only change, at "
                           "today's staking yield", **oc)
    derive("iv.hsp029_wallets_multiple_with_front_end", (1 / cov_fe) * (max_cov / hsp_cov),
           ["n1.coverage_with_front_end", "n2.max_coverage", "n2.hsp029_max_coverage"],
           "(1 / n1.coverage_with_front_end) x issuance ratio of the HSP-029 scenario "
           "(n2.max_coverage / n2.hsp029_max_coverage)")

    # ---- issuance to 2031 under today's rule and HSP-029 (longrun.py): rules, no forecast
    need = ["c.issuance_max_inflation_rate", "b.epochs", "f8.timelock_end_utc",
            "iv.staking_yield_gross", "n2.fees_near_per_day"]
    if all(k in n.items and n.items[k]["value"] is not None for k in need):
        from datetime import date as _date, datetime as _dt, timezone as _tz
        from fractions import Fraction
        v = lambda k: dec(n.items[k]["value"])  # noqa: E731
        days = (_date.fromisoformat(end_date) - _date.fromisoformat(start_date)).days
        ratified = _dt.fromisoformat(re.sub(r"(\.\d{6})\d*Z$", r"\1+00:00",
                                            n.items["f8.timelock_end_utc"]["value"]))
        kept = {"buybacks": v("n1.buybacks_near_per_day"),
                "with_front_end": v("n1.buybacks_near_per_day") + v("n1.front_end_near_per_day"),
                "all_fees": v("n2.fees_near_per_day")}
        history = {}
        for name, key in (("kept", "f2.wallets_kept_near_per_day"), ("fees_near", "f2.fees_near_per_day"),
                          ("fees_usd", "f2.fees_usd_per_day"), ("revenue_usd", "f2.revenue_usd_per_day"),
                          ("volume_usd", "f2.volume_usd_per_day"), ("buybacks_kept_usd", "f2.buybacks_kept_usd_per_day"),
                          ("take_rate", "f2.take_rate"), ("kept_share", "f2.wallets_kept_share_of_revenue")):
            if f"{key}.2026-04" in n.items and f"{key}.2026-10" in n.items:
                history[name] = (v(f"{key}.2026-04"), v(f"{key}.2026-10"))
        # the dollar multiple split in two: NEAR the buybacks wallets kept a day, and the mean price
        if "f2.mean_price_usd.2026-04" in n.items and "f2.mean_price_usd.2026-10" in n.items:
            history["mean_price"] = (v("f2.mean_price_usd.2026-04"), v("f2.mean_price_usd.2026-10"))
        _bb = {r["month"]: dec(r["buybacks_per_day"]) for r in json.loads(
            (data_dir / "coverage_monthly.json").read_text(encoding="utf-8"))["rows"]}
        if "2026-04" in _bb and "2026-10" in _bb:
            history["buybacks_kept_near"] = (_bb["2026-04"], _bb["2026-10"])
        res = longrun.model(supply_end, new_day, Fraction(n.items["c.issuance_max_inflation_rate"]["value"]),
                            dec(days) / v("b.epochs"),
                            _dt.fromisoformat(f"{end_date}T00:00:00+00:00"), ratified, kept,
                            v("iv.staking_yield_gross"), v("iv.wallets_share_of_fees_with_front_end"),
                            history)
        problems += [f"longrun: {x}" for x in longrun.check(res)]
        # the same hurdles from each month April-October, and from their day-weighted average
        bases, days_sum, acc = {}, 0, {"buybacks": dec(0), "with_front_end": dec(0)}
        month_rows = json.loads((data_dir / "coverage_monthly.json").read_text(encoding="utf-8"))["rows"]
        for row_m in month_rows:
            y, mo = map(int, row_m["month"].split("-"))
            if (y, mo) < (2026, 4):
                continue
            lvl = {"buybacks": dec(row_m["buybacks_per_day"]),
                   "with_front_end": dec(row_m["buybacks_per_day"]) + dec(row_m["fefunds_per_day"])}
            bases[row_m["month"]] = lvl
            nd = (_date(y + mo // 12, mo % 12 + 1, 1) - _date(y, mo, 1)).days
            days_sum += nd
            for k in acc:
                acc[k] += lvl[k] * nd
        if len(bases) > 1:
            first, last = min(bases), max(bases)
            bases[f"{first}_{last}"] = {k: v / days_sum for k, v in acc.items()}
            res.update(longrun.base_sensitivity(res, bases))
        mean_price = v("n2.mean_price_usd")
        res.update(longrun.usd_scenarios(res, {
            "buybacks": kept["buybacks"] * mean_price, "with_front_end": kept["with_front_end"] * mean_price,
            "all_fees": v("n2.fees_usd_per_day")}))
        lsrc = n.items["n1.new_near_per_day"]["source"]
        fmt = {"ratio": lambda x: f_num(x, 4), "days": lambda x: f_num(x, 4),
               "utc": lambda x: x.strftime("%Y-%m-%d %H:%M UTC"), "near": f_int,
               "million": lambda x: f"{rnd(x / 10 ** 6, 2)}M",
               "signed_pct": lambda x: f"{rnd(x * 100, 1):+.1f}%",
               "multiple": lambda x: "×" + f_num(x, 1), "growth": lambda x: f"{rnd(x * 100, 0):+.0f}%",
               "pct": f_pct, "usd2": lambda x: f_usd(x, 2)}
        lstatus = {k: n.items["n2.max_coverage"][k] for k in ("status",) if k in n.items["n2.max_coverage"]}
        for key, (value, kind, extra) in res.items():
            val = value.isoformat() if kind == "utc" else value
            n.add(key, val, fmt[kind](value), lsrc, unit=kind, **extra, **lstatus)

    # ---- peers on one basis (peers.py): DefiLlama flows and value at the mean price, both over the window
    ppath2 = data_dir / "peers.json"
    if ppath2.exists():
        pe = json.loads(ppath2.read_text(encoding="utf-8"))
        pesrc = n.source(ppath2)
        same("peers window", (pe["window"]["start"], pe["window"]["end"]), (str(start_date), str(end_date)))
        big = lambda x: "$0" if x == 0 else f"${rnd(x / 10 ** 9, 2)}B" if x >= 10 ** 9 else f"${rnd(x / 10 ** 6, 1)}M"
        nr = pe["results"]["near"]
        for key, ours in (("fees_usd_per_year", "iv.fees_usd_per_year"), ("revenue_usd_per_year", "iv.revenue_usd_per_year")):
            if abs(Decimal(nr[key]) / Decimal(n.items[ours]["value"]) - 1) > Decimal("0.001"):
                problems.append(f"peers.json: NEAR {key} differs from {ours} by more than 0.1%")
        if nr.get("mean_price_usd") and abs(Decimal(nr["mean_price_usd"]) / Decimal(n.items["n2.mean_price_usd"]["value"]) - 1) > Decimal("0.001"):
            problems.append("peers.json: NEAR's mean price differs from n2.mean_price_usd by more than 0.1%")
        for pid, r in pe["results"].items():
            if r.get("partial"):
                problems.append(f"peers.json: {pid} lacks some days of the window")
            pc2 = {"label": r["label"], "value_as_of": r["value_as_of"], "window": "2026-10-02_2026-11-01",
                   "basis": "DefiLlama flows over the window x 365.25; value = CoinGecko supply at the fetch x the "
                            "window's mean price (coins.llama.fi); *_at_fetch = CoinGecko value at the fetch"}
            for key, kind in (("fees_usd_per_year", "big"), ("revenue_usd_per_year", "big"),
                              ("holders_revenue_usd_per_year", "big"), ("market_cap_usd", "big"),
                              ("fdv_usd", "big"), ("price_usd", "price"), ("mcap_to_revenue", "x"),
                              ("fdv_to_revenue", "x"), ("mcap_to_fees", "x"), ("holders_yield_on_mcap", "pct"),
                              ("mean_price_usd", "price"), ("market_cap_at_fetch_usd", "big"),
                              ("fdv_at_fetch_usd", "big"), ("mcap_at_fetch_to_revenue", "x")):
                v = r.get(key)
                if v is None:
                    n.add(f"peer.{pid}.{key}", None, "not published", pesrc, **pc2)
                    continue
                d = Decimal(v)
                txt = {"big": big, "price": lambda x: f_usd(x, 2), "x": lambda x: f"{rnd(x, 0):,.0f}×",
                       "pct": lambda x: f_pct(x, 2)}[kind](d)
                n.add(f"peer.{pid}.{key}", d, txt, pesrc, **pc2)
        n.add("peer.value_as_of", pe["fetched_utc"], pe["fetched_utc"][:16].replace("T", " ") + " UTC", pesrc)

    # ---- backtest (backtest.py): the rating rules on each calendar month April-October 2026
    btpath = data_dir / "backtest.json"
    if btpath.exists():
        bt = json.loads(btpath.read_text(encoding="utf-8"))
        btsrc, bs = n.source(btpath), bt["summary"]
        bc = {"note": "rating.evaluate on calendar months; see differences_from_rating_py in backtest.json"}
        n.add("bt.months", bs["months"], f_int(bs["months"]), btsrc, **bc)
        for k in ("Hold", "Buy", "Avoid"):
            n.add(f"bt.{k.lower()}", bs["ratings"][k], f_int(bs["ratings"][k]), btsrc, **bc)
        n.add("bt.rule_b_months", bs["rule_b_months"], f_int(bs["rule_b_months"]), btsrc, **bc)
        n.add("bt.months_failing", len(bs["months_failing_an_avoid_test"]),
              f_int(len(bs["months_failing_an_avoid_test"])), btsrc,
              months=bs["months_failing_an_avoid_test"], **bc)
        n.add("bt.lowest_kept_share", dec(bs["lowest_kept_share"]), f_pct(dec(bs["lowest_kept_share"]), 0), btsrc,
              month=bs["lowest_kept_share_month"], **bc)
        n.add("bt.highest_coverage_counted", dec(bs["highest_coverage_counted"]),
              f_pct(dec(bs["highest_coverage_counted"]), 1), btsrc, month=bs["highest_coverage_counted_month"], **bc)
        ap = bs["a_pace"]
        for k, places in (("usd_multiple", 1), ("near_multiple", 1), ("required_multiple", 2)):
            n.add(f"bt.a_pace.{k}", dec(ap[k]), "×" + f_num(dec(ap[k]), places), btsrc,
                  from_month=ap["from_month"], to_month=ap["to_month"], days=ap["days"],
                  note="sensitivity, not a rule: the (a) growth (+" + f_pct(dec(ap["required_growth_a_year"]), 0)
                       + " a year) applied from the first to the last month")

    # ---- demand (demand.py): NEAR Intents' 30 days of volume against DefiLlama's bridge and aggregator lists
    dpath = data_dir / "demand.json"
    if dpath.exists():
        dm = json.loads(dpath.read_text(encoding="utf-8"))
        dsrc, dr = n.source(dpath), dm["results"]
        dc = {"as_of": dm["fetched_utc"], "basis": dm["basis"]}
        big = lambda x: f"${rnd(x / 10 ** 9, 2)}B"  # noqa: E731
        n.add("d.ours_30d_usd", dec(dr["ours_30d_usd"]), big(dec(dr["ours_30d_usd"])), dsrc, **dc)
        n.add("d.ours_rank", dr["ours_rank"], f_int(dr["ours_rank"]), dsrc, **dc)
        n.add("d.protocols_ranked", dr["protocols_ranked"], f_int(dr["protocols_ranked"]), dsrc, **dc)
        n.add("d.bridges_with_volume", dr["bridges_with_volume"], f_int(dr["bridges_with_volume"]), dsrc,
              note="protocols with 30-day volume in DefiLlama's 'Bridge' category, NEAR Intents included", **dc)
        n.add("d.all_rank", dr["all_rank"], ordinal(dr["all_rank"]), dsrc,
              note="rank among every protocol with 30-day volume in DefiLlama's /overview/dexs, any category; "
                   "above it: " + ", ".join(dr["all_categories_above"]), **dc)
        n.add("d.all_protocols_with_volume", dr["all_protocols_with_volume"], f_int(dr["all_protocols_with_volume"]),
              dsrc, **dc)
        if dr.get("parent_rank") is not None:
            n.add("d.parent_rank", dr["parent_rank"], ordinal(dr["parent_rank"]), dsrc,
                  note="rank in DefiLlama's /overview/dexs (its DEX-volume overview) with each protocol's versions "
                       "added up under its parent; NEAR Intents' parent group is " + dr["ours_group"], **dc)
            n.add("d.parent_groups_with_volume", dr["parent_groups_with_volume"],
                  f_int(dr["parent_groups_with_volume"]), dsrc, **dc)
            if dr["ours_group_30d_usd"] != dr["ours_30d_usd"]:
                problems.append("demand: NEAR Intents' parent group has volume other than NEAR Intents' own")
        n.add("d.window_end", dm["fetched_utc"], day_month(dm["fetched_utc"]), dsrc,
              note="DefiLlama's total30d: the 30 days end at the fetch, not at the project's window")
        for key in ("largest_other", "largest_aggregator"):
            v = dec(dr[key]["volume_30d_usd"])
            n.add(f"d.{key}.volume_30d_usd", v, big(v), dsrc, name=dr[key]["name"], **dc)
            m = dec(dr[f"ours_over_{key}"])
            n.add(f"d.ours_over_{key}", m, f"×{rnd(m, 1)}", dsrc, name=dr[key]["name"], **dc)
        n.add("d.as_of", dm["fetched_utc"], dm["fetched_utc"][:10], dsrc)
    # A staked holder's share of all NEAR grows by (1 + staking yield) / (1 + issuance rate) - 1 a year
    if "iv.staking_yield_gross" in n.items and "iv.issuance_rate_per_year" in n.items:
        g = (1 + dec(n.items["iv.staking_yield_gross"]["value"])) / (1 + dec(n.items["iv.issuance_rate_per_year"]["value"])) - 1
        n.add("iv.staked_share_growth", g, f_pct(g, 2), n.items["iv.staking_yield_gross"]["source"],
              derived_from=["iv.staking_yield_gross", "iv.issuance_rate_per_year"],
              note="before the validator's commission: (1 + staking yield) / (1 + issuance rate) - 1")
        # The same after a validator commission c, which each validator sets and this repository does not read:
        # an illustrative range, not a measurement
        for c in (5, 10):
            gc = ((1 + dec(n.items["iv.staking_yield_gross"]["value"]) * (1 - Decimal(c) / 100))
                  / (1 + dec(n.items["iv.issuance_rate_per_year"]["value"])) - 1)
            n.add(f"iv.staked_share_growth.commission_{c}", gc, f_pct(gc, 2), n.items["iv.staking_yield_gross"]["source"],
                  derived_from=["iv.staking_yield_gross", "iv.issuance_rate_per_year"],
                  note=f"after an assumed {c}% validator commission (not read from the chain): "
                       f"(1 + staking yield x (1 - {c}/100)) / (1 + issuance rate) - 1")
    # An unstaked holder's share of all NEAR changes by 1 / (1 + issuance rate) - 1 a year. The buybacks wallets
    # hold what they buy and burn nothing, so total supply, and this share, do not depend on them.
    if "iv.issuance_rate_per_year" in n.items:
        g0 = dec(n.items["iv.issuance_rate_per_year"]["value"])
        isrc = n.items["iv.issuance_rate_per_year"]["source"]
        for key, rate, what in (("iv.unstaked_share_change", g0, "today's issuance"),
                                ("iv.hsp029.unstaked_share_change", g0 * HSP029_SCALE, "HSP-029, issuance x 16/25")):
            u = 1 / (1 + rate) - 1
            n.add(key, u, f_pct(u, 2), isrc, derived_from=["iv.issuance_rate_per_year"],
                  note=f"{what}: 1 / (1 + issuance rate) - 1, share of all NEAR a year; no buyback term, "
                       "because bought NEAR is held, not burned")
        # The same two rows over the horizon, 1 November 2026 to 1 January 2031, at today's rates held constant
        years = Decimal(HORIZON_DAYS) / Decimal("365.25")
        if "iv.staked_share_growth" in n.items:
            for key, base, label in (("iv.to2031.staked_share_change", "iv.staked_share_growth", "staked"),
                                     ("iv.to2031.unstaked_share_change", "iv.unstaked_share_change", "unstaked")):
                c = (1 + dec(n.items[base]["value"])) ** years - 1
                n.add(key, c, f_pct(c, 1), isrc, derived_from=[base],
                      note=f"{label}: (1 + {base}) ^ ({HORIZON_DAYS} / 365.25) - 1, 1 Nov 2026 to 1 Jan 2031 at "
                           "today's rates; no forecast of price, fees or HSP-029")
    # The same with HSP-029: issuance and staking yield both x 16/25, buyback yield unchanged
    if all(k in n.items for k in ("iv.staking_yield_gross", "iv.issuance_rate_per_year", "iv.buyback_yield_buybacks")):
        f = HSP029_SCALE
        r2 = dec(n.items["iv.staking_yield_gross"]["value"]) * f
        g2 = dec(n.items["iv.issuance_rate_per_year"]["value"]) * f
        s2 = (1 + r2) / (1 + g2) - 1
        src = n.items["iv.staking_yield_gross"]["source"]
        n.add("iv.hsp029.staked_share_growth", s2, f_pct(s2, 2), src,
              derived_from=["iv.staking_yield_gross", "iv.issuance_rate_per_year"],
              note="HSP-029: (1 + staking yield x 16/25) / (1 + issuance rate x 16/25) - 1, before commission")
        d2 = g2 - dec(n.items["iv.buyback_yield_buybacks"]["value"])
        n.add("iv.hsp029.net_dilution_buybacks", d2, f_pct(d2, 2), src,
              derived_from=["iv.issuance_rate_per_year", "iv.buyback_yield_buybacks"],
              note="HSP-029: issuance rate x 16/25 - buyback yield (held at today's)")
    if "n1.buybacks_near_per_day" in n.items:
        y = dec(n.items["n1.buybacks_near_per_day"]["value"]) * dec("365.25")
        n.add("iv.buybacks_kept_near_per_year", y, f"{rnd(y / 10 ** 6, 2)}M", n.items["n1.buybacks_near_per_day"]["source"],
              unit="NEAR/year", derived_from=["n1.buybacks_near_per_day"], note="n1.buybacks_near_per_day x 365.25")
        if "ts.year_out_near" in n.items:
            yrs = dec(n.items["ts.year_out_near"]["value"]) / y
            n.add("ts.year_out_years_of_buybacks", yrs, f_num(yrs, 1), n.items["ts.year_out_near"]["source"],
                  unit="years", derived_from=["ts.year_out_near", "iv.buybacks_kept_near_per_year"],
                  note="what left treasury.near in April-May 2026 / a year of buybacks at this window's pace")
    if "iv.buybacks_kept_usd_per_day" in n.items:
        y = dec(n.items["iv.buybacks_kept_usd_per_day"]["value"]) * dec("365.25")
        n.add("iv.buybacks_kept_usd_per_year", y, f"${rnd(y / 10 ** 6, 1)}M", n.items["iv.buybacks_kept_usd_per_day"]["source"],
              derived_from=["iv.buybacks_kept_usd_per_day"], note="iv.buybacks_kept_usd_per_day x 365.25")
    if "ts.year_out_near" in n.items:
        sup = dec(n.items["iv.supply_value_usd"]["value"]) / dec(n.items["n2.mean_price_usd"]["value"])
        sh = dec(n.items["ts.year_out_near"]["value"]) / sup
        n.add("ts.year_out_share_of_supply", sh, f_pct(sh, 1), n.items["ts.year_out_near"]["source"],
              derived_from=["ts.year_out_near", "iv.supply_value_usd", "n2.mean_price_usd"],
              note="what left treasury.near in 2026 / total supply at the window's end block")
    # Avoid's test 2 is in dollars: at this window's NEAR kept a day it fails at this price, whatever the take rate
    if all(k in n.items for k in ("f2.buybacks_kept_usd_per_day.2026-04", "n1.buybacks_near_per_day", "n2.mean_price_usd")):
        floor_usd = dec(n.items["f2.buybacks_kept_usd_per_day.2026-04"]["value"])
        p_fire = floor_usd / dec(n.items["n1.buybacks_near_per_day"]["value"])
        n.add("iv.avoid_test2_price_usd", p_fire, f_usd(p_fire, 3), n.items["n1.buybacks_near_per_day"]["source"],
              unit="USD", derived_from=["f2.buybacks_kept_usd_per_day.2026-04", "n1.buybacks_near_per_day"],
              note="the NEAR price at which this window's NEAR kept a day is worth April's dollars: Avoid's test 2 "
                   "fails at or below it, whatever the take rate")
        drop = p_fire / dec(n.items["n2.mean_price_usd"]["value"]) - 1
        n.add("iv.avoid_test2_price_change", drop, f_pct(drop, 1), n.items["n1.buybacks_near_per_day"]["source"],
              derived_from=["iv.avoid_test2_price_usd", "n2.mean_price_usd"],
              note="iv.avoid_test2_price_usd / n2.mean_price_usd - 1")
    # Three stated paths for the value of all NEAR on 1 January 2031: not forecasts, no probability. A holder's
    # dollars change by (1 + share change to 2031) x (value 2031 / value now) - 1, staked or not.
    need = ("peer.near_l1.revenue_usd_per_year", "peer.near_all.revenue_usd_per_year", "peer.near_all.market_cap_usd",
            "peer.near_all.market_cap_at_fetch_usd", "peer.near_all.mcap_to_revenue",
            "lr.required_growth.buybacks.A.2031", "iv.to2031.staked_share_change", "iv.to2031.unstaked_share_change")
    if all(k in n.items for k in need):
        v = lambda k: dec(n.items[k]["value"])  # noqa: E731
        psrc = n.items["peer.near_all.market_cap_usd"]["source"]
        l1_peers = ("aptos", "solana", "ethereum", "sui")
        mult = sorted(v(f"peer.{p}.mcap_to_revenue") for p in l1_peers)
        median = (mult[1] + mult[2]) / 2
        n.add("sc.l1_peer_median_multiple", median, f"{f_int(median)}×", psrc, unit="multiple",
              derived_from=[f"peer.{p}.mcap_to_revenue" for p in l1_peers],
              note="median of the market cap / holders' revenue of the four L1s in the peers table (Aptos, "
                   "Solana, Ethereum, Sui), at their window mean prices")
        years = Decimal(HORIZON_DAYS) / Decimal("365.25")
        g = v("lr.required_growth.buybacks.A.2031")
        grow = (1 + g) ** years
        n.add("sc.bull.capture_multiple", grow, f"×{rnd(grow, 1)}", n.items["lr.required_growth.buybacks.A.2031"]["source"],
              unit="multiple", derived_from=["lr.required_growth.buybacks.A.2031"],
              note=f"(1 + lr.required_growth.buybacks.A.2031) ^ ({HORIZON_DAYS} / 365.25): Buy's (a) pace kept to 2031")
        l1 = v("peer.near_l1.revenue_usd_per_year")
        intents = v("peer.near_all.revenue_usd_per_year") - l1
        rev_ratio = (l1 + intents * grow) / (l1 + intents)
        # value 2031 / value now, for each basis of "now": the window's mean price, and the price at the peers fetch
        paths = {
            "bear": (lambda now: median * l1 / now,
                     "the buybacks stop and all NEAR is valued on its L1 gas alone at sc.l1_peer_median_multiple, "
                     "gas revenue held at the window's"),
            "base": (lambda now: Decimal(1), "the value of all NEAR stays where it is, in dollars"),
            "bull": (lambda now: rev_ratio,
                     "Intents' revenue grows at Buy's (a) pace to 2031 (sc.bull.capture_multiple), gas revenue held, "
                     "and all NEAR keeps today's multiple of revenue"),
        }
        for name, (ratio_of, how) in paths.items():
            for basis, now_key in (("", "peer.near_all.market_cap_usd"), (".at_fetch", "peer.near_all.market_cap_at_fetch_usd")):
                now = v(now_key)
                ratio = ratio_of(now)
                n.add(f"sc.{name}.value_usd{basis}", now * ratio, f"${rnd(now * ratio / 10 ** 9, 2)}B", psrc, unit="USD",
                      derived_from=list(need) + ["sc.l1_peer_median_multiple", "sc.bull.capture_multiple"],
                      note=f"value of all NEAR on 1 Jan 2031, from {now_key}, if {how}; a stated path, not a forecast")
                n.add(f"sc.{name}.value_change{basis}", ratio - 1, f_pct(ratio - 1, 0), psrc,
                      derived_from=[f"sc.{name}.value_usd{basis}", now_key], note=f"sc.{name}.value_usd{basis} / {now_key} - 1")
                for who in ("staked", "unstaked"):
                    c = (1 + v(f"iv.to2031.{who}_share_change")) * ratio - 1
                    n.add(f"sc.{name}.{who}_usd_change{basis}", c, f_pct(c, 0), psrc,
                          derived_from=[f"iv.to2031.{who}_share_change", f"sc.{name}.value_change{basis}"],
                          note=f"(1 + iv.to2031.{who}_share_change) x (1 + sc.{name}.value_change{basis}) - 1: a "
                               f"{who} holder's dollars, window to 1 Jan 2031, on this path")

    # ---- where treasury.near's April-May payments went next (treasury_trace.py)
    tpath = data_dir / "treasury_trace.json"
    if tpath.exists():
        td = json.loads(tpath.read_text(encoding="utf-8"))
        tsrc = n.source(tpath)
        steps = [r for r in td["results"]["steps_and_hops"] if "change_near" in r]
        bal = td["results"]["balances"]
        firsts = ["ecotreasury4.multisignature.near", "ecotreasury5.multisignature.near"] + \
                 [h["account"] for h in td["hops"] if h["path"] == 2][:1]
        held = sum(dec(bal[a]["2026-11-01"]) for a in firsts)
        tc = {"block": 222491356, "note": "the three accounts treasury.near paid in April and May 2026"}
        n.add("tt.first_receivers_held_near", held, f_int(held), tsrc, unit="NEAR", **tc)
        n.add("tt.accounts_followed", len(td["hops"]), f_int(len(td["hops"])), tsrc, unit="accounts")
        n.add("tt.transfers_followed", len(steps), f_int(len(steps)), tsrc, unit="balance steps of 1,000 NEAR or more")
        p1 = sum(-dec(r["change_near"]) for r in steps if r["account"].startswith("ecotreasury"))
        n.add("tt.path1.multisigs_sent_near", p1, f_int(p1), tsrc, unit="NEAR",
              note="ecotreasury4 and 5 to one account, mid-May 2026")
        p2 = [r for r in steps if r["path"] == 2]
        if p2:
            n.add("tt.path2.moved_near", -dec(p2[-1]["change_near"]), f_int(-dec(p2[-1]["change_near"])), tsrc,
                  unit="NEAR", note="the 13 May receiver's NEAR, two accounts later (late July 2026)")
        biggest = max((-dec(r["change_near"]) for r in steps if r["path"] == 1), default=0)
        n.add("tt.path1.largest_transfer_near", biggest, f_int(biggest), tsrc, unit="NEAR",
              note="largest single transfer on path 1, mixed with other NEAR (early October 2026)")

    # ---- the Confidential Intents Treasury account (confidential_treasury.py)
    cpath = data_dir / "confidential_treasury.json"
    if cpath.exists():
        cd = json.loads(cpath.read_text(encoding="utf-8"))
        csrc = n.source(cpath)
        by = {r["date"]: r for r in cd["series"]}
        for d in ("2026-04-01", "2026-09-01", "2026-10-01", "2026-11-01", "2026-11-08"):
            if d in by:
                r = by[d]
                cc = {"block": r["block"], "as_of": d}
                n.add(f"ct.priced_usd.{d}", r["priced_usd"], f"${dec(r['priced_usd']) / 10 ** 6:,.1f}M", csrc,
                      unit="USD", **cc)
                st = r["by_group_usd"]["stablecoins"]
                n.add(f"ct.stablecoins_usd.{d}", st, f"${dec(st) / 10 ** 6:,.1f}M", csrc, unit="USD", **cc)
                n.add(f"ct.near_usd.{d}", r["by_group_usd"]["NEAR"],
                      f"${dec(r['by_group_usd']['NEAR']) / 10 ** 6:,.1f}M", csrc, unit="USD", **cc)
                n.add(f"ct.unpriced_tokens.{d}", r["unpriced_tokens"], f_int(r["unpriced_tokens"]), csrc, **cc)
                n.add(f"ct.tokens_held.{d}", r["tokens_held"], f_int(r["tokens_held"]), csrc, **cc)
        if "2026-10-01" in by and "2026-11-08" in by:
            g = dec(by["2026-11-08"]["by_group_usd"]["stablecoins"]) / dec(by["2026-10-01"]["by_group_usd"]["stablecoins"]) - 1
            n.add("ct.stablecoins_change.2026-10-01_2026-11-08", g, f"+{rnd(g * 100, 0):.0f}%", csrc,
                  derived_from=["ct.stablecoins_usd.2026-10-01", "ct.stablecoins_usd.2026-11-08"])

    # ---- the rating under other thresholds (sensitivity.py)
    sepath = data_dir / "sensitivity.json"
    if sepath.exists():
        se = json.loads(sepath.read_text(encoding="utf-8"))
        sesrc = n.source(sepath)
        total = sum(se["month_ratings"].values())
        n.add("sens.combinations", se["combinations"], f_int(se["combinations"]), sesrc,
              note="Avoid floors 50/75/90% and 0.5/1/1.5x April's dollars, growth (a) +50%/rule/+100%, (b) as on chain or assumed met")
        n.add("sens.month_ratings", total, f_int(total), sesrc, note="combinations x months (April-October 2026)")
        n.add("sens.hold", se["month_ratings"]["Hold"], f_int(se["month_ratings"]["Hold"]), sesrc)
        if not se["every_month_hold"]:
            problems.append("sensitivity: some combination rates a month other than Hold; the README says every one is Hold")

    # ---- did the buybacks keep coming once the private path took over (private_shift.py)
    spath = data_dir / "private_shift.json"
    if spath.exists():
        sd = json.loads(spath.read_text(encoding="utf-8"))
        ssrc = n.source(spath)
        for name, per in sd["periods"].items():
            pc = {"first": per["first"], "last": per["last"], "days": per["days"]}
            for k, what in (("kept_near", "the three revenue wallets"), ("buybacks_near", "the buybacks wallets"),
                            ("front_end_near", "the front-end fund"), ("revenue_near", "DefiLlama's revenue in NEAR")):
                v = dec(per[f"{k}_per_day"])
                n.add(f"ps.{name}.{k}_per_day", v, f_int(v), ssrc, unit="NEAR/day", note=what, **pc)
            for k in ("kept_usd", "revenue_usd"):
                v = dec(per[f"{k}_per_day"])
                n.add(f"ps.{name}.{k}_per_day", v, f_usd(v), ssrc, unit="USD/day", **pc)
            v = dec(per["kept_share_of_revenue"])
            n.add(f"ps.{name}.kept_share_of_revenue", v, f_pct(v, 1), ssrc, unit="share",
                  note="NEAR the three wallets kept / DefiLlama's revenue in NEAR", **pc)
            n.add(f"ps.{name}.days", per["days"], f_int(per["days"]), ssrc, **pc)
        for k, r in sd["after_over_before"].items():
            r = dec(r) - 1
            n.add(f"ps.change.{k}_per_day", r, ("+" if r > 0 else "") + f_pct(r, 0), ssrc,
                  derived_from=[f"ps.before.{k}_per_day", f"ps.after.{k}_per_day"])
        ru = sd["before_runs_of_after_length"]
        for m in ("kept_near", "revenue_near"):
            for k in ("lowest", "highest"):
                v = dec(ru[f"{k}_{m}_per_day"])
                n.add(f"ps.before_runs.{k}_{m}_per_day", v, f_int(v), ssrc, unit="NEAR/day",
                      note=f"{k} mean of {ru['days']} consecutive days inside the before period ({ru['count']} runs)")
        if not ru["after_inside"]:
            n.add("ps.after_outside_before_runs", True, "yes", ssrc)
        for c in sd["cut_dates"]:
            for k in ("kept_near", "buybacks_near", "revenue_near", "revenue_usd"):
                r = dec(c[f"{k}_after_over_before"]) - 1
                n.add(f"ps.cut.{c['cut']}.{k}", r, ("+" if r > 0 else "") + f_pct(r, 0), ssrc,
                      note=f"after over before with the change on {c['cut']}")
        ks = [dec(c["kept_near_after_over_before"]) - 1 for c in sd["cut_dates"]]
        n.add("ps.cut.kept_near_lowest", min(ks), ("+" if min(ks) > 0 else "") + f_pct(min(ks), 0), ssrc)
        n.add("ps.cut.kept_near_highest", max(ks), ("+" if max(ks) > 0 else "") + f_pct(max(ks), 0), ssrc)
        ts = sd["treasury_stablecoins_usd"]
        if ts["after_start"] and ts["after_end"]:
            g = dec(ts["after_end"]) / dec(ts["after_start"]) - 1
            n.add("ps.treasury_stablecoins_change_after", g, ("+" if g > 0 else "") + f_pct(g, 0), ssrc,
                  note="Confidential Intents Treasury account, stablecoins, 27 Oct to 9 Nov (first blocks)")

    # ---- the pre-registration anchors (check_prereg.py, --anchor 2 and 3)
    for num, name in (("1", "prereg.json"), ("2", "prereg2_anchor.json"), ("3", "prereg3_anchor.json")):
        apath = data_dir / name
        if not apath.exists():
            continue
        ad = json.loads(apath.read_text(encoding="utf-8"))
        asrc = n.source(apath)
        if not all(ad["checks"].values()):
            problems.append(f"{name}: a check failed")
        inc = ad["transaction"]["included_in_block"]
        ac = {"socialdb_key": ad["key"], "tx": ad["transaction"]["hash"], "file": ad["file"]["name"]}
        n.add(f"pr.anchor{num}.tx_block", inc["height"], f_int(inc["height"]), asrc, unit="block", **ac)
        n.add(f"pr.anchor{num}.tx_utc", inc["timestamp_utc"], inc["timestamp_utc"][:19].replace("T", " ") + " UTC",
              asrc, **ac)

    # ---- PREREG-2.md: predictions 4 and 5, judged (judge_prereg2.py)
    ppath = data_dir / "prereg2.json"
    if ppath.exists():
        pd = json.loads(ppath.read_text(encoding="utf-8"))
        psrc = n.source(ppath)
        if not all(pd["prereg_checks"].values()):
            problems.append("prereg2.json: PREREG-2.md check failed")
        for num, e in sorted(pd["predictions"].items()):
            r, jb = e["result"], e["result"]["judging_block"]
            pc = {"judging_block": jb["height"], "as_of": jb["timestamp_utc"][:19] + "Z",
                  "rule": e["rule"], "probability": e["probability"]}
            if not all(r["checks"].values()):
                problems.append(f"prereg2.json: prediction {num} check failed")
            word = "holds" if r["holds"] else "fails"
            n.add(f"pr.{num}.result", word, word, psrc, **pc)
            n.add(f"pr.{num}.protocol_version", r["protocol_version"], str(r["protocol_version"]), psrc, **pc)
            n.add(f"pr.{num}.brier", r["brier"], r["brier"], psrc, unit="Brier score", **pc)
            n.add(f"pr.{num}.judging_height", jb["height"], f_int(jb["height"]), psrc, unit="block", **pc)
        for ver, f in sorted(pd["first_block_with_version"].items()):
            r, fb = f["result"], f["result"]["first_block"]
            fc = {"block": fb["height"], "note": "first block with this protocol version in effect"}
            if not all(r["checks"].values()):
                problems.append(f"prereg2.json: first block with version {ver} check failed")
            n.add(f"pr.v{ver}.first_height", fb["height"], f_int(fb["height"]), psrc, unit="block", **fc)
            n.add(f"pr.v{ver}.first_utc", fb["timestamp_utc"], fb["timestamp_utc"][:16].replace("T", " ") + " UTC",
                  psrc, **fc)
            d = Decimal(r["days_from_hsp027_passed"])
            n.add(f"pr.v{ver}.days_from_hsp027_passed", d, f_num(d, 0), psrc, unit="days", **fc)
        bm = pd["brier_mean"]
        n.add("pr.brier_mean", bm["mean"], bm["mean"], psrc, unit="mean Brier score", judged=bm["judged"])
        n.add("pr.judged", bm["judged"], f_int(bm["judged"]), psrc, unit="predictions")

    provisional = sorted(k for k, v in n.items.items() if v.get("status") in ("provisional",
                                                                                  "pending"))
    doc = {
        "about": "Every measured number used in the README. Built by "
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
    ("burn.py", lambda doc: ["--verify"]),
    ("treasury_spend.py", lambda doc: ["--verify"]),
    ("treasury_exits.py", lambda doc: ["--verify"]),
    ("treasury_trace.py", lambda doc: ["--verify"], "treasury_trace.json"),
    ("confidential_treasury.py", lambda doc: ["--verify"], "confidential_treasury.json"),
    ("private_shift.py", lambda doc: ["--verify"], "private_shift.json"),
    ("sensitivity.py", lambda doc: ["--verify"], "sensitivity.json"),
    ("check_prereg.py", lambda doc: ["--verify"]),
    ("check_prereg.py", lambda doc: ["--anchor", "2", "--verify"], "prereg2_anchor.json"),
    ("check_prereg.py", lambda doc: ["--anchor", "3", "--verify"], "prereg3_anchor.json"),
    ("base_rates.py", lambda doc: ["--verify"], "base_rates.json"),
    ("peers.py", lambda doc: ["--verify"], "peers.json"),
    ("demand.py", lambda doc: ["--verify"], "demand.json"),
    ("backtest.py", lambda doc: ["--verify"], "backtest.json"),
    ("judge_prereg2.py", lambda doc: ["--verify"]),
    ("control_map.py", lambda doc: ["--verify"]),
    ("control_history.py", lambda doc: ["--verify"]),
]


def verify(path, run_scripts=True, runner=subprocess.run):
    path = Path(path)
    doc = json.loads(path.read_text(encoding="utf-8"))
    root = path.resolve().parent.parent
    problems, public_only = [], []
    verify.public_only = public_only
    for rel, digest in doc["sources"].items():
        p = root / rel
        if not p.exists():
            problems.append(f"missing source {rel}")
        elif sha256_file(p) != digest:
            problems.append(f"source changed since the build: {rel}")
    if run_scripts:
        for script, args, *needs in SCRIPT_CHECKS:
            out_file = {"hsp029.py": "hsp029.json", "hsp029_voters.py": "hsp029_voters.json",
                        "farm_rate.py": "farm_rate.json",
                        "burn.py": "burn.json",
                        "check_prereg.py": "prereg.json",
                        "judge_prereg2.py": "prereg2.json",
                        "control_map.py": "control_map.json",
                        "control_history.py": "control_history.json"}
            need = needs[0] if needs else out_file.get(script)
            if need and not (root / "data" / need).exists():
                continue
            res = runner([sys.executable, str(root / "scripts" / script)] + args(doc),
                         cwd=root, capture_output=True, text=True)
            line = (res.stdout.strip().splitlines() or [""])[-1]
            print(f"  {script:<18} {'OK' if res.returncode == 0 else 'FAILED'}  {line[:110]}")
            if res.returncode != 0:
                problems.append(f"{script} --verify failed")
            elif "PUBLIC_REDACTED" in line:
                public_only.append(script)
    if not problems:
        again, p = build(root / "data", root / doc["window_file"])
        problems += p
        if again != doc:
            changed = [k for k in again["numbers"] if again["numbers"][k] != doc["numbers"].get(k)]
            problems.append(f"numbers.json does not rebuild the same ({len(changed)} differ: "
                            f"{', '.join(changed[:5])})")
    return problems


# ---------------------------------------------------------------- README markers

# Headline numbers that must appear, marked, in the README: a figure typed by hand instead
# of marked would otherwise go unchecked.
REQUIRED_IN_README = [
    "n2.fees_usd_per_day",
    "n1.coverage_buybacks",
    "n1.coverage_with_front_end",
    "n1.new_near_per_day",
    "n1.buybacks_near_per_day",
    "n2.max_coverage",
    "n2.equilibrium_price_usd",
    "c.buybacks_confirmations",
    "c.nearai_pool_reward_fee",
    "f6.change1.ratio",
    "iv.issuance_rate_per_year",
    "d.ours_30d_usd",
    "pr.4.brier",
    "pr.5.brier",
    "pr.anchor3.tx_block",
    "tt.first_receivers_held_near",
    "ct.priced_usd.2026-11-08",
    "ct.stablecoins_usd.2026-11-08",
    "iv.staked_share_growth",
    "iv.unstaked_share_change",
    "lr.required_growth.buybacks.A.2031",
]
# Headline numbers that moved to docs/DETAILS.md with README v3 (8 Nov): still required, there.
REQUIRED_IN_DETAILS = [
    "n2.hsp029_max_coverage",
    "n3.stakers_active",
    "n3.largest_share",
    "n3.top10_share",
    "n3.outside_top10_median_near",
    "iv.wallets_multiple_buybacks",
    "iv.wallets_multiple_with_front_end",
    "iv.fees_multiple",
    "c.treasury_share_of_new_supply",
    "f9.front_end_share_of_wallets",
    "iv.staking_yield_gross",
    "c.issuance_staked_share",
    "iv.revenue_equilibrium_price_usd",
]


def check_text(text, numbers, required=()):
    problems = []
    marked = {m.group(1) for m in MARK.finditer(text)}
    problems += [f"required number '{k}' is not marked in the text" for k in required
                 if k not in marked]
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
        po = getattr(verify, "public_only", [])
        print(f"VERIFY: PASS ({'PUBLIC_REDACTED' if po else 'FULL'}) - every number recomputed offline from public files "
              "and redacted copies." + (f" Private originals are not in git for privacy "
              f"({', '.join(po)}): their SHA-256 are recorded, and --archival re-fetches them."
                                        if po else " Private originals present and matching."))
        return
    if args.check or args.render:
        numbers = json.loads(out.read_text(encoding="utf-8"))["numbers"]
        target = Path(args.check or args.render)
        text = target.read_text(encoding="utf-8")
        if args.render:
            target.write_text(render_text(text, numbers), encoding="utf-8", newline="\n")
            text = target.read_text(encoding="utf-8")
        required = (REQUIRED_IN_README if target.name == "README.md" else
                    REQUIRED_IN_DETAILS if target.name == "DETAILS.md" else ())
        problems = check_text(text, numbers, required)
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
