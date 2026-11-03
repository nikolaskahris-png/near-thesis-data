# near-thesis-data

[![verify](https://github.com/nikolaskahris-png/near-thesis-data/actions/workflows/verify.yml/badge.svg)](https://github.com/nikolaskahris-png/near-thesis-data/actions/workflows/verify.yml)

**NEAR's value capture is real, small and discretionary.** Users pay real fees on NEAR Intents, but only a small
part reaches NEAR holders, and every link from the fee a user pays to the NEAR a holder keeps is set by a
few signers or by a company off-chain, not by code. Issuance, on the other side of the ledger, is a protocol rule.

**In short**

- **Control.** Each link from the fee a user pays to the NEAR a holder keeps is set by a multisig, a DAO or a
  company off-chain, not by code: the buybacks wallet needs <!--n:c.buybacks_confirmations-->2 of 4<!--/n--> signatures and burns nothing, one account
  changed the NEAR AI credits rate <!--n:f6.change1.ratio-->×2.0<!--/n-->, and <!--n:f8.fewest_voters_reaching_quorum-->6<!--/n--> voters were enough for the quorum of HSP-029, the
  issuance cut. A passed vote becomes a rule only when validators run it, and that step is measured live
  ([control map](#the-control-map-who-can-change-each-link), [Path to rules](#path-to-rules)).
- **Measured.** Users pay <!--n:n2.fees_usd_per_day-->$206,049<!--/n--> a day in fees (DefiLlama, *provisional*). *Coverage*, the NEAR that
  the buybacks wallets (the two wallets that hold bought-back NEAR) keep ÷ the NEAR issued in the same days, is
  <!--n:n1.coverage_buybacks-->10.8%<!--/n-->; <!--n:n1.coverage_with_front_end-->16.5%<!--/n--> counting the
  front-end fund too (the near-intents.org front end's own fees, kept in a separate fund).
- **Ceiling.** If NEAR kept every fee, coverage would be <!--n:n2.max_coverage-->47.9%<!--/n--> (*provisional*). Covering all of
  issuance needs what the buybacks wallets keep to grow <!--n:iv.wallets_multiple_buybacks-->×9.2<!--/n-->, or, with
  every fee kept, fees to grow <!--n:iv.fees_multiple-->×2.1<!--/n-->.
- **Verdict.** Hold NEAR staked, not for the fees it captures: supply grows
  <!--n:iv.issuance_rate_per_year-->2.46%<!--/n--> a year, staking pays about
  <!--n:iv.staking_yield_gross-->4.9%<!--/n--> before commissions, and the buybacks offset
  <!--n:iv.buybacks_offset_points_per_year-->0.27<!--/n--> of those points. The view turns positive only on the
  conditions in the [Investment view](#investment-view).
- **Check.** Four offline commands that run in seconds, no network ([Check it in two minutes](#check-it-in-two-minutes)).
  Five predictions are anchored on chain: two, with stated probabilities, are judged on 6 and 8 November, before
  the deadline; three on 16 November ([Pre-registration](#pre-registration)).

Investment Thesis track, NEAR HACKATHON (1–14 November 2026). Every figure below is computed by a script in this
repository and copied here from [`data/numbers.json`](data/numbers.json) with a hidden marker of its key (view the
source); `build_numbers.py --check README.md` fails if any figure differs. Sources: NEAR archival RPC, the NearBlocks
API, DefiLlama, and one off-chain read of a NEAR AI Cloud setting. Raw responses are saved byte for byte; those that
list people's accounts are kept private, with their SHA-256 ([Method](docs/DETAILS.md#method)). Block heights, dates
and protocol constants are written as they are.

> **Status: v1.1, 3 November 2026.** Measurement window 2 October → 1 November 2026 (00:00 UTC), blocks
> 218,126,921 → 222,491,356. Numbers 1 and 3 are final for this window. Number 2 and every DefiLlama-based
> figure are **provisional** until DefiLlama's data settles (rule in [Method](docs/DETAILS.md#method)).

## For judges

| Criterion | Where to look |
|---|---|
| Thesis | [`THESIS.md`](THESIS.md): claim, evidence for, evidence against, what would change our mind, metrics we cannot compute |
| Reproducibility | [Check it in two minutes](#check-it-in-two-minutes): four offline commands, Python standard library only. Every figure in this file is checked against `data/numbers.json`, and each entry there against the saved raw responses and their SHA-256 |
| Evidence | each finding names its script and data file; `scripts/remeasure.py` re-measures numbers 1 and 3 from the chain; DefiLlama's revenue is checked against the wallets' own balances (finding 1) |
| Technical implementation | accounting from block headers and balances, to the yoctoNEAR: issuance net of gas burnt (`burn.py`), `treasury.near`'s reward reproduced at every epoch start (`treasury_spend.py`), its balance falls located block by block (`treasury_exits.py`), farm positions that add up to the contract's total (`stakers.py`) |
| What this adds | who can change each link from fee to holder, and how often they have ([control map](#the-control-map-who-can-change-each-link)); the NEAR AI farm, its owner's flows and its credits rate (findings 3–5); the weight of each HSP-029 voter (finding 8) |
| Falsifiable | five predictions anchored on NEAR mainnet: two with stated probabilities, anchored before the event and judged on 6 and 8 November, before the deadline; three judged on 16 November ([Pre-registration](#pre-registration)) |
| Limits | [What we can't measure](#what-we-cant-measure); people's accounts appear only as SHA-256 tags ([Method](docs/DETAILS.md#method)) |

## Check it in two minutes

Python 3.12 (`python` below; `python3` on some systems), standard library only, no network, no keys:

```
python -m unittest discover -s tests              # every script's logic on fixed inputs
python scripts/build_numbers.py --verify           # every script's offline check, then numbers.json rebuilds the same
python scripts/build_numbers.py --check README.md  # every marked number in this file matches numbers.json
python scripts/check_prereg.py --file              # PREREG.md matches the anchored SHA-256 (saved copy)
```

The second command ends with `VERIFY: PASS (PUBLIC_FULL)`: every number recomputed with no network and without
the private originals ([Method](docs/DETAILS.md#method)). The `verify` badge runs these, and the check of
`data/upgrade_watch.csv`, on every push. Five live read-only calls, and a re-measurement of numbers 1 and 3 from
the chain, are in [Verify live](docs/DETAILS.md#verify-live).

## The three numbers

| # | What an investor watches | Value | Window or block | Reproduce (no network) |
|---|---|---|---|---|
| 1 | New NEAR supply covered by the buybacks wallets | **<!--n:n1.coverage_buybacks-->10.8%<!--/n-->** (<!--n:n1.buybacks_near_per_day-->9,570<!--/n--> of <!--n:n1.new_near_per_day-->88,392<!--/n--> NEAR a day) · with the front-end fund **<!--n:n1.coverage_with_front_end-->16.5%<!--/n-->** | 2 Oct → 1 Nov 2026, blocks 218,126,921 → 222,491,356 | `python scripts/daily.py --verify` |
| 2 | The ceiling: all fees recorded by DefiLlama ÷ issuance | **<!--n:n2.max_coverage-->47.9%<!--/n-->** · equilibrium price **<!--n:n2.equilibrium_price_usd-->$2.33<!--/n-->** · *provisional* | same window, complete DefiLlama days only | `python scripts/fees.py --verify data/fees_2026-10-02_2026-11-01.json` |
| 3 | How widely the NEAR AI farm is spread (NEAR staked through `stake.dao`, paid in credits instead of NEAR) | **<!--n:n3.stakers_active-->112<!--/n-->** active accounts · largest **<!--n:n3.largest_share-->73.3%<!--/n-->** · top 10 <!--n:n3.top10_share-->96.4%<!--/n--> · median outside the top 10 <!--n:n3.outside_top10_median_near-->60<!--/n--> NEAR | block 222,491,356 (1 Nov 2026 00:00 UTC) | `python scripts/stakers.py --verify` |

- **1.** Balance change of `buybacks.multisignature.near` + `1csfundsadmin.sputnik-dao.near` ÷ change of
  `total_supply` between the two block headers. The front-end fund, `fefundsadmin.sputnik-dao.near`
  (<!--n:n1.front_end_near_per_day-->4,985<!--/n--> NEAR a day), holds near-intents.org's own fees.
- **2.** Each day's fees converted at that day's NEAR price, ÷ new NEAR per day. At HSP-029's target rate
  (issuance ×16/25) the ceiling would be <!--n:n2.hsp029_max_coverage-->74.8%<!--/n-->.
- **3.** Every account that ever staked through `stake.dao`, read at the block: <!--n:n3.stakers_ever-->188<!--/n--> entered,
  <!--n:n3.stakers_left-->76<!--/n--> (<!--n:n3.left_share_of_ever-->40.4%<!--/n-->) have left, and the active positions add up exactly to the
  farm's total (<!--n:n3.farm_total_near-->1,364,348<!--/n--> NEAR). NEAR AI Agents subscription locks are kept out.

Full definitions, and why the locks are kept out: [details](docs/DETAILS.md#the-three-numbers).

## Investment view

*Dated 2 November 2026. Horizon: 12 months, to November 2027. Thresholds are the author's choice; every figure
in them is measured.*

**Verdict: hold NEAR staked with a validator; do not hold it for fee capture.** Today the buybacks absorb a small part of new NEAR, and they are a choice of a few
signers, not a rule: holding NEAR long term is a bet on the three conditions below, not a claim on today's fees.
At the end block <!--n:c.issuance_staked_share-->45.2%<!--/n--> of supply (<!--n:c.issuance_total_stake_near-->592,027,869<!--/n--> NEAR) is staked with validators. What each holder gets:

| Holder | NEAR received | What changes |
|---|---|---|
| Not staked | none | owns a smaller share as supply grows <!--n:iv.issuance_rate_per_year-->2.46%<!--/n--> a year; the buybacks offset <!--n:iv.buybacks_offset_points_per_year-->0.27<!--/n--> points of it |
| Staked with a validator | about <!--n:iv.staking_yield_gross-->4.9%<!--/n--> a year, before the validator's commission | keeps pace with issuance |
| Staked in the NEAR AI farm | none: `nearai.pool.near` keeps <!--n:c.nearai_pool_reward_fee-->100%<!--/n--> of rewards | <!--n:f6.units_per_near_year-->0.24<!--/n--> reward units per NEAR a year, <!--n:f6.usd_per_reward_unit-->$1.00<!--/n--> of credits each (off-chain setting); worth more than a validator's rewards only while NEAR is below <!--n:iv.farm_breakeven_price_usd-->$4.90<!--/n--> |

| Condition | Today | Turns positive when | How far | Measured by |
|---|---|---|---|---|
| **(a)** Coverage | <!--n:n1.coverage_buybacks-->10.8%<!--/n--> (<!--n:n1.coverage_with_front_end-->16.5%<!--/n--> with the front-end fund) | the buybacks wallets keep as much NEAR as is issued (100%) | what they keep must grow <!--n:iv.wallets_multiple_buybacks-->×9.2<!--/n--> (<!--n:iv.wallets_multiple_with_front_end-->×6.1<!--/n--> with the front-end fund) at today's issuance and price; if NEAR kept every fee, fees must grow <!--n:iv.fees_multiple-->×2.1<!--/n--> | `data/history.csv`, every day |
| **(b)** A rule, not a choice | bought NEAR held by a <!--n:c.buybacks_confirmations-->2 of 4<!--/n--> multisig, nothing burned | bought NEAR moves by a published rule to an account no one can spend from, or the protocol fee on `intents.near` is routed there | no rule yet ([Path to rules](#path-to-rules)) | `scripts/control_map.py` |
| **(c)** Stake spread | the largest account holds <!--n:n3.largest_share-->73.3%<!--/n--> of the NEAR AI farm | the largest account holds less than half | prediction 1 expects at least 70% on 16 November | `scripts/stakers.py` |

**Weight of each condition.** (a) and (b) decide value. (c) is a signal, not a lever: the farm holds
<!--n:iv.farm_share_of_stake-->0.23%<!--/n--> of all stake, and stake cannot offset issuance, because stakers are the ones who
receive the new NEAR. Buybacks can, because they pay for NEAR with money from outside: the fees users pay.

**Break-even prices** (*provisional*). Fees buy as many NEAR a day as are issued at a NEAR price of
<!--n:n2.equilibrium_price_usd-->$2.33<!--/n--> or less if NEAR kept every fee, and <!--n:iv.revenue_equilibrium_price_usd-->$0.80<!--/n--> or less with
today's revenue (the part DefiLlama counts as NEAR's, front-end fund included). HSP-029's lower rate, and when it
could take effect: [details](docs/DETAILS.md#investment-view-hsp-029-and-the-staking-yield).

**What would make it worse:** the buybacks wallets pay NEAR out (number 1 falls while DefiLlama revenue does not),
or monthly coverage falls back to its April level (<!--n:f1.coverage_buybacks.2026-04-->5.3%<!--/n-->). **When to check:**
16 November 2026 (the predictions), every month from `data/history.csv`, in full in November 2027.

## The control map: who can change each link

Each link from the fee a user pays to the NEAR a holder keeps, with who can change it and how often they have.
Values are read at block 222,491,356 (`scripts/control_map.py`, `data/control_map.json`); "used" counts every
proposal of the five DAOs involved (`scripts/control_history.py`, `data/control_history.json`) and key changes from
NearBlocks, checked against the chain. Multisigs and DAOs are a common way to run protocol funds; the point is what a
holder relies on today, and the mechanism that could turn each link into a rule ([Path to rules](#path-to-rules)).
The <!--n:c.dao_count-->5<!--/n--> DAOs have <!--n:c.dao_member_accounts-->22<!--/n--> member accounts, and the number that sit in more than one is <!--n:c.dao_members_in_two_or_more-->0<!--/n-->
(counted from the redacted policies, where each account is a SHA-256 tag).

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

**Links that decide value.**

| Link | Today | Who can change it | Signatures | Used |
|---|---|---|---|---|
| Fees users pay | <!--n:n2.fees_bps-->16.0<!--/n--> bps of volume (DefiLlama) | The distribution channels, off-chain. 1Click's terms let its operator change fees "at any time on a prospective basis" ([terms](https://docs.near-intents.org/near-intents/integration/distribution-channels/1click-terms-of-service)) | not on chain | not visible on chain |
| Protocol fee (`intents.near` `fee`) | <!--n:c.intents_fee_pips-->1 pip<!--/n--> = <!--n:c.intents_fee_percent-->0.0001%<!--/n--> | `intents.sputnik-dao.near` (role DAO); FeesManager role: <!--n:c.intents_fees_manager_accounts-->0<!--/n--> accounts | <!--n:c.intents_fee_change-->3 of 5<!--/n--> | `set_fee` <!--n:h.set_fee-->3<!--/n-->, `set_fee_collector` <!--n:h.set_fee_collector-->3<!--/n--> (<!--n:h.fee.first-->2024-11-07<!--/n--> → <!--n:h.fee.last-->2025-10-02<!--/n-->) |
| Buybacks wallet (`buybacks.multisignature.near`) | holds the bought NEAR; nothing is burned | its multisig members (<!--n:c.buybacks_full_access_keys-->0<!--/n--> full-access keys) | <!--n:c.buybacks_confirmations-->2 of 4<!--/n--> | keys unchanged since <!--n:h.keys.buybacks.last_change-->2026-03-18<!--/n--> |
| 1Click fund (`1csfundsadmin.sputnik-dao.near`) | counted with the buybacks wallet in number 1 | DAO: transfers / its own rules | <!--n:c.wallet_1cs_transfer-->2 of 4<!--/n--> / <!--n:c.wallet_1cs_rules-->2 of 4<!--/n--> | — |
| Front-end fund (`fefundsadmin.sputnik-dao.near`) | <!--n:f9.front_end_share_of_wallets-->34.2%<!--/n--> of what the three wallets kept | DAO: transfers / its own rules, upgrades and members. One Admin can change the rules alone, so one key can also move the funds, in two steps | <!--n:c.front_end_transfer-->2 of 5<!--/n--> / <!--n:c.front_end_rules-->1 of 5<!--/n--> | — |
| Issuance (`max_inflation_rate`) | <!--n:c.issuance_max_inflation_rate-->1/40<!--/n--> a year | a new nearcore release, run by validators with <!--n:c.issuance_upgrade_stake_threshold-->4/5<!--/n--> of stake | at least <!--n:c.issuance_validators_to_pass_upgrade-->44<!--/n--> of <!--n:c.issuance_validators-->381<!--/n--> validators (the largest); the <!--n:c.issuance_validators_to_block_upgrade-->5<!--/n--> largest can block; largest holds <!--n:c.issuance_largest_validator_share-->5.6%<!--/n--> | see HSP-027 below |
| Protocol treasury (`treasury.near`) | its balance grew by <!--n:c.treasury_share_of_new_supply-->10.1%<!--/n--> of new supply (<!--n:c.treasury_near_received-->268,973<!--/n--> NEAR in the window) | its multisig members | <!--n:c.treasury_confirmations-->2 of 4<!--/n--> | keys last changed <!--n:h.keys.treasury.last_change-->2025-09-05<!--/n-->; paid out <!--n:ts.year_out_near-->30,171,200<!--/n--> NEAR in 2026 (finding 9) |
| House of Stake voting (`vote.dao`) | decides what reaches a vote | owner `hos-root.sputnik-dao.near`; <!--n:c.hsp_reviewers-->5<!--/n--> reviewers choose what is put to a vote | <!--n:c.hsp_owner_rules-->3 of 5<!--/n--> | reviewers, council or guardians changed <!--n:h.voting.approved_actions-->5<!--/n--> times (<!--n:h.voting.first-->2026-02-09<!--/n--> → <!--n:h.voting.last-->2026-07-22<!--/n-->) |
| NEAR AI pool rewards (`nearai.pool.near`) | the pool keeps <!--n:c.nearai_pool_reward_fee-->100%<!--/n--> of staking rewards | its owner, a DAO with no access keys | <!--n:c.nearai_pool_owner_transfer-->2 of 3<!--/n--> | <!--n:h.staking.approved_actions-->57<!--/n--> staking actions by the owner |
| NEAR AI credits rate (`stake.dao` `edit_price`) | <!--n:f6.units_per_near_year-->0.24<!--/n--> reward units per staked NEAR per year | one catalog manager of the pool, named by the owner's DAO (<!--n:h.catalog_manager_added-->1<!--/n--> proposal) | 1 | changed <!--n:f6.rate_changes-->1<!--/n--> time: <!--n:f6.change1.utc-->2026-09-29 14:21 UTC<!--/n-->, <!--n:f6.change1.ratio-->×2.0<!--/n-->, without a proposal |

The same DAOs can also upgrade `intents.near` (<!--n:c.intents_code_changes-->20<!--/n--> code changes, last
<!--n:c.intents_code_last_change_utc-->2026-10-07<!--/n-->), move users' funds on it by proposal (<!--n:h.user_funds.approved_actions-->12<!--/n--> actions)
and pause its features (<!--n:h.pause.approved_actions-->7<!--/n--> actions): [contract-level admin scope](docs/DETAILS.md#contract-level-admin-scope).

## Findings

**1. Coverage has been below a quarter of issuance in every month since April.** From the wallets alone: balances
and block headers, independent of DefiLlama (`scripts/coverage.py`, `data/coverage_monthly.json`).

| | Apr | May | Jun | Jul | Aug | Sep | Oct |
|---|---|---|---|---|---|---|---|
| Buybacks wallets | <!--n:f1.coverage_buybacks.2026-04-->5.3%<!--/n--> | <!--n:f1.coverage_buybacks.2026-05-->8.4%<!--/n--> | <!--n:f1.coverage_buybacks.2026-06-->8.5%<!--/n--> | <!--n:f1.coverage_buybacks.2026-07-->6.2%<!--/n--> | <!--n:f1.coverage_buybacks.2026-08-->10.2%<!--/n--> | <!--n:f1.coverage_buybacks.2026-09-->15.3%<!--/n--> | <!--n:f1.coverage_buybacks.2026-10-->10.9%<!--/n--> |
| With the front-end fund | <!--n:f1.coverage_with_front_end.2026-04-->5.7%<!--/n--> | <!--n:f1.coverage_with_front_end.2026-05-->11.9%<!--/n--> | <!--n:f1.coverage_with_front_end.2026-06-->11.2%<!--/n--> | <!--n:f1.coverage_with_front_end.2026-07-->9.1%<!--/n--> | <!--n:f1.coverage_with_front_end.2026-08-->14.8%<!--/n--> | <!--n:f1.coverage_with_front_end.2026-09-->21.3%<!--/n--> | <!--n:f1.coverage_with_front_end.2026-10-->16.5%<!--/n--> |

Months start at the first block at or after 00:00 UTC of each 1st. Over the window, DefiLlama's revenue ÷ issuance
gives <!--n:n2.defillama_revenue_coverage-->16.5%<!--/n--> against <!--n:n1.coverage_with_front_end-->16.5%<!--/n--> from the wallets: DefiLlama counts
inflows to the same wallets and we measure their balances, so the two agreeing means almost nothing flowed out.

**2. October's revenue rose in dollars but bought fewer NEAR, because the NEAR price rose faster.** From September
to October revenue rose <!--n:f2.change.2026-09_2026-10.revenue_usd-->+15%<!--/n--> (<!--n:f2.revenue_usd_per_day.2026-09-->$61,317<!--/n--> →
<!--n:f2.revenue_usd_per_day.2026-10-->$70,630<!--/n--> a day) and the mean NEAR price <!--n:f2.change.2026-09_2026-10.mean_price-->+49%<!--/n-->
(<!--n:f2.mean_price_usd.2026-09-->$3.28<!--/n--> → <!--n:f2.mean_price_usd.2026-10-->$4.89<!--/n-->), so the NEAR that revenue buys fell
<!--n:f2.change.2026-09_2026-10.revenue_near-->-24%<!--/n-->, and coverage with it (<!--n:f1.coverage_buybacks.2026-09-->15.3%<!--/n--> →
<!--n:f1.coverage_buybacks.2026-10-->10.9%<!--/n-->). The wallets kept <!--n:f2.wallets_kept_share_of_revenue.2026-09-->98%<!--/n--> and
<!--n:f2.wallets_kept_share_of_revenue.2026-10-->100%<!--/n--> of that revenue: the fall is the price, not an outflow. Over the
longer run the take rate (revenue ÷ fees) rose from <!--n:f2.take_rate.2026-04-->8.1%<!--/n--> in April to <!--n:f2.take_rate.2026-10-->34.3%<!--/n-->
in October, while fees per dollar of volume stayed between <!--n:f2.fees_bps.2026-08-->13.8<!--/n--> and <!--n:f2.fees_bps.2026-10-->16.0<!--/n-->
bps from August to October. *Provisional, like every DefiLlama figure.*

**3. Since the farm opened, the NEAR held by the NEAR AI pool's owner changed by <!--n:f4.since_stake_dao.owner_near_change-->-401,848<!--/n--> NEAR.**
From the creation of `stake.dao` (<!--n:f4.stake_dao_start_utc-->2026-07-28<!--/n-->; first `stake` call <!--n:f4.first_stake_utc-->2026-07-30<!--/n-->) to
block 222,491,356 (`scripts/treasury_flows.py`, `data/treasury_flows.json`), the owner, a DAO that acts only
through proposals:

- approved unstaking <!--n:f4.since_stake_dao.unstaked_near-->425,334<!--/n--> NEAR and sending out
  <!--n:f4.since_stake_dao.near_sent_out-->423,980<!--/n--> NEAR (<!--n:f4.since_stake_dao.near_to_payments_account-->280,338<!--/n--> to its own
  payments account) and <!--n:f4.since_stake_dao.usdc_sent_out-->$365,000<!--/n--> in USDC;
- held <!--n:f4.since_stake_dao.owner_near_start-->1,336,984<!--/n--> → <!--n:f4.since_stake_dao.owner_near_end-->935,136<!--/n--> NEAR, liquid and in
  every pool;
- through its payments account, swapped <!--n:f4.since_stake_dao.swaps_near_given-->139,546<!--/n--> NEAR for
  <!--n:f4.since_stake_dao.swaps_usd_received-->$296,652<!--/n--> in <!--n:f4.since_stake_dao.swaps-->7<!--/n--> swaps on NEAR Intents (mean price
  <!--n:f4.since_stake_dao.swaps_mean_price_usd-->$2.13<!--/n-->).

In the same period users' stake in the farm reached <!--n:n3.farm_total_near-->1,364,348<!--/n--> NEAR. The two are separate figures,
not a net: users' stake can be withdrawn, and the purpose of each payment is not measured.

**4. The same account has been the largest in the farm since <!--n:f5.largest_same_account_since-->2026-08-15<!--/n-->, with between
<!--n:f5.largest_share.2026-10-15-->58.9%<!--/n--> and <!--n:f5.largest_share.2026-08-15-->76.9%<!--/n--> of it.** First block of the 1st and the
15th (`scripts/stakers.py`):

| | 1 Aug | 15 Aug | 1 Sep | 15 Sep | 1 Oct | 15 Oct | 1 Nov |
|---|---|---|---|---|---|---|---|
| Active accounts | <!--n:f5.stakers_active.2026-08-01-->16<!--/n--> | <!--n:f5.stakers_active.2026-08-15-->46<!--/n--> | <!--n:f5.stakers_active.2026-09-01-->51<!--/n--> | <!--n:f5.stakers_active.2026-09-15-->73<!--/n--> | <!--n:f5.stakers_active.2026-10-01-->88<!--/n--> | <!--n:f5.stakers_active.2026-10-15-->99<!--/n--> | <!--n:f5.stakers_active.2026-11-01-->112<!--/n--> |
| Largest account's share | <!--n:f5.largest_share.2026-08-01-->36.2%<!--/n--> | <!--n:f5.largest_share.2026-08-15-->76.9%<!--/n--> | <!--n:f5.largest_share.2026-09-01-->76.1%<!--/n--> | <!--n:f5.largest_share.2026-09-15-->75.7%<!--/n--> | <!--n:f5.largest_share.2026-10-01-->74.1%<!--/n--> | <!--n:f5.largest_share.2026-10-15-->58.9%<!--/n--> | <!--n:f5.largest_share.2026-11-01-->73.3%<!--/n--> |

On 1 August the largest was another account. The largest of 1 November held <!--n:f5.largest_near.2026-10-15-->500,000<!--/n--> NEAR
on 15 October and <!--n:f5.largest_near.2026-11-01-->1,000,000<!--/n--> on 1 November; its lower share on 15 October came from other
accounts' new stake.

**5. The credits rate is a setting, changed once by one account** (`scripts/farm_rate.py`, `data/farm_rate.json`).
The farm pays reward units; the contract has no USD conversion. The rate went from
<!--n:f6.change1.units_per_near_year_before-->0.12<!--/n--> to <!--n:f6.change1.units_per_near_year_after-->0.24<!--/n--> units per staked NEAR a year (<!--n:f6.change1.ratio-->×2.0<!--/n-->) on <!--n:f6.change1.utc-->2026-09-29 14:21 UTC<!--/n-->, through
<!--n:f6.edit_price_receipts_all_time-->1<!--/n--> `edit_price` call, the only one in the contract's history, signed by the pool's catalog
manager without a proposal of the owner's DAO. NEAR AI Cloud pays <!--n:f6.usd_per_reward_unit-->$1.00<!--/n--> of credits per unit (an off-chain
setting read on 2026-11-01 in a signed-in session, saved in `data/offchain/`), so the largest position receives
<!--n:f6.largest_usd_per_day-->$657.1<!--/n--> of credits a day; whether the credits are used is not visible. At the staking
yield of <!--n:iv.staking_yield_gross-->4.9%<!--/n-->, a staked NEAR earns as much in credits as in a validator's rewards (before
commission) at a NEAR price of <!--n:iv.farm_breakeven_price_usd-->$4.90<!--/n-->; with the rate before its only change, at
<!--n:iv.farm_breakeven_price_before_usd-->$2.45<!--/n-->. The mean NEAR price was <!--n:f2.mean_price_usd.2026-08-->$1.74<!--/n--> in August,
<!--n:f2.mean_price_usd.2026-09-->$3.28<!--/n--> in September and <!--n:f2.mean_price_usd.2026-10-->$4.89<!--/n--> in October (*provisional*): the
rate does not follow the price, and the one change moved the break-even to about October's price.

**6. NEAR AI Agents subscriptions are a separate product.** They are locks on `stake.dao`: <!--n:f7.locks-->86<!--/n--> locks
from <!--n:f7.lock_accounts-->83<!--/n--> accounts; NEAR in Active locks is <!--n:f7.active_lock_near_vs_farm-->1.1%<!--/n--> of the farm. Why
they are kept out of number 3: [details](docs/DETAILS.md#the-three-numbers).

**7. Of what the three wallets kept, <!--n:f9.front_end_share_of_wallets-->34.2%<!--/n--> went to the front-end fund, which
DefiLlama counts as buybacks.** It holds near-intents.org's fees, not bought-back NEAR; NEAR's docs publish where
these fees go ([fees](https://docs.near-intents.org/resources/fees)). This is why number 1 is given both ways.
NEAR's own dashboard ([revenue.near.org](https://revenue.near.org/), read on 23 October 2026) books the two
transfers from `1csfundsadmin.sputnik-dao.near` to the buybacks wallet under 1Click; number 1 adds the two wallets,
so that move cancels out.

**8. HSP-029 passed with no veNEAR against, and <!--n:f8.fewest_voters_reaching_quorum-->6<!--/n--> voters were enough for its quorum.**
At the vote's last block, 222,745,764 (`scripts/hsp029.py`, `scripts/hsp029_voters.py`): <!--n:f8.for_venear-->3,287,729<!--/n--> veNEAR
for, <!--n:f8.against_venear-->0<!--/n--> against and <!--n:f8.abstain_venear-->1,071<!--/n--> abstaining, from <!--n:f8.voters-->36<!--/n--> voters.
<!--n:f8.turnout_of_snapshot-->62.3%<!--/n--> of the <!--n:f8.snapshot_total_venear-->5,274,745<!--/n--> veNEAR in the snapshot voted, against a quorum of
<!--n:f8.quorum_required_venear-->1,846,161<!--/n-->. The largest voter cast <!--n:f8.top1_share_of_votes_cast-->12.2%<!--/n--> of the votes and the 8
largest <!--n:f8.top8_share_of_votes_cast-->80.6%<!--/n-->. `vote.dao` holds it in `<!--n:f8.contract_status_at_close-->Timelock<!--/n-->` until <!--n:f8.timelock_end_utc-->2026-11-16 16:48 UTC<!--/n-->.
The vote executes nothing on chain (`actions: null`): issuance falls only when validators run a release that
includes it ([Path to rules](#path-to-rules)).

**9. `treasury.near` receives 10% of the maximum issuance; in 2026 it paid out
<!--n:ts.year_out_near-->30,171,200<!--/n--> NEAR, all in April and May.** `scripts/treasury_spend.py` reproduces its reward to the yocto at
<!--n:ts.rule_exact-->101<!--/n--> of the <!--n:ts.rule_epochs-->101<!--/n--> epoch starts in the window: floor(floor(supply × Δt / (40 × 365 days)) / 10),
10% of the maximum issuance (<!--n:ts.share_of_minted-->10.03%<!--/n--> of what is minted, as validators below full uptime receive less).
In 2026 it received <!--n:ts.year_treasury_in_near-->2,700,599<!--/n--> NEAR and <!--n:ts.year_out_near-->30,171,200<!--/n--> left it: <!--n:ts.out_near.2026-04-->9,800,000<!--/n--> in April and
<!--n:ts.out_near.2026-05-->20,371,200<!--/n--> in May, none in the window of number 1. Its balance went from <!--n:ts.balance_start_near-->28,996,906<!--/n--> to
<!--n:ts.balance_end_near-->1,526,304<!--/n-->. `scripts/treasury_exits.py` locates each of the <!--n:te.steps-->73<!--/n--> balance steps to the block and reads
the <!--n:te.transactions_read-->8<!--/n--> transactions of 1 NEAR or more (`data/treasury_exits.json`):

| Date (UTC) | Receiver | NEAR | Transfers |
|---|---|---|---|
| 2026-04-15 | `ecotreasury5.multisignature.near` | <!--n:te.to.ecotreasury5.amount-->4,900,000<!--/n--> | <!--n:te.to.ecotreasury5.transfers-->1<!--/n--> |
| 2026-04-15 | `ecotreasury4.multisignature.near` | <!--n:te.to.ecotreasury4.amount-->4,900,000<!--/n--> | <!--n:te.to.ecotreasury4.transfers-->1<!--/n--> |
| 2026-05-13 | one implicit account, `sha256:e630d735067c39fe` | <!--n:te.to.sha256_e630d735.amount-->20,371,200<!--/n--> | <!--n:te.to.sha256_e630d735.transfers-->5<!--/n--> |
| 2026-04-15 | `foundation.near` | <!--n:te.to.foundation.amount-->3<!--/n--> (3 NEAR came back to `treasury.near` 153 seconds later) | <!--n:te.to.foundation.transfers-->1<!--/n--> |

Each payment is a `confirm` on the multisig (<!--n:c.treasury_confirmations-->2 of 4<!--/n--> keys). Multisig, DAO and institutional
receivers are named; other accounts are shown as tags ([Method](docs/DETAILS.md#method)). The purpose of each payment is not on chain and is
not characterized here.

## Path to rules

Each link that decides value can become a rule with a mechanism NEAR already has. Governance has started on this
path: HSP-027 (remove the developer gas rebate) passed on 3 July 2026, and
[HSP-029](https://gov.houseofstake.org/proposals/29) (issuance 2.5% → 1.6% a year over a 24-month ramp) passed its
vote on 2 November and stays in `vote.dao`'s timelock until <!--n:f8.timelock_end_utc-->2026-11-16 16:48 UTC<!--/n--> (finding 8). A House of Stake vote changes nothing on chain by itself (`actions: null`): it takes a
nearcore release that validators with <!--n:c.issuance_upgrade_stake_threshold-->4/5<!--/n--> of stake run. HSP-027 is protocol
version 87 in nearcore 2.14.0, open to validator votes from 4 November 2026 00:00 UTC
([`version.rs`](https://github.com/near/nearcore/blob/2.14.0/core/primitives/src/version.rs)); `scripts/upgrade_watch.py`
records every day how much stake signals it (`data/upgrade_watch.csv`), so "passed" versus "in force" is measured
during the hackathon. Its effect is small: gas burns <!--n:b.burnt_near_per_day-->974<!--/n--> NEAR a day, and removing the rebate
adds at most <!--n:b.hsp027_extra_burn_max_near_per_day-->417<!--/n--> (<!--n:b.hsp027_extra_max_share_of_minted-->0.47%<!--/n--> of gross issuance;
`scripts/burn.py`), against <!--n:n1.buybacks_near_per_day-->9,570<!--/n--> a day kept by the buybacks wallets.

| Link | What would make it a rule | Trade-off |
|---|---|---|
| Fees users pay | Part of the fee charged as the protocol fee on `intents.near` (up to 100% is allowed; today <!--n:c.intents_fee_pips-->1 pip<!--/n-->), with `fee_collector` set to the buybacks wallet or a locked account | The fee can still change by DAO vote (<!--n:c.intents_fee_change-->3 of 5<!--/n-->), but visibly and with a history |
| Buybacks wallet | Move bought NEAR on a published schedule to an account with no keys and no code, or to a contract with no withdraw method | Native NEAR cannot be burned by a call: locking lowers circulating supply, not `total_supply` |
| Issuance | Already a protocol rule; HSP-029 would lower it if validators adopt it | <!--n:c.issuance_validators_to_block_upgrade-->5<!--/n--> validators are enough to block |
| Protocol treasury | A public spending rule voted as an HSP, or a lower share through the protocol | Today <!--n:c.treasury_confirmations-->2 of 4<!--/n--> keys approve each payment; <!--n:ts.year_out_near-->30,171,200<!--/n--> NEAR left in 2026 (finding 9) |
| NEAR AI credits rate | A formula in the contract (the docs say the budget depends on APY and price), or changes only by DAO proposal with a delay | The rate follows neither today: it changed once, by hand |
| Front-end and 1Click funds, pool rewards | Their DAOs' spending and fee choices written as public rules (for example, an HSP), not decided proposal by proposal | Less room to adjust |
| `intents.near` code | A published delay between a release and its installation | A delay would also slow urgent fixes; pausing would stay immediate |

The same map for Hyperliquid, Aave and Jupiter, from their docs: [peers](docs/DETAILS.md#peers).

## Pre-registration

Three predictions, judged on 16 November 2026, are in [`PREREG.md`](PREREG.md). The file was anchored on
NEAR mainnet before judging: its SHA-256 is stored in SocialDB (`social.near`) under the key
`samerice7976.near/thesis/prereg/1`, written by transaction
[`8fZ8VTUyM1UjnybqPd1QCQi4c3y75dDRGR5TjkNGgnPL`](https://nearblocks.io/txns/8fZ8VTUyM1UjnybqPd1QCQi4c3y75dDRGR5TjkNGgnPL)
from `samerice7976.near`. The transaction was included in block 222,606,824 (2026-11-01 18:30:38 UTC)
and executed by `social.near` in block 222,606,825 (18:30:39 UTC). `PREREG.md` has not changed since. Prediction 2's
window had already opened, at 2026-11-01 00:00 UTC; `PREREG.md` states what had been read by then.

Anchored SHA-256: `d3f48ed9172b1785b4dcf290b84e9a06c870b8b9b5481c6d40e51a4605b1d494`

| # | Prediction | Holds if | Baseline |
|---|---|---|---|
| 1 | The largest account keeps at least 70% of the NEAR AI farm on 16 Nov | share ≥ 0.70 | <!--n:n3.largest_share-->73.3%<!--/n--> |
| 2 | Net inflows to the buybacks wallet, 1–15 Nov, stay below a quarter of new supply | ratio < 0.25 | <!--n:n1.coverage_buybacks-->10.8%<!--/n--> (2 Oct–1 Nov; `1csfundsadmin` did not change in the window, so this equals the buybacks wallet alone) |
| 3 | Fewer than 150 accounts are active in the NEAR AI farm on 16 Nov | count < 150 | <!--n:n3.stakers_active-->112<!--/n--> |

Exact rules, timing and void conditions are in `PREREG.md`. The results will be published whatever they are.

**Second pre-registration: when HSP-027 takes effect.** [`PREREG-2.md`](PREREG-2.md) was anchored the same way,
under `samerice7976.near/thesis/prereg/2`, by transaction
[`EZ6mexrYfaMFivjLqccSjxGkTgWDEqUBUeiZDoAx9art`](https://nearblocks.io/txns/EZ6mexrYfaMFivjLqccSjxGkTgWDEqUBUeiZDoAx9art),
included in block 222,916,018 (2026-11-03 19:48:55 UTC), four hours before validators' voting for protocol
version 87 opened. It states a probability for each prediction, so the result is scored, not only counted.

Anchored SHA-256: `545cf67530b37c902b2674cb4014818d3f79eb1718fe6bbab896a361e48ce0d3`

| # | Prediction | Holds if | Probability stated | Judged at |
|---|---|---|---|---|
| 4 | Protocol version 87 (HSP-027) is in effect on NEAR mainnet | `protocol_version` ≥ 87 | 0.85 | first block at or after 2026-11-06 00:00 UTC |
| 5 | Protocol version 88 is in effect on NEAR mainnet | `protocol_version` ≥ 88 | 0.75 | first block at or after 2026-11-08 00:00 UTC |

Both are judged before the hackathon's deadline; the results and their Brier scores will be added here.

```
python scripts/check_prereg.py --file     # no network: PREREG.md against the saved anchored SHA-256
python scripts/check_prereg.py            # 4 read-only RPC calls: SocialDB record, transaction, its blocks
python scripts/check_prereg.py --verify   # no network: the same checks from the saved responses
```

The second command compares the file's SHA-256, the record stored in SocialDB now and the record inside the
transaction's own arguments, and checks the signer and that no receipt failed.

## What we can't measure

- **Confidential volume.** Part of NEAR Intents volume is confidential and reported separately by NearStats.
- **DefiLlama's volume** comes from a NEAR dataset on Dune and cannot be rebuilt from the chain here. Solver
  spreads and gas are not in the fees.
- **Credits in dollars.** The conversion from reward units to credits is an off-chain NEAR AI Cloud setting, read
  only with a signed-in session, and can change with no trace on chain. Whether credits are used is not visible.
- **The largest farm position.** Who holds it, and where its NEAR came from, is not visible to us on chain.
- **What `treasury.near`'s payments were for.** Amounts, blocks and receivers are measured (finding 9); the
  purpose is not on chain.
- **Whether HSP-027 is in force** before validators adopt version 87; until then it is "passed", not "in force".
- **Peers** are compared from their docs and press, not from their chains.

## Timeline and disclosure

- Research into data sources: 22–31 October 2026, in private notes that are not part of this repository.
- Code and data: from the first commit, 2026-10-31 13:51:52 UTC. The hackathon counts work from its announcement
  on 19 October; there is no earlier code.
- Libraries: none beyond the Python standard library. `docs/sign.html` loads NEAR Wallet Selector 10.1.4 from esm.sh.
- This is the author's only submission to NEAR HACKATHON.

License: [MIT](LICENSE).
