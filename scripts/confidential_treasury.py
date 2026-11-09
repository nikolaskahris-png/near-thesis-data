"""What the Treasury account of NEAR Intents' Confidential Intents holds on the public chain, over time.

NEAR Intents' docs name the account: a shield transfer "moves them to the Treasury account
51e8f94d77b5e90dc9852ca6113771e11e8382ce69473a75e313e41665de7cbe", and an unshield is released from it
(docs.near-intents.org/integration/market-makers/confidential-liquidity). What it holds inside
intents.near backs balances on FAR, the private instance that public indexers do not see. Its value
over time is therefore how much has moved to the private path, read from the public chain.

For each date (the first of each month from April 2026, then every day from 2 October to the last
date read) at the first block of the day (the boundaries saved by base_rates.py):
  tokens   = intents.near mt_tokens_for_owner(Treasury account), every page
  balances = intents.near mt_batch_balance_of(Treasury account, tokens)
Decimals come from each token contract's ft_metadata. Value in USD = balance / 10^decimals x the
token's price at 12:00 UTC of the day before (coins.llama.fi prices/historical, within 3 hours), from,
in this order:
  1. coins.llama.fi's price for the token's own NEAR contract ("near:<contract>");
  2. for a token whose contract ends in .omft.near or .omdep.near (NEAR Intents' bridged tokens), the
     coingecko price of its symbol, from the fixed list SYMBOL_PRICE below;
  3. otherwise none: the token is counted as unpriced, and the number of unpriced tokens is reported.
Multi-token (nep245) balances are counted, not valued.

Read-only: JSON-RPC "query" (call_function) at archival blocks, and coins.llama.fi. No keys.
Every response is saved byte for byte with its SHA-256 in data/raw/confidential_treasury/;
--verify recomputes data/confidential_treasury.json with no network.

Usage:
    python scripts/confidential_treasury.py                  # fetch, compute, save (to LAST)
    python scripts/confidential_treasury.py --verify         # offline
    python scripts/confidential_treasury.py --daily          # every day after LAST with a data/daily file
    python scripts/confidential_treasury.py --verify-daily   # offline

data/confidential_treasury.json stops at LAST (8 November 2026) and is what numbers.json uses, so it
never changes. The days after LAST go to data/confidential_treasury_daily.json (--daily, run by the daily workflow), with the
same rules, at the block data/daily/D.json locks for day D (the same first-block-of-the-day rule).
rating.py reads both, for Avoid's private-path rule.
"""
import argparse
import base64
import hashlib
import json
import sys
from datetime import date, datetime, timedelta, timezone
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import daily  # noqa: E402
import fees  # noqa: E402
import lock_window as lw  # noqa: E402

REPO = lw.REPO
TREASURY = "51e8f94d77b5e90dc9852ca6113771e11e8382ce69473a75e313e41665de7cbe"
INTENTS = "intents.near"
RAW = "raw/confidential_treasury"
OUT = "confidential_treasury.json"
OUT_DAILY = "confidential_treasury_daily.json"
MONTHLY = [date(2026, m, 1) for m in range(4, 11)]
DAILY_FROM = date(2026, 10, 2)
LAST = date(2026, 11, 8)
PAGE = 100
BATCH = 50
PRICE_BATCH = 60
BRIDGED = (".omft.near", ".omdep.near")
# Symbol -> coingecko id, for NEAR Intents' bridged tokens only (rule 2). Nothing else is priced by symbol.
SYMBOL_PRICE = {
    "USDC": "usd-coin", "USDT": "tether", "USDT0": "tether", "USDt": "tether", "DAI": "dai", "xDAI": "xdai",
    "USDG": "global-dollar", "USD1": "usd1-wlfi", "ETH": "ethereum", "WETH": "ethereum", "BTC": "bitcoin",
    "cbBTC": "coinbase-wrapped-btc", "WBTC": "wrapped-bitcoin", "SOL": "solana", "STRK": "starknet",
    "XPL": "plasma", "ARB": "arbitrum", "SUI": "sui", "TRX": "tron", "APT": "aptos", "BERA": "berachain-bera",
    "PEPE": "pepe", "SHIB": "shiba-inu", "AURORA": "aurora-near", "UNI": "uniswap", "LINK": "chainlink",
    "AAVE": "aave", "BCH": "bitcoin-cash", "DASH": "dash", "ALEO": "aleo", "MOG": "mog-coin",
    "BOME": "book-of-meme", "WIF": "dogwifcoin", "TRUMP": "official-trump", "PENGU": "pudgy-penguins",
    "XAUT": "tether-gold", "GNO": "gnosis", "COW": "cow-protocol", "SAFE": "safe", "KNC": "kyber-network-crystal",
    "SPX": "spx6900", "TURBO": "turbo", "BRETT": "based-brett", "MOVE": "movement", "KAITO": "kaito",
    "ZEC": "zcash", "XRP": "ripple", "DOGE": "dogecoin", "LTC": "litecoin", "ADA": "cardano",
}
GROUPS = {"stablecoins": {"USDC", "USDT", "USDT0", "USDt", "DAI", "xDAI", "USDG", "USD1"},
          "NEAR": {"wNEAR"}, "BTC": {"BTC", "cbBTC", "WBTC", "NBTC", "xBTC"}, "ETH": {"ETH", "WETH"},
          "ZEC": {"ZEC"}}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def dates():
    out = list(MONTHLY)
    d = DAILY_FROM
    while d <= LAST:
        out.append(d)
        d += timedelta(1)
    return out


