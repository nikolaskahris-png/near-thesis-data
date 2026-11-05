"""Tests for scripts/longrun.py (no network, synthetic and window-level inputs).

Run: python -m unittest discover -s tests
"""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import longrun as lr  # noqa: E402

START = datetime(2026, 11, 1, tzinfo=timezone.utc)
RATIFIED = datetime(2026, 11, 16, 16, 48, 8, tzinfo=timezone.utc)
S0 = D("1310472976.201")
NEW = D("88392.087")
KEPT = {"buybacks": D("9569.750"), "with_front_end": D("14554.423"), "all_fees": D("42332.3")}


def run(**over):
    args = dict(s0=S0, new_per_day=NEW, max_rate=Fraction(1, 40), epoch_days=D(30) / 101,
                start=START, ratified=RATIFIED, kept=KEPT, staking_yield=D("0.0496"),
                take_share=D("0.3438"), history={"kept": (D("4945.224"), D("14564.0"))})
    args.update(over)
    return lr.model(**args)


class LongRunTest(unittest.TestCase):
    def test_calibration_first_epoch_equals_window_issuance(self):
        r = run()
        self.assertEqual(r["lr.first_epoch_issuance_per_day"][0], NEW)
        self.assertLess(abs(r["lr.k"][0] - D("0.98545")), D("0.0001"))

    def test_ramp_matches_the_proposal(self):
        m = lr.MONTH_DAYS
        self.assertEqual(lr.cap_b(D(-1)), D("0.025"))           # before activation
        self.assertEqual(lr.cap_b(D(0)), D("0.025"))
        self.assertEqual(lr.cap_b(6 * m), D("0.02275"))          # proposal: M6 2.275%
        self.assertEqual(lr.cap_b(12 * m), D("0.0205"))          # M12 2.050%
        self.assertEqual(lr.cap_b(18 * m), D("0.01825"))         # M18 1.825%
        self.assertEqual(lr.cap_b(24 * m), D("0.016"))           # M24 1.600%
        self.assertEqual(lr.cap_b(60 * m), D("0.016"))           # flat after the ramp

    def test_ramp_is_linear_per_epoch_not_a_staircase(self):
        m = lr.MONTH_DAYS
        a, b, c = lr.cap_b(3 * m), lr.cap_b(3 * m + D("0.3")), lr.cap_b(3 * m + D("0.6"))
        self.assertGreater(a, b)
        self.assertEqual(a - b, b - c)

    def test_paths_agree_before_activation(self):
        t0 = RATIFIED + timedelta(days=lr.HSP029_GRACE_DAYS)
        mark = t0 - timedelta(days=10)
        a = lr.run_path(S0, D("0.98545"), D(30) / 101, START, mark, lambda t: D("0.025"), [mark])
        b = lr.run_path(S0, D("0.98545"), D(30) / 101, START, mark,
                        lambda t: lr.cap_b(lr.days_between(t0, t)), [mark])
        self.assertEqual(a[mark], b[mark])

    def test_cross_check_with_the_proposal(self):
        r = run()
        self.assertEqual(lr.check(r), [])
        for n in ("2y", "6y"):
            self.assertLess(abs(r[f"lr.not_issued_B_vs_proposal.{n}"][0]), lr.CROSS_CHECK_TOLERANCE)
        old = dict(lr.PROPOSAL_NOT_ISSUED)
        try:
            lr.PROPOSAL_NOT_ISSUED["2y"] = D(20_000_000)
            self.assertTrue(any("2y" in p for p in lr.check(run())))
        finally:
            lr.PROPOSAL_NOT_ISSUED.update(old)

    def test_growth_inverts_to_the_issuance_of_the_year(self):
        r = run()
        for p in ("A", "B", "B_late"):
            for y in lr.TARGET_YEARS:
                for name, k0 in KEPT.items():
                    g = r[f"lr.required_growth.{name}.{p}.{y}"]
                    years = D(g[2]["years"])
                    target = r[f"lr.required_multiple.{name}.{p}.{y}"][0] * k0
                    back = k0 * ((1 + g[0]).ln() * years).exp()
                    self.assertLess(abs(back / target - 1), D("1e-25"))

    def test_hsp029_needs_less_growth_and_late_needs_more(self):
        r = run()
        for y in lr.TARGET_YEARS:
            a, b, late = (r[f"lr.required_growth.all_fees.{p}.{y}"][0] for p in ("A", "B", "B_late"))
            self.assertLess(b, a)
            self.assertLessEqual(b, late)
        # after the ramp both HSP-029 paths run at 1.6%: the yield ratio is the proposal's 0.64
        self.assertEqual(r["lr.yield_gross.B.2031"][0] / D("0.0496"), D("0.64"))
        self.assertEqual(r["lr.take_rate_ceiling_multiple"][0], 1 / D("0.3438"))

    def test_every_key_names_its_assumptions_or_a_note(self):
        for key, (_, kind, extra) in run().items():
            self.assertTrue(key.startswith("lr."))
            self.assertTrue("note" in extra or "assumptions" in extra, key)
            if key.startswith(("lr.required_", "lr.issuance_per_day.")):
                self.assertTrue(extra["assumptions"], key)


    def test_base_sensitivity(self):
        r = run()
        bases = {"2026-04": {"buybacks": D("4674.519"), "with_front_end": D("4945.224")},
                 "2026-09": {"buybacks": D("13478.332"), "with_front_end": D("18806.030")},
                 "2026-04_2026-09": {"buybacks": D("8000"), "with_front_end": D("10000")}}
        out = lr.base_sensitivity(r, bases)
        for p in ("A", "B"):
            for name in ("buybacks", "with_front_end"):
                key = f"lr.required_growth.{name}.{p}.2031"
                years = D(r[key][2]["years"])
                target = r[f"lr.issuance_per_day.{p}.2031"][0]
                for base, level in bases.items():
                    g = out[f"{key}.base.{base}"][0]
                    self.assertLess(abs(level[name] * ((1 + g).ln() * years).exp() / target - 1), D("1e-25"))
                # a lower base level needs faster growth; the average is not a month
                self.assertEqual(out[f"{key}.base_max"][2]["month"], "2026-04")
                self.assertEqual(out[f"{key}.base_min"][2]["month"], "2026-09")
        # the window's own level gives the main figure back
        same = lr.base_sensitivity(r, {"w": dict(KEPT)})
        self.assertEqual(same["lr.required_growth.buybacks.B.2031.base.w"][0], r["lr.required_growth.buybacks.B.2031"][0])

    def test_usd_scenarios(self):
        r = run()
        usd = {"buybacks": D("46692.3"), "all_fees": D("206049.33")}
        out = lr.usd_scenarios(r, usd)
        for p in ("A", "B"):
            issued = r[f"lr.issuance_per_day.{p}.2031"][0]
            # no growth: today's dollars over 2031's issuance
            self.assertEqual(out[f"lr.scenario.0.cover_price.buybacks.{p}.2031"][0], usd["buybacks"] / issued)
            # +100% a year: doubles every year
            years = D(out[f"lr.scenario.100.cover_price.all_fees.{p}.2031"][2]["years"])
            want = usd["all_fees"] * (D(2).ln() * years).exp() / issued
            self.assertEqual(out[f"lr.scenario.100.cover_price.all_fees.{p}.2031"][0], want)
            prices = [out[f"lr.scenario.{g}.cover_price.buybacks.{p}.2031"][0] for g in ("0", "25", "50", "100")]
            self.assertEqual(prices, sorted(prices))
        # HSP-029 issues less, so the same dollars cover issuance up to a higher price
        self.assertGreater(out["lr.scenario.50.cover_price.buybacks.B.2031"][0],
                           out["lr.scenario.50.cover_price.buybacks.A.2031"][0])

if __name__ == "__main__":
    unittest.main()
