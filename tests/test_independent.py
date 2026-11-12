"""A second implementation of three headline figures, written apart from scripts/ and importing none of it.

It reads only the raw RPC responses saved in data/raw/ and the day files that name the boundary blocks, and
recomputes:
  10.8%   NEAR the buybacks wallets kept / new NEAR, 2 October to 1 November 2026
  -3%     NEAR a day the three revenue wallets kept, 27 October - 8 November against 2 - 26 October
  2 of 4  confirmations of buybacks.multisignature.near against its member keys
Each is compared with data/numbers.json. A disagreement means one of the two implementations is wrong.
"""
import json
import unittest
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RAW = REPO / "data" / "raw"
NUMBERS = json.loads((REPO / "data" / "numbers.json").read_text(encoding="utf-8"))["numbers"]
BB, ONE, FE, INTENTS = ("buybacks.multisignature.near", "1csfundsadmin.sputnik-dao.near",
                        "fefundsadmin.sputnik-dao.near", "intents.near")


def raw(name):
    for d in (RAW / "accounts", RAW / "base_rates" / "blocks_accounts", RAW / "blocks"):
        p = d / name
        if p.exists():
            return json.loads(p.read_bytes())
    raise FileNotFoundError(name)


def native(h, acct):
    r = raw(f"{h}_{acct}.json")["result"]
    assert r["block_height"] == h
    return int(r["amount"])


def wnear(h, acct):
    r = raw(f"{h}_{acct}_intents_wnear.json")["result"]
    assert r["block_height"] == h
    return int(json.loads(bytes(r["result"]).decode()))


def header(h):
    return raw(f"block_{h}.json")["result"]["header"]


def first_block_of(day, h, prev):
    """The block at h is the first whose timestamp is at or after 00:00 UTC of day; the one before is earlier."""
    t = int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp()) * 10 ** 9
    b, p = header(h), header(prev)
    return int(b["timestamp"]) >= t > int(p["timestamp"]) and b["prev_hash"] == p["hash"]


def boundary(day):
    """Height and previous height of the first block of a day, from whichever day file names it."""
    for p in (REPO / "data" / "daily" / f"{day}.json",):
        if p.exists():
            e = json.loads(p.read_text(encoding="utf-8"))["end"]
            if e["date"] == day:
                return e["height"], e["previous_height"]
    d = json.loads((RAW / "base_rates" / "days" / f"{day}.json").read_text(encoding="utf-8"))
    return d["height"], d["previous_height"]


class Independent(unittest.TestCase):
    def test_coverage_10_8(self):
        a, ap = boundary("2026-10-02")
        b, bp = boundary("2026-11-01")
        self.assertTrue(first_block_of("2026-10-02", a, ap))
        self.assertTrue(first_block_of("2026-11-01", b, bp))
        kept = lambda h: native(h, BB) + wnear(h, BB) + native(h, ONE)
        new = int(header(b)["total_supply"]) - int(header(a)["total_supply"])
        cov = Fraction(kept(b) - kept(a), new)
        self.assertAlmostEqual(float(cov), float(NUMBERS["n1.coverage_buybacks"]["value"]), places=5)

    def test_private_path_change_minus_3(self):
        pts = {d: boundary(d) for d in ("2026-10-02", "2026-10-27", "2026-11-09")}
        for d, (h, p) in pts.items():
            self.assertTrue(first_block_of(d, h, p), d)
        three = lambda h: native(h, BB) + wnear(h, BB) + native(h, ONE) + native(h, FE) + wnear(h, FE)
        h0, h1, h2 = (pts[d][0] for d in ("2026-10-02", "2026-10-27", "2026-11-09"))
        before = Fraction(three(h1) - three(h0), 25)     # 2-26 October: the daily changes add up end to end
        after = Fraction(three(h2) - three(h1), 13)      # 27 October - 8 November
        change = after / before - 1
        self.assertAlmostEqual(float(change), float(NUMBERS["ps.change.kept_near_per_day"]["value"]), places=4)

    def test_two_of_four(self):
        conf = raw("../control/buybacks.multisignature.near_get_num_confirmations.json")["result"]
        k = int(json.loads(bytes(conf["result"]).decode()))
        keys = raw("../control/keys_buybacks.multisignature.near.json")["result"]["keys"]
        members = [x for x in keys if isinstance(x["access_key"]["permission"], dict)
                   and x["access_key"]["permission"]["FunctionCall"]["receiver_id"] == BB]
        full = [x for x in keys if x["access_key"]["permission"] == "FullAccess"]
        self.assertEqual(full, [])
        self.assertEqual(f"{k} of {len(members)}", NUMBERS["c.buybacks_confirmations"]["text"])


if __name__ == "__main__":
    unittest.main()
