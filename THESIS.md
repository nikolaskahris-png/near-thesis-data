# Thesis: NEAR's value capture is real, small and discretionary

*Investment Thesis track, NEAR HACKATHON. Dated 3 November 2026; horizon 12 months, to November 2027.
Measurement window 2 October → 1 November 2026 (00:00 UTC), blocks 218,126,921 → 222,491,356. Every figure here
is copied from [`data/numbers.json`](data/numbers.json) with a hidden marker of its key, and
`python scripts/build_numbers.py --check THESIS.md` fails if any differs. Figures from DefiLlama are
provisional until its data settles. Thresholds are the author's choice; block heights, dates and protocol
constants are written as they are. The data, method and findings are in the [README](README.md).*

## Claim

Users pay real fees on NEAR Intents, but only a small part reaches NEAR holders, and every link from the fee a
user pays to the NEAR a holder keeps is set by a few signers or by a company off-chain, not by code. Issuance,
on the other side of the ledger, is a protocol rule. Holding NEAR long term is therefore a bet on three
conditions, not a claim on today's fees: **(a)** what the buybacks wallets keep approaches the NEAR issued,
**(b)** the buybacks become a rule rather than a choice, and **(c)** stake in the NEAR AI farm spreads beyond one
account. Until then: hold NEAR staked with a validator, not for the fees it captures. At today's revenue,
front-end fund included, the wallets would cover issuance only at a NEAR price of <!--n:iv.revenue_equilibrium_price_usd-->$0.80<!--/n--> or less, against a mean of
<!--n:f2.mean_price_usd.2026-10-->$4.89<!--/n--> in October: because revenue is earned in dollars and issuance is paid in NEAR, the
higher the price, the less the wallets cover.

