# NEAR to 2031: value capture is real, small and discretionary

[![verify](https://github.com/nikolaskahris-png/near-thesis-data/actions/workflows/verify.yml/badge.svg)](https://github.com/nikolaskahris-png/near-thesis-data/actions/workflows/verify.yml)

**NEAR Intents' buybacks keep NEAR equal to <!--n:n1.coverage_buybacks-->10.8%<!--/n--> of new issuance, burn none of it, and <!--n:c.buybacks_confirmations-->2 of 4<!--/n--> signers, not code, can move it.** Growth is not what is missing (<!--n:bt.a_pace.near_multiple-->×2.1<!--/n--> in NEAR and <!--n:bt.a_pace.usd_multiple-->×7.5<!--/n--> in dollars from April to October, against the <!--n:bt.a_pace.required_multiple-->×1.32<!--/n--> that Buy's growth test asks); a published rule is. So the rating is **Hold**: keep the NEAR you own, staked, and do not add until that rule exists. Horizon 1 January 2031, checked every year.

**The problem.** Investment cases for NEAR quote the demand on NEAR Intents, but not how much of it reaches a holder or whether anything guarantees it. This repository measures both from the chain, and every number in it rebuilds offline in two minutes.

**[Live dashboard](https://nikolaskahris-png.github.io/near-thesis-data/dashboard/)** · [Check it in two minutes](#check-it-in-two-minutes) · [One-page thesis](THESIS.md) · [Every detail](docs/DETAILS.md) · [Terms](#terms) · Window: 2 October → 1 November 2026 · As of 9 November 2026; figures from other dates say so where they appear

## In sixty seconds

- **The demand is real.** Users paid <!--n:n2.fees_usd_per_day-->$206,049<!--/n--> a day in fees on NEAR Intents in the window, by DefiLlama's data.
- **Holders get a small part of it.** The buybacks wallets keep NEAR equal to <!--n:n1.coverage_buybacks-->10.8%<!--/n--> of the new NEAR issued (<!--n:n1.coverage_with_front_end-->16.5%<!--/n--> counting the front-end fund), and burn none of it.
- **It is a policy, not a rule.** No code requires the buybacks, and <!--n:c.buybacks_confirmations-->2 of 4<!--/n--> signers can move what the buybacks wallet holds.
- **It did not stop when the flow went private.** From 27 October, another public repository reports, most NEAR Intents flow settles on its private path. On mainnet the three revenue wallets kept <!--n:ps.after.kept_near_per_day-->13,800<!--/n--> NEAR a day from then to 8 November, against <!--n:ps.before.kept_near_per_day-->14,261<!--/n--> before (<!--n:ps.change.kept_near_per_day-->-3%<!--/n-->); DefiLlama's revenue, which counts the same wallets, changed <!--n:ps.change.revenue_near_per_day-->-6%<!--/n--> in NEAR. Tideline's date gives the smallest fall of five dates tried (<!--n:ps.cut.kept_near_highest-->-3%<!--/n--> to <!--n:ps.cut.kept_near_lowest-->-13%<!--/n-->), and in dollars both fell about a fifth.
- **Staking is what pays.** Staked, your share of all NEAR grows +<!--n:iv.staked_share_growth-->2.44%<!--/n--> a year before the validator's commission; unstaked, it changes <!--n:iv.unstaked_share_change-->-2.40%<!--/n-->.
- **What would change the rating.** Buy if the buybacks become a published rule and grow fast enough to cover issuance by 2031 (<!--n:lr.required_growth.buybacks.A.2031-->+75%<!--/n--> a year); Avoid if they stop. The rules can first fire on 1 December 2026, when the daily history has two windows; until then Hold is the author's reading of the claims below.

## The thesis in four claims

Each claim gives what we found, what argues against it, and the command that recomputes it with no network. Every figure in this file comes from [`data/numbers.json`](data/numbers.json), and a check fails if one differs.

### A. The demand is real

NEAR Intents moved <!--n:d.ours_30d_usd-->$4.02B<!--/n--> in DefiLlama's 30 days to <!--n:d.window_end-->7 November<!--/n--> (its latest 30 days at the fetch, not the window): <!--n:d.parent_rank-->15th<!--/n--> of <!--n:d.parent_groups_with_volume-->885<!--/n--> protocols in DefiLlama's DEX-volume overview, with each protocol's versions counted as one. Users paid <!--n:n2.fees_usd_per_day-->$206,049<!--/n--> a day in fees in the window, <!--n:n2.fees_bps-->16.0<!--/n--> bps of volume. The fee in the contract is only <!--n:c.intents_fee_pips-->1 pip<!--/n--> (<!--n:c.intents_fee_percent-->0.0001%<!--/n-->); what users pay is set off-chain, by NEAR Intents' terms and by the apps that route swaps to it.

**Against.** Volume and fees are DefiLlama's, from NEAR's datasets on Dune, and are not rebuilt from the chain here. Counted in NEAR, fees halved (<!--n:lr.history.2026-04_2026-10.fees_near_multiple-->×0.5<!--/n-->) from April to October while the price rose <!--n:lr.history.2026-04_2026-10.mean_price_multiple-->×3.6<!--/n-->. "Real" means what can be shown: users pay these fees in DefiLlama's data, and NEAR arrives in the buybacks wallets on mainnet. No swap from fee income to those inflows is traced. The volume itself may be about twice the value swapped: two other public repositories count the swaps they can see on chain at 46% of DefiLlama's figure ([soldanoandrea/near-thesis](https://github.com/soldanoandrea/near-thesis), six sampled days) and the stablecoin legs at 24% ([Axlnd3r/NePu](https://github.com/Axlnd3r/NePu), one week), so DefiLlama either counts both sides of a swap or includes swaps on the private path. Coverage, the ceiling and the rating use fees and the wallets' balances, not volume.

**Check.** `python scripts/demand.py --verify` → `OK`.

### B. It is small

Each day the buybacks wallets keep <!--n:n1.buybacks_near_per_day-->9,570<!--/n--> NEAR, against <!--n:n1.new_near_per_day-->88,392<!--/n--> new NEAR issued: coverage <!--n:n1.coverage_buybacks-->10.8%<!--/n-->, or <!--n:n1.coverage_with_front_end-->16.5%<!--/n--> counting the front-end fund. If NEAR kept every fee, coverage would be <!--n:n2.max_coverage-->47.9%<!--/n-->; fees alone would cover issuance only at a NEAR price of <!--n:n2.equilibrium_price_usd-->$2.33<!--/n--> or less. New NEAR adds <!--n:iv.issuance_rate_per_year-->2.46%<!--/n--> to supply a year, worth <!--n:iv.issuance_usd_per_year-->$157.5M<!--/n-->, against <!--n:iv.buybacks_kept_usd_per_year-->$17.1M<!--/n--> kept by the buybacks.

**Against.** Coverage is counted in NEAR and revenue is earned in dollars, so coverage falls when the price rises. In dollars the buybacks kept <!--n:lr.history.2026-04_2026-10.buybacks_kept_usd_multiple-->×7.5<!--/n--> as much a day in October as in April, of which <!--n:lr.history.2026-04_2026-10.mean_price_multiple-->×3.6<!--/n--> is the price.

**Check.** `python scripts/daily.py --verify`; `python scripts/coverage.py --verify`. Each ends with `OK`.

### C. It is a policy, not a rule

Nothing in code burns, locks or requires the buybacks, and every link can be changed by people:

1. **The bought NEAR can move.** The <!--n:n1.wallets_held_near-->4,109,089<!--/n--> NEAR the wallets hold can be moved by their signers: <!--n:c.buybacks_confirmations-->2 of 4<!--/n--> for the buybacks wallet, <!--n:c.front_end_transfer-->2 of 5<!--/n--> for the front-end fund.
2. **The treasury is managed, not coded.** The protocol treasury, `treasury.near`, is "currently managed by the NEAR Foundation" ([SEC filing](https://www.sec.gov/Archives/edgar/data/0002067111/000121390026103106/ea0306486-424b3_bitwise.htm)). It paid out <!--n:ts.year_out_near-->30,171,200<!--/n--> NEAR in April and May 2026; on 1 November the three accounts that received it held <!--n:tt.first_receivers_held_near-->302<!--/n--> NEAR. We stop where it mixes with other NEAR; another repository follows it further and reports that "20.95M NEAR of it reached the p2p-org and figment staking pools within five hops" ([soldanoandrea/near-thesis](https://github.com/soldanoandrea/near-thesis/blob/13b580f37e97d04fa0403f5c1a785f962886bddd/README.md); [where it went](docs/DETAILS.md#where-the-treasury-payout-went)). Either way, people decided where it went, not code.
3. **One account set a rate.** One account changed the NEAR AI credits rate <!--n:f6.change1.ratio-->×2.0<!--/n--> on <!--n:f6.change1.utc-->2026-09-29 14:21 UTC<!--/n-->, with no DAO proposal, and the pool keeps <!--n:c.nearai_pool_reward_fee-->100%<!--/n--> of staking rewards ([details](docs/DETAILS.md#the-near-ai-farm)).
4. **A vote is not a rule.** HSP-027 passed on 3 July 2026 and reached the chain <!--n:pr.v87.days_from_hsp027_passed-->124<!--/n--> days later, when validators ran the release. HSP-029, the issuance cut, passed on 2 November and waits for the same step.

**Against.** The policy has been kept: from April to October the wallets held on to <!--n:f2.wallets_kept_share_of_revenue.2026-04_2026-10-->96.9%<!--/n--> of what flowed in. Seven months is not years. A policy kept long enough is worth almost as much as a rule, so this thesis prices the difference as the gap between Hold and Buy, not as a reason to sell.

**Check.** `python scripts/control_map.py --verify`; `python scripts/control_history.py --verify`; `python scripts/farm_rate.py --verify`; `python scripts/treasury_trace.py --verify`. Each ends with `OK`.

### D. It did not stop when the flow went private

Private swaps on NEAR Intents settle on FAR, an instance that public indexers do not see; their funds pass through a Treasury account on the public chain. Tideline, another public repository on NEAR Intents, reads that account's transfers and reports: "Since 27 Oct 2026 swaps settle on intents.far, which public indexers cannot see", and from 2 to 8 November the account "carried 85% of the USD counted on chain" ([THESIS.md at commit 90a78e6](https://github.com/ervhint/tideline-thesis/blob/90a78e6a358315331dbb0c68548edcb736244a3e/THESIS.md), saved in `data/raw/sources/`). We take that date and read, day by day on mainnet, the three revenue wallets: the buybacks wallets (claim B's figures are these alone) and the front-end fund. DefiLlama's revenue counts NEAR flowing into the same three, so the two compare like for like:

| A day | 2–26 October | 27 October – 8 November | Change |
|---|---|---|---|
| NEAR kept by the three wallets | <!--n:ps.before.kept_near_per_day-->14,261<!--/n--> | <!--n:ps.after.kept_near_per_day-->13,800<!--/n--> | <!--n:ps.change.kept_near_per_day-->-3%<!--/n--> |
| DefiLlama's revenue, in NEAR | <!--n:ps.before.revenue_near_per_day-->14,323<!--/n--> | <!--n:ps.after.revenue_near_per_day-->13,514<!--/n--> | <!--n:ps.change.revenue_near_per_day-->-6%<!--/n--> |
| NEAR kept, in dollars | <!--n:ps.before.kept_usd_per_day-->$70,487<!--/n--> | <!--n:ps.after.kept_usd_per_day-->$57,179<!--/n--> | <!--n:ps.change.kept_usd_per_day-->-19%<!--/n--> |
| DefiLlama's revenue, in dollars | <!--n:ps.before.revenue_usd_per_day-->$70,677<!--/n--> | <!--n:ps.after.revenue_usd_per_day-->$56,007<!--/n--> | <!--n:ps.change.revenue_usd_per_day-->-21%<!--/n--> |

The wallets kept <!--n:ps.before.kept_share_of_revenue-->99.6%<!--/n--> of DefiLlama's revenue before and <!--n:ps.after.kept_share_of_revenue-->102.1%<!--/n--> after, and the after-mean in NEAR sits inside the range of every <!--n:ps.after.days-->13<!--/n--> consecutive days before (<!--n:ps.before_runs.lowest_kept_near_per_day-->12,781<!--/n--> to <!--n:ps.before_runs.highest_kept_near_per_day-->17,152<!--/n--> NEAR a day). So capture did not stop with the switch: in NEAR it fell about as much as revenue. In dollars both fell about a fifth (<!--n:ps.change.kept_usd_per_day-->-19%<!--/n--> and <!--n:ps.change.revenue_usd_per_day-->-21%<!--/n-->): NEAR's price fell over the same days, so each dollar of revenue bought more NEAR, which is why the fall is smaller in NEAR. Inside the three, the buybacks wallets kept <!--n:ps.change.buybacks_near_per_day-->+10%<!--/n--> more and the front-end fund <!--n:ps.change.front_end_near_per_day-->-27%<!--/n--> less. The result depends on the date, and Tideline's gives the smallest fall of the five tried:

| Change on | 20 Oct | 24 Oct | 27 Oct | 30 Oct | 2 Nov |
|---|---|---|---|---|---|
| NEAR kept by the three wallets | <!--n:ps.cut.2026-10-20.kept_near-->-9%<!--/n--> | <!--n:ps.cut.2026-10-24.kept_near-->-4%<!--/n--> | <!--n:ps.cut.2026-10-27.kept_near-->-3%<!--/n--> | <!--n:ps.cut.2026-10-30.kept_near-->-13%<!--/n--> | <!--n:ps.cut.2026-11-02.kept_near-->-8%<!--/n--> |
| DefiLlama's revenue, in NEAR | <!--n:ps.cut.2026-10-20.revenue_near-->-11%<!--/n--> | <!--n:ps.cut.2026-10-24.revenue_near-->-6%<!--/n--> | <!--n:ps.cut.2026-10-27.revenue_near-->-6%<!--/n--> | <!--n:ps.cut.2026-10-30.revenue_near-->-15%<!--/n--> | <!--n:ps.cut.2026-11-02.revenue_near-->-10%<!--/n--> |

The Treasury account itself held <!--n:ct.priced_usd.2026-11-08-->$123.5M<!--/n--> on 8 November, <!--n:ct.stablecoins_usd.2026-11-08-->$37.4M<!--/n--> of it in stablecoins.

**Against.** Thirteen days are a short run, the last days of DefiLlama's series can still be revised, and we take Tideline's date without re-reading its transactions. DefiLlama's revenue is built from these wallets' inflows, so the two agreeing shows that little flowed out, not which fees paid for what came in; fees charged on the private path are visible to neither. PREREG-3 tests the next 30 days.

**Check.** `python scripts/private_shift.py --verify`; `python scripts/confidential_treasury.py --verify`. Each ends with `OK`.

## What a holder earns to 2031

Your share of all NEAR. Two things lower the staked figure: your validator's commission, which this repository does not read (we assume 10%), and HSP-029, which cuts issuance and with it the staking yield, from <!--n:lr.activation_utc-->2027-02-14 16:48 UTC<!--/n--> if validators run it. With both, a staked holder's share grows <!--n:iv.to2031.staked_share_change.hsp029_commission_10-->6.3%<!--/n--> to 2031, not <!--n:iv.to2031.staked_share_change-->10.6%<!--/n-->. The buybacks hold what they buy, so they change no row.

| | A year, today | To 1 Jan 2031, today's rule | To 1 Jan 2031, with HSP-029 |
|---|---|---|---|
| Staked, before commission | +<!--n:iv.staked_share_growth-->2.44%<!--/n--> | +<!--n:iv.to2031.staked_share_change-->10.6%<!--/n--> | +<!--n:iv.to2031.staked_share_change.hsp029-->7.9%<!--/n--> |
| Staked, after an assumed 10% commission | +<!--n:iv.staked_share_growth.commission_10-->1.95%<!--/n--> | +<!--n:iv.to2031.staked_share_change.commission_10-->8.4%<!--/n--> | **+<!--n:iv.to2031.staked_share_change.hsp029_commission_10-->6.3%<!--/n-->** |
| Not staked | <!--n:iv.unstaked_share_change-->-2.40%<!--/n--> | <!--n:iv.to2031.unstaked_share_change-->-9.6%<!--/n--> | <!--n:iv.to2031.unstaked_share_change.hsp029-->-7.4%<!--/n--> |

In dollars, your holding changes by that share times the value of all NEAR. Three unweighted paths for that value, built from this repository's figures and the first row above; none is a target or a forecast ([how](docs/DETAILS.md#three-paths-to-2031)):

| Path for the value of all NEAR, window to 1 Jan 2031 | All NEAR | Staked, in $ | Not staked, in $ |
|---|---|---|---|
| **Bear.** The buybacks stop, and NEAR is valued on its gas alone at the median of the four L1s in the peers table (<!--n:sc.l1_peer_median_multiple-->2,695×<!--/n--> a year of revenue) | <!--n:sc.bear.value_change-->-34%<!--/n--> | <!--n:sc.bear.staked_usd_change-->-27%<!--/n--> | <!--n:sc.bear.unstaked_usd_change-->-40%<!--/n--> |
| **Base.** The value of all NEAR stays at <!--n:sc.base.value_usd-->$6.39B<!--/n--> | <!--n:sc.base.value_change-->0%<!--/n--> | +<!--n:sc.base.staked_usd_change-->11%<!--/n--> | <!--n:sc.base.unstaked_usd_change-->-10%<!--/n--> |
| **Bull.** Intents' revenue grows <!--n:lr.required_growth.buybacks.A.2031-->+75%<!--/n--> a year, Buy's growth test, <!--n:sc.bull.capture_multiple-->×10.2<!--/n--> by 2031, and all NEAR keeps today's <!--n:peer.near_all.mcap_to_revenue-->234×<!--/n--> of revenue | +<!--n:sc.bull.value_change-->871%<!--/n--> | +<!--n:sc.bull.staked_usd_change-->973%<!--/n--> | +<!--n:sc.bull.unstaked_usd_change-->777%<!--/n--> |

From the window's mean price, <!--n:n2.mean_price_usd-->$4.88<!--/n-->; from the price at the peers fetch, <!--n:peer.near.price_usd-->$3.71<!--/n-->, the bear path is <!--n:sc.bear.value_change.at_fetch-->-13%<!--/n--> (<!--n:sc.bear.staked_usd_change.at_fetch-->-4%<!--/n--> staked). The base path is the staking rate on share. The bear path's median hides a wide range: with each L1's own multiple instead, all NEAR would change <!--n:sc.bear.by_peer.aptos.value_change-->-90%<!--/n--> (Aptos), <!--n:sc.bear.by_peer.solana.value_change-->-51%<!--/n--> (Solana), <!--n:sc.bear.by_peer.ethereum.value_change-->-17%<!--/n--> (Ethereum) or +<!--n:sc.bear.by_peer.sui.value_change-->313%<!--/n--> (Sui). The bear path is what Avoid is built to catch. The bull path is what Buy asks for: capture <!--n:sc.bull.capture_multiple-->×10.2<!--/n--> in about four years. For scale, on its chain's gas alone NEAR's market value is <!--n:peer.near_l1.mcap_to_revenue-->4,091×<!--/n--> a year of that revenue, above Ethereum's <!--n:peer.ethereum.mcap_to_revenue-->3,394×<!--/n-->; counting Intents, <!--n:peer.near_all.mcap_to_revenue-->234×<!--/n--> ([peers](docs/DETAILS.md#peers-on-one-basis)).

## The rating as rules

`scripts/rating.py` applies these to every 30-day window and writes [`data/rating.csv`](data/rating.csv). Today it is Hold in every window, and until 1 December it cannot be anything else: Avoid needs a failing window 30 days earlier and the daily history starts on 1 November, and Buy needs (b), a lock that does not exist. Read the rules as a monitor that can fire from then on, not as evidence for Hold.

| | Rule | Read from |
|---|---|---|
| **Buy** | (b) a published rule keeps the buybacks: a declared lock with no contract and no access keys; **and** `treasury.near` sent nothing in the window; **and** either the NEAR the buybacks keep, capped at DefiLlama's revenue and fees, covers issuance, or at the yearly check it has grown <!--n:lr.required_growth.buybacks.A.2031-->+75%<!--/n--> a year in dollars and in NEAR | the chain; DefiLlama for the caps |
| **Avoid** | this 30-day window and the one ending 30 days before it each fail a test: (1) the wallets keep less than 75% of DefiLlama's revenue; (2) the buybacks keep April's <!--n:f2.buybacks_kept_usd_per_day.2026-04-->$6,270<!--/n--> a day or less. If DefiLlama's revenue is zero or a day is missing, test 1 is not judged and test 2 decides alone. Test 2 is not judged when DefiLlama's fees fell too and the Confidential Intents Treasury account grew, so capture that moved to the private path is not rated as capture that stopped | (1) DefiLlama; (2) the chain, and the Treasury account on it |
| **Hold** | everything else, including any window that cannot be judged | |

Avoid overrides Buy. The rating asks one question: does a rule, rather than a choice, pay holders for the NEAR issued? It sets no price target, because L1 tokens are not priced on fees and a target drawn from fees would be conviction, not evidence. Avoid's dollar test also fires on a crash alone: at this window's NEAR kept a day, at a price of <!--n:iv.avoid_test2_price_usd-->$0.655<!--/n--> or less. **The thresholds are the author's choice; how far they are from flipping the rating is measured.** The same rules on April to October 2026 with Avoid's floors at 50%, 75% or 90% of revenue and 0.5×, 1× or 1.5× April's dollars, Buy's growth at +50%, <!--n:lr.required_growth.buybacks.A.2031-->+75%<!--/n--> or +100% a year, and rule (b) as on chain or assumed met: <!--n:sens.combinations-->54<!--/n--> combinations, <!--n:sens.month_ratings-->378<!--/n--> monthly ratings, <!--n:sens.hold-->378<!--/n--> of them Hold (`python scripts/sensitivity.py --verify`). That grid cannot show where the rating flips, so the script also finds it: with the other thresholds at the rule's, a month of the seven becomes Avoid only if test 1's floor is raised to <!--n:sens.flip.kept_share_floor-->98.7%<!--/n--> of revenue, or test 2's to <!--n:sens.flip.usd_floor_x_april-->×2.49<!--/n--> April's dollars. In these monthly ratings Buy can come only from coverage of 100%, because the growth test is judged once a year; the best month reached <!--n:bt.highest_coverage_counted-->15.3%<!--/n-->. Growth is not what blocks Buy: from April to October what the buybacks kept grew <!--n:bt.a_pace.usd_multiple-->×7.5<!--/n--> in dollars and <!--n:bt.a_pace.near_multiple-->×2.1<!--/n--> in NEAR, against the <!--n:bt.a_pace.required_multiple-->×1.32<!--/n--> the test asks, so with a published rule that history would have met it.

Every rule, edge case and the backtest on April to October: [the rating in full](docs/DETAILS.md#the-rating-in-full).

## Predictions, anchored before they are judged

Each file's SHA-256 is anchored on NEAR mainnet, in SocialDB (`social.near`), before its predictions are judged, and no file has been amended since: `python scripts/check_prereg.py --file` (add `--anchor 2` or `--anchor 3` for the others) compares each file with its anchored hash, with no network. Results go into this repository whatever they are ([details](docs/DETAILS.md#pre-registration)).

| File | Prediction | Probability | Result |
|---|---|---|---|
| [PREREG-2](PREREG-2.md) #4 | process check: HSP-027 in effect by 6 Nov | 0.85 | <!--n:pr.4.result-->holds<!--/n-->, Brier <!--n:pr.4.brier-->0.0225<!--/n--> |
| [PREREG-2](PREREG-2.md) #5 | process check: protocol version 88 by 8 Nov | 0.75 | <!--n:pr.5.result-->holds<!--/n-->, Brier <!--n:pr.5.brier-->0.0625<!--/n--> |
| [PREREG](PREREG.md) #1–3 | the NEAR AI farm; buybacks inflows 1–15 Nov | — | judged 16 Nov |
| [PREREG-3](PREREG-3.md) #6–8 | the buybacks keep at least half / all of the 2 October window's dollars, 9 Nov – 9 Dec; DefiLlama has every day | 0.90 / 0.75 / 0.90, measured from history | judged 9 and 11 Dec |

No prediction that tests the thesis has a result yet: #4 and #5 only show that the pipeline works (Brier: 0 is perfect, 0.25 is always saying 0.5). #1–3 and #6–8 are judged after the submission deadline. PREREG-3 was anchored at block <!--n:pr.anchor3.tx_block-->223,613,293<!--/n-->, before its window opened; its probabilities are base rates from history, about 5 independent windows, and its baseline of $46,691.40 a day is the <!--n:iv.buybacks_kept_usd_per_day-->$46,692<!--/n--> used elsewhere before rounding the price.

## What would change our mind

| When | What we watch | If it happens |
|---|---|---|
| 9 Nov – 9 Dec | what the buybacks wallets keep, now that the private path is the main one | PREREG-3 scores it; the rating's own tests run every day |
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

## Terms

- **Buybacks wallets:** `buybacks.multisignature.near` and `1csfundsadmin.sputnik-dao.near`, where NEAR bought with NEAR Intents' fees is kept.
- **Front-end fund:** `fefundsadmin.sputnik-dao.near`, a separate DAO that holds near-intents.org's own fees.
- **Coverage:** NEAR the buybacks wallets keep ÷ new NEAR issued, over the same 30 days.
- **(a)** the growth test for Buy: what the buybacks keep grows <!--n:lr.required_growth.buybacks.A.2031-->+75%<!--/n--> a year, in dollars and in NEAR. **(b)** the rule test: a published lock that no one can spend from.
- **FAR:** NEAR Intents' private instance; swaps settled there are not visible to public indexers.
- **HSP-027 / HSP-029:** House of Stake proposals: remove the developer gas rebate (in force) and cut issuance (passed, not yet in force).
- **pip:** a millionth of the amount (1 pip = 0.0001%).
- More: [Terms](docs/DETAILS.md#terms).

## Timeline and disclosure

- Research into data sources: 22–31 October 2026, in private notes that are not part of this repository.
- Code and data: from the first commit, 2026-10-31 13:51:52 UTC; there is no earlier code. The [rules](https://nearhackathon.com/HACKATHON.md) (FAQ Q-001) count work from the hackathon's announcement on 19 October: "Earlier commits are baseline".
- Sources: NEAR archival RPC, the NearBlocks API, DefiLlama and coins.llama.fi, SEC filings and NEAR's own docs, linked where used, and one off-chain read of a NEAR AI Cloud setting. Raw responses are saved byte for byte; those that list people's accounts are kept private, with their SHA-256.
- AI: the code, scripts and text were written with Claude Code (Anthropic), directed by the author; those commits are marked `Co-Authored-By: Claude`.
- Libraries: none beyond the Python standard library. `docs/sign*.html` load NEAR Wallet Selector 10.1.4 from esm.sh.
- This is the author's only submission to NEAR HACKATHON.

License: [MIT](LICENSE).
