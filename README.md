# NEAR to 2031: value capture is real, small and discretionary

[![verify](https://github.com/nikolaskahris-png/near-thesis-data/actions/workflows/verify.yml/badge.svg)](https://github.com/nikolaskahris-png/near-thesis-data/actions/workflows/verify.yml)

**Rating: Hold.** Keep NEAR staked; do not add. Horizon 1 January 2031, checked every year. Until 1 December 2026 the rules cannot give anything else: Avoid needs two failing windows and the history starts on 1 November, and Buy needs a published lock that does not exist. Read them as a monitor, not as evidence for Hold.

- **Demand is large, on DefiLlama's data.** NEAR Intents moved <!--n:d.ours_30d_usd-->$4.02B<!--/n--> in DefiLlama's 30 days to <!--n:d.window_end-->7 November<!--/n--> (its latest 30 days at the fetch, not the window): <!--n:d.parent_rank-->15th<!--/n--> of <!--n:d.parent_groups_with_volume-->885<!--/n--> protocols in DefiLlama's DEX-volume overview, each protocol's versions counted as one. Across, Relay, deBridge and Stargate are not in it, so it is not a ranking against them. Counted in NEAR, the fees fell <!--n:lr.history.2026-04_2026-10.fees_near_multiple-->×0.5<!--/n--> from April to October. The chain confirms what reaches the buybacks wallets, not the fees.
- **What reaches holders is a policy, not a rule.** The buybacks wallets keep NEAR equal to <!--n:n1.coverage_buybacks-->10.8%<!--/n--> of the new NEAR issued, and burn none of it. No code requires them, <!--n:c.buybacks_confirmations-->2 of 4<!--/n--> signers can move the NEAR they hold, and the protocol treasury is "currently managed by the NEAR Foundation" ([SEC filing](https://www.sec.gov/Archives/edgar/data/0002067111/000121390026103106/ea0306486-424b3_bitwise.htm)).
- **Staking is what pays.** Your share of all NEAR, a year: staked +<!--n:iv.staked_share_growth-->2.44%<!--/n--> before the validator's commission (+<!--n:iv.staked_share_growth.commission_10-->1.95%<!--/n--> at 10%), unstaked <!--n:iv.unstaked_share_change-->-2.40%<!--/n-->. Buybacks change neither, because they hold what they buy.

**Buy** when **(b)** the buybacks become a published rule and `treasury.near` sent nothing in the window, *and* either the NEAR they keep, counted up to DefiLlama's revenue and fees, covers issuance, or **(a)** it grows <!--n:lr.required_growth.buybacks.A.2031-->+75%<!--/n--> a year. **Avoid** when this 30-day window and the one ending 30 days before it each fail a test: the wallets keep less than 75% of DefiLlama's revenue, or the buybacks keep April's <!--n:f2.buybacks_kept_usd_per_day.2026-04-->$6,270<!--/n--> a day or less (at this window's NEAR kept, a price of <!--n:iv.avoid_test2_price_usd-->$0.655<!--/n--> or less), unless the flow may have moved to the private path ([the rules](#the-rating-as-rules)).

**[Live dashboard](https://nikolaskahris-png.github.io/near-thesis-data/dashboard/)** · [Check it in two minutes](#check-it-in-two-minutes) · [One-page thesis](THESIS.md) · [Every detail](docs/DETAILS.md) · Window: 2 October → 1 November 2026 · As of 8 November 2026; figures from other dates say so where they appear

## The thesis in four claims

Each claim gives its number, the source, what argues against it, and the command that recomputes it with no network.

### A. Demand is large, on DefiLlama's data

NEAR Intents moved <!--n:d.ours_30d_usd-->$4.02B<!--/n--> in the 30 days to <!--n:d.window_end-->7 November<!--/n--> (DefiLlama's latest 30 days at the fetch, not the window), <!--n:d.ours_over_largest_other-->×1.9<!--/n--> the next of the <!--n:d.bridges_with_volume-->4<!--/n--> bridges with volume in that list (Unit, <!--n:d.largest_other.volume_30d_usd-->$2.12B<!--/n-->; the other two are far smaller) and <!--n:d.ours_over_largest_aggregator-->×2.6<!--/n--> the largest bridge aggregator in DefiLlama's volume data. The large bridges (Across, Relay, deBridge, Stargate) are not in that data; see Against. That list is DefiLlama's DEX-volume overview, where NEAR Intents sits as a "Bridge". Against every protocol in it, whatever its category, it is <!--n:d.parent_rank-->15th<!--/n--> of <!--n:d.parent_groups_with_volume-->885<!--/n--> once each protocol's versions are counted as one (<!--n:d.all_rank-->18th<!--/n--> of <!--n:d.all_protocols_with_volume-->1,104<!--/n--> as listed, with Uniswap V3 and V4 apart); those above it are DEXs, a launchpad and prediction markets. Volume a day by month:

| Apr | May | Jun | Jul | Aug | Sep | Oct |
|---|---|---|---|---|---|---|
| <!--n:f2.volume_usd_per_day.2026-04-->$63,184,683<!--/n--> | <!--n:f2.volume_usd_per_day.2026-05-->$64,377,032<!--/n--> | <!--n:f2.volume_usd_per_day.2026-06-->$78,489,734<!--/n--> | <!--n:f2.volume_usd_per_day.2026-07-->$71,147,733<!--/n--> | <!--n:f2.volume_usd_per_day.2026-08-->$89,591,202<!--/n--> | <!--n:f2.volume_usd_per_day.2026-09-->$160,103,146<!--/n--> | <!--n:f2.volume_usd_per_day.2026-10-->$128,569,084<!--/n--> |

Users paid <!--n:n2.fees_usd_per_day-->$206,049<!--/n--> a day in fees in the window. The protocol fee on `intents.near` is <!--n:c.intents_fee_pips-->1 pip<!--/n--> (<!--n:c.intents_fee_percent-->0.0001%<!--/n--> of the amount); what users pay, <!--n:n2.fees_bps-->16.0<!--/n--> bps of volume, is set off-chain, by NEAR Intents' terms and by the apps that route swaps to it.

**Against.** Volume and fees are DefiLlama's, from NEAR's datasets on Dune; this repository does not rebuild them from the chain. What the chain shows is the NEAR that reaches the wallets (claim C). DefiLlama's revenue is, by its adapter, those same inflows, so the two agreeing (<!--n:n2.defillama_revenue_coverage-->16.5%<!--/n--> and <!--n:n1.coverage_with_front_end-->16.5%<!--/n--> of issuance) shows that the wallets sent almost nothing out, not that the inflows were fees. The rise is not a line: October was <!--n:f2.change.2026-09_2026-10.volume_usd-->-20%<!--/n--> on September, and counted in NEAR the fees fell <!--n:lr.history.2026-04_2026-10.fees_near_multiple-->×0.5<!--/n--> from April to October while the price rose <!--n:lr.history.2026-04_2026-10.mean_price_multiple-->×3.6<!--/n-->. "Real", in this repository's title, means what can be shown: users pay these fees in DefiLlama's data, and NEAR arrives in the buybacks wallets on mainnet. No swap from fee income to those inflows is traced here, so the chain does not prove the inflows are fees. DefiLlama's separate bridge dataset (Across, Relay, deBridge), which counts deposits rather than swaps, is not compared.

**Check.** `python scripts/demand.py --verify` → `OK`.

### B. Capture is a policy, not a mechanism

The claim the rest depends on. Six records point the same way.

1. **Code.** Nothing burns or locks the NEAR bought back. The <!--n:n1.wallets_held_near-->4,109,089<!--/n--> NEAR the wallets hold can be moved by their signers: <!--n:c.buybacks_confirmations-->2 of 4<!--/n--> for the buybacks wallet, <!--n:c.front_end_transfer-->2 of 5<!--/n--> for the front-end fund (`fefundsadmin.sputnik-dao.near`, which holds near-intents.org's own fees; see C).
2. **Who runs the treasury.** Bitwise's prospectus for its NEAR ETF (SEC, 24 September 2026): 10% of issuance "is given to the NEAR Protocol treasury, which is currently managed by the NEAR Foundation" ([424B3](https://www.sec.gov/Archives/edgar/data/0002067111/000121390026103106/ea0306486-424b3_bitwise.htm)). On chain that is `treasury.near`, where <!--n:c.treasury_confirmations-->2 of 4<!--/n--> keys approve each payment.
3. **Who sets the take rate.** NEAR Intents' docs: "Authenticated partners on the generic policy get a 50/50 revenue share by default", and "Exceptions and custom agreements exist" ([fees](https://docs.near-intents.org/resources/fees)). The last fee change on `intents.near` was on <!--n:h.fee.last-->2025-10-02<!--/n-->: the 2026 rise in the share NEAR keeps did not come from the protocol fee setting. The contract's code did change (<!--n:c.intents_code_changes-->20<!--/n--> times, last on <!--n:c.intents_code_last_change_utc-->2026-10-07<!--/n-->), and the fees users pay are set off-chain.
4. **A vote is not a rule.** HSP-027 (remove the developer gas rebate) passed on 3 July 2026; the same SEC filing, on 24 September, still said "70% of the transaction fee is burned". The chain changed at block <!--n:pr.v87.first_height-->223,012,337<!--/n--> (<!--n:pr.v87.first_utc-->2026-11-04 11:46 UTC<!--/n-->), <!--n:pr.v87.days_from_hsp027_passed-->124<!--/n--> days after the vote, when validators ran the release. HSP-029 (issuance cut) passed on 2 November and waits for the same step.
5. **The docs and the contract differ.** NEAR AI's docs call its staking-for-credits rate "network-wide, not a fixed setting" ([docs](https://docs.near.ai/cloud/staking-for-inference/overview)). On chain, one account changed it <!--n:f6.change1.ratio-->×2.0<!--/n--> on <!--n:f6.change1.utc-->2026-09-29 14:21 UTC<!--/n-->, with no DAO proposal, and the pool keeps <!--n:c.nearai_pool_reward_fee-->100%<!--/n--> of rewards ([details](docs/DETAILS.md#the-near-ai-farm)).
6. **Where the treasury's payout went.** `treasury.near` paid <!--n:ts.year_out_near-->30,171,200<!--/n--> NEAR to three accounts in April and May 2026. On 1 November those three held <!--n:tt.first_receivers_held_near-->302<!--/n--> NEAR: between May and October the NEAR had moved on, through <!--n:tt.accounts_followed-->6<!--/n--> accounts in <!--n:tt.transfers_followed-->7<!--/n--> transfers of at least 1,000 NEAR, to accounts where it mixes with other NEAR. None of the transfers was a stake. Who holds those accounts, and why, is not on chain ([details](docs/DETAILS.md#where-the-treasury-payout-went)).

**Against.** The policy has been kept: from April to October the three wallets held on to <!--n:f2.wallets_kept_share_of_revenue.2026-04_2026-10-->96.9%<!--/n--> of what flowed in. That is seven months of data, not years. A policy kept long enough would be worth almost as much as a rule; this thesis prices the difference as the gap between Hold and Buy, not as a reason to sell.

**Check.** `python scripts/control_map.py --verify` and `python scripts/control_history.py --verify` (the 5 DAOs and their 390 proposals); `python scripts/farm_rate.py --verify` and `python scripts/stakers.py --verify` (the rate change and the farm); `python scripts/treasury_trace.py --verify` (point 6). Each ends with `OK`.

### C. It is small

The buybacks keep <!--n:n1.buybacks_near_per_day-->9,570<!--/n--> NEAR a day against <!--n:n1.new_near_per_day-->88,392<!--/n--> issued: coverage <!--n:n1.coverage_buybacks-->10.8%<!--/n-->, or <!--n:n1.coverage_with_front_end-->16.5%<!--/n--> counting the front-end fund. If NEAR kept every fee, <!--n:n2.max_coverage-->47.9%<!--/n-->; fees alone would cover issuance at a NEAR price of <!--n:n2.equilibrium_price_usd-->$2.33<!--/n-->. How it is measured: [below](#why-the-chain-not-the-dashboards).

**Why two numbers.** NEAR's blog says its "owned front-end captures 100% of its fees and routes them to NEAR buybacks" ([Q2 2026](https://www.near.org/blog/the-state-of-near-q-2-2026)). Those fees reach `fefundsadmin.sputnik-dao.near`, a different DAO with other signers (<!--n:c.front_end_rules-->1 of 5<!--/n--> can change its rules), so we count it separately.

**Against.** Coverage in NEAR falls when the price rises. In dollars the buybacks kept <!--n:lr.history.2026-04_2026-10.buybacks_kept_usd_multiple-->×7.5<!--/n--> more a day in October than in April, of which <!--n:lr.history.2026-04_2026-10.mean_price_multiple-->×3.6<!--/n--> is price. NEAR kept a day by month: <!--n:f1.buybacks_kept_near_per_day.2026-04-->4,675<!--/n--> in April, <!--n:f1.buybacks_kept_near_per_day.2026-09-->13,478<!--/n--> in September, <!--n:f1.buybacks_kept_near_per_day.2026-10-->9,589<!--/n--> in October.

**Check.** `python scripts/daily.py --verify`; `python scripts/coverage.py --verify`. Each ends with `OK`.

### D. Supply matters more than buybacks

A year of buybacks is about <!--n:iv.buybacks_kept_near_per_year-->3.50M<!--/n--> NEAR. Supply moves by much more:

- **Issuance:** <!--n:iv.issuance_rate_per_year-->2.46%<!--/n--> a year, worth <!--n:iv.issuance_usd_per_year-->$157.5M<!--/n--> against <!--n:iv.buybacks_kept_usd_per_year-->$17.1M<!--/n--> kept. HSP-029 cuts it once validators run it.
- **`treasury.near`:** it paid out <!--n:ts.year_out_near-->30,171,200<!--/n--> NEAR (<!--n:ts.year_out_share_of_supply-->2.3%<!--/n--> of all NEAR) in April and May 2026, <!--n:ts.year_out_years_of_buybacks-->8.6<!--/n--> years of buybacks at today's pace; it now holds <!--n:ts.balance_end_near-->1,526,304<!--/n-->.
- **Holders that are vehicles:** SVRN, a listed company, reported holding "more than 55.5 million" NEAR on 27 August 2026 ([SEC 6-K](https://www.sec.gov/Archives/edgar/data/0001869467/000091957426005810/p15060228_ex99-1.htm)).

**Against.** Supply that does not move does no harm, and none of this says what will move. What matters is that a few signers decide whether it moves, not a rule: claim B again.

**Check.** `python scripts/treasury_spend.py --verify`; `python scripts/treasury_exits.py --verify`. Each ends with `OK`.

## What a holder earns to 2031

Change in your share of all NEAR, before validator commission. Each validator sets its own commission and this repository does not read it; at an assumed 5% or 10% the staked row's first column is +<!--n:iv.staked_share_growth.commission_5-->2.19%<!--/n--> or +<!--n:iv.staked_share_growth.commission_10-->1.95%<!--/n-->. The buybacks wallets hold the NEAR they buy and burn none, so total supply grows by the full issuance and buybacks change neither row. "With HSP-029" is the rate once its cut is fully phased in: issuance and the staking yield × 16/25, everything else held. Nothing here forecasts price, fees or volume.

| | A year, today | To 1 Jan 2031, at today's rates | A year, with HSP-029 |
|---|---|---|---|
| Staked with a validator | +<!--n:iv.staked_share_growth-->2.44%<!--/n--> | +<!--n:iv.to2031.staked_share_change-->10.6%<!--/n--> | +<!--n:iv.hsp029.staked_share_growth-->1.57%<!--/n--> |
| Not staked | <!--n:iv.unstaked_share_change-->-2.40%<!--/n--> | <!--n:iv.to2031.unstaked_share_change-->-9.6%<!--/n--> | <!--n:iv.hsp029.unstaked_share_change-->-1.55%<!--/n--> |

**Hold, against what.** Hold is not a claim that NEAR will beat cash, ETH or SOL: nothing here forecasts price or return, and the three paths below are stated, not predicted. Staking moves share from unstaked to staked holders on any proof-of-stake chain whose supply grows; it is the reason to stake what you hold, not a reason to hold. The reason not to sell is narrower: the one flow to holders from NEAR Intents, the buybacks, is measured, has been kept (the wallets kept <!--n:f2.wallets_kept_share_of_revenue.2026-04_2026-10-->96.9%<!--/n--> of what flowed in from April to October), and the rules turn to Avoid if it stops. The downside is the bear path below. A reader who weighs it more may sell today, and this thesis cannot show them wrong; it states when the evidence would.

Hold protects your share, not its dollar value. What the buybacks add is money from outside: they keep <!--n:iv.buybacks_kept_usd_per_year-->$17.1M<!--/n--> a year against <!--n:iv.issuance_usd_per_year-->$157.5M<!--/n--> of NEAR issued. While they never sell, the NEAR outside their wallets grows about <!--n:iv.net_dilution_buybacks-->2.20%<!--/n--> a year instead of <!--n:iv.issuance_rate_per_year-->2.46%<!--/n-->.

**In dollars, three stated paths to 2031.** A holder's dollars change by the share change above times the change in the value of all NEAR. Three paths for that value, each built from figures in this repository, with no probability on any ([how](docs/DETAILS.md#three-paths-to-2031)):

| Path for the value of all NEAR, window to 1 Jan 2031 | All NEAR | Staked, in $ | Not staked, in $ |
|---|---|---|---|
| **Bear.** The buybacks stop, and NEAR is valued on its gas alone at the median of the four L1s in the peers table (<!--n:sc.l1_peer_median_multiple-->2,695×<!--/n--> a year of revenue) | <!--n:sc.bear.value_change-->-34%<!--/n--> | <!--n:sc.bear.staked_usd_change-->-27%<!--/n--> | <!--n:sc.bear.unstaked_usd_change-->-40%<!--/n--> |
| **Base.** The value of all NEAR stays at <!--n:sc.base.value_usd-->$6.39B<!--/n--> | <!--n:sc.base.value_change-->0%<!--/n--> | +<!--n:sc.base.staked_usd_change-->11%<!--/n--> | <!--n:sc.base.unstaked_usd_change-->-10%<!--/n--> |
| **Bull.** Intents' revenue grows at Buy's (a) pace, <!--n:sc.bull.capture_multiple-->×10.2<!--/n--> by 2031, and all NEAR keeps today's <!--n:peer.near_all.mcap_to_revenue-->234×<!--/n--> of revenue | +<!--n:sc.bull.value_change-->871%<!--/n--> | +<!--n:sc.bull.staked_usd_change-->973%<!--/n--> | +<!--n:sc.bull.unstaked_usd_change-->777%<!--/n--> |

From the window's mean price, <!--n:n2.mean_price_usd-->$4.88<!--/n-->. From the price at the peers fetch, <!--n:peer.near.price_usd-->$3.71<!--/n-->, the bear path is <!--n:sc.bear.value_change.at_fetch-->-13%<!--/n--> for all NEAR, <!--n:sc.bear.staked_usd_change.at_fetch-->-4%<!--/n--> staked and <!--n:sc.bear.unstaked_usd_change.at_fetch-->-22%<!--/n--> not staked; base and bull are the same in percent. The base path is the staking rate on share, +<!--n:iv.staked_share_growth-->2.44%<!--/n--> a year. The bear path is what Avoid is built to catch. The bull path is what Buy asks for: capture <!--n:sc.bull.capture_multiple-->×10.2<!--/n--> in about four years, where from April to October it grew <!--n:lr.history.2026-04_2026-10.buybacks_kept_usd_multiple-->×7.5<!--/n--> in dollars, most of it price (<!--n:lr.history.2026-04_2026-10.mean_price_multiple-->×3.6<!--/n-->).

**What Buy would need.** For buybacks to cover issuance on 1 January 2031, what they keep must grow <!--n:lr.required_growth.buybacks.A.2031-->+75%<!--/n--> a year at today's issuance, or <!--n:lr.required_growth.buybacks.B.2031-->+56%<!--/n--> with HSP-029. If NEAR kept every fee, fees would need <!--n:lr.required_growth.all_fees.B.2031-->+9%<!--/n--> a year with HSP-029. The gap between +9% and +56% is the policy, not demand ([model](docs/DETAILS.md#issuance-to-2031)).

**Valuation, in one line.** Like for like, on its chain's gas alone, NEAR's value is <!--n:peer.near_l1.mcap_to_revenue-->4,091×<!--/n--> a year of revenue: more than Ethereum (<!--n:peer.ethereum.mcap_to_revenue-->3,394×<!--/n-->) and Solana (<!--n:peer.solana.mcap_to_revenue-->1,995×<!--/n-->). Only by counting Intents, an app the others' figures would leave out, does it fall to <!--n:peer.near_all.mcap_to_revenue-->234×<!--/n-->, and Intents' revenue is the discretionary part ([peers](docs/DETAILS.md#peers-on-one-basis); revenue over the window, supply as of <!--n:peer.value_as_of-->2026-11-06 20:31 UTC<!--/n-->, at each chain's mean price in the window). At the prices of the fetch the same figures are <!--n:peer.near_l1.mcap_at_fetch_to_revenue-->3,111×<!--/n--> on gas (Ethereum <!--n:peer.ethereum.mcap_at_fetch_to_revenue-->3,071×<!--/n-->) and <!--n:peer.near_all.mcap_at_fetch_to_revenue-->178×<!--/n--> with Intents.

## The rating as rules

`scripts/rating.py` applies these to every 30-day window and writes [`data/rating.csv`](data/rating.csv). Today: Hold in every window, and until 1 December it cannot be anything else: Avoid needs a failing window 30 days earlier and the history starts on 1 November, and Buy needs (b), and no lock exists. The rules are a monitor that can fire from then on, not evidence for Hold.

**Backtest, April to October 2026.** The same rules on each calendar month before the window ([`data/backtest.csv`](data/backtest.csv); `python scripts/backtest.py --verify`). It shows that the rules run on real months; it is not evidence for Hold. It cannot test Buy: no lock existed, so (b) failed in every month and the result could only be Hold or Avoid. And Avoid's test 1 had little chance to fire: it compares the wallets with DefiLlama's revenue, which is their inflows, so it fails only if they send a quarter back out. Avoid did not fire in any of the <!--n:bt.months-->7<!--/n--> months. It came closest in April: the wallets kept <!--n:bt.lowest_kept_share-->77%<!--/n--> of revenue against the 75% floor, April is at test 2's floor by construction, since the floor is April's level; with no March window to compare its fees with and the Confidential Intents Treasury account growing that month, the private-path rule leaves it not judged. May passed both. Without (b), coverage would still have fallen short (highest <!--n:bt.highest_coverage_counted-->15.3%<!--/n-->, September), but the growth test would have passed: from April to October what the buybacks kept grew <!--n:bt.a_pace.usd_multiple-->×7.5<!--/n--> in dollars and <!--n:bt.a_pace.near_multiple-->×2.1<!--/n--> in NEAR, against <!--n:bt.a_pace.required_multiple-->×1.32<!--/n--> needed at <!--n:lr.required_growth.buybacks.A.2031-->+75%<!--/n--> a year. So in these months the rating was decided by (b) alone, not by demand: growth did not move it, and only a published lock could. We put no probability on (b); there is no history of such a lock to set one from. Limits: calendar months, not 30-day windows, and `treasury.near` was not read for past months.

| | Rule | Read from |
|---|---|---|
| **Buy** | (b) a published rule keeps the buybacks: a declared lock with no contract and no access keys; **and** `treasury.near` sent nothing in the window; **and** either the NEAR the buybacks keep, capped at DefiLlama's revenue and fees, covers issuance, or at the yearly check it has grown <!--n:lr.required_growth.buybacks.A.2031-->+75%<!--/n--> a year in dollars and in NEAR | the chain; DefiLlama for the caps |
| **Avoid** | this 30-day window and the one ending 30 days before it each fail a test: (1) the wallets keep less than 75% of DefiLlama's revenue; (2) the buybacks keep April's <!--n:f2.buybacks_kept_usd_per_day.2026-04-->$6,270<!--/n--> a day or less. If DefiLlama's revenue is zero or a day is missing, test 1 is not judged and test 2 decides alone. Test 2 is not judged when DefiLlama's fees fell too (or cannot be compared with the earlier window) and the Confidential Intents Treasury account's stablecoins grew over the window: capture that moved to the private path is not rated as capture that stopped. Not read counts as not grown | (1) DefiLlama; (2) the chain, and the Treasury account on it |
| **Hold** | everything else, including any window that cannot be judged | |

Avoid overrides Buy. Every rule, edge case and threshold: [the rating in full](docs/DETAILS.md#the-rating-in-full).

**Why the Buy test is coverage, not price.** The rating answers one question: does a rule, rather than a choice, pay holders for the NEAR issued? Coverage measures the payment in NEAR, and (b) the rule. It sets no price target: L1 tokens are not priced on fees (Ethereum is valued at <!--n:peer.ethereum.mcap_to_revenue-->3,394×<!--/n--> a year of its revenue), so a target drawn from fees would be conviction, not evidence. That is not a claim that fees do not matter to value. Buybacks paid by rule would be the one link from NEAR Intents' demand to a holder that does not depend on how the market prices L1s; usage and narrative move the price too, and the rating does not try to measure them. Priced on all its fees, NEAR would be the cheapest L1 in the table; on gas alone it is dearer than Ethereum. No rule uses either multiple. Avoid's test 1 is an outflow test: DefiLlama's revenue is the wallets' inflows, so the wallets keep less than 75% of it only if they send a quarter of what came in back out. Test 2 is in dollars. It fires if the share of fees NEAR keeps falls back to April's (<!--n:f2.take_rate.2026-04-->8.1%<!--/n-->, against <!--n:f2.take_rate.2026-10-->34.3%<!--/n--> in October), or if the price falls far enough: at this window's NEAR kept a day, at <!--n:iv.avoid_test2_price_usd-->$0.655<!--/n--> or less, <!--n:iv.avoid_test2_price_change-->-86.6%<!--/n--> from the window's mean. So a crash alone can trigger it, after the fact.

## Why the chain, not the dashboards

DefiLlama's fees for NEAR Intents come from two NEAR datasets on Dune; its revenue counts every inflow of NEAR into the three wallets from outside them ([adapter](https://github.com/DefiLlama/dimension-adapters/blob/master/fees/near-intents/index.ts)). A match with the wallets' balances shows that little flowed out, not that the inflows were fees. Of the measures of capture, the only one that depends on no one's dataset is the wallets' balances on mainnet; issuance, burn, the signers and `treasury.near` are read from the chain too.

It matters more now. NEAR Intents' docs describe FAR as "a permissioned instance of the NEAR protocol operated by a small validator set with no public networking" and say a confidential swap "settles entirely on FAR via a `token_diff` intent, invisible to public indexers" ([docs](https://docs.near-intents.org/integration/market-makers/confidential-intents.md)). The Treasury account that backs those balances is on the public chain, and we read what it holds: <!--n:ct.priced_usd.2026-04-01-->$2.9M<!--/n--> on 1 April, <!--n:ct.priced_usd.2026-10-01-->$150.2M<!--/n--> on 1 October, <!--n:ct.priced_usd.2026-11-08-->$123.5M<!--/n--> on 8 November. Its stablecoins, which do not move with prices, rose <!--n:ct.stablecoins_change.2026-10-01_2026-11-08-->+60%<!--/n--> in five weeks, to <!--n:ct.stablecoins_usd.2026-11-08-->$37.4M<!--/n-->. Tideline, another public repository on NEAR Intents ([github](https://github.com/ervhint/tideline)), tracks the share of flow on the private path; this measures what the Treasury account holds (`python scripts/confidential_treasury.py --verify`; <!--n:ct.unpriced_tokens.2026-11-08-->58<!--/n--> of <!--n:ct.tokens_held.2026-11-08-->193<!--/n--> tokens have no price and are not counted).

**If the private path becomes the main one.** Tideline's README says an email from NEAR Intents gives 9 November for that. We have not seen the email, that page is not saved here, and we found no primary source for the date, so nothing below depends on it. What it would change here:

- **Coverage** (<!--n:n1.coverage_buybacks-->10.8%<!--/n-->, <!--n:n1.coverage_with_front_end-->16.5%<!--/n-->) reads the wallets on mainnet, so it stays measured as long as the buybacks receive NEAR there. If they stop while DefiLlama's fees hold, test 2 fails, and two such windows give Avoid. If DefiLlama's fees fall too and the Confidential Intents Treasury account grows, test 2 is not judged: capture that moved to FAR is not rated as capture that stopped. That account is read every day from 2 October to 8 November; until it is read for a later window, that window gets no such exemption.
- **Fees, volume, the ceiling** (<!--n:n2.max_coverage-->47.9%<!--/n-->) and the <!--n:n2.equilibrium_price_usd-->$2.33<!--/n--> price come from NEAR's public datasets on Dune. Swaps settled on FAR would leave them, so they would understate demand; if DefiLlama's revenue goes to zero, Avoid's test 1 is not judged and test 2 decides alone.
- **PREREG-3 tests both from 9 November:** P6 and P7 what the wallets keep, P8 whether DefiLlama still has every day.

**Pre-registered, so the method can fail in public.** Each file's SHA-256 is anchored in SocialDB (`social.near`) before its predictions are judged; results are published whatever they are ([details](docs/DETAILS.md#pre-registration)).

| File | Prediction | Probability | Result |
|---|---|---|---|
| [PREREG-2](PREREG-2.md) #4 | process check: HSP-027 in effect by 6 Nov | 0.85 | <!--n:pr.4.result-->holds<!--/n-->, Brier <!--n:pr.4.brier-->0.0225<!--/n--> |
| [PREREG-2](PREREG-2.md) #5 | process check: protocol version 88 by 8 Nov | 0.75 | <!--n:pr.5.result-->holds<!--/n-->, Brier <!--n:pr.5.brier-->0.0625<!--/n--> |
| [PREREG](PREREG.md) #1–3 | the NEAR AI farm; buybacks inflows 1–15 Nov | — | judged 16 Nov |
| [PREREG-3](PREREG-3.md) #6–8 | the buybacks keep at least half / all of the 2 October window's dollars, 9 Nov – 9 Dec; DefiLlama has every day | 0.90 / 0.75 / 0.90, measured from history | judged 9 and 11 Dec |

No prediction that tests the thesis has a result yet. #4 and #5 asked whether a passed vote would reach the chain by a date. Both held; that shows the pipeline works, not skill at forecasting (Brier: 0 is perfect, 0.25 is always saying 0.5). The predictions that test the thesis, #1–3 and #6–8, are judged on 16 November and 9–11 December, after the submission deadline, and their results go into this repository whatever they are. PREREG-3's probabilities are base rates from overlapping 30-day windows since March, which its own [limits](PREREG-3.md) count as about 5 independent ones. PREREG-3 was anchored at block <!--n:pr.anchor3.tx_block-->223,613,293<!--/n-->, before its window opened. Its baseline, the 2 October window, is $46,691.40 a day at the unrounded mean price; elsewhere it shows as <!--n:iv.buybacks_kept_usd_per_day-->$46,692<!--/n-->, from the price rounded to $4.8791 (PREREG-3 explains the difference).

## What would change our mind

| When | What we watch | If it happens |
|---|---|---|
| 9 Nov – 9 Dec | what the buybacks wallets keep, as the private path becomes the main one | PREREG-3 scores it; the rating's own tests run every day |
| any day | a published buyback rule, or a keyless lock | (b) is met; Buy then depends on coverage |
| when validators run HSP-029 | issuance falls | the Buy hurdle drops to <!--n:lr.required_growth.buybacks.B.2031-->+56%<!--/n--> |
| any day | `treasury.near` sends anything | the Buy path is closed for that window |
| 1 Nov 2027 | first yearly check | Buy only if +75% (or +56%) is met in dollars and in NEAR |

## Check it in two minutes

Python 3.10 or later (`python3` on some systems, `py` on Windows), standard library only, no network, no keys. From the repository root:

```
python scripts/rebuild.py
```

It ends with `REBUILD: PASS`: every test passes, every number recomputes from the saved raw responses, and every number on this page matches [`data/numbers.json`](data/numbers.json). The same, step by step:

```
python -m unittest discover -s tests              # every script's logic on fixed inputs
python scripts/build_numbers.py --verify           # every script's offline check, then numbers.json rebuilds the same
python scripts/build_numbers.py --check README.md  # every marked number in this file matches numbers.json
python scripts/check_prereg.py --anchor 3 --verify # PREREG-3.md = its SocialDB record = the transaction's args
python scripts/rating.py --verify                  # the rating of every window recomputes
python scripts/quotes.py --verify                  # every quoted line is in its saved page
```

For lists that name accounts, git holds redacted copies: offline, the check proves they are consistent and that their totals match the raw contract responses, not that each entry is right.

**No network is needed for anything above.** What does need it, and what to do offline instead:

| Needs the network | Offline |
|---|---|
| The [live dashboard](https://nikolaskahris-png.github.io/near-thesis-data/dashboard/) | `python -m http.server 8000` in the repository root, then open `http://localhost:8000/dashboard/` (opening the file directly does not work: browsers block its data reads from `file://`). Every figure is read from `data/numbers.json`; only the "Check live" buttons say they cannot reach the RPC. |
| Re-measuring from the chain | `python scripts/remeasure.py --only 1` stops at once with `REMEASURE: NOT RUN - ...` and exit code 2. That is the expected result offline, not a failure of the repository. |
| Reading the SocialDB anchors | `python scripts/check_prereg.py --anchor 3 --verify` checks the saved record and transaction offline. |
| The pages the text quotes (SEC filings, NEAR's docs and blog, the hackathon rules) | each is saved in `data/raw/sources/` with its SHA-256; `python scripts/quotes.py --verify` checks that every quote is in its saved page (`rebuild.py` runs it). |

Offline, the one thing that cannot be proven is that the saved responses are what the chain returned. That takes one read-only call per number, listed with the expected answers in [Verify live](docs/DETAILS.md#verify-live).

## What we can't measure

- **The fees themselves.** They come from NEAR's datasets on Dune and cannot be rebuilt from the chain here; only the revenue side is checked on chain, through the wallets' balances.
- **The private path.** Volume and fees on FAR are not visible; we read only what the Treasury account holds on mainnet.
- **Who holds an account, and why NEAR moved.** Amounts, blocks and transactions are measured; purposes are not on chain.
- **Credits in dollars** for the NEAR AI farm: an off-chain setting that can change with no trace on chain.
- **Peers' mechanisms** are compared from their docs; their numbers are DefiLlama's and CoinGecko's.

## Timeline and disclosure

- Research into data sources: 22–31 October 2026, in private notes that are not part of this repository.
- Code and data: from the first commit, 2026-10-31 13:51:52 UTC; there is no earlier code. The [rules](https://nearhackathon.com/HACKATHON.md) (FAQ Q-001) count work from the hackathon's announcement on 19 October: "Earlier commits are baseline".
- Sources: NEAR archival RPC, the NearBlocks API, DefiLlama and coins.llama.fi, SEC filings and NEAR's own docs, linked where used, and one off-chain read of a NEAR AI Cloud setting. Raw responses are saved byte for byte; those that list people's accounts are kept private, with their SHA-256.
- AI: the code, scripts and text were written with Claude Code (Anthropic), directed by the author; those commits are marked `Co-Authored-By: Claude`.
- Libraries: none beyond the Python standard library. `docs/sign*.html` load NEAR Wallet Selector 10.1.4 from esm.sh.
- This is the author's only submission to NEAR HACKATHON.

License: [MIT](LICENSE).
