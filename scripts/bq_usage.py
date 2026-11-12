"""Claim E, second source: NEAR's own use from NEAR's public BigQuery dataset, and the organizers' question again.

The track's prompt example (nearai/near-hackathon-prompt-examples, tracks/02-thesis.md) asks for BigQuery. Two
queries (sql/bq_q1_transactions.sql, sql/bq_q2_receipt_actions.sql, sql/bq_q3_intents_callers.sql) were run once in the BigQuery console on
12 November 2026; their results are saved in data/bq/ with SHA-256 in data/bq/MANIFEST.json. Nothing here needs
the network or a Google account: this script only reads the saved files. Anyone with a Google account can re-run
the four queries (about 355 GB, inside BigQuery's free monthly terabyte) and compare.

What is computed (offline):
  agreement  every day of the year (1 November 2025 to 31 October 2026): BigQuery's transactions against
             NearBlocks' (data/usage_fetch.json, usage.py), and BigQuery's delegate (meta) actions against
             NearBlocks' meta transactions. Equal counts from two indexers check the pipeline, not the chain:
             both read NEAR's own block data.
  usage      first and last 30 days of the year (as usage.py): transactions, distinct signers, contracts
             deployed, calls to intents.near, distinct accounts calling it, calls per calling account.
             Also 1-11 November 2026 for intents.near.
  callers    who calls intents.near (sql/bq_q3_intents_callers.sql, the 20 biggest callers of 2-31 October and
             everyone else in one row): intents.near itself (its own internal calls), escrow.ai.near (the NEAR AI
             Agent Market's escrow: market.near.ai lists job payments as "secure deposit" to it), token contracts
             (bridged *.omft.near tokens, native USDC, wrap.near, nbtc.bridge.near, v2_1.omni.hot.tg, token.sweat), and
             everyone else; also each one's share of the calls from other accounts (the contract's own left
             out). The shares by kind come from query 4, which classifies every caller; query 3 names
             only its top 20. Checked: the rows add up to query 2's calls for the same days. Query 2's "accounts calling it"
             counts the account that sent each call (receipt_predecessor_account_id): often a solver or a token
             contract, not a user.
  outcomes   whether those calls succeeded (sql/bq_q4_intents_call_outcomes.sql: each call's receipt joined to
             intents.near's execution outcome; FAILURE counted as failed). Checked: calls by kind equal query 3's.
  lead       the organizers' hypothesis with the volume measured on chain: weekly log-changes of calls to
             intents.near (and of transactions sent to it) against transactions and signers 0-4 weeks later,
             52 weeks from 3 November 2025, the same functions, shifts and seed as usage.py.

    python scripts/bq_usage.py            compute data/bq_usage.json from the saved files
    python scripts/bq_usage.py --verify   recompute and compare
"""
import argparse
import csv
import io
import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lock_window as lw  # noqa: E402
import usage as us  # noqa: E402

REPO = lw.REPO
OUT = "bq_usage.json"
MANIFEST = "bq/MANIFEST.json"
NOV = (date(2026, 11, 1), date(2026, 11, 11))
OCT = (date(2026, 10, 2), date(2026, 10, 31))
ESCROW = "escrow.ai.near"
TOKENS = {"wrap.near", "nbtc.bridge.near", "v2_1.omni.hot.tg", "token.sweat",
          "17208628f84f5d6ad33f0da3bbbeb27ffcb398eac501a31bd6ad2011e36133a1"}   # last: native USDC on NEAR


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def kind(caller):
    if caller == "intents.near":
        return "intents_itself"
    if caller == ESCROW:
        return "near_ai_escrow"
    if caller.endswith(".omft.near") or caller in TOKENS:
        return "token_contracts"
    return "everyone_else"


def load(data_root):
    """{csv path: {date: row}} from data/bq/, checked against MANIFEST.json's SHA-256."""
    man = json.loads((data_root / MANIFEST).read_text(encoding="utf-8"))
    out, problems = {}, []
    for rel, meta in man["files"].items():
        raw = (data_root.parent / rel).read_bytes()
        if lw.sha256(raw) != meta["sha256"]:
            problems.append(f"{rel}: changed since it was saved")
            continue
        rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8"))))
        if len(rows) != meta["rows"]:
            problems.append(f"{rel}: {len(rows)} rows, manifest says {meta['rows']}")
        if "block_date" in rows[0]:
            out[rel] = {r["block_date"]: r for r in rows}
        elif "rank" in rows[0]:
            out[rel] = {r["rank"]: r for r in rows}
        else:
            out[rel] = {str(i): r for i, r in enumerate(rows)}
    return out, problems, man


