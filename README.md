# NEAR to 2031: value capture is real, small and discretionary

[![verify](https://github.com/nikolaskahris-png/near-thesis-data/actions/workflows/verify.yml/badge.svg)](https://github.com/nikolaskahris-png/near-thesis-data/actions/workflows/verify.yml)

**For each $1 of new NEAR issued, NEAR Intents' buybacks buy NEAR worth about <!--n:iv.cents_per_new_dollar-->11 cents<!--/n--> and keep it in wallets that <!--n:c.buybacks_confirmations-->2 of 4<!--/n--> multisig signers can move.** None of it is burned or locked.

**Rating to 2031: Hold.** Keep your NEAR staked; do not add more. The rating covers what holders are paid from fees by rule, not NEAR's value as a chain ([the rest of the value](#what-a-holder-earns-to-2031)).

**In plain words.** NEAR Intents swaps tokens across blockchains for a fee, and part of the fees buys NEAR: the buybacks. NEAR also issues new tokens every day, which dilutes anyone who does not stake. We measure on mainnet how much of that dilution the buybacks offset, and whether any rule guarantees it.

## Why Hold

| Question | Answer | The number |
|---|---|---|
| How much of the new NEAR do the buybacks offset? | A small part | <!--n:n1.coverage_buybacks-->10.8%<!--/n--> (95% interval <!--n:ci.coverage_buybacks.low-->9.5%<!--/n-->–<!--n:ci.coverage_buybacks.high-->12.4%<!--/n-->): <!--n:iv.buybacks_kept_usd_per_year-->$17.1M<!--/n--> a year bought, against <!--n:iv.issuance_usd_per_year-->$157.5M<!--/n--> of NEAR issued |
| Does a rule guarantee it? | No: it is a choice | nothing locks or burns it, and <!--n:c.buybacks_confirmations-->2 of 4<!--/n--> signers can move it. A House of Stake (NEAR governance) draft of 8 November, not yet voted, would put a dedicated share of fees in US Treasury bills before any buyback ([saved copy](data/raw/sources/hos_draft_2026_11_08.md)) |
| Is the demand real? | Yes, but most fees stay with the apps that route swaps | users paid <!--n:n2.fees_usd_per_day-->$206,049<!--/n--> a day in fees (DefiLlama) |
| Are holders paid more elsewhere? | Yes | what reaches NEAR holders is <!--n:peer.near.holders_yield_on_mcap-->0.40%<!--/n--> of NEAR's market value a year (almost all NEAR circulates, so one basis); Hyperliquid's is <!--n:peer.hyperliquid.holders_yield_on_mcap-->4.09%<!--/n--> of its circulating value (<!--n:peer.hyperliquid.holders_yield_on_fdv-->1.03%<!--/n--> fully diluted), and the tokens it buys sit at an address with no key ([The Block](https://www.theblock.co/news/defi/2025-12-17-hyper-foundation-proposes-removing-1-billion-hype-tokens-from-circulating-supply-by-zeroing-out-hyperliquids-assistance-fund-383091)) |
| Is the chain's own use growing? | No | daily transactions <!--n:u.txns.change-->-83%<!--/n--> in a year (<!--n:u.txns_not_meta.change-->-58%<!--/n--> leaving out relayed ones, which fell in one step in April); all its gas paid <!--n:u.fee_usd_year-->$1.2M<!--/n--> a year |

**Stay staked:** most new NEAR pays stakers; a staker bears only the treasury's <!--n:c.treasury_share_of_new_supply-->10.1%<!--/n--> slice and the validator's commission. Your share of all NEAR grows +<!--n:iv.staked_share_growth-->2.44%<!--/n--> a year staked and falls (<!--n:iv.unstaked_share_change-->-2.40%<!--/n-->) unstaked. **Do not add:** what reaches holders is small, and no rule fixes it.

**What would change the rating**

- **Buy:** the bought NEAR moves to a lock the chain shows cannot send it out, *and* the buybacks reach <!--n:iv.wallets_multiple_buybacks-->×9.2<!--/n--> today's pace, enough to offset all new NEAR (or grow <!--n:lr.required_growth.buybacks.A.2031-->+75%<!--/n--> a year, checked each 1 November).
- **Avoid, at once:** the amount of NEAR the buybacks hold (an amount, not a price; NEAR staked from them counts as gone) falls more than 10% below its peak. This is the drain test; the dashboard runs it live from the chain. [All the rules](#the-rating-as-rules).

![For the NEAR issued each day, the buybacks keep about a tenth; all fees would cover under half](docs/coverage.svg)

**What this repository adds:** a rating that is code and re-reads mainnet every day (today an alarm for Avoid; Buy needs a lock that does not exist) · predictions hashed on chain before they are judged, one of them judged automatically by a daily GitHub Action · the same rules run on four other protocols.

**[Live dashboard](https://nikolaskahris-png.github.io/near-thesis-data/dashboard/)** · [Try it in two minutes](#try-it-in-two-minutes) · [One-page thesis](THESIS.md) · [Every detail](docs/DETAILS.md) · [Terms](#terms) · Window: 2 October → 1 November 2026; any other date is named where used

## Try it in two minutes

1. **Open the [dashboard](https://nikolaskahris-png.github.io/near-thesis-data/dashboard/).** You see the rating, Hold, and the drain test read live from NEAR mainnet: the NEAR the buybacks hold, against the line 10% below its peak.
2. **On the "Buybacks wallets" card, press Check live.** Your browser reads mainnet and compares with the saved answer.
3. **In "Re-run it", move the sliders.** They start at today's <!--n:n1.coverage_buybacks-->10.8%<!--/n-->. Press "Hypothetical: buybacks locked, fees ×9.2 → Buy" to see what Buy takes.
4. **Run `python scripts/rebuild.py`.** It ends with `REBUILD: PASS`: every number on this page recomputed offline, no network, no keys, and PREREG.md checked against the hash anchored on mainnet.

## Also measured

- **It did not stop when swaps went private.** From 27 October to 8 November (13 days, running past the window's end), when swaps began to settle privately, the NEAR kept a day by the three revenue wallets (the two buybacks wallets and the front-end fund) changed by <!--n:ps.change.kept_near_per_day-->-3%<!--/n-->. That cannot be told from no change (<!--n:ci.shift.kept_near.low-->-28%<!--/n--> to <!--n:ci.shift.kept_near.high-->+28%<!--/n-->), but a stop would show as about -100% ([claim D](#d-it-did-not-stop-when-the-flow-went-private)).
- **The front-end fund**, a third wallet that keeps near-intents.org's own fees, raises coverage to <!--n:n1.coverage_with_front_end-->16.5%<!--/n-->; the Buy rule counts the two buybacks wallets' <!--n:n1.coverage_buybacks-->10.8%<!--/n-->.
- **People decide issuance too**, but only through a release that validators with <!--n:c.issuance_upgrade_stake_threshold-->4/5<!--/n--> of stake run.

## What to watch from Monday, 16 November

- The bought NEAR, every day, on the [dashboard](https://nikolaskahris-png.github.io/near-thesis-data/dashboard/): a drain turns the rating to Avoid.
- The House of Stake draft of 8 November: does it get a number and a vote?
- HSP-029, the issuance cut, leaves its timelock at <!--n:f8.timelock_end_utc-->2026-11-16 16:48 UTC<!--/n-->; it cuts issuance only once validators run a release.

## The thesis in five claims

Every marked figure comes from [`data/numbers.json`](data/numbers.json); a check fails if one differs. Each claim with every source: [long version](docs/DETAILS.md#v5-the-thesis-in-four-claims).

### A. The demand is real

NEAR Intents moved <!--n:d.ours_30d_usd-->$4.02B<!--/n--> in DefiLlama's latest 30 days, to <!--n:d.window_end-->7 November<!--/n-->, <!--n:d.parent_rank-->15th<!--/n--> of <!--n:d.parent_groups_with_volume-->885<!--/n--> protocols by DEX volume on DefiLlama. Users paid <!--n:n2.fees_usd_per_day-->$206,049<!--/n--> a day in fees in the window, most of it to the apps that route swaps.

**Against.** Volume and fees are DefiLlama's; NearBlocks, indexing the chain, sees <!--n:u.visible.before_private-->66%<!--/n--> of that volume before the private path ([claim E](#e-the-chain-is-used-less-and-its-use-pays-holders-almost-nothing)). Coverage and the rating use fees and wallet balances, not volume.

**Check.** `python scripts/demand.py --verify` → `OK`.

### B. It is small

Each day the buybacks wallets keep <!--n:n1.buybacks_near_per_day-->9,570<!--/n--> NEAR, against <!--n:n1.new_near_per_day-->88,392<!--/n--> new NEAR issued: coverage <!--n:n1.coverage_buybacks-->10.8%<!--/n-->. Resampled by week, it lies between <!--n:ci.coverage_buybacks.low-->9.5%<!--/n--> and <!--n:ci.coverage_buybacks.high-->12.4%<!--/n--> (95%); by month since April, <!--n:f1.coverage_buybacks.2026-04-->5.3%<!--/n--> to <!--n:f1.coverage_buybacks.2026-09-->15.3%<!--/n-->. If NEAR kept every fee, coverage would be <!--n:n2.max_coverage-->47.9%<!--/n-->; fees alone would cover issuance only at a NEAR price of <!--n:n2.equilibrium_price_usd-->$2.33<!--/n--> or less. New NEAR adds <!--n:iv.issuance_rate_per_year-->2.46%<!--/n--> to supply a year.

**Against.** Coverage is in NEAR and revenue in dollars, so coverage falls when the price rises; in dollars the buybacks kept <!--n:lr.history.2026-04_2026-10.buybacks_kept_usd_multiple-->×7.5<!--/n--> as much a day in October as in April. And most new NEAR goes to stakers: <!--n:c.treasury_share_of_new_supply-->10.1%<!--/n--> goes to `treasury.near`, and the buybacks keep <!--n:iv.buybacks_over_treasury_issuance-->107%<!--/n--> of that slice. So a staked holder is diluted only by that slice and the validator's commission; coverage measures what the buybacks give back against all new NEAR.

**Check.** `python scripts/daily.py --verify`; `python scripts/coverage.py --verify`; `python scripts/intervals.py --verify`. Each ends with `OK`.

### C. It is a policy, not a rule

Nothing in code burns, locks or requires the buybacks. The three revenue wallets' <!--n:n1.wallets_held_near-->4,109,089<!--/n--> NEAR moves with <!--n:c.buybacks_confirmations-->2 of 4<!--/n--> signers for each buybacks wallet and <!--n:c.front_end_transfer-->2 of 5<!--/n--> for the front-end fund. A passed vote is not yet a rule: HSP-027 passed on 3 July 2026 and reached the chain <!--n:pr.v87.days_from_hsp027_passed-->124<!--/n--> days later, and HSP-029, the issuance cut, waits for the same step. The protocol treasury and NEAR AI's links work the same way ([control map](docs/DETAILS.md#the-control-map-other-links)).

**Against.** The policy has been kept: April to October the wallets held <!--n:f2.wallets_kept_share_of_revenue.2026-04_2026-10-->96.9%<!--/n--> of what flowed in. A policy kept for years is worth almost a rule, so the gap costs Buy, not Hold.

**Check.** `python scripts/control_map.py --verify`; `python scripts/control_history.py --verify`. Each ends with `OK`.

### D. It did not stop when the flow went private

From 27 October swaps began to settle privately on FAR, unseen by public indexers; from 2 to 8 November it carried 85% of the dollars counted on chain ([Tideline at commit 90a78e6](https://github.com/ervhint/tideline-thesis/blob/90a78e6a358315331dbb0c68548edcb736244a3e/THESIS.md), another public repository). DefiLlama's revenue counts the same three wallets we read daily:

| A day, in NEAR | 2–26 October | 27 October – 8 November | Change |
|---|---|---|---|
| Kept by the three wallets | <!--n:ps.before.kept_near_per_day-->14,261<!--/n--> | <!--n:ps.after.kept_near_per_day-->13,800<!--/n--> | <!--n:ps.change.kept_near_per_day-->-3%<!--/n--> |
| DefiLlama's revenue | <!--n:ps.before.revenue_near_per_day-->14,323<!--/n--> | <!--n:ps.after.revenue_near_per_day-->13,514<!--/n--> | <!--n:ps.change.revenue_near_per_day-->-6%<!--/n--> |

In dollars the wallets kept <!--n:ps.change.kept_usd_per_day-->-19%<!--/n--> a day, mostly the price. The fall in NEAR is inside the noise: resampling the days gives <!--n:ci.shift.kept_near.low-->-28%<!--/n--> to <!--n:ci.shift.kept_near.high-->+28%<!--/n--> for the wallets (95%); no block length tried goes below <!--n:ci.shift.kept_near.lowest_any_block-->-30%<!--/n-->, and shuffling the 38 days gives p = <!--n:ci.shift.kept_near.permutation_p-->0.83<!--/n-->. A stop would be near -100%. The private path's account on mainnet held <!--n:ct.priced_usd.2026-11-08-->$123.5M<!--/n--> on 8 November, <!--n:ct.stablecoins_usd.2026-11-08-->$37.4M<!--/n--> in stablecoins.

**Against.** Thirteen days show capture did not stop, not that it held level; of five start dates tried, Tideline's gives the smallest fall, the worst <!--n:ps.cut.kept_near_lowest-->-13%<!--/n-->. [PREREG-3](PREREG-3.md) tests the next 30 days.

**Check.** `python scripts/private_shift.py --verify`; `python scripts/intervals.py --verify`. Each ends with `OK`.

### E. The chain is used less, and its use pays holders almost nothing

The track's own prompt example asks for daily transactions and active accounts, and whether NEAR Intents' volume leads network usage better than the price does ([nearai/near-hackathon-prompt-examples](https://github.com/nearai/near-hackathon-prompt-examples/blob/main/tracks/02-thesis.md)). From NearBlocks' daily statistics, November 2025 against October 2026:

| A day, 30-day means | November 2025 | October 2026 | Change |
|---|---|---|---|
| Transactions | <!--n:u.txns.first-->4.27M<!--/n--> | <!--n:u.txns.last-->716k<!--/n--> | <!--n:u.txns.change-->-83%<!--/n--> |
| Active accounts | <!--n:u.active_accounts.first-->2.77M<!--/n--> | <!--n:u.active_accounts.last-->132k<!--/n--> | <!--n:u.active_accounts.change-->-95%<!--/n--> |
| Transactions, not relayed (meta) | <!--n:u.txns_not_meta.first-->1.14M<!--/n--> | <!--n:u.txns_not_meta.last-->476k<!--/n--> | <!--n:u.txns_not_meta.change-->-58%<!--/n--> |

Most of the fall was relayed transactions, and most came in one step: <!--n:u.txns.month.2026-03-->3.48M<!--/n--> a day in March, <!--n:u.txns.month.2026-04-->947k<!--/n--> in April. All gas paid on NEAR in those twelve months was <!--n:u.fee_usd_year-->$1.2M<!--/n-->, <!--n:u.fee_share_of_issuance-->0.8%<!--/n--> of a year of new NEAR. The organizers' question: over <!--n:u.lead.weeks-->52<!--/n--> weeks, neither Intents' volume nor the price leads transactions or active accounts by 0–4 weeks that we can detect (largest correlation <!--n:u.lead.max_abs_corr-->0.22<!--/n-->, smallest p <!--n:u.lead.min_p-->0.44<!--/n-->).

NearBlocks also indexes NEAR Intents on mainnet, a check on DefiLlama: it sees <!--n:u.visible.before_private-->66%<!--/n--> of DefiLlama's volume in the 30 days before 27 October, <!--n:u.visible.after_private-->28%<!--/n--> from 27 October to 8 November and <!--n:u.visible.week_85-->12%<!--/n--> from 2 to 8 November: an independent sign of the move to the private path (claim D).

**Against.** These are NearBlocks' own aggregates, not rebuilt from blocks, and what counts as an active or relayed account is its definition. Fifty-two weeks give little power: "not detected" is not "no effect".

**Check.** `python scripts/usage.py --verify` → `OK`.

## What a holder earns to 2031

How your share of all NEAR changes; only staking moves it. HSP-029 assumed in force from <!--n:lr.activation_utc-->2027-02-14 16:48 UTC<!--/n-->.

| | A year, today | To 1 Jan 2031, today's rule | To 1 Jan 2031, with HSP-029 |
|---|---|---|---|
| Staked, before commission | +<!--n:iv.staked_share_growth-->2.44%<!--/n--> | +<!--n:iv.to2031.staked_share_change-->10.6%<!--/n--> | +<!--n:iv.to2031.staked_share_change.hsp029-->7.9%<!--/n--> |
| Staked, after a 10% commission | +<!--n:iv.staked_share_growth.commission_10-->1.95%<!--/n--> | +<!--n:iv.to2031.staked_share_change.commission_10-->8.4%<!--/n--> | **+<!--n:iv.to2031.staked_share_change.hsp029_commission_10-->6.3%<!--/n-->** |
| Not staked | <!--n:iv.unstaked_share_change-->-2.40%<!--/n--> | <!--n:iv.to2031.unstaked_share_change-->-9.6%<!--/n--> | <!--n:iv.to2031.unstaked_share_change.hsp029-->-7.4%<!--/n--> |

In dollars: that share times the value of all NEAR. No price target; three stated paths: [paths to 2031](docs/DETAILS.md#v4-what-a-holder-earns-to-2031).

**What the price implies.** NEAR is valued at <!--n:peer.near.mcap_to_revenue-->248×<!--/n--> the revenue DefiLlama counts for NEAR Intents, which flows to the three revenue wallets (<!--n:peer.near_all.mcap_to_revenue-->234×<!--/n--> adding L1 gas); Hyperliquid, Jupiter and Aave at <!--n:peer.jupiter.mcap_to_revenue-->24×<!--/n-->–<!--n:peer.aave.mcap_to_revenue-->39×<!--/n--> theirs. At their multiples, that revenue carries <!--n:iv.fee_supported_share.low-->10%<!--/n-->–<!--n:iv.fee_supported_share.high-->16%<!--/n--> of NEAR's value; carrying all of it needs <!--n:iv.breakeven_multiple.low-->×6.3<!--/n-->–<!--n:iv.breakeven_multiple.high-->×10.4<!--/n--> the revenue (<!--n:iv.breakeven_multiple.fdv.low-->×2.6<!--/n-->–<!--n:iv.breakeven_multiple.fdv.high-->×6.1<!--/n--> on fully diluted values).

**The rest of the value.** Against other layer-one chains the picture flips: counting Intents, NEAR is valued at <!--n:peer.near_all.mcap_to_revenue-->234×<!--/n--> a year of revenue, Solana at <!--n:peer.solana.mcap_to_revenue-->1,995×<!--/n-->, Ethereum at <!--n:peer.ethereum.mcap_to_revenue-->3,394×<!--/n-->; on its own gas NEAR is <!--n:peer.near_l1.mcap_to_revenue-->4,091×<!--/n-->. Layer-one tokens are priced on more than fees: staking, money, block space. That is most of NEAR's value, and this thesis does not rate it, but the use behind it is falling: <!--n:u.txns.change-->-83%<!--/n--> daily transactions in a year ([claim E](#e-the-chain-is-used-less-and-its-use-pays-holders-almost-nothing)). It rates the part a holder could be paid by rule, and finds none of it fixed.

## The rating as rules

`scripts/rating.py` applies them daily to each 30-day window ([`data/rating.csv`](data/rating.csv)). One question: does a rule, rather than a choice, pay holders for the NEAR issued?

| Rating | When | Read from |
|---|---|---|
| **Avoid** (overrides Buy) | **Either** the bought NEAR is more than 10% below its highest since 1 November (at once, until back within 10%).<br>**Or** this window and the one 30 days earlier each fail a test: (1) the three wallets keep under 75% of DefiLlama's revenue; (2) the buybacks keep April's <!--n:f2.buybacks_kept_usd_per_day.2026-04-->$6,270<!--/n--> a day or less, unless DefiLlama's fees fell (or the earlier window has no fee data) while the private path's stablecoins grew. | the chain; DefiLlama for test 1 |
| **Buy** | **All three:**<br>1. The buybacks sit in a lock the chain shows cannot send NEAR out: no contract and no keys, or a reviewed code hash (`AUDITED_CODE`, none yet) with no full-access key.<br>2. `treasury.near` sent nothing in the window.<br>3. The buybacks cover issuance, or at the yearly check on 1 November have grown <!--n:lr.required_growth.buybacks.A.2031-->+75%<!--/n--> a year, in dollars and in NEAR. A yearly pass then holds until the next check, without item 2 being checked again. | the chain; DefiLlama caps what counts |
| **Hold** | Everything else, unjudgeable windows included. | |

- **Why Hold today.** Buy needs a lock that does not exist. Across <!--n:sens.combinations-->54<!--/n--> threshold settings, <!--n:sens.hold-->378<!--/n--> of <!--n:sens.month_ratings-->378<!--/n--> monthly ratings from April to October are Hold; a monthly rating reaches Buy only through 100% coverage, so the growth thresholds among the 54 do not change it. So for now the rules can only move it to Avoid; why not to add is in [Why Hold](#why-hold).
- **A crash alone can trigger Avoid.** At this window's NEAR kept a day, test 2 fails at a price of <!--n:iv.avoid_test2_price_usd-->$0.655<!--/n--> or less.

Every note and the backtest: [the rating in full](docs/DETAILS.md#the-rating-in-full).

**The same rules on four other protocols.** `scripts/peers_rating.py` runs the same gates on them, from their docs and DefiLlama, not their chains (no drain test, no growth leg). For the peers, bought = DefiLlama's holders' revenue ÷ price; NEAR's row uses the buybacks wallets read on chain (10.8%), and on DefiLlama's basis would be <!--n:n2.defillama_revenue_coverage-->16.5%<!--/n-->. A basis is a way of counting new tokens:

| | Lock | Coverage, new tokens the protocol issues | Rating |
|---|---|---|---|
| Hyperliquid | <!--n:sr.hyperliquid.lock-->yes<!--/n--> | <!--n:sr.hyperliquid.basis1.coverage-->103%<!--/n--> at the docs' stake, <!--n:sr.hyperliquid.basis2.coverage-->98%<!--/n--> at today's; <!--n:sr.hyperliquid.basis4.coverage-->8%<!--/n--> with team unlocks | Buy at the docs' stake only, Hold on the other three |
| Pump.fun | <!--n:sr.pump.lock-->no<!--/n-->: a contract we have not reviewed | none issued; <!--n:sr.pump.basis2.coverage-->82%<!--/n--> of insider unlocks | <!--n:sr.pump.rating-->Hold<!--/n--> |
| Aave | <!--n:sr.aave.lock-->no<!--/n-->: a reserve governance can spend | — | <!--n:sr.aave.rating-->Hold<!--/n--> |
| Jupiter | <!--n:sr.jupiter.lock-->no<!--/n-->: burns go to a vote | none issued since February | <!--n:sr.jupiter.rating-->Hold<!--/n--> |

The rules can give Buy; NEAR fails the lock first ([inputs and quotes](docs/DETAILS.md#the-same-rules-on-four-other-protocols)).

## What would change our mind

- **Any day:** a drain gives Avoid (the stock rose every day from 1 to 12 November); **from mid-December**, so can the two window tests.
- **9 December 2026:** if from 9 November the buybacks keep less than half of <!--n:iv.buybacks_kept_usd_per_day-->$46,692<!--/n--> a day, PREREG-3's P6 (0.90) is scored wrong, and claim D with it.
- **Any day:** a lock plus 100% coverage (best month so far <!--n:bt.highest_coverage_counted-->15.3%<!--/n-->) gives Buy.
- **Any three months running:** coverage of 25% or more ends "small" ([the full list](THESIS.md#what-would-change-our-mind)).
- **1 November 2027, then yearly:** a lock plus growth of <!--n:lr.required_growth.buybacks.B.2031-->+56%<!--/n--> a year (with HSP-029) gives Buy.

**0.25** that the buybacks go to such a lock by 2031: our judgment, from three peers and NEAR's proposals so far ([sources](docs/DETAILS.md#how-likely-a-rule-is)).

## Objections we expect

- **"Hold is built into the rules."** No: the same rules give Hyperliquid, which has a lock, Buy on one basis ([the table](#the-rating-as-rules)). NEAR fails twice: no lock, and <!--n:n1.coverage_buybacks-->10.8%<!--/n--> coverage. Even with a lock assumed, every monthly rating since April is Hold, because only 100% coverage gives Buy month to month.
- **"HSP-029 changes the arithmetic."** It does, once validators run it: about <!--n:iv.hsp029_cents_per_new_dollar-->17 cents<!--/n--> per $1 of new NEAR, and full coverage at <!--n:iv.hsp029_wallets_multiple_buybacks-->×5.9<!--/n--> instead of <!--n:iv.wallets_multiple_buybacks-->×9.2<!--/n-->. The lock is still missing.
- **"Other repositories say 12–19%, not 10.8%."** They add burned gas, or count revenue, not balances. With all three wallets, ours is <!--n:n1.coverage_with_front_end-->16.5%<!--/n--> (<!--n:ci.coverage_with_front_end.low-->14.1%<!--/n-->–<!--n:ci.coverage_with_front_end.high-->18.7%<!--/n-->) ([definitions side by side](docs/DETAILS.md#why-public-coverage-figures-differ)).

More, including who decides issuance: [all objections](docs/DETAILS.md#v5-objections-we-expect).

## Predictions, anchored before they are judged

Each file's SHA-256 is anchored in SocialDB on mainnet before it is judged; none amended ([details](docs/DETAILS.md#pre-registration)).

| File | Prediction | Probability | Result |
|---|---|---|---|
| [PREREG-2](PREREG-2.md) #4 | process check: HSP-027 in effect by 6 Nov | 0.85 | <!--n:pr.4.result-->holds<!--/n-->, Brier <!--n:pr.4.brier-->0.0225<!--/n--> |
| [PREREG-2](PREREG-2.md) #5 | process check: protocol version 88 by 8 Nov | 0.75 | <!--n:pr.5.result-->holds<!--/n-->, Brier <!--n:pr.5.brier-->0.0625<!--/n--> |
| [PREREG](PREREG.md) #1–3 | NEAR AI farm; buybacks inflows 1–15 Nov | — | judged 16 Nov; #2 by the daily Action ([`data/prereg_judged.json`](data/prereg_judged.json)) |
| [PREREG-3](PREREG-3.md) #6–8 | buybacks keep ≥ half / all of the window's dollars, 9 Nov – 9 Dec; DefiLlama complete | 0.90 / 0.75 / 0.90 | judged 9 and 11 Dec |

#4 and #5 only test the pipeline. PREREG-3 was anchored at block <!--n:pr.anchor3.tx_block-->223,613,293<!--/n-->, before its window opened.

## Check it with one command

Python 3.10 or later (`python3` on some systems, `py` on Windows), standard library only, no network, no keys, about three minutes. From the repository root:

```
python scripts/rebuild.py
```

It runs the tests, among them `tests/test_independent.py`, a second implementation that imports nothing from `scripts/` and recomputes 10.8%, -3% and 2 of 4 from the raw responses; it recomputes every number from the saved raw responses, checks each marked number here against [`data/numbers.json`](data/numbers.json), each quote against its saved page and the chart. Each step: [AGENTS.md](AGENTS.md). Against the chain itself: [Verify live](docs/DETAILS.md#verify-live).

## How NEAR is used

- **Read.** From mainnet by archival RPC: the buybacks wallets, new NEAR issued, signers and keys, `treasury.near`, protocol upgrades.
- **Written.** Each prediction file's SHA-256 is anchored in SocialDB (`social.near`) before it is judged.
- **Every day.** A GitHub Action re-reads the chain and re-runs the rating; the dashboard reads the drain test live.

## What we can't measure

The fees (NEAR's datasets on Dune; only revenue is checked on chain), volume and fees on FAR, why NEAR moved (purposes are not on chain), the NEAR AI credits' dollar value (off-chain), and peers (from their docs, DefiLlama and CoinGecko).

## Terms

- **Buybacks wallets:** `buybacks.multisignature.near` and `1csfundsadmin.sputnik-dao.near`, where NEAR bought with NEAR Intents' fees is kept.
- **Front-end fund:** `fefundsadmin.sputnik-dao.near`, a separate DAO that holds near-intents.org's own fees. With the two above, the **three revenue wallets**.
- **Coverage:** NEAR the buybacks wallets keep (inflows less outflows) ÷ new NEAR issued (minted less gas burnt), over the same 30 days.
- **FAR:** a private instance of the NEAR protocol, run by a few validators ([NEAR Intents' docs](https://docs.near-intents.org/integration/market-makers/confidential-intents.md)); NEAR Intents' contract there is `intents.far`.
- More, including HSP-027 and HSP-029: [Terms](docs/DETAILS.md#terms).

## Timeline and disclosure

- Research: 22–31 October 2026, in private notes outside this repository. Code and data: from the first commit, 2026-10-31 13:51:52 UTC. The [rules](https://nearhackathon.com/HACKATHON.md) (FAQ Q-001) count work from the hackathon's announcement on 19 October: "Earlier commits are baseline".
- Sources: NEAR archival RPC, NearBlocks, DefiLlama, SEC filings and NEAR's docs, linked where used. Raw responses are saved byte for byte; those listing people's accounts are kept private, with their SHA-256.
- AI: code and text were written with Claude Code (Anthropic), directed by the author; those commits are marked `Co-Authored-By: Claude`. The demo video has no voice; its captions carry the narration.
- Libraries: none beyond the Python standard library. `docs/sign*.html` load NEAR Wallet Selector 10.1.4 from esm.sh.
- This is the author's only submission to NEAR HACKATHON.

License: [MIT](LICENSE).