A Breakpoint 2025 debate put the case against buybacks as "the promise of future buybacks is worth exactly as
much as your faith in those founders", and the case for them as on-chain transparency
([debate](https://solanacompass.com/learn/breakpoint-25/this-house-believes-that-token-buybacks-are-a-net-negative-value-accrual-mechanism)).
For NEAR, this repository measures both: the transparency is real, since every link is read on chain, and the
faith is still required, since no link is a rule.

## Evidence for

**Real.** Users pay <!--n:n2.fees_usd_per_day-->$206,049<!--/n--> a day in fees, <!--n:n2.fees_bps-->16.0<!--/n--> bps of volume
(DefiLlama). DefiLlama's revenue ÷ issuance gives <!--n:n2.defillama_revenue_coverage-->16.5%<!--/n--> and the wallets'
own balances give <!--n:n1.coverage_with_front_end-->16.5%<!--/n-->: DefiLlama counts what flows into the wallets and we
read their balances, so the two agreeing means the revenue arrives and almost none flows out.

**Small.** The buybacks wallets keep <!--n:n1.buybacks_near_per_day-->9,570<!--/n--> of the
<!--n:n1.new_near_per_day-->88,392<!--/n--> NEAR issued a day: coverage <!--n:n1.coverage_buybacks-->10.8%<!--/n-->,
<!--n:n1.coverage_with_front_end-->16.5%<!--/n--> with the front-end fund. It has been below a quarter of issuance in every
month since April (highest: <!--n:f1.coverage_buybacks.2026-09-->15.3%<!--/n-->, September). If NEAR kept every fee, coverage
would be <!--n:n2.max_coverage-->47.9%<!--/n-->. Supply grows <!--n:iv.issuance_rate_per_year-->2.46%<!--/n--> a year and the
buybacks offset <!--n:iv.buybacks_offset_points_per_year-->0.27<!--/n--> of those points.

**Discretionary.** Each link is set by people, not code (`scripts/control_map.py`, `scripts/control_history.py`):

- Fees users pay are set off-chain by the distribution channels; 1Click's terms let its operator change them
  "at any time on a prospective basis". The protocol fee on `intents.near` is <!--n:c.intents_fee_pips-->1 pip<!--/n-->,
  changed by a DAO (<!--n:c.intents_fee_change-->3 of 5<!--/n-->).
- The bought NEAR sits in a <!--n:c.buybacks_confirmations-->2 of 4<!--/n--> multisig and nothing is burned: with the front-end fund,
  <!--n:n1.wallets_held_near-->4,109,089<!--/n--> NEAR at the end block that signers can move.
- One account changed the NEAR AI credits rate <!--n:f6.change1.ratio-->×2.0<!--/n--> on
  <!--n:f6.change1.utc-->2026-09-29 14:21 UTC<!--/n-->, without a proposal of the owner's DAO. That one call moved the
  NEAR price below which the farm's credits pay more than staking with a validator from
  <!--n:iv.farm_breakeven_price_before_usd-->$2.45<!--/n--> to <!--n:iv.farm_breakeven_price_usd-->$4.90<!--/n-->.
- `treasury.near` paid out <!--n:ts.year_out_near-->30,171,200<!--/n--> NEAR in 2026, all in April and May, each payment
  a <!--n:c.treasury_confirmations-->2 of 4<!--/n--> multisig confirmation.
- <!--n:f8.fewest_voters_reaching_quorum-->6<!--/n--> voters were enough for the quorum of HSP-029, the issuance cut. The
  vote executes nothing on chain (`actions: null`) and stays in `vote.dao`'s timelock until
  <!--n:f8.timelock_end_utc-->2026-11-16 16:48 UTC<!--/n-->; it becomes a rule only when validators with
  <!--n:c.issuance_upgrade_stake_threshold-->4/5<!--/n--> of stake run a release that includes it.

Pulled in turn, the levers take coverage from <!--n:n1.coverage_buybacks-->10.8%<!--/n--> to
<!--n:n1.coverage_with_front_end-->16.5%<!--/n--> (the front-end fund), <!--n:n2.max_coverage-->47.9%<!--/n--> (every fee kept) and
<!--n:n2.hsp029_max_coverage-->74.8%<!--/n--> (HSP-029 at the end of its ramp); only the last is a rule
([lever model](README.md#investment-view), re-runnable in the
[dashboard](https://nikolaskahris-png.github.io/near-thesis-data/dashboard/#p3b)).

Issuance, by contrast, is code: at most <!--n:c.issuance_max_inflation_rate-->1/40<!--/n--> a year, changed only by a
nearcore release that at least <!--n:c.issuance_validators_to_pass_upgrade-->44<!--/n--> of
<!--n:c.issuance_validators-->381<!--/n--> validators would have to run.

## Evidence against

What weakens the claim, as measured by the same scripts:

1. **The discretion has not been used against holders.** From April to October the wallets kept
   <!--n:f2.wallets_kept_share_of_revenue.2026-04_2026-10-->96.9%<!--/n--> of DefiLlama's revenue
   (<!--n:f2.wallets_kept_near.2026-04_2026-10-->2,434,241<!--/n--> of <!--n:f2.revenue_near.2026-04_2026-10-->2,511,525<!--/n--> NEAR); the lowest month was April
   (<!--n:f2.wallets_kept_share_of_revenue.2026-04-->77%<!--/n-->), September and October
   <!--n:f2.wallets_kept_share_of_revenue.2026-09-->98%<!--/n--> and <!--n:f2.wallets_kept_share_of_revenue.2026-10-->100%<!--/n-->. The buybacks wallet's keys have not changed
   since <!--n:h.keys.buybacks.last_change-->2026-03-18<!--/n-->. "Discretionary" describes what can change, not a change that
   has happened.
2. **Capture is rising.** The take rate (revenue ÷ fees) rose from <!--n:f2.take_rate.2026-04-->8.1%<!--/n--> in April to
   <!--n:f2.take_rate.2026-10-->34.3%<!--/n--> in October, and monthly coverage from
   <!--n:f1.coverage_buybacks.2026-04-->5.3%<!--/n--> to <!--n:f1.coverage_buybacks.2026-10-->10.9%<!--/n-->. The discretion has so far
   moved in holders' favour, and "small" may not last.
3. **Part of "small" is the price.** From September to October revenue rose
   <!--n:f2.change.2026-09_2026-10.revenue_usd-->+15%<!--/n--> in dollars, but the mean NEAR price rose
   <!--n:f2.change.2026-09_2026-10.mean_price-->+49%<!--/n-->, so the NEAR it bought fell
   <!--n:f2.change.2026-09_2026-10.revenue_near-->-24%<!--/n-->. Revenue is in dollars and issuance in NEAR: at a mean price of
   <!--n:n2.mean_price_usd-->$4.88<!--/n--> coverage is low, while at <!--n:n2.equilibrium_price_usd-->$2.33<!--/n--> or less every fee
   would buy as many NEAR as are issued.
4. **Governance is moving toward rules.** HSP-029 passed with <!--n:f8.against_venear-->0<!--/n--> veNEAR against and
   <!--n:f8.turnout_of_snapshot-->62.3%<!--/n--> turnout. At its target rate the ceiling would be
   <!--n:n2.hsp029_max_coverage-->74.8%<!--/n-->, and full coverage would need fees to grow only
   <!--n:iv.hsp029_fees_multiple-->×1.3<!--/n--> if NEAR kept every fee. HSP-027 also passed, and its protocol version is
   scheduled for validator votes from 4 November.
5. **Condition (c) weighs little.** The NEAR AI farm holds <!--n:iv.farm_share_of_stake-->0.23%<!--/n--> of all stake, and stake
   cannot offset issuance, because stakers receive the new NEAR. It stays because it was pre-registered: it tests
   whether the AI narrative brings broad stake, and it is a case where one account sets the economics of a
   product.
6. **Control is spread, and multisigs and DAOs are a common way to run protocol funds.** The
   <!--n:c.dao_count-->5<!--/n--> DAOs that run the links have <!--n:c.dao_member_accounts-->22<!--/n--> member accounts, and the
   number that sit in more than one is <!--n:c.dao_members_in_two_or_more-->0<!--/n-->. That NEAR's links are run this way is not, by
   itself, a sign of misuse; the claim is only about what a holder can rely on today.

## What would change our mind

| Part of the claim | We are wrong if | Today | How far | Check |
|---|---|---|---|---|
| Small | the buybacks wallets alone keep 25% or more of issuance in three consecutive calendar months | highest month <!--n:f1.coverage_buybacks.2026-09-->15.3%<!--/n--> | today <!--n:n1.coverage_buybacks-->10.8%<!--/n--> of the way to full coverage; what they keep must grow <!--n:iv.wallets_multiple_buybacks-->×9.2<!--/n--> to cover issuance | `scripts/coverage.py`, `data/history.csv` |
| Discretionary: buybacks | bought NEAR moves by a published rule to an account no one can spend from, or the protocol fee on `intents.near` is raised with `fee_collector` set to the buybacks wallet or a locked account | <!--n:c.buybacks_confirmations-->2 of 4<!--/n--> multisig, nothing burned; fee <!--n:c.intents_fee_pips-->1 pip<!--/n--> | no rule yet | `scripts/control_map.py` |
| Discretionary: credits | the credits rate follows a formula in the contract, or changes only by a DAO proposal | changed <!--n:f6.rate_changes-->1<!--/n--> time by one account | no rule yet | `scripts/farm_rate.py` |
| Issuance is the only rule | HSP-029 is still not in a nearcore release adopted by validators on 1 November 2027 | in timelock until <!--n:f8.timelock_end_utc-->2026-11-16 16:48 UTC<!--/n--> | passed, not in force | `scripts/hsp029.py`, `scripts/upgrade_watch.py` |
| Stake spread | the largest account holds less than half of the NEAR AI farm | <!--n:n3.largest_share-->73.3%<!--/n--> | prediction 1 expects at least 70% on 16 November | `scripts/stakers.py` |

The verdict changes from "hold staked" to "hold for fee capture" only when (a) and (b) hold together. It gets
worse if the buybacks wallets pay NEAR out (coverage falls while DefiLlama's revenue does not), or monthly
coverage falls back to its April level. Five predictions are anchored on chain before they are judged:
[`PREREG.md`](PREREG.md) (16 November) and [`PREREG-2.md`](PREREG-2.md) (6 and 8 November, with stated
probabilities).

## Metrics we cannot compute

- **Confidential volume.** Part of NEAR Intents volume is confidential and reported separately by NearStats.
- **Volume from the chain.** DefiLlama's volume comes from a NEAR dataset on Dune and is not rebuilt here. It is
  not cross-checked against the NEAR Intents Explorer API, which needs a partner JWT. Solver spreads and gas are
  not in the fees.
- **Network activity.** Daily active accounts and transaction counts (the NEAR BigQuery dataset) are not
  computed: the claim is about where fees go, not about how many accounts are active.
- **Credits in dollars, and their use.** Units convert to credits by an off-chain NEAR AI Cloud setting, read
  only with a signed-in session; whether credits are used is not visible.
- **Who holds the largest farm position**, and where its NEAR came from.
- **What `treasury.near`'s payments were for.** Amounts, blocks and receivers are measured; the purpose is not on
  chain.
- **Peers** are compared from their docs, not from their chains ([peers](docs/DETAILS.md#peers)).

## Reproduce

Python standard library only, no network, no keys. One command rebuilds every number and every chart's
input from the committed raw files, checks every marked figure in this file, the README and the details, and
ends with `REBUILD: PASS`:

```
python scripts/rebuild.py
```

The charts, each with its query: [dashboard](https://nikolaskahris-png.github.io/near-thesis-data/dashboard/).