def compute(data_root):
    data_root = Path(data_root)
    bq, problems, man = load(data_root)
    if problems:
        return None, problems
    q1, q2 = bq["data/bq/q1_transactions.csv"], bq["data/bq/q2_receipt_actions.csv"]
    need = us.days(us.YEAR[0], max(us.WEEK0 + timedelta(weeks=us.WEEKS + 1) - timedelta(days=1), NOV[1]))
    for name, src in (("q1", q1), ("q2", q2)):
        miss = [d for d in need if d not in src]
        if miss:
            problems.append(f"{name}: {len(miss)} days missing, first {miss[0]}")
    nb, nprob, _ = us.series(data_root)
    problems += nprob
    if problems:
        return None, problems

    # agreement with NearBlocks, day by day
    agreement = {}
    for key, bsrc, bfield, nfield in (("txns", q1, "txns", "txns"), ("meta", q2, "delegate_actions", "meta_txns")):
        diffs = []
        for d in us.days(*us.YEAR):
            b, n = int(bsrc[d][bfield]), int(float(nb["txn"][d][nfield]))
            diffs.append((abs(b - n) / n if n else 0.0, b == n, d))
        agreement[key] = {"days": len(diffs), "days_equal": sum(1 for x in diffs if x[1]),
                          "max_rel_diff": max(x[0] for x in diffs),
                          "max_rel_diff_day": max(diffs)[2],
                          "mean_rel_diff": us.mean([x[0] for x in diffs])}

    first = us.days(us.YEAR[0], us.YEAR[0] + timedelta(days=29))
    last = us.days(us.YEAR[1] - timedelta(days=29), us.YEAR[1])
    nov = us.days(*NOV)
    usage = {}
    for key, src, field in (("txns", q1, "txns"), ("signers", q1, "signers"), ("txns_to_intents", q1, "txns_to_intents"),
                            ("intents_calls", q2, "intents_calls"), ("intents_callers", q2, "intents_callers"),
                            ("contracts_deployed", q2, "contracts_deployed"), ("delegate_actions", q2, "delegate_actions")):
        a = us.mean([float(src[d][field]) for d in first])
        b = us.mean([float(src[d][field]) for d in last])
        c = us.mean([float(src[d][field]) for d in nov])
        usage[key] = {"first_30d_mean": a, "last_30d_mean": b, "change": b / a - 1, "nov_1_11_mean": c}
    for key in ("intents_callers", "intents_calls", "signers"):
        src = q2 if key.startswith("intents") else q1
        usage[key]["first_30d_median"] = median([float(src[d][key]) for d in first])
        usage[key]["last_30d_median"] = median([float(src[d][key]) for d in last])
        usage[key]["nov_1_11_median"] = median([float(src[d][key]) for d in nov])
    usage["calls_per_caller"] = {
        "first_30d": usage["intents_calls"]["first_30d_mean"] / usage["intents_callers"]["first_30d_mean"],
        "last_30d": usage["intents_calls"]["last_30d_mean"] / usage["intents_callers"]["last_30d_mean"],
        "nov_1_11": usage["intents_calls"]["nov_1_11_mean"] / usage["intents_callers"]["nov_1_11_mean"]}
    usage["intents_share_of_actions"] = {
        "first_30d": sum(float(q2[d]["intents_calls"]) for d in first) / sum(float(q2[d]["actions"]) for d in first),
        "last_30d": sum(float(q2[d]["intents_calls"]) for d in last) / sum(float(q2[d]["actions"]) for d in last)}

    callers = {}
    q3 = bq["data/bq/q3_intents_callers.csv"]
    for per, (a, b), col in (("october", OCT, "calls_oct"), ("november", NOV, "calls_nov")):
        total = sum(int(r[col]) for r in q3.values())
        q2_total = sum(int(q2[d]["intents_calls"]) for d in us.days(a, b))
        if total != q2_total:
            problems.append(f"q3 {per}: {total} calls, q2 says {q2_total}")
        by = {}
        for r in q3.values():
            by[kind(r["caller"])] = by.get(kind(r["caller"]), 0) + int(r[col])
        outside = total - by["intents_itself"]      # calls from other accounts: the contract's own left out
        nd = len(us.days(a, b))
        callers[per] = {"first": a.isoformat(), "last": b.isoformat(), "calls": total,
                        "share": {k: v / total for k, v in sorted(by.items())},
                        "outside_calls": outside, "outside_calls_a_day": outside / nd,
                        "share_of_outside": {k: v / outside for k, v in sorted(by.items()) if k != "intents_itself"},
                        "near_ai_escrow_calls_a_day": by["near_ai_escrow"] / nd}
    # did the calls succeed? (sql/bq_q4_intents_call_outcomes.sql: each call's receipt joined to its outcome)
    outcomes = {}
    for per, (a, b), col in (("october", OCT, "calls_oct"), ("november", NOV, "calls_nov")):
        nd = len(us.days(a, b))
        rows = [r for r in bq["data/bq/q4_intents_call_outcomes.csv"].values() if r["period"] == per]
        by, failed = {}, {}
        for r in rows:
            by[r["kind"]] = by.get(r["kind"], 0) + int(r["calls"])
            if r["status"] != "SUCCESS_VALUE" and r["status"] != "SUCCESS_RECEIPT_ID":
                failed[r["kind"]] = failed.get(r["kind"], 0) + int(r["calls"])
        q3_by = {}
        for r in q3.values():
            q3_by[kind(r["caller"])] = q3_by.get(kind(r["caller"]), 0) + int(r[col])
        # query 3 names only its top 20, so it can be checked only on totals and the two named accounts
        for k in ("intents_itself", "near_ai_escrow"):
            if by.get(k) != q3_by.get(k):
                problems.append(f"q4 {per}: {k} {by.get(k)} calls, q3 says {q3_by.get(k)}")
        if sum(by.values()) != sum(q3_by.values()):
            problems.append(f"q4 {per}: {sum(by.values())} calls, q3 says {sum(q3_by.values())}")
        # shares by kind come from query 4, which classifies every caller (query 3 only its top 20)
        out = sum(v for k, v in by.items() if k != "intents_itself")
        callers[per]["share"] = {k: v / sum(by.values()) for k, v in sorted(by.items())}
        callers[per]["share_of_outside"] = {k: v / out for k, v in sorted(by.items()) if k != "intents_itself"}
        ok = {k: by[k] - failed.get(k, 0) for k in by if k != "intents_itself"}
        ok_out = sum(ok.values())
        outcomes[per] = {"by_kind": {k: {"calls": by[k], "failed": failed.get(k, 0),
                                         "failed_share": failed.get(k, 0) / by[k]} for k in sorted(by)},
                         "ok_outside_calls": ok_out, "ok_outside_a_day": ok_out / nd,
                         "ok_share_of_outside": {k: v / ok_out for k, v in sorted(ok.items())}}
    other = [r for r in q3.values() if r["caller"].startswith("(")][0]
    callers["accounts_outside_top_20"] = int(other["accounts"])
    callers["accounts_total"] = int(other["accounts"]) + len(q3) - 1
    if problems:
        return None, problems

    usage_y = {"txns": us.weekly(q1, "txns"), "signers": us.weekly(q1, "signers", "mean")}
    preds = {"intents_calls_bq": us.weekly(q2, "intents_calls"), "txns_to_intents_bq": us.weekly(q1, "txns_to_intents")}
    rng = random.Random(us.SEED)
    lead = {}
    for pn, pv in preds.items():
        x = us.dlog(pv)
        for yn, yv in usage_y.items():
            y = us.dlog(yv)
            k, c, cs = us.best_lag(x, y)
            lead[f"{pn}->{yn}"] = {"best_lag_weeks": k, "corr": c, "p_shift": us.shift_test(x, y, rng),
                                   "corr_by_lag": {str(j): v for j, v in cs.items()}}
    return {"measure": __doc__.splitlines()[0], "dataset": man["dataset"], "run_utc": man["run_utc"],
            "year": [us.YEAR[0].isoformat(), us.YEAR[1].isoformat()], "november": [NOV[0].isoformat(), NOV[1].isoformat()],
            "weeks": [us.WEEK0.isoformat(), us.WEEKS],
            "method": f"weekly log-changes, lags {list(us.LAGS)} weeks, {us.SHIFTS} circular shifts (min {us.MIN_SHIFT}), seed {us.SEED}",
            "agreement_with_nearblocks": agreement, "usage": usage, "intents_callers": callers,
            "intents_call_outcomes": outcomes, "lead": lead}, []


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    res, problems = compute(REPO / "data")
    if problems:
        print("\n".join(problems))
        sys.exit(1)
    out = REPO / "data" / OUT
    text = us.dumps(res)
    if a.verify:
        ok = out.exists() and out.read_text(encoding="utf-8") == text
        print("bq_usage: OK" if ok else "bq_usage: DIFFERS")
        sys.exit(0 if ok else 1)
    out.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
