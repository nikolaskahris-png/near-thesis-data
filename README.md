# NEAR's value capture is real, small and discretionary

[![verify](https://github.com/nikolaskahris-png/near-thesis-data/actions/workflows/verify.yml/badge.svg)](https://github.com/nikolaskahris-png/near-thesis-data/actions/workflows/verify.yml)

**Rating: Hold, not Buy. Five years, to 2031, reviewed every 12 months.**

- **Hold:** keep NEAR you already own, staked with a validator. Staking pays about <!--n:iv.staking_yield_gross-->5.0%<!--/n--> a year
  before commission while supply grows <!--n:iv.issuance_rate_per_year-->2.46%<!--/n-->, so a staked holder's share of all NEAR rises. That
  protects the share, not the dollar value.
- **Not a Buy:** what holders get from fees covers a small part of issuance, and nothing obliges anyone to keep it.
- **Upgrade to Buy** when, at a yearly check, all three hold. (a) **In dollars:** what the buybacks wallets keep a
  day has grown at least <!--n:lr.required_growth.buybacks.B.2031-->+56%<!--/n--> a year from this window's <!--n:iv.buybacks_kept_usd_per_day-->$46,692<!--/n-->, so a falling price alone
  cannot meet it. (a′) **In NEAR:** the same growth, so a rising price has not used it up. +56% a year is the pace that
  covers issuance on 1 January 2031 under HSP-029, the passed proposal that lowers issuance from 2.5% to 1.6% a year
  (<!--n:lr.required_growth.with_front_end.B.2031-->+41%<!--/n--> counting the front-end fund, which keeps near-intents.org's own fees; <!--n:lr.required_growth.buybacks.A.2031-->+75%<!--/n--> and
  <!--n:lr.required_growth.with_front_end.A.2031-->+58%<!--/n--> if HSP-029 is not in force). (b) Keeping it is a published rule. The hurdle depends on the
  base: from the April–October average it is <!--n:lr.required_growth.buybacks.B.2031.base.2026-04_2026-10-->+62%<!--/n-->; from single months,
  <!--n:lr.required_growth.buybacks.B.2031.base_min-->+44%<!--/n--> to <!--n:lr.required_growth.buybacks.B.2031.base_max-->+85%<!--/n-->.
- **Downgrade to Avoid** if the wallets pay NEAR out (coverage falls while DefiLlama's revenue does not), or what the
  buybacks wallets keep in dollars falls back to April's level (<!--n:f2.buybacks_kept_usd_per_day.2026-04-->$6,270<!--/n--> a day). A rising price alone cannot
  trigger it.

**Why coverage, for a staked holder.** Coverage is the buyback yield divided by the issuance rate: the wallets keep
<!--n:iv.buyback_yield_buybacks-->0.27%<!--/n--> of NEAR's value a year (<!--n:iv.buyback_yield_with_front_end-->0.41%<!--/n--> with the front-end fund), against <!--n:iv.issuance_rate_per_year-->2.46%<!--/n--> issued.
Staking moves issuance from unstaked holders to staked ones; buybacks are the only part of the return paid with
money from outside, so they are what all holders share. Net of buybacks, supply dilutes <!--n:iv.net_dilution_buybacks-->2.20%<!--/n--> a year. Coverage
falls when the price rises and revenue does not: each dollar buys back a smaller part of a dearer NEAR. In dollars,
April to October: fees <!--n:lr.history.2026-04_2026-10.fees_usd_multiple-->×1.9<!--/n-->, revenue <!--n:lr.history.2026-04_2026-10.revenue_usd_multiple-->×8.2<!--/n-->, volume <!--n:lr.history.2026-04_2026-10.volume_usd_multiple-->×2.0<!--/n-->, kept by the buybacks wallets
<!--n:lr.history.2026-04_2026-10.buybacks_kept_usd_multiple-->×7.5<!--/n-->; the NEAR price rose faster than fees, so fees counted in NEAR fell (<!--n:lr.history.2026-04_2026-10.fees_near_multiple-->×0.5<!--/n-->).

If NEAR kept every fee, fees counted in NEAR would need <!--n:lr.required_growth.all_fees.B.2031-->+9%<!--/n--> a year ([the model](#issuance-to-2031)).
Thresholds are the author's choice; every figure in them is measured.

Users pay <!--n:n2.fees_usd_per_day-->$206,049<!--/n--> a day in fees on NEAR Intents (DefiLlama). The
wallets that hold bought-back NEAR took in as much NEAR as <!--n:n1.coverage_buybacks-->10.8%<!--/n--> of what was issued in the
same days (<!--n:n1.coverage_with_front_end-->16.5%<!--/n--> with the front-end fund); if NEAR kept every fee, the ceiling would be
<!--n:n2.max_coverage-->47.9%<!--/n-->. At today's revenue, front-end fund included, the wallets would cover issuance only at
a NEAR price of <!--n:iv.revenue_equilibrium_price_usd-->$0.80<!--/n--> or less, against a mean of
<!--n:n2.mean_price_usd-->$4.88<!--/n--> in the same window. Revenue is in dollars and issuance in NEAR, so the higher the
price, the less it covers. At that mean price all NEAR is worth <!--n:iv.supply_value_usd-->$6.39B<!--/n-->:
<!--n:iv.value_to_fees-->85×<!--/n--> a year of fees and <!--n:iv.value_to_revenue-->248×<!--/n--> a year of revenue. A year of issuance is worth
<!--n:iv.issuance_usd_per_year-->$157.5M<!--/n-->; the wallets kept <!--n:iv.wallets_kept_usd_per_year-->$25.9M<!--/n--> a year.

**Who can change each link.** No link from the fee a user pays to the NEAR a holder keeps is fixed in code. The
fee level is set off-chain by the distribution channels. At the end block the wallets held
<!--n:n1.wallets_held_near-->4,109,089<!--/n--> NEAR that can be moved by their signers: the buybacks wallet with
<!--n:c.buybacks_confirmations-->2 of 4<!--/n--> signatures; in the front-end fund's DAO one Admin can change the rules. Nothing
is burned. So far the NEAR has stayed: from April to October the wallets kept
<!--n:f2.wallets_kept_share_of_revenue.2026-04_2026-10-->96.9%<!--/n--> of the revenue DefiLlama attributes to NEAR (lowest month,
April: <!--n:f2.wallets_kept_share_of_revenue.2026-04-->77%<!--/n-->). What is missing is a rule. [Path to rules](#path-to-rules)
lists, for each link, a mechanism NEAR already has.

**Check it.** `python scripts/rebuild.py` (Python 3.10+, standard library only, no network) ends with
`REBUILD: PASS`. Every figure here is copied from [`data/numbers.json`](data/numbers.json) with a hidden marker of
its key, and the check fails if one differs. Terms: [details](docs/DETAILS.md#terms).

> **Status: v2, 5 November 2026.** Window 2 October → 1 November 2026 (00:00 UTC), blocks 218,126,921 → 222,491,356.
> Every on-chain and DefiLlama figure is final for this window: DefiLlama's data were fetched again 24 hours later
> and no day had changed ([Method](docs/DETAILS.md#method)). The dollar value of NEAR AI credits is an off-chain
> reading, marked as such.

## Check it in two minutes

Python 3.10 or later (`python` below; `python3` on some systems), standard library only, no network, no keys:

```
python scripts/rebuild.py
```

The same, step by step:

```
python -m unittest discover -s tests              # every script's logic on fixed inputs
python scripts/build_numbers.py --verify           # every script's offline check, then numbers.json rebuilds the same
python scripts/build_numbers.py --check README.md  # every marked number in this file matches numbers.json
python scripts/check_prereg.py --file              # PREREG.md matches the anchored SHA-256 (saved copy)
```

The second command ends with `VERIFY: PASS (PUBLIC_FULL)`: every number recomputed with no network and without
the private originals ([Method](docs/DETAILS.md#method)). For the lists that name accounts (farm stakers, HSP-029
voters, validators) git holds redacted copies: offline, the check proves they are consistent and that their totals
equal the totals in the raw contract responses, not that each entry is right. The `verify` badge runs these on every push. Five live
read-only calls, and a re-measurement of numbers 1 and 3 from the chain: [Verify live](docs/DETAILS.md#verify-live).

## The numbers: two of value, one signal

| # | What it measures | Value | On chain? | Reproduce (no network) |
|---|---|---|---|---|
| 1 | Coverage: NEAR kept by the buybacks wallets ÷ NEAR issued, same days | **<!--n:n1.coverage_buybacks-->10.8%<!--/n-->** (<!--n:n1.buybacks_near_per_day-->9,570<!--/n--> of <!--n:n1.new_near_per_day-->88,392<!--/n--> NEAR a day) · with the front-end fund **<!--n:n1.coverage_with_front_end-->16.5%<!--/n-->** | yes: balances and block headers | `python scripts/daily.py --verify` |
| 2 | The ceiling: all fees recorded by DefiLlama ÷ issuance | **<!--n:n2.max_coverage-->47.9%<!--/n-->** · equilibrium price **<!--n:n2.equilibrium_price_usd-->$2.33<!--/n-->** | no: fees from a Dune dataset, prices from DefiLlama | `python scripts/fees.py --verify data/fees_2026-10-02_2026-11-01.json` |
| — | At stake: NEAR the wallets hold, movable by their signers | **<!--n:n1.wallets_held_near-->4,109,089<!--/n-->** (buybacks <!--n:n1.buybacks_held_near-->2,145,248<!--/n-->, front-end fund <!--n:n1.front_end_held_near-->1,963,842<!--/n-->) | yes | `python scripts/daily.py --verify` |
| 3 | Signal: how widely the NEAR AI farm is spread | **<!--n:n3.stakers_active-->112<!--/n-->** active accounts · largest **<!--n:n3.largest_share-->73.3%<!--/n-->** · top 10 <!--n:n3.top10_share-->96.4%<!--/n--> · median outside the top 10 <!--n:n3.outside_top10_median_near-->60<!--/n--> NEAR | yes | `python scripts/stakers.py --verify` |

- **1.** Balance change of `buybacks.multisignature.near` + `1csfundsadmin.sputnik-dao.near` ÷ change of
  `total_supply` between the two block headers. The front-end fund, `fefundsadmin.sputnik-dao.near`
  (<!--n:n1.front_end_near_per_day-->4,985<!--/n--> NEAR a day), holds near-intents.org's own fees, not bought-back NEAR, but DefiLlama
  counts it as buybacks: it is <!--n:f9.front_end_share_of_wallets-->34.2%<!--/n--> of what the three wallets kept, which is why number
  1 is given both ways ([fees](https://docs.near-intents.org/resources/fees)).
- **Outflow check, not a fee check.** DefiLlama's revenue ÷ issuance gives <!--n:n2.defillama_revenue_coverage-->16.5%<!--/n-->,
  as the wallets do. DefiLlama counts inflows to the same wallets and we measure their balances, so the match
  shows that almost nothing flowed out. It does not check the fees themselves.
- **2.** Each day's fees converted at that day's NEAR price, ÷ new NEAR per day; the equilibrium price is the
  NEAR price at which a day's fees buy as many NEAR as are issued. At HSP-029's target rate (issuance ×16/25) the
  ceiling would be <!--n:n2.hsp029_max_coverage-->74.8%<!--/n-->. The NEAR Intents exploit of 1 October, about $3.8M through the Omni
  deposit and withdrawal system ([report](https://crypto-economy.com/near-intents-halts-after-3-8m-exploit-vows-full-compensation-amid-hack-wave/)),
  came a day before the window; the `intents.near` DAO paused features and installed new code from 1 to 7 October
  (`data/control_history.json`). Without 2–7 October the ceiling is <!--n:n2.max_coverage_without_2026-10-02_to_07-->47.9%<!--/n-->.
- **3.** A signal, not a lever: the farm is <!--n:iv.farm_share_of_stake-->0.23%<!--/n--> of all stake (finding 5). Every account
  that ever staked through `stake.dao`, read at the block: <!--n:n3.stakers_ever-->188<!--/n--> entered, <!--n:n3.stakers_left-->76<!--/n--> have left,
  and the active positions add up exactly to the farm's total (<!--n:n3.farm_total_near-->1,364,348<!--/n--> NEAR).

Full definitions: [details](docs/DETAILS.md#the-three-numbers).

## Investment view

*Dated 5 November 2026. Horizon five years, to 1 January 2031, checked every 12 months. Thresholds are the author's
choice; every figure in them is measured.*

At the end block <!--n:c.issuance_staked_share-->45.2%<!--/n--> of supply (<!--n:c.issuance_total_stake_near-->592,027,869<!--/n--> NEAR) is
staked with validators. What each holder gets:

| Holder | NEAR received | What changes |
|---|---|---|
| Not staked | none | owns a smaller share as supply grows <!--n:iv.issuance_rate_per_year-->2.46%<!--/n--> a year; the buybacks offset <!--n:iv.buybacks_offset_points_per_year-->0.27<!--/n--> points of it in the supply outside their wallets |
| Staked with a validator | about <!--n:iv.staking_yield_gross-->5.0%<!--/n--> a year, before the validator's commission | keeps pace with issuance |
| Staked in the NEAR AI farm | none: `nearai.pool.near` keeps <!--n:c.nearai_pool_reward_fee-->100%<!--/n--> of rewards | credits instead (finding 5) |

| Condition | Today | Met when | Measured by |
|---|---|---|---|
| **(a)** Coverage | <!--n:n1.coverage_buybacks-->10.8%<!--/n--> (<!--n:n1.coverage_with_front_end-->16.5%<!--/n--> with the front-end fund) | the wallets keep as much NEAR as is issued: what they keep grows <!--n:iv.wallets_multiple_buybacks-->×9.2<!--/n--> (<!--n:iv.wallets_multiple_with_front_end-->×6.1<!--/n-->), or, with every fee kept, fees <!--n:iv.fees_multiple-->×2.1<!--/n--> | `data/history.csv`, daily |
| **(b)** A rule, not a choice | a <!--n:c.buybacks_confirmations-->2 of 4<!--/n--> multisig, nothing burned | bought NEAR moves by a published rule to an account no one can spend from | `scripts/control_map.py` |
| (c) Signal: stake spread | largest account <!--n:n3.largest_share-->73.3%<!--/n--> of the farm | the largest holds less than half | `scripts/stakers.py` |

(a) and (b) decide value; (c) does not, because stake cannot offset issuance: stakers are the ones who receive
the new NEAR. Buybacks pay for NEAR with money from outside, the fees users pay, but they offset issuance only in
the supply outside their wallets, and only while the NEAR stays there: total supply grows either way.

**The lever model.** Coverage if each lever were pulled in turn; only the last step is a rule. The
[dashboard](https://nikolaskahris-png.github.io/near-thesis-data/dashboard/#p3b) re-runs it with your own assumptions.

| Step | Coverage | Who moves the lever |
|---|---|---|
| Today: the buybacks wallets keep <!--n:iv.wallets_share_of_fees_buybacks-->22.6%<!--/n--> of all fees | <!--n:n1.coverage_buybacks-->10.8%<!--/n--> | a <!--n:c.buybacks_confirmations-->2 of 4<!--/n--> multisig; a choice |
| + the front-end fund (the three wallets keep <!--n:iv.wallets_share_of_fees_with_front_end-->34.4%<!--/n--> of all fees in NEAR; not the take rate, which is revenue ÷ fees in dollars) | <!--n:n1.coverage_with_front_end-->16.5%<!--/n--> | its DAO, transfers <!--n:c.front_end_transfer-->2 of 5<!--/n-->; a choice |
| + every fee kept by NEAR | <!--n:n2.max_coverage-->47.9%<!--/n--> | the distribution channels off-chain, or the protocol fee by DAO (<!--n:c.intents_fee_change-->3 of 5<!--/n-->); a choice |
| + HSP-029 at the end of its 24-month ramp | <!--n:n2.hsp029_max_coverage-->74.8%<!--/n--> | validators with <!--n:c.issuance_upgrade_stake_threshold-->4/5<!--/n--> of stake; a rule once they run it |
| Full coverage | 100% | fees grow a further <!--n:iv.hsp029_fees_multiple-->×1.3<!--/n-->, or NEAR at or below <!--n:n2.hsp029_equilibrium_price_usd-->$3.64<!--/n--> |

### Issuance to 2031

`scripts/longrun.py` steps total supply one epoch at a time under today's rule (A: at most 1/40 a year) and under
HSP-029 (B: 2.5% → 1.6% over 24 months, from <!--n:lr.activation_utc-->2027-02-14 16:48 UTC<!--/n-->, 90 days after its timelock ends),
holding the window's ratio of actual to maximum issuance. It forecasts no price, volume or fee: it gives the yearly
growth that the NEAR kept a day must reach to equal issuance on 1 January of each year.

| Covered on 1 January | Issuance a day, A → B | What the wallets keep must grow, A / B | All fees in NEAR must grow, A / B |
|---|---|---|---|
| 2028 | <!--n:lr.issuance_per_day.A.2028-->90,968<!--/n--> → <!--n:lr.issuance_per_day.B.2028-->76,482<!--/n--> | <!--n:lr.required_growth.with_front_end.A.2028-->+381%<!--/n--> / <!--n:lr.required_growth.with_front_end.B.2028-->+315%<!--/n--> a year | <!--n:lr.required_growth.all_fees.A.2028-->+93%<!--/n--> / <!--n:lr.required_growth.all_fees.B.2028-->+66%<!--/n--> |
| 2029 | <!--n:lr.issuance_per_day.A.2029-->93,242<!--/n--> → <!--n:lr.issuance_per_day.B.2029-->61,230<!--/n--> | <!--n:lr.required_growth.with_front_end.A.2029-->+135%<!--/n--> / <!--n:lr.required_growth.with_front_end.B.2029-->+94%<!--/n--> | <!--n:lr.required_growth.all_fees.A.2029-->+44%<!--/n--> / <!--n:lr.required_growth.all_fees.B.2029-->+19%<!--/n--> |
| 2031 | <!--n:lr.issuance_per_day.A.2031-->97,948<!--/n--> → <!--n:lr.issuance_per_day.B.2031-->61,108<!--/n--> | <!--n:lr.required_growth.with_front_end.A.2031-->+58%<!--/n--> / <!--n:lr.required_growth.with_front_end.B.2031-->+41%<!--/n--> | <!--n:lr.required_growth.all_fees.A.2031-->+22%<!--/n--> / <!--n:lr.required_growth.all_fees.B.2031-->+9%<!--/n--> |

Keeping every fee instead of today's share can add <!--n:lr.take_rate_ceiling_multiple-->×2.9<!--/n-->, once; the rest must come from fees
that grow faster than the NEAR price. From April to October what the wallets kept rose
<!--n:lr.history.2026-04_2026-10.kept_multiple-->×2.9<!--/n-->, but fees counted in NEAR fell (<!--n:lr.history.2026-04_2026-10.fees_near_multiple-->×0.5<!--/n-->): the rise came from the share
kept (take rate <!--n:lr.history.2026-04_2026-10.take_rate_multiple-->×4.2<!--/n-->), the lever with a ceiling. If HSP-029 starts six months late, covering
2029 needs <!--n:lr.required_growth.all_fees.B_late.2029-->+26%<!--/n--> a year instead of <!--n:lr.required_growth.all_fees.B.2029-->+19%<!--/n-->. The model's HSP-029 cut over six years,
<!--n:lr.not_issued_B.6y-->66.35M<!--/n--> NEAR, is within <!--n:lr.not_issued_B_vs_proposal.6y-->+0.4%<!--/n--> of the proposal's own figure.

**The base matters.** The table starts from the window's level, October. Starting instead from each month since April,
the buybacks wallets' 2031 hurdle under HSP-029 runs from <!--n:lr.required_growth.buybacks.B.2031.base_min-->+44%<!--/n--> to <!--n:lr.required_growth.buybacks.B.2031.base_max-->+85%<!--/n--> a year; from the
April–October average, <!--n:lr.required_growth.buybacks.B.2031.base.2026-04_2026-10-->+62%<!--/n--> (with the front-end fund <!--n:lr.required_growth.with_front_end.B.2031.base.2026-04_2026-10-->+50%<!--/n-->). October sits
inside that range, and the April–October average asks for more than October does. Every year, month and column: [details](docs/DETAILS.md#issuance-to-2031).

**Valuation, same window.** All NEAR in `total_supply` at the window's mean price
(<!--n:n2.mean_price_usd-->$4.88<!--/n-->) is worth <!--n:iv.supply_value_usd-->$6.39B<!--/n-->; circulating supply would need an off-chain source.

| A year of | Dollars | Value ÷ that |
|---|---|---|
| Fees users pay (DefiLlama) | <!--n:iv.fees_usd_per_year-->$75.3M<!--/n--> | <!--n:iv.value_to_fees-->85×<!--/n--> |
| Revenue DefiLlama counts as NEAR's | <!--n:iv.revenue_usd_per_year-->$25.8M<!--/n--> | <!--n:iv.value_to_revenue-->248×<!--/n--> |
| NEAR kept by the three wallets, on chain | <!--n:iv.wallets_kept_usd_per_year-->$25.9M<!--/n--> | <!--n:iv.value_to_wallets_kept-->247×<!--/n--> |
| Issuance, for comparison | <!--n:iv.issuance_usd_per_year-->$157.5M<!--/n--> | — |

Peers are not compared here, because their fees are not measured the same way.

**What would make it worse:** the wallets pay NEAR out (number 1 falls while DefiLlama revenue does not), or
monthly coverage falls back to its April level (<!--n:f1.coverage_buybacks.2026-04-->5.3%<!--/n-->). **When to check:** 6, 8 and 16
November 2026 (the predictions), every month from `data/history.csv`, and each November to 2031 against the table above.

## Path to rules

Each link that decides value can become a rule with a mechanism NEAR already has. Governance has started:
HSP-027 (remove the developer gas rebate) passed on 3 July 2026 (House of Stake; the vote is not saved here) and is protocol version 87, open to validator votes
from 4 November; [HSP-029](https://gov.houseofstake.org/proposals/29) (issuance 2.5% → 1.6% a year over 24 months)
passed on 2 November and is in timelock until <!--n:f8.timelock_end_utc-->2026-11-16 16:48 UTC<!--/n-->. A vote changes nothing on
chain by itself: validators with <!--n:c.issuance_upgrade_stake_threshold-->4/5<!--/n--> of stake must run a release that includes it,
and `scripts/upgrade_watch.py` measures that every day. HSP-027's effect is small: at most
<!--n:b.hsp027_extra_burn_max_near_per_day-->417<!--/n--> more NEAR burned a day, against <!--n:n1.buybacks_near_per_day-->9,570<!--/n--> kept by the buybacks wallets.

| Link | What would make it a rule | Trade-off |
|---|---|---|
| Fees users pay | Part of the fee charged as the protocol fee on `intents.near` (up to 100% is allowed; today <!--n:c.intents_fee_pips-->1 pip<!--/n-->), with `fee_collector` set to the buybacks wallet or a locked account | The fee can still change by DAO vote (<!--n:c.intents_fee_change-->3 of 5<!--/n-->), but visibly and with a history |
| Buybacks wallet | Move bought NEAR on a published schedule to an account with no keys and no code, or to a contract with no withdraw method | Native NEAR cannot be burned by a call: locking lowers circulating supply, not `total_supply` |
| Issuance | Already a protocol rule; HSP-029 would lower it if validators adopt it | <!--n:c.issuance_validators_to_block_upgrade-->5<!--/n--> validators are enough to block |
| Protocol treasury | A public spending rule voted as an HSP, or a lower share through the protocol | Today <!--n:c.treasury_confirmations-->2 of 4<!--/n--> keys approve each payment; <!--n:ts.year_out_near-->30,171,200<!--/n--> NEAR left in 2026 (finding 4) |
| Front-end and 1Click funds, pool rewards | Their DAOs' spending and fee choices written as public rules (for example, an HSP), not decided proposal by proposal | Less room to adjust |
| NEAR AI credits rate | A formula in the contract, or changes only by DAO proposal with a delay | The rate follows neither today: it changed once, by hand |
| `intents.near` code | A published delay between a release and its installation | A delay would also slow urgent fixes; pausing would stay immediate |

The same map for Hyperliquid, Aave and Jupiter, from their docs: [peers](docs/DETAILS.md#peers).

## The control map: who can change each link

Who can change each link, and how often they have, read at block 222,491,356 (`scripts/control_map.py`,
`scripts/control_history.py`). Multisigs and DAOs are a common way to run protocol funds; the point is what a
holder relies on today. The <!--n:c.dao_count-->5<!--/n--> DAOs have <!--n:c.dao_member_accounts-->22<!--/n--> member accounts;
<!--n:c.dao_members_in_two_or_more-->0<!--/n--> sit in more than one. The remaining links (1Click fund, House of Stake, NEAR AI pool):
[details](docs/DETAILS.md#the-control-map-other-links).

```mermaid
flowchart TD
  U["A user swaps on NEAR Intents"] --> F["Fees users pay: <!--n:n2.fees_bps-->16.0<!--/n--> bps of volume<br/>set off-chain by the distribution channels"]
  U --> P["Protocol fee on intents.near: <!--n:c.intents_fee_pips-->1 pip<!--/n--><br/>DAO <!--n:c.intents_fee_change-->3 of 5<!--/n--> · used <!--n:h.fee.approved_actions-->6<!--/n--> times"]
  F --> B["Buybacks wallets<br/>multisig <!--n:c.buybacks_confirmations-->2 of 4<!--/n--> · nothing burned"]
  F --> E["Front-end fund<br/>transfers <!--n:c.front_end_transfer-->2 of 5<!--/n--> · rules <!--n:c.front_end_rules-->1 of 5<!--/n-->"]
  B --> H["NEAR holders<br/>coverage <!--n:n1.coverage_buybacks-->10.8%<!--/n--> of issuance<br/>(<!--n:n1.coverage_with_front_end-->16.5%<!--/n--> if the front-end fund is counted)"]
  I["Issuance: at most <!--n:c.issuance_max_inflation_rate-->1/40<!--/n--> a year<br/>changed by <!--n:c.issuance_upgrade_stake_threshold-->4/5<!--/n--> of stake: at least <!--n:c.issuance_validators_to_pass_upgrade-->44<!--/n--> of <!--n:c.issuance_validators-->381<!--/n--> validators"] --> S["Stakers"]
  I --> T["treasury.near: balance grew by <!--n:c.treasury_share_of_new_supply-->10.1%<!--/n--> of new supply<br/>multisig <!--n:c.treasury_confirmations-->2 of 4<!--/n-->"]
  S --> N["nearai.pool.near keeps <!--n:c.nearai_pool_reward_fee-->100%<!--/n--> of rewards<br/>owner DAO <!--n:c.nearai_pool_owner_transfer-->2 of 3<!--/n-->"]
  N -.-> C["NEAR AI credits rate<br/>set by 1 account · changed <!--n:f6.rate_changes-->1<!--/n--> time, <!--n:f6.change1.ratio-->×2.0<!--/n-->"]
  P --- K["intents.near code: v<!--n:c.intents_code_version-->0.4.5<!--/n--><br/>release by DAO <!--n:c.intents_code_add_release-->3 of 5<!--/n--> · installed by <!--n:c.intents_code_updater_accounts-->1<!--/n--> Updater account<br/><!--n:c.intents_code_changes-->20<!--/n--> code changes"]
```

| Link | Today | Who can change it | Signatures | Used |
|---|---|---|---|---|
| Fees users pay | <!--n:n2.fees_bps-->16.0<!--/n--> bps of volume (DefiLlama) | The distribution channels, off-chain. The 1Click terms let its operator change fees "at any time on a prospective basis" ([terms](https://docs.near-intents.org/near-intents/integration/distribution-channels/1click-terms-of-service)) | not on chain | not visible on chain |
| Protocol fee (`intents.near` `fee`) | <!--n:c.intents_fee_pips-->1 pip<!--/n--> = <!--n:c.intents_fee_percent-->0.0001%<!--/n--> | `intents.sputnik-dao.near` (role DAO); FeesManager role: <!--n:c.intents_fees_manager_accounts-->0<!--/n--> accounts | <!--n:c.intents_fee_change-->3 of 5<!--/n--> | `set_fee` <!--n:h.set_fee-->3<!--/n-->, `set_fee_collector` <!--n:h.set_fee_collector-->3<!--/n--> (<!--n:h.fee.first-->2024-11-07<!--/n--> → <!--n:h.fee.last-->2025-10-02<!--/n-->) |
| Buybacks wallet (`buybacks.multisignature.near`) | holds the bought NEAR; nothing is burned | its multisig members (<!--n:c.buybacks_full_access_keys-->0<!--/n--> full-access keys) | <!--n:c.buybacks_confirmations-->2 of 4<!--/n--> | keys unchanged since <!--n:h.keys.buybacks.last_change-->2026-03-18<!--/n--> |
| Front-end fund (`fefundsadmin.sputnik-dao.near`) | <!--n:f9.front_end_share_of_wallets-->34.2%<!--/n--> of what the three wallets kept | DAO: transfers / its own rules, upgrades and members. One Admin (a DAO role) can change the rules alone, so one key can also move the funds, in two steps | <!--n:c.front_end_transfer-->2 of 5<!--/n--> / <!--n:c.front_end_rules-->1 of 5<!--/n--> | — |
| Issuance (`max_inflation_rate`) | <!--n:c.issuance_max_inflation_rate-->1/40<!--/n--> a year | a new nearcore release, run by validators with <!--n:c.issuance_upgrade_stake_threshold-->4/5<!--/n--> of stake | at least <!--n:c.issuance_validators_to_pass_upgrade-->44<!--/n--> of <!--n:c.issuance_validators-->381<!--/n--> validators (the largest); the <!--n:c.issuance_validators_to_block_upgrade-->5<!--/n--> largest can block; largest holds <!--n:c.issuance_largest_validator_share-->5.6%<!--/n--> | see [Path to rules](#path-to-rules) |
| Protocol treasury (`treasury.near`) | its balance grew by <!--n:c.treasury_share_of_new_supply-->10.1%<!--/n--> of new supply (<!--n:c.treasury_near_received-->268,973<!--/n--> NEAR in the window) | its multisig members | <!--n:c.treasury_confirmations-->2 of 4<!--/n--> | keys last changed <!--n:h.keys.treasury.last_change-->2025-09-05<!--/n-->; paid out <!--n:ts.year_out_near-->30,171,200<!--/n--> NEAR in 2026 (finding 4) |

The same DAOs can upgrade, pause and move users' funds on `intents.near`: [admin scope](docs/DETAILS.md#contract-level-admin-scope).

## Findings

**1. Coverage has been below a quarter of issuance in every calendar month since April.** From the wallets alone:
balances and block headers, independent of DefiLlama (`scripts/coverage.py`). October here is the calendar month,
so it differs slightly from the window's <!--n:n1.coverage_buybacks-->10.8%<!--/n-->.

| | Apr | May | Jun | Jul | Aug | Sep | Oct |
|---|---|---|---|---|---|---|---|
| Buybacks wallets | <!--n:f1.coverage_buybacks.2026-04-->5.3%<!--/n--> | <!--n:f1.coverage_buybacks.2026-05-->8.4%<!--/n--> | <!--n:f1.coverage_buybacks.2026-06-->8.5%<!--/n--> | <!--n:f1.coverage_buybacks.2026-07-->6.2%<!--/n--> | <!--n:f1.coverage_buybacks.2026-08-->10.2%<!--/n--> | <!--n:f1.coverage_buybacks.2026-09-->15.3%<!--/n--> | <!--n:f1.coverage_buybacks.2026-10-->10.9%<!--/n--> |
| With the front-end fund | <!--n:f1.coverage_with_front_end.2026-04-->5.7%<!--/n--> | <!--n:f1.coverage_with_front_end.2026-05-->11.9%<!--/n--> | <!--n:f1.coverage_with_front_end.2026-06-->11.2%<!--/n--> | <!--n:f1.coverage_with_front_end.2026-07-->9.1%<!--/n--> | <!--n:f1.coverage_with_front_end.2026-08-->14.8%<!--/n--> | <!--n:f1.coverage_with_front_end.2026-09-->21.3%<!--/n--> | <!--n:f1.coverage_with_front_end.2026-10-->16.5%<!--/n--> |

**2. October's revenue rose in dollars but bought fewer NEAR, because the price rose faster.** September →
October (calendar months): revenue <!--n:f2.change.2026-09_2026-10.revenue_usd-->+15%<!--/n-->, mean NEAR price
<!--n:f2.change.2026-09_2026-10.mean_price-->+49%<!--/n--> (<!--n:f2.mean_price_usd.2026-09-->$3.28<!--/n--> → <!--n:f2.mean_price_usd.2026-10-->$4.89<!--/n-->),
NEAR bought <!--n:f2.change.2026-09_2026-10.revenue_near-->-24%<!--/n-->. The wallets kept <!--n:f2.wallets_kept_share_of_revenue.2026-09-->98%<!--/n-->
and <!--n:f2.wallets_kept_share_of_revenue.2026-10-->100%<!--/n--> of that revenue, so the fall came from the price, not from an outflow.
April to October they kept <!--n:f2.wallets_kept_near.2026-04_2026-10-->2,434,241<!--/n--> of <!--n:f2.revenue_near.2026-04_2026-10-->2,511,525<!--/n--> NEAR;
the <!--n:f2.revenue_not_kept_near.2026-04_2026-10-->77,285<!--/n--> NEAR difference is not split between payments out, month-edge
timing and attribution. The take rate (revenue ÷ fees) rose from <!--n:f2.take_rate.2026-04-->8.1%<!--/n--> to
<!--n:f2.take_rate.2026-10-->34.3%<!--/n--> while fees stayed at <!--n:f2.fees_bps.2026-08-->13.8<!--/n-->–<!--n:f2.fees_bps.2026-10-->16.0<!--/n--> bps of
volume from August.

**3. HSP-029 passed with <!--n:f8.against_votes-->1<!--/n--> vote against (<!--n:f8.against_venear-->0<!--/n--> veNEAR, rounded), and
<!--n:f8.fewest_voters_reaching_quorum-->6<!--/n--> voters held enough veNEAR to reach its quorum.** veNEAR is the voting weight of NEAR
locked in House of Stake. At the vote's last block, 222,745,764 (`scripts/hsp029_voters.py`):
<!--n:f8.voters-->36<!--/n--> voters, <!--n:f8.for_voters-->32<!--/n--> for, <!--n:f8.turnout_of_snapshot-->62.3%<!--/n--> of the snapshot's veNEAR, quorum
<!--n:f8.quorum_required_venear-->1,846,161<!--/n-->; the 8 largest cast <!--n:f8.top8_share_of_votes_cast-->80.6%<!--/n--> of the votes. It executes nothing on chain:
issuance falls only when validators run a release that includes it ([Path to rules](#path-to-rules)).

**4. `treasury.near` receives 10% of the maximum issuance; in 2026 it paid out
<!--n:ts.year_out_near-->30,171,200<!--/n--> NEAR, all in April and May.** `scripts/treasury_spend.py` reproduces its reward to the yocto at
<!--n:ts.rule_exact-->101<!--/n--> of the <!--n:ts.rule_epochs-->101<!--/n--> epoch starts in the window (<!--n:ts.share_of_minted-->10.03%<!--/n--> of what is
minted, as validators below full uptime receive less). In 2026 it received <!--n:ts.year_treasury_in_near-->2,700,599<!--/n--> NEAR;
<!--n:ts.out_near.2026-04-->9,800,000<!--/n--> left in April and <!--n:ts.out_near.2026-05-->20,371,200<!--/n--> in May, none in the window of number 1.
Its balance went from <!--n:ts.balance_start_near-->28,996,906<!--/n--> to <!--n:ts.balance_end_near-->1,526,304<!--/n-->. Each payment is a `confirm` on the multisig (<!--n:c.treasury_confirmations-->2 of 4<!--/n--> keys); receivers, blocks and amounts
(`scripts/treasury_exits.py`): [details](docs/DETAILS.md#treasurynear-payments). The purpose of each payment is not on
chain and is not characterized here. These payments move existing NEAR, so they do not change `total_supply`
or the model above; they change what circulates, which no figure here measures.

**5. The NEAR AI farm is concentrated, and its credits rate is a setting.** The farm stakes NEAR through
`stake.dao` into `nearai.pool.near` and pays reward units, which NEAR AI Cloud turns into credits at
<!--n:f6.usd_per_reward_unit-->$1.00<!--/n--> each (off-chain setting). The same account has been the largest since
<!--n:f5.largest_same_account_since-->2026-08-15<!--/n-->. One account changed the rate <!--n:f6.change1.ratio-->×2.0<!--/n--> on
<!--n:f6.change1.utc-->2026-09-29 14:21 UTC<!--/n-->, the only `edit_price` call in the contract's history, without a proposal of the
owner's DAO. At the staking yield of <!--n:iv.staking_yield_gross-->5.0%<!--/n-->, credits pay more than a validator while NEAR is below
<!--n:iv.farm_breakeven_price_usd-->$4.84<!--/n--> (before the change: <!--n:iv.farm_breakeven_price_before_usd-->$2.42<!--/n-->). History, the pool
owner's flows and the Agents subscriptions: [details](docs/DETAILS.md#the-near-ai-farm).

## Pre-registration

Five predictions, anchored on NEAR mainnet before they are judged: each file's SHA-256 is stored in SocialDB
(`social.near`, key `samerice7976.near/thesis/prereg/<n>`). Results will be published whatever they are.

**[`PREREG-2.md`](PREREG-2.md): when HSP-027 takes effect**, with a probability for each, so the result is scored.
Transaction [`EZ6mexrY…`](https://nearblocks.io/txns/EZ6mexrYfaMFivjLqccSjxGkTgWDEqUBUeiZDoAx9art), block 222,916,018
(2026-11-03 19:48:55 UTC), four hours before validators' voting for version 87 opened.

Anchored SHA-256: `545cf67530b37c902b2674cb4014818d3f79eb1718fe6bbab896a361e48ce0d3`

| # | Prediction | Holds if | Probability stated | Judged at |
|---|---|---|---|---|
| 4 | Protocol version 87 (HSP-027) is in effect on NEAR mainnet | `protocol_version` ≥ 87 | 0.85 | first block at or after 2026-11-06 00:00 UTC |
| 5 | Protocol version 88 is in effect on NEAR mainnet | `protocol_version` ≥ 88 | 0.75 | first block at or after 2026-11-08 00:00 UTC |

Both are judged before the hackathon's deadline; the results and their Brier scores will be added here.

**[`PREREG.md`](PREREG.md): three predictions judged on 16 November 2026.** Transaction
[`8fZ8VTUy…`](https://nearblocks.io/txns/8fZ8VTUyM1UjnybqPd1QCQi4c3y75dDRGR5TjkNGgnPL), block 222,606,824
(2026-11-01 18:30:38 UTC); the file has not changed since. Prediction 2's window had opened at 00:00 UTC that day;
`PREREG.md` states what had been read by then.

Anchored SHA-256: `d3f48ed9172b1785b4dcf290b84e9a06c870b8b9b5481c6d40e51a4605b1d494`

| # | Prediction | Holds if | Baseline |
|---|---|---|---|
| 1 | The largest account keeps at least 70% of the NEAR AI farm on 16 Nov | share ≥ 0.70 | <!--n:n3.largest_share-->73.3%<!--/n--> |
| 2 | Net inflows to the buybacks wallet, 1–15 Nov, stay below a quarter of new supply | ratio < 0.25 | <!--n:n1.coverage_buybacks-->10.8%<!--/n--> (2 Oct–1 Nov; `1csfundsadmin` did not change in the window, so this equals the buybacks wallet alone) |
| 3 | Fewer than 150 accounts are active in the NEAR AI farm on 16 Nov | count < 150 | <!--n:n3.stakers_active-->112<!--/n--> |

These three are easy to check, not hard to pass: `PREREG.md` says how demanding each is. Rules, timing and void
conditions are in the files; `python scripts/check_prereg.py` checks the anchors live, `--verify` offline.

## What we can't measure

- **The fees themselves.** DefiLlama's fees and volume come from a NEAR dataset on Dune and cannot be rebuilt from
  the chain here; part of NEAR Intents volume is confidential and reported separately by NearStats. Solver spreads
  and gas are not in the fees. Only the revenue side is checked on chain, through the wallets' balances.
- **Credits in dollars.** The conversion from reward units to credits is an off-chain NEAR AI Cloud setting, read
  only with a signed-in session, and can change with no trace on chain. Whether credits are used is not visible.
- **The largest farm position.** Who holds it, and where its NEAR came from, is not visible to us on chain.
- **What `treasury.near`'s payments were for.** Amounts, blocks and receivers are measured (finding 4); the
  purpose is not on chain.
- **Whether HSP-027 is in force** before validators adopt version 87; until then it is "passed", not "in force".
- **Peers** are compared from their docs and press, not from their chains.

## Timeline and disclosure

- Research into data sources: 22–31 October 2026, in private notes that are not part of this repository.
- Code and data: from the first commit, 2026-10-31 13:51:52 UTC; there is no earlier code. The
  [rules](https://nearhackathon.com/HACKATHON.md) (FAQ Q-001) count work from the hackathon's announcement on
  19 October: "Earlier commits are baseline". Six commits come before 1 November.
- Sources: NEAR archival RPC, the NearBlocks API, DefiLlama, and one off-chain read of a NEAR AI Cloud setting.
  Raw responses are saved byte for byte; those that list people's accounts are kept private, with their SHA-256.
- Libraries: none beyond the Python standard library. `docs/sign.html` loads NEAR Wallet Selector 10.1.4 from esm.sh.
- This is the author's only submission to NEAR HACKATHON.

License: [MIT](LICENSE).