def height_of(data_root, d):
    doc = json.loads((data_root / "raw" / "base_rates" / "days" / f"{d.isoformat()}.json").read_text(encoding="utf-8"))
    return doc["height"]


def daily_dates(data_root):
    """Every day after LAST that has a locked day file, data/daily/D.json."""
    out = []
    for p in sorted((data_root / "daily").glob("*.json")):
        try:
            d = date.fromisoformat(p.stem)
        except ValueError:
            continue
        if d > LAST:
            out.append(d)
    return out


def daily_height(data_root, d):
    doc = json.loads((data_root / "daily" / f"{d.isoformat()}.json").read_text(encoding="utf-8"))
    return doc["end"]["height"]


def view(chain, account, method, args, block):
    params = {"request_type": "call_function", "account_id": account, "method_name": method,
              "args_base64": base64.b64encode(json.dumps(args).encode()).decode()}
    params.update({"block_id": block} if block is not None else {"finality": "final"})
    return chain._post({"jsonrpc": "2.0", "id": "ct", "method": "query", "params": params})


def result(raw):
    doc = json.loads(raw)
    if "error" in doc or "error" in doc.get("result", {}):
        return None
    return json.loads(bytes(doc["result"]["result"]).decode())


# ---------------------------------------------------------------- fetch
def fetch(data_root, ds=None, height=height_of):
    ds = dates() if ds is None else ds
    chain = lw.Chain()
    root = data_root / RAW
    files = {}

    def save(rel, raw):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(raw)
        files[f"data/{RAW}/{rel}"] = sha(raw)
        return raw

    def cached(rel, get):
        p = root / rel
        return save(rel, p.read_bytes() if p.exists() else get())

    contracts = set()
    for d in ds:
        h = height(data_root, d)
        tokens, i = [], 0
        while True:
            raw = cached(f"{h}/tokens_{i}.json", lambda: view(chain, INTENTS, "mt_tokens_for_owner",
                                                              {"account_id": TREASURY, "from_index": str(i * PAGE),
                                                               "limit": PAGE}, h))
            page = result(raw)
            if page is None:
                raise RuntimeError(f"{d}: mt_tokens_for_owner failed: {raw[:200]!r}")
            tokens += [t["token_id"] for t in page]
            if len(page) < PAGE:
                break
            i += 1
        for j in range(0, len(tokens), BATCH):
            ids = tokens[j:j + BATCH]
            cached(f"{h}/balances_{j // BATCH}.json", lambda: view(chain, INTENTS, "mt_batch_balance_of",
                                                                 {"account_id": TREASURY, "token_ids": ids}, h))
        contracts |= {t[len("nep141:"):] for t in tokens if t.startswith("nep141:")}
        print(f"{d}  block {h}  {len(tokens)} tokens  ({chain.calls} calls)", flush=True)
    for c in sorted(contracts):
        cached(f"metadata/{c}.json", lambda: view(chain, c, "ft_metadata", {}, None))
    meta = {c: result((root / f"metadata/{c}.json").read_bytes()) for c in sorted(contracts)}
    keys = sorted({f"near:{c}" for c in contracts} |
                  {f"coingecko:{SYMBOL_PRICE[m['symbol']]}" for c, m in meta.items()
                   if m and c.endswith(BRIDGED) and m.get("symbol") in SYMBOL_PRICE})
    for d in ds:
        day = d - timedelta(1)
        ts = int(datetime(day.year, day.month, day.day, 12, tzinfo=timezone.utc).timestamp())
        for k in range(0, len(keys), PRICE_BATCH):
            url = (f"https://coins.llama.fi/prices/historical/{ts}/{','.join(keys[k:k + PRICE_BATCH])}"
                   f"?searchWidth=3h")
            cached(f"prices/{day.isoformat()}_{k // PRICE_BATCH}.json", lambda: fees.fetch(url))
        print(f"prices {day}", flush=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"fetched_utc": stamp, "files": dict(sorted(files.items()))}


