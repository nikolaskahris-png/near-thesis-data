"""Tests for scripts/burn.py on a simulated chain (no network).

Run: python -m unittest discover -s tests
"""
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import burn  # noqa: E402
import daily  # noqa: E402
import lock_window as lw  # noqa: E402

Y = 10 ** 24
H_FIRST, H_LAST = 1000, 1700  # the window; the chain goes on after it, as the real one does
CHAIN_END = 2400
# first block of each epoch: uneven lengths, so the search cannot rely on the guess
STARTS = [790, 900, 1010, 1105, 1290, 1403, 1695, 1990]
MINTED = [None, None, 9 * Y, 7 * Y, 8 * Y, 6 * Y, 5 * Y, 4 * Y]  # minted at each start
S0 = 1_000_000 * Y


def gap(h):
    return h % 13 == 0 or h in (1103, 1104)  # skipped heights, including a run just before a start


def epoch_index(h):
    return max(i for i, s in enumerate(STARTS) if s <= h)


def burnt_of(h):
    return (h % 7 + 1) * Y // 100  # 0.01 .. 0.07 NEAR a block, in one chunk


def build_chain():
    existing = [h for h in range(STARTS[0], CHAIN_END + 1) if not gap(h)]
    # a start that falls on a skipped height begins at the next existing block
    mint_at = {next(h for h in existing if h >= s): m for s, m in zip(STARTS, MINTED)}
    supply, prev = {}, None
    for h in existing:
        if prev is None:
            supply[h] = S0
        else:
            m = mint_at.get(h) or 0
            supply[h] = supply[prev] + m - burnt_of(h)
        prev = h
    return existing, supply


EXISTING, SUPPLY = build_chain()
# a start that falls on a skipped height begins at the next existing block
STARTS_REAL = [next(h for h in EXISTING if h >= s) for s in STARTS]


def epoch_of(h):
    return max(i for i, s in enumerate(STARTS_REAL) if s <= h)


