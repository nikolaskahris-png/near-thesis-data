"""Check that this machine can reach every data source the project uses.

Read-only: HTTP GET requests and NEAR JSON-RPC view calls.
No API keys, no transactions, nothing is written on chain.

Usage:
    python scripts/check_sources.py              # print results
    python scripts/check_sources.py --out FILE   # also save them to FILE
"""
import argparse
import json
import platform
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

USER_AGENT = "near-thesis-data/0.1 (+https://github.com/nikolaskahris-png/near-thesis-data)"
RPC = "https://rpc.mainnet.fastnear.com"
ARCHIVAL = "https://archival-rpc.mainnet.fastnear.com"

# Fixed reference point: block 217,453,248 (27 Sep 2026, 07:04 UTC).
# An archival node must return exactly these values, from any machine, at any time.
REF_BLOCK = 217453248
REF_ACCOUNT = "buybacks.multisignature.near"
REF_AMOUNT = "1808799637054372461934377045294"
REF_TOTAL_SUPPLY = "1307425736172350000854043111652167"

# (name, url, core) - "core" sources are needed for the three tracked numbers.
GET_SOURCES = [
    ("fastnear-rpc", RPC + "/status", True),
    ("fastnear-archival", ARCHIVAL + "/status", True),
    ("neardata", "https://mainnet.neardata.xyz/v0/last_block/final", True),
    ("nearblocks", "https://api.nearblocks.io/v1/account/stake.dao", True),
    ("defillama-fees", "https://api.llama.fi/summary/fees/near-intents"
     "?dataType=dailyFees&excludeTotalDataChartBreakdown=true", True),
    ("defillama-price", "https://coins.llama.fi/prices/current/coingecko:near", True),
    ("nearstats", "https://nearstats.org/", False),
    ("github-api", "https://api.github.com", False),
]

RATE_CHECK_CALLS = 20


def fetch(url, body=None, timeout=25):
    """Return (http_status or None, response bytes, milliseconds, error text or None)."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return resp.status, raw, elapsed_ms(start), None
    except urllib.error.HTTPError as e:
        return e.code, b"", elapsed_ms(start), None
    except Exception as e:  # DNS, TLS, timeout, connection refused
        return None, b"", elapsed_ms(start), f"{type(e).__name__}: {e}"


def elapsed_ms(start):
    return int((time.monotonic() - start) * 1000)


def rpc(url, method, params):
    """Return (ok, result or error text, milliseconds)."""
    body = {"jsonrpc": "2.0", "id": "check", "method": method, "params": params}
    status, raw, ms, err = fetch(url, body)
    if err:
        return False, err, ms
    if status != 200:
        return False, f"HTTP {status}", ms
    try:
        doc = json.loads(raw)
    except ValueError:
        return False, "response is not JSON", ms
    if "error" in doc:
        return False, "RPC error " + json.dumps(doc["error"])[:200], ms
    return True, doc["result"], ms


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", help="also write the results to this file")
    args = parser.parse_args()

    lines = []
    core_ok = core_total = 0

    def log(text=""):
        print(text, flush=True)
        lines.append(text)

    log("Date (UTC): " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
    log(f"Python: {platform.python_version()} on {platform.system()} {platform.release()}")

    log()
    log("=== GET endpoints")
    for name, url, core in GET_SOURCES:
        status, raw, ms, err = fetch(url)
        ok = status == 200
        if core:
            core_total += 1
            core_ok += ok
        detail = f"HTTP {status}  {ms} ms  {len(raw)} bytes" if status else f"FAIL  {err}"
        log(f"{name:<20} {'OK  ' if ok else 'NO  '} {detail}")

    log()
    log("=== RPC calls (read-only)")
    ok, res, ms = rpc(RPC, "query", {"request_type": "view_account", "finality": "final",
                                    "account_id": REF_ACCOUNT})
    core_total += 1
    core_ok += ok
    log(f"{'rpc view_account':<20} {'OK  ' if ok else 'NO  '} {ms} ms  "
        + (f"block={res['block_height']}" if ok else res))

    ok, res, ms = rpc(ARCHIVAL, "block", {"block_id": REF_BLOCK})
    match = ok and res["header"]["total_supply"] == REF_TOTAL_SUPPLY
    core_total += 1
    core_ok += bool(match)
    log(f"{'archival block':<20} {'OK  ' if ok else 'NO  '} {ms} ms  "
        + ((f"total_supply {'MATCHES' if match else 'DIFFERS FROM'} reference") if ok else res))

    ok, res, ms = rpc(ARCHIVAL, "query", {"request_type": "view_account", "block_id": REF_BLOCK,
                                          "account_id": REF_ACCOUNT})
    match = ok and res["amount"] == REF_AMOUNT
    core_total += 1
    core_ok += bool(match)
    log(f"{'archival view_acct':<20} {'OK  ' if ok else 'NO  '} {ms} ms  "
        + ((f"amount {'MATCHES' if match else 'DIFFERS FROM'} reference") if ok else res))

    log()
    log(f"=== Archival rate check: {RATE_CHECK_CALLS} calls back to back")
    results, times = [], []
    for _ in range(RATE_CHECK_CALLS):
        status, _raw, ms, err = fetch(ARCHIVAL, {"jsonrpc": "2.0", "id": "rate", "method": "block",
                                                  "params": {"block_id": REF_BLOCK}})
        results.append(status if status else "fail")
        times.append(ms)
    n_ok = results.count(200)
    n_429 = results.count(429)
    log(f"ok={n_ok}  http429={n_429}  other={RATE_CHECK_CALLS - n_ok - n_429}  "
        f"slowest={max(times)} ms  median={sorted(times)[len(times) // 2]} ms")

    log()
    log(f"=== Result: {core_ok}/{core_total} core checks passed")

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        print(f"\nSaved to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