# ---------------------------------------------------------------- compute (offline)
def compute(data_root, fetched, ds=None, height=height_of):
    ds = dates() if ds is None else ds
    base = data_root.parent
    problems = []
    for rel, d in fetched["files"].items():
        p = base / rel
        if not p.exists() or sha(p.read_bytes()) != d:
            problems.append(f"missing or changed: {rel}")
    if problems:
        return None, problems
    root = data_root / RAW
    prices = {}
    for p in sorted((root / "prices").glob("*.json")):
        day = date.fromisoformat(p.stem.split("_")[0])
        noon = int(datetime(day.year, day.month, day.day, 12, tzinfo=timezone.utc).timestamp())
        for key, v in json.loads(p.read_bytes(), parse_float=Fraction)["coins"].items():
            if abs(v["timestamp"] - noon) <= 3 * 3600:
                prices.setdefault(key, {})[day] = Fraction(v["price"])
    meta = {p.stem: result(p.read_bytes()) for p in (root / "metadata").glob("*.json")}
    series = []
    for d in ds:
        h = height(data_root, d)
        tokens, bals = [], []
        for p in sorted((root / str(h)).glob("tokens_*.json"), key=lambda x: int(x.stem.split("_")[1])):
            tokens += [t["token_id"] for t in result(p.read_bytes())]
        for p in sorted((root / str(h)).glob("balances_*.json"), key=lambda x: int(x.stem.split("_")[1])):
            bals += result(p.read_bytes())
        if len(tokens) != len(bals):
            problems.append(f"{d}: {len(tokens)} tokens, {len(bals)} balances")
            continue
        day = d - timedelta(1)
        total, groups, unpriced, nep245, held = Fraction(0), {}, [], 0, 0
        for t, b in zip(tokens, bals):
            b = int(b)
            if b == 0:
                continue
            held += 1
            if not t.startswith("nep141:"):
                nep245 += 1
                continue
            c = t[len("nep141:"):]
            m = meta.get(c)
            price = None
            if m and m.get("decimals") is not None:
                price = prices.get(f"near:{c}", {}).get(day)
                if price is None and c.endswith(BRIDGED) and m.get("symbol") in SYMBOL_PRICE:
                    price = prices.get(f"coingecko:{SYMBOL_PRICE[m['symbol']]}", {}).get(day)
            if price is None:
                unpriced.append(c)
                continue
            v = Fraction(b, 10 ** m["decimals"]) * price
            total += v
            g = next((name for name, syms in GROUPS.items() if m.get("symbol") in syms), "other")
            groups[g] = groups.get(g, 0) + v
        series.append({"date": d.isoformat(), "block": h, "tokens_held": held, "priced_usd": fees.fmt(total, 0),
                       "by_group_usd": {g: fees.fmt(groups.get(g, 0), 0) for g in list(GROUPS) + ["other"]},
                       "unpriced_tokens": len(unpriced), "nep245_tokens": nep245})
    return {"measure": "value held by the Confidential Intents Treasury account inside intents.near",
            "account": TREASURY, "rules": __doc__.split("Usage:")[0].strip(),
            "series": series}, problems


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--daily", action="store_true")
    ap.add_argument("--verify-daily", action="store_true")
    ap.add_argument("--data", default=str(REPO / "data"))
    a = ap.parse_args()
    data_root = Path(a.data).resolve()
    daily_mode = a.daily or a.verify_daily
    path = data_root / (OUT_DAILY if daily_mode else OUT)
    height = daily_height if daily_mode else height_of
    if a.verify or a.verify_daily:
        if not path.exists():
            print(f"{path.name} is missing")
            sys.exit(1)
        doc = json.loads(path.read_text(encoding="utf-8"))
        ds = [date.fromisoformat(r["date"]) for r in doc["series"]] if daily_mode else None
        res, problems = compute(data_root, doc["fetched"], ds, height)
        if res is not None and {k: v for k, v in doc.items() if k != "fetched"} != res:
            problems.append(f"{path.name} differs from the recomputation")
    else:
        ds = daily_dates(data_root) if daily_mode else None
        if daily_mode and not ds:
            print(f"no day after {LAST} has a data/daily file yet")
            return 0
        fetched = fetch(data_root, ds, height)
        res, problems = compute(data_root, fetched, ds, height)
        if res is not None:
            res["fetched"] = fetched
            path.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8", newline="\n")
    if res:
        for r in res["series"]:
            g = r["by_group_usd"]
            print(f"{r['date']}  ${int(r['priced_usd']):>13,}  stable ${int(g['stablecoins']):>12,}  NEAR ${int(g['NEAR']):>12,}"
                  f"  unpriced {r['unpriced_tokens']}/{r['tokens_held']}")
    if problems:
        print("FAILED:\n  " + "\n  ".join(problems[:20]))
        sys.exit(1)
    print("OK" if (a.verify or a.verify_daily) else f"OK: saved data/{path.name}")


if __name__ == "__main__":
    main()
