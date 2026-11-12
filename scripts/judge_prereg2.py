"""Judge the predictions of PREREG-2.md: is a protocol version in effect at the judging block?

    python scripts/judge_prereg2.py 4          # prediction 4 (version 87, judged at 2026-11-06 00:00 UTC)
    python scripts/judge_prereg2.py 5          # prediction 5 (version 88, judged at 2026-11-08 00:00 UTC)
    python scripts/judge_prereg2.py --verify   # offline: recompute data/prereg2.json from the saved responses

The rules are PREREG-2.md's, applied exactly:
  - judging block: the first block whose header timestamp is at or after the time given, with the block
    before it timestamped before that time (lock_window.find_boundary, the rule of every window here);
  - protocol version in effect: `protocol_version` of JSON-RPC EXPERIMENTAL_protocol_config with block_id
    set to the judging block's height, from archival-rpc.mainnet.fastnear.com;
  - holds if that version is at or above the prediction's version; Brier score = (probability - outcome)^2.
Also reported, as PREREG-2.md asks: the first block with the version in effect, its time, and the days
from HSP-027's passing (2026-07-03) to that block. It is found by bisection between the last daily
record of data/upgrade_watch.csv below the version and the first at or above it, and proved by two
adjacent blocks (prev_hash link): the one before still below the version, the first one at or above it.

Every response used is saved byte for byte in data/raw/prereg2/ with its SHA-256; --verify recomputes
every result and check from those files and from PREREG-2.md itself (its SHA-256 must be the anchored one,
and the version and probability must be the ones its table states).

Read-only: JSON-RPC "block" and "EXPERIMENTAL_protocol_config". No keys, nothing written on chain.
"""
import argparse
import csv
import json
import re
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lock_window as lw  # noqa: E402

REPO = lw.REPO
OUT_NAME = "prereg2.json"
RAW_DIR = "raw/prereg2"
PREREG_FILE = "PREREG-2.md"
ANCHORED_SHA256 = "545cf67530b37c902b2674cb4014818d3f79eb1718fe6bbab896a361e48ce0d3"
# HSP-027's voting end, read from vote.dao by hsp027.py (data/hsp027.json): voting_start_time_ns +
# voting_duration_ns = 2026-07-03 23:00:00 UTC. Until 12 Nov 2026 this was 00:00 of that day, entered by hand.
HSP027_PASSED = "2026-07-03T23:00:00Z"
HSP027_FILE = "hsp027.json"
PREDICTIONS = {
    "4": {"version": 87, "probability": "0.85", "target_utc": "2026-11-06T00:00:00Z"},
    "5": {"version": 88, "probability": "0.75", "target_utc": "2026-11-08T00:00:00Z"},
}
RULE = ("first block whose header timestamp is at or after the time given; protocol_version of "
        "EXPERIMENTAL_protocol_config at that height; holds if >= the version")


