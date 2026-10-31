"""Lock the block boundaries of a measurement window.

For every date from --start to --end (inclusive) this finds the first block
whose header timestamp is at or after 00:00:00 UTC of that date. Every number
in the project that covers a window is measured between these blocks.

Proof stored for each boundary:
  - the raw archival RPC response of the boundary block and of the block
    before it, saved byte for byte in data/raw/blocks/, with sha256;
  - boundary timestamp >= midnight > previous block timestamp;
  - boundary.prev_hash == hash of the previous block, so no block exists
    between them.

Read-only: JSON-RPC "block" calls. No API keys, nothing is written on chain.

Usage:
    python scripts/lock_window.py --start 2026-10-02 --end 2026-11-01
    python scripts/lock_window.py --verify data/window_2026-10-02_2026-11-01.json

--verify needs no network: it checks the saved file against the raw responses.
"""
import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

USER_AGENT = "near-thesis-data/0.1 (+https://github.com/nikolaskahris-png/near-thesis-data)"
RPC = "https://rpc.mainnet.fastnear.com"
ARCHIVAL = "https://archival-rpc.mainnet.fastnear.com"
RULE = "first block whose header timestamp is at or after 00:00:00 UTC of the date"
# The last boundary must be at least this old before it is locked,
# so the block is final and every node returns the same one.
SAFETY_SECONDS = 600
NS = 1_000_000_000
REPO = Path(__file__).resolve().parent.parent


class Chain:
    """Archival RPC access. Missing (skipped) heights return None."""

    def __init__(self, url=ARCHIVAL, pause=0.05):
        self.url = url
        self.pause = pause
        self.calls = 0
        self.raw = {}  # height -> raw response bytes
        self.headers = {}  # height -> header, so no block is fetched twice
        self.skipped = set()

    def _post(self, body):
        data = json.dumps(body).encode("utf-8")
        headers = {"User-Agent": USER_AGENT, "Content-Type": "application/json",
                   "Accept": "application/json"}
        for attempt in range(6):
            time.sleep(self.pause)
            self.calls += 1
            req = urllib.request.Request(self.url, data=data, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return resp.read()
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503, 504) and attempt < 5:
                    time.sleep(2 ** attempt)
                    continue
                raise RuntimeError(f"HTTP {e.code} from {self.url}") from None
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                if attempt < 5:
                    time.sleep(2 ** attempt)
                    continue
                raise RuntimeError(f"cannot reach {self.url}: {e}") from None
        raise RuntimeError("unreachable")

    def block(self, height):
        """Return the block header dict at this height, or None if the height was skipped."""
        if height in self.headers:
            return self.headers[height]
        if height in self.skipped:
            return None
        raw = self._post({"jsonrpc": "2.0", "id": "lock", "method": "block",
                          "params": {"block_id": height}})
        doc = json.loads(raw)
        if "error" in doc:
            cause = (doc["error"].get("cause") or {}).get("name", "")
            if cause == "UNKNOWN_BLOCK":
                self.skipped.add(height)
                return None
            raise RuntimeError(f"RPC error at height {height}: {json.dumps(doc['error'])[:300]}")
        self.raw[height] = raw
        self.headers[height] = doc["result"]["header"]
        return self.headers[height]

    def final_header(self):
        raw = self._post({"jsonrpc": "2.0", "id": "lock", "method": "block",
                          "params": {"finality": "final"}})
        doc = json.loads(raw)
        if "error" in doc:
            raise RuntimeError(f"RPC error for final block: {json.dumps(doc['error'])[:300]}")
        return doc["result"]["header"]


def first_existing(chain, h, top):
    """First existing block at height h..top-1, as (height, header), or None."""
    while h < top:
        hdr = chain.block(h)
        if hdr is not None:
            return h, hdr
        h += 1
    return None


def find_boundary(chain, target_ns, guess, step=2000):
    """Return (boundary header, previous header) for a target timestamp.

    boundary = first existing block with timestamp >= target_ns;
    previous = the existing block right before it (timestamp < target_ns).
    """
    found = first_existing(chain, guess, guess + 1000)
    if found is None:
        raise RuntimeError(f"no block found near height {guess}")
    h, hdr = found
    lo = hi = None
    if hdr["timestamp"] >= target_ns:
        hi = h
        while lo is None:  # walk down until a block before the target
            cand = max(1, hi - step)
            found = first_existing(chain, cand, hi)
            if found is not None and found[1]["timestamp"] < target_ns:
                lo = found[0]
            elif found is not None:
                hi = found[0]
            step *= 2
    else:
        lo = h
        while hi is None:  # walk up until a block at or after the target
            found = first_existing(chain, lo + step, lo + step + 1000)
            if found is None:
                raise RuntimeError(f"no block found near height {lo + step}")
            if found[1]["timestamp"] >= target_ns:
                hi = found[0]
            else:
                lo = found[0]
            step *= 2

    # Binary search in (lo, hi]; heights in [top, hi) are known to be skipped.
    top = hi
    while top - lo > 1:
        mid = (lo + top) // 2
        found = first_existing(chain, mid, top)
        if found is None:
            top = mid
            continue
        m, hdr = found
        if hdr["timestamp"] >= target_ns:
            hi = top = m
        else:
            lo = m
    return chain.block(hi), chain.block(lo)


def midnight_ns(d):
    return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp()) * NS


