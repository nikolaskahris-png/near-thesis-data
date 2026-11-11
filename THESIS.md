# Thesis: NEAR's value capture is real, small and discretionary

*Investment Thesis track, NEAR HACKATHON. Dated 9 November 2026; horizon 1 January 2031, checked every 12 months. Window 2 October → 1 November 2026 (00:00 UTC), blocks 218,126,921 → 222,491,356 (`data/window_2026-10-02_2026-11-01.json`). Every other figure measured here is copied from [`data/numbers.json`](data/numbers.json) with a hidden marker, and `python scripts/build_numbers.py --check THESIS.md` fails if one differs. Thresholds are the author's choice. The longer version of this file, as of 8 November, is in [DETAILS](docs/DETAILS.md#thesis-in-full-version-3-8-november).*

## Claim

Users pay real fees on NEAR Intents, but only a small part reaches NEAR holders: the buybacks ([Terms](README.md#terms)) keep NEAR equal to <!--n:n1.coverage_buybacks-->10.8%<!--/n--> of new issuance and burn none. Every link from the fee a user pays to the NEAR a holder keeps can be changed by a few signers (<!--n:c.buybacks_confirmations-->2 of 4<!--/n--> for the buybacks wallet) or by a company off-chain; none is fixed in code. Issuance, on the other side of the ledger, is a protocol rule.

**Rating: Hold, not Buy, to 1 January 2031.** Hold means keeping NEAR already owned, staked: staking pays about <!--n:iv.staking_yield_gross-->5.0%<!--/n--> a year before the validator's commission while supply grows <!--n:iv.issuance_rate_per_year-->2.46%<!--/n-->, so a staked holder's share of all NEAR rises. It is not a Buy because what holders get from fees covers a small part of issuance and nothing obliges anyone to keep it. Growth is not what is missing: from April to October what the buybacks kept grew <!--n:bt.a_pace.near_multiple-->×2.1<!--/n--> in NEAR and <!--n:bt.a_pace.usd_multiple-->×7.5<!--/n--> in dollars, more than Buy's growth test asks (<!--n:bt.a_pace.required_multiple-->×1.32<!--/n-->), though from a low April and mostly through the share of fees NEAR keeps (<!--n:lr.history.2026-04_2026-10.take_rate_multiple-->×4.2<!--/n-->), which has a ceiling; a published rule is. If you hold no NEAR, Hold means do not buy yet; Avoid would mean not holding it for this thesis.

The rating turns to **Buy** only when keeping the buybacks becomes a published rule, and then either the buybacks cover issuance or, at a yearly check, what they keep has grown <!--n:lr.required_growth.buybacks.A.2031-->+75%<!--/n--> a year in dollars and in NEAR. It turns to **Avoid** if two 30-day windows in a row fail a test: the wallets keep less than 75% of DefiLlama's revenue, or the buybacks keep April's dollars or less. The rules as code, every edge case included, are in the [README](README.md#the-rating-as-rules).

## Evidence for

**Real.** Users pay <!--n:n2.fees_usd_per_day-->$206,049<!--/n--> a day in fees, <!--n:n2.fees_bps-->16.0<!--/n--> bps of volume (DefiLlama, from a dataset on Dune that is not rebuilt here). On chain, the wallets' balances agree with DefiLlama's revenue (<!--n:n1.coverage_with_front_end-->16.5%<!--/n--> and <!--n:n2.defillama_revenue_coverage-->16.5%<!--/n--> of issuance): almost nothing flows out.

**It did not stop when the flow went private.** Tideline, another public repository, reports private settlement growing from 27 October. Read on mainnet, the three revenue wallets kept <!--n:ps.after.kept_near_per_day-->13,800<!--/n--> NEAR a day from then to 8 November, against <!--n:ps.before.kept_near_per_day-->14,261<!--/n--> from 2 to 26 October (<!--n:ps.change.kept_near_per_day-->-3%<!--/n-->, inside the range of any <!--n:ps.after.days-->13<!--/n--> days before), while DefiLlama's revenue, which counts the same wallets, changed <!--n:ps.change.revenue_near_per_day-->-6%<!--/n--> in NEAR. With the change on other days from 20 October to 2 November, the wallets' change runs from <!--n:ps.cut.kept_near_lowest-->-13%<!--/n--> to <!--n:ps.cut.kept_near_highest-->-3%<!--/n-->; Tideline's date gives the smallest fall. In dollars both fell about a fifth (<!--n:ps.change.kept_usd_per_day-->-19%<!--/n--> and <!--n:ps.change.revenue_usd_per_day-->-21%<!--/n-->).

**Small.** The buybacks wallets keep <!--n:n1.buybacks_near_per_day-->9,570<!--/n--> of the <!--n:n1.new_near_per_day-->88,392<!--/n--> NEAR issued a day: coverage <!--n:n1.coverage_buybacks-->10.8%<!--/n--> (<!--n:n1.coverage_with_front_end-->16.5%<!--/n--> with the front-end fund). It has been below a quarter of issuance in every month since April (highest <!--n:f1.coverage_buybacks.2026-09-->15.3%<!--/n-->). If NEAR kept every fee, coverage would be <!--n:n2.max_coverage-->47.9%<!--/n-->.

**Discretionary.** Each link can be changed by people (`scripts/control_map.py`, `scripts/control_history.py`):

- The bought NEAR, <!--n:n1.buybacks_held_near-->2,145,248<!--/n--> at the end block, sits in wallets that <!--n:c.buybacks_confirmations-->2 of 4<!--/n--> signers can move, and none is burned; with the front-end fund (<!--n:c.front_end_transfer-->2 of 5<!--/n-->), <!--n:n1.wallets_held_near-->4,109,089<!--/n--> NEAR.
- The fee in the contract is <!--n:c.intents_fee_pips-->1 pip<!--/n-->; what users pay is set off-chain, and the terms of 1Click, NEAR Intents' swap service, let its operator change fees "at any time on a prospective basis".
- `treasury.near` paid out <!--n:ts.year_out_near-->30,171,200<!--/n--> NEAR in April and May 2026, each payment a <!--n:c.treasury_confirmations-->2 of 4<!--/n--> multisig confirmation.
- Not a buybacks link, but the same way of setting things: one account raised the NEAR AI credits rate <!--n:f6.change1.ratio-->×2.0<!--/n--> on <!--n:f6.change1.utc-->2026-09-29 14:21 UTC<!--/n-->, with no proposal of the owner's DAO.
- HSP-029, the issuance cut, passed with <!--n:f8.approval_share-->100.0%<!--/n--> of the veNEAR (locked NEAR's voting weight) cast for or against, on a turnout of <!--n:f8.turnout_of_snapshot-->62.3%<!--/n-->; as stake-weighted votes allow, <!--n:f8.fewest_voters_reaching_quorum-->6<!--/n--> of its <!--n:f8.voters-->36<!--/n--> voters held enough veNEAR to reach the quorum alone. The vote executes nothing on chain; it takes effect when validators run a release that includes it, the same step that protects issuance.

Issuance, by contrast, is code: at most <!--n:c.issuance_max_inflation_rate-->1/40<!--/n--> a year, changed only by a release run by <!--n:c.issuance_upgrade_stake_threshold-->4/5<!--/n--> of stake (at least <!--n:c.issuance_validators_to_pass_upgrade-->44<!--/n--> of <!--n:c.issuance_validators-->381<!--/n--> validators), as the halving upgrade was.

## Evidence against

1. **The policy has been kept.** From April to October the wallets kept <!--n:f2.wallets_kept_share_of_revenue.2026-04_2026-10-->96.9%<!--/n--> of DefiLlama's revenue, and the buybacks wallet's keys have not changed since <!--n:h.keys.buybacks.last_change-->2026-03-18<!--/n-->. "Discretionary" describes what can change, not a change that has happened.
2. **Capture is rising, in dollars.** From April to October what the buybacks keep grew <!--n:lr.history.2026-04_2026-10.buybacks_kept_usd_multiple-->×7.5<!--/n--> in dollars (<!--n:lr.history.2026-04_2026-10.buybacks_kept_near_multiple-->×2.1<!--/n--> in NEAR). "Small" may not last.
3. **Part of "small" is the price.** Revenue is earned in dollars and issuance paid in NEAR: at <!--n:n2.equilibrium_price_usd-->$2.33<!--/n--> or less every fee would buy as many NEAR as are issued.
4. **Governance is moving toward rules.** HSP-027 passed and has been in effect since <!--n:pr.v87.first_utc-->2026-11-04 11:46 UTC<!--/n-->, <!--n:pr.v87.days_from_hsp027_passed-->124<!--/n--> days after the vote. HSP-029 passed; at its target rate the ceiling would be <!--n:n2.hsp029_max_coverage-->74.8%<!--/n-->.
5. **Counting Intents, NEAR is the cheapest L1 here.** Its market cap is <!--n:peer.near_all.mcap_to_revenue-->234×<!--/n--> a year of revenue with Intents, against <!--n:peer.solana.mcap_to_revenue-->1,995×<!--/n--> for Solana and <!--n:peer.ethereum.mcap_to_revenue-->3,394×<!--/n--> for Ethereum; on gas alone it is <!--n:peer.near_l1.mcap_to_revenue-->4,091×<!--/n--> ([peers](docs/DETAILS.md#peers-on-one-basis)).

## What would change our mind

| Part of the claim | We are wrong if | Today | Check |
|---|---|---|---|
| Small | the buybacks wallets keep 25% or more of issuance in three consecutive calendar months | highest month <!--n:f1.coverage_buybacks.2026-09-->15.3%<!--/n--> | `scripts/coverage.py` |
| Discretionary | bought NEAR moves by a published rule to an account no one can spend from, or the contract's fee is raised with its collector set to the buybacks or a locked account | <!--n:c.buybacks_confirmations-->2 of 4<!--/n--> multisig; fee <!--n:c.intents_fee_pips-->1 pip<!--/n--> | `scripts/control_map.py` |
| Small, to 2031 | at a yearly check, what the buybacks keep has grown <!--n:lr.required_growth.buybacks.A.2031-->+75%<!--/n--> a year in dollars and in NEAR | <!--n:iv.buybacks_kept_usd_per_day-->$46,692<!--/n--> a day | `scripts/rating.py` |
| Did not stop when private | PREREG-3's P6 fails: from 9 November to 9 December the buybacks keep less than half the dollars a day of the 2 October window | <!--n:iv.buybacks_kept_usd_per_day-->$46,692<!--/n--> a day in the window; the three wallets kept <!--n:ps.after.kept_near_per_day-->13,800<!--/n--> NEAR a day, 27 October to 8 November | `scripts/private_shift.py`; P6 judged 9 December |
| Issuance is the only rule | HSP-029 is still not in force on 1 November 2027 | in timelock until <!--n:f8.timelock_end_utc-->2026-11-16 16:48 UTC<!--/n--> | `scripts/upgrade_watch.py` |

A row can prove the claim wrong while the rating stays Hold: Buy also needs a published rule, which we put at 0.25 by 2031 ([how likely a rule is](docs/DETAILS.md#how-likely-a-rule-is)). The thresholds are the author's; with other floors and growth rates, and even with a published rule assumed, all <!--n:sens.month_ratings-->378<!--/n--> monthly ratings from April to October are Hold (`scripts/sensitivity.py`), because a monthly rating reaches Buy only through coverage of 100%. The growth test is judged once a year, and with a published rule the April–October history would already pass it (<!--n:bt.a_pace.near_multiple-->×2.1<!--/n--> in NEAR and <!--n:bt.a_pace.usd_multiple-->×7.5<!--/n--> in dollars, against <!--n:bt.a_pace.required_multiple-->×1.32<!--/n-->). Until 1 December 2026 the rating cannot be anything but Hold, because Avoid needs a window 30 days earlier and the daily history starts on 1 November. Eight predictions are anchored on NEAR mainnet before they are judged, and none has been amended ([`PREREG.md`](PREREG.md), [`PREREG-2.md`](PREREG-2.md), [`PREREG-3.md`](PREREG-3.md)).

## Metrics we cannot compute

- **Fees and volume from the chain.** They come from NEAR's datasets on Dune, through DefiLlama; the NEAR Intents Explorer API needs a partner key. Solver spreads and gas are not in the fees.
- **The private path.** Volume and fees settled on FAR are not visible; only what the Treasury account holds on mainnet is read.
- **Which fees fund the buybacks.** What arrives in the wallets is measured; no swap from fee income to those inflows is traced.
- **Credits in dollars, and their use.** An off-chain NEAR AI Cloud setting, read only when signed in.
- **Purposes.** Who holds an account and why NEAR moved are not on chain; amounts, blocks and transactions are.

## Reproduce

Python standard library only, no network, no keys. One command rebuilds every number and every chart's
input from the committed raw files, checks every marked figure in this file, the README and the details, and
ends with `REBUILD: PASS`:

```
python scripts/rebuild.py
```

The charts, each with its query: [dashboard](https://nikolaskahris-png.github.io/near-thesis-data/dashboard/).