def ns_of(utc):
    return int(datetime.strptime(utc, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()) * lw.NS


def brier(probability, outcome):
    return str((Decimal(probability) - outcome) ** 2)


def header_of(raw):
    return json.loads(raw)["result"]["header"]


def version_of(raw):
    doc = json.loads(raw)
    if "error" in doc or "result" not in doc:
        raise RuntimeError(f"EXPERIMENTAL_protocol_config: {json.dumps(doc.get('error'))[:300]}")
    return int(doc["result"]["protocol_version"])


# ---------------------------------------------------------------- pure computation (also used by --verify)

def judge_result(number, raws):
    """raws: bytes of judging block, previous block, protocol config at the judging block."""
    p = PREDICTIONS[number]
    target = ns_of(p["target_utc"])
    b, prev = header_of(raws["judging_block"]), header_of(raws["previous_block"])
    version = version_of(raws["protocol_config"])
    outcome = 1 if version >= p["version"] else 0
    checks = {
        "judging_block_at_or_after_target": b["timestamp"] >= target,
        "previous_block_before_target": prev["timestamp"] < target,
        "previous_block_is_parent": b["prev_hash"] == prev["hash"],
    }
    return {
        "judging_block": lw.summary(b),
        "previous_block": lw.summary(prev),
        "protocol_version": version,
        "holds": bool(outcome),
        "outcome": outcome,
        "brier": brier(p["probability"], outcome),
        "checks": checks,
    }


def first_result(version, raws):
    """raws: the first block with the version in effect, the block before it, and both protocol configs."""
    first, before = header_of(raws["first_block"]), header_of(raws["block_before"])
    v_first, v_before = version_of(raws["first_config"]), version_of(raws["before_config"])
    passed = ns_of(HSP027_PASSED)
    days = Decimal(first["timestamp"] - passed) / Decimal(86400 * lw.NS)
    return {
        "first_block": lw.summary(first),
        "block_before": lw.summary(before),
        "version_at_first_block": v_first,
        "version_at_block_before": v_before,
        "days_from_hsp027_passed": str(days.quantize(Decimal("0.01"))),
        "checks": {
            "first_block_has_the_version": v_first >= version,
            "block_before_does_not": v_before < version,
            "block_before_is_parent": first["prev_hash"] == before["hash"],
        },
    }


def prereg_file_checks(text_bytes):
    text = text_bytes.decode("utf-8")
    checks = {"file_sha256_is_anchored": lw.sha256(text_bytes) == ANCHORED_SHA256}
    for number, p in PREDICTIONS.items():
        row = re.search(rf"^\| {number} \|.*$", text, re.M)
        ok = bool(row) and f"≥ {p['version']}" in row.group(0) and f"| {p['probability']} |" in row.group(0) \
            and p["target_utc"][:10] in row.group(0) and p["target_utc"][11:16] in row.group(0)
        checks[f"table_states_prediction_{number}"] = ok
    return checks


# ---------------------------------------------------------------- network

def config_raw(chain, height):
    return chain._post({"jsonrpc": "2.0", "id": "prereg2", "method": "EXPERIMENTAL_protocol_config",
                        "params": {"block_id": height}})


def watch_rows(data_dir):
    path = data_dir / "upgrade_watch.csv"
    with open(path, newline="", encoding="utf-8") as f:
        return [(int(r["final_height"]), ns_of(r["utc"][:19] + "Z"), int(r["protocol_version"]))
                for r in csv.DictReader(f)]


def guess_height(rows, target_ns):
    """A height near the target, from the daily records' heights and times."""
    (h0, t0, _), (h1, t1, _) = rows[-2], rows[-1]
    per_ns = (h1 - h0) / (t1 - t0)
    near = min(rows, key=lambda r: abs(r[1] - target_ns))
    return int(near[0] + (target_ns - near[1]) * per_ns)


def find_first(chain, version, lo, hi, cache):
    """Bisection: lo is an existing height below the version, hi one at or above. Returns (first, before)."""
    def v_at(h):
        if h not in cache:
            cache[h] = config_raw(chain, h)
        return version_of(cache[h])
    lo, hi = lw.first_existing(chain, lo, lo + 100)[0], lw.first_existing(chain, hi, hi + 100)[0]
    if v_at(lo) >= version or v_at(hi) < version:
        raise RuntimeError(f"bisection bounds do not bracket version {version}: {lo}, {hi}")
    top = hi
    while top - lo > 1:
        mid = (lo + top) // 2
        found = lw.first_existing(chain, mid, top)
        if found is None:          # mid..top-1 are skipped heights
            top = mid
            continue
        m = found[0]
        if v_at(m) >= version:
            hi = top = m
        else:
            lo = m
    return hi, lo


def save_raw(data_dir, name, raw):
    rel = f"data/{RAW_DIR}/{name}"
    path = data_dir / RAW_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return {"path": rel, "sha256": lw.sha256(raw)}


def judge(chain, number, data_dir, now_ns=None):
    p = PREDICTIONS[number]
    target = ns_of(p["target_utc"])
    now_ns = now_ns if now_ns is not None else time.time_ns()
    if now_ns < target + lw.SAFETY_SECONDS * lw.NS:
        raise RuntimeError(f"prediction {number} is judged at {p['target_utc']}; wait until "
                           f"{lw.SAFETY_SECONDS // 60} minutes after that, so the block is final")
    rows = watch_rows(data_dir)
    b, prev = lw.find_boundary(chain, target, guess_height(rows, target))
    cfg = config_raw(chain, b["height"])
    raws = {"judging_block": chain.raw[b["height"]], "previous_block": chain.raw[prev["height"]],
            "protocol_config": cfg}
    result = judge_result(number, raws)
    files = {
        "judging_block": save_raw(data_dir, f"block_{b['height']}.json", raws["judging_block"]),
        "previous_block": save_raw(data_dir, f"block_{prev['height']}.json", raws["previous_block"]),
        "protocol_config": save_raw(data_dir, f"protocol_config_{b['height']}.json", cfg),
    }
    entry = {"prediction": int(number), "version": p["version"], "probability": p["probability"],
             "target_utc": p["target_utc"], "rule": RULE, "raw_files": files, "result": result}

    first = None
    version = p["version"]
    below = [r for r in rows if r[2] < version]
    above = [r for r in rows if r[2] >= version]
    hi = above[0][0] if above else (b["height"] if result["holds"] else None)
    if hi is not None and below:
        cache = {b["height"]: cfg}
        lo = max(r[0] for r in below if r[0] < hi)
        f_h, b_h = find_first(chain, version, lo, hi, cache)
        chain.block(f_h), chain.block(b_h)
        fr = {"first_block": chain.raw[f_h], "block_before": chain.raw[b_h],
              "first_config": cache[f_h], "before_config": cache[b_h]}
        first = {"version": version, "searched_between": [lo, hi], "result": first_result(version, fr),
                 "raw_files": {
                     "first_block": save_raw(data_dir, f"block_{f_h}.json", fr["first_block"]),
                     "block_before": save_raw(data_dir, f"block_{b_h}.json", fr["block_before"]),
                     "first_config": save_raw(data_dir, f"protocol_config_{f_h}.json", fr["first_config"]),
                     "before_config": save_raw(data_dir, f"protocol_config_{b_h}.json", fr["before_config"]),
                 }}

    out = data_dir / OUT_NAME
    doc = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {
        "measure": "PREREG-2.md predictions: protocol version in effect at the judging block",
        "prereg_file": PREREG_FILE, "anchored_sha256": ANCHORED_SHA256,
        "source": {"rpc": lw.ARCHIVAL, "methods": ["block", "EXPERIMENTAL_protocol_config"]},
        "predictions": {}, "first_block_with_version": {}}
    doc["predictions"][number] = dict(entry, fetched_utc=lw.iso(now_ns))
    if first:
        doc["first_block_with_version"][str(version)] = dict(first, fetched_utc=lw.iso(now_ns))
    doc["prereg_checks"] = prereg_file_checks((data_dir.parent / PREREG_FILE).read_bytes())
    doc["brier_mean"] = mean_brier(doc)
    out.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8", newline="\n")
    return doc


def mean_brier(doc):
    scores = [Decimal(e["result"]["brier"]) for e in doc["predictions"].values()]
    return {"judged": len(scores), "mean": str(sum(scores) / len(scores)) if scores else None}


# ---------------------------------------------------------------- offline verify

def verify(path):
    path = Path(path)
    doc = json.loads(path.read_text(encoding="utf-8"))
    root = path.resolve().parent.parent
    problems = []

    def load(ref):
        p = root / ref["path"]
        if not p.exists():
            problems.append(f"missing {ref['path']}")
            return None
        raw = p.read_bytes()
        if lw.sha256(raw) != ref["sha256"]:
            problems.append(f"sha256 differs: {ref['path']}")
        return raw

    checks = prereg_file_checks((root / PREREG_FILE).read_bytes())
    if checks != doc.get("prereg_checks"):
        problems.append("PREREG-2.md checks do not recompute")
    problems += [f"PREREG-2.md: {k}" for k, ok in checks.items() if not ok]
    for number, e in doc["predictions"].items():
        p = PREDICTIONS[number]
        if (e["version"], e["probability"], e["target_utc"]) != (p["version"], p["probability"], p["target_utc"]):
            problems.append(f"prediction {number}: terms differ from PREREG-2.md")
        raws = {k: load(v) for k, v in e["raw_files"].items()}
        if None in raws.values():
            continue
        again = judge_result(number, raws)
        if again != e["result"]:
            problems.append(f"prediction {number}: result does not recompute")
        problems += [f"prediction {number}: {k}" for k, ok in again["checks"].items() if not ok]
    for version, f in doc["first_block_with_version"].items():
        raws = {k: load(v) for k, v in f["raw_files"].items()}
        if None in raws.values():
            continue
        again = first_result(int(version), raws)
        if again != f["result"]:
            problems.append(f"first block with version {version}: does not recompute")
        problems += [f"first block with version {version}: {k}" for k, ok in again["checks"].items() if not ok]
    if mean_brier(doc) != doc["brier_mean"]:
        problems.append("brier_mean does not recompute")
    hsp = root / "data" / HSP027_FILE
    if not hsp.exists():
        problems.append(f"missing data/{HSP027_FILE}: the date HSP-027 passed has no saved source")
    elif int(json.loads(hsp.read_text(encoding="utf-8"))["proposal"]["voting_end_ns"]) != ns_of(HSP027_PASSED):
        problems.append(f"HSP027_PASSED differs from the voting end in data/{HSP027_FILE}")
    return problems, doc


def describe(doc):
    parts = []
    for number, e in sorted(doc["predictions"].items()):
        r = e["result"]
        parts.append(f"P{number} {'holds' if r['holds'] else 'fails'} (version {r['protocol_version']} at "
                     f"{r['judging_block']['height']}, Brier {r['brier']})")
    return "; ".join(parts) or "no prediction judged yet"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("prediction", nargs="?", choices=sorted(PREDICTIONS))
    parser.add_argument("--verify", nargs="?", const=f"data/{OUT_NAME}", metavar="FILE")
    args = parser.parse_args()
    if args.verify:
        problems, doc = verify(REPO / args.verify)
        if problems:
            print("\n".join(problems))
            print("PREREG-2 VERIFY: FAIL")
            return 1
        print(f"OK: {describe(doc)}")
        return 0
    if not args.prediction:
        parser.error("give a prediction number (4 or 5), or --verify")
    try:
        doc = judge(lw.Chain(), args.prediction, REPO / "data")
    except RuntimeError as e:
        print(f"PREREG-2: NOT JUDGED - {e}")
        return 2
    print(describe(doc))
    for version, f in doc["first_block_with_version"].items():
        r = f["result"]
        print(f"first block with version {version}: {r['first_block']['height']} at "
              f"{r['first_block']['timestamp_utc']}, {r['days_from_hsp027_passed']} days after HSP-027 passed")
    print(f"saved data/{OUT_NAME}; offline check: python scripts/judge_prereg2.py --verify")
    return 0


if __name__ == "__main__":
    sys.exit(main())