class FakeBurnChain(lw.Chain):
    def __init__(self, break_at=None):
        super().__init__(url="fake", pause=0)
        self.break_at = break_at

    def _post(self, body):
        self.calls += 1
        h = body["params"]["block_id"]
        if h not in SUPPLY:
            return json.dumps({"jsonrpc": "2.0", "id": "lock", "error": {
                "name": "HANDLER_ERROR", "cause": {"name": "UNKNOWN_BLOCK", "info": {}}}}).encode()
        i = epoch_of(h)
        prev = max(x for x in EXISTING if x < h) if h > EXISTING[0] else None
        supply = SUPPLY[h]
        if h == self.break_at:
            supply += 1
        header = {"height": h, "hash": f"H{h}", "prev_height": prev, "prev_hash": f"H{prev}",
                  "epoch_id": f"E{i}", "next_epoch_id": f"E{i + 1}", "total_supply": str(supply)}
        chunks = [{"height_included": h, "balance_burnt": str(burnt_of(h) // 2)},
                  {"height_included": h, "balance_burnt": str(burnt_of(h) - burnt_of(h) // 2)},
                  {"height_included": h - 1, "balance_burnt": str(10 ** 30)}]  # not new: ignored
        return json.dumps({"jsonrpc": "2.0", "id": "lock",
                           "result": {"header": header, "chunks": chunks}}).encode()


def make_data(tmp, net_override=None):
    data = Path(tmp) / "data"
    data.mkdir()
    w0, w1 = H_FIRST, H_LAST - 3
    w0 = next(h for h in EXISTING if h >= w0)
    w1 = max(h for h in EXISTING if h <= w1)
    days = 2
    win = {"window": {"days": days}, "boundaries": [
        {"date": "2026-10-02", "height": w0, "hash": f"H{w0}"},
        {"date": "2026-10-03", "height": w1, "hash": f"H{w1}"}]}
    (data / "window_t.json").write_text(json.dumps(win), encoding="utf-8")
    net = (SUPPLY[w1] - SUPPLY[w0]) // days if net_override is None else net_override
    with (data / "history.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "new_supply_per_day"])
        w.writerow(["2026-10-03", daily.near(net)])
    return data, w0, w1


class BurnTest(unittest.TestCase):
    def measure(self, **kw):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        data, w0, w1 = make_data(tmp.name, kw.pop("net_override", None))
        burn.EPOCH_LENGTH = 100
        chain = FakeBurnChain(**kw)
        doc, problems = burn.run(chain, data / "window_t.json", data)
        return data, doc, problems, chain, (w0, w1)

    def test_finds_every_epoch_start_and_the_exact_totals(self):
        data, doc, problems, chain, (w0, w1) = self.measure()
        self.assertEqual(problems, [])
        starts = [e["start"] for e in doc["epochs"]]
        self.assertEqual(starts, [s for s in STARTS_REAL if w0 < s <= w1])
        self.assertEqual(starts[0], 1010)
        self.assertIn(1106, starts)  # 1105 is skipped: the start is the next existing block
        minted = sum(m for s, m in zip(STARTS, MINTED) if m and w0 < next(
            h for h in EXISTING if h >= s) <= w1)
        self.assertEqual(minted, 9 * Y + 7 * Y + 8 * Y + 6 * Y + 5 * Y)
        burnt = minted - (SUPPLY[w1] - SUPPLY[w0])
        r = doc["results"]
        self.assertEqual(r["epochs"], len(starts))
        self.assertEqual(r["minted_near"], daily.near(minted))
        self.assertEqual(r["burnt_near"], daily.near(burnt))
        self.assertEqual(r["net_near_per_day"], daily.near((SUPPLY[w1] - SUPPLY[w0]) // 2))
        self.assertTrue(r["net_equals_number_1"])
        self.assertEqual(r["hsp027_extra_burn_max_near_per_day"],
                         daily.near(__import__("fractions").Fraction(burnt, 2) * __import__("fractions").Fraction(3, 7)))
        # far fewer calls than a block-by-block scan
        self.assertLess(chain.calls, 150)

    def test_verify_offline_and_tampering(self):
        data, doc, problems, _, _ = self.measure()
        again, p = burn.compute(doc, data)
        self.assertEqual(p, [])
        self.assertEqual(again, doc["results"])
        # a changed raw block is caught by its sha256
        f = next((data / "raw" / "burn").glob("block_1010.json"))
        f.write_bytes(f.read_bytes().replace(b'"total_supply": "', b'"total_supply": "9'))
        _, p = burn.compute(doc, data)
        self.assertTrue(any("sha256" in x for x in p))

    def test_a_skipped_epoch_is_caught(self):
        data, doc, _, _, _ = self.measure()
        doc["epochs"].pop(1)  # forget one epoch start: the chain of epoch ids no longer links
        _, p = burn.compute(doc, data)
        self.assertTrue(any("previous epoch" in x for x in p))

    def test_identity_breaks_when_supply_does_not_follow_the_rule(self):
        _, doc, problems, _, _ = self.measure()
        self.assertEqual(problems, [])
        target = doc["identity"][2]["height"]
        _, _, problems, _, _ = self.measure(break_at=target)
        self.assertTrue(any(f"identity check at {target}" in x for x in problems), problems)

    def test_net_must_equal_number_1(self):
        _, _, problems, _, _ = self.measure(net_override=12345)
        self.assertTrue(any("differs from number 1" in x for x in problems))

    def test_treasury_share_uses_control_map_at_the_same_block(self):
        data, doc, _, _, (w0, w1) = self.measure()
        (data / "control_map.json").write_text(json.dumps({
            "block": {"height": w1}, "links": {"protocol_treasury": {"balance_change_near": "3.500"}}}))
        r, p = burn.compute(doc, data)
        self.assertEqual(p, [])
        self.assertEqual(r["treasury_share_of_minted"], "0.100000")  # 3.5 of 35 minted
        (data / "control_map.json").write_text(json.dumps({
            "block": {"height": w1 - 1}, "links": {"protocol_treasury": {"balance_change_near": "3.500"}}}))
        r, _ = burn.compute(doc, data)
        self.assertEqual(r["treasury_share_of_minted"], "")

    def test_new_chunks_only(self):
        r = json.loads(FakeBurnChain()._post({"params": {"block_id": 1500}}))["result"]
        self.assertEqual(burn.burnt_new(r), burnt_of(1500))


if __name__ == "__main__":
    unittest.main()