def iso(ns):
    return datetime.fromtimestamp(ns // NS, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") \
        + f".{ns % NS:09d}Z"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def summary(hdr):
    return {"height": hdr["height"], "hash": hdr["hash"], "prev_hash": hdr["prev_hash"],
            "timestamp_ns": str(hdr["timestamp_nanosec"]), "timestamp_utc": iso(hdr["timestamp"]),
            "total_supply_yocto": hdr["total_supply"]}


def lock(chain, start, end, data_dir):
    """Find, check and save every boundary. Returns the window document."""
    final = chain.final_header()
    last_target = midnight_ns(end)
    if final["timestamp"] < last_target + SAFETY_SECONDS * NS:
        ready = iso(last_target + SAFETY_SECONDS * NS)
        raise SystemExit(f"Too early: the last boundary ({end} 00:00 UTC) is not final yet. "
                         f"Run again after {ready[:16]} UTC.")

    # Average block time from the final block back to a fixed reference, for the first guess.
    ref = chain.block(217453248)
    ns_per_block = (final["timestamp"] - ref["timestamp"]) / (final["height"] - ref["height"])

    raw_dir = data_dir / "raw" / "blocks"
    raw_dir.mkdir(parents=True, exist_ok=True)
    boundaries = []
    d = start
    anchor = final
    while d <= end:
        target = midnight_ns(d)
        guess = int(anchor["height"] - (anchor["timestamp"] - target) / ns_per_block)
        before = chain.calls
        hdr, prev = find_boundary(chain, target, guess)
        assert hdr["timestamp"] >= target > prev["timestamp"], d
        assert hdr["prev_hash"] == prev["hash"], d
        entry = {"date": d.isoformat(), "target_utc": iso(target)[:19] + "Z"}
        entry.update(summary(hdr))
        entry["previous"] = {k: v for k, v in summary(prev).items()
                             if k in ("height", "hash", "timestamp_ns", "timestamp_utc")}
        files = {}
        for h in (hdr["height"], prev["height"]):
            path = raw_dir / f"block_{h}.json"
            path.write_bytes(chain.raw[h])
            files[path.relative_to(data_dir.parent).as_posix()] = sha256(chain.raw[h])
        entry["raw_files"] = files
        boundaries.append(entry)
        print(f"{d}  block {hdr['height']:>11,}  {entry['timestamp_utc'][:23]}  "
              f"previous {prev['height']:>11,}  {entry['previous']['timestamp_utc'][11:23]}  "
              f"({chain.calls - before} calls)", flush=True)
        anchor = hdr
        d += timedelta(days=1)

    return {
        "window": {"start": start.isoformat(), "end": end.isoformat(),
                   "days": (end - start).days, "boundaries": len(boundaries), "rule": RULE},
        "source": {"rpc": ARCHIVAL, "method": "block"},
        "boundaries": boundaries,
    }


def verify(path):
    """Offline check of a window file against its raw responses. Returns a list of problems."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    base = Path(path).resolve().parent.parent
    problems = []
    prev_height = 0
    expected = date.fromisoformat(doc["window"]["start"])
    for b in doc["boundaries"]:
        tag = b["date"]
        if b["date"] != expected.isoformat():
            problems.append(f"{tag}: expected date {expected}")
        expected += timedelta(days=1)
        headers = {}
        for rel, digest in b["raw_files"].items():
            raw = (base / rel).read_bytes()
            if sha256(raw) != digest:
                problems.append(f"{tag}: sha256 differs for {rel}")
                continue
            hdr = json.loads(raw)["result"]["header"]
            headers[hdr["height"]] = hdr
        hdr, prev = headers.get(b["height"]), headers.get(b["previous"]["height"])
        if hdr is None or prev is None:
            problems.append(f"{tag}: raw block missing")
            continue
        target = midnight_ns(date.fromisoformat(b["date"]))
        if summary(hdr) != {k: b[k] for k in summary(hdr)}:
            problems.append(f"{tag}: fields differ from raw block")
        if not hdr["timestamp"] >= target > prev["timestamp"]:
            problems.append(f"{tag}: timestamps do not straddle midnight")
        if hdr["prev_hash"] != prev["hash"]:
            problems.append(f"{tag}: previous block is not the direct parent")
        if hdr["height"] <= prev_height:
            problems.append(f"{tag}: heights not increasing")
        prev_height = hdr["height"]
    if len(doc["boundaries"]) != doc["window"]["boundaries"]:
        problems.append("boundary count differs from window header")
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--start", type=date.fromisoformat, help="first date, YYYY-MM-DD")
    parser.add_argument("--end", type=date.fromisoformat, help="last date, YYYY-MM-DD")
    parser.add_argument("--data-dir", type=Path, default=REPO / "data",
                        help="where to write (default: data/ of this repo)")
    parser.add_argument("--verify", metavar="FILE", help="check a window file offline")
    args = parser.parse_args()

    if args.verify:
        problems = verify(args.verify)
        doc = json.loads(Path(args.verify).read_text(encoding="utf-8"))
        n = len(doc["boundaries"])
        if problems:
            print("\n".join(problems))
            print(f"FAILED: {len(problems)} problem(s) in {n} boundaries")
            return 1
        print(f"OK: {n} boundaries, raw sha256, timestamps and parent hashes all check out")
        return 0

    if not (args.start and args.end) or args.end < args.start:
        parser.error("give --start and --end (end on or after start), or --verify FILE")

    args.data_dir = args.data_dir.resolve()
    chain = Chain()
    t0 = time.monotonic()
    doc = lock(chain, args.start, args.end, args.data_dir)
    out = args.data_dir / f"window_{args.start}_{args.end}.json"
    out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8", newline="\n")
    problems = verify(out)
    print(f"\n{len(doc['boundaries'])} boundaries, {chain.calls} RPC calls, "
          f"{time.monotonic() - t0:.0f} s")
    print(f"Saved {out}")
    if problems:
        print("\n".join(problems))
        print("FAILED offline check")
        return 1
    print("Offline check: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
